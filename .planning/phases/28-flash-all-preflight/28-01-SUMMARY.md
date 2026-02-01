# Phase 28 Plan 01: Flash All Preflight Safety Summary

**One-liner:** Preflight env validation, Moonraker safety prompt, and duplicate USB path guard for cmd_flash_all()

## What Was Done

### Task 1: Add preflight and Moonraker check before batch loop
- Added `_preflight_flash()` call after global config load, before Stage 1
- Added Moonraker unreachable confirmation prompt matching cmd_flash() pattern
- Added print-in-progress block with `error_with_recovery()` for consistent UX
- Removed duplicate Stage 4 print status check (lines 1191-1197)

### Task 2: Add duplicate USB path tracking in flash loop
- Initialized `used_paths: set[str]` before the flash loop
- Added `os.path.realpath()` check after `match_device()` resolves USB device
- Devices sharing a resolved path with a prior device are skipped with warning

## Commits

| Commit | Description |
|--------|-------------|
| 35f5a22 | feat(28-01): add preflight checks and duplicate path guard to Flash All |

## Deviations from Plan

None - plan executed exactly as written.

## Key Files

| File | Change |
|------|--------|
| kflash/flash.py | +41/-8 lines: preflight, Moonraker check, duplicate path guard |

## Verification

- `_preflight_flash` called once in cmd_flash_all() before batch loop
- `get_print_status()` called once at preflight, removed from Stage 4
- `used_paths` initialized and checked in flash loop
- `os.path.realpath` used for path comparison
- Python syntax check passes
