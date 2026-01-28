# Requirements - v2.1 TUI Color Theme

## Overview

Add KIAUH-style ANSI color support with a centralized, maintainable theme system.
- **Constraint:** Python 3.9+ stdlib only (no external dependencies)
- **Reference:** `.working/theme_plan.md` for detailed implementation plan

## Theme Infrastructure (Phase 8)

### THEME-01: Theme module with semantic style dataclass
Create `theme.py` with a Theme dataclass containing semantic style fields:
- Message types: success, warning, error, info, phase
- Device markers: marker_reg, marker_new, marker_blk, marker_dup
- UI elements: menu_title, menu_border, prompt
- Modifiers: bold, dim, reset

**Acceptance:** `from kflash.theme import Theme` imports successfully

### THEME-02: Terminal capability detection
Implement `supports_color()` function with detection logic:
1. NO_COLOR env var set → False (https://no-color.org/)
2. FORCE_COLOR env var set → True
3. stdout not a TTY → False
4. TERM == 'dumb' → False
5. Windows → attempt VT mode, return success
6. Unix-like TTY → True

**Acceptance:** Function returns correct boolean for each condition

### THEME-03: Windows VT mode support
Implement `_enable_windows_vt_mode()` helper:
- Use ctypes to call SetConsoleMode with ENABLE_VIRTUAL_TERMINAL_PROCESSING
- Return True if successful, False if unsupported/failed

**Acceptance:** Windows terminals render ANSI codes correctly (or fallback gracefully)

### THEME-04: No-color fallback theme
Create `_no_color_theme` instance with all style fields as empty strings.

**Acceptance:** `NO_COLOR=1` produces no escape codes in output

### THEME-05: Cached theme singleton
Implement accessor functions:
- `get_theme()` — Returns Theme instance, caches on first call
- `reset_theme()` — Clears cache (for testing)

**Acceptance:** Multiple `get_theme()` calls return same instance

### THEME-06: Screen clear utility
Implement `clear_screen()` function:
- Unix: `clear -x` (preserves scrollback) or ANSI fallback
- Windows with VT: ANSI sequence `\033[H\033[J`
- Windows without VT: `cmd /c cls`

**Acceptance:** Screen clears without destroying scrollback history

## CLI Output Styling (Phase 9)

### OUT-01: Colored [OK] messages
Green `[OK]` prefix in success() method.

**Acceptance:** `kflash --list-devices` shows green [OK] for successful operations

### OUT-02: Colored [FAIL] messages
Red `[FAIL]` prefix in error() method.

**Acceptance:** Error messages show red [FAIL] prefix

### OUT-03: Colored [!!] warnings
Yellow `[!!]` prefix in warn() method.

**Acceptance:** Warning messages show yellow [!!] prefix

### OUT-04: Colored [section] info
Cyan brackets in info() method for section labels.

**Acceptance:** Info messages show cyan [section] prefix

### OUT-05: Colored [phase] markers
Cyan brackets in phase() method for phase labels.

**Acceptance:** Phase labels show cyan [Discovery], [Build], etc.

### OUT-06: Colored device markers
Colored markers in device_line() method:
- REG → green (registered/connected)
- NEW → cyan (unregistered device)
- BLK → red (blocked device)
- DUP → yellow (duplicate match)

**Acceptance:** `kflash --list-devices` shows colored device markers

### OUT-07: Bold prompts
Bold text in prompt() and confirm() methods.

**Acceptance:** Input prompts display in bold

## TUI Integration (Phase 9)

### TUI-01: Screen clear before main menu
Call `clear_screen()` at start of main menu loop in run_menu().

**Acceptance:** Screen clears before menu displays, after each action

### TUI-02: Bold menu title
Apply theme.menu_title style to "kalico-flash" title in menu box.
Note: ANSI codes have zero display width - width calculations must use plain text.

**Acceptance:** Menu title "kalico-flash" displays bold

### TUI-03: Screen clear in settings submenu
Call `clear_screen()` at start of settings menu loop in _settings_menu().

**Acceptance:** Settings submenu clears screen before display

## Error Formatting (Phase 9)

### ERR-01: Colored [FAIL] header in errors
Apply theme.error style to [FAIL] prefix in format_error().
Only the header is colored - recovery steps remain plain for readability.

**Acceptance:** `kflash --device nonexistent` shows red [FAIL] header

---

## Verification (Minimal)

After Phase 9 completion, visual spot-check:
1. `kflash --list-devices` — colored markers
2. `kflash` — colored menu with screen clear
3. `NO_COLOR=1 kflash --list-devices` — no colors (fallback)

No extensive testing required - this is a visual enhancement.

---

## Traceability

| Req ID | Name | Phase | Status |
|--------|------|-------|--------|
| THEME-01 | Theme dataclass | 8 | Complete |
| THEME-02 | Terminal detection | 8 | Complete |
| THEME-03 | Windows VT mode | 8 | Complete |
| THEME-04 | No-color fallback | 8 | Complete |
| THEME-05 | Cached singleton | 8 | Complete |
| THEME-06 | Screen clear | 8 | Complete |
| OUT-01 | Colored [OK] | 9 | Complete |
| OUT-02 | Colored [FAIL] | 9 | Complete |
| OUT-03 | Colored [!!] | 9 | Complete |
| OUT-04 | Colored [section] | 9 | Complete |
| OUT-05 | Colored [phase] | 9 | Complete |
| OUT-06 | Colored markers | 9 | Complete |
| OUT-07 | Bold prompts | 9 | Complete |
| TUI-01 | Screen clear main | 9 | Complete |
| TUI-02 | Bold menu title | 9 | Complete |
| TUI-03 | Screen clear settings | 9 | Complete |
| ERR-01 | Colored error header | 9 | Complete |

---
*Created: 2026-01-28 for v2.1 milestone*
