# Pitfalls Research: klipper-flash

**Domain:** Python CLI tool for Klipper firmware building and flashing via subprocesses
**Researched:** 2026-01-25 (v1.0), 2026-01-26 (v2.0 additions), 2026-01-29 (v2.1 panel TUI + batch flash), 2026-01-30 (v3.2 visual dividers), 2026-01-31 (v4.0 config device editing, v5.0 CLI removal + key internalization)
**Overall confidence:** HIGH (domain knowledge from Klipper ecosystem, codebase analysis of key usage patterns, Python file operation semantics)

---

## v5.0 CLI Removal and Key Internalization Pitfalls

### CLI-1: Existing devices.json Keys Don't Match Slug Algorithm (Critical)

**What goes wrong:** Existing `devices.json` has user-typed keys like `octopus-pro`. New code generates slugs from `entry.name` ("Octopus Pro v1.1") producing `octopus-pro-v1-1`. The config cache at `~/.config/kalico-flash/configs/octopus-pro/` no longer resolves.

**Why it happens:** Slug algorithm and user's original key choice are independent. There is no guarantee `slugify("Octopus Pro v1.1") == "octopus-pro"`.

**Consequences:** All existing devices lose cached configs. User must re-run menuconfig for every board (10+ minutes each of manual TUI interaction on a Pi with multiple boards).

**Prevention:**
- Keep existing keys as-is forever. Only slugify names for NEW devices added after the migration
- On `registry.py` load, use the JSON dict key directly as `entry.key` (already the case at line 44-46 -- do not change this)
- Never call `slugify()` on existing device names during load or save
- The key is born once at registration and lives forever

**Detection:** If any code path calls `slugify(entry.name)` for an entry that already has a key, this pitfall is active. Grep for `slugify` calls -- they should only appear in the add-device flow.

**Phase:** Data model design. Must be the first decision made.

---

### CLI-2: Slug Collision Silently Overwrites Device (Critical)

**What goes wrong:** Two devices with similar names produce the same slug. "Octopus Pro" and "Octopus-Pro" both become `octopus-pro`. Second device overwrites the first in `devices.json` and clobbers its config cache directory.

**Why it happens:** Slugification collapses spaces, hyphens, underscores, and case into the same output. With board revisions ("v1.0" vs "v1.1"), collisions are more common than expected.

**Consequences:** Silent data loss of one device's registration and menuconfig cache.

**Prevention:**
- Check slug uniqueness against existing registry keys before inserting
- On collision: append numeric suffix (`octopus-pro-2`) or reject with clear error
- Never silently overwrite an existing key in the devices dict

**Detection:** Unit-testable: `assert slugify(name) not in registry.devices` before any insert.

**Phase:** Add-device flow implementation.

---

### CLI-3: Argparse Removal Breaks External Callers (Moderate)

**What goes wrong:** `install.sh` creates the `kflash` symlink. Moonraker update manager or user shell aliases may invoke `kflash` with flags. Removing argparse causes Python tracebacks for any caller passing arguments.

**Why it happens:** CLI flags are an external contract. Even though the tool is moving to TUI-only, external references to `kflash --device octopus-pro` may exist in user scripts, cron jobs, or Moonraker configs.

**Warning signs:**
- `install.sh` has any argument handling
- Moonraker `[update_manager]` config references kflash with arguments
- User has shell aliases like `alias flash-octo='kflash --device octopus-pro'`

**Prevention:**
- Keep a minimal `sys.argv` check: if any args are passed, print a clear migration message ("CLI flags removed. Run kflash with no arguments to launch the interactive menu.") and exit cleanly
- Do NOT just let Python traceback on unknown arguments
- Check `install.sh` and `moonraker.py` for any flag usage before removing

**Detection:** After removal, run `kflash --help`, `kflash --device foo`, `kflash -s` -- all should show the migration message, not a traceback.

**Phase:** CLI removal phase. Must be in the same commit as argparse removal.

---

### CLI-4: 30+ Instances of entry.key in User-Facing Output (Moderate)

**What goes wrong:** `flash.py` displays `entry.key` in output lines like `"octopus-pro (stm32h723)"` over 30 times. After internalization, displaying auto-generated slugs to users is confusing and ugly (`octopus-pro-v1-1` instead of "Octopus Pro v1.1").

**Why it happens:** The key was designed as user-facing. It permeates all output formatting. Grep for `entry.key` in flash.py shows it in device_line calls, info messages, warning messages, and batch result tracking.

**Consequences:** Users see slugified names everywhere instead of their chosen display names. Tool feels broken/ugly.

**Prevention:**
- Audit every `entry.key` usage in output/display code (all 30+ instances in flash.py)
- Replace user-facing displays with `entry.name`
- Keep `entry.key` for: dict lookups, config cache paths, log debugging only
- `BatchDeviceResult.device_key` stays internal; `device_name` becomes the display field

**Detection:** Grep `entry\.key` in any string formatting, f-string, or output method call. Every instance needs classification as "internal" or "display".

**Phase:** Output refactor, after data model is settled. Can be a separate commit.

---

### CLI-5: Slug Generation Edge Cases (Moderate)

**What goes wrong:** Hand-rolled slugify on Python 3.9 stdlib misses edge cases: leading/trailing hyphens, consecutive hyphens, empty result after stripping, unicode characters, very long names, or filesystem-unsafe characters.

**Why it happens:** Python 3.9 stdlib has no `slugify()`. Django's `slugify` handles these but is not available. Naive `re.sub(r'[^a-z0-9-]', '-', name.lower())` produces ugly results and edge case failures.

**Consequences:** Empty slugs (all-emoji name), filesystem errors (key with `/`), path traversal (`../../../etc/passwd` as device name), or unexpectedly long paths.

**Prevention:**
- Implementation: `re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')` with consecutive hyphen collapse
- Reject empty result: require at least one alphanumeric char in name
- Limit slug length (64 chars)
- Block path-traversal characters before slugification
- Test with: empty string, all-special-chars, `"../../../etc"`, unicode, 200-char names, names that are only numbers

**Phase:** Slug utility function. Implement and test before any integration.

---

### CLI-6: skip_menuconfig Flag Lost Without CLI (Minor)

**What goes wrong:** The `-s` / `--skip-menuconfig` CLI flag is currently the only way to skip menuconfig. After argparse removal, this capability is lost unless moved to GlobalConfig or TUI.

**Why it happens:** Developer focuses on removing argparse and forgets that some flags control runtime behavior that users depend on.

**Warning signs:** User used `kflash -s --device octopus-pro` in their workflow. After migration, no way to skip menuconfig.

**Prevention:**
- `skip_menuconfig` already exists in `GlobalConfig` (models.py line 17) and is stored in `devices.json` global section
- Verify the TUI flow respects `global_config.skip_menuconfig`
- Consider adding a per-device `skip_menuconfig` toggle in the TUI settings panel

**Phase:** CLI removal phase. Verify all flag behaviors have TUI or config equivalents before removing argparse.

---

### CLI-7: Documentation References Removed CLI Flags (Minor)

**What goes wrong:** README, CLAUDE.md (lines 8-13 of flash.py docstring, CLAUDE.md "CLI Commands" section), and install.sh all reference `--device KEY`, `--add-device`, `--list-devices` etc. Users following docs get confusing errors.

**Prevention:**
- Update flash.py module docstring, README, CLAUDE.md, and install.sh in the same commit as CLI removal
- Search for `--device`, `--add-device`, `--list-devices`, `--remove-device`, `--exclude-device`, `--include-device`, `-s` across all files

**Phase:** Same commit/PR as CLI removal.

---

## CLI Removal Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|---|---|---|
| Data model design | Re-deriving keys from names breaks existing devices (CLI-1) | Keys are immutable after creation, slugify only at add time |
| Slug implementation | Collisions, empty slugs, path traversal (CLI-2, CLI-5) | Collision check + strict filtering + length limit |
| Argparse removal | External callers get tracebacks (CLI-3) | Graceful migration message for any sys.argv |
| Output refactor | 30+ key displays become ugly slugs (CLI-4) | Replace entry.key with entry.name in all user-facing output |
| Flag migration | skip_menuconfig behavior lost (CLI-6) | Verify GlobalConfig.skip_menuconfig is respected by TUI |
| Documentation | Stale CLI docs everywhere (CLI-7) | Update all docs in same commit |

## "Looks Done But Isn't" Checklist (v5.0)

- [ ] **Existing keys preserved:** `registry.load()` still reads dict key directly, no slugification on load
- [ ] **Slug collision checked:** New device add rejects duplicate slugs
- [ ] **Graceful arg rejection:** `kflash --anything` prints migration message, not traceback
- [ ] **All entry.key displays audited:** User sees `entry.name`, not `entry.key`, in all output
- [ ] **Slug edge cases tested:** Empty, unicode, path traversal, long names, all-special-chars
- [ ] **Flag behaviors preserved:** skip_menuconfig works via GlobalConfig without CLI flag
- [ ] **Docs updated:** flash.py docstring, CLAUDE.md, README all reflect TUI-only interface
- [ ] **install.sh reviewed:** No flag handling that breaks after argparse removal

## Sources (v5.0)

### Codebase Analysis (HIGH confidence)
- `kflash/registry.py` lines 43-46: Keys read from JSON dict keys, not derived from names
- `kflash/models.py` line 27: `DeviceEntry.key` docstring says "user-chosen, used as --device flag"
- `kflash/config.py` lines 16, 27: `get_config_dir(device_key)` uses key directly as filesystem path component
- `kflash/flash.py`: 30+ instances of `entry.key` in user-facing output (grep confirmed)
- `kflash/models.py` line 17: `GlobalConfig.skip_menuconfig` already exists as persistent config
- `kflash/flash.py` lines 1-26: Module docstring documents CLI flags that will be removed

---

## v4.0 Config Device Pitfalls

### CFG-1: Orphaned Config Cache After Key Rename

**What goes wrong:** User renames device key from `octopus-pro` to `octo-v11`. Registry updates to new key, but the cached `.config` remains at `~/.config/kalico-flash/configs/octopus-pro/.config`. Next flash of `octo-v11` sees no cached config and forces a fresh menuconfig. The old directory sits on disk forever consuming space and causing confusion.

**Why it happens:** Registry save (`registry.py:save()`) and config cache directory (`config.py:get_config_dir()`) are completely decoupled. There is no `rename_device()` method -- only `add()` and `remove()`. A naive implementation does `remove(old_key) + add(new_entry)` without touching the filesystem cache.

**Warning signs:**
- `registry.remove()` does not touch config cache (confirmed: lines 113-120 have no filesystem ops)
- `_remove_cached_config()` in flash.py is a separate function called only during explicit device removal
- No existing code links registry mutations to config directory operations

**Prevention:**
- Key rename must be an atomic operation: update registry JSON AND rename config directory in one logical transaction
- Order matters: rename directory FIRST, then update registry. If directory rename fails, registry stays consistent. If registry update fails after directory rename, the old key's config is "lost" but recoverable (directory exists, just under new name)
- Use `shutil.move()` (not `os.rename()`) for the config directory -- handles cross-filesystem moves if XDG_CONFIG_HOME is on different mount
- If old config directory does not exist, skip the move silently (device may never have been configured)
- Test: rename key, verify `get_config_dir(new_key)/.config` exists and old directory is gone

**Phase:** Must be addressed in the key-rename implementation phase. Cannot be deferred.

---

### CFG-2: Key Rename Collision with Existing Device

**What goes wrong:** User renames `octopus` to `nitehawk` but `nitehawk` already exists in the registry. Naive implementation overwrites the existing device entry, destroying its registration and potentially its config cache.

**Why it happens:** `registry.add()` already checks for key collision (line 108-109: raises RegistryError if key exists). But a rename implemented as `remove(old) + add(new)` might skip this check if the add is done differently, or a direct dict mutation bypasses the guard entirely.

**Warning signs:**
- Implementation that modifies `registry.devices` dict directly instead of using `add()`
- No validation of new key before starting the rename operation
- Config directory collision: new key's config directory already exists from another device

**Prevention:**
- Validate new key does not exist in registry BEFORE any mutations
- Also check if `get_config_dir(new_key)` directory already exists on disk (could be leftover from a previously deleted device)
- If config directory collision: ask user whether to overwrite or abort
- Perform all validation before any state changes (fail fast, mutate late)

**Phase:** Key rename validation phase. Must be the first check in the rename flow.

---

### CFG-3: Key Rename Breaks In-Flight References

**What goes wrong:** User has `--device octopus-pro` in shell aliases, cron jobs, or Moonraker macros. After renaming the key, those references silently fail with "device not found" errors. User doesn't realize until their next automated flash attempt fails.

**Why it happens:** The device key is an external contract -- it's used as a CLI argument (`--device octopus-pro`). Renaming it breaks all external references. Unlike internal refactoring, CLI argument values are used by humans in scripts and muscle memory.

**Warning signs:**
- No warning shown to user about external references when renaming
- No "alias" or "previous key" tracking

**Prevention:**
- Display a clear warning before confirming rename: "Warning: If you use 'octopus-pro' in scripts, aliases, or automation, those references will break."
- Consider keeping old key as an alias (LOW priority, adds complexity)
- At minimum, show the old and new key clearly in confirmation: "Rename 'octopus-pro' to 'octo-v11'? [y/N]"
- Log the rename so user can find what changed: the registry diff is visible in devices.json git history

**Phase:** UX/confirmation phase. Add warning text to the rename confirmation prompt.

---

### CFG-4: Partial Registry Update on Crash

**What goes wrong:** Power loss or Ctrl+C between removing old key and adding new key in a rename-as-delete-then-add implementation. Device disappears from registry entirely. Config cache may or may not have been moved.

**Why it happens:** `registry.remove()` calls `save()` which does an atomic JSON write. Then `registry.add()` calls `save()` again. Between these two atomic writes, the device does not exist. If the process dies in that window, the device is gone.

**Warning signs:**
- Rename implemented as two separate `save()` calls
- Any code path where the device is absent from registry between operations
- `registry.load()` -> mutate -> `registry.save()` pattern done twice instead of once

**Prevention:**
- Implement rename as a SINGLE load-mutate-save cycle: load registry, delete old key from dict, insert new key in dict, save once
- The existing atomic write pattern (`_atomic_write_json`) ensures the JSON file is either fully old or fully new -- never partial
- Example: `data = registry.load(); del data.devices[old_key]; data.devices[new_key] = entry; registry.save(data)`
- For the config directory move: do it BEFORE the registry save. Worst case: directory moved but registry still has old key (recoverable by moving directory back)

**Phase:** Core implementation. The single-save pattern must be the design from the start.

---

### CFG-5: Key Validation Inconsistency

**What goes wrong:** The add-device wizard validates keys one way (e.g., lowercase alphanumeric + hyphens), but the edit/rename flow either skips validation or applies different rules. User creates a key with spaces or special characters that breaks `get_config_dir()` (directory name) or `--device` argument parsing.

**Why it happens:** Key validation logic lives inline in the add-device wizard rather than in a shared function. When building the edit flow, developer writes new validation or forgets it entirely.

**Warning signs:**
- Key validation logic duplicated or absent in edit flow
- No shared `validate_device_key()` function exists currently
- Keys with `/`, `..`, spaces, or shell metacharacters could create path traversal or argument parsing issues

**Prevention:**
- Extract key validation into a shared function (e.g., `validation.py:validate_device_key()`)
- Rules: lowercase, alphanumeric + hyphens only, no leading/trailing hyphens, 1-40 chars, no reserved names
- Call the same validation for both add and rename flows
- Specifically block path-unsafe characters: `/`, `\`, `..`, null bytes
- Test edge cases: empty string, single char, 100+ chars, unicode, shell metacharacters

**Phase:** Should be extracted before building the edit flow. Prerequisite task.

---

### CFG-6: Edit Flow Does Not Update DeviceEntry.key Field

**What goes wrong:** Developer renames the registry dict key (`devices["new-key"] = devices.pop("old-key")`) but forgets to update `entry.key` on the DeviceEntry dataclass itself. The entry's `.key` field still says `"old-key"` even though it's stored under `"new-key"` in the dict. Display code that uses `entry.key` shows the old name.

**Why it happens:** The `DeviceEntry.key` field (models.py line 27) is set during `load()` from the dict key (registry.py line 46: `key=key`). But during an in-memory mutation, the dict key and the dataclass field are separate values that must be updated independently.

**Warning signs:**
- `entry.key` used in output messages shows old key after rename
- `list-devices` shows correct key in one column but old key in another
- Config cache operations use `entry.key` and target the wrong directory

**Prevention:**
- When renaming, always create a NEW DeviceEntry with the new key: `new_entry = DeviceEntry(key=new_key, name=entry.name, ...)`
- Never mutate `entry.key` on an existing instance (dataclasses are nominally immutable by convention)
- The save path (registry.py line 90) iterates `sorted(registry.devices.items())` using dict keys, but the `key` field on DeviceEntry is written to... wait, it's NOT written to JSON (line 93-97 doesn't include `key`). The key is only the dict key. This means the `.key` field is only used at runtime for display/logic. Still must be correct.

**Phase:** Core implementation. Use new DeviceEntry construction, not mutation.

---

### CFG-7: Flash Method Edit Accepts Invalid Values

**What goes wrong:** User edits flash_method to "katapault" (typo) or "usb" (not a valid method). The value is stored in the registry. Next flash attempt fails with a confusing error deep in the flash logic rather than at edit time.

**Why it happens:** `flash_method` is typed as `Optional[str]` with no enum or validation. Valid values are `"katapult"`, `"make_flash"`, or `None` (use global default). Without validation at edit time, any string is accepted.

**Warning signs:**
- flash_method stored as free-form string in DeviceEntry
- No validation in registry.save() or registry.add()
- Error surfaces at flash time, not at config time

**Prevention:**
- Define valid flash methods as a constant: `VALID_FLASH_METHODS = {"katapult", "make_flash"}`
- Validate at edit time, not flash time
- In the TUI, present flash method as a selection (pick from list) not free text input
- Allow `None` / empty to mean "use global default" -- make this an explicit option in the picker

**Phase:** Edit flow implementation. Use selection UI, not text input for constrained fields.

---

### CFG-8: Editing serial_pattern Breaks Device Matching

**What goes wrong:** User edits serial_pattern to fix a typo but introduces a glob that matches zero devices or matches the wrong device. Next flash attempt either fails discovery ("no matching device") or matches an unintended board.

**Why it happens:** Serial patterns use glob matching against `/dev/serial/by-id/` filenames. A subtle change (e.g., removing a `*` wildcard, changing `stm32h723xx` to `stm32h723`) can break matching. Users don't understand glob syntax.

**Warning signs:**
- Pattern edited via free text input with no live validation
- No "test this pattern against currently connected devices" feature
- User edits pattern, doesn't test until next flash (could be days later)

**Prevention:**
- After pattern edit, immediately scan `/dev/serial/by-id/` and show matches: "This pattern matches: [list] or No devices match this pattern"
- If zero matches: warn but allow save (device may be disconnected)
- If multiple matches: warn about ambiguity
- Consider offering to re-run discovery instead of manual pattern editing

**Phase:** Edit flow implementation. Add live pattern validation after edit.

---

### CFG-9: TUI Edit Panel State Management

**What goes wrong:** User starts editing a device, changes several fields, then cancels. But some changes were already saved incrementally (e.g., name was saved before the user got to key rename and cancelled). Device is now in a partially-edited state.

**Why it happens:** If each field edit triggers an immediate registry save (like `set_flashable()` does on line 143-149), then cancellation cannot roll back prior field saves. The tool has no transaction/rollback mechanism.

**Warning signs:**
- Individual field edits call `registry.save()` immediately
- No "save all changes at once" pattern
- Cancel button/option exists but doesn't undo prior saves

**Prevention:**
- Collect ALL edits in memory, then save once at the end when user confirms
- Show a summary of all changes before saving: "Changes: name 'Octopus Pro' -> 'Octopus Pro v1.1', flash_method 'katapult' -> 'make_flash'. Save? [y/N]"
- Cancel discards all in-memory changes, registry untouched
- This matches the single-save pattern from CFG-4

**Phase:** TUI design phase. Decide collect-then-save vs save-per-field before building.

---

### CFG-10: Concurrent Registry Access During Edit

**What goes wrong:** User has two SSH sessions open. Session A starts editing a device. Session B flashes a device, which updates registry (e.g., flash method fallback). Session A saves, overwriting Session B's changes because it loaded a stale copy.

**Why it happens:** `registry.load()` reads the full file into memory. Edits mutate the in-memory copy. `registry.save()` writes the full file. There's no locking. The edit flow holds the in-memory copy for the duration of user interaction (could be minutes).

**Warning signs:**
- Edit flow calls `load()` at start, `save()` at end, with user interaction in between
- No file locking mechanism exists
- Multiple SSH sessions are the standard usage pattern (CLAUDE.md confirms SSH access)

**Prevention:**
- For MVP: accept the race condition. It's unlikely (single-user tool) and the atomic write prevents corruption (just data loss from overwrite)
- Document: "Don't edit device config while flashing in another session"
- Future improvement: load-modify-save with a re-read before save to detect changes, or advisory file locking with `fcntl.flock()`
- The atomic write pattern prevents file corruption but not logical conflicts

**Phase:** Acknowledged risk, not a blocker. Document in tool help/warnings. Consider locking in future version.

---

## Technical Debt Patterns (v4.0)

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Rename as delete+add (two saves) | Simple implementation | Race window where device is missing | Never -- use single load-mutate-save |
| Skip config directory migration | Faster to ship | Orphaned directories, lost configs on rename | Never -- core to the rename feature |
| Inline key validation in edit flow | No refactoring needed | Inconsistent validation, duplicate logic | Only if add-device is being rewritten simultaneously |
| Save per field in TUI | Simpler state management | No cancel/rollback capability | Never -- collect-then-save is not much harder |
| Free text for flash_method | No enum to maintain | Typos stored, fail at flash time | Never -- use selection UI |

## Integration Gotchas (v4.0)

| Integration Point | Common Mistake | Correct Approach |
|--------------------|----------------|------------------|
| Registry dict key vs DeviceEntry.key | Rename dict key, forget to update entry.key | Create new DeviceEntry with new key |
| Config cache directory | Rename registry key, forget directory migration | shutil.move() old dir to new dir BEFORE registry save |
| Key validation | Different rules in add vs edit | Extract shared validate_device_key() function |
| flash_method values | Accept any string | Selection from {"katapult", "make_flash", None} |
| serial_pattern edit | No live validation | Scan /dev/serial/by-id/ after edit, show matches |
| Cancel/rollback | Save each field immediately | Collect all edits, save once on confirm |

## "Looks Done But Isn't" Checklist (v4.0)

- [ ] **Key rename:** Both registry JSON key AND DeviceEntry.key field updated
- [ ] **Config migration:** Old config directory moved to new key's path
- [ ] **Collision check:** New key checked against existing registry entries AND existing config directories
- [ ] **Single save:** Rename uses one load-mutate-save cycle, not two
- [ ] **Shared validation:** Same key validation rules for add and rename
- [ ] **Flash method:** Constrained selection, not free text
- [ ] **serial_pattern:** Live match test after edit
- [ ] **Cancel works:** No partial saves when user cancels mid-edit
- [ ] **Warning shown:** User warned about external references (scripts, aliases) on key rename
- [ ] **Edge cases:** Empty key, duplicate key, key with path chars, key with spaces all rejected

## Pitfall-to-Phase Mapping (v4.0)

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Orphaned config cache (CFG-1) | Key rename implementation | Rename key, verify old dir gone, new dir has .config |
| Key collision (CFG-2) | Key rename validation | Try renaming to existing key, verify rejection |
| Broken external refs (CFG-3) | UX/confirmation | Rename shows warning about scripts/aliases |
| Partial update on crash (CFG-4) | Core implementation | Single registry.save() call in rename path |
| Key validation (CFG-5) | Prerequisite extraction | Shared function used by both add and rename |
| DeviceEntry.key stale (CFG-6) | Core implementation | After rename, entry.key matches new key |
| Invalid flash method (CFG-7) | Edit flow UI | Selection picker, not free text |
| Pattern breaks matching (CFG-8) | Edit flow UI | Live scan after pattern edit |
| No cancel/rollback (CFG-9) | TUI design | Cancel after partial edits, verify no changes saved |
| Concurrent access (CFG-10) | Documentation | Acknowledged race, document limitation |

## Sources (v4.0)

### Codebase Analysis (HIGH confidence)
- `kflash/registry.py` - Registry CRUD: add/remove/save use load-mutate-save pattern, no rename method exists
- `kflash/models.py` - DeviceEntry has `.key` field separate from dict key, flash_method is Optional[str] with no validation
- `kflash/config.py` - `get_config_dir(device_key)` uses key as directory name, no rename/move capability
- `kflash/flash.py` - `_remove_cached_config()` is the only place config dirs are cleaned up, called only on explicit device removal
- `kflash/registry.py:_atomic_write_json()` - Atomic write prevents corruption but not logical conflicts

### Domain Knowledge (HIGH confidence)
- Python `shutil.move()` vs `os.rename()` cross-filesystem behavior
- `fcntl.flock()` advisory locking semantics on Linux
- Glob pattern matching behavior for serial device paths
- Dataclass field vs dict key independence in Python

---

*[Previous v1.0, v2.0, v2.1, v3.2, v4.0 pitfalls preserved below for historical context]*

---

## v3.2 Visual Dividers Pitfalls

### DIV-1: Hardcoded Width Dividers Break on Terminal Resize

**What goes wrong:** Dividers with fixed character counts (e.g., `print("─" * 80)`) appear truncated or wrap incorrectly when terminal width changes after the divider is rendered. Users who resize their SSH terminal window mid-workflow see broken visual output.

**Why it happens:** Developers test at one terminal size (often 80 or 120 columns) and hardcode divider width to that size. Terminal width is checked once at startup but not per-divider. The tool runs over SSH where users frequently resize windows to fit their workflow.

**Warning signs:**
- Dividers that work in testing but user reports "weird wrapping"
- Dividers render correctly at start but break after `clear_screen()`
- Reports from SSH users specifically (terminal resize more common)

**Prevention:**
- Use `shutil.get_terminal_size()` per divider render, not once at startup
- Fall back to safe minimum (40 cols) when size detection fails
- Test with multiple terminal widths: 40, 80, 120, 200 columns
- The codebase already has `ansi.get_terminal_width()` with fallback - use it consistently

**Phase:** Phase 2: Divider Implementation - Terminal width detection must be per-divider, not cached

---

### DIV-2: NullOutput Breaking Output Protocol Contract

**What goes wrong:** Adding divider methods to `Output` protocol and `CliOutput` but forgetting to implement them in `NullOutput`. Protocol violations cause runtime failures when NullOutput is used (testing, programmatic use, future Moonraker integration).

**Why it happens:** Developers focus on visible output (CliOutput) and forget that NullOutput must implement every protocol method. Python's Protocol doesn't enforce implementation at definition time - only fails at runtime when called.

**Warning signs:**
- AttributeError when running with NullOutput
- Tests pass with CliOutput but fail with mock output
- Future Moonraker integration attempts fail mysteriously

**Prevention:**
- Every new Output method requires NullOutput implementation
- NullOutput methods should be no-ops (pass), not raise NotImplementedError
- Add test that instantiates NullOutput and calls all methods
- Check both CliOutput and NullOutput when adding protocol methods

**Phase:** Phase 2: Divider Implementation - Add NullOutput methods in same commit as Output protocol extension

---

### DIV-3: ANSI Escape Codes in Redirected/Piped Output

**What goes wrong:** Dividers containing ANSI color codes are written to log files or piped output where they render as `^[[38;2;100;160;180m───^[[0m` garbage. Users who pipe output to files or use `kflash --device X | tee log.txt` get unreadable logs.

**Why it happens:** Color detection happens once via `detect_color_tier()` based on `sys.stdout.isatty()`. But developers forget that colored dividers will leak through to non-TTY contexts if not properly gated. The theme system already handles this with ColorTier.NONE, but dividers must respect it.

**Warning signs:**
- Bug reports about "weird characters in log files"
- CI/CD output shows escape codes instead of colors
- Users report issues specifically when using `tee` or redirection

**Prevention:**
- Always use `theme.border` (not hardcoded `\033[...`) so tier fallback works
- Theme system already detects TTY - trust it
- When `tier == ColorTier.NONE`, divider should be plain ASCII
- Test with: `kflash --list-devices > output.txt` and verify no escape codes

**Phase:** Phase 2: Divider Implementation - Use theme colors consistently, never hardcode ANSI

---

### DIV-4: Unicode Box Drawing Characters on Degraded Terminals

**What goes wrong:** Unicode box-drawing characters (┄, ─, ╌) fail to render on terminals with limited Unicode support (old SSH clients, Windows CMD without UTF-8 codepage, misconfigured locales). Users see `?` or mojibake instead of dividers.

**Why it happens:** Developers test on modern terminals (WSL2, iTerm2, modern SSH clients) with full UTF-8 support. Raspberry Pi SSH sessions can have varying locale configurations. Windows Python can default to cp1252 encoding which lacks box-drawing characters.

**Warning signs:**
- User reports dividers showing as question marks
- Issues reported specifically from Windows SSH clients
- Bug reports mentioning "weird squares" or "boxes"

**Prevention:**
- Provide ASCII fallback for degraded terminals: `-` instead of `─`, `.` instead of `┄`
- Check `sys.stdout.encoding` - if not UTF-8, use ASCII
- Consider adding Unicode tier detection similar to ColorTier
- Test on actual Raspberry Pi SSH session (not just local dev)
- Test with `LANG=C` to simulate degraded locale

**Phase:** Phase 3: Fallback & Testing - Add encoding detection and ASCII fallback mode

---

### DIV-5: Dividers Interfering with Progress Bar/Spinner Output

**What goes wrong:** If dividers use `print()` while a countdown timer or progress indicator uses `\r` carriage return to update in place, the divider breaks the in-place update. The countdown shows `3...───\n2...` instead of staying on one line.

**Why it happens:** `print()` adds a newline by default. If code uses carriage return for in-place updates (like the countdown timer in TUI), a divider between updates breaks the illusion. The codebase has a countdown timer - dividers must not interrupt it.

**Warning signs:**
- Countdown timer displays multiple lines instead of updating one line
- Progress indicators show stacked output instead of smooth updates
- User reports "countdown looks weird with new dividers"

**Prevention:**
- Never print dividers between countdown timer start and completion
- Place dividers AFTER complete sections, not during active updates
- Review `tui.py` countdown timer code path - ensure no dividers mid-countdown
- If divider must appear near timer, flush timer line first with newline

**Phase:** Phase 2: Divider Implementation - Review all in-place update code paths before adding dividers

---

### DIV-6: Over-Dividing Creates Visual Noise

**What goes wrong:** Adding dividers between every output line creates cluttered, hard-to-scan output. Users complain the tool "looks busier" or "harder to read". The Minimalist Zen aesthetic is compromised by excessive decoration.

**Why it happens:** After adding divider capability, developers get enthusiastic and add them everywhere. "More visual separation = better" is intuitive but wrong. The tool's aesthetic is minimalist - dividers should be subtle punctuation, not wallpaper.

**Warning signs:**
- Output looks "busy" or "cluttered" in review
- Hard to quickly scan for phase boundaries (dividers everywhere = dividers nowhere)
- Feedback that "the old version was cleaner"

**Prevention:**
- Dividers only between major sections (phase boundaries, device switches)
- Light dashed `┄` for step dividers - visually quieter than solid lines
- Labeled dividers only for multi-device workflows (flash-all)
- Review output with "does this improve scannability?" test
- Get feedback: show before/after to stakeholder

**Phase:** Phase 1: Design Spec - Define clear rules for where dividers appear

---

### DIV-7: Divider Methods Not Called in All Workflow Paths

**What goes wrong:** Dividers added to main happy path (e.g., `cmd_flash`) but missing in alternative paths (add-device wizard, remove-device, error recovery). Inconsistent visual structure confuses users - "why do some commands have dividers and others don't?"

**Why it happens:** Developers focus on one command flow during implementation. The codebase has multiple entry points: flash, add-device, remove-device, list-devices, TUI menu, flash-all. Each has multiple code paths (success, error, cancellation).

**Warning signs:**
- User reports "dividers work in flash but not in add-device"
- Inconsistent visual structure between commands
- Some outputs look "polished" while others look "unfinished"

**Prevention:**
- Audit all commands and add dividers consistently:
  - `cmd_flash` (4 phases: Discovery, Config, Build, Flash)
  - `cmd_add_device` (step-by-step wizard)
  - `cmd_remove_device` (confirmation flow)
  - `cmd_flash_all` (per-device labeled dividers)
  - TUI menu (between panel and action output)
- Test each command path (success, error, cancel) to verify dividers appear
- Create checklist of all workflow entry points

**Phase:** Phase 4: Integration - Systematic audit of all command paths

---

### DIV-8: Labeled Dividers with Dynamic Content Breaking Width

**What goes wrong:** Flash-all labeled dividers like `─── 1/5 Very Long Device Name That Exceeds Width ───` overflow terminal width or wrap awkwardly. Dynamic device names of varying lengths make width calculations fail.

**Why it happens:** Device names are user-provided and unbounded. A 30-character device name plus label prefix/suffix plus padding dashes can exceed terminal width. Simple center-padding logic doesn't account for overflow.

**Warning signs:**
- Dividers wrap to second line with long device names
- Uneven padding left/right of label
- User reports "dividers look broken with my device names"

**Prevention:**
- Truncate device names in labeled dividers (e.g., 20 chars max)
- Calculate available width: `terminal_width - label_length - padding`
- Use `ansi.display_width()` (already in codebase) for accurate width
- Test with absurdly long device names (50+ chars)
- Consider format: `─── 1/5 octopus-pro ───` not `─── 1/5 BTT Octopus Pro v1.1 STM32H723 USB ───`

**Phase:** Phase 2: Divider Implementation - Use display_width() and truncate names

---

### DIV-9: Dividers in Error Output Break Tone

**What goes wrong:** Decorative dividers appearing in `error_with_recovery()` output feel tone-deaf. Visual decoration during urgent error messages undermines the severity.

**Why it happens:** Global divider injection applied uniformly without context awareness. Error messages need clarity, not decoration.

**Warning signs:**
- Error messages surrounded by divider lines feel "less urgent"
- User feedback that errors don't "feel like errors"
- Dividers appear between error type and recovery steps

**Prevention:**
- No dividers in error_with_recovery() output
- No dividers in exception handling paths
- Dividers only in normal workflow output
- Review all error handling paths - ensure dividers don't appear

**Phase:** Phase 4: Integration - Audit error paths

---

### DIV-10: ANSI Width Calculation Pitfall

**What goes wrong:** Using `len(divider_string)` for width padding when the string contains ANSI color codes. ANSI sequences like `\033[38;2;100;160;180m` are invisible but have 19+ character length, breaking alignment.

**Why it happens:** Developers forget that styled strings have invisible characters. The codebase already has `ansi.display_width()` but not using it consistently for divider rendering.

**Warning signs:**
- Labeled dividers don't center properly
- Divider padding misaligned left vs right
- Works with NO_COLOR but breaks with colors enabled

**Prevention:**
- Always use `ansi.display_width()` for width calculations
- Never use `len()` on strings that may contain ANSI codes
- The codebase already has this utility - use it
- Test with both color and no-color themes

**Phase:** Phase 2: Divider Implementation - Use display_width() from day one

---

## Technical Debt Patterns (v3.2)

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcode divider characters without fallback | Works on modern terminals, simple code | Breaks on degraded terminals, cp1252 encoding issues | Never - always provide ASCII fallback |
| Cache terminal width at startup | One syscall instead of per-divider | Breaks on terminal resize, common over SSH | Never - width detection is cheap (shutil) |
| Skip NullOutput implementation | Faster initial implementation | Protocol violation, breaks testing/future integrations | Never - required by Protocol contract |
| Add dividers without audit of all paths | Ships feature faster | Inconsistent UX, looks unfinished | Never - consistency is core to UX |
| Use plain `print("───")` without theme | Simple, no dependencies | No tier fallback, breaks on piped output | Testing only, never production |

## Integration Gotchas (v3.2)

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Output protocol | Adding method to Protocol + CliOutput only | Add to Protocol, CliOutput, AND NullOutput in same commit |
| Theme system | Hardcoding ANSI codes for divider color | Use `theme.border` - respects tier fallback automatically |
| ANSI utilities | Not using `display_width()` for width calc | Use `ansi.display_width()` - handles ANSI codes and CJK chars |
| Terminal size | Calling `get_terminal_width()` once | Call per-divider - users resize terminals |
| Countdown timer | Printing divider during in-place updates | Only print dividers AFTER timer completes |

## UX Pitfalls (v3.2)

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Dividers between every line | Output feels cluttered, hard to scan | Dividers only between major sections (phases, devices) |
| Inconsistent divider presence | Confusing - "why here but not there?" | Audit all command paths, add consistently |
| Dividers overwhelming phase labels | Can't find phase boundaries in clutter | Light dashed `┄` for steps, solid `─` for phases |
| No visual hierarchy | All dividers look the same | Light/dashed for steps, labeled/solid for devices |
| Dividers in error output | Decorative dividers in urgent error messages feel tone-deaf | No dividers in error_with_recovery() output |

## "Looks Done But Isn't" Checklist (v3.2)

- [ ] **Divider methods:** Both CliOutput AND NullOutput implement all new methods
- [ ] **Terminal width:** Every divider uses `get_terminal_width()`, not cached value
- [ ] **Theme colors:** All dividers use `theme.border`, no hardcoded ANSI codes
- [ ] **Unicode fallback:** ASCII alternatives defined for degraded terminals
- [ ] **All command paths:** flash, add-device, remove-device, list-devices, flash-all all audited
- [ ] **Error paths:** Dividers don't appear in error recovery messages
- [ ] **Redirect test:** `kflash --list-devices > file.txt` contains no escape codes (if NO_COLOR)
- [ ] **SSH test:** Verified on actual Raspberry Pi SSH session, not just local
- [ ] **Width edge cases:** Tested at 40, 80, 120+ column widths
- [ ] **Long names:** Tested with 50+ char device names in flash-all labeled dividers
- [ ] **ANSI width:** All divider padding uses `display_width()`, not `len()`
- [ ] **Countdown intact:** Timer updates stay on one line with dividers present

## Recovery Strategies (v3.2)

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| NullOutput missing methods | LOW | Add pass-through methods to NullOutput, patch release |
| Hardcoded ANSI in dividers | LOW | Replace hardcoded codes with `theme.border` references |
| Hardcoded width dividers | MEDIUM | Add `get_terminal_width()` calls, test across widths |
| Unicode without fallback | MEDIUM | Add encoding detection + ASCII mode, requires testing |
| Inconsistent divider placement | HIGH | Full audit of all command paths, systematic testing |
| Over-dividing visual noise | LOW | Remove excessive dividers - easier than adding |
| Labeled dividers overflow | LOW | Add truncation logic to device name in label |

## Pitfall-to-Phase Mapping (v3.2)

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Hardcoded width (DIV-1) | Phase 2: Implementation | Test at 40, 80, 120 cols - no wrapping/truncation |
| NullOutput missing (DIV-2) | Phase 2: Implementation | Instantiate NullOutput, call all divider methods - no errors |
| ANSI in redirected output (DIV-3) | Phase 2: Implementation | `kflash --list > out.txt` with NO_COLOR=1 - no escape codes |
| Unicode without fallback (DIV-4) | Phase 3: Fallback | Test with LANG=C - ASCII dividers appear |
| Dividers + progress updates (DIV-5) | Phase 2: Implementation | Run flash with countdown - timer stays on one line |
| Over-dividing (DIV-6) | Phase 1: Design | Stakeholder review of mockup - "improves scannability" |
| Inconsistent placement (DIV-7) | Phase 4: Integration | Checklist: all commands (flash, add, remove, list, flash-all) have dividers |
| Labeled divider overflow (DIV-8) | Phase 2: Implementation | Flash-all with 50-char device name - divider fits in 80 cols |
| Dividers in errors (DIV-9) | Phase 4: Integration | Error paths audited - no dividers |
| ANSI width calc (DIV-10) | Phase 2: Implementation | Labeled dividers center correctly with colors |

## Sources (v3.2)

### Web Research (LOW-MEDIUM confidence)
- [Add Separator Line Between Commands on Linux Terminal](https://www.ubuntubuzz.com/2012/04/add-separator-line-between-commands-on.html) - Command line separator patterns
- [Line Separator That is Width of Terminal Using printf](https://www.commandlinefu.com/commands/view/24626/line-separator-that-is-width-of-terminal) - Dynamic width terminal separators
- [Gaps before separators · Issue #1313 · Powerlevel9k/powerlevel9k](https://github.com/Powerlevel9k/powerlevel9k/issues/1313) - Visual separator issues in terminal themes
- [ANSI sequence "ESC [ 8;<lines>;<cols>t" fails to resize window](https://github.com/microsoft/terminal/issues/8673) - Terminal resize with ANSI sequences
- [ANSI control code for line wrapping not supported](https://github.com/microsoft/terminal/issues/8404) - ANSI line wrapping issues
- [Drawing tables (boxes) using UTF-8 symbols](https://aaabramov.medium.com/drawing-tables-boxes-using-utf-8-symbols-d7208e8c3f3e) - Unicode box drawing characters
- [Unicode boxes on a terminal](https://flotpython-exos-python.readthedocs.io/en/main/tps/unicode-boxes/README-unicode-boxes-nb.html) - Python Unicode box drawing, encoding issues
- [CLI UX best practices: progress displays](https://evilmartians.com/chronicles/cli-ux-best-practices-3-patterns-for-improving-progress-displays) - CLI progress output patterns
- [Terminal control/Dimensions - Rosetta Code](https://rosettacode.org/wiki/Terminal_control/Dimensions) - Terminal dimension detection

### Codebase Analysis (HIGH confidence)
- `kflash/output.py` - Output Protocol with CliOutput and NullOutput implementations
- `kflash/theme.py` - Theme system with ColorTier fallback (TRUECOLOR → ANSI256 → ANSI16 → NONE)
- `kflash/ansi.py` - ANSI-aware utilities: `strip_ansi()`, `display_width()`, `get_terminal_width()`
- `kflash/flash.py` - Multiple command entry points: cmd_flash, cmd_add_device, cmd_remove_device, cmd_flash_all
- `kflash/tui.py` - Countdown timer with in-place updates (potential conflict with dividers)
- `.planning/PROJECT.md` - Minimalist Zen aesthetic, stdlib-only constraint, SSH usage context

### Domain Knowledge (HIGH confidence)
- Python 3.9+ stdlib limitations (no Rich library, manual ANSI handling)
- SSH terminal behavior (window resizing, varying locale configurations)
- Raspberry Pi environment (UTF-8 locale not guaranteed, varied SSH clients)
- Protocol pattern in Python (runtime duck typing, no compile-time enforcement)
- ANSI escape code behavior in piped/redirected output

---

## Critical Pitfalls (can brick boards or lose data)

### CP-1: Klipper Service Not Restarted After Flash Failure

**Description:** If the flash subprocess fails (timeout, device disconnect, bad firmware image) and the tool exits without restarting the klipper service, the printer is left in a dead state. The user's running print queue, temperature monitoring, and safety watchdogs are all offline. On a heated printer, this means no thermal runaway protection.

**Warning signs:**
- Any unhandled exception between `systemctl stop klipper` and `systemctl start klipper`
- Early return or `sys.exit()` in error handling paths
- KeyboardInterrupt (Ctrl+C) during flash not caught
- Code reviews that show `stop` without a corresponding `finally` block containing `start`

**Prevention:**
- Wrap the entire stop-flash-start sequence in a `try/finally` block where `finally` ALWAYS runs `systemctl start klipper`
- Also catch `KeyboardInterrupt` and `SystemExit` explicitly in the finally path
- Add a signal handler for SIGTERM that triggers service restart before exit
- Consider a watchdog approach: record "klipper stopped" state to a temp file, and on tool startup check if a previous run left klipper stopped

**Phase to address:** Phase 1 (core flash flow). This is the single most important safety invariant in the entire tool. Must be the first thing designed and the last thing cut.

---

### CP-2: Flashing Wrong Firmware to Wrong Board

**Description:** If the user selects "Octopus Pro" but the .config cached is actually for the Nitehawk RP2040 (or vice versa), the wrong firmware binary gets flashed. For STM32 boards with Katapult bootloader, this typically results in a board that boots into a non-functional state. Recovery requires DFU mode via boot jumper (physical access to the board). For RP2040, recovery is easier (hold BOOTSEL and replug), but still disruptive.

**Warning signs:**
- Config files named generically or mismatched to device registry entries
- No validation that .config MCU architecture matches the target device
- Copy-paste errors in devices.json serial patterns
- `configs/` directory manually edited

**Prevention:**
- After loading a cached .config, parse it and verify the `CONFIG_BOARD_*` or `CONFIG_MCU` line matches the expected MCU family from devices.json
- Display the MCU architecture from .config before flashing and require confirmation: "About to flash STM32H723 firmware to Octopus Pro. Continue?"
- Never allow a flash to proceed if .config does not exist for the selected device
- Store MCU type in the .config.sha256 sidecar as metadata for cross-validation

**Phase to address:** Phase 1 (config manager). The config-device binding must be validated at flash time, not just at registration time.

---

### CP-3: Flashing During Active Print

**Description:** If klipper is running a print and the user runs `flash.py`, stopping klipper mid-print causes the hotend to remain at temperature with no firmware control (heater stuck on until thermal fuse blows or SSR is de-energized). The print is destroyed, and in worst case, the hotend or bed heater causes damage.

**Warning signs:**
- No check for printer state before stopping klipper
- Klipper API (Moonraker) not queried for print status
- Tool assumes "if user runs it, they want it"

**Prevention:**
- Before stopping klipper, query Moonraker API at `http://localhost:7125/printer/objects/query?print_stats` to check if `state` is `printing` or `paused`
- If printing, refuse to proceed with a clear message: "Printer is currently printing. Abort print first or use --force to override."
- If Moonraker is unreachable (not running), warn but allow proceed (the user may be recovering from a crashed klipper)
- This is a SHOULD, not a MUST for MVP -- a simple "Are you sure?" prompt is acceptable as minimum

**Phase to address:** Phase 2 (safety checks). Can be a simple prompt in Phase 1, upgraded to Moonraker API check in Phase 2.

---

*Pitfalls research: 2026-01-25 (v1.0), 2026-01-26 (v2.0 additions), 2026-01-29 (v2.1 panel TUI + batch flash), 2026-01-30 (v3.2 visual dividers), 2026-01-31 (v4.0 config device editing, v5.0 CLI removal + key internalization)*
*Confidence: HIGH -- based on direct codebase analysis of registry.py, config.py, models.py key usage patterns, and Python file operation semantics.*
