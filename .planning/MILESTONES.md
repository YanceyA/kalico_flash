# Project Milestones: klipper-flash

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

## v2.0 Public Release (In Progress)

**Goal:** Prepare kalico-flash for release to the broader Klipper community with safety features, polish, and ease of installation.

**Started:** 2026-01-26

**Phases:**

| Phase | Name | Requirements |
|-------|------|--------------|
| 4 | Foundation | Skip menuconfig, device exclusion, error messages |
| 5 | Moonraker Integration | Print safety check, version detection |
| 6 | User Experience | TUI menu, post-flash verification |
| 7 | Release Polish | Installation script, README documentation |

**Key features:**
- Simple TUI menu for navigation
- Print status check before flash (prevent mid-print disasters)
- Post-flash verification (confirm device reappears)
- Skip menuconfig flag for power users
- Better error messages with recovery guidance
- Version mismatch detection (host vs MCU)
- Installation script (kflash command)
- README documentation for public users
- Device exclusion support (Beacon probe marked not flashable)

**Requirements:** 55 total across 9 categories

---
