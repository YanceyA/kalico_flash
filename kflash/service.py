"""Klipper service lifecycle management with guaranteed restart."""

from __future__ import annotations

import subprocess
from collections.abc import Generator
from contextlib import contextmanager

from .errors import ERROR_TEMPLATES, ServiceError, format_error

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
            raise ServiceError(msg) from None
    except subprocess.TimeoutExpired as exc:
        template = ERROR_TEMPLATES["service_stop_failed"]
        msg = format_error(
            template["error_type"],
            f"Timeout ({timeout}s) stopping Klipper service",
            recovery=template["recovery_template"],
        )
        raise ServiceError(msg) from exc


def _start_klipper(timeout: int = TIMEOUT_SERVICE, out=None) -> None:
    """Start the Klipper service.

    Does not raise on failure - used in finally block.
    Prints warning if start fails.

    Args:
        timeout: Seconds to wait for start.
        out: Optional output interface for formatted errors.
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
            if out is not None:
                out.error_with_recovery(
                    template["error_type"],
                    template["message_template"],
                    context={"stderr": result.stderr.strip()},
                    recovery=template["recovery_template"],
                )
            else:
                print(
                    format_error(
                        template["error_type"],
                        template["message_template"],
                        context={"stderr": result.stderr.strip()},
                        recovery=template["recovery_template"],
                    )
                )
    except subprocess.TimeoutExpired:
        template = ERROR_TEMPLATES["service_start_failed"]
        message = f"Timeout ({timeout}s) starting Klipper service"
        if out is not None:
            out.error_with_recovery(
                template["error_type"],
                message,
                recovery=template["recovery_template"],
            )
        else:
            print(
                format_error(
                    template["error_type"],
                    message,
                    recovery=template["recovery_template"],
                )
            )
    except Exception as e:
        template = ERROR_TEMPLATES["service_start_failed"]
        message = f"Error starting Klipper: {e}"
        if out is not None:
            out.error_with_recovery(
                template["error_type"],
                message,
                recovery=template["recovery_template"],
            )
        else:
            print(
                format_error(
                    template["error_type"],
                    message,
                    recovery=template["recovery_template"],
                )
            )


@contextmanager
def klipper_service_stopped(
    timeout: int = TIMEOUT_SERVICE,
    out=None,
) -> Generator[None, None, None]:
    """Context manager that stops Klipper and guarantees restart.

    Stops the Klipper service on entry. Restarts it on exit,
    even if an exception occurs or Ctrl+C is pressed.

    Args:
        timeout: Seconds for systemctl operations.
        out: Optional output interface for formatted errors.

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
        _start_klipper(timeout, out=out)
