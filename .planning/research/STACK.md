# Stack Research: kalico-flash v2.0 Additions

**Project:** Python CLI tool for Klipper firmware building and flashing
**Target:** Python 3.9+ stdlib only, Raspberry Pi (ARM Linux), SSH usage
**Researched:** 2026-01-26
**Overall Confidence:** HIGH (all recommendations verified against official Python docs and Moonraker API)

**Context:** This document supplements the v1.0 stack research with v2.0-specific additions. The core stack (argparse, subprocess, pathlib, json, dataclasses, etc.) remains unchanged.

---

## v2.0 Feature Stack Summary

| Feature | Primary Modules | Confidence |
|---------|-----------------|------------|
| TUI Menu System | `print()` + Unicode, `input()`, `sys.stdin.isatty()` | HIGH |
| Moonraker API Integration | `urllib.request`, `urllib.error`, `socket`, `json` | HIGH |
| Post-Flash Verification | `time.sleep()`, `pathlib`, existing `discovery.py` | HIGH |
| Version Parsing | `re`, `dataclasses` | HIGH |
| Installation Script | Bash + `shutil.which()` validation | HIGH |

---

## 1. Moonraker API Integration

### Module Selection

**Use:** `urllib.request` + `urllib.error` + `socket` + `json`

**Rationale:** The stdlib-only constraint eliminates `requests`. `urllib.request` provides everything needed for simple HTTP GET/POST to localhost Moonraker API.

### Implementation Pattern

```python
import json
import socket
import urllib.error
import urllib.request
from typing import Optional

from errors import MoonrakerError  # New exception class

MOONRAKER_TIMEOUT = 5  # seconds
MOONRAKER_DEFAULT_PORT = 7125


def moonraker_get(
    endpoint: str,
    host: str = "localhost",
    port: int = MOONRAKER_DEFAULT_PORT,
) -> dict:
    """GET request to Moonraker API.

    Args:
        endpoint: API path, e.g., "/printer/info"
        host: Moonraker host (default localhost)
        port: Moonraker port (default 7125)

    Returns:
        Parsed JSON response dict

    Raises:
        MoonrakerError: On connection, timeout, or parse errors
    """
    url = f"http://{host}:{port}{endpoint}"
    try:
        with urllib.request.urlopen(url, timeout=MOONRAKER_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data
    except urllib.error.URLError as e:
        raise MoonrakerError(f"Connection failed: {e.reason}")
    except socket.timeout:
        raise MoonrakerError(f"Timeout ({MOONRAKER_TIMEOUT}s) connecting to Moonraker")
    except json.JSONDecodeError as e:
        raise MoonrakerError(f"Invalid JSON response: {e}")


def moonraker_post(
    endpoint: str,
    payload: dict,
    host: str = "localhost",
    port: int = MOONRAKER_DEFAULT_PORT,
) -> dict:
    """POST JSON to Moonraker API.

    Required for printer.objects.query endpoint.
    """
    url = f"http://{host}:{port}{endpoint}"
    json_data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url=url,
        data=json_data,
        method="POST",
        headers={"Content-Type": "application/json; charset=UTF-8"},
    )

    try:
        with urllib.request.urlopen(req, timeout=MOONRAKER_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise MoonrakerError(f"Connection failed: {e.reason}")
    except socket.timeout:
        raise MoonrakerError(f"Timeout ({MOONRAKER_TIMEOUT}s) connecting to Moonraker")
    except json.JSONDecodeError as e:
        raise MoonrakerError(f"Invalid JSON response: {e}")
```

### Moonraker Endpoints Required

| Feature | Endpoint | Method | Response Field |
|---------|----------|--------|----------------|
| Print status check | `/printer/info` | GET | `result.state` ("ready"/"printing"/"paused"/"error"/"startup"/"shutdown") |
| MCU firmware version | `/printer/objects/query` | POST | Query `mcu` object for `mcu_version` |
| Host software version | `/printer/info` | GET | `result.software_version` |

### Print Status Check Implementation

```python
def is_printer_busy(host: str = "localhost", port: int = 7125) -> tuple[bool, str]:
    """Check if printer is currently printing or paused.

    Returns:
        (is_busy, state_string) where is_busy=True means flashing is unsafe
    """
    try:
        data = moonraker_get("/printer/info", host, port)
        state = data.get("result", {}).get("state", "unknown")
        # Block flash if printing or paused (user may resume)
        is_busy = state in ("printing", "paused")
        return is_busy, state
    except MoonrakerError:
        # Can't reach Moonraker - assume safe (Klipper may already be stopped)
        return False, "unreachable"
```

### MCU Version Query Implementation

```python
def get_mcu_version(
    mcu_name: str = "mcu",
    host: str = "localhost",
    port: int = 7125,
) -> Optional[str]:
    """Get firmware version from an MCU via Moonraker.

    Args:
        mcu_name: "mcu" for main MCU, or specific name like "EBBCan"

    Returns:
        Version string like "v0.12.0-85-gd785b396" or None if unavailable
    """
    payload = {
        "objects": {
            mcu_name: ["mcu_version"]
        }
    }
    try:
        data = moonraker_post("/printer/objects/query", payload, host, port)
        status = data.get("result", {}).get("status", {})
        mcu_data = status.get(mcu_name, {})
        return mcu_data.get("mcu_version")
    except MoonrakerError:
        return None


def get_host_version(host: str = "localhost", port: int = 7125) -> Optional[str]:
    """Get Klipper host software version via Moonraker.

    Returns:
        Version string like "v0.12.0-85-gd785b396" or None if unavailable
    """
    try:
        data = moonraker_get("/printer/info", host, port)
        return data.get("result", {}).get("software_version")
    except MoonrakerError:
        return None
```

### Error Handling Strategy

**New exception class in errors.py:**
```python
class MoonrakerError(KlipperFlashError):
    """Moonraker API communication errors."""
    pass
```

**Graceful degradation pattern:** Moonraker unavailability should warn, not block.
- Print check failure: Warn and prompt user to confirm safe to proceed
- Version check failure: Skip version mismatch detection silently

**Confidence:** HIGH (verified from official Moonraker documentation at moonraker.readthedocs.io)

---

## 2. TUI Menu Implementation

### Design Philosophy

**Use:** Pure `print()` + `input()` with Unicode box-drawing characters

**Why NOT curses:**
1. Windows compatibility issues (requires `windows-curses` package)
2. Adds complexity for simple numbered menus
3. Existing codebase uses print/input pattern successfully in `output.py`
4. The complex TUI (menuconfig) is already delegated to make

### Unicode Box-Drawing Characters

```python
# Unicode box-drawing characters - work in any UTF-8 terminal
# These are part of the "Box Drawing" Unicode block (U+2500-U+257F)
BOX_TL = "\u250c"  # Top-left corner:
BOX_TR = "\u2510"  # Top-right corner:
BOX_BL = "\u2514"  # Bottom-left corner:
BOX_BR = "\u2518"  # Bottom-right corner:
BOX_H = "\u2500"   # Horizontal line:
BOX_V = "\u2502"   # Vertical line:
BOX_LT = "\u251c"  # Left T-junction:
BOX_RT = "\u2524"  # Right T-junction:
```

### Menu Rendering Pattern

```python
def print_boxed_menu(title: str, options: list[str], width: int = 50) -> None:
    """Print a boxed menu with numbered options.

    Example output:
    +--------------------------------------------------+
    |  Select Device to Flash                          |
    +--------------------------------------------------+
    |  1. octopus-pro - Octopus Pro v1.1 (STM32H723)  |
    |  2. nitehawk - Nitehawk 36 (RP2040)             |
    +--------------------------------------------------+
    |  q. Quit                                         |
    +--------------------------------------------------+
    """
    print(f"{BOX_TL}{BOX_H * width}{BOX_TR}")
    print(f"{BOX_V}  {title:<{width - 2}}{BOX_V}")
    print(f"{BOX_LT}{BOX_H * width}{BOX_RT}")

    for i, opt in enumerate(options, 1):
        line = f"{i}. {opt}"
        print(f"{BOX_V}  {line:<{width - 2}}{BOX_V}")

    print(f"{BOX_LT}{BOX_H * width}{BOX_RT}")
    print(f"{BOX_V}  {'q. Quit':<{width - 2}}{BOX_V}")
    print(f"{BOX_BL}{BOX_H * width}{BOX_BR}")
```

### Menu Selection Pattern

```python
def select_from_menu(
    options: list[str],
    prompt: str = "Select",
    max_attempts: int = 3,
) -> int:
    """Get user selection from numbered menu.

    Args:
        options: List of option strings
        prompt: Prompt text
        max_attempts: Max invalid inputs before returning -1

    Returns:
        0-based index of selected option, or -1 for quit/cancel
    """
    for attempt in range(max_attempts):
        try:
            choice = input(f"{prompt} [1-{len(options)}, q=quit]: ").strip().lower()
            if choice == "q":
                return -1
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return idx
            print(f"  Invalid selection. Enter 1-{len(options)} or 'q' to quit.")
        except ValueError:
            print("  Please enter a number or 'q'.")

    return -1  # Too many invalid attempts
```

### TTY Detection (already exists in codebase)

The existing pattern in `flash.py` uses `sys.stdin.isatty()`:

```python
import sys

# Already in cmd_flash():
if device_key is None and not sys.stdin.isatty():
    out.error("Interactive terminal required. Use --device KEY or run from SSH terminal.")
    return 1
```

### ASCII Fallback for Legacy Terminals

```python
import os

def _supports_unicode() -> bool:
    """Check if terminal likely supports Unicode box drawing."""
    lang = os.environ.get("LANG", "").upper()
    lc_all = os.environ.get("LC_ALL", "").upper()
    return "UTF-8" in lang or "UTF-8" in lc_all

# Module-level initialization
if _supports_unicode():
    BOX_TL, BOX_TR, BOX_BL, BOX_BR = "\u250c", "\u2510", "\u2514", "\u2518"
    BOX_H, BOX_V = "\u2500", "\u2502"
    BOX_LT, BOX_RT = "\u251c", "\u2524"
else:
    # ASCII fallback for non-UTF-8 terminals
    BOX_TL, BOX_TR, BOX_BL, BOX_BR = "+", "+", "+", "+"
    BOX_H, BOX_V = "-", "|"
    BOX_LT, BOX_RT = "+", "+"
```

**Confidence:** HIGH (uses only print/input which are proven to work in the existing codebase)

---

## 3. Version Parsing and Comparison

### Git Describe Format

Klipper/Kalico versions follow `git describe` format:
```
v0.12.0-85-gd785b396[-dirty]
^     ^ ^  ^        ^
|     | |  |        +-- optional: uncommitted changes
|     | |  +----------- commit hash (prefixed with 'g')
|     | +-------------- commits since tag
|     +---------------- patch version
+---------------------- major.minor version with 'v' prefix
```

### Implementation Pattern

```python
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class KlipperVersion:
    """Parsed Klipper/Kalico version from git describe format."""
    major: int
    minor: int
    patch: int
    commits_since_tag: int
    commit_hash: str
    dirty: bool
    raw: str  # Original string for display

    def __lt__(self, other: "KlipperVersion") -> bool:
        """Compare versions. Newer = greater."""
        return (self.major, self.minor, self.patch, self.commits_since_tag) < \
               (other.major, other.minor, other.patch, other.commits_since_tag)

    def __eq__(self, other: object) -> bool:
        """Versions equal if commit hash matches (ignore dirty flag)."""
        if not isinstance(other, KlipperVersion):
            return NotImplemented
        return self.commit_hash == other.commit_hash

    def is_compatible_with(self, other: "KlipperVersion") -> bool:
        """Check if versions are protocol-compatible (same major.minor.patch)."""
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)


# Regex pattern for git describe format
VERSION_PATTERN = re.compile(
    r"v?(\d+)\.(\d+)\.(\d+)"        # v0.12.0 (v prefix optional)
    r"(?:-(\d+))?"                   # -85 (commits since tag, optional)
    r"(?:-g([a-f0-9]+))?"            # -gd785b396 (commit hash, optional)
    r"(-dirty)?$",                   # -dirty (optional)
    re.IGNORECASE
)


def parse_klipper_version(version_str: str) -> Optional[KlipperVersion]:
    """Parse a Klipper/Kalico version string.

    Examples:
        "v0.12.0-85-gd785b396" -> KlipperVersion(0, 12, 0, 85, "d785b396", False, ...)
        "v0.12.0" -> KlipperVersion(0, 12, 0, 0, "", False, ...)
        "v0.12.0-dirty" -> KlipperVersion(0, 12, 0, 0, "", True, ...)
        "invalid" -> None

    Returns:
        KlipperVersion or None if string doesn't match expected format
    """
    match = VERSION_PATTERN.match(version_str.strip())
    if not match:
        return None

    return KlipperVersion(
        major=int(match.group(1)),
        minor=int(match.group(2)),
        patch=int(match.group(3)),
        commits_since_tag=int(match.group(4) or 0),
        commit_hash=match.group(5) or "",
        dirty=match.group(6) is not None,
        raw=version_str.strip(),
    )
```

### Version Mismatch Detection

```python
def check_version_mismatch(
    host_version: str,
    mcu_version: str,
) -> Optional[str]:
    """Check if host and MCU versions are compatible.

    Args:
        host_version: Klipper host software version string
        mcu_version: MCU firmware version string

    Returns:
        Warning message if versions don't match, None if compatible
    """
    host = parse_klipper_version(host_version)
    mcu = parse_klipper_version(mcu_version)

    if host is None or mcu is None:
        return None  # Can't compare unparseable versions

    if host == mcu:
        return None  # Exact match (same commit hash)

    if host.is_compatible_with(mcu):
        return None  # Same major.minor.patch, different commit

    if host > mcu:
        return (
            f"MCU firmware ({mcu.raw}) is older than host ({host.raw}).\n"
            "Flashing will update the MCU to match."
        )
    else:
        return (
            f"MCU firmware ({mcu.raw}) is NEWER than host ({host.raw}).\n"
            "This is unusual - did you downgrade Klipper/Kalico?"
        )
```

**Why not use `packaging` library:** stdlib-only constraint. Custom parser handles git describe format which isn't standard semver/PEP 440 anyway.

**Confidence:** HIGH (regex pattern verified against real Klipper version strings from documentation)

---

## 4. Post-Flash Device Verification

### Verification Strategy

After successful flash, the device should:
1. Disappear briefly (bootloader reset / DFU mode)
2. Reappear with `usb-Klipper_*` prefix (not `usb-katapult_*`)

### Implementation Pattern

```python
import time
from pathlib import Path
from typing import Optional, Tuple


def verify_device_reappears(
    serial_pattern: str,
    timeout: float = 15.0,
    poll_interval: float = 0.5,
) -> Tuple[bool, Optional[str]]:
    """Wait for device to reappear after flash with Klipper firmware.

    Args:
        serial_pattern: Glob pattern to match (e.g., "usb-Klipper_stm32h723xx_*")
        timeout: Max seconds to wait for device
        poll_interval: Seconds between checks

    Returns:
        (success, device_path) - device_path is None if not found within timeout
    """
    from discovery import scan_serial_devices, match_device

    deadline = time.monotonic() + timeout
    last_path = None

    while time.monotonic() < deadline:
        devices = scan_serial_devices()
        matched = match_device(serial_pattern, devices)

        if matched:
            # Verify it's Klipper firmware, not still in Katapult bootloader
            filename_lower = matched.filename.lower()
            if "klipper_" in filename_lower:
                return True, matched.path
            # Device appeared but still in bootloader - keep waiting
            last_path = matched.path

        time.sleep(poll_interval)

    # Timeout - return last seen path for diagnostics
    return False, last_path
```

### Integration into Flash Workflow

Add to `cmd_flash()` after successful flash result:

```python
# Post-flash verification (v2.0)
if flash_result.success:
    out.phase("Flash", "Verifying device reconnected with Klipper firmware...")
    success, device_path = verify_device_reappears(
        entry.serial_pattern,
        timeout=15.0,
    )
    if success:
        out.phase("Flash", f"Device verified at {device_path}")
    else:
        out.warn(
            "Device did not reappear within 15 seconds.\n"
            "Recovery: Power cycle the board. If still not appearing, "
            "the flash may have failed - try again."
        )
```

**Confidence:** HIGH (uses existing discovery module patterns, proven polling approach)

---

## 5. Installation Script (install.sh)

### Requirements

1. Create symlink `kflash` -> `flash.py` in user's PATH
2. Verify Python 3.9+ available
3. Check target directory exists and is in PATH
4. Handle existing symlink gracefully

### Bash Implementation

```bash
#!/bin/bash
# install.sh - Install kalico-flash as 'kflash' command

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${HOME}/.local/bin"
SYMLINK_NAME="kflash"
TARGET="${SCRIPT_DIR}/kalico-flash/flash.py"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

error() { echo -e "${RED}Error: $1${NC}" >&2; exit 1; }
warn() { echo -e "${YELLOW}Warning: $1${NC}"; }
success() { echo -e "${GREEN}$1${NC}"; }
info() { echo "$1"; }

# Check Python version
check_python() {
    if ! command -v python3 &> /dev/null; then
        error "python3 not found in PATH"
    fi

    local version
    version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    local major minor
    major=$(echo "$version" | cut -d. -f1)
    minor=$(echo "$version" | cut -d. -f2)

    if [ "$major" -lt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -lt 9 ]; }; then
        error "Python 3.9+ required (found $version)"
    fi
    info "Found Python $version"
}

# Check flash.py exists
check_target() {
    if [ ! -f "$TARGET" ]; then
        error "flash.py not found at $TARGET"
    fi
}

# Create install directory if needed
ensure_install_dir() {
    if [ ! -d "$INSTALL_DIR" ]; then
        info "Creating $INSTALL_DIR..."
        mkdir -p "$INSTALL_DIR"
    fi
}

# Check if directory is in PATH
check_path() {
    if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
        echo ""
        warn "$INSTALL_DIR is not in your PATH"
        echo "Add this line to your ~/.bashrc or ~/.profile:"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        echo "Then run: source ~/.bashrc"
        echo ""
    fi
}

# Create or update symlink
create_symlink() {
    local link="${INSTALL_DIR}/${SYMLINK_NAME}"

    if [ -L "$link" ]; then
        local current_target
        current_target=$(readlink "$link")
        if [ "$current_target" = "$TARGET" ]; then
            info "Symlink already exists and is correct"
            return
        fi
        info "Updating existing symlink..."
        rm "$link"
    elif [ -e "$link" ]; then
        error "$link exists and is not a symlink. Remove it manually first."
    fi

    ln -s "$TARGET" "$link"
    chmod +x "$TARGET"
    info "Created symlink: $link -> $TARGET"
}

# Main
main() {
    echo "Installing kalico-flash..."
    echo ""

    check_python
    check_target
    ensure_install_dir
    create_symlink
    check_path

    echo ""
    success "Installation complete!"
    echo ""
    echo "Usage:"
    echo "  kflash --help          Show help"
    echo "  kflash --list-devices  List registered devices"
    echo "  kflash --add-device    Register a new device"
    echo "  kflash                 Flash a device (interactive)"
}

main "$@"
```

### Python Validation Helper (optional)

```python
import shutil
import sys
from typing import List


def check_installation_requirements() -> List[str]:
    """Check requirements for kalico-flash operation.

    Returns:
        List of error/warning messages (empty = all good)
    """
    issues = []

    # Check Python version
    if sys.version_info < (3, 9):
        issues.append(
            f"Python 3.9+ required (found {sys.version_info.major}.{sys.version_info.minor})"
        )

    # Check make available (required for firmware builds)
    if shutil.which("make") is None:
        issues.append("'make' not found in PATH (required for firmware builds)")

    # Check git available (optional, for version detection)
    if shutil.which("git") is None:
        issues.append("'git' not found in PATH (optional, used for version detection)")

    return issues
```

**Confidence:** HIGH (standard Linux installation patterns)

---

## 6. New Dataclasses for v2.0

Add to `models.py`:

```python
from dataclasses import dataclass, field
from typing import Optional, Dict


@dataclass
class PrinterStatus:
    """Printer status from Moonraker API."""
    state: str  # "ready", "printing", "paused", "error", "startup", "shutdown"
    state_message: str = ""

    @property
    def is_busy(self) -> bool:
        """True if printer is printing or paused (unsafe to flash)."""
        return self.state in ("printing", "paused")

    @property
    def is_ready(self) -> bool:
        """True if printer is idle and ready."""
        return self.state == "ready"


@dataclass
class VersionInfo:
    """Version information from Moonraker."""
    host_version: Optional[str] = None
    mcu_versions: Dict[str, str] = field(default_factory=dict)  # mcu_name -> version


@dataclass
class VerificationResult:
    """Result of post-flash device verification."""
    success: bool
    device_path: Optional[str] = None
    elapsed_seconds: float = 0.0
    error_message: Optional[str] = None
```

---

## 7. New Exception Class for v2.0

Add to `errors.py`:

```python
class MoonrakerError(KlipperFlashError):
    """Moonraker API communication errors: connection refused, timeout, bad response."""
    pass
```

---

## 8. New CLI Flags for v2.0

Add to `build_parser()` in `flash.py`:

```python
# New v2.0 flags
parser.add_argument(
    "--skip-menuconfig",
    action="store_true",
    help="Use cached .config without launching menuconfig (requires existing cache)",
)

parser.add_argument(
    "--skip-print-check",
    action="store_true",
    help="Skip Moonraker print status check (use if Moonraker is unavailable)",
)

parser.add_argument(
    "--no-verify",
    action="store_true",
    help="Skip post-flash device verification",
)
```

---

## Anti-Patterns: What NOT to Use for v2.0

### External Dependencies (FORBIDDEN)

| Library | Why Avoid | Alternative |
|---------|-----------|-------------|
| `requests` | Not stdlib | `urllib.request` |
| `httpx` | Not stdlib | `urllib.request` |
| `aiohttp` | Not stdlib, async unnecessary | `urllib.request` (sync) |
| `rich` | Not stdlib | Plain print + Unicode box chars |
| `blessed` | Not stdlib | Plain print + Unicode box chars |
| `curses` | Windows issues, overkill | print/input |
| `semver` | Not stdlib | Custom regex parser |
| `packaging` | Not stdlib | Custom version parser |

### Implementation Anti-Patterns

| Pattern | Problem | Better Approach |
|---------|---------|-----------------|
| `asyncio` for HTTP | Complexity for localhost API | Sync `urllib.request` |
| Threading for polling | Unnecessary complexity | Simple `time.sleep()` loop |
| `curses.wrapper()` | Windows compatibility issues | print/input with box chars |
| Raw ANSI escape codes | Terminal compatibility varies | Let terminal handle Unicode |
| Global Moonraker connection | State management issues | Fresh connection per request |

### Version Comparison Pitfalls

```python
# WRONG: String comparison fails for versions
"v0.12.0" > "v0.9.0"  # Returns False (string comparison)

# WRONG: Tuple of strings fails
tuple("v0.12.0".split(".")) > tuple("v0.9.0".split("."))  # Unpredictable

# CORRECT: Parse to numeric components
parse_klipper_version("v0.12.0") > parse_klipper_version("v0.9.0")  # True
```

---

## Integration Points with Existing Code

### Output Module Extension

The existing `Output` protocol in `output.py` should be extended:

```python
class Output(Protocol):
    # Existing methods...

    # New for v2.0 TUI
    def menu(self, title: str, options: list[str]) -> int:
        """Display menu and return 0-based selection index, or -1 for cancel."""
        ...
```

### Discovery Module Extension

Add to `discovery.py`:

```python
def is_klipper_device(filename: str) -> bool:
    """Check if device filename indicates Klipper firmware (not Katapult bootloader)."""
    lower = filename.lower()
    return "klipper_" in lower and "katapult_" not in lower
```

### Beacon Probe Exclusion

Beacon devices appear as `usb-Beacon_*` and should be excluded from flash targets:

```python
def is_flashable_device(filename: str) -> bool:
    """Check if device is a flashable MCU (not Beacon or other non-flashable device)."""
    lower = filename.lower()
    # Exclude Beacon probes
    if lower.startswith("usb-beacon_"):
        return False
    # Must be Klipper or Katapult device
    return "klipper_" in lower or "katapult_" in lower
```

---

## Confidence Assessment

| Component | Confidence | Rationale |
|-----------|------------|-----------|
| Moonraker API | HIGH | Verified from official docs at moonraker.readthedocs.io |
| urllib.request patterns | HIGH | Python stdlib, well-documented |
| TUI with print/input | HIGH | Proven pattern in existing v1.0 codebase |
| Version parsing | HIGH | Regex tested against real Klipper version strings |
| Post-flash verification | HIGH | Uses existing discovery module, proven polling |
| Installation script | HIGH | Standard Linux shell patterns |

---

## Sources

**Moonraker API:**
- [Moonraker Printer Administration API](https://moonraker.readthedocs.io/en/latest/external_api/printer/)
- [Moonraker Introduction](https://github.com/Arksine/moonraker/blob/master/docs/external_api/introduction.md)

**Klipper Status Reference:**
- [Klipper Status Reference - MCU Object](https://www.klipper3d.org/Status_Reference.html)

**Python stdlib:**
- [urllib.request documentation](https://docs.python.org/3/library/urllib.request.html)
- [shutil.which documentation](https://docs.python.org/3/library/shutil.html#shutil.which)
- [socket module documentation](https://docs.python.org/3/library/socket.html)

**Best Practices:**
- [Python Timeouts Guide - Better Stack](https://betterstack.com/community/guides/scaling-python/python-timeouts/)
- [Unicode Box Drawing Characters](https://pythonadventures.wordpress.com/2014/03/20/unicode-box-drawing-characters/)
- [TTY Detection - GeeksforGeeks](https://www.geeksforgeeks.org/python/python-os-isatty-method/)
