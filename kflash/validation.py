"""Pure validation functions for TUI settings input.

Validates paths (existence, expected files) and numeric values (range checks)
before they are saved to the global configuration.
"""

from __future__ import annotations

import os
import re


def validate_numeric_setting(
    raw: str, min_val: float, max_val: float
) -> tuple[bool, float | None, str]:
    """Validate a numeric setting value.

    Returns:
        (is_valid, parsed_value, error_message)
    """
    try:
        val = float(raw)
    except ValueError:
        return False, None, "Not a number"

    if val < min_val or val > max_val:
        return False, None, f"Must be between {min_val} and {max_val}"

    return True, val, ""


def validate_path_setting(raw: str, setting_key: str) -> tuple[bool, str]:
    """Validate a path setting value.

    Expands ~ before checking. Returns (is_valid, error_message).
    """
    expanded = os.path.expanduser(raw)

    if not os.path.isdir(expanded):
        return False, f"Directory does not exist: {expanded}"

    if setting_key == "klipper_dir":
        makefile = os.path.join(expanded, "Makefile")
        if not os.path.isfile(makefile):
            return False, f"Missing expected file: {makefile}"

    elif setting_key == "katapult_dir":
        flashtool = os.path.join(expanded, "scripts", "flashtool.py")
        if not os.path.isfile(flashtool):
            return False, f"Missing expected file: {flashtool}"

    return True, ""


def validate_device_key(
    key: str, registry, current_key: str | None = None
) -> tuple[bool, str]:
    """Validate a device key for registration or rename.

    Args:
        key: Proposed device key (whitespace is stripped).
        registry: Registry instance for uniqueness check.
        current_key: If renaming, the current key (self-rename is allowed).

    Returns:
        (is_valid, error_message) — empty string on success.
    """
    key = key.strip()

    if not key:
        return False, "Device key cannot be empty"

    if not re.match(r"^[a-z0-9][a-z0-9_-]*$", key):
        return False, "Key must start with a-z/0-9 and contain only a-z, 0-9, _ or -"

    if current_key is not None and key == current_key:
        return True, ""

    if registry.get(key) is not None:
        return False, f"Device '{key}' already registered"

    return True, ""
