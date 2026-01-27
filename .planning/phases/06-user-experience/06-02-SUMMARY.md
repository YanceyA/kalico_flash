# Phase 6 Plan 02: Menu Action Handlers and Settings Submenu Summary

**One-liner:** Numbered remove selection, settings submenu with path editing, and retry-based input validation for all TUI menus

---

## Metadata

- **Phase:** 06 (User Experience)
- **Plan:** 02
- **Subsystem:** CLI / TUI
- **Tags:** tui, menu-handlers, settings, input-validation, error-handling
- **Completed:** 2026-01-27
- **Duration:** ~3 minutes

### Dependency Graph

- **Requires:** 06-01 (TUI core with menu loop and box rendering)
- **Provides:** Full menu handler implementations, settings submenu, input retry logic
- **Affects:** 06-03 (flash verification can build on resilient menu loop)

### Tech Stack

- **Added:** None (stdlib only: os, sys)
- **Patterns:** Retry-based input validation, submenu loop, generic path updater

### Key Files

- **Modified:** kalico-flash/tui.py (227 -> 361 lines)

---

## What Was Built

### Improved Remove Device Handler

Replaced the raw text-prompt remove handler with a numbered device list:

1. Loads registry, enumerates devices as `1. key (name)`
2. Uses `_get_menu_choice()` with retry logic for selection
3. Passes selected device key to `cmd_remove_device()` (which handles confirmation)
4. Handles empty registry, cancellation, and invalid input gracefully

### Settings Submenu (`_settings_menu`)

Full settings submenu with its own box-drawn menu and loop:

- **Option 1:** Change Klipper directory -- prompts with current value as default, persists via `registry.save_global()`
- **Option 2:** Change Katapult directory -- same pattern
- **Option 3:** View current settings -- displays all three GlobalConfig fields
- **Option 0:** Back to main menu

Uses `_render_menu()` for consistent box drawing and `_get_menu_choice()` for validated input.

Helper functions:
- `_update_path(registry, out, field, label)` -- generic path updater that creates a new GlobalConfig with one field changed
- `_view_settings(registry, out)` -- displays current settings or "no config" message

### Input Validation (`_get_menu_choice`)

Replaced `_get_choice()` with `_get_menu_choice()` that provides:

- Validation against a list of valid choices
- Up to 3 retry attempts with "N attempts remaining" feedback
- `q` normalised to `"0"` (exit/back) for consistency
- `None` return on max attempts exceeded (caller decides behavior)
- EOFError handling (returns "0" gracefully)

Used in main menu, settings submenu, and remove device selection.

### Error-Resilient Action Dispatch

Main menu loop now wraps all handler calls in nested try/except:

- `KeyboardInterrupt` during an action: prints "Cancelled." and returns to menu
- `Exception` during an action: prints "Action failed: {error}" and returns to menu
- Outer `KeyboardInterrupt` (at menu prompt): exits cleanly with code 0

---

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 7e2be87 | feat(06-02): improve remove handler and add menu choice helper |
| 2 | 8839335 | feat(06-02): implement settings submenu with path editing |
| 3 | b89757f | refactor(06-02): finalize error handling and clean up module docstring |

---

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Numbered list for remove instead of raw key | Better UX: user sees available devices, picks by number |
| Generic `_update_path()` for settings | DRY: same logic for klipper_dir and katapult_dir updates |
| Skip save when path unchanged | Avoid unnecessary disk writes and misleading "updated" message |
| Settings submenu has its own loop | User can make multiple changes before returning to main menu |
| `_get_menu_choice()` returns None on exhaustion | Caller decides: main menu exits, submenus return silently |
| Nested try/except in dispatch | Inner catches action errors, outer catches menu-level Ctrl+C |

---

## Deviations from Plan

None -- plan executed exactly as written.

---

## Requirements Addressed

| Requirement | Status |
|-------------|--------|
| TUI-02: User selecting Add device completes wizard and returns to menu | Met (via _action_add_device) |
| TUI-02: User selecting List devices sees list and returns to menu | Met (via _action_list_devices) |
| TUI-02: User selecting Flash completes and returns to menu | Met (via _action_flash_device) |
| TUI-03: User selecting Remove sees numbered list and confirms | Met (via _action_remove_device) |
| TUI-04: Invalid input shows error and re-prompts (max 3 attempts) | Met (via _get_menu_choice) |
| TUI-07: Settings submenu with path options | Met (via _settings_menu) |

---

## Next Phase Readiness

Plan 06-02 provides complete menu handler functionality for:
- **06-03:** Flash verification and post-flash checks (last plan in phase)

No blockers for subsequent plans.

---

*Generated: 2026-01-27*
