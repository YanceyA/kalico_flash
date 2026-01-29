"""Dataclass contracts for cross-module data exchange."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GlobalConfig:
    """Global settings shared across all devices."""

    klipper_dir: str = "~/klipper"
    katapult_dir: str = "~/katapult"
    default_flash_method: str = "katapult"
    allow_flash_fallback: bool = True
    skip_menuconfig: bool = False
    stagger_delay: float = 2.0
    return_delay: float = 5.0
    config_cache_dir: str = "~/.config/kalico-flash/configs"


@dataclass
class DeviceEntry:
    """A registered device in the registry."""

    key: str  # "octopus-pro" (user-chosen, used as --device flag)
    name: str  # "Octopus Pro v1.1" (display name)
    mcu: str  # "stm32h723" (extracted from serial path)
    serial_pattern: str  # "usb-Klipper_stm32h723xx_29001A*"
    flash_method: Optional[str] = None  # None = use global default
    flashable: bool = True  # Non-flashable devices excluded from flash selection


@dataclass
class BlockedDevice:
    """A device pattern that should be blocked from add/flash flows."""

    pattern: str
    reason: Optional[str] = None


@dataclass
class DiscoveredDevice:
    """A USB serial device found during scanning."""

    path: str  # "/dev/serial/by-id/usb-Klipper_stm32h723xx_..."
    filename: str  # "usb-Klipper_stm32h723xx_29001A001151313531383332-if00"


@dataclass
class RegistryData:
    """Complete registry file contents."""

    global_config: GlobalConfig = field(default_factory=GlobalConfig)
    devices: dict = field(default_factory=dict)  # key -> DeviceEntry
    blocked_devices: list[BlockedDevice] = field(default_factory=list)


@dataclass
class BuildResult:
    """Result of a firmware build."""

    success: bool
    firmware_path: Optional[str] = None  # Path to klipper.bin if success
    firmware_size: int = 0  # Size in bytes if success
    elapsed_seconds: float = 0.0  # Build duration
    error_message: Optional[str] = None  # Error details if failed


@dataclass
class FlashResult:
    """Result of a flash operation."""

    success: bool
    method: str  # "katapult" or "make_flash"
    elapsed_seconds: float = 0.0
    error_message: Optional[str] = None


@dataclass
class BatchDeviceResult:
    """Per-device result tracking for Flash All batch operations."""

    device_key: str
    device_name: str
    config_ok: bool = False
    build_ok: bool = False
    flash_ok: bool = False
    verify_ok: bool = False
    error_message: Optional[str] = None
    skipped: bool = False  # User chose to skip (version match)


@dataclass
class PrintStatus:
    """Current print job status from Moonraker."""

    state: str  # standby, printing, paused, complete, error, cancelled
    filename: Optional[str]  # None if no file loaded
    progress: float  # 0.0 to 1.0
