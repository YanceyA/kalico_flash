---
phase: quick-009
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - kflash/flash.py
  - kflash/config.py
autonomous: true

must_haves:
  truths:
    - "flash-all refuses to proceed if any device lacks a cached config"
    - "flash-all refuses to proceed if any cached config has MCU mismatch with registry"
    - "flash-all refuses to proceed if any flashable device is on the blocked list"
    - "flash-all shows config age for each device during validation"
    - "Single-device flash (cmd_flash) behavior is unchanged"
  artifacts:
    - path: "kflash/flash.py"
      provides: "Enhanced cmd_flash_all Stage 1 validation"
    - path: "kflash/config.py"
      provides: "Config age helper method"
  key_links:
    - from: "kflash/flash.py cmd_flash_all"
      to: "kflash/config.py ConfigManager.validate_mcu"
      via: "MCU validation call during Stage 1"
      pattern: "config_mgr\\.validate_mcu"
---

<objective>
Add validation guards to cmd_flash_all so it refuses to auto-flash devices with wrong, missing, or old (recommend review) cached configs.

Purpose: flash-all is a batch operation that skips menuconfig entirely, relying on cached configs. Without validation, it could silently flash wrong firmware (e.g., STM32 config onto RP2040) or flash very old configs the user forgot about.

Output: Enhanced Stage 1 in cmd_flash_all with MCU validation, blocked device filtering, and config age display.
</objective>

<context>
@kflash/flash.py (cmd_flash_all at line 1005, Stage 1 validation at lines 1055-1078)
@kflash/config.py (ConfigManager with validate_mcu, has_cached_config, get_cache_mtime)
@kflash/models.py (DeviceEntry, BatchDeviceResult)
@kflash/errors.py (ConfigError, ConfigMismatchError)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add config age helper to ConfigManager</name>
  <files>kflash/config.py</files>
  <action>
Add a method `get_cache_age_display() -> Optional[str]` to ConfigManager that returns a human-readable string for the cached config age (e.g., "2 hours ago", "3 days ago", "14 days ago"). Use `time.time() - mtime` from `get_cache_mtime()`. Return None if no cache exists.

Thresholds for display:
- < 1 hour: "{N} minutes ago"
- < 24 hours: "{N} hours ago"
- < 90 days: "{N} days ago"
- >= 90 days: "{N} days ago (recommend review)"

This is a pure helper, no side effects.
  </action>
  <verify>
Import ConfigManager in a Python REPL on the Pi and call get_cache_age_display() for a device with a cached config. Verify it returns a reasonable string.
  </verify>
  <done>ConfigManager has get_cache_age_display() method that returns human-readable age string.</done>
</task>

<task type="auto">
  <name>Task 2: Harden cmd_flash_all Stage 1 validation</name>
  <files>kflash/flash.py</files>
  <action>
Enhance the Stage 1 validation in cmd_flash_all (around lines 1055-1078) with these additional checks, run AFTER the existing missing-config check:

1. **Blocked device filter:** After building `flashable_devices`, filter out any that match the blocked list (reuse `_build_blocked_list` and `_blocked_reason_for_entry`). If ALL flashable devices are blocked, error and return 1. If some are blocked, warn and remove them from the list.

2. **MCU validation for each cached config:** For each device with a cached config, call `config_mgr.load_cached_config()` then `config_mgr.validate_mcu(entry.mcu)`. If the MCU doesn't match, add the device to a `mcu_mismatch` list. After checking all, if any mismatches exist, show each one with expected vs actual MCU and return 1 with recovery guidance: "Run `kflash -d {key}` for each mismatched device to reconfigure."

3. **Config age display:** For each validated device, show the config age using `get_cache_age_display()`. If any config is >= 90 days old (the "STALE" case), add a warning but do NOT block — just inform the user.

The validation order should be:
- Check flashable devices exist (existing)
- Filter blocked devices (new)
- Check cached configs exist (existing)
- Validate MCU match for each config (new)
- Display config ages with old (recommend review)ness warnings (new)

Important: Do NOT change any behavior in cmd_flash (single device). Only modify cmd_flash_all.

Wrap the MCU validation in try/except ConfigError to handle corrupt configs gracefully — treat as a validation failure, not a crash.
  </action>
  <verify>
1. `ssh yanceya@192.168.50.50 "cd ~/kalico-flash && python3 -c \"from kflash.flash import cmd_flash_all; print('import ok')\""` succeeds
2. Test on Pi with registered devices: run `kflash` and select Flash All from menu. Verify Stage 1 now shows config ages and validates MCU types.
3. Manually corrupt a cached config's CONFIG_MCU line and verify flash-all catches the mismatch and refuses to proceed.
  </verify>
  <done>
- flash-all validates MCU match for every cached config before building
- flash-all filters blocked devices from the batch
- flash-all displays config age for each device
- flash-all warns on old (recommend review) configs (30+ days)
- Corrupt or mismatched configs cause flash-all to abort with clear guidance
- Single-device cmd_flash is completely unchanged
  </done>
</task>

</tasks>

<verification>
1. Import check: `python3 -c "from kflash.flash import cmd_flash_all"` succeeds
2. Normal flow: flash-all with valid cached configs proceeds to Stage 2
3. MCU mismatch: Tamper with a cached .config CONFIG_MCU value, flash-all aborts at Stage 1
4. Missing config: Remove a cached config file, flash-all aborts (existing behavior preserved)
5. Blocked device: Add a device whose pattern matches DEFAULT_BLOCKED_DEVICES, flash-all skips it
6. Old (recommend review) config: Set a config mtime to 31+ days ago, flash-all warns but continues
7. Single-device: `kflash -d octopus-pro` still works identically to before
</verification>

<success_criteria>
- cmd_flash_all Stage 1 validates MCU type of every cached config against registry
- Blocked devices are filtered out of flash-all batch
- Config age is displayed for each device during validation
- Old (recommend review) configs (30+ days) produce a warning
- MCU mismatches or corrupt configs cause immediate abort with recovery guidance
- No changes to single-device cmd_flash behavior
</success_criteria>

<output>
After completion, create `.planning/quick/009-flash-all-config-validation-guard/009-SUMMARY.md`
</output>
