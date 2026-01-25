"""Centralized exception hierarchy for kalico-flash."""
from __future__ import annotations


class KlipperFlashError(Exception):
    """Base for all kalico-flash errors."""
    pass


class RegistryError(KlipperFlashError):
    """Registry file errors: corrupt JSON, missing fields, duplicate keys."""
    pass


class DeviceNotFoundError(KlipperFlashError):
    """Named device not in registry or not physically connected."""

    def __init__(self, identifier: str):
        super().__init__(f"Device not found: {identifier}")
        self.identifier = identifier


class DiscoveryError(KlipperFlashError):
    """USB discovery failures."""
    pass


class ConfigError(KlipperFlashError):
    """Config file errors: missing, corrupt, MCU mismatch."""
    pass


class BuildError(KlipperFlashError):
    """Build failures: make menuconfig, make clean, make."""
    pass


class ServiceError(KlipperFlashError):
    """Klipper service lifecycle errors: stop/start failures."""
    pass


class FlashError(KlipperFlashError):
    """Flash operation failures: Katapult, make flash, device not found."""
    pass
