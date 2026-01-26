# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-26)

**Core value:** One command to build and flash any registered board — no remembering serial paths, flash commands, or config locations.
**Current focus:** v2.0 Public Release — Phase 4 (Foundation)

## Current Position

Milestone: v2.0 Public Release
Phase: 4 - Foundation
Plan: Not started
Status: Roadmap created, ready for Phase 4 planning
Last activity: 2026-01-26 — Roadmap created

Progress: [░░░░░░░░░░] 0%

## v2.0 Roadmap Summary

| Phase | Name | Requirements | Status |
|-------|------|--------------|--------|
| 4 | Foundation | 16 | Pending |
| 5 | Moonraker Integration | 13 | Pending |
| 6 | User Experience | 14 | Pending |
| 7 | Release Polish | 12 | Pending |

**Total:** 55 requirements, 4 phases

## Phase 4 Scope

**Goal:** Establish core infrastructure for power users and error handling

**Requirements:**
- Skip Menuconfig: SKIP-01 to SKIP-05 (5)
- Device Exclusion: EXCL-01 to EXCL-05 (5)
- Error Messages: ERR-01 to ERR-06 (6)

**New modules:** messages.py
**Modified modules:** flash.py, registry.py, discovery.py, models.py

## Accumulated Context

### Key Decisions (carried forward from v1.0)

All v1.0 decisions marked "Good" in PROJECT.md. Key patterns established:
- Hub-and-spoke architecture with dataclass contracts
- Context manager for service lifecycle (guaranteed restart)
- Late imports for fast CLI startup
- Atomic writes for registry and config files

### v2.0 Research Findings

- All features achievable with Python stdlib only
- New modules: moonraker.py (Phase 5), tui.py (Phase 6), messages.py (Phase 4)
- Registry schema adds flashable flag for device exclusion
- Graceful degradation philosophy: warn but don't block on informational failures

### Tech Debt (from v1.0 audit)

- cmd_build() orphaned (no --build-only argparse flag)
- Builder class orphaned (convenience wrapper never used)
- DeviceNotFoundError, BuildError, FlashError defined but never raised

### Todos

- None yet (Phase 4 planning not started)

### Blockers

- None

---
*Last updated: 2026-01-26 after roadmap creation*
