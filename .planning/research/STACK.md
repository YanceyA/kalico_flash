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

## v2.1 TUI Panel Redesign Stack

**Added:** 2026-01-29
**Focus:** Truecolor panels, two-column layouts, batch flash with staggered output

### 1. Truecolor (24-bit RGB) ANSI Escape Codes

**Foreground:**
```python
f"\033[38;2;{r};{g};{b}m"   # or \x1b[38;2;R;G;Bm
```

**Background:**
```python
f"\033[48;2;{r};{g};{b}m"
```

**Reset:** `\033[0m`

**Combined with modifiers:**
```python
f"\033[1;38;2;{r};{g};{b}m"   # bold + truecolor foreground
f"\033[2;38;2;{r};{g};{b}m"   # dim + truecolor foreground
```

**Approach:** Extend the existing `Theme` dataclass in `theme.py` to use truecolor strings instead of ANSI 16 codes. The `zen_mockup.py` already demonstrates the exact palette and escape format. Migrate those color constants into `theme.py`.

The existing `_enable_windows_vt_mode()` already enables VT processing on Windows, which includes truecolor support (Windows Terminal, VS Code terminal). The existing `NO_COLOR` / `FORCE_COLOR` / TTY detection chain handles fallback.

**Truecolor detection:**
```python
def supports_truecolor() -> bool:
    """Check COLORTERM env var -- de facto standard for truecolor detection."""
    colorterm = os.environ.get("COLORTERM", "").lower()
    return colorterm in ("truecolor", "24bit")
```

If truecolor is not detected, fall back to the existing ANSI 16 palette. This provides a three-tier theme: truecolor > ANSI 16 > no-color.

**Confidence:** HIGH -- standard ANSI/VT100 escape sequences. Windows Terminal, VS Code terminal, iTerm2, kitty, alacritty, and all modern SSH terminal emulators support truecolor. Raspberry Pi over SSH inherits the client terminal's capabilities.

### 2. Rounded Box Drawing with Unicode

**Characters needed:**
```python
ROUNDED_BOX = {
    "tl": "\u256d",  # rounded top-left
    "tr": "\u256e",  # rounded top-right
    "bl": "\u2570",  # rounded bottom-left
    "br": "\u256f",  # rounded bottom-right
    "h":  "\u2500",  # horizontal line (same as current)
    "v":  "\u2502",  # vertical line (same as current)
}
```

Add as third option alongside existing `UNICODE_BOX` and `ASCII_BOX` in `tui.py`. Use rounded by default when Unicode is supported.

**Additional box-drawing chars for separators (from mockup):**
```python
DOTTED_H = "\u2504"  # dotted horizontal line (section dividers)
```

**Confidence:** HIGH -- standard Unicode box-drawing characters (U+256D-256F), present in virtually all monospace fonts.

### 3. Terminal Width Detection

**Use `shutil.get_terminal_size()` -- not `os.get_terminal_size()`.**

```python
import shutil
width, height = shutil.get_terminal_size(fallback=(80, 24))
```

**Why `shutil` over `os`:**
- `shutil.get_terminal_size()` accepts a `fallback` parameter
- `os.get_terminal_size()` raises `OSError` if no terminal (piped output)
- `shutil` version handles edge cases (non-TTY, redirected) gracefully

**Usage pattern for responsive panels:**
```python
def get_panel_width() -> int:
    term_width = shutil.get_terminal_size((80, 24)).columns
    return min(term_width - 2, 76)  # cap at 76 to avoid stretched panels
```

**Confidence:** HIGH -- stdlib since Python 3.3.

### 4. ANSI-Aware String Length (Critical Utility)

**This is the single most important utility for panel rendering.** ANSI escape codes are invisible on screen but count in `len()`. Every padding/alignment calculation must use this instead of `len()`:

```python
import re
_ANSI_RE = re.compile(r"\033\[[0-9;]*m")

def visible_len(s: str) -> int:
    """Length of string as displayed, stripping ANSI escapes."""
    return len(_ANSI_RE.sub("", s))

def visible_ljust(s: str, width: int) -> str:
    """Left-justify string to visible width, ANSI-aware."""
    pad = width - visible_len(s)
    return s + " " * max(0, pad)
```

The existing `_render_menu()` in `tui.py` already has a mild version of this problem -- it tracks plain text width separately from styled title text. The truecolor upgrade makes ANSI-aware length critical everywhere.

**Confidence:** HIGH -- `re` is stdlib, pattern is well-established.

### 5. Two-Column Action Layout

**Technique:** Pure string formatting with calculated column widths.

```python
def render_two_column(
    left: list[str], right: list[str], col_width: int, inner_width: int
) -> list[str]:
    """Render two columns of action items side by side."""
    lines = []
    for i in range(max(len(left), len(right))):
        l = left[i] if i < len(left) else ""
        r = right[i] if i < len(right) else ""
        lines.append(f"   {visible_ljust(l, col_width)}   {r}")
    return lines
```

Use `visible_ljust()` from section 4 for alignment. The mockup shows this pattern:
```
   1 > Refresh Devices          5 > Flash All Registered
   2 > Add Device               6 > Config
   3 > Remove Device            7 > Exit
   4 > Flash Device
```

Split `inner_width // 2` for each column. Left column items padded with `visible_ljust()`.

**Confidence:** HIGH -- string formatting, no special modules.

### 6. Keypress Detection for Countdown Timer

**Unix (Raspberry Pi -- primary target):**
```python
import sys, select, tty, termios

def wait_with_keypress(seconds: float) -> bool:
    """Wait up to seconds, return True if key pressed."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)  # char-at-a-time, no echo
        ready, _, _ = select.select([sys.stdin], [], [], seconds)
        if ready:
            sys.stdin.read(1)  # consume the keypress
            return True
        return False
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
```

**Windows (dev environment):**
```python
import msvcrt, time

def wait_with_keypress_win(seconds: float) -> bool:
    """Wait up to seconds, return True if key pressed."""
    start = time.monotonic()
    while time.monotonic() - start < seconds:
        if msvcrt.kbhit():
            msvcrt.getch()
            return True
        time.sleep(0.1)
    return False
```

**Cross-platform wrapper:**
```python
def wait_or_keypress(seconds: float) -> bool:
    if sys.platform == "win32":
        return wait_with_keypress_win(seconds)
    else:
        return wait_with_keypress(seconds)
```

**Critical:** Always wrap Unix version in try/finally to restore terminal settings. If left in cbreak mode after a crash, the user's shell session breaks.

**Confidence:** HIGH -- `select`, `tty`, `termios` (Unix) and `msvcrt` (Windows) are all stdlib.

### 7. Countdown Timer with In-Place Update

```python
def countdown_with_interrupt(seconds: int, message: str) -> bool:
    """Show countdown, return True if interrupted by keypress."""
    for remaining in range(seconds, 0, -1):
        sys.stdout.write(f"\r  {message} {remaining}s... (press any key)  ")
        sys.stdout.flush()
        if _check_keypress(timeout=1.0):
            sys.stdout.write("\r" + " " * 60 + "\r")
            return True
    sys.stdout.write("\r" + " " * 60 + "\r")
    return False
```

Use `\r` (carriage return) for in-place updates. No cursor movement escape codes needed.

### 8. Batch Flash Sequential Output

No threading or async needed. Flash operations are sequential (stop Klipper -> flash device 1 -> flash device 2 -> restart Klipper). Use the existing `service.py` context manager once, then iterate.

```python
for i, device in enumerate(devices, 1):
    print(f"  {SUBTLE}{'─' * 50} {LABEL}{i}/{total} {device.name}{RST}")
    # build, flash, verify -- reuse existing functions
```

Between-device delay uses the countdown timer from section 7.

**Confidence:** HIGH -- straightforward sequential loop with existing flash infrastructure.

### v2.1 Stdlib Modules Summary

| Module | Purpose | Platform |
|--------|---------|----------|
| `shutil` | `get_terminal_size()` | All |
| `re` | ANSI escape stripping for `visible_len()` | All |
| `os` | Env vars (`NO_COLOR`, `COLORTERM`, `LANG`) | All |
| `sys` | Platform detection, stdin/stdout | All |
| `select` | Non-blocking stdin poll | Unix only |
| `tty` | Set cbreak mode | Unix only |
| `termios` | Save/restore terminal settings | Unix only |
| `msvcrt` | Keypress detection | Windows only |
| `time` | `monotonic()` for countdown | All |

All Python 3.9+ stdlib. Zero pip dependencies.

### v2.1 Key Implementation Decisions

1. **Extend existing `Theme` dataclass** -- add truecolor fields, keep ANSI 16 as fallback via `supports_truecolor()` check
2. **Add `visible_len()` utility early** -- every panel rendering function depends on it
3. **Use `shutil.get_terminal_size()`** -- never `os.get_terminal_size()`
4. **Platform-switch for keypress** -- `sys.platform == "win32"` gate
5. **Sequential batch flash** -- no threading, one context manager wrapping all devices
6. **Rounded box as default** -- falls back to straight Unicode box, then ASCII
7. **Three-tier theme** -- truecolor > ANSI 16 > no-color

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

## Anti-Patterns: What NOT to Use

### External Dependencies (FORBIDDEN)

| Library | Why Avoid | Alternative |
|---------|-----------|-------------|
| `requests` | Not stdlib | `urllib.request` |
| `httpx` | Not stdlib | `urllib.request` |
| `aiohttp` | Not stdlib, async unnecessary | `urllib.request` (sync) |
| `rich` | Not stdlib | Plain print + Unicode box chars + truecolor ANSI |
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
| `len()` on ANSI strings | Wrong padding, broken alignment | `visible_len()` with regex strip |
| Global Moonraker connection | State management issues | Fresh connection per request |
| Threading for batch flash | Race conditions with service mgmt | Sequential loop, single context manager |

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
| Truecolor ANSI escapes | HIGH | ECMA-48 standard, validated in zen_mockup.py |
| Rounded box drawing | HIGH | Standard Unicode block, tested in mockup |
| Terminal width detection | HIGH | `shutil.get_terminal_size()` stdlib |
| ANSI-aware string length | HIGH | `re` stdlib, well-established pattern |
| Two-column layout | HIGH | String formatting, no special modules |
| Keypress detection | HIGH | `termios`/`tty`/`select` (Unix), `msvcrt` (Windows) stdlib |
| Countdown timer | HIGH | `time.monotonic()` + `\r` carriage return |
| Batch flash | HIGH | Sequential loop with existing infrastructure |
| Moonraker API | HIGH | Verified from official docs at moonraker.readthedocs.io |
| Version parsing | HIGH | Regex tested against real Klipper version strings |
| Post-flash verification | HIGH | Uses existing discovery module, proven polling |
| Installation script | HIGH | Standard Linux shell patterns |

---

## Sources

**Truecolor/ANSI:**
- ECMA-48 standard (ANSI escape code specification)
- Existing `zen_mockup.py` in `.working/UI-working/` (validates truecolor rendering)
- Existing `theme.py` (validates VT mode enable on Windows)

**Python stdlib:**
- [shutil.get_terminal_size](https://docs.python.org/3/library/shutil.html#shutil.get_terminal_size)
- [termios module](https://docs.python.org/3/library/termios.html)
- [tty module](https://docs.python.org/3/library/tty.html)
- [select module](https://docs.python.org/3/library/select.html)
- [msvcrt module](https://docs.python.org/3/library/msvcrt.html)
- [urllib.request documentation](https://docs.python.org/3/library/urllib.request.html)

**Moonraker API:**
- [Moonraker Printer Administration API](https://moonraker.readthedocs.io/en/latest/external_api/printer/)

**Unicode:**
- [Unicode Box Drawing block (U+2500-U+257F)](https://www.unicode.org/charts/PDF/U2500.pdf)
