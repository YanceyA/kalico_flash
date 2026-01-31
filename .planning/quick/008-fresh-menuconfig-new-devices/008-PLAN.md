---
phase: quick
plan: 008
type: execute
wave: 1
depends_on: []
files_modified:
  - kflash/config.py
  - kflash/flash.py
autonomous: true

must_haves:
  truths:
    - "New device without cached config gets fresh menuconfig defaults"
    - "Device with cached config still loads its saved settings"
  artifacts:
    - path: "kflash/config.py"
      provides: "clear_klipper_config method"
      contains: "def clear_klipper_config"
    - path: "kflash/flash.py"
      provides: "Calls clear_klipper_config when no cached config"
      contains: "clear_klipper_config"
  key_links:
    - from: "kflash/flash.py"
      to: "kflash/config.py"
      via: "ConfigManager.clear_klipper_config()"
      pattern: "clear_klipper_config"
---

<objective>
Clear stale .config from klipper directory when building for a new device without cached config, so menuconfig starts with fresh defaults instead of inheriting settings from the last build.
</objective>

<context>
@kflash/config.py
@kflash/flash.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add clear_klipper_config method and call it from flash.py</name>
  <files>kflash/config.py, kflash/flash.py</files>
  <action>
  1. In `kflash/config.py`, add method `clear_klipper_config()` to `ConfigManager`:
     ```python
     def clear_klipper_config(self) -> bool:
         """Remove .config from klipper directory for fresh menuconfig.
         Returns True if file was removed, False if it didn't exist."""
         if self.klipper_config_path.exists():
             self.klipper_config_path.unlink()
             return True
         return False
     ```
     Place it after `load_cached_config()` (after line 107).

  2. In `kflash/flash.py` `cmd_build()` (~line 311), in the `else` branch where no cached config:
     ```python
     else:
         config_mgr.clear_klipper_config()
         out.info("Config", "No cached config found, starting fresh")
     ```

  3. In `kflash/flash.py` `cmd_flash()` (~line 803), same pattern:
     ```python
     else:
         config_mgr.clear_klipper_config()
         out.phase("Config", "No cached config found, starting fresh")
     ```

  Do NOT touch cmd_flash_all — it requires cached configs and never hits this path.
  </action>
  <verify>
  - `python -c "from kflash.config import ConfigManager; print(hasattr(ConfigManager, 'clear_klipper_config'))"` returns True
  - grep confirms `clear_klipper_config` appears in both cmd_build and cmd_flash in flash.py
  - `python -m py_compile kflash/config.py && python -m py_compile kflash/flash.py` succeeds
  </verify>
  <done>
  - ConfigManager has clear_klipper_config() method
  - cmd_build() calls it when load_cached_config() returns False
  - cmd_flash() calls it when load_cached_config() returns False
  - All files compile without errors
  </done>
</task>

</tasks>

<verification>
- Both files compile cleanly
- Method exists on ConfigManager
- Both cmd_build and cmd_flash call clear_klipper_config in the no-cache branch
</verification>

<success_criteria>
New devices without cached config get a truly fresh menuconfig (no stale .config from previous builds).
Devices with cached config behave identically to before.
</success_criteria>

<output>
After completion, create `.planning/quick/008-fresh-menuconfig-new-devices/008-SUMMARY.md`
</output>
