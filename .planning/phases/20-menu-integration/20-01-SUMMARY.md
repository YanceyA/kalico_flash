---
phase: 20-menu-integration
plan: 01
subsystem: tui
tags: [menu, config-device, integration]
depends_on: [19-01]
provides: [e-key-config-device-integration]
affects: []
tech_stack:
  added: []
  patterns: [device-selection-reuse, action-divider-framing]
key_files:
  created: []
  modified: [kflash/screen.py, kflash/tui.py]
decisions: []
metrics:
  duration: ~5 min
  completed: 2026-01-31
---

# Phase 20 Plan 01: Menu Integration Summary

Wire E key to launch device config screen from main menu with device selection and dividers.

## What Was Done

### Task 1: Reorder ACTIONS list and add E) Config Device
- Reordered ACTIONS to: Flash > Flash All > Add > Config Device > Remove > Settings > Quit
- Added `("E", "Config Device")` at position 4
- Removed `("D", "Refresh Devices")` from display panel (D key still functional in dispatch)
- Renamed "Config" label to "Settings" for clarity

### Task 2: Add E key dispatch handler in run_menu
- Added `elif key == "e":` branch following the pattern of other device-targeting actions
- Empty device_map check shows warning message and returns to menu
- Reuses `_prompt_device_number` for device selection (auto-selects single device)
- `render_action_divider()` printed before and after `_device_config_screen` call
- Countdown return timer after config screen exits
- Updated unknown key hint string from `F/A/R/D/C/B/Q` to `F/B/A/E/R/C/Q`

## Commits

| # | Hash | Description |
|---|------|-------------|
| 1 | 22fc5ca | feat(20-01): reorder ACTIONS list and add E) Config Device |
| 2 | cd18ad9 | feat(20-01): wire E key to device config screen in run_menu |

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- ACTIONS contains 7 entries in correct order with ("E", "Config Device") at position 4
- `elif key == "e":` handler exists in tui.py run_menu
- render_action_divider called before and after _device_config_screen
- Unknown key hint includes E
