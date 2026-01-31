# Phase 22 Plan 01: Core Detection Engine Summary

**One-liner:** Katapult bootloader detection with flashtool.py -r, serial polling, and USB sysfs reset recovery

## What Was Done

### Task 1: KatapultCheckResult dataclass and timing constants
- Added `KatapultCheckResult` dataclass to `kflash/models.py` with tri-state `has_katapult` (True/False/None)
- Added four timing constants to `kflash/flasher.py` matching Phase 21 research values
- Commit: `ab386dc`

### Task 2: Three helper functions
- `_resolve_usb_sysfs_path()`: Resolves /dev/serial/by-id/ symlink to sysfs USB authorized file
- `_usb_sysfs_reset()`: Toggles USB authorized flag (0 then 1) with sudo tee for device re-enumeration
- `_poll_for_serial_device()`: Polls /dev/serial/by-id/ with fnmatch glob pattern matching
- Commit: `bc3b1c1`

### Task 3: check_katapult() orchestrator
- Extracts hex serial identifier from device path for cross-mode matching
- Enters bootloader via `flashtool.py -r`, polls for `katapult_` device appearance
- Recovers device via USB sysfs reset if no Katapult found
- All exceptions caught internally -- never raises, always returns KatapultCheckResult
- Commit: `911ca46`

## Deviations from Plan

None -- plan executed exactly as written.

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Imports (fnmatch, os, re) at module top | Cleaner than inline imports, all are stdlib |
| sudo tee for sysfs writes | Standard pattern for MainsailOS passwordless sudo |

## Key Files

| File | Change |
|------|--------|
| `kflash/models.py` | Added KatapultCheckResult dataclass |
| `kflash/flasher.py` | Added 4 timing constants, 3 helpers, check_katapult() |

## Verification

- All functions importable locally and on Pi (192.168.50.50)
- KatapultCheckResult instantiates with tri-state correctly
- Timing constants match Phase 21 research values

## Next Phase Readiness

Phase 23 can wire `check_katapult()` into the TUI device config screen. The function accepts a `log` callback for progress display integration.
