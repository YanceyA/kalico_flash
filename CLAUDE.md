# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

kalico-flash is a Python TUI tool that automates Kalico firmware building and flashing for USB-connected MCU boards on a Raspberry Pi. It replaces the manual `make clean` -> `make menuconfig` -> `make` -> `make flash` workflow with auto-discovery, device profiles, cached configs, and an interactive TUI flow.

**Target Environment:** Raspberry Pi running Kalico/Moonraker/Fluidd (MainsailOS or similar)
**Klipper Fork:** Kalico (https://docs.kalico.gg) -- not mainline Klipper
**Python:** 3.9+ stdlib only (no external dependencies)

## Repository Structure

```
kalico-flash/
├── kflash.py          # Entry point (shebang launcher)
├── install.sh         # Installer (kflash symlink to ~/.local/bin)
├── kflash/
│   ├── __init__.py    # Package init
│   ├── flash.py       # Main entry, TUI launcher
│   ├── tui.py         # TUI main loop, input handling, screen rendering
│   ├── screen.py      # Device config screen (edit device settings)
│   ├── panels.py      # Panel renderer (status panel, action panel, dividers)
│   ├── ansi.py        # ANSI escape utilities (cursor, clear, truecolor)
│   ├── theme.py       # Color theme (truecolor palette, semantic styles)
│   ├── models.py      # Dataclass contracts (DeviceEntry, BuildResult, etc.)
│   ├── errors.py      # Exception hierarchy and error templates
│   ├── output.py      # Structured output (phase labels, progress)
│   ├── registry.py    # Device registry with atomic JSON persistence
│   ├── discovery.py   # USB scanning and pattern matching
│   ├── config.py      # Kconfig caching and MCU validation
│   ├── validation.py  # Input validation, slug generation, config checks
│   ├── build.py       # menuconfig TUI and firmware compilation
│   ├── service.py     # Kalico service lifecycle (context manager)
│   ├── flasher.py     # Dual-method flash operations (Katapult + make flash)
│   └── moonraker.py   # Moonraker API client (print safety check)
└── devices.json       # Device registry (created on first device registration)
```

## Architecture

**TUI-driven dispatch:** `tui.py` runs the main loop, renders the screen, and dispatches user actions to `flash.py` workflows. Modules do not cross-import each other.

**Dataclass contracts:** All cross-module data exchange uses typed dataclasses in `models.py`:
- `DeviceEntry` -- Registered device (key, name, MCU, serial pattern)
- `DiscoveredDevice` -- USB device found during scanning
- `GlobalConfig` -- Paths to Klipper/Katapult source
- `BuildResult` / `FlashResult` -- Operation outcomes

**Context manager for safety:** `klipper_service_stopped()` in `service.py` guarantees Klipper restart on all code paths (success, failure, exception, Ctrl+C).

## TUI Menu

Run `kflash` to launch the TUI. The main screen shows:
- **Status panel**: Registered devices with connection status and firmware versions
- **Actions panel**: Available operations

Actions:
- **Flash Device (F)** -- Select a connected device, run menuconfig, build, flash
- **Flash All (A)** -- Flash all connected devices sequentially
- **Add Device (N)** -- Register a new USB device (prompts for name, selects MCU)
- **Remove Device (X)** -- Remove a registered device
- **Config Device (C)** -- Edit device settings (name, MCU, flash method, exclusion)
- **Refresh Devices (R)** -- Re-scan USB devices and update status
- **Quit (Q)** -- Exit

## Flash Workflow (4 Phases)

1. **[Discovery]** -- Scan `/dev/serial/by-id/`, match against registry patterns
2. **[Config]** -- Load cached `.config`, run `make menuconfig`, validate MCU type
3. **[Build]** -- `make clean` + `make -j$(nproc)` with timeout (300s)
4. **[Flash]** -- Stop Klipper, try Katapult first, fallback to `make flash`, restart Klipper

## Development Environment

Claude Code has SSH access to the target Raspberry Pi for live testing.

**Connection Details:**
- **Host:** `192.168.50.50`
- **User:** `yanceya`
- **Auth:** SSH key (passwordless)
- **Remote path:** `~/kalico-flash/`

**Pi Environment:**
- Python 3.11.2
- Kalico at `~/klipper/`
- Katapult at `~/katapult/`
- Connected boards: STM32H723 (Octopus Pro), RP2040 (Nitehawk), Beacon probe

**Sync code to Pi:**
```bash
scp /c/dev_projects/kalico_flash/kflash.py yanceya@192.168.50.50:~/kalico-flash/
scp /c/dev_projects/kalico_flash/kflash/*.py yanceya@192.168.50.50:~/kalico-flash/kflash/
```

**Run on Pi:**
```bash
ssh yanceya@192.168.50.50 "cd ~/kalico-flash && python3 kflash.py"
```

**Local development (Windows):**
```bash
cd kalico-flash
python kflash.py
```

No automated tests -- validation is manual on live hardware.

## Coding Conventions

- **Python 3.9+ stdlib only** -- No pip dependencies
- **Type hints** -- Use `from __future__ import annotations` for forward references
- **Dataclasses** -- For all structured data crossing module boundaries
- **Paths as strings** -- Store as `str` in dataclasses for JSON serialization
- **Atomic file writes** -- Use temp file + fsync + rename pattern for registry/config
- **Subprocess timeouts** -- Always specify: build=300s, flash=60s, service=30s
- **Inherited stdio** -- Use `subprocess.run()` with inherited stdio for TUI (`menuconfig`)

## Exception Hierarchy

All custom exceptions inherit from `KlipperFlashError`:
- `RegistryError` -- Registry file corrupt/missing
- `DeviceNotFoundError` -- Device not in registry or not connected
- `DiscoveryError` -- USB scanning failures
- `ConfigError` -- Config file or MCU validation errors
- `BuildError` -- make menuconfig/clean/build failures
- `ServiceError` -- Klipper service stop/start failures
- `FlashError` -- Katapult or make flash failures

## Key Implementation Details

- **Serial paths:** Use `/dev/serial/by-id/` symlinks (stable across reboots)
- **MCU validation:** Bidirectional prefix match (e.g., `stm32h723` matches `stm32h723xx`)
- **Flash method:** Katapult preferred (flashtool.py), `make flash` as fallback
- **Service management:** Requires passwordless sudo (standard on MainsailOS/FluiddPi)
- **Working directory:** `make` commands must run with `cwd=klipper_dir`
- **TTY check:** Interactive modes error if stdin is not a TTY

## Supported Boards

Tested with:
- **BTT Octopus Pro v1.1** -- STM32H723, USB, 128KB bootloader, 25kHz clock
- **LDO Nitehawk 36** -- RP2040, USB, 16KB bootloader, `!gpio8` at start

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

- RPi MCU flashing (different workflow -- linux process, not USB serial)
- CAN bus device discovery (USB only)
- Moonraker/Fluidd UI integration (TUI only)
- Firmware version tracking/rollback
- Automatic Klipper git pull (dangerous -- user manages source updates)
