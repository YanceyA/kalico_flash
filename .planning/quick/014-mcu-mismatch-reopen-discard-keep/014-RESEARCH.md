# Quick-014: MCU Mismatch Reopen/Discard/Keep - Research

**Researched:** 2026-01-31
**Domain:** MCU mismatch handling in CLI and TUI flows
**Confidence:** HIGH (all from direct code reading)

## Summary

Verified the plan's assumptions against actual code. Found one critical bug and a few minor issues the plan should account for.

**Primary finding:** The plan is mostly accurate but has a critical issue with the Discard flow logic and must fix a pre-existing `out.warning()` bug.

## Findings by Question

### 1. kflash/output.py - Output Protocol

**Protocol class `Output`** (line 11) has these methods:
- `info(self, section: str, message: str)` - line 15
- `success(self, message: str)` - line 16
- `warn(self, message: str)` - line 17 -- **NOTE: `warn` not `warning`**
- `error(self, message: str)` - line 18
- `error_with_recovery(self, error_type, message, context, recovery)` - line 19
- `device_line(self, marker, name, detail)` - line 26
- `prompt(self, message, default="")` - line 27
- `confirm(self, message, default=False)` - line 28 -- **YES exists**
- `phase(self, phase_name, message)` - line 29
- `step_divider(self)` - line 30
- `device_divider(self, index, total, name)` - line 31

**Implementations:**
- `CliOutput` (line 34) - primary CLI output
- `NullOutput` (line 118) - silent output for testing

**Plan accuracy:** Correct. Plan correctly identifies `confirm` exists (line 28) and notes to add after it. Plan correctly notes the method is `warn` not `warning`. NullOutput needs the new method too -- plan mentions this (task 1 step 3).

### 2. kflash/flash.py cmd_add_device - MCU mismatch block

**Lines 1937-1983.** Exact current mismatch block (lines 1964-1977):
```python
elif was_saved:
    config_mgr.save_cached_config()
    out.success(f"Config saved for '{device_key}'")
    try:
        is_match, actual_mcu = config_mgr.validate_mcu(entry.mcu)
        if not is_match:
            out.warning(                          # BUG: should be out.warn()
                f"MCU mismatch: config has '{actual_mcu}' but device "
                f"'{device_key}' expects '{entry.mcu}'"
            )
            out.info("Config", "You can re-run menuconfig from the config-device menu to fix this")
            input("  Press Enter to continue...")
    except Exception:
        pass  # Non-blocking
```

**Available variables at this scope:**
- `out` - CliOutput instance (passed as param)
- `registry` - Registry instance (passed as param)
- `device_key` - str (defined ~line 1830s)
- `entry` - DeviceEntry (created line 1924)
- `config_mgr` - ConfigManager (created line 1948)
- `klipper_dir` - str (line 1947)
- `run_menuconfig` - imported (line 1939)

**`run_menuconfig` call signature:** `run_menuconfig(klipper_dir: str, config_path: str) -> tuple[int, bool]`
Called as: `run_menuconfig(klipper_dir, str(config_mgr.klipper_config_path))` (line 1958-1959)

**CRITICAL BUG:** Lines 1944, 1963, 1970, 1981 all call `out.warning()` but `CliOutput` only has `out.warn()`. These would crash at runtime. Plan correctly identifies this and says to fix them.

**Plan accuracy for Discard flow:** The plan's Discard logic has a subtle issue:
```python
# Plan says:
if had_cache:
    config_mgr.load_cached_config()   # loads cache -> klipper dir
    config_mgr.save_cached_config()   # saves klipper dir -> cache
```
This is a no-op (loads cache to klipper, saves klipper back to cache). The intent is to restore the *previous* cache, but by this point `save_cached_config()` has already overwritten the cache (line 1965). **The previous cache is gone.** The plan needs to either:
1. Back up the cache *before* saving, or
2. Record whether a cache existed and just delete the new one if not (but can't restore old one)

Actually wait -- re-reading more carefully: `had_cache` is set before menuconfig runs. The flow is:
1. `had_cache = config_mgr.has_cached_config()` (before menuconfig)
2. `config_mgr.load_cached_config()` loads old cache to klipper dir
3. menuconfig runs, user saves, overwriting klipper .config
4. `config_mgr.save_cached_config()` overwrites cache with new (mismatched) config
5. On Discard: `config_mgr.load_cached_config()` loads the *already-overwritten* cache

So yes, **Discard cannot restore the previous config** because step 4 already overwrote the cache. The plan's Discard logic is broken. To fix: need to back up the old cache before step 4, or defer `save_cached_config()` until after validation passes.

### 3. kflash/tui.py _device_config_screen - MCU mismatch block

**Lines 863-888.** Exact block (lines 875-886):
```python
if was_saved:
    cm.save_cached_config()
    try:
        entry = registry.load().devices.get(original_key)
        if entry:
            is_match, actual_mcu = cm.validate_mcu(entry.mcu)
            if not is_match:
                print(f"  {theme.warning}Warning: Config MCU '{actual_mcu}' "
                      f"does not match device MCU '{entry.mcu}'{theme.reset}")
                input("  Press Enter to continue...")
    except Exception:
        pass
```

**Available variables:**
- `cm` - ConfigManager (line 871)
- `registry` - Registry (passed to parent function)
- `original_key` - str (device key before any renames)
- `gc` - GlobalConfig from `registry.load_global()` (line 870)
- `theme` - Theme (from parent scope)
- `config_path` - str = `str(cm.klipper_config_path)` (line 873)
- `run_menuconfig` - imported (line 867)

**Theme attributes used:** `theme.warning`, `theme.error`, `theme.reset` are used in surrounding code. `theme.info` exists in the Theme dataclass (line 237) and maps to the header color (line 290).

**Same Discard bug applies here** -- `cm.save_cached_config()` on line 876 overwrites cache before mismatch check.

### 4. kflash/config.py ConfigManager

All methods exist as the plan assumes:

| Method | Signature | Line |
|--------|-----------|------|
| `__init__` | `(self, device_key: str, klipper_dir: str)` | 106 |
| `has_cached_config` | `(self) -> bool` | 210 |
| `load_cached_config` | `(self) -> bool` | 118 |
| `save_cached_config` | `(self) -> None` | 144 |
| `clear_klipper_config` | `(self) -> bool` | 134 |
| `validate_mcu` | `(self, expected_mcu: str) -> tuple[bool, Optional[str]]` | 164 |
| `cache_path` | attribute, `Path` type | 115 |
| `klipper_config_path` | attribute, `Path` type | 116 |

## Critical Issues for Plan

### Issue 1: Discard Cannot Restore Previous Config (HIGH)

Both flash.py and tui.py call `save_cached_config()` immediately after menuconfig, BEFORE checking MCU match. By the time Discard runs, the old cache is gone.

**Fix options:**
- **Option A (recommended):** Defer `save_cached_config()` until after MCU validation passes (or user chooses Keep). Only save if match or Keep.
- **Option B:** Copy old cache to a backup path before saving, restore from backup on Discard.
- **Option C:** On Discard when `had_cache=True`, just don't do anything (cache is already overwritten, accept the loss). This makes Discard equivalent to Keep when there was a previous cache -- bad UX.

### Issue 2: out.warning() Bug (HIGH)

Lines 1944, 1963, 1970, 1981 in flash.py call `out.warning()` which doesn't exist on `CliOutput`. The plan already notes this fix.

### Issue 3: NullOutput Needs Method (LOW)

Plan mentions this. `NullOutput` (line 118) needs `mcu_mismatch_choice` returning a default (probably `'k'`).

## Open Questions

1. **Discard semantics:** Should Discard restore old config (requires backup) or just delete the new one? If the user had no previous cache, Discard = delete cache. If they had one, what's the expected behavior?

## Sources

### Primary (HIGH confidence)
- Direct code reading: kflash/output.py, kflash/flash.py, kflash/tui.py, kflash/config.py, kflash/theme.py, kflash/build.py
