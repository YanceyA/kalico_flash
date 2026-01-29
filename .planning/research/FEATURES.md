# Feature Landscape: kalico-flash

**Domain:** Embedded firmware build/flash CLI for Klipper 3D printer MCUs
**Researched:** 2026-01-29
**Overall confidence:** MEDIUM (verified with official Moonraker/Klipper docs, CLI best practices)

---

## v2.1 Features Research: Panel TUI and Flash All

**Focus:** Panel-based terminal UI redesign, batch flash, config screen, countdown timer
**Researched:** 2026-01-29

---

### Table Stakes

Features that must exist for the panel TUI and Flash All to feel complete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Bordered panel layout with sections | KIAUH and similar Klipper tools use box-drawn panels to organize status, devices, and actions. Users of the ecosystem expect this visual structure. Without it, the redesign is just a restyled menu. | Med | Unicode box chars (rounded corners). Print full screen on each redraw. No curses -- clear and reprint. |
| Device list grouped by category | Registered/New/Blocked grouping provides instant situational awareness. A flat list forces users to mentally classify each device. | Low | Continuous numbering across groups (1-N). Group headers as subheaders within the device panel. |
| Status panel showing last operation result | Users need "what just happened?" feedback without scrolling. KIAUH shows component status in its right panel; kalico-flash needs equivalent for last flash/build outcome. | Med | Persist across menu redraws. Show device name + PASS/FAIL + brief detail. Clear when new operation begins. |
| Two-column action layout | Actions arranged in two columns use terminal width efficiently and reduce vertical scrolling. Standard pattern in KIAUH-style menus. | Low | Calculate from terminal width. Pad with spaces. Fall back to single column on narrow terminals. |
| Flash All: single service bracket | The core value of batch: stop Klipper once, build+flash each device sequentially, restart Klipper once. Per-device stop/start is slow (5+ seconds each) and fragile. | Med | Wrap entire loop in existing `klipper_service_stopped()` context manager. |
| Flash All: continue on failure | If device 2 of 5 fails, devices 3-5 must still be attempted. Aborting on first failure wastes the batch opportunity and leaves remaining devices unflashed. | Low | Collect results in list. Report summary at end. Never abort mid-batch for a single device failure. |
| Per-device progress during Flash All | Users must know which device is processing, which succeeded, which failed. Without this, batch is a black hole. | Med | Print step divider per device: `--- [2/5] Octopus Pro ---`. Show PASS/FAIL inline. Summary table at end. |
| Config screen as separate view | Settings need their own panel that replaces the main view. Cramming settings into the action menu breaks the mental model of "see devices, pick action." | Med | Clear screen, draw config panel with current values, accept edits, return to main on back. |
| Countdown timer with keypress cancel | Flashing firmware is destructive. A 5-second countdown with "press any key to cancel" is standard safety UX for irreversible operations. Especially important for Flash All where multiple devices are at stake. | Low | `select.select()` on stdin with 1-second timeout loop (Unix). Print countdown updating in place with `\r`. |
| Numbered device references | Devices get stable numbers within a session. "Flash 3" means the same device until registry changes. Numbers appear in device panel and are accepted as action input. | Low | Assign at menu draw, store mapping in session state dict. |

### Differentiators

Features that make this feel polished. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Spaced panel headers `[ D E V I C E S ]` | Visual polish matching KIAUH aesthetic. Makes the tool feel intentional and crafted, not cobbled together. | Low | Pure string formatting: insert spaces between chars, wrap in brackets. |
| Truecolor theme with ANSI 16 fallback | 24-bit color on capable terminals (most modern terminals including Pi's default), graceful fallback to ANSI 16 on limited terminals. Modern look without breaking compatibility. | Med | Detect via `COLORTERM` env var. Theme as palette dict. All color through single abstraction. |
| Connection status indicators in device list | Green dot for connected, dim/red for disconnected. Immediate visibility without running a separate command. | Low | Check `/dev/serial/by-id/` at draw time. Brief cache to avoid repeated I/O. |
| Flash All summary table | After batch completes, formatted table: Device / Status / Duration. Much clearer than scrolling through sequential output. | Low | Collect `(device, status, duration)` tuples during loop. Print aligned table at end. |
| Step dividers in terminal output | Visual separators between build phases: `=== Building Firmware ===`. Breaks the wall of make output into scannable sections. | Low | Print before each phase within a flash operation. |
| Screen-aware layout | Adapt panel widths to terminal size via `shutil.get_terminal_size()`. Minimum 60 cols with graceful degradation. | Low | Already stdlib. Clamp widths between min/max. |
| Flash All: skip unchanged configs | If a device's config hash hasn't changed since last build, skip rebuild and go straight to flash. Turns a 5-device batch from 25 minutes to under 5 minutes. | Med | Requires SHA256 comparison already implemented. Announce "Config unchanged, skipping build" per device. |

### Anti-Features

Things to deliberately NOT build. Common mistakes when building panel TUIs.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Full curses/ncurses interactive TUI | Massive complexity. Breaks piping, breaks some SSH clients, requires handling resize signals, partial screen updates, and input buffering. Overkill for a menu that redraws after each action. | Print-and-clear: clear screen, print all panels, wait for input. No cursor positioning, no partial updates. Simple, robust, debuggable. |
| Real-time progress bars (tqdm-style) | Adds dependency (forbidden) or complex custom code. Build output already streams from make. A progress bar fighting subprocess output for the terminal causes visual chaos. | Let make output stream naturally between step dividers. Show spinner only for brief waits (service stop) using simple `\r` overwrite. |
| Async/parallel flash of multiple devices | USB serial flashing is inherently serial. Parallel flash attempts cause USB bus contention and potential firmware corruption. There is no safe way to flash two USB devices simultaneously. | Sequential with continue-on-failure. The service bracket (single stop/start) already provides the batch speed win. |
| Mouse support | Target users SSH into a Pi. Mouse events are unreliable over SSH, especially through tmux/screen. Adds complexity for zero practical benefit. | Keyboard numbers only. Type number, press Enter. |
| Config file editor in TUI | Editing Kconfig values in a custom editor reimplements menuconfig poorly. menuconfig handles option dependencies, validation, and help text. A custom editor would be buggy and incomplete. | Config screen shows tool settings (paths, preferences) only. Kconfig editing launches `make menuconfig` as subprocess (already works). |
| Tab/panel switching with keyboard shortcuts | Alt+1/Alt+2 panel switching is a different UX paradigm than numbered menus. Mixing paradigms confuses users. Also unreliable over SSH. | Single view at a time. Main menu OR config screen. Not tabbed, not split-pane. |
| Undo/rollback for flash operations | Firmware flashing is one-way. "Undo" implies the previous firmware is stored, which it is not. Promising rollback creates false safety expectations. | Countdown timer IS the safety mechanism. Once flashing starts, it completes or fails. |
| Persistent log viewer in TUI | Reimplements `less`/`tail` poorly. Users already have terminal scrollback and can pipe to files. | Print output inline. User scrolls their terminal or redirects to file. |
| Animated loading screens | Spinners and animations over SSH add visual noise and can cause rendering artifacts with slow connections. | Static status messages: "Stopping Klipper..." then "Klipper stopped." |

### Expected Behavior: Panel Layout

The main screen has three visual sections stacked vertically within a single bordered box:

```
╭─────────────────────────────────────────────╮
│           [ S T A T U S ]                   │
│  Last: Octopus Pro flashed successfully     │
├─────────────────────────────────────────────┤
│           [ D E V I C E S ]                 │
│                                             │
│  Registered                                 │
│    1) Octopus Pro v1.1      ● Connected     │
│    2) Nitehawk 36           ○ Disconnected  │
│                                             │
│  New                                        │
│    3) usb-Klipper_rp2040_E66...             │
│                                             │
│  Blocked                                    │
│    -  Beacon Probe          (excluded)      │
│                                             │
├─────────────────────────────────────────────┤
│           [ A C T I O N S ]                 │
│                                             │
│  F) Flash device        A) Flash All        │
│  C) Configure           S) Settings         │
│  R) Refresh             Q) Quit             │
│                                             │
╰─────────────────────────────────────────────╯
```

**Key behaviors:**
- Screen clears and redraws fully after each action returns
- Device numbers are input targets: after pressing F, prompt asks "Device number:"
- Status panel updates with result of last action
- Blocked devices shown but not selectable
- New (unregistered) devices shown with truncated serial path
- Actions use letter keys (not numbers) to avoid collision with device numbers

### Expected Behavior: Flash All

```
Flash All: 3 devices queued

[Countdown] Flashing in 5... 4... 3... 2... 1...
            Press any key to cancel.

[Service] Stopping Klipper...
[Service] Klipper stopped.

─── [1/3] Octopus Pro v1.1 ───────────────────
[Config]  Loading cached config
[Build]   make clean && make -j4... done (48KB)
[Flash]   Flashing via Katapult... OK
[Verify]  Device reconnected ✓

─── [2/3] Nitehawk 36 ────────────────────────
[Config]  Loading cached config
[Build]   make clean && make -j4... done (22KB)
[Flash]   Flashing via Katapult... FAILED
          flashtool.py exited with code 1

─── [3/3] EBB36 ──────────────────────────────
[Config]  Config unchanged, skipping build
[Flash]   Flashing via Katapult... OK
[Verify]  Device reconnected ✓

[Service] Starting Klipper...
[Service] Klipper started.

╭─────────────────────────────────────────────╮
│         [ S U M M A R Y ]                   │
│                                             │
│  Octopus Pro v1.1    PASS    12.4s          │
│  Nitehawk 36         FAIL    8.2s           │
│  EBB36               PASS    3.1s           │
│                                             │
│  Result: 2/3 succeeded                      │
╰─────────────────────────────────────────────╯
```

**Key behaviors:**
- Countdown before any destructive action (5 seconds default, configurable in settings)
- Single Klipper stop at start, single restart at end
- Each device gets a step divider with index and name
- Failed devices do NOT abort the batch
- Summary table at end with per-device status and duration
- Flash All only includes registered, non-excluded, connected devices
- If no devices qualify, show message and return to menu

### Expected Behavior: Config Screen

```
╭─────────────────────────────────────────────╮
│         [ S E T T I N G S ]                 │
│                                             │
│  1) Klipper directory    ~/klipper          │
│  2) Katapult directory   ~/katapult         │
│  3) Flash method         katapult           │
│  4) Countdown seconds    5                  │
│  5) Auto-skip menuconfig ON                 │
│                                             │
│  B) Back to main menu                       │
╰─────────────────────────────────────────────╯
```

**Key behaviors:**
- Replaces main view entirely (clear + redraw)
- Numbered items for editing: type number, enter new value
- Changes persist to registry JSON immediately
- B returns to main menu
- No nested sub-settings screens

### Expected Behavior: Countdown Timer

```
[Countdown] Flashing in 5... (press any key to cancel)
[Countdown] Flashing in 4...
[Countdown] Flashing in 3...
[Countdown] Flashing in 2...
[Countdown] Flashing in 1...
[Flash] Proceeding...
```

**Key behaviors:**
- Updates in place using `\r` carriage return (single line, no scroll)
- Any keypress during countdown cancels and returns to menu
- Default 5 seconds, configurable in settings (0 = no countdown)
- Used before single flash AND Flash All
- On cancel, print "Cancelled." and return to menu cleanly

### Feature Dependencies

```
Panel Drawing Engine (borders, headers, columns)
  |
  +--> Status Panel (needs operation result data)
  +--> Device Panel (needs registry + discovery at draw time)
  +--> Action Panel (needs letter-key mapping)
  +--> Config Screen (reuses panel drawing, separate view)
  |
Flash All
  |
  +--> Device Panel (selects which devices to flash)
  +--> Service Context Manager (single bracket)
  +--> Per-device build+flash loop
  +--> Result collection --> Summary Table
  |
Countdown Timer (independent, used by Flash and Flash All)
Truecolor Theme (independent, applied to all panel drawing)
```

### MVP Recommendation for v2.1

Build in this order:

1. **Panel drawing engine** -- borders, headers, two-column layout, screen clear+redraw
2. **Device panel with grouping** -- registered/new/blocked, connection status, numbering
3. **Action dispatch with letter keys** -- F/A/C/S/R/Q mapping
4. **Status panel** -- last operation result display
5. **Countdown timer** -- before flash operations
6. **Flash All** -- sequential with continue-on-failure, summary table
7. **Config screen** -- separate view for settings
8. **Truecolor theme** -- color palette applied to all panels

Defer:
- Screen-aware adaptive layout (hardcode 80 cols initially)
- Flash All skip-unchanged optimization (add after basic batch works)

---

## v2.0 Features Research (Preserved)

This section covers the planned v2.0 features. v1.0 feature research is preserved below.

---

## TUI Menu

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Numbered selection (1-9) | Users expect to type a number and press Enter | Low | Single digit works universally |
| Clear menu display | Show options with numbers | Low | Print statements sufficient |
| Return to menu after action | Don't exit after each operation | Low | Simple while loop |
| Exit option | Way to quit cleanly | Low | "0" or "q" to exit |
| TTY detection | Error gracefully if not interactive | Low | Already implemented in v1 |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Arrow key navigation | More polished UX | Medium | Requires curses (stdlib but Windows issues) |
| Search/filter | Quick find in long lists | High | Overkill for <10 devices |
| Animated selection | Visual feedback | Medium | curses dependency |
| Status inline | Show device connection status in menu | Low | Good UX improvement |

### Expected Behavior

**Industry standard (simple CLI menus):**
```
kalico-flash Menu
=================
1. Flash device
2. Add new device
3. List devices
4. Remove device
0. Exit

Choice [1-4, 0 to exit]:
```

**Key behaviors:**
- Invalid input prompts re-entry (don't crash)
- Menu redisplays after each action completes
- Actions that fail return to menu with error message
- Ctrl+C exits cleanly at any point

**Recommendation:** Build simple numbered menu first. curses adds complexity and Windows compatibility issues. Python stdlib curses is NOT available on Windows without third-party wheels (confirmed: [Python curses docs](https://docs.python.org/3/library/curses.html)). Since target is Raspberry Pi Linux, curses would work there, but simple numbered input is sufficient and tested.

**Sources:**
- [Python curses documentation](https://docs.python.org/3/library/curses.html)
- [curses-menu library](https://github.com/pmbarrett314/curses-menu) (third-party, not stdlib)

---

## Safety Checks (Print Status)

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Check before flash | Never flash during active print | Low | Single API call |
| Clear error message | "Printer is currently printing" | Low | String formatting |
| Blocking behavior | Refuse to proceed | Low | Early return |
| Moonraker API integration | Standard approach | Medium | HTTP request to localhost |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Wait-for-idle option | --wait flag to poll until idle | Medium | Polling loop with timeout |
| Progress display | Show print progress while waiting | Low | Nice but unnecessary |
| Multiple state handling | Detect paused, canceling, etc. | Low | Handle edge cases |

### Expected Behavior

**Moonraker API endpoint:**
```
GET http://localhost:7125/printer/objects/query?print_stats
```

**Response includes:**
```json
{
  "status": {
    "print_stats": {
      "state": "standby|printing|paused|complete|error",
      "filename": "...",
      "print_duration": 1234.5
    }
  }
}
```

**State values (from Klipper Status Reference):**
- `standby` - Safe to flash
- `printing` - BLOCK flash
- `paused` - BLOCK flash (user may resume)
- `complete` - Safe to flash
- `error` - Safe to flash (printer already stopped)

**Error message format:**
```
[Safety] Printer is currently printing 'benchy.gcode' (45% complete)
         Cannot flash firmware while print is active.

         Options:
         1. Wait for print to complete
         2. Cancel print via Fluidd/Mainsail
         3. Use --force to override (DANGEROUS)
```

**Fallback behavior:**
- If Moonraker unreachable, warn but allow flash with confirmation
- If printer disconnected (klippy not ready), allow flash (that's why you're flashing!)

**Recommendation:** Check `print_stats.state` - if "printing" or "paused", block. Use Python stdlib `urllib.request` for HTTP (no dependencies). Default timeout 5 seconds.

**Sources:**
- [Moonraker Printer Administration API](https://moonraker.readthedocs.io/en/latest/external_api/printer/)
- [Klipper Status Reference - print_stats](https://www.klipper3d.org/Status_Reference.html)

---

## Post-Flash Verification

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Wait for device reappear | Confirm flash succeeded | Medium | Polling loop |
| Timeout with failure | Don't wait forever | Low | 30-60 second max |
| Success message | "Device reconnected successfully" | Low | Print statement |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Recovery steps on timeout | Numbered list of what to try | Low | High value, low effort |
| Serial prefix change detection | Detect katapult_* vs Klipper_* | Low | Already have pattern matching |
| MCU version verification | Confirm new firmware version | High | Requires Klipper connection |

### Expected Behavior

**Verification flow:**
1. Flash completes (Katapult or make flash reports success)
2. Wait up to 30 seconds for device to reappear in `/dev/serial/by-id/`
3. Check for expected serial pattern (device registry has pattern)
4. Report success or timeout with recovery steps

**Polling strategy (from retry pattern research):**
- Initial wait: 3 seconds (device needs time to reboot)
- Poll interval: 2 seconds
- Max attempts: 15 (30 seconds total)
- Exponential backoff NOT needed (device either works or doesn't)

**Timeout recovery message:**
```
[Flash] Firmware written successfully
[Verify] Waiting for device to reconnect...
[Verify] TIMEOUT - Device did not reappear after 30 seconds

Recovery steps:
1. Check USB cable connection
2. Try unplugging and replugging the board
3. Check if device appears: ls /dev/serial/by-id/
4. If device shows katapult_* prefix, bootloader is active but firmware didn't flash
5. Try flashing again with: kflash --device octopus-pro
6. If still failing, try manual flash: cd ~/klipper && make flash FLASH_DEVICE=...
```

**Sources:**
- [Retry Pattern Best Practices](https://harish-bhattbhatt.medium.com/best-practices-for-retry-pattern-f29d47cd5117)
- [CLI Guidelines - Recoverable Operations](https://clig.dev/)

---

## Skip Menuconfig

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| --skip-menuconfig (-s) flag | Command-line option | Low | argparse addition |
| Cached config detection | Check if .config exists | Low | File existence check |
| Error if no cached config | Don't proceed without config | Low | Early validation |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Config hash comparison | Only skip if config unchanged | Medium | SHA256 of .config |
| Auto-skip when cached | Default to skip if exists | Low | Behavior change |
| --force-menuconfig | Override auto-skip | Low | If auto-skip enabled |

### Expected Behavior

**Klipper's KCONFIG_CONFIG pattern:**
```bash
# Standard Klipper approach for multiple boards
make menuconfig KCONFIG_CONFIG=config.octopus
make KCONFIG_CONFIG=config.octopus -j4
make flash KCONFIG_CONFIG=config.octopus FLASH_DEVICE=/dev/serial/by-id/...
```

**kalico-flash already caches configs:**
```
~/.config/kalico-flash/configs/{device-key}/.config
```

**Implementation:**
1. Check if cached config exists for device
2. If `--skip-menuconfig` and no config: ERROR
3. If `--skip-menuconfig` and config exists: copy to klipper dir, skip menuconfig
4. If no flag: run menuconfig as normal (may update cached config)

**Edge cases:**
- Cached config from different Klipper version: menuconfig may update it
- Config references hardware that changed: user responsibility

**Recommendation:** Simple flag implementation. Don't auto-skip - explicit is better than implicit. User knows when they want to skip.

**Sources:**
- [Klipper Installation - KCONFIG_CONFIG](https://www.klipper3d.org/Installation.html)
- [Voron Automating MCU Updates](https://docs.vorondesign.com/community/howto/drachenkatze/automating_klipper_mcu_updates.html)

---

## Error Messages

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Context (what were we doing) | "[Build] Compilation failed" | Low | Already have phase labels |
| Cause (what went wrong) | "make returned exit code 2" | Low | Capture subprocess output |
| Recovery steps | Numbered list of fixes | Medium | Write good copy |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Log file for details | Write verbose output to file | Medium | File I/O, path handling |
| Pre-populated bug report URL | GitHub issue with context | Medium | URL encoding |
| Error codes | Machine-readable error types | Low | Already have exception hierarchy |

### Expected Behavior

**From CLI Guidelines (clig.dev):**
- Rewrite errors for human understanding
- Position critical information at end (where eyes focus)
- Include debug info responsibly (file, not terminal)
- Group similar errors under single header

**Error message template:**
```
[Phase] What went wrong
        Why it might have happened

        To fix this:
        1. First thing to try
        2. Second thing to try
        3. If still failing, try X

        For more details: ~/.config/kalico-flash/logs/build.log
```

**Example - build failure:**
```
[Build] Firmware compilation failed (exit code 2)
        This usually means a configuration mismatch or missing toolchain.

        To fix this:
        1. Run 'kflash --device octopus-pro' without --skip-menuconfig
        2. In menuconfig, verify MCU type matches your board
        3. Check arm-none-eabi-gcc is installed: arm-none-eabi-gcc --version
        4. Review build log: cat ~/klipper/out/klipper.log
```

**Example - device not found:**
```
[Discovery] Device 'octopus-pro' not connected
            Expected serial pattern: usb-Klipper_stm32h723xx_*

            To fix this:
            1. Check USB cable is connected
            2. Verify device appears: ls /dev/serial/by-id/
            3. If device shows different name, re-register: kflash --add-device
            4. If using CAN bus, note this tool only supports USB devices
```

**Sources:**
- [Command Line Interface Guidelines](https://clig.dev/)
- [Error Handling in CLI Tools](https://medium.com/@czhoudev/error-handling-in-cli-tools-a-practical-pattern-thats-worked-for-me-6c658a9141a9)

---

## Version Detection

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Detect mismatch post-flash | Compare host vs MCU | Medium | Requires Klipper running |
| Warning message | "MCU version mismatch detected" | Low | String formatting |
| Recovery guidance | "Reflash or update Klipper" | Low | Static text |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Pre-flash version check | Warn before flashing | High | MCU must be connected and running |
| Automatic version match | Pull correct git commit | High | Out of scope (dangerous) |

### Expected Behavior

**The problem (from Klipper discourse):**
When host Klipper updates but MCU firmware is old, you get:
```
mcu 'mcu': Command format mismatch: endstop_home oid=%c clock=%u...
```

**Klipper provides this info via:**
- Host version: `git describe --always --tags --long --dirty` in klipper dir
- MCU version: `printer.mcu.mcu_version` via Moonraker API (requires running Klipper)

**Detection approach:**
1. After flash, if Klipper starts successfully, query `printer.mcu.mcu_version`
2. Compare with host version (git describe output)
3. If mismatch, warn but don't fail (flash was successful)

**Challenges:**
- Klipper must restart and connect to MCU first
- Version format: `v0.12.0-148-g1a2b3c4d` (git describe)
- Partial matches may be OK (same major.minor)

**Warning message:**
```
[Verify] Version mismatch detected
         Host Klipper: v0.12.0-148-g1a2b3c4d
         MCU firmware: v0.11.0-284-g5e6f7a8b

         This may cause "Command format mismatch" errors.
         To fix: Update Klipper host (git pull) then reflash all MCUs.
```

**Recommendation:** Implement as informational warning only. Don't block on mismatch - user may have intentional version pinning. LOW priority - most users will see Klipper's own error message anyway.

**Sources:**
- [Klipper MCU Protocol Error](https://klipper.discourse.group/t/mcu-protocol-error-caused-by-running-an-older-version-of-the-firmware/10371)
- [Mainsail MCU Protocol Error FAQ](https://docs.mainsail.xyz/faq/klipper_errors/command-format-mismatch)
- [Klipper Status Reference - mcu object](https://www.klipper3d.org/Status_Reference.html)

---

## Installation Script

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Symlink to PATH | `kflash` command available globally | Low | ln -s |
| Detect existing installation | Don't overwrite without confirmation | Low | File exists check |
| Uninstall instructions | How to remove | Low | Documentation |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Auto-detect PATH location | Find writable bin directory | Medium | Check multiple locations |
| Shell completion | Tab completion for device names | High | Bash/Zsh specific |
| Update mechanism | Check for new versions | High | Network, versioning |

### Expected Behavior

**Installation locations (priority order):**
1. `~/.local/bin/` - User-local, no sudo needed (preferred)
2. `~/bin/` - Alternative user-local
3. `/usr/local/bin/` - System-wide, requires sudo

**Install script (`install.sh`):**
```bash
#!/bin/bash
set -e

INSTALL_DIR="${HOME}/.local/bin"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Create bin directory if needed
mkdir -p "$INSTALL_DIR"

# Create symlink
ln -sf "${SCRIPT_DIR}/flash.py" "${INSTALL_DIR}/kflash"

# Make executable
chmod +x "${SCRIPT_DIR}/flash.py"

echo "Installed kflash to ${INSTALL_DIR}/kflash"
echo ""
echo "Ensure ${INSTALL_DIR} is in your PATH:"
echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
echo "  source ~/.bashrc"
```

**Uninstall:**
```bash
rm ~/.local/bin/kflash
```

**PATH considerations:**
- MainsailOS/FluiddPi may not have `~/.local/bin` in PATH by default
- Script should check and advise if not in PATH
- Never modify PATH automatically (user decision)

**Sources:**
- [Beginner's Guide to Executables](https://dev.to/hbalenda/beginner-s-guide-to-usr-local-bin-4fe2)
- [AWS CLI Installation Pattern](https://docs.aws.amazon.com/cli/v1/userguide/install-linux.html)

---

## Device Exclusion

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Mark device as non-flashable | Registry flag | Low | Boolean in JSON |
| Skip in selection menus | Don't offer excluded devices | Low | Filter in display |
| Show in list with status | "(excluded)" annotation | Low | String formatting |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Exclusion reason | "Beacon probe - use Beacon updater" | Low | String field |
| Temporary exclusion | Time-based or flag-based | Medium | Complexity not worth it |
| Pattern-based exclusion | Exclude by serial pattern | Medium | Regex overhead |

### Expected Behavior

**Use case: Beacon probe**
Beacon probe appears in `/dev/serial/by-id/` but should NOT be flashed via kalico-flash - it has its own update tool.

**Registry format:**
```json
{
  "devices": {
    "beacon": {
      "name": "Beacon Probe",
      "mcu": "rp2040",
      "serial_pattern": "usb-Beacon_*",
      "excluded": true,
      "exclusion_reason": "Use Beacon's built-in updater"
    }
  }
}
```

**Behavior:**
- `--list-devices`: Shows device with "(excluded)" status
- Interactive selection: Excluded devices not offered
- `--device beacon`: Error with exclusion reason
- `--add-device`: Option to mark as excluded during registration

**Error message:**
```
[Discovery] Device 'beacon' is excluded from flashing
            Reason: Use Beacon's built-in updater

            To flash anyway: kflash --device beacon --force
            To remove exclusion: kflash --remove-exclusion beacon
```

**Recommendation:** Simple boolean flag with optional reason string. Don't over-engineer with patterns or time-based rules.

---

## All Anti-Features (explicitly excluded)

Things to deliberately NOT build and why:

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| curses-based fancy menus | Windows compat, complexity | Print-and-clear panels |
| Auto-update Klipper source | Dangerous - breaks MCU compatibility | User runs `git pull` manually |
| CAN bus device support | Different discovery mechanism | Separate tool or future version |
| RPi MCU flashing | Different workflow (linux service) | Document manual process |
| Firmware version rollback | Requires storing binaries, complex | User keeps backups |
| GUI/web interface | Out of scope for CLI tool | Moonraker integration later |
| Windows/Mac support | Target is Raspberry Pi | Document Pi-only |
| Interactive prompts mid-flash | Dangerous during flash | All prompts before flash starts |
| Automatic config migration | Kconfig format may change | User re-runs menuconfig |
| Mouse support in TUI | Unreliable over SSH | Keyboard numbers only |
| Parallel device flashing | USB contention, corruption risk | Sequential with continue-on-failure |
| Tab switching / split panes | Wrong paradigm for numbered menus | Single view at a time |

**Key principle:** This tool does ONE thing well - flash USB-connected MCUs on a Raspberry Pi. Resist scope creep.

---

## Feature Dependencies (All Versions)

### v2.1 features depending on v2.0 capabilities

| v2.1 Feature | Depends On | v2.0 Capability |
|--------------|------------|-----------------|
| Panel Layout | Themed output | tui.py / output.py |
| Device Panel | Registry + discovery | registry.py, discovery.py |
| Status Panel | Operation results | BuildResult, FlashResult models |
| Flash All | Service bracket, build+flash | service.py, build.py, flasher.py |
| Config Screen | Settings persistence | registry.py (global config) |
| Countdown Timer | TTY input handling | Already available (Unix select) |
| Truecolor Theme | Color abstraction | tui.py theme system |

### v2 features depending on v1 capabilities

| v2 Feature | Depends On | v1 Capability |
|------------|------------|---------------|
| TUI Menu | Phase-labeled output | output.py module |
| Print Status Check | Moonraker connection | New (HTTP to localhost) |
| Post-Flash Verification | USB scanning | discovery.py module |
| Skip Menuconfig | Config caching | config.py module |
| Better Error Messages | Exception hierarchy | errors.py module |
| Version Detection | Moonraker API | New (HTTP to localhost) |
| Installation Script | Entry point | flash.py (already executable) |
| Device Exclusion | Device registry | registry.py module |

---

## Sources and Confidence

| Finding | Confidence | Basis |
|---------|------------|-------|
| Panel TUI print-and-clear pattern | HIGH | Standard Unix terminal pattern; KIAUH uses this approach |
| KIAUH panel layout style | MEDIUM | WebSearch results describe menu structure; could not fetch exact source |
| Flash All single-bracket pattern | HIGH | Follows from existing `klipper_service_stopped()` context manager design |
| Countdown with `select.select()` | HIGH | Python stdlib, well-documented Unix pattern |
| Continue-on-failure for batch | HIGH | Standard batch processing pattern; CLI UX best practice |
| Sequential-only USB flashing | HIGH | Hardware constraint; USB serial is single-device |
| Truecolor detection via COLORTERM | MEDIUM | Common convention but not standardized |
| CLI progress display patterns | MEDIUM | Verified with Evil Martians CLI UX article |
