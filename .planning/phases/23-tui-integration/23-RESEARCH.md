# Phase 23: TUI Integration - Research

**Researched:** 2026-01-31
**Domain:** Wiring Phase 22 check_katapult() into the existing device config TUI screen
**Confidence:** HIGH

## Summary

This phase integrates the `check_katapult()` function (delivered in Phase 22) into the device config screen (`_device_config_screen` in `tui.py`). The integration point is well-defined: add a "K" key handler in the device config screen's keypress dispatch loop, with a warning/confirmation gate, service lifecycle wrapping, and result display.

The existing codebase provides all building blocks: `check_katapult()` with `log` callback, `klipper_service_stopped()` context manager, themed output via `get_theme()`, and the `_getch()` / `input()` patterns already used throughout the TUI.

**Primary recommendation:** Add a "K" key handler in `_device_config_screen()` that follows the exact same pattern as the existing "5" (menuconfig) handler: print the key, show warning, get confirmation via `input()`, wrap the operation in `klipper_service_stopped()`, call `check_katapult()`, display result, then loop back.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib | 3.9+ | Everything | Project constraint: no external deps |

### Supporting
No additional libraries needed. All required functionality exists in the codebase:

| Module | Purpose | Already Exists |
|--------|---------|----------------|
| `kflash.flasher.check_katapult` | Katapult detection | Yes (Phase 22) |
| `kflash.service.klipper_service_stopped` | Service lifecycle | Yes |
| `kflash.theme.get_theme` | Themed output | Yes |
| `kflash.tui._getch` | Single keypress input | Yes |
| `kflash.discovery.scan_serial_devices` | Find device path | Yes |

### Alternatives Considered
None. This is purely wiring existing components together.

## Architecture Patterns

### Pattern 1: Device Config Screen Key Handler
**What:** The `_device_config_screen()` function uses a while-loop with `_getch()` dispatch. Keys "1"-"5" map to settings, "Esc"/"B" saves and returns, Ctrl+C discards.
**When to use:** Adding any new action to the device config screen.
**Current dispatch structure (tui.py line ~822):**
```python
if key in ("1", "2", "3", "4", "5"):
    # numbered setting handlers
elif key == "\x1b" or key == "b":
    # save and return
elif key == "\x03":
    # discard (ctrl+c)
```

The "K" key handler goes as a new `elif` branch after the numbered settings block, before the escape/return handlers.

### Pattern 2: Warning + Confirmation Gate
**What:** Display warning text, prompt user with default-No confirmation.
**Example from existing codebase (tui.py line ~560, unregistered device prompt):**
```python
answer = (
    input(f"  {theme.prompt}Device not registered. Add it now? (y/n):{theme.reset} ")
    .strip()
    .lower()
)
if answer in ("y", "yes"):
    # proceed
```

For the Katapult check, use the same pattern but with a warning message first and default to "n":
```python
print(f"  {theme.warning}Warning: This will briefly put the device into bootloader mode.{theme.reset}")
print(f"  {theme.warning}The device will be recovered automatically afterward.{theme.reset}")
answer = input(f"  {theme.prompt}Proceed with Katapult check? (y/N):{theme.reset} ").strip().lower()
if answer not in ("y", "yes"):
    continue  # back to device config loop
```

### Pattern 3: Service Lifecycle Wrapping
**What:** Use the `klipper_service_stopped()` context manager to stop Klipper before the check and guarantee restart.
**Source:** `kflash/service.py` line 142
```python
from .service import klipper_service_stopped
with klipper_service_stopped(out=out):
    result = check_katapult(device_path, serial_pattern, katapult_dir, log=log_fn)
```

### Pattern 4: Log Callback for Progress Display
**What:** `check_katapult()` accepts an optional `log` callback for progress messages.
**Implementation:**
```python
def log_fn(msg: str) -> None:
    print(f"  {theme.info}{msg}{theme.reset}")
```

### Pattern 5: Result Display (Tri-State)
**What:** `KatapultCheckResult.has_katapult` is True/False/None. Display differently for each.
```python
if result.has_katapult is True:
    print(f"  {theme.success}Katapult bootloader detected{theme.reset}")
elif result.has_katapult is False:
    print(f"  {theme.info}No Katapult bootloader detected{theme.reset}")
else:  # None = inconclusive
    print(f"  {theme.warning}Inconclusive: {result.error_message}{theme.reset}")
```

### Pattern 6: Resolving Device Path from DeviceEntry
**What:** The device config screen has access to `device_key` (the registry key) but `check_katapult()` needs a concrete `/dev/serial/by-id/...` path. Must scan USB to find the matching device.
**Implementation:** Reuse the pattern from `_action_add_device` (tui.py line ~411):
```python
from .discovery import scan_serial_devices, match_devices
entry = registry.get(device_key)
usb_devices = scan_serial_devices()
matches = match_devices(entry.serial_pattern, usb_devices)
if not matches:
    print(f"  {theme.error}Device not connected{theme.reset}")
    continue
device_path = matches[0].path
```

### Anti-Patterns to Avoid
- **Don't add "K" as a numbered setting (6):** It is an action, not a persistent setting. The existing DEVICE_SETTINGS list drives the numbered settings panel. "K" is a separate key action like Esc/B.
- **Don't skip the service lifecycle:** Even though check_katapult handles device recovery, Klipper must be stopped first because it holds the serial port open.
- **Don't auto-proceed without confirmation:** The check puts the device into bootloader mode, which is disruptive. Default must be No.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Service stop/start | Manual systemctl calls | `klipper_service_stopped()` | Guaranteed restart on all code paths |
| Device path resolution | Manual /dev scanning | `scan_serial_devices()` + `match_devices()` | Handles edge cases, patterns |
| Katapult detection | Custom USB probing | `check_katapult()` | Phase 22 handles all recovery paths |
| Themed output | Raw print | `get_theme()` colors | Consistent with rest of TUI |

## Common Pitfalls

### Pitfall 1: Device Not Connected
**What goes wrong:** User presses "K" but the device is disconnected (registered but not plugged in).
**Why it happens:** Device config screen shows registered devices regardless of connection status.
**How to avoid:** Check USB connection before proceeding. If `match_devices()` returns empty list, show error and return to config screen.
**Warning signs:** `check_katapult()` called with stale/nonexistent path.

### Pitfall 2: Klipper Not Stopped Before Check
**What goes wrong:** `check_katapult()` runs flashtool.py -r but Klipper has the serial port open, causing the bootloader entry command to fail.
**Why it happens:** Forgetting to wrap in `klipper_service_stopped()`.
**How to avoid:** Always wrap the check_katapult call in the context manager.

### Pitfall 3: Katapult Dir Not Configured
**What goes wrong:** `check_katapult()` needs katapult_dir to find flashtool.py.
**Why it happens:** User hasn't set katapult_dir in global config.
**How to avoid:** Load `GlobalConfig.katapult_dir` from registry before calling. The function itself returns an error result if flashtool.py is missing, so this is handled gracefully.

### Pitfall 4: Exception Masking Service Restart
**What goes wrong:** An unhandled exception in the K handler could bypass the finally block if not properly structured.
**Why it happens:** Using `klipper_service_stopped()` as context manager already guarantees restart via finally. Just ensure the `with` block is used correctly.
**How to avoid:** Put check_katapult call inside the `with` block. The context manager handles everything.

### Pitfall 5: Screen Rendering After Action
**What goes wrong:** After the check completes, the device config screen should re-render cleanly.
**Why it happens:** The while loop in `_device_config_screen` already clears screen and re-renders on each iteration. Just `continue` after the K action completes.
**How to avoid:** Don't add extra rendering; let the loop handle it naturally.

## Code Examples

### Complete "K" Key Handler (recommended implementation)
```python
elif key == "k":
    print(key)
    print()
    # Check device is connected
    from .discovery import match_devices, scan_serial_devices
    from .flasher import check_katapult
    from .service import klipper_service_stopped

    entry = registry.get(original_key)
    if entry is None:
        continue

    usb_devices = scan_serial_devices()
    matches = match_devices(entry.serial_pattern, usb_devices)
    if not matches:
        print(f"  {theme.error}Device not connected. Cannot check Katapult.{theme.reset}")
        input("  Press Enter to continue...")
        continue

    device_path = matches[0].path

    # Warning
    print(f"  {theme.warning}Warning: This will briefly put the device into bootloader mode.{theme.reset}")
    print(f"  {theme.warning}The device will be recovered automatically afterward.{theme.reset}")
    print()

    # Confirmation (default No)
    try:
        answer = input(f"  {theme.prompt}Proceed with Katapult check? (y/N):{theme.reset} ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = "n"

    if answer not in ("y", "yes"):
        continue

    # Execute with service lifecycle
    gc = registry.load_global()

    def log_fn(msg: str) -> None:
        print(f"  {theme.info}{msg}{theme.reset}")

    try:
        with klipper_service_stopped(out=out):
            result = check_katapult(
                device_path=device_path,
                serial_pattern=entry.serial_pattern,
                katapult_dir=gc.katapult_dir,
                log=log_fn,
            )
    except Exception as exc:
        print(f"  {theme.error}Error: {exc}{theme.reset}")
        input("  Press Enter to continue...")
        continue

    # Display result
    print()
    if result.has_katapult is True:
        print(f"  {theme.success}Katapult bootloader detected ({result.elapsed_seconds:.1f}s){theme.reset}")
    elif result.has_katapult is False:
        print(f"  {theme.info}No Katapult bootloader detected ({result.elapsed_seconds:.1f}s){theme.reset}")
    else:
        print(f"  {theme.warning}Inconclusive: {result.error_message}{theme.reset}")

    input("  Press Enter to continue...")
```

## State of the Art

No changes from previous phases. This is pure integration work using existing components.

## Open Questions

1. **Should "K" appear in the device config screen's rendered panel?**
   - What we know: Current device config screen shows numbered settings 1-5 in a panel, plus Esc/B hint in the prompt. "K" is not currently shown.
   - Recommendation: Add a hint line below the settings panel or in the prompt text, e.g. `"Setting # / K=Katapult check (or Esc/B to save & return)"`. This is a minor UI decision the planner can specify.

2. **Should the result be persisted anywhere?**
   - What we know: Requirements say "display clearly" but don't mention persistence.
   - Recommendation: Don't persist. Just display and return to config screen. Keep it simple.

## Sources

### Primary (HIGH confidence)
- Direct code reading of `kflash/tui.py` (device config screen implementation)
- Direct code reading of `kflash/flasher.py` (check_katapult function signature and behavior)
- Direct code reading of `kflash/service.py` (klipper_service_stopped context manager)
- Direct code reading of `kflash/models.py` (KatapultCheckResult dataclass)
- Direct code reading of `kflash/screen.py` (DEVICE_SETTINGS, render_device_config_screen)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no external deps, all stdlib
- Architecture: HIGH - all patterns directly observed in existing code
- Pitfalls: HIGH - derived from understanding the actual code flow

**Research date:** 2026-01-31
**Valid until:** 2026-03-31 (stable; no external dependencies to change)
