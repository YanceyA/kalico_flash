# Phase 27 Plan 02: Error Recovery Messages Summary

**One-liner:** Updated all error recovery templates to reference TUI action names instead of key shortcuts or CLI flags.

## What Was Done

- Audited all 13 entries in ERROR_TEMPLATES in `kflash/errors.py`
- Updated 5 templates with CLI/key-shortcut references to use TUI action names
- Kept manual terminal diagnostic commands unchanged (appropriate for troubleshooting)

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Audit and update error recovery templates | 43ade37 | kflash/errors.py |

## Changes by Template

| Template | Before | After |
|----------|--------|-------|
| device_not_registered | "Press D", "Press A" | "Add Device from the main menu", "main menu device list" |
| device_not_connected | "press A to re-register" | "use Add Device from the main menu to re-register" |
| mcu_mismatch | "Re-run menuconfig", "update device registration" | "Use Config Device from the main menu" (x2) |
| printer_busy | "re-run flash command" | "use Flash Device from the main menu" |
| device_excluded | "Press D to view all devices" | "Use Config Device from the main menu to manage device exclusion settings" |

## Templates Left Unchanged (Correct As-Is)

build_failed, menuconfig_failed, service_stop_failed, service_start_failed, flash_failed, verification_timeout, verification_wrong_prefix, katapult_not_found, moonraker_unavailable -- all use manual terminal commands for diagnostics, which is appropriate.

## Deviations from Plan

None -- plan executed exactly as written.

## Verification

- Zero matches for `Press [A-Z]` in errors.py
- Zero matches for `re-run` in errors.py
- Zero matches for CLI flags (`--device`, `--add-device`, etc.)
- Confirmed `main menu` appears in 5 updated templates
- Confirmed `Config Device` appears in mcu_mismatch and device_excluded
- Confirmed `Add Device` appears in device_not_registered and device_not_connected
- One `--version` match is a terminal command argument (arm-none-eabi-gcc), not a CLI flag

## Duration

~2 minutes
