# kalico-flash v2.0 Feature Specification

This document details the features planned for v2.0, which prepares kalico-flash for public release to the broader Klipper community.

**Target Users:** Klipper/Kalico users who want a simpler way to update MCU firmware without memorizing serial paths, flash commands, or config locations.

**Constraints:**
- Python 3.9+ stdlib only (no pip dependencies)
- Target platform: Raspberry Pi running Klipper/Moonraker
- Assumes Moonraker is installed and accessible at localhost:7125

---

## Table of Contents

1. [Simple TUI Menu](#1-simple-tui-menu)
2. [Print Status Check](#2-print-status-check)
3. [Post-Flash Verification](#3-post-flash-verification)
4. [Skip Menuconfig Flag](#4-skip-menuconfig-flag)
5. [Better Error Messages](#5-better-error-messages)
6. [Version Mismatch Detection](#6-version-mismatch-detection)
7. [Installation Script](#7-installation-script)
8. [README Documentation](#8-readme-documentation)
9. [Deployment Options](#deployment-options)

---

## 1. Simple TUI Menu

### Goal

Provide a user-friendly numbered menu interface so users can navigate kalico-flash without memorizing CLI flags. Similar in spirit to KIAUH but much simpler.

### Current Behavior

Users must know the correct flags:
```bash
python flash.py --list-devices
python flash.py --add-device
python flash.py --device octopus
```

Running `python flash.py` with no args jumps directly into interactive flash mode.

### Desired Behavior

Running `python flash.py` (or `kflash` after install) with no args shows a menu:

```
┌──────────────────────────────────────┐
│         kalico-flash v2.0            │
├──────────────────────────────────────┤
│  1) Flash a device                   │
│  2) List registered devices          │
│  3) Add new device                   │
│  4) Remove device                    │
│  5) Settings                         │
│  ─────────────────────────────────── │
│  0) Exit                             │
└──────────────────────────────────────┘
Select [1]: _
```

**Menu behavior:**
- Default selection is `1` (most common action)
- Invalid input shows error and re-prompts (max 3 attempts)
- After completing an action, return to menu (don't exit)
- Exit on `0`, `q`, or Ctrl+C
- Menu only shows when stdin is a TTY; non-TTY falls back to existing CLI behavior

**Settings submenu (option 5):**
```
┌──────────────────────────────────────┐
│            Settings                  │
├──────────────────────────────────────┤
│  1) Change Klipper directory         │
│  2) Change Katapult directory        │
│  3) View current settings            │
│  ─────────────────────────────────── │
│  0) Back to main menu                │
└──────────────────────────────────────┘
```

### Technical Notes

- Create new module `tui.py` (~150-200 lines estimated)
- Use only `print()` and `input()` - no curses or external libraries
- Box drawing uses Unicode characters (supported by all modern terminals)
- Fallback to ASCII (`+`, `-`, `|`) if Unicode detection fails
- Menu loop in `tui.py`, delegates to existing `cmd_*` functions in `flash.py`
- Existing CLI flags (`--device`, `--add-device`, etc.) continue to work unchanged

### Acceptance Criteria

- [ ] Running `python flash.py` with no args shows the menu
- [ ] All menu options work and return to menu after completion
- [ ] `--device KEY` and other flags bypass menu entirely
- [ ] Menu handles invalid input gracefully
- [ ] Non-TTY environments (piped input, cron) skip menu with helpful error

---

## 2. Print Status Check

### Goal

Prevent users from accidentally stopping Klipper mid-print, which would destroy the print and potentially damage the printer (thermal runaway if heaters left on without control).

### Current Behavior

The flash workflow stops Klipper unconditionally:
```
[Flash] Stopping Klipper...
```

If a print is running, the print fails, filament may blob, and heaters could be left in an unsafe state.

### Desired Behavior

Before stopping Klipper, query Moonraker for print status:

```
[Flash] Checking printer status...
[Error] Printer is currently printing (45% complete)
[Error] Refusing to flash while print is in progress.

Hint: Wait for print to complete, or cancel via Mainsail/Fluidd.
```

If printer is idle or in error state, proceed normally.

### Technical Notes

**Moonraker API endpoint:**
```
GET http://localhost:7125/printer/objects/query?print_stats
```

**Response (printing):**
```json
{
  "result": {
    "status": {
      "print_stats": {
        "state": "printing",
        "filename": "benchy.gcode",
        "progress": 0.45
      }
    }
  }
}
```

**States to block:**
- `printing` - Active print in progress
- `paused` - Print paused (user may resume)

**States to allow:**
- `standby` - Idle, no print
- `complete` - Print finished
- `cancelled` - Print was cancelled
- `error` - Printer in error state (may need reflash to fix)

**Implementation:**
- Add `moonraker.py` module for API calls (reusable for other features)
- Use `urllib.request` (stdlib) for HTTP calls
- Timeout: 5 seconds for API call
- If Moonraker is unreachable, warn but allow flash (user may be reflashing to fix connection issues)

**Moonraker URL configuration:**
- Default: `http://localhost:7125`
- Add `moonraker_url` to `GlobalConfig` in registry for custom setups
- Most users won't need to change this

### Acceptance Criteria

- [ ] Flash is blocked if `print_stats.state` is `printing` or `paused`
- [ ] Error message shows print filename and progress percentage
- [ ] Flash proceeds if printer is idle, complete, cancelled, or error
- [ ] If Moonraker unreachable, warn and prompt user to confirm continue
- [ ] Works with default Moonraker URL, configurable in settings

---

## 3. Post-Flash Verification

### Goal

Confirm that the flash actually succeeded by verifying the device reappears after flashing and Klipper can communicate with it.

### Current Behavior

After flash completes:
```
[Flash] Klipper restarted
[Success] Flashed Octopus Pro via katapult in 8.2s
```

User has no confirmation the device is actually working until they check Mainsail/Fluidd or see Klipper errors.

### Desired Behavior

After flash, verify device came back online:

```
[Flash] Firmware uploaded successfully
[Flash] Waiting for device to reappear...
[Flash] Device found after 2.3s: /dev/serial/by-id/usb-Klipper_stm32h723xx_...
[Flash] Restarting Klipper...
[Flash] Verifying MCU connection...
[Success] Flashed Octopus Pro via katapult - MCU responding
```

**If device doesn't reappear:**
```
[Flash] Firmware uploaded successfully
[Flash] Waiting for device to reappear...
[Warning] Device not found after 15s

Possible causes:
  - Flash failed silently (firmware corrupted)
  - USB cable disconnected during flash
  - Device stuck in bootloader mode

Recovery steps:
  1. Power cycle the printer (full power off, not just reset)
  2. Check USB cable connection
  3. Run: kflash --list-devices
  4. If device shows as 'katapult_*', try flashing again
```

### Technical Notes

**Device reappearance check:**
- After `flash_device()` returns success, poll `/dev/serial/by-id/` for device
- Look for device matching the registered serial pattern
- Poll interval: 500ms
- Timeout: 15 seconds (some boards take time to enumerate)
- Device should show `Klipper_*` prefix (not `katapult_*`) after successful flash

**MCU connection verification (optional enhancement):**
- After Klipper restart, query Moonraker for MCU status
- `GET http://localhost:7125/printer/objects/query?mcu`
- Check that MCU is responding (no protocol errors)
- This catches "flash succeeded but wrong firmware" scenarios

**Implementation location:**
- Add verification logic to `cmd_flash()` after flash completes
- Could be a new function in `flasher.py`: `verify_flash_success()`

### Acceptance Criteria

- [ ] After successful flash, tool waits for device to reappear in `/dev/serial/by-id/`
- [ ] Success message confirms device path
- [ ] If device doesn't appear within timeout, show warning with recovery steps
- [ ] Timeout is reasonable (15s) to handle slow USB enumeration
- [ ] Klipper is still restarted even if verification fails (user may need it running to diagnose)

---

## 4. Skip Menuconfig Flag

### Goal

Allow power users to skip the menuconfig TUI when they just want to rebuild and reflash with the existing cached configuration.

### Current Behavior

Every flash operation launches menuconfig:
```
[Config] Launching menuconfig...
<ncurses TUI appears, user must navigate and save/exit>
```

This is fine for first-time setup but tedious for routine updates.

### Desired Behavior

New flag `--skip-menuconfig` (or `-s` for short):

```bash
kflash --device octopus --skip-menuconfig
```

Behavior:
```
[Config] Using cached config for 'octopus'
[Config] MCU validated: stm32h723
[Build] Running make clean + make...
```

**If no cached config exists:**
```
[Error] No cached config for 'octopus'
[Error] Cannot skip menuconfig without existing config.

Run without --skip-menuconfig to configure the device first.
```

### Technical Notes

**Implementation:**
- Add `--skip-menuconfig` / `-s` flag to argparser
- Pass flag through to `cmd_flash()`
- In config phase: if flag set AND cached config exists, skip `run_menuconfig()` call
- Still perform MCU validation (load config, check MCU matches device)
- If flag set but no cache exists, error out (don't silently fall back to menuconfig)

**Interaction with TUI menu:**
- When using TUI menu option "Flash a device", prompt: "Skip menuconfig? [y/N]"
- Default is No (show menuconfig) to match current behavior

**Flag naming:**
- Long: `--skip-menuconfig`
- Short: `-s`
- Alternatives considered: `--no-menuconfig`, `--quick`, `-q`

### Acceptance Criteria

- [ ] `--skip-menuconfig` flag skips TUI if cached config exists
- [ ] Error with helpful message if no cached config
- [ ] MCU validation still runs (catches config/device mismatch)
- [ ] Flag works with `--device KEY`
- [ ] TUI menu offers skip option as y/n prompt

---

## 5. Better Error Messages

### Goal

When operations fail, provide clear error messages with actionable recovery steps so users can self-diagnose without searching forums.

### Current Behavior

Errors are technical and don't guide the user:
```
[Error] Flash failed: Device not responding
```

### Desired Behavior

Errors include context and recovery steps:

```
[Error] Flash failed: Device not responding after 60s

This usually means:
  - Device lost power during flash
  - USB connection is unstable
  - Bootloader is corrupted

Recovery steps:
  1. Power cycle the printer completely (not just reset)
  2. Check USB cable - try a different cable or port
  3. Run: kflash --list-devices
     - If device shows as 'katapult_*': try flash again
     - If device doesn't appear: may need DFU recovery
  4. For DFU recovery, see: https://docs.kalico.gg/mcu-recovery
```

### Error Categories and Messages

**Build Errors:**
```
[Error] Build failed: make returned exit code 2

Common causes:
  - Missing toolchain (arm-none-eabi-gcc not installed)
  - Incompatible Klipper version for this MCU
  - Corrupted source files

Recovery steps:
  1. Check build output above for specific error
  2. Verify toolchain: arm-none-eabi-gcc --version
  3. Try: cd ~/klipper && make clean && make menuconfig
```

**Device Not Found:**
```
[Error] Device 'octopus' not connected

The device is registered but not detected on USB.

Check:
  1. Is the printer powered on?
  2. Is the USB cable connected to the Pi?
  3. Run: ls /dev/serial/by-id/
     - If empty: no USB serial devices detected
     - If shows 'katapult_*': device is in bootloader mode
     - If shows 'Klipper_*': device is running (should be detected)
```

**Moonraker Unreachable:**
```
[Warning] Cannot reach Moonraker at localhost:7125

Moonraker may be stopped or misconfigured.
Proceeding without print status check.

To verify Moonraker: curl http://localhost:7125/printer/info
```

**MCU Mismatch:**
```
[Error] MCU mismatch: config has 'stm32f446' but device expects 'stm32h723'

You selected the wrong MCU in menuconfig.
Flashing wrong firmware could damage your board.

Fix:
  1. Run flash again (without --skip-menuconfig)
  2. In menuconfig, select: STM32H723
  3. Save and exit
```

**Service Control Failed:**
```
[Error] Failed to stop Klipper service

Possible causes:
  - Klipper service doesn't exist (not installed via systemd)
  - Permission denied (passwordless sudo not configured)

Check:
  1. Service status: sudo systemctl status klipper
  2. Sudo access: sudo -n true && echo "OK" || echo "Need password"
```

**No Bootloader Installed**
```
Possible cause:
  For STM32 boards without Katapult:
  [Flash] No Katapult detected
  [Flash] Attempting make flash...
  [Flash] Bootloader entry failed - device has no responsive bootloader

  Check-Guidance:
  This board requires manual bootloader entry:
    1. Hold BOOT0 button (or set BOOT0 jumper)
    2. Press RESET
    3. Release BOOT0
    4. Run: kflash --device octopus
```
This is why Katapult is so valuable - it eliminates the need for physical button presses.


### Technical Notes

- Create `messages.py` module with error message templates
- Messages are functions that accept context parameters (device name, MCU type, etc.)
- Each error category has: summary line, common causes, numbered recovery steps
- Keep messages concise but complete - users should be able to self-recover
- Include relevant commands they can copy/paste to diagnose

### Acceptance Criteria

- [ ] All error paths have contextual recovery guidance
- [ ] Messages include specific commands to diagnose
- [ ] No generic "operation failed" without explanation
- [ ] Messages fit on a standard 80-column terminal
- [ ] Recovery steps are numbered and actionable

---

## 6. Version Mismatch Detection

### Goal

Detect when MCU firmware is out of sync with host Klipper version and alert the user before they waste time on unnecessary reflash or miss a needed update.

### Current Behavior

No version checking. User must manually track whether MCUs need updates after running `git pull` on Klipper source.

### Desired Behavior

At start of flash workflow, check version alignment:

**When MCU needs update:**
```
[Discovery] Target: Octopus Pro (stm32h723)
[Version] Host Klipper: v0.12.0-145-gabcd1234
[Version] MCU firmware:  v0.12.0-100-g5678efgh
[Version] MCU is 45 commits behind - update recommended

Proceed with flash? [Y/n]: _
```

**When MCU is current:**
```
[Discovery] Target: Octopus Pro (stm32h723)
[Version] Host Klipper: v0.12.0-145-gabcd1234
[Version] MCU firmware:  v0.12.0-145-gabcd1234
[Version] MCU firmware is up to date

Flash anyway? [y/N]: _
```

The default changes based on whether update is needed (Y for outdated, N for current).

### Technical Notes

**Getting host Klipper version:**
```bash
cd ~/klipper && git describe --tags --always --dirty
# Output: v0.12.0-145-gabcd1234
```
Or read from `~/klipper/.git/HEAD` and refs.

**Getting MCU firmware version:**
Query Moonraker API:
```
GET http://localhost:7125/printer/info
```

Response includes:
```json
{
  "result": {
    "software_version": "v0.12.0-145-gabcd1234",
    "mcu_info": {
      "mcu": {
        "mcu_version": "v0.12.0-100-g5678efgh"
      }
    }
  }
}
```

**Version comparison:**
- Parse git describe format: `v{major}.{minor}.{patch}-{commits}-g{hash}`
- Compare commit count for same major.minor.patch
- If major/minor/patch differs, definitely needs update
- Show commit difference for user context

**Edge cases:**
- If Moonraker unreachable: skip version check, warn user
- If MCU not responding (why user is flashing): skip check
- If version format unrecognized: skip check, warn user
- Multiple MCUs: check the specific MCU being flashed

**Implementation:**
- Add version checking to early phase of `cmd_flash()`
- New function in `moonraker.py`: `get_mcu_version(mcu_name)`
- New function: `get_host_klipper_version(klipper_dir)`

### Acceptance Criteria

- [ ] Shows host and MCU versions before flash
- [ ] Indicates whether update is needed
- [ ] Default prompt answer reflects recommendation (Y if outdated, N if current)
- [ ] Gracefully handles unreachable Moonraker or unresponsive MCU
- [ ] Works with multiple MCUs (checks the one being flashed)

---

## 7. Installation Script

### Goal

Provide a simple `install.sh` that creates a `kflash` command accessible from any directory.

### Current Behavior

Users must `cd` to the kalico-flash directory and run `python flash.py`:
```bash
cd ~/kalico-flash
python3 kalico-flash/flash.py --list-devices
```

### Desired Behavior

After running install script:
```bash
kflash --list-devices  # works from anywhere
kflash                 # launches TUI menu
```

### Installation Script

```bash
#!/bin/bash
# install.sh - Install kalico-flash and create 'kflash' command

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FLASH_SCRIPT="$SCRIPT_DIR/kalico-flash/flash.py"
COMMAND_NAME="kflash"

# Verify flash.py exists
if [[ ! -f "$FLASH_SCRIPT" ]]; then
    echo "Error: flash.py not found at $FLASH_SCRIPT"
    echo "Make sure you're running this from the kalico-flash repository root."
    exit 1
fi

# Make executable
chmod +x "$FLASH_SCRIPT"

# Find appropriate bin directory
if [[ -d "$HOME/.local/bin" ]]; then
    BIN_DIR="$HOME/.local/bin"
    # Ensure it's in PATH
    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        echo "Note: ~/.local/bin is not in PATH"
        echo "Add to your ~/.bashrc: export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
elif [[ -d "$HOME/bin" ]]; then
    BIN_DIR="$HOME/bin"
else
    # Create ~/.local/bin if neither exists
    BIN_DIR="$HOME/.local/bin"
    mkdir -p "$BIN_DIR"
    echo "Created $BIN_DIR"
    echo "Add to your ~/.bashrc: export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# Create symlink
ln -sf "$FLASH_SCRIPT" "$BIN_DIR/$COMMAND_NAME"

echo "Installed: $BIN_DIR/$COMMAND_NAME -> $FLASH_SCRIPT"
echo ""
echo "Usage:"
echo "  kflash              # Interactive menu"
echo "  kflash --help       # Show all options"
echo "  kflash --device KEY # Flash specific device"

# Verify it works
if command -v kflash &> /dev/null; then
    echo ""
    echo "Verification: kflash command is available"
else
    echo ""
    echo "Note: You may need to restart your shell or run:"
    echo "  source ~/.bashrc"
fi
```

### Uninstall Script

```bash
#!/bin/bash
# uninstall.sh - Remove kflash command

COMMAND_NAME="kflash"

for BIN_DIR in "$HOME/.local/bin" "$HOME/bin" "/usr/local/bin"; do
    if [[ -L "$BIN_DIR/$COMMAND_NAME" ]]; then
        rm "$BIN_DIR/$COMMAND_NAME"
        echo "Removed: $BIN_DIR/$COMMAND_NAME"
        exit 0
    fi
done

echo "kflash command not found in standard locations"
```

### Technical Notes

- Script uses symlink, not copy - updates to flash.py are immediately available
- Prefers `~/.local/bin` (modern convention) over `~/bin` (legacy)
- Does not use `/usr/local/bin` to avoid needing sudo
- Shebang in `flash.py` (`#!/usr/bin/env python3`) makes symlink work directly
- MainsailOS and FluiddPi have `~/.local/bin` in PATH by default

### Acceptance Criteria

- [ ] `install.sh` creates working `kflash` symlink
- [ ] Works without sudo
- [ ] Provides clear feedback on success
- [ ] Warns if bin directory not in PATH
- [ ] `uninstall.sh` cleanly removes symlink
- [ ] Both scripts are idempotent (safe to run multiple times)

---

## 8. README Documentation

### Goal

Update README.md with clear installation instructions, usage examples, and troubleshooting guidance for new users.

### Current README

Basic overview focused on development context.

### New README Structure

```markdown
# kalico-flash

One-command firmware updates for Klipper/Kalico MCU boards.

## What It Does

kalico-flash automates the Klipper firmware build and flash process:
- Auto-discovers USB-connected MCU boards
- Caches menuconfig settings per device
- Handles Katapult bootloader with make flash fallback
- Manages Klipper service lifecycle (safe stop/restart)

## Quick Start

### Installation

```bash
cd ~
git clone https://github.com/you/kalico-flash.git
cd kalico-flash
./install.sh
```

### First Device Setup

```bash
kflash
# Select: 3) Add new device
# Follow prompts to register your board
```

### Flash a Device

```bash
kflash
# Select: 1) Flash a device
# Or directly: kflash --device octopus
```

## Requirements

- Raspberry Pi (or similar) running Klipper + Moonraker
- Python 3.9+
- USB-connected MCU board
- Katapult bootloader (recommended) or DFU capability

## Commands

| Command | Description |
|---------|-------------|
| `kflash` | Interactive menu |
| `kflash --device KEY` | Flash specific device |
| `kflash --device KEY -s` | Flash without menuconfig |
| `kflash --list-devices` | Show registered devices |
| `kflash --add-device` | Register new board |
| `kflash --remove-device KEY` | Unregister board |
| `kflash --help` | Full help |

## Supported Boards

Any USB-connected board that:
- Appears in `/dev/serial/by-id/` as `Klipper_*` or `katapult_*`
- Can be flashed via Katapult or `make flash`

Tested with:
- BTT Octopus Pro (STM32H723)
- LDO Nitehawk 36 (RP2040)

## Troubleshooting

### Device not found
...

### Flash failed
...

### MCU protocol error after update
...

## Updating

```bash
cd ~/kalico-flash
git pull
```

## Uninstalling

```bash
cd ~/kalico-flash
./uninstall.sh
rm -rf ~/kalico-flash
```
```

### Acceptance Criteria

- [ ] README has clear installation instructions
- [ ] Quick start gets user from zero to first flash
- [ ] All CLI commands documented with examples
- [ ] Common errors have troubleshooting entries
- [ ] Update and uninstall instructions included

---

## Deployment Options

### Recommended: Git Clone

The recommended installation method is git clone. This is consistent with how most Klipper ecosystem tools are installed (Klipper itself, Moonraker, KIAUH, Katapult).

**Installation:**
```bash
cd ~
git clone https://github.com/youruser/kalico-flash.git
cd kalico-flash
./install.sh
```

**Updating:**
```bash
cd ~/kalico-flash
git pull
```

**Advantages:**
- Simple, familiar to Klipper users
- Easy updates via `git pull`
- User can inspect code before running
- No package manager or pip required

### Alternative: Curl One-Liner

For users who want a single command:

```bash
curl -sSL https://raw.githubusercontent.com/youruser/kalico-flash/main/install-remote.sh | bash
```

The `install-remote.sh` script would:
1. Clone the repository to `~/kalico-flash`
2. Run `install.sh`
3. Print success message

**Advantages:**
- Single command installation
- Good for documentation/tutorials

**Disadvantages:**
- "Curl pipe bash" makes some users uncomfortable
- Slightly more complex to maintain

### Not Recommended: pip/PyPI

While Python packages are typically distributed via pip/PyPI, this is **not recommended** for kalico-flash because:

1. **Stdlib-only constraint** - No dependencies to manage anyway
2. **Target environment** - Raspberry Pi images may have restricted pip
3. **Klipper convention** - Users expect git clone for Klipper tools
4. **Update workflow** - `git pull` is simpler than pip upgrade

### Moonraker Update Manager Integration

For users who want automatic update notifications, they can add to `moonraker.conf`:

```ini
[update_manager kalico-flash]
type: git_repo
path: ~/kalico-flash
origin: https://github.com/youruser/kalico-flash.git
primary_branch: main
is_system_service: False
```

This shows kalico-flash in Mainsail/Fluidd's update manager alongside Klipper, Moonraker, etc.

---

## Implementation Priority

Suggested implementation order based on dependencies and user impact:

1. **Skip Menuconfig Flag** - Small, self-contained, enables automation
2. **Better Error Messages** - Improves UX for all users immediately
3. **Print Status Check** - Safety feature, requires Moonraker module
4. **Post-Flash Verification** - Builds on existing flash flow
5. **Version Mismatch Detection** - Requires Moonraker module (built in #3)
6. **Simple TUI Menu** - Largest change, can use all other features
7. **Installation Script** - Simple, do alongside documentation
8. **README Documentation** - Final polish, documents all features

---

## Out of Scope for v2.0

The following were considered but deferred:

| Feature | Reason |
|---------|--------|
| Katapult first-time installation | Too many board variations, high brick risk |
| CAN bus device support | Different workflow, significant complexity |
| SHA256 config change detection | Nice optimization but not essential |
| Multi-device batch flash | Edge case, adds complexity |
| Moonraker plugin/web UI | Future enhancement, CLI is primary interface |
| Firmware rollback | Requires version tracking infrastructure |

---

*Document created: 2026-01-26*
*Based on v1.0 codebase analysis and ecosystem research*
