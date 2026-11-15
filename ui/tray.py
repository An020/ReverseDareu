#!/usr/bin/env python3
"""
DAREU System Tray Applet
Shows battery level, active DPI stage, and provides quick actions in the status area.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "daemon"))
from dareud import send_ipc_command


def print_status_summary():
    res = send_ipc_command("get_status")
    if res.get("status") == "ok":
        data = res.get("data", {})
        dpi_stages = data.get("dpi_stages", [800])
        active_idx = data.get("active_stage", 0)
        curr_dpi = dpi_stages[active_idx] if active_idx < len(dpi_stages) else 800
        battery = data.get("battery_level", 0)
        charging = "⚡" if data.get("charging") else ""
        print(f"DAREU: {curr_dpi} DPI | 🔋 {battery}% {charging}")
    else:
        print("DAREU: Daemon disconnected")


if __name__ == "__main__":
    print_status_summary()
