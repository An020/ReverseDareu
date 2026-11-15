"""
Linux HID Interface for DAREU Peripherals
Manages raw communication with /dev/hidraw device nodes.
"""

import os
import glob
import time
import fcntl
import struct
import select
from typing import List, Dict, Optional, Tuple


def hidiocsfeature(length: int) -> int:
    """_IOC(_IOC_WRITE | _IOC_READ, 'H', 0x06, length)"""
    return (3 << 30) | (length << 16) | (ord('H') << 8) | 0x06


def hidiocgfeature(length: int) -> int:
    """_IOC(_IOC_WRITE | _IOC_READ, 'H', 0x07, length)"""
    return (3 << 30) | (length << 16) | (ord('H') << 8) | 0x07


# TgUsbHidDevice Vendor Feature Report signature:
# UsagePage(0xFF00), Usage(0x02), ..., Feature(Data,Var,Abs)
TG_FEATURE_DESC_SIGNATURE = bytes.fromhex("0600ff0902")

DAREU_VIDS = {
    0x260D: "DAREU Gaming",
    0x258A: "SinoWealth / DAREU",
    0x1A2C: "Semico Wireless Receiver",
    0x0C45: "Sonix Controller"
}


class HidDevice:
    def __init__(
        self,
        dev_path: str,
        name: str,
        vid: int,
        pid: int,
        is_tg_feature_interface: bool = False
    ):
        self.dev_path = dev_path
        self.name = name
        self.vid = vid
        self.pid = pid
        self.is_tg_feature_interface = is_tg_feature_interface
        self._fd: Optional[int] = None

    def open(self) -> bool:
        try:
            self._fd = os.open(self.dev_path, os.O_RDWR | os.O_NONBLOCK)
            return True
        except (OSError, PermissionError):
            return False

    def close(self):
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None

    @property
    def is_open(self) -> bool:
        return self._fd is not None

    def send_report(self, data: bytes) -> bool:
        """Sends an output report to the peripheral."""
        if self._fd is None:
            return False
        try:
            written = os.write(self._fd, data)
            return written == len(data)
        except OSError:
            return False

    def read_report(self, timeout_ms: int = 500, length: int = 64) -> Optional[bytes]:
        """Reads an input report with timeout."""
        if self._fd is None:
            return None
        r, _, _ = select.select([self._fd], [], [], timeout_ms / 1000.0)
        if not r:
            return None
        try:
            return os.read(self._fd, length)
        except OSError:
            return None

    def send_and_receive(self, request: bytes, timeout_ms: int = 500) -> Optional[bytes]:
        """Sends a request and waits for corresponding response."""
        if not self.send_report(request):
            return None
        return self.read_report(timeout_ms=timeout_ms)

    def set_feature_report(self, data: bytes) -> bool:
        """Sends a HID Feature Report via HIDIOCSFEATURE ioctl."""
        if self._fd is None:
            return False
        try:
            buf = bytearray(data)
            fcntl.ioctl(self._fd, hidiocsfeature(len(buf)), buf, True)
            return True
        except OSError:
            return False

    def get_feature_report(self, report_id: int = 0, length: int = 65) -> Optional[bytes]:
        """Reads a HID Feature Report via HIDIOCGFEATURE ioctl."""
        if self._fd is None:
            return None
        try:
            buf = bytearray(length)
            buf[0] = report_id & 0xFF
            fcntl.ioctl(self._fd, hidiocgfeature(length), buf, True)
            return bytes(buf)
        except OSError:
            return None

    def tg_command(self, packet: bytes, retries: int = 15, delay_ms: int = 12) -> Optional[bytes]:
        """
        Executes a 65-byte TgUsbHidDevice Feature Report command (HidControl.TgHidUsb.SetCommand).
        Sends HIDIOCSFEATURE(65) and polls HIDIOCGFEATURE(65) until status (resp[1] & 0x0F) == 0x02.
        """
        if len(packet) != 65:
            padded = bytearray(65)
            n = min(len(packet), 65)
            padded[:n] = packet[:n]
            packet = bytes(padded)

        if not self.set_feature_report(packet):
            return None

        report_id = packet[0]
        for _ in range(retries):
            time.sleep(delay_ms / 1000.0)
            resp = self.get_feature_report(report_id=report_id, length=65)
            if resp is None or len(resp) < 5:
                continue
            status = resp[1] & 0x0F
            if status == 0x01:
                continue
            if status == 0x02 and resp[3] == packet[3] and resp[4] == packet[4]:
                return resp
        return None


class HidManager:
    @staticmethod
    def is_tg_feature_descriptor(desc: bytes) -> bool:
        """Returns True if HID report descriptor matches TgUsbHidDevice 64-byte Vendor Feature Report."""
        return TG_FEATURE_DESC_SIGNATURE in desc and b"\xb1" in desc

    @staticmethod
    def scan_devices() -> List[HidDevice]:
        """Scans sysfs for all connected DAREU HID devices."""
        devices = []
        for uevent_path in sorted(glob.glob("/sys/class/hidraw/hidraw*/device/uevent")):
            try:
                with open(uevent_path, "r", encoding="utf-8") as f:
                    uevent_data = f.read()
                
                info: Dict[str, str] = {}
                for line in uevent_data.splitlines():
                    if "=" in line:
                        k, v = line.split("=", 1)
                        info[k.strip()] = v.strip()
                
                # HID_ID format: bus:vendor:product (e.g., 0003:0000260D:00000046)
                hid_id = info.get("HID_ID", "")
                parts = hid_id.split(":")
                if len(parts) >= 3:
                    vid = int(parts[1], 16)
                    pid = int(parts[2], 16)
                    if vid in DAREU_VIDS:
                        dev_name = info.get("HID_NAME", f"DAREU Device (PID 0x{pid:04X})")
                        dev_dir = os.path.dirname(uevent_path)
                        hidraw_node = os.path.basename(os.path.dirname(dev_dir))
                        dev_path = f"/dev/{hidraw_node}"
                        desc_path = os.path.join(dev_dir, "report_descriptor")
                        is_tg = False
                        if os.path.exists(desc_path):
                            try:
                                with open(desc_path, "rb") as df:
                                    is_tg = HidManager.is_tg_feature_descriptor(df.read())
                            except OSError:
                                pass
                        devices.append(HidDevice(dev_path, dev_name, vid, pid, is_tg_feature_interface=is_tg))
            except Exception:
                continue
        return devices
