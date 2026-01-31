# Quick Task 011: Restore Refresh Devices to Actions Panel

## Task
The "D" key handler for refreshing devices exists in tui.py but was missing from the ACTIONS list in screen.py, so it wasn't displayed in the actions panel.

## Tasks

### Task 1: Add D > Refresh Devices to ACTIONS list
- **File:** `kflash/screen.py` (ACTIONS list)
- **Change:** Insert `("D", "Refresh Devices")` so it appears at the top of the second column (position 5 in the 8-item list)
- **Commit:** `fix: restore Refresh Devices to actions panel`
