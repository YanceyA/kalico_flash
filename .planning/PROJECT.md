# kalico-flash

## What This Is

A Python CLI tool that automates Klipper/Kalico firmware building and flashing for USB-connected MCU boards on a Raspberry Pi. Features interactive TUI menu, print safety checks, post-flash verification, and comprehensive error recovery. Replaces the manual workflow of make clean, make menuconfig, make, make flash with auto-discovery, device profiles, cached configs, and a single-command flow.

## Core Value

One command to build and flash any registered board — no remembering serial paths, flash commands, or config locations.

## Current Milestone: v2.1 TUI Color Theme

**Goal:** Add KIAUH-style ANSI color support with a centralized theme system
**Started:** 2026-01-28
**Phases:** 8-9

See: `.planning/ROADMAP.md` for phase breakdown
See: `.planning/REQUIREMENTS.md` for full requirements list
See: `.working/theme_plan.md` for detailed implementation plan

## Previous State (v2.0 shipped)

**Shipped:** 2026-01-27
**Modules:** 12 Python modules in kalico-flash/
**LOC:** 2,909 lines Python 3.9+ stdlib only
**Status:** Ready for public release

**CLI commands:**
- `kflash` — Interactive TUI menu with Add/List/Flash/Remove/Settings
- `kflash --device KEY` — Flash specific registered device
- `kflash --device KEY -s` — Flash with skip-menuconfig (uses cached config)
- `kflash --add-device` — Register new board
- `kflash --list-devices` — Show registered/connected devices
- `kflash --remove-device KEY` — Unregister board
- `kflash --exclude-device KEY` — Mark device as non-flashable
- `kflash --include-device KEY` — Mark device as flashable

## Requirements

### Validated

**v1.0 (MVP):**
- ✓ Device registry with atomic JSON persistence — v1.0
- ✓ USB discovery with pattern matching (/dev/serial/by-id/) — v1.0
- ✓ Config caching with MCU validation (prevents wrong-board firmware) — v1.0
- ✓ Build pipeline (make menuconfig + make clean + make -j) — v1.0
- ✓ Service lifecycle (guaranteed Klipper restart on all code paths) — v1.0
- ✓ Dual-method flash (Katapult first, make flash fallback) — v1.0
- ✓ Phase-labeled output ([Discovery], [Config], [Build], [Flash]) — v1.0
- ✓ Subprocess timeouts (build: 300s, flash: 60s, service: 30s) — v1.0
- ✓ Hub-and-spoke architecture with dataclass contracts — v1.0

**v2.0 (Public Release):**
- ✓ Interactive TUI menu with numbered options — v2.0
- ✓ Unicode/ASCII box drawing for terminal compatibility — v2.0
- ✓ Print safety check via Moonraker (blocks flash during print) — v2.0
- ✓ Host vs MCU version comparison before flash — v2.0
- ✓ Post-flash verification (confirms device reappears as Klipper) — v2.0
- ✓ Skip-menuconfig flag for power users with cached configs — v2.0
- ✓ Device exclusion for non-flashable devices (Beacon probe) — v2.0
- ✓ Contextual error messages with numbered recovery steps — v2.0
- ✓ Installation script (kflash command) — v2.0
- ✓ README documentation with Quick Start and CLI Reference — v2.0
- ✓ Moonraker Update Manager integration — v2.0
- ✓ Settings submenu for path configuration — v2.0

### Active (v2.1 TUI Color Theme)

**Theme Infrastructure:**
- [ ] THEME-01: Theme module with semantic style dataclass
- [ ] THEME-02: Terminal capability detection (TTY, NO_COLOR, FORCE_COLOR)
- [ ] THEME-03: Windows VT mode support via ctypes
- [ ] THEME-04: No-color fallback theme
- [ ] THEME-05: Cached theme singleton with get_theme()/reset_theme()
- [ ] THEME-06: Screen clear utility

**CLI Output Styling:**
- [ ] OUT-01: Colored [OK] messages (green)
- [ ] OUT-02: Colored [FAIL] messages (red)
- [ ] OUT-03: Colored [!!] warnings (yellow)
- [ ] OUT-04: Colored [section] info (cyan)
- [ ] OUT-05: Colored [phase] markers (cyan)
- [ ] OUT-06: Colored device markers (REG/NEW/BLK/DUP)
- [ ] OUT-07: Bold prompts

**TUI Integration:**
- [ ] TUI-01: Screen clear before main menu
- [ ] TUI-02: Bold menu title
- [ ] TUI-03: Screen clear in settings submenu

**Error Formatting:**
- [ ] ERR-01: Colored [FAIL] header in errors

### Future Candidates

- [ ] SHA256 change detection to skip rebuild when config unchanged
- [ ] --no-clean flag for incremental builds
- [ ] Batch flash multiple devices
- [ ] CAN bus device support

### Out of Scope

- RPi MCU flashing — different workflow (linux process, not USB serial)
- CAN bus device discovery — USB only for now
- Moonraker/Fluidd web UI integration — CLI only, architecture supports future integration
- Firmware version tracking/rollback — requires infrastructure
- Automatic klipper git pull — dangerous, user manages source updates
- curses-based TUI — complexity and Windows issues, print/input sufficient
- Moonraker URL configuration — hardcoded localhost:7125, keep it simple

## Context

- **Target environment:** Raspberry Pi running Klipper/Moonraker/Fluidd (MainsailOS or similar)
- **Klipper fork:** Kalico (https://docs.kalico.gg) — not mainline Klipper
- **Boards:**
  - Octopus Pro v1.1 — STM32H723, USB, 128kb bootloader, 25kHz clock
  - Nitehawk 36 — RP2040, USB, 16kb bootloader, !gpio8 at start
  - Beacon probe — Registered as non-flashable
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
- **Deployment**: Git clone + ./install.sh on Pi

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Katapult-first with auto-fallback | Katapult is preferred flash method; make flash as safety net | ✓ Good |
| Single serial pattern per device (klipper mode only) | Katapult mode requires manual DFU entry, too complex for this tool | ✓ Good |
| menuconfig runs every flash (unless -s flag) | User wants option to tweak config each time | ✓ Good |
| No dry-run | SSH workflow doesn't benefit enough to justify complexity | ✓ Good |
| Stdlib only | Raspberry Pi environment, avoid dependency management | ✓ Good |
| Context manager for service lifecycle | Guarantees restart even on exception/Ctrl+C | ✓ Good |
| Hub-and-spoke architecture | Clean separation, no cross-imports between modules | ✓ Good |
| Dataclass contracts for cross-module data | Strong typing, clear interfaces | ✓ Good |
| Late imports in CLI | Fast startup, only load what's needed | ✓ Good |
| Graceful degradation for Moonraker | Return None on failure, never raise; warn but don't block | ✓ Good |
| Version check informational only | Never blocks flash, just shows warning if outdated | ✓ Good |
| No --force for print blocking | Safety first - wait or cancel print, no override | ✓ Good |
| Print/input TUI (not curses) | Simpler, no Windows issues, works over SSH | ✓ Good |
| format_error() for all error output | Consistent 80-column wrapped output with context | ✓ Good |
| Symlink over wrapper script | Direct symlink to flash.py, uses Python shebang | ✓ Good |
| 30s verification timeout | RP2040 boards need more time to re-enumerate | ✓ Good |

---
*Last updated: 2026-01-28 after v2.1 milestone initialization*
