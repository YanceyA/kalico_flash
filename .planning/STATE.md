# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-26)

**Core value:** One command to build and flash any registered board — no remembering serial paths, flash commands, or config locations.
**Current focus:** v2.0 Public Release — Phase 5 (Moonraker Integration)

## Current Position

Milestone: v2.0 Public Release
Phase: 4 of 4 complete (Foundation)
Plan: All 5 plans complete + 1 critical fix
Status: Phase 4 verified, ready for Phase 5
Last activity: 2026-01-26 — Completed Phase 4: Foundation (all success criteria verified)

Progress: [████░░░░░░] ~29% (16/55 requirements complete)

## v2.0 Roadmap Summary

| Phase | Name | Requirements | Status |
|-------|------|--------------|--------|
| 4 | Foundation | 16 | Complete ✓ |
| 5 | Moonraker Integration | 13 | Pending |
| 6 | User Experience | 14 | Pending |
| 7 | Release Polish | 12 | Pending |

**Total:** 55 requirements, 4 phases

## Phase 4 Completion Summary

**Goal:** Establish core infrastructure for power users and error handling

**Requirements Completed:**
- Skip Menuconfig: SKIP-01 to SKIP-05 (5) ✓
- Device Exclusion: EXCL-01 to EXCL-05 (5) ✓
- Error Messages: ERR-01 to ERR-06 (6) ✓

**Plans Executed:**
- 04-01: Error message framework (format_error, ERROR_TEMPLATES)
- 04-02: Device exclusion schema (flashable field)
- 04-03: Skip-menuconfig flag and CLI commands
- 04-04: Flash.py error integration (22 error_with_recovery calls)
- 04-05: Supporting modules error integration

**Critical Fix Applied:** commit b03e9cc — format_error() now preserves numbered list formatting

**Success Criteria:** All 5 verified ✓
1. ✓ Skip-menuconfig with cached config
2. ✓ Graceful fallback when no cached config
3. ✓ Device exclusion end-to-end
4. ✓ Numbered recovery steps display correctly
5. ✓ 80-column wrapping with context

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

### Tech Debt (from v1.0 audit)

- cmd_build() orphaned (no --build-only argparse flag)
- Builder class orphaned (convenience wrapper never used)
- DeviceNotFoundError, BuildError, FlashError defined but never raised

### Blockers

- None

## Next Phase Preview

**Phase 5: Moonraker Integration**

Goal: Users have safety checks and version awareness before flashing

Key features:
- Print status check (block flash during active print)
- Klipper version detection
- MCU firmware version comparison
- Graceful degradation when Moonraker unavailable

## Session Continuity

Last session: 2026-01-26T08:35:00Z
Stopped at: Phase 4 complete, verified
Resume file: None

---
*Last updated: 2026-01-26 after Phase 4 completion*
