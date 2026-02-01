---
phase: quick
plan: "015"
subsystem: tui
tags: [tui, layout, device-panel]
completed: 2026-02-01
duration: ~3min
---

# Quick Task 015: Redesign TUI Menu Layout - Device Rows

**One-liner:** Restructured device rows to show name+firmware on line 1, mcu+serial on line 2, with aligned blocked devices and "Host Firmware:" label.

## Changes Made

### Task 1: Restructure render_device_rows() and fix host version label

**Commit:** ada51dc

**What changed in `render_device_rows()`:**
- **Registered devices:** Line 1 = `icon #N  name - flavor version  status_icon`, Line 2 = `(mcu)  serial` (6-space indent)
- **New/unregistered devices:** Line 1 shows "Unregistered Device" instead of raw USB filename; serial moves to line 2
- **Blocked devices:** Serial path indented with 6-space padding to align with mcu/serial lines of other devices
- **Exclusion warning:** Remains on line 3 for non-flashable registered devices

**What changed in `_host_version_line()`:**
- Label changed from "Host:" to "Host Firmware:"

## Files Modified

| File | Change |
|------|--------|
| kflash/screen.py | Rewrote render_device_rows(), updated _host_version_line() |

## Deviations from Plan

None - plan executed exactly as written.
