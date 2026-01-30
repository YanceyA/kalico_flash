"""Config file management: caching, MCU parsing, atomic operations."""

from __future__ import annotations

import os
import re
import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional

from .errors import ConfigError, format_error


def get_config_dir(device_key: str) -> Path:
    """Get XDG config directory for a device.

    Returns path to ~/.config/kalico-flash/configs/{device-key}/
    Respects XDG_CONFIG_HOME if set and absolute.
    """
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config and os.path.isabs(xdg_config):
        base = Path(xdg_config)
    else:
        base = Path.home() / ".config"
    return base / "kalico-flash" / "configs" / device_key


def parse_mcu_from_config(config_path: str) -> Optional[str]:
    """Extract MCU type from .config file.

    Returns e.g., 'stm32h723xx', 'rp2040', or None if not found.
    """
    path = Path(config_path)
    if not path.exists():
        return None

    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None

    # Match: CONFIG_MCU="stm32h723xx"
    match = re.search(r'^CONFIG_MCU="([^"]+)"', content, re.MULTILINE)
    return match.group(1) if match else None


def _atomic_copy(src: str, dst: str) -> None:
    """Copy file atomically: copy to temp, fsync, rename.

    Creates destination directory if needed.
    Cleans up temp file on failure.
    """
    dst_dir = os.path.dirname(os.path.abspath(dst))
    os.makedirs(dst_dir, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="wb", dir=dst_dir, delete=False, suffix=".tmp"
    ) as tf:
        tmp_path = tf.name
        try:
            with open(src, "rb") as sf:
                shutil.copyfileobj(sf, tf)
            tf.flush()
            os.fsync(tf.fileno())
        except BaseException:
            os.unlink(tmp_path)
            raise
    os.replace(tmp_path, dst)


class ConfigManager:
    """Manage per-device Klipper .config caching.

    Handles:
    - Loading cached config to klipper directory
    - Saving klipper config to cache after menuconfig
    - Validating MCU type matches device registry
    """

    def __init__(self, device_key: str, klipper_dir: str):
        """Initialize config manager.

        Args:
            device_key: Device identifier (used for cache path)
            klipper_dir: Path to klipper source directory
        """
        self.device_key = device_key
        self.klipper_dir = Path(klipper_dir).expanduser()
        self.cache_path = get_config_dir(device_key) / ".config"
        self.klipper_config_path = self.klipper_dir / ".config"

    def load_cached_config(self) -> bool:
        """Load cached config to klipper directory.

        Returns True if cached config was copied.
        Returns False if no cached config exists.
        Creates klipper directory if needed.
        """
        if not self.cache_path.exists():
            return False

        # Ensure klipper directory exists
        self.klipper_dir.mkdir(parents=True, exist_ok=True)

        _atomic_copy(str(self.cache_path), str(self.klipper_config_path))
        return True

    def clear_klipper_config(self) -> bool:
        """Remove .config from klipper directory for fresh menuconfig.

        Returns True if file was removed, False if it didn't exist.
        """
        if self.klipper_config_path.exists():
            self.klipper_config_path.unlink()
            return True
        return False

    def save_cached_config(self) -> None:
        """Save klipper config to cache.

        Raises ConfigError if klipper .config doesn't exist.
        """
        if not self.klipper_config_path.exists():
            msg = format_error(
                "Config error",
                "No .config file found after menuconfig",
                context={"path": str(self.klipper_dir)},
                recovery=(
                    "1. Run make menuconfig first\n"
                    "2. Save config before exiting menuconfig\n"
                    "3. Check path: ls {klipper_dir}/.config"
                ).format(klipper_dir=self.klipper_dir),
            )
            raise ConfigError(msg)

        _atomic_copy(str(self.klipper_config_path), str(self.cache_path))

    def validate_mcu(self, expected_mcu: str) -> tuple[bool, Optional[str]]:
        """Validate MCU type in klipper .config matches expected.

        Uses prefix matching: 'stm32h723' matches 'stm32h723xx'.

        Args:
            expected_mcu: Expected MCU type from device registry

        Returns:
            (is_match, actual_mcu) tuple

        Raises:
            ConfigError: If .config doesn't exist or has no CONFIG_MCU
        """
        if not self.klipper_config_path.exists():
            msg = format_error(
                "Config error",
                "No .config file for MCU validation",
                context={"path": str(self.klipper_dir)},
                recovery=(
                    "1. Run make menuconfig to create .config\n"
                    "2. Or use --skip-menuconfig with existing cached config\n"
                    "3. Check: ls {klipper_dir}/.config"
                ).format(klipper_dir=self.klipper_dir),
            )
            raise ConfigError(msg)

        actual_mcu = parse_mcu_from_config(str(self.klipper_config_path))
        if actual_mcu is None:
            msg = format_error(
                "Config error",
                "No CONFIG_MCU found in .config file",
                context={"path": str(self.klipper_config_path)},
                recovery=(
                    "1. Run make menuconfig and select MCU type\n"
                    "2. Save config before exiting\n"
                    "3. Verify: grep CONFIG_MCU {config_path}"
                ).format(config_path=self.klipper_config_path),
            )
            raise ConfigError(msg)

        # Prefix match: device registry may have 'stm32h723', config has 'stm32h723xx'
        is_match = actual_mcu.startswith(expected_mcu) or expected_mcu.startswith(
            actual_mcu
        )

        return is_match, actual_mcu

    def get_mtime(self) -> Optional[float]:
        """Get modification time of klipper .config file.

        Returns mtime in seconds since epoch, or None if file doesn't exist.
        Used to detect if menuconfig saved changes.
        """
        if not self.klipper_config_path.exists():
            return None
        return self.klipper_config_path.stat().st_mtime

    def has_cached_config(self) -> bool:
        """Check if cached config exists for this device."""
        return self.cache_path.exists()

    def get_cache_mtime(self) -> Optional[float]:
        """Get modification time of cached config.

        Returns mtime in seconds since epoch, or None if no cache exists.
        """
        if not self.cache_path.exists():
            return None
        return self.cache_path.stat().st_mtime

    def get_cache_age_display(self) -> Optional[str]:
        """Get human-readable age of cached config.

        Returns e.g. "2 hours ago", "3 days ago", "14 days ago (recommend review)".
        Returns None if no cached config exists.
        """
        mtime = self.get_cache_mtime()
        if mtime is None:
            return None

        age_seconds = time.time() - mtime
        if age_seconds < 0:
            age_seconds = 0

        minutes = int(age_seconds / 60)
        hours = int(age_seconds / 3600)
        days = int(age_seconds / 86400)

        if hours < 1:
            label = f"{max(minutes, 1)} minutes ago"
        elif days < 1:
            label = f"{hours} hours ago" if hours > 1 else "1 hour ago"
        else:
            label = f"{days} days ago" if days > 1 else "1 day ago"
            if days >= 90:
                label += " (recommend review)"

        return label
