# Quick Task 010: Config Device — Prompt to Add Unregistered Device

## Task
When user selects "Config Device" (E) and picks an unregistered (new) device, prompt them to add it instead of silently returning.

## Tasks

### Task 1: Add unregistered device check to E handler
- **File:** `kflash/tui.py` (lines 545-562, the `elif key == "e":` block)
- **Change:** After `_prompt_device_number` returns a key, check if the selected device row has `group == "new"`. If so, prompt "Device not registered. Add it now? (y/n):" — if yes, call `_action_add_device` with the device row; if no, return to main menu with "Config: cancelled" status.
- **Commit:** `fix: prompt to add unregistered device in config menu`
