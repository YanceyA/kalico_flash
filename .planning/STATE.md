# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-26)

**Core value:** One command to build and flash any registered board — no remembering serial paths, flash commands, or config locations.
**Current focus:** v2.0 Public Release — Phase 6 (User Experience)

## Current Position

Milestone: v2.0 Public Release
Phase: 5 of 4 complete (Moonraker Integration)
Plan: All 2 plans complete
Status: Phase 5 verified, ready for Phase 6
Last activity: 2026-01-27 — Completed Phase 5: Moonraker Integration (all success criteria verified)

Progress: [█████░░░░░] ~53% (29/55 requirements complete)

## v2.0 Roadmap Summary

| Phase | Name | Requirements | Status |
|-------|------|--------------|--------|
| 4 | Foundation | 16 | Complete ✓ |
| 5 | Moonraker Integration | 13 | Complete ✓ |
| 6 | User Experience | 14 | Pending |
| 7 | Release Polish | 12 | Pending |

**Total:** 55 requirements, 4 phases

## Phase 5 Completion Summary

**Goal:** Users have safety checks and version awareness before flashing

**Requirements Completed:**
- Safety Checks: SAFE-01 to SAFE-05 (5) ✓
- Version Detection: VER-01, VER-02, VER-03, VER-05, VER-06, VER-07 (6) ✓
- N/A: SAFE-06 (out of scope), VER-04 (informational only)

**Plans Executed:**
- 05-01: Moonraker API client (moonraker.py, PrintStatus dataclass)
- 05-02: Flash workflow integration (safety check, version display)

**Success Criteria:** All 5 verified ✓
1. ✓ Print blocking during active prints with filename and progress
2. ✓ Flash allowed when printer idle/complete/cancelled/error
3. ✓ Graceful degradation when Moonraker unreachable (warn + confirm)
4. ✓ Version display with host and MCU versions, mismatch warning
5. ✓ Multi-MCU support with target MCU marked

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
| MCU name normalization | "mcu" -> "main" for clarity, "mcu nhk" -> "nhk" for brevity | 05-01 |
| Graceful degradation pattern | All API functions return None on error, never raise | 05-01 |
| No --force flag for print blocking | Safety first - wait or cancel print, no override | 05-02 |
| Version check is informational only | Never blocks flash, just shows warning if outdated | 05-02 |
| Target MCU marked with asterisk | Clear indication which MCU is being flashed in multi-MCU setups | 05-02 |

### Tech Debt (from v1.0 audit)

- cmd_build() orphaned (no --build-only argparse flag)
- Builder class orphaned (convenience wrapper never used)
- DeviceNotFoundError, BuildError, FlashError defined but never raised

### Blockers

- None

## Next Phase Preview

**Phase 6: User Experience**

Goal: Interactive users have menu-driven workflow and flash verification

Key features:
- TUI menu with numbered options
- Post-flash device verification
- Unicode/ASCII terminal detection
- Non-TTY environment handling

## Session Continuity

Last session: 2026-01-27T11:00:00Z
Stopped at: Phase 5 complete, verified
Resume file: None

---
*Last updated: 2026-01-27 after Phase 5 completion*
