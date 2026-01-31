# Phase 19: Edit Interaction - Research

**Researched:** 2026-01-31
**Domain:** Terminal TUI interaction loop with collect-then-save editing
**Confidence:** HIGH

## Summary

Phase 19 adds interactive editing to the device config screen rendered in Phase 18. The codebase already has a complete, working analog: `_config_screen()` in `tui.py` (lines 597-694) which handles the global settings screen with single-keypress dispatch, toggle/numeric/path editing, and a render-read-dispatch loop.

The key difference is the **collect-then-save pattern** (SAVE-01): edits accumulate in a `dict` of pending changes rather than saving per-field. This dict is applied to the registry in a single atomic save on screen exit.

**Primary recommendation:** Model `_device_config_screen()` directly on `_config_screen()`, replacing per-field saves with a pending-changes dict that merges into the DeviceEntry on exit. Key rename requires special ordering: validate -> move cache dir -> atomic registry save with key change.

## Standard Stack

Not applicable -- Python 3.9+ stdlib only, no external dependencies. All building blocks exist in the codebase already.

## Architecture Patterns

### Pattern 1: Collect-Then-Save with Pending Changes Dict

**What:** Edits accumulate in `pending: dict[str, Any] = {}` keyed by field name. The screen renders from a "working copy" that overlays pending changes onto the original DeviceEntry. On exit (Esc/B), all pending changes are saved in one `registry.update_device()` call.

**When to use:** When multiple fields may be edited before committing, and you want to avoid partial saves.

**Implementation sketch:**
```python
def _device_config_screen(device_key: str, registry, out) -> None:
    pending: dict[str, Any] = {}
    original = registry.get(device_key)

    while True:
        # Build working copy by overlaying pending on original
        working = dataclasses.replace(original, **pending)

        clear_screen()
        print(render_device_config_screen(working))
        print("  Setting # (or Esc/B to save & return): ", end="", flush=True)

        key = _getch()

        if key in ("\x1b", "b", "\x03"):
            # Save all pending changes on exit
            if pending:
                _save_device_edits(device_key, pending, registry)
            return

        if key == "1":  # name (text, reject empty)
            _edit_text_field(pending, working, "name", "Display name", reject_empty=True)
        elif key == "2":  # key (text, validate uniqueness)
            _edit_key_field(pending, working, device_key, registry)
        elif key == "3":  # flash_method (cycle)
            _cycle_field(pending, working, "flash_method", [None, "katapult", "make_flash"])
        elif key == "4":  # flashable (toggle)
            pending["flashable"] = not working.flashable
        elif key == "5":  # menuconfig (action)
            _launch_menuconfig(working, registry)
```

### Pattern 2: Key Rename Save Ordering

**What:** Key rename is special because it changes the dict key in the registry, not just a field value. The save function must handle this distinctly.

**Ordering:**
1. Validate new key (format + uniqueness) -- already done during edit
2. Move config cache dir (`rename_device_config_cache(old_key, new_key)`)
3. Atomic registry update: load -> delete old key -> insert new key with all updates -> save

**Why this order:** If cache move fails, registry is unchanged (clean). If registry save fails after cache move, user has orphaned cache dir under new name but registry still points to old key -- recoverable by user.

```python
def _save_device_edits(original_key: str, pending: dict, registry) -> None:
    new_key = pending.pop("key", None)

    if new_key and new_key != original_key:
        # Move config cache first (can fail without corrupting registry)
        from .config import rename_device_config_cache
        rename_device_config_cache(original_key, new_key)

        # Atomic registry: load, delete old, insert new with updates
        data = registry.load()
        device = data.devices.pop(original_key)
        for field, value in pending.items():
            setattr(device, field, value)
        device.key = new_key
        data.devices[new_key] = device
        registry.save(data)
    elif pending:
        registry.update_device(original_key, **pending)
```

### Pattern 3: Cycle Field (Single Keypress)

**What:** Flash method cycles through `[None, "katapult", "make_flash"]` on each keypress. No prompt needed.

```python
def _cycle_field(pending, working, field, values):
    current = getattr(working, field)
    idx = values.index(current) if current in values else -1
    pending[field] = values[(idx + 1) % len(values)]
```

### Pattern 4: Text Input with Empty Rejection

**What:** For name editing, prompt for input, reject empty strings with error message and reprompt. Same pattern as path/numeric validation in `_config_screen` but simpler.

```python
def _edit_text_field(pending, working, field, label, reject_empty=False):
    current = getattr(working, field)
    while True:
        raw = input(f"  {label} [{current}]: ").strip()
        if not raw:
            break  # Keep current value
        if reject_empty and not raw:
            print("  Error: Cannot be empty")
            continue
        pending[field] = raw
        break
```

Note: The empty check after strip handles the edge case. If user enters spaces only, strip makes it empty, and empty input means "keep current" (standard pattern from `_config_screen`).

### Pattern 5: Menuconfig Action (Shell Out)

**What:** Option 5 launches `make menuconfig` for the device. This is an action, not an edit -- it shells out, then returns to the screen. Uses existing `ConfigManager` to load cached config, run menuconfig, save back.

This needs the klipper_dir from global config and the device key from the working copy.

### Anti-Patterns to Avoid

- **Save per field:** Would cause N disk writes for N edits and makes key rename non-atomic
- **Mutating original DeviceEntry:** Use `dataclasses.replace()` for working copy, keep original immutable
- **Key rename as delete+add:** Two registry operations = race condition window; use single load-modify-save cycle (KEY-03)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Key validation | Custom regex | `validate_device_key()` in validation.py | Already handles format + uniqueness + self-rename |
| Config cache move | Manual os.rename | `rename_device_config_cache()` in config.py | Handles cross-filesystem, existence checks |
| Atomic JSON save | Manual file write | `registry.save()` | Already uses temp+fsync+rename pattern |
| Single keypress read | Custom terminal handling | `_getch()` in tui.py | Already handles raw mode, escape sequences |

## Common Pitfalls

### Pitfall 1: Key Rename Updates device_key in Pending But Not Loop Variable

**What goes wrong:** After renaming key in pending dict, the loop variable `device_key` still holds the old key. If user edits more fields after renaming, subsequent save uses wrong key.
**How to avoid:** Key rename is stored in `pending["key"]` only. The save function reads it from pending. The loop always uses `original_key` (never changes). The working copy shows the new key via `dataclasses.replace()`.

### Pitfall 2: Menuconfig Needs Current Key, Not Pending Key

**What goes wrong:** If user renamed key in pending but hasn't saved yet, menuconfig needs to use the *original* key for config cache lookup (cache hasn't been renamed yet).
**How to avoid:** Pass `original_key` (not `working.key`) to ConfigManager for menuconfig.

### Pitfall 3: Empty String vs No Input for Text Fields

**What goes wrong:** User presses Enter with no input -- this should mean "keep current value" (cancel edit), not "set to empty string."
**How to avoid:** Check `if not raw: break` before any validation. Only reach rejection logic if user typed something.

### Pitfall 4: Config Cache Move Fails After Validation

**What goes wrong:** Key was validated as unique, but between validation and save, cache dir for new key appeared (unlikely but possible).
**How to avoid:** `rename_device_config_cache` raises `FileExistsError` -- catch it and show error, don't save to registry.

### Pitfall 5: Ctrl+C During Edit Should Not Lose All Pending Changes

**What goes wrong:** User presses Ctrl+C during text input prompt -- pending changes lost.
**How to avoid:** Wrap input() in try/except (EOFError, KeyboardInterrupt). On interrupt, break out of input but stay in main loop with pending changes preserved. Only discard on explicit Esc/B from main loop. This matches the existing `_config_screen` pattern.

## Code Examples

### Existing Pattern: _config_screen Toggle (tui.py:648-651)
```python
if setting["type"] == "toggle":
    new_gc = dataclasses.replace(gc, **{field_key: not current})
    registry.save_global(new_gc)
```
Phase 19 equivalent (no immediate save):
```python
if setting["type"] == "toggle":
    pending["flashable"] = not working.flashable
```

### Existing Pattern: _config_screen Text Input (tui.py:674-693)
```python
print(key)
while True:
    try:
        raw = input(f"  {setting['label']} [{current}]: ").strip()
    except (EOFError, KeyboardInterrupt):
        raw = ""
        break
    if not raw:
        break
    ok, err = validate_path_setting(raw, field_key)
    if ok:
        new_gc = dataclasses.replace(gc, **{field_key: raw})
        registry.save_global(new_gc)
        break
    else:
        print(f"  {theme.error}{err}{theme.reset}")
```

### Existing: validate_device_key (validation.py:55-82)
```python
def validate_device_key(key, registry, current_key=None):
    # Returns (is_valid, error_message)
    # Handles: empty, format regex, self-rename, uniqueness
```

### Existing: rename_device_config_cache (config.py:30-48)
```python
def rename_device_config_cache(old_key, new_key):
    # Returns True if moved, False if no cache
    # Raises FileExistsError if new_key cache exists
```

### Existing: Registry.update_device (registry.py:143-156)
```python
def update_device(self, key, **updates):
    # Load-modify-save atomic pattern
    # Does NOT handle key rename (only field updates)
```

## State of the Art

No external changes -- this is internal codebase evolution. All building blocks were created in Phase 18.

## Open Questions

1. **Should Ctrl+C from main loop discard or save pending changes?**
   - Current `_config_screen` returns on Ctrl+C (no save since it saves per-field)
   - Recommendation: Discard on Ctrl+C (escape hatch), save on Esc/B (intentional exit). This is the most intuitive behavior.

2. **Should menuconfig update the device_key tracker if key was renamed in pending?**
   - Recommendation: No. Use original_key for menuconfig since cache hasn't been renamed yet. Document this clearly in code comments.

## Sources

### Primary (HIGH confidence)
- `C:\dev_projects\kalico_flash\kflash\tui.py` lines 597-694 -- existing `_config_screen` pattern
- `C:\dev_projects\kalico_flash\kflash\screen.py` lines 461-513 -- DEVICE_SETTINGS and render_device_config_screen
- `C:\dev_projects\kalico_flash\kflash\registry.py` lines 143-156 -- update_device method
- `C:\dev_projects\kalico_flash\kflash\validation.py` lines 55-82 -- validate_device_key
- `C:\dev_projects\kalico_flash\kflash\config.py` lines 30-48 -- rename_device_config_cache
- `C:\dev_projects\kalico_flash\kflash\models.py` lines 23-32 -- DeviceEntry dataclass

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- stdlib only, no external deps
- Architecture: HIGH -- direct analog exists in `_config_screen`, all building blocks from Phase 18 verified in code
- Pitfalls: HIGH -- derived from reading actual codebase patterns and identifying divergence points

**Research date:** 2026-01-31
**Valid until:** 2026-03-31 (stable internal codebase patterns)
