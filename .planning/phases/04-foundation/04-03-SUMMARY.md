---
phase: 04-foundation
plan: 03
subsystem: cli
tags: [argparse, skip-menuconfig, device-exclusion, cli-flags]

# Dependency graph
requires:
  - phase: 04-01
    provides: format_error(), error_with_recovery(), ExcludedDeviceError
  - phase: 04-02
    provides: DeviceEntry.flashable field, Registry.set_flashable()
provides:
  - -s/--skip-menuconfig flag for bypassing menuconfig with cached config
  - -d short alias for --device flag
  - --exclude-device and --include-device CLI commands
  - Excluded device filtering in interactive selection
  - Error recovery guidance for excluded device attempts
affects: [04-04 (list-devices UX), 05-xx (Moonraker integration), 06-xx (UX polish)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CLI flag patterns: short alias + long form with consistent naming"
    - "Interactive selection filtering: separate flashable vs excluded for display"

key-files:
  created: []
  modified:
    - kalico-flash/flash.py
    - kalico-flash/discovery.py

key-decisions:
  - "skip_menuconfig warns and proceeds to menuconfig if no cached config exists"
  - "MCU validation always runs even with skip_menuconfig flag"
  - "Excluded devices shown in interactive mode but not selectable"
  - "Add-device wizard asks about flashable status at registration time"

patterns-established:
  - "Exclusion filtering: filter at selection time, not at discovery time"
  - "Recovery guidance: use error_with_recovery() for actionable error messages"

# Metrics
duration: 8min
completed: 2026-01-26
---

# Phase 04 Plan 03: Skip-Menuconfig and Device Exclusion CLI Summary

**-s flag skips menuconfig when cached config exists; --exclude-device/--include-device control flashable status with filtering in interactive selection**

## Performance

- **Duration:** 8 min
- **Started:** 2026-01-26T07:30:00Z
- **Completed:** 2026-01-26T07:38:00Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- Added -s/--skip-menuconfig flag that skips menuconfig when cached config exists
- Added -d short alias for --device flag for power users
- Implemented cmd_exclude_device() and cmd_include_device() for managing flashable status
- Updated cmd_list_devices() to show [excluded] marker on excluded devices
- Updated cmd_flash() interactive mode to filter excluded devices from selection
- Added flashable check to explicit --device path with recovery guidance
- Updated cmd_add_device() wizard to ask if device is flashable

## Task Commits

Each task was committed atomically:

1. **Task 1: Add CLI flags for skip-menuconfig and device exclusion** - `e45f743` (feat)
2. **Task 2: Implement skip-menuconfig logic in cmd_flash()** - `5e32d2c` (feat)
3. **Task 3: Implement device exclusion commands and filtering** - `6de47e7` (feat)

## Files Created/Modified
- `kalico-flash/flash.py` - Added CLI flags, skip-menuconfig logic, exclusion commands, filtering
- `kalico-flash/discovery.py` - Updated docstring for find_registered_devices()

## Decisions Made
- When -s flag is used without a cached config, warn and proceed to menuconfig anyway (user-friendly fallback)
- MCU validation always runs even when skipping menuconfig (safety check)
- Excluded devices are shown in interactive selection with [excluded] marker but cannot be selected
- Explicit --device on excluded device shows error with recovery guidance using error_with_recovery()
- Add-device wizard defaults to flashable=True (most devices are flashable)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Skip-menuconfig and device exclusion features complete
- Ready for Phase 04-04 (additional CLI polish) or Phase 05 (Moonraker integration)
- All error paths use new error framework from 04-01

---
*Phase: 04-foundation*
*Completed: 2026-01-26*
