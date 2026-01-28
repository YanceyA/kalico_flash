"""Moonraker API client for print status and version detection.

Provides graceful degradation when Moonraker is unavailable - all public
functions return None on failure instead of raising exceptions. This allows
the flash workflow to continue with a warning rather than blocking.

Endpoints used:
- /printer/objects/query?print_stats&virtual_sdcard - Print status and progress
- /printer/objects/list - Discover all MCU objects
- /printer/objects/query?mcu&mcu%20nhk - MCU firmware versions
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from models import PrintStatus

# Connection settings (hardcoded per CONTEXT.md: no custom URL support)
MOONRAKER_URL = "http://localhost:7125"
TIMEOUT = 5  # seconds


def get_print_status() -> Optional[PrintStatus]:
    """Query Moonraker for current print status.

    Returns:
        PrintStatus if successful, None if Moonraker unreachable or error.
    """
    try:
        url = f"{MOONRAKER_URL}/printer/objects/query?print_stats&virtual_sdcard"
        with urlopen(url, timeout=TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))

        status = data["result"]["status"]
        print_stats = status.get("print_stats", {})
        virtual_sdcard = status.get("virtual_sdcard", {})

        return PrintStatus(
            state=print_stats.get("state", "standby"),
            filename=print_stats.get("filename") or None,
            progress=virtual_sdcard.get("progress", 0.0),
        )
    except (URLError, HTTPError, json.JSONDecodeError, KeyError, TimeoutError, OSError):
        return None


def get_mcu_versions() -> Optional[dict[str, str]]:
    """Query Moonraker for all MCU firmware versions.

    Returns:
        Dict mapping MCU name to version string, None if unreachable.
        Names are normalized: "mcu" -> "main", "mcu nhk" -> "nhk".
        Example: {"main": "v0.12.0-45-g7ce409d", "nhk": "v0.12.0-45-g7ce409d"}
    """
    try:
        # First get list of all printer objects to discover MCUs
        list_url = f"{MOONRAKER_URL}/printer/objects/list"
        with urlopen(list_url, timeout=TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))

        # Find all MCU objects (mcu, mcu linux, mcu nhk, etc.)
        all_objects = data["result"]["objects"]
        mcu_objects = [obj for obj in all_objects
                       if obj == "mcu" or obj.startswith("mcu ")]

        if not mcu_objects:
            return None

        # Query MCU objects for mcu_version field
        # URL-encode spaces as %20 for query params
        query_params = "&".join(obj.replace(" ", "%20") for obj in mcu_objects)
        query_url = f"{MOONRAKER_URL}/printer/objects/query?{query_params}"

        with urlopen(query_url, timeout=TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))

        versions: dict[str, str] = {}
        for mcu_name, mcu_data in data["result"]["status"].items():
            if "mcu_version" in mcu_data:
                # Normalize names: "mcu" -> "main", "mcu nhk" -> "nhk"
                if mcu_name == "mcu":
                    name = "main"
                else:
                    # Strip "mcu " prefix (4 characters)
                    name = mcu_name[4:]
                versions[name] = mcu_data["mcu_version"]

        return versions if versions else None

    except (URLError, HTTPError, json.JSONDecodeError, KeyError, TimeoutError, OSError):
        return None


def get_host_klipper_version(klipper_dir: str) -> Optional[str]:
    """Get host Klipper version via git describe.

    Uses --long flag to always include commit count and hash, matching
    the format used by MCU firmware (e.g., "v0.12.0-0-g7ce409d" when
    exactly at tag, "v0.12.0-45-g7ce409d" when 45 commits ahead).

    Args:
        klipper_dir: Path to Klipper source directory (supports ~ expansion).

    Returns:
        Version string like "v0.12.0-45-g7ce409d" or None if failed.
    """
    klipper_path = Path(klipper_dir).expanduser()
    try:
        result = subprocess.run(
            ["git", "describe", "--always", "--tags", "--long", "--dirty"],
            cwd=str(klipper_path),
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def is_mcu_outdated(host_version: str, mcu_version: str) -> bool:
    """Check if MCU firmware appears behind host Klipper.

    Performs a simple string comparison after stripping whitespace.
    This is informational only - never blocks flash.

    Args:
        host_version: Version string from git describe (e.g., "v0.12.0-45-g7ce409d")
        mcu_version: Version string from MCU firmware

    Returns:
        True if MCU version differs from host version.
    """
    return host_version.strip() != mcu_version.strip()
