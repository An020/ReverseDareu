# DAREU USB HID Protocol Specification

## 1. Frame Structure

All control packets sent to or received from DAREU peripherals are framed as fixed-length 64-byte USB HID Reports (transferred via Output/Input Reports or Feature Reports).

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|   Report ID   |    Action     |   Class ID    |  Command ID   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|   Sequence    |               Payload Data ...                |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| ... Payload continued (padded with zeros up to 64 bytes)      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### Field Definitions
- **Report ID** (Byte 0):
  - Primary Control: `0x07` (standard for A950, A980, EK75, and 2.4G dongles)
  - Secondary/Extended: `0x08` or `0x04`
- **Action** (Byte 1):
  - `0x01`: GET (Query current configuration/status from device)
  - `0x02`: SET (Apply configuration changes to device)
  - `0x03`: NOTIFY / RESPONSE (Echo or asynchronous state update)
- **Class ID** (Byte 2): Functional domain category (0x01 to 0x0A).
- **Command ID** (Byte 3): Specific sub-command within category.
- **Sequence / Sub-index** (Byte 4): Packet transaction index or sub-item index (e.g. stage index).
- **Payload** (Bytes 5..63): Command-specific payload.

---

## 2. Command Class Details

### Class 0x03: Lighting (LED / RGB)
- **Command `0x02`: LED Effect**
  - Action: `0x02` (Set)
  - Byte 4: Lighting Zone / Sub-LED ID (`0x00` = All / Primary)
  - Byte 5: Effect Mode:
    - `0x00`: LED_OFF
    - `0x01`: LED_Static (solid color)
    - `0x02`: LED_Breathing
    - `0x03`: LED_Neon (color spectrum cycle)
    - `0x04`: LED_Reactive
    - `0x05`: LED_Wave
    - `0x06`: LED_Ripple
    - `0x07`: LED_Diffusion
  - Byte 6: Red channel (`0x00` - `0xFF`)
  - Byte 7: Green channel (`0x00` - `0xFF`)
  - Byte 8: Blue channel (`0x00` - `0xFF`)
  - Byte 9: Brightness level (`0` - `100` / `0x00` - `0x64`)
  - Byte 10: Animation speed (`0` - `100` / `0x00` - `0x64`)

### Class 0x04: Sensor (DPI & Tracking)
- **Command `0x03`: DPI Configure**
  - Action: `0x02` (Set)
  - Byte 4: Stage count (typically `1` to `6`)
  - Bytes 5-6: Stage 1 DPI value (16-bit little endian, e.g. `0x0320` = 800 DPI)
  - Bytes 7-8: Stage 2 DPI value (e.g. `0x0640` = 1600 DPI)
  - Bytes 9-10: Stage 3 DPI value (e.g. `0x0C80` = 3200 DPI)
  - Bytes 11-12: Stage 4 DPI value (e.g. `0x1900` = 6400 DPI)
- **Command `0x04`: DPI Active**
  - Action: `0x01` (Get) or `0x02` (Set)
  - Byte 4: Active stage index (`0` to `5`)
- **Command `0x06`: Sensor Lifted Setting (LOD)**
  - Action: `0x02` (Set)
  - Byte 4: LOD height mode (`0x01` = Low / 1.0mm, `0x02` = High / 2.0mm)

### Class 0x07: Power Management & Battery Telemetry
- **Command `0x00`: Battery Status**
  - Query Packet:
    - `[0x07, 0x01, 0x07, 0x00, 0x00, ...]`
  - Response Packet:
    - Byte 0: `0x07`
    - Byte 1: `0x03` (Response)
    - Byte 2: `0x07` (Class)
    - Byte 3: `0x00` (Command)
    - Byte 4: Battery level percentage (`0` - `100`%)
    - Byte 5: Charging flag (`0x00` = Discharging, `0x01` = Charging, `0x02` = Full)
    - Byte 6: Wireless link quality / signal strength (RSSI)
- **Command `0x02`: Sleep Timeout**
  - Byte 4: Minutes before entering sleep mode (e.g. 5, 10, 15 minutes).

---

## 3. TgUsbHidDevice 65-Byte Feature Report Protocol (Keyboards: EK75 PRO / TK51GF)

DAREU keyboards managed by `DeviceBase.dll` (`UsbHidDevice.TgUsbHidDevice`) and product plugins (`Products/TK51GF.dll`) communicate over the vendor-defined HID Feature Report interface (`Usage Page 0xFF00`, `Usage 0x02`, `Feature Report 64B`, descriptor prefix `06 00 ff 09 02 a1 01 15 00 25 01 75 08 95 40 b1 01 c0`).

On Linux `hidraw`, commands are sent via `ioctl(fd, HIDIOCSFEATURE(65), buf)` (`0xC0414806`) and responses are polled via `ioctl(fd, HIDIOCGFEATURE(65), buf)` (`0xC0414807`) until `(resp[1] & 0x0F) == 0x02` and `resp[3:5] == req[3:5]`.

### 3.1 Frame Layout (65 Bytes)
- **Byte 0**: `0x00` (Unnumbered HID Report ID)
- **Byte 1**: Status / Target (`0x00` on Host->Device request; `(resp[1] & 0x0F) == 0x02` on Device->Host ready response)
- **Byte 2**: Packet header + payload length (`0x03` to `0x0D`)
- **Byte 3**: Command Category (`0x01` = Device, `0x02` = Profile, `0x03` = LED / Lighting)
- **Byte 4**: Command ID
- **Bytes 5..64**: Command-specific payload padded with `0x00`

### 3.2 Keyboard Lighting Commands
| Operation | Bytes `0..14` (Hex) | Description |
|-----------|---------------------|-------------|
| `GetProfileActive` | `00 00 00 05 83 00 00 ...` | Returns active `profile_id` in `resp[5]` (default `1`) |
| `SetDeviceMode(0)` | `00 00 01 00 03 00 00 00 ...` | Sets device to hardware lighting mode (`0x00`) |
| `GetLedIdList(pid)` | `00 00 01 03 80 <pid> 00 ...` | Returns `count = resp[7]`, region IDs at `resp[8 .. 8+count]` (`[1, 2]` on EK75 PRO: `1` = main keys, `2` = side light bar) |
| `GetLedEffect(pid, rid)` | `00 00 01 03 82 <pid> 00 <rid> ...` | Queries active lighting effect for `region_id` |
| `SetLedEffect` | `00 00 08 03 02 <pid> 00 <rid> <eff> <flag> <spd> 01 <R> <G> <B>` | Sets effect (`0`=Off, `1`=Static, `2`=Breathing, `3`=Neon, `4`=Reactive, `5`=Wave, `6`=Raindrop, `9`=Running, `10`=Diffusion, `11`=Starlit), `flag` (`0x80`=rainbow), speed (`0..4`), and RGB (`0..255`) |
| `GetLedBrigtness(pid, rid)` | `00 00 02 03 83 <pid> 00 <rid> 00 ...` | Queries brightness for `region_id` (`resp[8]` = `0..100`) |
| `SetLedBrigtness` | `00 00 02 03 03 <pid> 00 <rid> <brt>` | Sets brightness (`0..100`) for `region_id` |

