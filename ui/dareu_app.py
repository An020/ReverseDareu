#!/usr/bin/env python3
"""
DAREU Control Center (Native Linux / Omarchy Desktop GUI)
Modern, dark-themed control interface for DAREU mice and keyboards.
"""

import sys
import os
import json
import tkinter as tk
from tkinter import ttk, colorchooser
from pathlib import Path

# Add daemon directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "daemon"))
from dareud import send_ipc_command
from protocol import LedEffect


# Omarchy Dark Theme Color Palette
BG_MAIN = "#1a1b26"
BG_CARD = "#24283b"
BG_INPUT = "#16161e"
TEXT_PRIMARY = "#c0caf5"
TEXT_MUTED = "#565f89"
ACCENT_CYAN = "#7dcfff"
ACCENT_BLUE = "#7aa2f7"
ACCENT_GREEN = "#9ece6a"
ACCENT_RED = "#f7768e"


EFFECT_NAME_TO_ID = {
    "Static": LedEffect.STATIC,
    "Breathing": LedEffect.BREATHING,
    "Neon Cycle": LedEffect.NEON,
    "Wave": LedEffect.WAVE,
    "Reactive": LedEffect.REACTIVE,
    "Raindrop": LedEffect.RAINDROP,
    "Running Light": LedEffect.RUNNING_LIGHT,
    "Diffusion": LedEffect.DIFFUSION,
    "Starlit": LedEffect.STARLIT,
    "Off": LedEffect.OFF,
}
EFFECT_ID_TO_NAME = {int(v): k for k, v in EFFECT_NAME_TO_ID.items()}


class DareuApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DAREU Control Center - Omarchy")
        self.geometry("780x560")
        self.minsize(720, 500)
        self.configure(bg=BG_MAIN)

        self.status = {
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
        self.devices = []
        self._initializing_ui = True
        self._slider_after_id = None

        self.fetch_daemon_state()
        self.setup_ui()
        self._initializing_ui = False

    def fetch_daemon_state(self):
        resp = send_ipc_command("get_status")
        if resp.get("status") == "ok":
            self.status = resp.get("data", self.status)

        dev_resp = send_ipc_command("get_devices")
        if dev_resp.get("status") == "ok":
            self.devices = dev_resp.get("devices", [])

    def setup_ui(self):
        # Header banner
        header = tk.Frame(self, bg=BG_CARD, height=60, padx=20, pady=10)
        header.pack(fill="x", side="top")

        title_lbl = tk.Label(
            header, text="DAREU GAMING", font=("Cantarell", 16, "bold"),
            fg=ACCENT_CYAN, bg=BG_CARD
        )
        title_lbl.pack(side="left")

        dev_text = self.devices[0]["name"] if self.devices else "DAREU A980 Pro (Connected)"
        dev_lbl = tk.Label(
            header, text=f"Device: {dev_text}", font=("Cantarell", 10),
            fg=TEXT_MUTED, bg=BG_CARD
        )
        dev_lbl.pack(side="left", padx=15)

        # Battery indicator in header
        bat_level = self.status.get("battery_level", 85)
        bat_lbl = tk.Label(
            header, text=f"🔋 {bat_level}%", font=("Cantarell", 11, "bold"),
            fg=ACCENT_GREEN if bat_level > 20 else ACCENT_RED, bg=BG_CARD
        )
        bat_lbl.pack(side="right")

        # Main content area
        content = tk.Frame(self, bg=BG_MAIN, padx=20, pady=20)
        content.pack(fill="both", expand=True)

        # 1. DPI Stage Control Card
        dpi_card = tk.LabelFrame(
            content, text=" DPI Configuration ", font=("Cantarell", 11, "bold"),
            bg=BG_CARD, fg=ACCENT_BLUE, padx=15, pady=15, bd=1, relief="solid"
        )
        dpi_card.pack(fill="x", pady=10)

        self.dpi_buttons = []
        btn_box = tk.Frame(dpi_card, bg=BG_CARD)
        btn_box.pack(fill="x")

        stages = self.status.get("dpi_stages", [400, 800, 1600, 3200, 6400])
        active = self.status.get("active_stage", 1)

        for idx, val in enumerate(stages):
            is_active = (idx == active)
            btn = tk.Button(
                btn_box, text=f"Stage {idx+1}\n{val} DPI",
                font=("Cantarell", 10, "bold" if is_active else "normal"),
                bg=ACCENT_BLUE if is_active else BG_INPUT,
                fg="#ffffff" if is_active else TEXT_PRIMARY,
                activebackground=ACCENT_CYAN,
                padx=15, pady=8, bd=0, relief="flat",
                command=lambda i=idx: self.select_dpi_stage(i)
            )
            btn.pack(side="left", padx=6, expand=True, fill="x")
            self.dpi_buttons.append(btn)

        # 2. Polling Rate Selection Card
        poll_card = tk.LabelFrame(
            content, text=" Polling Rate (Report Rate) ", font=("Cantarell", 11, "bold"),
            bg=BG_CARD, fg=ACCENT_BLUE, padx=15, pady=12, bd=1, relief="solid"
        )
        poll_card.pack(fill="x", pady=10)

        poll_box = tk.Frame(poll_card, bg=BG_CARD)
        poll_box.pack(fill="x")

        self.poll_buttons = []
        rates = [125, 250, 500, 1000, 2000, 4000, 8000]
        curr_rate = self.status.get("polling_rate", 1000)

        for rate in rates:
            is_active = (rate == curr_rate)
            btn = tk.Button(
                poll_box, text=f"{rate} Hz", font=("Cantarell", 9, "bold" if is_active else "normal"),
                bg=ACCENT_CYAN if is_active else BG_INPUT,
                fg="#1a1b26" if is_active else TEXT_PRIMARY,
                padx=10, pady=5, bd=0, relief="flat",
                command=lambda r=rate: self.select_polling_rate(r)
            )
            btn.pack(side="left", padx=4, expand=True, fill="x")
            self.poll_buttons.append(btn)

        # 3. RGB Lighting Card
        rgb_card = tk.LabelFrame(
            content, text=" RGB Chroma Lighting Studio ", font=("Cantarell", 11, "bold"),
            bg=BG_CARD, fg=ACCENT_BLUE, padx=15, pady=15, bd=1, relief="solid"
        )
        rgb_card.pack(fill="both", expand=True, pady=10)

        ctrl_row = tk.Frame(rgb_card, bg=BG_CARD)
        ctrl_row.pack(fill="x", pady=5)

        tk.Label(ctrl_row, text="Effect Mode:", font=("Cantarell", 10), fg=TEXT_PRIMARY, bg=BG_CARD).pack(side="left")
        initial_eff_name = EFFECT_ID_TO_NAME.get(int(self.status.get("rgb_effect", 1)), "Static")
        self.effect_var = tk.StringVar(value=initial_eff_name)
        effects = list(EFFECT_NAME_TO_ID.keys())
        effect_combo = ttk.Combobox(ctrl_row, textvariable=self.effect_var, values=effects, state="readonly", width=15)
        effect_combo.pack(side="left", padx=10)
        effect_combo.bind("<<ComboboxSelected>>", self.on_effect_changed)

        # Color preview & picker button
        color_btn = tk.Button(
            ctrl_row, text="Pick Custom Color", font=("Cantarell", 9, "bold"),
            bg=BG_INPUT, fg=ACCENT_CYAN, padx=10, pady=3, bd=0,
            command=self.pick_color
        )
        color_btn.pack(side="left", padx=12)

        self.color_preview = tk.Frame(ctrl_row, width=28, height=28, bd=1, relief="solid")
        r, g, b = self.status.get("rgb_color", [0, 210, 255])
        self.color_preview.configure(bg=f"#{r:02x}{g:02x}{b:02x}")
        self.color_preview.pack(side="left")

        self.rainbow_var = tk.BooleanVar(value=bool(self.status.get("rgb_rainbow", False)))
        rainbow_chk = tk.Checkbutton(
            ctrl_row, text="Rainbow / Multi-Color", variable=self.rainbow_var,
            font=("Cantarell", 9), bg=BG_CARD, fg=TEXT_PRIMARY,
            selectcolor=BG_INPUT, activebackground=BG_CARD, activeforeground=ACCENT_CYAN,
            highlightthickness=0, command=self.on_rainbow_changed
        )
        rainbow_chk.pack(side="left", padx=12)

        # Sliders for Brightness & Speed
        slider_row = tk.Frame(rgb_card, bg=BG_CARD)
        slider_row.pack(fill="x", pady=10)

        tk.Label(slider_row, text="Brightness:", font=("Cantarell", 9), fg=TEXT_PRIMARY, bg=BG_CARD).pack(side="left")
        self.bright_slider = tk.Scale(
            slider_row, from_=0, to=100, orient="horizontal", bg=BG_CARD, fg=TEXT_PRIMARY,
            troughcolor=BG_INPUT, highlightthickness=0, command=self.on_slider_changed
        )
        self.bright_slider.set(self.status.get("rgb_brightness", 100))
        self.bright_slider.pack(side="left", padx=10, fill="x", expand=True)

        tk.Label(slider_row, text="Speed:", font=("Cantarell", 9), fg=TEXT_PRIMARY, bg=BG_CARD).pack(side="left")
        self.speed_slider = tk.Scale(
            slider_row, from_=0, to=100, orient="horizontal", bg=BG_CARD, fg=TEXT_PRIMARY,
            troughcolor=BG_INPUT, highlightthickness=0, command=self.on_slider_changed
        )
        self.speed_slider.set(self.status.get("rgb_speed", 50))
        self.speed_slider.pack(side="left", padx=10, fill="x", expand=True)

    def select_dpi_stage(self, stage_idx: int):
        self.status["active_stage"] = stage_idx
        for idx, btn in enumerate(self.dpi_buttons):
            if idx == stage_idx:
                btn.configure(bg=ACCENT_BLUE, fg="#ffffff", font=("Cantarell", 10, "bold"))
            else:
                btn.configure(bg=BG_INPUT, fg=TEXT_PRIMARY, font=("Cantarell", 10, "normal"))
        send_ipc_command("set_dpi", {"active": stage_idx})

    def select_polling_rate(self, rate_hz: int):
        self.status["polling_rate"] = rate_hz
        rates = [125, 250, 500, 1000, 2000, 4000, 8000]
        for idx, btn in enumerate(self.poll_buttons):
            if rates[idx] == rate_hz:
                btn.configure(bg=ACCENT_CYAN, fg="#1a1b26", font=("Cantarell", 9, "bold"))
            else:
                btn.configure(bg=BG_INPUT, fg=TEXT_PRIMARY, font=("Cantarell", 9, "normal"))
        send_ipc_command("set_polling_rate", {"rate": rate_hz})

    def pick_color(self):
        color = colorchooser.askcolor(title="DAREU RGB Color")
        if color and color[0]:
            r, g, b = [int(c) for c in color[0]]
            self.status["rgb_color"] = [r, g, b]
            self.status["rgb_rainbow"] = False
            self.rainbow_var.set(False)
            self.color_preview.configure(bg=f"#{r:02x}{g:02x}{b:02x}")
            self.apply_lighting()

    def on_rainbow_changed(self):
        self.status["rgb_rainbow"] = bool(self.rainbow_var.get())
        self.apply_lighting()

    def on_effect_changed(self, event=None):
        eff_name = self.effect_var.get()
        self.status["rgb_effect"] = int(EFFECT_NAME_TO_ID.get(eff_name, LedEffect.STATIC))
        self.apply_lighting()

    def on_slider_changed(self, val=None):
        if self._initializing_ui or not hasattr(self, "bright_slider") or not hasattr(self, "speed_slider"):
            return
        self.status["rgb_brightness"] = self.bright_slider.get()
        self.status["rgb_speed"] = self.speed_slider.get()
        if self._slider_after_id is not None:
            self.after_cancel(self._slider_after_id)
        self._slider_after_id = self.after(120, self._flush_slider_lighting)

    def _flush_slider_lighting(self):
        self._slider_after_id = None
        self.apply_lighting()

    def apply_lighting(self):
        send_ipc_command("set_rgb", {
            "effect": self.status["rgb_effect"],
            "color": self.status["rgb_color"],
            "brightness": self.status["rgb_brightness"],
            "speed": self.status["rgb_speed"],
            "rainbow": self.status.get("rgb_rainbow", False)
        })


def main():
    app = DareuApp()
    app.mainloop()


if __name__ == "__main__":
    main()
