# Project Milestones: kalico-flash

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
