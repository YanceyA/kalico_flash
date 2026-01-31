# Architecture Patterns

**Domain:** "Config Device" TUI action for kalico-flash
**Researched:** 2026-01-31
**Confidence:** HIGH (based on direct codebase analysis)

## Integration Summary

The "Config device" feature slots cleanly into the existing hub-and-spoke architecture. **No new modules are needed.** The feature follows the exact same pattern as the existing `_config_screen` (global settings) but targets a `DeviceEntry` instead of `GlobalConfig`.

## Modules Requiring Changes

| Module | Change Type | What Changes |
|--------|------------|--------------|
| `tui.py` | **Modified** | New `"e"` key handler in `run_menu`, new `_action_config_device` handler, new `_device_config_screen` function |
| `screen.py` | **Modified** | New `DEVICE_SETTINGS` list, new `render_device_config_screen` function |
| `registry.py` | **Modified** | New `update_device` method (load-modify-save with key rename support) |
| `config.py` | **Modified** | New `rename_config_cache` function for key change migration |
| `validation.py` | **Modified** | New `validate_device_key` function (non-empty, no spaces, not duplicate) |
| `models.py` | **No change** | `DeviceEntry` already has all needed fields (key, name, mcu, serial_pattern, flash_method, flashable) |
| `panels.py` | **No change** | `render_panel` already supports arbitrary content |
| `flash.py` | **No change** | Hub does not need modification; TUI handles dispatch |

## Data Flow: Config Device Action

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
    +-- registry.get(device_key) -> DeviceEntry
    |
    +-- screen.render_device_config_screen(entry) -> panel string
    |
    +-- getch() -> setting number
    |
    +-- Edit loop (same pattern as _config_screen):
    |     toggle: flip immediately, registry.update_device(...)
    |     text:   input() with validation, registry.update_device(...)
    |     key:    input() + validate_device_key() + rename_config_cache()
    |             + registry.update_device(old_key, new_entry)
    |
    +-- Loop back to render until Esc/B
    |
    v
Returns (status_message, status_level) to run_menu
```

## Component Boundaries

### tui.py: `_device_config_screen`

Owns the interaction loop. Reads keypresses, dispatches edits, calls registry. Mirrors `_config_screen` exactly in structure.

**Receives:** registry, out, device_key (string, may change during session if key renamed)
**Returns:** None (modifies registry as side effect, like `_config_screen`)

### screen.py: `DEVICE_SETTINGS` + `render_device_config_screen`

Defines the editable fields and renders the panel. Pure rendering, no state mutation.

```python
DEVICE_SETTINGS: list[dict] = [
    {"key": "name", "label": "Display name", "type": "text"},
    {"key": "key", "label": "Device key", "type": "key"},
    {"key": "mcu", "label": "MCU type", "type": "text"},
    {"key": "serial_pattern", "label": "Serial pattern", "type": "readonly"},
    {"key": "flash_method", "label": "Flash method", "type": "choice", "choices": ["katapult", "make_flash", "global default"]},
    {"key": "flashable", "label": "Flashable", "type": "toggle"},
]
```

**Receives:** DeviceEntry
**Returns:** Multi-line panel string

### registry.py: `update_device`

Atomic update of a device entry. Handles key rename (remove old + add new in single `save()` call).

```python
def update_device(self, old_key: str, entry: DeviceEntry) -> None:
    """Update device, handling key rename if entry.key != old_key."""
    data = self.load()
    if old_key not in data.devices:
        raise RegistryError(f"Device '{old_key}' not found")
    if entry.key != old_key and entry.key in data.devices:
        raise RegistryError(f"Device '{entry.key}' already exists")
    del data.devices[old_key]
    data.devices[entry.key] = entry
    self.save(data)
```

### config.py: `rename_config_cache`

Moves cached `.config` directory when device key changes.

```python
def rename_config_cache(old_key: str, new_key: str) -> bool:
    """Rename config cache directory. Returns True if moved."""
    old_dir = get_config_dir(old_key)
    new_dir = get_config_dir(new_key)
    if old_dir.exists() and not new_dir.exists():
        new_dir.parent.mkdir(parents=True, exist_ok=True)
        old_dir.rename(new_dir)
        return True
    return False
```

### validation.py: `validate_device_key`

```python
def validate_device_key(raw: str, existing_keys: list[str], current_key: str = "") -> tuple[bool, str]:
    """Validate device key. Returns (is_valid, error_message)."""
    if not raw:
        return False, "Key cannot be empty"
    if " " in raw:
        return False, "Key cannot contain spaces"
    if raw != current_key and raw in existing_keys:
        return False, f"Key '{raw}' already exists"
    return True, ""
```

## Patterns to Follow

### Pattern 1: Config Screen Loop (from existing `_config_screen`)

The existing global config screen establishes the exact pattern:

1. `while True:` loop
2. Load current state from registry
3. `clear_screen()` + render action divider + render panel
4. `_getch()` for setting number
5. Dispatch by setting type (toggle/text/numeric/path)
6. Validate with reject-and-reprompt, save, loop

Device config replicates this 1:1 with `DeviceEntry` instead of `GlobalConfig`.

### Pattern 2: Action Handler Signature

All TUI actions follow the same signature and return pattern:

```python
def _action_config_device(registry, out, device_key: str) -> tuple[str, str]:
    """Returns (status_message, status_level)."""
    try:
        _device_config_screen(registry, out, device_key)
        return ("Device config saved", "success")
    except KeyboardInterrupt:
        return ("Config: cancelled", "warning")
    except Exception as exc:
        return (f"Config: {exc}", "error")
```

### Pattern 3: Registry Load-Modify-Save

All registry mutations follow load -> modify -> save through `Registry.save()` which calls `_atomic_write_json`. The new `update_device` method follows this same pattern with a single `save()` call for atomicity.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Cross-Module Imports

**What:** Having screen.py import from registry.py or config.py directly.
**Why bad:** Violates hub-and-spoke. Creates coupling.
**Instead:** tui.py orchestrates. screen.py receives data, returns strings. registry.py persists.

### Anti-Pattern 2: Key Rename as Two Separate Save Operations

**What:** Calling `registry.remove(old)` then `registry.add(new)` as separate method calls.
**Why bad:** Each calls `save()` internally. If process dies between remove and add, device is lost.
**Instead:** Single `update_device` method that does both in one `load()` + modify + `save()` cycle.

### Anti-Pattern 3: Editing Serial Pattern Freely

**What:** Letting users type arbitrary serial patterns via free-text input.
**Why bad:** Invalid patterns break device matching silently. The pattern is auto-generated from USB discovery during `cmd_add_device` and follows a specific glob format.
**Instead:** Display serial pattern as **read-only** info in the config screen. If the user needs to change it, they remove and re-add the device.

### Anti-Pattern 4: Tracking Key Rename State Across Loop Iterations

**What:** Passing the "current key" through the loop by mutation and losing track.
**Why bad:** After a key rename, `device_key` variable is stale. Next iteration would fail to load.
**Instead:** When key is renamed, update the local `device_key` variable immediately. The `while True` loop re-loads from registry at the top of each iteration using the current key.

## Key Design Decision: Serial Pattern Editability

The serial pattern is auto-generated from USB discovery during `cmd_add_device`. Allowing free-text editing creates risk of broken patterns. **Recommendation:** Display serial pattern as read-only info in the config screen (type `"readonly"`). This means 5 editable fields + 1 display-only field.

## Main Menu Integration

Current actions use keys: F, A, R, D, C, B, Q.

| Key | Rationale |
|-----|-----------|
| **E** | "Edit device" - distinct from C (Config/global settings), intuitive |

**Recommendation:** Use **E** for "Edit Device". Update `ACTIONS` list in `screen.py` and dispatch in `run_menu`.

```python
# screen.py ACTIONS becomes:
ACTIONS: list[tuple[str, str]] = [
    ("F", "Flash Device"),
    ("A", "Add Device"),
    ("E", "Edit Device"),      # NEW
    ("R", "Remove Device"),
    ("D", "Refresh Devices"),
    ("C", "Config"),
    ("B", "Flash All"),
    ("Q", "Quit"),
]
```

The `run_menu` unknown-key message updates from `F/A/R/D/C/B/Q` to `F/A/E/R/D/C/B/Q`.

## Suggested Build Order

Build in dependency order. Each step is independently testable on the Pi via SSH.

1. **registry.py: `update_device`** - Foundation. Everything else calls this.
2. **config.py: `rename_config_cache`** - Needed before key editing works.
3. **validation.py: `validate_device_key`** - Needed before TUI can accept key input.
4. **screen.py: `DEVICE_SETTINGS` + `render_device_config_screen`** - Rendering layer. Can be tested by calling directly.
5. **tui.py: `_device_config_screen`** - Interaction loop, wires everything together.
6. **tui.py: `run_menu` dispatch + screen.py `ACTIONS`** - Menu integration (new "E" key).

### Dependency Graph

```
registry.update_device (step 1)
    ^
    |
config.rename_config_cache (step 2) --+
    ^                                  |
    |                                  |
validation.validate_device_key (step 3)|
    ^                                  |
    |                                  |
screen.render_device_config_screen (step 4)
    ^                                  |
    |                                  |
tui._device_config_screen (step 5) ---+
    ^
    |
tui.run_menu "E" key (step 6)
```

## Sources

- Direct codebase analysis of all modules in `C:/dev_projects/kalico_flash/kflash/`
- Existing patterns from `_config_screen`, `_action_flash_device`, `_action_remove_device` in tui.py
- Registry CRUD patterns from registry.py
- Config cache path logic from config.py `get_config_dir`
