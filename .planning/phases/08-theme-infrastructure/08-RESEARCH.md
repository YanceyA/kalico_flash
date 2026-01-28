# Theme System Implementation Plan

**Date:** January 28, 2026
**Goal:** Add KIAUH-style ANSI color support with a centralized, maintainable theme system.
**Constraint:** Python 3.9+ stdlib only (no external dependencies).

---

## Executive Summary

Create a new `theme.py` module that centralizes all terminal styling definitions. Use a dataclass with semantic style names (e.g., `theme.success` not `theme.green`) so the meaning is clear and colors can be adjusted in one place. Integrate with the existing `Output` protocol pattern.

---

## 1) NEW MODULE: `kflash/theme.py`

### Purpose
Centralized terminal styling definitions, capability detection, and screen utilities.

### Contents

#### 1.1 ANSI Escape Code Constants
```python
# Base escape codes (not exported directly - use Theme dataclass)
RESET = "\033[0m"
_GREEN = "\033[92m"      # Bright green
_YELLOW = "\033[93m"     # Bright yellow
_RED = "\033[91m"        # Bright red
_CYAN = "\033[96m"       # Bright cyan
_BOLD = "\033[1m"        # Bold
_DIM = "\033[2m"         # Dim/faint
```

#### 1.2 Theme Dataclass
```python
@dataclass
class Theme:
    """Theme with semantic style definitions.

    All fields contain ANSI escape sequences (or empty strings for no-color mode).
    Usage: t = get_theme(); print(f"{t.success}[OK]{t.reset} Done")
    """
    # Message type styles
    success: str = _GREEN       # [OK] messages
    warning: str = _YELLOW      # [!!] warnings
    error: str = _RED           # [FAIL] errors (stderr)
    info: str = _CYAN           # [section] info messages
    phase: str = _CYAN          # [Discovery], [Build], etc.

    # Device marker styles
    marker_reg: str = _GREEN    # REG - registered/connected
    marker_new: str = _CYAN     # NEW - unregistered device
    marker_blk: str = _RED      # BLK - blocked device
    marker_dup: str = _YELLOW   # DUP - duplicate USB match
    marker_num: str = ""        # Numbered selection (neutral)

    # UI element styles
    menu_title: str = _BOLD     # Menu box title
    menu_border: str = ""       # Box drawing chars (neutral by default)
    prompt: str = _BOLD         # Input prompts

    # Text modifiers
    bold: str = _BOLD
    dim: str = _DIM

    # Reset code (always applied after styled text)
    reset: str = RESET
```

#### 1.3 No-Color Theme Instance
```python
_color_theme = Theme()  # Uses all defaults

_no_color_theme = Theme(
    success="", warning="", error="", info="", phase="",
    marker_reg="", marker_new="", marker_blk="", marker_dup="", marker_num="",
    menu_title="", menu_border="", prompt="",
    bold="", dim="", reset=""
)
```

#### 1.4 Terminal Capability Detection
```python
def supports_color() -> bool:
    """Detect if terminal supports ANSI colors.

    Detection signals (in order):
    1. NO_COLOR env var set → False (https://no-color.org/)
    2. FORCE_COLOR env var set → True (user override)
    3. stdout not a TTY → False (piped/redirected)
    4. TERM == 'dumb' → False
    5. Windows → attempt VT mode enable, return success
    6. Unix-like TTY → True (assume color support)
    """
```

#### 1.5 Windows VT Mode Helper
```python
def _enable_windows_vt_mode() -> bool:
    """Enable ANSI escape code processing on Windows 10+.

    Uses ctypes to call SetConsoleMode with ENABLE_VIRTUAL_TERMINAL_PROCESSING.
    Returns True if successful, False if unsupported or failed.
    """
```

#### 1.6 Theme Accessor (Cached Singleton)
```python
_cached_theme: Theme | None = None

def get_theme() -> Theme:
    """Return appropriate theme based on terminal capabilities.

    Caches result on first call. Use reset_theme() to re-detect.
    """
    global _cached_theme
    if _cached_theme is None:
        _cached_theme = _color_theme if supports_color() else _no_color_theme
    return _cached_theme

def reset_theme() -> None:
    """Clear cached theme (for testing or after env change)."""
    global _cached_theme
    _cached_theme = None
```

#### 1.7 Screen Clear Utility
```python
def clear_screen() -> None:
    """Clear terminal screen, preserving scrollback buffer.

    Follows KIAUH pattern (clear -x on Unix).

    Implementation:
    - Unix: subprocess.run(["clear", "-x"]) if available, else ANSI fallback
    - Windows with VT: ANSI escape sequence \\033[H\\033[J
    - Windows without VT: subprocess.run(["cmd", "/c", "cls"])
    """
```

### Design Decisions
- **Dataclass over Enum**: Direct field access (`theme.success`) is cleaner than enum value access (`.value`)
- **Singleton accessor**: Theme determined at startup, never changes mid-session
- **Semantic naming**: Style names describe purpose, not color - easier to adjust palette later
- **NO_COLOR respect**: Standard convention (https://no-color.org/) for accessibility

### Manual Test
```bash
# Test color detection
python -c "from kflash.theme import supports_color, get_theme; print(supports_color(), get_theme())"

# Test NO_COLOR
NO_COLOR=1 python -c "from kflash.theme import get_theme; t=get_theme(); print(repr(t.success))"
# Should print: ''

# Test FORCE_COLOR
FORCE_COLOR=1 python -c "from kflash.theme import get_theme; t=get_theme(); print(repr(t.success))"
# Should print: '\x1b[92m'
```

---

## 2) MODIFY: `kflash/output.py`

### Affected Methods
All methods in `CliOutput` class (lines 30-76).

### Current State
Plain text output with bracket markers:
- `[OK]`, `[FAIL]`, `[!!]`, `[section]`, `[phase]`
- No color or styling

### Proposed Changes

#### 2.1 Add Theme Import and Instance
```python
from .theme import get_theme

class CliOutput:
    """CLI output with ANSI color support."""

    def __init__(self):
        self.theme = get_theme()
```

#### 2.2 Update Each Output Method

**`info()`** - Cyan bracket, white text:
```python
def info(self, section: str, message: str) -> None:
    t = self.theme
    print(f"{t.info}[{section}]{t.reset} {message}")
```

**`success()`** - Green `[OK]`:
```python
def success(self, message: str) -> None:
    t = self.theme
    print(f"{t.success}[OK]{t.reset} {message}")
```

**`warn()`** - Yellow `[!!]`:
```python
def warn(self, message: str) -> None:
    t = self.theme
    print(f"{t.warning}[!!]{t.reset} {message}")
```

**`error()`** - Red `[FAIL]`:
```python
def error(self, message: str) -> None:
    t = self.theme
    print(f"{t.error}[FAIL]{t.reset} {message}", file=sys.stderr)
```

**`phase()`** - Cyan phase name:
```python
def phase(self, phase_name: str, message: str) -> None:
    t = self.theme
    print(f"{t.phase}[{phase_name}]{t.reset} {message}")
```

**`device_line()`** - Colored marker based on type:
```python
def device_line(self, marker: str, name: str, detail: str) -> None:
    t = self.theme
    # Map marker to style
    marker_styles = {
        "REG": t.marker_reg,
        "NEW": t.marker_new,
        "BLK": t.marker_blk,
        "DUP": t.marker_dup,
    }
    style = marker_styles.get(marker.upper(), "")
    print(f"  {style}[{marker}]{t.reset} {name:<24s} {detail}")
```

**`prompt()`** - Bold prompt text:
```python
def prompt(self, message: str, default: str = "") -> str:
    t = self.theme
    suffix = f" [{default}]" if default else ""
    response = input(f"{t.prompt}{message}{suffix}:{t.reset} ").strip()
    return response or default
```

**`confirm()`** - Bold prompt text:
```python
def confirm(self, message: str, default: bool = False) -> bool:
    t = self.theme
    suffix = " [Y/n]" if default else " [y/N]"
    response = input(f"{t.prompt}{message}{suffix}:{t.reset} ").strip().lower()
    if not response:
        return default
    return response in ("y", "yes")
```

### Design Decisions
- **Theme instance in `__init__`**: Cached once per CliOutput instance
- **Bracket markers preserved**: `[OK]`, `[FAIL]`, etc. still visible for parsing/scripts
- **Marker style lookup**: Dictionary-based for clean extensibility
- **NullOutput unchanged**: No theme needed for silent output

### Manual Test
```bash
# On Pi via SSH
python3 kflash.py --list-devices
# Verify: REG markers green, NEW markers cyan, FAIL messages red

python3 kflash.py --add-device
# Verify: Prompts are bold, warnings are yellow
```

---

## 3) MODIFY: `kflash/tui.py`

### Affected Locations
- `run_menu()` (line 165) - Main menu loop
- `_render_menu()` (line 72) - Menu box rendering
- `_settings_menu()` (line 301) - Settings submenu

### Current State
- Box drawing with Unicode/ASCII detection (already implemented)
- Plain text title: ` kalico-flash `
- No screen clearing between redraws

### Proposed Changes

#### 3.1 Add Imports
```python
from .theme import get_theme, clear_screen
```

#### 3.2 Screen Clear Before Menu Display
In `run_menu()`, add screen clear before rendering:
```python
def run_menu(registry, out) -> int:
    # ... TTY check ...

    box = _get_box_chars()
    menu_text = _render_menu(MENU_OPTIONS, box)

    while True:
        try:
            clear_screen()  # <-- NEW: Clear before each redraw
            print()
            print(menu_text)
            print()
            # ... rest of loop ...
```

Similarly in `_settings_menu()`:
```python
def _settings_menu(registry, out) -> None:
    box = _get_box_chars()
    settings_text = _render_menu(SETTINGS_OPTIONS, box)

    while True:
        clear_screen()  # <-- NEW
        print()
        print(settings_text)
        # ...
```

#### 3.3 Themed Menu Title
In `_render_menu()`, apply theme to title:
```python
def _render_menu(options: list[tuple[str, str]], box: dict[str, str]) -> str:
    theme = get_theme()

    # Calculate inner width: " N) Label " with padding
    inner_items = [f" {num}) {label} " for num, label in options]
    inner_width = max(len(item) for item in inner_items)

    # Title with theme (styled portion is visual only, width calc uses plain text)
    title_text = "kalico-flash"
    title_display = f"{theme.menu_title}{title_text}{theme.reset}"

    # Ensure minimum width for the title
    inner_width = max(inner_width, len(title_text) + 2)  # +2 for padding spaces

    lines: list[str] = []

    # Top border with styled title centered
    pad_total = inner_width - len(title_text) - 2  # -2 for spaces around title
    pad_left = pad_total // 2
    pad_right = pad_total - pad_left
    lines.append(
        box["tl"] + box["h"] * pad_left + f" {title_display} " + box["h"] * pad_right + box["tr"]
    )

    # ... rest unchanged ...
```

**Note:** ANSI escape codes have zero display width, so width calculations must use the plain text length, not the styled string length.

### Design Decisions
- **Clear before each menu redraw**: Matches KIAUH behavior, cleaner UX
- **Only title is styled**: Box borders remain neutral (less visual noise)
- **Width calculation careful**: ANSI codes don't contribute to visual width

### Manual Test
```bash
# Interactive menu test
python3 kflash.py
# Verify: Screen clears before menu, title is bold, actions return to cleared menu
```

---

## 4) MODIFY: `kflash/errors.py`

### Affected Location
- `format_error()` function (lines 8-62)

### Current State
Plain text error formatting with boxed structure:
```
[FAIL] Error Type
Message text here
```

### Proposed Changes

#### 4.1 Add Theme Import
```python
from .theme import get_theme
```

#### 4.2 Colored Error Header
```python
def format_error(
    error_type: str,
    message: str,
    context: dict[str, str] | None = None,
    recovery: str | None = None,
) -> str:
    """Format error with colored header (if terminal supports color)."""
    t = get_theme()

    lines: list[str] = []

    # Colored header
    lines.append(f"{t.error}[FAIL]{t.reset} {error_type}")

    # ... rest of formatting unchanged ...
```

### Design Decisions
- **Only header is colored**: Recovery steps and context remain plain for readability
- **Stderr output unchanged**: Color codes work on stderr too

### Manual Test
```bash
# Trigger an error (e.g., invalid device)
python3 kflash.py --device nonexistent
# Verify: [FAIL] is red, error message follows
```

---

## 5) IMPLEMENTATION ORDER

### Wave 1: Core Theme Module
1. Create `kflash/theme.py` with full implementation
2. Test detection logic locally and on Pi

### Wave 2: Output Integration
1. Modify `kflash/output.py` - add theme to CliOutput
2. Test `--list-devices` and basic commands

### Wave 3: TUI Integration
1. Modify `kflash/tui.py` - screen clear + themed title
2. Test interactive menu

### Wave 4: Error Formatting
1. Modify `kflash/errors.py` - colored error header
2. Test error scenarios

### Wave 5: Verification
1. Full test on Pi over SSH
2. Test `NO_COLOR=1` fallback
3. Test on Windows (if applicable)

---

## 6) COLOR REFERENCE TABLE

| Style Name | ANSI Code | Color | Used For |
|------------|-----------|-------|----------|
| `success` | `\033[92m` | Bright Green | `[OK]` messages |
| `warning` | `\033[93m` | Bright Yellow | `[!!]` warnings |
| `error` | `\033[91m` | Bright Red | `[FAIL]` errors |
| `info` | `\033[96m` | Bright Cyan | `[section]` info |
| `phase` | `\033[96m` | Bright Cyan | `[Discovery]`, `[Build]` |
| `marker_reg` | `\033[92m` | Bright Green | `[REG]` connected device |
| `marker_new` | `\033[96m` | Bright Cyan | `[NEW]` unregistered |
| `marker_blk` | `\033[91m` | Bright Red | `[BLK]` blocked |
| `marker_dup` | `\033[93m` | Bright Yellow | `[DUP]` duplicate |
| `menu_title` | `\033[1m` | Bold | Menu title |
| `prompt` | `\033[1m` | Bold | Input prompts |
| `dim` | `\033[2m` | Dim | Secondary info |
| `reset` | `\033[0m` | Reset | After styled text |

---

## 7) BACKWARDS COMPATIBILITY

- **Bracket markers preserved**: `[OK]`, `[FAIL]`, `[!!]` unchanged for script parsing
- **No-color fallback**: Automatic for unsupported terminals
- **NO_COLOR standard**: Respected per https://no-color.org/
- **Output Protocol unchanged**: Interface remains compatible

---

## 8) FILES SUMMARY

| File | Action | Lines Changed (Est.) |
|------|--------|---------------------|
| `kflash/theme.py` | Create | ~120 new |
| `kflash/output.py` | Modify | ~30 changed |
| `kflash/tui.py` | Modify | ~20 changed |
| `kflash/errors.py` | Modify | ~5 changed |

---

## 9) VERIFICATION CHECKLIST

- [ ] `python kflash.py --list-devices` shows colored markers
- [ ] `python kflash.py` menu clears screen, title is bold
- [ ] `python kflash.py --device nonexistent` shows red `[FAIL]`
- [ ] `NO_COLOR=1 python kflash.py --list-devices` shows no colors
- [ ] SSH to Pi: colors render correctly in terminal
- [ ] Windows (if tested): ANSI codes render or fallback gracefully
