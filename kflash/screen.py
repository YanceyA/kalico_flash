"""Main screen data aggregation and rendering for the TUI.

Produces three panel-based sections (Status, Devices, Actions) as a single
printable string. All device data is received as parameters — no direct USB
scanning — for testability and separation of concerns.

Uses Phase 11 panel primitives from kflash.panels for bordered rendering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .ansi import display_width
from .panels import center_panel, render_panel, render_two_column
from .theme import get_theme


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class DeviceRow:
    """A single device row for the main screen device list."""

    number: int  # Sequential number for selection (0 = not selectable)
    key: str  # Registry key or filename for unregistered
    name: str  # Display name
    mcu: str  # MCU type
    serial_path: str  # USB serial path or pattern
    version: Optional[str]  # Firmware version if known
    connected: bool  # Whether device is currently connected
    group: str  # "registered", "new", "blocked"


@dataclass
class ScreenState:
    """Complete state needed to render the main screen."""

    devices: list[DeviceRow] = field(default_factory=list)
    host_version: Optional[str] = None
    status_message: str = "Welcome to kalico-flash. Select an action below."
    status_level: str = "info"  # "info", "success", "error", "warning"


# ---------------------------------------------------------------------------
# Actions definition
# ---------------------------------------------------------------------------

ACTIONS: list[tuple[str, str]] = [
    ("F", "Flash Device"),
    ("A", "Add Device"),
    ("R", "Remove Device"),
    ("D", "Refresh Devices"),
    ("C", "Config"),
    ("B", "Flash All"),
    ("Q", "Quit"),
]


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def truncate_serial(path: str, max_width: int = 40) -> str:
    """Truncate a serial path to fit within max_width visible characters.

    If the path fits, return as-is. Otherwise keep the start and end
    with an ellipsis in the middle.
    """
    if len(path) <= max_width:
        return path
    # Reserve 3 chars for "..."
    available = max_width - 3
    left = available // 2
    right = available - left
    return path[:left] + "..." + path[-right:]


# ---------------------------------------------------------------------------
# Device list building
# ---------------------------------------------------------------------------

def build_device_list(
    registry_data,
    usb_devices: list,
    blocked_list: list[tuple[str, Optional[str]]],
    mcu_versions: Optional[dict[str, str]] = None,
) -> list[DeviceRow]:
    """Build a numbered device list grouped by status.

    Groups (in order):
    1. Registered connected (numbered starting at 1)
    2. Registered disconnected (numbered, continuing sequence)
    3. New / unregistered (numbered, continuing sequence)
    4. Blocked (number=0, not selectable)

    Args:
        registry_data: RegistryData with devices and blocked_devices.
        usb_devices: List of DiscoveredDevice from USB scan.
        blocked_list: Pre-built blocked patterns list.
        mcu_versions: Optional MCU version map from Moonraker.

    Returns:
        Ordered list of DeviceRow.
    """
    import fnmatch

    from .discovery import is_supported_device, match_devices

    if mcu_versions is None:
        mcu_versions = {}

    # Cross-reference registry against USB
    entry_matches: dict[str, list] = {}
    device_matches: dict[str, list] = {}
    for entry in registry_data.devices.values():
        matches = match_devices(entry.serial_pattern, usb_devices)
        entry_matches[entry.key] = matches
        for device in matches:
            device_matches.setdefault(device.filename, []).append(entry)

    matched_filenames = set(device_matches.keys())
    unmatched = [d for d in usb_devices if d.filename not in matched_filenames]

    # Helper to check blocked status
    def _is_blocked(filename: str) -> tuple[bool, str]:
        name = filename.lower()
        for pattern, reason in blocked_list:
            pat = pattern.lower()
            if not pat.startswith("*"):
                pat = "*" + pat
            if not pat.endswith("*"):
                pat = pat + "*"
            if fnmatch.fnmatch(name, pat):
                return True, reason or "Blocked device"
        return False, ""

    # Build groups
    registered_connected: list[DeviceRow] = []
    registered_disconnected: list[DeviceRow] = []
    new_devices: list[DeviceRow] = []
    blocked_devices: list[DeviceRow] = []

    for entry in registry_data.devices.values():
        matches = entry_matches.get(entry.key, [])
        connected = len(matches) > 0
        serial = matches[0].filename if matches else entry.serial_pattern
        version = mcu_versions.get(entry.mcu)

        row = DeviceRow(
            number=0,  # assigned later
            key=entry.key,
            name=entry.name,
            mcu=entry.mcu,
            serial_path=serial,
            version=version,
            connected=connected,
            group="registered",
        )
        if connected:
            registered_connected.append(row)
        else:
            registered_disconnected.append(row)

    for device in unmatched:
        blocked, reason = _is_blocked(device.filename)
        if blocked or not is_supported_device(device.filename):
            blocked_devices.append(DeviceRow(
                number=0,
                key=device.filename,
                name=device.filename,
                mcu="",
                serial_path=device.filename,
                version=None,
                connected=True,
                group="blocked",
            ))
        else:
            new_devices.append(DeviceRow(
                number=0,
                key=device.filename,
                name=device.filename,
                mcu="unknown",
                serial_path=device.filename,
                version=None,
                connected=True,
                group="new",
            ))

    # Assign sequential numbers
    counter = 1
    for row in registered_connected + registered_disconnected + new_devices:
        row.number = counter
        counter += 1
    # Blocked remain number=0

    return registered_connected + registered_disconnected + new_devices + blocked_devices


# ---------------------------------------------------------------------------
# Rendering functions
# ---------------------------------------------------------------------------

def render_device_row(row: DeviceRow) -> str:
    """Render a single device row with status icon and details."""
    theme = get_theme()

    # Status icon
    if row.connected:
        icon = f"{theme.success}\u25cf{theme.reset}"  # ● green
    else:
        icon = f"{theme.subtle}\u25cb{theme.reset}"  # ○ grey

    serial = truncate_serial(row.serial_path)

    if row.group == "blocked":
        return f"{icon}  {theme.subtle}{row.name}{theme.reset}"

    num = f"#{row.number}" if row.number > 0 else ""
    ver = row.version or ""

    parts = [icon]
    if num:
        parts.append(f" {theme.label}{num}{theme.reset}")
    parts.append(f"  {theme.text}{row.name}{theme.reset}")
    if row.mcu:
        parts.append(f" {theme.subtle}({row.mcu}){theme.reset}")
    parts.append(f"  {theme.subtle}{serial}{theme.reset}")
    if ver:
        parts.append(f"  {theme.value}{ver}{theme.reset}")

    return "".join(parts)


def render_status_panel(
    status_message: str = "Welcome to kalico-flash. Select an action below.",
    status_level: str = "info",
) -> str:
    """Render the Status panel with color-coded message."""
    theme = get_theme()

    level_colors = {
        "success": theme.success,
        "error": theme.error,
        "warning": theme.warning,
        "info": theme.text,
    }
    color = level_colors.get(status_level, theme.text)
    content = [f"{color}{status_message}{theme.reset}"]

    return render_panel("status", content)


def render_devices_panel(
    devices: list[DeviceRow],
    host_version: Optional[str] = None,
) -> str:
    """Render the Devices panel with grouped device rows."""
    theme = get_theme()

    if not devices:
        content = [
            f"{theme.subtle}No devices found. Connect a board and select Refresh.{theme.reset}"
        ]
        footer = _host_version_line(host_version)
        if footer:
            content.append("")
            content.append(footer)
        return render_panel("devices", content)

    content: list[str] = []

    # Group by group field, maintaining order
    groups: dict[str, list[DeviceRow]] = {}
    for row in devices:
        groups.setdefault(row.group, []).append(row)

    group_labels = {
        "registered": "Registered",
        "new": "New",
        "blocked": "Blocked",
    }

    first = True
    for group_key in ("registered", "new", "blocked"):
        rows = groups.get(group_key)
        if not rows:
            continue
        if not first:
            content.append("")
        first = False
        label = group_labels.get(group_key, group_key.title())
        content.append(f"{theme.label}{label}{theme.reset}")
        for row in rows:
            content.append(f"  {render_device_row(row)}")

    # Footer with host version
    footer = _host_version_line(host_version)
    if footer:
        content.append("")
        content.append(footer)

    return render_panel("devices", content)


def _host_version_line(host_version: Optional[str]) -> str:
    """Build the host version footer line."""
    theme = get_theme()
    if host_version:
        return f"{theme.subtle}Host Klipper: {host_version}{theme.reset}"
    return f"{theme.subtle}Host version: unavailable{theme.reset}"


def render_actions_panel() -> str:
    """Render the Actions panel with two-column key layout."""
    theme = get_theme()

    # Format each action as (key, label) for render_two_column
    items: list[tuple[str, str]] = []
    for key, label in ACTIONS:
        styled_label = f"{theme.text}{label}{theme.reset}"
        items.append((key, styled_label))

    lines = render_two_column(items)
    return render_panel("actions", lines)


def render_main_screen(state: ScreenState) -> str:
    """Render the complete main screen with Status, Devices, and Actions panels.

    Returns a single string ready for print().
    """
    panels = [
        render_status_panel(state.status_message, state.status_level),
        render_devices_panel(state.devices, state.host_version),
        render_actions_panel(),
    ]

    centered = [center_panel(p) for p in panels]
    return "\n\n".join(centered)
