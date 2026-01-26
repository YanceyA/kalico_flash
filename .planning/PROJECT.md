# kalico-flash

## What This Is

A Python CLI tool that automates Klipper/Kalico firmware building and flashing for USB-connected MCU boards on a Raspberry Pi. Replaces the manual workflow of make clean, make menuconfig, make, make flash with auto-discovery, device profiles, cached configs, and a single-command flow. Built for a Voron 2.4 running Kalico with an Octopus Pro (H723), Nitehawk 36 (RP2040), and Beacon probe.

## Core Value

One command to build and flash any registered board — no remembering serial paths, flash commands, or config locations.

## Current Milestone: v2.0 Public Release

**Goal:** Prepare kalico-flash for release to the broader Klipper community with safety features, polish, and ease of installation.

**Target features:**
- Simple TUI menu for navigation without memorizing CLI flags
- Print status check before flash (prevent mid-print disasters)
- Post-flash verification (confirm device reappears)
- Skip menuconfig flag for power users
- Better error messages with recovery guidance
- Version mismatch detection (host vs MCU)
- Installation script (kflash command)
- README documentation for public users
- Device exclusion support (Beacon probe marked not flashable)

## Previous Milestone (v1.0 shipped)

- **10 Python modules** in klipper-flash/
- **1,695 LOC** Python 3.9+ stdlib only
- **Tested and working** on target Raspberry Pi

**CLI commands:**
- `python flash.py` — Interactive device selection, full flash workflow
- `python flash.py --device KEY` — Flash specific registered device
- `python flash.py --add-device` — Register new board
- `python flash.py --list-devices` — Show registered/connected devices
- `python flash.py --remove-device KEY` — Unregister board

## Requirements

### Validated

- ✓ Device registry with atomic JSON persistence — v1.0
- ✓ USB discovery with pattern matching (/dev/serial/by-id/) — v1.0
- ✓ Config caching with MCU validation (prevents wrong-board firmware) — v1.0
- ✓ Build pipeline (make menuconfig + make clean + make -j) — v1.0
- ✓ Service lifecycle (guaranteed Klipper restart on all code paths) — v1.0
- ✓ Dual-method flash (Katapult first, make flash fallback) — v1.0
- ✓ Phase-labeled output ([Discovery], [Config], [Build], [Flash]) — v1.0
- ✓ Subprocess timeouts (build: 300s, flash: 60s, service: 30s) — v1.0
- ✓ Hub-and-spoke architecture with dataclass contracts — v1.0

### Active (v2.0 candidates)

- [ ] SHA256 change detection to skip rebuild when config unchanged
- [ ] --skip-menuconfig flag to skip TUI when cached config exists
- [ ] --no-clean flag for incremental builds
- [ ] Post-flash verification (check device reappears with klipper serial pattern)
- [ ] Moonraker print status check before stopping klipper (refuse if printing)

### Out of Scope

- RPi MCU flashing — different workflow (linux process, not USB serial)
- CAN bus device discovery — USB only
- Moonraker/Fluidd UI integration — CLI only, architecture supports future integration
- Multi-device batch flash — one device at a time
- Firmware version tracking/rollback — out of scope
- Automatic klipper git pull — dangerous, user manages source updates

## Context

- **Target environment:** Raspberry Pi running Klipper/Moonraker/Fluidd (MainsailOS or similar)
- **Klipper fork:** Kalico (https://docs.kalico.gg) — not mainline Klipper
- **Boards:**
  - Octopus Pro v1.1 — STM32H723, USB, 128kb bootloader, 25kHz clock
  - Nitehawk 36 — RP2040, USB, 16kb bootloader, !gpio8 at start
- **Serial paths:** Use /dev/serial/by-id/ symlinks (stable across reboots), match klipper pattern only
- **Flash methods:** Both boards support katapult (flashtool.py) and make flash. Katapult is preferred, make flash is fallback.
- **Klipper source:** ~/klipper (default), Katapult source: ~/katapult (default)
- **menuconfig:** ncurses TUI, must run with inherited stdio (subprocess.run, not check_output)
- **Permissions:** User has passwordless sudo (standard for MainsailOS/FluiddPi)

### Reference Commands

**Octopus Pro (H723):**
```
python3 ~/katapult/scripts/flashtool.py -f ~/klipper/out/klipper.bin -d /dev/serial/by-id/usb-katapult_stm32h723xx_29001A001151313531383332-if00
make flash FLASH_DEVICE=/dev/serial/by-id/usb-Klipper_stm32h723xx_29001A001151313531383332-if00
```

**Nitehawk 36 (RP2040):**
```
make flash FLASH_DEVICE=/dev/serial/by-id/usb-Klipper_rp2040_30333938340A53E6-if00
python3 ~/katapult/scripts/flashtool.py -f ~/klipper/out/klipper.bin -d /dev/serial/by-id/usb-katapult_rp2040_30333938340A53E6-if00
```

## Constraints

- **Python version**: 3.9+ stdlib only — no pip installs, no external dependencies
- **Platform**: Raspberry Pi (ARM Linux) — must work over SSH
- **Working directory**: make commands must run with cwd=klipper_dir
- **Service management**: sudo systemctl stop/start klipper (passwordless sudo assumed)
- **Deployment**: Built on dev machine, manually copied to Pi

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Katapult-first with auto-fallback | Katapult is preferred flash method; make flash as safety net | ✓ Good |
| Single serial pattern per device (klipper mode only) | Katapult mode requires manual DFU entry, too complex for this tool | ✓ Good |
| menuconfig runs every flash | User wants the option to tweak config each time | ✓ Good |
| No dry-run | SSH workflow doesn't benefit enough to justify complexity | ✓ Good |
| Stdlib only | Raspberry Pi environment, avoid dependency management | ✓ Good |
| Context manager for service lifecycle | Guarantees restart even on exception/Ctrl+C | ✓ Good |
| Hub-and-spoke architecture | Clean separation, no cross-imports between modules | ✓ Good |
| Dataclass contracts for cross-module data | Strong typing, clear interfaces | ✓ Good |
| Late imports in CLI | Fast startup, only load what's needed | ✓ Good |

---
*Last updated: 2026-01-26 after v2.0 milestone start*
