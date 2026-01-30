---
phase: quick-005
plan: 01
subsystem: tui
tags: [tui, add-device, ux-consistency]
completed: 2026-01-30
duration: ~3 min
tech-stack:
  patterns: [device-number-prompt, pre-selected-device-passthrough]
key-files:
  modified:
    - kflash/flash.py
    - kflash/tui.py
decisions:
  - id: q005-1
    description: "Filter add-device prompt to group=='new' devices only"
    rationale: "Only unregistered devices make sense for add action"
---

# Quick Task 005: Add Device Prompt Like Remove Summary

**One-liner:** TUI add-device now prompts "Device #:" filtered to new devices, matching remove/flash UX pattern.

## What Was Done

### Task 1: Refactor cmd_add_device to accept optional pre-selected device
- **Commit:** `4125beb`
- Added `selected_device=None` parameter to `cmd_add_device()`
- When provided, skips discovery scan, device listing, and selection prompt
- TUI path still scans USB to check for existing registry match
- CLI `--add-device` path completely unchanged

### Task 2: Update TUI add-device action to use Device # prompt
- **Commit:** `e6d4550`
- Created `_prompt_new_device_number()` filtering `device_map` to `group=="new"` rows only
- Auto-selects when single new device available (matches existing pattern)
- Updated `_action_add_device()` to accept optional `device_row` parameter
- Finds matching `DiscoveredDevice` via USB scan and serial_path comparison
- TUI `a` key block now uses prompt flow instead of direct wizard call

## Deviations from Plan

None - plan executed exactly as written.

## Verification

1. TUI: Press 'a' -> shows "Device #:" prompt (no discovery list)
2. TUI: Press 'a' with no new devices -> shows "No new devices to add" warning
3. CLI: `--add-device` still shows full discovery list (unchanged)
4. Registration wizard runs after device selection
