# Phase 18: Foundation & Screen - Research

**Researched:** 2026-01-31
**Domain:** Device config screen backend and rendering
**Confidence:** HIGH

## Summary

Phase 18 establishes the backend persistence layer and screen rendering for device configuration editing. The codebase already has all required primitives: atomic registry updates (`registry.py`), panel rendering (`panels.py`), two-panel screen layout pattern (Phase 13 config screen), and config cache directory management (`config.py`).

The primary work is: (1) add `Registry.update_device()` method for atomic device updates, (2) create device key validation function to reject duplicates/invalid characters, (3) add config cache rename helper for key changes, (4) define `DEVICE_SETTINGS` list following the `SETTINGS` pattern from Phase 13, (5) create `render_device_config_screen()` following the two-panel layout from `render_config_screen()`.

This is pure composition work - no new patterns, libraries, or architectural decisions. Everything follows established Phase 11-13 patterns for panel-based TUI screens.

**Primary recommendation:** Extend existing modules (`registry.py`, `validation.py`, `config.py`, `screen.py`) with device-specific methods that mirror their global config equivalents. No new modules needed.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib | 3.9+ | All operations | Project constraint: no external deps |
| `dataclasses` | stdlib | DeviceEntry already exists | Established pattern |
| `os.rename` / `shutil.move` | stdlib | Config cache directory rename | Filesystem operations |
| `re` | stdlib | Key validation (character class checks) | Pattern matching for invalid chars |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `tempfile` | stdlib | Atomic registry writes | Already used in `_atomic_write_json` |
| `os.path` | stdlib | Config cache directory operations | Path manipulation for rename |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `re` for key validation | Manual string iteration | Regex is clearer for character class checks (`[a-z0-9-_]`) |
| `shutil.move` for cache rename | `os.rename` + fallback | `shutil.move` handles cross-filesystem moves automatically |

## Architecture Patterns

### Pattern 1: Registry Update Method (Mirror save_global)
**What:** Add `Registry.update_device(key, **updates)` that loads registry, modifies one device entry in-place, and atomically saves. Mirrors the existing `Registry.save_global()` pattern.
**When to use:** When editing device properties from the config screen.
**Example:**
```python
def update_device(self, key: str, **updates) -> bool:
    """Update device entry fields atomically. Returns False if device not found."""
    registry = self.load()
    if key not in registry.devices:
        return False

    entry = registry.devices[key]
    # Update fields via dataclass replace
    for field, value in updates.items():
        if hasattr(entry, field):
            setattr(entry, field, value)

    registry.devices[key] = entry
    self.save(registry)
    return True
```

### Pattern 2: Key Validation Function (Similar to validate_path_setting)
**What:** Validation function that checks device key format and uniqueness. Returns `(is_valid, error_message)` tuple following the pattern from `validation.py`.
**When to use:** Before saving a renamed device key.
**Example:**
```python
def validate_device_key(key: str, registry, current_key: str = None) -> tuple[bool, str]:
    """Validate device key format and uniqueness.

    Args:
        key: Proposed device key.
        registry: Registry instance for uniqueness check.
        current_key: Current key (for rename case - ignore self-match).

    Returns:
        (is_valid, error_message)
    """
    if not key:
        return False, "Device key cannot be empty"

    if not re.match(r'^[a-z0-9][a-z0-9_-]*$', key):
        return False, "Key must start with letter/digit, contain only lowercase letters, digits, hyphens, underscores"

    if current_key and key == current_key:
        return True, ""  # Renaming to same key is valid (no-op)

    if registry.get(key) is not None:
        return False, f"Device '{key}' already registered"

    return True, ""
```

### Pattern 3: Config Cache Rename Helper
**What:** Function that renames a device's config cache directory when the device key changes. Uses atomic operations - check old exists, create new parent, move directory, verify new exists.
**When to use:** After successful key rename in registry, before screen returns.
**Example:**
```python
def rename_device_config_cache(old_key: str, new_key: str) -> bool:
    """Rename config cache directory when device key changes.

    Returns True if renamed, False if no cache existed.
    """
    from pathlib import Path
    import shutil

    old_dir = get_config_dir(old_key)
    new_dir = get_config_dir(new_key)

    if not old_dir.exists():
        return False  # No cached config to rename

    # Ensure parent directory exists
    new_dir.parent.mkdir(parents=True, exist_ok=True)

    # Move directory atomically
    shutil.move(str(old_dir), str(new_dir))

    return True
```

### Pattern 4: Two-Panel Device Config Screen (Follows render_config_screen)
**What:** Render function that produces identity panel (read-only) + editable fields panel (numbered). Follows exact pattern from Phase 13's `render_config_screen()`.
**When to use:** Device config screen rendering.
**Example:**
```python
DEVICE_SETTINGS = [
    {"key": "name", "label": "Display name", "type": "text"},
    {"key": "key", "label": "Device key", "type": "text"},
    {"key": "flash_method", "label": "Flash method", "type": "cycle"},
    {"key": "flashable", "label": "Include in flash operations", "type": "toggle"},
    {"key": "menuconfig", "label": "Edit firmware config", "type": "action"},
]

def render_device_config_screen(device_entry: DeviceEntry) -> str:
    """Render device config screen with identity + settings panels."""
    theme = get_theme()

    # Identity panel (read-only)
    identity_lines = [
        f"{theme.label}MCU Type:{theme.reset} {theme.value}{device_entry.mcu}{theme.reset}",
        f"{theme.label}Serial Pattern:{theme.reset} {theme.subtle}{device_entry.serial_pattern}{theme.reset}",
    ]
    identity_panel = render_panel("device identity", identity_lines)

    # Settings panel (editable, numbered)
    settings_lines = []
    for i, setting in enumerate(DEVICE_SETTINGS, 1):
        value = getattr(device_entry, setting["key"], None)
        if setting["type"] == "toggle":
            display = "ON" if value else "OFF"
        elif setting["type"] == "cycle":
            display = value or "default"
        elif setting["type"] == "action":
            display = ""
        else:
            display = str(value)

        label = f"{theme.label}{i}.{theme.reset} {theme.text}{setting['label']}:{theme.reset}"
        if display:
            label += f" {theme.value}{display}{theme.reset}"
        settings_lines.append(label)

    settings_panel = render_panel("settings", settings_lines)

    return "\n\n".join([identity_panel, settings_panel])
```

### Pattern 5: DEVICE_SETTINGS List Definition
**What:** List of setting definitions (key, label, type) that drives both rendering and editing. Mirrors `SETTINGS` from Phase 13.
**When to use:** Always for device config screen.
**Structure:**
```python
DEVICE_SETTINGS: list[dict] = [
    {"key": "name", "label": "Display name", "type": "text"},
    {"key": "key", "label": "Device key", "type": "text"},
    {"key": "flash_method", "label": "Flash method", "type": "cycle", "values": [None, "katapult", "make_flash"]},
    {"key": "flashable", "label": "Include in flash operations", "type": "toggle"},
    {"key": "menuconfig", "label": "Edit firmware config", "type": "action"},
]
```

### Anti-Patterns to Avoid
- **Per-field save:** Phase 13 pattern collects edits in memory and saves on screen exit. Don't save after each field edit.
- **New module for device config:** All code composes into existing `screen.py`, `tui.py`, `registry.py`, `validation.py`, `config.py`.
- **Separate validation module:** Device key validation goes in `validation.py` alongside path/numeric validation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Panel rendering | Custom box drawing for device screen | `panels.render_panel()` | Already exists, themed, consistent with global config screen |
| Atomic registry save | Custom temp file logic | `Registry.save()` calls `_atomic_write_json` | Existing pattern with fsync, handles failures |
| Device entry lookup | Manual dict access | `Registry.get(key)` | Returns None for missing keys, cleaner |
| Config cache path | Manual path construction | `config.get_config_dir(device_key)` | Respects XDG_CONFIG_HOME, consistent |

## Common Pitfalls

### Pitfall 1: Key Rename Ordering (Partial State Corruption)
**What goes wrong:** If you rename the key in registry first, then fail to rename config cache, the device exists under new key but config still lives under old key path.
**Why it happens:** Atomic registry save completes before filesystem operation, leaving mismatched state.
**How to avoid:** Order: validate new key → rename config cache → atomic registry save. If cache rename fails, abort before registry update.
**Warning signs:** Device exists with new key but `has_cached_config()` returns False after rename.

### Pitfall 2: Empty/Whitespace Keys Passing Validation
**What goes wrong:** User enters spaces or empty string, validation accepts it, registry save succeeds but key is unusable.
**Why it happens:** Forgot to check `.strip()` or test for empty after stripping.
**How to avoid:** Validate after stripping whitespace: `key = key.strip()` then `if not key: return False, "empty"`.
**Warning signs:** Device appears in registry but can't be selected via CLI `--device` flag.

### Pitfall 3: Invalid Characters in Device Keys
**What goes wrong:** User enters keys with spaces, slashes, special chars. Works initially but breaks CLI argument parsing or filesystem paths.
**Why it happens:** No character validation beyond space check (Phase 0 only rejects spaces).
**How to avoid:** Regex pattern `^[a-z0-9][a-z0-9_-]*$` - start with alphanumeric, allow lowercase letters/digits/hyphens/underscores only.
**Warning signs:** Key with uppercase letters breaks case-sensitive matching, slashes break config cache paths.

### Pitfall 4: Dataclass Immutability Assumptions
**What goes wrong:** Attempting `entry.name = new_name` on a DeviceEntry retrieved from registry doesn't persist.
**Why it happens:** DeviceEntry is a dataclass but registry.devices dict holds separate instances. Modifying instance doesn't update dict.
**How to avoid:** Always mutate via `registry.devices[key] = modified_entry` or use `Registry.update_device()` method which handles load-modify-save.
**Warning signs:** Changes appear to work in memory but don't persist to JSON after reload.

### Pitfall 5: Config Cache Path Cross-Filesystem Moves
**What goes wrong:** `os.rename()` fails with OSError when config cache dir is on different filesystem than new destination.
**Why it happens:** `os.rename()` is atomic but only works within same filesystem.
**How to avoid:** Use `shutil.move()` which handles cross-filesystem moves by falling back to copy+delete.
**Warning signs:** Key rename works in registry but config cache rename fails with OSError 18 (EXDEV: cross-device link).

## Code Examples

### Registry Update Method (registry.py)
```python
def update_device(self, key: str, **updates) -> bool:
    """Update device entry fields atomically.

    Args:
        key: Device key to update.
        **updates: Field names and values to update.

    Returns:
        True if updated, False if device not found.

    Example:
        registry.update_device("octopus-pro", name="New Name", flashable=False)
    """
    registry = self.load()
    if key not in registry.devices:
        return False

    entry = registry.devices[key]
    # Update fields via setattr (dataclass fields are mutable)
    for field, value in updates.items():
        if hasattr(entry, field):
            setattr(entry, field, value)

    registry.devices[key] = entry
    self.save(registry)
    return True
```

### Device Key Validation (validation.py)
```python
def validate_device_key(key: str, registry, current_key: str = None) -> tuple[bool, str]:
    """Validate device key format and uniqueness.

    Rules:
    - Not empty after stripping whitespace
    - Start with letter or digit
    - Contain only lowercase letters, digits, hyphens, underscores
    - Unique in registry (unless renaming to current key)

    Args:
        key: Proposed device key.
        registry: Registry instance for uniqueness check.
        current_key: Current device key (for rename - allows self-match).

    Returns:
        (is_valid, error_message) - error_message is empty string on success.
    """
    import re

    key = key.strip()

    if not key:
        return False, "Device key cannot be empty"

    # Character validation: lowercase alphanumeric + hyphen/underscore only
    if not re.match(r'^[a-z0-9][a-z0-9_-]*$', key):
        return False, "Key must start with letter/digit, use only lowercase letters, digits, hyphens, underscores"

    # Uniqueness check (skip if renaming to same key)
    if current_key and key == current_key:
        return True, ""

    if registry.get(key) is not None:
        return False, f"Device '{key}' already registered"

    return True, ""
```

### Config Cache Rename Helper (config.py)
```python
def rename_device_config_cache(old_key: str, new_key: str) -> bool:
    """Rename config cache directory when device key changes.

    Args:
        old_key: Current device key.
        new_key: New device key.

    Returns:
        True if cache directory was renamed, False if no cache existed.

    Raises:
        OSError: If filesystem operation fails.
    """
    import shutil

    old_dir = get_config_dir(old_key)
    new_dir = get_config_dir(new_key)

    if not old_dir.exists():
        return False  # No cached config to rename

    if new_dir.exists():
        # Target already exists (shouldn't happen with unique key validation)
        raise FileExistsError(f"Config cache for '{new_key}' already exists")

    # Ensure parent directory exists
    new_dir.parent.mkdir(parents=True, exist_ok=True)

    # Move directory (handles cross-filesystem moves)
    shutil.move(str(old_dir), str(new_dir))

    return True
```

### Device Settings Definition (screen.py)
```python
DEVICE_SETTINGS: list[dict] = [
    {"key": "name", "label": "Display name", "type": "text"},
    {"key": "key", "label": "Device key", "type": "text"},
    {"key": "flash_method", "label": "Flash method", "type": "cycle", "values": [None, "katapult", "make_flash"]},
    {"key": "flashable", "label": "Include in flash operations", "type": "toggle"},
    {"key": "menuconfig", "label": "Edit firmware config", "type": "action"},
]
```

### Device Config Screen Rendering (screen.py)
```python
def render_device_config_screen(device_entry: DeviceEntry) -> str:
    """Render device config screen with identity panel + editable settings panel.

    Follows two-panel pattern from render_config_screen():
    1. Identity panel (read-only): MCU type, serial pattern
    2. Settings panel (numbered): display name, key, flash method, flashable, menuconfig

    Args:
        device_entry: DeviceEntry to render.

    Returns:
        Multi-line string ready for print().
    """
    theme = get_theme()

    # Panel 1: Device Identity (read-only)
    identity_lines = [
        f"{theme.label}MCU Type:{theme.reset} {theme.value}{device_entry.mcu}{theme.reset}",
        f"{theme.label}Serial Pattern:{theme.reset} {theme.subtle}{device_entry.serial_pattern}{theme.reset}",
    ]
    identity_panel = render_panel("device identity", identity_lines)

    # Panel 2: Settings (editable, numbered)
    settings_lines = []
    for i, setting in enumerate(DEVICE_SETTINGS, 1):
        value = getattr(device_entry, setting["key"], None)

        # Format value based on type
        if setting["type"] == "toggle":
            display = "ON" if value else "OFF"
        elif setting["type"] == "cycle":
            display = value if value else "default"
        elif setting["type"] == "action":
            display = "\u25b8 Launch"  # ▸ Launch
        else:  # text
            display = str(value)

        # Build line: "1. Display name: Octopus Pro v1.1"
        line = f"{theme.label}{i}.{theme.reset} {theme.text}{setting['label']}:{theme.reset}"
        if display:
            line += f" {theme.value}{display}{theme.reset}"
        settings_lines.append(line)

    settings_panel = render_panel("settings", settings_lines)

    # Combine panels
    return "\n\n".join([identity_panel, settings_panel])
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual registry dict manipulation | `Registry.update_device()` method | Phase 18 | Atomic updates, consistent with `save_global()` pattern |
| Space-only key validation | Character class regex validation | Phase 18 | Prevents CLI argument parsing issues, filesystem path issues |
| `os.rename` for cache moves | `shutil.move` for cache moves | Phase 18 | Handles cross-filesystem moves safely |

## Open Questions

1. **Flash method cycle values order**
   - What we know: Device can use global default (None), katapult, or make_flash
   - What's unclear: What order should cycle present? None → katapult → make_flash or katapult → make_flash → None?
   - Recommendation: None → katapult → make_flash (default first, then explicit methods in priority order)

2. **Key rename with active flash operation**
   - What we know: Phase 18 is screen-only, no interaction loop yet
   - What's unclear: Should key rename be blocked if device is currently being flashed?
   - Recommendation: Out of scope for Phase 18. Phase 19 interaction handles this (TUI is single-threaded, flash blocks screen)

3. **Menuconfig action behavior**
   - What we know: Phase 18 is rendering only
   - What's unclear: Should menuconfig option be grayed out if no cached config exists?
   - Recommendation: Show with status indicator: "Edit firmware config (no cache)" vs "Edit firmware config (cached)"

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `registry.py`, `config.py`, `screen.py`, `tui.py`, `validation.py`, `models.py`, `panels.py`
- Phase 13 research and implementation (config screen pattern)
- Phase 13 CONTEXT.md (two-panel layout decision)
- v3.3 REQUIREMENTS.md (CDEV-01, CDEV-02, CDEV-03, KEY-01, SAVE-02, VIS-02)

### Secondary (MEDIUM confidence)
- Python `shutil.move()` cross-filesystem behavior - well-documented stdlib
- Regex character class patterns for validation - standard practice

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - stdlib only, all primitives exist in codebase
- Architecture: HIGH - follows established Phase 13 pattern exactly
- Pitfalls: HIGH - identified from key rename atomic ordering, existing add_device validation patterns
- Code examples: HIGH - directly adapted from working Phase 13 config screen code

**Research date:** 2026-01-31
**Valid until:** 2026-02-28 (stable domain, no external dependencies, well-established patterns)
