---
phase: quick-002
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - kflash/flash.py
  - kflash/moonraker.py
autonomous: true

must_haves:
  truths:
    - "List devices shows MCU software version under each registered device"
    - "List devices shows [Blocked devices] label before blocked section"
    - "List devices shows host Klipper version at the end"
    - "Flash device menu shows MCU version under each flashable device"
    - "Flash device menu shows host version before selection prompt"
  artifacts:
    - path: "kflash/flash.py"
      provides: "Updated cmd_list_devices and cmd_flash with version display"
    - path: "kflash/moonraker.py"
      provides: "Function to get MCU version for a specific device"
  key_links:
    - from: "kflash/flash.py"
      to: "kflash/moonraker.py"
      via: "get_mcu_version_for_device import"
      pattern: "get_mcu_version_for_device"
---

<objective>
Display MCU firmware versions and host Klipper version in list devices and flash device menus.

Purpose: Users need to see which MCU firmware versions are running to identify outdated boards before flashing.
Output: Enhanced list/flash menus with version information.
</objective>

<context>
@kflash/flash.py - cmd_list_devices (lines 1059-1188), cmd_flash discovery section (lines 589-618)
@kflash/moonraker.py - get_mcu_versions(), get_host_klipper_version()
@kflash/output.py - Output interface with device_line method
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add MCU version lookup helper to moonraker.py</name>
  <files>kflash/moonraker.py</files>
  <action>
Add a new function `get_mcu_version_for_device(mcu_type: str) -> Optional[str]` that:
1. Calls existing `get_mcu_versions()` to get all MCU versions
2. Attempts to match the device's mcu_type (e.g., "stm32h723", "rp2040") to a Moonraker MCU name
3. Matching logic (in order):
   - Exact match on MCU name (e.g., device mcu "nhk" matches Moonraker "nhk")
   - If device mcu contains the Moonraker mcu name or vice versa
   - Fall back to "main" for primary MCU if no match found
4. Returns the version string or None if unavailable

This centralizes the MCU-to-version mapping logic that's currently duplicated in cmd_flash.
  </action>
  <verify>
SSH to Pi and run Python:
```
python3 -c "from kflash.moonraker import get_mcu_version_for_device; print(get_mcu_version_for_device('stm32h723')); print(get_mcu_version_for_device('rp2040'))"
```
Should return version strings like "v2026.01.00-0-g4a173af8" or None if Klipper not running.
  </verify>
  <done>Function returns correct MCU version for given mcu_type string</done>
</task>

<task type="auto">
  <name>Task 2: Update cmd_list_devices with version display</name>
  <files>kflash/flash.py</files>
  <action>
Modify `cmd_list_devices` function to:

1. At the start, after loading registry and USB devices, fetch versions:
   - Import `get_mcu_versions, get_host_klipper_version` from moonraker
   - Call `get_host_klipper_version(data.global_config.klipper_dir)` if global_config exists
   - Call `get_mcu_versions()` to get all MCU versions

2. After each registered device line (around line 1170), add indented version line:
   - After `out.device_line("REG", name_str, device.filename)` or similar
   - Add: `out.info("", f"       MCU software version {version}")` where version comes from matching mcu_versions
   - Use the existing matching logic: check if entry.mcu matches any key in mcu_versions, fall back to "main"
   - Only show version line if version is available

3. Before the unmatched devices section (around line 1175), add a "Blocked devices" label:
   - Before iterating over blocked devices, add: `out.info("Blocked devices", "")`
   - But only if there are blocked devices to show

4. Remove the "[Devices] Use --add-device to register unknown devices." line (line 1186):
   - This line should only appear in non-menu context
   - Add a parameter `from_menu: bool = False` to cmd_list_devices
   - Only show this line if `from_menu=False`

5. At the end of the function, add host version line:
   - Add: `out.info("Version", f"Host Klipper: {host_version}")` if host_version is available

6. Update `_action_list_devices` in tui.py to pass `from_menu=True`.
  </action>
  <verify>
SSH to Pi and run:
```
cd ~/kalico-flash && python3 -m kflash --list-devices
```
Should show:
- Registered devices with MCU version on indented line below
- "[Blocked devices]" label before blocked section
- "[Version] Host Klipper: vX.X.X" at the end
  </verify>
  <done>
List devices shows MCU version under each device, blocked devices label, host version at end.
No "Use --add-device" hint when called from menu.
  </done>
</task>

<task type="auto">
  <name>Task 3: Update flash device menu with version display</name>
  <files>kflash/flash.py</files>
  <action>
Modify `cmd_flash` function in the interactive discovery section (around lines 589-618):

1. After showing the flashable devices list header (line 590), modify the device listing loop:
   - After `out.device_line(str(i + 1), f"{entry.key} ({entry.mcu})", device.filename)`
   - Add version line: `out.info("", f"     MCU software version {version}")`
   - Get version by matching entry.mcu against mcu_versions dict
   - Only show if version is available

2. After the device list but before the selection prompt:
   - Add host version: `out.info("Version", f"Host Klipper: {host_version}")`
   - Only if host_version is available
   - This goes right before the "Select device number" prompt

The mcu_versions and host_version should already be available from the existing version info section (lines 736-780), but that runs AFTER device selection. Move the version fetching earlier:
- Fetch mcu_versions and host_version after loading registry data (around line 443)
- Store in local variables for use in both discovery display and later version check
  </action>
  <verify>
SSH to Pi and run:
```
cd ~/kalico-flash && python3 -m kflash
```
Select "3) Flash Device" from menu. Should show:
- Each flashable device with MCU version on indented line below
- "[Version] Host Klipper: vX.X.X" before selection prompt
  </verify>
  <done>
Flash device menu shows MCU version under each device and host version before prompt.
  </done>
</task>

</tasks>

<verification>
1. Run `python3 -m kflash --list-devices` on Pi with Klipper running
2. Verify MCU versions appear under each registered device
3. Verify "[Blocked devices]" label appears before blocked section
4. Verify host version appears at end
5. Run interactive menu, select Flash Device
6. Verify MCU versions appear under each flashable device
7. Verify host version appears before selection prompt
8. Test with Klipper stopped - versions should gracefully not appear
</verification>

<success_criteria>
- List devices shows MCU software version indented under each registered device
- List devices shows "[Blocked devices]" label before blocked devices section
- List devices shows "[Version] Host Klipper: vX.X.X" at end
- Flash device menu shows MCU version indented under each flashable device
- Flash device menu shows host version before selection prompt
- Graceful degradation when Moonraker/Klipper unavailable (no versions shown)
</success_criteria>

<output>
After completion, create `.planning/quick/002-mcu-version-display/002-SUMMARY.md`
</output>
