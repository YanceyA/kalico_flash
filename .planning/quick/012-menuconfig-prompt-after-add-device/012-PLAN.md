---
phase: quick-012
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - kflash/flash.py
autonomous: true

must_haves:
  truths:
    - "After registering a device, user is prompted to run menuconfig"
    - "Declining the prompt returns 0 (success) without running menuconfig"
    - "Accepting the prompt launches menuconfig via cmd_build for that device"
    - "Prompt works from both direct add-device and config-device unregistered path"
  artifacts:
    - path: "kflash/flash.py"
      provides: "Y/n menuconfig prompt at end of cmd_add_device"
      contains: "menuconfig"
  key_links:
    - from: "cmd_add_device"
      to: "cmd_build"
      via: "Y/n prompt after successful registration"
      pattern: "confirm.*menuconfig"
---

<objective>
Add a Y/n prompt at the end of cmd_add_device that offers to run menuconfig for the newly registered device.

Purpose: After adding a device, the user typically needs to configure firmware settings via menuconfig. This saves them from navigating back to do it manually.
Output: Modified cmd_add_device in flash.py with post-registration menuconfig prompt.
</objective>

<context>
@kflash/flash.py — cmd_add_device (line ~1635) and cmd_build (line ~265)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add menuconfig prompt after device registration</name>
  <files>kflash/flash.py</files>
  <action>
In cmd_add_device, after line 1933 (`out.success(f"Registered '{device_key}' ({display_name})")`), add:

1. A step divider
2. A Y/n confirmation prompt: "Run menuconfig now to configure firmware? (Y/n)"
   - Use `out.confirm()` with `default=True`
3. If yes: call `cmd_build(registry, device_key, out)` which handles the full menuconfig workflow (loads/creates config, runs menuconfig TUI, saves config, validates MCU)
   - Note: cmd_build also does `make` compilation after menuconfig. This is INTENTIONAL — the user description says "generate a config" but running the full build after config is the natural workflow and matches what "Build Firmware" does in the TUI.
   - WAIT — re-reading the description: "optionally run make menuconfig, so the user can generate a config for the MCU." This means ONLY menuconfig, NOT a full build. So instead of calling cmd_build, directly invoke the menuconfig portion:
     a. Import ConfigManager from .config
     b. Load registry data to get klipper_dir from global_config
     c. Create ConfigManager with device_key and klipper_dir
     d. Call config_mgr.load_or_create() to set up the .config file
     e. Import run_menuconfig from .build
     f. Call run_menuconfig(klipper_dir, str(config_mgr.klipper_config_path))
     g. If menuconfig returns saved config (was_saved=True), call config_mgr.save_config() to cache it
     h. Print success/info message about config being saved or not
   - If menuconfig fails or config not saved, just warn — don't return error code since the device was already registered successfully
4. If no: do nothing, return 0 as before

Important: This prompt fires regardless of how cmd_add_device was called (CLI --add-device, TUI Add Device, or TUI Config Device unregistered path) since all paths go through this same function.
  </action>
  <verify>
    Test on Pi via SSH:
    1. `ssh yanceya@192.168.50.50 "cd ~/kalico-flash && python3 -m kflash --add-device"` — register a test device, verify menuconfig prompt appears after registration
    2. Verify declining prompt returns cleanly
    3. Clean up test device: `ssh yanceya@192.168.50.50 "cd ~/kalico-flash && python3 -m kflash --remove-device test-device"`
  </verify>
  <done>After successful device registration, user sees "Run menuconfig now?" prompt. Accepting launches menuconfig and caches the resulting config. Declining returns success without menuconfig.</done>
</task>

</tasks>

<verification>
- cmd_add_device shows menuconfig prompt after successful registration
- Prompt uses default=True (Y/n) so pressing Enter runs menuconfig
- Declining skips menuconfig and returns 0
- Works from all entry points (CLI, TUI add, TUI config-device unregistered)
</verification>

<success_criteria>
- Menuconfig Y/n prompt appears after every successful device registration
- Config is cached when menuconfig completes with save
- No errors when declining the prompt
</success_criteria>

<output>
After completion, create `.planning/quick/012-menuconfig-prompt-after-add-device/012-SUMMARY.md`
</output>
