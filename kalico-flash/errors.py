"""Centralized exception hierarchy for kalico-flash."""
from __future__ import annotations

import textwrap


def format_error(
    error_type: str,
    message: str,
    context: dict[str, str] | None = None,
    recovery: str | None = None,
) -> str:
    """Format an error message with optional context and recovery guidance.

    Produces plain ASCII output, wrapped to 80 columns per line.
    No ANSI escape codes or Unicode box-drawing characters.

    Args:
        error_type: Category of error (e.g., "Device not found", "Build failed")
        message: Primary error description
        context: Optional dict of contextual information (device, mcu, path, etc.)
        recovery: Optional prose paragraph with recovery steps and diagnostic commands

    Returns:
        Multi-line formatted error string ready for display
    """
    lines = [f"[FAIL] {error_type}: {message}"]

    if context:
        # Build context prose from key-value pairs
        context_parts = []
        if "device" in context:
            context_parts.append(f"device '{context['device']}'")
        if "mcu" in context:
            context_parts.append(f"MCU '{context['mcu']}'")
        if "path" in context:
            context_parts.append(f"path '{context['path']}'")
        if "expected" in context and "actual" in context:
            context_parts.append(
                f"expected '{context['expected']}' but found '{context['actual']}'"
            )
        # Include any other keys not explicitly handled
        for key, value in context.items():
            if key not in ("device", "mcu", "path", "expected", "actual"):
                context_parts.append(f"{key} '{value}'")

        if context_parts:
            context_prose = "Affected: " + ", ".join(context_parts) + "."
            lines.append("")
            lines.append(textwrap.fill(context_prose, width=80))

    if recovery:
        lines.append("")
        lines.append(textwrap.fill(recovery, width=80))

    return "\n".join(lines)


# Error templates for consistent messaging across the codebase.
# Each template provides: error_type, message_template, and recovery_template.
# Templates use {placeholders} for context substitution.
ERROR_TEMPLATES: dict[str, dict[str, str]] = {
    # Build errors (make menuconfig, make clean, make)
    "build_failed": {
        "error_type": "Build failed",
        "message_template": "Firmware compilation failed for {device}",
        "recovery_template": (
            "Check the build output above for specific errors. Common issues "
            "include missing toolchain components or invalid configuration options. "
            "Run `make menuconfig` in the Klipper directory to verify your settings, "
            "then try the build again."
        ),
    },
    "menuconfig_failed": {
        "error_type": "Menuconfig failed",
        "message_template": "make menuconfig exited with an error",
        "recovery_template": (
            "The menuconfig interface could not start. Ensure you have ncurses "
            "development libraries installed. On Debian/Ubuntu systems, run "
            "`sudo apt install libncurses-dev`. Check that the Klipper source "
            "directory exists and contains a valid Makefile."
        ),
    },
    # Device not found errors
    "device_not_registered": {
        "error_type": "Device not found",
        "message_template": "No device registered with key '{device}'",
        "recovery_template": (
            "Run `python flash.py --list-devices` to see all registered devices. "
            "If this is a new board, use `python flash.py --add-device` to register "
            "it first. Device keys are case-sensitive."
        ),
    },
    "device_not_connected": {
        "error_type": "Device not connected",
        "message_template": "Device '{device}' is registered but not connected",
        "recovery_template": (
            "The device is in your registry but was not found on USB. Check that "
            "the board is powered and connected via USB. Run `ls /dev/serial/by-id/` "
            "to see currently connected devices. If the device appears with a "
            "different serial path, you may need to update the registration."
        ),
    },
    # MCU mismatch errors
    "mcu_mismatch": {
        "error_type": "MCU mismatch",
        "message_template": "Config MCU '{actual}' does not match registered MCU '{expected}'",
        "recovery_template": (
            "The cached configuration was built for a different MCU than the one "
            "registered for this device. This can happen if you copied a config "
            "from another board or modified the .config file directly. Run without "
            "`--skip-menuconfig` to reconfigure, or update the device registration "
            "if the MCU type has changed."
        ),
    },
    # Service control errors
    "service_stop_failed": {
        "error_type": "Service error",
        "message_template": "Failed to stop Klipper service",
        "recovery_template": (
            "Could not stop the Klipper service before flashing. Check that you "
            "have passwordless sudo configured for service control. Run "
            "`sudo systemctl status klipper` to see the current service state. "
            "You can try manually stopping with `sudo systemctl stop klipper` "
            "before running the flash command."
        ),
    },
    "service_start_failed": {
        "error_type": "Service error",
        "message_template": "Failed to restart Klipper service after flash",
        "recovery_template": (
            "The flash operation completed but Klipper could not be restarted. "
            "Run `sudo systemctl start klipper` to start it manually. Check "
            "`sudo journalctl -u klipper -n 50` for startup errors. The firmware "
            "was flashed successfully, so the issue is with the service, not the "
            "board."
        ),
    },
    # Flash errors
    "flash_failed": {
        "error_type": "Flash failed",
        "message_template": "Could not flash firmware to {device}",
        "recovery_template": (
            "Both Katapult and make flash methods failed. Ensure the device is in "
            "bootloader mode. For Katapult, the device should appear with a "
            "'katapult_' prefix in `/dev/serial/by-id/`. For DFU mode, check "
            "`lsusb` for your MCU. Try power-cycling the board with the BOOT "
            "button held, then run the flash command again."
        ),
    },
    "katapult_not_found": {
        "error_type": "Katapult not available",
        "message_template": "Katapult flashtool not found at {path}",
        "recovery_template": (
            "The Katapult flash tool could not be found. Falling back to make "
            "flash method. If you want to use Katapult, ensure it is installed "
            "at ~/katapult and contains the flashtool.py script. Katapult provides "
            "faster flashing without requiring DFU mode."
        ),
    },
    # Moonraker errors (placeholder for Phase 5)
    "moonraker_unavailable": {
        "error_type": "Moonraker unavailable",
        "message_template": "Could not connect to Moonraker API",
        "recovery_template": (
            "The Moonraker API is not responding. Check that Moonraker is running "
            "with `sudo systemctl status moonraker`. The flash operation will "
            "proceed without print status checking. If you want to ensure the "
            "printer is idle before flashing, verify Moonraker is accessible first."
        ),
    },
    "printer_busy": {
        "error_type": "Printer busy",
        "message_template": "Printer is currently {state}",
        "recovery_template": (
            "The printer appears to be in use. Flashing firmware while printing "
            "will abort the print and may damage the print or printer. Wait for "
            "the current operation to complete, or use `--force` if you are certain "
            "it is safe to proceed."
        ),
    },
    # Excluded device error
    "device_excluded": {
        "error_type": "Device excluded",
        "message_template": "Device '{device}' is marked as non-flashable",
        "recovery_template": (
            "This device has been excluded from flashing, typically because it "
            "uses specialized firmware or should not be modified. If you need to "
            "flash this device, first run `python flash.py --include-device {device}` "
            "to mark it as flashable again."
        ),
    },
}


class KlipperFlashError(Exception):
    """Base for all kalico-flash errors."""
    pass


class RegistryError(KlipperFlashError):
    """Registry file errors: corrupt JSON, missing fields, duplicate keys."""
    pass


class DeviceNotFoundError(KlipperFlashError):
    """Named device not in registry or not physically connected."""

    def __init__(self, identifier: str):
        super().__init__(f"Device not found: {identifier}")
        self.identifier = identifier


class DiscoveryError(KlipperFlashError):
    """USB discovery failures."""
    pass


class ConfigError(KlipperFlashError):
    """Config file errors: missing, corrupt, MCU mismatch."""
    pass


class BuildError(KlipperFlashError):
    """Build failures: make menuconfig, make clean, make."""
    pass


class ServiceError(KlipperFlashError):
    """Klipper service lifecycle errors: stop/start failures."""
    pass


class FlashError(KlipperFlashError):
    """Flash operation failures: Katapult, make flash, device not found."""
    pass
