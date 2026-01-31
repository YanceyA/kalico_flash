---
phase: 25-key-internalization-in-tui
verified: 2026-02-01T20:30:00Z
status: passed
score: 4/4 must-haves verified
---

# Phase 25: Key Internalization in TUI Verification Report

**Phase Goal:** Device keys are invisible internal identifiers — users interact only with display names
**Verified:** 2026-02-01T20:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Add-device wizard prompts only for display name — no key prompt, system generates key silently | ✓ VERIFIED | Lines 1814-1839 in flash.py: display name prompt with duplicate check, auto-generation via generate_device_key(), no key prompt exists |
| 2 | Device config screen has no key edit option (setting removed from DEVICE_SETTINGS) | ✓ VERIFIED | DEVICE_SETTINGS in screen.py has 4 entries (name, flash_method, flashable, menuconfig) — no key entry. Config screen handler (tui.py:801) accepts only keys "1"-"4", no key edit handler exists |
| 3 | All user-facing output (device lists, flash messages, batch results) shows entry.name not entry.key | ✓ VERIFIED | Verified 40+ output locations in flash.py all use entry.name. FlashAll batch results use result.device_name (line 1380). Device list shows "name (mcu)" format (line 1567). All remaining device_key/entry.key references are internal (registry lookups, cache paths, context dicts) or CLI-only code paths |
| 4 | Existing devices.json keys preserved exactly as-is — no re-derivation or migration on load | ✓ VERIFIED | No re-derivation logic exists. Registry operations (load, add, update) preserve keys. generate_device_key only called once in add-device wizard for NEW devices (line 1836) |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `kflash/flash.py` | Rewired add-device wizard with auto-key generation | ✓ VERIFIED | Lines 1814-1839: display name prompt with case-insensitive duplicate check; lines 1833-1839: generate_device_key import and call with ValueError handling; line 1934: success message shows display name only; line 1926: device_key still passed to DeviceEntry creation |
| `kflash/screen.py` | DEVICE_SETTINGS without key entry | ✓ VERIFIED | DEVICE_SETTINGS (lines 479-489) has 4 entries: name, flash_method, flashable, menuconfig. No key edit option present |
| `kflash/tui.py` | Updated config screen handlers and key-free output | ✓ VERIFIED | Config screen handler (lines 768-867) accepts only "1"-"4" input; key edit handler removed; _save_device_edits (lines 738-747) has no key rename logic; _action_flash_device and _action_remove_device (lines 333-447) show entry.name in failure messages |
| `kflash/output.py` | mcu_mismatch_choice uses name not key | ✓ VERIFIED | Lines 29, 99, 165: mcu_mismatch_choice parameter is device_name, used in output message "but device '{device_name}' expects..." |

**All artifacts:** ✓ VERIFIED (4/4)

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| kflash/flash.py | kflash/validation.py | generate_device_key import and call | ✓ WIRED | Line 1833: import statement; line 1836: generate_device_key(display_name, registry) called; ValueError caught at line 1837-1839 |
| kflash/tui.py | kflash/screen.py | DEVICE_SETTINGS consumed by config screen | ✓ WIRED | Line 760: DEVICE_SETTINGS imported; line 803: indexed with int(key)-1; lines 805-830: dispatched to correct handlers based on setting["key"] |
| Add-device wizard | Display name duplicate check | Case-insensitive set comparison | ✓ WIRED | Line 1816: existing_names = {e.name.lower() for e in registry_data.devices.values()}; line 1823: name_input.lower() in existing_names |
| Flash.py cmd_flash | entry.name output | All device display lines | ✓ WIRED | 40+ locations verified: device_line calls (lines 510, 531, 571, 581, 593, 609), phase messages (lines 734, 832, 844, 848, 874, 1014), warnings (line 1125), batch results (lines 1138, 1157, 1173, 1220, 1223) |

**All key links:** ✓ WIRED (4/4)

### Requirements Coverage

Based on .planning/REQUIREMENTS.md:

| Requirement | Status | Evidence |
|-------------|--------|----------|
| KEY-03: Add-device wizard no longer prompts for device key | ✓ VERIFIED | No "Device key" prompt exists in cmd_add_device; only display name prompted at lines 1814-1830 |
| KEY-04: Device config screen removes key edit option | ✓ VERIFIED | DEVICE_SETTINGS has 4 entries, no key option; config handler accepts only "1"-"4" |
| KEY-05: All user-facing output shows entry.name instead of entry.key | ✓ VERIFIED | All TUI and flash.py output uses entry.name; remaining device_key refs are internal or CLI-only |
| KEY-06: Existing devices.json keys preserved as-is | ✓ VERIFIED | No re-derivation logic; registry operations preserve keys; generate_device_key only for new devices |

**Requirements:** 4/4 verified

### Anti-Patterns Found

| File | Pattern | Severity | Impact | Status |
|------|---------|----------|--------|--------|
| flash.py:682 | CLI recovery message shows device_key | LOW | CLI-only code path (from_tui=False), will be removed in Phase 26 | ACCEPTABLE |

**Note:** The device_key reference at line 682 is in a CLI-only code path (the else branch of `if from_tui`). Phase 25 scope is TUI internalization; Phase 26 will remove all CLI code paths entirely.

### Code Quality Observations

**Strengths:**
1. Clean separation of concerns — all TUI output uses entry.name, all internal operations use entry.key
2. Comprehensive coverage — verified 40+ output locations across flash.py, tui.py, output.py
3. Backward compatibility — existing devices.json keys preserved, no migration needed
4. Error handling — ValueError from generate_device_key caught with user-friendly message
5. Duplicate prevention — case-insensitive name check prevents user confusion

**Preserved Internal Usage:**
- Registry lookups: `registry.get(device_key)` — correct
- Cache paths: `ConfigManager(device_key, ...)` — correct
- Context dicts: `{"device": device_key}` for error templates — correct (internal debugging)
- DeviceEntry creation: `key=device_key` — correct

## Summary

Phase 25 goal **ACHIEVED**. All 4 success criteria verified:

1. ✓ Add-device wizard prompts only for display name — key auto-generated silently
2. ✓ Device config screen has no key edit option — DEVICE_SETTINGS reduced to 4 entries
3. ✓ All user-facing output shows entry.name — 40+ locations verified across flash.py, tui.py, output.py
4. ✓ Existing devices.json keys preserved — no re-derivation logic exists

Device keys are now completely invisible to users in the TUI. Users interact exclusively with display names. Internal operations correctly continue using device_key for registry lookups and cache paths.

**Ready to proceed:** Phase 26 (Remove CLI) can begin.

---

_Verified: 2026-02-01T20:30:00Z_
_Verifier: Claude (gsd-verifier)_
