# Phase 29: Flash Workflow Hardening - Research

**Researched:** 2026-02-01
**Domain:** Python TUI flash safety checks and build output capture
**Confidence:** HIGH

## Summary

This phase adds two capabilities: (1) USB-derived MCU cross-check before flashing (SAFE-03), and (2) build failure output capture for Flash All (DBUG-01). Both build on existing infrastructure with minimal new code.

The `extract_mcu_from_serial()` function in `discovery.py` already extracts MCU type from USB serial filenames. The `run_build()` function already captures output when `quiet=True`. The gaps are: no cross-check logic in flash workflows, and `BuildResult` lacks an `error_output` field.

**Primary recommendation:** Add MCU cross-check at discovery phase (before build), add `error_output` field to `BuildResult`, and show last 20 lines in Flash All summary on failure.

## Standard Stack

No new libraries needed. All changes use Python 3.9+ stdlib only (subprocess, dataclasses).

## Architecture Patterns

### SAFE-03: MCU Cross-Check Integration Points

**Single-device flash (`cmd_flash`):**
- After device selection (line ~643 in flash.py, after `device_path` is resolved)
- Call `extract_mcu_from_serial(usb_device.filename)` to get USB-derived MCU
- Compare against `entry.mcu` using existing bidirectional prefix match logic
- On mismatch: warn user, require `out.confirm()` to proceed
- On `None` return: skip check silently (best-effort)

**Flash All (`cmd_flash_all`):**
- In Stage 4 flash loop (line ~1242), after finding `usb_device`
- Call `extract_mcu_from_serial(usb_device.filename)`
- On mismatch: set `result.error_message`, skip device, continue loop
- On `None` return: skip check, proceed with flash

**MCU comparison logic:**
- `extract_mcu_from_serial()` returns lowercase base MCU (e.g., "stm32h723")
- `entry.mcu` stores the same format (e.g., "stm32h723")
- Simple case-insensitive string equality is sufficient
- Existing `config.py` `validate_mcu()` uses bidirectional prefix match, but that handles config variants (stm32h723xx). For USB-to-registry comparison, exact match on base MCU is correct since both are already normalized.

### DBUG-01: Build Output Capture

**`BuildResult` model change:**
- Add `error_output: Optional[str] = None` field to `BuildResult` in `models.py`

**`run_build()` change (build.py):**
- When `quiet=True` and build fails, capture `build_result.stderr` (and optionally `stdout`)
- Decode bytes to string, store in `BuildResult.error_output`
- Already using `capture_output=quiet` so stdout/stderr are available on the `CompletedProcess` object

**Flash All summary change (flash.py `cmd_flash_all`):**
- In Stage 5 summary, when `result.build_ok is False`, check if associated `BuildResult` has `error_output`
- Display last 20 lines inline
- Need to store `BuildResult` alongside `BatchDeviceResult` (currently only stores error_message string)

### Recommended Approach for Build Output Storage

Option A (simpler): Store full output in `BatchDeviceResult.error_message` or a new `error_output` field on `BatchDeviceResult`.

Option B (cleaner): Store `BuildResult` reference on `BatchDeviceResult`.

**Recommendation:** Add `error_output: Optional[str] = None` to both `BuildResult` and `BatchDeviceResult`. In the build loop, propagate `build_result.error_output` to `batch_result.error_output`. In summary, show last 20 lines from `batch_result.error_output`.

### Code Flow for Last-20-Lines Display

```python
# In build loop (Stage 3), on failure:
if not build_result.success:
    result.error_message = build_result.error_message or "Build failed"
    result.error_output = build_result.error_output  # full captured output

# In summary (Stage 5), for failed builds:
if not result.build_ok and result.error_output:
    lines = result.error_output.strip().splitlines()
    tail = lines[-20:] if len(lines) > 20 else lines
    out.info("", f"  Last {len(tail)} lines of build output:")
    for line in tail:
        out.info("", f"    {line}")
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MCU extraction from serial | Custom parser | `extract_mcu_from_serial()` | Already exists in discovery.py |
| MCU comparison | Complex matching | Simple `==` on lowercase strings | Both sources already normalized to base MCU |
| Output capture | Manual pipe handling | `capture_output=True` on subprocess | Already implemented via `quiet=True` |

## Common Pitfalls

### Pitfall 1: Subprocess captured output is bytes, not str
**What goes wrong:** `build_result.stdout` and `build_result.stderr` are `bytes` when `capture_output=True`
**How to avoid:** Decode with `.decode('utf-8', errors='replace')` before storing

### Pitfall 2: MCU comparison false positives
**What goes wrong:** "stm32f4" prefix-matches "stm32f411" leading to incorrect "match"
**How to avoid:** Use exact equality (`==`) not prefix match. Both `extract_mcu_from_serial()` and registry `entry.mcu` store the base MCU without variant suffix.

### Pitfall 3: Flash All skipped device not tracked properly
**What goes wrong:** Skipped device shows as "FAIL" in summary instead of "SKIP/MCU_MISMATCH"
**How to avoid:** Set `result.skipped = True` and a descriptive `error_message` for MCU mismatch skips. The `BatchDeviceResult` already has a `skipped` field.

### Pitfall 4: Build output can be very large
**What goes wrong:** Storing full multi-MB build output in memory
**How to avoid:** Cap stored output (e.g., last 200 lines or 50KB). For the summary, only display last 20 lines.

## Code Examples

### MCU cross-check in cmd_flash (single device)
```python
# After device_path is resolved, before config phase
from .discovery import extract_mcu_from_serial

usb_mcu = extract_mcu_from_serial(usb_device.filename)
if usb_mcu is not None and usb_mcu.lower() != entry.mcu.lower():
    out.warn(
        f"MCU mismatch: USB device reports '{usb_mcu}' "
        f"but registry expects '{entry.mcu}'"
    )
    if not out.confirm("Continue anyway?", default=False):
        out.phase("Discovery", "Cancelled - MCU mismatch")
        return 1
```

### MCU cross-check in cmd_flash_all (batch)
```python
# In Stage 4 flash loop, after finding usb_device
usb_mcu = extract_mcu_from_serial(usb_device.filename)
if usb_mcu is not None and usb_mcu.lower() != entry.mcu.lower():
    result.error_message = (
        f"MCU mismatch: USB='{usb_mcu}', registry='{entry.mcu}'"
    )
    result.skipped = True
    out.warn(f"Skipping {entry.name}: {result.error_message}")
    continue
```

### Build output capture in run_build
```python
# After failed build with quiet=True
if build_result.returncode != 0:
    error_output = None
    if quiet and hasattr(build_result, 'stderr'):
        raw = (build_result.stderr or b"") + (build_result.stdout or b"")
        error_output = raw.decode("utf-8", errors="replace")
    return BuildResult(
        success=False,
        elapsed_seconds=elapsed,
        error_message=f"make failed with exit code {build_result.returncode}",
        error_output=error_output,
    )
```

## Open Questions

1. **Should MCU cross-check happen before or after build in Flash All?**
   - Before build saves time (skip build entirely for mismatched devices)
   - But Stage 4 is the flash loop, and USB rescan happens after Klipper stops
   - **Recommendation:** Add cross-check in Stage 4 (flash loop) since that is where USB devices are matched. Could also add a pre-check in Stage 1 with initial scan.

2. **Should `error_output` combine stdout+stderr or just stderr?**
   - Build errors often appear in stderr, but make progress in stdout
   - **Recommendation:** Combine both (stderr first, then stdout) for completeness

## Sources

### Primary (HIGH confidence)
- Direct code analysis of `discovery.py`, `build.py`, `flash.py`, `models.py`
- `extract_mcu_from_serial()` API verified from source
- `run_build()` `quiet` parameter verified from source
- `BatchDeviceResult.skipped` field verified from models.py

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependencies, all stdlib
- Architecture: HIGH - direct code analysis of existing patterns
- Pitfalls: HIGH - based on Python subprocess behavior and existing code patterns

**Research date:** 2026-02-01
**Valid until:** 2026-03-01 (stable codebase, no external dependencies)
