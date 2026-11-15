"""
Mock DAREU HID Device for automated testing and CI verification.
Simulates hardware register state and returns protocol-compliant responses.
"""

from typing import Optional, List, Dict
import struct


class MockDareuDevice:
    def __init__(self, name: str = "Mock DAREU A980 Pro", vid: int = 0x260D, pid: int = 0x0037):
        self.name = name
        self.vid = vid
        self.pid = pid
        self.dev_path = "/dev/hidraw_mock0"
        self.is_tg_feature_interface = False
        self.is_open = True
        self.received_reports: List[bytes] = []

        # Internal simulated hardware state
        self.dpi_stages = [400, 800, 1600, 3200, 6400]
        self.active_dpi = 1
        self.polling_rate = 1000
        self.rgb_effect = 1
        self.rgb_color = (0, 210, 255)
        self.battery_level = 92
        self.charging = False

    def send_report(self, data: bytes) -> bool:
        """Receives an output report sent by daemon."""
        self.received_reports.append(data)
        if len(data) >= 5:
            action = data[1]
            class_id = data[2]
            cmd_id = data[3]

            # Sensor / DPI SET
            if class_id == 0x04 and cmd_id == 0x03:
                count = data[4]
                stages = []
                for i in range(min(count, 6)):
                    stages.append(struct.unpack_from('<H', data, 5 + i * 2)[0])
                self.dpi_stages = stages
            elif class_id == 0x04 and cmd_id == 0x04:
                self.active_dpi = data[4]
            # Lighting SET
            elif class_id == 0x03 and cmd_id == 0x02:
                self.rgb_effect = data[5]
                self.rgb_color = (data[6], data[7], data[8])
        return True

    def read_report(self, timeout_ms: int = 500, length: int = 64) -> Optional[bytes]:
        """Generates response report corresponding to last request."""
        if not self.received_reports:
            return None
        last = self.received_reports[-1]
        resp = bytearray(64)
        resp[0] = 0x07
        resp[1] = 0x03 # NOTIFY / RESPONSE
        resp[2] = last[2] # Class
        resp[3] = last[3] # Command

        # Battery response
        if last[2] == 0x07 and last[3] == 0x00:
            resp[4] = self.battery_level
            resp[5] = 1 if self.charging else 0
            resp[6] = 95 # RSSI
        # DPI response
        elif last[2] == 0x04 and last[3] == 0x03:
            resp[4] = len(self.dpi_stages)
            for i, val in enumerate(self.dpi_stages[:6]):
                struct.pack_into('<H', resp, 5 + i * 2, val)
            resp[17] = self.active_dpi
        return bytes(resp)

    def close(self):
        self.is_open = False
