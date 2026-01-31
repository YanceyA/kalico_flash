"""Panel rendering primitives for TUI screens.

Pure functions that produce bordered panels, two-column layouts, spaced-letter
headers, and step dividers — all returning multi-line strings ready for print().

Uses ANSI-aware width calculations from kflash.ansi to ensure correct alignment
even when content contains color escape sequences.
"""

from __future__ import annotations

from kflash.ansi import (
    display_width,
    get_terminal_width,
    pad_to_width,
    supports_unicode,
)
from kflash.theme import get_theme

# ---------------------------------------------------------------------------
# Box-drawing characters (rounded corners)
# ---------------------------------------------------------------------------

BOX_ROUNDED: dict[str, str] = {
    "tl": "\u256d",  # ╭
    "tr": "\u256e",  # ╮
    "bl": "\u2570",  # ╰
    "br": "\u256f",  # ╯
    "h": "\u2500",  # ─
    "v": "\u2502",  # │
}

MAX_PANEL_WIDTH = 80


# ---------------------------------------------------------------------------
# Panel rendering
# ---------------------------------------------------------------------------


def _spaced_header(text: str) -> str:
    """Convert *text* to spaced uppercase letters in brackets.

    Example: ``"devices"`` -> ``"[ D E V I C E S ]"``
    """
    spaced = " ".join(text.upper())
    return f"[ {spaced} ]"


def render_panel(
    header: str,
    content_lines: list[str],
    max_width: int = MAX_PANEL_WIDTH,
    padding: int = 2,
) -> str:
    """Render a bordered panel with a spaced-letter header.

    Args:
        header: Header text (will be uppercased and spaced).
        content_lines: Lines of content (may contain ANSI codes).
        max_width: Maximum panel width in columns.
        padding: Horizontal padding inside the panel borders.

    Returns:
        Multi-line string with rounded Unicode borders.
    """
    theme = get_theme()
    b = BOX_ROUNDED

    # Build header display string (plain first for width calc)
    header_plain = _spaced_header(header)
    header_display = f"{theme.header}{header_plain}{theme.reset}"

    # Calculate inner width from content
    max_content_w = 0
    for line in content_lines:
        w = display_width(line)
        if w > max_content_w:
            max_content_w = w

    header_plain_w = display_width(header_plain)
    min_inner = max(max_content_w + 2 * padding, header_plain_w + 2)
    inner_width = min(min_inner, max_width - 2)
    # Ensure header fits
    if inner_width < header_plain_w + 2:
        inner_width = header_plain_w + 2

    lines: list[str] = []

    # Top border: ╭[ H E A D E R ]────────╮
    remaining = inner_width - header_plain_w
    top_fill = b["h"] * remaining
    lines.append(
        f"{theme.border}{b['tl']}{theme.reset}"
        f"{header_display}"
        f"{theme.border}{top_fill}{b['tr']}{theme.reset}"
    )

    # Content lines: │  content padded  │
    for line in content_lines:
        padded = " " * padding + line
        padded = pad_to_width(padded, inner_width - padding) + " " * padding
        # Clamp: ensure exactly inner_width visible columns
        padded = " " * padding + pad_to_width(line, inner_width - 2 * padding) + " " * padding
        lines.append(
            f"{theme.border}{b['v']}{theme.reset}{padded}{theme.border}{b['v']}{theme.reset}"
        )

    # Empty panel: add one blank line
    if not content_lines:
        blank = " " * inner_width
        lines.append(
            f"{theme.border}{b['v']}{theme.reset}{blank}{theme.border}{b['v']}{theme.reset}"
        )

    # Bottom border: ╰────────────────────╯
    bottom_fill = b["h"] * inner_width
    lines.append(f"{theme.border}{b['bl']}{bottom_fill}{b['br']}{theme.reset}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Two-column layout
# ---------------------------------------------------------------------------


def render_two_column(items: list[tuple[str, str]], gap: int = 4) -> list[str]:
    """Split items into two balanced columns with adaptive widths.

    Args:
        items: List of ``(number, label)`` tuples, e.g. ``("#1", "Flash Device")``.
        gap: Number of spaces between columns.

    Returns:
        List of formatted lines (no borders).
    """
    if not items:
        return []

    theme = get_theme()

    # Format each item
    def fmt(number: str, label: str) -> str:
        return f"{theme.label}{number}{theme.reset} {theme.subtle}\u25b8{theme.reset} {label}"

    formatted = [fmt(n, label) for n, label in items]

    if len(items) == 1:
        return [formatted[0]]

    mid = (len(items) + 1) // 2
    left = formatted[:mid]
    right = formatted[mid:]

    # Calculate left column width
    left_width = max(display_width(s) for s in left)

    result: list[str] = []
    for i, left_item in enumerate(left):
        line = pad_to_width(left_item, left_width)
        if i < len(right):
            line += " " * gap + right[i]
        result.append(line)

    return result


# ---------------------------------------------------------------------------
# Step divider
# ---------------------------------------------------------------------------


def render_step_divider(label: str, total_width: int | None = None) -> str:
    """Render a partial-width dashed line with centered label.

    Args:
        label: Text to center in the divider.
        total_width: Total character width (auto-detected if None).

    Returns:
        Single formatted line.
    """
    theme = get_theme()
    if total_width is None:
        total_width = get_terminal_width()
    dash = "\u2504" if supports_unicode() else "-"  # ┄ or -

    label_text = f" {label} "
    label_width = len(label_text)
    side = (total_width - label_width) // 2
    if side < 0:
        side = 0

    left_dashes = dash * side
    right_dashes = dash * (total_width - label_width - side)

    return (
        f"{theme.border}{left_dashes}{theme.reset}"
        f"{theme.dim}{label_text}{theme.reset}"
        f"{theme.border}{right_dashes}{theme.reset}"
    )


def render_action_divider(label: str = "") -> str:
    """Render a divider line to separate action output from menu.

    Args:
        label: Optional text to center in the divider. If provided, uses
               render_step_divider. If empty, produces a simple dashed line.

    Returns:
        Single formatted line.
    """
    if label:
        return render_step_divider(label)

    theme = get_theme()
    dash = "\u2504" if supports_unicode() else "-"  # ┄ or -
    width = get_terminal_width()
    return f"{theme.border}{dash * width}{theme.reset}"


def render_device_divider(index: int, total: int, name: str, total_width: int | None = None) -> str:
    """Render a labeled device divider: --- 1/3 DeviceName ---

    Args:
        index: 1-based device index.
        total: Total number of devices.
        name: Device display name.
        total_width: Override width (auto-detected if None).

    Returns:
        Single formatted line.
    """
    theme = get_theme()
    if total_width is None:
        total_width = get_terminal_width()
    dash = "\u2500" if supports_unicode() else "-"  # ─ or -
    label = f" {index}/{total} {name} "
    label_width = len(label)
    side_left = (total_width - label_width) // 2
    if side_left < 0:
        side_left = 0
    side_right = total_width - label_width - side_left
    if side_right < 0:
        side_right = 0
    return (
        f"{theme.border}{dash * side_left}{theme.reset}"
        f"{theme.border}{label}{theme.reset}"
        f"{theme.border}{dash * side_right}{theme.reset}"
    )


# ---------------------------------------------------------------------------
# Panel centering
# ---------------------------------------------------------------------------


def center_panel(panel_str: str, terminal_width: int | None = None) -> str:
    """Horizontally center a rendered panel in the terminal.

    Args:
        panel_str: Multi-line panel string from render_panel().
        terminal_width: Override terminal width (auto-detected if None).

    Returns:
        Panel string with leading spaces for centering.
    """
    if terminal_width is None:
        terminal_width = get_terminal_width()

    lines = panel_str.split("\n")
    max_w = max((display_width(line) for line in lines), default=0)

    if max_w >= terminal_width:
        return panel_str

    indent = " " * ((terminal_width - max_w) // 2)
    return "\n".join(indent + line for line in lines)
