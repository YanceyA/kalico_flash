# Phase 15: Config Validation - Research

**Researched:** 2026-01-30
**Domain:** Python stdlib path validation, input validation in TUI edit loops
**Confidence:** HIGH

## Summary

This phase adds validation to the config screen's settings edit flow in `tui.py` (`_config_screen` function, lines 583-661). The current implementation accepts any numeric or path input without validation. The task is to add validation with error messages and re-prompting using only Python stdlib (`os.path`, `pathlib`).

No external libraries are needed. This is pure Python stdlib work with `os.path.expanduser()`, `os.path.isdir()`, `os.path.isfile()`, and basic numeric range checking.

**Primary recommendation:** Add a validation module or validation functions (could live in a new `validation.py` or inline in `tui.py`) that validate before calling `registry.save_global()`, with a re-prompt loop on failure.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| os.path | stdlib | expanduser, isdir, isfile, join | Already used throughout codebase |
| pathlib.Path | stdlib | Path.expanduser(), exists(), is_dir() | Already used in config.py |

No additional libraries needed.

## Architecture Patterns

### Current Edit Flow (tui.py lines 635-661)

The numeric and path edit branches currently:
1. Prompt user with `input()`
2. Parse value
3. Save immediately via `registry.save_global()`

### Recommended Pattern: Validation Loop with Re-prompt

Replace the single-shot input with a validation loop:

```python
# Numeric validation pattern
while True:
    raw = input(f"  {setting['label']} [{current}]: ").strip()
    if not raw:
        break  # keep current value
    try:
        val = float(raw)
    except ValueError:
        print(f"  {theme.error}Invalid: enter a number{theme.reset}")
        continue
    if not (lo <= val <= hi):
        print(f"  {theme.error}Invalid: must be {lo}-{hi}s{theme.reset}")
        continue
    new_gc = dataclasses.replace(gc, **{field_key: val})
    registry.save_global(new_gc)
    break
```

```python
# Path validation pattern
while True:
    raw = input(f"  {setting['label']} [{current}]: ").strip()
    if not raw:
        break
    expanded = os.path.expanduser(raw)
    if not os.path.isdir(expanded):
        print(f"  {theme.error}Invalid: directory not found: {expanded}{theme.reset}")
        continue
    # Content validation per field
    if field_key == "klipper_dir" and not os.path.isfile(os.path.join(expanded, "Makefile")):
        print(f"  {theme.error}Invalid: no Makefile found (not a Klipper directory){theme.reset}")
        continue
    if field_key == "katapult_dir" and not os.path.isfile(os.path.join(expanded, "scripts", "flashtool.py")):
        print(f"  {theme.error}Invalid: no scripts/flashtool.py found (not a Katapult directory){theme.reset}")
        continue
    new_gc = dataclasses.replace(gc, **{field_key: raw})  # store unexpanded
    registry.save_global(new_gc)
    break
```

### Where to Put Validation Logic

Two options:

**Option A (recommended): Validation functions in a new `validation.py` module**
- Pure functions: `validate_path_setting(field_key, value) -> tuple[bool, str]`
- `validate_numeric_setting(field_key, value) -> tuple[bool, str]`
- Returns (is_valid, error_message)
- TUI calls these in the loop; keeps tui.py clean

**Option B: Inline in tui.py**
- Simpler, fewer files, but mixes validation logic with TUI code

Recommend Option A for consistency with the hub-and-spoke architecture.

### Validation Rules Map

```python
NUMERIC_BOUNDS = {
    "stagger_delay": (0.0, 30.0),
    "return_delay": (0.0, 60.0),
}

PATH_CONTENT_CHECKS = {
    "klipper_dir": [("Makefile", "Not a Klipper directory (no Makefile)")],
    "katapult_dir": [("scripts/flashtool.py", "Not a Katapult directory (no scripts/flashtool.py)")],
    "config_cache_dir": [],  # directory existence only
}
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tilde expansion | Custom ~ handling | `os.path.expanduser()` | Handles edge cases, cross-platform |
| Path existence | Custom checks | `os.path.isdir()`, `os.path.isfile()` | Stdlib, handles symlinks |

## Common Pitfalls

### Pitfall 1: Storing Expanded Paths
**What goes wrong:** Storing `/home/pi/klipper` instead of `~/klipper` breaks portability
**How to avoid:** Expand for validation only, store the user's original input (with ~)

### Pitfall 2: Remote Validation on Windows Dev
**What goes wrong:** Path validation checks local filesystem, but paths are on the Pi
**How to avoid:** This tool runs ON the Pi. But during development, tests won't find `/home/pi/klipper`. Accept this limitation since there are no automated tests.

### Pitfall 3: EOFError/KeyboardInterrupt in Validation Loop
**What goes wrong:** User presses Ctrl+C or Ctrl+D during re-prompt, crashes
**How to avoid:** Wrap the entire validation loop in try/except (EOFError, KeyboardInterrupt) -> break/continue to outer config loop

### Pitfall 4: Empty Input After Error
**What goes wrong:** After showing error, empty input should cancel edit (not re-show error)
**How to avoid:** Empty string always breaks out of the validation loop (keeps current value)

## Code Examples

### Complete Numeric Validation Function

```python
def validate_numeric(field_key: str, raw: str) -> tuple[bool, float, str]:
    """Validate a numeric setting value.

    Returns (is_valid, parsed_value, error_message).
    """
    bounds = {"stagger_delay": (0.0, 30.0), "return_delay": (0.0, 60.0)}
    try:
        val = float(raw)
    except ValueError:
        return False, 0.0, "Enter a number"
    lo, hi = bounds.get(field_key, (0.0, float("inf")))
    if not (lo <= val <= hi):
        return False, 0.0, f"Must be between {lo} and {hi} seconds"
    return True, val, ""
```

### Complete Path Validation Function

```python
def validate_path(field_key: str, raw: str) -> tuple[bool, str]:
    """Validate a path setting value.

    Returns (is_valid, error_message).
    """
    import os
    expanded = os.path.expanduser(raw)
    if not os.path.isdir(expanded):
        return False, f"Directory not found: {expanded}"

    content_checks = {
        "klipper_dir": ("Makefile", "No Makefile found — not a Klipper directory"),
        "katapult_dir": (
            os.path.join("scripts", "flashtool.py"),
            "No scripts/flashtool.py — not a Katapult directory",
        ),
    }
    if field_key in content_checks:
        relpath, msg = content_checks[field_key]
        if not os.path.isfile(os.path.join(expanded, relpath)):
            return False, msg
    return True, ""
```

## State of the Art

No changes -- this is pure Python stdlib, stable APIs.

## Open Questions

None. The requirements are clear and the implementation is straightforward stdlib work.

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `tui.py` lines 583-661 (current config edit flow)
- Codebase inspection: `screen.py` SETTINGS list (field keys and types)
- Codebase inspection: `models.py` GlobalConfig (field definitions and defaults)
- Python stdlib `os.path` module (expanduser, isdir, isfile)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Python stdlib only, no external deps
- Architecture: HIGH - Clear insertion point in existing tui.py edit flow
- Pitfalls: HIGH - Well-understood domain, codebase patterns established

**Research date:** 2026-01-30
**Valid until:** 2026-03-01
