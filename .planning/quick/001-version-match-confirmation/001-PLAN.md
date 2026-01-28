# Quick Task 001: Add Version Match Confirmation Dialog

## Problem

When flashing a device whose MCU firmware version already matches the host Klipper version, the tool should prompt the user to confirm whether they want to continue. Currently, version information is displayed but no check triggers a confirmation when versions match.

User's observed behavior:
```
[Version] Host Klipper: v2026.01.00-0-g4a173af8
[Version]   [*] MCU nhk: v2026.01.00-0-g4a173af8
```
Expected: A confirmation dialog like "MCU firmware is already up-to-date. Continue anyway? [y/N]"

## Root Cause

In `kflash/flash.py` lines 736-772, the version check logic:
1. Displays host version and MCU versions ✓
2. Marks the target MCU with asterisk ✓
3. Checks if MCU is **outdated** and warns ✓
4. Does NOT check if versions **match** to prompt for confirmation ✗

## Solution

Add a check after the version display logic: if target MCU version equals host version, prompt user to confirm they want to flash anyway since firmware is already current.

## Tasks

### Task 1: Add version match confirmation in cmd_flash()

**File:** `kflash/flash.py`
**Location:** After line 766 (the `is_mcu_outdated` check block)

**Changes:**
1. Add an `else` branch to handle when versions match (not outdated)
2. Use `out.confirm()` to ask user if they want to continue
3. Return 0 if user declines

**Code to add (after the outdated warning block, around line 766):**
```python
                else:
                    # MCU firmware matches host - confirm user wants to reflash
                    if not out.confirm(
                        "MCU firmware is already up-to-date. Continue anyway?",
                        default=False
                    ):
                        out.phase("Flash", "Cancelled - firmware already current")
                        return 0
```

## Acceptance Criteria

- [ ] When MCU version matches host version, user is prompted "MCU firmware is already up-to-date. Continue anyway? [y/N]"
- [ ] Default is No (N) to prevent accidental reflashing
- [ ] If user declines, flash is cancelled with informative message
- [ ] If user confirms, flash proceeds normally
- [ ] Existing "outdated" warning behavior is preserved
