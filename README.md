# kalico-flash

A Python CLI tool that automates Kalico firmware building and flashing for USB-connected MCU boards on a Raspberry Pi.

Replaces the manual workflow of `make clean`, `make menuconfig`, `make`, `make flash` with auto-discovery, device profiles, cached configs, and a single-command flow.

## Features

- **One-command flash workflow** - Build and flash firmware with `python flash.py`
- **Device registry** - Register boards once, flash by name forever
- **USB auto-discovery** - Scans `/dev/serial/by-id/` for connected devices
- **Config caching** - Per-device menuconfig settings preserved between sessions
- **MCU validation** - Prevents flashing wrong firmware to a board
- **Dual-method flash** - Katapult first, `make flash` fallback
- **Service lifecycle** - Guaranteed Klipper restart even on Ctrl+C or errors
- **Phase-labeled output** - Clear `[Discovery]`, `[Config]`, `[Build]`, `[Flash]` progress
- **Zero dependencies** - Python 3.9+ stdlib only, no pip installs required

## Requirements

- **Python 3.9+** (stdlib only)
- **Raspberry Pi** (or similar Linux SBC) running Klipper/Moonraker
- **Klipper source** at `~/klipper` (configurable)
- **Katapult** at `~/katapult` (optional, for preferred flash method)
- **Passwordless sudo** (standard on MainsailOS/FluiddPi)
- **USB-connected MCU boards** (not CAN bus)

## Installation

1. Copy the `kalico-flash/` directory to your Raspberry Pi:
   ```bash
   scp -r kalico-flash/ pi@your-pi:~/kalico-flash/
   ```

2. Verify Python version:
   ```bash
   python3 --version  # Must be 3.9+
   ```

3. Test the tool:
   ```bash
   cd ~/kalico-flash
   python3 flash.py --help
   ```

## Usage

### Register a New Device

```bash
python3 flash.py --add-device
```

Interactive wizard that:
1. Scans USB for connected boards
2. Prompts for device key (e.g., `octopus-pro`)
3. Auto-detects MCU type from serial path
4. Saves to `devices.json`

First run also configures global paths (Klipper/Katapult directories).

### List Registered Devices

```bash
python3 flash.py --list-devices
```

Shows all registered devices with connection status:
```
[Devices] 2 registered, 3 USB devices found
  [OK] octopus-pro: Octopus Pro v1.1 (stm32h723)  /dev/serial/by-id/usb-Klipper_stm32h723xx_...
  [--] nitehawk: Nitehawk 36 (rp2040)             (disconnected)
  [??] Unknown device                             [usb-Beacon_RevH_...]
```

### Flash a Device (Interactive)

```bash
python3 flash.py
```

If multiple registered devices are connected, prompts for selection. Single device auto-selects with confirmation.

### Flash a Specific Device

```bash
python3 flash.py --device octopus-pro
```

Skips selection, directly flashes the named device.

### Remove a Device

```bash
python3 flash.py --remove-device octopus-pro
```

Removes from registry, optionally deletes cached config.

## Workflow

When you run `python3 flash.py`, the tool executes four phases:

### 1. Discovery
- Scans `/dev/serial/by-id/` for USB serial devices
- Matches against registered device patterns
- Prompts for device selection (if interactive)

### 2. Config
- Loads cached `.config` for the device (if exists)
- Launches `make menuconfig` TUI for review/changes
- Saves updated config to cache
- Validates MCU type matches device registry

### 3. Build
- Runs `make clean` in Klipper directory
- Runs `make -jN` (N = CPU cores) for parallel build
- Verifies `out/klipper.bin` was created

### 4. Flash
- Verifies device still connected
- Stops Klipper service (`sudo systemctl stop klipper`)
- Attempts Katapult flash (`flashtool.py`)
- Falls back to `make flash` if Katapult fails
- Restarts Klipper service (guaranteed, even on error)

## Architecture

```
kalico-flash/
├── flash.py       # CLI entry point, argument parsing, command routing
├── models.py      # Dataclass contracts (DeviceEntry, BuildResult, etc.)
├── errors.py      # Exception hierarchy (KlipperFlashError base)
├── output.py      # Pluggable output interface (CLI, future Moonraker)
├── registry.py    # Device registry with atomic JSON persistence
├── discovery.py   # USB scanning and pattern matching
├── config.py      # Kconfig caching and MCU validation
├── build.py       # menuconfig TUI and firmware compilation
├── service.py     # Klipper service lifecycle (context manager)
├── flasher.py     # Dual-method flash operations
└── devices.json   # Device registry (created on first --add-device)
```

### Design Principles

- **Hub-and-spoke architecture** - `flash.py` orchestrates, modules don't cross-import
- **Dataclass contracts** - Strong typing for cross-module data exchange
- **Late imports** - Fast CLI startup, only loads what's needed
- **Atomic writes** - Registry and config use temp file + fsync + rename
- **Context manager** - Service lifecycle guarantees restart on all code paths

## Configuration

### Global Config

Set during first `--add-device`:
- `klipper_dir` - Path to Klipper source (default: `~/klipper`)
- `katapult_dir` - Path to Katapult source (default: `~/katapult`)
- `default_flash_method` - `katapult` or `make_flash` (default: `katapult`)

### Per-Device Config

Stored in `devices.json`:
```json
{
  "devices": {
    "octopus-pro": {
      "name": "Octopus Pro v1.1",
      "mcu": "stm32h723",
      "serial_pattern": "usb-Klipper_stm32h723xx_29001A001151313531383332*",
      "flash_method": null
    }
  }
}
```

### Menuconfig Cache

Per-device `.config` files stored in:
```
~/.config/kalico-flash/configs/{device-key}/.config
```

Respects `XDG_CONFIG_HOME` if set.

## Timeouts

| Operation | Default | Notes |
|-----------|---------|-------|
| Build | 300s | `make clean` + `make -j` |
| Flash | 60s | Per method (Katapult, then make flash) |
| Service | 30s | `systemctl stop/start klipper` |

## Supported Boards

Tested with:
- **BTT Octopus Pro v1.1** - STM32H723, USB, 128KB bootloader
- **LDO Nitehawk 36** - RP2040, USB, 16KB bootloader

Should work with any USB-connected board that:
- Appears in `/dev/serial/by-id/` with `Klipper_` or `katapult_` prefix
- Supports `make flash` or Katapult flashing

## Troubleshooting

### "No USB devices found"
- Check board is powered and connected via USB
- Verify with `ls /dev/serial/by-id/`
- Ensure board is in Klipper mode (not DFU/bootloader)

### "Device not found in registry"
- Run `--list-devices` to see registered names
- Use exact device key with `--device`
- Re-register with `--add-device` if needed

### "MCU mismatch"
- Config was edited for different board type
- Re-run menuconfig and select correct MCU
- Or delete cached config: `rm ~/.config/kalico-flash/configs/{key}/.config`

### "Flash timeout"
- Board may need manual recovery
- Power cycle the board
- Try `--device KEY` to retry

### "Failed to stop Klipper"
- Check sudo permissions: `sudo -n systemctl status klipper`
- Verify Klipper service exists: `systemctl list-units | grep klipper`

## Future Plans (v2.0)

- [ ] SHA256 change detection to skip rebuild when config unchanged
- [ ] `--skip-menuconfig` flag when cached config exists
- [ ] `--no-clean` flag for incremental builds
- [ ] Post-flash verification (device reappears with Klipper serial)
- [ ] Moonraker print status check (refuse flash while printing)

## Out of Scope

- **RPi MCU flashing** - Different workflow (linux process, not USB)
- **CAN bus devices** - USB only
- **Multi-device batch flash** - One device at a time
- **Firmware rollback** - No version tracking
- **Automatic Klipper updates** - User manages source

## License

This project is provided as-is for personal use with Klipper/Kalico 3D printing setups.

## Acknowledgments

Built for a Voron 2.4 running [Kalico](https://docs.kalico.gg) (Klipper fork).
