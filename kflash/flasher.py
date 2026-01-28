"""Dual-method flash operations: Katapult-first with make-flash fallback."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Optional

from errors import DiscoveryError, format_error
from models import FlashResult

# Default timeout for flash operations (from CONTEXT.md)
TIMEOUT_FLASH = 60


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


def flash_device(
    device_path: str,
    firmware_path: str,
    katapult_dir: str,
    klipper_dir: str,
    timeout: int = TIMEOUT_FLASH,
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

    Returns:
        FlashResult with success status, method used, and timing.
    """
    start = time.monotonic()

    # Try Katapult first
    result = _try_katapult_flash(device_path, firmware_path, katapult_dir, timeout)

    if result.success:
        return result

    # Katapult failed, try make flash
    print(f"[Flash] Katapult failed: {result.error_message}")
    print("[Flash] Trying make flash as fallback...")

    fallback_result = _try_make_flash(device_path, klipper_dir, timeout)

    # If fallback also failed, include total elapsed time
    if not fallback_result.success:
        fallback_result.elapsed_seconds = time.monotonic() - start

    return fallback_result
