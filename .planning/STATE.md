# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-26)

**Core value:** One command to build and flash any registered board — no remembering serial paths, flash commands, or config locations.
**Current focus:** v2.0 Public Release — Phase 4 (Foundation)

## Current Position

Milestone: v2.0 Public Release
Phase: 4 of 4 (Foundation)
Plan: 3 of 5 complete (04-01, 04-02, 04-03)
Status: In progress
Last activity: 2026-01-26 — Completed 04-03-PLAN.md (Skip-Menuconfig and Device Exclusion CLI)

Progress: [███░░░░░░░] ~15% (Plan 3 of ~20 total plans across phases)

## v2.0 Roadmap Summary

| Phase | Name | Requirements | Status |
|-------|------|--------------|--------|
| 4 | Foundation | 16 | In Progress (Plan 3/5) |
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

### Phase 4 Decisions

| Decision | Rationale | Plan |
|----------|-----------|------|
| format_error() for all error output | Consistent 80-column wrapped output with context and recovery | 04-01 |
| ERROR_TEMPLATES dict | Centralized error messages for consistency | 04-01 |
| ConfigMismatchError exception | Distinguish MCU mismatch from generic ConfigError | 04-01 |
| ExcludedDeviceError exception | Clear error type for excluded device attempts | 04-01 |
| flashable field defaults to True | Backward compatibility - existing devices remain flashable | 04-02 |
| flashable at END of DeviceEntry | Dataclass field ordering (non-default after default) | 04-02 |
| .get("flashable", True) in load() | Schema evolution pattern for backward compatibility | 04-02 |
| Always persist flashable in JSON | Consistency and debuggability | 04-02 |
| skip_menuconfig warns if no cache | User-friendly fallback - warn and launch menuconfig anyway | 04-03 |
| MCU validation always runs | Safety check even when skipping menuconfig | 04-03 |
| Excluded devices shown but not selectable | Users see excluded devices with [excluded] marker in interactive mode | 04-03 |
| Add-device asks about flashable | Registration wizard includes flashable question (default: True) | 04-03 |

### Tech Debt (from v1.0 audit)

- cmd_build() orphaned (no --build-only argparse flag)
- Builder class orphaned (convenience wrapper never used)
- DeviceNotFoundError, BuildError, FlashError defined but never raised

### Todos

- Plan 04: Additional CLI polish or integration tests
- Plan 05: Error message integration across all modules

### Blockers

- None

## Session Continuity

Last session: 2026-01-26T07:38:00Z
Stopped at: Completed 04-03-PLAN.md
Resume file: None

---
*Last updated: 2026-01-26 after 04-03-PLAN.md completion*
