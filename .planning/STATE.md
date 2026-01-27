# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-26)

**Core value:** One command to build and flash any registered board — no remembering serial paths, flash commands, or config locations.
**Current focus:** v2.0 Public Release — Complete

## Current Position

Milestone: v2.0 Public Release
Phase: 7 of 7 complete (Release Polish)
Plan: All 2 plans complete
Status: **Milestone complete, ready for audit**
Last activity: 2026-01-27 — Completed Phase 7: Release Polish (all success criteria verified)

Progress: [██████████] 100% (55/55 requirements complete)

## v2.0 Roadmap Summary

| Phase | Name | Requirements | Status |
|-------|------|--------------|--------|
| 4 | Foundation | 16 | Complete |
| 5 | Moonraker Integration | 13 | Complete |
| 6 | User Experience | 14 | Complete |
| 7 | Release Polish | 12 | Complete |

**Total:** 55 requirements, 4 phases — All complete

## Phase 7 Progress (Complete)

**Goal:** New users can install and learn the tool from documentation

**Plan 07-01: Install Script (Complete)**
- Created install.sh at repo root (90 lines)
- Symlink-based install to ~/.local/bin/kflash (XDG-compliant)
- Idempotent: mkdir -p, ln -sfn for safe re-runs
- --uninstall flag removes symlink cleanly
- PATH check with offer to add to ~/.bashrc
- Prerequisite warnings: Python 3.9+, ~/klipper, dialout group
- Fixed argparse prog name (flash.py -> kflash)
- Commits: 956e12c, 1cbe355, bf9221b

**Plan 07-02: README Documentation (Complete)**
- Rewrote README.md for public release (244 lines)
- Quick Start: 4-step guide (Clone → Install → Add → Flash)
- CLI Reference: Complete table with all 10 commands
- Moonraker Update Manager: Copy-paste ready config snippet
- Features section with real examples
- No troubleshooting section (per CONTEXT.md - inline errors sufficient)
- Commits: 1be3dae, 23ec73d

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

### Phase 6 Decisions

| Decision | Rationale | Plan |
|----------|-----------|------|
| Action handlers call existing flash.py commands | Hub-and-spoke: tui.py dispatches, flash.py has logic | 06-01 |
| Late imports in action handlers | Fast startup; tui.py imports flash.py functions only when needed | 06-01 |
| TTY guard in both tui.py and flash.py | Defense in depth: flash.py checks before routing, tui.py at entry | 06-01 |
| Settings is a stub | Settings UI comes in a later plan; menu slot reserved now | 06-01 |
| Numbered list for remove device | Better UX than raw key entry; user sees available devices | 06-02 |
| Generic _update_path() for settings | DRY: same logic for klipper_dir and katapult_dir | 06-02 |
| Nested try/except in menu dispatch | Inner catches action errors, outer catches Ctrl+C | 06-02 |
| _get_menu_choice() returns None on exhaustion | Caller decides exit behavior (main menu exits, submenus return) | 06-02 |
| Verify inside klipper_service_stopped() context | Device should reappear before Klipper restarts | 06-03 |
| Three-way verification result handling | Distinguishes flash failure from verification failure | 06-03 |
| Progress dots every 2 seconds | Balances user feedback with readable output | 06-03 |

### Phase 7 Decisions

| Decision | Rationale | Plan |
|----------|-----------|------|
| Symlink over wrapper script | Direct symlink is simpler; Python shebang handles execution | 07-01 |
| Warn-only prerequisite checks | Don't fail install on missing prereqs; user may be setting up | 07-01 |
| Don't remove PATH on uninstall | May affect other tools; only remove symlink | 07-01 |
| No troubleshooting section | Inline error messages from Phase 4 provide recovery steps | 07-02 |
| USER as GitHub placeholder | User replaces with their fork URL | 07-02 |
| Features with examples | Shows real commands and output, not abstract descriptions | 07-02 |

### Tech Debt (from v1.0 audit)

- cmd_build() orphaned (no --build-only argparse flag)
- Builder class orphaned (convenience wrapper never used)
- DeviceNotFoundError, BuildError, FlashError defined but never raised

### Blockers

- None

## Session Continuity

Last session: 2026-01-27T09:30:00Z
Stopped at: Phase 7 complete, milestone complete
Resume file: None

---
*Last updated: 2026-01-27 after Phase 7 completion — Milestone complete*
