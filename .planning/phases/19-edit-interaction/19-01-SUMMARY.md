# Phase 19 Plan 01: Device Config Screen Interaction Summary

**One-liner:** Collect-then-save device config screen with 5 edit types (text, validated text, cycle, toggle, menuconfig action)

## What Was Done

- Added `_save_device_edits()` helper that handles key rename (move config cache dir then atomic registry rewrite) and simple field updates separately
- Added `_device_config_screen()` with render-read-dispatch loop modeled on existing `_config_screen()`
- All 5 DEVICE_SETTINGS types implemented: text (name), text+validate (key), cycle (flash_method), toggle (flashable), action (menuconfig)
- Esc/B saves all pending changes atomically, Ctrl+C discards without saving
- Menuconfig uses `original_key` for config cache lookup (cache not renamed until save)
- All `input()` calls protected against KeyboardInterrupt/EOFError

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1+2 | 2823042 | feat(19-01): implement _device_config_screen with collect-then-save loop |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] ConfigManager constructor arg order**
- Plan specified `ConfigManager(gc.klipper_dir, original_key)` but actual signature is `ConfigManager(device_key, klipper_dir)`
- Fixed to match actual API

**2. [Rule 3 - Blocking] Menuconfig launch approach**
- Plan assumed `cm.run_menuconfig()` exists on ConfigManager; actual API uses standalone `run_menuconfig()` from build module
- Used `build.run_menuconfig()` with `ConfigManager` for cache load/save

## Decisions Made

- Menuconfig in device config screen loads cached config, runs menuconfig, saves back to cache if user saved -- lightweight standalone edit without full flash workflow

## Files Modified

- `kflash/tui.py` -- added `_save_device_edits()` and `_device_config_screen()` (~156 lines)

## Next Phase Readiness

Function is defined but not yet wired to any menu handler. Phase 20 or a subsequent plan will connect it to the main TUI dispatch.
