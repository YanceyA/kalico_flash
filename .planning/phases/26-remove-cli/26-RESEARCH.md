# Phase 26: Remove CLI - Research

**Researched:** 2026-02-01
**Domain:** Python CLI-to-TUI migration, dead code removal
**Confidence:** HIGH

## Summary

Phase 26 removes all argparse/CLI infrastructure from `flash.py`, making it a thin `main() -> tui.run_menu()` launcher. The codebase is well-structured for this: the TUI already imports specific `cmd_*` functions from `flash.py` via late imports, and all CLI-only code is isolated in `main()` and `build_parser()`.

The main complexity is auditing `cmd_*` functions for CLI-only assumptions (e.g., `from_tui` boolean parameters, CLI-worded error messages, `--device KEY` hints) and cleaning those up since the TUI is now the only caller.

**Primary recommendation:** Delete `build_parser()`, `import argparse`, and the CLI dispatch logic in `main()`. Simplify `main()` to TTY check + `run_menu()`. Then audit `cmd_*` functions to remove `from_tui` parameters and CLI-worded hints/recovery messages.

## Standard Stack

Not applicable -- this phase uses only Python stdlib and existing project code. No new libraries needed.

## Architecture Patterns

### Current Structure (flash.py)

```
flash.py (2063 lines):
  - build_parser()           # DELETE: argparse setup (lines 92-157)
  - import argparse          # DELETE: (line 30)
  - main()                   # REWRITE: currently dispatches CLI args (lines 2007-2062)
  - cmd_flash()              # KEEP: called by tui._action_flash_device
  - cmd_flash_all()          # KEEP: called by tui.run_menu (key 'b')
  - cmd_build()              # KEEP: called by tui (if wired) -- audit usage
  - cmd_add_device()         # KEEP: called by tui._action_add_device
  - cmd_remove_device()      # KEEP: called by tui._action_remove_device
  - cmd_list_devices()       # KEEP: called by tui (verify usage)
  - cmd_exclude_device()     # AUDIT: is this called from TUI?
  - cmd_include_device()     # AUDIT: is this called from TUI?
  - _preflight_build()       # KEEP: used by cmd_flash
  - _preflight_flash()       # KEEP: used by cmd_flash
  - _resolve_flash_method()  # KEEP: used by cmd_flash
  - _remove_cached_config()  # KEEP: used by cmd_remove_device, cmd_add_device
  - _emit_preflight()        # KEEP: used by preflight functions
  - _normalize_pattern()     # KEEP: used by blocking functions
  - _build_blocked_list()    # KEEP: used by tui._build_screen_state
  - _blocked_reason_*()      # KEEP: used by multiple functions
  - _short_path()            # KEEP: used by cmd_flash
  - VERSION                  # KEEP: may be used elsewhere
  - DEFAULT_BLOCKED_DEVICES  # KEEP: used by _build_blocked_list
```

### Target Structure (flash.py after phase)

```
flash.py (~1950 lines estimated):
  - main()                   # 10-15 lines: TTY check -> run_menu()
  - All cmd_* functions      # Kept, with from_tui params removed
  - All helper functions     # Kept
  - No argparse, no build_parser(), no CLI dispatch
```

### Pattern: Thin Launcher

```python
def main() -> int:
    if not sys.stdin.isatty():
        print("kalico-flash requires an interactive terminal.", file=sys.stderr)
        return 1

    from .output import CliOutput
    from .registry import Registry

    out = CliOutput()
    registry_path = Path(__file__).parent / "devices.json"
    registry = Registry(str(registry_path))

    try:
        from .tui import run_menu
        return run_menu(registry, out)
    except KeyboardInterrupt:
        out.warn("Aborted.")
        return 130
    except Exception as e:
        out.error(f"Unexpected error: {e}")
        return 3
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| N/A | This phase is deletion, not creation | N/A | N/A |

## Common Pitfalls

### Pitfall 1: Deleting functions still used by TUI

**What goes wrong:** Removing a `cmd_*` function that the TUI imports causes ImportError at runtime.
**Why it happens:** TUI uses late imports (`from .flash import cmd_flash`) so static analysis misses them.
**How to avoid:** Grep for every function name being considered for deletion across the entire `kflash/` package before removing it.
**Warning signs:** Any function in flash.py that doesn't appear in `main()` or `build_parser()` dispatch is likely used elsewhere.

### Pitfall 2: CLI-worded hints left in cmd_* functions

**What goes wrong:** After CLI removal, error messages still say "Run --add-device" or "Use --device KEY".
**Why it happens:** The `from_tui` boolean conditional branches have CLI-worded text that becomes dead code, but the non-TUI branch text remains as the default.
**How to avoid:** Audit every `from_tui` conditional and every string containing `--` flags. Replace with TUI-appropriate wording.

**Specific locations requiring cleanup:**

1. `cmd_build()` line 293: `"Run --add-device first."` (from_tui=False branch)
2. `cmd_flash()` line 441: `"Use --device KEY or run from SSH terminal."`
3. `cmd_flash()` line 447: `"Run --add-device first."` (from_tui=False branch)
4. `cmd_flash()` lines 541-544: CLI recovery hints
5. `cmd_flash()` line 648: comment `"Explicit --device KEY mode"`
6. `cmd_flash()` line 682: `"run \`kflash --include-device\`"`
7. `cmd_list_devices()` line 1552: `"Run --add-device to register a board."` (from_menu=False branch)
8. `cmd_list_devices()` line 1624: `"Use --add-device to register unknown devices."`
9. `cmd_add_device()` line 1658: `"Interactive terminal required for --add-device."`
10. `errors.py` lines 97-98, 108, 206-207: CLI-worded recovery templates

### Pitfall 3: from_tui / from_menu parameter removal breaks callers

**What goes wrong:** Removing `from_tui` parameter changes function signature, but TUI passes `from_tui=True`.
**How to avoid:** When removing `from_tui` param, also update all callers. Key callers:
- `tui.py:339` passes `from_tui=True` to `cmd_flash()`
- `tui.py` does NOT pass `from_tui` to `cmd_build()`, `cmd_remove_device()`, `cmd_add_device()`

### Pitfall 4: cmd_exclude_device / cmd_include_device may be dead code

**What goes wrong:** These functions are only called from CLI dispatch in `main()` (args.exclude_device, args.include_device). The TUI device config screen handles flashable toggling directly via `registry.set_flashable()`.
**How to avoid:** Verify with grep that no TUI code calls these. If dead, they can be removed.

### Pitfall 5: errors.py has dual CLI/TUI recovery text system

**What goes wrong:** `errors.py` has `get_recovery_text(key, from_tui)` with `_TUI_RECOVERY_OVERRIDES` dict. After CLI removal, the base templates still contain CLI-worded text.
**How to avoid:** Simplify `get_recovery_text()` to always return TUI text. Merge `_TUI_RECOVERY_OVERRIDES` into the base templates and remove the `from_tui` parameter.

## Code Examples

### Functions to DELETE entirely

```python
# flash.py
build_parser()              # Lines 92-157 - argparse setup
# The CLI dispatch block in main() (lines 2023-2048)

# Likely dead:
cmd_exclude_device()        # Lines 1422-1441 - only CLI caller
cmd_include_device()        # Lines 1444-1463 - only CLI caller
```

### Imports to DELETE from flash.py

```python
import argparse             # Line 30 - no longer needed
```

### Parameters to simplify

```python
# cmd_build: remove from_tui param, always use TUI wording
# cmd_flash: remove from_tui param, always use TUI wording
# cmd_flash: the device_key=None interactive selection path (lines 478-646)
#            is still used by TUI, but CLI-worded branches within should be cleaned
# cmd_list_devices: remove from_menu param, always use TUI wording
# cmd_add_device: the else branch (lines 1680-1779, "CLI path") may still be needed
#                 if TUI ever calls without selected_device -- verify
```

### errors.py simplification

```python
# Before: dual path
def get_recovery_text(template_key: str, from_tui: bool = False) -> str:
    if from_tui and template_key in _TUI_RECOVERY_OVERRIDES:
        return _TUI_RECOVERY_OVERRIDES[template_key]
    return ERROR_TEMPLATES[template_key]["recovery_template"]

# After: single path (TUI-only)
def get_recovery_text(template_key: str) -> str:
    if template_key in _TUI_RECOVERY_OVERRIDES:
        return _TUI_RECOVERY_OVERRIDES[template_key]
    return ERROR_TEMPLATES[template_key]["recovery_template"]
# Then merge TUI overrides into base templates and remove the override dict
```

## State of the Art

Not applicable -- this is internal refactoring, not technology adoption.

## Open Questions

1. **cmd_exclude_device / cmd_include_device removal**
   - What we know: Only called from CLI dispatch. TUI uses `registry.set_flashable()` directly.
   - What's unclear: Whether any future code might want these as reusable functions.
   - Recommendation: Delete them. They're trivial wrappers that can be recreated if needed.

2. **cmd_add_device CLI path (lines 1680-1779)**
   - What we know: TUI always passes `selected_device`, so the `else` branch (full discovery scan) may be dead.
   - What's unclear: Whether removing this branch breaks anything.
   - Recommendation: Verify TUI always calls with `selected_device`. If so, the else branch is dead code. However, it may be safer to keep it as a fallback.

3. **cmd_flash device_key=None path**
   - What we know: TUI calls `cmd_flash(registry, device_key, out, ...)` always with a device_key. The `device_key is None` interactive selection path (lines 478-646) may be dead from TUI.
   - What's unclear: Whether TUI ever passes None for device_key.
   - Recommendation: Check TUI callers. If TUI always passes a key, this is dead code but large -- may warrant keeping for now or separate cleanup.

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis of `kflash/flash.py` (2063 lines), `kflash/tui.py` (969 lines), `kflash/errors.py`
- Grep analysis of cross-module imports and function references

## Metadata

**Confidence breakdown:**
- Architecture: HIGH - direct codebase reading, no external dependencies
- Pitfalls: HIGH - identified from actual code cross-references
- Cleanup scope: HIGH - grep-verified function usage across modules

**Research date:** 2026-02-01
**Valid until:** 2026-03-01 (stable -- internal refactoring)
