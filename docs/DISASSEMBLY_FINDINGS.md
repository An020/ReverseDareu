# Reverse Engineering Findings: DAREU All-in-One Peripheral Suite

## 1. Overview & Packaging Architecture
- **Source Artifact**: `DAREU_All_in_one_V1.5.6.16.exe` (SHA-256: `aa0d2091ccbc89a193c11032926c18654aeb7d06d456c5a8ba10ce148bbaa6ae`).
- **Packaging Format**: Inno Setup 6.1.0 (Unicode).
- **Extracted Contents**: 120 files across core runtime, device plugins (`app/Products/`), firmware updater, and fonts.
- **Runtime Stack**:
  - `DareuDriver.exe`: .NET Framework 4.8 x86 WPF GUI client.
  - `DeviceBase.dll`: Core device abstraction, protocol formatting, feature report generation.
  - `HidControl.dll`: Native Win32 HID subsystem wrapper (`HidD_*` API calls).
  - `LedController.dll`: Dynamic RGB lighting animation engine and audio visualizer sync.
  - `Products/*.dll`: Individual device definitions for TM series (mice) and TK/EK series (keyboards).

## 2. Hardware Vendor IDs & Target Peripherals
DAREU peripherals and 2.4G wireless receivers register under several USB Vendor IDs:
1. `VID 0x260D`: Primary DAREU OEM Vendor ID (used by modern mice like A950, A980, and keyboards like EK75, A87, A98).
2. `VID 0x258A`: SinoWealth USB microcontroller chips used in budget DAREU keyboards/mice.
3. `VID 0x1A2C`: China Resource Semico USB wireless receivers / dongles.
4. `VID 0x0C45`: Sonix Technology USB sensors and optical controllers.

Sample Device Product IDs (PIDs):
- `PID 0x0037` (55)
- `PID 0x0042` (66)
- `PID 0x1131` (4401)
- `PID 0xFFFA` (65530)
- `PID 0x0055` (85)

## 3. Communication Channel & Transport
- **Protocol**: USB HID Report Transfer.
- **Report Types**:
  - `Output Report`: Length 62–64 bytes, Primary Report ID `0x07` (or `0x08` / `0x04`).
  - `Input Report`: Length 62–64 bytes, matching Report ID `0x07`.
  - `Feature Report`: Used for extended state queries, sleep timers, and profile EEPROM flash reads/writes.
- **Device Node Mapping**: Linux `/dev/hidraw*`.

## 4. Hardware Command Dispatch Architecture
Decompiled from `DeviceBase.dll` dispatch switch statements:
Each transaction follows: `[Report ID] [Action] [Class ID] [Command ID] [Sub-index] [Payload...]`

### Command Classes
- **Class `0x01` - Keyboard / Keys**: Key IDs, debounce time, key assignment, analog actuation points (Rapid Trigger / HE), Fn lock, Win/Mac mode.
- **Class `0x02` - Mouse / Buttons**: Button IDs, debounce time (0–30ms), button assignments (Left, Right, Middle, Forward, Back, DPI Cycle, Sniper).
- **Class `0x03` - Lighting / RGB**: LED IDs, mode effect (Static, Breathing, Neon, Reactive, Wave, etc.), brightness (0–100%), speed (0–100%), custom frames.
- **Class `0x04` - Sensor / DPI**: DPI configuration stages (1 to 6 stages), DPI value (50–26000 DPI), active stage index, Lift-off Distance (LOD: 1mm/2mm).
- **Class `0x05` - Profile**: On-board profile selection, creation, deletion, reset.
- **Class `0x06` - Macro**: Macro sequence storage, delay injection, memory allocation.
- **Class `0x07` - Power Management**: Battery level percentage query, sleep timeout, dim timeout, low-battery warning threshold.
- **Class `0x08` - Audio**: Headset volume, mute, EQ, mic gain.
- **Class `0x09` - DFU**: Firmware update handshake, block flash, CRC check.
- **Class `0x0A` - Test & Device Info**: USB VID/PID query, manufacturer/product string query, reset.
