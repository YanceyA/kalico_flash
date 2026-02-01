# Architecture Patterns: Test Framework for kalico-flash

**Domain:** Test suite integration for existing Python TUI tool
**Researched:** 2026-02-01
**Overall confidence:** HIGH (based on direct source code analysis of all modules)

## Testability Analysis by Module

### Tier 1: Pure Functions (Zero Mocking, Highest ROI)

These functions take inputs and return outputs with no side effects. Test first.

| Module | Function | What It Does | Test Complexity |
|--------|----------|-------------|-----------------|
| `discovery.py` | `is_supported_device(filename)` | Prefix check against string | Trivial |
| `discovery.py` | `match_device(pattern, devices)` | fnmatch against DiscoveredDevice list | Trivial |
| `discovery.py` | `match_devices(pattern, devices)` | fnmatch, returns all matches | Trivial |
| `discovery.py` | `find_registered_devices(devices, registry_devices)` | Cross-reference two lists | Low |
| `discovery.py` | `extract_mcu_from_serial(filename)` | Regex extraction | Trivial |
| `discovery.py` | `generate_serial_pattern(filename)` | Regex replace + wildcard | Trivial |
| `config.py` | `parse_mcu_from_config(config_path)` | Regex on file content | Low (needs temp file) |
| `validation.py` | `validate_numeric_setting(raw, min, max)` | Parse + range check | Trivial |
| `validation.py` | `generate_device_key(name, registry)` | Unicode normalization + slug | Low (needs mock registry.get) |
| `validation.py` | `validate_device_key(key, registry, current_key)` | Regex + registry lookup | Low (needs mock registry.get) |
| `moonraker.py` | `detect_firmware_flavor(version)` | Regex classification | Trivial |
| `moonraker.py` | `_parse_git_describe(version)` | Regex parse to tuple | Trivial |
| `moonraker.py` | `is_mcu_outdated(host, mcu)` | Compare parsed versions | Trivial |
| `flash.py` | `_normalize_pattern(pattern)` | strip + lower | Trivial |
| `flash.py` | `_build_blocked_list(registry_data)` | Combine defaults + registry | Low |
| `flash.py` | `_blocked_reason_for_filename(filename, blocked_list)` | fnmatch against blocked list | Trivial |
| `flash.py` | `_blocked_reason_for_entry(entry, blocked_list)` | fnmatch bidirectional | Low |
| `flash.py` | `_resolve_flash_method(entry, global_config)` | String resolution with fallback | Trivial |
| `flash.py` | `_short_path(path_value)` | Path.name extraction | Trivial |
| `errors.py` | `format_error(...)` | String formatting | Trivial |
| `errors.py` | `get_recovery_text(template_key)` | Dict lookup | Trivial |
| `models.py` | All dataclasses | Construction, field access | Trivial |

**Count: ~22 pure functions.** This is the bulk of testable logic and should be Phase 1.

### Tier 2: Filesystem Dependencies (Need tmpdir Fixtures)

| Module | Class/Function | Dependency | Fixture Strategy |
|--------|---------------|------------|-----------------|
| `registry.py` | `Registry` (all methods) | JSON file read/write | `tmp_path` with sample devices.json |
| `config.py` | `ConfigManager` | Two directories (cache + klipper) | `tmp_path` with mock .config files |
| `config.py` | `get_config_dir(device_key)` | `XDG_CONFIG_HOME` env var | `monkeypatch.setenv` |
| `config.py` | `rename_device_config_cache(old, new)` | Directory rename | `tmp_path` |
| `config.py` | `_atomic_copy(src, dst)` | Temp file + fsync + rename | `tmp_path` |
| `validation.py` | `validate_path_setting(raw, key)` | `os.path.isdir`, `os.path.isfile` | `tmp_path` with mock dirs |

**Note:** `Registry` is highly testable with tmpdir -- constructor takes `registry_path: str`, so just point it at a temp file. No seam changes needed.

**Note:** `ConfigManager.__init__` takes `device_key` and `klipper_dir` -- fully injectable. Set `XDG_CONFIG_HOME` via monkeypatch to control cache_path.

### Tier 3: Subprocess Dependencies (Need unittest.mock)

| Module | Function | Subprocess Call | Mock Strategy |
|--------|----------|----------------|--------------|
| `build.py` | `run_menuconfig()` | `make menuconfig` (inherited stdio) | Mock `subprocess.run`, verify args |
| `build.py` | `run_build()` | `make clean` + `make -jN` | Mock `subprocess.run`, return codes |
| `flasher.py` | `_try_katapult_flash()` | `python3 flashtool.py` | Mock `subprocess.run` |
| `flasher.py` | `_try_make_flash()` | `make flash` | Mock `subprocess.run` |
| `flasher.py` | `flash_device()` | Delegates to above two | Mock the two inner functions |
| `flasher.py` | `check_katapult()` | `flashtool.py -r` + sysfs | Complex -- mock subprocess + filesystem |
| `flasher.py` | `_usb_sysfs_reset()` | `sudo tee` | Mock `subprocess.run` |
| `service.py` | `verify_passwordless_sudo()` | `sudo -n true` | Mock `subprocess.run` |
| `service.py` | `_stop_klipper()` | `sudo systemctl stop` | Mock `subprocess.run` |
| `service.py` | `_start_klipper()` | `sudo systemctl start` | Mock `subprocess.run` |
| `service.py` | `klipper_service_stopped()` | Context manager wrapping above | Mock stop/start |
| `moonraker.py` | `get_host_klipper_version()` | `git describe` | Mock `subprocess.run` |

### Tier 4: Network Dependencies (Need urllib mock)

| Module | Function | Network Call | Mock Strategy |
|--------|----------|-------------|--------------|
| `moonraker.py` | `get_print_status()` | `urlopen` to localhost:7125 | Mock `urllib.request.urlopen` |
| `moonraker.py` | `get_mcu_versions()` | Two `urlopen` calls | Mock `urlopen` with JSON responses |
| `moonraker.py` | `get_mcu_version_for_device()` | Calls `get_mcu_versions()` | Mock `get_mcu_versions` directly |

### Tier 5: TUI-Coupled (Skip or Minimal Testing)

| Module | Reason to Skip |
|--------|---------------|
| `tui.py` | Main loop, input handling, screen rendering -- deeply interactive |
| `screen.py` | Device config screen -- curses-like interaction |
| `panels.py` | Panel rendering -- visual output, low logic |
| `ansi.py` | ANSI escape codes -- trivial utilities |
| `theme.py` | Color constants -- no logic |
| `flash.py` `cmd_flash()` | 400+ line orchestrator with TUI imports, interactive prompts |
| `flash.py` `cmd_flash_all()` | Similar -- deeply coupled to user interaction |
| `flash.py` `cmd_add_device()` | Interactive wizard with multiple prompts |

**Exception:** `cmd_build()` in flash.py is moderately testable with mocked registry, config manager, build module, and NullOutput. Worth considering for Phase 3.

## Existing Test Seams (No Refactoring Needed)

The architecture is already well-suited for testing:

1. **`Registry(registry_path: str)`** -- Path injection via constructor. Point at tmpdir.
2. **`ConfigManager(device_key, klipper_dir)`** -- Both params injectable. Set `XDG_CONFIG_HOME` for cache path.
3. **`Output` Protocol + `NullOutput`** -- Already exists in output.py. Perfect for suppressing output in tests.
4. **Dataclass contracts** -- All cross-module data uses plain dataclasses. Easy to construct test fixtures.
5. **Hub-and-spoke architecture** -- Modules don't cross-import (except flash.py importing everything). Each module testable in isolation.
6. **`discovery.py` functions accept lists** -- `match_device(pattern, devices)` takes a device list, not scanning the filesystem. Pure by design.

## Seams That Would Improve Testability (Small Refactors)

### Seam 1: `scan_serial_devices()` hardcodes `/dev/serial/by-id`

**Current:** `SERIAL_BY_ID = "/dev/serial/by-id"` module constant, used directly.
**Improvement:** Add optional `serial_dir` parameter with default.
**Impact:** Enables testing scan logic with tmpdir instead of mocking Path.iterdir.
**Priority:** LOW -- callers already use the pure `match_device`/`find_registered_devices` with injected lists.

### Seam 2: `moonraker.py` hardcodes `MOONRAKER_URL`

**Current:** Module-level constant `http://localhost:7125`.
**Improvement:** Not needed for testing -- mock `urlopen` at the urllib level.
**Priority:** SKIP -- mocking urlopen is standard and sufficient.

### Seam 3: `flash.py` orchestrators do late imports

**Current:** `cmd_flash()` does `from .discovery import scan_serial_devices` inside function body.
**Improvement:** These are already mockable via `unittest.mock.patch`. No change needed.
**Priority:** SKIP.

## Recommended Test Directory Structure

```
tests/
    __init__.py
    conftest.py                    # Shared fixtures: factories, tmp registry, NullOutput
    test_models.py                 # Dataclass construction, field defaults
    test_discovery.py              # Pure matching/extraction functions
    test_validation.py             # Slug generation, input validation
    test_moonraker_parsing.py      # detect_firmware_flavor, _parse_git_describe, is_mcu_outdated
    test_errors.py                 # format_error, ERROR_TEMPLATES
    test_flash_helpers.py          # _normalize_pattern, _blocked_reason_*, _resolve_flash_method
    test_registry.py               # Registry CRUD with tmpdir
    test_config.py                 # ConfigManager with tmpdir, parse_mcu_from_config
    test_build.py                  # run_build, run_menuconfig with mocked subprocess
    test_flasher.py                # flash_device, _try_katapult_flash with mocked subprocess
    test_service.py                # klipper_service_stopped with mocked subprocess
    test_moonraker_api.py          # get_print_status, get_mcu_versions with mocked urlopen
```

## Fixture Strategy (conftest.py)

```python
# Key fixtures for conftest.py:

# 1. Dataclass factories
def make_device_entry(**overrides) -> DeviceEntry:
    defaults = {
        "key": "test-device",
        "name": "Test Device",
        "mcu": "stm32h723",
        "serial_pattern": "usb-Klipper_stm32h723xx_TEST*",
    }
    defaults.update(overrides)
    return DeviceEntry(**defaults)

def make_discovered_device(**overrides) -> DiscoveredDevice:
    defaults = {
        "path": "/dev/serial/by-id/usb-Klipper_stm32h723xx_TEST-if00",
        "filename": "usb-Klipper_stm32h723xx_TEST-if00",
    }
    defaults.update(overrides)
    return DiscoveredDevice(**defaults)

# 2. Registry fixture (tmpdir-based)
@pytest.fixture
def tmp_registry(tmp_path):
    path = tmp_path / "devices.json"
    return Registry(str(path))

# 3. Config fixture (tmpdir-based)
@pytest.fixture
def tmp_config(tmp_path, monkeypatch):
    klipper_dir = tmp_path / "klipper"
    klipper_dir.mkdir()
    config_home = tmp_path / "config"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    return klipper_dir, config_home

# 4. NullOutput (already exists in output.py)
@pytest.fixture
def null_output():
    from kflash.output import NullOutput
    return NullOutput()

# 5. Sample .config content
SAMPLE_CONFIG_STM32 = 'CONFIG_MCU="stm32h723xx"\nCONFIG_BOARD_DIRECTORY="stm32"\n'
SAMPLE_CONFIG_RP2040 = 'CONFIG_BOARD_DIRECTORY="rp2040"\n'
```

## Build Order for Tests

Tests should be built in this order, each phase adding confidence for the next:

### Phase 1: Pure Functions (No Dependencies)
Files: `test_models.py`, `test_discovery.py`, `test_validation.py`, `test_moonraker_parsing.py`, `test_errors.py`, `test_flash_helpers.py`

**Rationale:** Zero infrastructure needed. Validates the core logic that everything else depends on. ~22 functions, probably ~80+ test cases. This alone covers the majority of branching logic in the codebase.

### Phase 2: Filesystem Integration
Files: `test_registry.py`, `test_config.py`

**Rationale:** Depends on understanding dataclass contracts (Phase 1). Uses tmpdir fixtures. Tests Registry CRUD round-trips and ConfigManager load/save/validate cycles. High value because registry corruption = data loss.

### Phase 3: Subprocess Mocking
Files: `test_build.py`, `test_flasher.py`, `test_service.py`

**Rationale:** Depends on understanding FlashResult/BuildResult models (Phase 1). Tests the "dangerous" operations with mocked subprocess. Key scenarios: timeout handling, return code propagation, fallback logic in `flash_device()`.

### Phase 4: Network Mocking
Files: `test_moonraker_api.py`

**Rationale:** Lower priority -- Moonraker functions already degrade gracefully (return None). But worth testing the JSON parsing and error handling paths.

## Component Boundaries Diagram

```
                    +------------------+
                    |    tui.py        |  (SKIP - interactive)
                    |    screen.py     |
                    +--------+---------+
                             |
                    +--------v---------+
                    |    flash.py      |  Orchestrator
                    |  (cmd_flash,     |  (Tier 5 for orchestrators,
                    |   cmd_build,     |   Tier 1 for helpers)
                    |   cmd_add, etc.) |
                    +--+--+--+--+--+--+
                       |  |  |  |  |
          +------------+  |  |  |  +------------+
          |               |  |  |               |
    +-----v-----+  +-----v--v--v-----+  +------v------+
    | discovery  |  | config    build |  | moonraker   |
    | (Tier 1)   |  | (Tier 2) (T 3) |  | (Tier 1+4)  |
    +-----+------+  +-----+----+-----+  +------+------+
          |               |    |                |
    +-----v------+  +-----v----v-----+  +------v------+
    | models     |  | registry       |  | service     |
    | (Tier 1)   |  | (Tier 2)       |  | (Tier 3)    |
    +------------+  +-------+--------+  +------+------+
                            |                  |
                    +-------v--------+  +------v------+
                    | errors         |  | flasher     |
                    | (Tier 1)       |  | (Tier 3)    |
                    +----------------+  +-------------+
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Testing Orchestrators End-to-End
**What:** Trying to test `cmd_flash()` or `cmd_flash_all()` as unit tests.
**Why bad:** 400+ lines, 10+ dependencies, interactive prompts, deep coupling.
**Instead:** Test the helper functions they call. The orchestrators are integration-tested manually on hardware.

### Anti-Pattern 2: Mocking Too Deep
**What:** Mocking `os.path.exists` globally to test `ConfigManager`.
**Why bad:** Brittle, breaks when implementation changes internal calls.
**Instead:** Use real tmpdir with real files. Only mock at the subprocess/network boundary.

### Anti-Pattern 3: Testing ANSI/Theme Output
**What:** Asserting exact ANSI escape sequences in output.
**Why bad:** Theme changes break all tests. Zero logic to validate.
**Instead:** Use `NullOutput` in tests. Theme is visual-only.

## Sources

- Direct source code analysis of all 14 modules in `kflash/`
- `output.py` already provides `NullOutput` class (line 132) for test use
- Architecture follows hub-and-spoke pattern per CLAUDE.md
