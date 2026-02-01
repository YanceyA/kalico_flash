# Project Research Summary

**Project:** kalico-flash v4.2 (Test Framework)
**Domain:** Test suite for safety-critical firmware flash tool
**Researched:** 2026-02-01
**Confidence:** HIGH

## Executive Summary

This research evaluated how to add comprehensive testing to kalico-flash, a Python TUI tool that automates firmware building and flashing for Klipper/Kalico MCU boards. The tool has zero tests currently despite operating in a safety-critical domain where bugs can physically brick expensive boards. The recommended approach is pytest-based unit testing focused on pure function logic, using real filesystem fixtures for I/O validation and deliberately avoiding TUI/subprocess testing.

The codebase is well-architected for testing: 22 pure functions handle critical safety logic (MCU extraction, pattern matching, slug generation, config validation), existing dataclass contracts enable clean test fixtures, and the hub-and-spoke module structure prevents cross-dependencies. The highest ROI comes from testing these pure functions with parametrized test cases covering edge cases, real-world serial device naming variants, and the subtle bidirectional MCU prefix matching that prevents wrong-firmware-on-wrong-board scenarios.

Key risks are over-mocking (coupling tests to implementation details rather than behavior), testing TUI rendering instead of business logic, and chasing coverage metrics instead of safety value. The recommended MVP is 50-65 focused tests targeting the 9 safety-critical functions where bugs cause hardware damage, followed by 40-50 additional tests for confidence/regression coverage. This achieves comprehensive safety validation without the maintenance burden of hundreds of low-value tests.

## Key Findings

### Recommended Stack

Research confirms pytest as the optimal test framework based on three decisive factors: (1) native `@pytest.mark.parametrize` support which is critical for data-driven testing of MCU extraction and pattern matching functions with their many input variants, (2) built-in `tmp_path` fixture for real filesystem testing without cleanup boilerplate, and (3) rich assertion introspection that provides clear failure context. The stdlib `unittest.mock` handles all mocking needs without additional dependencies.

**Core technologies:**
- **pytest >=7.0** - Test runner, parametrize, fixtures; best fit for pure function data-driven testing with minimal boilerplate
- **unittest.mock** - All mocking needs; already in stdlib, works natively with pytest
- **tmp_path fixture** - Temp directory management; tests Registry persistence, config cache, atomic writes with real files
- **monkeypatch fixture** - Environment isolation; XDG_CONFIG_HOME, SERIAL_BY_ID constant, time-dependent functions

**Critical decision: pytest vs unittest**
Parametrize is the deciding factor. High-value test targets (`extract_mcu_from_serial`, `validate_mcu`, `generate_device_key`) are pure functions with 8-10 input/output pairs each. With pytest, each case becomes a distinct test in output. With unittest's `subTest`, they share a single pass/fail. This difference is critical for debugging failures in CI or during development.

### Expected Features

Testing requirements split into table stakes (safety-critical) and differentiators (confidence/UX). Research identified 9 table-stakes test targets totaling 51-65 tests and 9 differentiator targets adding 36-46 tests.

**Must have (table stakes - blocks first release):**
- `extract_mcu_from_serial()` tests - Wrong MCU extraction = wrong firmware on wrong chip = bricked board (8-10 tests)
- `validate_mcu()` + `parse_mcu_from_config()` - Guards "is this config for this board?" check with bidirectional prefix match (6-8 + 5-7 tests)
- `match_devices()` + `generate_serial_pattern()` - Device targeting logic; wrong match = wrong board flashed (5-6 + 4-5 tests)
- `generate_device_key()` - Slug collision = one device's config overwrites another's (8-10 tests)
- Flash All safety guards - Batch automation 4-guard system (ambiguous pattern, duplicate path, MCU cross-check, missing config) (8-10 tests)
- `is_supported_device()` - Gatekeeper preventing non-Klipper devices entering flash pipeline (4-5 tests)
- Registry round-trip - JSON corruption = lost device registrations (3-4 tests)

**Should have (confidence/regression):**
- `validate_device_key()` - Prevents invalid registry keys; bad UX not data loss (5-6 tests)
- Version parsing (`_parse_git_describe`, `is_mcu_outdated`, `detect_firmware_flavor`) - Informational only, never blocks flash (14-18 tests)
- Validation functions (`validate_numeric_setting`, blocklist matching) - Input safety and policy enforcement (11-14 tests)
- `find_registered_devices()` - TUI status display accuracy (3-4 tests)

**Defer (anti-features - deliberately NOT testing):**
- TUI rendering (ansi.py, theme.py, panels.py, screen.py, tui.py) - Visual testing, zero safety impact, pure maintenance cost
- Subprocess calls (build.py, service.py, flasher.py) - Trivial wrappers; mocking provides false confidence; hardware interaction risk unmockable
- `scan_serial_devices()` - 5-line `Path.iterdir()` wrapper; test consumers instead
- Moonraker HTTP calls - Graceful degradation (return None); test pure response processors instead
- Atomic write primitives - Testing OS `os.replace()` semantics, not our code
- Interactive prompts - Test validation functions, not input/output flow
- Error message formatting - String formatting with no logic

### Architecture Approach

The codebase exhibits excellent testability through pure function extraction, dependency injection, and dataclass contracts. Architecture analysis identified 5 tiers of testability: Tier 1 pure functions (22 functions, zero mocking), Tier 2 filesystem dependencies (6 functions, tmp_path fixtures), Tier 3 subprocess (11 functions, defer to Phase 3), Tier 4 network (4 functions, defer to Phase 4), and Tier 5 TUI-coupled (skip entirely).

**Major test architecture components:**
1. **Pure function tests** - 22 functions (discovery, validation, moonraker parsing, flash helpers, errors, models) take inputs/return outputs with no side effects; test with direct calls and parametrize
2. **Filesystem integration tests** - Registry and ConfigManager use injectable paths; test with real temp files via `tmp_path`, monkeypatch for `XDG_CONFIG_HOME`
3. **Stub registry for validation** - `generate_device_key()` and `validate_device_key()` need registry.get(); use simple stub class, not MagicMock
4. **Test seams already exist** - No refactoring needed: Registry(registry_path), ConfigManager(device_key, klipper_dir), Output protocol with NullOutput, dataclass contracts, hub-and-spoke module structure

**Key architectural insight:** The dependency chain shows `extract_mcu_from_serial` is the most upstream safety function. If it returns wrong output, both single-flash and batch-flash safety checks are compromised. This determines test priority ordering.

### Critical Pitfalls

**Top 5 pitfalls from research:**

1. **Mocking implementation details instead of testing behavior (CRITICAL)** - Tests that mock internal function calls (`@patch('kflash.discovery.Path.iterdir')`) and assert call sequences break on any refactor. Prevention: Test pure functions with direct calls; use tmp_path for filesystem; reserve mocking for subprocess/network boundaries only.

2. **Testing TUI rendering instead of business logic (CRITICAL)** - TUI is largest module (1400 lines) but has zero safety impact. Tests for ANSI output, cursor positioning, panel layout are brittle and catch no real bugs. Prevention: DO NOT test tui.py, panels.py, screen.py, ansi.py; DO test discovery.py, validation.py, config.py, registry.py safety functions.

3. **Forgetting bidirectional prefix match is the whole point (CRITICAL)** - `validate_mcu()` line 196 implements `actual_mcu.startswith(expected_mcu) or expected_mcu.startswith(actual_mcu)`. Testing only exact matches misses the production scenario (registry says "stm32h723", config says "stm32h723xx"). Prevention: Required test cases must cover both directions of prefix match AND rejection of different families.

4. **Mocking subprocess where tmp_path would work (MODERATE)** - Mocking Path.exists(), open(), json.loads() for Registry/ConfigManager is fragile and doesn't catch real bugs (path encoding, missing parents, atomic write races). Prevention: Use real files in tmp_path for all filesystem operations; reserve @patch for subprocess.run, urlopen.

5. **Writing hundreds of trivial tests for coverage numbers (MODERATE)** - Aiming for "90% coverage" produces tests that check dataclass defaults or duplicate implementation. Target is ~50-65 focused tests (Phase 1) growing to ~90-110 (Phase 1+2), not 200+ tests. Prevention: Every test must answer "What bug does this catch?"

## Implications for Roadmap

Based on research, suggested phase structure follows testability tiers and risk priority:

### Phase 1: Safety-Critical Pure Functions
**Rationale:** These 5 test targets block first release. They cover every path where a bug causes hardware damage or data loss. All are pure functions (zero mocking, fastest to write) with established test patterns.
**Delivers:** 40-50 tests covering MCU extraction/validation, device pattern matching, slug generation, Flash All guards
**Addresses:** Table-stakes features #1-5, #7 (extract_mcu, validate_mcu, parse_mcu, match_devices, generate_serial_pattern, generate_device_key, Flash All guards)
**Avoids:** Pitfall TEST-2 (testing TUI instead of logic), TEST-7 (missing bidirectional prefix match)
**Complexity:** LOW - all pure functions, direct calls, parametrize-driven

### Phase 2: Remaining Table Stakes + Top Differentiators
**Rationale:** Completes safety coverage (is_supported_device, Registry round-trip) then adds highest-value regression tests (version parsing is most complex differentiator logic).
**Delivers:** 15-20 tests for remaining safety + 14-18 tests for version parsing
**Uses:** tmp_path for Registry tests, stub registry for validation
**Implements:** Filesystem integration testing pattern, real JSON round-trips
**Addresses:** Table-stakes #6, #9; differentiators #4, #5 (is_supported_device, Registry, version parsing)
**Avoids:** Pitfall TEST-6 (mocking JSON instead of real files)

### Phase 3: Remaining Differentiators
**Rationale:** Completes test suite with lower-priority validation and blocklist tests. These improve confidence but bugs here cause bad UX, not data loss.
**Delivers:** 15-20 tests for validation functions, blocklist matching, find_registered_devices
**Addresses:** Differentiators #1, #2, #3, #9 (validate_device_key, validate_numeric_setting, blocklist, find_registered_devices)
**Complexity:** LOW - mostly pure functions with edge case focus

### Phase 4 (Optional): Subprocess/Network Mocking
**Rationale:** DEFER unless specific regression needs arise. These tests mock subprocess.run/urlopen extensively for minimal safety value. The real risk is hardware interaction, which mocks don't capture.
**Delivers:** Mocked tests for build.py, flasher.py, service.py, moonraker.py API calls
**Uses:** unittest.mock.patch for subprocess/urllib
**Complexity:** MEDIUM - complex mocking, low confidence value

### Phase Ordering Rationale

- **Pure functions first (Phase 1):** Zero infrastructure needed, fastest to write, highest safety ROI. Validates core logic that all other code depends on.
- **Filesystem integration second (Phase 2):** Depends on understanding dataclass contracts from Phase 1. Registry round-trips test actual I/O and catch real corruption bugs.
- **Differentiators third (Phase 3):** Once safety is solid, add regression/UX tests. These are lower priority but easy wins.
- **Subprocess/network last (Phase 4):** DEFER by default. Only add if specific bugs justify the mocking complexity. The orchestrator functions are integration-tested manually on hardware.

### Research Flags

**Phases with standard patterns (skip research-phase):**
- **Phase 1:** Well-documented pytest parametrize patterns; pure function testing is textbook
- **Phase 2:** Standard tmp_path fixture usage; JSON round-trip testing is established
- **Phase 3:** Straightforward edge case enumeration; no novel patterns

**No phases need deeper research.** The testing patterns are mature and well-documented. The main implementation questions ("Which 22 pure functions?" "What are the edge cases?") are already answered by code analysis in FEATURES.md and PITFALLS.md.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | pytest and unittest.mock are mature, stable tools with 10+ years of ecosystem validation |
| Features | HIGH | Based on direct code analysis of all 14 modules; test targets identified by tracing dependency chains and safety-critical paths |
| Architecture | HIGH | Direct source code analysis confirmed existing test seams (injectable paths, dataclass contracts, Output protocol); no refactoring needed |
| Pitfalls | HIGH | Concrete examples drawn from actual codebase functions (config.py:196 bidirectional match, discovery.py:80 MCU regex, validation.py slug pipeline) |

**Overall confidence:** HIGH

### Gaps to Address

No critical gaps. All research questions resolved:

- **Stack choice rationale:** Confirmed pytest wins on parametrize alone; no further framework evaluation needed
- **Test target identification:** Complete; 22 pure functions catalogued with complexity ratings and test estimates
- **Mocking strategy:** Clear boundaries established (tmp_path for filesystem, monkeypatch for env, stub for registry, defer subprocess/network)
- **Test count target:** Quantified as 50-65 (Phase 1) to 90-110 (Phase 1+2), avoiding coverage-metric trap

**Minor validation during implementation:**
- Confirm pytest >=7.0 installs cleanly on both Windows dev environment and Pi (expected: yes, pytest is universal)
- Verify tmp_path works correctly with Path vs str serialization in dataclasses (expected: yes, use str(tmp_path) when passing to constructors)

## Sources

### Primary (HIGH confidence)
- Direct source code analysis: All 14 kflash modules examined for testability, dependency patterns, and safety-critical logic paths
- pytest stable API documentation - mature framework with unchanged core features across major versions
- unittest.mock stdlib documentation - Python standard library guarantees
- CLAUDE.md project architecture documentation - confirms hub-and-spoke structure, dataclass contracts, existing Output protocol

### Secondary (MEDIUM confidence)
- Python testing best practices - general industry consensus on pure-function-first testing, mocking boundaries, fixture composition
- Domain knowledge: firmware flashing tools where wrong-device-flash = bricked MCU requiring physical recovery (BOOT0 pin jumper, serial bootloader)

---
*Research completed: 2026-02-01*
*Ready for roadmap: yes*
