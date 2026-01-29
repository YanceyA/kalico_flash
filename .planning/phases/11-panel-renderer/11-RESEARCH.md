# Phase 11: Panel Renderer - Research

**Researched:** 2026-01-29
**Domain:** Terminal panel rendering with Unicode box-drawing (Python 3.9+ stdlib only)
**Confidence:** HIGH

## Summary

Phase 11 builds pure rendering functions that produce bordered panels with Unicode box-drawing characters, two-column layouts, spaced letter headers, and step dividers. All functions return multi-line strings — no screen management, no input handling. The domain is well-understood: Python's `textwrap` module provides wrapping/indentation, and Phase 10's `ansi.py` provides ANSI-aware string utilities. Unicode box-drawing characters (U+2500..U+257F) are standardized, but terminal rendering has known pitfalls around font alignment and gaps between characters.

The codebase already has box-drawing experience in `tui.py` (sharp corners: ┌─┐), but Phase 11 requires rounded corners (╭─╮) per the zen mockup. The key challenge is ANSI-aware width calculation for panel borders when content contains colored text — Phase 10's `display_width()` and `pad_to_width()` solve this. Two-column layout is a manual algorithm: split items into balanced columns, compute adaptive column widths based on content, render with whitespace gap.

**Primary recommendation:** Create `kflash/panels.py` with stdlib-only rendering functions: `render_panel()` (rounded borders, header, content), `render_two_column()` (balanced columns with adaptive widths), `render_step_divider()` (partial-width dashed line). Use Phase 10's ANSI utilities throughout. Store Unicode box chars in module constants for easy ASCII fallback if needed later.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `textwrap` | stdlib | Text wrapping, indentation | Standard for paragraph wrapping, `initial_indent`/`subsequent_indent` for list formatting |
| Phase 10 `ansi.py` | internal | ANSI-aware width/padding | Already implemented: `display_width()`, `pad_to_width()`, `strip_ansi()` |
| Phase 10 `theme.py` | internal | Colors from truecolor palette | Provides `theme.border`, `theme.header`, `theme.label`, `theme.subtle` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python `shutil` | stdlib | Terminal width detection | Via Phase 10's `get_terminal_width()` |
| Python `math` | stdlib | Rounding for centering | `math.floor()` / `math.ceil()` for padding calculations |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual box-drawing | `asciitree` library | asciitree provides BOX_LIGHT, BOX_HEAVY styles but adds dependency; manual gives full control over rounded corners |
| Manual two-column | `Rich` Layout/Columns | Rich is excellent but violates stdlib-only constraint; manual is 30 lines of code |
| `textwrap` | Manual word-wrap | `textwrap` handles edge cases (long words, hyphenation) better than naive split |

**Installation:**
None — stdlib only, Phase 10 already implemented ANSI utilities.

## Architecture Patterns

### Recommended Module Structure
```
kflash/
├── ansi.py          # [Phase 10] ANSI-aware string utilities
├── theme.py         # [Phase 10] Truecolor palette and Theme dataclass
└── panels.py        # [Phase 11] NEW: Pure rendering functions
```

### Pattern 1: Rounded Border Panel with Header
**What:** Render a multi-line panel with rounded Unicode corners (╭╮╰╯), spaced letter header in top border, colored content.
**When to use:** Device list panels, action menus, status panels.
**Example:**
```python
from kflash.ansi import display_width, pad_to_width, get_terminal_width
from kflash.theme import get_theme

# Unicode box-drawing constants (rounded corners)
BOX_ROUNDED = {
    "tl": "╭",  # top-left
    "tr": "╮",  # top-right
    "bl": "╰",  # bottom-left
    "br": "╯",  # bottom-right
    "h": "─",   # horizontal
    "v": "│",   # vertical
}

def render_panel(
    header: str,
    content_lines: list[str],
    max_width: int = 80,
    padding: int = 2,
) -> str:
    """Render a bordered panel with rounded corners and spaced header.

    Args:
        header: Panel title (will be uppercased and spaced)
        content_lines: List of content lines (may contain ANSI codes)
        max_width: Maximum panel width (default 80)
        padding: Inner padding on each side (default 2)

    Returns:
        Multi-line string ready for printing.
    """
    theme = get_theme()
    box = BOX_ROUNDED

    # Spaced header: "devices" -> "[ D E V I C E S ]"
    spaced = " ".join(header.upper())
    header_text = f"[ {spaced} ]"
    header_display = f"{theme.header}{header_text}{theme.reset}"
    header_width = len(header_text)  # Plain width for calculation

    # Calculate inner width based on content
    content_widths = [display_width(line) for line in content_lines]
    needed_width = max(content_widths + [header_width])
    inner_width = min(needed_width + 2 * padding, max_width - 2)  # -2 for border chars

    lines = []

    # Top border with header (left-aligned in border)
    header_pad = inner_width - header_width
    lines.append(
        f"{theme.border}{box['tl']}{header_display}{theme.border}{box['h'] * header_pad}{box['tr']}{theme.reset}"
    )

    # Content lines with padding and ANSI-aware alignment
    for line in content_lines:
        padded = " " * padding + line
        aligned = pad_to_width(padded, inner_width - padding)
        lines.append(f"{theme.border}{box['v']}{theme.reset}{aligned}{theme.border}{box['v']}{theme.reset}")

    # Bottom border
    lines.append(
        f"{theme.border}{box['bl']}{box['h'] * inner_width}{box['br']}{theme.reset}"
    )

    return "\n".join(lines)
```

### Pattern 2: Two-Column Layout with Balanced Rows
**What:** Split a list of items into two columns with adaptive widths and even row distribution.
**When to use:** Action menus, device lists with many items.
**Example:**
```python
def render_two_column(
    items: list[tuple[str, str]],  # (number, label) pairs
    gap: int = 4,
) -> list[str]:
    """Render items in two balanced columns.

    Args:
        items: List of (number, label) tuples (e.g., ("1", "Add Device"))
        gap: Whitespace gap between columns (default 4)

    Returns:
        List of formatted lines (no panel borders — caller adds those).
    """
    if not items:
        return []

    # Split into two balanced columns
    mid = (len(items) + 1) // 2  # Round up for left column
    left_items = items[:mid]
    right_items = items[mid:]

    # Format items: "#1 ▸ Add Device"
    theme = get_theme()
    arrow = f"{theme.subtle}▸{theme.reset}"

    def format_item(num: str, label: str) -> str:
        return f"{theme.label}{num}{theme.reset} {arrow} {theme.text}{label}{theme.reset}"

    left_col = [format_item(n, l) for n, l in left_items]
    right_col = [format_item(n, l) for n, l in right_items]

    # Calculate column widths (ANSI-aware)
    left_width = max(display_width(item) for item in left_col)

    # Render rows
    lines = []
    for i in range(mid):
        left = pad_to_width(left_col[i], left_width) if i < len(left_col) else " " * left_width
        right = right_col[i] if i < len(right_col) else ""
        lines.append(f"{left}{' ' * gap}{right}")

    return lines
```

### Pattern 3: Step Divider with Centered Label
**What:** Partial-width dashed line with step label centered in line.
**When to use:** Flash workflow progress, multi-step operations.
**Example:**
```python
def render_step_divider(
    label: str,
    width: int = 60,  # Partial width, ~60% of panel
    dash_char: str = "┄",
) -> str:
    """Render a step divider line with centered label.

    Args:
        label: Step label (e.g., "step 1", "1/2 Octopus Pro")
        width: Total divider width including label (default 60)
        dash_char: Unicode dashed line character (default ┄)

    Returns:
        Single formatted line.
    """
    theme = get_theme()
    label_text = f" {label} "
    label_width = len(label_text)

    # Calculate dashes on each side
    dash_total = width - label_width
    dash_left = dash_total // 2
    dash_right = dash_total - dash_left

    left_dashes = dash_char * dash_left
    right_dashes = dash_char * dash_right

    return f"{theme.subtle}{left_dashes}{theme.dim}{label_text}{theme.reset}{theme.subtle}{right_dashes}{theme.reset}"
```

### Pattern 4: Panel Centering and Adaptive Width
**What:** Center a panel in the terminal when terminal is wider than panel max width.
**When to use:** All panels — provides consistent look across terminal sizes.
**Example:**
```python
def center_panel(panel_lines: list[str], terminal_width: int) -> str:
    """Center panel lines in terminal.

    Args:
        panel_lines: List of rendered panel lines
        terminal_width: Current terminal width from get_terminal_width()

    Returns:
        Multi-line string with each line left-padded for centering.
    """
    # Find max visual width (ANSI-aware)
    max_line_width = max(display_width(line) for line in panel_lines)

    if max_line_width >= terminal_width:
        # No room to center, return as-is
        return "\n".join(panel_lines)

    # Calculate left padding for centering
    left_pad = (terminal_width - max_line_width) // 2
    padding = " " * left_pad

    return "\n".join(padding + line for line in panel_lines)
```

### Anti-Patterns to Avoid
- **Using `len()` for border alignment:** Always use `display_width()` from Phase 10. Colored content breaks `len()` calculations.
- **Hardcoding box characters in rendering functions:** Store in module-level constants (easy to swap for ASCII fallback if Unicode issues arise).
- **Building strings with `+=` in loops:** Use list comprehension + `"\n".join()` for multi-line output.
- **Centering header in top border with naive math:** ANSI codes in header text mean visible width ≠ string length. Strip ANSI or calculate plain text width separately.
- **Tight coupling to theme colors:** Functions should accept theme as argument or get it via `get_theme()` — don't import specific color values.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Text wrapping for long content | Character-by-character loop | `textwrap.fill()` or `textwrap.wrap()` | Handles long words, hyphenation, edge cases |
| ANSI escape stripping | Custom regex or char loop | Phase 10 `strip_ansi()` | Already implemented, tested regex pattern |
| Visible width of colored text | `len()` with manual ANSI subtraction | Phase 10 `display_width()` | Handles CJK wide chars, tested |
| String padding to exact width | Manual space concatenation | Phase 10 `pad_to_width()` | ANSI-aware, handles edge cases |
| Terminal width detection | `os.environ["COLUMNS"]` | Phase 10 `get_terminal_width()` | Fallback defaults, minimum clamp |

**Key insight:** Panel rendering requires ANSI-aware string operations at every step. Phase 10 provides the primitives — use them everywhere. Don't reimplement width calculation or padding logic.

## Common Pitfalls

### Pitfall 1: Unicode Box-Drawing Gaps
**What goes wrong:** Box-drawing characters may not "touch" — small gaps appear between vertical or horizontal lines.
**Why it happens:** Font rendering isn't designed for perfect alignment. Hinting processes at different sizes/settings cause misalignment. Terminal emulators may render box-drawing characters with slight offsets.
**How to avoid:** Accept that gaps may occur on some terminals/fonts. Modern terminals (Kitty, Wezterm, Alacritty) use custom rendering for box-drawing to eliminate gaps, but older terminals may show them. Rounded corners (╭╮╰╯) are more forgiving than sharp corners because curves hide sub-pixel misalignment better than hard edges.
**Warning signs:** Panels look "broken" on some terminals but perfect on others. User reports visual issues on Windows or older SSH clients.

### Pitfall 2: Header Width Calculation with ANSI Codes
**What goes wrong:** Top border is too short or too long because header width calculation includes invisible ANSI escape sequences.
**Why it happens:** Styling the header text (e.g., `theme.header + text + theme.reset`) adds ANSI codes that aren't visible but count in `len()`.
**How to avoid:** Calculate width from *plain* header text, store it separately, then apply styling to the display version. Example: `header_width = len(header_text)` before adding `theme.header`.
**Warning signs:** Top border length doesn't match bottom border. Header text appears off-center or border chars misaligned.

### Pitfall 3: Two-Column Row Imbalance
**What goes wrong:** Left column has many more rows than right column, or vice versa.
**Why it happens:** Using integer division without rounding up for left column. Example: 7 items split as 3/4 instead of 4/3.
**How to avoid:** Use `mid = (len(items) + 1) // 2` to round up for the left column. This ensures left has ≥ right row count.
**Warning signs:** Two-column layout looks visually unbalanced — one column much longer than the other.

### Pitfall 4: Content Wider Than Panel
**What goes wrong:** Content line is wider than panel inner width, breaking right border alignment.
**Why it happens:** Not validating content width before rendering. Long device names or status messages exceed max width.
**How to avoid:** Either (1) wrap content with `textwrap.fill()` before passing to panel renderer, or (2) truncate with ellipsis. Panel renderer can't fix this — caller must pre-process content.
**Warning signs:** Right border `│` appears mid-line or misaligned vertically.

### Pitfall 5: Step Divider Width Mismatch
**What goes wrong:** Step divider is wider than panel content area, or label is longer than divider width.
**Why it happens:** Hardcoded divider width doesn't account for label length or panel width.
**How to avoid:** Accept panel `inner_width` as argument to `render_step_divider()` and scale divider to ~60% of that. Validate `label_width < width` and truncate or abbreviate label if needed.
**Warning signs:** Divider extends beyond panel borders or label overwrites dashes.

### Pitfall 6: Monospaced Font Assumption on Windows
**What goes wrong:** Box-drawing characters render in sans-serif font instead of monospaced, breaking alignment.
**Why it happens:** Windows `cmd.exe` or PowerShell may default to Consolas (monospaced) but Unicode chars fall back to Arial (proportional). Browser-based terminals may use different fonts for box-drawing.
**How to avoid:** Can't fix at code level — this is terminal/font config. Document that kalico-flash requires a monospaced Unicode-capable font (Cascadia Code, JetBrains Mono, etc.). Provide ASCII fallback box chars if Unicode issues reported widely.
**Warning signs:** Panels look perfect on Linux/macOS but broken on Windows. User reports "weird spacing" or "gaps everywhere."

## Code Examples

### Complete Panel Rendering Function
```python
# Source: Derived from Phase 11 context decisions and zen_mockup.py analysis
from kflash.ansi import display_width, pad_to_width, get_terminal_width
from kflash.theme import get_theme

BOX_ROUNDED = {
    "tl": "╭", "tr": "╮", "bl": "╰", "br": "╯",
    "h": "─", "v": "│",
}

def render_panel(
    header: str,
    content_lines: list[str],
    max_width: int = 80,
    padding: int = 2,
) -> str:
    """Render a bordered panel with rounded corners and spaced header.

    Content lines may contain ANSI escape codes. Width calculations are
    ANSI-aware via display_width() and pad_to_width().

    Args:
        header: Panel title (uppercased and spaced automatically)
        content_lines: Pre-formatted content lines
        max_width: Maximum total panel width including borders (default 80)
        padding: Horizontal padding inside border (default 2 chars each side)

    Returns:
        Multi-line string with borders, ready for print().
    """
    theme = get_theme()
    box = BOX_ROUNDED

    # Spaced header: "devices" -> "[ D E V I C E S ]"
    spaced = " ".join(header.upper())
    header_text = f"[ {spaced} ]"
    header_display = f"{theme.header}{header_text}{theme.reset}"
    header_plain_width = len(header_text)

    # Calculate inner width
    content_widths = [display_width(line) for line in content_lines]
    needed = max(content_widths + [header_plain_width]) + 2 * padding
    inner_width = min(needed, max_width - 2)  # -2 for left/right border

    lines = []

    # Top border with header
    header_pad = inner_width - header_plain_width
    lines.append(
        f"{theme.border}{box['tl']}{header_display}{theme.border}"
        f"{box['h'] * header_pad}{box['tr']}{theme.reset}"
    )

    # Content lines
    for line in content_lines:
        padded = " " * padding + line
        aligned = pad_to_width(padded, inner_width - padding)
        lines.append(
            f"{theme.border}{box['v']}{theme.reset}{aligned}"
            f"{theme.border}{box['v']}{theme.reset}"
        )

    # Bottom border
    lines.append(
        f"{theme.border}{box['bl']}{box['h'] * inner_width}{box['br']}{theme.reset}"
    )

    return "\n".join(lines)
```

### Two-Column Action Menu
```python
# Source: zen_mockup.py actions panel pattern
def render_action_menu(actions: list[tuple[str, str]]) -> list[str]:
    """Render actions in two columns with adaptive widths.

    Args:
        actions: List of (number, label) tuples

    Returns:
        List of formatted lines (caller wraps in panel).
    """
    theme = get_theme()
    arrow = f"{theme.subtle}▸{theme.reset}"

    def fmt(num: str, label: str) -> str:
        return f"{theme.label}{num}{theme.reset} {arrow} {theme.text}{label}{theme.reset}"

    mid = (len(actions) + 1) // 2
    left_items = [fmt(n, l) for n, l in actions[:mid]]
    right_items = [fmt(n, l) for n, l in actions[mid:]]

    left_width = max(display_width(item) for item in left_items)
    gap = 4

    lines = []
    for i in range(mid):
        left = pad_to_width(left_items[i], left_width)
        right = right_items[i] if i < len(right_items) else ""
        lines.append(f"  {left}{' ' * gap}{right}")

    return lines
```

### Step Divider Usage
```python
# Source: zen_mockup.py flash workflow dividers
def render_step_divider(label: str, total_width: int = 60) -> str:
    """Render partial-width step divider with centered label."""
    theme = get_theme()
    label_text = f" {label} "
    dash_total = total_width - len(label_text)
    dash_left = dash_total // 2
    dash_right = dash_total - dash_left

    return (
        f"{theme.subtle}{'┄' * dash_left}{theme.dim}{label_text}"
        f"{theme.reset}{theme.subtle}{'┄' * dash_right}{theme.reset}"
    )

# Usage in flash workflow
print(render_step_divider("step 1"))
print(f"  {theme.text}Building firmware...{theme.reset}")
print()
print(render_step_divider("step 2"))
```

## State of the Art

| Old Approach (v2.1) | Current Approach (v3.0) | When Changed | Impact |
|---------------------|-------------------------|--------------|--------|
| Sharp corners (┌─┐) | Rounded corners (╭─╮) | Phase 11 | Softer visual aesthetic matching mockup |
| No panel renderer | Pure rendering functions | Phase 11 | Separation of rendering from TUI logic |
| `len()` for alignment | `display_width()` from Phase 10 | Phase 11 | Correct alignment with ANSI colors |
| Hardcoded menu boxes | Reusable `render_panel()` | Phase 11 | Consistent panels across all screens |
| No two-column layout | Balanced column algorithm | Phase 11 | Better space usage for action menus |

**Preserved from v2.1:**
- Unicode box-drawing (no ASCII fallback yet — may add if Windows issues arise)
- Box character constants in module scope
- TTY detection for Unicode support (`tui.py` pattern)

**New patterns:**
- Spaced letter headers: `[ D E V I C E S ]`
- Step dividers with dashed lines and labels
- ANSI-aware width calculation throughout
- Pure rendering functions (return strings, no print)

## Open Questions

1. **ASCII Fallback for Box-Drawing**
   - What we know: Some Windows terminals or SSH sessions may render Unicode box-drawing poorly.
   - What's unclear: Whether kalico-flash should auto-detect and fall back to ASCII (+ instead of ╭) or rely on user terminal config.
   - Recommendation: Start with Unicode only (matching mockup). If user reports filed, add `BOX_ASCII` constants and detection logic similar to `tui.py`'s `_supports_unicode()`.

2. **Panel Width Clamping Strategy**
   - What we know: Context says "max width with centering — panels cap at a max width and center if terminal is wider."
   - What's unclear: Exact max width value (70? 80? 100?) and behavior when terminal is narrower than max.
   - Recommendation: Default `max_width=80` (matches standard terminal). When terminal is narrower, use full terminal width minus 2-char margin. Caller can override via parameter.

3. **Content Wrapping Responsibility**
   - What we know: Panel renderer accepts pre-formatted `content_lines`.
   - What's unclear: Should panel renderer auto-wrap long lines, or is that caller's job?
   - Recommendation: Caller's job. Panel renderer is a *rendering* primitive — content preparation (wrapping, truncation, formatting) happens in the layer above (Phases 12-14). Keeps functions pure and reusable.

4. **Empty Panel Handling**
   - What we know: Panels may have zero content lines (e.g., "No devices registered").
   - What's unclear: Should panel renderer add a blank line or minimum height?
   - Recommendation: Render exactly what's passed. If caller wants empty panel to have height, caller passes `[" "]` or `[""]`.

## Sources

### Primary (HIGH confidence)
- Python `textwrap` module documentation - [Official Python docs](https://docs.python.org/3/library/textwrap.html)
- Python `shutil.get_terminal_size()` documentation - Via Phase 10 implementation
- Existing codebase: `kflash/tui.py` - Box-drawing pattern with Unicode/ASCII detection
- Existing codebase: `kflash/ansi.py` - Phase 10 ANSI utilities (strip_ansi, display_width, pad_to_width)
- Existing mockup: `.working/UI-working/zen_mockup.py` - Exact panel structure and formatting
- Phase 11 context: `.planning/phases/11-panel-renderer/11-CONTEXT.md` - User decisions on borders, headers, columns

### Secondary (MEDIUM confidence)
- [Everything You Can Do with Python's textwrap Module](https://martinheinz.dev/blog/108) - Examples of initial_indent and subsequent_indent
- [CLI Formatting: Center Text In Terminal](https://medium.com/@bill.a.brown90/cli-formatting-center-text-in-terminal-6d476cf7d148) - Centering patterns
- [Box Drawing characters with examples](https://gist.github.com/flaviut/0db1aec4cadf2ef06455) - Unicode U+2500 range reference
- [Box drawing on the web](https://velvetcache.org/2024/02/12/box-drawing-on-the-web/) - Font rendering challenges

### Tertiary (LOW confidence)
- [Getting custom box drawing characters to line up perfectly](https://github.com/kovidgoyal/kitty/discussions/7680) - Kitty terminal custom rendering discussion
- [Better unicode box drawing unicode characters rendering](https://github.com/alacritty/alacritty/issues/7067) - Alacritty rendering issues
- Various forum posts on Unicode box-drawing gaps - Platform-specific rendering variability

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - stdlib only, Phase 10 utilities verified
- Architecture: HIGH - clear patterns, mockup provides exact structure
- Pitfalls: MEDIUM-HIGH - ANSI alignment is well-understood (Phase 10), Unicode font issues are documented but platform-specific

**Research date:** 2026-01-29
**Valid until:** 2026-03-01 (stable domain, stdlib-only, no external dependencies)
