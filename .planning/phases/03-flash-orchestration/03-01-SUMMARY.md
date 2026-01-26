---
phase: 03-flash-orchestration
plan: 01
subsystem: flash-service
tags: [service-lifecycle, flash-operations, klipper, katapult, subprocess]

# Dependency graph
requires:
  - phase: 01-foundation-device-management
    plan: 02
    provides: DiscoveryError for device verification
  - phase: 02-build-config-pipeline
    plan: 02
    provides: BuildResult dataclass pattern
provides:
  - KlipperServiceManager context manager with guaranteed restart
  - FlashManager with dual-method flash (Katapult + make flash fallback)
  - ServiceError, FlashError exception types
  - FlashResult dataclass for flash outcomes
affects: [03-flash-orchestration/02, 03-flash-orchestration/03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Context manager with finally-block guarantee for service restart"
    - "Dual-method fallback: try primary, fall back to secondary on failure"
    - "Timeout-protected subprocess calls with error capture"

key-files:
  created:
    - klipper-flash/service.py
    - klipper-flash/flasher.py
  modified:
    - klipper-flash/errors.py
    - klipper-flash/models.py

key-decisions:
  - "_start_klipper warns but doesn't raise (safe for finally block)"
  - "Katapult failure message shown before attempting make flash fallback"
  - "Flash timeout applies per-method, not total (each method gets full timeout)"
  - "verify_device_path raises DiscoveryError for pre-flash device check"

patterns-established:
  - "Service lifecycle: context manager with stop-on-enter, restart-on-exit"
  - "Flash strategy: Katapult-first with automatic make flash fallback"
  - "FlashResult captures method used, timing, and error details"

# Metrics
duration: 4min
completed: 2026-01-25
---

# Phase 03 Plan 01: Service & Flasher Core Summary

**Context manager for guaranteed Klipper restart plus dual-method flash with Katapult-first fallback**

## Performance

- **Duration:** 4 min
- **Started:** 2026-01-25T10:06:23Z
- **Completed:** 2026-01-25T10:10:30Z
- **Tasks:** 3
- **Files created:** 2
- **Files modified:** 2

## Accomplishments

- ServiceError and FlashError exception types added to errors.py
- FlashResult dataclass added to models.py with success, method, elapsed_seconds, error_message
- service.py with klipper_service_stopped context manager
- verify_passwordless_sudo() for sudo -n true check
- Guaranteed Klipper restart in finally block (even on Ctrl+C or exception)
- flasher.py with dual-method flash_device()
- _try_katapult_flash() calling flashtool.py with timeout
- _try_make_flash() calling make FLASH_DEVICE with timeout
- verify_device_path() for pre-flash device existence check
- TIMEOUT_SERVICE=30 and TIMEOUT_FLASH=60 constants

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend errors.py and models.py** - `49bedb3` (feat)
   - Added ServiceError, FlashError classes
   - Added FlashResult dataclass

2. **Task 2: Create service.py** - `a83a783` (feat)
   - klipper_service_stopped context manager
   - verify_passwordless_sudo function
   - _stop_klipper (raises on failure)
   - _start_klipper (warns, doesn't raise)

3. **Task 3: Create flasher.py** - `07d46cf` (feat)
   - flash_device with dual-method logic
   - _try_katapult_flash with timeout
   - _try_make_flash with timeout
   - verify_device_path with DiscoveryError

## Files Created/Modified

| File | Lines | Purpose |
|------|-------|---------|
| klipper-flash/service.py | 110 | Klipper service lifecycle management |
| klipper-flash/flasher.py | 185 | Dual-method flash operations |
| klipper-flash/errors.py | +8 | ServiceError, FlashError classes |
| klipper-flash/models.py | +9 | FlashResult dataclass |

## Key Links Established

| From | To | Via |
|------|-----|-----|
| service.py | subprocess | systemctl stop/start klipper |
| flasher.py | katapult/scripts/flashtool.py | subprocess call |
| flasher.py | make flash | subprocess with FLASH_DEVICE env |
| flasher.py | errors.py | DiscoveryError for missing device |

## Decisions Made

- **_start_klipper warns but doesn't raise:** Ensures original exception isn't masked by raising in finally
- **Katapult failure message before fallback:** User sees why primary method failed
- **Timeout per-method:** Each flash method gets its own timeout (not shared)
- **verify_device_path raises DiscoveryError:** Consistent with existing error hierarchy

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all verifications passed on first run.

## Module Exports Summary

**service.py exports:**
- `klipper_service_stopped` - Context manager
- `verify_passwordless_sudo` - Bool function
- `TIMEOUT_SERVICE` - Constant (30s)

**flasher.py exports:**
- `flash_device` - Main flash function
- `verify_device_path` - Pre-flash check
- `TIMEOUT_FLASH` - Constant (60s)

**errors.py adds:**
- `ServiceError` - Service lifecycle errors
- `FlashError` - Flash operation errors

**models.py adds:**
- `FlashResult` - Flash operation result dataclass

## Next Phase Readiness

- Service lifecycle manager ready for integration
- Flash methods ready with fallback logic
- Error types and result models in place
- Ready for Plan 02: Wire flash into CLI with safety checks

---
*Phase: 03-flash-orchestration*
*Completed: 2026-01-25*
