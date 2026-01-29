# Phase 13: Config Screen & Settings - Research

**Researched:** 2026-01-29
**Domain:** TUI settings screen, registry persistence, countdown timer
**Confidence:** HIGH

## Summary

This phase adds a dedicated config screen to the TUI and a post-command countdown timer. The codebase already has all the building blocks: panel rendering (`panels.py`), screen composition (`screen.py`), single-keypress input (`tui.py::_getch`), registry persistence (`registry.py`), and a working settings submenu (`tui.py::_settings_menu`) that will be replaced.

The primary work is: (1) extend `GlobalConfig` with 4 new fields, (2) build a config screen using existing panel primitives, (3) implement inline editing for toggle/numeric/path types, (4) add a countdown timer function using `_getch` with `select`/timeout, (5) wire countdown into action dispatch.

**Primary recommendation:** Reuse existing panel renderer and `_getch` for config screen; extend `GlobalConfig` dataclass and registry serialization for new settings; implement countdown as a standalone function called after action handlers return.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib | 3.9+ | Everything | Project constraint: no external deps |
| `dataclasses` | stdlib | GlobalConfig extension | Existing pattern |
| `time.monotonic` | stdlib | Countdown timer | Already used in `wait_for_device` |
| `select` (Unix) / `msvcrt` (Win) | stdlib | Non-blocking keypress during countdown | Platform-native timeout input |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `select.select` for timeout | `threading.Timer` | Threading adds complexity; select is simpler for single-key polling |

## Architecture Patterns

### Pattern 1: Config Screen as Separate Screen Function
**What:** A `_config_screen(registry, out)` function following the same pattern as the main menu loop — clear screen, render panels, read keypress, dispatch, loop.
**When to use:** Always — matches existing `_settings_menu` pattern but with panel rendering.
**Example:**
```python
def _config_screen(registry, out) -> None:
    while True:
        clear_screen()
        print()
        print(_render_config_screen(registry))
        print()
        print(f"  {theme.prompt}Setting # (or Esc/B to return):{theme.reset} ", end="", flush=True)
        key = _getch()
        if key in ("\x1b", "b"):
            return
        # dispatch to setting editor based on key
```

### Pattern 2: GlobalConfig Extension with Backward-Compatible Deserialization
**What:** Add new fields to `GlobalConfig` with defaults. Registry `load()` uses `.get()` with defaults so old JSON files work without migration.
**When to use:** Always for adding new settings.
**Example:**
```python
@dataclass
class GlobalConfig:
    klipper_dir: str = "~/klipper"
    katapult_dir: str = "~/katapult"
    default_flash_method: str = "katapult"
    allow_flash_fallback: bool = True
    # New Phase 13 fields
    skip_menuconfig: bool = False
    stagger_delay: float = 2.0
    return_delay: float = 5.0
    config_cache_dir: str = "~/.config/kalico-flash/configs"
```

### Pattern 3: Countdown Timer with Keypress Cancel
**What:** Display a countdown line, polling for keypress each second. On Unix, use `select.select` with 1s timeout on stdin. On Windows, use `msvcrt.kbhit()` polling with `time.sleep` intervals.
**When to use:** After flash, flash-all, add-device, remove-device actions.
**Example:**
```python
def _countdown_return(seconds: float) -> None:
    """Display countdown, any keypress skips immediately."""
    import time
    theme = get_theme()
    remaining = int(seconds)
    while remaining > 0:
        print(f"\r  {theme.subtle}Returning to menu in {remaining}s... (press any key){theme.reset}  ", end="", flush=True)
        if _wait_for_key(timeout=1.0):
            break
        remaining -= 1
    print()  # clear line
```

### Pattern 4: Setting Type Dispatch
**What:** Each setting has a type (toggle, numeric, path) that determines its edit behavior. Toggle flips on keypress. Numeric and path require line input.
**When to use:** Config screen edit dispatch.
**Example:**
```python
SETTINGS = [
    {"key": "skip_menuconfig", "label": "Skip menuconfig", "type": "toggle"},
    {"key": "stagger_delay", "label": "Stagger delay (seconds)", "type": "numeric"},
    {"key": "return_delay", "label": "Return delay (seconds)", "type": "numeric"},
    {"key": "klipper_dir", "label": "Klipper directory", "type": "path"},
    {"key": "katapult_dir", "label": "Katapult directory", "type": "path"},
    {"key": "config_cache_dir", "label": "Config cache directory", "type": "path"},
]
```

### Anti-Patterns to Avoid
- **Separate config file:** Settings must go in the existing `devices.json` global section, not a new file.
- **Confirmation dialog after each change:** Context says "instant redraw, no confirmation flash."
- **Grouped/tabbed settings:** Context says flat numbered list, no sections.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Panel rendering | Custom box drawing | `panels.render_panel()` | Already exists, themed, ANSI-aware |
| Screen clearing | Manual escape codes | `theme.clear_screen()` | Cross-platform, already exists |
| Single keypress | Custom terminal raw mode | `tui._getch()` | Already handles Windows/Unix |
| Atomic JSON writes | Manual file I/O | `registry.save()` / `registry.save_global()` | Already handles temp+fsync+rename |

## Common Pitfalls

### Pitfall 1: Raw Mode Breaks Line Input
**What goes wrong:** After `_getch()` sets raw mode, if you need `input()` for path editing, terminal may be in wrong state.
**Why it happens:** `_getch` restores terminal settings, but only on Unix. Need to ensure terminal is in cooked mode before calling `input()`.
**How to avoid:** For path/numeric settings that need typed input, switch to `input()` (which works in cooked mode) after detecting the setting number via `_getch`. The existing code in `_prompt_device_number` already does this pattern successfully.
**Warning signs:** Characters not echoing, Enter not working during path input.

### Pitfall 2: Escape Key Detection in Raw Mode
**What goes wrong:** Escape key (`\x1b`) is also the start of ANSI escape sequences (arrow keys, etc.). Reading just one byte may conflict.
**Why it happens:** Arrow keys send multi-byte sequences starting with `\x1b`.
**How to avoid:** After reading `\x1b`, either treat it as Escape immediately (simple, current `_getch` returns single char) or peek for additional bytes with a short timeout. The simple approach (Esc = immediate return) is fine for this use case since arrow keys aren't needed.
**Warning signs:** Arrow keys causing unexpected screen exits.

### Pitfall 3: Registry Backward Compatibility
**What goes wrong:** Adding new fields to GlobalConfig breaks old registry files that lack those keys.
**Why it happens:** Deserialization expects fields that don't exist in old JSON.
**How to avoid:** `registry.load()` already uses `dict.get()` with defaults for all GlobalConfig fields. New fields must follow the same pattern — add `.get("new_field", default)` in the load method.
**Warning signs:** KeyError or missing attribute on GlobalConfig after loading old registry.

### Pitfall 4: Countdown on Windows vs Unix
**What goes wrong:** `select.select()` doesn't work on stdin on Windows.
**Why it happens:** Windows doesn't support selecting on file descriptors the same way.
**How to avoid:** Use `msvcrt.kbhit()` on Windows (poll in a loop with short sleeps), `select.select` on Unix. Mirror the platform branching already in `_getch`.
**Warning signs:** Countdown blocks forever on Windows, or `select` raises an error.

## Code Examples

### Extending GlobalConfig (models.py)
```python
@dataclass
class GlobalConfig:
    klipper_dir: str = "~/klipper"
    katapult_dir: str = "~/katapult"
    default_flash_method: str = "katapult"
    allow_flash_fallback: bool = True
    skip_menuconfig: bool = False
    stagger_delay: float = 2.0
    return_delay: float = 5.0
    config_cache_dir: str = "~/.config/kalico-flash/configs"
```

### Registry Load Extension (registry.py)
```python
global_config = GlobalConfig(
    klipper_dir=global_raw.get("klipper_dir", "~/klipper"),
    katapult_dir=global_raw.get("katapult_dir", "~/katapult"),
    default_flash_method=global_raw.get("default_flash_method", "katapult"),
    allow_flash_fallback=global_raw.get("allow_flash_fallback", True),
    skip_menuconfig=global_raw.get("skip_menuconfig", False),
    stagger_delay=global_raw.get("stagger_delay", 2.0),
    return_delay=global_raw.get("return_delay", 5.0),
    config_cache_dir=global_raw.get("config_cache_dir", "~/.config/kalico-flash/configs"),
)
```

### Registry Save Extension (registry.py)
```python
"global": {
    "klipper_dir": registry.global_config.klipper_dir,
    "katapult_dir": registry.global_config.katapult_dir,
    "default_flash_method": registry.global_config.default_flash_method,
    "allow_flash_fallback": registry.global_config.allow_flash_fallback,
    "skip_menuconfig": registry.global_config.skip_menuconfig,
    "stagger_delay": registry.global_config.stagger_delay,
    "return_delay": registry.global_config.return_delay,
    "config_cache_dir": registry.global_config.config_cache_dir,
}
```

### Timed Keypress Wait (cross-platform)
```python
def _wait_for_key(timeout: float = 1.0) -> bool:
    """Wait for a keypress up to timeout seconds. Returns True if key pressed."""
    try:
        import msvcrt
        import time
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if msvcrt.kbhit():
                msvcrt.getwch()  # consume the key
                return True
            time.sleep(0.05)
        return False
    except ImportError:
        pass

    import select
    import sys
    import tty
    import termios
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if ready:
            sys.stdin.read(1)  # consume
            return True
        return False
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
```

### Config Screen Rendering
```python
def _render_config_screen(registry) -> str:
    """Render config screen with status + settings panels."""
    data = registry.load()
    gc = data.global_config

    settings_lines = []
    for i, setting in enumerate(SETTINGS, 1):
        value = getattr(gc, setting["key"])
        if setting["type"] == "toggle":
            display = "ON" if value else "OFF"
        else:
            display = str(value)
        settings_lines.append(
            f"{theme.label}{i}.{theme.reset} {setting['label']}: {theme.value}{display}{theme.reset}"
        )

    status = render_panel("status", [f"{theme.text}Press setting number to edit, Esc to return{theme.reset}"])
    settings = render_panel("settings", settings_lines)
    return "\n\n".join(center_panel(p) for p in [status, settings])
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `_settings_menu` with `_render_menu` box-drawing | Panel-based config screen with `render_panel` | Phase 13 | Consistent visual style with main screen |
| `_get_menu_choice` with `input()` | `_getch()` single keypress | Phase 12 | Faster interaction, matches main screen UX |

## Open Questions

1. **Numeric input validation bounds**
   - What we know: Stagger delay and return delay are numeric seconds
   - What's unclear: Min/max bounds (0 allowed? 999?)
   - Recommendation: Allow 0-60 for stagger, 0-30 for return delay. 0 = disabled.

2. **Path validation for directory settings**
   - What we know: Context says "Claude's discretion" for invalid path handling
   - What's unclear: Validate on save or just store string?
   - Recommendation: Store as-is (paths are remote Pi paths, can't validate on Windows dev machine). Show warning if path doesn't look like a path (no `/` or `~`).

3. **Config cache dir interaction with existing code**
   - What we know: `config.py` currently uses `XDG_CONFIG_HOME` logic to find config cache
   - What's unclear: Whether the new setting should override XDG detection
   - Recommendation: New setting becomes the explicit override. If set to default, existing XDG logic applies.

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `tui.py`, `panels.py`, `screen.py`, `registry.py`, `models.py`, `theme.py`, `ansi.py`
- Phase 13 CONTEXT.md decisions

### Secondary (MEDIUM confidence)
- Python `select` module behavior on Unix for stdin timeout — well-documented stdlib behavior
- `msvcrt.kbhit()` for Windows non-blocking input — well-documented stdlib behavior

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - stdlib only, all primitives exist in codebase
- Architecture: HIGH - follows established patterns from phases 11-12
- Pitfalls: HIGH - identified from direct code inspection of platform branching and terminal handling

**Research date:** 2026-01-29
**Valid until:** 2026-02-28 (stable domain, no external dependencies)
