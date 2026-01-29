# Architecture Patterns

**Domain:** TUI panel redesign and batch flash for kalico-flash
**Researched:** 2026-01-29
**Confidence:** HIGH (based on direct codebase analysis)

## Current Architecture Summary

Hub-and-spoke: `flash.py` is the sole orchestrator. Modules do not cross-import (except `tui.py` late-imports `flash.cmd_*` functions). Data flows through dataclasses in `models.py`. Theme is a cached singleton in `theme.py`. Output is a Protocol-based pluggable interface in `output.py`.

Key observation: `tui.py` currently owns both rendering (box drawing, menu layout) and input handling (choice selection, dispatch). These are interleaved in the same functions.

## Recommended Architecture for New Features

### Component Map: New vs Modified

| Component | Status | Purpose |
|-----------|--------|---------|
| `panels.py` | **NEW** | Panel rendering engine (box drawing, layout, content formatting) |
| `tui.py` | **MODIFY** | Refactor to use panels.py for rendering, add Flash All menu option |
| `theme.py` | **MODIFY** | Add truecolor support, panel-specific styles (border, heading, divider) |
| `models.py` | **MODIFY** | Add `BatchFlashResult` dataclass |
| `flash.py` | **MODIFY** | Add `cmd_flash_all()` orchestrator function |
| `output.py` | **MODIFY** | Add `divider()` method to Output Protocol and CliOutput |
| `service.py` | **NO CHANGE** | Existing context manager works as-is for batch flash |
| `flasher.py` | **NO CHANGE** | Per-device flash logic unchanged |

### Why a New `panels.py` Module

The current `tui.py` mixes rendering with input/dispatch. The new panel system (Status, Devices, Actions panels with box drawing) is a rendering concern. Keeping it in `tui.py` would bloat that module and make panel rendering unavailable to other contexts.

`panels.py` should be a pure rendering module:
- Takes data in, returns strings out
- No input handling, no side effects
- Consumes `theme.py` for styling
- Called by `tui.py` for the interactive menu

This preserves hub-and-spoke: `tui.py` calls `panels.py` for rendering, `flash.py` for actions. `panels.py` does not import either.

### Component Boundaries

```
flash.py (orchestrator)
  |
  +-- tui.py (input loop + dispatch)
  |     |
  |     +-- panels.py (pure rendering, returns strings)
  |     |     |
  |     |     +-- theme.py (color codes)
  |     |
  |     +-- flash.cmd_* (late imports for actions)
  |
  +-- cmd_flash_all() (new, in flash.py)
        |
        +-- service.klipper_service_stopped() (single context manager)
        +-- config.ConfigManager (per device)
        +-- build.run_build() (per device)
        +-- flasher.flash_device() (per device)
        +-- tui.wait_for_device() (per device)
```

## Flash All Data Flow

This is the critical architectural decision. The key constraint: Klipper must be stopped only ONCE for the entire batch, not per-device.

### Recommended: `cmd_flash_all()` in `flash.py`

Add a new function in `flash.py` (the existing orchestrator) rather than a new module. Rationale: batch flash is orchestration logic, and `flash.py` already orchestrates single-device flash. A separate `batch.py` would duplicate imports and break the pattern that `flash.py` is the single orchestration hub.

### Data Flow

```
cmd_flash_all(registry, out, skip_menuconfig):
  1. Load registry, get all flashable+connected devices
  2. Preflight ALL devices (validate configs, MCU types)
  3. Safety check: Moonraker print status (once)
  4. Build ALL devices sequentially (Klipper still running)
     - For each device: load config -> optional menuconfig -> validate MCU -> make clean + make
     - Collect BuildResult per device
     - STOP on first build failure (don't flash partial set)
  5. Stop Klipper ONCE:
     with klipper_service_stopped(out=out):
       for device in devices:
         flash_device(...)          # existing function
         wait_for_device(...)       # verify before next device
  6. Klipper restarts (context manager exit)
  7. Report summary: per-device success/failure
```

### New Dataclass

```python
@dataclass
class BatchFlashResult:
    """Result of a batch flash operation."""
    total: int
    succeeded: list[str]       # device keys
    failed: list[tuple[str, str]]  # (device_key, error_message)
    elapsed_seconds: float
```

### Why Build Before Stop, Flash Inside Stop

Building firmware does NOT require Klipper to be stopped (make runs against source, not running firmware). Flashing DOES require Klipper stopped (it holds the serial port). This minimizes Klipper downtime.

### Error Handling Strategy

- Build failure on any device: abort entire batch before stopping Klipper. No partial flash.
- Flash failure on one device: log failure, continue flashing remaining devices. Rationale: Klipper is already stopped, other devices still need flashing.
- Verification failure: log warning, continue. Device may need manual intervention later.

## Panel Rendering Architecture

### `panels.py` API Surface

```python
def render_status_panel(message: str, style: str, width: int) -> str:
    """Render the status panel (last command result)."""

def render_device_panel(
    devices: list[DeviceDisplayInfo],
    width: int,
) -> str:
    """Render the device panel with grouped numbered devices."""

def render_actions_panel(
    options: list[tuple[str, str]],
    width: int,
) -> str:
    """Render the actions panel (menu options)."""

def render_config_panel(
    settings: dict[str, str],
    width: int,
) -> str:
    """Render the config/settings panel."""

@dataclass
class DeviceDisplayInfo:
    """Display-ready device info for panel rendering."""
    number: int
    key: str
    name: str
    mcu: str
    status: str          # "connected", "disconnected", "excluded", "blocked"
    version: str | None
```

Key design: panels return multi-line strings. `tui.py` composes them (decides layout order, spacing) and prints. This means `panels.py` has zero I/O.

### Panel Composition in `tui.py`

```python
def _render_main_screen(registry_data, usb_devices, status_msg) -> str:
    """Compose all panels into a single screen."""
    width = _get_terminal_width()
    parts = []
    parts.append(render_status_panel(status_msg, width))
    parts.append(render_device_panel(device_infos, width))
    parts.append(render_actions_panel(MENU_OPTIONS, width))
    return "\n".join(parts)
```

### Config Screen

The config screen replaces the current `_settings_menu()` loop. Instead of a separate box-drawn menu, it renders a config panel showing current values with numbered edit options. Same pattern: `panels.py` renders, `tui.py` handles input.

## Theme Upgrade Path

### Current: 16-color ANSI

```python
_GREEN = "\033[92m"  # Bright green
```

### Target: Truecolor with fallback

```python
# In theme.py
def _truecolor(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"

def supports_truecolor() -> bool:
    """Check COLORTERM env var for truecolor/24bit."""
    colorterm = os.environ.get("COLORTERM", "").lower()
    return colorterm in ("truecolor", "24bit")
```

Add a third theme tier: `_truecolor_theme`, `_color_theme` (existing 16-color), `_no_color_theme`. Detection order: NO_COLOR -> FORCE_COLOR -> truecolor check -> TTY check.

Theme dataclass adds new fields for panels:

```python
# New fields
panel_border: str     # Box drawing color
panel_heading: str    # Panel title color
divider: str          # Step divider color
status_ok: str        # Status panel success
status_fail: str      # Status panel failure
device_connected: str
device_disconnected: str
```

## Step Dividers

Add `divider(label: str)` to the Output Protocol:

```python
def divider(self, label: str) -> None:
    """Print a labeled horizontal divider."""
    t = self.theme
    line = t.divider + "--- " + label + " " + "-" * (60 - len(label)) + t.reset
    print(line)
```

This is a minor Output Protocol extension. Add to CliOutput and NullOutput.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Putting batch logic in flasher.py
**Why bad:** flasher.py is a leaf module for single-device flash. Adding batch orchestration (service lifecycle, build coordination) violates its single responsibility and the hub-and-spoke pattern.
**Instead:** Keep batch orchestration in flash.py.

### Anti-Pattern 2: Panels that call input()
**Why bad:** Couples rendering to terminal I/O, prevents reuse for future Moonraker output.
**Instead:** Panels return strings. tui.py handles all input().

### Anti-Pattern 3: Stopping Klipper per-device in batch
**Why bad:** Unnecessary service churn. Each stop/start cycle takes ~5-10 seconds and risks race conditions with device enumeration.
**Instead:** Single stop before all flashes, single start after.

### Anti-Pattern 4: New orchestrator module for batch
**Why bad:** Creates a second hub alongside flash.py, breaking the single-orchestrator pattern.
**Instead:** cmd_flash_all() lives in flash.py next to cmd_flash().

## Suggested Build Order

Build in this order to maintain a working system at each step:

1. **Theme upgrade** (theme.py only) - Add truecolor detection and new style fields. Zero risk, no other module changes needed. Existing code continues to work because new fields have defaults.

2. **Output Protocol extension** (output.py) - Add `divider()` method. Backward compatible addition.

3. **Panel renderer** (new panels.py) - Pure rendering module. Can be built and tested in isolation since it just returns strings.

4. **TUI refactor** (tui.py) - Replace `_render_menu()` with panel-based composition. Replace `_settings_menu()` with config panel. This is the integration point.

5. **BatchFlashResult model** (models.py) - Add dataclass. No impact on existing code.

6. **Flash All command** (flash.py) - Add `cmd_flash_all()`, wire into TUI menu and argparse. This depends on everything above being stable.

### Dependency Graph

```
theme.py (step 1) <-- panels.py (step 3) <-- tui.py (step 4)
output.py (step 2) <------------------------------/
models.py (step 5) <-- flash.py cmd_flash_all (step 6)
                        service.py (no change) <--/
                        flasher.py (no change) <--/
```

## Sources

- Direct codebase analysis of all 10 Python modules in `kflash/`
- Architecture patterns from existing CLAUDE.md documentation
