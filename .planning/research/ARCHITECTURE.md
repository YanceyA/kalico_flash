# Architecture Patterns: CLI Removal and Device Key Internalization

**Domain:** kalico-flash CLI-to-TUI-only refactor
**Researched:** 2026-01-31
**Confidence:** HIGH (based on direct codebase analysis of all 16 source files)

## Current Architecture Summary

Hub-and-spoke: `flash.py` is the hub containing `main()` with argparse, all `cmd_*` functions, preflight checks, and blocked-device logic. `tui.py` provides the interactive menu loop. Modules do not cross-import except through flash.py orchestration.

**Entry flow today:**
```
kflash.py -> flash.main() -> argparse
  if --add-device    -> cmd_add_device()
  if --device KEY    -> cmd_flash()
  if --list-devices  -> cmd_list_devices()
  if --remove-device -> cmd_remove_device()
  if --exclude/include -> cmd_exclude/include_device()
  if no args + TTY   -> tui.run_menu()
  if no args + !TTY  -> print help
```

**Key observation:** The TUI (`run_menu`) already handles every operation through action handlers (`_action_flash_device`, `_action_add_device`, `_action_remove_device`). These handlers call back into `flash.py`'s `cmd_*` functions. The CLI flags are a parallel entry path that duplicates the TUI's capabilities.

## What Changes

### 1. Entry Point (`flash.py` -> simplified)

**Remove:** `build_parser()`, `argparse` import, all CLI flag handling in `main()`.

**New `main()`:**
```python
def main() -> int:
    if not sys.stdin.isatty():
        sys.exit("kalico-flash requires an interactive terminal.")
    from .output import CliOutput
    from .registry import Registry
    from .tui import run_menu
    out = CliOutput()
    registry_path = Path(__file__).parent / "devices.json"
    registry = Registry(str(registry_path))
    try:
        return run_menu(registry, out)
    except KeyboardInterrupt:
        return 130
    except KlipperFlashError as e:
        out.error(str(e))
        return 1
```

**Rationale:** `flash.py` becomes a thin launcher. All routing lives in `tui.run_menu()` where it already exists. The `cmd_*` functions remain in flash.py as the orchestration layer -- the TUI calls them, no change needed there.

**Impact:** ~60 lines removed (parser + flag routing). Zero changes to any `cmd_*` function signatures.

### 2. Device Key Internalization (`cmd_add_device` in `flash.py`)

**Current:** User manually types a device key at "Device key" prompt (step 4, line 1815-1827).

**New:** Auto-generate key from device name using a `slugify` function.

**Where to add `generate_device_key()`:** `validation.py` (already has `validate_device_key`).

```python
def generate_device_key(display_name: str, registry) -> str:
    """Generate a unique device key from display name.

    'Octopus Pro v1.1' -> 'octopus-pro-v1-1'
    If collision, appends -2, -3, etc.
    """
    slug = re.sub(r'[^a-z0-9]+', '-', display_name.lower()).strip('-')
    if not slug:
        slug = 'device'
    candidate = slug
    counter = 2
    while registry.get(candidate) is not None:
        candidate = f"{slug}-{counter}"
        counter += 1
    return candidate
```

**Impact on `cmd_add_device`:** Remove step 4 (key prompt loop, lines 1814-1827). Replace with:
```python
device_key = generate_device_key(display_name, registry)
out.info("Registry", f"Device key: {device_key}")
```

**Impact on `DeviceEntry.key`:** Field remains. Still used as dict key in registry, config cache dir name, and internal references. Users just no longer see or type it.

### 3. Device Key in Device Config Screen (`tui.py` `_device_config_screen`)

**Current:** DEVICE_SETTINGS index 1 is `{"key": "key", ...}` allowing key editing.

**New:** Remove key from DEVICE_SETTINGS. Key becomes read-only, derived from name. When user edits name, key auto-regenerates.

**Changes in `screen.py`:**
- Remove `{"key": "key", ...}` from `DEVICE_SETTINGS` (line 481)
- Adjust numbering (settings become 1-4 instead of 1-5)

**Changes in `tui.py` `_device_config_screen`:**
- Remove key editing branch (lines 833-846)
- When name changes, auto-derive new key: `pending["key"] = generate_device_key(new_name, registry)`
- Adjust keypress range from `("1","2","3","4","5")` to `("1","2","3","4")`

### 4. References to `--device KEY` in User-Facing Strings

Grep for `--device` in output strings that will need updating:

| File | Line | Current Text | Action |
|------|------|-------------|--------|
| `flash.py` | 1816 | `"Device key (used with --device flag..."` | Remove (step eliminated) |
| `flash.py` | 681 | `"run \`kflash --include-device {device_key}\`"` | Change to TUI instructions |
| `flash.py` | 543 | `"Register new device: kflash --add-device"` | Change to "Press A to add" |
| `flash.py` | 541 | `"List registered devices: kflash --list-devices"` | Change to "Press D to refresh" |
| `errors.py` | Various | recovery templates referencing CLI flags | Update all to TUI instructions |

**Note:** `from_tui` parameter on several `cmd_*` functions already switches between CLI and TUI recovery text. After CLI removal, the `from_tui` parameter can be removed and all paths default to TUI text.

## Component Boundaries (Post-Change)

| Component | Responsibility | Changes |
|-----------|---------------|---------|
| `flash.py` | Thin launcher + `cmd_*` orchestration | Remove argparse, simplify `main()` |
| `tui.py` | Menu loop, action dispatch, input handling | No structural change |
| `screen.py` | Panel rendering, settings definitions | Remove key from DEVICE_SETTINGS |
| `registry.py` | JSON CRUD, atomic writes | No change |
| `config.py` | Config caching keyed by device key | No change (still uses key internally) |
| `validation.py` | Input validation | Add `generate_device_key()` |
| `models.py` | Dataclass contracts | No change (`DeviceEntry.key` stays) |
| `discovery.py` | USB scanning | No change |
| All other modules | build, flash, service, moonraker, etc. | No change |

## Data Flow Changes

### Before (CLI path):
```
User types: kflash --device octopus-pro
  -> argparse extracts key
  -> cmd_flash(registry, "octopus-pro", out)
  -> registry.get("octopus-pro")
```

### After (TUI-only path, unchanged):
```
User presses F, selects device #1
  -> _prompt_device_number returns key from DeviceRow.key
  -> _action_flash_device calls cmd_flash(registry, key, out)
  -> registry.get(key)
```

### Key generation (new):
```
User enters display name "Octopus Pro v1.1"
  -> generate_device_key("Octopus Pro v1.1", registry)
  -> returns "octopus-pro-v1-1"
  -> DeviceEntry(key="octopus-pro-v1-1", name="Octopus Pro v1.1", ...)
  -> registry.add(entry)
  -> config cache at ~/.config/kalico-flash/configs/octopus-pro-v1-1/
```

### Key rename on name edit:
```
User edits name from "Octopus Pro v1.1" to "Octopus Pro 446"
  -> generate_device_key("Octopus Pro 446", registry)
  -> returns "octopus-pro-446"
  -> pending["key"] = "octopus-pro-446", pending["name"] = "Octopus Pro 446"
  -> _save_device_edits renames config cache + registry entry
```

## Migration Strategy for Existing devices.json

**No migration needed.** The `DeviceEntry.key` field persists in JSON. Existing keys like `"octopus-pro"` continue to work. The only change is that new devices get auto-generated keys instead of user-typed ones. The device config screen still allows name editing which triggers key regeneration, but existing devices keep their keys unless the user edits the name.

**Edge case:** If a user edits an existing device name, the key will be regenerated from the new name. The `_save_device_edits` function already handles key rename with config cache migration (lines 730-761 of tui.py). No new migration code required.

## Anti-Patterns to Avoid

### Do Not Remove DeviceEntry.key
The key is the primary identifier throughout the codebase: registry dict keys, config cache directory names, `cmd_*` function parameters, `_prompt_device_number` return values. Removing it would cascade changes through every module. Keep it as an internal implementation detail -- just stop exposing it to users.

### Do Not Move cmd_* Functions to tui.py
The `cmd_*` functions in flash.py are the orchestration layer. They contain preflight checks, phase sequencing, error handling with recovery text. Moving them to tui.py would violate the hub-and-spoke pattern and make tui.py a 2000+ line file. Keep the current separation: tui.py dispatches, flash.py orchestrates.

### Do Not Remove from_tui Parameter in Phase 1
While `from_tui` becomes always-true after CLI removal, removing it in the same change adds risk. Remove it in a follow-up cleanup phase to keep each change small and reviewable.

## Suggested Build Order

### Phase 1: Add key generation (safe, additive)
- Add `generate_device_key()` to `validation.py`
- No existing behavior changes
- Testable in isolation on Pi

### Phase 2: Internalize key in add-device flow
- Replace key prompt in `cmd_add_device` with auto-generation
- Show generated key as info message
- Existing devices unaffected

### Phase 3: Remove key editing from device config screen
- Remove key from `DEVICE_SETTINGS` in `screen.py`
- Add auto-key-regeneration on name edit in `tui.py`
- Adjust keypress range in `_device_config_screen`

### Phase 4: Remove CLI/argparse
- Simplify `main()` in `flash.py` to TUI-only launcher
- Remove `build_parser()` and argparse import
- Update all `--flag` references in user-facing strings
- Remove `from_tui` parameter (optional, can defer)

### Phase 5: Cleanup
- Remove dead CLI-only code paths (non-TTY help printing)
- Update CLAUDE.md CLI usage section
- Remove `--device`, `--add-device`, etc. from docstrings

**Why this order:** Phase 1-2 are purely additive (no breaking changes). Phase 3 changes TUI behavior but is self-contained. Phase 4 is the breaking change (CLI removal) but by this point all functionality is already TUI-native. Phase 5 is cosmetic cleanup.

## Sources

- Direct codebase analysis of all files in `C:\dev_projects\kalico_flash\kflash\`
- `flash.py` lines 92-157 (argparse parser), 1986-2041 (main entry point)
- `flash.py` lines 1813-1827 (device key prompt in add-device wizard)
- `tui.py` lines 455-621 (run_menu dispatch), 730-889 (device config screen)
- `screen.py` lines 479-490 (DEVICE_SETTINGS definition)
- `validation.py` (existing validate_device_key function)
- `config.py` lines 16-27 (get_config_dir uses device_key), 30-48 (rename_device_config_cache)
- `registry.py` lines 43-51 (device key as dict key in JSON)
