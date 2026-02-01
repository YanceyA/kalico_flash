# Pitfalls Research: Test Framework for kalico-flash

**Domain:** Adding pytest test suite to existing Python TUI/firmware-flash tool (zero tests currently)
**Researched:** 2026-02-01
**Overall confidence:** HIGH (domain knowledge from Python testing patterns, direct codebase analysis)

---

## Critical Pitfalls

Mistakes that waste significant time or produce a test suite nobody maintains.

### TEST-1: Mocking Implementation Details Instead of Testing Behavior (Critical)

**What goes wrong:** Tests mock internal function calls (e.g., `@patch('kflash.discovery.Path.iterdir')`) and assert exact call sequences. Any refactor -- renaming an internal helper, changing call order, extracting a function -- breaks tests even when behavior is unchanged. Developer spends more time fixing tests than writing features.

**Why it happens:** When adding tests to existing code, the natural approach is "mock everything this function calls." This couples tests to the implementation graph rather than the input/output contract.

**Consequences:** 50+ tests break on a harmless refactor. Developer stops trusting tests, starts skipping them, eventually deletes the suite.

**Warning signs:**
- `@patch` decorators outnumber assertions in a test
- Test names describe HOW not WHAT: `test_scan_calls_iterdir_and_filters` vs `test_scan_returns_klipper_devices_only`
- Changing a private helper `_foo()` to `_bar()` breaks tests in other modules

**Prevention -- concrete examples from THIS codebase:**

DO test `extract_mcu_from_serial()` (discovery.py:80) as pure function:
```python
def test_extract_mcu_stm32():
    assert extract_mcu_from_serial("usb-Klipper_stm32h723xx_290-if00") == "stm32h723"

def test_extract_mcu_rp2040():
    assert extract_mcu_from_serial("usb-Klipper_rp2040_303-if00") == "rp2040"

def test_extract_mcu_non_klipper_returns_none():
    assert extract_mcu_from_serial("usb-Beacon_Beacon_RevH_FC2-if00") is None
```

DO NOT mock internals of `ConfigManager.validate_mcu()` (config.py:164). Instead, create a real temp `.config` file and test the output:
```python
def test_validate_mcu_matches_prefix(tmp_path):
    config_file = tmp_path / ".config"
    config_file.write_text('CONFIG_MCU="stm32h723xx"\n')
    # Test with real file, not mocked parse_mcu_from_config
```

**Detection:** If a test file has more `@patch` lines than `assert` lines, it is testing implementation, not behavior.

---

### TEST-2: Testing the TUI Instead of the Logic Behind It (Critical)

**What goes wrong:** Developer writes tests for `tui.py` screen rendering, cursor positioning, ANSI output, and input handling. These tests are extremely brittle (any visual change breaks them), hard to write (require terminal emulation), and catch almost no real bugs. Meanwhile, the pure logic functions that actually matter remain untested.

**Why it happens:** TUI is the largest module (~1400 lines). It feels like "the most important thing to test." But TUI bugs are visual -- users see them immediately. Logic bugs (wrong MCU match, slug collision, pattern mismatch) are silent and dangerous.

**Consequences:** 40% of test suite covers TUI rendering. Tests break every time someone adjusts spacing or colors. Zero coverage on the MCU validation that prevents bricking boards.

**Warning signs:**
- Tests that assert exact ANSI escape sequences
- Tests that mock `sys.stdout` and check character-by-character output
- Tests for `panels.py`, `screen.py`, `ansi.py` rendering details

**Prevention:**
- Do NOT test: `tui.py`, `panels.py`, `screen.py` rendering, `ansi.py` output formatting
- DO test: `discovery.py` pattern matching, `validation.py` all functions, `config.py` MCU parsing/validation, `flash.py` blocked-device logic, `registry.py` load/save/CRUD
- The high-value test targets in this codebase are:

| Module | Function | Why High-Value |
|--------|----------|----------------|
| `discovery.py` | `extract_mcu_from_serial()` | Wrong MCU = wrong firmware = bricked board |
| `discovery.py` | `match_devices()` | Wrong match = flash wrong board |
| `discovery.py` | `find_registered_devices()` | Missed match = device not offered for flash |
| `discovery.py` | `generate_serial_pattern()` | Bad pattern = device never matches again |
| `validation.py` | `generate_device_key()` | Slug collision = data loss |
| `validation.py` | `validate_device_key()` | Invalid key = filesystem errors |
| `config.py` | `parse_mcu_from_config()` | Wrong parse = MCU mismatch not detected |
| `config.py` | `ConfigManager.validate_mcu()` | Prefix match logic is subtle and critical |
| `flash.py` | `_blocked_reason_for_filename()` | Unblocked device = flash attempt on non-MCU |
| `registry.py` | `Registry.load()/save()` | Data corruption = all devices lost |

---

### TEST-3: Mocking subprocess Where tmp_path Would Work (Moderate)

**What goes wrong:** Developer mocks `Path.exists()`, `Path.read_text()`, `shutil.move()` etc. for functions that do filesystem I/O. The mocks become complex, fragile, and don't catch real bugs (e.g., path encoding issues, missing parent directories, atomic write race conditions).

**Why it happens:** "Never touch the real filesystem in tests" is over-applied. pytest's `tmp_path` fixture gives a real temporary directory that is cleaned up automatically. For this codebase, most filesystem operations are simple reads/writes that work perfectly with real files.

**Consequences:** Mocked filesystem tests pass but real code fails because mock didn't simulate `os.replace()` atomicity, `XDG_CONFIG_HOME` expansion, or `Path.home()` resolution.

**Warning signs:**
- `@patch('pathlib.Path.exists')` anywhere
- `@patch('builtins.open')` for config file reading
- Mock setup longer than the test assertion

**Prevention -- concrete examples from THIS codebase:**

For `config.py` ConfigManager, use real temp directories:
```python
def test_load_and_save_cached_config(tmp_path, monkeypatch):
    klipper_dir = tmp_path / "klipper"
    klipper_dir.mkdir()
    (klipper_dir / ".config").write_text('CONFIG_MCU="stm32h723xx"\n')

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    mgr = ConfigManager("test-device", str(klipper_dir))
    mgr.save_cached_config()

    assert mgr.cache_path.exists()
    assert 'stm32h723xx' in mgr.cache_path.read_text()
```

For `registry.py`, use real JSON files in tmp_path:
```python
def test_registry_roundtrip(tmp_path):
    reg = Registry(str(tmp_path / "devices.json"))
    data = reg.load()  # Returns default RegistryData
    data.devices["test"] = DeviceEntry(key="test", name="Test", mcu="stm32h723", serial_pattern="usb-Klipper_stm32h723xx_*")
    reg.save(data)

    reloaded = reg.load()
    assert "test" in reloaded.devices
```

Reserve `@patch` for: subprocess calls (build.py, flasher.py, service.py), HTTP calls (moonraker.py), and `/dev/serial/by-id/` scanning (discovery.py `scan_serial_devices()`).

---

### TEST-4: Writing Hundreds of Trivial Tests for Coverage Numbers (Moderate)

**What goes wrong:** Developer aims for "90% coverage" and writes tests like `test_global_config_defaults()` that assert dataclass default values, or `test_discovered_device_has_path()` that checks a field exists. These tests never fail, never catch bugs, and bloat the suite.

**Why it happens:** Coverage metrics feel productive. Each trivial test is easy to write. "More tests = safer" is intuitive but wrong for maintenance cost.

**Consequences:** 200 tests, 15 minutes to run through, 80% are trivial. Developer ignores test failures because "it's probably one of those dumb tests." Real failures get lost in noise.

**Warning signs:**
- Tests that only check constructor default values
- Tests that duplicate the implementation (`assert slug.lower() == slug.lower()`)
- Test count growing faster than feature count
- Tests with no edge cases -- only happy path

**Prevention:**
- Target: ~40-60 focused tests total for this codebase, not 200+
- Every test should answer: "What bug does this catch?" If the answer is "none, it just checks the code works," skip it.
- High-value test categories for kalico-flash:

| Category | Example | Why It Catches Bugs |
|----------|---------|---------------------|
| Edge cases | `extract_mcu_from_serial("usb-Klipper_stm32f411xe_600-if00")` | Variant suffix `xe` vs `xx` -- real MCU naming |
| Boundary | `generate_device_key("---", registry)` | Empty slug after normalization |
| Cross-cutting | `validate_mcu("stm32h723", config_with_stm32h723xx)` | Bidirectional prefix match subtlety |
| Regression | Pattern that broke in production | Prevents known-bad state |
| Safety | Blocked device detection for Beacon probe | Wrong-device flash prevention |

---

### TEST-5: Not Using monkeypatch for Environment-Dependent Code (Moderate)

**What goes wrong:** Tests for `get_config_dir()` (config.py:16) use `@patch.dict(os.environ)` or worse, actually set `XDG_CONFIG_HOME` globally. Tests pass locally but fail in CI or on other developers' machines because environment leaks between tests.

**Why it happens:** `os.environ` is global mutable state. `@patch.dict` works but `monkeypatch` is cleaner and auto-reverts. Developers unfamiliar with pytest reach for unittest patterns.

**Consequences:** Flaky tests that pass on one machine and fail on another. `XDG_CONFIG_HOME` set by one test affects the next test. `Path.home()` returns different values in different environments.

**Prevention:**
- Always use `monkeypatch.setenv()` / `monkeypatch.delenv()` for environment variables
- Always use `monkeypatch.setattr()` for module-level constants like `discovery.SERIAL_BY_ID`
- For `get_config_dir()`, test with AND without `XDG_CONFIG_HOME`:
```python
def test_config_dir_respects_xdg(monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")
    assert str(get_config_dir("test")) == "/custom/config/kalico-flash/configs/test"

def test_config_dir_default_without_xdg(monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    result = get_config_dir("test")
    assert "kalico-flash/configs/test" in str(result)
```

---

### TEST-6: Testing Registry with Mocked JSON Instead of Real Files (Moderate)

**What goes wrong:** Developer mocks `json.loads()` and `Path.read_text()` to test Registry. The mock returns perfectly structured data. Real-world `devices.json` has missing keys, extra keys from newer versions, or hand-edited formatting. Tests pass, but `Registry.load()` crashes on real files.

**Why it happens:** Mocking feels "cleaner" than creating temp JSON files. But the value of registry tests is verifying the parsing handles real-world JSON variations.

**Prevention:**
- Test with real JSON files in `tmp_path` that simulate real scenarios:
```python
def test_load_missing_optional_fields(tmp_path):
    """devices.json from older version without flashable field."""
    (tmp_path / "devices.json").write_text(json.dumps({
        "global": {"klipper_dir": "~/klipper"},
        "devices": {"test": {"name": "Test", "mcu": "stm32h723", "serial_pattern": "usb-*"}}
    }))
    reg = Registry(str(tmp_path / "devices.json"))
    data = reg.load()
    assert data.devices["test"].flashable is True  # Default

def test_load_corrupt_json(tmp_path):
    (tmp_path / "devices.json").write_text("{invalid json")
    reg = Registry(str(tmp_path / "devices.json"))
    with pytest.raises(RegistryError):
        reg.load()
```

---

### TEST-7: Forgetting the Bidirectional Prefix Match Is the Whole Point (Critical)

**What goes wrong:** Developer tests `validate_mcu()` with exact matches only (`"stm32h723xx"` vs `"stm32h723xx"`). The critical behavior -- bidirectional prefix matching where `"stm32h723"` matches `"stm32h723xx"` AND `"stm32h723xx"` matches `"stm32h723"` -- goes untested. This is the exact logic that prevents flashing wrong firmware to wrong board.

**Why it happens:** Happy-path testing. The developer tests the obvious case and moves on. The subtle case (registry says `stm32h723`, config says `stm32h723xx`) is the actual production scenario.

**Concrete code:** `config.py:196`:
```python
is_match = actual_mcu.startswith(expected_mcu) or expected_mcu.startswith(actual_mcu)
```

**Prevention -- required test cases:**
```python
# Registry has short form, config has long form (MOST COMMON)
def test_validate_mcu_short_expected_long_actual():
    # expected="stm32h723" (from registry), actual="stm32h723xx" (from .config)
    # Must match -- this is the normal case

# Registry has long form, config has short form
def test_validate_mcu_long_expected_short_actual():
    # expected="stm32h723xx", actual="stm32h723"
    # Must match -- bidirectional

# Different MCU families must NOT match
def test_validate_mcu_different_family():
    # expected="stm32h723", actual="rp2040"
    # Must NOT match -- this prevents wrong-board flash

# Partial prefix overlap that SHOULD NOT match
def test_validate_mcu_partial_overlap():
    # expected="stm32h7", actual="stm32h4" -- different chip family
    # stm32h4 does NOT start with stm32h7, stm32h7 does NOT start with stm32h4
    # Correctly rejected by current logic
```

---

### TEST-8: Test File Organization That Doesn't Scale (Minor)

**What goes wrong:** All tests in one `test_all.py` file. Or tests scattered without matching module structure. Developer can't find which test covers which function. Adding tests becomes friction because the file is 800 lines long.

**Prevention:**
- Mirror the source structure:
```
tests/
  test_discovery.py    # Tests for discovery.py
  test_validation.py   # Tests for validation.py
  test_config.py       # Tests for config.py
  test_registry.py     # Tests for registry.py
  test_flash.py        # Tests for flash.py blocked-device logic
  conftest.py          # Shared fixtures (sample devices, registry data)
```
- `conftest.py` should provide reusable fixtures:
```python
@pytest.fixture
def sample_devices():
    return [
        DiscoveredDevice(path="/dev/serial/by-id/usb-Klipper_stm32h723xx_290-if00", filename="usb-Klipper_stm32h723xx_290-if00"),
        DiscoveredDevice(path="/dev/serial/by-id/usb-Klipper_rp2040_303-if00", filename="usb-Klipper_rp2040_303-if00"),
        DiscoveredDevice(path="/dev/serial/by-id/usb-Beacon_Beacon_RevH_FC2-if00", filename="usb-Beacon_Beacon_RevH_FC2-if00"),
    ]
```

---

### TEST-9: Parametrize Abuse -- Too Clever, Not Readable (Minor)

**What goes wrong:** Developer discovers `@pytest.mark.parametrize` and writes:
```python
@pytest.mark.parametrize("input,expected", [
    ("usb-Klipper_stm32h723xx_290-if00", "stm32h723"),
    ("usb-Klipper_rp2040_303-if00", "rp2040"),
    # ... 30 more cases
])
```
When one case fails, the error message shows `FAILED test_discovery.py::test_extract_mcu[input2-expected2]` with no context about what `input2` means.

**Prevention:**
- Use parametrize for 3-8 related cases with clear IDs:
```python
@pytest.mark.parametrize("filename,expected", [
    pytest.param("usb-Klipper_stm32h723xx_290-if00", "stm32h723", id="stm32-with-variant"),
    pytest.param("usb-Klipper_rp2040_303-if00", "rp2040", id="rp2040"),
    pytest.param("usb-katapult_stm32h723xx_290-if00", "stm32h723", id="katapult-prefix"),
    pytest.param("usb-Beacon_Beacon_RevH_FC2-if00", None, id="non-klipper-device"),
])
```
- For edge cases that need explanation, write individual tests with docstrings
- Never parametrize across fundamentally different behaviors (don't mix "returns value" and "raises exception" in one parametrize)

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Initial setup | Over-scoping: trying to test everything at once | Start with pure functions only (TEST-2) |
| discovery.py tests | Mocking Path.iterdir for scan_serial_devices | Only mock scan; test match/extract as pure functions |
| config.py tests | Mocking filesystem for ConfigManager | Use tmp_path with real files (TEST-3) |
| registry.py tests | Mocking JSON parsing | Use real JSON files in tmp_path (TEST-6) |
| validation.py tests | Missing edge cases (empty, unicode, collisions) | Explicit edge case list per function (TEST-4) |
| MCU validation | Only testing exact matches | Bidirectional prefix match is THE critical test (TEST-7) |
| flash.py tests | Testing the full flash workflow | Only test blocked-device logic; flash workflow is subprocess-heavy |
| Coverage goals | Chasing 90%+ coverage | Target ~50 high-value tests, not coverage percentage |

## "Looks Done But Isn't" Checklist

- [ ] **Bidirectional MCU prefix match tested:** Both `short.startswith(long)` and `long.startswith(short)` cases covered
- [ ] **Slug collision tested:** `generate_device_key()` with existing keys produces unique suffixed slugs
- [ ] **Blocked device patterns tested:** Beacon probe pattern correctly blocks, Klipper devices pass through
- [ ] **Registry roundtrip tested:** save then load preserves all fields including optionals
- [ ] **No TUI tests:** Zero tests for tui.py, panels.py, screen.py, ansi.py rendering
- [ ] **No subprocess tests that run real make/flash:** All build/flash subprocess calls mocked
- [ ] **tmp_path used for filesystem tests:** No mocking of Path.exists(), open(), etc.
- [ ] **monkeypatch used for env vars:** No global os.environ mutation
- [ ] **Test count reasonable:** Under 80 total tests, each catches a specific bug class

## Sources

### Codebase Analysis (HIGH confidence)
- `kflash/discovery.py` - Pure functions: `extract_mcu_from_serial()`, `match_devices()`, `is_supported_device()`, `generate_serial_pattern()`
- `kflash/validation.py` - Pure functions: `generate_device_key()`, `validate_device_key()`, `validate_numeric_setting()`
- `kflash/config.py` - `parse_mcu_from_config()` pure; `ConfigManager` needs tmp_path; `validate_mcu()` line 196 has bidirectional prefix match
- `kflash/registry.py` - `Registry.load()/save()` with atomic writes, JSON parsing with defaults for missing fields
- `kflash/flash.py` - `_blocked_reason_for_filename()`, `_blocked_reason_for_entry()` pure-ish functions
- `kflash/models.py` - Dataclass contracts with Optional fields and defaults

### Domain Knowledge (HIGH confidence)
- pytest fixtures (`tmp_path`, `monkeypatch`) behavior and cleanup guarantees
- Python `@patch` vs `monkeypatch` tradeoffs for test maintainability
- Common failure modes when adding test suites to existing Python projects
- Firmware flashing safety: wrong-MCU-match is the primary test-preventable risk

---

*Pitfalls research: 2026-02-01 (test framework edition)*
*Confidence: HIGH -- based on direct codebase analysis identifying specific testable functions, their risk profiles, and concrete prevention strategies.*
