# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

kalico-flash is a Python CLI tool that automates Kalico firmware building and flashing for USB-connected MCU boards on a Raspberry Pi. It replaces the manual `make clean` → `make menuconfig` → `make` → `make flash` workflow with auto-discovery, device profiles, cached configs, and a single-command flow.

**Target Environment:** Raspberry Pi running Kalico/Moonraker/Fluidd (MainsailOS or similar)
**Klipper Fork:** Kalico (https://docs.kalico.gg) — not mainline Klipper
**Python:** 3.9+ stdlib only (no external dependencies)

## Repository Structure

```
kalico-flash/
├── flash.py       # CLI entry point, argument parsing, command routing
├── models.py      # Dataclass contracts (DeviceEntry, BuildResult, etc.)
├── errors.py      # Exception hierarchy (KalicoFlashError base)
├── output.py      # Pluggable output interface (CLI, future Moonraker)
├── registry.py    # Device registry with atomic JSON persistence
├── discovery.py   # USB scanning and pattern matching
├── config.py      # Kconfig caching and MCU validation
├── build.py       # menuconfig TUI and firmware compilation
├── service.py     # Kalico service lifecycle (context manager)
├── flasher.py     # Dual-method flash operations
└── devices.json   # Device registry (created on first --add-device)
```

## Architecture

**Hub-and-spoke pattern:** `flash.py` orchestrates all modules — modules do not cross-import each other.

**Dataclass contracts:** All cross-module data exchange uses typed dataclasses in `models.py`:
- `DeviceEntry` — Registered device (key, name, MCU, serial pattern)
- `DiscoveredDevice` — USB device found during scanning
- `GlobalConfig` — Paths to Klipper/Katapult source
- `BuildResult` / `FlashResult` — Operation outcomes

**Late imports:** CLI loads modules only when needed for fast startup.

**Context manager for safety:** `klipper_service_stopped()` in `service.py` guarantees Klipper restart on all code paths (success, failure, exception, Ctrl+C).

## CLI Commands

```bash
# Interactive: select device from connected boards, then flash
python flash.py

# Flash specific registered device
python flash.py --device octopus-pro

# Register a new board (interactive wizard)
python flash.py --add-device

# Show registered devices with connection status
python flash.py --list-devices

# Remove a registered device
python flash.py --remove-device octopus-pro
```

## Flash Workflow (4 Phases)

1. **[Discovery]** — Scan `/dev/serial/by-id/`, match against registry patterns
2. **[Config]** — Load cached `.config`, run `make menuconfig`, validate MCU type
3. **[Build]** — `make clean` + `make -j$(nproc)` with timeout (300s)
4. **[Flash]** — Stop Klipper, try Katapult first, fallback to `make flash`, restart Klipper

## Development Commands

**Run the tool:**
```bash
cd kalico-flash
python flash.py --help
```

**Test on target Pi:**
```bash
scp -r kalico-flash/ pi@your-pi:~/kalico-flash/
ssh pi@your-pi
cd ~/kalico-flash && python3 flash.py --list-devices
```

No automated tests — validation is manual on live hardware.

## Coding Conventions

- **Python 3.9+ stdlib only** — No pip dependencies
- **Type hints** — Use `from __future__ import annotations` for forward references
- **Dataclasses** — For all structured data crossing module boundaries
- **Paths as strings** — Store as `str` in dataclasses for JSON serialization
- **Atomic file writes** — Use temp file + fsync + rename pattern for registry/config
- **Subprocess timeouts** — Always specify: build=300s, flash=60s, service=30s
- **Inherited stdio** — Use `subprocess.run()` with inherited stdio for TUI (`menuconfig`)

## Exception Hierarchy

All custom exceptions inherit from `KlipperFlashError`:
- `RegistryError` — Registry file corrupt/missing
- `DeviceNotFoundError` — Device not in registry or not connected
- `DiscoveryError` — USB scanning failures
- `ConfigError` — Config file or MCU validation errors
- `BuildError` — make menuconfig/clean/build failures
- `ServiceError` — Klipper service stop/start failures
- `FlashError` — Katapult or make flash failures

## Key Implementation Details

- **Serial paths:** Use `/dev/serial/by-id/` symlinks (stable across reboots)
- **MCU validation:** Bidirectional prefix match (e.g., `stm32h723` matches `stm32h723xx`)
- **Flash method:** Katapult preferred (flashtool.py), `make flash` as fallback
- **Service management:** Requires passwordless sudo (standard on MainsailOS/FluiddPi)
- **Working directory:** `make` commands must run with `cwd=klipper_dir`
- **TTY check:** Interactive modes error if stdin is not a TTY

## Supported Boards

Tested with:
- **BTT Octopus Pro v1.1** — STM32H723, USB, 128KB bootloader, 25kHz clock
- **LDO Nitehawk 36** — RP2040, USB, 16KB bootloader, `!gpio8` at start

Should work with any USB-connected board that appears in `/dev/serial/by-id/` with `Klipper_` or `katapult_` prefix.

## Configuration Storage

**Device registry:** `kalico-flash/devices.json`
```json
{
  "global": {
    "klipper_dir": "~/klipper",
    "katapult_dir": "~/katapult",
    "default_flash_method": "katapult"
  },
  "devices": {
    "octopus-pro": {
      "name": "Octopus Pro v1.1",
      "mcu": "stm32h723",
      "serial_pattern": "usb-Klipper_stm32h723xx_*"
    }
  }
}
```

**Menuconfig cache:** `~/.config/kalico-flash/configs/{device-key}/.config` (respects `XDG_CONFIG_HOME`)

## Out of Scope

- RPi MCU flashing (different workflow — linux process, not USB serial)
- CAN bus device discovery (USB only)
- Moonraker/Fluidd UI integration (CLI only)
- Multi-device batch flash (one device at a time)
- Firmware version tracking/rollback
- Automatic Klipper git pull (dangerous — user manages source updates)

## Future Plans (v2.0 candidates)

- SHA256 change detection to skip rebuild when config unchanged
- `--skip-menuconfig` flag when cached config exists
- `--no-clean` flag for incremental builds
- Post-flash verification (device reappears with Klipper serial)
- Moonraker print status check (refuse flash while printing)
