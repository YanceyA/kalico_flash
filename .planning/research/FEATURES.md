# Feature Landscape: Test Targets for kalico-flash

**Domain:** Test suite for firmware flash tool (safety-critical embedded tooling)
**Researched:** 2026-02-01
**Confidence:** HIGH (based on direct code analysis of all 14 modules)

---

## Table Stakes

Tests that prevent hardware damage, data loss, or silent corruption. A bug in any of these functions can brick an MCU board or overwrite another device's configuration. Missing these = the test suite fails its purpose.

| # | Test Target | Module | Why Critical | Complexity | Est. Tests |
|---|-------------|--------|-------------|------------|------------|
| 1 | `extract_mcu_from_serial()` | discovery.py | **Wrong MCU extraction = wrong firmware on wrong chip = bricked board.** This regex parses `usb-Klipper_stm32h723xx_290...` into `stm32h723`. Must handle: Klipper/katapult prefixes, case variations, suffix stripping (`xx`, `xe`), non-Klipper devices returning None (Beacon probe). Used in both single-flash MCU cross-check and Flash All safety guard. | Low | 8-10 |
| 2 | `validate_mcu()` (ConfigManager) | config.py | **Guards the "is this config for this board?" check.** Bidirectional prefix match: `stm32h723` must match `stm32h723xx` AND vice versa. A false positive here silently allows flashing STM32F4 firmware onto an STM32H7 board. | Low | 6-8 |
| 3 | `parse_mcu_from_config()` | config.py | **Extracts MCU from Kconfig `.config` file.** If this returns wrong value or None on valid config, MCU validation breaks silently. Must test: `CONFIG_MCU="stm32h723xx"` primary path, `CONFIG_BOARD_DIRECTORY="rp2040"` fallback, missing file, malformed content. | Low | 5-7 |
| 4 | `match_devices()` | discovery.py | **Determines which physical USB device gets flashed.** Wrong match = wrong board flashed. Tests must verify fnmatch glob behavior with real-world serial patterns including wildcard-at-end patterns like `usb-Klipper_stm32h723xx_29001A*`. | Low | 5-6 |
| 5 | `generate_device_key()` | validation.py | **Slug collision = one device's config cache overwrites another's.** Tests must cover: Unicode folding (`Cafe` with accent), punctuation stripping, hyphen collapsing, 64-char truncation at boundary, `-2`/`-3` collision suffixes, empty-after-normalization ValueError. | Low | 8-10 |
| 6 | `generate_serial_pattern()` | discovery.py | **Generated pattern is stored permanently and used for ALL future device matching.** Wrong pattern = device never found again, or matches wrong device. Must strip `-ifNN` suffix and append `*`. | Low | 4-5 |
| 7 | Flash All safety guards | flash.py | **Batch automation removes human oversight -- these 4 guards are the only protection.** Each must be tested independently: (1) ambiguous USB pattern detection (`match_devices` returning >1), (2) duplicate USB path guard (`used_paths` set preventing same physical device flashed twice), (3) MCU cross-check (`extract_mcu_from_serial` vs registry MCU), (4) missing cached config rejection. | Medium | 8-10 |
| 8 | `is_supported_device()` | discovery.py | **Gatekeeper deciding if USB device is Klipper/Katapult.** False positive = non-Klipper device (Beacon probe, random USB) enters flash pipeline. Must be case-insensitive prefix check. | Low | 4-5 |
| 9 | Registry round-trip | registry.py | **Data corruption in JSON = lost device registrations.** Verify all DeviceEntry fields survive load/save/load cycle including: `flash_method=None`, `flashable=True/False`, blocked_devices list with string and dict formats. | Low | 3-4 |

**Total table stakes: ~51-65 tests across 9 targets**

---

## Differentiators

Tests that improve confidence and catch regressions, but a bug here causes bad UX or wrong information rather than hardware damage. Add these after table stakes are solid.

| # | Test Target | Module | Value Proposition | Complexity | Est. Tests |
|---|-------------|--------|-------------------|------------|------------|
| 1 | `validate_device_key()` | validation.py | Prevents invalid registry keys (empty, bad chars, duplicates). Failure = confusing error downstream, not data loss. | Low | 5-6 |
| 2 | `validate_numeric_setting()` | validation.py | Range checking for stagger_delay, return_delay. Wrong value = annoying timing, not dangerous. | Low | 4-5 |
| 3 | `_blocked_reason_for_filename()` and `_blocked_reason_for_entry()` | flash.py | Blocklist matching prevents flashing non-MCU devices. Catches policy violations but table-stakes safety guards also catch these. | Low | 4-5 |
| 4 | `detect_firmware_flavor()` | moonraker.py | Distinguishes "Kalico" vs "Klipper" from version strings (`v2026.01` vs `v0.12.0`). Cosmetic but confirms version parsing works. | Low | 4-5 |
| 5 | `is_mcu_outdated()` and `_parse_git_describe()` | moonraker.py | Version comparison logic. Wrong answer = user reflashes unnecessarily or skips needed update. Informational only -- never blocks flash. | Low | 6-8 |
| 6 | `get_cache_age_display()` | config.py | Human-readable age strings ("2 hours ago", "14 days ago (Recommend Review)"). Wrong = confusing display. | Low | 4-5 |
| 7 | `_resolve_flash_method()` | flash.py | Device override vs global default resolution. Wrong = unexpected flash method, but fallback logic provides safety net. | Low | 3-4 |
| 8 | Registry edge cases | registry.py | Graceful handling of corrupt JSON, missing fields, hand-edited files. Raises `RegistryError` vs silent data loss. | Low | 3-4 |
| 9 | `find_registered_devices()` | discovery.py | Correct matched/unmatched partitioning. Wrong = TUI shows wrong status, but flash safety guards catch issues downstream. | Low | 3-4 |

**Total differentiators: ~36-46 tests across 9 targets**

---

## Anti-Features

Tests to deliberately NOT write. Each wastes time, adds maintenance burden, and provides false confidence.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Testing TUI rendering** (ansi.py, theme.py, panels.py, screen.py, tui.py) | TUI output is visual, changes frequently, and has zero safety impact. Testing ANSI escape sequences or panel layout is pure maintenance cost -- any UI change breaks tests without catching real bugs. ~4 modules, ~1500 lines with no testable safety logic. | Manual visual testing on Pi. These modules are pure presentation. |
| **Testing subprocess calls** (build.py `run_build`, `run_menuconfig`; service.py `klipper_service_stopped`; flasher.py `_try_katapult_flash`, `_try_make_flash`) | These wrap `subprocess.run()` with timeouts. The logic is trivial: call external tool, check returncode, return result dataclass. Mocking subprocess provides false confidence -- the real risk is hardware interaction, which no mock captures. | Test the *decision logic* around subprocess results (e.g., Flash All skipping failed builds, fallback method selection). Not the subprocess calls themselves. |
| **Testing `scan_serial_devices()`** | Reads `/dev/serial/by-id/` directory listing. The function is 5 lines of `Path.iterdir()`. Mocking the filesystem for this provides zero value. | Test the functions that *consume* scan results: `match_devices`, `find_registered_devices`, `is_supported_device`. |
| **Testing Moonraker HTTP calls** (`get_print_status`, `get_mcu_versions`, `get_host_klipper_version`) | Network calls with graceful degradation (all return None on any error via broad except clause). Mocking urllib to test "did we return None on URLError?" is obvious and low-value. | Test the pure functions that *process* Moonraker responses: `detect_firmware_flavor`, `is_mcu_outdated`, `_parse_git_describe`. |
| **Testing `_atomic_copy` / `_atomic_write_json`** | These use the well-established temp-file-fsync-rename pattern. The atomicity guarantee comes from OS `os.replace()` semantics, not our code. Testing our wrapper around OS primitives is testing the OS. | Trust the pattern. Registry round-trip tests exercise atomic write indirectly. |
| **Testing interactive prompts / user input flows** | All user interaction goes through `out` interface or raw `input()`. Testing input/output flow requires mocking stdin/stdout extensively for minimal safety value. The interesting logic is in the *validation* of user input, not the prompting. | Test the pure validation functions: `validate_device_key`, `validate_numeric_setting`, `generate_device_key`. |
| **Snapshot tests for output formatting** | Output format changes with every UI iteration. Snapshot tests become a friction tax on every cosmetic change, catching zero bugs. | No replacement needed. Output formatting is not a correctness concern. |
| **Testing `check_katapult()` bootloader detection** | Complex hardware interaction: sends command to enter bootloader, polls for USB device change, performs USB sysfs reset on failure. Every code path depends on physical USB hardware state. Mocking this deeply enough to be useful recreates the entire function. | Hardware-only testing on Pi. This function is correctly structured (returns `KatapultCheckResult` tri-state) but untestable without hardware. |
| **Testing error message formatting** (`errors.py` templates, `format_error()`) | String formatting with no logic. Testing "does the template produce the right string" is testing Python f-strings. | Not worth testing. Visual review during development is sufficient. |

---

## Feature Dependencies

```
extract_mcu_from_serial() ---> validate_mcu() bidirectional match
     |                              [MCU string format must be consistent]
     +---> Flash All MCU cross-check (cmd_flash_all line 1279)
              [same extraction used in safety guard]

generate_serial_pattern() ---> match_devices() glob matching
     |                              [pattern format must produce valid globs]
     +---> find_registered_devices()
              [stored patterns used for cross-reference]

generate_device_key() ---> Registry.get() collision check
     |                         [key lookup for uniqueness]
     +---> ConfigManager path construction
              [key determines config cache directory]

parse_mcu_from_config() ---> validate_mcu()
                                 [extracted MCU compared to registry MCU]
```

**Key insight:** The dependency chain shows that `extract_mcu_from_serial` is the most upstream safety function. If it returns wrong output, both single-flash and batch-flash safety checks are compromised. This is why it is test target #1.

---

## MVP Test Recommendation

For maximum safety coverage with minimum test count, build in this order:

### Phase 1: Safety-Critical (blocks first release of test suite)

1. **`extract_mcu_from_serial()`** -- Single most dangerous function. Every serial name variant in the wild must parse correctly. Include edge cases: case variations (`Klipper` vs `katapult`), unknown MCU types, non-Klipper devices returning None, suffix variants (`xx`, `xe`, none).

2. **`validate_mcu()` + `parse_mcu_from_config()`** -- The MCU safety gate. Test the full chain: config file content -> parse MCU string -> bidirectional prefix match. Include: `stm32h723` vs `stm32h723xx`, `rp2040` (no suffix), `stm32f411` vs `stm32f411xe`, missing `CONFIG_MCU` with `CONFIG_BOARD_DIRECTORY` fallback, missing file.

3. **`generate_device_key()`** -- Data integrity. Test: Unicode names, punctuation stripping, 64-char truncation at exact boundary, collision suffix generation (`-2`, `-3`), empty-after-normalization error.

4. **`match_devices()` + `generate_serial_pattern()`** -- Device targeting. Test: wildcard matching, no-match returns empty list, multi-match returns all (Flash All depends on count for ambiguity detection), `-ifNN` suffix stripping.

5. **Flash All safety guards** -- Batch safety. Test each guard as isolated logic: ambiguous pattern rejection (>1 match), duplicate USB path rejection (`used_paths` set), MCU cross-check rejection (USB MCU != registry MCU), missing config rejection.

### Phase 2: Confidence (add after Phase 1 is solid)

6. **`is_supported_device()`** + **Registry round-trip** -- Remaining table stakes.

7. **Version parsing** (`_parse_git_describe`, `is_mcu_outdated`, `detect_firmware_flavor`) -- Most complex differentiator logic.

8. **Validation functions** (`validate_device_key`, `validate_numeric_setting`) -- Input safety.

9. **Blocklist matching** + **`find_registered_devices()`** -- Remaining differentiators.

### Total target: ~50-65 tests (Phase 1) growing to ~90-110 (Phase 1 + Phase 2)

This stays well under "hundreds of low-value tests" while covering every path where a bug causes hardware damage or data loss.

---

## Sources

- Direct code analysis: `discovery.py` (extract_mcu_from_serial regex, match_devices fnmatch, generate_serial_pattern)
- Direct code analysis: `config.py` (parse_mcu_from_config regex, validate_mcu bidirectional prefix match)
- Direct code analysis: `validation.py` (generate_device_key slug pipeline, validate_device_key regex)
- Direct code analysis: `flash.py` cmd_flash_all lines 1240-1283 (4 safety guards in batch flash loop)
- Direct code analysis: `registry.py` (load/save round-trip with optional fields, blocked_devices parsing)
- Direct code analysis: `moonraker.py` (_parse_git_describe, is_mcu_outdated, detect_firmware_flavor)
- Domain knowledge: firmware flashing tools where wrong-device-flash = bricked MCU requiring physical BOOT0 pin recovery
