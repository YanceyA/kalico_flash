# Phase 3: Flash & Orchestration - Research

**Researched:** 2026-01-25
**Domain:** Flash orchestration (Katapult/make flash), service lifecycle management, subprocess timeouts, signal handling
**Confidence:** HIGH

## Summary

Phase 3 implements the flash orchestration layer: a single command that discovers the device, runs menuconfig, builds firmware, stops Klipper, flashes the MCU, and restarts Klipper -- with guaranteed service restart on all code paths (success, failure, exception, Ctrl+C).

The core technical challenges are:

1. **Flash method orchestration**: Katapult flashtool.py is the primary flash method. It accepts `-d DEVICE` for serial devices and `-f FIRMWARE` for the binary path. If Katapult fails, fall back to `make flash FLASH_DEVICE=/dev/serial/by-id/...`.

2. **Service lifecycle guarantee**: The Klipper service must be stopped before flash and restarted after -- even on exception, timeout, or SIGINT. This requires a context manager with a finally block, not try/except alone.

3. **Passwordless sudo verification**: Before any service operation, verify `sudo -n true` succeeds. If it prompts for password, fail fast with a clear error message.

4. **Subprocess timeouts**: All subprocesses except menuconfig must have timeouts. Build: 300s, flash: 60s (per CONTEXT.md decision), service operations: 30s.

5. **Device re-verification**: After menuconfig and build (which can take several minutes), re-scan USB to verify the device path is still valid before flash.

**Primary recommendation:** Implement a `KlipperServiceManager` context manager that stops Klipper on `__enter__` and restarts on `__exit__` (in finally). Use `subprocess.run(..., timeout=T)` for all operations except menuconfig. Create a `FlashManager` class that orchestrates Katapult-first-with-fallback logic.

## Standard Stack

The established libraries/tools for this domain:

### Core (Python 3.9+ stdlib)
| Library | Module | Purpose | Why Standard |
|---------|--------|---------|--------------|
| subprocess | subprocess | Run external commands with timeouts | TimeoutExpired, capture_output, check |
| contextlib | contextlib | Context manager decorator | @contextmanager for service lifecycle |
| signal | signal | Signal handler registration | SIGINT handling for cleanup |
| time | time | Elapsed time, wait loops | Device reconnection detection |
| pathlib | pathlib | Path validation, existence checks | Device path verification |

### Supporting
| Library | Module | Purpose | When to Use |
|---------|--------|---------|-------------|
| os | os | Environment variables, expanduser | KCONFIG_CONFIG, path expansion |
| dataclasses | dataclasses | FlashResult contract | Return structured flash outcome |
| typing | typing | Type annotations | Protocol, Optional for interfaces |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| @contextmanager | Class-based context manager | Decorator is simpler for this use case |
| subprocess.run timeout | asyncio with timeout | asyncio adds complexity; sync is fine here |
| SIGINT handler | KeyboardInterrupt catch | Handler is more reliable for cleanup |

**No external dependencies required** - all functionality available in Python 3.9+ stdlib.

## Architecture Patterns

### Recommended Module Structure
```
klipper-flash/
    service.py        # NEW: KlipperServiceManager context manager
    flash_ops.py      # NEW: FlashManager with Katapult/make flash logic
    orchestrator.py   # NEW: Full workflow orchestration (optional, or inline in flash.py)
    errors.py         # Add FlashError, ServiceError (existing file)
    models.py         # Add FlashResult dataclass (existing file)
    ... (existing modules)
```

### Pattern 1: Service Lifecycle Context Manager with Finally Block
**What:** Guarantee Klipper service restart on all exit paths
**When to use:** Any operation that requires Klipper stopped (flash, MCU reset)
**Example:**
```python
# Source: Python contextlib documentation, adapted for service management
from contextlib import contextmanager
import subprocess
from errors import ServiceError

@contextmanager
def klipper_service_stopped(timeout: int = 30):
    """Context manager that stops Klipper and guarantees restart.

    Usage:
        with klipper_service_stopped():
            # Klipper is stopped here
            flash_device(...)
        # Klipper is restarted here, even if flash_device raises
    """
    _stop_klipper(timeout)
    try:
        yield
    finally:
        # Always restart, even on exception or Ctrl+C
        _start_klipper(timeout)


def _stop_klipper(timeout: int) -> None:
    """Stop Klipper service."""
    result = subprocess.run(
        ["sudo", "systemctl", "stop", "klipper"],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise ServiceError(f"Failed to stop Klipper: {result.stderr}")


def _start_klipper(timeout: int) -> None:
    """Start Klipper service. Best-effort, logs errors but does not raise."""
    try:
        result = subprocess.run(
            ["sudo", "systemctl", "start", "klipper"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            # Log but don't raise - we're in finally, can't interrupt cleanup
            print(f"[!!] Warning: Failed to restart Klipper: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("[!!] Warning: Timeout restarting Klipper service")
```

**Critical design note:** The finally block must not raise exceptions that mask the original exception. If Klipper restart fails, log a warning but don't raise.

### Pattern 2: Passwordless Sudo Verification
**What:** Verify sudo works without password before any service operation
**When to use:** Before stopping Klipper service
**Example:**
```python
# Source: Baeldung Linux passwordless sudo check
import subprocess

def verify_passwordless_sudo() -> bool:
    """Check if passwordless sudo is available.

    Returns True if sudo can run without password prompt.
    """
    try:
        result = subprocess.run(
            ["sudo", "-n", "true"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
```

### Pattern 3: Katapult Flash with Fallback to make flash
**What:** Try Katapult flashtool.py first, fall back to make flash on failure
**When to use:** Primary flash operation
**Example:**
```python
# Source: Katapult flashtool.py documentation, Klipper make flash
import subprocess
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

@dataclass
class FlashResult:
    """Result of a flash operation."""
    success: bool
    method: str  # "katapult" or "make_flash"
    error_message: Optional[str] = None


def flash_device(
    device_path: str,
    firmware_path: str,
    katapult_dir: str,
    klipper_dir: str,
    timeout: int = 60,
) -> FlashResult:
    """Flash firmware to device, trying Katapult first then make flash.

    Args:
        device_path: /dev/serial/by-id/... path to device
        firmware_path: Path to klipper.bin
        katapult_dir: Path to Katapult source (for flashtool.py)
        klipper_dir: Path to Klipper source (for make flash)
        timeout: Flash operation timeout in seconds

    Returns:
        FlashResult with success status and method used
    """
    # Try Katapult first
    katapult_result = _try_katapult_flash(
        device_path, firmware_path, katapult_dir, timeout
    )
    if katapult_result.success:
        return katapult_result

    # Katapult failed, try make flash
    print(f"[Flash] Katapult failed, trying make flash...")
    make_result = _try_make_flash(
        device_path, klipper_dir, timeout
    )
    return make_result


def _try_katapult_flash(
    device_path: str,
    firmware_path: str,
    katapult_dir: str,
    timeout: int,
) -> FlashResult:
    """Attempt flash via Katapult flashtool.py."""
    flashtool = Path(katapult_dir).expanduser() / "scripts" / "flashtool.py"

    if not flashtool.exists():
        return FlashResult(
            success=False,
            method="katapult",
            error_message=f"flashtool.py not found: {flashtool}",
        )

    try:
        result = subprocess.run(
            ["python3", str(flashtool), "-d", device_path, "-f", firmware_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return FlashResult(success=True, method="katapult")
        return FlashResult(
            success=False,
            method="katapult",
            error_message=result.stderr or f"Exit code {result.returncode}",
        )
    except subprocess.TimeoutExpired:
        return FlashResult(
            success=False,
            method="katapult",
            error_message=f"Timeout after {timeout}s",
        )


def _try_make_flash(
    device_path: str,
    klipper_dir: str,
    timeout: int,
) -> FlashResult:
    """Attempt flash via make flash."""
    klipper_path = Path(klipper_dir).expanduser()

    try:
        result = subprocess.run(
            ["make", f"FLASH_DEVICE={device_path}", "flash"],
            cwd=str(klipper_path),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return FlashResult(success=True, method="make_flash")
        return FlashResult(
            success=False,
            method="make_flash",
            error_message=result.stderr or f"Exit code {result.returncode}",
        )
    except subprocess.TimeoutExpired:
        return FlashResult(
            success=False,
            method="make_flash",
            error_message=f"Timeout after {timeout}s",
        )
```

### Pattern 4: Device Path Re-Verification
**What:** Confirm device still exists at path before flash
**When to use:** After menuconfig + build, before flash
**Example:**
```python
# Source: Python pathlib documentation
from pathlib import Path
from errors import DiscoveryError

def verify_device_path(device_path: str) -> None:
    """Verify device path exists.

    Raises DiscoveryError if device not found.
    """
    path = Path(device_path)
    if not path.exists():
        raise DiscoveryError(
            f"Device no longer connected: {device_path}\n"
            "The device may have been unplugged during build."
        )
```

### Pattern 5: Phase-Labeled Output
**What:** Prefix console output with phase labels
**When to use:** All workflow steps
**Example:**
```python
# Source: CONTEXT.md phase label decision
# Output interface extension for phase labels

class CliOutput:
    # ... existing methods ...

    def phase(self, phase_name: str, message: str) -> None:
        """Output a phase-labeled message."""
        print(f"[{phase_name}] {message}")

# Usage:
out.phase("Discovery", "Scanning for devices...")
out.phase("Config", "Loading cached config...")
out.phase("Build", "Running make clean + make...")
out.phase("Flash", "Flashing via Katapult...")
```

### Pattern 6: Subprocess Timeout Handling
**What:** Apply timeouts to all subprocess calls except menuconfig
**When to use:** Build, flash, service operations
**Example:**
```python
# Source: Python subprocess documentation
import subprocess

# Timeout constants (from CONTEXT.md + requirements)
TIMEOUT_BUILD = 300      # 5 minutes for make
TIMEOUT_FLASH = 60       # 60 seconds for flash (CONTEXT.md decision)
TIMEOUT_SERVICE = 30     # 30 seconds for systemctl
TIMEOUT_SUDO_CHECK = 5   # Quick check for sudo

def run_with_timeout(cmd, timeout, cwd=None, capture=True):
    """Run subprocess with timeout, clean error on timeout."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        return result
    except subprocess.TimeoutExpired as e:
        raise BuildError(f"Command timed out after {timeout}s: {' '.join(cmd)}")
```

### Anti-Patterns to Avoid
- **Catching KeyboardInterrupt without re-raising:** In a context manager finally block, let KeyboardInterrupt propagate after cleanup. Don't suppress it.
- **Raising in finally block:** If restart fails, log the error but don't raise. The original exception must propagate.
- **Using subprocess.Popen without wait:** Always wait() or communicate() to ensure process cleanup.
- **Hardcoding device paths:** Always use the discovered /dev/serial/by-id/ path, never /dev/ttyUSB0.
- **Assuming sudo always works:** Always verify passwordless sudo before service operations.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Service lifecycle | try/except around stop/start | Context manager with finally | Finally block executes on exception AND Ctrl+C |
| Timeout handling | Manual threading/alarm | subprocess.run(timeout=N) | Stdlib handles cleanup properly |
| Sudo availability check | Parsing /etc/sudoers | `sudo -n true` | Non-invasive, works regardless of config method |
| Device path validation | Manual stat() calls | Path.exists() | Clean, readable API |
| Flash method detection | Parsing Katapult output | Exit code + fallback | Simple, reliable |

**Key insight:** The context manager pattern with finally block is critical for SRVC-02. The finally block runs even when:
- The code raises an exception
- KeyboardInterrupt (Ctrl+C) is received
- sys.exit() is called from within the block (finally still runs before exit)

## Common Pitfalls

### Pitfall 1: Service Restart Failure Masking Original Error
**What goes wrong:** Klipper restart fails in finally block, raises exception that hides the flash error
**Why it happens:** Exceptions in finally block replace the original exception
**How to avoid:** Catch exceptions in finally block, log them, but don't re-raise. Use logging or print, not raise.
**Warning signs:** "Failed to restart Klipper" is the only error shown, even though flash failed

### Pitfall 2: Subprocess Timeout Leaves Zombie Process
**What goes wrong:** TimeoutExpired is raised but the process keeps running
**Why it happens:** subprocess.run() with timeout kills the process, but subprocess.Popen() does not
**How to avoid:** Use subprocess.run() for timeouts. If using Popen, call proc.kill() in the exception handler.
**Warning signs:** Multiple make processes running, device locked by previous attempt

### Pitfall 3: Katapult Requires pyserial
**What goes wrong:** flashtool.py fails with "ModuleNotFoundError: No module named 'serial'"
**Why it happens:** Katapult's flashtool.py depends on pyserial for USB/UART devices
**How to avoid:** Document that pyserial must be installed (`sudo apt install python3-serial`). Check for import error and provide helpful message.
**Warning signs:** Katapult always fails, make flash always succeeds

### Pitfall 4: Device Path Changes After Bootloader Entry
**What goes wrong:** Device path was verified, but Katapult triggers bootloader mode, changing the path
**Why it happens:** When Katapult sends the "enter bootloader" command, the device disconnects and reconnects with a different USB product ID (katapult instead of Klipper)
**How to avoid:** This is expected behavior. Don't re-verify path during flash - trust the flash tool to handle reconnection. Only verify before stopping Klipper.
**Warning signs:** "Device not found" errors during Katapult flash even though device exists

### Pitfall 5: Passwordless Sudo for Specific Commands Only
**What goes wrong:** `sudo -n true` works but `sudo -n systemctl stop klipper` fails
**Why it happens:** sudoers file may allow NOPASSWD only for specific commands
**How to avoid:** Test with actual systemctl command, not just "true". Or document that NOPASSWD must cover systemctl.
**Warning signs:** Sudo check passes but service stop hangs waiting for password

### Pitfall 6: Signal Handler Interferes with Subprocess
**What goes wrong:** Custom SIGINT handler prevents subprocess from being killed properly
**Why it happens:** Python signal handlers run in the main thread, can interfere with subprocess wait()
**How to avoid:** Don't install custom signal handlers. Let KeyboardInterrupt propagate naturally. The context manager finally block will handle cleanup.
**Warning signs:** Ctrl+C doesn't stop the build, or leaves orphan processes

### Pitfall 7: Interactive Device Selection with No Devices
**What goes wrong:** User runs flash command with no --device flag and no devices connected
**Why it happens:** Interactive selection expects at least one device
**How to avoid:** Scan first, check if empty. If no devices found, error with "No USB devices found. Connect a board and try again." Don't show empty selection menu.
**Warning signs:** Index out of range errors, or cryptic empty menu

## Code Examples

Verified patterns from official sources:

### Full Flash Orchestration Flow
```python
# Source: Combined patterns from research
from contextlib import contextmanager
from pathlib import Path
from typing import Optional
import subprocess
import time

from errors import FlashError, ServiceError, DiscoveryError
from models import FlashResult, DeviceEntry
from discovery import scan_serial_devices, match_device


def orchestrate_flash(
    device: DeviceEntry,
    klipper_dir: str,
    katapult_dir: str,
    out,  # Output protocol
) -> int:
    """Full flash workflow with service lifecycle management.

    Returns 0 on success, 1 on failure.
    """
    # Phase 1: Discovery
    out.phase("Discovery", f"Looking for {device.name}...")
    devices = scan_serial_devices()
    matched = match_device(device.serial_pattern, devices)
    if not matched:
        out.error(f"Device not connected: {device.serial_pattern}")
        return 1
    device_path = matched.path
    out.phase("Discovery", f"Found at {device_path}")

    # Phase 2: Config + Build (already implemented in Phase 2)
    # ... menuconfig, MCU validation, build ...

    # Phase 3: Pre-flash verification
    out.phase("Flash", "Verifying device connection...")
    if not Path(device_path).exists():
        out.error(f"Device disconnected during build: {device_path}")
        return 1

    # Phase 4: Verify sudo
    if not verify_passwordless_sudo():
        out.error(
            "Passwordless sudo not configured.\n"
            "Add to /etc/sudoers: yourusername ALL=(ALL) NOPASSWD: /bin/systemctl"
        )
        return 1

    # Phase 5: Flash with service lifecycle
    firmware_path = str(Path(klipper_dir).expanduser() / "out" / "klipper.bin")
    start_time = time.monotonic()

    with klipper_service_stopped():
        out.phase("Flash", "Klipper stopped, flashing...")
        result = flash_device(
            device_path=device_path,
            firmware_path=firmware_path,
            katapult_dir=katapult_dir,
            klipper_dir=klipper_dir,
        )
    # Klipper restarted automatically here

    elapsed = time.monotonic() - start_time

    # Phase 6: Summary
    if result.success:
        out.success(
            f"Flash complete: {device.name} via {result.method} "
            f"in {elapsed:.1f}s"
        )
        return 0
    else:
        out.error(f"Flash failed: {result.error_message}")
        return 1


def verify_passwordless_sudo() -> bool:
    """Check if passwordless sudo is available."""
    try:
        result = subprocess.run(
            ["sudo", "-n", "true"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
```

### Wait for Device Reconnection After Flash
```python
# Source: Klipper flash_usb.py pattern
import time
from pathlib import Path

def wait_for_device(serial_pattern: str, timeout: float = 10.0) -> Optional[str]:
    """Wait for device to reconnect after flash.

    Args:
        serial_pattern: Glob pattern for device serial
        timeout: Maximum seconds to wait

    Returns:
        Device path if found, None if timeout
    """
    from discovery import scan_serial_devices, match_device

    end_time = time.monotonic() + timeout
    while time.monotonic() < end_time:
        devices = scan_serial_devices()
        matched = match_device(serial_pattern, devices)
        if matched:
            return matched.path
        time.sleep(0.5)
    return None
```

### Error Messages with Recovery Steps
```python
# Source: CLUX-03 requirement pattern
from dataclasses import dataclass
from typing import List

@dataclass
class ErrorContext:
    """Structured error with recovery information."""
    what_failed: str
    command_run: str
    likely_cause: str
    recovery_steps: List[str]

def format_flash_error(result: FlashResult, device_path: str) -> ErrorContext:
    """Generate helpful error context for flash failure."""
    if "timeout" in (result.error_message or "").lower():
        return ErrorContext(
            what_failed="Flash operation timed out",
            command_run=f"flashtool.py -d {device_path}",
            likely_cause="Device not responding or in wrong state",
            recovery_steps=[
                "1. Power cycle the MCU board",
                "2. Verify device appears in `ls /dev/serial/by-id/`",
                "3. Try running flash again",
            ],
        )
    # ... more error cases ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| try/except for cleanup | Context manager with finally | Always preferred | Guaranteed cleanup on all paths |
| subprocess.call() | subprocess.run() with timeout | Python 3.5+ | Built-in timeout support |
| os.system() for shell commands | subprocess.run() with list args | Security best practice | No shell injection risk |
| `service klipper stop` | `systemctl stop klipper` | systemd adoption | Standard on modern Linux |

**Deprecated/outdated:**
- `subprocess.call()`: Use `subprocess.run()` - better API, returns CompletedProcess
- `os.system()`: Never use - shell injection risk, no timeout support
- Catching SIGINT with signal.signal(): Let KeyboardInterrupt propagate, handle in finally

## Open Questions

Things that couldn't be fully resolved:

1. **Katapult flashtool.py pyserial dependency**
   - What we know: flashtool.py requires pyserial for USB/UART devices
   - What's unclear: Whether MainsailOS/FluiddPi always has it pre-installed
   - Recommendation: Check for import error gracefully; provide helpful install message if missing

2. **Device path during bootloader mode**
   - What we know: When Katapult enters bootloader, USB product ID changes
   - What's unclear: Exact timing and whether we need to wait for reconnection
   - Recommendation: Let flashtool.py handle the reconnection; don't re-verify path during flash

3. **Concurrent flash operations**
   - What we know: Only one device can be flashed at a time (Klipper must be stopped)
   - What's unclear: What happens if another instance is running
   - Recommendation: Not handling concurrent execution in v1; assume single operator

4. **Build timeout variation**
   - What we know: Build time varies by MCU complexity and Pi model
   - What's unclear: Whether 300s is sufficient for all cases
   - Recommendation: Use 300s default, log if it takes longer than expected

## Sources

### Primary (HIGH confidence)
- [Python subprocess documentation](https://docs.python.org/3/library/subprocess.html) - TimeoutExpired, run() with timeout
- [Python contextlib documentation](https://docs.python.org/3/library/contextlib.html) - @contextmanager, finally block semantics
- [Katapult flashtool.py source](https://github.com/Arksine/katapult/blob/master/scripts/flashtool.py) - CLI options (-d, -f, -v, -r)
- [Katapult README](https://github.com/Arksine/katapult/blob/master/README.md) - USB flashing process documentation
- [Klipper flash_usb.py](https://github.com/Klipper3d/klipper/blob/master/scripts/flash_usb.py) - make flash FLASH_DEVICE pattern
- [Klipper Installation docs](https://www.klipper3d.org/Installation.html) - Service management commands
- [Baeldung passwordless sudo check](https://www.baeldung.com/linux/sudo-passwordless-check) - sudo -n pattern

### Secondary (MEDIUM confidence)
- [Python signal handling](https://docs.python.org/3/library/signal.html) - SIGINT behavior with subprocess
- [AWS CodeGuru leaky subprocess timeout](https://docs.aws.amazon.com/codeguru/detector-library/python/leaky-subprocess-timeout/) - Timeout cleanup patterns
- [njs blog: Control-C handling](https://vorpus.org/blog/control-c-handling-in-python-and-trio/) - KeyboardInterrupt in context managers

### Tertiary (LOW confidence)
- Klipper discourse forum posts on flashtool.py issues - Community troubleshooting
- MainsailOS documentation on pre-installed packages - Uncertain if current

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All Python stdlib, subprocess patterns well-documented
- Service lifecycle: HIGH - Context manager with finally is guaranteed by Python spec
- Katapult CLI: HIGH - Verified against current flashtool.py source code
- make flash: HIGH - Standard Klipper pattern, well-documented
- Passwordless sudo check: HIGH - Standard Linux pattern, verified with Baeldung

**Research date:** 2026-01-25
**Valid until:** 2026-03-25 (60 days - stable domain, Katapult/Klipper flash patterns don't change frequently)
