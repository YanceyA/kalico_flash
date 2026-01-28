"""Centralized terminal styling with ANSI color support.

Provides a Theme dataclass with semantic style names (e.g., theme.success not
theme.green) and automatic terminal capability detection. Follows the NO_COLOR
standard (https://no-color.org/) for accessibility.

Usage:
    t = get_theme()
    print(f"{t.success}[OK]{t.reset} Operation complete")
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass

# ANSI escape codes (use Theme dataclass fields, not these directly)
RESET = "\033[0m"
_GREEN = "\033[92m"   # Bright green
_YELLOW = "\033[93m"  # Bright yellow
_RED = "\033[91m"     # Bright red
_CYAN = "\033[96m"    # Bright cyan
_BOLD = "\033[1m"     # Bold
_DIM = "\033[2m"      # Dim/faint


@dataclass
class Theme:
    """Theme with semantic style definitions.

    All fields contain ANSI escape sequences (or empty strings for no-color mode).
    Access via get_theme() to ensure correct detection of terminal capabilities.
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


# Pre-instantiated theme instances
_color_theme = Theme()

_no_color_theme = Theme(
    success="",
    warning="",
    error="",
    info="",
    phase="",
    marker_reg="",
    marker_new="",
    marker_blk="",
    marker_dup="",
    marker_num="",
    menu_title="",
    menu_border="",
    prompt="",
    bold="",
    dim="",
    reset="",
)


def _enable_windows_vt_mode() -> bool:
    """Enable ANSI escape code processing on Windows 10+.

    Uses ctypes to call SetConsoleMode with ENABLE_VIRTUAL_TERMINAL_PROCESSING.
    Returns True if successful, False if unsupported or failed.
    """
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        STD_OUTPUT_HANDLE = -11
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

        handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
        return True
    except Exception:
        return False


def supports_color() -> bool:
    """Detect if terminal supports ANSI colors.

    Detection signals (in order):
    1. NO_COLOR env var set -> False (https://no-color.org/)
    2. FORCE_COLOR env var set -> True (user override)
    3. stdout not a TTY -> False (piped/redirected)
    4. TERM == 'dumb' -> False
    5. Windows -> attempt VT mode enable, return success
    6. Unix-like TTY -> True (assume color support)
    """
    # NO_COLOR takes priority (accessibility standard)
    if os.environ.get("NO_COLOR"):
        return False

    # FORCE_COLOR overrides everything else
    if os.environ.get("FORCE_COLOR"):
        return True

    # Non-TTY (piped, redirected) - no color
    if not sys.stdout.isatty():
        return False

    # Dumb terminal
    if os.environ.get("TERM") == "dumb":
        return False

    # Windows: try enabling VT mode
    if sys.platform == "win32":
        return _enable_windows_vt_mode()

    # Unix TTY: assume color support
    return True


# Cached singleton
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


def clear_screen() -> None:
    """Clear terminal screen, preserving scrollback buffer where possible.

    Implementation:
    - Unix: clear -x if available, else ANSI fallback
    - Windows with VT: ANSI escape sequence
    - Windows without VT: cmd /c cls
    """
    if sys.platform == "win32":
        if supports_color():
            # VT mode enabled, use ANSI
            print("\033[H\033[J", end="", flush=True)
        else:
            subprocess.run(["cmd", "/c", "cls"], check=False)
    else:
        # Unix: clear -x preserves scrollback
        result = subprocess.run(
            ["clear", "-x"],
            capture_output=True,
        )
        if result.returncode != 0:
            # Fallback to ANSI
            print("\033[H\033[J", end="", flush=True)
