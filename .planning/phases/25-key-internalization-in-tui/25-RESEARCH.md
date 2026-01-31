# Phase 25: Key Internalization in TUI - Research

**Researched:** 2026-02-01
**Domain:** Python TUI refactoring (internal codebase changes only)
**Confidence:** HIGH

## Summary

This phase requires surgical edits across 3-4 files to hide device keys from users. The codebase is well-understood since all changes are internal. No external libraries or new patterns are needed.

The work breaks into two clear tasks: (1) rewire the add-device wizard to auto-generate keys via `generate_device_key()` instead of prompting, and (2) replace `entry.key` with `entry.name` in all user-facing output and remove the key edit option from the device config screen.

**Primary recommendation:** Modify `cmd_add_device()` in flash.py and `DEVICE_SETTINGS` / `_device_config_screen()` in screen.py/tui.py. Audit all user-facing strings for key leakage.

## Standard Stack

Not applicable -- this is a pure internal refactoring using Python stdlib only. No new dependencies.

## Architecture Patterns

### Current Add-Device Flow (flash.py:cmd_add_device, lines 1635-2003)

The wizard currently has this sequence:
1. Discovery/selection (lines 1660-1778)
2. Check existing registration (lines 1780-1792)
3. Global config first-run (lines 1796-1808)
4. **Key prompt** (lines 1813-1827) -- REMOVE THIS
5. Display name prompt (lines 1834-1837)
6. MCU auto-detection (lines 1841-1854)
7. Serial pattern (lines 1856-1882)
8. Flash method (lines 1887-1913)
9. Exclude from flash (lines 1917-1919)
10. Create DeviceEntry and save (lines 1923-1933)

**Required change:** Delete step 4 entirely. After step 5 (display name), call `generate_device_key(display_name, registry)` to produce the key silently. Reorder so name comes before key generation.

### Current Device Config Screen (tui.py:_device_config_screen, lines 768-941)

`DEVICE_SETTINGS` in screen.py (lines 479-490) has 5 entries:
1. `name` (text edit)
2. `key` (text edit with validation) -- REMOVE THIS
3. `flash_method` (cycle)
4. `flashable` (toggle)
5. `menuconfig` (action)

The `_device_config_screen` handler in tui.py (lines 823-938) dispatches on key indices 1-5. After removing entry 2, re-index to 1-4.

### Key Leakage Audit

Places where `entry.key` or `device_key` appears in user-facing strings:

**flash.py:**
- Line 307: `cmd_build` -- `"Cached config for '{device_key}'"` (internal log, acceptable)
- Line 344: `_action_flash_device` -- `f"Flash: failed for {device_key}"` -- CHANGE to `entry.name`
- Line 440: `_action_remove_device` -- `f"Removed device '{device_key}'"` -- CHANGE to `entry.name`
- Line 509: `cmd_flash` duplicate USB display -- `entry.key` in display -- CHANGE
- Line 566: `cmd_list_devices` -- `f"{entry.key}: {entry.name} ({entry.mcu})"` -- CHANGE to just name
- Line 580: excluded devices display -- `entry.key` -- CHANGE
- Line 608: flashable device list -- `entry.key` -- CHANGE
- Line 1124: flash_all blocked -- `entry.name ({entry.key})` -- CHANGE to just name
- Line 1172: flash_all config ages -- `entry.name ({entry.key})` -- CHANGE
- Line 1219/1222: flash_all version -- `entry.name ({entry.key})` -- CHANGE
- Line 1407: `cmd_remove_device` confirm -- shows key -- CHANGE
- Line 1412: remove success -- shows key -- CHANGE
- Line 1816: key prompt text -- REMOVE
- Line 1824: duplicate key warning -- N/A (prompt removed)
- Line 1933: add success -- `f"Registered '{device_key}' ({display_name})"` -- CHANGE

**tui.py:**
- Line 299: `_prompt_device_number` returns `row.key` (internal, OK)
- Line 342: `_action_flash_device` -- `entry.name if entry else device_key` (already uses name for success)
- Line 344: `_action_flash_device` failure -- `device_key` -- CHANGE to name

**output.py:**
- Line 103: `mcu_mismatch_choice` -- `device '{device_key}'` -- CHANGE to name

**screen.py:**
- `DEVICE_SETTINGS` line 481 -- key edit entry -- REMOVE

### Duplicate Name Detection

CONTEXT.md specifies case-insensitive duplicate name check. Currently there's no such check. Need to add:
```python
existing_names = [e.name.lower() for e in registry.load().devices.values()]
if display_name.lower() in existing_names:
    # reject and re-prompt
```

### Name Truncation in Bracketed Output

CONTEXT.md specifies 20-char truncation with `...` for bracketed output contexts (e.g. `[Octopus Pro v1.1] Building...`). Currently flash output uses `entry.name` in some places but not consistently with truncation. Need a helper:
```python
def _truncate_name(name: str, max_len: int = 20) -> str:
    if len(name) <= max_len:
        return name
    return name[:max_len - 3] + "..."
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Slug generation | Custom slugifier | `generate_device_key()` from Phase 24 | Already implemented with collision handling |
| Case-insensitive comparison | Custom logic | `str.lower()` comparison | Simple, sufficient |

## Common Pitfalls

### Pitfall 1: Missed Key References
**What goes wrong:** A `device_key` or `entry.key` leaks into user-facing output somewhere not caught in the audit.
**How to avoid:** After implementation, grep for `entry\.key`, `device_key`, `\.key\b` in all output/display contexts and verify each is either internal-only or replaced.
**Warning signs:** User sees a slug like `octopus-pro-v1-1` instead of `Octopus Pro v1.1`.

### Pitfall 2: Device Config Screen Index Shift
**What goes wrong:** After removing the "key" entry from `DEVICE_SETTINGS`, the key handler in `_device_config_screen` still dispatches on old indices (1-5 instead of 1-4).
**How to avoid:** Update the key range check from `("1", "2", "3", "4", "5")` to `("1", "2", "3", "4")` and verify each index maps correctly.

### Pitfall 3: _save_device_edits Key Rename Logic
**What goes wrong:** `_save_device_edits` in tui.py has key-rename logic (lines 734-765) that moves cache dirs and rewrites registry. With key editing removed, this code becomes dead but harmless. Could confuse future maintainers.
**How to avoid:** Remove the `new_key` branch from `_save_device_edits` since key editing is no longer possible. Or leave it as defensive code -- either is acceptable.

### Pitfall 4: ValueError from generate_device_key
**What goes wrong:** If display name is all special characters (e.g., "!!!"), `generate_device_key` raises `ValueError`.
**How to avoid:** Catch `ValueError` in the add-device wizard and re-prompt with an error message.

### Pitfall 5: CLI --device Flag Still Uses Keys
**What goes wrong:** The `--device KEY` CLI flag still needs internal keys to work. Don't break this.
**How to avoid:** Keys remain functional internally. The `--device` flag continues accepting keys. Only user-facing *output* changes. The argparse help text says "Device key" -- could change to just "Device identifier" but this is optional.

## Code Examples

### Replacing key prompt with auto-generation (flash.py:cmd_add_device)

Current steps 4-5 (lines 1813-1837):
```python
# Step 4: Device key  -- DELETE THIS BLOCK
device_key = None
for _attempt in range(3):
    key_input = out.prompt("Device key (used with --device flag, e.g., 'octopus-pro')")
    ...

# Step 5: Display name
display_name = out.prompt("Display name (e.g., 'Octopus Pro v1.1')")
```

Replace with:
```python
# Step 4: Display name (with duplicate check)
from .validation import generate_device_key

display_name = None
for _attempt in range(3):
    name_input = out.prompt("Display name (e.g., 'Octopus Pro v1.1')")
    if not name_input:
        out.warn("Display name cannot be empty.")
        continue
    # Case-insensitive duplicate check
    existing_names = {e.name.lower() for e in registry_data.devices.values()}
    if name_input.lower() in existing_names:
        out.warn(f"You already have a device named '{name_input}'. Enter a different name.")
        continue
    display_name = name_input
    break

if display_name is None:
    out.error("Too many invalid inputs.")
    return 1

# Auto-generate key silently
try:
    device_key = generate_device_key(display_name, registry)
except ValueError:
    out.error("Display name must contain at least one letter or number.")
    return 1
```

### Removing key from DEVICE_SETTINGS (screen.py)

Current:
```python
DEVICE_SETTINGS: list[dict] = [
    {"key": "name", "label": "Display name", "type": "text"},
    {"key": "key", "label": "Device key", "type": "text"},        # REMOVE
    {"key": "flash_method", ...},
    {"key": "flashable", ...},
    {"key": "menuconfig", ...},
]
```

After:
```python
DEVICE_SETTINGS: list[dict] = [
    {"key": "name", "label": "Display name", "type": "text"},
    {"key": "flash_method", ...},
    {"key": "flashable", ...},
    {"key": "menuconfig", ...},
]
```

### Updating _device_config_screen key range (tui.py)

Change `("1", "2", "3", "4", "5")` to `("1", "2", "3", "4")` and remove the `elif setting["key"] == "key"` handler block (lines 837-851).

## Open Questions

1. **CLI --device flag help text:** Currently says "Device key to build and flash". Should this be updated to say "Device identifier"? The key is still needed for CLI usage but users won't know their keys anymore since they're auto-generated. Users could look in devices.json or we could add a `--list-keys` flag. This is a minor UX gap but not blocking for Phase 25.
   - Recommendation: Leave as-is for now. Power users who use CLI flags can check devices.json. A future phase could add name-based device lookup.

2. **cmd_remove_device by key vs name:** `--remove-device` currently takes a key. With keys hidden, users won't know what key to type. The TUI remove flow uses device numbers so it's fine there.
   - Recommendation: Not in scope for Phase 25 (TUI-only changes). CLI ergonomics can be addressed in a future phase.

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection of all `.py` files in `kflash/` directory
- Phase 24 implementation: `kflash/validation.py:generate_device_key()` (verified present)
- Phase 25 CONTEXT.md decisions (user-locked)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no external dependencies, pure stdlib
- Architecture: HIGH - direct codebase inspection, all touch points identified
- Pitfalls: HIGH - exhaustive grep-based audit of key references

**Research date:** 2026-02-01
**Valid until:** 2026-03-01 (stable internal codebase, no external dependencies)
