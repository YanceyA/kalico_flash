"""Config file management: caching, MCU parsing, atomic operations."""
from __future__ import annotations

import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from errors import ConfigError


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

    def save_cached_config(self) -> None:
        """Save klipper config to cache.

        Raises ConfigError if klipper .config doesn't exist.
        """
        if not self.klipper_config_path.exists():
            raise ConfigError(
                f"No .config file in klipper directory: {self.klipper_dir}"
            )

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
            raise ConfigError(
                f"No .config file in klipper directory: {self.klipper_dir}"
            )

        actual_mcu = parse_mcu_from_config(str(self.klipper_config_path))
        if actual_mcu is None:
            raise ConfigError(
                f"No CONFIG_MCU found in .config: {self.klipper_config_path}"
            )

        # Prefix match: device registry may have 'stm32h723', config has 'stm32h723xx'
        is_match = (
            actual_mcu.startswith(expected_mcu) or
            expected_mcu.startswith(actual_mcu)
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
