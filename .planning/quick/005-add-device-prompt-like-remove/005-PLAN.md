---
phase: quick-005
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - kflash/tui.py
  - kflash/flash.py
autonomous: true

must_haves:
  truths:
    - "Pressing 'a' in TUI shows 'Device #:' prompt, not a discovery list"
    - "Only new/unregistered devices are selectable for add"
    - "After selecting a device number, the registration wizard runs (key, name, MCU, etc.)"
    - "cmd_add_device from CLI (--add-device) still works unchanged with full discovery output"
  artifacts:
    - path: "kflash/tui.py"
      provides: "TUI add-device action using _prompt_device_number"
    - path: "kflash/flash.py"
      provides: "Refactored cmd_add_device accepting optional pre-selected device"
  key_links:
    - from: "kflash/tui.py _action_add_device"
      to: "kflash/flash.py cmd_add_device"
      via: "Pass pre-selected DiscoveredDevice to skip discovery/selection"
---

<objective>
Make the TUI add-device action prompt "Device #:" like remove and flash do, instead of reprinting the full discovery list. The TUI already shows all devices in the DEVICES panel.

Purpose: Consistent UX across TUI actions; no redundant output.
Output: Modified tui.py and flash.py with streamlined TUI add flow.
</objective>

<context>
@kflash/tui.py
@kflash/flash.py
@kflash/screen.py (DeviceRow dataclass with group field)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Refactor cmd_add_device to accept optional pre-selected device</name>
  <files>kflash/flash.py</files>
  <action>
Add an optional parameter `selected_device=None` to `cmd_add_device(registry, out, selected_device=None)`.

When `selected_device` is provided (a DiscoveredDevice object):
- Skip the entire discovery scan, device listing, and selection prompt (lines ~1532-1631)
- Jump directly to the "already registered?" check at line 1636 using the pre-selected device
- Still need to scan devices for the duplicate pattern check at line 1712, so do a quick `scan_serial_devices()` there (the `devices` variable is used by `match_devices` on line 1712)
- For the `existing_entry` check: look up if the selected device matches any registry entry using `match_devices` against registry entries, set `existing_entry` accordingly (or None if new)

When `selected_device` is None (CLI --add-device path): behavior is completely unchanged.

This keeps the CLI path untouched while allowing the TUI to bypass discovery output.
  </action>
  <verify>
Run `python -c "from kflash.flash import cmd_add_device; help(cmd_add_device)"` on Pi to confirm signature.
Run `ssh yanceya@192.168.50.50 "cd ~/kalico-flash && python3 flash.py --add-device"` to verify CLI path still works.
  </verify>
  <done>cmd_add_device accepts optional selected_device param; CLI behavior unchanged.</done>
</task>

<task type="auto">
  <name>Task 2: Update TUI add-device action to use Device # prompt</name>
  <files>kflash/tui.py</files>
  <action>
In tui.py, modify the `elif key == "a":` block (line ~452-455) to match the remove/flash pattern:

```python
elif key == "a":
    print(key)
    device_key, device_row = _prompt_new_device_number(device_map, out)
    if device_row:
        status_message, status_level = _action_add_device(
            registry, out, device_row
        )
        _countdown_return(registry.load().global_config.return_delay)
    else:
        status_message = "Add: no device selected"
        status_level = "warning"
```

Create `_prompt_new_device_number(device_map, out)` function that:
- Filters device_map to only rows where `row.group == "new"`
- If no new devices: `out.warn("No new devices to add.")` and return `(None, None)`
- If exactly one new device: auto-select it (like `_prompt_device_number` does)
- Otherwise: prompt "  Device #: " and validate input against the filtered new-device numbers
- Returns `(key, DeviceRow)` or `(None, None)`

Update `_action_add_device` signature to accept optional `device_row` parameter:
```python
def _action_add_device(registry, out, device_row=None) -> tuple[str, str]:
```

When `device_row` is provided:
- Import `DiscoveredDevice` from models and `scan_serial_devices` from discovery
- Find the matching DiscoveredDevice by scanning and matching `device_row.serial_path` against scan results
- Pass it to `cmd_add_device(registry, out, selected_device=matched_device)`

When `device_row` is None (shouldn't happen from TUI anymore, but keep for safety):
- Existing behavior: `cmd_add_device(registry, out)`
  </action>
  <verify>
SCP files to Pi and run TUI: `ssh -t yanceya@192.168.50.50 "cd ~/kalico-flash && python3 flash.py"`
Press 'a' and verify it shows "Device #:" prompt instead of discovery list.
  </verify>
  <done>TUI add-device shows "Device #:" prompt matching remove/flash behavior; only new devices selectable.</done>
</task>

</tasks>

<verification>
1. TUI: Press 'a' -> see "Device #:" prompt (no discovery list printed)
2. TUI: Press 'a' with no new devices -> see "No new devices to add" warning
3. CLI: `--add-device` still shows full discovery list and works as before
4. TUI: Successfully register a new device through the streamlined flow
</verification>

<success_criteria>
- TUI add-device action prompts "Device #:" on a single line, consistent with remove and flash
- No discovery output printed in TUI context
- CLI --add-device behavior completely unchanged
- New device registration wizard (key, name, MCU, flash method) still runs after selection
</success_criteria>

<output>
After completion, create `.planning/quick/005-add-device-prompt-like-remove/005-SUMMARY.md`
</output>
