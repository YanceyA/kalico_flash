# Phase 28: Flash All Preflight - Research

**Researched:** 2026-02-01
**Domain:** Batch flash safety checks in existing Python TUI codebase
**Confidence:** HIGH

## Summary

This phase adds three preflight safety mechanisms to `cmd_flash_all()` in `flash.py`: (1) fail-fast environment validation before any device is processed, (2) Moonraker unreachable confirmation prompt matching single-device behavior, and (3) duplicate USB path detection to prevent two registry entries targeting the same physical device.

All three requirements are straightforward modifications to the existing `cmd_flash_all()` function. The single-device `cmd_flash()` already implements the patterns for SAFE-01 and SAFE-02 -- Flash All just needs to replicate them. SAFE-04 is new logic but simple (a `set` tracking resolved paths).

**Primary recommendation:** Add preflight checks at the top of `cmd_flash_all()` before the batch loop, reusing existing `_preflight_flash()` for environment checks and `get_print_status()` patterns from `cmd_flash()`.

## Standard Stack

Not applicable -- this is pure Python stdlib modification to an existing function. No new libraries.

## Architecture Patterns

### Pattern 1: Environment Preflight (SAFE-01)

**What:** Call `_preflight_flash()` once before entering the batch loop, just as `cmd_flash()` does at line 640.

**Current state in `cmd_flash_all()`:** The function validates cached configs and MCU matches (Stage 1, lines 1009-1088) but never calls `_preflight_flash()`. It also checks `get_print_status()` but only inside Stage 4 (line 1192), after builds have already completed.

**Where to insert:** After loading `global_config` (line 1008) and before Stage 1. Use the global default flash method and `allow_flash_fallback` from `global_config`.

**Code reference:**
```python
# In cmd_flash(), line 636-640:
preferred_method = _resolve_flash_method(entry, data.global_config)
allow_fallback = data.global_config.allow_flash_fallback
if not _preflight_flash(out, klipper_dir, katapult_dir, preferred_method, allow_fallback):
    return 1
```

For Flash All, there is no single entry -- use `global_config.default_flash_method` as the method.

### Pattern 2: Moonraker Unreachable Prompt (SAFE-02)

**What:** When `get_print_status()` returns `None`, warn and prompt for confirmation before proceeding. When printing/paused, abort.

**Current state in `cmd_flash_all()`:** Line 1192-1196 checks print status but only blocks on active print. It does NOT prompt when Moonraker is unreachable (it just prints a warning at line 1100 during version check but continues silently).

**Single-device reference (cmd_flash lines 648-673):**
```python
print_status = get_print_status()
if print_status is None:
    out.warn("Moonraker unreachable - print status and version check unavailable")
    if not out.confirm("Continue without safety checks?", default=False):
        out.phase("Flash", "Cancelled")
        return 0
elif print_status.state in ("printing", "paused"):
    # Block with error
```

**Where to insert:** Move/replace the existing print status check (line 1192) to before Stage 1, so it runs before any builds. Remove the duplicate check at Stage 4.

### Pattern 3: Duplicate USB Path Tracking (SAFE-04)

**What:** Track resolved USB paths in a `set[str]`. Before flashing each device, check if its resolved path is already in the set. If so, skip with a warning.

**Current state:** No duplicate path tracking exists in `cmd_flash_all()`. The function does handle duplicate serial pattern matches in `cmd_flash()` (lines 389-394, 601-615) but only for pattern-to-multiple-device mapping, not for two different patterns resolving to the same device.

**Where to insert:** Inside the flash loop (Stage 4, around line 1210), after `match_device()` resolves the USB path. Before calling `flash_device()`, check `usb_device.path` against `used_paths` set.

```python
used_paths: set[str] = set()
# ... in loop:
usb_device = match_device(entry.serial_pattern, usb_devices)
if usb_device and usb_device.path in used_paths:
    result.error_message = f"USB path already targeted by another device"
    result.skipped = True
    out.warn(f"Skipping {entry.name}: USB path {usb_device.path} already used")
    continue
if usb_device:
    used_paths.add(usb_device.path)
```

### Anti-Patterns to Avoid

- **Don't duplicate the print status check** -- currently it's checked at line 1192 (Stage 4, after builds). Move it to the top, don't add a second check.
- **Don't call `_preflight_flash()` per-device** -- it checks the same global environment for every device. Call once.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Environment validation | Custom checks for make/klipper/katapult | `_preflight_flash()` already at line 114 | Already handles all edge cases including method-specific checks |
| Print status prompt | Custom Moonraker query | `get_print_status()` + `out.confirm()` pattern from `cmd_flash()` | Exact same UX needed |

## Common Pitfalls

### Pitfall 1: Flash Method Resolution for Batch Preflight

**What goes wrong:** `_preflight_flash()` takes a `preferred_method` parameter. In single-device flow, this comes from the specific device entry. In Flash All, there's no single device.
**How to avoid:** Use `global_config.default_flash_method` for the batch preflight call. Individual device methods may differ, but if the global environment is broken (no make, no klipper dir), it fails regardless. Katapult flashtool check should use the most permissive path -- if any device might use katapult, check for it.
**Recommendation:** Call `_preflight_flash()` with `preferred_method=global_config.default_flash_method` and `allow_fallback=global_config.allow_flash_fallback`. This matches what most devices will use. If a specific device overrides to a different method, that's fine -- the key resources (klipper dir, make) are checked regardless.

### Pitfall 2: used_paths Must Track Resolved Symlink Paths

**What goes wrong:** `/dev/serial/by-id/` entries are symlinks. Two different filenames could resolve to the same `/dev/ttyACM0`. The `DiscoveredDevice.path` stores the by-id path (the symlink), not the resolved target.
**How to avoid:** Use `os.path.realpath()` on the device path before comparing, to handle cases where two by-id symlinks point to the same physical device.
**Warning signs:** Two devices with different serial patterns but same underlying tty device.

### Pitfall 3: Removing Duplicate Stage 4 Print Check

**What goes wrong:** After moving the print status check to the top, forgetting to remove the existing check at line 1192-1196 leaves dead code that could confuse future readers.
**How to avoid:** Remove lines 1192-1196 when adding the early check.

## Code Examples

### SAFE-01: Preflight Before Batch Loop

```python
# After line 1008 (katapult_dir assignment), before Stage 1:
preferred_method = (global_config.default_flash_method or "katapult").strip().lower()
allow_fallback = global_config.allow_flash_fallback
if not _preflight_flash(out, klipper_dir, katapult_dir, preferred_method, allow_fallback):
    return 1
```

### SAFE-02: Moonraker Prompt (Move to Top)

```python
# After preflight, before Stage 1:
print_status = get_print_status()
if print_status is None:
    out.warn("Moonraker unreachable - print status and version check unavailable")
    if not out.confirm("Continue without safety checks?", default=False):
        out.phase("Flash All", "Cancelled")
        return 0
elif print_status.state in ("printing", "paused"):
    progress_pct = int(print_status.progress * 100)
    filename = print_status.filename or "unknown"
    out.error(f"Print in progress: {filename} ({progress_pct}%). Aborting flash.")
    return 1
else:
    out.phase("Safety", f"Printer state: {print_status.state} - OK to flash")
```

### SAFE-04: Duplicate Path Detection in Flash Loop

```python
# Before the flash loop (inside klipper_service_stopped):
used_paths: set[str] = set()

# In the loop, after match_device:
if usb_device is not None:
    real_path = os.path.realpath(usb_device.path)
    if real_path in used_paths:
        result.error_message = f"USB path already targeted by prior device"
        result.skipped = True
        out.warn(f"Skipping {entry.name}: duplicate USB path")
        continue
    used_paths.add(real_path)
```

## State of the Art

Not applicable -- internal codebase patterns, not external technology.

## Open Questions

1. **Should preflight check ALL device flash methods or just global default?**
   - What we know: `_preflight_flash()` checks katapult flashtool only if the method includes katapult. If global default is `make_flash` but one device overrides to `katapult`, the batch preflight won't catch a missing flashtool.
   - Recommendation: Check with global default + fallback. Per-device method differences are edge cases that will fail at flash time with a clear error. The main goal is catching missing `make` and klipper dir.

2. **Should `used_paths` use realpath or by-id path?**
   - What we know: `DiscoveredDevice.path` is the `/dev/serial/by-id/...` symlink path. Two different by-id names can't normally point to the same underlying device unless there's a hardware/driver anomaly.
   - Recommendation: Use `os.path.realpath()` to be safe, but note this is a defensive measure. The by-id path itself would likely work fine in practice.

## Sources

### Primary (HIGH confidence)
- Direct code analysis of `C:\dev_projects\kalico_flash\kflash\flash.py` -- `cmd_flash()` (lines 324-955), `cmd_flash_all()` (lines 958-1297), `_preflight_flash()` (lines 114-157)
- Direct code analysis of `C:\dev_projects\kalico_flash\kflash\models.py` -- `BatchDeviceResult` dataclass (lines 82-93)
- Direct code analysis of `C:\dev_projects\kalico_flash\kflash\discovery.py` -- `match_device()`, `DiscoveredDevice`
- Direct code analysis of `C:\dev_projects\kalico_flash\kflash\moonraker.py` -- `get_print_status()` returns `Optional[PrintStatus]`

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no external dependencies, pure internal refactoring
- Architecture: HIGH - patterns already exist in cmd_flash(), direct replication
- Pitfalls: HIGH - identified from reading the actual code paths

**Research date:** 2026-02-01
**Valid until:** 2026-03-01 (stable internal codebase)
