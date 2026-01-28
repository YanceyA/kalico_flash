# Phase 9: Apply Theming - Research

**Researched:** 2026-01-28
**Domain:** ANSI color integration, terminal input handling, TUI patterns
**Confidence:** HIGH

## Summary

Phase 9 integrates the existing theme.py infrastructure (from Phase 8) into output.py, tui.py, and errors.py. The theme module is fully implemented with color detection, NO_COLOR support, and clear_screen(). This phase applies those styles to message output, menu rendering, and error formatting.

The implementation is straightforward - import get_theme() and wrap bracket markers with style codes. The main technical considerations are:
1. ANSI codes have zero display width - width calculations must use plain text
2. The pause-with-keypress feature requires platform-specific terminal handling (select + termios on Unix)
3. Some CONTEXT.md decisions differ from current theme.py definitions (marker names, blue vs cyan for phase)

**Primary recommendation:** Apply theme styles with minimal code changes; add pause_with_keypress() utility function using select/termios for the feedback pause feature.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| theme.py | Local | ANSI style definitions | Already implemented in Phase 8 |

### Supporting (stdlib only)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| select | stdlib | Check stdin readability with timeout | Unix non-blocking input |
| termios | stdlib | Save/restore terminal settings | Raw mode for single keypress |
| tty | stdlib | setcbreak() for unbuffered input | Character-at-a-time reads |
| re | stdlib | Strip ANSI codes for width calc | Menu box alignment |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| select+termios | threading+Queue | Cross-platform but more complex |
| tty.setcbreak() | tty.setraw() | setraw() traps Ctrl+C, setcbreak() allows it |
| Manual ANSI strip | wcwidth library | External dep, overkill for ASCII-only |

**Installation:**
No installation needed - all stdlib modules.

## Architecture Patterns

### Recommended Modifications

**output.py changes:**
```
output.py
├── import from .theme import get_theme
├── CliOutput.__init__() stores self.theme = get_theme()
├── info() - wrap [section] with t.info
├── success() - wrap [OK] with t.success
├── warn() - wrap [!!] with t.warning
├── error() - wrap [FAIL] with t.error
├── phase() - wrap [phase] with t.phase
├── device_line() - lookup marker style from dict
├── prompt() - wrap message with t.prompt
└── confirm() - wrap message with t.prompt
```

**tui.py changes:**
```
tui.py
├── import from .theme import get_theme, clear_screen
├── run_menu() - call clear_screen() at loop start
├── _render_menu() - apply theme to title (watch width calc!)
├── _settings_menu() - call clear_screen() at loop start
└── (new) pause_with_keypress() - timeout with early exit
```

**errors.py changes:**
```
errors.py
├── import from .theme import get_theme
└── format_error() - wrap [FAIL] with t.error
```

### Pattern 1: Styled Bracket Output
**What:** Color only the bracket portion, not the message text
**When to use:** All info/success/warn/error/phase methods
**Example:**
```python
# Source: CONTEXT.md decision - color scope
def success(self, message: str) -> None:
    t = self.theme
    print(f"{t.success}[OK]{t.reset} {message}")
    # Only [OK] is green, message stays default color
```

### Pattern 2: Device Marker Style Lookup
**What:** Dictionary mapping marker type to theme style
**When to use:** device_line() method
**Example:**
```python
# Source: theme.py marker_* fields
def device_line(self, marker: str, name: str, detail: str) -> None:
    t = self.theme
    marker_styles = {
        "REG": t.marker_reg,  # green
        "NEW": t.marker_new,  # cyan (or yellow per CONTEXT.md)
        "BLK": t.marker_blk,  # red (or yellow per CONTEXT.md)
        "DUP": t.marker_dup,  # yellow
    }
    style = marker_styles.get(marker.upper(), "")
    print(f"  {style}[{marker}]{t.reset} {name:<24s} {detail}")
```

### Pattern 3: Width-Safe Title Rendering
**What:** Calculate width using plain text, display with ANSI codes
**When to use:** Menu box title in _render_menu()
**Example:**
```python
# Source: Official Python stdlib knowledge
# ANSI codes are zero-width - len() includes bytes that don't render
title_plain = "kalico-flash"
title_display = f"{theme.menu_title}{title_plain}{theme.reset}"

# Use plain text length for width calculations
inner_width = max(inner_width, len(title_plain) + 2)

# Display uses styled version
lines.append(box["tl"] + box["h"] * pad + f" {title_display} " + box["h"] * pad + box["tr"])
```

### Pattern 4: Non-Blocking Keypress with Timeout (Unix)
**What:** Wait for keypress OR timeout, whichever comes first
**When to use:** Feedback pause after action completion
**Example:**
```python
# Source: Python docs (select, termios, tty modules)
import select
import sys
import termios
import tty

def pause_with_keypress(timeout: float = 5.0, prompt: str = "") -> bool:
    """Wait for keypress or timeout. Returns True if key pressed.

    Unix-only implementation using select + termios.
    """
    if not sys.stdin.isatty():
        # Non-TTY: just sleep
        import time
        time.sleep(timeout)
        return False

    if prompt:
        print(prompt, end="", flush=True)

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)  # Character-at-a-time, allows Ctrl+C
        rlist, _, _ = select.select([sys.stdin], [], [], timeout)
        if rlist:
            sys.stdin.read(1)  # Consume the keypress
            return True
        return False
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
```

### Anti-Patterns to Avoid
- **Including ANSI codes in width calculations:** len() counts bytes, not display width
- **Using tty.setraw() for keypress:** Traps Ctrl+C, use setcbreak() instead
- **Forgetting termios restore in finally:** Terminal stays in weird state on exception
- **Calling select on stdin on Windows:** Only works with sockets on Windows

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Color detection | Custom env checks | theme.supports_color() | Already handles NO_COLOR, FORCE_COLOR, TTY, Windows |
| Screen clear | ANSI sequences everywhere | theme.clear_screen() | Already handles Unix/Windows differences |
| Style lookup | Switch statements | Theme dataclass fields | Semantic names, single source of truth |
| Terminal mode save/restore | Manual tcgetattr/tcsetattr | try/finally pattern | Guarantees restore on any exit path |

**Key insight:** The theme module already encapsulates the hard parts (detection, Windows VT mode, clear variations). This phase is just wiring - don't re-implement what exists.

## Common Pitfalls

### Pitfall 1: ANSI Width Miscalculation
**What goes wrong:** Menu box characters misalign because len() includes escape codes
**Why it happens:** `len("\033[1mtext\033[0m")` is 13, not 4
**How to avoid:** Always calculate width from plain text, apply styles after
**Warning signs:** Box corners don't line up, title off-center

### Pitfall 2: Terminal State Corruption
**What goes wrong:** Terminal stays in raw/cbreak mode after Ctrl+C
**Why it happens:** Exception raised before termios restore
**How to avoid:** Always use try/finally for termios operations
**Warning signs:** Terminal doesn't echo typed characters, backspace broken

### Pitfall 3: Windows select() Failure
**What goes wrong:** select([sys.stdin], ...) raises error on Windows
**Why it happens:** Windows select() only works with sockets, not file handles
**How to avoid:** Check platform before using select; use time.sleep() fallback
**Warning signs:** "select" module error on Windows

### Pitfall 4: Color in Piped Output
**What goes wrong:** ANSI codes appear as garbage in log files
**Why it happens:** Forgot to check isatty() or NO_COLOR
**How to avoid:** get_theme() already handles this - use it consistently
**Warning signs:** `[OK]` shows as `[0m[92m[OK][0m` in logs

### Pitfall 5: Marker/Style Mismatch
**What goes wrong:** Wrong color appears for device markers
**Why it happens:** CONTEXT.md and REQUIREMENTS.md have different marker specs
**How to avoid:** Follow CONTEXT.md decisions (locked), update theme.py if needed
**Warning signs:** Device list colors don't match user expectations

## Code Examples

Verified patterns from official sources:

### Strip ANSI for Width Calculation
```python
# Source: Python re module, common pattern
import re

ANSI_PATTERN = re.compile(r'\x1b\[[0-9;]*m')

def visible_width(s: str) -> int:
    """Return display width of string (ANSI codes don't count)."""
    return len(ANSI_PATTERN.sub('', s))
```

### Safe Keypress Detection (Unix)
```python
# Source: Python docs - termios, tty, select modules
import select
import sys
import termios
import tty

def wait_for_key_or_timeout(timeout_seconds: float) -> bool:
    """Block until keypress or timeout. Returns True if key pressed."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        readable, _, _ = select.select([sys.stdin], [], [], timeout_seconds)
        if readable:
            sys.stdin.read(1)  # Consume
            return True
        return False
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
```

### Theme-Aware Output Method
```python
# Source: Phase 8 research document pattern
def info(self, section: str, message: str) -> None:
    t = self.theme
    print(f"{t.info}[{section}]{t.reset} {message}")
```

## Reconciliation Notes

### CONTEXT.md vs REQUIREMENTS.md Differences

| Item | REQUIREMENTS.md | CONTEXT.md | Resolution |
|------|-----------------|------------|------------|
| Phase color | Cyan (`\033[96m`) | Blue (distinct from cyan) | Add blue (`\033[94m`) to theme.py |
| Marker NEW | cyan | yellow | Follow CONTEXT.md (user decision) |
| Marker BLK | red | yellow | Follow CONTEXT.md (user decision) |
| Marker names | REG/NEW/BLK/DUP | R/N/B | Cosmetic, keep REG/NEW/BLK in code |

**Recommendation:** Update theme.py to add `_BLUE = "\033[94m"` and set `phase: str = _BLUE`. Update marker colors to match CONTEXT.md decisions.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Inline escape codes | Centralized Theme dataclass | Phase 8 | Single source of truth |
| tty.setraw() for input | tty.setcbreak() | Long-standing | Allows Ctrl+C interrupt |

**Deprecated/outdated:**
- None - theme.py from Phase 8 is current best practice

## Open Questions

Things that couldn't be fully resolved:

1. **Windows pause behavior**
   - What we know: select() doesn't work on stdin on Windows
   - What's unclear: Whether time.sleep() fallback is acceptable UX
   - Recommendation: Use simple sleep() on Windows; most users are on Pi (Linux)

2. **Menu border styling**
   - What we know: CONTEXT.md says borders/separators cyan
   - What's unclear: Current theme.py has `menu_border: str = ""` (no style)
   - Recommendation: Set menu_border to cyan to match title

## Sources

### Primary (HIGH confidence)
- Python docs: select module - https://docs.python.org/3/library/select.html
- Python docs: termios module - https://docs.python.org/3/library/termios.html
- Python docs: tty module - https://docs.python.org/3/library/tty.html
- Local: theme.py implementation from Phase 8
- Local: 09-CONTEXT.md user decisions

### Secondary (MEDIUM confidence)
- W3Resource Python exercises (ANSI strip regex) - https://www.w3resource.com/python-exercises/re/python-re-exercise-45.php
- Recurse Center blog (string lengths with ANSI) - https://www.recurse.com/blog/74-a-string-of-unexpected-lengths

### Tertiary (LOW confidence)
- None - all findings verified with official docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - stdlib modules, well-documented
- Architecture: HIGH - straightforward integration with existing theme.py
- Pitfalls: HIGH - well-known terminal handling issues
- Pause feature: MEDIUM - Unix-only implementation, Windows fallback unclear

**Research date:** 2026-01-28
**Valid until:** Indefinite - stdlib modules are stable
