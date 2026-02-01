# kalico-flash beta review (Feb)

## Scope and goals
High-level review focused on: safe flashing workflow, consistent error messaging, and risk mitigation against flashing the wrong MCU firmware.

## Executive summary
The core workflow is solid, but there are a few critical safety gaps in Flash All and device targeting that should be addressed before beta. Most issues are fixable by strengthening device selection/verification, aligning safety prompts, and making the cache path behavior explicit.

## Required changes (blocking)

### 1) Flash All can target the wrong device when a serial pattern matches multiple USB devices
- Risk: wrong firmware on the wrong MCU. Currently Flash All uses `match_device()` (first match) and does not block duplicates.
- Recommended fix:
  - Scan connected USB devices and detect duplicate matches for each entry (use `match_devices()`), then hard-block any entry with >1 matches.
  - Use the exact matched USB path for each device and keep a set of used paths to prevent any USB ID being targeted twice.
  - Surface a clear error explaining that duplicates must be unplugged or registry patterns must be made unique.

### 2) No hardware MCU cross-check vs registry before flashing
- Risk: registry MCU and config MCU can match, but the connected device could be different (stale registry, wrong serial pattern, re-used USB ID).
- Recommended fix:
  - Derive MCU type from the actual connected device (`extract_mcu_from_serial(device.filename)`), and compare to `entry.mcu`.
  - On mismatch, block and require explicit user confirmation only in interactive mode. For batch/Flash All, skip and record failure.
  - If available, prefer Moonraker `mcu_constants.MCU` for a higher-confidence match.

## Important changes (should fix)

### 3) Flash All lacks Moonraker unreachable confirmation
- Single-device flow asks for confirmation when Moonraker is unreachable; Flash All does not.
- Recommended fix:
  - If `get_print_status()` returns None, require explicit confirmation before continuing.
  - For non-interactive or batch, default to abort unless a `--yes`/`--force` flag is supplied.

### 4) Flash All should only process connected, registered devices with valid cached configs
- Requirement: Only flash MCUs that are connected, registered, and have a valid cached config.
- Recommended fix:
  - Stage 1 should build the candidate list from a live USB scan and the registry, filtering to devices that are:
    - registered
    - flashable
    - not blocked
    - connected (exactly one USB match)
    - cached config exists AND validates MCU
  - Devices failing any criteria should be excluded from the batch list and reported in a preflight summary.

### 5) Preflight checks are skipped in Flash All
- Recommended fix:
  - Reuse `_preflight_flash()` or a batch-safe variant before Stage 1.
  - If the preferred method is Katapult but unavailable and fallback disabled, block early with the existing recovery template.

### 6) Quiet builds in Flash All hide actionable errors
- Recommended fix:
  - Capture stdout/stderr to a per-device log file in the temp directory.
  - For failures, print the last 20-40 lines in the summary and include the path to the full log for details.

## Suggested non-interactive mode (for safety + future-proofing)
Note: CLI usage is being deprecated, but non-interactive safety still matters for any scripted or headless flows (batch/CI, service wrappers, or future Moonraker integration).

Recommended behavior:
- Add a `--yes` or `--non-interactive` flag that:
  - refuses to prompt, and fails fast on any safety uncertainty
  - requires explicit `--force` to bypass Moonraker unreachable checks
  - refuses to flash if MCU mismatch is detected (no override)
- In interactive TUI mode, keep confirmations but provide clear warnings and recovery steps.

## Config cache dir: deeper analysis
The settings UI exposes `config_cache_dir`, but `ConfigManager` ignores it and always uses `~/.config/kalico-flash/configs/{device_key}`. This is confusing and can produce inconsistent behavior when users expect a custom cache path to be honored.

Options:
1) Implement it:
   - Update `get_config_dir()` to read `GlobalConfig.config_cache_dir`.
   - Ensure the value is expanded (`~`) and validated for absolute paths.
   - Update migration logic to move existing per-device caches when the path changes.
2) Remove it:
   - Remove the setting from UI and registry, and update docs accordingly.

Recommendation:
- If the project expects power users or multi-profile setups, implement it.
- If simplicity is preferred for beta, remove it to avoid false affordances.

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

### Flash All candidate selection (connected + registered + cached config + unique match)
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class FlashCandidate:
    entry: DeviceEntry
    usb_device: DiscoveredDevice

@dataclass
class SkipReason:
    entry_key: str
    reason: str

def build_flash_candidates(
    registry_data: RegistryData,
    usb_devices: list[DiscoveredDevice],
    blocked_list: list[tuple[str, Optional[str]]],
    klipper_dir: str,
) -> tuple[list[FlashCandidate], list[SkipReason]]:
    candidates: list[FlashCandidate] = []
    skipped: list[SkipReason] = []
    used_paths: set[str] = set()

    flashable_entries = [e for e in registry_data.devices.values() if e.flashable]
    for entry in flashable_entries:
        reason = _blocked_reason_for_entry(entry, blocked_list)
        if reason:
            skipped.append(SkipReason(entry.key, f"blocked: {reason}"))
            continue

        matches = match_devices(entry.serial_pattern, usb_devices)
        if len(matches) == 0:
            skipped.append(SkipReason(entry.key, "not connected"))
            continue
        if len(matches) > 1:
            skipped.append(SkipReason(entry.key, "duplicate USB IDs"))
            continue

        usb_device = matches[0]
        if usb_device.path in used_paths:
            skipped.append(SkipReason(entry.key, "USB path already targeted"))
            continue

        # Cached config required
        cm = ConfigManager(entry.key, klipper_dir)
        if not cm.cache_path.exists():
            skipped.append(SkipReason(entry.key, "no cached config"))
            continue

        # Validate cached config MCU matches registry MCU
        try:
            cm.load_cached_config()
            is_match, actual = cm.validate_mcu(entry.mcu)
            if not is_match:
                skipped.append(SkipReason(entry.key, f"config MCU mismatch: {actual}"))
                continue
        except ConfigError as exc:
            skipped.append(SkipReason(entry.key, f"config error: {exc}"))
            continue

        # Hardware MCU check from device path (best effort)
        hw_mcu = extract_mcu_from_serial(usb_device.filename)
        if hw_mcu and not (hw_mcu.startswith(entry.mcu) or entry.mcu.startswith(hw_mcu)):
            skipped.append(SkipReason(entry.key, f"hardware MCU mismatch: {hw_mcu}"))
            continue

        used_paths.add(usb_device.path)
        candidates.append(FlashCandidate(entry, usb_device))

    return candidates, skipped
```

### Flash All preflight + Moonraker safety alignment
```python
def flash_all_preflight(out, global_config) -> bool:
    if not _preflight_flash(out, global_config.klipper_dir, global_config.katapult_dir,
                           global_config.default_flash_method, global_config.allow_flash_fallback):
        return False

    status = get_print_status()
    if status is None:
        out.warn("Moonraker unreachable - print status unavailable")
        if not out.confirm("Continue without safety checks?", default=False):
            return False
    elif status.state in ("printing", "paused"):
        out.error_with_recovery(
            "Printer busy",
            f"Print in progress: {status.filename or 'unknown'} ({int(status.progress * 100)}%)",
            recovery=ERROR_TEMPLATES["printer_busy"]["recovery_template"],
        )
        return False
    return True
```

### Non-interactive mode skeleton (for any headless or scripted entry points)
```python
class PromptPolicy:
    def __init__(self, interactive: bool, force: bool = False):
        self.interactive = interactive
        self.force = force

    def confirm(self, out, message: str, default: bool = False) -> bool:
        if self.interactive:
            return out.confirm(message, default=default)
        # Non-interactive: fail-safe unless explicitly forced
        return self.force and default is True

def ensure_safe_to_proceed(policy: PromptPolicy, out, safety_ok: bool) -> bool:
    if safety_ok:
        return True
    return policy.confirm(out, "Safety checks unavailable. Proceed anyway?", default=False)
```

### Config cache dir implementation option
```python
def get_config_dir(device_key: str, base_dir: Optional[str] = None) -> Path:
    if base_dir:
        base = Path(os.path.expanduser(base_dir))
    else:
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        base = Path(xdg_config) if xdg_config and os.path.isabs(xdg_config) else Path.home() / ".config"
        base = base / "kalico-flash" / "configs"
    return base / device_key
```

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

---

## Claude Code Review — Validation of Feedback

Validated against actual codebase (`kflash/flash.py`, `kflash/discovery.py`, `kflash/config.py`, `kflash/screen.py`, `kflash/registry.py`).

### Finding 1: Flash All duplicate detection

CLAUDE: **Finding:** The review claims Flash All "uses `match_device()` (first match) and does not block duplicates." This is **partially incorrect**. Flash All already calls `match_devices()` and explicitly detects duplicate USB matches (flash.py ~lines 386-398). Entries with >1 match are flagged and blocked. However, the review's secondary point about tracking used USB paths (preventing the same physical device being targeted by two different registry entries) is **valid** — that tracking does not exist.

**Recommendation:** The duplicate-detection claim should be corrected in the review. The used-path tracking suggestion remains worth implementing.

**Comments:** The existing duplicate detection covers the primary risk (one entry matching multiple USB devices). The residual gap — two entries matching the same single USB device — is a lower-probability edge case but still worth closing.

**Suggestions:** Add a `used_paths: set[str]` accumulator as proposed in the skeleton code. This is a small, low-risk change.

---

### Finding 2: No hardware MCU cross-check

CLAUDE: **Finding:** **Confirmed.** `extract_mcu_from_serial()` exists in `discovery.py` (lines 80-100) and correctly parses MCU type from USB serial filenames (e.g., `Klipper_stm32h723xx_...` → `stm32h723`). However, it is **never called** in either the single-device or Flash All flash workflows. The only validation is config-MCU vs registry-MCU, not hardware-MCU vs registry-MCU.

**Recommendation:** Agree with the review. Add a hardware MCU cross-check using `extract_mcu_from_serial()` before flashing. This is a high-value safety gate with minimal implementation cost since the function already exists.

**Comments:** The bidirectional prefix match already used for config validation (`stm32h723` matches `stm32h723xx`) should be reused here. Note that `extract_mcu_from_serial()` returns `None` for non-standard serial names, so the check must be best-effort (skip if extraction fails).

**Suggestions:** Apply in both single-device and Flash All flows. In single-device interactive mode, allow user override on mismatch. In Flash All, skip the device and report the mismatch.

---

### Finding 3: Flash All lacks Moonraker unreachable confirmation

CLAUDE: **Finding:** **Confirmed.** Single-device flow (flash.py ~lines 648-656) checks `if print_status is None` and prompts for confirmation. Flash All (flash.py ~lines 1192-1197) only checks for active print states (`printing`, `paused`) but silently continues when Moonraker is unreachable (`None`).

**Recommendation:** Agree. Add the same unreachable-confirmation prompt to Flash All, before the batch loop begins.

**Comments:** This is a straightforward alignment fix. The skeleton code in the review is reasonable.

**Suggestions:** Single prompt at the start of Flash All (not per-device) is sufficient since Moonraker status applies globally.

---

### Finding 4: Flash All candidate filtering

CLAUDE: **Finding:** **Partially confirmed.** Flash All already filters to flashable, non-blocked, connected devices with cached configs and validates MCU against config. The review's specific criteria are mostly already met. The gap is that the filtering is spread across multiple stages rather than consolidated into a clear preflight candidate list, making it harder to audit and extend.

**Recommendation:** Consolidating into a `build_flash_candidates()` function as proposed would improve clarity but is a refactor rather than a bug fix. Prioritize below the actual safety gaps (findings 2, 3, 5).

**Comments:** The proposed `FlashCandidate` / `SkipReason` dataclasses are a clean pattern. Consider this for a post-beta cleanup.

**Suggestions:** If implementing, also add the preflight summary report showing why each skipped device was excluded.

---

### Finding 5: Preflight checks skipped in Flash All

CLAUDE: **Finding:** **Confirmed.** `_preflight_flash()` is called in single-device flow but not in Flash All. This means Flash All will fail mid-batch with confusing errors if the Klipper directory, Makefile, `make` command, or Katapult flashtool are missing.

**Recommendation:** Agree. Call `_preflight_flash()` (or equivalent) once at the start of Flash All before entering the batch loop. This is a high-value, low-effort fix.

**Comments:** Failing early with a clear message is much better than failing mid-batch after some devices have already been flashed.

**Suggestions:** A single preflight call at the top of `cmd_flash_all` is sufficient — no need for per-device preflight.

---

### Finding 6: Quiet builds hide errors

CLAUDE: **Finding:** **Confirmed.** Flash All calls `run_build(klipper_dir, quiet=True)` and on failure only prints a generic "build failed" message. The actual compiler errors are captured but not surfaced.

**Recommendation:** Agree with the review's suggestion to capture output to a log file and print the tail on failure.

**Comments:** For a TUI context, printing the last 20 lines of build output inline after a failure is reasonable. A full log file path is a nice addition but not strictly necessary for beta.

**Suggestions:** Consider storing build output in `BuildResult.error_output` (full captured stderr) and displaying a truncated version in the summary.

---

### Finding 7: config_cache_dir setting ignored

CLAUDE: **Finding:** **Confirmed.** `screen.py` (line 41) exposes `config_cache_dir` as an editable path setting. `registry.py` persists it to/from JSON. But `config.py`'s `get_config_dir()` never reads `GlobalConfig.config_cache_dir` — it always derives the path from `XDG_CONFIG_HOME` or `~/.config`.

**Recommendation:** Agree with the review's "remove it" option for beta. A dead setting that appears functional is worse than no setting. Implementing it properly requires migration logic for existing caches, which is unnecessary complexity for beta.

**Comments:** If removed, also remove from `GlobalConfig` dataclass and registry serialization to keep things clean.

**Suggestions:** Remove the setting from screen.py, registry.py, and models.py. Add a comment in `get_config_dir()` noting the XDG convention. Revisit post-beta if users request custom paths.

---

### Finding 8: Non-interactive mode suggestion

CLAUDE: **Finding:** The review suggests `--yes`/`--non-interactive`/`--force` flags. Per the updated CLAUDE.md, CLI usage is being removed in favor of TUI-only. This suggestion is **not applicable for beta**.

**Recommendation:** Deprioritize. The TUI is inherently interactive. If a future Moonraker integration or scripted entry point is added, revisit then.

**Comments:** The `PromptPolicy` abstraction is over-engineered for a TUI-only tool. Safety prompts in the TUI are sufficient.

**Suggestions:** Skip for beta. Note as a future consideration if headless/API usage is added.

---

### Finding 9: Test suite suggestion

CLAUDE: **Finding:** The suggested test structure and focus areas are **reasonable and well-targeted**. The functions identified (`extract_mcu_from_serial`, `match_devices`, `validate_mcu`, `generate_device_key`) are pure or near-pure functions that are straightforward to unit test.

**Recommendation:** Agree this is high-value. The discovery and config validation functions are the most testable and most safety-critical — good prioritization.

**Comments:** `unittest` with `unittest.mock` is the right choice given the stdlib-only constraint. The mocking guidance is accurate.

**Suggestions:** Start with `test_discovery.py` — it covers the functions most relevant to the safety findings above.

---

### Overall assessment

The review is **largely accurate and well-prioritized**. Finding 1's claim about missing duplicate detection is factually wrong (it exists), but the used-path tracking gap is real. All other findings (2, 3, 5, 6, 7) are confirmed as written. The non-interactive mode suggestion (finding 8) is not applicable given the TUI-only direction.

**Recommended fix priority for beta:**
1. Preflight checks in Flash All (finding 5) — low effort, high safety value
2. Moonraker unreachable confirmation in Flash All (finding 3) — low effort, aligns with single-device
3. Hardware MCU cross-check (finding 2) — medium effort, high safety value
4. Surface build errors in Flash All (finding 6) — low effort, improves debuggability
5. Remove dead config_cache_dir setting (finding 7) — low effort, removes confusion
6. Used-path tracking in Flash All (finding 1) — low effort, closes edge case

## Summary verdict
Request changes before beta to close the safety gaps in Flash All targeting, add a hardware MCU cross-check, and align safety prompts for Moonraker failures.
