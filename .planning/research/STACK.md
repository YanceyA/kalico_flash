# Technology Stack

**Project:** kalico-flash "Config Device" feature
**Researched:** 2026-01-31
**Overall Confidence:** HIGH (all APIs are Python stdlib, all patterns already proven in codebase)

---

## Recommended Stack

No new dependencies. This feature uses existing stdlib APIs and existing codebase patterns exclusively.

### Stdlib APIs Needed for New Capabilities

| API | Module | Purpose | Why |
|-----|--------|---------|-----|
| `shutil.move()` | `shutil` | Rename cached config directory on key change | Handles cross-filesystem moves safely. Already imported in `config.py`. |
| `dataclasses.replace()` | `dataclasses` | Create modified DeviceEntry with new field values | Already used in `_config_screen` for GlobalConfig edits. Same pattern for DeviceEntry. |
| `re.match()` | `re` | Validate device key format (slug: lowercase, hyphens, digits) | Already imported in `config.py`. |
| `Path.exists()` / `Path.is_dir()` | `pathlib` | Check if cached config dir exists before migration | Already used throughout `config.py`. |

### Integration Points with Existing Stack

| Module | Current Role | What's Needed for Config Device |
|--------|-------------|-------------------------------|
| `registry.py` | CRUD for devices via `add()`, `remove()`, `get()`, `save()` | Key rename = load registry, delete old key, insert new key, single `save()`. No new Registry methods strictly required. |
| `config.py` | `get_config_dir(device_key)` returns `~/.config/kalico-flash/configs/{key}/` | Use to locate old/new cache dirs during key rename. No changes to `config.py`. |
| `tui.py` | `_config_screen()` with `_getch()` + setting dispatch | New `_device_config_screen(registry, out, device_key)` following identical pattern. Reuses `_getch()`, `_countdown_return()`, theme. |
| `screen.py` | `render_config_screen(gc)` + `SETTINGS` list | Add `render_device_config_screen(device)` + `DEVICE_SETTINGS` list. Same flat-numbered-list panel rendering. |
| `validation.py` | `validate_numeric_setting()`, `validate_path_setting()` | Add `validate_device_key(key, existing_keys)` for slug format + uniqueness. |
| `models.py` | `DeviceEntry(key, name, mcu, serial_pattern, flash_method, flashable)` | No changes. All editable fields already exist. |
| `errors.py` | `RegistryError` for key conflicts | Reuse as-is. No new error types. |

---

## DeviceEntry Fields as Editable Settings

| # | Field | Edit Type | Validation | Side Effects |
|---|-------|-----------|------------|-------------|
| 1 | `name` | text input | Non-empty string | Display name only, none |
| 2 | `key` | text input | `^[a-z0-9][a-z0-9-]*$`, no duplicates | Triggers config cache dir migration |
| 3 | `flash_method` | cycle | `None` / `"katapult"` / `"make"` | Toggle on keypress like boolean |
| 4 | `flashable` | toggle | boolean | Flip on keypress |
| -- | `mcu` | read-only | -- | Derived from serial, not user-editable |
| -- | `serial_pattern` | read-only | -- | Set at add-device, editing breaks matching |

---

## Key Rename + Config Migration: Implementation Approach

**Use `shutil.move()` not `Path.rename()`** because:
- `shutil.move()` works across filesystems (defensive, even though config cache is likely same FS)
- Config cache dir is at `~/.config/kalico-flash/configs/{device-key}/`
- On key rename: `shutil.move(get_config_dir(old_key), get_config_dir(new_key))`
- If source dir doesn't exist (no cached config yet), skip migration silently
- If destination dir already exists, block the rename (key conflict -- caught by validation)

**Registry update is atomic** because:
- Load full registry, delete old key, insert new key with updated `.key` field, single `save()` call
- `_atomic_write_json` in `registry.py` handles the atomicity (temp + fsync + rename)
- No partial state possible

**Ordering: migrate config dir BEFORE registry save.** If dir move fails, registry unchanged. If registry save fails after dir move, the orphaned new-key dir is harmless (no registry entry points to it, and it will be found if the user retries the rename).

---

## What NOT to Add

| Temptation | Why Not |
|------------|---------|
| New `Registry.rename()` method | Rename is delete + insert + save, 3 lines in the action handler. A dedicated method adds API surface for a one-off operation. |
| Separate "editable device" wrapper dataclass | `DeviceEntry` + `dataclasses.replace()` already covers this. |
| Undo/history for edits | Overengineered. Edits save immediately, matching existing config screen behavior. |
| Config backup before rename | `shutil.move()` is atomic on same filesystem. The old dir is moved, not copied-then-deleted. |
| New error types | `RegistryError` covers key conflicts. No new failure modes. |
| External validation library | `re.match()` for slug format is 1 line. |

---

## Alternatives Considered

| Decision | Chosen | Alternative | Why Not Alternative |
|----------|--------|-------------|-------------------|
| Dir migration | `shutil.move()` | `Path.rename()` | `rename()` fails across filesystems |
| Registry rename | Delete + insert in handler | New `Registry.rename()` | One-off operation, not worth API surface |
| Key validation | Regex in `validation.py` | Inline check in TUI | Reusable, testable, consistent with existing validation pattern |
| flash_method editing | Cycle through options on keypress | Dropdown/sub-menu | Matches toggle pattern already used for booleans in config screen |

---

## Installation

No changes. Zero new dependencies.

```bash
# Nothing to install. Python 3.9+ stdlib only.
```

---

## Confidence Assessment

| Component | Confidence | Rationale |
|-----------|------------|-----------|
| `shutil.move()` for dir rename | HIGH | stdlib, well-documented, already imported |
| `dataclasses.replace()` for editing | HIGH | Already used in `_config_screen` for GlobalConfig |
| Config screen pattern reuse | HIGH | Exact same pattern as existing settings screen |
| Key validation with regex | HIGH | `re` stdlib, trivial pattern |
| Atomic registry update | HIGH | Existing `_atomic_write_json` handles this |

---

## Sources

- Existing codebase: `registry.py` (atomic save pattern), `config.py` (`get_config_dir`, `shutil` import), `tui.py` (`_config_screen` pattern), `screen.py` (panel rendering), `validation.py` (validation helpers), `models.py` (`DeviceEntry` fields)
- Python stdlib: `shutil.move()`, `dataclasses.replace()`, `pathlib.Path`, `re` -- all stable, unchanged APIs
