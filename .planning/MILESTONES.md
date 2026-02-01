# Project Milestones: kalico-flash

## v4.0 Remove CLI & Internalize Device Keys (Shipped: 2026-02-01)

**Delivered:** Removed all CLI/argparse infrastructure and made device keys auto-generated internal identifiers. The tool now operates exclusively through TUI — `kflash` launches directly into the interactive menu with no argument parsing.

**Phases completed:** 24-27 (6 plans total)

**Key accomplishments:**

- Auto-generated device keys from display names via Unicode-aware slugification with collision handling
- Device keys fully internalized — users interact only with display names across all TUI surfaces
- All argparse, CLI flags, and CLI-only code paths deleted; main() reduced to thin TUI launcher
- Documentation (README, CLAUDE.md, install.sh) and error recovery messages updated for TUI-only operation
- Net code reduction: -229 lines (352 deleted, 123 added) across 6 source files

**Stats:**

- 6 files modified
- 6,371 lines of Python (total project)
- 4 phases, 6 plans
- 1 day (2026-02-01)

**Git range:** `feat(24-01)` → `docs(27)`

**What's next:** TBD

---

## v3.4 Check Katapult (Shipped: 2026-01-31)

**Delivered:** Katapult bootloader detection engine with live hardware research, tri-state check function, and TUI integration. Feature parked after testing revealed device recovery limitations — code retained in codebase for future revisit.

**Phases completed:** 21-23 (3 plans total)

**Key accomplishments:**

- Resolved all hardware questions via live SSH testing on Pi (sysfs paths, serial substrings, timing measurements)
- Built check_katapult() detection engine with tri-state result, USB helpers, and research-derived timing constants
- Wired Katapult check into device config screen with safety gates (warning, confirmation, service lifecycle)
- Discovered recovery limitations through live testing — Katapult devices can't be auto-recovered, DFU devices need manual reset
- Parked feature from UI after testing — code retained in flasher.py for future use

**Stats:**

- 19 files modified
- 6,694 lines of Python (total project)
- 3 phases, 3 plans
- 1 day (2026-01-31)

**Git range:** `docs(21)` → `fix(23)`

**Feature status:** PARKED — implemented and tested but removed from UI. Code in flasher.py (check_katapult, helpers, KatapultCheckResult) retained for future revisit when more boards available and recovery strategy improved.

**What's next:** v4.0 Remove CLI & Internalize Device Keys

---

## v3.3 Config Device (Shipped: 2026-01-31)

**Delivered:** Device config editing from the TUI — edit device key, name, flash method, include/exclude, and launch menuconfig from the main menu.

**Phases completed:** 18-20 (4 plans total)

**Key accomplishments:**

- Registry update_device() with atomic load-modify-save pattern
- Device config screen with two-panel layout (identity + editable settings)
- Collect-then-save editing loop for 5 field types (text, validated text, cycle, toggle, action)
- Safe key rename with config cache directory migration
- E key wired into main menu with device selection and step dividers

**Stats:**

- 15 source files modified
- 6,179 lines of Python (total project)
- 3 phases, 4 plans
- Same day (2026-01-31)

**Git range:** `feat(18-01)` → `feat(20-01)`

**What's next:** v3.4 Check Katapult — Katapult bootloader detection from device config screen

---

## v3.2 Action Dividers (Shipped: 2026-01-31)

**Delivered:** Visual step and device dividers in all command workflows — light dashed separators between phases and labeled dividers between devices in batch operations.

**Phases completed:** 16-17 (3 plans total)

**Key accomplishments:**

- Output Protocol extended with step_divider() and device_divider() methods
- Dividers adapt to terminal width and degrade to ASCII on non-Unicode terminals
- Flash, Add Device, Remove Device workflows separated by step dividers
- Flash All shows labeled device dividers between each device in build and flash phases

**Stats:**

- 2 phases, 3 plans
- Same day (2026-01-31)

**Git range:** `feat(16-01)` → `feat(17-02)`

**What's next:** v3.3 Config Device

---

## v3.1 Config Validation (Shipped: 2026-01-30)

**Delivered:** Input validation for all TUI settings — path existence/content checks and numeric bounds with reject-and-reprompt behavior.

**Phases completed:** 15 (1 plan total)

**Key accomplishments:**

- Pure validator functions for path existence and file content checks (validation.py)
- Numeric range enforcement for stagger_delay (0-30s) and return_delay (0-60s)
- Reject-and-reprompt loops wired into TUI settings edit flow
- Tilde expansion before validation, original user input preserved for storage

**Stats:**

- 3 source files (1 created, 2 modified)
- 5,600 lines of Python (total project)
- 1 phase, 1 plan
- Same day (2026-01-30)

**Git range:** `feat(15-01)` → `docs(v3.1)`

**What's next:** TBD

---

## v3.0 TUI Redesign & Flash All (Shipped: 2026-01-30)

**Delivered:** Complete TUI redesign with truecolor panels, numbered device references, config screen with settings persistence, and Flash All with batch processing.

**Phases completed:** 10-14 (8 plans total)

**Key accomplishments:**

- Truecolor RGB palette with 3-tier fallback (truecolor → ANSI 256 → ANSI 16)
- ANSI-aware string utilities and panel renderer with rounded borders
- Panel-based main screen with status, devices, and actions sections
- Config screen with flat numbered settings and type-dispatched editing
- Countdown timer with keypress cancel for post-action review
- Flash All with build-then-flash architecture and continue-on-failure
- Post-flash verification per device in batch mode

**Stats:**

- 13 Python modules
- 5,500+ lines of Python
- 5 phases, 8 plans
- 2 days (2026-01-29 → 2026-01-30)

**Git range:** `feat(10-01)` → `docs(14)`

**What's next:** Config validation for settings

---

## v2.1 TUI Color Theme (Shipped: 2026-01-29)

**Delivered:** Semantic color theming with terminal capability detection and cached singleton pattern.

**Phases completed:** 8-9 (3 plans total)

**Key accomplishments:**

- Theme module with semantic style dataclass
- Terminal capability detection (TTY, NO_COLOR, FORCE_COLOR)
- Windows VT mode support via ctypes
- Colored output messages, device markers, bold prompts, and error headers

**Stats:**

- 13 Python modules (1 new: theme.py)
- 3,200+ lines of Python
- 2 phases, 3 plans
- 1 day (2026-01-29)

**Git range:** `feat(08-01)` → `docs(09)`

**What's next:** TUI redesign

---

## v2.0 Public Release (Shipped: 2026-01-27)

**Delivered:** Production-ready CLI with interactive menu, print safety checks, version detection, post-flash verification, and comprehensive documentation for public release.

**Phases completed:** 4-7 (12 plans total)

**Key accomplishments:**

- Interactive TUI menu with Unicode/ASCII box drawing and setup-first navigation
- Print safety checks via Moonraker API (blocks flash during active prints)
- Host vs MCU version comparison with outdated firmware warnings
- Post-flash verification polling (confirms device reappears as Klipper, not Katapult)
- Skip-menuconfig flag for power users with cached configs
- Device exclusion for non-flashable devices (Beacon probe support)
- Contextual error messages with numbered recovery steps
- Installation script (kflash command via ~/.local/bin symlink)
- Complete README documentation with Quick Start and CLI Reference

**Stats:**

- 12 Python modules (2 new: moonraker.py, tui.py)
- 2,909 lines of Python
- 4 phases, 12 plans
- 2 days (2026-01-26 → 2026-01-27)

**Git range:** `feat(04-01)` → `docs(07)`

**What's next:** Public release to Klipper community

---

## v1.0 MVP (Shipped: 2026-01-25)

**Delivered:** One-command Klipper firmware build and flash for USB-connected MCU boards with guaranteed service restart.

**Phases completed:** 1-3 (8 plans total)

**Key accomplishments:**

- Device registry with atomic JSON persistence (add/remove/list with serial patterns)
- USB discovery with pattern matching (scans /dev/serial/by-id/, extracts MCU types)
- Config caching with MCU validation (XDG paths, atomic writes, prevents wrong-board firmware)
- Build pipeline with streaming output (menuconfig TUI passthrough, make clean + make -j)
- Service lifecycle context manager (guaranteed Klipper restart on all code paths)
- Dual-method flash with fallback (Katapult first, automatic make flash fallback)

**Stats:**

- 10 Python modules created
- 1,695 lines of Python
- 3 phases, 8 plans, ~24 tasks
- 1 day from start to ship

**Git range:** `feat(01-01)` → `feat(03-02)`

**What's next:** v2.0 Public Release

---
