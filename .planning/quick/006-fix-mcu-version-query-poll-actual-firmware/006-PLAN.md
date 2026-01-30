---
phase: q-006
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - kflash/moonraker.py
  - kflash/screen.py
autonomous: true

must_haves:
  truths:
    - "Each device shows its own MCU firmware version, not the main MCU version"
    - "Devices with no matching MCU return None instead of main's version"
  artifacts:
    - path: "kflash/moonraker.py"
      provides: "chip-type-keyed version entries from mcu_constants.MCU"
    - path: "kflash/screen.py"
      provides: "_lookup_version returns None on no match"
  key_links:
    - from: "kflash/moonraker.py get_mcu_versions()"
      to: "kflash/screen.py _lookup_version()"
      via: "chip-type keys enable substring match on mcu_type"
      pattern: "stm32h723xx.*version"
---

<objective>
Fix MCU version lookup so each device displays its actual firmware version instead of falling back to the main MCU's version.

Purpose: Currently all devices show the host/main Klipper version because chip-type matching fails against Moonraker's name-based keys.
Output: Correct per-device firmware versions in the TUI device list.
</objective>

<context>
@kflash/moonraker.py
@kflash/screen.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add chip-type keys to get_mcu_versions and remove fallbacks</name>
  <files>kflash/moonraker.py, kflash/screen.py</files>
  <action>
In `kflash/moonraker.py` `get_mcu_versions()`:

1. The existing query only requests MCU objects without specifying fields, which returns all fields including `mcu_constants`. In the loop at line 86, after extracting `mcu_version`, also check for `mcu_constants` dict and read the `MCU` key if present.

2. If `mcu_constants.MCU` exists (e.g., "stm32h723xx"), add it as an additional key in the versions dict mapping to the same version string. Only add if the chip key doesn't already exist (avoid overwriting).

The result dict should contain BOTH name-based keys ("main", "nhk") AND chip-type keys ("stm32h723xx", "rp2040", "stm32f411xe").

3. In `get_mcu_version_for_device()` (line 190-228): Remove the fallback to "main" at lines 224-226. If no exact or substring match, return None.

In `kflash/screen.py` `_lookup_version()` (line 168-183):

4. Remove line 183 (`return mcu_versions.get("main")`). Replace with `return None`.
  </action>
  <verify>
SCP files to Pi, run: `ssh yanceya@192.168.50.50 "cd ~/kalico-flash && python3 -c \"from kflash.moonraker import get_mcu_versions; v = get_mcu_versions(); print(v)\""` — output should contain chip-type keys like "stm32h723xx" alongside name keys like "main".

Then run `python3 flash.py` and verify each device in the list shows its own version (blackpill should show a short hash, not the main Klipper version tag).
  </verify>
  <done>
- get_mcu_versions() returns both name-keyed and chip-type-keyed entries
- _lookup_version("stm32f411") matches "stm32f411xe" via substring and returns the correct version
- Devices with no MCU match show no version instead of main's version
  </done>
</task>

</tasks>

<verification>
On Pi with Moonraker running:
1. `get_mcu_versions()` returns chip-type keys from `mcu_constants.MCU`
2. TUI device list shows distinct versions per device
3. No device incorrectly shows main MCU's version as fallback
</verification>

<success_criteria>
Each registered device displays its actual firmware version in the TUI. Devices whose MCU type cannot be matched display no version rather than an incorrect fallback.
</success_criteria>

<output>
After completion, create `.planning/quick/006-fix-mcu-version-query-poll-actual-firmware/006-SUMMARY.md`
</output>
