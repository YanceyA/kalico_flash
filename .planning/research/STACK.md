# Technology Stack: Test Framework for kalico-flash

**Project:** kalico-flash test suite
**Researched:** 2026-02-01
**Overall Confidence:** HIGH (pytest and unittest.mock are mature, stable tools)

---

## Recommended Stack

### Test Framework
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pytest | >=7.0 | Test runner, assertions, fixtures, parametrize | Best fit for data-driven pure function testing (see comparison) |

### Mocking
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| unittest.mock | stdlib | All mocking needs | Already in stdlib, works natively with pytest, no extra dependency |

### Test Utilities (all pytest built-ins)
| Utility | Purpose | When to Use |
|---------|---------|-------------|
| `tmp_path` fixture | Auto-managed temp directories | Registry persistence, config cache, atomic write tests |
| `monkeypatch` fixture | Patch env vars, module attributes | XDG_CONFIG_HOME, SERIAL_BY_ID constant, time.time |
| `@pytest.mark.parametrize` | Data-driven test cases | MCU extraction, slug generation, pattern matching |

---

## Framework Comparison: pytest vs unittest

| Criterion | pytest | unittest |
|-----------|--------|----------|
| **Assertion style** | Plain `assert x == y` with rich diff on failure | `self.assertEqual(x, y)` -- verbose, less readable |
| **Test discovery** | Bare functions, no class needed | Must subclass `TestCase` |
| **Fixtures** | `@pytest.fixture` with DI, scoping, composition | `setUp`/`tearDown` only, no composition |
| **Parametrize** | `@pytest.mark.parametrize` -- native, generates N test cases | `subTest()` -- weaker, one test with sub-iterations |
| **Temp directories** | `tmp_path` built-in fixture, auto-cleanup | Manual `tempfile.mkdtemp()` + cleanup in `tearDown` |
| **Output on failure** | Rich diffs, short tracebacks, assertion introspection | Minimal context |
| **Boilerplate** | Low (functions) | High (classes, method names, self references) |

### Why pytest wins for this project

**1. Parametrize is the deciding factor.** The highest-value test targets are pure functions with many input/output pairs:

```python
# With pytest -- clean, each case is a separate test
@pytest.mark.parametrize("filename, expected", [
    ("usb-Klipper_stm32h723xx_290...-if00", "stm32h723"),
    ("usb-Klipper_rp2040_303...-if00", "rp2040"),
    ("usb-katapult_stm32h723xx_290...-if00", "stm32h723"),
    ("usb-Klipper_stm32f411xe_600...-if00", "stm32f411"),
    ("usb-Beacon_Beacon_RevH_FC2...-if00", None),
])
def test_extract_mcu_from_serial(filename, expected):
    assert extract_mcu_from_serial(filename) == expected

# With unittest -- verbose, all cases share one test
class TestExtractMcu(unittest.TestCase):
    def test_extract_mcu_from_serial(self):
        cases = [
            ("usb-Klipper_stm32h723xx_290...-if00", "stm32h723"),
            # ...
        ]
        for filename, expected in cases:
            with self.subTest(filename=filename):
                self.assertEqual(extract_mcu_from_serial(filename), expected)
```

With parametrize, each case appears as a distinct test in output. With subTest, failure in one case does not stop others but they all share a single pass/fail.

**2. tmp_path eliminates boilerplate.** Registry and config tests need temp files. pytest's `tmp_path` auto-creates unique temp dirs per test and cleans up automatically. No `setUp`/`tearDown` needed.

**3. No conflict with production constraints.** pytest is dev-only. It never ships to the Pi. The constraint is "no production dependencies," which pytest respects fully.

**The only argument for unittest** is zero dependencies. But since pytest is explicitly allowed as a dev dependency and the test targets are data-driven pure functions, that argument does not outweigh the ergonomic advantages.

**Recommendation: Use pytest.**

---

## Mocking Strategy

### Principle: Prefer real objects over mocks

Most high-value test targets are pure functions. They take strings/lists and return strings/lists. No mocking needed -- just call them with test data. Reserve mocking for external boundaries only.

### Boundary 1: Filesystem (Registry, Config)

**Approach: Real temp directories via `tmp_path`.**

```python
def test_registry_add_device(tmp_path):
    reg = Registry(str(tmp_path / "devices.json"))
    entry = DeviceEntry(key="octopus", name="Octopus", mcu="stm32h723",
                        serial_pattern="usb-Klipper_stm32h723xx_*")
    reg.add(entry)
    assert reg.get("octopus") is not None
```

This tests actual JSON serialization, atomic writes, and file I/O. Mocking `open()` would hide real bugs.

**Mock only for error paths:**
```python
def test_registry_load_corrupt_json(tmp_path):
    path = tmp_path / "devices.json"
    path.write_text("not json")
    reg = Registry(str(path))
    with pytest.raises(RegistryError):
        reg.load()
```

### Boundary 2: USB Device Scanning

**Approach: Direct argument injection (no mocking needed for most functions).**

`match_devices()`, `extract_mcu_from_serial()`, `is_supported_device()`, `find_registered_devices()` all accept data as arguments. Pass test data directly:

```python
def test_match_devices():
    devices = [
        DiscoveredDevice(path="/dev/serial/by-id/usb-Klipper_stm32h723xx_290-if00",
                         filename="usb-Klipper_stm32h723xx_290-if00"),
    ]
    result = match_devices("usb-Klipper_stm32h723xx_*", devices)
    assert len(result) == 1
```

**For `scan_serial_devices()` (reads real filesystem):**
Use `monkeypatch` to redirect the module constant:

```python
def test_scan_serial_devices(tmp_path, monkeypatch):
    monkeypatch.setattr(discovery, "SERIAL_BY_ID", str(tmp_path))
    (tmp_path / "usb-Klipper_stm32h723xx_290-if00").touch()
    devices = scan_serial_devices()
    assert len(devices) == 1
```

### Boundary 3: Subprocess (build, flash, service)

**Not a priority for initial test suite.** These modules are integration-heavy and would require extensive mocking of `subprocess.run` return values, which provides low confidence.

When eventually needed:
```python
from unittest.mock import patch, MagicMock

@patch("subprocess.run")
def test_build_success(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    # ... test build logic
```

### Boundary 4: Environment Variables

**Approach: `monkeypatch.setenv` / `monkeypatch.delenv`.**

```python
def test_config_dir_respects_xdg(monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")
    result = get_config_dir("octopus")
    assert str(result).startswith("/custom/config")
```

### Boundary 5: Registry for validation.py

`generate_device_key()` and `validate_device_key()` take a `registry` with `.get()` method. Use a simple stub:

```python
class StubRegistry:
    def __init__(self, existing_keys=None):
        self._keys = set(existing_keys or [])
    def get(self, key):
        return "exists" if key in self._keys else None
```

This is simpler and more readable than `MagicMock(side_effect=...)`.

### Mocking Summary

| Boundary | Strategy | Why |
|----------|----------|-----|
| Pure functions | No mock -- direct calls | Most test targets need no isolation |
| Filesystem (happy) | Real `tmp_path` | Tests actual I/O, catches real bugs |
| Filesystem (errors) | Write corrupt/missing files in `tmp_path` | Still real filesystem, controlled failure |
| USB scanning | `monkeypatch.setattr` on constant | Redirect to temp dir |
| Environment vars | `monkeypatch.setenv` | Clean per-test isolation |
| Registry dependency | Stub class with `.get()` | Simpler than MagicMock |
| Subprocess | `unittest.mock.patch` | Defer to later phases |
| Time | `monkeypatch.setattr(time, "time", ...)` | For `get_cache_age_display` |

---

## Test Runner Configuration

**Use `pyproject.toml`.** Single config file, no `.cfg`/`.ini` proliferation.

```toml
[project.optional-dependencies]
dev = ["pytest>=7.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
```

### Directory Structure

```
tests/
    conftest.py          # Shared fixtures
    test_discovery.py    # extract_mcu, match_devices, is_supported, generate_pattern
    test_validation.py   # generate_device_key, validate_device_key, validate_numeric
    test_config.py       # parse_mcu_from_config, validate_mcu, get_config_dir, cache_age
    test_registry.py     # Registry CRUD, atomic writes, corrupt file handling
    test_models.py       # Dataclass construction (lightweight, optional)
```

### conftest.py Fixtures

```python
import pytest
from kflash.models import DeviceEntry, DiscoveredDevice
from kflash.registry import Registry


@pytest.fixture
def sample_devices():
    """Common USB devices for pattern matching tests."""
    return [
        DiscoveredDevice(
            path="/dev/serial/by-id/usb-Klipper_stm32h723xx_290-if00",
            filename="usb-Klipper_stm32h723xx_290-if00",
        ),
        DiscoveredDevice(
            path="/dev/serial/by-id/usb-Klipper_rp2040_303-if00",
            filename="usb-Klipper_rp2040_303-if00",
        ),
        DiscoveredDevice(
            path="/dev/serial/by-id/usb-Beacon_Beacon_RevH_FC2-if00",
            filename="usb-Beacon_Beacon_RevH_FC2-if00",
        ),
    ]


@pytest.fixture
def registry(tmp_path):
    """Registry backed by a temp file."""
    return Registry(str(tmp_path / "devices.json"))


class StubRegistry:
    """Minimal registry stub for validation functions."""
    def __init__(self, existing_keys=None):
        self._keys = set(existing_keys or [])
    def get(self, key):
        return DeviceEntry(key=key, name="", mcu="", serial_pattern="") if key in self._keys else None


@pytest.fixture
def stub_registry():
    """Factory for stub registries with preset keys."""
    def _make(existing_keys=None):
        return StubRegistry(existing_keys)
    return _make
```

---

## What NOT to Add

| Tool | Why Not |
|------|---------|
| **pytest-cov / coverage** | Premature. Get tests written first. Add coverage tracking once suite is established and you want to find gaps. |
| **pytest-mock** | Thin wrapper around `unittest.mock`. The stdlib mock is sufficient; avoids an extra dependency for negligible benefit. |
| **tox** | Single target Python version (3.9+). No version matrix needed. No CI. |
| **hypothesis** | Property-based testing is overkill for deterministic string parsing with known input patterns. Parametrize covers the cases. |
| **freezegun** | Only one time-dependent function (`get_cache_age_display`). `monkeypatch.setattr(time, "time", lambda: fixed_val)` suffices. |
| **mypy / type checking** | Valuable but separate concern from test suite. Out of scope for this milestone. |
| **pre-commit hooks** | No CI pipeline. Manual workflow. Adding hooks adds friction. |
| **mutmut / mutation testing** | Premature optimization. Requires existing test suite with good coverage. |
| **pytest-asyncio** | No async code in codebase. |
| **pytest-xdist** | Parallel test execution. Test suite will be small and fast. Unnecessary complexity. |

---

## Cross-Platform Notes

Tests must work on both Windows (dev) and Linux/ARM (Pi).

| Concern | Mitigation |
|---------|------------|
| Path separators | Use `pathlib.Path` and `os.path.join`, not hardcoded `/` in assertions |
| `/dev/serial/by-id/` | Tests for `scan_serial_devices` mock the path; pure functions use strings |
| `os.replace` atomicity | Works on both platforms for temp file writes |
| Line endings | Not an issue -- tests deal with data, not file content comparison |

**Key rule:** Test assertions should compare logical values (strings, objects), not filesystem paths with hardcoded separators.

---

## Installation

```bash
# Install pytest as dev dependency
pip install pytest>=7.0

# Run tests
pytest

# Run specific test file
pytest tests/test_discovery.py

# Run with verbose output
pytest -v
```

---

## Sources

- pytest stable API (HIGH confidence -- mature, unchanged across major versions)
- unittest.mock stdlib (HIGH confidence -- Python stdlib)
- Direct analysis of kalico-flash source code for boundary identification and test target assessment
