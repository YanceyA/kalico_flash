# Phase 2: Build & Config Pipeline - Research

**Researched:** 2026-01-25
**Domain:** Klipper firmware configuration (Kconfig), Python subprocess management, file system operations
**Confidence:** HIGH

## Summary

Phase 2 implements the firmware configuration and build pipeline. The core technical challenges are:

1. **Config management**: Klipper uses the Linux Kconfig system (`make menuconfig`). The `.config` file is a simple key=value format with `CONFIG_MCU` identifying the microcontroller type (e.g., `CONFIG_MCU="stm32h723xx"`).

2. **Interactive TUI passthrough**: `make menuconfig` is an ncurses application that requires a TTY. Python's `subprocess.run()` with default (inherited) stdio handles this correctly - no PIPE redirection.

3. **Real-time build output**: `make` output should stream in real-time. Using `subprocess.run()` with inherited stdio achieves this without buffering issues.

4. **Atomic file operations**: The existing `registry.py` already implements the correct pattern (write to temp file, fsync, rename). This same pattern applies to config file caching.

**Primary recommendation:** Use `subprocess.run()` with inherited stdio for both menuconfig (interactive TUI) and make (streaming output). Detect config save via mtime comparison. Parse `CONFIG_MCU` from .config using simple line parsing.

## Standard Stack

The established libraries/tools for this domain:

### Core (Python 3.9+ stdlib)
| Library | Module | Purpose | Why Standard |
|---------|--------|---------|--------------|
| subprocess | subprocess | Process execution, TUI passthrough, build invocation | Direct control over stdio inheritance |
| pathlib | pathlib | Path manipulation, stat() for mtime | Cross-platform, Pythonic API |
| os | os | Environment variables, atomic rename | XDG_CONFIG_HOME, os.replace() |
| tempfile | tempfile | Atomic write pattern | NamedTemporaryFile for safe writes |
| re | re | Config file parsing | Simple regex for key=value extraction |

### Supporting
| Library | Module | Purpose | When to Use |
|---------|--------|---------|-------------|
| shutil | shutil | File copying | Copying .config to/from klipper directory |
| time | time | Build duration measurement | Success message with elapsed time |
| multiprocessing | multiprocessing | CPU count | `make -j$(nproc)` equivalent |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| subprocess.run | subprocess.Popen | run() simpler when not capturing output; Popen for fine-grained control |
| os.replace | shutil.move | os.replace is atomic; shutil.move is not guaranteed atomic |
| regex parsing | configparser | .config is not INI format (no sections); regex is simpler |

**No external dependencies required** - all functionality available in Python 3.9+ stdlib.

## Architecture Patterns

### Recommended Module Structure
```
klipper-flash/
├── config.py          # Config file management (cache, MCU parsing)
├── build.py           # Build orchestration (menuconfig, make)
├── errors.py          # Add ConfigError, BuildError (existing file)
├── models.py          # Add BuildResult dataclass (existing file)
└── ... (existing modules)
```

### Pattern 1: Subprocess with Inherited stdio (TUI Passthrough)
**What:** Run interactive ncurses application (menuconfig) with full terminal control
**When to use:** Any interactive subprocess that needs terminal access
**Example:**
```python
# Source: Python subprocess documentation
import subprocess

def run_menuconfig(klipper_dir: str, config_path: str) -> int:
    """Run menuconfig with custom config file."""
    env = os.environ.copy()
    env["KCONFIG_CONFIG"] = config_path

    result = subprocess.run(
        ["make", "menuconfig"],
        cwd=klipper_dir,
        env=env,
        # No stdin/stdout/stderr args = inherited from parent
    )
    return result.returncode
```

### Pattern 2: Streaming Build Output
**What:** Run make with real-time output to terminal
**When to use:** Long-running build commands where user wants progress feedback
**Example:**
```python
# Source: Python subprocess documentation
import subprocess
import multiprocessing

def run_build(klipper_dir: str) -> int:
    """Run make clean && make -j$(nproc) with streaming output."""
    nproc = multiprocessing.cpu_count()

    # Clean first
    clean_result = subprocess.run(
        ["make", "clean"],
        cwd=klipper_dir,
        # Inherited stdio = output streams to terminal
    )
    if clean_result.returncode != 0:
        return clean_result.returncode

    # Build with parallel jobs
    build_result = subprocess.run(
        ["make", f"-j{nproc}"],
        cwd=klipper_dir,
    )
    return build_result.returncode
```

### Pattern 3: Atomic File Write with Temp File
**What:** Write file atomically to prevent corruption on power loss
**When to use:** Any file that must be consistent (config cache, registry)
**Example:**
```python
# Source: Existing registry.py implementation
import os
import tempfile
import shutil

def atomic_copy(src: str, dst: str) -> None:
    """Copy file atomically: copy to temp, fsync, rename."""
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
```

### Pattern 4: XDG Config Directory Resolution
**What:** Locate user config directory per XDG Base Directory Specification
**When to use:** Storing per-user configuration files
**Example:**
```python
# Source: XDG Base Directory Specification
import os
from pathlib import Path

def get_config_dir() -> Path:
    """Get XDG config directory for klipper-flash."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config and os.path.isabs(xdg_config):
        base = Path(xdg_config)
    else:
        base = Path.home() / ".config"
    return base / "klipper-flash"
```

### Pattern 5: Config File Parsing for MCU Type
**What:** Extract CONFIG_MCU value from Kconfig .config file
**When to use:** Validating MCU type before build
**Example:**
```python
# Source: Klipper Kconfig structure analysis
import re
from pathlib import Path
from typing import Optional

def parse_mcu_from_config(config_path: str) -> Optional[str]:
    """Extract MCU type from .config file.

    Returns e.g., 'stm32h723xx', 'rp2040', or None if not found.
    """
    path = Path(config_path)
    if not path.exists():
        return None

    content = path.read_text()
    # Match: CONFIG_MCU="stm32h723xx"
    match = re.search(r'^CONFIG_MCU="([^"]+)"', content, re.MULTILINE)
    return match.group(1) if match else None
```

### Anti-Patterns to Avoid
- **Using subprocess.PIPE for menuconfig:** ncurses TUI fails without real TTY - use inherited stdio
- **Using check_output() for build:** Blocks until completion, no real-time output - use run() with inherited stdio
- **Parsing .config with configparser:** Not INI format (no sections, uses # comments) - use regex
- **Using shutil.move for atomic writes:** Not guaranteed atomic on all filesystems - use temp file + os.replace
- **Hardcoding ~/.config path:** Ignores XDG_CONFIG_HOME environment variable - check env first

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parallel job count | `os.cpu_count() or 4` | `multiprocessing.cpu_count()` | Same result, more semantic |
| Path joining | String concatenation | `pathlib.Path / operator` | Cross-platform path separators |
| Home directory | `os.environ['HOME']` | `Path.home()` | Cross-platform (Windows has no $HOME) |
| Atomic rename | `os.rename()` | `os.replace()` | replace() is atomic even if target exists |
| File mtime | Manual stat parsing | `Path.stat().st_mtime` | Clean API, handles errors |

**Key insight:** The existing codebase (registry.py) already implements atomic write correctly. Reuse that pattern for config file caching.

## Common Pitfalls

### Pitfall 1: Buffered Build Output
**What goes wrong:** Build output appears all at once when make completes, not in real-time
**Why it happens:** Using `subprocess.PIPE` for stdout causes Python to buffer output
**How to avoid:** Don't redirect stdout/stderr - let them inherit from parent process
**Warning signs:** User sees no output for 30+ seconds during compilation

### Pitfall 2: Menuconfig Crashes on Non-TTY
**What goes wrong:** Menuconfig fails with "Terminal not capable" or similar
**Why it happens:** ncurses requires a real TTY, subprocess.PIPE provides a pipe
**How to avoid:** Use inherited stdio (no stdin/stdout/stderr args to subprocess.run)
**Warning signs:** Works in SSH terminal, fails in cron or piped scripts

### Pitfall 3: Config Not Saved After Menuconfig Exit
**What goes wrong:** User exits menuconfig, but cached .config is not updated
**Why it happens:** User pressed ESC or exited without saving
**How to avoid:** Compare .config mtime before/after menuconfig; prompt user if unchanged
**Warning signs:** Build uses old config, user is confused

### Pitfall 4: MCU Validation Bypass via Stale Config
**What goes wrong:** User copies wrong cached config, MCU validation passes incorrectly
**Why it happens:** Cached config MCU doesn't match device registry entry
**How to avoid:** Always validate MCU from cached config against device registry before copying to klipper dir
**Warning signs:** Flashing wrong firmware to board

### Pitfall 5: KCONFIG_CONFIG Path Must Be Absolute
**What goes wrong:** make menuconfig ignores KCONFIG_CONFIG, uses .config anyway
**Why it happens:** Relative path resolution differs between shell and make
**How to avoid:** Always use absolute path for KCONFIG_CONFIG environment variable
**Warning signs:** Config changes don't persist to expected file

### Pitfall 6: Klipper Directory Not Expanded
**What goes wrong:** `~` or `$HOME` in path not expanded, subprocess fails with "directory not found"
**Why it happens:** subprocess does not expand shell variables/tildes
**How to avoid:** Use `os.path.expanduser()` or `Path.expanduser()` before passing to subprocess
**Warning signs:** Works when path is `/home/pi/klipper`, fails with `~/klipper`

## Code Examples

Verified patterns from official sources:

### Detect if Menuconfig Saved Changes
```python
# Source: Python pathlib documentation + Kconfig exit behavior analysis
from pathlib import Path
import subprocess
import os

def run_menuconfig_with_save_detection(
    klipper_dir: str,
    config_path: str
) -> tuple[int, bool]:
    """Run menuconfig and detect if config was saved.

    Returns (return_code, was_saved).
    """
    config_file = Path(config_path)

    # Get mtime before (or 0 if file doesn't exist)
    mtime_before = config_file.stat().st_mtime if config_file.exists() else 0

    env = os.environ.copy()
    env["KCONFIG_CONFIG"] = str(config_file.absolute())

    result = subprocess.run(
        ["make", "menuconfig"],
        cwd=klipper_dir,
        env=env,
    )

    # Get mtime after
    mtime_after = config_file.stat().st_mtime if config_file.exists() else 0

    was_saved = mtime_after > mtime_before
    return result.returncode, was_saved
```

### Full Build with Output Size Check
```python
# Source: Python subprocess and pathlib documentation
from pathlib import Path
import subprocess
import multiprocessing
import time

def build_firmware(klipper_dir: str) -> tuple[int, int, float]:
    """Build Klipper firmware.

    Returns (return_code, firmware_size_bytes, elapsed_seconds).
    Size is 0 if build failed.
    """
    klipper_path = Path(klipper_dir).expanduser()
    start_time = time.monotonic()

    # make clean
    clean = subprocess.run(["make", "clean"], cwd=klipper_path)
    if clean.returncode != 0:
        elapsed = time.monotonic() - start_time
        return clean.returncode, 0, elapsed

    # make -j$(nproc)
    nproc = multiprocessing.cpu_count()
    build = subprocess.run(["make", f"-j{nproc}"], cwd=klipper_path)
    elapsed = time.monotonic() - start_time

    if build.returncode != 0:
        return build.returncode, 0, elapsed

    # Check firmware size
    firmware = klipper_path / "out" / "klipper.bin"
    size = firmware.stat().st_size if firmware.exists() else 0

    return 0, size, elapsed
```

### MCU Validation Against Registry
```python
# Source: Klipper Kconfig CONFIG_MCU format
import re
from pathlib import Path
from typing import Optional

def validate_mcu_match(
    config_path: str,
    expected_mcu: str
) -> tuple[bool, Optional[str]]:
    """Validate CONFIG_MCU in .config matches expected MCU.

    Returns (is_match, actual_mcu).
    MCU comparison is prefix-based: 'stm32h723' matches 'stm32h723xx'.
    """
    content = Path(config_path).read_text()
    match = re.search(r'^CONFIG_MCU="([^"]+)"', content, re.MULTILINE)

    if not match:
        return False, None

    actual_mcu = match.group(1)
    # Prefix match: device registry has 'stm32h723', config has 'stm32h723xx'
    is_match = actual_mcu.startswith(expected_mcu) or expected_mcu.startswith(actual_mcu)

    return is_match, actual_mcu
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PID Kconfig | kconfiglib (Python) | Klipper 20201020 | menuconfig is now Python-based, same TUI |
| os.path everywhere | pathlib | Python 3.4+ | Cleaner API, cross-platform |
| subprocess.call | subprocess.run | Python 3.5+ | Better API, CompletedProcess return |
| text=False default | text=True common | Python 3.7+ | Easier string handling |

**Deprecated/outdated:**
- `subprocess.call()`: Use `subprocess.run()` instead (more features, cleaner API)
- `os.path.expanduser()`: Works but `Path.expanduser()` is more Pythonic
- Manual temp file cleanup: Use `NamedTemporaryFile(delete=False)` with try/finally

## Open Questions

Things that couldn't be fully resolved:

1. **Menuconfig exit code on save vs cancel**
   - What we know: Menuconfig prompts on exit if changes unsaved; ESC without save shows "NOT saved"
   - What's unclear: Whether return code differs (some sources suggest Error 1 on unsaved exit)
   - Recommendation: Use mtime comparison as primary detection, return code as secondary signal

2. **CONFIG_MCU format consistency across architectures**
   - What we know: STM32 uses `stm32h723xx`, RP2040 uses `rp2040`
   - What's unclear: Whether all architectures follow same pattern (lowercase, no prefix)
   - Recommendation: Use prefix matching to be flexible with format variations

3. **Build time variation**
   - What we know: Full clean build takes 30-90 seconds on Raspberry Pi 4
   - What's unclear: Exact timing for different MCU targets
   - Recommendation: Don't hardcode timeouts; let make complete naturally

## Sources

### Primary (HIGH confidence)
- [Python subprocess documentation](https://docs.python.org/3/library/subprocess.html) - subprocess.run, PIPE behavior, inherited stdio
- [Klipper STM32 Kconfig](https://github.com/Klipper3d/klipper/blob/master/src/stm32/Kconfig) - CONFIG_MCU format, chip definitions
- [Klipper main Kconfig](https://github.com/Klipper3d/klipper/blob/master/src/Kconfig) - Architecture selection structure
- Existing codebase: `registry.py` - Atomic write pattern with tempfile

### Secondary (MEDIUM confidence)
- [Voron Documentation - Automating Klipper MCU Updates](https://docs.vorondesign.com/community/howto/drachenkatze/automating_klipper_mcu_updates.html) - KCONFIG_CONFIG usage
- [XDG Base Directory Specification](https://xdgbasedirectoryspecification.com/) - Config directory resolution
- [Python pathlib documentation](https://docs.python.org/3/library/pathlib.html) - stat(), st_mtime

### Tertiary (LOW confidence - WebSearch only)
- Various blog posts on subprocess real-time output - Confirmed with official docs
- Kconfig save/cancel detection - Mtime comparison is reliable alternative

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All Python stdlib, well-documented
- Architecture patterns: HIGH - Based on existing codebase patterns and official Python docs
- Pitfalls: HIGH - Based on known Kconfig/ncurses behavior and subprocess documentation

**Research date:** 2026-01-25
**Valid until:** 2026-03-25 (60 days - stable domain, Klipper/Python APIs don't change frequently)
