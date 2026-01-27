---
phase: 06-user-experience
plan: 03
subsystem: ui
tags: [polling, verification, post-flash, tui, error-recovery]

# Dependency graph
requires:
  - phase: 06-user-experience (plan 01)
    provides: tui.py module with menu loop and action handlers
  - phase: 06-user-experience (plan 02)
    provides: menu handlers and settings submenu
  - phase: 04-foundation
    provides: error templates, format_error(), hub-and-spoke architecture
provides:
  - wait_for_device() polling function for post-flash verification
  - verification_timeout and verification_wrong_prefix error templates
  - Integrated verification step in flash workflow (Phase 4 of cmd_flash)
affects: [07-release-polish]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Post-flash device polling with progress dots (2s interval)"
    - "Three-way verification result: success+verified, success+unverified, flash-failed"
    - "Verification inside context manager (Klipper stays stopped during wait)"

key-files:
  modified:
    - kalico-flash/tui.py
    - kalico-flash/errors.py
    - kalico-flash/flash.py

key-decisions:
  - "Verify inside klipper_service_stopped() context - device should reappear before Klipper restarts"
  - "Three-way result handling distinguishes flash failure from verification failure"
  - "Progress dots every 2 seconds for user feedback during 30s polling window"

patterns-established:
  - "Post-operation verification: poll for expected state after destructive operation"
  - "Error template selection based on failure mode (timeout vs wrong prefix)"

# Metrics
duration: 6min
completed: 2026-01-27
---

# Phase 6 Plan 3: Flash Verification Summary

**Post-flash device verification with 30s polling, Klipper/katapult prefix detection, and recovery guidance on failure**

## Performance

- **Duration:** 6 min
- **Started:** 2026-01-27T07:33:54Z
- **Completed:** 2026-01-27T07:40:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Added wait_for_device() to tui.py with progress dots, pattern matching, and prefix validation
- Added verification_timeout and verification_wrong_prefix error templates with actionable recovery steps
- Integrated verification into cmd_flash() Phase 4, running inside klipper_service_stopped() context manager

## Task Commits

Each task was committed atomically:

1. **Task 1: Add wait_for_device() polling function to tui.py** - `46daed4` (feat)
2. **Task 2: Add verification error templates to errors.py** - `60f6c59` (feat)
3. **Task 3: Integrate verification into flash.py cmd_flash()** - `bca06bb` (feat)

## Files Created/Modified
- `kalico-flash/tui.py` - Added wait_for_device() public function (70 lines) with polling, progress dots, prefix checking
- `kalico-flash/errors.py` - Added verification_timeout and verification_wrong_prefix error templates
- `kalico-flash/flash.py` - Added wait_for_device import, verification inside context manager, three-way result handling

## Decisions Made
- **Verification inside context manager:** Device should reappear before Klipper restarts, so verification polls while Klipper service is still stopped. This avoids Klipper grabbing the serial port before we can check the device state.
- **Three-way result handling:** Distinguishes between (1) flash succeeded + device verified, (2) flash succeeded + verification failed, and (3) flash itself failed. Each path shows appropriate error templates and recovery steps.
- **Progress dots every 2 seconds:** Balances user feedback with readable output -- not too fast (noisy) or too slow (appears frozen).
- **Wrong prefix detection:** If device reappears as katapult_ instead of Klipper_, it means flash failed and device fell back to bootloader. Specific guidance helps the user retry.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 6 (User Experience) is fully complete: TUI core, menu handlers, settings, and flash verification
- All 14 Phase 6 requirements addressed across 3 plans
- Ready for Phase 7 (Release Polish)

---
*Phase: 06-user-experience*
*Completed: 2026-01-27*
