# Pitfalls Research: klipper-flash

**Domain:** Python CLI tool for Klipper firmware building and flashing via subprocesses
**Researched:** 2026-01-25 (v1.0), 2026-01-26 (v2.0 additions), 2026-01-29 (v2.1 panel TUI + batch flash)
**Overall confidence:** HIGH (domain knowledge from Klipper ecosystem, Linux device model, Python subprocess semantics)

---

## Critical Pitfalls (can brick boards or lose data)

### CP-1: Klipper Service Not Restarted After Flash Failure

**Description:** If the flash subprocess fails (timeout, device disconnect, bad firmware image) and the tool exits without restarting the klipper service, the printer is left in a dead state. The user's running print queue, temperature monitoring, and safety watchdogs are all offline. On a heated printer, this means no thermal runaway protection.

**Warning signs:**
- Any unhandled exception between `systemctl stop klipper` and `systemctl start klipper`
- Early return or `sys.exit()` in error handling paths
- KeyboardInterrupt (Ctrl+C) during flash not caught
- Code reviews that show `stop` without a corresponding `finally` block containing `start`

**Prevention:**
- Wrap the entire stop-flash-start sequence in a `try/finally` block where `finally` ALWAYS runs `systemctl start klipper`
- Also catch `KeyboardInterrupt` and `SystemExit` explicitly in the finally path
- Add a signal handler for SIGTERM that triggers service restart before exit
- Consider a watchdog approach: record "klipper stopped" state to a temp file, and on tool startup check if a previous run left klipper stopped

**Phase to address:** Phase 1 (core flash flow). This is the single most important safety invariant in the entire tool. Must be the first thing designed and the last thing cut.

---

### CP-2: Flashing Wrong Firmware to Wrong Board

**Description:** If the user selects "Octopus Pro" but the .config cached is actually for the Nitehawk RP2040 (or vice versa), the wrong firmware binary gets flashed. For STM32 boards with Katapult bootloader, this typically results in a board that boots into a non-functional state. Recovery requires DFU mode via boot jumper (physical access to the board). For RP2040, recovery is easier (hold BOOTSEL and replug), but still disruptive.

**Warning signs:**
- Config files named generically or mismatched to device registry entries
- No validation that .config MCU architecture matches the target device
- Copy-paste errors in devices.json serial patterns
- `configs/` directory manually edited

**Prevention:**
- After loading a cached .config, parse it and verify the `CONFIG_BOARD_*` or `CONFIG_MCU` line matches the expected MCU family from devices.json
- Display the MCU architecture from .config before flashing and require confirmation: "About to flash STM32H723 firmware to Octopus Pro. Continue?"
- Never allow a flash to proceed if .config does not exist for the selected device
- Store MCU type in the .config.sha256 sidecar as metadata for cross-validation

**Phase to address:** Phase 1 (config manager). The config-device binding must be validated at flash time, not just at registration time.

---

### CP-3: Flashing During Active Print

**Description:** If klipper is running a print and the user runs `flash.py`, stopping klipper mid-print causes the hotend to remain at temperature with no firmware control (heater stuck on until thermal fuse blows or SSR is de-energized). The print is destroyed, and in worst case, the hotend or bed heater causes damage.

**Warning signs:**
- No check for printer state before stopping klipper
- Klipper API (Moonraker) not queried for print status
- Tool assumes "if user runs it, they want it"

**Prevention:**
- Before stopping klipper, query Moonraker API at `http://localhost:7125/printer/objects/query?print_stats` to check if `state` is `printing` or `paused`
- If printing, refuse to proceed with a clear message: "Printer is currently printing. Abort print first or use --force to override."
- If Moonraker is unreachable (not running), warn but allow proceed (the user may be recovering from a crashed klipper)
- This is a SHOULD, not a MUST for MVP -- a simple "Are you sure?" prompt is acceptable as minimum

**Phase to address:** Phase 2 (safety checks). Can be a simple prompt in Phase 1, upgraded to Moonraker API check in Phase 2.

---

### CP-4: Interrupted Flash Leaves Board in Bootloader Mode

**Description:** When flashing via Katapult, the flashtool.py script first sends a reset command to put the MCU into bootloader mode, then streams the firmware. If the process is interrupted between these two steps (network drop, Ctrl+C, SSH disconnect), the board is stuck in Katapult bootloader mode. It will NOT appear as a Klipper device in `/dev/serial/by-id/` -- it appears as a Katapult device instead. The tool's discovery will not find it by its Klipper serial pattern.

**Warning signs:**
- Device disappears from discovery after a failed flash attempt
- `/dev/serial/by-id/` shows `usb-katapult_*` instead of `usb-Klipper_*`
- Flash fails with "device not found" on retry because the pattern expects Klipper prefix

**Prevention:**
- Support BOTH Klipper and Katapult serial patterns per device in the registry. Add a `katapult_serial_pattern` field alongside `serial_pattern`
- After a failed flash, explicitly check for the Katapult-mode device and inform the user: "Device is in bootloader mode at [katapult path]. Retrying flash..."
- Implement automatic retry: if flash fails, re-scan for Katapult device and retry once
- Document the manual recovery path in error messages: "If device is stuck, hold BOOTSEL/press reset and replug USB"

**Phase to address:** Phase 2 (error recovery). Phase 1 should at minimum log the correct Katapult device path in error output.

---

### CP-5: Corrupted .config Cached and Reused Silently

**Description:** If the .config file becomes corrupted (partial write, disk full on Pi's SD card, interrupted copy), the SHA256 hash will change, triggering a rebuild with a broken config. `make` may succeed but produce a non-functional firmware binary (wrong peripherals enabled, wrong clock, wrong bootloader offset). Flashing this firmware bricks the board until recovered via DFU.

**Warning signs:**
- SD card on Raspberry Pi is notoriously unreliable (wear, corruption)
- .config is a text file with no internal checksum or magic bytes
- `make` does not validate all .config options against hardware

**Prevention:**
- After writing .config to cache, immediately read it back and verify the hash matches what was computed
- Before copying cached .config to klipper_dir, validate it is a syntactically valid Kconfig file (check for `CONFIG_` prefixed lines, non-empty, reasonable size)
- Use atomic write pattern: write to `.config.tmp`, verify, then `os.rename()` to `.config` (rename is atomic on Linux ext4/btrfs)
- Add a `--verify-config` flag that displays key .config values (MCU, bootloader offset, clock) for manual inspection

**Phase to address:** Phase 1 (config manager). Atomic writes and basic validation should be in from the start.

---

### CP-6: Serial Device Path Disappears Between Discovery and Flash

**Description:** The user discovers devices, selects one, goes through menuconfig and build (which can take 2-5 minutes), then the tool attempts to flash. But during build time, the USB device may have been disconnected (loose cable), the kernel may have reassigned it, or another process may have claimed it. The flash command gets a stale path.

**Warning signs:**
- Long gap between device discovery and device use
- No re-validation of device path before flash
- Nitehawk36 is on a toolhead cable that can be bumped

**Prevention:**
- Re-verify the serial device path exists immediately before the flash step (not just at discovery time)
- If the path is gone, re-scan and attempt to find the device by pattern
- If device cannot be found, abort with clear message BEFORE stopping klipper (do not stop klipper if you cannot find the flash target)
- Display the path being used: "Flashing to /dev/serial/by-id/usb-Klipper_stm32h723xx_..."

**Phase to address:** Phase 1 (flash flow). The re-verification check is a simple `os.path.exists()` call and must be in the initial implementation.

---

## Subprocess Pitfalls

### SP-1: menuconfig Requires Inherited stdio

**Description:** `make menuconfig` is an ncurses TUI application. If launched with `subprocess.run(capture_output=True)` or `subprocess.PIPE`, it will crash immediately because ncurses cannot initialize without a real terminal. This is the most common mistake when automating Klipper builds.

**Warning signs:**
- Using `subprocess.check_output()` or `capture_output=True` for menuconfig
- Using `subprocess.PIPE` for stdin, stdout, or stderr
- Testing on a system with a terminal and not testing over SSH (both need real TTY)

**Prevention:**
- Use `subprocess.run(["make", "menuconfig"], cwd=klipper_dir)` with NO stdin/stdout/stderr redirection
- This means menuconfig output cannot be captured -- that is correct and expected
- Verify the tool works when invoked over SSH (SSH provides a PTY by default, but `ssh -T` does not)
- Consider detecting if stdin is a TTY (`sys.stdin.isatty()`) and refusing to run menuconfig if not

**Phase to address:** Phase 1 (builder). This must be correct from day one. Get it wrong and nothing works.

---

### SP-2: make Commands Must Run with Correct cwd

**Description:** All `make` commands (clean, menuconfig, build, flash) must execute with `cwd` set to the Klipper source directory. If cwd is wrong, `make` either fails (no Makefile) or worse, finds a different Makefile in the current directory and does something unexpected.

**Warning signs:**
- Using `subprocess.run("make clean && make", shell=True)` without cwd
- Forgetting that `os.chdir()` affects the entire process (and subsequent operations)
- Different devices may use different klipper_dir paths

**Prevention:**
- ALWAYS pass `cwd=klipper_dir` to every `subprocess.run()` call involving make
- Never use `os.chdir()` -- it is global state and affects all subsequent operations
- Validate that `klipper_dir/Makefile` exists before running any make command
- Each device in the registry has its own `klipper_dir` -- always use the device-specific path

**Phase to address:** Phase 1 (builder). Fundamental to correctness.

---

### SP-3: Shell Injection via Device Names or Paths

**Description:** If device names, serial paths, or directory paths from devices.json are interpolated into shell commands via `shell=True`, a malicious or malformed entry could execute arbitrary commands. Example: a serial path like `/dev/serial/by-id/foo; rm -rf /` would be catastrophic.

**Warning signs:**
- Using `subprocess.run(f"make flash FLASH_DEVICE={path}", shell=True)`
- String concatenation or f-strings to build shell commands
- Not validating device registry inputs

**Prevention:**
- NEVER use `shell=True` for subprocess calls. Use list-form arguments: `subprocess.run(["make", "flash", f"FLASH_DEVICE={path}"], cwd=klipper_dir)`
- Even with list-form, validate that paths contain only expected characters (alphanumeric, hyphens, underscores, slashes, dots)
- Validate registry entries on load: serial_pattern must match expected format, paths must be absolute and not contain shell metacharacters

**Phase to address:** Phase 1 (all subprocess calls). Use list-form arguments from day one. No exceptions.

---

### SP-4: subprocess.run() Without Timeout

**Description:** `make` builds, flash operations, and service management commands can hang indefinitely. A build waiting for user input (unexpected prompt), a flash waiting for a device that disappeared, or systemctl waiting for a service that won't stop -- all will hang the tool forever with no way to recover except killing the SSH session.

**Warning signs:**
- `subprocess.run()` calls with no `timeout` parameter
- Flash operations that depend on USB device responsiveness
- `systemctl stop klipper` when klipper is in a crash loop

**Prevention:**
- Set reasonable timeouts for every subprocess call:
  - `make clean`: 30 seconds
  - `make -j$(nproc)`: 300 seconds (5 minutes, builds are slow on Pi)
  - `make flash`: 120 seconds
  - `flashtool.py`: 120 seconds
  - `systemctl stop/start`: 30 seconds
  - `menuconfig`: NO timeout (interactive, user controls duration)
- Catch `subprocess.TimeoutExpired` and handle gracefully (ensure klipper restart in finally block)
- Log the timeout duration in error messages so users know what happened

**Phase to address:** Phase 1 (all subprocess calls). Every subprocess.run() call must have a timeout except menuconfig.

---

### SP-5: Capturing Build Output Masks Errors

**Description:** If build output is captured (PIPE) but not displayed in real-time, the user sees nothing during a 2-3 minute build. If the build fails, they only see a generic "build failed" message without the actual compiler error. Conversely, if output is not captured at all, the tool cannot detect success/failure programmatically.

**Warning signs:**
- Using `capture_output=True` and only checking returncode
- Not displaying build output in real-time
- Swallowing stderr

**Prevention:**
- For `make clean` and `make -j$(nproc)`: let stdout/stderr flow to the terminal (no capture). Check returncode for success/failure
- Alternatively, use `subprocess.Popen` with real-time line reading if you need to add prefixes or filter output, but this adds complexity
- For the flash step, similarly let output flow -- the user needs to see flash progress
- The simplest correct approach: `subprocess.run(cmd, cwd=klipper_dir, timeout=300)` and check `.returncode`

**Phase to address:** Phase 1 (builder). Start with the simple inherited-stdio approach. Add output capture/formatting only if needed later.

---

### SP-6: Parallel Make Job Count Wrong on Pi

**Description:** Using `make -j$(nproc)` or hardcoding `-j4` can overwhelm a Raspberry Pi with limited RAM (1-2GB on Pi 3/4). The GCC linker step for Klipper firmware is memory-intensive. On a Pi 3 with 1GB RAM, `-j4` can cause OOM kills, resulting in a failed build and possibly corrupted intermediate files.

**Warning signs:**
- Pi becomes unresponsive during build
- Build fails with signal 9 (SIGKILL from OOM killer)
- Build produces corrupted .bin files

**Prevention:**
- Detect available memory and CPU cores at runtime using `os.cpu_count()` and `/proc/meminfo`
- For Raspberry Pi: use `min(os.cpu_count(), 2)` as default to avoid OOM on 1GB Pis
- Allow user override via environment variable or flag: `FLASH_JOBS=4 flash.py`
- If build fails with signal 9, suggest reducing job count in error message

**Phase to address:** Phase 1 (builder). Default to conservative parallelism. Can be tuned later.

---

## Serial Device Pitfalls

### SD-1: /dev/serial/by-id/ Symlinks Are Not Instant After Replug

**Description:** When a USB device is replugged or resets (which happens during flashing), the `/dev/serial/by-id/` symlink is recreated by udev. This takes 1-3 seconds. If the tool immediately checks for the device after a flash (to verify it came back), it will not find it.

**Warning signs:**
- Post-flash verification says "device not found" even though flash succeeded
- Race condition between flash completion and device re-enumeration
- Works sometimes, fails sometimes (timing-dependent)

**Prevention:**
- After flash completes, wait with exponential backoff before checking device presence: try at 1s, 2s, 4s, up to 15s total
- Do not treat "device not found immediately after flash" as an error -- treat it as "waiting for device to re-enumerate"
- Log the wait: "Waiting for device to re-enumerate..."
- If device does not appear after timeout, THEN report as potential failure

**Phase to address:** Phase 2 (post-flash verification). Phase 1 can simply flash and restart klipper without verification.

---

### SD-2: Multiple Devices Match Same Serial Pattern

**Description:** If two boards of the same MCU family are connected (e.g., two RP2040 boards), the glob pattern `usb-Klipper_rp2040*` may match both. The tool selects one (likely the first alphabetically) which may be the wrong board.

**Warning signs:**
- Pattern uses only MCU family prefix, not full serial number
- Adding a new board of the same type breaks existing device matching
- User reports "wrong board flashed"

**Prevention:**
- Serial patterns in the registry should be specific enough to uniquely identify ONE device. Include enough of the serial number: `usb-Klipper_rp2040_30333938340A53E6*`
- During add-device wizard, auto-generate the pattern from the FULL device path, not just the MCU prefix
- At discovery time, if a pattern matches multiple devices, warn the user and ask which one to use
- Validate uniqueness: when adding a device, check that its pattern does not overlap with any existing device

**Phase to address:** Phase 1 (discovery + add-device wizard). Generate specific patterns from the start.

---

### SD-3: Device Path Changes After Firmware Flash

**Description:** The `/dev/serial/by-id/` path contains the device descriptor string, which is embedded in the firmware. When you flash new firmware, the descriptor string may change (e.g., Klipper version string changes, or switching from Katapult to Klipper changes the prefix entirely: `usb-katapult_stm32*` becomes `usb-Klipper_stm32*`).

**Warning signs:**
- Device "disappears" after successful flash
- Pattern matching fails on next run
- Klipper serial path in printer.cfg no longer matches the flashed device

**Prevention:**
- Understand and document that the serial path prefix depends on the running firmware:
  - Running Klipper firmware: `usb-Klipper_<mcu>_<serial>`
  - Running Katapult bootloader: `usb-katapult_<mcu>_<serial>` (note lowercase 'k')
- Store both patterns per device
- After flash, the device will appear with the Klipper prefix (if flash succeeded)
- The hardware serial number portion (e.g., `30333938340A53E6`) is stable across firmware changes -- match on that if needed

**Phase to address:** Phase 1 (registry design). Include both Klipper and Katapult patterns from initial registry schema.

---

### SD-4: /dev/serial/by-id/ Does Not Exist on Some Systems

**Description:** The `/dev/serial/by-id/` directory is created by udev rules. On minimal Linux installations, Docker containers, or systems with custom udev rules, this directory may not exist. If no serial devices are connected, the directory also does not exist (it is created dynamically).

**Warning signs:**
- `FileNotFoundError` when scanning the directory
- Tool crashes on startup on a fresh OS install with no boards connected
- Directory exists sometimes but not others

**Prevention:**
- Check if `/dev/serial/by-id/` exists before listing it. If it does not exist, return an empty device list (not an error)
- Display helpful message: "No serial devices found. Ensure USB boards are connected and powered."
- Do NOT create the directory -- it is managed by udev
- Use `pathlib.Path("/dev/serial/by-id").iterdir()` wrapped in try/except for FileNotFoundError

**Phase to address:** Phase 1 (discovery). Handle gracefully from the start.

---

### SD-5: Symlinks in /dev/serial/by-id/ Are Relative

**Description:** The symlinks in `/dev/serial/by-id/` point to relative paths like `../../ttyACM0`. If you resolve them or pass them to commands, you must either use the symlink path directly (which works fine for flash commands) or resolve them correctly using `os.path.realpath()`. Do NOT try to manually construct `/dev/ttyACM0` by string manipulation.

**Warning signs:**
- Manual path construction from symlink targets
- Using `os.readlink()` and prepending `/dev/` to get device path
- Breaking when symlink target depth changes

**Prevention:**
- Use the `/dev/serial/by-id/<name>` path directly in all commands. Klipper, Katapult, and make flash all accept symlink paths
- If you need the real device path (e.g., for display), use `pathlib.Path(symlink).resolve()` or `os.path.realpath()`
- Never parse or manipulate symlink target strings

**Phase to address:** Phase 1 (discovery). Use symlink paths directly. Simple and correct.

---

## Service Management Pitfalls

### SM-1: sudo systemctl Requires Passwordless sudo

**Description:** The tool needs to run `sudo systemctl stop klipper` and `sudo systemctl start klipper`. If the user does not have passwordless sudo configured, the command will hang waiting for a password (which the tool cannot provide if it has captured stdin/stdout).

**Warning signs:**
- Tool hangs at "Stopping klipper service..."
- Works when run as root but not as regular user
- Works in interactive terminal but not in automated scripts

**Prevention:**
- On first run or during setup, verify passwordless sudo works: run `sudo -n systemctl is-active klipper` (the `-n` flag prevents interactive password prompt and fails immediately if password is needed)
- If passwordless sudo is not available, display setup instructions: "Add `<user> ALL=(ALL) NOPASSWD: /usr/bin/systemctl` to /etc/sudoers.d/klipper-flash"
- Always use `sudo -n` to prevent hanging. If it fails, report the reason clearly
- Alternatively, check if klipper is managed by a user-level systemd unit (some setups use `systemctl --user`)

**Phase to address:** Phase 1 (service management). Must verify sudo access before attempting service operations.

---

### SM-2: Klipper Service Name May Not Be "klipper"

**Description:** Different Klipper installations use different service names. MainsailOS uses `klipper.service`. KIAUH installations may use `klipper-1.service` for multi-instance setups. Some users run klipper under a different service manager entirely.

**Warning signs:**
- `systemctl stop klipper` returns "Unit klipper.service not found"
- Multiple klipper instances running (klipper-1, klipper-2)
- Klipper is running but service stop does not affect it

**Prevention:**
- Make the service name configurable in a global config or CLI argument. Default to `klipper`
- On first run, detect the service name: check for `klipper.service`, `klipper-1.service`, etc.
- Verify the service is actually stopped after the stop command (check with `systemctl is-active`)
- Store the detected service name for subsequent runs

**Phase to address:** Phase 1 (service management). Default to "klipper" but make it configurable.

---

### SM-3: Klipper Service Fails to Start After Flash

**Description:** After flashing new firmware, klipper may fail to start if the new firmware is incompatible with the existing printer.cfg (e.g., pin names changed, features removed, protocol version mismatch). The tool reports "klipper started" but klipper immediately crashes and enters a restart loop.

**Warning signs:**
- `systemctl start klipper` succeeds (returns 0) but klipper is not actually running
- Klipper enters rapid restart cycle (starts, crashes, restarts)
- Moonraker reports "MCU protocol error" or "Unable to connect to MCU"

**Prevention:**
- After starting klipper, wait 5 seconds and check `systemctl is-active klipper`
- If active, report success with caveat: "Klipper started. Check Fluidd/Mainsail for MCU connection status."
- If failed, report the status and suggest: "Klipper failed to start. Check logs with: journalctl -u klipper -n 50"
- Do NOT try to automatically fix klipper startup failures -- that is beyond the tool's scope

**Phase to address:** Phase 2 (post-flash verification). Phase 1 just starts the service and reports.

---

### SM-4: Stopping Klipper Does Not Release Serial Port Immediately

**Description:** When klipper is stopped via systemctl, it sends SIGTERM to the klipper process. The process closes serial ports during shutdown. But the kernel may take 1-2 seconds to fully release the serial port. If flash begins immediately after stop, it may fail with "device busy" or "permission denied".

**Warning signs:**
- Flash fails with "Permission denied" or "Device or resource busy" intermittently
- Adding a sleep fixes it (classic race condition)
- Works on fast machines, fails on slow Pis

**Prevention:**
- After stopping klipper, verify the service is fully stopped: `systemctl is-active klipper` should return `inactive`
- Add a brief delay (2 seconds) between stop and flash to allow kernel to release serial port
- If flash fails with EBUSY, retry once after 3 more seconds
- Check if any other process holds the serial port: `fuser /dev/serial/by-id/<path>` before flashing

**Phase to address:** Phase 1 (flash flow). Add a 2-second delay after klipper stop. Simple and effective.

---

### SM-5: Other Services Also Hold Serial Ports

**Description:** Klipper is not the only service that may hold serial ports open. Moonraker communicates with Klipper (not directly to serial), but other software like `sonar`, a secondary klipper instance, or even a running `minicom`/`screen` session can hold the port.

**Warning signs:**
- Flash fails with "device busy" even after stopping klipper
- Other processes show up in `fuser` output for the serial device
- Works after full system reboot but not after just stopping klipper

**Prevention:**
- Before flashing, check if any process holds the target serial device: run `fuser /dev/serial/by-id/<path>` and report which PIDs are using it
- If processes are found, display them and suggest stopping them
- Do NOT automatically kill unknown processes -- that is dangerous
- Document known services that may need stopping (klipper, secondary instances)

**Phase to address:** Phase 2 (pre-flash checks). Phase 1 assumes stopping klipper is sufficient (true for most setups).

---

## SSH/Terminal Pitfalls

### SSH-1: SSH Disconnect During Flash Leaves Tool Running (or Not)

**Description:** If the SSH connection drops during a flash operation, the behavior depends on how the tool was launched. Without `nohup`, `screen`, or `tmux`, the tool receives SIGHUP and terminates. If it terminates between klipper stop and klipper start, the printer is left without klipper running (see CP-1). If it terminates during the flash write, the board may be left in an inconsistent state.

**Warning signs:**
- Flaky WiFi on the Pi (common with Raspberry Pi built-in WiFi)
- Long flash operations (Katapult can take 30+ seconds)
- User closes laptop lid during flash

**Prevention:**
- Install a SIGHUP handler that triggers the same cleanup as the finally block (restart klipper)
- Recommend running via `screen` or `tmux` in the tool's help text
- Consider auto-detecting if running in a screen/tmux session and warning if not: "Warning: Not running in screen/tmux. SSH disconnect during flash may leave klipper stopped."
- Keep the "klipper is stopped" state recorded in a lockfile so next invocation can recover

**Phase to address:** Phase 2 (robustness). Phase 1 should have the SIGHUP handler. Screen/tmux detection is Phase 2.

---

### SSH-2: Terminal Width/Height Affects menuconfig

**Description:** `make menuconfig` (ncurses TUI) requires a minimum terminal size (typically 80x24). If the SSH terminal is too small, menuconfig either crashes or renders incorrectly. Some SSH clients send wrong TERM environment variables.

**Warning signs:**
- menuconfig crashes with "Error opening terminal" or "screen too small"
- UI renders garbled text
- Works from one SSH client but not another

**Prevention:**
- Before launching menuconfig, check terminal dimensions: `os.get_terminal_size()` or `shutil.get_terminal_size()`
- If terminal is smaller than 80x24, warn: "Terminal too small for menuconfig (need 80x24, have XxY). Resize your terminal window."
- Ensure `TERM` environment variable is set (inherit from parent process, which is the default)
- If `TERM` is not set, set it to `xterm-256color` as a safe default before launching menuconfig

**Phase to address:** Phase 1 (builder). Simple check before menuconfig launch.

---

### SSH-3: Locale and Encoding Issues on Pi

**Description:** Raspberry Pi OS may have incomplete locale configuration. If `LANG` or `LC_ALL` is not set to a UTF-8 locale, Python's `subprocess` may fail to decode process output that contains non-ASCII characters (compiler warnings with file paths, device names with special characters).

**Warning signs:**
- `UnicodeDecodeError` when reading subprocess output
- Works in some environments but not others
- Locale warnings in build output

**Prevention:**
- When capturing subprocess output, use `encoding='utf-8', errors='replace'` to prevent crashes on encoding issues
- For inherited stdio (menuconfig, build), this is not an issue since output goes directly to terminal
- Do not assume ASCII-safe output from any subprocess

**Phase to address:** Phase 1 (all subprocess calls). Use `errors='replace'` wherever output is decoded.

---

## Config Management Pitfalls

### CM-1: .config File Is Klipper Source-Tree State, Not Standalone

**Description:** The `.config` file generated by `make menuconfig` is relative to the Klipper source tree version. The same `.config` may produce different firmware (or fail to build) if the Klipper source is updated (`git pull`). A cached .config from Klipper v0.12 may not be valid for Klipper v0.13.

**Warning signs:**
- Build fails after `git pull` in klipper directory with "unknown config option"
- Firmware builds but has wrong features enabled/disabled
- User updates Klipper, flash succeeds, printer firmware is subtly wrong

**Prevention:**
- Record the Klipper git commit hash alongside each cached .config (store in the .sha256 sidecar or a separate metadata file)
- On flash, check if current Klipper HEAD matches the stored commit. If different, warn: "Klipper source has been updated since this config was last saved. Consider running menuconfig to verify config."
- Do NOT automatically invalidate cached configs on Klipper update -- the user should decide
- Display the Klipper version in the flash summary

**Phase to address:** Phase 2 (config management enhancement). Phase 1 can just cache .config without version tracking.

---

### CM-2: SHA256 Hash Comparison Is Byte-Exact

**Description:** SHA256 hashing is byte-exact. If `make menuconfig` rewrites the .config file with different line endings, different whitespace, or reordered sections (which it sometimes does even without user changes), the hash changes and the tool reports "config changed" when nothing meaningful changed. This triggers unnecessary rebuilds.

**Warning signs:**
- Tool reports config changed after opening and immediately closing menuconfig
- Rebuilds happening even when user made no changes
- Different hash on identical logical configuration

**Prevention:**
- This is actually acceptable behavior for Phase 1. A false-positive "config changed" just triggers an unnecessary rebuild, which is safe
- If it becomes annoying, normalize the .config before hashing: sort lines, strip trailing whitespace, normalize line endings
- Do NOT try to parse .config semantically -- that is fragile and unnecessary
- Document that "config changed" after menuconfig with no edits is normal and harmless

**Phase to address:** Phase 2 (quality of life). Phase 1 accepts false-positive rebuilds as safe.

---

### CM-3: configs/ Directory on SD Card Is a Corruption Risk

**Description:** Raspberry Pi typically runs from an SD card, which has limited write endurance and is prone to corruption on power loss. The `configs/` directory with .config files and .sha256 sidecars is being written to on every flash. If the SD card corrupts, cached configs are lost.

**Warning signs:**
- SD card read-only filesystem errors
- Corrupted JSON (devices.json)
- Missing .config files after power cycle

**Prevention:**
- Use atomic writes for all file operations (write to .tmp, rename to final name)
- Catch IOError/OSError on all file writes and display meaningful messages
- Consider storing configs in the git repository (this project is already a git repo) for additional durability
- On load, validate that JSON parses correctly and .config files are non-empty
- Do NOT write files unnecessarily -- only update .sha256 when hash actually changes

**Phase to address:** Phase 1 (config manager). Atomic writes and validation from the start.

---

### CM-4: devices.json Concurrent Access

**Description:** If two instances of the tool run simultaneously (user opens two SSH sessions), both may read devices.json, make changes, and write back, with one overwriting the other's changes. More realistically, if the tool crashes mid-write of devices.json, the file may be truncated or empty.

**Warning signs:**
- devices.json becomes empty or contains partial JSON
- Device entries disappear
- Simultaneous SSH sessions

**Prevention:**
- Use atomic write for devices.json: write to devices.json.tmp, then rename
- Use a lockfile (`devices.json.lock`) to prevent concurrent access. Use `fcntl.flock()` on Linux
- On load, validate JSON structure and handle empty/corrupt files gracefully (restore from .bak if available)
- Before writing, read current state and merge (or simply refuse to run if lock is held)
- Keep a `.bak` copy of devices.json before each write

**Phase to address:** Phase 2 (robustness). Phase 1 uses atomic writes only. Lockfile is Phase 2.

---

### CM-5: make menuconfig Overwrites .config In-Place

**Description:** When `make menuconfig` runs, it reads `.config` from the Klipper source directory, presents the TUI, and on save writes `.config` back to the same location. If the tool copies the cached .config to klipper_dir/.config before menuconfig and the user hits Escape (exit without save), the .config in klipper_dir remains as the cached version (unchanged). But if Klipper's `make menuconfig` has "auto-save on exit" behavior, it may modify .config even when the user did not intentionally change anything.

**Warning signs:**
- Config hash changes after menuconfig with no user edits
- Loss of cached config if user accidentally overwrites
- Confusion about which .config is authoritative (cache vs. klipper_dir)

**Prevention:**
- The authoritative .config is ALWAYS the one in klipper_dir AFTER menuconfig runs
- After menuconfig exits, always copy klipper_dir/.config back to cache (regardless of whether user made changes)
- The hash comparison then determines whether a rebuild is needed
- Document the flow clearly: cache -> klipper_dir -> menuconfig -> klipper_dir -> cache -> hash compare

**Phase to address:** Phase 1 (config flow). Get the copy direction right from the start.

---

## Phase-Specific Warning Summary (v1.0)

| Phase | Pitfall IDs | Theme |
|-------|-------------|-------|
| Phase 1 (Core Flow) | CP-1, CP-2, CP-5, CP-6, SP-1, SP-2, SP-3, SP-4, SP-5, SP-6, SD-2, SD-4, SD-5, SM-1, SM-2, SM-4, SSH-2, SSH-3, CM-3, CM-5 | Safety invariants, correct subprocess usage, basic robustness |
| Phase 2 (Error Recovery) | CP-3, CP-4, SD-1, SD-3, SM-3, SM-5, SSH-1, CM-1, CM-2, CM-4 | Post-flash verification, recovery from failures, concurrent access |
| Phase 3 (Polish) | -- | Cosmetic issues, UX improvements that do not affect safety |

---

# v2.0 Feature Pitfalls

The following pitfalls are specific to adding v2.0 features to the existing kalico-flash codebase. These supplement the foundational pitfalls above.

---

## TUI Menu Pitfalls

### TUI-1: Box Drawing Characters Fail Over SSH

**Risk:** Unicode box-drawing characters (U+2500-U+257F) render as garbage or cause `UnicodeEncodeError` when user connects via SSH with incorrect terminal encoding.

**Warning signs:**
- Works locally but fails over SSH
- `UnicodeEncodeError: 'ascii' codec can't encode character` in logs
- Box characters appear as `?` or `\ufffd`

**Prevention:**
1. Detect encoding with `sys.stdout.encoding` before drawing
2. Provide ASCII fallback for non-UTF-8 terminals:
   ```python
   BOX_H = "\u2500" if sys.stdout.encoding == "utf-8" else "-"
   BOX_V = "\u2502" if sys.stdout.encoding == "utf-8" else "|"
   ```
3. Set `PYTHONIOENCODING=utf-8` recommendation in docs
4. For Python 3.7+: `sys.stdout.reconfigure(encoding="utf-8")` with try/except

**Phase:** TUI Menu implementation

---

### TUI-2: Terminal Width Truncation

**Risk:** Menu items or status lines exceed terminal width, causing ugly wrapping or truncated text that hides important information.

**Warning signs:**
- Long device names or paths wrap mid-word
- Status messages get cut off on narrow terminals
- Layout breaks on 80-column SSH sessions

**Prevention:**
1. Query terminal width: `shutil.get_terminal_size().columns`
2. Truncate paths with ellipsis: `/dev/serial/by-id/usb-Klipper_stm32...`
3. Set minimum width (e.g., 60 columns) and warn if smaller
4. Test on 80x24 terminals (standard SSH default)

**Phase:** TUI Menu implementation

---

### TUI-3: Input Blocking in Non-TTY Context

**Risk:** TUI menu code calls `input()` when stdin is not a TTY (piped input, cron job), causing hang or crash.

**Warning signs:**
- Script hangs when run from automation
- `EOFError` when stdin is closed
- Works interactively, fails in scripts

**Prevention:**
1. Check `sys.stdin.isatty()` before entering TUI mode (already done in v1.0 - preserve this)
2. Provide `--non-interactive` flag or environment variable
3. Exit gracefully with error message if TUI required but no TTY
4. Ensure all `input()` calls are wrapped in TTY checks

**Phase:** TUI Menu implementation

---

### TUI-4: Screen State Corruption After Subprocess

**Risk:** Running `make menuconfig` (ncurses TUI) corrupts terminal state. After returning, the TUI menu displays incorrectly or input breaks.

**Warning signs:**
- Garbled display after menuconfig exits
- Arrow keys produce escape sequences instead of navigation
- Terminal requires `reset` command to fix

**Prevention:**
1. Do NOT mix print-based TUI with ncurses subprocesses in same view
2. Clear screen after menuconfig returns: `print("\033c", end="")`
3. Consider using `subprocess.run()` with inherited stdio (current approach) rather than custom TUI around it
4. Let menuconfig own the full terminal, return to CLI output after

**Phase:** TUI Menu implementation (design decision)

---

### TUI-5: Rapid Refresh Flicker

**Risk:** Refreshing the entire menu on every keypress causes visible flicker, especially over SSH with latency.

**Warning signs:**
- Screen flashes on each input
- Noticeable delay between redraw and input
- Users report "jumpy" interface

**Prevention:**
1. Only redraw changed lines, not entire screen
2. Use cursor positioning (`\033[{row};{col}H`) for partial updates
3. Batch output before flush
4. For simple menus: just print numbered list once, read single input (current approach works well)

**Phase:** TUI Menu implementation (if using dynamic refresh)

---

## Moonraker API Pitfalls

### MOON-1: Connection Refused Not Handled

**Risk:** HTTP request to `localhost:7125` fails with `ConnectionRefusedError` when Moonraker is not running, crashing the script.

**Warning signs:**
- `urllib.error.URLError: [Errno 111] Connection refused`
- Script crashes instead of showing friendly error
- No fallback behavior when Moonraker unavailable

**Prevention:**
1. Wrap all HTTP calls in try/except for `URLError`, `socket.timeout`
2. Provide clear message: "Moonraker not responding. Is it running?"
3. Make Moonraker check optional (graceful degradation - allow flash with warning)
4. Use stdlib `urllib.request` with timeout (since no external deps allowed)

Example:
```python
import urllib.request
import urllib.error
import socket

def check_moonraker_print_status(url="http://localhost:7125", timeout=5):
    try:
        req = urllib.request.Request(f"{url}/printer/objects/query?print_stats")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            return data["result"]["status"]["print_stats"]["state"]
    except (urllib.error.URLError, socket.timeout):
        return None  # Moonraker not available
```

**Phase:** Moonraker integration

---

### MOON-2: Klippy Not Ready State

**Risk:** Moonraker is running but Klipper hasn't connected yet. API calls return errors or stale data.

**Warning signs:**
- `/server/info` returns `klippy_state: "startup"` or `"error"`
- `print_stats` query fails or returns unexpected values
- Race condition at boot time

**Prevention:**
1. Always check `/server/info` first and verify `klippy_state == "ready"`
2. If state is `"startup"`, retry after 2 seconds (up to 3 times)
3. If state is `"error"` or `"shutdown"`, inform user Klipper has a problem
4. Don't assume print_stats is available until Klippy is ready

**Phase:** Moonraker integration

---

### MOON-3: print_stats State Misinterpretation

**Risk:** Using wrong field to detect "printing" state. The `idle_timeout` state shows "Printing" even for manual G-code commands.

**Warning signs:**
- Flash blocked during manual homing or heating
- User reports "it says I'm printing but I'm not"
- Confusion between `idle_timeout` and `print_stats`

**Prevention:**
1. Use `print_stats.state` field, NOT `idle_timeout.state`
2. Valid states: `standby`, `printing`, `paused`, `complete`, `error`, `cancelled`
3. Only block flash when `print_stats.state == "printing"` or `"paused"`
4. Provide `--force` flag to override print check

**Phase:** Moonraker integration

---

### MOON-4: Timeout on Slow Raspberry Pi

**Risk:** HTTP timeout too short for slow Pi or high-load situations (during print). Request fails despite Moonraker being responsive.

**Warning signs:**
- "Request timed out" during heavy print operations
- Works when idle, fails when printing
- Pi SD card I/O causing delays

**Prevention:**
1. Use reasonable timeout (5-10 seconds for status check)
2. Retry once on timeout before giving up
3. Log actual response times for debugging
4. Consider async check that doesn't block main flow

**Phase:** Moonraker integration

---

### MOON-5: API URL Hardcoded Incorrectly

**Risk:** Assuming Moonraker is always at `http://localhost:7125`. Some setups use different ports or reverse proxies.

**Warning signs:**
- Works on standard setups, fails on custom installations
- User has Moonraker on different port
- Docker or VM setups with port mapping

**Prevention:**
1. Default to `localhost:7125` but allow configuration in `devices.json`
2. Add `moonraker_url` to GlobalConfig with sensible default
3. Support both `http://` and bare `host:port` formats
4. Document how to override for non-standard setups

**Phase:** Moonraker integration

---

## Post-Flash Verification Pitfalls

### VERIFY-1: Premature Check Before Device Re-enumerates

**Risk:** Checking for device too soon after flash. USB device needs time to reboot and re-enumerate. False "device not found" error.

**Warning signs:**
- Verification fails but device is actually fine
- "Flash failed" immediately followed by device appearing
- Works with delays, fails without

**Prevention:**
1. Wait minimum 2-3 seconds after flash before first check
2. Poll with exponential backoff: 1s, 2s, 4s (up to 15s total)
3. Log each poll attempt for debugging
4. Consider "device disappeared" as intermediate success state

**Phase:** Post-flash verification

---

### VERIFY-2: Serial Path Changes After Flash

**Risk:** Device serial path may change slightly after flash (e.g., interface number). Pattern match fails on reappearance.

**Warning signs:**
- Device at `/dev/serial/by-id/usb-Klipper_stm32h723xx_XXX-if00` before
- Returns as `/dev/serial/by-id/usb-Klipper_stm32h723xx_XXX-if01` after
- Glob pattern doesn't match new path

**Prevention:**
1. Use pattern without interface suffix: `usb-Klipper_stm32h723xx_XXX*`
2. Current `generate_serial_pattern()` already strips `-ifNN` (good - preserve this)
3. Match on MCU identifier portion, not full path
4. Re-scan `/dev/serial/by-id/` and match against pattern

**Phase:** Post-flash verification

---

### VERIFY-3: Klipper vs Katapult Prefix Confusion

**Risk:** Device returns with different USB descriptor after flash. Was `usb-katapult_*`, now `usb-Klipper_*`. Verification fails to recognize.

**Warning signs:**
- "Device not found" after successful Katapult flash
- Device present but with different name prefix
- Pattern hardcoded to one descriptor type

**Prevention:**
1. Accept both `Klipper_` and `katapult_` prefixes in verification
2. Match on MCU type and serial number, not brand prefix
3. Define success as: device with matching MCU serial reappears
4. Consider adding helper: `normalize_serial_pattern()` that matches both prefixes

**Phase:** Post-flash verification

---

### VERIFY-4: Blocking Wait Freezes UI

**Risk:** Synchronous polling loop freezes the entire CLI while waiting for device. User can't cancel, no progress indication.

**Warning signs:**
- CLI appears frozen after flash
- Ctrl+C doesn't respond immediately
- No feedback during 15-second wait

**Prevention:**
1. Print status during wait: "Waiting for device... (5s)"
2. Check for KeyboardInterrupt in poll loop
3. Use short poll intervals (0.5s) with timeout counter
4. Show spinner or dots to indicate activity

**Phase:** Post-flash verification

---

### VERIFY-5: Race Condition with Klipper Restart

**Risk:** Klipper service restarts and grabs device before verification can check. Device appears briefly then "disappears" when Klipper locks it.

**Warning signs:**
- Device shows up then vanishes from `/dev/serial/by-id/`
- Race between our poll and Klipper starting
- Verification succeeds but then shows device missing

**Prevention:**
1. Perform verification AFTER Klipper restart, not before
2. Or: verify device exists, THEN restart Klipper
3. Check that device is present AND Klipper claims it (via Moonraker API if available)
4. Consider verification as "device reappeared" regardless of Klipper lock

**Phase:** Post-flash verification (coordinate with service.py context manager)

---

## Version Detection Pitfalls

### VER-1: git describe Fails on Shallow Clone

**Risk:** `git describe` fails or returns wrong value on shallow clones (common in Docker, CI). No tags available to describe.

**Warning signs:**
- `fatal: No names found, cannot describe anything`
- Version shows as `unknown` or git commit hash only
- Works locally, fails on some Pi installations

**Prevention:**
1. Catch `subprocess.CalledProcessError` and return sensible default
2. Fall back to reading `VERSION` file if git fails
3. For Klipper: check `~/klipper/klippy/.version` or git log
4. Never crash on version detection failure - return "unknown"

**Phase:** Version detection

---

### VER-2: Tag Format Variation

**Risk:** Different tag formats break parsing. Klipper uses `v0.11.0-xxx`, Kalico might use different format. Regex fails.

**Warning signs:**
- Parse error on version string
- Comparison fails between different formats
- Works with one repo, fails with another

**Prevention:**
1. Use flexible regex: `r'^v?(\d+)\.(\d+)\.(\d+)'`
2. Handle `git describe` output: `v0.11.0-123-gabcdef`
3. Extract base version (0.11.0), commit count (123), hash (abcdef)
4. For comparison: only use major.minor.patch, ignore rest

**Phase:** Version detection

---

### VER-3: Version Comparison Logic Errors

**Risk:** String comparison instead of numeric: "0.9.0" > "0.11.0" is wrong because "9" > "1" lexicographically.

**Warning signs:**
- Old version reported as newer
- Upgrade recommendations wrong
- "You are up to date" when behind

**Prevention:**
1. Parse into tuple of integers: `(0, 11, 0)`
2. Compare tuples: `(0, 11, 0) > (0, 9, 0)` = True
3. Cannot use `packaging.version` due to stdlib-only constraint
4. Implement: `tuple(int(x) for x in version.split('.')[:3])`

**Phase:** Version detection

---

### VER-4: Dirty Working Tree Handling

**Risk:** `git describe --dirty` may include `-dirty` suffix. Comparison or display breaks on non-clean repos.

**Warning signs:**
- Version shows `v0.11.0-dirty`
- Comparison fails on `-dirty` suffix
- False "update available" due to dirty state

**Prevention:**
1. Strip `-dirty` suffix before parsing
2. Or: use `git describe --always` without `--dirty`
3. Decide: should dirty state be shown to user? (probably yes, informational)
4. Handle in parsing, not comparison

**Phase:** Version detection

---

### VER-5: Missing .git Directory

**Risk:** Klipper installed without git history (downloaded zip, package install). No `.git` directory for version detection.

**Warning signs:**
- `fatal: not a git repository`
- `FileNotFoundError` on `.git/` access
- Script assumes git always present

**Prevention:**
1. Check `Path(klipper_dir / ".git").exists()` first
2. Fall back to version file or return "unknown"
3. Don't block operations on version detection failure
4. Version display is informational, not critical

**Phase:** Version detection

---

## Device Exclusion Pitfalls

### EXCL-1: Excluded Device Still Shows in Selection

**Risk:** Device marked as excluded still appears in interactive menu. User can select it and attempt flash, causing confusion.

**Warning signs:**
- Beacon (excluded) shows as option [2]
- User selects it, gets error "device cannot be flashed"
- Poor UX: why show if unusable?

**Prevention:**
1. Filter excluded devices from menu BEFORE display
2. Show them in `--list-devices` with `[EXCL]` marker for visibility
3. Never include in interactive selection
4. Add `--include-excluded` flag if admin really needs to see them

**Phase:** Device exclusion

---

### EXCL-2: Exclusion Flag Schema Migration

**Risk:** Adding `excluded: bool` to DeviceEntry breaks existing `devices.json` files. Missing field causes KeyError.

**Warning signs:**
- `KeyError: 'excluded'` when loading old registry
- Upgrade breaks existing installations
- Users must re-register devices

**Prevention:**
1. Use `data.get("excluded", False)` with default in registry.py
2. Treat missing field as False (not excluded)
3. Write field on any save to migrate forward
4. Document in CHANGELOG that new field added

Current registry.py already uses `.get()` pattern - maintain this.

**Phase:** Device exclusion (registry.py modification)

---

### EXCL-3: Pattern Match Ambiguity with Excluded Devices

**Risk:** Excluded device matches same pattern as flashable device. Both match `usb-*Beacon*` or similar overlapping patterns.

**Warning signs:**
- Wrong device selected for flash
- Excluded device accidentally matched
- User confusion about which device was targeted

**Prevention:**
1. Exclusion check happens AFTER pattern match, BEFORE action
2. If matched device is excluded, skip and continue matching
3. Warn user: "Matched device is excluded from flashing"
4. Consider more specific patterns to avoid overlap

**Phase:** Device exclusion (discovery.py modification)

---

### EXCL-4: Beacon-Specific Detection Not Generalized

**Risk:** Hardcoding Beacon-specific detection. Other devices may need exclusion in future (CAN bridges, USB hubs with serial).

**Warning signs:**
- Code has `if "Beacon" in filename`
- New excluded device type requires code change
- No generic exclusion mechanism

**Prevention:**
1. Make exclusion registry-based, not code-based
2. `excluded: true` field in DeviceEntry, not special-case logic
3. Optionally: `exclusion_reason: "USB probe, no flashable firmware"`
4. Allow user to mark any device as excluded via `--add-device` wizard

**Phase:** Device exclusion (design principle)

---

## Installation Script Pitfalls

### INST-1: Symlink Permission Denied

**Risk:** Creating symlink in `/usr/local/bin` requires root. Script run without sudo fails silently or crashes.

**Warning signs:**
- `PermissionError: [Errno 13] Permission denied`
- Install "succeeds" but command not in PATH
- Works for root, fails for normal user

**Prevention:**
1. Check write permission before attempting symlink
2. Offer alternative: install to `~/.local/bin` (no sudo required)
3. Provide clear message: "Run with sudo to install to /usr/local/bin"
4. Support `--user` flag for user-local installation

**Phase:** Installation script

---

### INST-2: Symlink Already Exists

**Risk:** Running installer twice fails on existing symlink. `os.symlink()` raises `FileExistsError`.

**Warning signs:**
- `FileExistsError: [Errno 17] File exists`
- Upgrade path broken
- User must manually remove old symlink

**Prevention:**
1. Check if symlink exists: `Path(target).is_symlink()`
2. If exists and points to same location: success (idempotent)
3. If exists and points elsewhere: warn and ask to overwrite
4. Use `os.replace()` pattern: create temp symlink, then replace

**Phase:** Installation script

---

### INST-3: Target Path Not in PATH

**Risk:** Install to `/usr/local/bin` but that's not in user's PATH. Command appears installed but can't be found.

**Warning signs:**
- `kalico-flash: command not found` after install
- `/usr/local/bin` not in `$PATH` on some distros
- Works for one user, not another

**Prevention:**
1. Check if install directory is in `$PATH`: `os.environ.get("PATH", "").split(":")`
2. Warn if not: "Note: /usr/local/bin may not be in your PATH"
3. Suggest adding to PATH in shell config
4. Or: use `~/bin` which is commonly auto-added

**Phase:** Installation script

---

### INST-4: Relative vs Absolute Symlink

**Risk:** Creating relative symlink that breaks when CWD changes. Symlink points to `../kalico-flash/flash.py` which only works from specific directory.

**Warning signs:**
- Symlink works in some directories, not others
- `No such file or directory` when running from different location
- Debugging nightmare for users

**Prevention:**
1. Always create symlinks with absolute target paths
2. Resolve source path: `Path(source).resolve()`
3. Verify symlink target exists before creating
4. Test: `ls -la /usr/local/bin/kalico-flash` should show absolute path

**Phase:** Installation script

---

### INST-5: Python Shebang Portability

**Risk:** Shebang `#!/usr/bin/env python3` assumes `python3` is correct interpreter. Some systems have `python3.11` but not `python3`.

**Warning signs:**
- `/usr/bin/env: 'python3': No such file or directory`
- Works on MainsailOS, fails on custom Linux
- Different Python version than expected

**Prevention:**
1. Use `#!/usr/bin/env python3` (most portable)
2. Document minimum Python version requirement (3.9+)
3. Installer can verify Python exists: `which python3`
4. Show clear error if Python version too old

**Phase:** Installation script

---

## Integration Pitfalls (Cross-Cutting)

### INT-1: Breaking Existing CLI Interface

**Risk:** Adding TUI menu breaks `--device KEY` flag behavior. Users who automated the CLI find their scripts broken.

**Warning signs:**
- Scripts that used `flash.py --device octopus` stop working
- New prompts interrupt automation
- Backward compatibility broken

**Prevention:**
1. TUI menu is ONLY for no-args interactive mode
2. `--device KEY` bypasses TUI entirely (current behavior - PRESERVE IT)
3. Test: `echo "" | python flash.py --device key` should not prompt
4. Document: "existing CLI flags unchanged, TUI only in interactive mode"

**Phase:** TUI Menu implementation

---

### INT-2: Output Protocol Violation

**Risk:** New TUI code bypasses `output.py` protocol. Direct `print()` calls break future Moonraker integration.

**Warning signs:**
- Mix of `out.info()` and raw `print()`
- Moonraker output handler doesn't receive TUI messages
- Inconsistent logging

**Prevention:**
1. All user-facing output goes through `Output` protocol
2. Add new methods to protocol if needed: `menu_draw()`, `progress()`
3. TUI class should receive `Output` instance
4. Audit: grep for bare `print(` in new code (except in Output implementations)

**Phase:** TUI Menu implementation (architecture discipline)

---

### INT-3: Feature Flag Explosion

**Risk:** Too many flags: `--skip-menuconfig`, `--force`, `--no-verify`, `--no-moonraker-check`. CLI becomes confusing.

**Warning signs:**
- Help text is overwhelming
- Users don't know which flags to use
- Flags conflict with each other

**Prevention:**
1. Limit to essential flags
2. Use sensible defaults that rarely need override
3. Group related flags: `--quick` = skip-menuconfig + no-verify
4. Consider config file for persistent preferences

**Phase:** All v2.0 features (holistic design)

---

### INT-4: Error Message Regression

**Risk:** New code has generic error messages. Previous helpful messages (with recovery steps) replaced with bare exceptions.

**Warning signs:**
- "Error: subprocess failed" instead of specific guidance
- Stack traces shown to users
- Recovery steps missing

**Prevention:**
1. Maintain pattern: specific error type + actionable recovery
2. Every except block should provide user guidance
3. Test error paths, not just happy paths
4. Review existing error handling quality before adding new code

**Phase:** All v2.0 features

---

### INT-5: Module Coupling Creep

**Risk:** v2.0 features start cross-importing between modules, breaking hub-and-spoke architecture. Circular imports, hidden dependencies.

**Warning signs:**
- `from tui import ...` in flasher.py
- Circular import errors
- Modules become interdependent

**Prevention:**
1. New modules follow same pattern: only import models.py, errors.py
2. flash.py remains the only orchestrator
3. New modules are "leaves" that don't know about each other
4. Code review: check imports at top of each new module

**Phase:** All v2.0 features (architecture discipline)

---

### INT-6: Blocking Moonraker Check During Flash

**Risk:** Moonraker API call to check print status blocks the flash workflow. If Moonraker is slow/hung, flash appears frozen.

**Warning signs:**
- Flash takes 30+ seconds longer than expected
- Hangs before "Stopping Klipper" message
- Moonraker issues block unrelated operation

**Prevention:**
1. Use short timeout for Moonraker check (3-5 seconds)
2. Make check optional/non-blocking
3. Log "Checking print status..." so user knows what's happening
4. Fail open: if check times out, warn but continue (or provide --force)

**Phase:** Moonraker integration

---

### INT-7: Config Hash vs Klipper Source Mismatch

**Risk:** Cached config hash matches, but Klipper source updated. Config valid for old Klipper version may not work with new.

**Warning signs:**
- `--skip-menuconfig` uses stale config
- Build fails with Kconfig errors
- Config options renamed/removed in new Klipper

**Prevention:**
1. Include Klipper git commit hash in config hash calculation
2. Or: detect if Kconfig options changed since last menuconfig
3. Warn: "Klipper updated since last config. Run menuconfig to verify."
4. Consider: config hash is optimization, not guarantee

**Phase:** Skip menuconfig feature

---

## Critical Pitfalls Summary (v2.0)

| ID | Pitfall | Severity | Phase |
|----|---------|----------|-------|
| MOON-1 | Connection refused not handled | HIGH | Moonraker |
| MOON-3 | print_stats state misinterpretation | HIGH | Moonraker |
| VERIFY-1 | Premature check before re-enumerate | HIGH | Verification |
| VER-3 | Version comparison logic errors | HIGH | Version |
| EXCL-2 | Schema migration breaks registry | HIGH | Exclusion |
| INT-1 | Breaking existing CLI interface | HIGH | TUI |
| INT-5 | Module coupling creep | MEDIUM | All |
| TUI-1 | Box drawing fails over SSH | MEDIUM | TUI |
| INST-1 | Symlink permission denied | MEDIUM | Install |
| VER-1 | git describe fails on shallow clone | MEDIUM | Version |

---

# v2.1 Panel TUI + Batch Flash Pitfalls

The following pitfalls are specific to adding a panel-based TUI with truecolor theming and a "Flash All" batch command. These apply to the existing codebase which already has box-drawing menus (`tui.py`), a theme system (`theme.py`), and a `klipper_service_stopped()` context manager (`service.py`).

---

## Critical Panel TUI Pitfalls

### PANEL-1: ANSI Escape Sequences Break Width Calculations

**What goes wrong:** ANSI escape sequences like `\033[38;2;100;160;180m` are invisible on screen but have string length 19+ characters. Any code using `len(styled_string)` for padding or alignment produces misaligned panels. The existing `_render_menu()` in `tui.py` already has a partial version of this problem -- it calculates `inner_width` from plain text items but embeds `theme.menu_title` (a styled string) into the border line. Currently this works because `len(title_plain)` is used separately, but extending to full panel layouts with multiple styled elements per line will multiply alignment bugs across every row.

**Why it happens:** Python `len()` counts characters including invisible escape codes. Every styled token adds 10-20 invisible characters to a line. With truecolor (`\033[38;2;R;G;Bm`), each color adds 19 chars per token, and a reset adds 4 more. A line with 3 colored tokens has 60+ invisible chars.

**Consequences:** Box borders don't align. Right-side vertical bars appear shifted. Content overflows panel boundaries. The bug is invisible with no-color theme (all escape strings are empty), making it hard to catch during development if NO_COLOR is set.

**Prevention:**
1. Build a `strip_ansi(text) -> str` utility using `re.sub(r'\033\[[0-9;]*m', '', text)` as the FIRST utility before any panel code
2. Build `display_width(text) -> int` that returns `len(strip_ansi(text))`
3. ALL padding, alignment, and ljust/rjust operations must use display width, never raw `len()`
4. Create a `pad_to_width(text, width) -> str` helper that pads based on display width
5. Test every panel render with BOTH color and no-color themes

**Detection:** Render panels with truecolor theme and check if right border characters align vertically. If they zigzag, this pitfall is active.

**Phase:** Panel rendering foundation -- must be the very first thing built before any panels.

---

### PANEL-2: Truecolor Not Supported in All Terminals

**What goes wrong:** The mockup uses specific RGB colors (#64A0B4, #82C8DC, etc.) which require truecolor escape sequences (`\033[38;2;R;G;Bm`). Many terminals don't support this: PuTTY (default settings), older `screen` sessions (not `tmux`), some SSH clients, and terminals with `TERM=xterm` (not `xterm-256color` or `xterm-direct`). These terminals will display garbled escape codes as literal text.

**Why it happens:** The existing `theme.py` uses ANSI 16-color codes (`\033[92m` etc.) which are universally supported. Switching to truecolor is a significant compatibility regression unless fallback is handled.

**Consequences:** Garbled output with literal escape sequences visible. On some terminals, the entire output becomes unreadable -- not just ugly colors but corrupted text.

**Prevention:**
1. Detect truecolor support via `COLORTERM` env var: values `truecolor` or `24bit` indicate support
2. Build a 3-tier theme system: truecolor (RGB) -> 256-color (approximation) -> 16-color (existing ANSI, current default)
3. Map each RGB value to nearest 256-color index as fallback: `\033[38;5;{index}m`
4. Keep current 16-color Theme as the safe baseline -- never remove it
5. The theme selection should be: `COLORTERM=truecolor` -> truecolor; `TERM` contains `256color` -> 256-color; else -> 16-color

**Detection:** SSH into Pi from PuTTY with default settings. If you see `[38;2;100;160;180m` as literal text, truecolor detection is missing.

**Phase:** Theme enhancement -- must be done before panel rendering uses new colors.

---

### PANEL-3: Batch Flash Partial Completion Without Recovery Info

**What goes wrong:** "Flash All" stops klipper once, flashes N devices sequentially, restarts klipper once. If device 2 of 4 fails (build error, flash timeout, device disconnected), the naive approach raises an exception. The `klipper_service_stopped()` context manager catches it and restarts klipper, but the user has NO record of which devices succeeded and which failed. They must manually check each board.

**Why it happens:** The existing single-device flash flow raises exceptions on failure (correct for single device). Wrapping a loop around it propagates the first failure and abandons remaining devices.

**Consequences:** User doesn't know printer state. Some boards have new firmware, some have old. Klipper may fail to start because MCU protocol versions are mismatched between boards. Worst case: user re-runs "Flash All" and re-flashes already-succeeded boards unnecessarily.

**Prevention:**
1. Batch flash must catch per-device exceptions and CONTINUE to the next device
2. Accumulate results into a list: `list[tuple[str, FlashResult | Exception]]`
3. After ALL devices attempted, display a summary table:
   ```
   octopus-pro    [OK]   Flashed successfully
   nitehawk-36    [FAIL] Build timeout after 300s
   ebb36          [OK]   Flashed successfully
   ```
4. Return non-zero exit code if ANY device failed
5. The `klipper_service_stopped()` context wraps the ENTIRE batch, not individual devices

**Detection:** Ask "what happens if device 2 of 4 fails?" If the answer is "remaining devices are skipped," this pitfall is active.

**Phase:** Batch flash implementation -- design the result accumulation pattern before coding the loop.

---

### PANEL-4: Klipper Stopped During Build Phase Wastes Downtime

**What goes wrong:** The obvious batch flash implementation: stop klipper -> for each device: (menuconfig -> build -> flash) -> restart klipper. But `make` build takes 1-3 minutes per device. With 4 devices, klipper is down for 4-12 minutes unnecessarily, because building firmware does NOT require klipper to be stopped -- only flashing does.

**Why it happens:** The existing single-device flow interleaves build and flash inside the `klipper_service_stopped()` context. This is fine for one device (build takes 2-3 min, flash takes 30s, total downtime 3 min). For batch, it multiplies.

**Consequences:** Klipper is offline for 10-20 minutes. Moonraker shows "disconnected." User's OctoPrint/Fluidd dashboard shows errors. If heaters were active, thermal runaway protection in firmware handles it but Moonraker cannot monitor temperatures.

**Prevention:**
1. Split batch flash into two phases:
   - **Build phase (klipper running):** For each device, run menuconfig (if needed) and `make`. Collect firmware binaries.
   - **Flash phase (klipper stopped):** Stop klipper ONCE, flash all pre-built binaries, restart klipper ONCE.
2. This reduces downtime from N * (build + flash) to N * flash_only (roughly 30s per device instead of 3 min per device).
3. The build phase can even abort early -- if any build fails, don't stop klipper at all.
4. This is an architectural decision that affects the entire batch flash design.

**Detection:** Time the full batch sequence. If klipper is stopped while `make` is running, this pitfall is active.

**Phase:** Batch flash architecture -- this separation must be designed FIRST, before implementation.

---

## Moderate Panel TUI Pitfalls

### PANEL-5: Terminal Width Handling for Panel Layout

**What goes wrong:** Panel with fixed-width borders is designed for 80+ columns. SSH sessions default to 80x24. tmux panes can be 40 columns. If the terminal is narrower than the panel, borders wrap to the next line, completely destroying the layout.

**Prevention:**
1. Query width with `shutil.get_terminal_size().columns` (stdlib, already used in concept)
2. Define minimum viable panel width (e.g., 50 chars)
3. If terminal < minimum, fall back to non-panel output (plain text with colors)
4. Truncate content text to fit, NEVER truncate border characters
5. Consider: panels have a fixed max width (e.g., 60 chars) and center within terminal, rather than stretching to fill

**Phase:** Panel rendering foundation.

---

### PANEL-6: Screen Flicker from Full Clear + Redraw

**What goes wrong:** The existing `clear_screen()` in `theme.py` uses `\033[H\033[J` (cursor home + clear to end). Panel TUI clears and redraws on every state change. Over SSH with 50-200ms latency, the user sees: blank screen -> brief pause -> new content. This creates visible flicker.

**Prevention:**
1. Use cursor home WITHOUT clear: `\033[H` moves cursor to top-left, then overwrite existing content
2. Pad each line to terminal width to erase previous content without explicit clear
3. Buffer entire frame as single string, write with one `sys.stdout.write()` + `flush()` call
4. For progress updates (flash status), use cursor positioning to update only changed lines: `\033[{row};1H`
5. Reserve full clear for transitions between major screens (menu -> flash -> menu), not for in-screen updates

**Phase:** Panel rendering foundation -- rendering strategy (full-clear vs. overwrite) is an early choice.

---

### PANEL-7: Countdown Timer Keypress Detection

**What goes wrong:** "Flash All in 5...4...3... press any key to cancel" needs non-blocking keypress detection. Python stdlib has no cross-platform solution. `input()` blocks until Enter. The target platform is Raspberry Pi (Linux), but development is on Windows.

**Prevention:**
1. **Linux (target):** Use `termios` + `select.select([sys.stdin], [], [], 0.1)` to poll for keypress with 100ms intervals. Set terminal to cbreak mode with `tty.setcbreak()`, restore in `finally` block.
2. **Windows (dev):** Use `msvcrt.kbhit()` + `msvcrt.getch()` for non-blocking keypress.
3. Abstract behind `wait_with_cancel(seconds: float) -> bool` that returns True if user pressed a key.
4. **Simpler alternative:** Use "Press Enter to continue or Ctrl+C to cancel" -- avoids all raw terminal complexity. `input()` with `signal.alarm()` (Unix) for timeout. This is less fancy but zero platform issues.
5. Always restore terminal mode in `finally` block. Raw/cbreak mode left active will break all subsequent `input()` calls.

**Detection:** Test on both Pi (SSH) and Windows. If countdown doesn't respond to keypress on either platform, the abstraction is incomplete.

**Phase:** Batch flash UX. Can start with simple Enter/Ctrl+C approach and upgrade later.

---

### PANEL-8: `make` Output Corrupts Panel Layout

**What goes wrong:** `make` build and `make flash` use inherited stdio (per project conventions -- SP-1, SP-5). Their output scrolls freely. If a panel frame is drawn around the build, make's output (compiler lines, warnings, progress) overwrites panel borders.

**Prevention:**
1. During build/flash phases that use inherited stdio, SUSPEND panel rendering entirely
2. Show a simple pre-build message: `"Building firmware for octopus-pro..."`, let make output scroll normally, show post-build status after make exits
3. Do NOT try to capture make output and render it inside a panel -- this loses real-time progress and adds complexity
4. For batch flash, between devices, re-render the summary panel showing completed/pending status
5. Alternative: capture output with `subprocess.PIPE` and display filtered/summarized, but this contradicts the existing inherited-stdio convention and loses real-time feedback

**Phase:** Batch flash UX -- decide early whether build output is captured or inherited. Recommendation: inherit stdio during build, panels only for pre/post status.

---

### PANEL-9: Unicode Box Drawing Width on Edge Cases

**What goes wrong:** Standard box-drawing characters (U+2500 block) are single-width in all standard terminals. But the existing `_supports_unicode()` in `tui.py` only checks `LANG` and `LC_ALL` env vars. Over SSH, the remote Pi may have `LANG=C` or `LANG=en_GB.UTF-8` while the local terminal supports UTF-8. Misdetection causes ASCII fallback when Unicode would work, or Unicode attempt when ASCII is needed.

**Prevention:**
1. Also check `sys.stdout.encoding` -- if it reports `utf-8`, the Python IO layer will handle encoding regardless of LANG
2. Check `TERM` variable -- modern terminals with `xterm-256color` or similar almost always support Unicode
3. Keep ASCII fallback (already exists in `tui.py`) for truly incapable terminals
4. For panel text content with user-provided strings (device names), stick to ASCII device names in registry to avoid width calculation issues

**Phase:** Panel rendering foundation.

---

### PANEL-10: Raw Terminal Mode Conflicts with `input()`

**What goes wrong:** If terminal is set to raw/cbreak mode for countdown keypress detection (PANEL-7), any `input()` call elsewhere breaks -- no line editing, no echo, no Enter processing. This is especially dangerous if an exception occurs during raw mode and the `finally` block doesn't execute (e.g., SIGKILL).

**Prevention:**
1. Use context managers for raw mode: `with cbreak_terminal(): ...`
2. NEVER leave terminal in raw mode across function boundaries
3. The countdown timer should be a self-contained function that sets and restores terminal mode internally
4. If using raw mode, install `atexit.register(restore_terminal)` as a safety net
5. After any subprocess that uses inherited stdio (`make menuconfig`), terminal mode may already be restored -- but verify with explicit restore

**Phase:** Batch flash UX -- only relevant if implementing non-blocking keypress.

---

### PANEL-11: Service Context Manager Nesting with Batch Flash

**What goes wrong:** The existing `klipper_service_stopped()` context manager stops klipper on entry and restarts on exit. If batch flash code accidentally nests this (e.g., calling single-device flash function that has its own `with klipper_service_stopped()`), klipper gets stopped twice (second stop is a no-op) but the inner context restarts klipper mid-batch. Remaining devices flash with klipper running, which corrupts the serial port.

**Why it happens:** The single-device flash function may contain `with klipper_service_stopped()` internally. Calling it in a loop within an outer `klipper_service_stopped()` context creates nesting.

**Prevention:**
1. Batch flash must NOT call the single-device flash function as-is. Extract the flash-only logic (no service management) into a separate function.
2. Structure: `_flash_device_only(device)` does the flash without touching klipper. `cmd_flash_single(device)` wraps it with `klipper_service_stopped()`. `cmd_flash_all(devices)` wraps the loop with a SINGLE `klipper_service_stopped()` and calls `_flash_device_only()` per device.
3. Alternatively, make `klipper_service_stopped()` reentrant -- track "is already stopped" state and skip nested stop/start. But this adds complexity and hidden state.

**Detection:** Read the batch flash code and check whether `klipper_service_stopped()` appears inside a loop that is itself inside `klipper_service_stopped()`. If yes, this pitfall is active.

**Phase:** Batch flash architecture -- must be designed during the initial batch flash function decomposition.

---

## Phase-Specific Warnings (v2.1 Panel TUI + Batch Flash)

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Panel renderer foundation | ANSI width miscalculation (PANEL-1) | Build `strip_ansi`/`display_width` as FIRST utility |
| Panel renderer foundation | Terminal width (PANEL-5) | Use `shutil.get_terminal_size()` from day one |
| Panel renderer foundation | Screen flicker (PANEL-6) | Choose cursor-home + overwrite, not full-clear |
| Panel renderer foundation | Unicode detection (PANEL-9) | Check `sys.stdout.encoding` in addition to LANG |
| Theme truecolor upgrade | No truecolor support (PANEL-2) | 3-tier fallback: truecolor -> 256 -> 16-color |
| Batch flash architecture | Partial completion (PANEL-3) | Per-device try/except with result accumulation |
| Batch flash architecture | Long klipper downtime (PANEL-4) | Build ALL first, then stop klipper, then flash all |
| Batch flash architecture | Context manager nesting (PANEL-11) | Extract `_flash_device_only()` without service mgmt |
| Batch flash UX | Countdown keypress (PANEL-7) | Start with Enter/Ctrl+C, upgrade to raw mode later |
| Batch flash UX | make output vs panels (PANEL-8) | Suspend panels during inherited-stdio phases |
| Batch flash UX | Raw mode conflicts (PANEL-10) | Context manager for raw mode, atexit safety net |

---

## Key Takeaway

The single most important design principle for this tool: **the klipper service must always be restarted**. Every code path -- success, failure, exception, signal, timeout, keyboard interrupt -- must ensure klipper is running when the tool exits. This is not just a convenience issue; it is a safety issue. A printer with heated bed and no firmware control is a fire hazard. Design the entire tool around this invariant.

The second most important principle: **verify before you flash**. Check that the device exists, the config matches the target MCU, and no print is running before touching anything. It is always safer to abort and ask the user than to proceed with uncertain state.

**For v2.0 additions:** Preserve existing behavior. The `--device KEY` flag must continue to work exactly as before. TUI enhancements are additive, not replacements. Follow the hub-and-spoke architecture. All new modules must be leaves that only import models.py and errors.py.

**For v2.1 panel TUI + batch flash:** The three architectural decisions that must be made FIRST:
1. **ANSI width utilities** (PANEL-1) before any panel rendering code
2. **Build-then-flash separation** (PANEL-4) before batch flash implementation
3. **Service context decomposition** (PANEL-11) to prevent nested stop/start

---

## Sources

### v1.0 Research
- Klipper ecosystem domain knowledge
- Linux device model semantics
- Python subprocess API behavior
- Real-world failure modes documented in Klipper/Katapult community forums

### v2.0 Research (2026-01-26)
- [Moonraker Printer Objects Documentation](https://moonraker.readthedocs.io/en/latest/printer_objects/)
- [Moonraker Printer Administration API](https://moonraker.readthedocs.io/en/latest/external_api/printer/)
- [Git describe documentation](https://git-scm.com/docs/git-describe)
- [PEP 440 Version Identification](https://peps.python.org/pep-0440/)
- [PySerial USB disconnection handling](https://github.com/pyserial/pyserial/issues/331)
- [Python symlink permission issues](https://bugs.python.org/issue45226)
- [SSH pseudo-terminal allocation](https://www.baeldung.com/linux/ssh-pseudo-terminal-allocation)
- [Unicode box drawing characters in Python](https://pythonadventures.wordpress.com/2014/03/20/unicode-box-drawing-characters/)
- [Python requests retry patterns](https://www.zenrows.com/blog/python-requests-retry)
- Existing kalico-flash codebase analysis (flash.py, registry.py, discovery.py, service.py, output.py, etc.)

### v2.1 Research (2026-01-29)
- Existing codebase analysis: `tui.py` (box-drawing menu, `_render_menu`, `_supports_unicode`), `theme.py` (ANSI 16-color, `supports_color`, `clear_screen`), `service.py` (`klipper_service_stopped` context manager), `output.py` (Output protocol, CliOutput)
- Python `termios`/`tty` module documentation for raw terminal mode
- Python `shutil.get_terminal_size()` documentation
- ANSI escape sequence specifications (SGR parameters for 256-color and truecolor)
- `COLORTERM` environment variable convention for truecolor detection
- Python `select` module for non-blocking stdin polling on Unix

---

*Pitfalls research: 2026-01-25 (v1.0), 2026-01-26 (v2.0 additions), 2026-01-29 (v2.1 panel TUI + batch flash)*
*Confidence: HIGH -- based on direct codebase analysis, Klipper ecosystem domain knowledge, Python terminal handling semantics.*
