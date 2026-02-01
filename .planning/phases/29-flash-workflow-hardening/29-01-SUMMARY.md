---
phase: 29-flash-workflow-hardening
plan: 01
subsystem: flash-safety
tags: [mcu-crosscheck, build-output, safety]
completed: 2026-02-01
duration: ~5min
dependency-graph:
  requires: [28-flash-all-preflight]
  provides: [mcu-crosscheck-before-flash, build-error-output-capture]
  affects: [30-cleanup]
tech-stack:
  added: []
  patterns: [usb-mcu-extraction-crosscheck, subprocess-output-capture]
key-files:
  created: []
  modified: [kflash/models.py, kflash/build.py, kflash/flash.py]
decisions:
  - id: D29-01
    decision: "MCU cross-check is best-effort -- skipped silently when extraction returns None"
    reason: "Not all USB device filenames contain extractable MCU info"
metrics:
  tasks: 2/2
  commits: 2
---

# Phase 29 Plan 01: MCU Cross-Check & Build Error Output Summary

MCU cross-check validates USB device identity against registry before flashing; build error output capture shows last 20 lines inline when Flash All builds fail.

## What Was Done

### Task 1: error_output fields and build output capture
- Added `error_output: Optional[str] = None` to `BuildResult` and `BatchDeviceResult` in models.py
- Modified `run_build()` in build.py to capture combined stdout+stderr on failure when `quiet=True`
- Captures output for make clean failures, make build failures, and timeout exceptions
- Caps at last 200 lines

### Task 2: MCU cross-check and build error display
- `cmd_flash`: After device resolution, calls `extract_mcu_from_serial()` on USB filename and warns+prompts if MCU doesn't match registry entry
- `cmd_flash_all`: Same check but skips device with warning instead of prompting
- Both functions skip check silently when extraction returns None
- Flash All summary now displays last 20 lines of build output inline for failed builds

## Commits

| Hash | Description |
|------|-------------|
| 6089c83 | feat(29-01): add error_output fields and build output capture |
| c38a264 | feat(29-01): MCU cross-check before flash and build error display |

## Deviations from Plan

None -- plan executed exactly as written.

## Next Phase Readiness

No blockers. Phase 29 plan 01 complete.
