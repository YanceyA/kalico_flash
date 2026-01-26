---
phase: 01-foundation-device-management
plan: 02
subsystem: cli
tags: [python, argparse, cli, wizard, interactive, registry]

# Dependency graph
requires:
  - 01-01 (errors.py, models.py, output.py, registry.py, discovery.py)
provides:
  - CLI entry point (flash.py) with argparse dispatch
  - --add-device interactive wizard for device registration
  - --remove-device command with confirmation
  - --list-devices stub (implemented in Plan 03)
  - --device flag definition for future flash workflow
affects: [01-03, 02-build-pipeline, 03-flash-orchestration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Thin CLI wrapper over library modules (ARCH-02)"
    - "Late imports in main() for fast startup"
    - "TTY check before interactive wizards"
    - "Retry loops with attempt limits for input validation"

key-files:
  created:
    - klipper-flash/flash.py
  modified: []

key-decisions:
  - "TTY check returns error for non-interactive stdin (supports SSH but not piped input)"
  - "Global config prompted only on first device registration (not every run)"
  - "Serial pattern auto-generated from device filename, overlap warning but not blocking"
  - "Flash method defaults to None (inherits global) when user selects 'katapult'"

patterns-established:
  - "All user I/O through Output Protocol methods (never bare input/print)"
  - "All data persistence through Registry class (never direct file writes)"
  - "sys.exit() only in CLI entry point, not library modules (ARCH-01)"
  - "Exit codes: 0=success, 1=user error, 3=unexpected, 130=interrupted"

# Metrics
duration: 4min
completed: 2026-01-25
---

# Phase 1 Plan 2: CLI Entry Point and Device Wizard Summary

**CLI entry point with argparse dispatch, interactive add-device wizard with USB scanning and MCU auto-detection, and remove-device command with confirmation prompt**

## Performance

- **Duration:** 4 min
- **Started:** 2026-01-25T18:10:00Z
- **Completed:** 2026-01-25T18:14:00Z
- **Tasks:** 2
- **Files created:** 1

## Accomplishments

- Created flash.py CLI entry point with argparse and mutually exclusive management commands
- Implemented 9-step interactive add-device wizard:
  1. USB serial device scanning
  2. Device selection with validation
  3. Global config on first run (klipper/katapult paths)
  4. Device key with duplicate/format validation
  5. Display name collection
  6. MCU auto-detection with override option
  7. Serial pattern generation with overlap warning
  8. Flash method selection
  9. Registry persistence
- Implemented remove-device command with confirmation prompt
- Stubbed list-devices for Plan 03

## Task Commits

Each task was committed atomically:

1. **Task 1: CLI scaffold with argparse and dispatch** - `71d3c08` (feat)
2. **Task 2: Add-device wizard with interactive flow** - `74dfd1b` (feat)

## Files Created/Modified

- `klipper-flash/flash.py` - CLI entry point with:
  - `build_parser()` - argparse with --device, --add-device, --list-devices, --remove-device
  - `main()` - dispatch with late imports, exception handling, exit codes
  - `cmd_add_device()` - 9-step interactive wizard
  - `cmd_remove_device()` - confirmation-based removal
  - `cmd_list_devices()` - stub for Plan 03

## Decisions Made

1. **TTY requirement:** Non-interactive stdin (piped input) rejected with clear error message pointing to SSH terminal
2. **Global config timing:** Only prompted during first device registration, not on every --add-device invocation
3. **Pattern overlap:** Warning issued but not blocking -- user may have legitimate reasons for overlapping patterns
4. **Default flash method storage:** When user selects "katapult" (the global default), store `None` to inherit from global config

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all verification tests passed on first execution.

## User Setup Required

None - no external service configuration required for CLI scaffold.

## Next Phase Readiness

- CLI entry point complete with dispatch structure
- add-device wizard fully implements device registration flow
- remove-device works with confirmation
- Ready for Plan 03 to implement --list-devices with table formatting
- Architecture verified: sys.exit only in flash.py, all I/O via Output Protocol, all persistence via Registry

---
*Phase: 01-foundation-device-management*
*Completed: 2026-01-25*
