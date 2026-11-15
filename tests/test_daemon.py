"""
Integration tests for DareuDaemon and mock device communication.
"""

import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "daemon"))
sys.path.insert(0, str(Path(__file__).parent))

from dareud import DareuDaemon
from hid_interface import HidDevice, HidManager
from mock_device import MockDareuDevice
from protocol import LedEffect


def test_daemon_profile_lifecycle():
    daemon = DareuDaemon(mock_mode=True)
    profile = daemon.load_profile()
    assert "dpi_stages" in profile
    assert "active_stage" in profile
    assert "rgb_color" in profile


def test_daemon_request_dispatch():
    daemon = DareuDaemon(mock_mode=True)
    mock_dev = MockDareuDevice()
    daemon.devices = [mock_dev]

    # Test ping
    res = daemon.handle_request({"cmd": "ping"})
    assert res["status"] == "ok"
    assert res["mock_mode"] is True

    # Test get_devices
    res = daemon.handle_request({"cmd": "get_devices"})
    assert res["status"] == "ok"
    assert len(res["devices"]) > 0

    # Test set_dpi
    new_stages = [600, 1200, 2400, 4800]
    res = daemon.handle_request({"cmd": "set_dpi", "params": {"stages": new_stages, "active": 2}})
    assert res["status"] == "ok"
    assert daemon.profile["dpi_stages"] == new_stages
    assert daemon.profile["active_stage"] == 2
    assert mock_dev.dpi_stages == new_stages
    assert mock_dev.active_dpi == 2

    # Test set_rgb
    res = daemon.handle_request({
        "cmd": "set_rgb",
        "params": {
            "effect": int(LedEffect.NEON),
            "color": [255, 0, 128],
            "brightness": 80,
            "speed": 60
        }
    })
    assert res["status"] == "ok"
    assert daemon.profile["rgb_effect"] == int(LedEffect.NEON)
    assert daemon.profile["rgb_color"] == [255, 0, 128]
    assert mock_dev.rgb_effect == int(LedEffect.NEON)
    assert mock_dev.rgb_color == (255, 0, 128)

    # Test set_polling_rate
    res = daemon.handle_request({"cmd": "set_polling_rate", "params": {"rate": 2000}})
    assert res["status"] == "ok"
    assert daemon.profile["polling_rate"] == 2000


def test_tg_keyboard_rgb_dispatch():
    # Verify descriptor detection for EK75 PRO /dev/hidraw3 Feature Report interface
    ek75_feature_desc = bytes.fromhex("0600ff0902a1011500250175089540b101c0")
    ek75_boot_desc = bytes.fromhex("05010906a101050719e029e715002501750195088102c0")
    assert HidManager.is_tg_feature_descriptor(ek75_feature_desc) is True
    assert HidManager.is_tg_feature_descriptor(ek75_boot_desc) is False

    # Verify TgUsbHidDevice 65B Feature Report handshake & keyboard RGB dispatch
    dev = HidDevice(
        dev_path="/dev/null",
        name="DAREU EK75 PRO",
        vid=0x260D,
        pid=0x0046,
        is_tg_feature_interface=True,
    )
    dev._fd = 999  # Simulated open fd
    sent_reports = []

    def fake_set_feature(data: bytes) -> bool:
        assert len(data) == 65
        sent_reports.append(bytes(data))
        return True

    def fake_get_feature(report_id: int = 0x00, length: int = 65) -> bytes:
        last = sent_reports[-1]
        resp = bytearray(length)
        resp[0] = 0x00
        resp[1] = 0x02  # Ready / ACK
        resp[2] = last[2]
        resp[3] = last[3]
        resp[4] = last[4]
        if last[3] == 0x05 and last[4] == 0x83:
            # GetProfileActive -> profile 1
            resp[5] = 0x01
        elif last[3] == 0x03 and last[4] == 0x80:
            # GetLedIdList -> 2 regions: [1, 2]
            resp[5] = 0x01
            resp[6] = 0x00
            resp[7] = 0x02
            resp[8] = 0x01
            resp[9] = 0x02
        return bytes(resp)

    dev.set_feature_report = fake_set_feature
    dev.get_feature_report = fake_get_feature

    daemon = DareuDaemon(mock_mode=False)
    daemon.devices = [dev]
    res = daemon.handle_request({
        "cmd": "set_rgb",
        "params": {
            "effect": int(LedEffect.WAVE),
            "color": [0, 229, 255],
            "brightness": 75,
            "speed": 50,
            "rainbow": True,
        },
    })
    assert res["status"] == "ok"
    assert res["applied"] is True
    # Expect: GetProfileActive, SetDeviceMode, GetLedIdList,
    # Region 1 (SetLedEffect, SetLedBrigtness), Region 2 (SetLedEffect, SetLedBrigtness)
    assert len(sent_reports) == 7
    assert sent_reports[0][3:5] == bytes([0x05, 0x83])  # GetProfileActive
    assert sent_reports[1][3:5] == bytes([0x00, 0x03])  # SetDeviceMode(0)
    assert sent_reports[2][3:5] == bytes([0x03, 0x80])  # GetLedIdList
    assert sent_reports[3][3:5] == bytes([0x03, 0x02])  # SetLedEffect (region 1)
    assert sent_reports[3][7] == 1 and sent_reports[3][8] == int(LedEffect.WAVE)
    assert (sent_reports[3][9] & 0x80) == 0x80  # rainbow bit set
    assert sent_reports[4][3:5] == bytes([0x03, 0x03])  # SetLedBrigtness (region 1)
    assert sent_reports[4][8] == 75
    assert sent_reports[5][3:5] == bytes([0x03, 0x02])  # SetLedEffect (region 2)
    assert sent_reports[5][7] == 2
    assert sent_reports[6][3:5] == bytes([0x03, 0x03])  # SetLedBrigtness (region 2)

