# Roadmap - v2.1 TUI Color Theme

## Overview

| Phase | Name | Requirements | Status |
|-------|------|--------------|--------|
| 8 | Theme Infrastructure | THEME-01 to THEME-06 | Complete |
| 9 | Apply Theming | OUT-01-07, TUI-01-03, ERR-01 | In Progress |

---

## Phase 8: Theme Infrastructure

**Goal:** Create theme.py module with semantic styling, detection, and utilities

**Requirements:** THEME-01, THEME-02, THEME-03, THEME-04, THEME-05, THEME-06

**Status:** Complete (2026-01-28)

**Plans:** 1 plan

Plans:
- [x] 08-01-PLAN.md - Create theme.py with Theme dataclass, detection, and utilities

**Files:**
- Create `kalico-flash/theme.py` (~120 lines)

**Implementation:**
1. ANSI escape code constants (RESET, colors, bold, dim)
2. Theme dataclass with semantic fields
   - Message types: success, warning, error, info, phase
   - Device markers: marker_reg, marker_new, marker_blk, marker_dup, marker_num
   - UI elements: menu_title, menu_border, prompt
   - Modifiers: bold, dim, reset
3. No-color theme instance (all fields empty)
4. `supports_color()` function with detection logic
   - NO_COLOR -> False
   - FORCE_COLOR -> True
   - Not TTY -> False
   - TERM=dumb -> False
   - Windows -> VT mode enable attempt
   - Unix TTY -> True
5. `_enable_windows_vt_mode()` helper via ctypes
6. `get_theme()` and `reset_theme()` cached singleton
7. `clear_screen()` utility
   - Unix: `clear -x` or ANSI fallback
   - Windows: VT mode ANSI or `cls`

**Success Criteria:**
- `from kflash.theme import get_theme` returns Theme dataclass
- `NO_COLOR=1` returns no-color theme
- `clear_screen()` works on both Unix and Windows

**Reference:** `.working/theme_plan.md` sections 1.1-1.7

---

## Phase 9: Apply Theming

**Goal:** Integrate theme across output, TUI, and errors

**Requirements:** OUT-01 to OUT-07, TUI-01 to TUI-03, ERR-01

**Status:** In Progress

**Plans:** 2 plans

Plans:
- [ ] 09-01-PLAN.md - Reconcile theme.py colors with CONTEXT.md decisions
- [ ] 09-02-PLAN.md - Apply theming to output.py, tui.py, errors.py

**Files:**
- Modify `kflash/theme.py` (~10 lines changed)
- Modify `kflash/output.py` (~30 lines changed)
- Modify `kflash/tui.py` (~40 lines changed)
- Modify `kflash/errors.py` (~5 lines changed)

**Implementation:**

### Plan 01: Theme Reconciliation (Wave 1)
Update theme.py to match CONTEXT.md decisions:
- Add blue color for phase (distinct from cyan info)
- Change marker_new to yellow (caution/attention)
- Change marker_blk to yellow (caution/unavailable)
- Change menu_border to cyan (match title)

### Plan 02: Apply Theming (Wave 2)

**output.py Changes:**
1. Import `get_theme` from theme module
2. Add `self.theme = get_theme()` in CliOutput.__init__
3. Update methods with themed output:
   - `info()` - cyan `[section]` bracket
   - `success()` - green `[OK]` bracket
   - `warn()` - yellow `[!!]` bracket
   - `error()` - red `[FAIL]` bracket
   - `phase()` - blue `[phase]` bracket
   - `device_line()` - marker style lookup dict
   - `prompt()` / `confirm()` - bold prompt text

**tui.py Changes:**
1. Import `get_theme`, `clear_screen` from theme module
2. Add `clear_screen()` at start of `run_menu()` while loop
3. Add `clear_screen()` at start of `_settings_menu()` while loop
4. Apply `theme.menu_title` to title in `_render_menu()`
   - Note: ANSI codes have zero width - use plain text for width calc
5. Add `pause_with_keypress()` utility for feedback pauses

**errors.py Changes:**
1. Import `get_theme` from theme module
2. Apply `theme.error` style to `[FAIL]` header in `format_error()`

**Success Criteria:**
- `kflash --list-devices` shows colored markers
- `kflash` menu clears screen, title is bold
- Error messages show red [FAIL] header

**Reference:** `.working/theme_plan.md` sections 2-4

---

## Verification (After Phase 9)

Visual spot-check only:
1. `kflash --list-devices` - colored device markers
2. `kflash` - screen clear, bold title, colored menu actions
3. `kflash --device nonexistent` - red [FAIL] error
4. `NO_COLOR=1 kflash --list-devices` - no colors (fallback works)

SSH to Pi to verify colors render correctly over remote terminal.

---
*Created: 2026-01-28 for v2.1 milestone*
