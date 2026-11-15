#!/usr/bin/env python3
"""
DAREU Peripheral Management Daemon (dareud)
Manages peripheral hardware communication, profile persistence, and provides an IPC socket.
"""

import os
import sys
import time
import json
import socket
import select
import signal
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional

from protocol import DareuProtocol, TgKeyboardProtocol, LedEffect
from hid_interface import HidManager, HidDevice


def get_config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "dareu"
    return Path.home() / ".config" / "dareu"


def get_socket_file() -> Path:
    xdg_runtime = os.environ.get("XDG_RUNTIME_DIR")
    if xdg_runtime:
        return Path(xdg_runtime) / "dareu.sock"
    user_run = Path(f"/run/user/{os.getuid()}")
    if user_run.exists():
        return user_run / "dareu.sock"
    return Path("/tmp") / "dareu.sock"


CONFIG_DIR = get_config_dir()
CONFIG_FILE = CONFIG_DIR / "profiles.json"
SOCKET_FILE = get_socket_file()


DEFAULT_PROFILE = {
    "dpi_stages": [400, 800, 1600, 3200, 6400],
    "active_stage": 1,
    "polling_rate": 1000,
    "rgb_effect": int(LedEffect.STATIC),
    "rgb_color": [0, 210, 255],
    "rgb_brightness": 100,
    "rgb_speed": 50,
    "rgb_rainbow": False,
    "battery_level": 88,
    "charging": False
}


class DareuDaemon:
    def __init__(self, mock_mode: bool = False):
        self.mock_mode = mock_mode
        self.running = False
        self.profile = self.load_profile()
        self.devices: List[HidDevice] = []
        self._server_sock: Optional[socket.socket] = None
        self._lock = threading.Lock()

    def load_profile(self) -> Dict[str, Any]:
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return {**DEFAULT_PROFILE, **data}
        except Exception:
            pass
        return DEFAULT_PROFILE.copy()

    def save_profile(self):
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.profile, f, indent=2)
        except Exception:
            pass

    def apply_keyboard_rgb(self, dev: HidDevice) -> bool:
        """Applies current RGB profile to a TgUsbHidDevice keyboard Feature Report interface."""
        if not dev.is_open and not dev.open():
            return False

        effect = int(self.profile.get("rgb_effect", int(LedEffect.STATIC)))
        color = self.profile.get("rgb_color", [0, 210, 255])
        brightness = int(self.profile.get("rgb_brightness", 100))
        speed = int(self.profile.get("rgb_speed", 50))
        rainbow = bool(self.profile.get("rgb_rainbow", False))

        # 1. Query active on-board profile (defaults to 1)
        resp_prof = dev.tg_command(TgKeyboardProtocol.build_get_active_profile())
        profile_id = TgKeyboardProtocol.parse_active_profile(resp_prof)

        # 2. Ensure keyboard is in hardware lighting mode (0)
        dev.tg_command(TgKeyboardProtocol.build_set_device_mode(0))

        # 3. Query LED region IDs (e.g. [1, 2] on EK75 PRO)
        resp_reg = dev.tg_command(TgKeyboardProtocol.build_get_led_regions(profile_id=profile_id))
        regions = TgKeyboardProtocol.parse_led_regions(resp_reg)

        # 4. Set LED effect and brightness for each region
        ok = False
        for region_id in regions:
            pkt_eff = TgKeyboardProtocol.build_set_led_effect(
                effect=effect,
                r=color[0],
                g=color[1],
                b=color[2],
                speed=speed,
                rainbow=rainbow,
                profile_id=profile_id,
                region_id=region_id
            )
            pkt_brt = TgKeyboardProtocol.build_set_led_brightness(
                brightness=brightness,
                profile_id=profile_id,
                region_id=region_id
            )
            if dev.tg_command(pkt_eff) is not None:
                ok = True
            if dev.tg_command(pkt_brt) is not None:
                ok = True
        return ok

    def scan_hardware(self):
        with self._lock:
            existing_by_path = {d.dev_path: d for d in self.devices}
            scanned = HidManager.scan_devices()
            scanned_paths = {d.dev_path for d in scanned}

            # Close removed devices
            for path, old_dev in existing_by_path.items():
                if path not in scanned_paths:
                    old_dev.close()

            updated: List[HidDevice] = []
            for dev in scanned:
                if dev.dev_path in existing_by_path:
                    kept = existing_by_path[dev.dev_path]
                    kept.is_tg_feature_interface = dev.is_tg_feature_interface
                    if not kept.is_open:
                        if kept.open() and kept.is_tg_feature_interface:
                            self.apply_keyboard_rgb(kept)
                    updated.append(kept)
                else:
                    if dev.open() and dev.is_tg_feature_interface:
                        self.apply_keyboard_rgb(dev)
                    updated.append(dev)
            self.devices = updated

    def handle_request(self, req: Dict[str, Any]) -> Dict[str, Any]:
        cmd = req.get("cmd")
        params = req.get("params", {})

        if cmd == "ping":
            return {"status": "ok", "mock_mode": self.mock_mode}

        elif cmd == "get_devices":
            dev_list = []
            if self.mock_mode or not self.devices:
                dev_list.append({
                    "name": "DAREU A980 Pro (Mock/Simulated)",
                    "vid": "0x260d",
                    "pid": "0x0037",
                    "path": "/dev/hidraw_mock",
                    "mock": True
                })
            else:
                # Prefer showing TgUsbHidDevice feature interfaces first
                sorted_devs = sorted(
                    self.devices,
                    key=lambda x: (not getattr(x, "is_tg_feature_interface", False), x.dev_path)
                )
                for d in sorted_devs:
                    dev_list.append({
                        "name": d.name,
                        "vid": f"0x{d.vid:04x}",
                        "pid": f"0x{d.pid:04x}",
                        "path": d.dev_path,
                        "is_tg_feature": getattr(d, "is_tg_feature_interface", False),
                        "open": d.is_open,
                        "mock": False
                    })
            return {"status": "ok", "devices": dev_list}

        elif cmd == "get_status":
            return {"status": "ok", "data": self.profile}

        elif cmd == "set_dpi":
            stages = params.get("stages", self.profile["dpi_stages"])
            active = params.get("active", self.profile["active_stage"])
            self.profile["dpi_stages"] = stages
            self.profile["active_stage"] = active
            self.save_profile()

            pkt_stages = DareuProtocol.build_set_dpi_stages(stages, active)
            pkt_active = DareuProtocol.build_set_active_dpi(active)
            for d in self.devices:
                d.send_report(pkt_stages)
                d.send_report(pkt_active)
            return {"status": "ok", "data": self.profile}

        elif cmd == "set_rgb":
            effect = int(params.get("effect", self.profile["rgb_effect"]))
            color = params.get("color", self.profile["rgb_color"])
            brightness = int(params.get("brightness", self.profile["rgb_brightness"]))
            speed = int(params.get("speed", self.profile["rgb_speed"]))
            rainbow = bool(params.get("rainbow", self.profile.get("rgb_rainbow", False)))

            self.profile["rgb_effect"] = effect
            self.profile["rgb_color"] = color
            self.profile["rgb_brightness"] = brightness
            self.profile["rgb_speed"] = speed
            self.profile["rgb_rainbow"] = rainbow
            self.save_profile()

            tg_vid_pids = {(d.vid, d.pid) for d in self.devices if getattr(d, "is_tg_feature_interface", False)}
            applied = False

            for d in self.devices:
                if getattr(d, "is_tg_feature_interface", False):
                    if self.apply_keyboard_rgb(d):
                        applied = True
                elif (d.vid, d.pid) not in tg_vid_pids:
                    eff_enum = LedEffect(effect) if effect in LedEffect._value2member_map_ else LedEffect.STATIC
                    pkt = DareuProtocol.build_set_lighting(
                        eff_enum, color[0], color[1], color[2], brightness, speed
                    )
                    if d.send_report(pkt):
                        applied = True
            return {"status": "ok", "data": self.profile, "applied": applied}

        elif cmd == "set_polling_rate":
            rate = params.get("rate", self.profile["polling_rate"])
            self.profile["polling_rate"] = rate
            self.save_profile()

            pkt = DareuProtocol.build_set_polling_rate(rate)
            for d in self.devices:
                d.send_report(pkt)
            return {"status": "ok", "data": self.profile}

        return {"status": "error", "message": f"Unknown command: {cmd}"}

    def start_ipc_server(self):
        if SOCKET_FILE.exists():
            SOCKET_FILE.unlink()
        
        self._server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server_sock.bind(str(SOCKET_FILE))
        self._server_sock.listen(5)
        self._server_sock.setblocking(False)

    def run(self):
        self.running = True
        self.start_ipc_server()
        last_scan = 0

        while self.running:
            now = time.time()
            if now - last_scan > 3.0:
                if not self.mock_mode:
                    self.scan_hardware()
                last_scan = now

            r, _, _ = select.select([self._server_sock], [], [], 0.5)
            if r:
                try:
                    conn, _ = self._server_sock.accept()
                    data = conn.recv(4096)
                    if data:
                        req = json.loads(data.decode("utf-8"))
                        resp = self.handle_request(req)
                        conn.sendall(json.dumps(resp).encode("utf-8"))
                    conn.close()
                except Exception:
                    pass

    def stop(self):
        self.running = False
        if self._server_sock:
            self._server_sock.close()
            self._server_sock = None
        if SOCKET_FILE.exists():
            try:
                SOCKET_FILE.unlink()
            except OSError:
                pass
        for d in self.devices:
            d.close()


_FALLBACK_DAEMON: Optional[DareuDaemon] = None


def send_ipc_command(cmd: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Helper client to send command to running dareud daemon, with direct hardware fallback."""
    global _FALLBACK_DAEMON
    if SOCKET_FILE.exists():
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.connect(str(SOCKET_FILE))
            msg = json.dumps({"cmd": cmd, "params": params or {}}).encode("utf-8")
            sock.sendall(msg)
            resp_data = sock.recv(4096)
            return json.loads(resp_data.decode("utf-8"))
        except OSError:
            pass
        finally:
            sock.close()

    if _FALLBACK_DAEMON is None:
        _FALLBACK_DAEMON = DareuDaemon(mock_mode=False)
    _FALLBACK_DAEMON.scan_hardware()
    return _FALLBACK_DAEMON.handle_request({"cmd": cmd, "params": params or {}})


def main():
    import argparse
    parser = argparse.ArgumentParser(description="DAREU Peripheral Management Daemon")
    parser.add_argument("--mock", action="store_true", help="Run with simulated virtual hardware")
    parser.add_argument("--status", action="store_true", help="Query status from running daemon")
    args = parser.parse_args()

    if args.status:
        res = send_ipc_command("get_status")
        print(json.dumps(res, indent=2))
        return

    daemon = DareuDaemon(mock_mode=args.mock)

    def sig_handler(sig, frame):
        daemon.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    print(f"Starting dareud (mock={args.mock}) on socket {SOCKET_FILE}...")
    daemon.run()


if __name__ == "__main__":
    main()
