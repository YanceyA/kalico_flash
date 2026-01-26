# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-26)

**Core value:** One command to build and flash any registered board — no remembering serial paths, flash commands, or config locations.
**Current focus:** v2.0 Public Release — Phase 5 (Moonraker Integration)

## Current Position

Milestone: v2.0 Public Release
Phase: 5 of 4 (Moonraker Integration)
Plan: 2 of 4 complete
Status: Phase 5 in progress
Last activity: 2026-01-27 — Completed 05-02-PLAN.md (Print safety and version integration)

Progress: [██████░░░░] ~38% (21/55 requirements addressed)

## v2.0 Roadmap Summary

| Phase | Name | Requirements | Status |
|-------|------|--------------|--------|
| 4 | Foundation | 16 | Complete |
| 5 | Moonraker Integration | 13 | In Progress (Plan 2/4 done) |
| 6 | User Experience | 14 | Pending |
| 7 | Release Polish | 12 | Pending |

**Total:** 55 requirements, 4 phases

## Phase 5 Progress

**Goal:** Users have safety checks and version awareness before flashing

**Plans:**
- 05-01: Moonraker API client module (Complete)
- 05-02: Print safety integration (Complete)
- 05-03: Version display integration (Pending)
- 05-04: Graceful degradation flow (Pending)

**Completed in 05-01:**
- Created moonraker.py with 4 API functions
- Added PrintStatus dataclass to models.py
- Implemented graceful degradation pattern (return None, not raise)

**Completed in 05-02:**
- Print safety check blocks flash during printing/paused
- Shows "Print in progress: filename (45%)" when blocked
- Moonraker unreachable prompts Y/N confirmation (default=No)
- Version display shows host and all MCU versions
- Target MCU marked with asterisk in version list
- Version mismatch warning (informational only)

## Accumulated Context

### Key Decisions (carried forward from v1.0)

All v1.0 decisions marked "Good" in PROJECT.md. Key patterns established:
- Hub-and-spoke architecture with dataclass contracts
- Context manager for service lifecycle (guaranteed restart)
- Late imports for fast CLI startup
- Atomic writes for registry and config files

### v2.0 Research Findings

- All features achievable with Python stdlib only
- New modules: moonraker.py (Phase 5), tui.py (Phase 6)
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
| Numbered recovery steps (1., 2., 3.) | Scannable, actionable, easier to follow in terminal | 04-04 |
| ERROR_TEMPLATES for service errors | Use pre-defined templates for service_stop_failed, service_start_failed | 04-05 |
| Inline format_error for config/flasher | Context varies per call site, inline is clearer | 04-05 |
| Split recovery text for wrapping | Preserve newlines in numbered lists when wrapping to 80 cols | Fix |

### Phase 5 Decisions

| Decision | Rationale | Plan |
|----------|-----------|------|
| Hardcoded localhost:7125 URL | Per CONTEXT.md: "no custom URL support - keep it simple" | 05-01 |
| Simple string comparison for versions | Informational only, never blocks flash | 05-01 |
| PrintStatus in models.py | Hub-and-spoke consistency - all dataclasses in models.py | 05-01 |
| MCU name normalization | "mcu" -> "main", "mcu nhk" -> "nhk" for clarity | 05-01 |
| Catch OSError in exception handling | Covers socket errors and low-level network failures | 05-01 |
| No --force flag for print blocking | Per CONTEXT.md: "no force-override for print safety" | 05-02 |
| Version check informational only | Per CONTEXT.md: "Version comparison is informational only - never blocks flash" | 05-02 |
| Target MCU marked with asterisk | User can identify which MCU is being flashed in version table | 05-02 |
| Moonraker unreachable default=No | Conservative default - user must explicitly opt to continue without safety checks | 05-02 |

### Tech Debt (from v1.0 audit)

- cmd_build() orphaned (no --build-only argparse flag)
- Builder class orphaned (convenience wrapper never used)
- DeviceNotFoundError, BuildError, FlashError defined but never raised

### Blockers

- None

## Session Continuity

Last session: 2026-01-27T10:40:00Z
Stopped at: Completed 05-02-PLAN.md
Resume file: None

---
*Last updated: 2026-01-27 after 05-02 completion*
