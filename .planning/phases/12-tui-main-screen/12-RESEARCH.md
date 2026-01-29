# Phase 12: TUI Main Screen - Research

**Researched:** 2026-01-29
**Domain:** Terminal user interface with panel-based screen layout and interactive input
**Confidence:** HIGH

## Summary

Phase 12 implements a panel-based TUI main screen using the panel renderer from Phase 11. The implementation uses Python stdlib only (no Rich/Textual) with ANSI escape codes for screen clearing and single-character input via msvcrt (Windows) or termios (Unix). Key challenges: single keypress input without external dependencies, device status tracking across registry/USB scan, and screen refresh timing after command completion.

The codebase already has foundation: Phase 11 provides panel rendering (`render_panel`, `render_two_column`), Phase 10 provides ANSI utilities (`display_width`, `strip_ansi`), and Phase 8-9 provide color theming. Existing `tui.py` has menu infrastructure with `_get_menu_choice()` for validated input and `run_menu()` loop pattern. The main screen extends this pattern with: (1) three panels (Status, Devices, Actions) rendered per refresh, (2) single keypress action selection, (3) device numbering for cross-action reference, and (4) post-command refresh returning to full menu.

**Primary recommendation:** Build on existing `run_menu()` pattern in `tui.py` with full screen redraw on each refresh. Use stdlib-only single character input (msvcrt/termios) wrapped in a reusable function. Implement device status aggregation from registry + USB scan + Moonraker versions as a pure function returning structured data for panel rendering.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib | 3.9+ | All implementation | Project constraint: no external dependencies |
| msvcrt | stdlib | Windows single-char input | Built-in Windows terminal control |
| termios/tty | stdlib | Unix single-char input | Built-in Unix terminal control |
| fnmatch | stdlib | Pattern matching | Device serial pattern matching |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| subprocess | stdlib | Screen clearing (fallback) | When ANSI codes unavailable |
| sys | stdlib | TTY detection, platform checks | Cross-platform compatibility |
| time | stdlib | Post-command delays | Return delay timers |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib input | Rich/Textual | Violates project constraint (no external deps) |
| ANSI clear | curses | curses not portable to Windows, more complex |
| Full redraw | Cursor positioning | Phase context mandates full clear + redraw |

**Installation:**
None - stdlib only per project CLAUDE.md constraint.

## Architecture Patterns

### Pattern 1: Panel-Based Screen Layout
**What:** Top-to-bottom panels (Status, Devices, Actions) rendered as separate panel strings, joined with blank lines, printed once per refresh.

**When to use:** Full-screen TUI with distinct informational zones. Avoids cursor positioning complexity.

**Example:**
```python
from kflash.panels import render_panel, render_two_column, center_panel
from kflash.theme import clear_screen

def render_main_screen(status_data, device_data, action_data):
    """Render full screen with three panels."""
    status_panel = render_panel("status", [status_data.message])
    device_panel = render_panel("devices", device_data.lines)
    action_panel = render_panel("actions", render_two_column(action_data.items))

    # Full clear + redraw
    clear_screen()
    print()
    print(center_panel(status_panel))
    print()
    print(center_panel(device_panel))
    print()
    print(center_panel(action_panel))
    print()
```

**Why this works:** Phase 11 panels handle borders/alignment. Phase 10 ANSI utilities ensure color codes don't break layout. Full redraw avoids cursor state bugs.

### Pattern 2: Device Status Aggregation
**What:** Pure function that takes registry data, USB scan results, and Moonraker versions, returns structured device list with status/version/numbering.

**When to use:** When display logic needs to be separated from data gathering. Enables testing without hardware.

**Example:**
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class DeviceDisplayInfo:
    """Device row data for panel rendering."""
    number: int  # Display number (#1, #2, #3)
    name: str
    serial_short: str  # Truncated serial path
    version: Optional[str]  # Klipper version from Moonraker
    status: str  # "connected" | "disconnected"
    category: str  # "registered" | "new" | "blocked"

def aggregate_device_status(
    registry_data,
    usb_devices,
    mcu_versions,
    host_version,
    blocked_list
) -> list[DeviceDisplayInfo]:
    """Pure function: gather device data for display."""
    # Cross-reference registry vs USB vs Moonraker
    # Assign sequential numbers, truncate serial paths
    # Return flat list for rendering
    pass
```

**Why this works:** Testable without USB hardware. Clear separation: data aggregation vs display rendering.

### Pattern 3: Single Keypress Input (stdlib only)
**What:** Cross-platform single character input without Enter, using msvcrt (Windows) or termios (Unix).

**When to use:** Action selection, quick confirmation prompts. Matches phase requirement for single keypress.

**Example:**
```python
import sys

def getch() -> str:
    """Read single character from stdin without echo (cross-platform)."""
    if sys.platform == "win32":
        import msvcrt
        return msvcrt.getch().decode('utf-8', errors='ignore')
    else:
        import tty
        import termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch
```

**Why this works:** stdlib only (project constraint). Handles platform differences internally. Single function for all single-char needs.

### Pattern 4: Action Dispatch with Device Number Input
**What:** Action key pressed → if device-targeting action, prompt for device number → dispatch to command handler.

**When to use:** Actions that operate on specific devices (Flash, Remove). Number from device panel (#1, #2, etc).

**Example:**
```python
def handle_action_key(key: str, device_list: list[DeviceDisplayInfo], registry, out):
    """Dispatch action based on keypress."""
    if key == "f":  # Flash Device
        # Prompt for device number
        print("Enter device number: ", end="", flush=True)
        num_input = input().strip()
        try:
            idx = int(num_input) - 1
            device = device_list[idx]
            # Call flash command with device
            from .flash import cmd_flash
            cmd_flash(registry, device.key, out)
        except (ValueError, IndexError):
            out.warn(f"Invalid device number: {num_input}")
    elif key == "r":  # Refresh Devices
        # No device selection needed - just re-scan
        pass
    # ... etc
```

**Why this works:** Two-stage input for device-targeting actions. Validates device number against displayed list. Reuses existing command handlers.

### Anti-Patterns to Avoid
- **Cursor positioning:** Phase context mandates full clear + redraw. Don't try to update specific screen regions.
- **Polling loops:** Use blocking input (getch, input) not busy-wait loops checking stdin.
- **Implicit device selection:** Always show numbered list and require explicit number input for device actions.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Panel borders/alignment | Manual padding/ANSI width | Phase 11 `render_panel()` | Already handles ANSI codes, CJK chars |
| Color theming | Raw ANSI codes | Phase 8 `get_theme()` | Terminal capability detection, semantic names |
| Terminal width | Environment parsing | Phase 10 `get_terminal_width()` | Already handles fallbacks, clamping |
| Device discovery | Direct /dev scan | `discovery.py` functions | Pattern matching, blocking, MCU extraction |
| Version comparison | String comparison | `moonraker.py` functions | Git-describe parsing, tag/count comparison |

**Key insight:** Phases 8-11 provide primitives. Phase 12 wires them into an interactive loop. Don't duplicate existing logic.

## Common Pitfalls

### Pitfall 1: ANSI Width Miscalculation with Colored Content
**What goes wrong:** Right panel borders don't align when device names/versions contain color codes.

**Why it happens:** Using `len()` instead of `display_width()` from Phase 10. Color escape sequences contribute to string length but not visible width.

**How to avoid:** Always use `display_width()` for width calculations, `pad_to_width()` for padding. Phase 11 panels already do this.

**Warning signs:** Jagged right borders. Panel content overflowing borders.

### Pitfall 2: Device Number Reordering Between Actions
**What goes wrong:** User selects device #3, presses Flash, but by the time they confirm, a device disconnects and #3 now refers to a different device.

**Why it happens:** Device list regenerated between screen refresh and action execution. Numbers change based on USB scan order.

**How to avoid:** (1) Assign numbers at screen render, store mapping in screen state. (2) Validate device key (not just number) before executing action. (3) Show device name in confirmation prompts.

**Warning signs:** User reports "flashed wrong device." Actions targeting unexpected devices.

### Pitfall 3: Blocking Input Without TTY Check
**What goes wrong:** Non-TTY environment (piped input, cron job) hangs forever waiting for keypress.

**Why it happens:** `getch()` and `input()` block indefinitely when stdin is not a TTY.

**How to avoid:** Check `sys.stdin.isatty()` before entering interactive loop. Exit with error message if non-TTY.

**Warning signs:** Command hangs when run in CI/automation. No error message when stdin redirected.

### Pitfall 4: Screen Flicker on Refresh
**What goes wrong:** Screen flickers or shows partial redraw during refresh.

**Why it happens:** Printing panels line-by-line without buffering. Terminal updates visible mid-render.

**How to avoid:** Build full screen string first, then single `print()` call. Or use `print(..., end="", flush=False)` and single `flush()` at end.

**Warning signs:** Visible flicker during device scan. Top panel briefly shows old content before updating.

## Code Examples

Verified patterns from official sources and existing codebase:

### Screen Clear (from existing theme.py)
```python
# Source: C:\dev_projects\kalico_flash\kflash\theme.py:327-347
from kflash.theme import clear_screen

def refresh_screen():
    """Clear terminal and prepare for full redraw."""
    clear_screen()  # Handles Windows vs Unix, VT mode detection
```

**Notes:** Already implemented in Phase 8. Handles Windows VT mode enablement. Preserves scrollback when possible.

### Device Status Icon (from mockup)
```python
# Source: C:\dev_projects\kalico_flash\.working\UI-working\zen_mockup.py:27-29
from kflash.theme import get_theme

def status_icon(connected: bool) -> str:
    """Return colored status icon."""
    theme = get_theme()
    if connected:
        return f"{theme.success}●{theme.reset}"  # Green filled circle
    else:
        return f"{theme.subtle}○{theme.reset}"  # Grey empty circle
```

**Notes:** Two states only per phase context. Unicode circles (● ○) are widely supported.

### Middle Truncation for Serial Paths
```python
# Custom pattern - no stdlib function for middle ellipsis
def truncate_middle(s: str, max_len: int) -> str:
    """Truncate string in middle with ellipsis, keeping start and end visible."""
    if len(s) <= max_len:
        return s
    if max_len < 5:
        return s[:max_len]

    # Keep first and last portions, insert ellipsis
    side_len = (max_len - 3) // 2  # Reserve 3 chars for "..."
    return s[:side_len] + "..." + s[-(max_len - side_len - 3):]
```

**Notes:** Useful for long serial paths (e.g., `usb-Klipper_stm32h723xx_29001A...313531383332-if00`). Keeps device ID prefix and interface suffix visible.

### Two-Column Action Layout (from Phase 11)
```python
# Source: Phase 11 render_two_column pattern
from kflash.panels import render_two_column

actions = [
    ("f", "Flash Device"),
    ("a", "Add Device"),
    ("r", "Remove Device"),
    ("d", "Refresh Devices"),  # Replaces List Devices
    ("c", "Config"),
    ("x", "Flash All"),
    ("q", "Quit"),
]

# Format as (#key, label) for two_column
action_items = [(f"{i+1}", label) for i, (key, label) in enumerate(actions)]
action_lines = render_two_column(action_items)
```

**Notes:** Phase 11 handles column balancing (left gets extra if odd). Gap between columns is configurable.

### Device Panel with Groups
```python
# Pattern for section headers inside device panel
from kflash.theme import get_theme

def render_device_section(title: str, devices: list[DeviceDisplayInfo]) -> list[str]:
    """Render section header + device rows."""
    theme = get_theme()
    lines = []

    # Section header with icon
    if title == "Registered":
        icon = f"{theme.success}●{theme.reset}"
    elif title == "New":
        icon = f"{theme.warning}○{theme.reset}"
    else:  # Blocked
        icon = f"{theme.error}✗{theme.reset}"

    lines.append(f"  {icon} {theme.bold}{theme.label}{title}{theme.reset}")

    # Divider line
    lines.append(f"  {theme.subtle}{'┄' * 60}{theme.reset}")

    # Device rows
    if not devices:
        lines.append(f"   {theme.subtle}None{theme.reset}")
    else:
        for device in devices:
            status = status_icon(device.status == "connected")
            version_str = device.version or f"{theme.yellow}Unknown{theme.reset}"
            lines.append(
                f"   {theme.label}#{device.number}{theme.reset}  "
                f"{theme.text}{device.name}{theme.reset}      "
                f"{theme.subtle}{device.serial_short}{theme.reset}   "
                f"{theme.text}{version_str}{theme.reset}  {status}"
            )

    return lines
```

**Notes:** Groups: Registered, New, Blocked. Empty groups show "None". Footer outside groups shows host version.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Rich/Textual libraries | Stdlib ANSI codes | Phase 8-10 (2026-01) | No external dependencies, full control |
| Cursor positioning | Full clear + redraw | Phase 12 context | Simpler logic, no cursor state bugs |
| Action name prompts | Single keypress | Phase 12 requirement | Faster UX, matches modern TUI conventions |
| List Devices action | Refresh Devices | Phase 12 requirement | Live status update, better for main screen |

**Deprecated/outdated:**
- `flash.py` numbered menu (1-5 with Enter): Being replaced by single-keypress main screen TUI
- Box-drawing characters in `tui.py` (sharp corners): Phase 11 uses rounded corners from mockup

## Open Questions

1. **Device number input method after action keypress**
   - What we know: Action keys are single keypress. Device-targeting actions need device number.
   - What's unclear: Should device number also be single keypress (limits to 9 devices) or Enter-confirmed input (supports 10+ devices)?
   - Recommendation: Enter-confirmed input for flexibility. Show prompt: "Enter device number: _". Validates against displayed range.

2. **Status panel content on first launch**
   - What we know: Phase context says "welcome message with brief hint"
   - What's unclear: Exact text, whether to show last action across sessions (persistence)
   - Recommendation: Non-persistent welcome. Example: "Welcome to kalico-flash. Select an action below." No persistence needed.

3. **Screen refresh timing after long commands**
   - What we know: Phase context says "screen refreshes after every command completes"
   - What's unclear: If command output is visible (make logs), when does screen refresh? Immediately or after pause?
   - Recommendation: Commands that show output (Flash, Build) should pause before returning to main screen. Add "Press any key to continue" or 3-second auto-return.

4. **Blocked device display in main screen**
   - What we know: Blocked devices shown in device panel, but are they numbered?
   - What's unclear: Should blocked devices get numbers (e.g., #4) or just status icon without number?
   - Recommendation: No numbers for blocked devices. They're not actionable. Show icon + name + reason only.

## Sources

### Primary (HIGH confidence)
- Existing codebase analysis:
  - `C:\dev_projects\kalico_flash\kflash\tui.py` - Menu infrastructure, `_get_menu_choice` pattern
  - `C:\dev_projects\kalico_flash\kflash\panels.py` - Phase 11 panel rendering
  - `C:\dev_projects\kalico_flash\kflash\theme.py` - Phase 8 theming, `clear_screen()`
  - `C:\dev_projects\kalico_flash\kflash\discovery.py` - Device scanning patterns
  - `C:\dev_projects\kalico_flash\kflash\moonraker.py` - Version retrieval functions
- Phase 11 PLAN.md - Panel renderer specification
- Phase 12 CONTEXT.md - Implementation decisions (locked)
- `.working/UI-working/zen_mockup.py` - Visual reference for mockup

### Secondary (MEDIUM confidence)
- [How to clear screen in Python - GeeksforGeeks](https://www.geeksforgeeks.org/python/clear-screen-python/) - ANSI clear patterns
- [Build your own Command Line with ANSI escape codes](https://www.lihaoyi.com/post/BuildyourownCommandLinewithANSIescapecodes.html) - ANSI fundamentals

### Tertiary (LOW confidence)
- [Python TUI best practices 2026](https://dev.to/lazy_code/5-best-python-tui-libraries-for-building-text-based-user-interfaces-5fdi) - General TUI patterns (library-focused)
- [Python getch cross-platform](https://www.pythontutorials.net/blog/how-to-read-a-single-character-from-the-user/) - Single char input techniques
- [String truncation patterns](https://coderivers.org/blog/string-truncate-python/) - General truncation (no middle-truncate specifics)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - stdlib only verified by project constraint and existing implementation
- Architecture: HIGH - Patterns derived from existing codebase (Phases 8-11) and proven TUI conventions
- Pitfalls: HIGH - Based on common TUI bugs and Phase 10 ANSI width issues already solved
- Code examples: HIGH - All examples from existing codebase or verified stdlib patterns

**Research date:** 2026-01-29
**Valid until:** 2026-02-28 (30 days - stable domain, stdlib patterns change slowly)
