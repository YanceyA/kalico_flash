"""Build operations: menuconfig TUI passthrough and firmware compilation."""

from __future__ import annotations

import multiprocessing
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from .models import BuildResult

# Default timeout for build operations (5 minutes)
TIMEOUT_BUILD = 300


def run_menuconfig(klipper_dir: str, config_path: str) -> tuple[int, bool]:
    """Run make menuconfig with inherited stdio for ncurses TUI.

    Sets KCONFIG_CONFIG to the absolute path of config_path so menuconfig
    reads/writes the specified file instead of .config in klipper_dir.

    Args:
        klipper_dir: Path to klipper source directory (supports ~)
        config_path: Path to .config file to use

    Returns:
        (return_code, was_saved) tuple:
        - return_code: Exit code from menuconfig
        - was_saved: True if config file was modified (mtime changed)
    """
    klipper_path = Path(klipper_dir).expanduser()
    config_abs = Path(config_path).expanduser().absolute()

    # Record mtime before (None if file doesn't exist yet)
    mtime_before: Optional[float] = None
    if config_abs.exists():
        mtime_before = config_abs.stat().st_mtime

    # Set up environment with KCONFIG_CONFIG pointing to absolute path
    env = os.environ.copy()
    env["KCONFIG_CONFIG"] = str(config_abs)

    # Run menuconfig with inherited stdio (no PIPE) for ncurses TUI
    # User can navigate, edit, save with normal keyboard controls
    result = subprocess.run(
        ["make", "menuconfig"],
        cwd=str(klipper_path),
        env=env,
    )

    # Check if config was saved (mtime changed or file created)
    was_saved = False
    if config_abs.exists():
        mtime_after = config_abs.stat().st_mtime
        if mtime_before is None or mtime_after > mtime_before:
            was_saved = True

    return result.returncode, was_saved


def run_build(klipper_dir: str, timeout: int = TIMEOUT_BUILD, quiet: bool = False) -> BuildResult:
    """Run make clean + make -j with streaming output.

    Executes build in klipper directory with inherited stdio for real-time
    output. Uses all available CPU cores for parallel compilation.

    Args:
        klipper_dir: Path to klipper source directory (supports ~)
        timeout: Seconds before timeout (default: TIMEOUT_BUILD)

    Returns:
        BuildResult with success status, firmware path/size, elapsed time
    """
    klipper_path = Path(klipper_dir).expanduser()
    start_time = time.monotonic()
    pipe_kwargs = {"capture_output": True} if quiet else {}

    # Run make clean with inherited stdio for streaming output
    try:
        clean_result = subprocess.run(
            ["make", "clean"],
            cwd=str(klipper_path),
            timeout=timeout,
            **pipe_kwargs,
        )
    except subprocess.TimeoutExpired:
        return BuildResult(
            success=False,
            elapsed_seconds=time.monotonic() - start_time,
            error_message=f"make clean timed out after {timeout}s",
        )

    if clean_result.returncode != 0:
        elapsed = time.monotonic() - start_time
        return BuildResult(
            success=False,
            elapsed_seconds=elapsed,
            error_message=f"make clean failed with exit code {clean_result.returncode}",
        )

    # Run make -j with all available cores
    nproc = multiprocessing.cpu_count()
    try:
        build_result = subprocess.run(
            ["make", f"-j{nproc}"],
            cwd=str(klipper_path),
            timeout=timeout,
            **pipe_kwargs,
        )
    except subprocess.TimeoutExpired:
        return BuildResult(
            success=False,
            elapsed_seconds=time.monotonic() - start_time,
            error_message=f"Build timed out after {timeout}s",
        )

    elapsed = time.monotonic() - start_time

    if build_result.returncode != 0:
        return BuildResult(
            success=False,
            elapsed_seconds=elapsed,
            error_message=f"make failed with exit code {build_result.returncode}",
        )

    # Check for firmware output
    firmware_path = klipper_path / "out" / "klipper.bin"
    if not firmware_path.exists():
        return BuildResult(
            success=False,
            elapsed_seconds=elapsed,
            error_message=f"Build succeeded but firmware not found: {firmware_path}",
        )

    firmware_size = firmware_path.stat().st_size

    return BuildResult(
        success=True,
        firmware_path=str(firmware_path),
        firmware_size=firmware_size,
        elapsed_seconds=elapsed,
    )


class Builder:
    """Convenience wrapper for build operations on a klipper directory."""

    def __init__(self, klipper_dir: str):
        """Initialize builder.

        Args:
            klipper_dir: Path to klipper source directory (supports ~)
        """
        self.klipper_dir = klipper_dir

    def menuconfig(self, config_path: str) -> tuple[int, bool]:
        """Run make menuconfig for the specified config file.

        Args:
            config_path: Path to .config file to use

        Returns:
            (return_code, was_saved) tuple
        """
        return run_menuconfig(self.klipper_dir, config_path)

    def build(self) -> BuildResult:
        """Run make clean + make -j.

        Returns:
            BuildResult with success status and build info
        """
        return run_build(self.klipper_dir)
