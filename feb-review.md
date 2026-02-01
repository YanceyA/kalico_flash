## Test suite pattern and structure (small, high-value)
Since there are no current tests and the project is stdlib-only, a minimal `unittest` suite will work with no dependencies.

Suggested structure:
```
/tests
  /unit
    test_discovery.py
    test_config.py
    test_flash_all_selection.py
    test_validation.py
  /fixtures
    devices.json
```

Recommended test focus:
- `test_discovery.py`
  - `extract_mcu_from_serial()` for several known patterns (Klipper, Katapult, unsupported).
  - `generate_serial_pattern()` stripping `-if00` correctly.
  - `match_devices()` and duplicate detection.

- `test_config.py`
  - `parse_mcu_from_config()` reads `CONFIG_MCU` and `CONFIG_BOARD_DIRECTORY`.
  - `ConfigManager.validate_mcu()` exact vs prefix matching behavior.
  - `ConfigManager.save_cached_config()` error path when `.config` missing.

- `test_flash_all_selection.py`
  - Selection filter: only connected + registered + flashable + unblocked + unique match + cached config.
  - Duplicate USB IDs cause a block for that device.
  - Missing cache excludes device and reports reason.

- `test_validation.py`
  - `generate_device_key()` slugging and collision handling.
  - `validate_numeric_setting()` range handling.

Mocking guidance:
- Use `unittest.mock` to mock filesystem, subprocess, and Moonraker calls.
- For USB scans, mock `scan_serial_devices()` to return controlled lists.
- For cached configs, use `tempfile.TemporaryDirectory()` and write sample `.config` files.

Run command:
```
python -m unittest discover -s tests -p "test_*.py"
```

## Implementation notes for Flash All update
- Build a single, explicit `flash_candidates` list early in Stage 1:
  - scan USB
  - map matches to registry entries
  - filter to exactly one connected match
  - validate cached config exists and MCU matches registry
- Only build/flash `flash_candidates`. Others should be reported with clear reasons.

## Draft code skeletons (not full implementation)

### Minimal test skeleton example (unittest)
```python
import unittest
from unittest import mock

class TestFlashAllSelection(unittest.TestCase):
    def test_duplicate_matches_are_skipped(self):
        # Arrange: two USB devices match one entry serial_pattern
        # Act: build_flash_candidates()
        # Assert: entry is in skipped with "duplicate USB IDs"
        pass
```


### Finding 9: Test suite suggestion

CLAUDE: **Finding:** The suggested test structure and focus areas are **reasonable and well-targeted**. The functions identified (`extract_mcu_from_serial`, `match_devices`, `validate_mcu`, `generate_device_key`) are pure or near-pure functions that are straightforward to unit test.

**Recommendation:** Agree this is high-value. The discovery and config validation functions are the most testable and most safety-critical — good prioritization.

**Comments:** `unittest` with `unittest.mock` is the right choice given the stdlib-only constraint. The mocking guidance is accurate.

**Suggestions:** Start with `test_discovery.py` — it covers the functions most relevant to the safety findings above.


