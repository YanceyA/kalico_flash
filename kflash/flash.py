#!/usr/bin/env python3
"""CLI entry point for kalico-flash.

Unified tool for building and flashing Klipper firmware to USB-connected
MCU boards. Provides device registration, discovery, and full build/flash
workflow with phase-labeled output.

Usage:
    kflash --add-device        # Register a new board
    kflash --list-devices      # Show registered boards and status
    kflash --remove-device KEY # Remove a registered board
    kflash --device KEY        # Build and flash the named device
    kflash                     # Interactive menu (TTY) or help (non-TTY)

This is the CLI entry point. Core logic lives in:
    - registry.py: Device registry persistence
    - discovery.py: USB device scanning and matching
    - output.py: Pluggable output interface (CLI, future Moonraker)
    - models.py: Dataclass contracts for cross-module data
    - errors.py: Exception hierarchy
    - config.py: Kconfig caching and MCU parsing
    - build.py: Menuconfig and firmware compilation
    - service.py: Klipper service lifecycle management
    - flasher.py: Dual-method flash operations
    - tui.py: Interactive menu for no-args mode
"""

from __future__ import annotations

import argparse
import fnmatch
import shutil
import sys
from pathlib import Path


# Python version guard
if sys.version_info < (3, 9):
    sys.exit("Error: kalico-flash requires Python 3.9 or newer.")


VERSION = "0.1.0"

DEFAULT_BLOCKED_DEVICES = [
    ("usb-beacon_*", "Beacon probe (not a Klipper MCU)"),
]


def _normalize_pattern(pattern: str) -> str:
    return pattern.strip().lower()


def _build_blocked_list(registry_data) -> list[tuple[str, str | None]]:
    blocked = [(pattern, reason) for pattern, reason in DEFAULT_BLOCKED_DEVICES]
    for entry in getattr(registry_data, "blocked_devices", []):
        blocked.append((entry.pattern, entry.reason))
    return blocked


def _blocked_reason_for_filename(
    filename: str, blocked_list: list[tuple[str, str | None]]
) -> str | None:
    name = filename.lower()
    for pattern, reason in blocked_list:
        if fnmatch.fnmatch(name, _normalize_pattern(pattern)):
            return reason or "Blocked by policy"
    return None


def _blocked_reason_for_entry(
    entry, blocked_list: list[tuple[str, str | None]]
) -> str | None:
    serial_pattern = entry.serial_pattern.lower()
    for pattern, reason in blocked_list:
        normalized = _normalize_pattern(pattern)
        if fnmatch.fnmatch(serial_pattern, normalized) or fnmatch.fnmatch(
            normalized, serial_pattern
        ):
            return reason or "Blocked by policy"
    from .discovery import SUPPORTED_PREFIXES

    if not any(serial_pattern.startswith(prefix) for prefix in SUPPORTED_PREFIXES):
        return "Unsupported USB device"
    return None


def _short_path(path_value: str) -> str:
    """Return filename-only for /dev/serial/by-id paths."""
    try:
        return Path(path_value).name
    except (TypeError, ValueError):
        return path_value


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="kflash",
        description="Build and flash Klipper firmware for USB-connected MCU boards.",
        epilog="Run without args for interactive menu, or use -d KEY "
        "to flash a specific board. Use -s to skip menuconfig when cached config exists. "
        "Device management: --add-device, --list-devices, --remove-device, "
        "--exclude-device, --include-device.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"kalico-flash v{VERSION}",
    )
    parser.add_argument(
        "-d",
        "--device",
        metavar="KEY",
        help="Device key to build and flash (run without --device for interactive selection)",
    )
    parser.add_argument(
        "-s",
        "--skip-menuconfig",
        action="store_true",
        help="Skip menuconfig if cached config exists",
    )

    # Management commands (mutually exclusive)
    mgmt = parser.add_mutually_exclusive_group()
    mgmt.add_argument(
        "--add-device",
        action="store_true",
        help="Interactive wizard to register a new device",
    )
    mgmt.add_argument(
        "--list-devices",
        action="store_true",
        help="List all registered devices with connection status",
    )
    mgmt.add_argument(
        "--remove-device",
        metavar="NAME",
        help="Remove a registered device by key",
    )

    # Device exclusion commands (not mutually exclusive with management group)
    parser.add_argument(
        "--exclude-device",
        metavar="KEY",
        help="Mark a device as non-flashable",
    )
    parser.add_argument(
        "--include-device",
        metavar="KEY",
        help="Mark a device as flashable",
    )

    # Future flags (Phase 2/3):
    # --build-only: Build firmware without flashing
    # --flash-only: Flash existing firmware without rebuilding
    # --config PATH: Path to Kconfig fragment
    # --force: Skip confirmation prompts
    # --dry-run: Show what would be done without doing it

    return parser


def _emit_preflight(out, errors: list[str], warnings: list[str]) -> bool:
    """Emit preflight warnings/errors. Returns True if no errors."""
    for warning in warnings:
        out.warn(f"Preflight: {warning}")

    if errors:
        out.error("Preflight checks failed:")
        for err in errors:
            out.error(f"  - {err}")
        return False
    return True


def _preflight_build(out, klipper_dir: str) -> bool:
    """Validate build prerequisites and Klipper directory."""
    errors: list[str] = []
    warnings: list[str] = []

    klipper_path = Path(klipper_dir).expanduser()
    if not klipper_path.is_dir():
        errors.append(f"Klipper directory not found: {klipper_path}")
    elif not (klipper_path / "Makefile").is_file():
        errors.append(f"Klipper Makefile not found in: {klipper_path}")

    if shutil.which("make") is None:
        errors.append("`make` not found in PATH")

    return _emit_preflight(out, errors, warnings)


def _preflight_flash(
    out,
    klipper_dir: str,
    katapult_dir: str,
    preferred_method: str,
    allow_fallback: bool,
) -> bool:
    """Validate flash prerequisites for the selected method(s)."""
    if not _preflight_build(out, klipper_dir):
        return False

    errors: list[str] = []
    warnings: list[str] = []

    method = (preferred_method or "katapult").strip().lower()
    if method not in ("katapult", "make_flash"):
        errors.append(f"Unknown flash method: {method}")
        return _emit_preflight(out, errors, warnings)

    methods = [method]
    if allow_fallback:
        methods.append("make_flash" if method == "katapult" else "katapult")

    if "katapult" in methods:
        flashtool = Path(katapult_dir).expanduser() / "scripts" / "flashtool.py"
        if not flashtool.is_file():
            msg = f"Katapult flashtool not found at {flashtool}"
            if method == "katapult" and not allow_fallback:
                errors.append(msg)
            else:
                warnings.append(msg)
        if shutil.which("python3") is None:
            msg = "`python3` not found in PATH (required for Katapult)"
            if method == "katapult" and not allow_fallback:
                errors.append(msg)
            else:
                warnings.append(msg)

    if shutil.which("sudo") is None:
        warnings.append("`sudo` not found; Klipper service control may fail")
    if shutil.which("systemctl") is None:
        warnings.append("`systemctl` not found; Klipper service control may fail")

    return _emit_preflight(out, errors, warnings)


def _resolve_flash_method(entry, global_config) -> str:
    """Resolve preferred flash method for a device."""
    method = entry.flash_method or global_config.default_flash_method or "katapult"
    return method.strip().lower()


def _remove_cached_config(device_key: str, out, prompt: bool = True) -> None:
    """Remove cached config directory for a device key."""
    from .config import get_config_dir

    config_dir = get_config_dir(device_key)
    if not config_dir.exists():
        return

    should_remove = True
    if prompt:
        should_remove = out.confirm(
            f"Also remove cached config for '{device_key}'?", default=False
        )

    if not should_remove:
        out.info("Registry", "Cached config kept")
        return

    try:
        shutil.rmtree(config_dir)
        out.success("Cached config removed")
    except OSError as exc:
        out.warn(f"Failed to remove cached config: {exc}")


def cmd_build(registry, device_key: str, out) -> int:
    """Build firmware for a registered device.

    Orchestrates: load cached config -> menuconfig -> save config -> MCU validation -> build
    """
    # Late imports for fast startup
    from .config import ConfigManager
    from .build import run_menuconfig, run_build
    from .errors import ConfigError, ERROR_TEMPLATES

    # Load device entry
    entry = registry.get(device_key)
    if entry is None:
        template = ERROR_TEMPLATES["device_not_registered"]
        out.error_with_recovery(
            template["error_type"],
            template["message_template"].format(device=device_key),
            context={"device": device_key},
            recovery=template["recovery_template"],
        )
        return 1

    # Load global config for klipper_dir
    data = registry.load()
    if data.global_config is None:
        out.error("Global config not set. Run --add-device first.")
        return 1

    klipper_dir = data.global_config.klipper_dir
    out.info("Build", f"Building firmware for {entry.name} ({entry.mcu})")

    if not _preflight_build(out, klipper_dir):
        return 1

    # Initialize config manager
    config_mgr = ConfigManager(device_key, klipper_dir)

    # Step 1: Load cached config (if exists)
    if config_mgr.load_cached_config():
        out.info("Config", f"Loaded cached config for '{device_key}'")
    else:
        out.info("Config", "No cached config found, starting fresh")

    # Step 2: Run menuconfig
    out.info("Config", "Launching menuconfig...")
    ret_code, was_saved = run_menuconfig(
        klipper_dir, str(config_mgr.klipper_config_path)
    )

    if ret_code != 0:
        template = ERROR_TEMPLATES["menuconfig_failed"]
        out.error_with_recovery(
            template["error_type"],
            template["message_template"],
            context={"device": device_key},
            recovery=template["recovery_template"],
        )
        return 1

    if not was_saved:
        out.warn("Config was not saved in menuconfig")
        if not out.confirm("Continue build anyway?"):
            out.info("Build", "Cancelled")
            return 0

    # Step 3: Save config to cache
    try:
        config_mgr.save_cached_config()
        out.info("Config", f"Cached config for '{device_key}'")
    except ConfigError as e:
        out.error_with_recovery(
            "Config error",
            f"Failed to cache config: {e}",
            context={"device": device_key},
            recovery="1. Verify Klipper directory is writable\n2. Check disk space\n3. Re-run menuconfig",
        )
        return 1

    # Step 4: MCU validation
    try:
        is_match, actual_mcu = config_mgr.validate_mcu(entry.mcu)
        if not is_match:
            template = ERROR_TEMPLATES["mcu_mismatch"]
            out.error_with_recovery(
                template["error_type"],
                template["message_template"].format(
                    actual=actual_mcu, expected=entry.mcu
                ),
                context={
                    "device": device_key,
                    "expected": entry.mcu,
                    "actual": actual_mcu,
                },
                recovery=template["recovery_template"],
            )
            return 1
        out.info("Config", f"MCU validated: {actual_mcu}")
    except ConfigError as e:
        out.error_with_recovery(
            "Config error",
            f"MCU validation failed: {e}",
            context={"device": device_key},
            recovery="1. Run menuconfig and verify MCU selection\n2. Check .config file exists\n3. Ensure CONFIG_MCU is set",
        )
        return 1

    # Step 5: Build
    out.info("Build", "Running make clean + make...")
    result = run_build(klipper_dir)

    if not result.success:
        template = ERROR_TEMPLATES["build_failed"]
        out.error_with_recovery(
            template["error_type"],
            template["message_template"].format(device=device_key),
            context={"device": device_key},
            recovery=template["recovery_template"],
        )
        return 1

    # Success
    size_kb = result.firmware_size / 1024 if result.firmware_size else 0
    out.success(
        f"Build complete: {result.firmware_path} ({size_kb:.1f} KB) "
        f"in {result.elapsed_seconds:.1f}s"
    )
    return 0


def cmd_flash(registry, device_key, out, skip_menuconfig: bool = False) -> int:
    """Build and flash firmware for a registered device.

    Orchestrates the full workflow:
    1. [Discovery] Scan USB devices, select target
    2. [Config] Load/edit menuconfig, validate MCU
    3. [Build] Compile firmware with timeout
    4. [Flash] Stop Klipper, flash device, restart Klipper

    Args:
        registry: Registry instance for device lookup
        device_key: Device key to flash (None for interactive selection)
        out: Output interface for user messages
        skip_menuconfig: If True, skip menuconfig when cached config exists

    Returns:
        0 on success, 1 on failure
    """
    import time

    # Late imports for fast startup
    from .discovery import (
        scan_serial_devices,
        find_registered_devices,
        match_device,
        match_devices,
        is_supported_device,
    )
    from .config import ConfigManager
    from .build import run_menuconfig, run_build, TIMEOUT_BUILD
    from .service import klipper_service_stopped, verify_passwordless_sudo
    from .flasher import flash_device, verify_device_path, TIMEOUT_FLASH
    from .errors import ConfigError, DiscoveryError, ERROR_TEMPLATES
    from .tui import wait_for_device, _get_menu_choice

    # TTY check for interactive mode
    if device_key is None and not sys.stdin.isatty():
        out.error(
            "Interactive terminal required. Use --device KEY or run from SSH terminal."
        )
        return 1

    # Load registry data
    data = registry.load()
    if data.global_config is None:
        out.error("Global config not set. Run --add-device first.")
        return 1
    blocked_list = _build_blocked_list(data)

    # Fetch version information early for display in device selection
    from .moonraker import (
        get_print_status,
        get_mcu_versions,
        get_host_klipper_version,
        is_mcu_outdated,
        get_mcu_version_for_device,
    )
    mcu_versions = get_mcu_versions()
    host_version = get_host_klipper_version(data.global_config.klipper_dir)

    # === Phase 1: Discovery ===
    out.phase("Discovery", "Scanning for USB devices...")
    usb_devices = scan_serial_devices()
    duplicate_matches: dict[str, list] = {}
    for entry in data.devices.values():
        matches = match_devices(entry.serial_pattern, usb_devices)
        if len(matches) > 1:
            duplicate_matches[entry.key] = matches
    blocked_entries: dict[str, str] = {}
    for entry in data.devices.values():
        reason = _blocked_reason_for_entry(entry, blocked_list)
        if reason:
            blocked_entries[entry.key] = reason

    if device_key is None:
        # Interactive mode: select from connected registered devices
        if not usb_devices:
            out.error("No USB devices found. Connect a board and try again.")
            return 1

        # Cross-reference with registry
        matched, unmatched = find_registered_devices(usb_devices, data.devices)

        # Remove any entries with duplicate USB IDs or blocked status from selectable list
        if duplicate_matches:
            matched = [(e, d) for e, d in matched if e.key not in duplicate_matches]
        if blocked_entries:
            matched = [(e, d) for e, d in matched if e.key not in blocked_entries]

        if not matched:
            if duplicate_matches:
                out.error_with_recovery(
                    "Duplicate USB IDs",
                    "Registered device(s) match multiple connected USB IDs",
                    recovery=(
                        "1. Unplug duplicate devices so only one remains\n"
                        "2. Reconnect and retry\n"
                        "3. If duplicates persist, update registry to unique devices"
                    ),
                )
                out.phase("Discovery", "Blocked devices with duplicate USB IDs:")
                for key, devices in duplicate_matches.items():
                    entry = data.devices.get(key)
                    if entry is None:
                        continue
                    details = ", ".join(d.filename for d in devices)
                    out.device_line(
                        "DUP", f"{entry.key} ({entry.mcu}) [duplicate]", details
                    )
                return 1

            if blocked_entries:
                blocked_connected = [
                    (entry, device)
                    for entry, device in find_registered_devices(
                        usb_devices, data.devices
                    )[0]
                    if entry.key in blocked_entries
                ]
                if blocked_connected:
                    out.error_with_recovery(
                        "Blocked devices",
                        "Connected registered devices are blocked and cannot be flashed",
                        recovery="1. Remove blocked entries from devices.json\n2. Or connect a flashable device",
                    )
                    out.phase("Discovery", "Blocked registered devices:")
                    for entry, device in blocked_connected:
                        reason = blocked_entries.get(entry.key, "Blocked by policy")
                        out.device_line(
                            "BLK", f"{entry.key} ({entry.mcu}) [blocked]", reason
                        )
                    return 1

            out.error_with_recovery(
                "Device not found",
                "No registered devices connected",
                recovery="1. List registered devices: kflash --list-devices\n2. Check USB connections\n3. Register new device: kflash --add-device",
            )
            out.phase("Discovery", "Found USB devices but none are registered:")
            for device in usb_devices:
                blocked_reason = _blocked_reason_for_filename(
                    device.filename, blocked_list
                )
                if blocked_reason or not is_supported_device(device.filename):
                    out.device_line(
                        "BLK",
                        device.filename,
                        blocked_reason or "Unsupported USB device",
                    )
                else:
                    out.device_line("NEW", device.filename, "Unregistered device")
            return 1

        if duplicate_matches:
            out.phase("Discovery", "Blocked devices with duplicate USB IDs:")
            for key, devices in duplicate_matches.items():
                entry = data.devices.get(key)
                if entry is None:
                    continue
                details = ", ".join(d.filename for d in devices)
                out.device_line(
                    "DUP", f"{entry.key} ({entry.mcu}) [duplicate]", details
                )

        # Filter to only flashable devices for selection
        flashable_matched = [(e, d) for e, d in matched if e.flashable]
        excluded_matched = [(e, d) for e, d in matched if not e.flashable]

        # Show excluded devices with note if any
        if excluded_matched:
            out.phase("Discovery", "Excluded devices (not selectable):")
            for entry, device in excluded_matched:
                out.device_line(
                    "REG", f"{entry.key} ({entry.mcu}) [excluded]", device.filename
                )

        if blocked_entries:
            blocked_connected = [
                (entry, device)
                for entry, device in find_registered_devices(usb_devices, data.devices)[
                    0
                ]
                if entry.key in blocked_entries
            ]
            if blocked_connected:
                out.phase("Discovery", "Blocked devices (not selectable):")
                for entry, device in blocked_connected:
                    reason = blocked_entries.get(entry.key, "Blocked by policy")
                    out.device_line(
                        "BLK", f"{entry.key} ({entry.mcu}) [blocked]", reason
                    )

        if not flashable_matched:
            template = ERROR_TEMPLATES["device_excluded"]
            out.error_with_recovery(
                template["error_type"],
                "All connected devices are excluded from flashing",
                recovery=template["recovery_template"],
            )
            return 1

        # Show numbered list of connected flashable devices
        out.phase("Discovery", f"Found {len(flashable_matched)} flashable device(s):")
        for i, (entry, device) in enumerate(flashable_matched):
            out.device_line(str(i + 1), f"{entry.key} ({entry.mcu})", device.filename)
            # Show MCU software version if available
            if mcu_versions:
                version = get_mcu_version_for_device(entry.mcu)
                if version:
                    out.info("", f"     MCU software version: {version}")

        # Show host Klipper version before selection
        if host_version:
            out.info("Version", f"Host Klipper: {host_version}")

        # Single device: auto-select with confirmation
        if len(flashable_matched) == 1:
            entry, usb_device = flashable_matched[0]
            if out.confirm(f"Flash {entry.name}?", default=True):
                device_key = entry.key
                device_path = usb_device.path
            else:
                out.phase("Discovery", "Cancelled")
                return 0
        else:
            # Multiple devices: prompt for selection
            choices = ["0"] + [str(i) for i in range(1, len(flashable_matched) + 1)]
            choice = _get_menu_choice(
                choices,
                out,
                max_attempts=3,
                prompt="Select device number (0/q to cancel): ",
            )
            if choice is None or choice == "0":
                out.phase("Discovery", "Cancelled")
                return 0
            idx = int(choice) - 1
            entry, usb_device = flashable_matched[idx]
            device_key = entry.key
            device_path = usb_device.path
    else:
        # Explicit --device KEY mode: verify device exists and is connected
        entry = registry.get(device_key)
        if entry is None:
            template = ERROR_TEMPLATES["device_not_registered"]
            out.error_with_recovery(
                template["error_type"],
                template["message_template"].format(device=device_key),
                context={"device": device_key},
                recovery=template["recovery_template"],
            )
            return 1

        blocked_reason = _blocked_reason_for_entry(entry, blocked_list)
        if blocked_reason:
            out.error_with_recovery(
                "Device blocked",
                f"Device '{device_key}' is blocked: {blocked_reason}",
                context={"device": device_key},
                recovery=(
                    "1. Remove the device from blocked_devices in devices.json\n"
                    "2. Or update the device serial pattern to a supported target"
                ),
            )
            return 1

        # Check if device is excluded from flashing
        if not entry.flashable:
            out.error_with_recovery(
                "Device excluded",
                device_key,
                {"device": device_key, "name": entry.name},
                f"The device '{device_key}' is marked as non-flashable. "
                f"To make it flashable, run `kflash --include-device {device_key}`.",
            )
            return 1

        # Block if this device matches multiple USB IDs
        if device_key in duplicate_matches:
            out.error_with_recovery(
                "Duplicate USB IDs",
                f"Device '{device_key}' matches multiple connected USB IDs",
                context={"device": device_key},
                recovery=(
                    "1. Unplug duplicate devices so only one remains\n"
                    "2. Reconnect and retry\n"
                    "3. If duplicates persist, update registry to unique devices"
                ),
            )
            for device in duplicate_matches[device_key]:
                out.device_line("DUP", device.filename, "Duplicate USB ID")
            return 1

        # Find matching USB device
        usb_device = match_device(entry.serial_pattern, usb_devices)
        if usb_device is None:
            template = ERROR_TEMPLATES["device_not_connected"]
            out.error_with_recovery(
                template["error_type"],
                template["message_template"].format(device=device_key),
                context={"device": device_key},
                recovery=template["recovery_template"],
            )
            return 1

        device_path = usb_device.path

    # Load the device entry for the rest of the workflow
    entry = registry.get(device_key)
    klipper_dir = data.global_config.klipper_dir
    katapult_dir = data.global_config.katapult_dir
    preferred_method = _resolve_flash_method(entry, data.global_config)
    allow_fallback = data.global_config.allow_flash_fallback

    if not _preflight_flash(
        out, klipper_dir, katapult_dir, preferred_method, allow_fallback
    ):
        return 1

    out.phase(
        "Discovery", f"Target: {entry.name} ({entry.mcu}) at {_short_path(device_path)}"
    )

    # === Moonraker Safety Check ===
    print_status = get_print_status()

    if print_status is None:
        # Moonraker unreachable - warn and require confirmation
        out.warn("Moonraker unreachable - print status and version check unavailable")
        if not out.confirm("Continue without safety checks?", default=False):
            out.phase("Flash", "Cancelled")
            return 0
    elif print_status.state in ("printing", "paused"):
        # Block flash during active print
        progress_pct = int(print_status.progress * 100)
        filename = print_status.filename or "unknown"
        out.error_with_recovery(
            "Printer busy",
            f"Print in progress: {filename} ({progress_pct}%)",
            recovery=(
                "1. Wait for current print to complete\n"
                "2. Or cancel print in Fluidd/Mainsail dashboard\n"
                "3. Then re-run flash command"
            ),
        )
        return 1
    else:
        # Safe state - show status and continue
        out.phase("Safety", f"Printer state: {print_status.state} - OK to flash")

    # === Version Information ===
    # mcu_versions and host_version already fetched earlier for device selection display

    if host_version:
        out.phase("Version", f"Host Klipper: {host_version}")

        if mcu_versions:
            # Display all MCU versions, mark target with asterisk
            # Map device MCU type to Moonraker MCU name by checking mcu_constants
            target_mcu = None
            for mcu_name in mcu_versions:
                # Simple heuristic: if device mcu contains the mcu_name or vice versa
                if (
                    entry.mcu.lower() in mcu_name.lower()
                    or mcu_name.lower() in entry.mcu.lower()
                ):
                    target_mcu = mcu_name
                    break
            # If no match found by name, use "main" as default for primary MCU
            if target_mcu is None and "main" in mcu_versions:
                target_mcu = "main"

            for mcu_name, mcu_version in sorted(mcu_versions.items()):
                marker = "*" if mcu_name == target_mcu else " "
                out.phase("Version", f"  [{marker}] MCU {mcu_name}: {mcu_version}")

            # Check if target MCU is outdated or already current
            if target_mcu and target_mcu in mcu_versions:
                if is_mcu_outdated(host_version, mcu_versions[target_mcu]):
                    out.warn("MCU firmware is behind host Klipper - update recommended")
                else:
                    # MCU firmware matches host - confirm user wants to reflash
                    if not out.confirm(
                        "MCU firmware is already up-to-date. Continue anyway?",
                        default=False,
                    ):
                        out.phase("Flash", "Cancelled - firmware already current")
                        return 0
        else:
            out.warn("MCU versions unavailable (Klipper may not be running)")
    elif mcu_versions:
        # Have MCU versions but not host version (unusual)
        out.warn("Host Klipper version unavailable")
    # If neither available, skip version display silently (Moonraker down case handled above)

    # === Phase 2: Config ===
    out.phase("Config", f"Loading config for {entry.name}...")
    config_mgr = ConfigManager(device_key, klipper_dir)

    if config_mgr.load_cached_config():
        out.phase("Config", f"Loaded cached config for '{device_key}'")
    else:
        out.phase("Config", "No cached config found, starting fresh")

    # Skip menuconfig if flag is set AND cached config exists
    if skip_menuconfig:
        if config_mgr.has_cached_config():
            out.phase("Config", f"Using cached config for {device_key}")
            # Skip menuconfig but still validate MCU
        else:
            # Per CONTEXT.md: warn and launch menuconfig anyway
            out.warn(f"No cached config for '{device_key}', launching menuconfig")
            skip_menuconfig = False  # Fall through to menuconfig

    if not skip_menuconfig:
        out.phase("Config", "Launching menuconfig...")
        ret_code, was_saved = run_menuconfig(
            klipper_dir, str(config_mgr.klipper_config_path)
        )

        if ret_code != 0:
            template = ERROR_TEMPLATES["menuconfig_failed"]
            out.error_with_recovery(
                template["error_type"],
                template["message_template"],
                context={"device": device_key},
                recovery=template["recovery_template"],
            )
            return 1

        if not was_saved:
            out.warn("Config was not saved in menuconfig")
            if not out.confirm("Continue build anyway?"):
                out.phase("Config", "Cancelled")
                return 0

        # Save config to cache
        try:
            config_mgr.save_cached_config()
            out.phase("Config", f"Cached config for '{device_key}'")
        except ConfigError as e:
            out.error_with_recovery(
                "Config error",
                f"Failed to cache config: {e}",
                context={"device": device_key},
                recovery="1. Verify Klipper directory is writable\n2. Check disk space\n3. Re-run menuconfig",
            )
            return 1

    # MCU validation (always runs, even with skip_menuconfig)
    try:
        is_match, actual_mcu = config_mgr.validate_mcu(entry.mcu)
        if not is_match:
            template = ERROR_TEMPLATES["mcu_mismatch"]
            out.error_with_recovery(
                template["error_type"],
                template["message_template"].format(
                    actual=actual_mcu, expected=entry.mcu
                ),
                context={
                    "device": device_key,
                    "expected": entry.mcu,
                    "actual": actual_mcu,
                },
                recovery=template["recovery_template"],
            )
            return 1
        out.phase("Config", f"MCU validated: {actual_mcu}")
    except ConfigError as e:
        out.error_with_recovery(
            "Config error",
            f"MCU validation failed: {e}",
            context={"device": device_key},
            recovery="1. Run menuconfig and verify MCU selection\n2. Check .config file exists\n3. Ensure CONFIG_MCU is set",
        )
        return 1

    # === Phase 3: Build ===
    out.phase("Build", "Running make clean + make...")
    build_result = run_build(klipper_dir, timeout=TIMEOUT_BUILD)

    if not build_result.success:
        template = ERROR_TEMPLATES["build_failed"]
        out.error_with_recovery(
            template["error_type"],
            template["message_template"].format(device=device_key),
            context={"device": device_key},
            recovery=template["recovery_template"],
        )
        return 1

    firmware_path = build_result.firmware_path
    size_kb = build_result.firmware_size / 1024 if build_result.firmware_size else 0
    out.phase(
        "Build",
        f"Firmware ready: {size_kb:.1f} KB in {build_result.elapsed_seconds:.1f}s",
    )

    # === Phase 4: Flash ===
    out.phase("Flash", "Verifying device connection...")
    try:
        verify_device_path(device_path)
    except DiscoveryError as e:
        out.error_with_recovery(
            "Device disconnected",
            str(e),
            context={"device": device_key, "path": device_path},
            recovery="1. Check USB connection and board power\n2. List devices: ls /dev/serial/by-id/\n3. Reconnect and retry flash",
        )
        return 1

    # Check passwordless sudo (informational only - let sudo prompt if needed)
    if not verify_passwordless_sudo():
        out.phase("Flash", "Note: sudo may prompt for password")

    out.phase("Flash", "Stopping Klipper...")
    flash_start = time.monotonic()

    try:
        with klipper_service_stopped(out=out):
            out.phase("Flash", "Flashing firmware...")

            def _flash_log(message: str) -> None:
                out.phase("Flash", message)

            flash_result = flash_device(
                device_path=device_path,
                firmware_path=firmware_path,
                katapult_dir=katapult_dir,
                klipper_dir=klipper_dir,
                timeout=TIMEOUT_FLASH,
                preferred_method=preferred_method,
                allow_fallback=allow_fallback,
                log=_flash_log,
            )

            if flash_result.success:
                # Verify device reappears BEFORE restarting Klipper
                out.phase("Verify", "Waiting for device to reappear...")
                verified, device_path_new, error_reason = wait_for_device(
                    entry.serial_pattern,
                    timeout=30.0,
                    out=out,
                )
            else:
                verified = False
                device_path_new = None
                error_reason = flash_result.error_message

        # Context manager exited - Klipper has restarted
        out.phase("Service", "Klipper restarted")
    except Exception as e:
        template = ERROR_TEMPLATES["flash_failed"]
        out.error_with_recovery(
            template["error_type"],
            f"Flash operation error: {e}",
            context={"device": device_key},
            recovery=template["recovery_template"],
        )
        return 1

    flash_elapsed = time.monotonic() - flash_start

    # === Summary ===
    if flash_result.success and verified:
        out.success(
            f"Flashed {entry.name} via {flash_result.method} in {flash_elapsed:.1f}s"
        )
        out.phase("Verify", f"Device confirmed at: {device_path_new}")
        return 0

    elif flash_result.success and not verified:
        # Flash appeared to succeed but device didn't reappear correctly
        out.warn(f"Device verification failed: {error_reason}")
        if device_path_new:
            template = ERROR_TEMPLATES["verification_wrong_prefix"]
        else:
            template = ERROR_TEMPLATES["verification_timeout"]
        out.error_with_recovery(
            template["error_type"],
            template["message_template"],
            context={"device": device_key, "pattern": entry.serial_pattern},
            recovery=template["recovery_template"],
        )
        return 1

    else:
        # flash_result.success was False
        template = ERROR_TEMPLATES["flash_failed"]
        out.error_with_recovery(
            template["error_type"],
            template["message_template"].format(device=device_key),
            context={
                "device": device_key,
                "method": flash_result.method,
                "error": flash_result.error_message,
            },
            recovery=template["recovery_template"],
        )
        return 1


def cmd_flash_all(registry, out) -> int:
    """Build and flash firmware for all registered flashable devices.

    Orchestrates a 5-stage batch workflow:
    1. Validate all devices have cached configs
    2. Version check — prompt if all MCUs already match host
    3. Build all firmware quietly, copy to temp dir
    4. Flash all inside single klipper_service_stopped()
    5. Print summary table

    One device failure never blocks others from being processed.

    Args:
        registry: Registry instance for device lookup.
        out: Output interface for user messages.

    Returns:
        0 if all devices passed, 1 if any failed.
    """
    import os
    import shutil
    import tempfile
    import time

    # Late imports
    from .config import ConfigManager
    from .build import run_build
    from .discovery import scan_serial_devices, match_device
    from .flasher import flash_device, TIMEOUT_FLASH
    from .service import klipper_service_stopped, verify_passwordless_sudo
    from .moonraker import (
        get_print_status,
        get_mcu_versions,
        get_host_klipper_version,
        is_mcu_outdated,
        get_mcu_version_for_device,
    )
    from .tui import wait_for_device
    from .models import BatchDeviceResult

    # Load registry
    data = registry.load()
    if data.global_config is None:
        out.error("Global config not set. Run --add-device first.")
        return 1

    global_config = data.global_config
    klipper_dir = global_config.klipper_dir
    katapult_dir = global_config.katapult_dir

    # === Stage 1: Validate cached configs ===
    out.phase("Flash All", "Validating cached configs...")

    flashable_devices = sorted(
        [e for e in data.devices.values() if e.flashable],
        key=lambda e: e.key,
    )

    if not flashable_devices:
        out.error("No flashable devices registered. Use --add-device to register boards.")
        return 1

    missing_configs: list[str] = []
    for entry in flashable_devices:
        config_mgr = ConfigManager(entry.key, klipper_dir)
        if not config_mgr.cache_path.exists():
            missing_configs.append(entry.key)

    if missing_configs:
        out.error("The following devices lack cached configs:")
        for key in missing_configs:
            out.error(f"  - {key}")
        out.error("Run 'kflash -d <device>' for each to configure before using Flash All.")
        return 1

    out.phase("Flash All", f"{len(flashable_devices)} device(s) with cached configs")

    # === Stage 2: Version check ===
    host_version = get_host_klipper_version(klipper_dir)
    mcu_versions = get_mcu_versions()

    flash_list = list(flashable_devices)

    if host_version is None or mcu_versions is None:
        out.warn("Version check unavailable -- Moonraker not reachable. Flashing all devices.")
    else:
        out.phase("Version", f"Host Klipper: {host_version}")
        outdated: list = []
        current: list = []

        for entry in flashable_devices:
            mcu_ver = get_mcu_version_for_device(entry.mcu)
            if mcu_ver and not is_mcu_outdated(host_version, mcu_ver):
                current.append(entry)
            else:
                outdated.append(entry)

        if not outdated:
            # All match
            out.phase("Version", "All devices already match host version.")
            try:
                answer = input("  Flash anyway? [y/N]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                answer = "n"
            if answer != "y":
                out.phase("Flash All", "Cancelled -- firmware already current")
                return 0
        elif current:
            # Some match, some don't
            out.phase("Version", "Outdated devices:")
            for entry in outdated:
                out.info("", f"  - {entry.name} ({entry.key})")
            out.phase("Version", "Up-to-date devices:")
            for entry in current:
                out.info("", f"  - {entry.name} ({entry.key})")
            try:
                answer = input("  Flash only outdated devices? [Y/n]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                answer = "y"
            if answer != "n":
                flash_list = outdated
            # else flash_list remains all devices

    # Initialize results tracking
    results: list[BatchDeviceResult] = []
    for entry in flash_list:
        results.append(BatchDeviceResult(
            device_key=entry.key,
            device_name=entry.name,
            config_ok=True,  # Already validated in Stage 1
        ))

    # === Stage 3: Build all firmware ===
    out.phase("Flash All", f"Building firmware for {len(flash_list)} device(s)...")
    temp_dir = tempfile.mkdtemp(prefix="kalico-flash-")
    total = len(flash_list)

    try:
        for i, (entry, result) in enumerate(zip(flash_list, results)):
            print(f"  Building {i + 1}/{total}: {entry.name}...")
            config_mgr = ConfigManager(entry.key, klipper_dir)
            config_mgr.load_cached_config()

            build_result = run_build(klipper_dir, quiet=True)

            if build_result.success:
                # Copy firmware to temp dir
                device_fw_dir = os.path.join(temp_dir, entry.key)
                os.makedirs(device_fw_dir, exist_ok=True)
                fw_src = os.path.join(
                    str(Path(klipper_dir).expanduser()), "out", "klipper.bin"
                )
                fw_dst = os.path.join(device_fw_dir, "klipper.bin")
                shutil.copy2(fw_src, fw_dst)
                result.build_ok = True
                print(f"  \u2713 {entry.name} built ({i + 1}/{total})")
            else:
                result.error_message = build_result.error_message or "Build failed"
                print(f"  \u2717 {entry.name} build failed ({i + 1}/{total})")

        # Check if any builds succeeded
        built_results = [(e, r) for e, r in zip(flash_list, results) if r.build_ok]
        if not built_results:
            out.error("All builds failed. Nothing to flash.")
            return 1

        # === Stage 4: Flash all (inside single service stop) ===
        out.phase("Flash All", f"Flashing {len(built_results)} device(s)...")

        # Safety check: print status
        print_status = get_print_status()
        if print_status is not None and print_status.state in ("printing", "paused"):
            progress_pct = int(print_status.progress * 100)
            filename = print_status.filename or "unknown"
            out.error(f"Print in progress: {filename} ({progress_pct}%). Aborting flash.")
            return 1

        # Verify passwordless sudo
        if not verify_passwordless_sudo():
            out.phase("Flash All", "Note: sudo may prompt for password")

        flash_idx = 0
        flash_total = len(built_results)

        with klipper_service_stopped(out=out):
            # Re-scan USB after Klipper stop
            usb_devices = scan_serial_devices()

            for entry, result in built_results:
                if flash_idx > 0:
                    time.sleep(global_config.stagger_delay)
                flash_idx += 1

                # Find device
                usb_device = match_device(entry.serial_pattern, usb_devices)
                if usb_device is None:
                    result.error_message = "Device not found on USB"
                    print(f"  \u2717 {entry.name} not found ({flash_idx}/{flash_total})")
                    continue

                # Determine flash method
                method = entry.flash_method or global_config.default_flash_method or "katapult"
                allow_fallback = global_config.allow_flash_fallback

                fw_path = os.path.join(temp_dir, entry.key, "klipper.bin")
                flash_result = flash_device(
                    device_path=usb_device.path,
                    firmware_path=fw_path,
                    katapult_dir=katapult_dir,
                    klipper_dir=klipper_dir,
                    timeout=TIMEOUT_FLASH,
                    preferred_method=method,
                    allow_fallback=allow_fallback,
                )

                if flash_result.success:
                    result.flash_ok = True
                    # Post-flash verification
                    verified, _, error_reason = wait_for_device(
                        entry.serial_pattern, timeout=30.0, out=out,
                    )
                    if verified:
                        result.verify_ok = True
                        print(f"  \u2713 {entry.name} flashed and verified ({flash_idx}/{flash_total})")
                    else:
                        result.error_message = error_reason or "Verification failed"
                        print(f"  \u2717 {entry.name} flash OK but verify failed ({flash_idx}/{flash_total})")

                    # Re-scan after flash for next device
                    usb_devices = scan_serial_devices()
                else:
                    result.error_message = flash_result.error_message or "Flash failed"
                    print(f"  \u2717 {entry.name} flash failed ({flash_idx}/{flash_total})")

        out.phase("Service", "Klipper restarted")

    finally:
        # Clean up temp dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    # === Stage 5: Summary table ===
    out.phase("Flash All", "Summary:")
    out.info("", "  Device                Build   Flash   Verify")
    out.info("", "  " + "-" * 48)

    all_passed = True
    for result in results:
        build_str = "PASS" if result.build_ok else "FAIL"
        if result.build_ok:
            flash_str = "PASS" if result.flash_ok else "FAIL"
        else:
            flash_str = "SKIP"
        if result.flash_ok:
            verify_str = "PASS" if result.verify_ok else "FAIL"
        else:
            verify_str = "SKIP"

        if not (result.build_ok and result.flash_ok and result.verify_ok):
            all_passed = False

        name = result.device_name[:20].ljust(20)
        out.info("", f"  {name}  {build_str:6s}  {flash_str:6s}  {verify_str}")

    passed = sum(1 for r in results if r.build_ok and r.flash_ok and r.verify_ok)
    failed = len(results) - passed
    out.info("", "")
    out.info("", f"  {passed} passed, {failed} failed out of {len(results)} device(s)")

    return 0 if all_passed else 1


def cmd_remove_device(registry, device_key: str, out) -> int:
    """Remove a device from the registry with optional config cleanup."""
    from .errors import ERROR_TEMPLATES

    entry = registry.get(device_key)
    if entry is None:
        template = ERROR_TEMPLATES["device_not_registered"]
        out.error_with_recovery(
            template["error_type"],
            template["message_template"].format(device=device_key),
            context={"device": device_key},
            recovery=template["recovery_template"],
        )
        return 1

    if not out.confirm(f"Remove '{device_key}' ({entry.name})?"):
        out.info("Registry", "Removal cancelled")
        return 0

    registry.remove(device_key)
    out.success(f"Removed '{device_key}'")
    _remove_cached_config(device_key, out, prompt=True)

    return 0


def cmd_exclude_device(registry, device_key: str, out) -> int:
    """Mark a device as non-flashable."""
    from .errors import ERROR_TEMPLATES

    entry = registry.get(device_key)
    if entry is None:
        template = ERROR_TEMPLATES["device_not_registered"]
        out.error_with_recovery(
            template["error_type"],
            template["message_template"].format(device=device_key),
            context={"device": device_key},
            recovery=template["recovery_template"],
        )
        return 1
    if not entry.flashable:
        out.warn(f"Device '{device_key}' is already excluded")
        return 0
    registry.set_flashable(device_key, False)
    out.success(f"Excluded '{device_key}' from flashing")
    return 0


def cmd_include_device(registry, device_key: str, out) -> int:
    """Mark a device as flashable."""
    from .errors import ERROR_TEMPLATES

    entry = registry.get(device_key)
    if entry is None:
        template = ERROR_TEMPLATES["device_not_registered"]
        out.error_with_recovery(
            template["error_type"],
            template["message_template"].format(device=device_key),
            context={"device": device_key},
            recovery=template["recovery_template"],
        )
        return 1
    if entry.flashable:
        out.warn(f"Device '{device_key}' is already flashable")
        return 0
    registry.set_flashable(device_key, True)
    out.success(f"Included '{device_key}' for flashing")
    return 0


def cmd_list_devices(registry, out, from_menu: bool = False) -> int:
    """List all registered devices with connection status.

    Cross-references registered devices against live USB scan to show:
    - [REG] Connected devices with their USB filename
    - [REG] Disconnected devices (registered but not currently connected)
    - [NEW] Unknown USB devices (connected but not registered)

    Args:
        registry: Registry instance for device lookup.
        out: Output interface for user messages.
        from_menu: If True, suppress "Use --add-device" hint (menu has its own navigation).
    """
    from .discovery import scan_serial_devices, match_devices, is_supported_device
    from .moonraker import get_mcu_versions, get_host_klipper_version, get_mcu_version_for_device

    # Load registry and scan USB devices
    data = registry.load()
    usb_devices = scan_serial_devices()
    blocked_list = _build_blocked_list(data)

    # Fetch version information
    mcu_versions = get_mcu_versions()
    host_version = None
    if data.global_config:
        host_version = get_host_klipper_version(data.global_config.klipper_dir)

    # Cross-reference registered vs discovered
    entry_matches: dict[str, list] = {}
    device_matches: dict[str, list] = {}
    for entry in data.devices.values():
        matches = match_devices(entry.serial_pattern, usb_devices)
        entry_matches[entry.key] = matches
        for device in matches:
            device_matches.setdefault(device.filename, []).append(entry)

    matched_filenames = set(device_matches.keys())
    unmatched = [
        device for device in usb_devices if device.filename not in matched_filenames
    ]

    duplicate_entry_keys = {
        key for key, matches in entry_matches.items() if len(matches) > 1
    }
    duplicate_devices = {
        filename
        for filename, entries in device_matches.items()
        if len(entries) > 1
        or any(entry.key in duplicate_entry_keys for entry in entries)
    }

    registered_connected = 0
    new_count = 0
    blocked_count = 0
    duplicate_count = 0
    for device in usb_devices:
        blocked_reason = _blocked_reason_for_filename(device.filename, blocked_list)
        if blocked_reason or not is_supported_device(device.filename):
            blocked_count += 1
            continue
        entries = device_matches.get(device.filename, [])
        if entries:
            if device.filename in duplicate_devices:
                duplicate_count += 1
            else:
                registered_connected += 1
        else:
            new_count += 1

    # Handle: no registered devices AND no USB devices
    if not data.devices and not usb_devices:
        out.info("Devices", "No registered devices and no USB devices found.")
        return 0

    # Handle: no registered devices BUT USB devices exist (first-run UX)
    if not data.devices and usb_devices:
        summary = (
            f"{len(usb_devices)} USB devices found: {registered_connected} registered, "
            f"{new_count} new, {blocked_count} blocked, {duplicate_count} duplicate"
        )
        out.info("Devices", f"No registered devices. {summary}.")
        for device in usb_devices:
            blocked_reason = _blocked_reason_for_filename(device.filename, blocked_list)
            if blocked_reason or not is_supported_device(device.filename):
                marker = "BLK"
                detail = blocked_reason or "Unsupported USB device"
            else:
                marker = "NEW"
                detail = "Unregistered device"
            out.device_line(marker, device.filename, detail)
        out.info("Devices", "Run --add-device to register a board.")
        return 0

    # Normal display: show registered devices with connection status
    summary = (
        f"{len(usb_devices)} USB devices found: {registered_connected} registered, "
        f"{new_count} new, {blocked_count} blocked, {duplicate_count} duplicate"
    )
    out.info("Devices", f"{len(data.devices)} registered. {summary}.")

    for key in sorted(data.devices.keys()):
        entry = data.devices[key]
        # Build name with optional [excluded] marker
        name_str = f"{entry.key}: {entry.name} ({entry.mcu})"
        if not entry.flashable:
            name_str += " [excluded]"
        blocked_reason = _blocked_reason_for_entry(entry, blocked_list)
        if blocked_reason:
            name_str += " [blocked]"

        if blocked_reason:
            matches = entry_matches.get(key, [])
            if matches:
                detail = f"{blocked_reason} [{matches[0].filename}]"
            else:
                detail = blocked_reason
            out.device_line("BLK", name_str, detail)
        elif key in duplicate_entry_keys:
            devices = entry_matches.get(key, [])
            detail = ", ".join(d.filename for d in devices)
            out.device_line("DUP", name_str, detail)
        elif entry_matches.get(key):
            device = entry_matches[key][0]
            out.device_line("REG", name_str, device.filename)
        else:
            out.device_line("REG", name_str, "(disconnected)")

        # Show MCU software version if available
        if mcu_versions:
            version = get_mcu_version_for_device(entry.mcu)
            if version:
                out.info("", f"       MCU software version: {version}")

    # Show unmatched (unknown/blocked) USB devices if any
    if unmatched:
        # Separate blocked from new devices
        blocked_unmatched = []
        new_unmatched = []
        for device in unmatched:
            blocked_reason = _blocked_reason_for_filename(device.filename, blocked_list)
            if blocked_reason or not is_supported_device(device.filename):
                blocked_unmatched.append((device, blocked_reason or "Unsupported USB device"))
            else:
                new_unmatched.append(device)

        # Show new (unregistered) devices
        if new_unmatched:
            out.info("", "")  # blank line for separation
            for device in new_unmatched:
                out.device_line("NEW", device.filename, "Unregistered device")

        # Show blocked devices with label
        if blocked_unmatched:
            out.info("", "")  # blank line for separation
            out.info("Blocked devices", "")
            for device, reason in blocked_unmatched:
                out.device_line("BLK", device.filename, reason)

        # Only show hint if there are new devices and not from menu
        if new_unmatched and not from_menu:
            out.info("Devices", "Use --add-device to register unknown devices.")

    # Show host Klipper version at the end
    if host_version:
        out.info("", "")  # blank line for separation
        out.info("Version", f"Host Klipper: {host_version}")

    return 0


def cmd_add_device(registry, out, selected_device=None) -> int:
    """Interactive wizard to register a new device.

    Args:
        registry: Registry instance for device persistence.
        out: Output interface for user messages.
        selected_device: Optional pre-selected DiscoveredDevice (from TUI).
            When provided, skips discovery scan, listing, and selection prompt.
    """
    # Import discovery functions for USB scanning
    from .discovery import (
        scan_serial_devices,
        extract_mcu_from_serial,
        generate_serial_pattern,
        is_supported_device,
        match_devices,
    )
    from .models import DeviceEntry, GlobalConfig
    from .tui import _get_menu_choice

    # TTY check: wizard requires interactive terminal
    if not sys.stdin.isatty():
        out.error(
            "Interactive terminal required for --add-device. Run from SSH terminal."
        )
        return 1

    if selected_device is not None:
        # TUI path: device already selected, skip discovery/listing/selection
        selected = selected_device

        # Determine if this device is already registered
        registry_data = registry.load()
        devices = scan_serial_devices()
        existing_entry = None
        for entry in registry_data.devices.values():
            matches = match_devices(entry.serial_pattern, devices)
            for matched_dev in matches:
                if matched_dev.filename == selected.filename:
                    existing_entry = entry
                    break
            if existing_entry is not None:
                break
    else:
        # CLI path: full discovery scan and selection
        # Step 1: Scan USB devices
        out.info("Discovery", "Scanning for USB serial devices...")
        devices = scan_serial_devices()
        if not devices:
            out.error("No USB devices found. Plug in a board and try again.")
            return 1

        registry_data = registry.load()
        blocked_list = _build_blocked_list(registry_data)

        entry_matches: dict[str, list] = {}
        device_matches: dict[str, list] = {}
        for entry in registry_data.devices.values():
            matches = match_devices(entry.serial_pattern, devices)
            entry_matches[entry.key] = matches
            for device in matches:
                device_matches.setdefault(device.filename, []).append(entry)

        duplicate_entry_keys = {
            key for key, matches in entry_matches.items() if len(matches) > 1
        }

        registered_devices: list[tuple[object, object]] = []
        new_devices: list = []
        blocked_devices: list[tuple[object, str]] = []
        duplicate_devices: list[tuple[object, list]] = []

        for device in devices:
            blocked_reason = _blocked_reason_for_filename(device.filename, blocked_list)
            if blocked_reason or not is_supported_device(device.filename):
                blocked_devices.append((device, blocked_reason or "Unsupported USB device"))
                continue

            entries = device_matches.get(device.filename, [])
            if entries and (
                len(entries) > 1
                or any(entry.key in duplicate_entry_keys for entry in entries)
            ):
                duplicate_devices.append((device, entries))
                continue

            if entries:
                registered_devices.append((device, entries[0]))
            else:
                new_devices.append(device)

        summary = (
            f"{len(devices)} USB devices found: {len(registered_devices)} registered, "
            f"{len(new_devices)} new, {len(blocked_devices)} blocked, "
            f"{len(duplicate_devices)} duplicate"
        )
        out.info("Discovery", summary)

        selectable: list[tuple[object, object | None]] = []
        if registered_devices:
            out.info("Discovery", f"Registered devices ({len(registered_devices)}):")
            for device, entry in registered_devices:
                idx = len(selectable) + 1
                label = f"{idx}. {device.filename}"
                detail = f"{entry.key} ({entry.mcu})"
                out.device_line("REG", label, detail)
                selectable.append((device, entry))

        if new_devices:
            out.info("Discovery", f"New devices ({len(new_devices)}):")
            for device in new_devices:
                idx = len(selectable) + 1
                label = f"{idx}. {device.filename}"
                out.device_line("NEW", label, "Unregistered device")
                selectable.append((device, None))

        if duplicate_devices:
            out.info(
                "Discovery", f"Duplicate devices (not eligible) ({len(duplicate_devices)}):"
            )
            for device, entries in duplicate_devices:
                keys = ", ".join(entry.key for entry in entries)
                out.device_line("DUP", device.filename, f"Matches: {keys}")

        if blocked_devices:
            out.info(
                "Discovery", f"Blocked devices (not eligible) ({len(blocked_devices)}):"
            )
            for device, reason in blocked_devices:
                out.device_line("BLK", device.filename, reason)

        if not selectable:
            out.error("No eligible devices available to add.")
            return 1

        choices = ["0"] + [str(i) for i in range(1, len(selectable) + 1)]
        choice = _get_menu_choice(
            choices,
            out,
            max_attempts=3,
            prompt="Select device number (0/q to cancel): ",
        )
        if choice is None or choice == "0":
            out.info("Registry", "Add device cancelled")
            return 0

        selected, existing_entry = selectable[int(choice) - 1]

    # Check if selected device is already registered
    if existing_entry is not None:
        existing = existing_entry
        if not out.confirm(
            f"Device already registered as '{existing.key}'. Remove and re-add this device?",
            default=False,
        ):
            out.info("Registry", "Add device cancelled")
            return 0
        registry.remove(existing.key)
        out.success(f"Removed existing device '{existing.key}'")
        _remove_cached_config(existing.key, out, prompt=True)
        registry_data = registry.load()

    # Step 3: Global config (first run only)
    if not registry_data.devices:
        out.info("Setup", "First device registration - configuring global paths...")
        klipper_dir = out.prompt("Klipper source directory", default="~/klipper")
        katapult_dir = out.prompt("Katapult source directory", default="~/katapult")
        registry.save_global(
            GlobalConfig(
                klipper_dir=klipper_dir,
                katapult_dir=katapult_dir,
                default_flash_method="katapult",
                allow_flash_fallback=True,
            )
        )
        out.success("Global configuration saved")

    # Step 4: Device key
    device_key = None
    for attempt in range(3):
        key_input = out.prompt(
            "Device key (used with --device flag, e.g., 'octopus-pro')"
        )
        if not key_input:
            out.warn("Device key cannot be empty.")
            continue
        if " " in key_input:
            out.warn("Device key cannot contain spaces.")
            continue
        if registry.get(key_input) is not None:
            out.warn(
                f"Device '{key_input}' already registered. Choose a different key."
            )
            continue
        device_key = key_input
        break
    if device_key is None:
        out.error("Too many invalid inputs.")
        return 1

    # Step 5: Display name
    display_name = out.prompt("Display name (e.g., 'Octopus Pro v1.1')")
    if not display_name:
        display_name = device_key  # Fallback to key if empty

    # Step 6: MCU auto-detection
    detected_mcu = extract_mcu_from_serial(selected.filename)
    if detected_mcu:
        if out.confirm(f"Detected MCU: {detected_mcu}. Correct?", default=True):
            mcu = detected_mcu
        else:
            mcu = out.prompt("Enter MCU type")
    else:
        out.info("Discovery", "Could not auto-detect MCU from device name.")
        mcu = out.prompt("MCU type (e.g., stm32h723, rp2040)")

    if not mcu:
        out.error("MCU type is required.")
        return 1

    # Step 7: Serial pattern
    serial_pattern = generate_serial_pattern(selected.filename)
    out.info("Registry", f"Serial pattern: {serial_pattern}")

    # Check if pattern matches multiple connected devices (duplicate USB IDs)
    pattern_matches = match_devices(serial_pattern, devices)
    if len(pattern_matches) > 1:
        out.error(
            "Serial pattern matches multiple connected devices. "
            "Unplug duplicates and retry."
        )
        for device in pattern_matches:
            out.device_line("DUP", device.filename, "Duplicate USB ID")
        return 1

    # Check for pattern overlap with existing devices
    registry_data = registry.load()
    for existing_key, existing_entry in registry_data.devices.items():
        if existing_entry.serial_pattern == serial_pattern:
            out.error(
                f"Serial pattern already registered to '{existing_key}'. "
                "Remove it first or choose a different device."
            )
            return 1
        if fnmatch.fnmatch(selected.filename, existing_entry.serial_pattern):
            out.error(
                f"Selected device matches existing entry '{existing_key}'. "
                "Remove it first or replace it."
            )
            return 1

    # Step 8: Flash method
    flash_method = None
    default_method = "katapult"
    if registry_data.global_config is not None:
        default_method = registry_data.global_config.default_flash_method or "katapult"
    if default_method not in ("katapult", "make_flash"):
        default_method = "katapult"
    if registry_data.global_config is not None:
        fallback_state = (
            "enabled"
            if registry_data.global_config.allow_flash_fallback
            else "disabled"
        )
        out.info(
            "Flash",
            f"Preferred method default is {default_method}. Flash fallback is {fallback_state}.",
        )
    for attempt in range(3):
        method_input = (
            out.prompt("Preferred flash method", default=default_method).strip().lower()
        )
        if method_input in ("katapult", "make_flash"):
            # If same as global default, store None to inherit
            if method_input == default_method:
                flash_method = None
            else:
                flash_method = method_input
            break
        out.warn("Flash method must be 'katapult' or 'make_flash'.")
    else:
        out.error("Too many invalid inputs.")
        return 1

    # Step 9: Ask if device is flashable
    exclude_from_flash = out.confirm(
        "Exclude this device from flashing?", default=False
    )
    is_flashable = not exclude_from_flash

    # Step 10: Create and save
    entry = DeviceEntry(
        key=device_key,
        name=display_name,
        mcu=mcu,
        serial_pattern=serial_pattern,
        flash_method=flash_method,
        flashable=is_flashable,
    )
    registry.add(entry)
    out.success(f"Registered '{device_key}' ({display_name})")
    return 0


def main() -> int:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args()

    # Late imports for fast startup
    from .output import CliOutput
    from .registry import Registry
    from .errors import KlipperFlashError

    out = CliOutput()

    # Registry file lives next to this module
    registry_path = Path(__file__).parent / "devices.json"
    registry = Registry(str(registry_path))

    try:
        # Handle management commands
        if args.add_device:
            return cmd_add_device(registry, out)
        elif args.list_devices:
            return cmd_list_devices(registry, out)
        elif args.remove_device:
            return cmd_remove_device(registry, args.remove_device, out)
        elif args.exclude_device:
            return cmd_exclude_device(registry, args.exclude_device, out)
        elif args.include_device:
            return cmd_include_device(registry, args.include_device, out)

        # Handle explicit --device flash
        elif args.device:
            return cmd_flash(
                registry, args.device, out, skip_menuconfig=args.skip_menuconfig
            )

        # No args: interactive menu on TTY, help on non-TTY
        else:
            if sys.stdin.isatty():
                from .tui import run_menu

                return run_menu(registry, out)
            else:
                parser.print_help()
                return 0

    except KeyboardInterrupt:
        out.warn("Aborted.")
        return 130
    except KlipperFlashError as e:
        out.error(str(e))
        return 1
    except Exception as e:
        out.error(f"Unexpected error: {e}")
        return 3


if __name__ == "__main__":
    sys.exit(main())
