---
phase: q-006
plan: 01
subsystem: moonraker-version-lookup
tags: [moonraker, mcu-version, chip-type, bugfix]
dependency-graph:
  requires: []
  provides: [per-device-firmware-version]
  affects: [screen-tui-device-list]
tech-stack:
  added: []
  patterns: [chip-type-keyed-version-dict]
key-files:
  created: []
  modified: [kflash/moonraker.py, kflash/screen.py]
metrics:
  duration: ~3 min
  completed: 2026-01-30
---

# Quick Task 006: Fix MCU Version Query - Poll Actual Firmware

Chip-type keys (stm32h723xx, rp2040, stm32f411xe) added to version dict from mcu_constants.MCU; fallback to "main" removed from both moonraker.py and screen.py.

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | 8797650 | fix(q-006): per-device MCU version via chip-type keys, remove main fallback |

## What Changed

### kflash/moonraker.py
- `get_mcu_versions()`: After extracting name-keyed version, also reads `mcu_constants.MCU` from response and adds chip-type key (e.g., `"stm32h723xx"`) mapping to the same version string.
- `get_mcu_version_for_device()`: Removed lines 224-226 that fell back to `"main"` when no match found. Now returns `None`.

### kflash/screen.py
- `_lookup_version()`: Replaced `return mcu_versions.get("main")` with `return None`.

## Verification

On Pi, `get_mcu_versions()` returns:
```
{'main': 'v2026.01.00-0-g4a173af8', 'stm32h723xx': 'v2026.01.00-0-g4a173af8',
 'blackpill': '9f74c260', 'stm32f411xe': '9f74c260',
 'nhk': 'v2026.01.00-0-g4a173af8', 'rp2040': 'v2026.01.00-0-g4a173af8',
 'beacon': 'Beacon 2.1.0'}
```

Blackpill now shows `9f74c260` (its actual firmware hash) instead of main's `v2026.01.00-0-g4a173af8`.

## Deviations from Plan

None - plan executed exactly as written.
