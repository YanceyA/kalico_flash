#!/usr/bin/env python3
"""CLI entry point for kalico-flash.

Unified tool for building and flashing Klipper firmware to USB-connected
MCU boards. Provides device registration, discovery, and full build/flash
workflow with phase-labeled output.

Usage:
    python flash.py --add-device        # Register a new board
    python flash.py --list-devices      # Show registered boards and status
    python flash.py --remove-device KEY # Remove a registered board
    python flash.py --device KEY        # Build and flash the named device
    python flash.py                     # Interactive: select device to flash

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
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


# Python version guard
if sys.version_info < (3, 9):
    sys.exit("Error: kalico-flash requires Python 3.9 or newer.")


VERSION = "0.1.0"


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="flash.py",
        description="Build and flash Klipper firmware for USB-connected MCU boards.",
        epilog="Run without args for interactive device selection, or use -d KEY "
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
        "-d", "--device",
        metavar="KEY",
        help="Device key to build and flash (run without --device for interactive selection)",
    )
    parser.add_argument(
        "-s", "--skip-menuconfig",
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


def cmd_build(registry, device_key: str, out) -> int:
    """Build firmware for a registered device.

    Orchestrates: load cached config -> menuconfig -> save config -> MCU validation -> build
    """
    # Late imports for fast startup
    from config import ConfigManager
    from build import run_menuconfig, run_build
    from errors import ConfigError

    # Load device entry
    entry = registry.get(device_key)
    if entry is None:
        out.error(f"Device '{device_key}' not found.")
        return 1

    # Load global config for klipper_dir
    data = registry.load()
    if data.global_config is None:
        out.error("Global config not set. Run --add-device first.")
        return 1

    klipper_dir = data.global_config.klipper_dir
    out.info("Build", f"Building firmware for {entry.name} ({entry.mcu})")

    # Initialize config manager
    config_mgr = ConfigManager(device_key, klipper_dir)

    # Step 1: Load cached config (if exists)
    if config_mgr.load_cached_config():
        out.info("Config", f"Loaded cached config for '{device_key}'")
    else:
        out.info("Config", "No cached config found, starting fresh")

    # Step 2: Run menuconfig
    out.info("Config", "Launching menuconfig...")
    ret_code, was_saved = run_menuconfig(klipper_dir, str(config_mgr.klipper_config_path))

    if ret_code != 0:
        out.error(f"menuconfig exited with code {ret_code}")
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
        out.error(f"Failed to cache config: {e}")
        return 1

    # Step 4: MCU validation
    try:
        is_match, actual_mcu = config_mgr.validate_mcu(entry.mcu)
        if not is_match:
            out.error(
                f"MCU mismatch: config has '{actual_mcu}' but device "
                f"'{device_key}' expects '{entry.mcu}'"
            )
            out.error("Refusing to build wrong firmware. Fix .config and try again.")
            return 1
        out.info("Config", f"MCU validated: {actual_mcu}")
    except ConfigError as e:
        out.error(f"MCU validation failed: {e}")
        return 1

    # Step 5: Build
    out.info("Build", "Running make clean + make...")
    result = run_build(klipper_dir)

    if not result.success:
        out.error(f"Build failed: {result.error_message}")
        return 1

    # Success
    size_kb = result.firmware_size / 1024 if result.firmware_size else 0
    out.success(
        f"Build complete: {result.firmware_path} ({size_kb:.1f} KB) "
        f"in {result.elapsed_seconds:.1f}s"
    )
    return 0


def cmd_flash(registry, device_key, out) -> int:
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

    Returns:
        0 on success, 1 on failure
    """
    import time

    # Late imports for fast startup
    from discovery import scan_serial_devices, find_registered_devices, match_device
    from config import ConfigManager
    from build import run_menuconfig, run_build, TIMEOUT_BUILD
    from service import klipper_service_stopped, verify_passwordless_sudo
    from flasher import flash_device, verify_device_path, TIMEOUT_FLASH
    from errors import ConfigError, DiscoveryError

    # TTY check for interactive mode
    if device_key is None and not sys.stdin.isatty():
        out.error("Interactive terminal required. Use --device KEY or run from SSH terminal.")
        return 1

    # Load registry data
    data = registry.load()
    if data.global_config is None:
        out.error("Global config not set. Run --add-device first.")
        return 1

    # === Phase 1: Discovery ===
    out.phase("Discovery", "Scanning for USB devices...")
    usb_devices = scan_serial_devices()

    if device_key is None:
        # Interactive mode: select from connected registered devices
        if not usb_devices:
            out.error("No USB devices found. Connect a board and try again.")
            return 1

        # Cross-reference with registry
        matched, unmatched = find_registered_devices(usb_devices, data.devices)

        if not matched:
            out.error("No registered devices connected.")
            out.phase("Discovery", "Found USB devices but none are registered:")
            for device in usb_devices:
                out.device_line("??", device.filename, "")
            out.phase("Discovery", "Run --add-device to register a board first.")
            return 1

        # Show numbered list of connected registered devices
        out.phase("Discovery", f"Found {len(matched)} registered device(s):")
        for i, (entry, device) in enumerate(matched):
            out.device_line(str(i + 1), f"{entry.key} ({entry.mcu})", device.path)

        # Single device: auto-select with confirmation
        if len(matched) == 1:
            entry, usb_device = matched[0]
            if out.confirm(f"Flash {entry.name}?", default=True):
                device_key = entry.key
                device_path = usb_device.path
            else:
                out.phase("Discovery", "Cancelled")
                return 0
        else:
            # Multiple devices: prompt for selection
            for attempt in range(3):
                choice = out.prompt("Select device number", default="1")
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(matched):
                        entry, usb_device = matched[idx]
                        device_key = entry.key
                        device_path = usb_device.path
                        break
                    out.warn(f"Invalid selection. Choose 1-{len(matched)}.")
                except ValueError:
                    out.warn("Please enter a number.")
            else:
                out.error("Too many invalid selections.")
                return 1
    else:
        # Explicit --device KEY mode: verify device exists and is connected
        entry = registry.get(device_key)
        if entry is None:
            out.error(f"Device '{device_key}' not found in registry.")
            return 1

        # Find matching USB device
        usb_device = match_device(entry.serial_pattern, usb_devices)
        if usb_device is None:
            out.error(f"Device '{device_key}' is not connected.")
            out.phase("Discovery", f"Looking for: {entry.serial_pattern}")
            return 1

        device_path = usb_device.path

    # Load the device entry for the rest of the workflow
    entry = registry.get(device_key)
    klipper_dir = data.global_config.klipper_dir
    katapult_dir = data.global_config.katapult_dir

    out.phase("Discovery", f"Target: {entry.name} ({entry.mcu}) at {device_path}")

    # === Phase 2: Config ===
    out.phase("Config", f"Loading config for {entry.name}...")
    config_mgr = ConfigManager(device_key, klipper_dir)

    if config_mgr.load_cached_config():
        out.phase("Config", f"Loaded cached config for '{device_key}'")
    else:
        out.phase("Config", "No cached config found, starting fresh")

    out.phase("Config", "Launching menuconfig...")
    ret_code, was_saved = run_menuconfig(klipper_dir, str(config_mgr.klipper_config_path))

    if ret_code != 0:
        out.error(f"menuconfig exited with code {ret_code}")
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
        out.error(f"Failed to cache config: {e}")
        return 1

    # MCU validation
    try:
        is_match, actual_mcu = config_mgr.validate_mcu(entry.mcu)
        if not is_match:
            out.error(
                f"MCU mismatch: config has '{actual_mcu}' but device "
                f"'{device_key}' expects '{entry.mcu}'"
            )
            out.error("Refusing to build wrong firmware. Fix .config and try again.")
            return 1
        out.phase("Config", f"MCU validated: {actual_mcu}")
    except ConfigError as e:
        out.error(f"MCU validation failed: {e}")
        return 1

    # === Phase 3: Build ===
    out.phase("Build", "Running make clean + make...")
    build_result = run_build(klipper_dir, timeout=TIMEOUT_BUILD)

    if not build_result.success:
        out.error(f"Build failed: {build_result.error_message}")
        out.error("Recovery: Check build output above for errors.")
        return 1

    firmware_path = build_result.firmware_path
    size_kb = build_result.firmware_size / 1024 if build_result.firmware_size else 0
    out.phase("Build", f"Firmware ready: {size_kb:.1f} KB in {build_result.elapsed_seconds:.1f}s")

    # === Phase 4: Flash ===
    out.phase("Flash", "Verifying device connection...")
    try:
        verify_device_path(device_path)
    except DiscoveryError as e:
        out.error(str(e))
        out.error("Recovery: Reconnect the device and try again.")
        return 1

    # Check passwordless sudo (informational only - let sudo prompt if needed)
    if not verify_passwordless_sudo():
        out.phase("Flash", "Note: sudo may prompt for password")

    out.phase("Flash", "Stopping Klipper...")
    flash_start = time.monotonic()

    try:
        with klipper_service_stopped():
            out.phase("Flash", "Flashing firmware...")
            flash_result = flash_device(
                device_path=device_path,
                firmware_path=firmware_path,
                katapult_dir=katapult_dir,
                klipper_dir=klipper_dir,
                timeout=TIMEOUT_FLASH,
            )
        out.phase("Flash", "Klipper restarted")
    except Exception as e:
        out.error(f"Flash operation error: {e}")
        out.error("Recovery: Power cycle the board and try again.")
        return 1

    flash_elapsed = time.monotonic() - flash_start

    # === Summary ===
    if flash_result.success:
        out.success(
            f"Flashed {entry.name} via {flash_result.method} in {flash_elapsed:.1f}s"
        )
        return 0
    else:
        out.error(f"Flash failed: {flash_result.error_message}")
        out.error(f"Method attempted: {flash_result.method}")
        out.error("Recovery: Power cycle the board and try again.")
        return 1


def cmd_remove_device(registry, device_key: str, out) -> int:
    """Remove a device from the registry with optional config cleanup."""
    entry = registry.get(device_key)
    if entry is None:
        out.error(f"Device '{device_key}' not found in registry")
        return 1

    if not out.confirm(f"Remove '{device_key}' ({entry.name})?"):
        out.info("Registry", "Removal cancelled")
        return 0

    registry.remove(device_key)
    out.success(f"Removed '{device_key}'")

    # Check for cached config file (Phase 2 creates these in configs/ directory)
    config_dir = Path(__file__).parent / "configs"
    config_file = config_dir / f"{device_key}.config"
    sha_file = config_dir / f"{device_key}.config.sha256"

    try:
        if config_file.exists():
            if out.confirm(f"Also remove cached config for '{device_key}'?", default=False):
                config_file.unlink()
                if sha_file.exists():
                    sha_file.unlink()
                out.success("Cached config removed")
            else:
                out.info("Registry", "Cached config kept")
    except FileNotFoundError:
        # configs/ directory doesn't exist yet (Phase 1) -- nothing to clean up
        pass

    return 0


def cmd_list_devices(registry, out) -> int:
    """List all registered devices with connection status.

    Cross-references registered devices against live USB scan to show:
    - [OK] Connected devices with their /dev/serial/by-id/ path
    - [--] Disconnected devices (registered but not currently connected)
    - [??] Unknown USB devices (connected but not registered)
    """
    from discovery import scan_serial_devices, find_registered_devices

    # Load registry and scan USB devices
    data = registry.load()
    usb_devices = scan_serial_devices()

    # Cross-reference registered vs discovered
    matched, unmatched = find_registered_devices(usb_devices, data.devices)

    # Build lookup dict: device key -> DiscoveredDevice (for connected devices)
    connected_map = {entry.key: device for entry, device in matched}

    # Handle: no registered devices AND no USB devices
    if not data.devices and not usb_devices:
        out.info("Devices", "No registered devices and no USB devices found.")
        return 0

    # Handle: no registered devices BUT USB devices exist (first-run UX)
    if not data.devices and usb_devices:
        out.info("Devices", f"No registered devices. Found {len(usb_devices)} USB devices.")
        for device in usb_devices:
            out.device_line("??", "Unknown device", f"[{device.filename}]")
        out.info("Devices", "Run --add-device to register a board.")
        return 0

    # Normal display: show registered devices with connection status
    out.info("Devices", f"{len(data.devices)} registered, {len(usb_devices)} USB devices found")

    for key in sorted(data.devices.keys()):
        entry = data.devices[key]
        if key in connected_map:
            # Connected: show path
            device = connected_map[key]
            out.device_line("OK", f"{entry.key}: {entry.name} ({entry.mcu})", device.path)
        else:
            # Disconnected
            out.device_line("--", f"{entry.key}: {entry.name} ({entry.mcu})", "(disconnected)")

    # Show unmatched (unknown) USB devices if any
    if unmatched:
        out.info("", "")  # blank line for separation
        for device in unmatched:
            out.device_line("??", "Unknown device", f"[{device.filename}]")
        out.info("Devices", "Use --add-device to register unknown devices.")

    return 0


def cmd_add_device(registry, out) -> int:
    """Interactive wizard to register a new device."""
    # Import discovery functions for USB scanning
    from discovery import scan_serial_devices, extract_mcu_from_serial, generate_serial_pattern
    from models import DeviceEntry, GlobalConfig
    import fnmatch

    # TTY check: wizard requires interactive terminal
    if not sys.stdin.isatty():
        out.error("Interactive terminal required for --add-device. Run from SSH terminal.")
        return 1

    # Step 1: Scan USB devices
    out.info("Discovery", "Scanning for USB serial devices...")
    devices = scan_serial_devices()
    if not devices:
        out.error("No USB devices found. Plug in a board and try again.")
        return 1

    out.info("Discovery", f"Found {len(devices)} USB serial device(s):")
    for i, device in enumerate(devices):
        out.device_line(str(i + 1), device.filename, device.path)

    # Step 2: Select device
    selected = None
    for attempt in range(3):
        choice = out.prompt("Select device number", default="1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(devices):
                selected = devices[idx]
                break
            out.warn(f"Invalid selection. Choose 1-{len(devices)}.")
        except ValueError:
            out.warn("Please enter a number.")
    if selected is None:
        out.error("Too many invalid selections.")
        return 1

    # Step 3: Global config (first run only)
    registry_data = registry.load()
    if not registry_data.devices:
        out.info("Setup", "First device registration - configuring global paths...")
        klipper_dir = out.prompt("Klipper source directory", default="~/klipper")
        katapult_dir = out.prompt("Katapult source directory", default="~/katapult")
        registry.save_global(GlobalConfig(
            klipper_dir=klipper_dir,
            katapult_dir=katapult_dir,
            default_flash_method="katapult",
        ))
        out.success("Global configuration saved")

    # Step 4: Device key
    device_key = None
    for attempt in range(3):
        key_input = out.prompt("Device key (used with --device flag, e.g., 'octopus-pro')")
        if not key_input:
            out.warn("Device key cannot be empty.")
            continue
        if " " in key_input:
            out.warn("Device key cannot contain spaces.")
            continue
        if registry.get(key_input) is not None:
            out.warn(f"Device '{key_input}' already registered. Choose a different key.")
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

    # Check for pattern overlap with existing devices
    registry_data = registry.load()
    for existing_key, existing_entry in registry_data.devices.items():
        # Check if new pattern would match same devices as existing
        if fnmatch.fnmatch(selected.filename, existing_entry.serial_pattern):
            out.warn(
                f"Pattern overlap: '{serial_pattern}' may conflict with "
                f"existing device '{existing_key}' ({existing_entry.serial_pattern})"
            )
            break

    # Step 8: Flash method
    flash_method = None
    for attempt in range(3):
        method_input = out.prompt("Flash method", default="katapult")
        if method_input in ("katapult", "make_flash"):
            # If same as global default, store None to inherit
            if method_input == "katapult":
                flash_method = None
            else:
                flash_method = method_input
            break
        out.warn("Flash method must be 'katapult' or 'make_flash'.")
    else:
        out.error("Too many invalid inputs.")
        return 1

    # Step 9: Create and save
    entry = DeviceEntry(
        key=device_key,
        name=display_name,
        mcu=mcu,
        serial_pattern=serial_pattern,
        flash_method=flash_method,
    )
    registry.add(entry)
    out.success(f"Registered '{device_key}' ({display_name})")
    return 0


def main() -> int:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args()

    # Late imports for fast startup
    from output import CliOutput
    from registry import Registry
    from errors import KlipperFlashError

    out = CliOutput()

    # Registry file lives next to flash.py
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

        # Handle flash workflow (explicit --device or interactive selection)
        else:
            # args.device is None for interactive mode, or a specific key
            return cmd_flash(registry, args.device, out)

    except KeyboardInterrupt:
        print("\nAborted.")
        return 130
    except KlipperFlashError as e:
        out.error(str(e))
        return 1
    except Exception as e:
        out.error(f"Unexpected error: {e}")
        return 3


if __name__ == "__main__":
    sys.exit(main())
