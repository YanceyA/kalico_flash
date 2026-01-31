---
phase: quick-013
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - kflash/flash.py
  - kflash/tui.py
autonomous: true

must_haves:
  truths:
    - "After menuconfig save in add-device flow, user sees warning if MCU mismatches device profile"
    - "After menuconfig save in config-device flow, user sees warning if MCU mismatches device profile"
    - "Warning is non-blocking (informational only, does not abort)"
  artifacts:
    - path: "kflash/flash.py"
      provides: "MCU mismatch check in cmd_add_device menuconfig block"
    - path: "kflash/tui.py"
      provides: "MCU mismatch check in config-device menuconfig action"
  key_links:
    - from: "flash.py cmd_add_device"
      to: "config.ConfigManager.validate_mcu"
      via: "call after save_cached_config"
    - from: "tui.py config-device menuconfig"
      to: "config.ConfigManager.validate_mcu"
      via: "call after save_cached_config"
---

<objective>
Add MCU mismatch warning after menuconfig saves in both the add-device and config-device workflows.

Purpose: Catch user errors early -- if someone configures menuconfig for the wrong MCU family, warn them immediately rather than waiting until flash time.
Output: Warning message displayed after menuconfig save when MCU doesn't match device profile.
</objective>

<context>
@kflash/flash.py (lines 1935-1972 — cmd_add_device menuconfig block)
@kflash/tui.py (lines 863-878 — config-device menuconfig action)
@kflash/config.py (lines 159-203 — validate_mcu method)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add MCU mismatch warning after menuconfig save in both locations</name>
  <files>kflash/flash.py, kflash/tui.py</files>
  <action>
In both locations, after `config_mgr.save_cached_config()` (or `cm.save_cached_config()`), add an MCU validation check. The pattern is the same for both:

1. **flash.py line ~1965** (inside `elif was_saved:` block in cmd_add_device):
   After `config_mgr.save_cached_config()` and the success message, add:
   ```python
   try:
       is_match, actual_mcu = config_mgr.validate_mcu(entry.mcu)
       if not is_match:
           out.warning(
               f"MCU mismatch: config has '{actual_mcu}' but device "
               f"'{device_key}' expects '{entry.mcu}'"
           )
           out.info("Config", "You can re-run menuconfig from the config-device menu to fix this")
   except Exception:
       pass  # Non-blocking — validation errors handled at flash time
   ```

2. **tui.py line ~876** (inside `if was_saved:` block in config-device menuconfig action):
   After `cm.save_cached_config()`, add:
   ```python
   try:
       entry = registry.load().devices.get(original_key)
       if entry:
           is_match, actual_mcu = cm.validate_mcu(entry.mcu)
           if not is_match:
               print(f"  {theme.warn}Warning: Config MCU '{actual_mcu}' "
                     f"does not match device MCU '{entry.mcu}'{theme.reset}")
   except Exception:
       pass
   ```
   Note: Check if `theme.warn` exists; if not, use `theme.warning` or whatever the yellow/warn color attribute is in the theme. Look at other `theme.` usages nearby for the correct attribute name.

Both checks are wrapped in try/except to be non-blocking. The real validation with proper error handling already exists in the flash workflow — this is just an early heads-up.
  </action>
  <verify>
    1. `ssh yanceya@192.168.50.50 "cd ~/kalico-flash && python3 -c 'from kflash.flash import cmd_add_device; print(\"import ok\")'"`
    2. `ssh yanceya@192.168.50.50 "cd ~/kalico-flash && python3 -c 'from kflash.tui import config_device_screen; print(\"import ok\")'"`
    3. Manual test: run add-device, configure menuconfig with wrong MCU, confirm warning appears
  </verify>
  <done>Both add-device and config-device menuconfig flows show a non-blocking warning when saved config MCU doesn't match the device profile MCU.</done>
</task>

</tasks>

<verification>
- Import both modules without error after changes
- Warning appears only when MCU actually mismatches (not on valid configs)
- Warning does not block or abort the flow — just informational
- Existing flash-time MCU validation still works unchanged
</verification>

<success_criteria>
- Saving menuconfig with mismatched MCU in add-device shows warning
- Saving menuconfig with mismatched MCU in config-device shows warning
- Saving menuconfig with correct MCU shows no warning
- No regressions in flash workflow MCU validation
</success_criteria>

<output>
After completion, create `.planning/quick/013-mcu-mismatch-check-after-menuconfig/013-SUMMARY.md`
</output>
