"""Device registry backed by devices.json."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Optional

from .errors import RegistryError
from .models import BlockedDevice, DeviceEntry, GlobalConfig, RegistryData


class Registry:
    """Device registry with JSON CRUD and atomic writes."""

    def __init__(self, registry_path: str):
        self.path = registry_path

    def load(self) -> RegistryData:
        """Load registry from disk. Returns default if file missing."""
        p = Path(self.path)
        if not p.exists():
            return RegistryData()
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise RegistryError(f"Corrupt registry file: {e}")

        global_raw = raw.get("global", {})
        global_config = GlobalConfig(
            klipper_dir=global_raw.get("klipper_dir", "~/klipper"),
            katapult_dir=global_raw.get("katapult_dir", "~/katapult"),
            default_flash_method=global_raw.get("default_flash_method", "katapult"),
            allow_flash_fallback=global_raw.get("allow_flash_fallback", True),
            skip_menuconfig=global_raw.get("skip_menuconfig", False),
            stagger_delay=global_raw.get("stagger_delay", 2.0),
            return_delay=global_raw.get("return_delay", 5.0),
            config_cache_dir=global_raw.get("config_cache_dir", "~/.config/kalico-flash/configs"),
        )
        devices: dict[str, DeviceEntry] = {}
        for key, data in raw.get("devices", {}).items():
            devices[key] = DeviceEntry(
                key=key,
                name=data["name"],
                mcu=data["mcu"],
                serial_pattern=data["serial_pattern"],
                flash_method=data.get("flash_method"),
                flashable=data.get("flashable", True),  # Default to True if missing
            )

        blocked_devices: list[BlockedDevice] = []
        for item in raw.get("blocked_devices", []):
            if isinstance(item, str):
                blocked_devices.append(BlockedDevice(pattern=item))
                continue
            if isinstance(item, dict):
                pattern = item.get("pattern") or item.get("serial_pattern")
                if pattern:
                    blocked_devices.append(
                        BlockedDevice(
                            pattern=pattern,
                            reason=item.get("reason"),
                        )
                    )

        return RegistryData(
            global_config=global_config,
            devices=devices,
            blocked_devices=blocked_devices,
        )

    def save(self, registry: RegistryData) -> None:
        """Save registry to disk atomically."""
        data = {
            "global": {
                "klipper_dir": registry.global_config.klipper_dir,
                "katapult_dir": registry.global_config.katapult_dir,
                "default_flash_method": registry.global_config.default_flash_method,
                "allow_flash_fallback": registry.global_config.allow_flash_fallback,
                "skip_menuconfig": registry.global_config.skip_menuconfig,
                "stagger_delay": registry.global_config.stagger_delay,
                "return_delay": registry.global_config.return_delay,
                "config_cache_dir": registry.global_config.config_cache_dir,
            },
            "devices": {},
            "blocked_devices": [],
        }
        for key, device in sorted(registry.devices.items()):
            data["devices"][key] = {
                "name": device.name,
                "mcu": device.mcu,
                "serial_pattern": device.serial_pattern,
                "flash_method": device.flash_method,
                "flashable": device.flashable,
            }
        for blocked in registry.blocked_devices:
            entry = {"pattern": blocked.pattern}
            if blocked.reason:
                entry["reason"] = blocked.reason
            data["blocked_devices"].append(entry)
        _atomic_write_json(self.path, data)

    def add(self, entry: DeviceEntry) -> None:
        """Add a device to the registry. Raises RegistryError if key exists."""
        registry = self.load()
        if entry.key in registry.devices:
            raise RegistryError(f"Device '{entry.key}' already registered")
        registry.devices[entry.key] = entry
        self.save(registry)

    def remove(self, key: str) -> bool:
        """Remove a device from the registry. Returns False if not found."""
        registry = self.load()
        if key not in registry.devices:
            return False
        del registry.devices[key]
        self.save(registry)
        return True

    def get(self, key: str) -> Optional[DeviceEntry]:
        """Get a device by key. Returns None if not found."""
        registry = self.load()
        return registry.devices.get(key)

    def list_all(self) -> list:
        """List all registered devices."""
        registry = self.load()
        return list(registry.devices.values())

    def load_global(self) -> GlobalConfig:
        """Load global configuration."""
        registry = self.load()
        return registry.global_config

    def save_global(self, config: GlobalConfig) -> None:
        """Update global configuration."""
        registry = self.load()
        registry.global_config = config
        self.save(registry)

    def update_device(self, key: str, **updates) -> bool:
        """Update fields on a registered device. Returns False if key not found.

        Uses load-modify-save pattern for atomic persistence.
        Valid fields: name, mcu, serial_pattern, flash_method, flashable.
        """
        registry = self.load()
        if key not in registry.devices:
            return False
        device = registry.devices[key]
        for field, value in updates.items():
            setattr(device, field, value)
        self.save(registry)
        return True

    def set_flashable(self, key: str, flashable: bool) -> bool:
        """Set flashable status for a device. Returns False if device not found."""
        registry = self.load()
        if key not in registry.devices:
            return False
        registry.devices[key].flashable = flashable
        self.save(registry)
        return True


def _atomic_write_json(path: str, data: dict) -> None:
    """Write JSON atomically: write to temp file, fsync, rename."""
    dir_name = os.path.dirname(os.path.abspath(path))
    os.makedirs(dir_name, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", dir=dir_name, delete=False, suffix=".tmp", encoding="utf-8"
    ) as tf:
        tmp_path = tf.name
        try:
            json.dump(data, tf, indent=2, sort_keys=True)
            tf.write("\n")
            tf.flush()
            os.fsync(tf.fileno())
        except BaseException:
            os.unlink(tmp_path)
            raise
    os.replace(tmp_path, path)
