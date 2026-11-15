### WORK STILL IN PROGRESS
*Only the part where changing keyboard light is confirmed to be working on EK75 Pro, no confirmation whether it works on every DareU products*
# ReverseDareu (`dareu-control`)

Native Linux peripheral daemon, desktop control center, and Arch/Omarchy packaging for DAREU gaming mice and keyboards, built by reverse-engineering the Windows `DAREU_All_in_one_V1.5.6.16.exe` driver suite.

## Features

- **Native USB HID Control (`dareud`)**: Communicates directly with `/dev/hidraw*` nodes without requiring Wine for everyday configuration.
- **Dual Protocol Support**:
  - **64-byte Output/Input Reports (`DareuProtocol`)**: DPI stage configuration (up to 6 stages, 50–32000 DPI), active stage switching, polling rate (`125`–`8000` Hz), and RGB lighting effects.
  - **65-byte Vendor Feature Reports (`TgKeyboardProtocol`)**: `HIDIOCSFEATURE` / `HIDIOCGFEATURE` handshake for `TgUsbHidDevice` keyboards (such as EK75 PRO / TK51GF) with automatic multi-region LED discovery and hardware mode switching.
- **Omarchy Desktop GUI (`dareu-control`)**: Dark-themed Tkinter interface for DPI stages, polling rates, RGB effect modes, custom color picking, rainbow toggle, brightness, and speed.
- **Hotplug & Persistence**: Scans sysfs every 3 seconds, reapplies keyboard RGB profiles on reconnect, and persists settings in XDG config storage.
- **Arch Linux Integration**: Ships a `PKGBUILD` installing `udev` non-root permissions, a `systemd` user service, XDG autostart, desktop entry, and icon.
- **Wine Fallback Runner**: Includes a Wine launcher script for running the extracted Windows utility when vendor firmware flashing (DFU) is needed.

## Supported Hardware

Devices are detected automatically via `/sys/class/hidraw/hidraw*/device/uevent` across four USB Vendor IDs:

| Vendor ID | Chipset / Brand | Notes |
|---|---|---|
| `0x260D` | DAREU Gaming | Primary OEM VID (e.g. A950, A980, EK75 PRO, A87, A98) |
| `0x258A` | SinoWealth / DAREU | Budget DAREU mice and keyboards |
| `0x1A2C` | Semico | 2.4 GHz wireless receivers / dongles |
| `0x0C45` | Sonix Technology | Optical controllers and sensors |

> [!NOTE]
> The GUI and daemon support virtual `--mock` mode when no DAREU hardware is plugged in. Live battery polling is implemented at the protocol level (`DareuProtocol.build_get_battery` / `parse_battery_response`), while the daemon currently serves the persisted/default battery state.

## Architecture

```
ui/dareu_app.py (Tkinter GUI) ──┐
ui/tray.py (Status summary)    ──┼──▶ Unix Socket ($XDG_RUNTIME_DIR/dareu.sock)
CLI (dareud --status)          ──┘              │
                                                ▼
                                     daemon/dareud.py (DareuDaemon)
                                       ├── daemon/protocol.py (64B & 65B packets)
                                       └── daemon/hid_interface.py (/dev/hidraw* & ioctl)
```

### Repository Layout

```text
├── PKGBUILD                         # Arch Linux package build script (dareu-control)
├── dareu.install                    # pacman hooks (udev reload & systemd --user restart)
├── autostart/
│   └── dareu-autostart.desktop      # XDG autostart entry for dareud
├── daemon/
│   ├── dareud.py                    # Background daemon, hotplug scanner, JSON IPC & profiles
│   ├── hid_interface.py             # Sysfs hidraw scanner, raw r/w, HIDIOCS/GFEATURE ioctls
│   └── protocol.py                  # DareuProtocol (64B) & TgKeyboardProtocol (65B)
├── desktop/
│   ├── dareu.desktop                # Application launcher entry
│   ├── dareu.ico
│   └── dareu.png                    # 64x64 app icon
├── docs/
│   ├── DAREU_PROTOCOL_SPEC.md       # Byte-level packet and ioctl specification
│   ├── DISASSEMBLY_FINDINGS.md      # Reverse-engineering notes from Windows binaries
│   └── EXTRACTED_MANIFEST.json      # File inventory & SHA-256 hashes of original installer
├── systemd/
│   └── dareu.service                # systemd user unit for dareud
├── tests/
│   ├── mock_device.py               # Simulated HID register state
│   ├── run_tests.py                 # Test suite entrypoint
│   ├── test_daemon.py               # Daemon lifecycle & TgKeyboard handshake tests
│   └── test_protocol.py             # Packet serialization/deserialization tests
├── udev/
│   └── 99-dareu.rules               # Non-root /dev/hidraw* and USB access rules
├── ui/
│   ├── dareu_app.py                 # Native Tkinter control center
│   └── tray.py                      # One-line status formatter for bars/scripts
└── wine/
    └── dareu-wine-runner.sh         # Fallback Wine wrapper for firmware updates
```

## Prerequisites

- **Arch Linux / Omarchy** (or any Linux distribution with Python 3, Tkinter, and `udev`)
- `python` and `tk` (required by `PKGBUILD`)
- **Optional**: `wine`, `wine-mono`, and `innoextract` (only if extracting and running the original Windows binary for firmware updates)

## Installation

### Arch Linux / Omarchy (`PKGBUILD`)

Build and install the native system package from the repository root:

```bash
makepkg -si
```

The package installs:
- `/usr/bin/dareud`, `/usr/bin/dareu-control`, `/usr/bin/dareu-wine-runner`
- `/usr/lib/dareu/{dareud.py,dareu_app.py,hid_interface.py,protocol.py}`
- `/usr/lib/udev/rules.d/70-dareu.rules` and `99-dareu.rules`
- `/usr/lib/systemd/user/dareu.service` (enabled under `default.target.wants`)
- `/etc/xdg/autostart/dareu-autostart.desktop`
- `/usr/share/applications/dareu.desktop` and `/usr/share/icons/hicolor/64x64/apps/dareu.png`
- `/usr/share/doc/dareu/{DAREU_PROTOCOL_SPEC.md,DISASSEMBLY_FINDINGS.md}`

During installation, [dareu.install](dareu.install) reloads `udev` rules, grants read/write access on connected DAREU `/dev/hidraw*` nodes, and restarts `dareu.service` for the active user. If your device was already plugged in before rules loaded, unplug and replug it or run:

```bash
sudo udevadm control --reload-rules && sudo udevadm trigger --subsystem-match=hidraw
```

### Run Directly From Source (No System Install)

For development or testing without `makepkg`:

```bash
# 1. Start the daemon (add --mock to test without physical hardware)
PYTHONPATH=daemon python3 daemon/dareud.py --mock

# 2. Launch the desktop UI in another terminal
python3 ui/dareu_app.py
```

## Usage

### Daemon (`dareud`)

```bash
dareud                # Run daemon against real /dev/hidraw* devices
dareud --mock         # Run with a simulated DAREU A980 Pro
dareud --status       # Print active profile JSON from the running daemon
```

Manage the installed background service with `systemctl`:

```bash
systemctl --user status dareu.service
systemctl --user restart dareu.service
journalctl --user -u dareu.service -f
```

### Desktop GUI & Status Output

- Launch **DAREU Control Center** from your application launcher or run `dareu-control`.
- Use `python3 ui/tray.py` from the repository in status bars (such as Waybar) to print a summary line:

```text
DAREU: 800 DPI | 🔋 88%
```

### Wine Fallback (Firmware Updates)

When vendor DFU firmware updates are required, extract the Windows installer (`DAREU_All_in_one_V1.5.6.16.exe`) into `extracted/` inside the repository and run the wrapper script directly from the repo:

```bash
innoextract -d extracted DAREU_All_in_one_V1.5.6.16.exe
./wine/dareu-wine-runner.sh
```

This creates a 32-bit Wine prefix at `~/.local/share/dareu-wine` and launches `extracted/app/DareuDriver.exe`.

## Configuration & IPC

| Path / Variable | Purpose | Default |
|---|---|---|
| `XDG_CONFIG_HOME` | Base directory for saved profiles | `~/.config/dareu/profiles.json` |
| `XDG_RUNTIME_DIR` | Directory for daemon Unix socket | `$XDG_RUNTIME_DIR/dareu.sock` (fallback `/run/user/<uid>/dareu.sock` or `/tmp/dareu.sock`) |

### Daemon IPC Commands

The daemon accepts JSON objects over its Unix domain socket:

| Command | Parameters | Description |
|---|---|---|
| `ping` | — | Health check and mock mode status |
| `get_devices` | — | List detected HID devices (or mock device) |
| `get_status` | — | Return current profile dictionary |
| `set_dpi` | `stages` (`list[int]`), `active` (`int`) | Save and dispatch DPI stages and active index |
| `set_polling_rate` | `rate` (`125`–`8000`) | Set mouse report rate in Hz |
| `set_rgb` | `effect`, `color` (`[r,g,b]`), `brightness`, `speed`, `rainbow` | Apply lighting across standard or `TgUsbHidDevice` endpoints |

## Testing

Run the unit and mock integration suite with Python's standard library (no external packages required):

```bash
python3 tests/run_tests.py
```

The test suite verifies 64-byte and 65-byte packet serialization, HID report descriptor matching, profile lifecycle persistence, and `TgKeyboardProtocol` RGB dispatch against [mock_device.py](tests/mock_device.py).

## Documentation

- [DAREU USB HID Protocol Specification](docs/DAREU_PROTOCOL_SPEC.md)
- [Reverse Engineering & Disassembly Findings](docs/DISASSEMBLY_FINDINGS.md)

## License

Licensed under **GPL-3.0** (`GPL3` in [PKGBUILD](PKGBUILD)).
