---
phase: 25
plan: 02
subsystem: tui
tags: [key-internalization, user-facing-output, device-config]
depends_on:
  requires: [25-01]
  provides: [key-free-user-output, simplified-config-screen]
  affects: [26, 27]
tech-stack:
  added: []
  patterns: [display-name-only-output]
key-files:
  created: []
  modified:
    - kflash/screen.py
    - kflash/tui.py
    - kflash/output.py
    - kflash/flash.py
decisions:
  - id: d25-02-01
    summary: "Keep device_key in context dicts and error templates unchanged"
    reason: "These are internal/debug data, not user-facing display"
  - id: d25-02-02
    summary: "Add device_name parameter to _remove_cached_config rather than passing registry"
    reason: "Simpler signature change, avoids threading registry through utility function"
metrics:
  duration: "8 minutes"
  completed: "2026-02-01"
---

# Phase 25 Plan 02: Key Internalization in User-Facing Output Summary

**One-liner:** Removed key edit from device config screen and replaced all user-facing entry.key/device_key with entry.name across flash.py, tui.py, and output.py.

## What Was Done

### Task 1: Remove key edit from DEVICE_SETTINGS and update config screen
- Removed `{"key": "key", "label": "Device key"}` from DEVICE_SETTINGS (5 -> 4 entries)
- Removed key edit handler (`elif setting["key"] == "key"` block) from config screen
- Removed key rename logic from `_save_device_edits` (was dead code after key edit removal)
- Updated valid input range from `("1".."5")` to `("1".."4")`
- Fixed MCU mismatch message in config screen to use `entry.name` instead of `original_key`

### Task 2: Replace entry.key with entry.name in flash.py
- All device display lines (DUP, BLK, REG, excluded, flashable) show `entry.name`
- Config phase messages use `entry.name` for loaded/cached/skipped messages
- Flash-all batch output: skip warnings, config ages, version lists all use names
- Remove/exclude/include confirmations show device name
- Added `device_name` parameter to `_remove_cached_config` for proper display
- Preserved all internal key usage (registry lookups, cache paths, context dicts)

### Task 3: Replace entry.key with entry.name in tui.py and output.py
- Flash failure and remove messages in TUI actions show device name
- Renamed `mcu_mismatch_choice` parameter from `device_key` to `device_name` across all three Output implementations (Protocol, CliOutput, NullOutput)
- Updated caller in flash.py add-device flow to pass `entry.name`

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 6d18681 | Remove key edit from device config screen |
| 2 | a61030c | Replace entry.key with entry.name in flash.py |
| 3 | 5092d30 | Replace entry.key with entry.name in tui.py and output.py |

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

- DEVICE_SETTINGS has 4 entries (no key edit)
- Zero user-facing output contains entry.key or device_key
- All remaining entry.key/device_key references are internal (registry, cache, context dicts)
- Config screen dispatches correctly on indices 1-4

## Next Phase Readiness

Phase 25 complete. All device keys are now invisible to users:
- Plan 01: Auto-generated keys in add-device wizard
- Plan 02: Key edit removed, all display uses names

Ready for phase 26 (if any remaining work) or phase 27.
