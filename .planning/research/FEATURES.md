# Feature Landscape: kalico-flash

**Domain:** Embedded firmware build/flash CLI for Klipper 3D printer MCUs
**Researched:** 2026-01-26
**Overall confidence:** MEDIUM (verified with official Moonraker/Klipper docs, CLI best practices)

---

## v2.0 Features Research

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

## v2.0 Anti-Features (explicitly excluded)

Things to deliberately NOT build and why:

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| curses-based fancy menus | Windows compat, complexity | Simple numbered input |
| Auto-update Klipper source | Dangerous - breaks MCU compatibility | User runs `git pull` manually |
| Multi-device batch flash | Complexity, error recovery unclear | Flash one at a time |
| CAN bus device support | Different discovery mechanism | Separate tool or future version |
| RPi MCU flashing | Different workflow (linux service) | Document manual process |
| Firmware version rollback | Requires storing binaries, complex | User keeps backups |
| GUI/web interface | Out of scope for CLI tool | Moonraker integration later |
| Windows/Mac support | Target is Raspberry Pi | Document Pi-only |
| Colored output (v2.0) | Not all terminals support | Use phase labels instead |
| Interactive prompts mid-flash | Dangerous during flash | All prompts before flash starts |
| Automatic config migration | Kconfig format may change | User re-runs menuconfig |

**Key principle:** This tool does ONE thing well - flash USB-connected MCUs on a Raspberry Pi. Resist scope creep.

---

## v2.0 Feature Dependencies

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

### Feature implementation order (suggested)

1. **Better Error Messages** - Foundation, improves all other features
2. **Device Exclusion** - Simple registry change, unblocks Beacon users
3. **Skip Menuconfig** - Low effort, high value for repeat flashing
4. **Installation Script** - One-time setup, then easier testing
5. **TUI Menu** - Main UX improvement, uses better error messages
6. **Post-Flash Verification** - Uses discovery module
7. **Print Status Check** - New Moonraker integration
8. **Version Detection** - Lowest priority, informational only

---

## v2.0 Summary

### Must-Have for v2.0
- Simple numbered TUI menu (not curses)
- Print status safety check (block if printing/paused)
- Post-flash verification with timeout and recovery steps
- `--skip-menuconfig` flag
- Better error messages with numbered recovery steps
- Device exclusion flag in registry

### Nice-to-Have
- Installation script with symlink
- Version mismatch detection (informational warning)

### Explicitly Excluded
- curses-based fancy menus (Windows compat, complexity)
- Auto-update Klipper source
- Multi-device batch operations
- CAN bus support
- GUI/web interface

**Confidence Assessment:**
- Moonraker API: HIGH (verified with official docs)
- Klipper print_stats: HIGH (verified with Status Reference)
- CLI patterns: MEDIUM (industry practices, not Klipper-specific)
- curses limitations: HIGH (Python docs confirm Windows issues)

---

# v1.0 Features Research (Preserved)

The original v1.0 feature research from 2026-01-25 follows for reference.

---

## Table Stakes

Features the tool must have to be useful at all. Without these, a user would just keep running the manual commands.

### 1. USB Device Discovery via /dev/serial/by-id/

| Aspect | Detail |
|--------|--------|
| **Why expected** | The entire point is eliminating the manual `ls -l /dev/serial/by-id/` step and copy-pasting long device paths |
| **Complexity** | Low |
| **Notes** | Scan `/dev/serial/by-id/`, glob-match against registry patterns. Must use stable by-id symlinks, never `/dev/ttyACMx`. Confidence: HIGH -- this is a simple directory scan, well-understood pattern |

### 2. Device Registry (add / remove / list)

| Aspect | Detail |
|--------|--------|
| **Why expected** | Without persistent device profiles, the tool has no memory between runs and offers no advantage over a shell alias |
| **Complexity** | Low |
| **Notes** | JSON file with friendly names, serial patterns, MCU type, flash method, directory paths. CRUD via `--add-device`, `--remove-device`, `--list-devices`. Must validate uniqueness of friendly names and serial patterns |

### 3. Menuconfig Integration (Interactive TUI Passthrough)

| Aspect | Detail |
|--------|--------|
| **Why expected** | Klipper firmware configuration is done through `make menuconfig`, an ncurses TUI. Users must be able to configure their MCU settings |
| **Complexity** | Low-Medium |
| **Notes** | CRITICAL: Must use `subprocess.run()` with inherited stdin/stdout/stderr (no capture). The TUI needs a real terminal. This is a common mistake -- using `subprocess.check_output()` will break the ncurses interface. Working directory must be set to `klipper_dir` |

### 4. Config Caching with SHA256 Change Detection

| Aspect | Detail |
|--------|--------|
| **Why expected** | Running menuconfig every single flash is the #1 pain point in the manual workflow. Caching `.config` per device and detecting changes is the core value proposition |
| **Complexity** | Medium |
| **Notes** | Cache `.config` to `configs/<device>.config` with `.sha256` sidecar. Copy cached config into klipper dir before menuconfig. After menuconfig (or skip), hash and compare. This drives the "skip menuconfig if unchanged" and "skip rebuild if unchanged" optimizations |

### 5. Build Orchestration (make clean + make)

| Aspect | Detail |
|--------|--------|
| **Why expected** | Must run the build after config. This is the compile step -- `make clean && make -j$(nproc)` |
| **Complexity** | Low |
| **Notes** | Must set `cwd` to `klipper_dir`. Parallel build with `-j$(nproc)` for reasonable speed on Raspberry Pi (4+ minutes on Pi 4 for some MCUs). Should capture and display build output in real-time (not buffer it) |

### 6. Flash Execution (Two Methods)

| Aspect | Detail |
|--------|--------|
| **Why expected** | The actual firmware write. Two methods must work: `make flash FLASH_DEVICE=<path>` and Katapult `flashtool.py -f <klipper_dir>/out/klipper.bin -d <path>` |
| **Complexity** | Medium |
| **Notes** | Method is per-device in registry. Katapult needs both `katapult_dir` (for flashtool.py) and the built binary path. `make flash` needs `FLASH_DEVICE` env/arg. Both need the serial device path resolved at runtime |

### 7. Klipper Service Stop/Start Around Flash

| Aspect | Detail |
|--------|--------|
| **Why expected** | Klipper holds serial ports open. Flash will fail if klipper.service is running. This is the most common user error when flashing manually |
| **Complexity** | Low |
| **Notes** | `sudo systemctl stop klipper` before flash, `sudo systemctl start klipper` after -- even on failure. Must be wrapped in try/finally or equivalent. Requires passwordless sudo (standard on MainsailOS/FluiddPi). This is a non-negotiable safety requirement |

### 8. Error Handling with Service Recovery

| Aspect | Detail |
|--------|--------|
| **Why expected** | If the build fails or flash fails, Klipper must still be restarted. Leaving the printer with klipper stopped is a usability disaster (printer is offline until user SSHes in and manually restarts) |
| **Complexity** | Medium |
| **Notes** | Every failure path must ensure klipper restart. Clear error messages with the failing command and its exit code. Users need to know what went wrong to fix it |

### 9. Direct Device Selection (--device NAME)

| Aspect | Detail |
|--------|--------|
| **Why expected** | Power users and scripting require non-interactive invocation. `./flash.py --device octopus-pro --skip-menuconfig` should work without prompts |
| **Complexity** | Low |
| **Notes** | Bypasses interactive device selection. Must still verify the device is physically connected before attempting flash |

### 10. Dry Run Mode (--dry-run)

| Aspect | Detail |
|--------|--------|
| **Why expected** | Users need to verify what commands will execute before running them, especially when setting up a new device or debugging flash failures |
| **Complexity** | Low |
| **Notes** | Print each command that would be executed without running it. Do not stop klipper, do not build, do not flash. Essential for debugging and learning |

---

## Differentiators

Features that make this tool meaningfully better than a shell script or manual workflow. Not strictly required but significantly improve UX.

### 1. Smart Skip Logic (Config Unchanged = Skip Menuconfig + Skip Rebuild)

| Aspect | Detail |
|--------|--------|
| **Value proposition** | The SHA256 change detection enables intelligent skipping: if config hasn't changed since last build, skip both menuconfig AND rebuild. Turns a 5-minute process into a 30-second flash-only operation |
| **Complexity** | Medium |
| **Notes** | Controlled via `--skip-menuconfig` and `--no-clean`. The tool should clearly communicate what it's skipping and why. This is the single biggest UX win over manual workflow |

### 2. Connection Status in Device Listing

| Aspect | Detail |
|--------|--------|
| **Value proposition** | `--list-devices` shows which registered devices are currently connected. Immediately answers "is my board plugged in?" without separate `ls` commands |
| **Complexity** | Low |
| **Notes** | Cross-reference registry patterns against current `/dev/serial/by-id/` contents. Display checkmark for connected, X for disconnected. Show the resolved device path when connected |

### 3. Unknown Device Detection and Registration Prompt

| Aspect | Detail |
|--------|--------|
| **Value proposition** | During discovery, devices that match no registry pattern are shown as "Unknown" with an offer to register. Eliminates the "I see a device but don't know what it is" confusion |
| **Complexity** | Low |
| **Notes** | In the project brief example: `? Unknown device [/dev/serial/by-id/usb-Klipper_rp2040_E66...]` with option `'a' to add new`. Natural on-ramp for adding new boards |

### 4. Interactive Add-Device Wizard

| Aspect | Detail |
|--------|--------|
| **Value proposition** | Step-by-step guided registration: pick USB device, name it, set flash method, run initial menuconfig, cache the resulting config. Much friendlier than manually editing JSON |
| **Complexity** | Medium |
| **Notes** | Auto-generates serial pattern from selected device path. Should extract MCU family from the serial ID string where possible (e.g., `stm32h723` from `usb-Klipper_stm32h723xx_...`). Saves the user from understanding the JSON schema |

### 5. Clear Progress Indicators with Phase Labels

| Aspect | Detail |
|--------|--------|
| **Value proposition** | `[Discovery]`, `[Config]`, `[Build]`, `[Flash]` phase labels (as shown in project brief) make it obvious what's happening and where failures occur |
| **Complexity** | Low |
| **Notes** | Not a spinner or progress bar (those are complex and low-value on a terminal). Simple bracketed phase labels with success/failure markers. Terminal color (green checkmark, red X) if stdout is a TTY |

### 6. Build Output Size Reporting

| Aspect | Detail |
|--------|--------|
| **Value proposition** | Showing firmware binary size after build (e.g., "done (48KB)") is a quick sanity check -- wildly different sizes indicate config errors |
| **Complexity** | Low |
| **Notes** | Read `klipper/out/klipper.bin` size after successful build. Requires knowing the output path, which is always `out/klipper.bin` relative to `klipper_dir` |

### 7. Incremental Build Support (--no-clean)

| Aspect | Detail |
|--------|--------|
| **Value proposition** | Skipping `make clean` when config hasn't changed saves 2-3 minutes on a Pi. Experienced users can choose speed over safety |
| **Complexity** | Low |
| **Notes** | Only safe when config is unchanged. The tool should warn or refuse `--no-clean` when config has changed, since stale object files can produce corrupt firmware |

---

## v1.0 Anti-Features

Things to deliberately NOT build in v1 and why.

### 1. CAN Bus Device Discovery and Flashing

| Aspect | Detail |
|--------|--------|
| **Why avoid** | CAN bus flashing uses completely different discovery (`~/klippy-env/bin/python ~/klipper/scripts/canbus_query.py can0`), different flash tool arguments, and CAN interface setup. It's a separate domain with separate failure modes. The project brief explicitly defers this |
| **What to do instead** | Support USB-only in v1. Design the flash method abstraction to be extensible so CAN support can be added later without refactoring the core |

### 2. Moonraker API Integration / Web UI

| Aspect | Detail |
|--------|--------|
| **Why avoid** | Adding Moonraker component support means writing a Moonraker plugin, handling HTTP/WebSocket APIs, and building Fluidd/Mainsail UI elements. This is 10x the scope of a CLI tool and a completely different development skillset |
| **What to do instead** | Keep it as a standalone CLI. Users SSH to flash firmware -- this is already the established pattern and won't change until the Klipper ecosystem standardizes remote firmware updates |

### 3. Multi-Device Batch Flash

| Aspect | Detail |
|--------|--------|
| **Why avoid** | Batch flashing all devices in one command is risky: if the first board bricks, the user may want to abort rather than flash the second. Different boards have different configs, different menuconfig states, and different failure modes. Sequential non-interactive flash of multiple devices needs careful error-handling design that's premature for v1 |
| **What to do instead** | Flash one device at a time. Users can script `./flash.py --device X && ./flash.py --device Y` if they want batch behavior |

### 4. Firmware Version Tracking and Rollback

| Aspect | Detail |
|--------|--------|
| **Why avoid** | Klipper firmware version is tied to the git commit of the klipper source tree, not to the binary. Tracking "which commit was flashed" requires git integration with the klipper repo, storing build artifacts, and implementing rollback (which means re-building from an old commit). High complexity, low frequency of use |
| **What to do instead** | Users can `git log` in their klipper directory. The tool should not manage the klipper source tree |

### 5. Automatic Klipper Git Pull Before Build

| Aspect | Detail |
|--------|--------|
| **Why avoid** | Pulling the latest klipper code before building firmware is dangerous -- it can introduce breaking changes. Klipper/Kalico updates should be a deliberate decision, not automated into the flash workflow. This especially matters for Kalico fork users who may be on specific branches |
| **What to do instead** | The tool builds whatever is in `klipper_dir` right now. Users update Klipper separately (via Moonraker update manager or manual `git pull`) |

### 6. Config Diff Display

| Aspect | Detail |
|--------|--------|
| **Why avoid** | While showing `.config` diffs sounds useful, Klipper's `.config` format contains hundreds of lines of auto-generated `# CONFIG_xxx is not set` entries. Diffs are noisy and unhelpful. The meaningful signal is "config changed: yes/no" which the SHA256 hash already provides |
| **What to do instead** | Report "config changed" or "config unchanged". If users want details, they can diff the cached files manually |

### 7. Bootloader (Katapult) Building and Installation

| Aspect | Detail |
|--------|--------|
| **Why avoid** | Katapult bootloader installation is a one-time setup per board using DFU/SWD and is board-specific. It requires different hardware connections (holding BOOT button, using STLink, etc.). Mixing bootloader setup with routine firmware flashing creates dangerous confusion -- wrong flash could brick the bootloader |
| **What to do instead** | Assume Katapult bootloader is already installed. Document bootloader setup as a prerequisite in README |

### 8. GUI / TUI Wrapper

| Aspect | Detail |
|--------|--------|
| **Why avoid** | Building a curses-based TUI around what is essentially a sequential workflow adds complexity with no value. The tool already passes through to menuconfig's TUI when needed. Adding another TUI layer on top creates confusion about which interface is which |
| **What to do instead** | Simple line-based CLI with clear prompts. Let menuconfig be the only TUI |

### 9. Plugin or Extension System

| Aspect | Detail |
|--------|--------|
| **Why avoid** | The tool has exactly 2 flash methods (make flash, katapult) and a fixed workflow. An extension system would be over-engineering for a tool with 2 MCU boards. If a third method is needed, add it to the code |
| **What to do instead** | Hard-code the two flash methods. Use clean function boundaries so adding a third is a one-file change |

### 10. External Dependencies (pip packages)

| Aspect | Detail |
|--------|--------|
| **Why avoid** | The project brief explicitly requires Python 3.9+ stdlib only. Raspberry Pi environments often have fragile Python setups with system-managed packages. Adding pip dependencies creates "externally-managed-environment" errors, venv management burden, and version conflicts with klipper's own klippy-env |
| **What to do instead** | Pure stdlib. `json`, `subprocess`, `pathlib`, `hashlib`, `fnmatch`, `os`, `shutil` are all that's needed |

---

## Feature Dependencies

Features that require other features to exist first.

```
Device Registry
  |
  +---> Device Discovery (needs patterns from registry to match)
  |
  +---> Config Caching (needs device names for cache file paths)
  |       |
  |       +---> Skip Logic (needs cached hash to compare against)
  |       |
  |       +---> Menuconfig Integration (needs cached .config to restore)
  |
  +---> Flash Execution (needs flash_method and paths from registry)
  |       |
  |       +---> Build Orchestration (flash needs built binary)
  |       |       |
  |       |       +---> Config Caching (build needs .config in place)
  |       |
  |       +---> Service Stop/Start (flash needs klipper stopped)
  |
  +---> Add Device Wizard (writes to registry)
          |
          +---> Device Discovery (wizard scans USB to pick device)
          |
          +---> Menuconfig Integration (wizard runs initial menuconfig)
          |
          +---> Config Caching (wizard saves initial .config)
```

### Critical Path for MVP

The minimum dependency chain that produces a working flash:

1. **Device Registry** (load JSON) -- foundational data store
2. **Device Discovery** (scan USB, match patterns) -- find the board
3. **Config Caching** (copy .config, hash) -- prepare build config
4. **Menuconfig Integration** (subprocess passthrough) -- user configures MCU
5. **Build Orchestration** (make clean + make) -- compile firmware
6. **Service Stop/Start** (systemctl) -- free serial port
7. **Flash Execution** (make flash or katapult) -- write firmware
8. **Error Handling** (try/finally service restart) -- safety net

### Secondary Features (After MVP Works)

- Add Device Wizard (convenience, but users can edit JSON manually for v0.1)
- Skip Logic (optimization, not correctness)
- Connection Status (nice-to-have)
- Dry Run (debugging aid)

---

## UX Patterns

How similar CLI tools present information to users, and what klipper-flash should adopt.

### Phase-Based Output (Adopted from platformio, cargo)

Tools that orchestrate multi-step builds use labeled phases:

```
[Discovery] Scanning /dev/serial/by-id/...
[Config]    Loading cached config for Octopus Pro v1.1
[Build]     make clean... make -j4... done (48KB)
[Flash]     Stopping klipper.service...
[Flash]     Flashing via katapult flashtool.py...
[Flash]     Starting klipper.service...
[Done]      Octopus Pro v1.1 flashed successfully.
```

**Recommendation:** Use bracketed phase labels aligned to consistent width. This is already in the project brief's example output -- keep it.

### Color as Enhancement, Not Requirement

```
Good: [+] Success (green if TTY, plain text if pipe)
Bad:  Invisible output when piped to file because colors are hardcoded
```

**Recommendation:** Check `sys.stdout.isatty()` before emitting ANSI color codes. Use green for success markers, red for errors, yellow for warnings/skips. Never make color the only signal -- always include text like "SUCCESS" or "FAILED".

### Interactive Prompts with Defaults

```
Select device [1-3, or 'a' to add new]: 1
Flash method [make_flash/katapult] (default: katapult):
Klipper directory [~/klipper]:
```

**Recommendation:** Show numbered options for selection. Show defaults in brackets. Accept Enter for default. This pattern is from standard Python `input()` workflows and requires no external library.

### Error Messages That Help Users Fix Problems

```
Bad:  "Flash failed"
Good: "Flash failed: katapult flashtool.py exited with code 1
       Device /dev/serial/by-id/usb-katapult_stm32h723xx_... not found.

       Possible causes:
       - Board is not in bootloader mode (try holding BOOT and pressing RESET)
       - USB cable is disconnected
       - Different USB port since last registration

       Klipper service has been restarted."
```

**Recommendation:** On failure, show: (1) what failed, (2) the exact command and exit code, (3) likely causes for common errors, (4) confirmation that klipper was restarted. Domain-specific error messages are a major differentiator over raw shell commands.

### Confirmation Before Destructive Actions

The flash operation is destructive (overwrites firmware). The workflow should include a natural confirmation point. In the default flow, the interactive device selection IS the confirmation. For `--device` mode, no extra confirmation is needed because the user explicitly named the target.

**Recommendation:** Do NOT add "Are you sure?" prompts. The interactive selection already provides intent. Adding extra confirmation slows down the power-user workflow and trains users to blindly hit Enter.

### Non-Zero Exit Codes for Scripting

| Exit Code | Meaning |
|-----------|---------|
| 0 | Success |
| 1 | General error (build failed, flash failed) |
| 2 | Device not found (named device not connected) |
| 3 | Registry error (device not in registry, JSON parse error) |
| 130 | User cancelled (Ctrl+C) |

**Recommendation:** Define exit codes so that scripts can react appropriately. `./flash.py --device octopus-pro && echo "Success" || echo "Failed with $?"`.

### Quiet vs Verbose Output

Most CLI tools support verbosity levels. For klipper-flash:

- **Default:** Phase labels + summary (as shown in project brief)
- **Future consideration:** `--verbose` flag to show full `make` output. For v1, always showing build output is fine since it's useful for debugging.

**Recommendation for v1:** Show all output. Build output from `make` streams to terminal naturally since we use `subprocess.run()` with inherited stdio. Don't suppress anything -- users flash firmware rarely enough that verbosity is an asset, not a nuisance.

---

## MVP Feature Prioritization

### Must Ship (v1.0)

1. Device registry (JSON CRUD)
2. USB device discovery with pattern matching
3. Config caching with SHA256 change detection
4. Menuconfig passthrough (interactive TUI)
5. Build orchestration (make clean + make)
6. Flash execution (make flash + katapult methods)
7. Klipper service stop/start with guaranteed restart
8. `--device NAME` for non-interactive use
9. `--skip-menuconfig` for cached config
10. `--dry-run` for safety

### Should Ship (v1.1)

1. `--no-clean` for incremental builds
2. Add-device wizard (interactive registration)
3. Connection status in `--list-devices`
4. Unknown device detection with registration prompt
5. Build output size reporting
6. Colored output (TTY-aware)

### Defer Indefinitely

Everything in the Anti-Features section.

---

## Sources and Confidence

| Finding | Confidence | Basis |
|---------|------------|-------|
| Klipper build workflow (make menuconfig/make/make flash) | HIGH | Direct codebase evidence in flash_script_plan.md reference commands; well-established Klipper workflow from training data |
| Katapult flashtool.py invocation pattern | HIGH | Direct codebase evidence in flash_script_plan.md lines 178-187 showing exact commands |
| Service stop/start requirement | HIGH | Documented in project brief line 122-123; universal Klipper constraint (klipper holds serial ports) |
| /dev/serial/by-id/ discovery pattern | HIGH | Direct codebase evidence in mcu_octopus.cfg and mcu_nitehawk36.cfg showing actual serial paths |
| subprocess.run() for menuconfig | HIGH | Documented in project brief line 124-125; well-known ncurses requirement |
| CAN bus complexity as separate domain | MEDIUM | Based on training data knowledge of Klipper CAN bus workflows; not verified against current docs |
| CLI UX patterns (phase labels, exit codes) | MEDIUM | Based on training data knowledge of platformio, cargo, and general CLI design; no current sources verified |
| Python 3.9 stdlib sufficiency | HIGH | Project brief explicitly requires stdlib-only; all needed modules (json, subprocess, pathlib, hashlib, fnmatch) are stdlib |
| Incremental build safety concerns | MEDIUM | Based on general knowledge of Make build systems; not verified against Klipper's specific Makefile behavior |
| Moonraker print_stats API | HIGH | Verified with official Moonraker documentation |
| Klipper Status Reference (print_stats, mcu objects) | HIGH | Verified with official Klipper documentation |
| CLI error message best practices | MEDIUM | Verified with clig.dev guidelines |
