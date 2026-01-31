# Project Research Summary

**Project:** kalico-flash v4.0 (CLI Removal and Device Key Internalization)
**Domain:** Python CLI-to-TUI refactor for firmware build/flash tool
**Researched:** 2026-01-31
**Confidence:** HIGH

## Executive Summary

The v4.0 milestone removes argparse CLI flags and internalizes device keys, transforming kalico-flash from a hybrid CLI/TUI tool into a TUI-only application. Research shows this is a simplification exercise, not feature addition. The entire change requires zero new dependencies—only deletion of argparse and addition of a 4-line slugification function using stdlib `re.sub()`. Device keys transition from user-typed CLI arguments to auto-generated internal identifiers derived from display names.

The recommended approach: remove `build_parser()` and all CLI flag handling from `flash.py`, making `main()` launch straight to TUI. Add `generate_device_key()` in `validation.py` that slugifies display names ("Octopus Pro v1.1" → "octopus-pro-v1-1") with numeric suffixes for collisions. Crucially, existing devices.json keys remain unchanged—only new devices added after migration get auto-generated keys. Config cache directories stay where they are. No migration scripts needed. This preserves all existing user data while preventing future CLI complexity.

The primary risk is partial data corruption during the transition: user-facing strings still referencing `--device` flags, entry.key displayed instead of entry.name, or collision handling missing. Prevention requires systematic audit of all 30+ instances of `entry.key` in user output (must show `entry.name` instead), comprehensive grep for `--device`/`--add-device`/`--list-devices` in error messages (replace with TUI instructions like "Press F to flash"), and collision check in slug generation (append `-2`, `-3` until unique). The architectural patterns needed already exist—this is surgical deletion plus one validation function, not invention.

## Key Findings

### Recommended Stack

No new stack elements required. All capabilities exist in Python 3.9+ stdlib, already imported in the codebase.

**Core technologies:**
- `re.sub()` — Slug generation from display name - single regex `[^a-z0-9]+` replaces all non-alphanumeric with hyphens, already imported
- `str.lower()` + `str.strip('-')` — Case normalization and edge cleanup for filesystem-safe keys
- `sys.argv` — Minimal `--help` detection without argparse - two string comparisons replace entire parser
- `shutil.move()` — Config cache migration IF key rename feature included (optional for v4.0) - already imported in config.py

**What to remove:**
- `argparse` module import and `build_parser()` function (~60 lines)
- All CLI flag routing in `main()` (--device, --add-device, --list-devices, --remove-device, --exclude-device, --include-device)
- Device key prompt from add-device wizard (step 4, lines 1814-1827 in flash.py)
- Device key editing from device config screen (DEVICE_SETTINGS index 2 in screen.py)

**Integration points (existing files only):**
- `flash.py` — Simplify `main()` to TUI-only launcher, remove argparse dispatch
- `validation.py` — Add `generate_device_key(name, registry)` with collision handling
- `tui.py` — Remove key editing from `_device_config_screen()`, adjust setting indices
- `screen.py` — Remove key from `DEVICE_SETTINGS` list
- `errors.py` — Update ERROR_TEMPLATES to replace CLI flag references with TUI instructions

**Key architectural decision:** Existing device keys are immutable. The JSON dict key from devices.json becomes the permanent internal identifier. Only NEW devices registered after v4.0 get auto-generated slugs. No registry migration code required—this preserves backward compatibility and avoids config cache rename complexity.

### Expected Features

Research identified clear must-haves (transition requirements) vs should-haves (polish) vs anti-features (scope creep to avoid).

**Must have (transition blockers):**
- `kflash` launches TUI directly - with CLI removed, non-TTY should print brief usage message and exit
- Auto-generate key from display name during add-device - slugify function: lowercase, regex replace non-alphanumeric, strip edges
- Uniqueness handling for generated keys - check registry, append `-2`, `-3` if collision
- Preserve existing devices.json keys - existing keys stay as-is, no migration or regeneration
- Preserve existing config cache directories - no directory renames, paths continue working
- Remove key prompt from add-device wizard - user only provides display name, system generates key silently
- Remove key editing from device config screen - keys are internal, not user-editable
- Update all CLI flag references in error messages - replace `--device KEY` with TUI action instructions ("Press F")
- Show display name everywhere keys were shown - audit all `entry.key` in output, replace with `entry.name`

**Should have (polish):**
- Show key in device config as read-only - power users debugging config cache paths benefit from visibility
- Minimal `--help` flag handling - graceful message even without argparse, not Python traceback
- Show generated key in add-device success - transparency: "Registered 'Octopus Pro v1.1' (key: octopus-pro-v1-1)"

**Anti-features (explicitly excluded):**
- Let users edit auto-generated keys - re-introduces user-facing identifier complexity, requires config cache rename logic
- Keep any CLI flags "just in case" - creates confusion about CLI vs TUI operations, maintains two code paths
- Auto-rename existing keys to match names - breaks existing config cache paths, unnecessary migration complexity
- Generate keys from MCU type or serial - MCU types repeat across devices, serial patterns are long/ugly
- Add CLI entry point later - scope creep, defeats simplification purpose
- Prompt for confirmation of auto-generated key - key is internal, user doesn't need to approve it

**Deferred to post-v4.0:**
- Smarter slug generation (strip version suffixes like "v1.1") - low impact refinement
- Key rename with migration - complex feature requiring atomic registry + directory operations, can be separate milestone

### Architecture Approach

The transition preserves the hub-and-spoke architecture. `flash.py` becomes a thinner launcher, `tui.py` remains the menu loop orchestrator. No new modules, no cross-module imports. This is surgical deletion of argparse plus one utility function, not a refactor.

**Entry flow transformation:**

BEFORE (hybrid CLI/TUI):
```
kflash.py -> flash.main() -> argparse
  if --add-device    -> cmd_add_device()
  if --device KEY    -> cmd_flash()
  if --list-devices  -> cmd_list_devices()
  if --remove-device -> cmd_remove_device()
  if no args + TTY   -> tui.run_menu()
  if no args + !TTY  -> print help
```

AFTER (TUI-only):
```
kflash.py -> flash.main()
  if not TTY -> exit("kalico-flash requires an interactive terminal.")
  -> load registry
  -> tui.run_menu()
  (all operations route through TUI action handlers)
```

**Component modifications (5 files):**
1. **flash.py** — Delete `build_parser()`, simplify `main()` to 15 lines (TTY check, load registry, launch TUI), update `cmd_add_device()` to call `generate_device_key()` instead of prompting
2. **validation.py** — Add `generate_device_key(name, registry)` function with slugification + collision handling (~25 lines)
3. **tui.py** — Remove key edit handler from `_device_config_screen()`, adjust setting indices from 1-5 to 1-4
4. **screen.py** — Remove key entry from `DEVICE_SETTINGS` list (4 items instead of 5)
5. **errors.py** + all output strings — Replace all `--device`/`--add-device` references with TUI instructions ("Press F to flash", "Press A to add")

**Data flow changes:**

Key generation (new):
```
User enters display name "Octopus Pro v1.1"
  -> generate_device_key("Octopus Pro v1.1", registry)
  -> slug = "octopus-pro-v1-1"
  -> check registry.devices: not present
  -> return "octopus-pro-v1-1"
  -> DeviceEntry(key="octopus-pro-v1-1", name="Octopus Pro v1.1", ...)
  -> config cache at ~/.config/kalico-flash/configs/octopus-pro-v1-1/
```

Key collision (new):
```
User enters "Nitehawk 36" (second device with this name)
  -> slug = "nitehawk-36"
  -> check registry: "nitehawk-36" exists
  -> try "nitehawk-36-2", check registry: available
  -> return "nitehawk-36-2"
```

Existing device flow (unchanged):
```
Registry load reads devices.json
  -> "octopus-pro": { "name": "Octopus Pro v1.1", ... }
  -> DeviceEntry(key="octopus-pro", name="Octopus Pro v1.1", ...)
  -> User-typed key from v3.x preserved forever
  -> Config cache at ~/.config/kalico-flash/configs/octopus-pro/ (unchanged)
```

**Migration strategy:** No migration needed. The `DeviceEntry.key` field persists in JSON. Existing keys continue working. The change only affects new devices added post-v4.0. If a user edits an existing device name in the config screen, the key does NOT regenerate (keys are immutable after creation). Key regeneration only happens during the add-device flow.

### Critical Pitfalls

From PITFALLS.md v5.0 research, the top 5 risks:

1. **Existing devices.json Keys Don't Match Slug Algorithm (CLI-1)** — Existing user-typed keys like `octopus-pro` won't match `slugify("Octopus Pro v1.1")` producing `octopus-pro-v1-1`. If code regenerates keys on load, all devices lose cached configs. **Prevention:** Keep existing keys immutable. Only slugify for NEW devices. On `registry.py` load, use JSON dict key directly as `entry.key` (already the case). Never call `slugify()` on existing device names. Test: grep for `slugify` calls—they should only appear in add-device flow.

2. **Slug Collision Silently Overwrites Device (CLI-2)** — Two devices with similar names ("Octopus Pro" and "Octopus-Pro") both become `octopus-pro`. Second device overwrites first in devices.json and clobbers config cache. **Prevention:** Check slug uniqueness against existing registry keys before insert. On collision, append numeric suffix (`octopus-pro-2`). Never silently overwrite. Test: add two devices with names that slugify identically, verify second gets `-2` suffix.

3. **Argparse Removal Breaks External Callers (CLI-3)** — User shell aliases, cron jobs, or Moonraker configs invoke `kflash --device octopus-pro`. Removing argparse causes tracebacks. **Prevention:** Keep minimal `sys.argv` check—if any args passed, print clear migration message ("CLI flags removed. Run kflash with no arguments.") and exit cleanly. Test: run `kflash --help`, `kflash --device foo`, verify graceful message not traceback.

4. **30+ Instances of entry.key in User-Facing Output (CLI-4)** — `flash.py` displays `entry.key` in device_line calls, info messages, batch results. After internalization, users see ugly slugs (`octopus-pro-v1-1`) instead of display names. **Prevention:** Audit every `entry.key` in output formatting. Replace user-facing displays with `entry.name`. Keep `entry.key` for: dict lookups, config cache paths, debug logs only. Test: grep `entry\.key` in any f-string or output call, classify each as internal vs display.

5. **Slug Generation Edge Cases (CLI-5)** — Empty result after stripping (all-emoji name), filesystem-unsafe characters, path traversal (`../../../etc/passwd`), very long names. **Prevention:** Implementation: `re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')` with consecutive hyphen collapse. Reject empty result (require at least one alphanumeric). Limit slug length (64 chars). Block path-traversal before slugification. Test: empty string, all-special-chars, `"../../../etc"`, unicode, 200-char names.

**Additional critical pitfall:**
- **skip_menuconfig Flag Lost Without CLI (CLI-6)** — The `-s`/`--skip-menuconfig` CLI flag currently controls runtime behavior. After argparse removal, this capability must exist in GlobalConfig. **Prevention:** `skip_menuconfig` already exists in GlobalConfig (models.py). Verify TUI flow respects `global_config.skip_menuconfig`. No action needed if already wired—just verify during testing.

## Implications for Roadmap

Based on research, suggested phase structure for v4.0:

### Phase 1: Add Slug Generation (Additive, Safe)
**Rationale:** Build the slug generation function first as a standalone utility. Pure function with no side effects, testable in isolation. Adds capability without changing existing behavior—no risk of breaking working code.

**Delivers:**
- `generate_device_key(name, registry)` in validation.py with slugification logic
- Collision handling: check existing registry keys, append numeric suffix until unique
- Edge case handling: empty slugs, long names, path-traversal characters, unicode

**Addresses:**
- Pitfall CLI-2 (collision check prevents overwrites)
- Pitfall CLI-5 (edge case handling prevents filesystem errors)

**Avoids:** Building removal phases before the replacement function exists

**Research flag:** No additional research needed—slugification is 4 lines of stdlib re.sub(), collision handling is dict lookup loop. All patterns documented in STACK.md.

---

### Phase 2: Internalize Key in Add-Device Flow
**Rationale:** Replace key prompt with auto-generation. Isolated to one workflow (add-device wizard). Existing devices unaffected. Can be tested independently before touching CLI or config screen.

**Delivers:**
- Remove step 4 (key prompt loop) from `cmd_add_device()` in flash.py
- Call `generate_device_key(display_name, registry)` instead
- Show generated key in success message for transparency

**Uses:**
- Foundation from Phase 1: `generate_device_key()` function
- Existing validation infrastructure

**Implements:** Key internalization without breaking existing devices

**Addresses:**
- Table stakes: auto-generate keys from names
- Pitfall CLI-1 (existing keys untouched, only new devices get slugs)

**Research flag:** No additional research needed—add-device wizard structure already analyzed in ARCHITECTURE.md.

---

### Phase 3: Remove Key from Device Config Screen
**Rationale:** Keys are now internal identifiers. Remove user editing capability. Self-contained change to TUI module. No dependencies on Phase 4 (CLI removal).

**Delivers:**
- Remove key entry from `DEVICE_SETTINGS` in screen.py
- Remove key edit handler from `_device_config_screen()` in tui.py
- Optionally add key as read-only to identity panel (show but don't edit)
- Adjust keypress range from 1-5 to 1-4

**Addresses:**
- Table stakes: keys are internal, not user-editable
- Pitfall CLI-4 (key shown for debugging, not edited)

**Avoids:** Exposing auto-generated slugs as user-editable fields

**Research flag:** No additional research needed—device config screen patterns verified in FEATURES.md.

---

### Phase 4: Remove CLI/Argparse
**Rationale:** The breaking change. By this point, all functionality is TUI-native (Phases 1-3). This phase removes the redundant CLI entry path. Single atomic change—all argparse removal in one commit.

**Delivers:**
- Delete `build_parser()` function from flash.py
- Simplify `main()` to TUI-only launcher (TTY check, load registry, run_menu)
- Remove `--device`, `--add-device`, `--list-devices`, `--remove-device`, `--exclude-device`, `--include-device` handling
- Minimal `sys.argv` check for graceful error on any arguments passed

**Addresses:**
- Table stakes: kflash launches TUI directly
- Pitfall CLI-3 (graceful migration message for external callers)

**Avoids:** Half-removing CLI (creates confusion which operations work from CLI vs TUI)

**Research flag:** No additional research needed—argparse removal is deletion, TUI launch pattern verified in ARCHITECTURE.md main() flow.

---

### Phase 5: Update User-Facing Strings
**Rationale:** Systematic audit and replacement of all CLI references in output. Must happen AFTER Phase 4 (CLI removal) to ensure no missed references. This is cleanup, not functional change.

**Delivers:**
- Replace all `--device KEY` references with TUI instructions ("Press F to flash")
- Replace all `entry.key` in user-facing output with `entry.name`
- Update flash.py module docstring (remove CLI command examples)
- Update CLAUDE.md "CLI Commands" section to "TUI Menu"
- Update error recovery templates in errors.py

**Addresses:**
- Pitfall CLI-4 (30+ instances of entry.key in output)
- Pitfall CLI-7 (documentation references removed flags)

**Avoids:** Leaving stale `--device` instructions that confuse users

**Research flag:** No additional research needed—systematic grep for `--device`, `--add-device`, `entry\.key`, replace with approved alternatives.

---

### Phase Ordering Rationale

- **Additive before destructive:** Phase 1-2 add slug generation and integrate it into add-device. Phase 3 removes key editing. Phase 4 removes CLI. Each builds on previous without breaking existing functionality.
- **Isolated testing:** Phase 1 is pure function (unit testable). Phase 2 is one workflow (add-device testable). Phase 3 is one screen (config screen testable). Phase 4 is entry point (integration testable). Phase 5 is string replacement (grep verification).
- **Fail-fast progression:** If slug generation (Phase 1) has issues, stop before changing any user-facing behavior. If add-device integration (Phase 2) fails, existing devices still work. If CLI removal (Phase 4) breaks something, Phases 1-3 are unrelated.
- **Atomic breaking change:** CLI removal (Phase 4) happens all at once after foundation is proven. No partial CLI—clean before/after split.

**Dependency graph:**
```
Phase 1 (Slug Generation) ──> Phase 2 (Add-Device) ──┐
                                                       ├──> Phase 4 (CLI Removal) ──> Phase 5 (String Cleanup)
Phase 3 (Config Screen) ───────────────────────────────┘
```

Phase 2 depends on Phase 1 (needs slug function). Phases 2+3 can be parallelized (independent). Phase 4 waits for 2+3 (all TUI paths must be key-internalized before CLI removal). Phase 5 waits for Phase 4 (can't update CLI references until CLI is removed).

### Research Flags

**All phases have standard patterns (skip research-phase):**
- **Phase 1:** Slugification pattern verified—4 lines of `re.sub()`, collision is dict lookup loop. Edge cases documented in PITFALLS.md CLI-5.
- **Phase 2:** Add-device wizard structure analyzed in ARCHITECTURE.md (step 4 removal, lines 1813-1827). Slug generation callable from Phase 1.
- **Phase 3:** Device config screen pattern verified in FEATURES.md v3.3 research (DEVICE_SETTINGS list, _device_config_screen handler).
- **Phase 4:** Argparse removal is deletion. TUI-only entry point pattern in ARCHITECTURE.md (simplified main() example lines 32-49).
- **Phase 5:** String replacement is systematic grep. No patterns to research—just find-replace with approved text.

**No phase requires additional research.** All patterns exist in codebase, all pitfalls documented, all stack elements verified (re.sub, sys.argv, dict operations all stdlib). This is surgical deletion plus one utility function.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All operations use Python 3.9+ stdlib. re.sub for slugs, sys.argv for arg check, dict operations for collision. Zero new dependencies. |
| Features | HIGH | Feature requirements derived from codebase analysis of 30+ entry.key usages, argparse dispatch structure, add-device wizard flow. Must-haves are removal tasks with clear verification. |
| Architecture | HIGH | Direct codebase analysis of flash.py (argparse lines 92-157), validation.py (existing validation patterns), tui.py (config screen), screen.py (DEVICE_SETTINGS). Hub-and-spoke maintained. |
| Pitfalls | HIGH | Seven specific pitfalls researched via codebase analysis of key usage patterns (registry.py dict keys, config.py paths, models.py DeviceEntry.key field). Prevention strategies documented with test cases. |

**Overall confidence:** HIGH

### Gaps to Address

Minor validation points to resolve during implementation:

- **Slug suffix start value:** Start numeric suffix at 2 (first device gets clean slug, second gets `-2`) or 1 (second gets `-1`)? **Resolution:** Start at 2 per STACK.md recommendation—matches common conventions (file copies, URLs). First device gets `octopus-pro`, second gets `octopus-pro-2`.

- **Empty slug handling:** If user enters all-emoji name or all-special-chars name, slug becomes empty string after strip. **Resolution:** Reject during add-device validation: "Display name must contain at least one letter or number." Or default to `device` as slug base if empty (then `device-2`, `device-3`). Prefer rejection—forces user to provide meaningful name.

- **Long slug truncation:** If display name is 200 chars, slug could exceed filesystem limits. **Resolution:** Limit slug to 64 chars after slugification. Truncate before adding numeric suffix if needed. Config cache directory names must be portable.

- **Unicode handling:** Device names may contain unicode (e.g., `"Voron™ Octopus"`). **Resolution:** `str.lower()` handles unicode correctly in Python 3. The `re.sub(r'[^a-z0-9]+', '-', ...)` pattern strips non-ASCII, so `"Voron™ Octopus"` becomes `voron-octopus`. No special unicode normalization needed per STACK.md (NFKD unnecessary for ASCII board names).

- **Existing key format validation:** Existing devices.json may have keys that don't match slug format (e.g., `octopus_pro_v1` with underscores instead of hyphens). **Resolution:** Accept all existing keys as-is. The slug format only applies to NEW devices added post-v4.0. Validate existing keys are filesystem-safe (no `/`, `..`, null bytes) but don't enforce slug format retroactively.

- **Skip menuconfig after CLI removal:** Verify TUI respects `global_config.skip_menuconfig` for flash operations. **Resolution:** Check flash workflow in flash.py—if already wired to GlobalConfig, no change needed. Just verify during Phase 4 testing.

## Sources

### Primary (HIGH confidence)
- **Codebase analysis** — Direct inspection of all affected modules:
  - `kflash/flash.py` — Argparse parser lines 92-157, main dispatch lines 1986-2041, add-device wizard key prompt lines 1813-1827
  - `kflash/validation.py` — Existing validate_device_key regex spec `^[a-z0-9][a-z0-9_-]*$` at lines 55-80
  - `kflash/tui.py` — Device config screen lines 730-890, config screen pattern in _config_screen
  - `kflash/screen.py` — DEVICE_SETTINGS definition lines 479-490 with key edit item
  - `kflash/config.py` — get_config_dir using device_key lines 16-27, rename_device_config_cache lines 30-48
  - `kflash/registry.py` — Devices dict key usage lines 43-51, DeviceEntry.key field reading
  - `kflash/models.py` — DeviceEntry.key field definition, GlobalConfig.skip_menuconfig field
  - `kflash/errors.py` — ERROR_TEMPLATES with CLI flag references in recovery text
- **Python stdlib documentation** — re.sub() regex replacement, sys.argv argument checking, str methods for case/strip

### Secondary (MEDIUM confidence)
- **Slug generation conventions** — Common URL/filename slugification patterns (lowercase, hyphen-separated, numeric suffixes for duplicates). Not Python-specific but industry standard.

### Tertiary (LOW confidence)
- None—all research based on direct codebase analysis and stdlib documentation.

---
*Research completed: 2026-01-31*
*Ready for roadmap: yes*
