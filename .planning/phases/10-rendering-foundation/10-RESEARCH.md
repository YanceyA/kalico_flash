# Phase 10: Rendering Foundation - Research

**Researched:** 2026-01-29
**Domain:** ANSI terminal rendering primitives (Python 3.9+ stdlib only)
**Confidence:** HIGH

## Summary

Phase 10 upgrades the existing `theme.py` from ANSI 16 color codes to a truecolor RGB palette (with fallback tiers), adds ANSI-aware string utilities for correct visual alignment, and provides terminal width detection. All downstream panel rendering (Phases 11-14) depends on these primitives.

The domain is well-understood: Python's stdlib provides `os.get_terminal_size()`, `shutil.get_terminal_size()`, and `re` for ANSI stripping. Truecolor uses `\033[38;2;R;G;Bm` SGR sequences. The zen mockup already defines the exact RGB values to use. No external libraries needed.

**Primary recommendation:** Extend the existing `theme.py` with a `ColorTier` enum and tier-aware `Theme` dataclass, then create a new `ansi.py` module for string utilities (`strip_ansi`, `display_width`, `pad_to_width`) and terminal size detection.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `re` | stdlib | ANSI escape sequence stripping | Standard regex, no dependencies |
| Python `os` | stdlib | `os.get_terminal_size()` | Direct syscall, no fallback needed |
| Python `shutil` | stdlib | `shutil.get_terminal_size()` fallback | Provides default (80,24) on failure |
| Python `unicodedata` | stdlib | East Asian Width for CJK chars | Correct `display_width` for wide chars |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python `enum` | stdlib | `ColorTier` enum (TRUECOLOR, ANSI256, ANSI16, NONE) | Tier detection and selection |
| Python `dataclasses` | stdlib | Theme dataclass (already used) | Structured color definitions |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled ANSI stripping | `Rich` library | Rich is excellent but violates stdlib-only constraint |
| `unicodedata.east_asian_width` | `wcwidth` PyPI package | More accurate for edge cases but adds dependency |
| `os.get_terminal_size()` | `fcntl.ioctl` TIOCGWINSZ | Lower level, less portable, no benefit |

## Architecture Patterns

### Recommended Module Structure
```
kflash/
├── theme.py       # Extended: ColorTier enum, truecolor palette, tier-aware Theme
└── ansi.py        # NEW: strip_ansi, display_width, pad_to_width, get_terminal_width
```

### Pattern 1: Color Tier Detection
**What:** Detect terminal color capability at startup, cache the result, select appropriate palette tier.
**When to use:** On first `get_theme()` call (existing lazy init pattern).
**Example:**
```python
import os
import sys
from enum import Enum

class ColorTier(Enum):
    TRUECOLOR = "truecolor"
    ANSI256 = "256"
    ANSI16 = "16"
    NONE = "none"

def detect_color_tier() -> ColorTier:
    """Detect terminal color capability.

    Detection order:
    1. NO_COLOR env var -> NONE
    2. FORCE_COLOR env var -> TRUECOLOR (user override)
    3. Not a TTY -> NONE
    4. TERM=dumb -> NONE
    5. COLORTERM in {truecolor, 24bit} -> TRUECOLOR
    6. TERM contains '256color' -> ANSI256
    7. Otherwise -> ANSI16
    """
    if os.environ.get("NO_COLOR"):
        return ColorTier.NONE
    if os.environ.get("FORCE_COLOR"):
        return ColorTier.TRUECOLOR
    if not sys.stdout.isatty():
        return ColorTier.NONE
    if os.environ.get("TERM") == "dumb":
        return ColorTier.NONE

    colorterm = os.environ.get("COLORTERM", "").lower()
    if colorterm in ("truecolor", "24bit"):
        return ColorTier.TRUECOLOR

    term = os.environ.get("TERM", "").lower()
    if "256color" in term:
        return ColorTier.ANSI256

    return ColorTier.ANSI16
```

### Pattern 2: RGB-to-Tier Conversion
**What:** Define colors as RGB tuples, convert to appropriate escape sequence for detected tier.
**When to use:** Theme initialization.
**Example:**
```python
def rgb_to_ansi(r: int, g: int, b: int, tier: ColorTier) -> str:
    """Convert RGB to ANSI escape sequence for the given tier."""
    if tier == ColorTier.NONE:
        return ""
    if tier == ColorTier.TRUECOLOR:
        return f"\033[38;2;{r};{g};{b}m"
    if tier == ColorTier.ANSI256:
        # Convert to nearest 256-color index
        return f"\033[38;5;{_rgb_to_256(r, g, b)}m"
    # ANSI16: map to nearest basic color
    return _rgb_to_16(r, g, b)

def _rgb_to_256(r: int, g: int, b: int) -> int:
    """Map RGB to nearest xterm-256 color index.

    The 6x6x6 color cube occupies indices 16-231.
    Formula: 16 + 36*r_idx + 6*g_idx + b_idx
    where each index is round(val/255 * 5).
    Greyscale ramp at 232-255 for near-grey values.
    """
    # Check if near greyscale first
    if abs(r - g) < 10 and abs(g - b) < 10:
        grey = (r + g + b) // 3
        if grey < 8:
            return 16  # black end of cube
        if grey > 248:
            return 231  # white end of cube
        return 232 + round((grey - 8) / 247 * 23)

    # 6x6x6 cube
    ri = round(r / 255 * 5)
    gi = round(g / 255 * 5)
    bi = round(b / 255 * 5)
    return 16 + 36 * ri + 6 * gi + bi

def _rgb_to_16(r: int, g: int, b: int) -> str:
    """Map RGB to nearest ANSI 16 color escape sequence.

    Uses brightness and dominant channel to select from the 8+8 palette.
    """
    brightness = (r + g + b) / 3
    bright_prefix = "9" if brightness > 127 else "3"

    # Determine dominant channel
    if r > g and r > b:
        code = 1  # red
    elif g > r and g > b:
        code = 2  # green
    elif b > r and b > g:
        code = 4  # blue
    elif r > b:  # r ~= g
        code = 3  # yellow
    elif g > r:  # g ~= b
        code = 6  # cyan
    elif r > g:  # r ~= b
        code = 5  # magenta
    else:
        code = 7  # white/grey

    return f"\033[{bright_prefix}{code}m"
```

### Pattern 3: ANSI String Utilities
**What:** Functions that operate on visible text content, ignoring ANSI escape sequences.
**When to use:** Any time you need to measure, pad, or strip styled strings.
**Example:**
```python
import re

# Matches all ANSI escape sequences (CSI sequences and OSC)
_ANSI_RE = re.compile(r"\033\[[0-9;]*[A-Za-z]|\033\][^\033]*(?:\033\\|\007)")

def strip_ansi(s: str) -> str:
    """Remove all ANSI escape sequences from a string."""
    return _ANSI_RE.sub("", s)

def display_width(s: str) -> int:
    """Return the visible character count of a string, ignoring ANSI codes.

    Accounts for East Asian wide characters (CJK) which occupy 2 columns.
    """
    import unicodedata
    stripped = strip_ansi(s)
    width = 0
    for ch in stripped:
        eaw = unicodedata.east_asian_width(ch)
        width += 2 if eaw in ("W", "F") else 1
    return width

def pad_to_width(s: str, target_width: int, fill: str = " ") -> str:
    """Pad string to exact visible width, accounting for embedded ANSI codes.

    Like str.ljust() but ANSI-aware.
    """
    current = display_width(s)
    if current >= target_width:
        return s
    return s + fill * (target_width - current)
```

### Pattern 4: Terminal Width Detection
**What:** Get current terminal width at render time.
**When to use:** Before rendering any panel.
**Example:**
```python
import shutil

def get_terminal_width(default: int = 80, minimum: int = 40) -> int:
    """Get terminal width, clamped to a minimum.

    Uses shutil.get_terminal_size() which falls back to (80, 24) on failure.
    """
    width = shutil.get_terminal_size((default, 24)).columns
    return max(width, minimum)
```

### Anti-Patterns to Avoid
- **Caching terminal width at import time:** Terminal can be resized. Detect at render time.
- **Using `len()` on ANSI strings for alignment:** Always use `display_width()`.
- **Hardcoding escape sequences in rendering code:** Always go through theme; enables tier fallback and NO_COLOR.
- **Separate fg/bg conversion functions:** Keep one `rgb_to_ansi()` with a `bg=False` parameter if background is needed later. For now, foreground only.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ANSI sequence detection | Custom character-by-character parser | Regex `\033\[[0-9;]*[A-Za-z]` | Well-known pattern, handles all SGR/CSI sequences |
| Terminal size | `fcntl` ioctl calls | `shutil.get_terminal_size()` | Cross-platform, handles edge cases, provides defaults |
| 256-color mapping | Lookup table of all 256 colors | 6x6x6 cube formula + greyscale ramp | Formula is 3 lines, table would be 256 entries |

**Key insight:** The ANSI escape code format is standardized (ECMA-48). The regex pattern and SGR sequence format are well-established. Don't invent custom parsing.

## Common Pitfalls

### Pitfall 1: Incomplete ANSI Regex
**What goes wrong:** Regex misses certain sequences (OSC, cursor movement, etc.) causing display_width to be wrong.
**Why it happens:** ANSI has many sequence types beyond SGR colors.
**How to avoid:** Use a comprehensive regex: `\033\[[0-9;]*[A-Za-z]` covers all CSI sequences. Add `\033\][^\033]*(?:\033\\|\007)` for OSC if needed. For this project, CSI is sufficient since we only emit SGR color codes.
**Warning signs:** Panel borders misaligned when colored content is present.

### Pitfall 2: East Asian Wide Characters
**What goes wrong:** CJK characters occupy 2 terminal columns but `len()` counts them as 1.
**Why it happens:** Terminal emulators render CJK at double width per Unicode standard.
**How to avoid:** Use `unicodedata.east_asian_width()` in `display_width()`.
**Warning signs:** Not critical for this project (English-only UI), but including it costs almost nothing and future-proofs the utility.

### Pitfall 3: COLORTERM Not Set on SSH
**What goes wrong:** SSH to Raspberry Pi may not forward `COLORTERM`, causing truecolor detection to fail even though the local terminal supports it.
**Why it happens:** SSH does not automatically forward custom env vars. `COLORTERM` is not in the default `AcceptEnv` list.
**How to avoid:** Fallback chain is the solution: if COLORTERM missing, check TERM for 256color, then fall back to ANSI 16. ANSI 16 always works on any color-capable terminal. Users can set `FORCE_COLOR=1` or add `SendEnv COLORTERM` to SSH config.
**Warning signs:** Colors look different over SSH vs local terminal.

### Pitfall 4: 256-Color Greyscale Mapping
**What goes wrong:** Near-grey RGB values (like the mockup's `100;120;130` subtle color) map to wrong cube entry instead of greyscale ramp.
**Why it happens:** The 6x6x6 cube has large gaps; greyscale ramp (232-255) gives better resolution for near-neutral colors.
**How to avoid:** Check if R, G, B are within ~10 of each other before using the cube formula. If so, use the greyscale ramp.
**Warning signs:** Subtle/dim colors look wrong in 256-color mode.

### Pitfall 5: Background Color SGR Format
**What goes wrong:** Using `38` (foreground) code for background colors.
**Why it happens:** Copy-paste error; foreground is `38;2;R;G;B`, background is `48;2;R;G;B`.
**How to avoid:** If background colors are ever needed, use a `bg` parameter in `rgb_to_ansi()`. Currently the mockup only uses foreground colors.
**Warning signs:** N/A for Phase 10 (no backgrounds used).

## Code Examples

### Complete Palette from Mockup
```python
# Source: .working/UI-working/zen_mockup.py
# All colors defined as RGB tuples for tier-independent storage
PALETTE = {
    # Structure
    "border":  (100, 160, 180),  # muted teal
    "header":  (130, 200, 220),  # bright cyan
    "label":   (140, 180, 160),  # sage green
    "prompt":  (180, 220, 200),  # warm mint

    # Data
    "text":    (200, 210, 215),  # light grey
    "value":   (220, 225, 230),  # near-white
    "subtle":  (100, 120, 130),  # dim grey

    # Semantic
    "green":   (80, 200, 120),   # positive
    "yellow":  (220, 190, 60),   # warning
    "red":     (200, 80, 80),    # negative
}
```

### Theme Dataclass Upgrade Pattern
```python
@dataclass
class Theme:
    """Upgraded theme with tier-aware colors.

    Constructed via get_theme() which detects tier and converts RGB values.
    """
    # Panel structure
    border: str      # panel borders
    header: str      # panel titles (bold)
    label: str       # keys, labels
    prompt: str      # input prompts

    # Content
    text: str        # body text
    value: str       # data values
    subtle: str      # dim/secondary

    # Semantic (kept from v2.1 for message formatting)
    success: str     # [OK] messages
    warning: str     # [!!] warnings
    error: str       # [FAIL] errors
    info: str        # [section] info
    phase: str       # [Discovery], etc.

    # Modifiers
    bold: str
    dim: str
    reset: str

    # Metadata
    tier: ColorTier
```

### Terminal Width Usage Pattern
```python
def render_something():
    width = get_terminal_width()
    panel_width = min(width - 2, 72)  # Max 72, leave 2 char margin
    # ... render at panel_width
```

## State of the Art

| Old Approach (v2.1) | Current Approach (v3.0) | When Changed | Impact |
|---------------------|-------------------------|--------------|--------|
| ANSI 16 bright codes (`\033[92m`) | Truecolor RGB (`\033[38;2;R;G;Bm`) | Phase 10 | Richer palette matching mockup |
| `len()` for string width | `display_width()` with ANSI stripping | Phase 10 | Correct panel alignment |
| No terminal width detection | `get_terminal_width()` at render time | Phase 10 | Adaptive panel sizing |
| Binary color/no-color | 4-tier detection (truecolor/256/16/none) | Phase 10 | Graceful degradation |

**Preserved from v2.1:**
- `NO_COLOR` / `FORCE_COLOR` env var support
- `supports_color()` function (refactored into `detect_color_tier()`)
- Windows VT mode enabling
- Lazy singleton caching via `get_theme()` / `reset_theme()`
- `clear_screen()` function (unchanged)

## Open Questions

1. **Bold modifier with truecolor**
   - What we know: Bold (`\033[1m`) can be combined with truecolor (`\033[1;38;2;R;G;Bm`) via a single sequence or two separate sequences.
   - What's unclear: Whether the mockup's `HEADER` style (which uses `\033[1;38;2;...m`) should be stored as bold+color combined or as separate theme fields.
   - Recommendation: Store bold as a separate modifier. The `header` field in the theme includes bold inline in its escape sequence (matching the mockup's approach). This keeps the pattern simple.

2. **Background colors for status badges**
   - What we know: The mockup uses foreground-only colors. Future phases might want subtle background tinting for status badges.
   - What's unclear: Whether `rgb_to_ansi()` needs a `bg` parameter now.
   - Recommendation: Add `bg=False` parameter to `rgb_to_ansi()` now. Costs one `if` statement, avoids refactoring later. Use `48;2;R;G;B` for background.

## Sources

### Primary (HIGH confidence)
- Python `re` module documentation - ANSI CSI sequence format is ECMA-48 standard
- Python `shutil.get_terminal_size()` documentation - fallback behavior confirmed
- Python `unicodedata.east_asian_width()` documentation - width categories confirmed
- Python `os.get_terminal_size()` documentation - raises `OSError` when not a terminal
- Existing codebase: `kflash/theme.py` - current v2.1 implementation reviewed
- Existing mockup: `.working/UI-working/zen_mockup.py` - exact RGB values extracted

### Secondary (MEDIUM confidence)
- ECMA-48 standard for SGR sequence format (`ESC [ params m`)
- `COLORTERM` env var convention for truecolor detection (de facto standard, not formal spec)
- xterm-256 color cube formula (16 + 36r + 6g + b) - widely documented

### Tertiary (LOW confidence)
- SSH `COLORTERM` forwarding behavior - varies by SSH client/server configuration

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all stdlib, well-documented APIs
- Architecture: HIGH - patterns are straightforward, mockup provides exact values
- Pitfalls: HIGH - known terminal rendering issues, well-documented solutions

**Research date:** 2026-01-29
**Valid until:** 2026-03-01 (stable domain, no external dependencies)
