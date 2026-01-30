---
phase: quick
plan: 008
subsystem: config
tags: [menuconfig, kconfig, device-registration]
requires: []
provides: [fresh-menuconfig-for-new-devices]
affects: []
tech-stack:
  added: []
  patterns: [clear-stale-config]
key-files:
  created: []
  modified:
    - kflash/config.py
    - kflash/flash.py
decisions: []
metrics:
  duration: 52s
  completed: 2026-01-30
---

# Quick Task 008: Fresh Menuconfig for New Devices Summary

**One-liner:** Clear stale .config from klipper directory when building new devices without cached configs

## What Was Built

Added automatic cleanup of stale `.config` files from the klipper build directory when starting menuconfig for a new device that has no cached configuration. This ensures menuconfig starts with fresh defaults instead of inheriting potentially incompatible settings from a previous build for a different MCU.

**Problem solved:** When registering a new device (e.g., switching from STM32 to RP2040), the klipper directory's `.config` from a previous build would persist, causing menuconfig to load incompatible settings as "current config" instead of starting fresh with architecture-appropriate defaults.

**Solution:**
- Added `ConfigManager.clear_klipper_config()` method that removes `.config` from klipper directory
- Called automatically in `cmd_build()` and `cmd_flash()` when `load_cached_config()` returns False
- Devices with cached configs are unaffected — only new devices get a clean slate

## Task Completion

| Task | Name | Commit | Files | Status |
|------|------|--------|-------|--------|
| 1 | Add clear_klipper_config method and call it | 4b6a50f | kflash/config.py, kflash/flash.py | Complete |

## Deviations from Plan

None - plan executed exactly as written.

## Technical Details

### Implementation

**ConfigManager.clear_klipper_config()** (kflash/config.py:109-117)
```python
def clear_klipper_config(self) -> bool:
    """Remove .config from klipper directory for fresh menuconfig.

    Returns True if file was removed, False if it didn't exist.
    """
    if self.klipper_config_path.exists():
        self.klipper_config_path.unlink()
        return True
    return False
```

**Integration points:**
- `cmd_build()` line 311: Clears config after failed `load_cached_config()`
- `cmd_flash()` line 804: Clears config after failed `load_cached_config()`
- `cmd_flash_all()`: Intentionally not modified — requires cached configs, never hits this path

### Behavior Changes

**Before:**
1. User registers new RP2040 device after previously building for STM32
2. Menuconfig loads with STM32 settings as "current"
3. User must manually reset to defaults or risk incompatible config

**After:**
1. User registers new RP2040 device
2. `.config` is cleared automatically before menuconfig
3. Menuconfig starts fresh with RP2040 defaults
4. User sees clean slate appropriate for the new architecture

**No regression risk:** Devices with cached configs still load their saved settings — this only affects the new-device first-run experience.

## Verification

All verification criteria met:

- ✓ `ConfigManager` has `clear_klipper_config()` method
- ✓ `cmd_build()` calls it when no cached config exists
- ✓ `cmd_flash()` calls it when no cached config exists
- ✓ Both files compile without errors
- ✓ Grep confirms method calls in both command functions

## Files Changed

**kflash/config.py**
- Added `clear_klipper_config()` method after `load_cached_config()` (lines 109-117)

**kflash/flash.py**
- Modified `cmd_build()` to call `clear_klipper_config()` at line 311
- Modified `cmd_flash()` to call `clear_klipper_config()` at line 804

## Next Phase Readiness

**Ready for:** All phases requiring clean menuconfig starts for new devices

**No blockers or concerns**

## Decisions Made

None — straightforward implementation following established patterns

## Related Work

- Complements device registration wizard (cmd_add_device)
- Works with existing cached config infrastructure
- Aligns with per-device config caching design from Phase 4

---

**Total duration:** 52 seconds
**Completed:** 2026-01-30
