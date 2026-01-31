# Quick Task 010: Summary

## What Changed
Modified `kflash/tui.py` — the "E" (Config Device) action handler.

When a user selects an unregistered ("new") device for config, instead of silently returning to the main menu, it now:
1. Prompts: "Device not registered. Add it now? (y/n):"
2. If yes → runs the add-device wizard (`_action_add_device`) with the selected device pre-filled
3. If no → returns to main menu with "Config: cancelled" status

## File Changed
- `kflash/tui.py` — `elif key == "e":` block (~line 548)
