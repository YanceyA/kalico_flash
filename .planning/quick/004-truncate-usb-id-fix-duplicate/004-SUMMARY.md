# Quick Task 004: Truncate USB ID and Fix Duplicate Display

**One-liner:** Single-char ellipsis truncation for long USB IDs and deduplicated new-device rows in TUI

## Changes Made

### Task 1: Fix truncate_serial and remove duplicate USB ID for new devices
- **Commit:** 9564904
- **File:** `kflash/screen.py`

**What changed:**
1. `truncate_serial()` now uses Unicode ellipsis (U+2026) instead of `"..."`, saving 2 columns while keeping max_width=40
2. New/unregistered device names are truncated via `truncate_serial()` so labels fit the panel
3. Serial path suffix is skipped when it equals `row.name` (new devices where both are the filename)

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- `truncate_serial('usb-Klipper_stm32h723xx_29001A001151313531383332-if00')` returns 40-char string with ellipsis in middle
- New device rows show USB ID once (as truncated name), not twice
- Registered devices unaffected (name != serial_path, so serial still appended)
