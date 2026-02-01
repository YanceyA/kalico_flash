"""USB serial scanning and pattern matching."""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path
from typing import Optional

from .models import DiscoveredDevice

SERIAL_BY_ID = "/dev/serial/by-id"

# Supported device prefixes for Klipper/Katapult USB IDs (case-insensitive)
SUPPORTED_PREFIXES = ("usb-klipper_", "usb-katapult_")


def scan_serial_devices() -> list:
    """Scan /dev/serial/by-id/ and return all USB serial devices."""
    serial_dir = Path(SERIAL_BY_ID)
    if not serial_dir.is_dir():
        return []
    devices = []
    for entry in sorted(serial_dir.iterdir()):
        devices.append(
            DiscoveredDevice(
                path=str(entry),
                filename=entry.name,
            )
        )
    return devices


def is_supported_device(filename: str) -> bool:
    """Return True if filename looks like a Klipper/Katapult USB device."""
    lower = filename.lower()
    return any(lower.startswith(prefix) for prefix in SUPPORTED_PREFIXES)


def match_device(pattern: str, devices: list) -> Optional[DiscoveredDevice]:
    """Find first device whose filename matches a glob pattern."""
    matches = match_devices(pattern, devices)
    return matches[0] if matches else None


def _prefix_variants(pattern: str) -> list[str]:
    """Return pattern variants with both Klipper_ and katapult_ prefixes.

    A pattern like ``usb-katapult_rp2040_30*`` returns both itself and
    ``usb-Klipper_rp2040_30*`` so matching works regardless of which
    bootloader mode the device booted into.
    """
    lower = pattern.lower()
    if lower.startswith("usb-klipper_"):
        alt = "usb-katapult_" + pattern[len("usb-Klipper_"):]
        return [pattern, alt]
    if lower.startswith("usb-katapult_"):
        alt = "usb-Klipper_" + pattern[len("usb-katapult_"):]
        return [pattern, alt]
    return [pattern]


def match_devices(pattern: str, devices: list) -> list[DiscoveredDevice]:
    """Find all devices whose filename matches a glob pattern.

    Matching is prefix-agnostic: a ``usb-katapult_*`` pattern will also
    match ``usb-Klipper_*`` filenames and vice-versa so that devices are
    found regardless of which bootloader mode they booted into.
    """
    variants = _prefix_variants(pattern)
    return [
        device for device in devices
        if any(fnmatch.fnmatch(device.filename, v) for v in variants)
    ]


def find_registered_devices(devices: list, registry_devices: dict) -> tuple:
    """Cross-reference discovered devices against registry.

    Returns ALL matching devices including non-flashable ones. Filtering for
    flashable devices should be done by the caller (flash module) at selection time.

    Args:
        devices: List of DiscoveredDevice from scan_serial_devices()
        registry_devices: Dict of key -> DeviceEntry from registry

    Returns:
        (matched, unmatched) where:
          matched = list of (DeviceEntry, DiscoveredDevice) tuples (includes non-flashable)
          unmatched = list of DiscoveredDevice not matching any pattern
    """
    matched = []
    unmatched_devices = list(devices)  # copy

    for entry in registry_devices.values():
        variants = _prefix_variants(entry.serial_pattern)
        for device in devices:
            if any(fnmatch.fnmatch(device.filename, v) for v in variants):
                matched.append((entry, device))
                if device in unmatched_devices:
                    unmatched_devices.remove(device)
                break

    return matched, unmatched_devices


def extract_mcu_from_serial(filename: str) -> Optional[str]:
    """Extract MCU type from a /dev/serial/by-id/ filename.

    Examples:
        usb-Klipper_stm32h723xx_290... -> stm32h723
        usb-Klipper_rp2040_303...      -> rp2040
        usb-katapult_stm32h723xx_290.. -> stm32h723
        usb-Klipper_stm32f411xe_600... -> stm32f411
        usb-Beacon_Beacon_RevH_FC2...  -> None (not a Klipper/Katapult device)

    Returns the MCU type without variant suffix (xx, xe, etc.) or None if
    pattern does not match.
    """
    m = re.match(
        r"usb-(?:Klipper|katapult)_([a-z0-9]+?)(?:x[a-z0-9]*)?_",
        filename,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).lower()
    return None


def generate_serial_pattern(filename: str) -> str:
    """Generate a serial glob pattern from a full device filename.

    Takes the full filename up to (but not including) the interface suffix,
    then appends a wildcard.

    Example:
        usb-Klipper_stm32h723xx_29001A001151313531383332-if00
        -> usb-Klipper_stm32h723xx_29001A001151313531383332*
    """
    # Strip -ifNN suffix, add wildcard
    base = re.sub(r"-if\d+$", "", filename)
    return base + "*"
