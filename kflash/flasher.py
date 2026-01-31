"""Dual-method flash operations: Katapult-first with make-flash fallback."""

from __future__ import annotations

import fnmatch
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Callable, Optional

from .errors import DiscoveryError, format_error
from .models import FlashResult, KatapultCheckResult

# Default timeout for flash operations (from CONTEXT.md)
TIMEOUT_FLASH = 60

# Katapult detection timing (from Phase 21 hardware research)
BOOTLOADER_ENTRY_TIMEOUT = 5.0   # Max wait for flashtool.py -r
USB_RESET_SLEEP = 0.5            # Pause between deauthorize/reauthorize
POLL_INTERVAL = 0.25             # Serial device polling interval
POLL_TIMEOUT = 5.0               # Max wait for device reappearance


def verify_device_path(device_path: str) -> None:
    """Verify the device is still connected.

    Args:
        device_path: Path to the USB serial device.

    Raises:
        DiscoveryError: If the device is not found.
    """
    if not Path(device_path).exists():
        msg = format_error(
            "Device disconnected",
            "Device no longer connected after build",
            context={"path": device_path},
            recovery=(
                "1. Check USB cable connection\n"
                "2. Verify board power LED is on\n"
                "3. List devices: ls /dev/serial/by-id/\n"
                "4. Reconnect and retry flash"
            ),
        )
        raise DiscoveryError(msg)


def _try_katapult_flash(
    device_path: str,
    firmware_path: str,
    katapult_dir: str,
    timeout: int,
) -> FlashResult:
    """Attempt to flash using Katapult flashtool.py.

    Args:
        device_path: Path to the USB serial device.
        firmware_path: Path to the firmware binary (klipper.bin).
        katapult_dir: Path to the Katapult directory.
        timeout: Seconds before timeout.

    Returns:
        FlashResult with success status and details.
    """
    start = time.monotonic()

    # Build path to flashtool.py
    flashtool = Path(katapult_dir).expanduser() / "scripts" / "flashtool.py"

    if not flashtool.exists():
        return FlashResult(
            success=False,
            method="katapult",
            elapsed_seconds=time.monotonic() - start,
            error_message=f"Katapult flashtool not found: {flashtool}",
        )

    try:
        result = subprocess.run(
            ["python3", str(flashtool), "-d", device_path, "-f", firmware_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = time.monotonic() - start

        if result.returncode == 0:
            return FlashResult(
                success=True,
                method="katapult",
                elapsed_seconds=elapsed,
            )
        else:
            return FlashResult(
                success=False,
                method="katapult",
                elapsed_seconds=elapsed,
                error_message=result.stderr.strip() or result.stdout.strip(),
            )

    except subprocess.TimeoutExpired:
        return FlashResult(
            success=False,
            method="katapult",
            elapsed_seconds=timeout,
            error_message=f"Flash timeout ({timeout}s) - device may need manual recovery",
        )


def _try_make_flash(
    device_path: str,
    klipper_dir: str,
    timeout: int,
) -> FlashResult:
    """Attempt to flash using make flash.

    Args:
        device_path: Path to the USB serial device.
        klipper_dir: Path to the Klipper directory.
        timeout: Seconds before timeout.

    Returns:
        FlashResult with success status and details.
    """
    start = time.monotonic()
    klipper_path = Path(klipper_dir).expanduser()

    try:
        result = subprocess.run(
            ["make", f"FLASH_DEVICE={device_path}", "flash"],
            cwd=str(klipper_path),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = time.monotonic() - start

        if result.returncode == 0:
            return FlashResult(
                success=True,
                method="make_flash",
                elapsed_seconds=elapsed,
            )
        else:
            return FlashResult(
                success=False,
                method="make_flash",
                elapsed_seconds=elapsed,
                error_message=result.stderr.strip() or result.stdout.strip(),
            )

    except subprocess.TimeoutExpired:
        return FlashResult(
            success=False,
            method="make_flash",
            elapsed_seconds=timeout,
            error_message=f"Flash timeout ({timeout}s) - device may need manual recovery",
        )


def _resolve_usb_sysfs_path(serial_path: str) -> str:
    """Resolve /dev/serial/by-id/ symlink to sysfs USB authorized file path."""
    real_dev = os.path.realpath(serial_path)
    tty_name = os.path.basename(real_dev)
    sysfs_device = f"/sys/class/tty/{tty_name}/device"
    if not os.path.exists(sysfs_device):
        raise DiscoveryError(f"sysfs path not found: {sysfs_device}")
    iface_path = os.path.realpath(sysfs_device)
    usb_dev_path = os.path.dirname(iface_path)
    authorized = os.path.join(usb_dev_path, "authorized")
    if not os.path.exists(authorized):
        raise DiscoveryError(f"USB authorized file not found: {authorized}")
    return authorized


def _usb_sysfs_reset(authorized_path: str) -> None:
    """Toggle USB device authorized flag to force re-enumeration."""
    for value in ('0', '1'):
        result = subprocess.run(
            ['sudo', 'tee', authorized_path],
            input=value,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            raise DiscoveryError(
                f"Failed to write '{value}' to {authorized_path}: "
                f"{result.stderr.strip()}"
            )
        if value == '0':
            time.sleep(USB_RESET_SLEEP)


def _poll_for_serial_device(
    pattern: str,
    timeout: float = POLL_TIMEOUT,
) -> Optional[str]:
    """Poll /dev/serial/by-id/ for device matching glob pattern."""
    serial_dir = '/dev/serial/by-id'
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            for name in os.listdir(serial_dir):
                if fnmatch.fnmatch(name, pattern):
                    return os.path.join(serial_dir, name)
        except FileNotFoundError:
            pass  # Directory may vanish briefly during USB reset
        time.sleep(POLL_INTERVAL)
    return None


def flash_device(
    device_path: str,
    firmware_path: str,
    katapult_dir: str,
    klipper_dir: str,
    timeout: int = TIMEOUT_FLASH,
    preferred_method: str = "katapult",
    allow_fallback: bool = True,
    log: Optional[Callable[[str], None]] = None,
) -> FlashResult:
    """Flash firmware to device using Katapult or make flash.

    Tries Katapult flashtool.py first. If that fails, falls back to
    make flash automatically.

    Args:
        device_path: Path to the USB serial device.
        firmware_path: Path to the firmware binary (klipper.bin).
        katapult_dir: Path to the Katapult directory.
        klipper_dir: Path to the Klipper directory.
        timeout: Seconds per flash attempt (applies to each method).
        preferred_method: "katapult" or "make_flash" (default: "katapult").
        allow_fallback: If True, attempt the other method on failure.
        log: Optional callback for progress messages.

    Returns:
        FlashResult with success status, method used, and timing.
    """
    start = time.monotonic()

    method = (preferred_method or "katapult").strip().lower()
    if method not in ("katapult", "make_flash"):
        return FlashResult(
            success=False,
            method=method,
            elapsed_seconds=0.0,
            error_message=f"Unknown flash method: {method}",
        )

    methods = [method]
    if allow_fallback:
        methods.append("make_flash" if method == "katapult" else "katapult")

    last_result: Optional[FlashResult] = None
    for current in methods:
        if current == "katapult":
            result = _try_katapult_flash(device_path, firmware_path, katapult_dir, timeout)
        else:
            result = _try_make_flash(device_path, klipper_dir, timeout)

        last_result = result
        if result.success:
            return result

        # If no fallback, return immediately
        if not allow_fallback or current == methods[-1]:
            break

        if log is not None:
            log(f"{current} failed: {result.error_message}")
            log("Trying fallback method...")

    # If all methods failed, return last result with total elapsed time
    if last_result is None:
        return FlashResult(
            success=False,
            method=method,
            elapsed_seconds=time.monotonic() - start,
            error_message="No flash methods attempted",
        )

    last_result.elapsed_seconds = time.monotonic() - start
    return last_result
