# Quick Task 013: MCU Mismatch Check After Menuconfig

**One-liner:** Non-blocking MCU mismatch warning after menuconfig save in add-device and config-device flows

## What Was Done

Added MCU validation checks after menuconfig saves in two locations:

1. **flash.py cmd_add_device** (line ~1964): After `save_cached_config()`, calls `validate_mcu()` and shows warning via `out.warning()` if MCU families don't match.

2. **tui.py config-device menuconfig action** (line ~876): After `save_cached_config()`, loads device entry from registry and calls `validate_mcu()`, printing warning with theme color if mismatch detected.

Both checks are wrapped in `try/except` to be non-blocking -- the real validation with proper error handling already exists in the flash workflow.

## Files Modified

| File | Change |
|------|--------|
| kflash/flash.py | MCU mismatch warning after menuconfig save in add-device |
| kflash/tui.py | MCU mismatch warning after menuconfig save in config-device |

## Commits

| Hash | Message |
|------|---------|
| 18d9ad8 | feat(quick-013): add MCU mismatch warning after menuconfig save |

## Deviations from Plan

None -- plan executed exactly as written.

## Verification

- Both modules import successfully on Pi
- Warning only triggers when `validate_mcu()` returns `is_match=False`
- Wrapped in try/except so failures are silent (non-blocking)

---
*Completed: 2026-01-31*
