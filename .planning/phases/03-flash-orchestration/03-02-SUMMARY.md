# Phase 3 Plan 02: Flash Orchestrator Complete

**One-liner:** cmd_flash orchestrates full discovery->config->build->flash workflow with phase-labeled output and interactive device selection.

## What Was Built

### output.py Additions
- Added `phase()` method to Output Protocol for phase-labeled messages
- Added `phase()` to CliOutput: `[PhaseName] message` format
- Added `phase()` to NullOutput: silent stub for testing

### build.py Additions
- Added `TIMEOUT_BUILD = 300` constant (5 minutes for make operations)
- Updated `run_build()` to accept optional `timeout` parameter
- Added `TimeoutExpired` handling for both `make clean` and `make -j`

### flash.py Additions
- Added `cmd_flash(registry, device_key, out)` orchestrator function (217 lines)
- Orchestrates complete workflow in 4 labeled phases:
  1. **[Discovery]** - Scan USB devices, select target (interactive or explicit)
  2. **[Config]** - Load cached config, run menuconfig, validate MCU
  3. **[Build]** - Compile firmware with timeout protection
  4. **[Flash]** - Stop Klipper, flash device, restart Klipper
- Interactive mode when `device_key=None`: shows numbered list of connected registered devices
- Single device auto-selects with confirmation prompt
- Multiple devices prompt for number selection (3 attempts)
- Updated `main()` to route to `cmd_flash` for both `--device KEY` and no-args modes
- Updated help text and docstrings

## Key Integration Points

| From | To | Via | Pattern |
|------|----|-----|---------|
| flash.py | service.py | klipper_service_stopped | `with klipper_service_stopped():` |
| flash.py | flasher.py | flash_device | `flash_device(device_path, firmware_path, ...)` |
| flash.py | discovery.py | scan_serial_devices | `scan_serial_devices()` |
| flash.py | config.py | ConfigManager | `ConfigManager(device_key, klipper_dir)` |
| flash.py | build.py | run_build | `run_build(klipper_dir, timeout=TIMEOUT_BUILD)` |

## Output Format Examples

**Phase labels:**
```
[Discovery] Scanning for USB devices...
[Discovery] Found 2 registered device(s):
  [1] octopus (stm32h723)              /dev/serial/by-id/usb-Klipper_...
  [2] nhk (stm32g0b1)                  /dev/serial/by-id/usb-Klipper_...
[Config] Loading config for Octopus Pro...
[Config] MCU validated: stm32h723
[Build] Running make clean + make...
[Build] Firmware ready: 52.3 KB in 24.1s
[Flash] Stopping Klipper...
[Flash] Flashing firmware...
[Flash] Klipper restarted
[OK] Flashed Octopus Pro via katapult in 8.2s
```

**Failure output:**
```
[FAIL] Flash failed: Device not responding
[FAIL] Method attempted: katapult
[FAIL] Recovery: Power cycle the board and try again.
```

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 8b4aa25 | feat | Add phase() output method and TIMEOUT_BUILD |
| 5dbd2c5 | feat | Add cmd_flash orchestrator with full build+flash workflow |

## Files Modified

| File | Lines | Changes |
|------|-------|---------|
| klipper-flash/output.py | 68 | Added phase() to Protocol, CliOutput, NullOutput |
| klipper-flash/build.py | 163 | Added TIMEOUT_BUILD, timeout param, TimeoutExpired handling |
| klipper-flash/flash.py | 664 | Added cmd_flash orchestrator, updated main(), docstrings |

## Deviations from Plan

### Task 3 Merged into Task 2

Task 3 (interactive device selection) was implemented directly as part of Task 2's cmd_flash function rather than as a separate commit. This was more natural since the interactive selection is integral to cmd_flash's flow, not a separate feature. Result: 2 commits instead of 3, same functionality delivered.

## Test Coverage

**Syntax validation:**
- `python -m py_compile flash.py output.py build.py` - PASS

**Import chain:**
- All late imports resolve correctly
- `cmd_flash`, `CliOutput`, `TIMEOUT_BUILD`, `klipper_service_stopped`, `flash_device` all import cleanly

**Help text:**
- `--device` shown as optional
- Epilog mentions interactive selection and flash workflow

**Note:** Full end-to-end testing requires running on target Pi with actual USB devices and Klipper service.

## Phase 3 Status

| Plan | Status | Description |
|------|--------|-------------|
| 03-01 | Complete | Service lifecycle + flasher modules |
| 03-02 | Complete | Flash orchestrator with full workflow |
| 03-03 | Pending | Integration testing and documentation |

## Success Criteria Met

- [x] output.py has phase() method on Protocol, CliOutput, and NullOutput
- [x] build.py has TIMEOUT_BUILD=300 and run_build() handles TimeoutExpired
- [x] flash.py has cmd_flash() orchestrating: discovery -> config -> build -> flash
- [x] flash.py --device KEY runs full workflow with phase labels
- [x] flash.py (no args) shows interactive device selection
- [x] Phase labels use [Discovery], [Config], [Build], [Flash] format
- [x] Success shows device name, flash method, elapsed time
- [x] Failure shows what failed with recovery hint
- [x] All modules compile without syntax errors
