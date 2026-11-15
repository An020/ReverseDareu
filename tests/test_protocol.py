"""
Unit tests for DAREU USB HID protocol encoder and decoder.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "daemon"))
from protocol import (
    DareuProtocol,
    DareuReportId,
    DareuAction,
    DareuClass,
    LedEffect,
    TgKeyboardProtocol,
)


def test_packet_structure():
    pkt = DareuProtocol.build_get_battery()
    assert len(pkt) == 64
    assert pkt[0] == DareuReportId.CONTROL
    assert pkt[1] == DareuAction.GET
    assert pkt[2] == DareuClass.POWER
    assert pkt[3] == 0x00


def test_dpi_serialization():
    stages = [400, 800, 1600, 3200, 6400, 12000]
    pkt = DareuProtocol.build_set_dpi_stages(stages, active_stage=2)
    assert len(pkt) == 64
    assert pkt[1] == DareuAction.SET
    assert pkt[2] == DareuClass.SENSOR
    assert pkt[3] == 0x03 # DPI Configure
    assert pkt[4] == 6 # 6 stages

    # Check 16-bit packed DPI values
    import struct
    assert struct.unpack_from('<H', pkt, 5)[0] == 400
    assert struct.unpack_from('<H', pkt, 7)[0] == 800
    assert struct.unpack_from('<H', pkt, 9)[0] == 1600
    assert struct.unpack_from('<H', pkt, 11)[0] == 3200
    assert struct.unpack_from('<H', pkt, 13)[0] == 6400
    assert struct.unpack_from('<H', pkt, 15)[0] == 12000


def test_active_dpi_selection():
    pkt = DareuProtocol.build_set_active_dpi(3)
    assert pkt[1] == DareuAction.SET
    assert pkt[2] == DareuClass.SENSOR
    assert pkt[3] == 0x04 # DPI Active
    assert pkt[4] == 3


def test_lighting_serialization():
    pkt = DareuProtocol.build_set_lighting(
        effect=LedEffect.STATIC, r=255, g=128, b=0, brightness=90, speed=40
    )
    assert len(pkt) == 64
    assert pkt[1] == DareuAction.SET
    assert pkt[2] == DareuClass.LIGHTING
    assert pkt[3] == 0x02 # LED Effect
    assert pkt[5] == LedEffect.STATIC
    assert pkt[6] == 255
    assert pkt[7] == 128
    assert pkt[8] == 0
    assert pkt[9] == 90
    assert pkt[10] == 40


def test_battery_response_parsing():
    raw = bytearray(64)
    raw[0] = 0x07
    raw[1] = 0x03
    raw[2] = 0x07
    raw[3] = 0x00
    raw[4] = 85 # 85%
    raw[5] = 1 # Charging
    raw[6] = 98 # RSSI

    res = DareuProtocol.parse_battery_response(bytes(raw))
    assert res["percentage"] == 85
    assert res["charging"] is True
    assert res["state"] == "charging"
    assert res["rssi"] == 98


def test_polling_rate():
    pkt = DareuProtocol.build_set_polling_rate(1000)
    assert pkt[1] == DareuAction.SET
    assert pkt[2] == DareuClass.SENSOR
    assert pkt[4] == 4 # 1000Hz mapped to code 4


def test_tg_keyboard_protocol():
    # GetProfileActive (Category=0x05, Cmd=0x83)
    pkt_prof = TgKeyboardProtocol.build_get_active_profile()
    assert len(pkt_prof) == 65
    assert pkt_prof[:6] == bytes([0x00, 0x00, 0x00, 0x05, 0x83, 0x00])

    # SetDeviceMode(0) (Category=0x00, Cmd=0x03)
    pkt_mode = TgKeyboardProtocol.build_set_device_mode(0)
    assert len(pkt_mode) == 65
    assert pkt_mode[:8] == bytes([0x00, 0x00, 0x01, 0x00, 0x03, 0x00, 0x00, 0x00])

    # GetLedIdList(1) (Category=0x03, Cmd=0x80)
    pkt_reg = TgKeyboardProtocol.build_get_led_regions(1)
    assert len(pkt_reg) == 65
    assert pkt_reg[:7] == bytes([0x00, 0x00, 0x01, 0x03, 0x80, 0x01, 0x00])

    # Parse GetLedIdList response for 2 LED zones (main keys=1, side bar=2)
    resp_reg = bytearray(65)
    resp_reg[:10] = bytes([0x00, 0x02, 0x04, 0x03, 0x80, 0x01, 0x00, 0x02, 0x01, 0x02])
    assert TgKeyboardProtocol.parse_led_regions(bytes(resp_reg)) == [1, 2]

    # SetLedEffect (Static RGB #FF8040, speed=75 -> level 3)
    pkt_eff = TgKeyboardProtocol.build_set_led_effect(
        profile_id=1,
        region_id=1,
        effect=int(LedEffect.STATIC),
        speed=75,
        direction=0,
        rainbow=False,
        r=255,
        g=128,
        b=64,
    )
    assert len(pkt_eff) == 65
    assert pkt_eff[:15] == bytes([
        0x00, 0x00, 0x08, 0x03, 0x02,
        0x01, 0x00, 0x01, 0x01, 0x00,
        0x03, 0x01, 255, 128, 64,
    ])

    # SetLedBrigtness (100%)
    pkt_brt = TgKeyboardProtocol.build_set_led_brightness(
        brightness=100,
        profile_id=1,
        region_id=2,
    )
    assert len(pkt_brt) == 65
    assert pkt_brt[:9] == bytes([
        0x00, 0x00, 0x02, 0x03, 0x03,
        0x01, 0x00, 0x02, 100,
    ])

