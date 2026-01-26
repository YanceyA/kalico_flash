# Phase 5: Moonraker Integration - Research

**Researched:** 2026-01-27
**Domain:** Moonraker API integration for print safety checks and version detection
**Confidence:** HIGH

## Summary

Phase 5 integrates kalico-flash with the Moonraker API to provide two safety features: blocking flash operations during active prints (SAFE-01 through SAFE-06) and displaying version information before flashing (VER-01 through VER-07). Both features gracefully degrade when Moonraker is unavailable.

All functionality is implementable using Python 3.9+ stdlib only. The `urllib.request` module provides HTTP client capabilities with timeout support. The existing hub-and-spoke architecture and Output protocol provide clean extension points for Moonraker integration without cross-module coupling.

**Primary recommendation:** Create a new `moonraker.py` module that encapsulates all API interactions. Integrate into `cmd_flash()` early in the workflow (before Phase 2: Config). This keeps Moonraker concerns isolated and maintains the existing module structure.

## Standard Stack

This phase uses only Python standard library, as required by project constraints.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| urllib.request | stdlib | HTTP client for Moonraker API | Built-in, supports timeout, no external deps |
| urllib.error | stdlib | HTTP error handling | URLError for connection failures, HTTPError for status codes |
| json | stdlib | JSON parsing | API responses are JSON format |
| subprocess | stdlib | Git version detection | Run `git describe` in Klipper directory |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| textwrap | stdlib | Format version table | 80-column alignment for table output |
| dataclasses | stdlib | PrintStatus/VersionInfo contracts | Structured data for cross-module exchange |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| urllib.request | requests library | requests is more ergonomic but adds external dependency |
| urllib.request | http.client | Lower-level, more boilerplate, same capabilities |
| JSON parsing | Manual string parsing | JSON module is robust, handles edge cases |

**Installation:**
No additional installation required - all stdlib.

## Architecture Patterns

### Recommended Project Structure

Add one new module; modify flash.py and models.py:

```
kalico-flash/
├── flash.py       # Add Moonraker check before flash phase
├── models.py      # Add PrintStatus, VersionInfo, MoonrakerConfig dataclasses
├── errors.py      # ERROR_TEMPLATES already has moonraker_unavailable, printer_busy
├── output.py      # Existing Output protocol sufficient (info, warn, confirm, error)
├── moonraker.py   # NEW: Moonraker API client module
└── [unchanged]    # registry.py, discovery.py, config.py, build.py, service.py, flasher.py
```

### Pattern 1: Isolated API Client Module

**What:** Single module encapsulating all Moonraker HTTP interactions.
**When to use:** Any external API integration with graceful degradation.
**Example:**
```python
# Source: Python urllib.request documentation
# moonraker.py - Moonraker API client

from __future__ import annotations
import json
import urllib.request
from urllib.error import URLError, HTTPError
from dataclasses import dataclass
from typing import Optional

MOONRAKER_URL = "http://localhost:7125"
TIMEOUT = 5  # seconds

@dataclass
class PrintStatus:
    """Current print job status from Moonraker."""
    state: str              # standby, printing, paused, complete, error, cancelled
    filename: Optional[str] # None if no file loaded
    progress: float         # 0.0 to 1.0

@dataclass
class VersionInfo:
    """Klipper version information."""
    host_version: str       # From git describe in klipper_dir
    mcu_versions: dict      # MCU name -> firmware version string

def get_print_status() -> Optional[PrintStatus]:
    """Query Moonraker for current print status.

    Returns:
        PrintStatus if successful, None if Moonraker unreachable.
    """
    try:
        url = f"{MOONRAKER_URL}/printer/objects/query?print_stats&virtual_sdcard"
        with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))

        status = data["result"]["status"]
        print_stats = status.get("print_stats", {})
        virtual_sdcard = status.get("virtual_sdcard", {})

        return PrintStatus(
            state=print_stats.get("state", "standby"),
            filename=print_stats.get("filename") or None,
            progress=virtual_sdcard.get("progress", 0.0),
        )
    except (URLError, HTTPError, json.JSONDecodeError, KeyError):
        return None
```

### Pattern 2: Git Describe for Host Version

**What:** Run `git describe --always --tags --dirty` in Klipper directory.
**When to use:** Getting host Klipper version without Moonraker.
**Example:**
```python
# Source: git-describe documentation
import subprocess
from pathlib import Path

def get_host_klipper_version(klipper_dir: str) -> Optional[str]:
    """Get Klipper version from git describe.

    Args:
        klipper_dir: Path to Klipper source directory.

    Returns:
        Version string like "v0.12.0-45-g7ce409d" or None if failed.
    """
    klipper_path = Path(klipper_dir).expanduser()
    try:
        result = subprocess.run(
            ["git", "describe", "--always", "--tags", "--dirty"],
            cwd=str(klipper_path),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None
```

### Pattern 3: MCU Version from Moonraker API

**What:** Query Moonraker for MCU firmware versions via printer objects.
**When to use:** Getting firmware version before flash for comparison.
**Example:**
```python
# Source: Moonraker API documentation
def get_mcu_versions() -> Optional[dict]:
    """Query Moonraker for all MCU firmware versions.

    Returns:
        Dict mapping MCU name to version string, None if unreachable.
        Example: {"mcu": "v0.12.0-45-g7ce409d", "nhk": "v0.12.0-45-g7ce409d"}
    """
    try:
        # First get list of MCU objects
        list_url = f"{MOONRAKER_URL}/printer/objects/list"
        with urllib.request.urlopen(list_url, timeout=TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))

        # Find all MCU objects (mcu, mcu linux, mcu nhk, etc.)
        mcu_objects = [obj for obj in data["result"]["objects"]
                       if obj.startswith("mcu")]

        if not mcu_objects:
            return None

        # Query all MCU objects for mcu_version
        query_params = "&".join(mcu_objects)
        query_url = f"{MOONRAKER_URL}/printer/objects/query?{query_params}"

        with urllib.request.urlopen(query_url, timeout=TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))

        versions = {}
        for mcu_name, mcu_data in data["result"]["status"].items():
            if "mcu_version" in mcu_data:
                # Normalize "mcu" to main, extract alias for others
                name = "main" if mcu_name == "mcu" else mcu_name.replace("mcu ", "")
                versions[name] = mcu_data["mcu_version"]

        return versions if versions else None

    except (URLError, HTTPError, json.JSONDecodeError, KeyError):
        return None
```

### Pattern 4: Version Comparison Logic

**What:** Compare git describe versions to detect outdated MCU firmware.
**When to use:** VER-03 requirement for version mismatch indication.
**Example:**
```python
# Source: Git describe format documentation
def parse_git_describe(version: str) -> tuple:
    """Parse git describe output into components.

    Args:
        version: String like "v0.12.0-45-g7ce409d" or "v0.12.0" or "7ce409d"

    Returns:
        Tuple of (tag, commits_ahead, commit_hash) where commits_ahead
        is 0 if version is exactly a tag.
    """
    # Handle dirty suffix
    version = version.rstrip("-dirty")

    parts = version.split("-")
    if len(parts) >= 3 and parts[-1].startswith("g"):
        # Format: tag-N-gHASH
        tag = "-".join(parts[:-2])
        commits = int(parts[-2])
        commit_hash = parts[-1][1:]  # Remove 'g' prefix
        return (tag, commits, commit_hash)
    elif len(parts) == 1:
        # Format: exact tag (v0.12.0) or bare hash (7ce409d)
        if parts[0].startswith("v"):
            return (parts[0], 0, "")
        else:
            return ("", 0, parts[0])
    else:
        # Unknown format, return as-is
        return (version, 0, "")

def is_mcu_outdated(host_version: str, mcu_version: str) -> bool:
    """Check if MCU firmware is behind host Klipper.

    Returns True if MCU appears to be behind the host version.
    Comparison is informational only - does not block flash.
    """
    host_tag, host_commits, host_hash = parse_git_describe(host_version)
    mcu_tag, mcu_commits, mcu_hash = parse_git_describe(mcu_version)

    # If same tag and same commit hash (if both present), they match
    if host_hash and mcu_hash:
        return host_hash != mcu_hash

    # If tags differ, MCU may be outdated
    if host_tag != mcu_tag:
        return True

    # Same tag, but host has commits ahead
    if host_commits > mcu_commits:
        return True

    return False
```

### Pattern 5: Graceful Degradation with Warning

**What:** Warn user and require confirmation when Moonraker unavailable.
**When to use:** SAFE-05 and VER-05 requirements.
**Example:**
```python
# Integration in cmd_flash() in flash.py

def cmd_flash(registry, device_key, out, skip_menuconfig: bool = False) -> int:
    # ... existing discovery code ...

    # === New: Moonraker Safety Check ===
    from moonraker import get_print_status, get_mcu_versions, get_host_klipper_version

    klipper_dir = data.global_config.klipper_dir

    # Check print status
    print_status = get_print_status()
    if print_status is None:
        # Moonraker unreachable - warn and confirm
        out.warn("Moonraker unreachable - print status and version check unavailable")
        if not out.confirm("Continue without safety checks?", default=False):
            out.phase("Flash", "Cancelled")
            return 0
    elif print_status.state in ("printing", "paused"):
        # Block flash during active print
        progress_pct = int(print_status.progress * 100)
        template = ERROR_TEMPLATES["printer_busy"]
        out.error_with_recovery(
            template["error_type"],
            f"Print in progress: {print_status.filename} ({progress_pct}%)",
            recovery=template["recovery_template"],
        )
        return 1

    # Show version info (informational only)
    host_version = get_host_klipper_version(klipper_dir)
    mcu_versions = get_mcu_versions()

    if host_version and mcu_versions:
        _display_version_table(out, host_version, mcu_versions, device_key)
    elif host_version:
        out.phase("Version", f"Host Klipper: {host_version}")
        out.warn("MCU version unavailable (MCU may be offline)")

    # ... continue with existing config/build/flash phases ...
```

### Pattern 6: Version Table Display

**What:** Format version comparison as readable table.
**When to use:** VER-01 through VER-04 requirements.
**Example:**
```python
# Source: Project decision - table format for version display

def _display_version_table(out, host_version: str, mcu_versions: dict, target_mcu: str) -> None:
    """Display version comparison table.

    Shows host Klipper version and all MCU firmware versions.
    Highlights the target MCU and indicates if update is needed.
    """
    out.phase("Version", "Klipper version check")
    out.info("", f"  Host Klipper:    {host_version}")

    for mcu_name, mcu_version in sorted(mcu_versions.items()):
        marker = " *" if mcu_name == target_mcu else "  "
        out.info("", f"{marker}MCU {mcu_name:12s} {mcu_version}")

    # Check if target MCU is outdated
    target_version = mcu_versions.get(target_mcu)
    if target_version and is_mcu_outdated(host_version, target_version):
        out.warn("MCU firmware is behind host Klipper - update recommended")
```

### Anti-Patterns to Avoid

- **Blocking on unreachable Moonraker:** Never block the flash workflow when Moonraker is down. Always warn and offer continue option.
- **Hardcoded MCU names:** Don't assume MCU names. Query Moonraker for available MCUs dynamically.
- **Silent version mismatch:** Always show version info when available. Never silently proceed without showing versions.
- **Retrying failed connections:** Per CONTEXT.md, one attempt with 5-second timeout, then warn. No retry logic.
- **Force-override flag for print blocking:** Per CONTEXT.md, no flag to bypass print blocking. User must cancel/complete print first.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP GET with timeout | Raw socket | `urllib.request.urlopen(timeout=5)` | Handles redirects, encoding, headers |
| JSON parsing | Manual string parsing | `json.loads()` | Handles escaping, unicode, nested objects |
| Git version detection | Parse .git files | `git describe` subprocess | Git handles edge cases (detached HEAD, tags) |
| Version comparison | Full semver parsing | Simple git describe comparison | Klipper uses git describe format, not semver |

**Key insight:** The `urllib.request` module is sufficient for simple GET requests with JSON responses. Don't add `requests` library dependency just for cleaner syntax.

## Common Pitfalls

### Pitfall 1: URLError vs HTTPError Handling

**What goes wrong:** Catching only HTTPError misses connection refused/timeout errors.
**Why it happens:** HTTPError is for HTTP status codes (4xx/5xx), URLError is for network failures.
**How to avoid:** Always catch URLError first (it's the parent), then HTTPError if you need status-specific handling.
**Warning signs:** Unhandled exception when Moonraker is stopped or unreachable.

### Pitfall 2: Moonraker API Response Nesting

**What goes wrong:** Accessing `data["print_stats"]` instead of `data["result"]["status"]["print_stats"]`.
**Why it happens:** Moonraker wraps all responses in a `result` object.
**How to avoid:** Always navigate through `data["result"]["status"]` for object query responses.
**Warning signs:** KeyError on seemingly valid responses.

### Pitfall 3: MCU Object Naming Convention

**What goes wrong:** Assuming MCU is always named "mcu" when it could be "mcu linux" or "mcu nhk".
**Why it happens:** Additional MCUs use "[mcu alias]" config sections which become "mcu alias" objects.
**How to avoid:** Query `/printer/objects/list` first to discover all MCU objects, then query each.
**Warning signs:** Missing firmware version for toolhead or secondary MCUs.

### Pitfall 4: Print Progress Units

**What goes wrong:** Displaying progress as decimal (0.45) instead of percentage (45%).
**Why it happens:** `virtual_sdcard.progress` is 0.0-1.0, not 0-100.
**How to avoid:** Multiply by 100 and cast to int for display: `int(progress * 100)`.
**Warning signs:** User sees "Print in progress: file.gcode (0.45%)" instead of "(45%)".

### Pitfall 5: Git Describe in Wrong Directory

**What goes wrong:** Running `git describe` in kalico-flash directory instead of Klipper directory.
**Why it happens:** Forgetting to pass `cwd=klipper_dir` to subprocess.run.
**How to avoid:** Always specify `cwd=str(Path(klipper_dir).expanduser())` for git commands.
**Warning signs:** Version shows kalico-flash version or "fatal: not a git repository".

### Pitfall 6: Blocking on Version Check Failure

**What goes wrong:** Treating MCU version lookup failure as an error that blocks flash.
**Why it happens:** Applying same logic as print status check to version check.
**How to avoid:** Per requirements, version check is informational only. Warn but proceed if unavailable.
**Warning signs:** User can't flash because MCU is offline (which is why they want to flash!).

## Moonraker API Reference

### Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/printer/objects/query?print_stats&virtual_sdcard` | GET | Print status and progress |
| `/printer/objects/list` | GET | Discover all MCU objects |
| `/printer/objects/query?mcu&mcu%20nhk` | GET | MCU firmware versions |
| `/printer/info` | GET | Host Klipper version (alternative to git) |

### print_stats.state Values

| State | Meaning | Flash Allowed |
|-------|---------|---------------|
| standby | Idle, no print | Yes |
| printing | Print in progress | NO - Block |
| paused | Print paused by user | NO - Block |
| complete | Last print finished | Yes |
| error | Last print errored | Yes |
| cancelled | Last print cancelled | Yes |

### MCU Object Response Structure

```json
{
  "result": {
    "eventtime": 1234567.89,
    "status": {
      "mcu": {
        "mcu_version": "v0.12.0-45-g7ce409d",
        "mcu_build_versions": "gcc: ...",
        "mcu_constants": {"MCU": "stm32h723xx", ...}
      },
      "mcu nhk": {
        "mcu_version": "v0.12.0-45-g7ce409d",
        ...
      }
    }
  }
}
```

## Integration Points in Existing Code

### cmd_flash() Modification

Insert Moonraker checks between Phase 1 (Discovery) and Phase 2 (Config):

```
Current flow:
  Phase 1: Discovery -> Phase 2: Config -> Phase 3: Build -> Phase 4: Flash

New flow:
  Phase 1: Discovery -> NEW: Moonraker Check -> Phase 2: Config -> ...
```

The Moonraker check happens AFTER device selection but BEFORE any build actions. This allows the user to see what device will be flashed before the safety check potentially blocks or prompts.

### Output Protocol Sufficiency

The existing Output protocol has all methods needed:
- `info()` - Version table display
- `warn()` - Moonraker unreachable, version mismatch warnings
- `error_with_recovery()` - Print blocking error
- `confirm()` - "Continue without safety checks?" prompt
- `phase()` - Phase labels

No changes to output.py required.

### ERROR_TEMPLATES Updates

The errors.py file already has templates for `moonraker_unavailable` and `printer_busy`. Review and update wording per CONTEXT.md decisions:

- `printer_busy`: "Printer is busy - cannot flash during active print"
- `moonraker_unavailable`: Update recovery steps for Phase 5 context

## Code Examples

### Complete Moonraker Module

```python
# moonraker.py - Moonraker API client for kalico-flash
"""Moonraker API client for print status and version detection.

Provides graceful degradation when Moonraker is unavailable - all public
functions return None on failure instead of raising exceptions.
"""
from __future__ import annotations

import json
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.error import URLError, HTTPError

# Connection settings (per CONTEXT.md: no custom URL support)
MOONRAKER_URL = "http://localhost:7125"
TIMEOUT = 5  # seconds


@dataclass
class PrintStatus:
    """Current print job status from Moonraker."""
    state: str              # standby, printing, paused, complete, error, cancelled
    filename: Optional[str] # None if no file loaded
    progress: float         # 0.0 to 1.0


def get_print_status() -> Optional[PrintStatus]:
    """Query Moonraker for current print status.

    Returns:
        PrintStatus if successful, None if Moonraker unreachable.
    """
    try:
        url = f"{MOONRAKER_URL}/printer/objects/query?print_stats&virtual_sdcard"
        with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))

        status = data["result"]["status"]
        print_stats = status.get("print_stats", {})
        virtual_sdcard = status.get("virtual_sdcard", {})

        return PrintStatus(
            state=print_stats.get("state", "standby"),
            filename=print_stats.get("filename") or None,
            progress=virtual_sdcard.get("progress", 0.0),
        )
    except (URLError, HTTPError, json.JSONDecodeError, KeyError, TimeoutError):
        return None


def get_mcu_versions() -> Optional[dict]:
    """Query Moonraker for all MCU firmware versions.

    Returns:
        Dict mapping MCU name to version string, None if unreachable.
        Example: {"main": "v0.12.0-45-g7ce409d", "nhk": "v0.12.0-45-g7ce409d"}
    """
    try:
        # Get list of all printer objects
        list_url = f"{MOONRAKER_URL}/printer/objects/list"
        with urllib.request.urlopen(list_url, timeout=TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))

        # Find MCU objects
        mcu_objects = [obj for obj in data["result"]["objects"]
                       if obj == "mcu" or obj.startswith("mcu ")]

        if not mcu_objects:
            return None

        # Query MCU objects
        query_params = "&".join(obj.replace(" ", "%20") for obj in mcu_objects)
        query_url = f"{MOONRAKER_URL}/printer/objects/query?{query_params}"

        with urllib.request.urlopen(query_url, timeout=TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))

        versions = {}
        for mcu_name, mcu_data in data["result"]["status"].items():
            if "mcu_version" in mcu_data:
                # Normalize: "mcu" -> "main", "mcu nhk" -> "nhk"
                name = "main" if mcu_name == "mcu" else mcu_name[4:]  # Strip "mcu "
                versions[name] = mcu_data["mcu_version"]

        return versions if versions else None

    except (URLError, HTTPError, json.JSONDecodeError, KeyError, TimeoutError):
        return None


def get_host_klipper_version(klipper_dir: str) -> Optional[str]:
    """Get host Klipper version via git describe.

    Args:
        klipper_dir: Path to Klipper source directory.

    Returns:
        Version string like "v0.12.0-45-g7ce409d" or None if failed.
    """
    klipper_path = Path(klipper_dir).expanduser()
    try:
        result = subprocess.run(
            ["git", "describe", "--always", "--tags", "--dirty"],
            cwd=str(klipper_path),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def is_mcu_outdated(host_version: str, mcu_version: str) -> bool:
    """Check if MCU firmware appears behind host Klipper.

    Comparison is informational only - never blocks flash.

    Returns:
        True if MCU version differs from host version.
    """
    # Simple comparison: if versions differ, consider outdated
    # This handles the common case where MCU should match host exactly
    return host_version.strip() != mcu_version.strip()
```

### Integration in cmd_flash()

```python
# In flash.py cmd_flash() after device selection, before config phase

def cmd_flash(registry, device_key, out, skip_menuconfig: bool = False) -> int:
    # ... existing Phase 1: Discovery code ...

    out.phase("Discovery", f"Target: {entry.name} ({entry.mcu}) at {device_path}")

    # === NEW: Moonraker Safety Check ===
    from moonraker import get_print_status, get_mcu_versions, get_host_klipper_version
    from errors import ERROR_TEMPLATES

    # Check print status before proceeding
    print_status = get_print_status()

    if print_status is None:
        # Moonraker unreachable
        out.warn("Moonraker unreachable - print status and version check unavailable")
        if not out.confirm("Continue without safety checks?", default=False):
            out.phase("Flash", "Cancelled")
            return 0
    elif print_status.state in ("printing", "paused"):
        # Block flash during active print
        progress_pct = int(print_status.progress * 100)
        filename = print_status.filename or "unknown"
        out.error_with_recovery(
            "Printer busy",
            f"Print in progress: {filename} ({progress_pct}%)",
            recovery=(
                "1. Wait for current print to complete\n"
                "2. Or cancel print in Fluidd/Mainsail dashboard\n"
                "3. Then re-run flash command"
            ),
        )
        return 1
    else:
        out.phase("Safety", f"Printer state: {print_status.state} - OK to flash")

    # Version display (informational only)
    host_version = get_host_klipper_version(data.global_config.klipper_dir)
    mcu_versions = get_mcu_versions()

    if host_version:
        out.phase("Version", f"Host Klipper: {host_version}")

        if mcu_versions:
            # Find MCU name for target device
            # Map device MCU type to Moonraker MCU object name
            target_mcu = _find_target_mcu(entry.mcu, mcu_versions)

            for mcu_name, mcu_version in sorted(mcu_versions.items()):
                marker = "*" if mcu_name == target_mcu else " "
                out.info("Version", f"  [{marker}] MCU {mcu_name}: {mcu_version}")

            if target_mcu and target_mcu in mcu_versions:
                if is_mcu_outdated(host_version, mcu_versions[target_mcu]):
                    out.warn("MCU firmware is behind host Klipper - update recommended")
        else:
            out.warn("MCU versions unavailable (Klipper may not be running)")

    # === Continue with existing Phase 2: Config ===
    out.phase("Config", f"Loading config for {entry.name}...")
    # ... rest of existing code ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No print check | Moonraker API check | Phase 5 | Prevents flash during print |
| No version display | Git describe + API | Phase 5 | User sees version mismatch |
| External requests lib | stdlib urllib | Always | No external dependencies |

**Deprecated/outdated:**
- requests library: Would simplify HTTP code but adds external dependency
- Moonraker WebSocket: Overkill for simple one-shot queries

## Open Questions

Things that couldn't be fully resolved:

1. **MCU name mapping to device registry**
   - What we know: Moonraker reports MCUs as "mcu", "mcu nhk", "mcu linux"
   - What's unclear: How to map registered device MCU type (e.g., "stm32h723") to Moonraker MCU name
   - Recommendation: Use MCU constants (mcu_constants.MCU) from Moonraker to match against registered device MCU type

2. **Multiple MCU version display order**
   - What we know: Show all MCUs, highlight target
   - What's unclear: Should "main" always be first, or alphabetical?
   - Recommendation: Alphabetical by MCU name, with target marked with asterisk

3. **Version comparison edge cases**
   - What we know: Simple string comparison catches most cases
   - What's unclear: What if host is dirty (-dirty suffix) but MCU is not?
   - Recommendation: Treat any difference as "outdated" - user should rebuild MCU to match

## Sources

### Primary (HIGH confidence)
- [Moonraker API Documentation](https://moonraker.readthedocs.io/en/latest/external_api/printer/) - print_stats, objects query
- [Moonraker Printer Objects](https://moonraker.readthedocs.io/en/latest/printer_objects/) - mcu object structure
- [Python urllib.request](https://docs.python.org/3/library/urllib.request.html) - HTTP client
- [git-describe documentation](https://git-scm.com/docs/git-describe) - version format

### Secondary (MEDIUM confidence)
- Existing codebase (flash.py, errors.py, output.py) - integration patterns
- Phase 4 research document - error message format, Output protocol usage

### Tertiary (LOW confidence)
- None - all API behavior verified with official documentation

## Metadata

**Confidence breakdown:**
- Moonraker API: HIGH - official documentation, widely used
- urllib.request: HIGH - stdlib, well-documented
- Version comparison: MEDIUM - simple approach covers common cases
- MCU name mapping: MEDIUM - may need refinement during implementation

**Research date:** 2026-01-27
**Valid until:** 90 days (stable Moonraker API, no external dependencies)
