# Phase 1: Foundation & Device Management - Context

**Gathered:** 2026-01-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Architecture skeleton and device management modules — registry CRUD, USB discovery, dataclass contracts, pluggable output pattern. User can register, list, remove, and discover USB-connected MCU boards through importable Python modules. Building and flashing are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Add-device wizard flow
- No USB devices detected = error and exit ("No USB devices found. Plug in a board and try again.")
- Serial pattern auto-generated from full serial number (most specific, e.g., `usb-Klipper_stm32h723xx_29001A001151313531383332*`)
- MCU type auto-extracted from serial path, shown to user for confirmation ("Detected MCU: stm32h723. Correct? [Y/n]")
- klipper_dir and katapult_dir use smart defaults (~/klipper, ~/katapult), user confirms or changes
- Device key (used for --device flag) is user-chosen freeform (e.g., "octopus-pro")

### Output & feedback style
- No ANSI color — plain text only
- Verbosity: phase labels + summary (e.g., "[Discovery] Found 2 devices...")
- Text markers for status: [OK] success, [FAIL] failure, [??] unknown — no Unicode symbols
- Concise on success, detailed on failure

### Pluggable output interface
- Claude's discretion on implementation pattern (callback, events, or other)
- Must support future Moonraker integration without rewriting core modules

### Registry schema
- Device key: user-chosen string (prompted during wizard)
- Fields: name (display), mcu, serial_pattern, flash_method
- flash_method: per-device with global default (katapult+fallback is default, device can override to make_flash-only)
- klipper_dir: GLOBAL, not per-device — single klipper source for all boards
- katapult_dir: GLOBAL, not per-device
- Keep schema minimal — no notes field, no git hash tracking
- Global paths (klipper_dir, katapult_dir) stored separately from device entries in devices.json (or in a config section)

### Device listing presentation
- Compact list format: one line per device (e.g., "octopus-pro: Octopus Pro v1.1 (stm32h723) [OK] /dev/serial/by-id/usb-Klipper_...")
- Connected devices show actual serial path
- Disconnected devices show status marker only: "[--] (disconnected)"
- Unknown devices appear inline with registration prompt: "[??] Unknown device [usb-Klipper_rp2040_E66...] — press 'a' to register"
- Empty registry + first run: auto-detect USB devices and offer to register ("No registered devices. Found 2 USB devices. Register one now? [y/N]")

### Claude's Discretion
- Pluggable output interface design (callback function, event emitter, or other pattern)
- Exact dataclass field types and defaults
- Module internal structure and helper functions
- Error message wording specifics

</decisions>

<specifics>
## Specific Ideas

- The tool should feel like a focused utility — not a framework. Simple prompts, no menus within menus.
- First-run experience should be smooth: detect boards, offer to register, get the user set up without reading docs.
- The flash_script_plan.md example session shows the target UX:
  ```
  [Discovery] Scanning /dev/serial/by-id/...
    [OK] Octopus Pro v1.1  [/dev/serial/by-id/usb-Klipper_stm32h723xx_2A003...]
    [OK] EBB36 v1.2        [/dev/serial/by-id/usb-Katapult_stm32g0b1xx_1F00...]
    [??] Unknown device     [/dev/serial/by-id/usb-Klipper_rp2040_E66...]
  ```

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-foundation-device-management*
*Context gathered: 2026-01-25*
