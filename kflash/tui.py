"""Interactive TUI menu for kalico-flash.

Provides a panel-based main screen with single-keypress navigation and a
settings submenu when running without arguments.  Handles Unicode/ASCII
terminal detection, non-TTY fallback, invalid-input retry logic, and
error-resilient action dispatch.

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
    """Check if terminal supports Unicode box drawing."""
    lang = os.environ.get("LANG", "").upper()
    lc_all = os.environ.get("LC_ALL", "").upper()
    return "UTF-8" in lang or "UTF-8" in lc_all or "UTF8" in lang or "UTF8" in lc_all


def _get_box_chars() -> dict[str, str]:
    """Return the appropriate box-drawing character set for this terminal."""
    return UNICODE_BOX if _supports_unicode() else ASCII_BOX


# ---------------------------------------------------------------------------
# Menu rendering (kept for settings submenu)
# ---------------------------------------------------------------------------

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

    Used by the settings submenu. The main menu now uses panel rendering.
    """
    theme = get_theme()

    inner_items = [f" {num}) {label} " for num, label in options]
    inner_width = max(len(item) for item in inner_items)

    title_plain = "kalico-flash"
    title_width = len(title_plain) + 2
    inner_width = max(inner_width, title_width)

    title_display = f" {theme.menu_title}{title_plain}{theme.reset} "

    lines: list[str] = []

    pad_total = inner_width - title_width
    pad_left = pad_total // 2
    pad_right = pad_total - pad_left
    lines.append(
        box["tl"] + box["h"] * pad_left + title_display + box["h"] * pad_right + box["tr"]
    )

    lines.append(box["v"] + box["h"] * inner_width + box["v"])

    for item in inner_items:
        padded = item.ljust(inner_width)
        lines.append(box["v"] + padded + box["v"])

    lines.append(box["bl"] + box["h"] * inner_width + box["br"])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Input handling
# ---------------------------------------------------------------------------


def _getch() -> str:
    """Read a single keypress without requiring Enter.

    Returns lowercase character. Works on both Windows (msvcrt) and
    Unix (termios raw mode).
    """
    try:
        # Windows
        import msvcrt
        ch = msvcrt.getwch()
        return ch.lower()
    except ImportError:
        pass

    # Unix / Linux
    import tty
    import termios

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch.lower()


def _wait_for_key(timeout: float = 1.0) -> bool:
    """Wait for a keypress up to *timeout* seconds.

    Returns ``True`` if a key was pressed, ``False`` if the timeout expired.
    Cross-platform: uses ``msvcrt`` on Windows and ``select`` on Unix.
    """
    try:
        import msvcrt
        import time

        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if msvcrt.kbhit():
                msvcrt.getwch()  # consume
                return True
            time.sleep(0.05)
        return False
    except ImportError:
        pass

    import select
    import tty
    import termios

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if ready:
            sys.stdin.read(1)  # consume
            return True
        return False
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _countdown_return(seconds: float) -> None:
    """Display a countdown timer; any keypress skips immediately.

    If *seconds* is zero or negative the function returns instantly.
    Uses ``_wait_for_key`` for cross-platform non-blocking detection.
    """
    if seconds <= 0:
        return

    theme = get_theme()
    remaining = int(seconds)
    while remaining > 0:
        print(
            f"\r  {theme.subtle}Returning to menu in {remaining}s... "
            f"(press any key){theme.reset}  ",
            end="",
            flush=True,
        )
        if _wait_for_key(timeout=1.0):
            break
        remaining -= 1
    # Clear the countdown line
    print("\r" + " " * 60 + "\r", end="", flush=True)


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
# Screen state building
# ---------------------------------------------------------------------------


def _build_screen_state(registry, status_message: str, status_level: str):
    """Build a ScreenState by loading registry data and scanning USB devices.

    Returns (ScreenState, device_map) where device_map maps device number
    to DeviceRow for device-targeting actions.
    """
    from .screen import ScreenState, build_device_list
    from .discovery import scan_serial_devices
    from .flash import _build_blocked_list

    data = registry.load()
    usb_devices = scan_serial_devices()
    blocked_list = _build_blocked_list(data)

    # Fetch version info (best effort)
    mcu_versions = None
    host_version = None
    try:
        from .moonraker import get_mcu_versions, get_host_klipper_version
        mcu_versions = get_mcu_versions()
        if data.global_config:
            host_version = get_host_klipper_version(data.global_config.klipper_dir)
    except Exception:
        pass

    devices = build_device_list(data, usb_devices, blocked_list, mcu_versions)

    state = ScreenState(
        devices=devices,
        host_version=host_version,
        status_message=status_message,
        status_level=status_level,
    )

    # Build device_map: number -> DeviceRow (only numbered devices)
    device_map: dict[int, object] = {}
    for row in devices:
        if row.number > 0:
            device_map[row.number] = row

    return state, device_map


# ---------------------------------------------------------------------------
# Device number prompting
# ---------------------------------------------------------------------------


def _prompt_device_number(device_map: dict, out) -> str | None:
    """Prompt the user for a device number and return the device key.

    If only one device exists, auto-selects it. Allows up to 3 attempts.
    Returns the device key string or None if cancelled/invalid.
    """
    if not device_map:
        out.warn("No devices available.")
        return None

    # Auto-select if only one device
    if len(device_map) == 1:
        row = next(iter(device_map.values()))
        return row.key

    for attempt in range(3):
        try:
            num_str = input("  Device #: ").strip()
        except (EOFError, KeyboardInterrupt):
            return None

        if not num_str or num_str.lower() in ("q", "0"):
            return None

        try:
            num = int(num_str)
        except ValueError:
            remaining = 2 - attempt
            if remaining > 0:
                out.warn(f"Invalid number '{num_str}'. {remaining} attempts remaining.")
            continue

        if num in device_map:
            return device_map[num].key

        remaining = 2 - attempt
        if remaining > 0:
            out.warn(f"No device #{num}. {remaining} attempts remaining.")

    return None


# ---------------------------------------------------------------------------
# Action handlers (return status message tuples)
# ---------------------------------------------------------------------------


def _action_flash_device(registry, out, device_key: str) -> tuple[str, str]:
    """Flash a specific device. Returns (message, level)."""
    from .flash import cmd_flash

    try:
        result = cmd_flash(registry, device_key, out)
        if result == 0:
            entry = registry.get(device_key)
            name = entry.name if entry else device_key
            return (f"Flash: {name} flashed successfully", "success")
        else:
            return (f"Flash: failed for {device_key}", "error")
    except KeyboardInterrupt:
        return ("Flash: cancelled", "warning")
    except Exception as exc:
        return (f"Flash: {exc}", "error")


def _action_add_device(registry, out) -> tuple[str, str]:
    """Launch the add-device wizard. Returns (message, level)."""
    from .flash import cmd_add_device

    try:
        result = cmd_add_device(registry, out)
        if result == 0:
            return ("Device added successfully", "success")
        else:
            return ("Add device: cancelled or failed", "warning")
    except KeyboardInterrupt:
        return ("Add device: cancelled", "warning")
    except Exception as exc:
        return (f"Add device: {exc}", "error")


def _action_remove_device(registry, out, device_key: str) -> tuple[str, str]:
    """Remove a specific device. Returns (message, level)."""
    from .flash import cmd_remove_device

    try:
        result = cmd_remove_device(registry, device_key, out)
        if result == 0:
            return (f"Removed device '{device_key}'", "success")
        else:
            return (f"Remove: cancelled or failed for {device_key}", "warning")
    except KeyboardInterrupt:
        return ("Remove: cancelled", "warning")
    except Exception as exc:
        return (f"Remove: {exc}", "error")


# ---------------------------------------------------------------------------
# Main menu loop (panel-based)
# ---------------------------------------------------------------------------


def run_menu(registry, out) -> int:
    """Main interactive menu loop with panel-based screen.

    Displays a panel-based main screen with Status, Devices, and Actions
    panels. Single keypress selects actions. Device-targeting actions
    prompt for device number. Screen refreshes after every command.

    Returns 0 on normal exit.
    """
    # Non-TTY guard
    if not sys.stdin.isatty():
        print("kalico-flash: interactive menu requires a terminal.")
        print("Run with --help for usage information.")
        return 0

    from .screen import render_main_screen

    theme = get_theme()
    status_message = "Welcome to kalico-flash. Select an action below."
    status_level = "info"

    while True:
        try:
            # Build screen state (scans USB, loads registry)
            state, device_map = _build_screen_state(
                registry, status_message, status_level
            )

            # Render and display
            clear_screen()
            print()
            print(render_main_screen(state))
            print()
            print(f"  {theme.prompt}Press action key:{theme.reset} ", end="", flush=True)

            # Read single keypress
            try:
                key = _getch()
            except (EOFError, OSError):
                return 0

            # Handle Ctrl+C (comes as \x03 in raw mode)
            if key == "\x03":
                print()
                return 0

            # Dispatch
            if key == "q":
                return 0

            elif key == "f":
                print(key)
                device_key = _prompt_device_number(device_map, out)
                if device_key:
                    status_message, status_level = _action_flash_device(
                        registry, out, device_key
                    )
                    _countdown_return(registry.load().global_config.return_delay)
                else:
                    status_message = "Flash: no device selected"
                    status_level = "warning"

            elif key == "a":
                print(key)
                status_message, status_level = _action_add_device(registry, out)
                _countdown_return(registry.load().global_config.return_delay)

            elif key == "r":
                print(key)
                device_key = _prompt_device_number(device_map, out)
                if device_key:
                    status_message, status_level = _action_remove_device(
                        registry, out, device_key
                    )
                    _countdown_return(registry.load().global_config.return_delay)
                else:
                    status_message = "Remove: no device selected"
                    status_level = "warning"

            elif key == "d":
                print(key)
                status_message = "Devices refreshed"
                status_level = "info"

            elif key == "c":
                print(key)
                _config_screen(registry, out)
                status_message = "Returned from settings"
                status_level = "info"

            elif key == "b":
                print(key)
                status_message = "Flash All: not yet implemented"
                status_level = "warning"

            else:
                # Echo the key and show warning
                if key.isprintable():
                    print(key)
                    status_message = f"Unknown key '{key}'. Use F/A/R/D/C/B/Q."
                else:
                    print()
                    status_message = "Unknown key. Use F/A/R/D/C/B/Q."
                status_level = "warning"

        except KeyboardInterrupt:
            print()
            return 0


# ---------------------------------------------------------------------------
# Settings submenu (unchanged)
# ---------------------------------------------------------------------------

def _config_screen(registry, out) -> None:
    """Config screen with panel-based settings display and inline editing.

    Renders a status panel with instructions and a settings panel with 6
    numbered rows. Single keypress selects a setting to edit. Toggle settings
    flip immediately; numeric and path settings prompt for typed input.
    """
    from .screen import render_config_screen, SETTINGS
    from .models import GlobalConfig
    import dataclasses

    theme = get_theme()

    while True:
        data = registry.load()
        gc = data.global_config

        clear_screen()
        print()
        print(render_config_screen(gc))
        print()
        print(
            f"  {theme.prompt}Setting # (or Esc/B to return):{theme.reset} ",
            end="",
            flush=True,
        )

        try:
            key = _getch()
        except (EOFError, OSError):
            return

        # Ctrl+C
        if key == "\x03":
            return

        # Escape or B to return
        if key == "\x1b" or key == "b":
            return

        # Check for valid setting number
        if key in ("1", "2", "3", "4", "5", "6"):
            idx = int(key) - 1
            setting = SETTINGS[idx]
            field_key = setting["key"]
            current = getattr(gc, field_key)

            if setting["type"] == "toggle":
                # Flip immediately
                new_gc = dataclasses.replace(gc, **{field_key: not current})
                registry.save_global(new_gc)

            elif setting["type"] == "numeric":
                print(key)
                try:
                    raw = input(f"  {setting['label']} [{current}]: ").strip()
                except (EOFError, KeyboardInterrupt):
                    continue
                if not raw:
                    continue
                try:
                    val = float(raw)
                    if val < 0:
                        continue
                except ValueError:
                    continue
                new_gc = dataclasses.replace(gc, **{field_key: val})
                registry.save_global(new_gc)

            elif setting["type"] == "path":
                print(key)
                try:
                    raw = input(f"  {setting['label']} [{current}]: ").strip()
                except (EOFError, KeyboardInterrupt):
                    continue
                if not raw:
                    continue
                new_gc = dataclasses.replace(gc, **{field_key: raw})
                registry.save_global(new_gc)


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

    Returns:
        A 3-tuple ``(success, device_path, error_reason)``.
    """
    import time
    import fnmatch
    from .discovery import scan_serial_devices

    start = time.monotonic()
    last_dot_time = start

    if out is None:
        print("Verifying", end="", flush=True)

    while time.monotonic() - start < timeout:
        now = time.monotonic()
        if out is None and now - last_dot_time >= 2.0:
            print(".", end="", flush=True)
            last_dot_time = now

        devices = scan_serial_devices()
        for device in devices:
            if fnmatch.fnmatch(device.filename, serial_pattern):
                if out is None:
                    print()

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
        print()
    return (False, None, f"Timeout after {int(timeout)}s waiting for device")
