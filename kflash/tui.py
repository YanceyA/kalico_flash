"""Interactive TUI menu for kalico-flash.

Provides a numbered main menu and settings submenu when running without
arguments.  Handles Unicode/ASCII terminal detection, non-TTY fallback,
invalid-input retry logic, and error-resilient action dispatch.

Exports:
    run_menu: Main menu loop entry point.
    wait_for_device: Post-flash device verification with polling.
"""

from __future__ import annotations

import os
import sys

from .theme import get_theme, clear_screen


# ---------------------------------------------------------------------------
# Unicode / ASCII box-drawing detection
# ---------------------------------------------------------------------------

UNICODE_BOX: dict[str, str] = {
    "tl": "\u250c",  # top-left corner
    "tr": "\u2510",  # top-right corner
    "bl": "\u2514",  # bottom-left corner
    "br": "\u2518",  # bottom-right corner
    "h": "\u2500",  # horizontal line
    "v": "\u2502",  # vertical line
}

ASCII_BOX: dict[str, str] = {
    "tl": "+",
    "tr": "+",
    "bl": "+",
    "br": "+",
    "h": "-",
    "v": "|",
}


def _supports_unicode() -> bool:
    """Check if terminal supports Unicode box drawing.

    Inspects LANG and LC_ALL environment variables for UTF-8 indicators.
    """
    lang = os.environ.get("LANG", "").upper()
    lc_all = os.environ.get("LC_ALL", "").upper()
    return "UTF-8" in lang or "UTF-8" in lc_all or "UTF8" in lang or "UTF8" in lc_all


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
    theme = get_theme()

    # Calculate inner width: " N) Label " with padding
    inner_items = [f" {num}) {label} " for num, label in options]
    inner_width = max(len(item) for item in inner_items)

    # Calculate title width using PLAIN text
    title_plain = "kalico-flash"
    title_width = len(title_plain) + 2  # +2 for spaces
    inner_width = max(inner_width, title_width)

    # Create styled title for display
    title_display = f" {theme.menu_title}{title_plain}{theme.reset} "

    lines: list[str] = []

    # Top border with styled title
    pad_total = inner_width - title_width
    pad_left = pad_total // 2
    pad_right = pad_total - pad_left
    lines.append(
        box["tl"] + box["h"] * pad_left + title_display + box["h"] * pad_right + box["tr"]
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
    valid_choices: list[str],
    out,
    max_attempts: int = 3,
    prompt: str = "Select option: ",
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
            choice = input(prompt).strip().lower()
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
            clear_screen()
            print()
            print(menu_text)
            print()

            choice = _get_menu_choice(
                ["0", "1", "2", "3", "4", "5"],
                out,
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
# Action handlers
# ---------------------------------------------------------------------------


def _action_add_device(registry, out) -> None:
    """Launch the add-device wizard."""
    # Late import to keep hub-and-spoke pattern
    from .flash import cmd_add_device

    cmd_add_device(registry, out)


def _action_list_devices(registry, out) -> None:
    """Show registered devices with connection status."""
    from .flash import cmd_list_devices

    cmd_list_devices(registry, out, from_menu=True)


def _action_flash_device(registry, out) -> None:
    """Launch the flash workflow for an interactively-selected device."""
    from .flash import cmd_flash

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

    valid = ["0"] + [str(i) for i in range(1, len(devices) + 1)]
    choice = _get_menu_choice(
        valid,
        out,
        max_attempts=3,
        prompt="Select device number (0/q to cancel): ",
    )

    if choice is None or choice == "0":
        out.warn("Cancelled.")
        return

    idx = int(choice) - 1
    device_key = devices[idx][0]

    from .flash import cmd_remove_device

    cmd_remove_device(registry, device_key, out)


# ---------------------------------------------------------------------------
# Settings submenu
# ---------------------------------------------------------------------------

SETTINGS_OPTIONS: list[tuple[str, str]] = [
    ("1", "Change Klipper directory"),
    ("2", "Change Katapult directory"),
    ("3", "View current settings"),
    ("4", "Toggle flash fallback (Katapult -> make flash)"),
    ("0", "Back to main menu"),
]


def _settings_menu(registry, out) -> None:
    """Settings submenu for path configuration.

    Displays a box-drawn submenu that lets the user change Klipper/Katapult
    source directories or view current global settings.  Returns to the
    main menu on ``0``, ``q``, or after too many invalid attempts.
    """
    box = _get_box_chars()
    settings_text = _render_menu(SETTINGS_OPTIONS, box)

    while True:
        clear_screen()
        print()
        print(settings_text)
        print()

        choice = _get_menu_choice(["0", "1", "2", "3", "4"], out)

        if choice is None or choice == "0":
            return

        if choice == "1":
            _update_path(registry, out, "klipper_dir", "Klipper source directory")
        elif choice == "2":
            _update_path(registry, out, "katapult_dir", "Katapult source directory")
        elif choice == "3":
            _view_settings(registry, out)
        elif choice == "4":
            _toggle_flash_fallback(registry, out)


def _update_path(registry, out, field: str, label: str) -> None:
    """Prompt for a new path value and persist it to the registry.

    Args:
        registry: Registry instance.
        out: Output interface.
        field: GlobalConfig field name (``klipper_dir`` or ``katapult_dir``).
        label: Human-readable label for the prompt.
    """
    data = registry.load()
    gc = data.global_config
    if gc is None:
        out.warn("No global config exists. Run Add Device first.")
        return

    current = getattr(gc, field)
    new_path = out.prompt(label, default=current)

    if new_path == current:
        out.info("Settings", "No change.")
        return

    from .models import GlobalConfig

    kwargs = {
        "klipper_dir": gc.klipper_dir,
        "katapult_dir": gc.katapult_dir,
        "default_flash_method": gc.default_flash_method,
        "allow_flash_fallback": gc.allow_flash_fallback,
    }
    kwargs[field] = new_path
    registry.save_global(GlobalConfig(**kwargs))
    out.success(f"{label} updated to: {new_path}")


def _view_settings(registry, out) -> None:
    """Display current global configuration values."""
    data = registry.load()
    gc = data.global_config
    if gc is not None:
        out.info("Settings", f"Klipper directory:      {gc.klipper_dir}")
        out.info("Settings", f"Katapult directory:     {gc.katapult_dir}")
        out.info(
            "Settings", f"Preferred flash method (global): {gc.default_flash_method}"
        )
        fallback_state = "enabled" if gc.allow_flash_fallback else "disabled"
        out.info("Settings", f"Flash fallback:         {fallback_state}")
    else:
        out.info("Settings", "No global configuration set. Run Add Device first.")


def _toggle_flash_fallback(registry, out) -> None:
    """Toggle global flash fallback behavior."""
    data = registry.load()
    gc = data.global_config
    if gc is None:
        out.warn("No global config exists. Run Add Device first.")
        return

    from .models import GlobalConfig

    new_value = not gc.allow_flash_fallback
    registry.save_global(
        GlobalConfig(
            klipper_dir=gc.klipper_dir,
            katapult_dir=gc.katapult_dir,
            default_flash_method=gc.default_flash_method,
            allow_flash_fallback=new_value,
        )
    )
    state = "enabled" if new_value else "disabled"
    out.success(f"Flash fallback {state}")


# ---------------------------------------------------------------------------
# Post-flash device verification
# ---------------------------------------------------------------------------


def wait_for_device(
    serial_pattern: str,
    timeout: float = 30.0,
    interval: float = 0.5,
    out=None,
) -> tuple[bool, str | None, str | None]:
    """Poll for device to reappear after flash.

    Prints progress dots every 2 seconds when ``out`` is None. Checks both
    device existence AND prefix (``Klipper_`` expected, ``katapult_`` means failure).

    Args:
        serial_pattern: Glob pattern to match device filename
            (e.g. ``usb-Klipper_stm32h723xx_*``).
        timeout: Maximum seconds to wait (default 30).
        interval: Seconds between polls (default 0.5).
        out: Optional output interface. If provided, progress dots are suppressed.

    Returns:
        A 3-tuple ``(success, device_path, error_reason)``:

        - ``(True, "/dev/...", None)`` -- device found with ``Klipper_`` prefix.
        - ``(False, "/dev/...", "...")`` -- device found but wrong state.
        - ``(False, None, "Timeout...")`` -- device never appeared.
    """
    import time
    import fnmatch
    from .discovery import scan_serial_devices

    start = time.monotonic()
    last_dot_time = start

    if out is None:
        print("Verifying", end="", flush=True)

    while time.monotonic() - start < timeout:
        # Progress dots every 2 seconds
        now = time.monotonic()
        if out is None and now - last_dot_time >= 2.0:
            print(".", end="", flush=True)
            last_dot_time = now

        # Scan for matching devices
        devices = scan_serial_devices()
        for device in devices:
            if fnmatch.fnmatch(device.filename, serial_pattern):
                if out is None:
                    print()  # Newline after dots

                filename_lower = device.filename.lower()
                if filename_lower.startswith("usb-klipper_"):
                    return (True, device.path, None)
                elif filename_lower.startswith("usb-katapult_"):
                    return (
                        False,
                        device.path,
                        "Device in bootloader mode (katapult)",
                    )
                else:
                    return (
                        False,
                        device.path,
                        f"Unexpected device prefix: {device.filename}",
                    )

        time.sleep(interval)

    if out is None:
        print()  # Newline after dots
    return (False, None, f"Timeout after {int(timeout)}s waiting for device")
