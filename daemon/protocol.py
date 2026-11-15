"""
DAREU USB HID Protocol Implementation
Translates high-level device configuration requests into 64-byte USB HID report frames.
"""

from enum import IntEnum
import struct
from typing import Dict, Any, List, Optional


class DareuReportId(IntEnum):
    CONTROL = 0x07
    EXTENDED = 0x08
    LEGACY = 0x04


class DareuAction(IntEnum):
    GET = 0x01
    SET = 0x02
    NOTIFY = 0x03


class DareuClass(IntEnum):
    KEYBOARD = 0x01
    MOUSE = 0x02
    LIGHTING = 0x03
    SENSOR = 0x04
    PROFILE = 0x05
    MACRO = 0x06
    POWER = 0x07
    AUDIO = 0x08
    DFU = 0x09
    TEST = 0x0A


class LedEffect(IntEnum):
    OFF = 0
    STATIC = 1
    BREATHING = 2
    NEON = 3
    REACTIVE = 4
    WAVE = 5
    RAINDROP = 6
    RIPPLE = 6
    RUNNING_LIGHT = 9
    DIFFUSION = 10
    STARLIT = 11


class TgKeyboardProtocol:
    """
    UsbHidDevice.TgUsbHidDevice 65-byte HID Feature Report protocol
    used by DAREU keyboards (e.g., EK75 PRO / TK51GF).
    """
    PACKET_SIZE = 65

    @classmethod
    def _create_packet(
        cls,
        payload_len: int,
        category: int,
        command_id: int,
        profile_id: int = 0,
        report_id: int = 0,
        target_dev: int = 0
    ) -> bytearray:
        pkt = bytearray(cls.PACKET_SIZE)
        pkt[0] = report_id & 0xFF
        pkt[1] = target_dev & 0xFF
        pkt[2] = payload_len & 0xFF
        pkt[3] = category & 0xFF
        pkt[4] = command_id & 0xFF
        pkt[5] = profile_id & 0xFF
        pkt[6] = 0x00
        return pkt

    @classmethod
    def build_get_active_profile(cls, report_id: int = 0, target_dev: int = 0) -> bytes:
        """UsbHidDeviceBase.GetProfileActive (Category=0x05, Cmd=0x83)."""
        pkt = cls._create_packet(0x00, 0x05, 0x83, profile_id=0x00, report_id=report_id, target_dev=target_dev)
        return bytes(pkt)

    @classmethod
    def parse_active_profile(cls, resp: Optional[bytes]) -> int:
        if resp and len(resp) >= 6 and (resp[1] & 0x0F) == 0x02:
            return max(1, resp[5])
        return 1

    @classmethod
    def build_get_device_mode(cls, report_id: int = 0, target_dev: int = 0) -> bytes:
        """TgUsbHidDevice.GetDeviceMode (Category=0x00, Cmd=0x83)."""
        pkt = cls._create_packet(0x01, 0x00, 0x83, profile_id=0x00, report_id=report_id, target_dev=target_dev)
        return bytes(pkt)

    @classmethod
    def build_set_device_mode(cls, mode: int = 0, report_id: int = 0, target_dev: int = 0) -> bytes:
        """TgUsbHidDevice.SetDeviceMode (Category=0x00, Cmd=0x03). mode=0: HW mode, mode=1: SW driver mode."""
        pkt = cls._create_packet(0x01, 0x00, 0x03, profile_id=0x00, report_id=report_id, target_dev=target_dev)
        pkt[7] = mode & 0xFF
        return bytes(pkt)

    @classmethod
    def build_get_led_regions(cls, profile_id: int = 1, report_id: int = 0, target_dev: int = 0) -> bytes:
        """TgUsbHidDevice.GetLedIdList (Category=0x03, Cmd=0x80)."""
        pkt = cls._create_packet(0x01, 0x03, 0x80, profile_id=max(1, profile_id), report_id=report_id, target_dev=target_dev)
        return bytes(pkt)

    @classmethod
    def parse_led_regions(cls, resp: Optional[bytes]) -> List[int]:
        if resp and len(resp) >= 9 and (resp[1] & 0x0F) == 0x02:
            count = min(resp[7], 56)
            regions = [r for r in resp[8:8 + count] if r != 0]
            if regions:
                return regions
        return [1, 2]

    @classmethod
    def build_get_led_effect(
        cls,
        profile_id: int = 1,
        region_id: int = 1,
        report_id: int = 0,
        target_dev: int = 0
    ) -> bytes:
        """TgUsbHidDevice.GetLedEffect (Category=0x03, Cmd=0x82)."""
        pkt = cls._create_packet(0x01, 0x03, 0x82, profile_id=max(1, profile_id), report_id=report_id, target_dev=target_dev)
        pkt[7] = region_id & 0xFF
        return bytes(pkt)

    @classmethod
    def parse_led_effect(cls, resp: Optional[bytes]) -> Dict[str, Any]:
        if not resp or len(resp) < 12 or (resp[1] & 0x0F) != 0x02:
            return {"error": "Invalid response"}
        color_count = min(resp[11], 5)
        colors = []
        for i in range(color_count):
            off = 12 + i * 3
            if off + 3 <= len(resp):
                colors.append([resp[off], resp[off + 1], resp[off + 2]])
        return {
            "profile_id": resp[5],
            "region_id": resp[7],
            "effect": resp[8],
            "flag": resp[9],
            "rainbow": bool(resp[9] & 0x80),
            "speed_hw": resp[10],
            "color_count": color_count,
            "colors": colors
        }

    @classmethod
    def normalize_speed_to_hw(cls, speed: int) -> int:
        """Maps UI speed (0..100 or 0..4) to hardware speed level (0..4)."""
        if 0 <= speed <= 4:
            return int(speed)
        return min(4, max(0, round(speed * 4 / 100)))

    @classmethod
    def build_set_led_effect(
        cls,
        effect: int,
        r: int = 0,
        g: int = 210,
        b: int = 255,
        speed: int = 50,
        rainbow: bool = False,
        direction: int = 0,
        profile_id: int = 1,
        region_id: int = 1,
        report_id: int = 0,
        target_dev: int = 0
    ) -> bytes:
        """
        TgUsbHidDevice.SetLedEffect (Category=0x03, Cmd=0x02).
        buf[2] = 5 + 3*colorCount, buf[7] = regionId, buf[8] = effect,
        buf[9] = flag, buf[10] = speed (0..4), buf[11] = colorCount, buf[12..14] = [R, G, B].
        """
        color_bytes = [
            max(0, min(255, int(r))),
            max(0, min(255, int(g))),
            max(0, min(255, int(b)))
        ]
        payload_len = 5 + len(color_bytes)
        pkt = cls._create_packet(
            payload_len, 0x03, 0x02, profile_id=max(1, profile_id), report_id=report_id, target_dev=target_dev
        )
        flag = (0x80 if rainbow else 0x00) | (direction & 0x7F)
        pkt[7] = region_id & 0xFF
        pkt[8] = int(effect) & 0xFF
        pkt[9] = flag & 0xFF
        pkt[10] = cls.normalize_speed_to_hw(speed) & 0xFF
        pkt[11] = (len(color_bytes) // 3) & 0xFF
        for idx, val in enumerate(color_bytes):
            pkt[12 + idx] = val
        return bytes(pkt)

    @classmethod
    def build_get_led_brightness(
        cls,
        profile_id: int = 1,
        region_id: int = 1,
        report_id: int = 0,
        target_dev: int = 0
    ) -> bytes:
        """TgUsbHidDevice.GetLedBrigtness (Category=0x03, Cmd=0x83)."""
        pkt = cls._create_packet(0x02, 0x03, 0x83, profile_id=max(1, profile_id), report_id=report_id, target_dev=target_dev)
        pkt[7] = region_id & 0xFF
        return bytes(pkt)

    @classmethod
    def parse_led_brightness(cls, resp: Optional[bytes]) -> Optional[int]:
        if resp and len(resp) >= 9 and (resp[1] & 0x0F) == 0x02:
            return resp[8]
        return None

    @classmethod
    def build_set_led_brightness(
        cls,
        brightness: int = 100,
        profile_id: int = 1,
        region_id: int = 1,
        report_id: int = 0,
        target_dev: int = 0
    ) -> bytes:
        """TgUsbHidDevice.SetLedBrigtness (Category=0x03, Cmd=0x03)."""
        pkt = cls._create_packet(0x02, 0x03, 0x03, profile_id=max(1, profile_id), report_id=report_id, target_dev=target_dev)
        pkt[7] = region_id & 0xFF
        pkt[8] = max(0, min(100, int(brightness))) & 0xFF
        return bytes(pkt)


class DareuProtocol:
    PACKET_SIZE = 64

    @classmethod
    def _create_base_packet(cls, action: DareuAction, class_id: DareuClass, command_id: int, sequence: int = 0) -> bytearray:
        packet = bytearray(cls.PACKET_SIZE)
        packet[0] = DareuReportId.CONTROL
        packet[1] = int(action)
        packet[2] = int(class_id)
        packet[3] = int(command_id)
        packet[4] = int(sequence)
        return packet

    # --- Sensor / DPI Commands ---

    @classmethod
    def build_set_dpi_stages(cls, stages: List[int], active_stage: int = 0) -> bytes:
        """Configures up to 6 DPI stages and sets the active stage index."""
        pkt = cls._create_base_packet(DareuAction.SET, DareuClass.SENSOR, command_id=0x03)
        stage_count = min(len(stages), 6)
        pkt[4] = stage_count
        for i in range(stage_count):
            val = max(50, min(stages[i], 32000))
            offset = 5 + (i * 2)
            struct.pack_into('<H', pkt, offset, val)
        return bytes(pkt)

    @classmethod
    def build_set_active_dpi(cls, stage_index: int) -> bytes:
        """Switches the active DPI stage (0-indexed)."""
        pkt = cls._create_base_packet(DareuAction.SET, DareuClass.SENSOR, command_id=0x04)
        pkt[4] = max(0, min(stage_index, 5))
        return bytes(pkt)

    @classmethod
    def build_get_dpi(cls) -> bytes:
        """Queries the current DPI configuration."""
        pkt = cls._create_base_packet(DareuAction.GET, DareuClass.SENSOR, command_id=0x03)
        return bytes(pkt)

    @classmethod
    def parse_dpi_response(cls, packet: bytes) -> Dict[str, Any]:
        """Parses response packet for DPI query."""
        if len(packet) < 17:
            return {"error": "Packet too short"}
        stage_count = packet[4]
        stages = []
        for i in range(min(stage_count, 6)):
            offset = 5 + (i * 2)
            val = struct.unpack_from('<H', packet, offset)[0]
            stages.append(val)
        return {
            "stage_count": stage_count,
            "stages": stages,
            "active_stage": packet[17] if len(packet) > 17 else 0
        }

    # --- Lighting / RGB Commands ---

    @classmethod
    def build_set_lighting(
        cls,
        effect: LedEffect,
        r: int = 255,
        g: int = 255,
        b: int = 255,
        brightness: int = 100,
        speed: int = 50,
        zone: int = 0
    ) -> bytes:
        """Builds RGB lighting configuration packet."""
        pkt = cls._create_base_packet(DareuAction.SET, DareuClass.LIGHTING, command_id=0x02, sequence=zone)
        pkt[5] = int(effect)
        pkt[6] = max(0, min(r, 255))
        pkt[7] = max(0, min(g, 255))
        pkt[8] = max(0, min(b, 255))
        pkt[9] = max(0, min(brightness, 100))
        pkt[10] = max(0, min(speed, 100))
        return bytes(pkt)

    @classmethod
    def build_get_lighting(cls, zone: int = 0) -> bytes:
        """Queries active lighting effect for zone."""
        pkt = cls._create_base_packet(DareuAction.GET, DareuClass.LIGHTING, command_id=0x02, sequence=zone)
        return bytes(pkt)

    @classmethod
    def parse_lighting_response(cls, packet: bytes) -> Dict[str, Any]:
        """Parses response packet for lighting query."""
        if len(packet) < 11:
            return {"error": "Packet too short"}
        return {
            "zone": packet[4],
            "effect": LedEffect(packet[5]) if packet[5] in LedEffect._value2member_map_ else packet[5],
            "r": packet[6],
            "g": packet[7],
            "b": packet[8],
            "brightness": packet[9],
            "speed": packet[10]
        }

    # --- Power & Battery Commands ---

    @classmethod
    def build_get_battery(cls) -> bytes:
        """Queries battery level and charging status."""
        pkt = cls._create_base_packet(DareuAction.GET, DareuClass.POWER, command_id=0x00)
        return bytes(pkt)

    @classmethod
    def parse_battery_response(cls, packet: bytes) -> Dict[str, Any]:
        """Parses battery status response packet."""
        if len(packet) < 7:
            return {"error": "Packet too short"}
        percentage = min(100, max(0, packet[4]))
        charging_code = packet[5]
        charging_states = {0: "discharging", 1: "charging", 2: "full"}
        return {
            "percentage": percentage,
            "charging": charging_code == 1,
            "state": charging_states.get(charging_code, "unknown"),
            "rssi": packet[6] if len(packet) > 6 else 100
        }

    # --- Polling Rate (Sensor Attribute / Mouse Attribute) ---

    @classmethod
    def build_set_polling_rate(cls, rate_hz: int) -> bytes:
        """
        Configures polling rate.
        Mapping: 125Hz=1, 250Hz=2, 500Hz=3, 1000Hz=4, 2000Hz=5, 4000Hz=6, 8000Hz=7
        """
        rate_map = {125: 1, 250: 2, 500: 3, 1000: 4, 2000: 5, 4000: 6, 8000: 7}
        val = rate_map.get(rate_hz, 4)
        pkt = cls._create_base_packet(DareuAction.SET, DareuClass.SENSOR, command_id=0x00)
        pkt[4] = val
        return bytes(pkt)
