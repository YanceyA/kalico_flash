---
phase: 13-config-screen-settings
plan: 01
subsystem: tui-settings
tags: [tui, config, settings, registry, panels]
depends_on:
  requires: [11-panel-renderer, 12-tui-main-screen]
  provides: [config-screen, global-settings-persistence]
  affects: [13-02-countdown-timer, 14-flash-all]
tech-stack:
  added: []
  patterns: [dataclasses-replace-for-immutable-updates, setting-type-dispatch]
key-files:
  created: []
  modified: [kflash/models.py, kflash/registry.py, kflash/screen.py, kflash/tui.py]
decisions:
  - id: 13-01-01
    decision: "Use dataclasses.replace() for GlobalConfig updates instead of manual kwargs reconstruction"
    rationale: "Cleaner, preserves all fields automatically, no risk of forgetting new fields"
  - id: 13-01-02
    decision: "Flat numbered settings list with type dispatch (toggle/numeric/path)"
    rationale: "Context specifies no grouping/tabs; type determines edit behavior"
metrics:
  duration: "3 min"
  completed: "2026-01-29"
---

# Phase 13 Plan 01: Config Screen & Settings Summary

**One-liner:** Panel-based config screen with 6 editable settings (toggle/numeric/path) persisted in registry JSON via dataclasses.replace pattern.

## What Was Done

### Task 1: Extend GlobalConfig and registry serialization
- Added 4 new fields to `GlobalConfig`: `skip_menuconfig` (bool), `stagger_delay` (float), `return_delay` (float), `config_cache_dir` (str)
- Registry `load()` uses `.get()` with defaults for backward compatibility with old JSON files
- Registry `save()` serializes all new fields to the `"global"` section

### Task 2: Config screen rendering and interactive loop
- Added `SETTINGS` constant and `render_config_screen()` to `screen.py` using existing panel primitives
- Replaced old `_settings_menu` with new `_config_screen` in `tui.py`
- Toggle settings flip immediately on keypress; numeric/path settings prompt with `input()`
- All changes persist immediately via `registry.save_global()` using `dataclasses.replace()`
- C key opens config from main menu; Esc/B returns

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| 5a85405 | feat | Extend GlobalConfig with 4 new settings fields + registry serialization |
| 75fb868 | feat | Add config screen with 6 editable settings, replace old settings menu |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Old settings functions used manual kwargs for GlobalConfig**
- **Found during:** Task 2
- **Issue:** `_update_path`, `_toggle_flash_fallback` manually listed GlobalConfig fields in kwargs dict, missing new fields
- **Fix:** Replaced entire old settings menu with new `_config_screen` using `dataclasses.replace()` which preserves all fields
- **Files modified:** kflash/tui.py

## Verification

- GlobalConfig loads with correct defaults for all 4 new fields
- Registry round-trip preserves all new fields in JSON
- Config screen renders 6 numbered settings with correct value formatting
- `_config_screen` imports and wires correctly from main menu C key dispatch

## Next Phase Readiness

Ready for 13-02 (countdown timer). The `return_delay` setting is now available in GlobalConfig for the countdown feature.
