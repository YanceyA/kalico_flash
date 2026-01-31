# Phase 20: Menu Integration - Research

**Researched:** 2026-01-31
**Domain:** TUI menu wiring (Python stdlib)
**Confidence:** HIGH

## Summary

This phase wires the existing device config screen (`_device_config_screen` in `tui.py`) into the main menu loop via a new "E" key binding. The codebase already has all building blocks: the device config screen (Phase 19), device selection prompting (`_prompt_device_number`), and the main menu dispatch loop in `run_menu`.

The work is purely integration: add "E" to ACTIONS, handle the keypress in `run_menu`, prompt for device selection (reusing existing patterns), and call `_device_config_screen`. No new modules, no new rendering, no external dependencies.

**Primary recommendation:** Follow the exact pattern used by the "R" (Remove) action — prompt device number, dispatch to handler, show status on return.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib | 3.9+ | All implementation | Project constraint: no external deps |

No new libraries needed. This phase is pure wiring of existing code.

## Architecture Patterns

### Pattern 1: Action dispatch in run_menu
**What:** The `run_menu` function in `tui.py` (line 455) uses a `while True` loop with `_getch()` and `if/elif` dispatch on key characters. Each action follows the same template.
**When to use:** Adding any new menu action.
**Example (from existing "R" remove action, lines 533-543):**
```python
elif key == "r":
    print(key)
    print()
    device_key = _prompt_device_number(device_map, out)
    if device_key:
        status_message, status_level = _action_remove_device(registry, out, device_key)
        print()
        _countdown_return(registry.load().global_config.return_delay)
    else:
        status_message = "Remove: no device selected"
        status_level = "warning"
```

### Pattern 2: Device selection with auto-select
**What:** `_prompt_device_number` (line 286) already auto-selects when only one device exists and prompts for a number otherwise. It uses `device_map` which maps numbers to `DeviceRow` objects.
**When to use:** Any action that targets a specific device.
**Key detail:** The device_map from `_build_screen_state` includes ALL registered devices (connected and disconnected) with numbers. This matches the CONTEXT.md decision to show all registered devices.

### Pattern 3: ACTIONS list defines panel rendering
**What:** `ACTIONS` in `screen.py` (line 78) is a list of `(key, label)` tuples that drives `render_actions_panel()`. The order in this list determines display order.
**Current order:** F, A, R, D, C, B, Q
**Required order per CONTEXT.md:** F (Flash) > B (Flash All) > A (Add) > E (Config) > R (Remove) > C (Config/Settings) > Q (Quit)

### Pattern 4: Step dividers between sections
**What:** `render_action_divider()` in `panels.py` renders an unlabeled dashed line. Already used in `run_menu` between screen redraws (line 487) and in `_device_config_screen` (line 755).
**When to use:** Between device selection output and config screen launch, and after config screen exits.

### Pattern 5: Action handler return convention
**What:** Action handlers return `tuple[str, str]` as `(message, level)` where level is "success"/"error"/"warning"/"info". This becomes the status bar message on the next menu render.

### Anti-Patterns to Avoid
- **Don't create a new device selection function:** `_prompt_device_number` already handles the numbered selection with auto-select for single device. Reuse it directly.
- **Don't add dividers inside `_device_config_screen`:** CONTEXT.md says Phase 19 handled internal dividers. Only add dividers at the integration boundary (before/after the config screen call).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Device selection prompt | New selection UI | `_prompt_device_number(device_map, out)` | Already handles auto-select, retry, cancel |
| Screen rendering | New panels | `_device_config_screen(device_key, registry, out)` | Phase 19 built this |
| Divider lines | Manual print dashes | `render_action_divider()` from panels.py | Consistent styling, Unicode support |
| Status messages | Ad-hoc prints | Return `(message, level)` tuple | Standard menu pattern |

## Common Pitfalls

### Pitfall 1: ACTIONS order mismatch with key dispatch
**What goes wrong:** ACTIONS list order doesn't match CONTEXT.md required panel ordering.
**Why it happens:** ACTIONS list is currently F, A, R, D, C, B, Q but needs reordering.
**How to avoid:** Update ACTIONS to: F, B, A, E, R, C, Q. The "D" (Refresh) key is implicit (not in CONTEXT.md panel list) — check if it should remain or be removed.
**Warning signs:** Visual panel doesn't match spec.

### Pitfall 2: No devices registered edge case
**What goes wrong:** Pressing "E" with empty registry crashes or shows confusing output.
**Why it happens:** `_prompt_device_number` returns None when device_map is empty, but the error message should be specific per CONTEXT.md.
**How to avoid:** Check `device_map` emptiness before calling `_prompt_device_number`. If empty, set status to "No devices registered. Use Add Device first." and return.

### Pitfall 3: Unknown key message not updated
**What goes wrong:** After adding "E", the fallback message still says "Use F/A/R/D/C/B/Q" (line 575).
**How to avoid:** Update the hint string to include "E".

### Pitfall 4: Save summary message missing
**What goes wrong:** CONTEXT.md requires "Brief success summary shown after saving changes before returning to menu" but `_device_config_screen` currently returns None (no status).
**How to avoid:** Either modify `_device_config_screen` to return a summary string, or create a wrapper `_action_config_device` that tracks changes and builds a summary. The wrapper pattern is cleaner (matches other `_action_*` functions).

### Pitfall 5: Device selection shows connection status
**What goes wrong:** CONTEXT.md says "Device list shows just numbered names" but `_prompt_device_number` relies on the main screen's device_map which already shows full device info in the panel above.
**How to avoid:** The device selection is just a "#:" prompt — the numbered list is already visible in the devices panel. No extra listing needed. Just prompt for the number.

## Code Examples

### Adding "E" to ACTIONS list (screen.py)
```python
# Required order per CONTEXT.md:
# Flash > Flash All > Add > Config > Remove > Settings > Quit
ACTIONS: list[tuple[str, str]] = [
    ("F", "Flash Device"),
    ("B", "Flash All"),
    ("A", "Add Device"),
    ("E", "Config Device"),
    ("R", "Remove Device"),
    ("C", "Settings"),
    ("Q", "Quit"),
]
```

### Menu dispatch for "E" key (tui.py, in run_menu)
```python
elif key == "e":
    print(key)
    print()
    if not device_map:
        status_message = "No devices registered. Use Add Device first."
        status_level = "warning"
    else:
        device_key = _prompt_device_number(device_map, out)
        if device_key:
            print()
            print(render_action_divider())  # divider before config screen
            _device_config_screen(device_key, registry, out)
            print()
            print(render_action_divider())  # divider after config screen
            status_message = "Returned from device config"
            status_level = "info"
        else:
            status_message = "Config: no device selected"
            status_level = "warning"
```

### Save summary enhancement (_device_config_screen or wrapper)
```python
def _action_config_device(registry, out, device_key: str) -> tuple[str, str]:
    """Config a device. Returns (message, level)."""
    try:
        _device_config_screen(device_key, registry, out)
        # Check what changed by comparing before/after
        return ("Device config: changes saved", "success")
    except KeyboardInterrupt:
        return ("Device config: cancelled (changes discarded)", "warning")
    except Exception as exc:
        return (f"Device config: {exc}", "error")
```

## State of the Art

No changes — this is internal wiring of existing components.

## Open Questions

1. **"D" (Refresh) key in ACTIONS panel**
   - CONTEXT.md panel ordering doesn't mention Refresh: "Flash > Flash All > Add > Config > Remove > Settings > Quit"
   - Current code has D mapped to refresh. Should it remain in ACTIONS but not in the listed order, or be removed from the panel?
   - Recommendation: Keep D functional but check if it should appear in the actions panel. The CONTEXT.md ordering may just be listing the new arrangement without explicitly excluding D.

2. **Save summary detail level**
   - CONTEXT.md says "Brief success summary shown after saving changes (e.g., 'Saved: renamed key, updated flash method')"
   - `_device_config_screen` currently doesn't return change info. `_save_device_edits` doesn't return a summary either.
   - Recommendation: Have `_save_device_edits` return a list of changed field names, or compare the pending dict to build summary text. Alternatively, modify `_device_config_screen` to return the pending dict keys.

3. **Countdown after config screen exit**
   - Other actions (flash, add, remove) use `_countdown_return`. Should config device also use it?
   - Recommendation: Yes, for consistency, if changes were made. If no changes (Ctrl+C discard), skip countdown.

## Sources

### Primary (HIGH confidence)
- Direct code analysis of `C:\dev_projects\kalico_flash\kflash\tui.py` — menu loop, dispatch, device selection
- Direct code analysis of `C:\dev_projects\kalico_flash\kflash\screen.py` — ACTIONS list, device config screen rendering
- Direct code analysis of `C:\dev_projects\kalico_flash\kflash\panels.py` — render_action_divider, step dividers
- Direct code analysis of `C:\dev_projects\kalico_flash\kflash\flash.py` — cmd_remove_device pattern

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no external deps, stdlib only
- Architecture: HIGH - all patterns directly observed in existing code
- Pitfalls: HIGH - derived from specific code locations and CONTEXT.md requirements

**Research date:** 2026-01-31
**Valid until:** 2026-03-01 (stable internal codebase, no external dependencies)
