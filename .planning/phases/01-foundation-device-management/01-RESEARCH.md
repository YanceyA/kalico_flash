# Phase 1: Foundation & Device Management - Research

**Researched:** 2026-01-25
**Domain:** Python stdlib-only architecture skeleton, device registry, USB discovery, pluggable output
**Confidence:** HIGH

## Summary

Phase 1 builds the foundational modules for klipper-flash: error hierarchy, dataclass contracts, device registry (JSON CRUD), USB discovery (serial-by-id scanning + pattern matching), and a pluggable output interface. It also delivers the CLI thin wrapper for device management commands (--add-device, --list-devices, --remove-device, --device). No build, config caching, or flash logic is in scope.

The standard approach is Python 3.9+ stdlib only: `dataclasses` for contracts, `json` + `pathlib` for persistence, `fnmatch` for glob matching, `typing.Protocol` for the pluggable output interface, and `argparse` for CLI. The architecture enforces hub-and-spoke coordination (orchestrator calls modules, modules never call each other) and separates I/O from logic (no `print()` or `sys.exit()` in library modules).

The key Phase 1 research questions are: (1) how to structure the pluggable output interface (Claude's discretion), (2) how to handle the registry schema with global vs per-device fields per the user's decision, (3) how to extract MCU type from serial paths, and (4) how to write the dataclass contracts with Python 3.9 compatibility.

**Primary recommendation:** Build errors.py first (all modules depend on it), then dataclasses/types module, then registry, then discovery, then output interface, then CLI wrapper. Use `typing.Protocol` for the output interface -- it is stdlib since Python 3.8, requires no inheritance, and cleanly separates CLI output from core logic.

## Standard Stack

The established libraries/tools for this phase:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `dataclasses` | stdlib (3.7+) | DeviceEntry, DiscoveredDevice, RegistryData contracts | Type-safe structured data without external deps |
| `json` | stdlib | Read/write devices.json | Human-readable, git-friendly persistence |
| `pathlib` | stdlib | Path manipulation, directory scanning | Modern file API, cleaner than os.path |
| `fnmatch` | stdlib | Glob pattern matching against serial filenames | Case-sensitive on Linux, well-defined semantics |
| `typing` | stdlib | Protocol for output interface, type hints | Protocol available since 3.8 |
| `argparse` | stdlib | CLI argument parsing | Flat flags, mutually exclusive groups |
| `os` | stdlib | os.replace() for atomic writes, os.fsync() | POSIX atomic rename guarantee |
| `tempfile` | stdlib | NamedTemporaryFile for atomic write pattern | Safe temp file in same directory |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `re` | stdlib | MCU type extraction from serial path | Parsing usb-Klipper_{mcu}_{serial}-if00 |
| `sys` | stdlib | Version guard, stderr output | Entry point only |
| `textwrap` | stdlib | dedent for multi-line help text | argparse description formatting |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `typing.Protocol` | ABC (`abc.ABC`) | Protocol is better: no inheritance required, duck-typing friendly, cleaner for callback injection |
| `typing.Protocol` | Plain callable/function | Protocol gives multi-method interface (info, error, success, warn) vs single callback; cleaner for structured output |
| `fnmatch` | `re` | fnmatch is purpose-built for glob patterns; re would require converting glob to regex |
| `json` | `configparser` | JSON handles nested structures (device entries + global config); ini cannot |

**Installation:**
```bash
# No installation needed -- all stdlib
# Python 3.9+ version guard in flash.py:
import sys
if sys.version_info < (3, 9):
    sys.exit("Error: Python 3.9+ required. Found: " + sys.version)
```

## Architecture Patterns

### Recommended Project Structure (Phase 1 scope)
```
klipper-flash/
    flash.py              # CLI entry point + argparse + dispatch (ARCH-02)
    errors.py             # Centralized exception hierarchy
    types.py              # Dataclass contracts: DeviceEntry, DiscoveredDevice, RegistryData
    registry.py           # Device registry JSON CRUD (RGST-01 through RGST-05)
    discovery.py          # USB serial scanning + pattern matching (DISC-01 through DISC-04)
    output.py             # Output Protocol + default CLI implementation (ARCH-03)
    devices.json          # Device registry data (created on first use)
```

**Why `types.py` separate from `registry.py`:** The CONTEXT.md decision splits global paths (klipper_dir, katapult_dir) from device entries. The dataclasses define the schema contract used by multiple modules. Keeping them in their own module prevents circular imports and makes the contracts referenceable from anywhere.

**Why `errors.py` separate:** All modules raise domain-specific exceptions. The orchestrator catches them. Centralizing prevents circular imports (e.g., discovery.py would otherwise need to import from registry.py for a shared error type).

### Pattern 1: Pluggable Output Interface via Protocol

**What:** Define an `Output` Protocol with methods for info, error, success, warn, and prompt. Core modules accept an `Output` parameter. The CLI provides a concrete implementation. Future Moonraker integration provides a different implementation.

**When to use:** Every module function that needs to communicate status to the user.

**Confidence:** HIGH -- `typing.Protocol` is stdlib since Python 3.8, fully available in Python 3.9.

```python
# output.py
from __future__ import annotations
from typing import Protocol, Optional

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


class CliOutput:
    """Default CLI output -- plain text, no ANSI color."""

    def info(self, section: str, message: str) -> None:
        print(f"[{section}] {message}")

    def success(self, message: str) -> None:
        print(f"[OK] {message}")

    def warn(self, message: str) -> None:
        print(f"[!!] {message}")

    def error(self, message: str) -> None:
        import sys
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


class NullOutput:
    """Silent output for testing or programmatic use."""

    def info(self, section: str, message: str) -> None: pass
    def success(self, message: str) -> None: pass
    def warn(self, message: str) -> None: pass
    def error(self, message: str) -> None: pass
    def device_line(self, marker: str, name: str, detail: str) -> None: pass
    def prompt(self, message: str, default: str = "") -> str: return default
    def confirm(self, message: str, default: bool = False) -> bool: return default
```

**Design rationale:**
- Protocol (structural subtyping) means no inheritance needed. Any class with matching methods satisfies the type.
- CliOutput uses plain text markers per CONTEXT.md: `[OK]`, `[FAIL]`, `[??]`, `[--]` -- no ANSI color, no Unicode.
- NullOutput enables unit testing without capturing stdout.
- `prompt()` and `confirm()` are on the Protocol because the add-device wizard needs interactive I/O, and this must be replaceable for Moonraker (which would provide values via API).
- No `sys.exit()` anywhere in output -- errors are reported, the caller decides to exit.

### Pattern 2: Registry Schema with Global vs Per-Device Fields

**What:** The devices.json file has two top-level keys: `"global"` for shared paths and defaults, `"devices"` for per-device entries.

**When to use:** All registry read/write operations.

```python
# types.py
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

@dataclass
class GlobalConfig:
    """Global settings shared across all devices."""
    klipper_dir: str = "~/klipper"
    katapult_dir: str = "~/katapult"
    default_flash_method: str = "katapult"

@dataclass
class DeviceEntry:
    """A registered device in the registry."""
    key: str                    # "octopus-pro" (user-chosen, used as --device flag)
    name: str                   # "Octopus Pro v1.1" (display name)
    mcu: str                    # "stm32h723" (extracted from serial path)
    serial_pattern: str         # "usb-Klipper_stm32h723xx_29001A001151313531383332*"
    flash_method: Optional[str] = None  # None = use global default

@dataclass
class DiscoveredDevice:
    """A USB serial device found during scanning."""
    path: str                   # "/dev/serial/by-id/usb-Klipper_stm32h723xx_..."
    filename: str               # "usb-Klipper_stm32h723xx_29001A001151313531383332-if00"

@dataclass
class RegistryData:
    """Complete registry file contents."""
    global_config: GlobalConfig = field(default_factory=GlobalConfig)
    devices: dict = field(default_factory=dict)  # key -> DeviceEntry fields
```

**JSON schema (devices.json):**
```json
{
  "global": {
    "klipper_dir": "~/klipper",
    "katapult_dir": "~/katapult",
    "default_flash_method": "katapult"
  },
  "devices": {
    "octopus-pro": {
      "name": "Octopus Pro v1.1",
      "mcu": "stm32h723",
      "serial_pattern": "usb-Klipper_stm32h723xx_29001A001151313531383332*",
      "flash_method": null
    },
    "nitehawk": {
      "name": "Nitehawk 36",
      "mcu": "rp2040",
      "serial_pattern": "usb-Klipper_rp2040_30333938340A53E6*",
      "flash_method": "make_flash"
    }
  }
}
```

**Design rationale:**
- CONTEXT.md decision: klipper_dir and katapult_dir are GLOBAL, not per-device.
- CONTEXT.md decision: flash_method is per-device with global default. `null` in JSON means "use global default."
- CONTEXT.md decision: Device key is user-chosen freeform string.
- CONTEXT.md decision: Registry schema is minimal -- name, mcu, serial_pattern, flash_method only.
- `str` for paths in dataclasses (not `Path`) because JSON serialization is simpler and paths are stored as strings in the file. Convert to `Path` at point of use.

### Pattern 3: MCU Extraction from Serial Path

**What:** Auto-extract MCU type from `/dev/serial/by-id/` filename for the add-device wizard.

**When to use:** During --add-device wizard when user selects a USB device.

```python
import re

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
    # Match usb-{Klipper|katapult}_{mcu_with_variant}_{serial}
    m = re.match(r"usb-(?:Klipper|katapult)_([a-z0-9]+?)(?:x[a-z0-9]*)?_", filename, re.IGNORECASE)
    if m:
        return m.group(1).lower()
    return None
```

**Verified against real serial paths from codebase:**
| Serial Filename | Extracted MCU |
|----------------|--------------|
| `usb-Klipper_stm32h723xx_29001A...` | `stm32h723` |
| `usb-Klipper_rp2040_30333938...` | `rp2040` |
| `usb-Klipper_stm32f411xe_60005E...` | `stm32f411` |
| `usb-katapult_stm32h723xx_29001A...` | `stm32h723` |
| `usb-katapult_rp2040_30333938...` | `rp2040` |
| `usb-Beacon_Beacon_RevH_FC269...` | `None` (not Klipper/Katapult) |

**Confidence:** HIGH -- verified against 6 actual serial paths from this project's hardware config files.

### Pattern 4: Serial Pattern Auto-Generation

**What:** Auto-generate a glob pattern from a selected device's full serial filename.

```python
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
```

**Design rationale:**
- CONTEXT.md decision: "Serial pattern auto-generated from full serial number (most specific)."
- Uses the full serial number for uniqueness (addresses pitfall SD-2: multiple devices matching same pattern).
- The `-if00` interface suffix is stripped because it could theoretically change.
- The `*` wildcard handles any suffix variations.

### Pattern 5: Atomic File Writes

**What:** Write files safely using temp-file-then-rename to prevent corruption on SD cards.

```python
import os
import tempfile
import json

def atomic_write_json(path: str, data: dict) -> None:
    """Write JSON atomically: write to temp file, fsync, rename."""
    dir_name = os.path.dirname(path) or "."
    with tempfile.NamedTemporaryFile(
        mode="w", dir=dir_name, delete=False, suffix=".tmp",
        encoding="utf-8"
    ) as tf:
        tmp_path = tf.name
        try:
            json.dump(data, tf, indent=2, sort_keys=True)
            tf.write("\n")  # POSIX trailing newline
            tf.flush()
            os.fsync(tf.fileno())
        except BaseException:
            os.unlink(tmp_path)
            raise
    os.replace(tmp_path, path)
```

**Design rationale:**
- `os.replace()` is atomic on POSIX (Linux ext4/btrfs) when source and target are on same filesystem.
- Temp file created in same directory guarantees same filesystem.
- `os.fsync()` flushes to disk before rename -- critical on Raspberry Pi SD cards.
- `sort_keys=True` for deterministic output (stable git diffs).
- Trailing newline for POSIX convention.
- `BaseException` catch (not just `Exception`) cleans up temp file on KeyboardInterrupt too.

**Confidence:** HIGH -- this is a well-established POSIX pattern. `os.replace()` is documented in Python stdlib as atomic on POSIX systems.

### Anti-Patterns to Avoid
- **sys.exit() in library code:** All error handling via exceptions. Only flash.py calls sys.exit() (ARCH-01).
- **print() in library code:** All output via the Output Protocol. Only flash.py creates CliOutput (ARCH-03).
- **Modules calling each other directly:** Hub-and-spoke only. discovery.py never imports registry.py (ARCH-04).
- **Raw dicts between modules:** Always use dataclasses for cross-module data (ARCH-05).
- **Global mutable state:** Config/state passed as function arguments, not module-level globals.
- **input() in library code:** Interactive prompts go through Output.prompt() and Output.confirm() so they are replaceable.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Glob pattern matching | Custom regex matching | `fnmatch.fnmatch()` | Battle-tested, handles edge cases in glob semantics, case-sensitive on Linux |
| JSON pretty printing | Manual string formatting | `json.dumps(indent=2, sort_keys=True)` | Handles escaping, Unicode, nested structures correctly |
| Path manipulation | String concatenation | `pathlib.Path` | Handles separators, resolution, existence checks cleanly |
| Atomic file write | Direct `open().write()` | temp file + `os.replace()` | Prevents corruption on crash/power loss (SD card risk) |
| CLI argument parsing | Manual sys.argv parsing | `argparse` with mutually exclusive groups | Handles help text, validation, error messages |
| Type-safe data contracts | Raw dicts with string keys | `@dataclass` with type annotations | IDE support, typo detection, serialization via `dataclasses.asdict()` |
| Structural subtyping | ABC inheritance | `typing.Protocol` | No inheritance needed, duck-typing friendly |

**Key insight:** This phase is entirely stdlib Python. Every component maps to a well-known standard library module. There is zero reason to hand-roll any of the above.

## Common Pitfalls

### Pitfall 1: Python 3.9 Type Hint Syntax
**What goes wrong:** Using `X | Y` union syntax or `list[str]` without `from __future__ import annotations` causes `TypeError` at runtime on Python 3.9.
**Why it happens:** PEP 604 (`X | Y`) is runtime-available only in Python 3.10+. PEP 585 (`list[str]`) is runtime-available only in 3.9+ BUT only in annotations context, not in default values or isinstance checks.
**How to avoid:** Add `from __future__ import annotations` to EVERY module file. This makes all annotations strings (lazy evaluation), enabling modern syntax on Python 3.9. Use `typing.Optional[X]` instead of `X | None` for runtime contexts like dataclass field defaults.
**Warning signs:** Code works on dev machine (3.11+) but fails on Raspberry Pi (3.9).

### Pitfall 2: Dataclass Serialization with Path Objects
**What goes wrong:** `dataclasses.asdict()` converts `Path` objects to `PosixPath('...')` which is not JSON-serializable.
**Why it happens:** `asdict()` recursively converts dataclass fields but does not call `str()` on non-dataclass, non-dict, non-list values.
**How to avoid:** Store paths as `str` in dataclasses, not `Path`. Convert to `Path` at point of use (in the module that needs filesystem access). This keeps serialization trivial.
**Warning signs:** `TypeError: Object of type PosixPath is not JSON serializable`.

### Pitfall 3: /dev/serial/by-id/ Does Not Exist
**What goes wrong:** `Path('/dev/serial/by-id').iterdir()` raises `FileNotFoundError` if no USB serial devices are connected (the directory is created dynamically by udev).
**Why it happens:** The directory only exists when at least one USB serial device is connected. Fresh boot with no devices = no directory.
**How to avoid:** Check `Path('/dev/serial/by-id').is_dir()` before iterating. Return empty list if not found. Display helpful message via Output.info().
**Warning signs:** Tool crashes on startup with no boards plugged in.

### Pitfall 4: Empty or Corrupt devices.json
**What goes wrong:** First run has no devices.json. Power loss during write can leave truncated/empty file.
**Why it happens:** File does not exist initially. SD card corruption is common on Raspberry Pi.
**How to avoid:** Handle missing file gracefully (return default empty RegistryData). Use atomic writes for all saves. Validate JSON structure on load (check for expected keys). On parse error, report clearly and suggest re-registering devices.
**Warning signs:** `json.JSONDecodeError`, `KeyError` on malformed data.

### Pitfall 5: Device Key Collision
**What goes wrong:** User registers two devices with the same key (e.g., both named "board").
**Why it happens:** No uniqueness validation during add-device wizard.
**How to avoid:** Before saving, check if key already exists in registry. If so, error with message: "Device 'board' already registered. Use a different name or --remove-device first."
**Warning signs:** Second device silently overwrites first in JSON dict.

### Pitfall 6: Serial Pattern Overlap
**What goes wrong:** Two devices have patterns where one matches the other's serial path (e.g., `usb-Klipper_rp2040*` matches both rp2040 boards).
**Why it happens:** Pattern is too broad (MCU prefix only instead of full serial number).
**How to avoid:** Auto-generate patterns from full serial path (CONTEXT.md decision). During add, check new pattern against all existing registered devices -- warn if it matches any already-matched device.
**Warning signs:** Wrong device identified during discovery; user sees unexpected device name.

### Pitfall 7: input() Blocks on Non-Interactive Use
**What goes wrong:** Running `flash.py --add-device` in a non-interactive context (pipe, cron) hangs on `input()`.
**Why it happens:** `input()` blocks waiting for stdin when there is no terminal.
**How to avoid:** Check `sys.stdin.isatty()` before launching interactive wizards. If not a TTY, error with "Interactive terminal required for --add-device. Run from SSH terminal."
**Warning signs:** Tool hangs indefinitely in automated contexts.

## Code Examples

Verified patterns from official sources:

### Registry Load/Save with Atomic Writes
```python
# registry.py
from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path
from typing import Optional

from types import DeviceEntry, GlobalConfig, RegistryData
from errors import RegistryError

class Registry:
    """Device registry backed by devices.json."""

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
        )
        devices = {}
        for key, data in raw.get("devices", {}).items():
            devices[key] = DeviceEntry(
                key=key,
                name=data["name"],
                mcu=data["mcu"],
                serial_pattern=data["serial_pattern"],
                flash_method=data.get("flash_method"),
            )
        return RegistryData(global_config=global_config, devices=devices)

    def save(self, registry: RegistryData) -> None:
        """Save registry to disk atomically."""
        data = {
            "global": {
                "klipper_dir": registry.global_config.klipper_dir,
                "katapult_dir": registry.global_config.katapult_dir,
                "default_flash_method": registry.global_config.default_flash_method,
            },
            "devices": {}
        }
        for key, device in sorted(registry.devices.items()):
            data["devices"][key] = {
                "name": device.name,
                "mcu": device.mcu,
                "serial_pattern": device.serial_pattern,
                "flash_method": device.flash_method,
            }
        _atomic_write_json(self.path, data)

    def get(self, key: str) -> Optional[DeviceEntry]:
        registry = self.load()
        return registry.devices.get(key)

    def add(self, entry: DeviceEntry) -> None:
        registry = self.load()
        if entry.key in registry.devices:
            raise RegistryError(f"Device '{entry.key}' already registered")
        registry.devices[entry.key] = entry
        self.save(registry)

    def remove(self, key: str) -> bool:
        registry = self.load()
        if key not in registry.devices:
            return False
        del registry.devices[key]
        self.save(registry)
        return True

    def list_all(self) -> list:
        registry = self.load()
        return list(registry.devices.values())


def _atomic_write_json(path: str, data: dict) -> None:
    dir_name = os.path.dirname(os.path.abspath(path))
    os.makedirs(dir_name, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", dir=dir_name, delete=False, suffix=".tmp",
        encoding="utf-8"
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
```

### Discovery Module
```python
# discovery.py
from __future__ import annotations
import fnmatch
from pathlib import Path
from typing import Optional

from types import DiscoveredDevice

SERIAL_BY_ID = "/dev/serial/by-id"

def scan_serial_devices() -> list:
    """Scan /dev/serial/by-id/ and return all USB serial devices."""
    serial_dir = Path(SERIAL_BY_ID)
    if not serial_dir.is_dir():
        return []
    devices = []
    for entry in sorted(serial_dir.iterdir()):
        devices.append(DiscoveredDevice(
            path=str(entry),
            filename=entry.name,
        ))
    return devices

def match_device(pattern: str, devices: list) -> Optional[DiscoveredDevice]:
    """Find first device whose filename matches a glob pattern."""
    for device in devices:
        if fnmatch.fnmatch(device.filename, pattern):
            return device
    return None

def find_registered_devices(devices: list, registry_devices: dict) -> tuple:
    """Cross-reference discovered devices against registry.

    Returns (matched, unmatched) where:
      matched = list of (DeviceEntry, DiscoveredDevice) tuples
      unmatched = list of DiscoveredDevice not matching any pattern
    """
    matched = []
    unmatched_devices = list(devices)  # copy

    for entry in registry_devices.values():
        for device in devices:
            if fnmatch.fnmatch(device.filename, entry.serial_pattern):
                matched.append((entry, device))
                if device in unmatched_devices:
                    unmatched_devices.remove(device)
                break

    return matched, unmatched_devices
```

### Error Hierarchy
```python
# errors.py
from __future__ import annotations

class KlipperFlashError(Exception):
    """Base for all klipper-flash errors."""
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

# Phase 2/3 will add:
# class BuildError(KlipperFlashError): ...
# class FlashError(KlipperFlashError): ...
# class ServiceError(KlipperFlashError): ...
```

### CLI Dispatch Pattern
```python
# flash.py (entry point)
from __future__ import annotations
import argparse
import sys

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flash.py",
        description="Build and flash Klipper firmware for USB-connected MCU boards.",
    )
    parser.add_argument("--device", metavar="NAME",
        help="Select device by registry key (skip interactive selection)")

    mgmt = parser.add_mutually_exclusive_group()
    mgmt.add_argument("--add-device", action="store_true",
        help="Interactive wizard to register a new device")
    mgmt.add_argument("--list-devices", action="store_true",
        help="Show all registered devices with connection status")
    mgmt.add_argument("--remove-device", metavar="NAME",
        help="Remove a device from the registry")
    return parser

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # Late imports to keep startup fast
    from output import CliOutput
    from registry import Registry
    from errors import KlipperFlashError

    out = CliOutput()
    registry = Registry("devices.json")

    try:
        if args.add_device:
            return cmd_add_device(registry, out)
        elif args.list_devices:
            return cmd_list_devices(registry, out)
        elif args.remove_device:
            return cmd_remove_device(registry, args.remove_device, out)
        else:
            # Phase 2/3: cmd_flash()
            out.error("Flash workflow not yet implemented. Use --add-device, --list-devices, or --remove-device.")
            return 1
    except KeyboardInterrupt:
        print("\nAborted.")
        return 130
    except KlipperFlashError as e:
        out.error(str(e))
        return 1
    except Exception as e:
        out.error(f"Unexpected error: {e}")
        return 3

if __name__ == "__main__":
    sys.exit(main())
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `typing.Optional[X]` | `X \| None` (3.10+) | Python 3.10 | Use `Optional` for 3.9 compat, or `from __future__ import annotations` |
| `os.path.join()` | `pathlib.Path / "file"` | Python 3.4+ | Use pathlib throughout |
| `open()/write()/close()` | `Path.write_text()` | Python 3.4+ | Simpler for non-atomic simple writes |
| `dict` for data contracts | `@dataclass` | Python 3.7+ | Type-safe, IDE support |
| `abc.ABC` for interfaces | `typing.Protocol` | Python 3.8+ | No inheritance required |
| Manual temp file + rename | `tempfile.NamedTemporaryFile` + `os.replace()` | Python 3.3+ | `os.replace()` is the correct atomic rename |

**Deprecated/outdated:**
- `os.rename()` for atomic replacement: Use `os.replace()` instead -- it works cross-platform and handles existing target files correctly.
- `typing.Union[X, None]` verbose form: `Optional[X]` is equivalent and preferred for 3.9.

## Open Questions

Things that couldn't be fully resolved:

1. **Module naming: `types.py` shadows stdlib `types` module**
   - What we know: Python has a stdlib module called `types` (for type manipulation functions). Naming our dataclass module `types.py` would shadow it.
   - What's unclear: Whether any code in the project would need `import types` from stdlib.
   - Recommendation: Name it `models.py` or `contracts.py` or `datatypes.py` instead. `models.py` is the most conventional in Python projects.

2. **Registry path: relative or absolute?**
   - What we know: The tool will be deployed to the Raspberry Pi. Registry needs a stable location.
   - What's unclear: Whether devices.json should live next to flash.py (relative) or in a fixed location like `~/.config/klipper-flash/`.
   - Recommendation: Default to `Path(__file__).parent / "devices.json"` (next to flash.py). This matches the flat project structure and is simple. Can add `--registry` flag later if needed.

3. **Global config first-run behavior**
   - What we know: CONTEXT.md says "klipper_dir and katapult_dir use smart defaults (~/klipper, ~/katapult), user confirms or changes."
   - What's unclear: When exactly global config gets set -- during first --add-device, or on very first invocation?
   - Recommendation: Set during first --add-device wizard. If devices.json does not exist, create with defaults. Show defaults, let user confirm/change.

## Sources

### Primary (HIGH confidence)
- Python 3.9 `typing` module docs: `Protocol` available since 3.8 -- [docs.python.org/3.9/library/typing.html](https://docs.python.org/3.9/library/typing.html)
- Python `dataclasses` module docs -- [docs.python.org/3/library/dataclasses.html](https://docs.python.org/3/library/dataclasses.html)
- Python `os.replace()` docs -- atomic rename on POSIX
- Python `fnmatch` module docs -- glob pattern matching semantics
- Python `json` module docs -- serialization with sort_keys and indent
- Codebase serial paths (hardware/*.cfg) -- verified MCU extraction against 6 real paths

### Secondary (MEDIUM confidence)
- Atomic write pattern using `tempfile.NamedTemporaryFile` + `os.fsync()` + `os.replace()` -- [GitHub Gist: Safe atomic file writes for JSON](https://gist.github.com/therightstuff/cbdcbef4010c20acc70d2175a91a321f)
- Protocol pattern for output abstraction -- [Real Python: Python Protocols](https://realpython.com/python-protocol/)
- Python discuss.python.org thread on adding atomicwrite to stdlib

### Tertiary (LOW confidence)
- None -- all Phase 1 patterns are well-established stdlib usage with no uncertain areas.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all stdlib, all verified against Python 3.9 docs
- Architecture: HIGH -- Protocol pattern verified available in 3.8+; hub-and-spoke is established CLI pattern
- Pitfalls: HIGH -- based on Python stdlib semantics and Raspberry Pi deployment constraints
- MCU extraction: HIGH -- verified against 6 actual serial paths from this project's hardware config files
- Pluggable output design: HIGH -- Protocol is the right tool, verified in stdlib docs

**Research date:** 2026-01-25
**Valid until:** 2026-03-25 (stable domain, Python stdlib does not change frequently)
