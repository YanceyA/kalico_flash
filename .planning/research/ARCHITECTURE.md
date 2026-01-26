# Architecture Research: klipper-flash

**Domain:** Python stdlib-only CLI tool for firmware build/flash orchestration
**Researched:** 2026-01-25
**Overall confidence:** HIGH (well-understood Python patterns, no exotic dependencies)

---

## Module Responsibilities

Each module has a single axis of responsibility. The key architectural principle is **separation of orchestration from execution**: `flash.py` owns the workflow sequence, while each module owns its domain operations.

### flash.py -- CLI Entry Point and Orchestrator

**Owns:**
- Argument parsing (`argparse`)
- Workflow sequencing (what happens in what order)
- Top-level error handling and user messaging
- Exit code management
- Dispatching to the correct workflow (flash, add-device, list-devices, remove-device)

**Does NOT own:**
- Any direct subprocess calls
- Any file I/O except reading its own CLI arguments
- Device state or config state
- Knowledge of how to build or flash

**Design rationale:** The entry point should be a thin orchestrator. If you read `flash.py` you should see the entire workflow as a readable sequence of function calls. No implementation details leak here. This makes it easy to test workflows by mocking module functions and easy to add new commands later.

**Key pattern -- workflow functions, not a monolith:**
```python
def cmd_flash(args):
    """The normal flash workflow."""
    device = resolve_device(args)       # discovery + registry
    config = prepare_config(device, args)  # config_manager
    build_firmware(device, config, args)   # builder
    flash_firmware(device, args)           # flasher (handles service lifecycle)

def cmd_add_device(args):
    """The add-device wizard workflow."""
    ...

def main():
    args = parse_args()
    COMMANDS = {
        'flash': cmd_flash,       # default
        'add': cmd_add_device,
        'list': cmd_list_devices,
        'remove': cmd_remove_device,
    }
    ...
```

### discovery.py -- USB Device Discovery

**Owns:**
- Scanning `/dev/serial/by-id/` directory
- Returning a list of discovered device paths
- Matching device paths against glob patterns (using `fnmatch`)
- Resolving a device path from a serial_pattern

**Does NOT own:**
- The device registry (that is `registry.py`)
- Any knowledge of what to do with a discovered device
- Interactive user selection (that is `flash.py` orchestration)

**Public interface:**
```python
@dataclass
class DiscoveredDevice:
    path: Path          # /dev/serial/by-id/usb-Klipper_stm32f446xx_...
    filename: str       # usb-Klipper_stm32f446xx_...

def scan_serial_devices() -> list[DiscoveredDevice]:
    """Return all devices in /dev/serial/by-id/."""

def match_device(pattern: str, devices: list[DiscoveredDevice]) -> DiscoveredDevice | None:
    """Find first device matching a glob pattern."""

def find_device_path(pattern: str) -> Path | None:
    """Convenience: scan + match in one call. Returns None if not found."""
```

**Design rationale:** Discovery is a pure read-only operation with no side effects. It should be trivially testable by mocking `Path('/dev/serial/by-id').iterdir()`. Keep it stateless.

### registry.py -- Device Registry CRUD

**Owns:**
- Reading/writing `devices.json`
- Schema validation of device entries
- CRUD operations: list, get, add, remove, update
- Generating serial patterns from device paths (for the add-device wizard)

**Does NOT own:**
- USB scanning (uses `discovery.py` if needed)
- Config files (that is `config_manager.py`)
- Any subprocess execution

**Public interface:**
```python
@dataclass
class DeviceEntry:
    key: str                # "octopus-pro"
    name: str               # "Octopus Pro v1.1"
    mcu: str                # "stm32f446"
    serial_pattern: str     # "usb-Klipper_stm32f446*"
    flash_method: str       # "make_flash" | "katapult"
    klipper_dir: Path       # ~/klipper
    katapult_dir: Path | None  # ~/katapult (only for katapult method)

class Registry:
    def __init__(self, registry_path: Path): ...
    def load(self) -> dict[str, DeviceEntry]: ...
    def save(self, entries: dict[str, DeviceEntry]) -> None: ...
    def get(self, key: str) -> DeviceEntry | None: ...
    def add(self, entry: DeviceEntry) -> None: ...
    def remove(self, key: str) -> bool: ...
    def list_all(self) -> list[DeviceEntry]: ...
```

**Design rationale:** The registry is a tiny JSON persistence layer. Making it a class with explicit `load`/`save` keeps it simple and testable. The `DeviceEntry` dataclass is the shared data contract other modules use. Using `dataclasses` from stdlib avoids any dependency on Pydantic or attrs.

### config_manager.py -- Config Caching and Change Detection

**Owns:**
- Copying `.config` between klipper_dir and the cache directory
- SHA256 hashing of `.config` files
- Reading/writing `.config.sha256` sidecar files
- Determining whether config has changed (hash comparison)

**Does NOT own:**
- Running menuconfig (that is `builder.py`)
- Knowledge of when to skip menuconfig (that is the orchestrator's decision)
- The device registry

**Public interface:**
```python
class ConfigManager:
    def __init__(self, configs_dir: Path): ...

    def has_cached_config(self, device_key: str) -> bool: ...

    def restore_config(self, device_key: str, klipper_dir: Path) -> bool:
        """Copy cached .config into klipper_dir/.config. Returns True if found."""

    def cache_config(self, device_key: str, klipper_dir: Path) -> str:
        """Copy klipper_dir/.config into cache, update SHA256. Returns new hash."""

    def config_changed(self, device_key: str, klipper_dir: Path) -> bool:
        """Compare current klipper_dir/.config hash against cached hash."""

    def get_cached_hash(self, device_key: str) -> str | None:
        """Read the stored SHA256 hash for a device."""
```

**Design rationale:** Config management is pure file I/O with hashing. No subprocesses, no network. Completely deterministic and testable. The `ConfigManager` class holds the `configs_dir` path so callers do not need to know where configs live.

### builder.py -- Firmware Build Orchestration

**Owns:**
- Running `make menuconfig` (with inherited stdio for ncurses)
- Running `make clean`
- Running `make -j$(nproc)` (or `make -jN`)
- Working directory management (cwd=klipper_dir)
- Build success/failure detection (exit codes)

**Does NOT own:**
- Config caching or hashing (uses `config_manager.py`)
- Deciding whether to skip menuconfig or clean (the orchestrator decides, passes flags)
- Flashing

**Public interface:**
```python
class BuildError(Exception):
    """Raised when a build step fails."""
    def __init__(self, step: str, returncode: int, message: str): ...

def run_menuconfig(klipper_dir: Path) -> None:
    """Run make menuconfig interactively. Raises BuildError on failure."""

def run_clean(klipper_dir: Path) -> None:
    """Run make clean. Raises BuildError on failure."""

def run_build(klipper_dir: Path, jobs: int | None = None) -> None:
    """Run make -jN. Raises BuildError on failure."""

def get_cpu_count() -> int:
    """Return os.cpu_count() or 1 as fallback."""
```

**Design rationale:** Builder functions are stateless. Each is a single subprocess call. Keeping them as module-level functions (not a class) is appropriate because there is no state to carry between calls -- klipper_dir is passed as an argument. The orchestrator calls them in sequence and handles errors.

**Critical: menuconfig subprocess handling:**
```python
def run_menuconfig(klipper_dir: Path) -> None:
    result = subprocess.run(
        ['make', 'menuconfig'],
        cwd=klipper_dir,
        # DO NOT capture stdout/stderr -- ncurses needs the real terminal
    )
    if result.returncode != 0:
        raise BuildError('menuconfig', result.returncode, 'menuconfig failed or was cancelled')
```

### flasher.py -- Flash Execution and Service Lifecycle

**Owns:**
- Stopping and starting the klipper systemd service
- Executing the flash command (make flash or katapult flashtool)
- The **guaranteed service restart** pattern (the critical safety invariant)
- Flash method dispatch (make_flash vs katapult)

**Does NOT own:**
- Device discovery or registry
- Build steps
- Config management

**Public interface:**
```python
class FlashError(Exception):
    """Raised when flashing fails. Klipper service is ALREADY restarted."""
    def __init__(self, method: str, returncode: int, message: str): ...

class ServiceError(Exception):
    """Raised when service stop/start fails."""
    def __init__(self, action: str, message: str): ...

def flash_device(device: DeviceEntry, device_path: Path, dry_run: bool = False) -> None:
    """
    Stop klipper, flash firmware, start klipper.

    GUARANTEE: Klipper service will be restarted even if flashing fails.
    On flash failure, raises FlashError AFTER restarting klipper.
    """
```

**This is the most architecturally critical module.** See the Error Handling Strategy section below for the full pattern.

---

## Data Flow

### Flow 1: Normal Flash (happy path)

```
User runs: ./flash.py --device octopus-pro --skip-menuconfig

flash.py (orchestrator)
  |
  |-- registry.load("octopus-pro")
  |     Returns: DeviceEntry(key="octopus-pro", serial_pattern="usb-Klipper_stm32f446*", ...)
  |
  |-- discovery.find_device_path("usb-Klipper_stm32f446*")
  |     Scans /dev/serial/by-id/
  |     Returns: Path("/dev/serial/by-id/usb-Klipper_stm32f446xx_2A003...")
  |
  |-- config_manager.restore_config("octopus-pro", klipper_dir)
  |     Copies configs/octopus-pro.config -> ~/klipper/.config
  |
  |-- [skip menuconfig because --skip-menuconfig AND config_manager.config_changed() is False]
  |
  |-- builder.run_clean(klipper_dir)
  |-- builder.run_build(klipper_dir)
  |
  |-- flasher.flash_device(device_entry, device_path)
  |     |-- sudo systemctl stop klipper
  |     |-- make flash FLASH_DEVICE=<path>  [or katapult flashtool]
  |     |-- sudo systemctl start klipper   [ALWAYS, even on failure]
  |
  |-- config_manager.cache_config("octopus-pro", klipper_dir)
  |     Updates cached .config and .sha256
  |
  Done. Exit 0.
```

### Flow 2: Add Device Wizard

```
User runs: ./flash.py --add-device

flash.py (orchestrator)
  |
  |-- discovery.scan_serial_devices()
  |     Returns: [DiscoveredDevice(...), DiscoveredDevice(...), ...]
  |
  |-- [interactive: user picks a device from list]
  |-- [interactive: user provides name, mcu, flash_method, paths]
  |
  |-- registry.add(DeviceEntry(...))
  |     Writes to devices.json
  |
  |-- config_manager.restore_config(key, klipper_dir)  [if exists, otherwise no-op]
  |-- builder.run_menuconfig(klipper_dir)
  |     Interactive ncurses -- user configures and saves
  |
  |-- config_manager.cache_config(key, klipper_dir)
  |     Copies .config to cache, writes .sha256
  |
  Done. Exit 0.
```

### Flow 3: Flash with Error Recovery

```
flash.py (orchestrator)
  |
  |-- [discovery, config, build all succeed]
  |
  |-- flasher.flash_device(device_entry, device_path)
  |     |-- sudo systemctl stop klipper        [success]
  |     |-- make flash FLASH_DEVICE=<path>     [FAILS, exit code 1]
  |     |-- sudo systemctl start klipper       [ALWAYS runs -- guaranteed]
  |     |-- raises FlashError (after klipper is restarted)
  |
  |-- flash.py catches FlashError
  |-- Prints error message with details
  |-- Exit 1.
```

### Data Types Flowing Between Modules

```
                    DeviceEntry (dataclass)
                    ========================
registry.py ------> flash.py orchestrator ------> flasher.py
                         |
                         v
                    discovery.py returns Path
                         |
                         v
                    config_manager.py takes (device_key: str, klipper_dir: Path)
                         |
                         v
                    builder.py takes (klipper_dir: Path)
```

The `DeviceEntry` dataclass (defined in `registry.py`) is the primary data contract. It carries everything needed: device key, name, serial pattern, flash method, and directory paths. The orchestrator unpacks what each module needs from this dataclass.

---

## Build Order

Modules have clear dependency layers. This determines what can be implemented and tested independently.

### Layer 0: No Dependencies (build first)

These modules depend only on Python stdlib and can be built and tested in isolation.

| Module | Depends On | Can Test With |
|--------|-----------|---------------|
| `discovery.py` | `pathlib`, `fnmatch` | Mock filesystem |
| `config_manager.py` | `pathlib`, `hashlib`, `shutil` | Temp directories |
| `registry.py` | `json`, `pathlib`, `dataclasses` | Temp JSON files |

**Recommendation:** Build these three first. They are pure I/O modules with no subprocess calls and no inter-module dependencies. They form the foundation everything else sits on.

### Layer 1: Subprocess Modules (build second)

These modules call subprocesses and are harder to test but have no inter-module dependencies.

| Module | Depends On | Can Test With |
|--------|-----------|---------------|
| `builder.py` | `subprocess`, `os` | Mock subprocess.run |
| `flasher.py` | `subprocess` | Mock subprocess.run |

**Recommendation:** Build `builder.py` first because you need it during the add-device wizard to run menuconfig. Build `flasher.py` second. Both can be tested against mock subprocesses, but real integration testing requires a Klipper environment.

### Layer 2: Orchestrator (build last)

| Module | Depends On | Can Test With |
|--------|-----------|---------------|
| `flash.py` | All of the above | Integration test with mocked modules |

**Recommendation:** Build the orchestrator last. By this point all modules have known interfaces and can be composed. The orchestrator is where workflow logic and user interaction live.

### Suggested Implementation Sequence

```
Phase 1: Foundation
  1. registry.py + DeviceEntry dataclass
  2. discovery.py
  3. config_manager.py

Phase 2: Execution
  4. builder.py (menuconfig, clean, build)
  5. flasher.py (flash + service lifecycle)

Phase 3: Integration
  6. flash.py (CLI parsing + workflow orchestration)
  7. Integration testing on actual hardware
```

---

## Error Handling Strategy

This is the most architecturally critical aspect of the tool. The fundamental invariant is:

> **If klipper was stopped, klipper MUST be restarted, regardless of any error.**

A printer with klipper stopped is unusable. A failed flash with klipper running is annoying but recoverable. A failed flash with klipper stopped is a brick-like experience requiring SSH troubleshooting.

### The Service Guard Pattern

The core pattern is a context manager that guarantees service restart. This is better than try/finally scattered across the orchestrator because it encapsulates the invariant in one place.

```python
# flasher.py

import subprocess
from contextlib import contextmanager

@contextmanager
def klipper_stopped(dry_run: bool = False):
    """
    Context manager that stops klipper on entry and GUARANTEES restart on exit.

    Usage:
        with klipper_stopped():
            do_flash_stuff()  # if this raises, klipper still restarts

    The guarantee: even if the body raises an exception, even if it raises
    KeyboardInterrupt, klipper.service will be started before the exception
    propagates.
    """
    _stop_klipper(dry_run)
    try:
        yield
    finally:
        _start_klipper(dry_run)

def _stop_klipper(dry_run: bool = False) -> None:
    if dry_run:
        print("[DRY RUN] Would stop klipper.service")
        return
    result = subprocess.run(
        ['sudo', 'systemctl', 'stop', 'klipper'],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise ServiceError('stop', result.stderr.strip())

def _start_klipper(dry_run: bool = False) -> None:
    if dry_run:
        print("[DRY RUN] Would start klipper.service")
        return
    result = subprocess.run(
        ['sudo', 'systemctl', 'start', 'klipper'],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        # This is a critical failure -- print loudly but don't mask the original error
        print("\n[CRITICAL] Failed to restart klipper.service!")
        print(f"  Error: {result.stderr.strip()}")
        print("  Manual fix: sudo systemctl start klipper")
        # DO NOT raise here -- we might be in a finally block handling another exception

def flash_device(device: 'DeviceEntry', device_path: 'Path', dry_run: bool = False) -> None:
    """Stop klipper, flash, restart klipper. Guaranteed restart."""
    with klipper_stopped(dry_run):
        if device.flash_method == 'katapult':
            _flash_katapult(device, device_path, dry_run)
        elif device.flash_method == 'make_flash':
            _flash_make(device, device_path, dry_run)
        else:
            raise FlashError(device.flash_method, -1, f"Unknown flash method: {device.flash_method}")
```

**Why a context manager instead of try/finally in the orchestrator:**

1. **Encapsulation:** The invariant lives in one place. You cannot accidentally forget the finally block.
2. **Composability:** If future code needs to flash multiple devices, each gets its own `klipper_stopped()` block.
3. **Signal safety:** Python's `contextmanager` handles `GeneratorExit` and keyboard interrupts correctly in the `finally` clause.
4. **Testing:** You can test the context manager independently of any flash logic.

### Error Propagation Strategy

Errors propagate upward through the module layers. Each module raises domain-specific exceptions. The orchestrator catches and reports them.

```
Layer 0 (data modules):
  - FileNotFoundError    -- missing config, missing registry
  - json.JSONDecodeError -- corrupt devices.json
  - ValueError           -- invalid device entry

Layer 1 (subprocess modules):
  - BuildError           -- make clean/build/menuconfig failed
  - FlashError           -- flash command failed (klipper ALREADY restarted)
  - ServiceError         -- systemctl stop/start failed

Layer 2 (orchestrator):
  - Catches all of the above
  - Prints user-friendly message
  - Sets exit code
  - NEVER lets an exception reach the user as a raw traceback
```

**Orchestrator error handling skeleton:**

```python
def main() -> int:
    """Returns exit code."""
    try:
        args = parse_args()
        dispatch_command(args)
        return 0
    except KeyboardInterrupt:
        print("\nAborted by user.")
        return 130
    except FileNotFoundError as e:
        print(f"\n[ERROR] File not found: {e}")
        return 1
    except (BuildError, FlashError) as e:
        print(f"\n[ERROR] {e}")
        return 1
    except ServiceError as e:
        print(f"\n[CRITICAL] Service management failed: {e}")
        print("  Manual fix: sudo systemctl start klipper")
        return 2
    except Exception as e:
        print(f"\n[UNEXPECTED ERROR] {e}")
        print("  Please report this bug.")
        return 3

if __name__ == '__main__':
    sys.exit(main())
```

### Exception Hierarchy

```python
# errors.py (or defined at top of each module)

class KlipperFlashError(Exception):
    """Base for all klipper-flash errors."""
    pass

class BuildError(KlipperFlashError):
    def __init__(self, step: str, returncode: int, message: str):
        self.step = step
        self.returncode = returncode
        super().__init__(f"Build failed at '{step}' (exit {returncode}): {message}")

class FlashError(KlipperFlashError):
    def __init__(self, method: str, returncode: int, message: str):
        self.method = method
        self.returncode = returncode
        super().__init__(f"Flash failed with '{method}' (exit {returncode}): {message}")

class ServiceError(KlipperFlashError):
    def __init__(self, action: str, message: str):
        self.action = action
        super().__init__(f"Service '{action}' failed: {message}")

class DeviceNotFoundError(KlipperFlashError):
    def __init__(self, identifier: str):
        super().__init__(f"Device not found: {identifier}")

class RegistryError(KlipperFlashError):
    def __init__(self, message: str):
        super().__init__(f"Registry error: {message}")
```

**Design decision: Keep exceptions in each module or centralize?**

Recommendation: Define a small `errors.py` module with all custom exceptions. This avoids circular imports (e.g., flasher.py needing to import from registry.py just for an exception class) and gives the orchestrator a single import for all exception types. At 6 modules, this is small enough to warrant centralization without becoming unwieldy.

---

## Interface Design

### Module Communication Pattern

Modules communicate through **function calls with simple arguments**. No event system, no callback pattern, no observer pattern. This tool is a sequential pipeline with clear steps. Simplicity is the right architecture.

```
flash.py calls:     registry.load()          -> DeviceEntry
flash.py calls:     discovery.find_device()  -> Path
flash.py calls:     config_manager.restore() -> bool
flash.py calls:     builder.run_build()      -> None (or raises)
flash.py calls:     flasher.flash_device()   -> None (or raises)
```

No module calls another module directly. All cross-module coordination goes through the orchestrator. This is a **hub-and-spoke** pattern, not a web of inter-module dependencies.

### Data Types: Dataclasses Over Dicts

Use `dataclasses` (stdlib since 3.7) for all structured data. Never pass raw dicts between modules.

```python
from dataclasses import dataclass, field, asdict
from pathlib import Path

@dataclass
class DeviceEntry:
    key: str
    name: str
    mcu: str
    serial_pattern: str
    flash_method: str               # "make_flash" | "katapult"
    klipper_dir: Path
    katapult_dir: Path | None = None

    def to_dict(self) -> dict:
        """Serialize for JSON storage."""
        d = asdict(self)
        d['klipper_dir'] = str(self.klipper_dir)
        d['katapult_dir'] = str(self.katapult_dir) if self.katapult_dir else None
        return d

    @classmethod
    def from_dict(cls, key: str, data: dict) -> 'DeviceEntry':
        """Deserialize from JSON storage."""
        return cls(
            key=key,
            name=data['name'],
            mcu=data['mcu'],
            serial_pattern=data['serial_pattern'],
            flash_method=data['flash_method'],
            klipper_dir=Path(data['klipper_dir']),
            katapult_dir=Path(data['katapult_dir']) if data.get('katapult_dir') else None,
        )

@dataclass
class DiscoveredDevice:
    path: Path      # Full /dev/serial/by-id/usb-... path
    filename: str   # Just the filename part
```

### Subprocess Execution Pattern

All subprocess calls should follow a consistent pattern. Define a helper in `builder.py` or a shared utility.

```python
def _run_command(
    cmd: list[str],
    cwd: Path | None = None,
    capture: bool = True,
    check: bool = True,
    description: str = "",
) -> subprocess.CompletedProcess:
    """
    Run a subprocess with consistent handling.

    Args:
        cmd: Command and arguments
        cwd: Working directory
        capture: If True, capture stdout/stderr. If False, inherit stdio (for menuconfig).
        check: If True, raise on non-zero exit. If False, return result.
        description: Human-readable description for error messages.
    """
    kwargs = {'cwd': cwd}
    if capture:
        kwargs['capture_output'] = True
        kwargs['text'] = True

    result = subprocess.run(cmd, **kwargs)

    if check and result.returncode != 0:
        stderr = getattr(result, 'stderr', '') or ''
        raise subprocess.CalledProcessError(
            result.returncode, cmd, output=getattr(result, 'stdout', ''), stderr=stderr
        )
    return result
```

**Key insight: menuconfig is the exception.** Every other subprocess can capture output. Menuconfig MUST inherit stdio because it is an ncurses TUI. The `capture=False` parameter handles this cleanly.

### User Interaction Pattern

All user interaction (prompts, selection menus) lives in `flash.py` or a dedicated `ui.py` helper if it grows large. No other module should call `input()` or `print()` for user interaction.

```python
# In flash.py or ui.py

def select_from_list(items: list[str], prompt: str = "Select") -> int:
    """Display numbered list, return selected index."""
    for i, item in enumerate(items, 1):
        print(f"  {i}. {item}")
    while True:
        try:
            choice = int(input(f"\n{prompt} [1-{len(items)}]: "))
            if 1 <= choice <= len(items):
                return choice - 1
        except (ValueError, EOFError):
            pass
        print(f"  Please enter a number between 1 and {len(items)}")

def confirm(prompt: str, default: bool = False) -> bool:
    """Y/N confirmation prompt."""
    suffix = " [Y/n]: " if default else " [y/N]: "
    response = input(prompt + suffix).strip().lower()
    if not response:
        return default
    return response in ('y', 'yes')
```

### Dry Run Support

The `--dry-run` flag should be supported at the subprocess level, not by duplicating logic. The pattern:

```python
# builder.py
def run_build(klipper_dir: Path, jobs: int | None = None, dry_run: bool = False) -> None:
    cmd = ['make', f'-j{jobs or get_cpu_count()}']
    if dry_run:
        print(f"[DRY RUN] Would run: {' '.join(cmd)} in {klipper_dir}")
        return
    # actual execution...
```

The orchestrator passes `dry_run` down to every module function. This is explicit and simple. No global state, no monkeypatching.

---

## Recommended File Layout

Based on the analysis above, the final module structure is:

```
klipper-flash/
├── flash.py              # Orchestrator: CLI parsing, workflow sequencing, user interaction
├── discovery.py          # USB device scanning and pattern matching
├── registry.py           # Device registry (devices.json CRUD) + DeviceEntry dataclass
├── config_manager.py     # Config caching, hashing, change detection
├── builder.py            # make menuconfig / clean / build subprocess calls
├── flasher.py            # Flash execution + klipper service lifecycle (context manager)
├── errors.py             # All custom exception classes
├── devices.json          # Device registry data
└── configs/              # Per-device cached .config + .sha256 files
```

**Notable addition: `errors.py`.** A centralized exceptions module prevents circular imports and gives the orchestrator a single import target. It is small (under 50 lines) and avoids the need for any module to import from another module just for exception types.

**Notable absence: `utils.py`.** Resist the temptation to create a catch-all utils module. If a function is used by exactly one module, it belongs in that module. The only shared abstractions are the dataclasses (in `registry.py`) and exceptions (in `errors.py`).

---

## Scalability and Future-Proofing

### Adding New Flash Methods

The current design supports `make_flash` and `katapult`. Future methods (CAN bus, DFU, etc.) can be added by:

1. Adding the method name to `DeviceEntry.flash_method`
2. Adding a `_flash_<method>()` function in `flasher.py`
3. Adding a dispatch case in `flash_device()`

No architectural changes needed. The dispatch is in one function in one module.

### Adding Batch Flash

The brief mentions batch flash as a future feature. The current architecture supports this cleanly:

```python
# Future: flash all devices
def cmd_flash_all(args):
    registry = Registry(REGISTRY_PATH)
    for device in registry.list_all():
        path = discovery.find_device_path(device.serial_pattern)
        if path:
            # Each device gets its own service lifecycle
            flasher.flash_device(device, path)
```

The `klipper_stopped()` context manager means klipper is stopped/started per device. For batch, you would want a variant that stops once and starts once:

```python
with klipper_stopped():
    for device in devices:
        _flash_single(device, path)  # inner flash without service management
```

This refactor is straightforward when the service lifecycle is already isolated in a context manager.

### Adding Moonraker Integration

Future Moonraker/Fluidd integration would add a new entry point (a Moonraker component) that calls the same module functions. Because the orchestrator is separate from the module logic, a web API can compose the same building blocks without touching any existing module code.

---

## Key Architectural Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Module communication | Hub-and-spoke via orchestrator | Prevents inter-module coupling, easy to test |
| Data contracts | `dataclasses` | Stdlib, typed, serializable |
| Error handling | Domain exceptions + context manager for service | Guarantees klipper restart invariant |
| Subprocess execution | Consistent wrapper, `capture=False` for TUI | Handles menuconfig special case cleanly |
| State management | JSON file for registry, filesystem for configs | No database dependency, human-readable |
| User interaction | Isolated in orchestrator only | Modules stay testable, no hidden I/O |
| Dry run support | Passed as parameter, not global state | Explicit, no action-at-a-distance |
| Exception location | Centralized `errors.py` | Prevents circular imports |

---

## Sources and Confidence

| Area | Confidence | Basis |
|------|------------|-------|
| Module decomposition | HIGH | Standard Python package design patterns, well-understood domain |
| Context manager for service lifecycle | HIGH | Established Python pattern for guaranteed cleanup; `contextlib.contextmanager` is stdlib |
| Dataclass-based data contracts | HIGH | `dataclasses` available since Python 3.7, target is 3.9+ |
| Hub-and-spoke orchestration | HIGH | Standard CLI architecture; avoids coupling in small tools |
| Subprocess handling for ncurses | HIGH | `subprocess.run()` with inherited stdio is the documented approach for interactive subprocesses |
| Error propagation strategy | HIGH | Standard Python exception hierarchy pattern |

---

---

# v2.0 Architecture Integration

**Updated:** 2026-01-26
**Focus:** How v2.0 features integrate with existing hub-and-spoke architecture

This section documents how new v2.0 features integrate with the existing kalico-flash architecture while preserving the hub-and-spoke pattern, stdlib-only constraint, and dataclass contracts.

---

## Current v1.0 Architecture Recap

The implemented v1.0 architecture follows the patterns above with these actual modules:

```
kalico-flash/
├── flash.py       # CLI hub: argument parsing, cmd_* functions, orchestration
├── models.py      # Dataclass contracts (DeviceEntry, BuildResult, FlashResult, etc.)
├── errors.py      # Exception hierarchy (KlipperFlashError base)
├── output.py      # Pluggable output interface (Output protocol, CliOutput)
├── registry.py    # Device registry with atomic JSON persistence
├── discovery.py   # USB scanning and pattern matching
├── config.py      # Kconfig caching and MCU validation
├── build.py       # menuconfig TUI and firmware compilation
├── service.py     # Klipper service lifecycle (context manager)
└── flasher.py     # Dual-method flash operations (Katapult + make_flash)
```

**Key observations from implemented code:**
- `output.py` provides a `Protocol`-based pluggable output interface (CLI, future Moonraker)
- `models.py` is the central dataclass location (not in registry.py as originally planned)
- `config.py` (not `config_manager.py`) handles Kconfig caching with XDG paths
- Flash workflow is orchestrated through `cmd_flash()` in flash.py

---

## New Modules for v2.0

### tui.py - Interactive Menu System

**Responsibility:** Curses-based menu for interactive mode when running without arguments.

**Why new module:** Distinct UI mode that wraps existing `cmd_*` functions. Keeps curses complexity isolated from the CLI orchestrator.

**Integration with existing architecture:**
```
User runs: python flash.py (no args, TTY detected)
    |
    v
flash.py (main) -> detects no args + TTY
    |
    v
from tui import run_tui_menu
run_tui_menu(registry, out) -> displays menu
    |
    v (user selects action)
    |
returns to flash.py which calls appropriate cmd_* function
```

**Implementation approach using stdlib curses:**
```python
# tui.py
"""Interactive TUI menu for kalico-flash."""
from __future__ import annotations

import curses
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from registry import Registry
    from output import Output

MENU_OPTIONS = [
    ("Flash a device", "flash"),
    ("List devices", "list"),
    ("Add device", "add"),
    ("Remove device", "remove"),
    ("Exit", "exit"),
]


def run_tui_menu(registry: 'Registry', out: 'Output') -> tuple[str, str | None]:
    """Display interactive menu and return selected action.

    Returns:
        (action, device_key) tuple where action is one of:
        "flash", "list", "add", "remove", "exit"
        device_key is set only for "flash" action.
    """
    return curses.wrapper(_menu_loop, registry)


def _menu_loop(stdscr, registry: 'Registry') -> tuple[str, str | None]:
    """Main menu loop inside curses wrapper."""
    curses.curs_set(0)  # Hide cursor
    stdscr.keypad(True)  # Enable arrow keys

    current_row = 0

    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "kalico-flash", curses.A_BOLD)
        stdscr.addstr(1, 0, "-" * 40)

        for idx, (label, _) in enumerate(MENU_OPTIONS):
            if idx == current_row:
                stdscr.addstr(idx + 3, 2, f"> {label}", curses.A_REVERSE)
            else:
                stdscr.addstr(idx + 3, 4, label)

        stdscr.refresh()
        key = stdscr.getch()

        if key == curses.KEY_UP and current_row > 0:
            current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(MENU_OPTIONS) - 1:
            current_row += 1
        elif key in (curses.KEY_ENTER, ord('\n'), ord(' ')):
            _, action = MENU_OPTIONS[current_row]
            if action == "flash":
                # Sub-menu to select device
                device_key = _select_device(stdscr, registry)
                return (action, device_key)
            return (action, None)
        elif key == ord('q'):
            return ("exit", None)
```

**Data flow:**
- TUI reads from Registry to display device list
- TUI returns action string to flash.py
- flash.py calls appropriate cmd_* function
- Normal workflow executes with existing modules

**Does NOT cross-import:** Only imports registry and output types for type hints.

---

### moonraker.py - Moonraker API Client

**Responsibility:** HTTP client for Moonraker API to check print status and query MCU versions.

**Why new module:** External service communication is isolated. Keeps networking code separate from core flash logic.

**Moonraker API endpoints needed:**

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/printer/info` | GET | Check Klipper state | `{"state": "ready", ...}` |
| `/printer/objects/query` | POST | Get print_stats | `{"status": {"print_stats": {"state": "..."}}}` |
| `/printer/objects/query` | POST | Get MCU version | `{"status": {"mcu": {"mcu_version": "..."}}}` |

**Implementation using stdlib urllib:**
```python
# moonraker.py
"""Moonraker API client for kalico-flash."""
from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Optional
from dataclasses import dataclass

from errors import MoonrakerError


@dataclass
class PrintStatus:
    """Print status from Moonraker."""
    state: str  # "standby", "printing", "paused", "complete", "error", "cancelled"
    filename: str

    @property
    def is_printing(self) -> bool:
        return self.state == "printing"

    @property
    def is_active(self) -> bool:
        """True if print is active (printing or paused)."""
        return self.state in ("printing", "paused")


@dataclass
class McuVersion:
    """MCU firmware version info."""
    mcu_name: str   # "mcu" or custom name
    version: str    # "v0.12.0-272-g13c75ea87"
    build_info: str # gcc/binutils versions


class MoonrakerClient:
    """HTTP client for Moonraker API."""

    def __init__(self, base_url: str = "http://localhost:7125", timeout: int = 5):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def is_available(self) -> bool:
        """Check if Moonraker is reachable."""
        try:
            self._get("/printer/info")
            return True
        except MoonrakerError:
            return False

    def get_print_status(self) -> PrintStatus:
        """Get current print status."""
        data = self._post("/printer/objects/query", {
            "objects": {"print_stats": None}
        })
        stats = data.get("status", {}).get("print_stats", {})
        return PrintStatus(
            state=stats.get("state", "standby"),
            filename=stats.get("filename", ""),
        )

    def get_mcu_versions(self) -> list[McuVersion]:
        """Get firmware versions for all MCUs."""
        # First get list of MCUs from printer info
        info = self._get("/printer/info")
        # Query mcu object
        data = self._post("/printer/objects/query", {
            "objects": {"mcu": None}
        })
        mcu_data = data.get("status", {}).get("mcu", {})
        return [McuVersion(
            mcu_name="mcu",
            version=mcu_data.get("mcu_version", "unknown"),
            build_info=mcu_data.get("mcu_build_versions", ""),
        )]

    def _get(self, endpoint: str) -> dict:
        """HTTP GET request."""
        url = f"{self.base_url}{endpoint}"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.URLError as e:
            raise MoonrakerError(f"Cannot reach Moonraker at {self.base_url}: {e}")
        except json.JSONDecodeError as e:
            raise MoonrakerError(f"Invalid JSON response: {e}")

    def _post(self, endpoint: str, data: dict) -> dict:
        """HTTP POST request with JSON body."""
        url = f"{self.base_url}{endpoint}"
        try:
            body = json.dumps(data).encode()
            req = urllib.request.Request(url, data=body, method='POST')
            req.add_header('Content-Type', 'application/json')
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.URLError as e:
            raise MoonrakerError(f"Cannot reach Moonraker at {self.base_url}: {e}")
        except json.JSONDecodeError as e:
            raise MoonrakerError(f"Invalid JSON response: {e}")
```

**Integration with flash workflow:**
```python
# In flash.py cmd_flash(), before flash phase:

# Pre-flight: Check Moonraker for active print
try:
    from moonraker import MoonrakerClient
    client = MoonrakerClient(data.global_config.moonraker_url)
    if client.is_available():
        status = client.get_print_status()
        if status.is_active:
            out.error(f"Cannot flash while printing: {status.filename}")
            out.error("Wait for print to complete or cancel it first.")
            return 1
except MoonrakerError as e:
    out.warn(f"Could not check print status: {e}")
    # Continue anyway - Moonraker being down shouldn't block flash
```

**Graceful degradation:** If Moonraker is unreachable, warn but allow flash to proceed.

---

### messages.py - Error Message Templates

**Responsibility:** Centralized error messages with recovery guidance.

**Why new module:** Consistent error UX across all commands. Single place to update messaging.

**Implementation:**
```python
# messages.py
"""Error message templates with recovery guidance."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from output import Output


# Error message templates
# Keys match exception types or error conditions
MESSAGES = {
    "device_disconnected": {
        "title": "Device Disconnected",
        "detail": "Device '{device_key}' was unplugged during the operation.",
        "recovery": [
            "Reconnect the USB cable",
            "Check that the board has power (LED should be on)",
            "Run --list-devices to verify connection",
        ],
    },
    "mcu_mismatch": {
        "title": "MCU Type Mismatch",
        "detail": "Config has '{actual}' but device '{device_key}' expects '{expected}'.",
        "recovery": [
            "Run menuconfig and select the correct MCU type",
            "Or update device registration if MCU changed",
        ],
    },
    "build_timeout": {
        "title": "Build Timeout",
        "detail": "Build did not complete within {timeout} seconds.",
        "recovery": [
            "Check for compiler errors in output above",
            "Try running 'make clean' manually in klipper directory",
            "Ensure sufficient disk space",
        ],
    },
    "flash_timeout": {
        "title": "Flash Timeout",
        "detail": "Flash did not complete within {timeout} seconds.",
        "recovery": [
            "Power cycle the board (unplug and replug USB)",
            "Check if board is in bootloader mode",
            "Try manual flash with 'make flash'",
        ],
    },
    "print_in_progress": {
        "title": "Print In Progress",
        "detail": "Cannot flash while printing '{filename}'.",
        "recovery": [
            "Wait for print to complete",
            "Or cancel the print in Fluidd/Mainsail first",
        ],
    },
    "klipper_stop_failed": {
        "title": "Failed to Stop Klipper",
        "detail": "Could not stop klipper.service: {error}",
        "recovery": [
            "Check if you have passwordless sudo configured",
            "Run 'sudo systemctl stop klipper' manually",
        ],
    },
    "katapult_not_found": {
        "title": "Katapult Not Found",
        "detail": "Katapult flashtool not found at {path}.",
        "recovery": [
            "Verify Katapult is installed at the configured path",
            "Or change device flash_method to 'make_flash'",
        ],
    },
}


def format_error(key: str, **context) -> str:
    """Format error message with context.

    Returns formatted string with title, detail, and recovery steps.
    """
    if key not in MESSAGES:
        return f"Unknown error: {key}"

    msg = MESSAGES[key]
    lines = []
    lines.append(msg["title"])
    lines.append(msg["detail"].format(**context))
    lines.append("")
    lines.append("Recovery steps:")
    for step in msg["recovery"]:
        lines.append(f"  - {step}")

    return "\n".join(lines)


def print_error_with_recovery(out: 'Output', key: str, **context) -> None:
    """Print formatted error through output interface."""
    if key not in MESSAGES:
        out.error(f"Unknown error: {key}")
        return

    msg = MESSAGES[key]
    out.error(msg["title"])
    out.error(msg["detail"].format(**context))
    out.info("Recovery", "Steps to fix:")
    for step in msg["recovery"]:
        out.info("", f"  - {step}")
```

---

## Modified Modules for v2.0

### flash.py - Hub Changes

**Changes needed:**

1. **TUI entry point** when no args and TTY
2. **New CLI flags:** `--skip-menuconfig`, `--no-clean`
3. **Moonraker pre-check** before flash
4. **Post-flash verification** call

**Modified main() function:**
```python
def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    from output import CliOutput
    from registry import Registry

    out = CliOutput()
    registry_path = Path(__file__).parent / "devices.json"
    registry = Registry(str(registry_path))

    try:
        # Handle management commands
        if args.add_device:
            return cmd_add_device(registry, out)
        elif args.list_devices:
            return cmd_list_devices(registry, out)
        elif args.remove_device:
            return cmd_remove_device(registry, args.remove_device, out)

        # Handle flash workflow
        if args.device:
            # Explicit --device KEY mode
            return cmd_flash(registry, args.device, out,
                           skip_menuconfig=args.skip_menuconfig,
                           no_clean=args.no_clean)

        # No args: TUI mode if TTY, otherwise error
        if sys.stdin.isatty():
            from tui import run_tui_menu
            action, device_key = run_tui_menu(registry, out)
            if action == "exit":
                return 0
            elif action == "flash":
                return cmd_flash(registry, device_key, out)
            elif action == "list":
                return cmd_list_devices(registry, out)
            elif action == "add":
                return cmd_add_device(registry, out)
            elif action == "remove":
                # TUI would need sub-menu for device selection
                return cmd_remove_device(registry, device_key, out)
        else:
            out.error("Interactive terminal required. Use --device KEY.")
            return 1

    except KeyboardInterrupt:
        print("\nAborted.")
        return 130
    except KlipperFlashError as e:
        out.error(str(e))
        return 1
```

**Modified cmd_flash() signature:**
```python
def cmd_flash(registry, device_key: str, out,
              skip_menuconfig: bool = False,
              no_clean: bool = False) -> int:
```

**New args in build_parser():**
```python
parser.add_argument(
    "--skip-menuconfig",
    action="store_true",
    help="Skip menuconfig if cached config exists",
)
parser.add_argument(
    "--no-clean",
    action="store_true",
    help="Skip 'make clean' for incremental builds",
)
```

---

### registry.py - Schema Evolution

**Changes needed:**

1. Add `flashable` field to DeviceEntry (default True)
2. Add `moonraker_url` to GlobalConfig
3. Backward-compatible loading of old format

**DeviceEntry changes in models.py:**
```python
@dataclass
class DeviceEntry:
    key: str
    name: str
    mcu: Optional[str]  # Changed: Allow None for non-flashable devices
    serial_pattern: str
    flash_method: Optional[str] = None
    flashable: bool = True  # NEW: False for Beacon-like devices


@dataclass
class GlobalConfig:
    klipper_dir: str = "~/klipper"
    katapult_dir: str = "~/katapult"
    default_flash_method: str = "katapult"
    moonraker_url: str = "http://localhost:7125"  # NEW
```

**registry.py load() changes:**
```python
def load(self) -> RegistryData:
    # ... existing code ...
    for key, data in raw.get("devices", {}).items():
        devices[key] = DeviceEntry(
            key=key,
            name=data["name"],
            mcu=data.get("mcu"),  # Changed: get() for optional
            serial_pattern=data["serial_pattern"],
            flash_method=data.get("flash_method"),
            flashable=data.get("flashable", True),  # NEW with default
        )
    # ... existing code ...
```

**Updated JSON schema:**
```json
{
  "global": {
    "klipper_dir": "~/klipper",
    "katapult_dir": "~/katapult",
    "default_flash_method": "katapult",
    "moonraker_url": "http://localhost:7125"
  },
  "devices": {
    "octopus-pro": {
      "name": "Octopus Pro v1.1",
      "mcu": "stm32h723",
      "serial_pattern": "usb-Klipper_stm32h723xx_*",
      "flashable": true
    },
    "beacon": {
      "name": "Beacon Probe",
      "mcu": null,
      "serial_pattern": "usb-Beacon_*",
      "flashable": false
    }
  }
}
```

---

### flasher.py - Post-Flash Verification

**Add new function:**
```python
def verify_flash_success(
    serial_pattern: str,
    timeout: int = 30,
    poll_interval: float = 1.0,
) -> tuple[bool, str]:
    """Wait for device to reappear with Klipper serial after flash.

    Polls /dev/serial/by-id/ until a device matching the pattern
    appears with "Klipper_" prefix, indicating successful flash.

    Args:
        serial_pattern: Glob pattern to match
        timeout: Seconds to wait
        poll_interval: Seconds between polls

    Returns:
        (success, device_path) tuple
    """
    from discovery import scan_serial_devices, match_device
    import time

    # Convert pattern to look for Klipper_ prefix
    klipper_pattern = serial_pattern.replace("usb-katapult_", "usb-Klipper_")
    if not klipper_pattern.startswith("usb-Klipper_"):
        klipper_pattern = "usb-Klipper_*"  # Fallback to any Klipper device

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        devices = scan_serial_devices()
        matched = match_device(klipper_pattern, devices)
        if matched:
            return True, matched.path
        time.sleep(poll_interval)

    return False, ""
```

**Integration in cmd_flash():**
```python
# After flash_result.success:
if flash_result.success:
    out.phase("Verify", "Waiting for device to reappear...")
    verified, new_path = verify_flash_success(entry.serial_pattern)
    if verified:
        out.phase("Verify", f"Device confirmed at {new_path}")
    else:
        out.warn("Device did not reappear within 30s - check manually")
```

---

### build.py - Incremental Build Support

**Modify run_build() signature:**
```python
def run_build(klipper_dir: str, timeout: int = TIMEOUT_BUILD,
              clean: bool = True) -> BuildResult:
    """Run make build with optional clean step.

    Args:
        klipper_dir: Path to klipper source
        timeout: Build timeout in seconds
        clean: If True, run 'make clean' first. If False, incremental.
    """
    klipper_path = Path(klipper_dir).expanduser()
    start_time = time.monotonic()

    if clean:
        # Run make clean with inherited stdio
        try:
            clean_result = subprocess.run(
                ["make", "clean"],
                cwd=str(klipper_path),
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return BuildResult(
                success=False,
                elapsed_seconds=time.monotonic() - start_time,
                error_message=f"make clean timed out",
            )

        if clean_result.returncode != 0:
            return BuildResult(
                success=False,
                elapsed_seconds=time.monotonic() - start_time,
                error_message=f"make clean failed",
            )

    # Run make -j with all available cores
    # ... rest unchanged ...
```

---

### discovery.py - Filter Flashable Devices

**Add helper function:**
```python
def filter_flashable_devices(
    matched: list[tuple['DeviceEntry', 'DiscoveredDevice']]
) -> list[tuple['DeviceEntry', 'DiscoveredDevice']]:
    """Filter matched devices to only include flashable ones.

    Used in interactive selection to exclude Beacon-like devices
    that should not be flashed through this tool.
    """
    return [(entry, device) for entry, device in matched
            if getattr(entry, 'flashable', True)]
```

---

## New Exceptions (errors.py)

```python
class MoonrakerError(KlipperFlashError):
    """Moonraker API communication failures."""
    pass


class PrintInProgressError(KlipperFlashError):
    """Attempted flash while print is active."""

    def __init__(self, filename: str, state: str):
        super().__init__(
            f"Cannot flash while printing. State: {state}, file: {filename}"
        )
        self.filename = filename
        self.state = state


class VerificationError(KlipperFlashError):
    """Post-flash device verification failed."""

    def __init__(self, pattern: str, timeout: int):
        super().__init__(
            f"Device did not reappear within {timeout}s. Pattern: {pattern}"
        )
        self.pattern = pattern
        self.timeout = timeout
```

---

## New Dataclasses (models.py)

```python
@dataclass
class PrintStatus:
    """Moonraker print status."""
    state: str  # "standby", "printing", "paused", "complete", "error", "cancelled"
    filename: str

    @property
    def is_printing(self) -> bool:
        return self.state == "printing"

    @property
    def is_active(self) -> bool:
        return self.state in ("printing", "paused")


@dataclass
class McuVersion:
    """MCU firmware version from Moonraker."""
    mcu_name: str
    version: str
    build_info: str


@dataclass
class VerifyResult:
    """Result of post-flash verification."""
    success: bool
    device_path: Optional[str] = None
    elapsed_seconds: float = 0.0
```

---

## Build Order for v2.0 Features

Implementation sequence based on dependencies:

### Phase 1: Foundation Changes (no new modules)
1. **models.py** - Add new dataclasses, modify DeviceEntry/GlobalConfig
2. **errors.py** - Add MoonrakerError, PrintInProgressError, VerificationError
3. **registry.py** - Backward-compatible schema changes

### Phase 2: Moonraker Integration
4. **moonraker.py** - New module (depends on models, errors)
5. **flash.py** - Add pre-flash Moonraker check

### Phase 3: Build Improvements
6. **build.py** - Add `clean` parameter to run_build()
7. **flash.py** - Add `--skip-menuconfig`, `--no-clean` flags

### Phase 4: Post-Flash Verification
8. **flasher.py** - Add verify_flash_success() function
9. **flash.py** - Integrate verification after flash

### Phase 5: TUI Menu
10. **tui.py** - New module (depends on registry, output)
11. **flash.py** - Add TUI entry point in main()

### Phase 6: Error UX
12. **messages.py** - New module (standalone)
13. **flash.py** - Use message templates for errors

### Phase 7: Device Exclusion
14. **discovery.py** - Add filter_flashable_devices()
15. **flash.py** - Filter in interactive selection
16. **cmd_add_device** - Add flashable prompt

---

## v2.0 Integration Diagram

```
                              +----------------+
                              |    ENTRY       |
                              +-------+--------+
                                      |
                    +--------+--------+--------+--------+
                    |        |        |        |        |
              no args     --device  --add   --list   --remove
              + TTY         KEY     -device -devices  -device
                    |        |        |        |        |
                    v        |        |        |        |
               +----+----+   |        |        |        |
               | tui.py  |<--+        |        |        |  NEW
               | (menu)  |   |        |        |        |
               +---------+   |        |        |        |
                    |        |        |        |        |
                    +--------+--------+--------+--------+
                                      |
                              +-------v--------+
                              |   flash.py     |
                              |  (cmd_flash)   |
                              +-------+--------+
                                      |
        +-----------------------------+
        |                             |
        v                             v
+-------+-------+            +--------+--------+
| moonraker.py  |<-- NEW     |   WORKFLOW      |
| (pre-check)   |            |                 |
+---------------+            +--------+--------+
                                      |
        +------------+----------------+----------------+------------+
        |            |                |                |            |
        v            v                v                v            v
+-------+---+ +------+-----+  +-------+------+  +------+-----+ +----+------+
|discovery  | |  config    |  |    build     |  |  service   | |  flasher  |
|(scan,     | |(load/save, |  |(menuconfig,  |  |(stop/start)| |(flash,    |
| filter)   | | validate)  |  | compile)     |  |            | | verify)   | <-- MODIFIED
+-----------+ +------------+  +--------------+  +------------+ +-----------+
                                      |
        ^                             |
        |                     +-------+-------+
        |                     | messages.py   |<-- NEW
        +---------------------| (error fmt)   |
                              +---------------+
                                      |
                              +-------v--------+
                              |   models.py    |<-- MODIFIED
                              | (dataclasses)  |
                              +----------------+
                                      |
                              +-------v--------+
                              |   errors.py    |<-- MODIFIED
                              | (exceptions)   |
                              +----------------+
```

---

## Summary: v2.0 Changes by Component

| Component | Status | Changes |
|-----------|--------|---------|
| `tui.py` | **NEW** | Curses menu for interactive mode |
| `moonraker.py` | **NEW** | HTTP client for print status, MCU versions |
| `messages.py` | **NEW** | Error message templates with recovery |
| `flash.py` | MODIFIED | TUI entry, Moonraker check, new flags, verify call |
| `models.py` | MODIFIED | PrintStatus, McuVersion, VerifyResult; GlobalConfig.moonraker_url; DeviceEntry.flashable |
| `errors.py` | MODIFIED | MoonrakerError, PrintInProgressError, VerificationError |
| `registry.py` | MODIFIED | Schema v2 with backward compat |
| `flasher.py` | MODIFIED | verify_flash_success() function |
| `discovery.py` | MODIFIED | filter_flashable_devices() helper |
| `build.py` | MODIFIED | Optional `clean` parameter |
| `output.py` | UNCHANGED | Existing protocol sufficient |
| `service.py` | UNCHANGED | No changes needed |
| `config.py` | UNCHANGED | No changes needed |

---

## Architecture Principles Preserved

1. **Hub-and-spoke:** All new modules (tui, moonraker, messages) are spokes called from flash.py
2. **No cross-imports:** New modules import only models.py, errors.py, not each other
3. **Dataclass contracts:** All new cross-module data uses dataclasses
4. **Stdlib only:** curses and urllib.request are stdlib
5. **Late imports:** New modules loaded only when needed
6. **Graceful degradation:** Moonraker failures warn but don't block

---

## Sources

- [Python curses documentation](https://docs.python.org/3/library/curses.html) - HIGH confidence
- [Moonraker Printer Objects](https://moonraker.readthedocs.io/en/latest/printer_objects/) - HIGH confidence
- [Moonraker External API](https://moonraker.readthedocs.io/en/latest/external_api/printer/) - HIGH confidence
- Existing kalico-flash v1.0 codebase analysis - HIGH confidence
