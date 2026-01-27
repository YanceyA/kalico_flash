"""Interactive TUI menu for kalico-flash.

Provides a numbered menu loop when running without arguments.
Handles Unicode/ASCII terminal detection and non-TTY fallback.

Exports:
    run_menu: Main menu loop entry point.
"""
from __future__ import annotations

import os
import sys


# ---------------------------------------------------------------------------
# Unicode / ASCII box-drawing detection
# ---------------------------------------------------------------------------

UNICODE_BOX: dict[str, str] = {
    "tl": "\u250c",   # top-left corner
    "tr": "\u2510",   # top-right corner
    "bl": "\u2514",   # bottom-left corner
    "br": "\u2518",   # bottom-right corner
    "h":  "\u2500",   # horizontal line
    "v":  "\u2502",   # vertical line
}

ASCII_BOX: dict[str, str] = {
    "tl": "+",
    "tr": "+",
    "bl": "+",
    "br": "+",
    "h":  "-",
    "v":  "|",
}


def _supports_unicode() -> bool:
    """Check if terminal supports Unicode box drawing.

    Inspects LANG and LC_ALL environment variables for UTF-8 indicators.
    """
    lang = os.environ.get("LANG", "").upper()
    lc_all = os.environ.get("LC_ALL", "").upper()
    return (
        "UTF-8" in lang
        or "UTF-8" in lc_all
        or "UTF8" in lang
        or "UTF8" in lc_all
    )


def _get_box_chars() -> dict[str, str]:
    """Return the appropriate box-drawing character set for this terminal."""
    return UNICODE_BOX if _supports_unicode() else ASCII_BOX


# ---------------------------------------------------------------------------
# Menu rendering
# ---------------------------------------------------------------------------

# Setup-first order per CONTEXT.md decision:
#   1=Add, 2=List, 3=Flash, 4=Remove, 5=Settings, 0=Exit
MENU_OPTIONS: list[tuple[str, str]] = [
    ("1", "Add Device"),
    ("2", "List Devices"),
    ("3", "Flash Device"),
    ("4", "Remove Device"),
    ("5", "Settings"),
    ("0", "Exit"),
]


def _render_menu(options: list[tuple[str, str]], box: dict[str, str]) -> str:
    """Render a numbered menu with box-drawing characters.

    Args:
        options: List of (number, label) tuples.
        box: Box-drawing character dict (Unicode or ASCII).

    Returns:
        Multi-line string ready for printing.
    """
    # Calculate inner width: " N) Label " with padding
    inner_items = [f" {num}) {label} " for num, label in options]
    inner_width = max(len(item) for item in inner_items)
    # Ensure minimum width for the title
    title = " kalico-flash "
    inner_width = max(inner_width, len(title))

    lines: list[str] = []

    # Top border with title centered
    pad_total = inner_width - len(title)
    pad_left = pad_total // 2
    pad_right = pad_total - pad_left
    lines.append(
        box["tl"]
        + box["h"] * pad_left
        + title
        + box["h"] * pad_right
        + box["tr"]
    )

    # Separator line after title
    lines.append(box["v"] + box["h"] * inner_width + box["v"])

    # Menu items
    for item in inner_items:
        padded = item.ljust(inner_width)
        lines.append(box["v"] + padded + box["v"])

    # Bottom border
    lines.append(box["bl"] + box["h"] * inner_width + box["br"])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Input handling
# ---------------------------------------------------------------------------

def _get_menu_choice(
    valid_choices: list[str], out, max_attempts: int = 3,
) -> str | None:
    """Get a valid menu choice with retry logic.

    Prompts the user for input, validates against ``valid_choices``, and
    retries up to ``max_attempts`` times on invalid input.  Typing ``q``
    is normalised to ``"0"`` (exit / back).

    Args:
        valid_choices: Acceptable input strings (e.g. ``["0","1","2"]``).
        out: Output interface for warning messages.
        max_attempts: Maximum number of attempts before giving up.

    Returns:
        A string from *valid_choices*, ``"0"`` (on ``q``), or ``None``
        if the user exceeded *max_attempts*.
    """
    for attempt in range(max_attempts):
        try:
            choice = input("Select option: ").strip().lower()
        except EOFError:
            return "0"

        if choice in ("q",):
            return "0"

        if choice in valid_choices:
            return choice

        remaining = max_attempts - attempt - 1
        if remaining > 0:
            out.warn(f"Invalid option '{choice}'. {remaining} attempts remaining.")
        else:
            out.warn(f"Invalid option '{choice}'. Too many invalid attempts.")

    return None


# ---------------------------------------------------------------------------
# Main menu loop
# ---------------------------------------------------------------------------

def run_menu(registry, out) -> int:
    """Main interactive menu loop.

    Displays a numbered menu and dispatches user selections.
    Returns 0 on normal exit (user chose Exit, typed 'q', or pressed Ctrl+C).

    Args:
        registry: Registry instance for device operations.
        out: Output interface (CliOutput or compatible).

    Returns:
        Exit code (always 0 for normal menu exit).
    """
    # Non-TTY guard: show help message instead of broken menu
    if not sys.stdin.isatty():
        print("kalico-flash: interactive menu requires a terminal.")
        print("Run with --help for usage information.")
        return 0

    box = _get_box_chars()
    menu_text = _render_menu(MENU_OPTIONS, box)

    while True:
        try:
            print()
            print(menu_text)
            print()

            choice = _get_menu_choice(
                ["0", "1", "2", "3", "4", "5"], out,
            )

            if choice is None:
                out.error("Too many invalid inputs. Exiting.")
                return 1

            if choice == "0":
                return 0

            # Dispatch to handler with error resilience
            try:
                if choice == "1":
                    _action_add_device(registry, out)
                elif choice == "2":
                    _action_list_devices(registry, out)
                elif choice == "3":
                    _action_flash_device(registry, out)
                elif choice == "4":
                    _action_remove_device(registry, out)
                elif choice == "5":
                    _settings_menu(registry, out)
            except KeyboardInterrupt:
                out.warn("Cancelled.")
            except Exception as exc:
                out.error(f"Action failed: {exc}")

        except KeyboardInterrupt:
            # Ctrl+C at the menu prompt exits cleanly per CONTEXT.md
            print()
            return 0


# ---------------------------------------------------------------------------
# Action stubs -- wired to real commands in Plan 02
# ---------------------------------------------------------------------------

def _action_add_device(registry, out) -> None:
    """Launch the add-device wizard."""
    # Late import to keep hub-and-spoke pattern
    from flash import cmd_add_device
    cmd_add_device(registry, out)


def _action_list_devices(registry, out) -> None:
    """Show registered devices with connection status."""
    from flash import cmd_list_devices
    cmd_list_devices(registry, out)


def _action_flash_device(registry, out) -> None:
    """Launch the flash workflow for an interactively-selected device."""
    from flash import cmd_flash
    cmd_flash(registry, None, out)


def _action_remove_device(registry, out) -> None:
    """Remove a registered device via numbered selection."""
    data = registry.load()
    devices = list(data.devices.items())

    if not devices:
        out.warn("No devices registered.")
        return

    out.info("Remove Device", "Select device to remove:")
    for i, (key, entry) in enumerate(devices, 1):
        out.info("", f"  {i}. {key} ({entry.name})")

    valid = [str(i) for i in range(1, len(devices) + 1)]
    choice = _get_menu_choice(valid, out, max_attempts=3)

    if choice is None or choice == "0":
        out.warn("Cancelled.")
        return

    idx = int(choice) - 1
    device_key = devices[idx][0]

    from flash import cmd_remove_device
    cmd_remove_device(registry, device_key, out)


def _action_settings(out) -> None:
    """Show settings (placeholder for future implementation)."""
    out.info("Settings", "Not implemented yet")
