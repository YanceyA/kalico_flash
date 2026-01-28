"""Klipper service lifecycle management with guaranteed restart."""
from __future__ import annotations

import subprocess
from contextlib import contextmanager
from typing import Generator

from errors import ServiceError, format_error, ERROR_TEMPLATES

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
            template = ERROR_TEMPLATES["service_stop_failed"]
            msg = format_error(
                template["error_type"],
                template["message_template"],
                context={"stderr": result.stderr.strip()},
                recovery=template["recovery_template"],
            )
            raise ServiceError(msg)
    except subprocess.TimeoutExpired:
        template = ERROR_TEMPLATES["service_stop_failed"]
        msg = format_error(
            template["error_type"],
            f"Timeout ({timeout}s) stopping Klipper service",
            recovery=template["recovery_template"],
        )
        raise ServiceError(msg)


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
            template = ERROR_TEMPLATES["service_start_failed"]
            print(format_error(
                template["error_type"],
                template["message_template"],
                context={"stderr": result.stderr.strip()},
                recovery=template["recovery_template"],
            ))
    except subprocess.TimeoutExpired:
        template = ERROR_TEMPLATES["service_start_failed"]
        print(format_error(
            template["error_type"],
            f"Timeout ({timeout}s) starting Klipper service",
            recovery=template["recovery_template"],
        ))
    except Exception as e:
        template = ERROR_TEMPLATES["service_start_failed"]
        print(format_error(
            template["error_type"],
            f"Error starting Klipper: {e}",
            recovery=template["recovery_template"],
        ))


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
