# Project Research Summary

**Project:** kalico-flash v3.3 (Config Device)
**Domain:** Python CLI firmware build/flash tool for Klipper 3D printer MCUs
**Researched:** 2026-01-31
**Confidence:** HIGH

## Executive Summary

The "Config Device" feature adds per-device property editing to kalico-flash via a TUI configuration screen accessible from the main menu. Research shows this feature follows an exact replica of the existing global config screen pattern - same interaction model, same rendering approach, same validation flow. The implementation requires zero new dependencies, uses only stdlib APIs already imported elsewhere in the codebase, and integrates cleanly into the existing hub-and-spoke architecture with no new modules.

The recommended approach provides five editable fields: display name (text input), device key (text with slug validation), flash method (cycle between "katapult"/"make_flash"/default), flashable status (boolean toggle), and optionally MCU type. Serial pattern is displayed as read-only since it's hardware-derived and editing it breaks device matching. The most complex operation is device key rename, which must atomically update both the registry JSON and the cached config directory on disk using a single load-modify-save cycle with `shutil.move()` for directory migration.

The main risk is partial state corruption during key rename - registry updated but config directory not moved, or vice versa. Prevention requires strict ordering: validate new key uniqueness FIRST, move config directory SECOND using `shutil.move()`, then update registry THIRD in a single atomic save. All the architectural patterns needed already exist in the codebase: atomic registry writes in registry.py, panel-based config screens in tui.py, validation helpers in validation.py. This is a composition exercise, not invention.

## Key Findings

### Recommended Stack

No new stack elements needed. The feature uses existing stdlib APIs and proven codebase patterns exclusively. All required capabilities already exist in current modules.

**Core technologies:**
- `shutil.move()` — Config cache directory migration on key rename - handles cross-filesystem moves safely, already imported in config.py
- `dataclasses.replace()` — Create modified DeviceEntry for in-memory edits - already used in _config_screen for GlobalConfig
- `re.match()` — Device key validation with slug format (lowercase, alphanumeric + hyphens) - already imported in config.py
- `pathlib.Path` — Config directory existence checks before migration - already used throughout config.py

**Integration points (existing modules only):**
- `registry.py` — Add `update_device()` method following existing load-modify-save pattern from add/remove
- `config.py` — Add `rename_config_cache()` helper for directory migration on key change
- `tui.py` — New `_device_config_screen()` following _config_screen pattern exactly (getch loop, setting dispatch, immediate save)
- `screen.py` — New `render_device_config_screen()` and `DEVICE_SETTINGS` list following existing panel rendering
- `validation.py` — Add `validate_device_key()` following existing validation helper pattern

**Key architectural decision:** No new `Registry.rename()` method. Key rename is implemented as delete-old-key + insert-new-key + single-save in the action handler. This keeps Registry API minimal and follows the existing load-modify-save pattern used throughout the codebase.

### Expected Features

Research identified clear must-haves (table stakes for device editing) vs should-haves (polish) vs anti-features (explicitly excluded).

**Must have (table stakes):**
- Show current device property values before editing - users expect to see what they're changing
- Edit display name via text input - most common operation, uses current value as default
- Edit flash method override - cycle between "default"/"katapult"/"make_flash" on single keypress
- Edit flashable status - boolean toggle to include/exclude from flash-all batch operations
- Immediate persistence on each edit - matches existing global config screen behavior, no "save" button
- Device selection prompt - pick which device to configure via numbered menu, reuses _prompt_device_number

**Should have (competitive):**
- Device key rename with config cache migration - valuable but complex, requires atomic registry + directory operations
- Show effective flash method when using default - display "default (katapult)" so user sees actual behavior based on global config
- Input validation with clear feedback - reject empty names, duplicate keys, invalid key formats (spaces, special chars)
- Read-only device identity display - show MCU and serial_pattern at top of screen for context without allowing edits

**Defer (post-MVP):**
- Edit MCU type - MCU is hardware-derived from USB discovery, editing breaks config cache matching; require remove and re-add instead
- Edit serial pattern - pattern is auto-generated from discovery, manual editing breaks device matching and is error-prone
- Multi-device batch edit - users typically have 2-5 devices, single-device editing with fast toggle UX is sufficient
- Undo/revert changes - adds state tracking complexity for minimal benefit; each field saves immediately like global config

**Anti-features (explicitly excluded):**
- Free-form JSON editing - exposes raw registry format, error-prone, breaks abstraction
- Delete device from config screen - delete is destructive and already handled by Remove Device (R key) with separate confirmation flow
- Edit blocked_devices list - blocked devices are a separate registry concept, mixing them into device config muddies the UI
- Transaction/rollback system - overengineered for simple field edits; immediate save matches existing config screen pattern

### Architecture Approach

The feature slots into the existing hub-and-spoke architecture with zero new modules. Implementation mirrors the existing global config screen (_config_screen in tui.py) but targets DeviceEntry instead of GlobalConfig. The TUI orchestrates all interactions, screen.py handles pure rendering, registry.py persists atomically, and validation.py provides reusable validation functions.

**Component modifications (5 files):**
1. **tui.py** — New `_device_config_screen()` function mirroring _config_screen structure (while True loop, getch, dispatch, save), new "e" key handler in run_menu, new _action_config_device handler
2. **screen.py** — New `DEVICE_SETTINGS` list defining editable fields, new `render_device_config_screen()` function following existing panel pattern, add "E" to ACTIONS list
3. **registry.py** — New `update_device(old_key, new_entry)` method implementing atomic rename (delete old + insert new + single save)
4. **config.py** — New `rename_config_cache(old_key, new_key)` function using shutil.move() for directory migration
5. **validation.py** — New `validate_device_key(key, existing_keys, current_key)` function with slug format + uniqueness checks

**Data flow for device config action:**
```
User presses "E" in main menu
    |
    v
tui.py: run_menu dispatches to _action_config_device
    |
    v
tui.py: _prompt_device_number (reused from Flash/Remove)
    |
    v
tui.py: _device_config_screen(registry, out, device_key)
    |
    +-- Load: registry.get(device_key) -> DeviceEntry
    |
    +-- Render: screen.render_device_config_screen(entry) -> panel string
    |
    +-- Input: _getch() -> setting number
    |
    +-- Edit dispatch (same pattern as _config_screen):
    |     toggle (flashable): flip immediately, registry.update_device(...)
    |     cycle (flash_method): next value, registry.update_device(...)
    |     text (name): input() with validation, registry.update_device(...)
    |     key rename: input() + validate_device_key()
    |                + config.rename_config_cache(old, new)
    |                + registry.update_device(old_key, new_entry with new key)
    |
    +-- Loop back to render until Esc/B
    |
    v
Returns (status_message, status_level) to run_menu
```

**Key design decision: Serial pattern editability**

Serial pattern is auto-generated from USB discovery during add-device and follows a specific glob format (e.g., `usb-Klipper_stm32h723xx_*`). Allowing free-text editing creates risk of broken patterns that silently break device matching. **Recommendation:** Display serial pattern as read-only info in the config screen (type "readonly" in DEVICE_SETTINGS). If user needs to change it, they remove and re-add the device.

**Why no new modules:** Device config is a TUI interaction that orchestrates existing subsystems (registry persistence, panel rendering, validation). Creating a new module (e.g., device_config.py) would extract code that logically belongs in tui.py alongside the other _action_ handlers and config screen implementations.

### Critical Pitfalls

From PITFALLS.md v4.0 research, the top 5 risks for device config implementation:

1. **Orphaned Config Cache After Key Rename (CFG-1)** — User renames device key from "octopus-pro" to "octo-v11". Registry updates to new key, but cached .config remains at `~/.config/kalico-flash/configs/octopus-pro/.config`. Next flash sees no cached config and forces menuconfig. **Prevention:** Key rename MUST move config directory using `shutil.move(get_config_dir(old_key), get_config_dir(new_key))` BEFORE registry save. If old directory doesn't exist, skip silently. Test: verify old dir gone and new dir contains .config after rename.

2. **Partial Registry Update on Crash (CFG-4)** — Power loss or Ctrl+C between removing old key and adding new key leaves device missing from registry entirely. **Prevention:** Implement rename as SINGLE load-modify-save cycle, not two separate save calls. Example: `data = registry.load(); del data.devices[old_key]; data.devices[new_key] = new_entry; registry.save(data)`. The existing _atomic_write_json ensures JSON is either fully old or fully new.

3. **Key Rename Collision with Existing Device (CFG-2)** — User renames "octopus" to "nitehawk" but "nitehawk" already exists, overwriting another device's registration and config cache. **Prevention:** Validate new key does not exist in registry AND config directory does not already exist on disk BEFORE any mutations. Fail fast, mutate late. Check both `new_key in registry.devices` and `get_config_dir(new_key).exists()`.

4. **Key Validation Inconsistency (CFG-5)** — Add-device wizard validates keys one way (lowercase alphanumeric + hyphens), edit/rename flow validates differently or skips validation, allowing invalid keys with spaces, slashes, or shell metacharacters. **Prevention:** Extract shared `validate_device_key()` function in validation.py with rules: lowercase, alphanumeric + hyphens only, no leading/trailing hyphens, 1-40 chars. Call same function from both add and rename flows. Block path-unsafe characters: `/`, `\`, `..`, null bytes.

5. **DeviceEntry.key Field Not Updated (CFG-6)** — Developer renames registry dict key but forgets to update `.key` field on DeviceEntry dataclass. The entry's .key field still says "old-key" even though it's stored under "new-key" in dict. **Prevention:** Always create NEW DeviceEntry with new key using `dataclasses.replace(entry, key=new_key)` or full constructor. Never mutate entry.key on existing instance. The .key field is used at runtime for display and must match registry dict key.

**Additional critical pitfall:**
- **Flash Method Edit Accepts Invalid Values (CFG-7)** — User edits flash_method to "katapault" (typo) or "usb" (not valid). Value stored in registry, fails at flash time with confusing error. **Prevention:** Define valid flash methods as constant `VALID_FLASH_METHODS = {"katapult", "make_flash"}`. Use selection/cycle UI (keypress toggles), not free text input. Validate at edit time, not flash time.

## Implications for Roadmap

Based on research, suggested phase structure for v3.3:

### Phase 1: Foundation - Registry + Validation
**Rationale:** Registry update mechanism and validation are prerequisites for everything else. Build from bottom up following dependency order. These are the layers other phases depend on.

**Delivers:**
- `registry.update_device(old_key, entry)` method with atomic save (delete old + insert new + single save)
- `validation.validate_device_key(key, existing_keys, current_key)` with slug format validation + uniqueness check
- `config.rename_config_cache(old_key, new_key)` for directory migration using shutil.move()

**Addresses:**
- Pitfall CFG-2 (collision check before mutations)
- Pitfall CFG-4 (single save cycle, not two)
- Pitfall CFG-5 (shared validation function)

**Avoids:** Building TUI before persistence layer exists, inconsistent validation logic duplicated across add/edit flows

**Research flag:** No additional research needed - patterns verified in existing registry.py, validation.py. Stack elements confirmed (shutil, pathlib, re all stdlib).

---

### Phase 2: Rendering Layer - Screen Panels
**Rationale:** Screen rendering is pure (no side effects) and independently testable. Can be developed and tested by calling directly with mock DeviceEntry before TUI integration. No dependencies on Phase 1 except data models.

**Delivers:**
- `DEVICE_SETTINGS` list definition in screen.py (fields, labels, types)
- `render_device_config_screen(entry)` function following existing render_config_screen pattern
- Read-only identity section (MCU, serial_pattern displayed but not numbered/editable)

**Uses:**
- Existing `render_panel()` from panels.py for bordered box rendering
- Existing theme system for colors and spacing
- DeviceEntry model from models.py (no changes needed)

**Implements:** Display component from architecture - receives DeviceEntry, returns formatted multi-line string

**Addresses:** Table stakes features - show current values, read-only device identity for user orientation

**Research flag:** No additional research needed - panel rendering patterns verified in existing screen.py render_config_screen.

---

### Phase 3: TUI Interaction Loop
**Rationale:** Wires together rendering (Phase 2), validation (Phase 1), and persistence (Phase 1). Follows established _config_screen pattern exactly - minimal invention risk. This is composition, not creation.

**Delivers:**
- `_device_config_screen(registry, out, device_key)` function with while True edit loop
- Field dispatch logic: toggle (flashable), cycle (flash_method), text (name), key rename
- Device number prompt integration (reuses _prompt_device_number)
- Immediate save after each field edit (matches global config pattern)

**Uses:**
- Foundation from Phase 1: registry.update_device, validate_device_key, rename_config_cache
- Rendering from Phase 2: render_device_config_screen
- Existing _getch utility for single-keypress input
- Existing countdown_return pattern for back navigation

**Implements:** Interaction component - manages user input loop, orchestrates edits, calls registry save

**Addresses:**
- Table stakes: edit name, flash method, flashable with immediate save
- Pitfall CFG-1 (config cache migration on key rename)
- Pitfall CFG-6 (create new DeviceEntry, don't mutate)
- Pitfall CFG-7 (cycle UI for flash_method, not free text)

**Research flag:** No additional research needed - TUI pattern verified in existing _config_screen, device selection pattern in _prompt_device_number.

---

### Phase 4: Menu Integration
**Rationale:** Last step - adds new "E" action key to main menu. Cannot be done until TUI interaction loop (Phase 3) is functional and tested. This is the user-facing entry point.

**Delivers:**
- New "e" key handler in run_menu dispatch (flash.py or tui.py depending on architecture)
- _action_config_device handler wrapping _device_config_screen with try/except
- Updated ACTIONS list in screen.py: add ("E", "Edit Device") after Add Device
- Error handling: catch KeyboardInterrupt, RegistryError, return status tuple

**Integrates:** Phases 1-3 into existing main menu loop

**Addresses:** User-facing access to device config screen from main menu

**Avoids:** Incomplete integration - "E" key must work identically to other action keys (F/A/R/D/C/B)

**Research flag:** No additional research needed - action dispatch pattern verified in existing run_menu handlers (flash, add, remove all follow same pattern).

---

### Phase 5: Key Rename Enhancement (Optional)
**Rationale:** Device key rename is the most complex feature due to atomic registry + filesystem operations. Basic device editing (name, flash method, flashable) works without key rename. This can be deferred to post-MVP if time constrained, or implemented as part of Phase 3 if schedule allows.

**Delivers:**
- Key rename field in DEVICE_SETTINGS (conditionally enabled)
- Collision checking: validate against registry.devices AND existing config directories
- External reference warning: "Renaming will break scripts/aliases that use 'old-key'"
- Atomic update: rename_config_cache THEN registry.update_device in single transaction

**Addresses:**
- Pitfall CFG-1 (orphaned config cache)
- Pitfall CFG-3 (broken external references warning)
- Pitfall CFG-6 (create new DeviceEntry with new key)

**Avoids:** Shipping with key rename half-implemented - all or nothing feature due to atomicity requirements

**Research flag:** No additional research needed - pitfalls documented in PITFALLS.md CFG-1 through CFG-6, prevention strategies defined.

---

### Phase Ordering Rationale

- **Bottom-up dependency order:** Registry/validation (Phase 1) must exist before rendering (Phase 2) can be manually tested, rendering must exist before TUI loop (Phase 3) can be built, TUI must exist before menu integration (Phase 4) can wire it up.
- **Fail-fast validation in Phase 1:** All validation logic extracted first prevents invalid state from reaching Phase 3 (interaction loop). Invalid keys, duplicate keys, empty names all rejected at validation layer.
- **Independently testable layers:** Each phase produces testable output. Phase 1 functions can be called directly. Phase 2 rendering can be tested with mock DeviceEntry. Phase 3 TUI can be tested via SSH manual interaction before Phase 4 menu integration.
- **MVP vs Enhancement split:** Phases 1-4 deliver core device config editing (name, flash method, flashable). Phase 5 (key rename) is valuable but adds significant complexity - can be deferred if schedule pressure exists or included if time permits.

**Dependency graph:**
```
Phase 1 (Registry + Validation) ──┬──> Phase 3 (TUI Interaction)
                                  │          |
Phase 2 (Rendering) ──────────────┘          |
                                             |
                                             v
                                        Phase 4 (Menu Integration)
                                             |
                                             v
                                    Phase 5 (Key Rename - Optional)
```

### Research Flags

**All phases have standard patterns (skip research-phase):**
- **Phase 1:** Registry CRUD pattern verified in registry.py (add, remove, save all use load-modify-save). Validation pattern verified in validation.py (validate_numeric_setting, validate_path_setting as examples). Stdlib APIs verified (shutil.move, pathlib, re).
- **Phase 2:** Panel rendering pattern verified in screen.py (render_config_screen, SETTINGS list structure). render_panel utility confirmed in panels.py.
- **Phase 3:** TUI config screen pattern verified in tui.py (_config_screen while loop, _getch input, toggle/text dispatch, immediate save). Device selection pattern verified (_prompt_device_number).
- **Phase 4:** Action dispatch pattern verified in flash.py or tui.py run_menu (F/A/R/D handlers all follow try/except/return-tuple pattern). ACTIONS list pattern verified in screen.py.
- **Phase 5:** Key rename pitfalls documented in PITFALLS.md (CFG-1 through CFG-6). Prevention strategies defined. shutil.move() cross-filesystem behavior verified from Python stdlib docs.

**No phase requires additional research.** All patterns exist in codebase, all pitfalls documented, all stack elements verified. This is a composition task using proven patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All APIs are Python 3.9+ stdlib already imported in codebase. shutil.move in config.py, dataclasses.replace used in _config_screen, re imported in config.py, pathlib used throughout. |
| Features | HIGH | Feature requirements derived from existing global config screen UX. Must-haves match table stakes for config editing (show values, edit fields, immediate save). Anti-features explicitly defined based on overengineering risks. |
| Architecture | HIGH | Direct codebase analysis of all integration points. Pattern matching confirmed: _config_screen mirrors exactly for DeviceEntry. Hub-and-spoke architecture maintained - no cross-module imports. |
| Pitfalls | HIGH | Ten specific pitfalls researched via codebase analysis of registry.py (atomic save pattern), config.py (get_config_dir usage), models.py (DeviceEntry fields). Prevention strategies documented per pitfall with code examples. |

**Overall confidence:** HIGH

### Gaps to Address

Minor validation points to resolve during implementation:

- **Flash method validation:** Currently `Optional[str]` in DeviceEntry with no enum constraint. Need to define `VALID_FLASH_METHODS = {"katapult", "make_flash"}` constant and validate at edit time. **Resolution:** Add constant to models.py or registry.py, validate in TUI cycle handler. Low risk - straightforward addition.

- **Serial pattern editing decision:** Research recommends read-only (hardware-derived, editing breaks matching). Need to confirm with user if any use case requires pattern editing. **Resolution:** Display as read-only in Phase 2. If user feedback requests editing capability, add in post-MVP with live validation (scan /dev/serial/by-id/ after edit, show matches).

- **Config cache directory collision handling:** If new key's config directory already exists (leftover from previously deleted device), should we overwrite or abort? **Resolution:** Warn and offer choice, default to abort. Edge case - handle during Phase 5 (key rename) with explicit user prompt: "Config directory for 'new-key' already exists. Overwrite? [y/N]"

- **Concurrent registry access race:** Multiple SSH sessions editing registry simultaneously creates last-write-wins scenario. Atomic write prevents file corruption but not logical conflicts (Session A and Session B both load, edit different fields, whoever saves last wins). **Resolution:** Accept for MVP - single-user tool, unlikely scenario. Document limitation in CLAUDE.md or tool help. Consider advisory file locking (fcntl.flock) in future version if users report issues.

- **MCU field editability:** FEATURES.md research says MCU should be read-only (hardware-derived). ARCHITECTURE.md suggests MCU might be editable field. **Resolution:** Display as read-only by default. If use case emerges (user manually corrected MCU type), add as advanced edit with warning: "Changing MCU breaks config cache matching. Continue? [y/N]"

## Sources

### Primary (HIGH confidence)
- **Codebase analysis** — Direct inspection of all integration modules:
  - `kflash/registry.py` — Registry CRUD patterns (add/remove/save use load-modify-save), atomic save via _atomic_write_json, existing set_flashable method as precedent
  - `kflash/config.py` — Config cache directory path logic via get_config_dir(), existing shutil import for file operations
  - `kflash/tui.py` — Global config screen pattern in _config_screen() (while loop, getch, dispatch, immediate save), device number prompt in _prompt_device_number(), theme and rendering
  - `kflash/screen.py` — Panel rendering in render_config_screen(), SETTINGS list structure, ACTIONS list for menu keys
  - `kflash/validation.py` — Existing validation pattern for numeric/path settings as template
  - `kflash/models.py` — DeviceEntry dataclass with all editable fields (key, name, mcu, serial_pattern, flash_method, flashable)
  - `kflash/errors.py` — RegistryError for key conflicts, existing exception hierarchy
- **Python stdlib documentation** — shutil.move() cross-filesystem behavior, dataclasses.replace() immutable update pattern, pathlib.Path directory manipulation, re.match() pattern validation

### Secondary (MEDIUM confidence)
- **CLI UX patterns** — General config screen interaction patterns from similar tools (KIAUH panel-based menus, standard numbered selection prompts). Not tool-specific research but validated against existing kalico-flash patterns.

### Tertiary (LOW confidence)
- None - all research based on direct codebase analysis and stdlib documentation.

---
*Research completed: 2026-01-31*
*Ready for roadmap: yes*
