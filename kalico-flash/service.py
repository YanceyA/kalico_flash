"""Klipper service lifecycle management with guaranteed restart."""
from __future__ import annotations

import subprocess
from contextlib import contextmanager
from typing import Generator

from errors import ServiceError

# Default timeout for systemctl operations
TIMEOUT_SERVICE = 30


def verify_passwordless_sudo() -> bool:
    """Check if sudo can run without a password.

    Returns:
        True if passwordless sudo works, False otherwise.
    """
    try:
        result = subprocess.run(
            ["sudo", "-n", "true"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False


def _stop_klipper(timeout: int = TIMEOUT_SERVICE) -> None:
    """Stop the Klipper service.

    Args:
        timeout: Seconds to wait for stop.

    Raises:
        ServiceError: If stop fails.
    """
    try:
        result = subprocess.run(
            ["sudo", "systemctl", "stop", "klipper"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            raise ServiceError(f"Failed to stop Klipper: {result.stderr.strip()}")
    except subprocess.TimeoutExpired:
        raise ServiceError(f"Timeout ({timeout}s) stopping Klipper service")


def _start_klipper(timeout: int = TIMEOUT_SERVICE) -> None:
    """Start the Klipper service.

    Does not raise on failure - used in finally block.
    Prints warning if start fails.

    Args:
        timeout: Seconds to wait for start.
    """
    try:
        result = subprocess.run(
            ["sudo", "systemctl", "start", "klipper"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            print(f"[Warning] Failed to restart Klipper: {result.stderr.strip()}")
            print("[Warning] Run 'sudo systemctl start klipper' manually.")
    except subprocess.TimeoutExpired:
        print(f"[Warning] Timeout ({timeout}s) starting Klipper service")
        print("[Warning] Run 'sudo systemctl start klipper' manually.")
    except Exception as e:
        print(f"[Warning] Error starting Klipper: {e}")
        print("[Warning] Run 'sudo systemctl start klipper' manually.")


@contextmanager
def klipper_service_stopped(timeout: int = TIMEOUT_SERVICE) -> Generator[None, None, None]:
    """Context manager that stops Klipper and guarantees restart.

    Stops the Klipper service on entry. Restarts it on exit,
    even if an exception occurs or Ctrl+C is pressed.

    Args:
        timeout: Seconds for systemctl operations.

    Yields:
        None - the context is active while Klipper is stopped.

    Raises:
        ServiceError: If stopping Klipper fails.

    Example:
        with klipper_service_stopped():
            flash_firmware(device)
        # Klipper is restarted here, even if flash_firmware raised
    """
    _stop_klipper(timeout)
    try:
        yield
    finally:
        # Always restart, even on exception or KeyboardInterrupt
        # Don't raise here - would mask the original error
        _start_klipper(timeout)
