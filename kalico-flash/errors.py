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
        # Preserve newlines in numbered lists: wrap each line individually
        for line in recovery.split('\n'):
            if line.strip():
                lines.append(textwrap.fill(line, width=80))
            else:
                lines.append('')  # Preserve blank lines

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
            "1. Check the build output above for the specific error message\n"
            "2. Run `make menuconfig` in ~/klipper to verify configuration\n"
            "3. Ensure toolchain is installed: `arm-none-eabi-gcc --version`\n"
            "4. Clean and retry: `cd ~/klipper && make clean && make`"
        ),
    },
    "menuconfig_failed": {
        "error_type": "Menuconfig failed",
        "message_template": "make menuconfig exited with an error",
        "recovery_template": (
            "1. Install ncurses: `sudo apt install libncurses-dev`\n"
            "2. Verify Klipper directory exists: `ls ~/klipper/Makefile`\n"
            "3. Try running menuconfig directly: `cd ~/klipper && make menuconfig`"
        ),
    },
    # Device not found errors
    "device_not_registered": {
        "error_type": "Device not found",
        "message_template": "No device registered with key '{device}'",
        "recovery_template": (
            "1. List registered devices: `python flash.py --list-devices`\n"
            "2. Register new device: `python flash.py --add-device`\n"
            "3. Check device key spelling (case-sensitive)"
        ),
    },
    "device_not_connected": {
        "error_type": "Device not connected",
        "message_template": "Device '{device}' is registered but not connected",
        "recovery_template": (
            "1. Check USB connection and board power\n"
            "2. List connected devices: `ls /dev/serial/by-id/`\n"
            "3. If device shows with different name, re-register with `--add-device`"
        ),
    },
    # MCU mismatch errors
    "mcu_mismatch": {
        "error_type": "MCU mismatch",
        "message_template": "Config MCU '{actual}' does not match registered MCU '{expected}'",
        "recovery_template": (
            "1. Run without --skip-menuconfig to reconfigure\n"
            "2. Or update device registration if MCU changed\n"
            "3. Verify config: `grep CONFIG_MCU ~/klipper/.config`"
        ),
    },
    # Service control errors
    "service_stop_failed": {
        "error_type": "Service error",
        "message_template": "Failed to stop Klipper service",
        "recovery_template": (
            "1. Check service status: `sudo systemctl status klipper`\n"
            "2. Verify passwordless sudo: `sudo -n systemctl stop klipper`\n"
            "3. Try manual stop: `sudo systemctl stop klipper`"
        ),
    },
    "service_start_failed": {
        "error_type": "Service error",
        "message_template": "Failed to restart Klipper service after flash",
        "recovery_template": (
            "1. Start manually: `sudo systemctl start klipper`\n"
            "2. Check logs: `sudo journalctl -u klipper -n 50`\n"
            "3. Firmware was flashed - issue is service, not board"
        ),
    },
    # Flash errors
    "flash_failed": {
        "error_type": "Flash failed",
        "message_template": "Could not flash firmware to {device}",
        "recovery_template": (
            "1. Power cycle the board with BOOT button held\n"
            "2. Check bootloader mode: `ls /dev/serial/by-id/ | grep -i katapult`\n"
            "3. For DFU mode, check: `lsusb | grep -i stm32`\n"
            "4. Retry flash after board enters bootloader"
        ),
    },
    "katapult_not_found": {
        "error_type": "Katapult not available",
        "message_template": "Katapult flashtool not found at {path}",
        "recovery_template": (
            "1. Falling back to make flash method\n"
            "2. To use Katapult, install at ~/katapult\n"
            "3. Verify: `ls ~/katapult/scripts/flashtool.py`"
        ),
    },
    # Moonraker errors (placeholder for Phase 5)
    "moonraker_unavailable": {
        "error_type": "Moonraker unavailable",
        "message_template": "Could not connect to Moonraker API",
        "recovery_template": (
            "1. Check Moonraker status: `sudo systemctl status moonraker`\n"
            "2. Restart Moonraker: `sudo systemctl restart moonraker`\n"
            "3. Verify API: `curl http://localhost:7125/server/info`\n"
            "4. Flash proceeds without print status check if unavailable"
        ),
    },
    "printer_busy": {
        "error_type": "Printer busy",
        "message_template": "Printer is currently {state}",
        "recovery_template": (
            "1. Wait for current print/operation to complete\n"
            "2. Check printer status in Fluidd/Mainsail dashboard\n"
            "3. Use `--force` flag only if safe to interrupt operation\n"
            "4. Cancel print first if flashing is urgent"
        ),
    },
    # Excluded device error
    "device_excluded": {
        "error_type": "Device excluded",
        "message_template": "Device '{device}' is marked as non-flashable",
        "recovery_template": (
            "1. Include device: `python flash.py --include-device {device}`\n"
            "2. List all devices: `python flash.py --list-devices`\n"
            "3. Device was excluded to prevent accidental flash"
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

    def __init__(self, identifier: str, *, connected: bool = False):
        super().__init__(f"Device not found: {identifier}")
        self.identifier = identifier
        self.connected = connected  # True if in registry but not physically connected


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


class ConfigMismatchError(KlipperFlashError):
    """Cached config MCU does not match registered device MCU."""

    def __init__(self, expected_mcu: str, actual_mcu: str, device_key: str):
        super().__init__(
            f"MCU mismatch for {device_key}: expected {expected_mcu}, got {actual_mcu}"
        )
        self.expected_mcu = expected_mcu
        self.actual_mcu = actual_mcu
        self.device_key = device_key


class ExcludedDeviceError(KlipperFlashError):
    """Device is marked as non-flashable (excluded from flashing)."""

    def __init__(self, device_key: str):
        super().__init__(f"Device '{device_key}' is excluded from flashing")
        self.device_key = device_key
