"""Pluggable output interface via Protocol."""
from __future__ import annotations

import sys
from typing import Protocol


class Output(Protocol):
    """Pluggable output interface. Core modules call these methods.
    CLI provides CliOutput. Future Moonraker provides MoonrakerOutput."""

    def info(self, section: str, message: str) -> None: ...
    def success(self, message: str) -> None: ...
    def warn(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...
    def device_line(self, marker: str, name: str, detail: str) -> None: ...
    def prompt(self, message: str, default: str = "") -> str: ...
    def confirm(self, message: str, default: bool = False) -> bool: ...
    def phase(self, phase_name: str, message: str) -> None: ...


class CliOutput:
    """Default CLI output -- plain text, no ANSI color."""

    def info(self, section: str, message: str) -> None:
        print(f"[{section}] {message}")

    def success(self, message: str) -> None:
        print(f"[OK] {message}")

    def warn(self, message: str) -> None:
        print(f"[!!] {message}")

    def error(self, message: str) -> None:
        print(f"[FAIL] {message}", file=sys.stderr)

    def device_line(self, marker: str, name: str, detail: str) -> None:
        print(f"  [{marker}] {name:<24s} {detail}")

    def prompt(self, message: str, default: str = "") -> str:
        suffix = f" [{default}]" if default else ""
        response = input(f"{message}{suffix}: ").strip()
        return response or default

    def confirm(self, message: str, default: bool = False) -> bool:
        suffix = " [Y/n]" if default else " [y/N]"
        response = input(f"{message}{suffix}: ").strip().lower()
        if not response:
            return default
        return response in ("y", "yes")

    def phase(self, phase_name: str, message: str) -> None:
        """Output a phase-labeled message."""
        print(f"[{phase_name}] {message}")


class NullOutput:
    """Silent output for testing or programmatic use."""

    def info(self, section: str, message: str) -> None: pass
    def success(self, message: str) -> None: pass
    def warn(self, message: str) -> None: pass
    def error(self, message: str) -> None: pass
    def device_line(self, marker: str, name: str, detail: str) -> None: pass
    def prompt(self, message: str, default: str = "") -> str: return default
    def confirm(self, message: str, default: bool = False) -> bool: return default
    def phase(self, phase_name: str, message: str) -> None: pass
