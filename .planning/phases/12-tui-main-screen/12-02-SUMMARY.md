# Phase 12 Plan 02: TUI Interactive Loop Summary

**One-liner:** Panel-based run_menu with single keypress dispatch, device number prompting, and post-action screen refresh replacing old numbered menu.

## Completed Tasks

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Rewrite tui.py with panel-based loop and single keypress input | 1bf6a7f | kflash/tui.py |
| 2 | Verify full interactive flow on Pi + fix actions panel bug | ab9f08f | kflash/screen.py |

## What Was Built

- **_getch()**: Cross-platform single keypress reader (Windows msvcrt / Unix termios)
- **_build_screen_state()**: Aggregates registry, USB scan, Moonraker versions into ScreenState
- **_prompt_device_number()**: Device number input with auto-select for single device
- **run_menu()**: Panel-based main loop with F/A/R/D/C/B/Q dispatch and status updates
- **Action handlers**: Return (message, level) tuples for status panel feedback

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed actions panel rendering wrong first character**

- **Found during:** Task 2 (Pi verification)
- **Issue:** render_actions_panel in screen.py replaced label's first char with key letter, producing "Blash All" and "Defresh Devices"
- **Fix:** Changed to pass plain styled label text since render_two_column already formats "K > Label"
- **Files modified:** kflash/screen.py
- **Commit:** ab9f08f

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Ctrl+C in raw mode detected as \x03 | _getch uses tty.setraw which doesn't translate signals |
| Auto-select single device for F/R actions | Reduces friction when only one device exists |
| Echo pressed key before device prompt | Visual feedback that keypress was received |

## Verification

- All kflash imports succeed on Pi (Python 3.11.2)
- Panel screen renders correctly with live device data (Octopus Pro connected, RP2040 new, Beacon blocked)
- `--help` and `--list-devices` backward compatibility confirmed
- Actions panel shows correct labels after bug fix
