---
phase: quick-014
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - kflash/output.py
  - kflash/flash.py
  - kflash/tui.py
autonomous: true
must_haves:
  truths:
    - "MCU mismatch after menuconfig presents R/D/K choice in cmd_add_device"
    - "MCU mismatch after menuconfig presents R/D/K choice in tui _device_config_screen"
    - "Re-open re-launches menuconfig and re-validates, looping if still mismatched"
    - "Discard restores previous cache (or deletes klipper .config if none existed)"
    - "Keep saves the mismatched config to cache and exits"
    - "Config is NOT saved to cache until after MCU validation passes or user picks Keep"
  artifacts:
    - path: "kflash/output.py"
      provides: "mcu_mismatch_choice method on CliOutput and NullOutput"
      contains: "mcu_mismatch_choice"
    - path: "kflash/flash.py"
      provides: "R/D/K loop in cmd_add_device with deferred save"
      contains: "mcu_mismatch_choice"
    - path: "kflash/tui.py"
      provides: "R/D/K loop in _device_config_screen with deferred save"
      contains: "Re-open"
  key_links:
    - from: "kflash/flash.py"
      to: "kflash/output.py"
      via: "out.mcu_mismatch_choice()"
      pattern: "mcu_mismatch_choice"
---

<objective>
Replace the MCU mismatch warning (press Enter to continue) with an interactive
[R]e-open / [D]iscard / [K]eep prompt in both cmd_add_device (flash.py) and
_device_config_screen (tui.py). Critically, defer save_cached_config() until
AFTER MCU validation so Discard can restore the untouched old cache.

Purpose: Let users fix MCU mismatches immediately instead of manually navigating back.
Output: Three files updated with mismatch prompt logic.
</objective>

<context>
@kflash/output.py
@kflash/flash.py (cmd_add_device, lines ~1935-1983)
@kflash/tui.py (_device_config_screen, lines ~863-889)
@kflash/config.py (ConfigManager: has_cached_config, load_cached_config, save_cached_config, clear_klipper_config, cache_path)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add mcu_mismatch_choice to output.py (Protocol, CliOutput, NullOutput)</name>
  <files>kflash/output.py</files>
  <action>
1. Add to the `Output` Protocol class (after `confirm` on line 28):
   ```python
   def mcu_mismatch_choice(self, actual_mcu: str, expected_mcu: str, device_key: str) -> str: ...
   ```

2. Add to `CliOutput` class (after `confirm` method, before `phase`):
   ```python
   def mcu_mismatch_choice(self, actual_mcu: str, expected_mcu: str, device_key: str) -> str:
       """Prompt user after MCU mismatch. Returns 'r', 'd', or 'k'."""
       self.warn(f"MCU mismatch: config has '{actual_mcu}' but device '{device_key}' expects '{expected_mcu}'")
       while True:
           choice = input("  [R]e-open menuconfig / [D]iscard config / [K]eep anyway: ").strip().lower()
           if choice in ('r', 'd', 'k'):
               return choice
   ```

3. Add to `NullOutput` class (after `confirm` method):
   ```python
   def mcu_mismatch_choice(self, actual_mcu: str, expected_mcu: str, device_key: str) -> str:
       return 'k'
   ```
   NullOutput returns 'k' (keep) as safe default for non-interactive use.

NOTE: Use `self.warn()` not `self.warning()` -- the method name is `warn`.
  </action>
  <verify>Run on Pi: ssh yanceya@192.168.50.50 "cd ~/kalico-flash && python3 -c \"from kflash.output import CliOutput, NullOutput; assert hasattr(CliOutput, 'mcu_mismatch_choice'); assert hasattr(NullOutput, 'mcu_mismatch_choice'); print('ok')\""</verify>
  <done>CliOutput, NullOutput, and Protocol all have mcu_mismatch_choice method</done>
</task>

<task type="auto">
  <name>Task 2: Replace mismatch block in flash.py cmd_add_device with deferred-save R/D/K loop</name>
  <files>kflash/flash.py</files>
  <action>
The CRITICAL change: Do NOT call save_cached_config() immediately after menuconfig.
Defer it until after MCU validation passes or user picks Keep. This preserves the
old cache so Discard can restore from it.

**Fix 1: All `out.warning()` calls in cmd_add_device must become `out.warn()`.**
These are OUTSIDE the replaced block and must be fixed separately:
- Line 1944: `out.warning("Cannot run menuconfig...")` → `out.warn("Cannot run menuconfig...")`
- Line 1963: `out.warning("menuconfig exited with errors...")` → `out.warn("menuconfig exited with errors...")`
- Line 1981: `out.warning(f"menuconfig failed: {exc}")` → `out.warn(f"menuconfig failed: {exc}")`
- Line 1970 is inside the replaced block (Fix 3) so it's handled there.
Use `replace_all` or find-and-replace `out.warning(` → `out.warn(` across the entire function.

**Fix 2: Record had_cache after ConfigManager creation but before load_cached_config.**
After `config_mgr = ConfigManager(device_key, klipper_dir)` (line 1948) and before
`if config_mgr.load_cached_config():` (line 1951), add:
```python
had_cache = config_mgr.has_cached_config()
```

**Fix 3: Replace lines 1964-1977 (the elif was_saved block) with deferred-save R/D/K loop.**

Replace the entire `elif was_saved:` block (lines 1964-1977) with:

```python
elif was_saved:
    # DON'T save to cache yet -- need to validate MCU first
    try:
        is_match, actual_mcu = config_mgr.validate_mcu(entry.mcu)
        while not is_match:
            choice = out.mcu_mismatch_choice(actual_mcu, entry.mcu, device_key)
            if choice == 'r':
                out.info("Config", "Re-launching menuconfig...")
                ret_code2, was_saved2 = run_menuconfig(
                    klipper_dir, str(config_mgr.klipper_config_path)
                )
                if was_saved2:
                    is_match, actual_mcu = config_mgr.validate_mcu(entry.mcu)
                else:
                    out.info("Config", "menuconfig exited without saving")
                    break
            elif choice == 'd':
                # Restore old cache to klipper dir, or delete klipper .config if no prior cache
                if had_cache:
                    config_mgr.load_cached_config()
                    out.info("Config", "Restored previous cached config")
                else:
                    config_mgr.clear_klipper_config()
                    out.info("Config", "Discarded config (no previous cache)")
                break
            else:  # 'k'
                config_mgr.save_cached_config()
                out.info("Config", "Keeping mismatched config")
                break
        else:
            # MCU matched (while condition became False) -- save now
            config_mgr.save_cached_config()
            out.success(f"Config saved for '{device_key}'")
    except Exception:
        pass  # Non-blocking
```

Key points about this structure:
- `while not is_match: ... else:` -- the else runs when is_match becomes True
- On Keep: save_cached_config() saves the mismatched config the user chose to keep
- On Discard with had_cache: load_cached_config() restores from UNTOUCHED old cache
- On Discard without had_cache: clear_klipper_config() removes the klipper .config
- On Re-open: re-run menuconfig, re-validate, loop continues
- On Re-open where menuconfig exits without saving: break (no save). Note: klipper dir retains the mismatched .config from the first menuconfig run but it is NOT cached. This is acceptable — user chose not to save.
- On match (else clause): save_cached_config() saves the good config
  </action>
  <verify>Run on Pi: ssh yanceya@192.168.50.50 "cd ~/kalico-flash && python3 -c \"from kflash.flash import cmd_add_device; print('import ok')\""</verify>
  <done>cmd_add_device uses deferred save with R/D/K loop; all out.warning() calls fixed to out.warn(); Discard correctly restores from untouched cache</done>
</task>

<task type="auto">
  <name>Task 3: Replace mismatch block in tui.py _device_config_screen with deferred-save R/D/K loop</name>
  <files>kflash/tui.py</files>
  <action>
Same deferred-save pattern as flash.py. The cache must NOT be overwritten before
the mismatch check.

**Fix 1: Record had_cache before menuconfig.**
Before `cm.load_cached_config()` (~line 872), add:
```python
had_cache = cm.has_cached_config()
```

**Fix 2: Replace lines 875-886 (the if was_saved block) with deferred-save R/D/K loop.**

Replace the `if was_saved:` block with:

```python
if was_saved:
    # DON'T save to cache yet -- validate MCU first
    try:
        entry = registry.load().devices.get(original_key)
        if entry:
            is_match, actual_mcu = cm.validate_mcu(entry.mcu)
            while not is_match:
                print(f"  {theme.warning}MCU mismatch: config has '{actual_mcu}' "
                      f"but device '{original_key}' expects '{entry.mcu}'{theme.reset}")
                choice = input("  [R]e-open menuconfig / [D]iscard config / [K]eep anyway: ").strip().lower()
                if choice not in ('r', 'd', 'k'):
                    continue
                if choice == 'r':
                    ret2, saved2 = run_menuconfig(gc.klipper_dir, config_path)
                    if saved2:
                        is_match, actual_mcu = cm.validate_mcu(entry.mcu)
                    else:
                        print(f"  {theme.info}menuconfig exited without saving{theme.reset}")
                        break
                elif choice == 'd':
                    if had_cache:
                        cm.load_cached_config()
                        print(f"  {theme.info}Restored previous config{theme.reset}")
                    else:
                        cm.clear_klipper_config()
                        print(f"  {theme.info}Discarded config{theme.reset}")
                    break
                else:  # 'k'
                    cm.save_cached_config()
                    print(f"  {theme.info}Keeping mismatched config{theme.reset}")
                    break
            else:
                # MCU matched -- save now
                cm.save_cached_config()
    except Exception:
        pass
```

Key differences from flash.py version:
- Uses `print()` with theme attributes instead of `out.mcu_mismatch_choice()` (TUI uses direct print, not the output protocol)
- Uses `cm` instead of `config_mgr`
- Uses `gc.klipper_dir` and `config_path` from surrounding scope
- On Discard with had_cache: `cm.load_cached_config()` restores from UNTOUCHED old cache
- On Discard without had_cache: `cm.clear_klipper_config()` removes klipper .config
- `theme.warning`, `theme.info`, `theme.reset` are confirmed valid attributes
  </action>
  <verify>Run on Pi: ssh yanceya@192.168.50.50 "cd ~/kalico-flash && python3 -c \"from kflash.tui import DeviceTUI; print('import ok')\"" || ssh yanceya@192.168.50.50 "cd ~/kalico-flash && python3 -c \"from kflash.tui import run_menu; print('import ok')\""</verify>
  <done>TUI _device_config_screen uses deferred save with R/D/K loop; Discard correctly restores from untouched cache</done>
</task>

</tasks>

<verification>
1. Import check: `python3 -c "from kflash.output import CliOutput, NullOutput; from kflash.flash import cmd_add_device; from kflash.tui import run_menu; print('all imports ok')"`
2. Verify NullOutput.mcu_mismatch_choice returns 'k': `python3 -c "from kflash.output import NullOutput; assert NullOutput().mcu_mismatch_choice('a','b','c') == 'k'; print('ok')"`
3. Manual test on Pi: Run `python3 kflash.py --add-device`, configure with wrong MCU, verify R/D/K prompt appears
4. Verify [R] re-opens menuconfig and re-checks MCU
5. Verify [D] restores previous cache (check cache file unchanged) or deletes klipper .config if new device
6. Verify [K] saves the mismatched config to cache and continues
7. Verify normal flow (matching MCU) saves config without prompting
8. Verify no `out.warning()` calls remain in cmd_add_device (all fixed to `out.warn()`)
</verification>

<success_criteria>
- MCU mismatch in cmd_add_device shows [R]e-open / [D]iscard / [K]eep prompt
- MCU mismatch in tui _device_config_screen shows same prompt inline
- save_cached_config() is NEVER called before MCU validation (the critical fix)
- Re-open loops back through menuconfig + validation
- Discard restores old cache (load_cached_config from untouched cache) or clears klipper .config
- Keep calls save_cached_config() to persist the mismatched config
- Normal matching MCU flow calls save_cached_config() in the while/else clause
- NullOutput.mcu_mismatch_choice returns 'k' for non-interactive use
- All out.warning() calls in cmd_add_device fixed to out.warn()
- No import errors, no regressions in normal flow
</success_criteria>

<output>
After completion, create `.planning/quick/014-mcu-mismatch-reopen-discard-keep/014-SUMMARY.md`
</output>
