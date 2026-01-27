# Phase 6 Plan 01: TUI Core - Menu Loop and Box Rendering Summary

**One-liner:** Interactive TUI menu with Unicode/ASCII box drawing, numbered options, and flash.py entry point routing

---

## Metadata

- **Phase:** 06 (User Experience)
- **Plan:** 01
- **Subsystem:** CLI / TUI
- **Tags:** tui, menu, unicode, box-drawing, entry-point
- **Completed:** 2026-01-27
- **Duration:** ~4 minutes

### Dependency Graph

- **Requires:** None (Wave 1, no dependencies)
- **Provides:** tui.py module with run_menu(), menu rendering, unicode detection
- **Affects:** 06-02 (menu action wiring), 06-03 (flash verification)

### Tech Stack

- **Added:** None (stdlib only: os, sys)
- **Patterns:** Setup-first menu ordering, late imports for hub-and-spoke

### Key Files

- **Created:** kalico-flash/tui.py (226 lines)
- **Modified:** kalico-flash/flash.py (epilog, docstring, main() routing)

---

## What Was Built

### tui.py Module (New)

Created the foundational TUI module with these components:

1. **Unicode Detection** (`_supports_unicode()`): Inspects LANG and LC_ALL environment variables for UTF-8 indicators. Returns True for Unicode box-drawing, False for ASCII fallback.

2. **Box Character Sets**: Two constant dicts (UNICODE_BOX and ASCII_BOX) with top-left, top-right, bottom-left, bottom-right corners, horizontal, and vertical characters.

3. **Menu Rendering** (`_render_menu()`): Builds a box-drawn menu with centered title ("kalico-flash"), separator line, and numbered options. Calculates width dynamically from option labels.

4. **Main Menu Loop** (`run_menu()`):
   - TTY guard at entry (prints help message for non-TTY)
   - While-True loop: render menu, get input, dispatch to handler
   - Exit on "0", "q", "Q", or Ctrl+C (KeyboardInterrupt)
   - Returns 0 on all exit paths

5. **Action Handlers**: Five action functions that late-import from flash.py:
   - `_action_add_device()` -> `cmd_add_device()`
   - `_action_list_devices()` -> `cmd_list_devices()`
   - `_action_flash_device()` -> `cmd_flash()`
   - `_action_remove_device()` -> prompts for key, then `cmd_remove_device()`
   - `_action_settings()` -> placeholder (prints "Not implemented yet")

6. **Menu Order** (per CONTEXT.md): Add(1), List(2), Flash(3), Remove(4), Settings(5), Exit(0)

### flash.py Entry Point Changes

Modified `main()` to support three routing paths:

1. **Management commands** (--add-device, --list-devices, etc.): Unchanged
2. **Explicit --device KEY**: Routes to `cmd_flash()` directly
3. **No args + TTY**: Late-imports `run_menu()` from tui.py, launches interactive menu
4. **No args + non-TTY**: Prints help text via `parser.print_help()`, returns 0

Updated epilog from "interactive device selection" to "interactive menu" and added tui.py to module docstring.

---

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 28ba5ff | feat(06-01): create tui.py with menu rendering and unicode detection |
| 2 | 4922127 | feat(06-01): wire tui.py into flash.py entry point |

---

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Action handlers call existing flash.py commands | Hub-and-spoke pattern: tui.py dispatches, flash.py has the logic |
| Late imports in action handlers | Fast startup; tui.py only imports flash.py functions when needed |
| Remove device prompts for key inline | No device selection UI yet; simple prompt is sufficient for Plan 01 |
| Settings is a stub | Settings UI comes in a later plan; menu slot reserved now |
| TTY guard in both tui.py and flash.py | Defense in depth: flash.py checks before routing, tui.py checks at entry |

---

## Deviations from Plan

### Auto-added Improvements

**1. [Rule 2 - Missing Critical] Action handlers wired to real commands instead of stubs**

- **Found during:** Task 1
- **Issue:** Plan said "handlers will be stubs" but existing flash.py commands (cmd_add_device, cmd_list_devices, cmd_flash, cmd_remove_device) are already fully implemented. Stubbing them would make the menu non-functional when it could work immediately.
- **Fix:** Wired action handlers to import and call the existing flash.py command functions.
- **Files modified:** kalico-flash/tui.py
- **Commit:** 28ba5ff

---

## Requirements Addressed

| Requirement | Status |
|-------------|--------|
| User running kflash with no args sees numbered menu | Met |
| User can exit with 0, q, or Ctrl+C | Met |
| User in non-TTY environment sees help, not broken menu | Met |
| User on UTF-8 terminal sees Unicode box drawing | Met |
| User on legacy terminal sees ASCII box drawing | Met |

---

## Next Phase Readiness

Plan 06-01 provides the foundation for:
- **06-02**: Menu action wiring and refinement (actions are already functional)
- **06-03**: Flash verification and post-flash checks

No blockers for subsequent plans.

---

*Generated: 2026-01-27*
