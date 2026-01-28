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
import re
import subprocess
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from .models import PrintStatus

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
        mcu_objects = [
            obj for obj in all_objects if obj == "mcu" or obj.startswith("mcu ")
        ]

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
            version = result.stdout.strip()
            if version and "-g" in version:
                return version
            # Fallback: synthesize vX-Y-gHASH when git describe returns tag-only
            tag = version if version.startswith("v") else None
            if not tag:
                tag_result = subprocess.run(
                    ["git", "describe", "--tags", "--abbrev=0"],
                    cwd=str(klipper_path),
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT,
                )
                if tag_result.returncode == 0:
                    tag = tag_result.stdout.strip()
            count_result = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                cwd=str(klipper_path),
                capture_output=True,
                text=True,
                timeout=TIMEOUT,
            )
            hash_result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=str(klipper_path),
                capture_output=True,
                text=True,
                timeout=TIMEOUT,
            )
            if count_result.returncode == 0 and hash_result.returncode == 0:
                count = count_result.stdout.strip()
                short_hash = hash_result.stdout.strip()
                if tag:
                    return f"{tag}-{count}-g{short_hash}"
                return f"{count}-g{short_hash}"
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def _parse_git_describe(version: str) -> tuple[Optional[str], Optional[int]]:
    """Parse git-describe style version strings.

    Returns (tag, commit_count). commit_count is None if not present.
    """
    v = version.strip()
    if not v:
        return None, None

    # Typical forms:
    #   v0.12.0-45-g7ce409d
    #   v0.12.0-0-g7ce409d
    #   v0.12.0-45-g7ce409d-dirty
    #   v2026.01.00
    match = re.match(
        r"^(v[0-9A-Za-z.\-_]+?)(?:-([0-9]+)-g[0-9a-fA-F]+)?(?:-dirty)?$",
        v,
    )
    if not match:
        return None, None
    tag = match.group(1)
    count = int(match.group(2)) if match.group(2) is not None else None
    return tag, count


def get_mcu_version_for_device(mcu_type: str) -> Optional[str]:
    """Get MCU firmware version for a specific device by its mcu_type.

    Attempts to match the device's mcu_type (e.g., "stm32h723", "rp2040", "nhk")
    to a Moonraker MCU name and return its version.

    Matching logic (in order):
    1. Exact match on MCU name (e.g., device mcu "nhk" matches Moonraker "nhk")
    2. If device mcu contains the Moonraker mcu name or vice versa
    3. Fall back to "main" for primary MCU if no match found

    Args:
        mcu_type: Device MCU type string (e.g., "stm32h723", "rp2040", "nhk")

    Returns:
        Version string like "v0.12.0-45-g7ce409d" or None if unavailable.
    """
    mcu_versions = get_mcu_versions()
    if not mcu_versions:
        return None

    mcu_lower = mcu_type.lower()

    # 1. Exact match
    for mcu_name, version in mcu_versions.items():
        if mcu_name.lower() == mcu_lower:
            return version

    # 2. Substring match (device mcu contains moonraker name or vice versa)
    for mcu_name, version in mcu_versions.items():
        name_lower = mcu_name.lower()
        if mcu_lower in name_lower or name_lower in mcu_lower:
            return version

    # 3. Fall back to "main" for primary MCU
    if "main" in mcu_versions:
        return mcu_versions["main"]

    return None


def is_mcu_outdated(host_version: str, mcu_version: str) -> bool:
    """Check if MCU firmware appears behind host Klipper.

    Compares tag + commit count when available. Falls back to
    tag-only comparison or raw string comparison if parsing fails.
    This is informational only - never blocks flash.
    """
    host = host_version.strip()
    mcu = mcu_version.strip()
    if not host or not mcu:
        return False

    host_tag, host_count = _parse_git_describe(host)
    mcu_tag, mcu_count = _parse_git_describe(mcu)

    if host_tag and mcu_tag:
        if host_tag != mcu_tag:
            return True
        if host_count is not None and mcu_count is not None:
            return host_count != mcu_count
        # If commit counts are missing, don't warn on equal tags
        return False

    return host != mcu
