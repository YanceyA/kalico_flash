---
phase: 03-flash-orchestration
verified: 2026-01-25T23:30:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 3: Flash & Orchestration Verification Report

**Phase Goal:** User runs one command to build and flash any registered board with guaranteed klipper service restart on all code paths

**Verified:** 2026-01-25T23:30:00Z
**Status:** PASSED
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | flash.py orchestrates full workflow: discover device, configure, build, stop klipper, flash, restart klipper -- in one command with --device NAME or interactive selection | VERIFIED | cmd_flash() function in flash.py implements all phases: Discovery (lines 215-288), Config (lines 290-333), Build (lines 335-346), Flash (lines 348-392) with context manager |
| 2 | Klipper service is always restarted after flash -- on success, failure, exception, or Ctrl+C -- enforced by context manager with finally block | VERIFIED | service.py klipper_service_stopped() has finally block (line 107) that calls _start_klipper() which does not raise exceptions; used in flash.py line 365 |
| 3 | Katapult flashtool.py is attempted first; if it fails, make flash is automatically tried as fallback, both using /dev/serial/by-id/ stable symlink paths | VERIFIED | flasher.py flash_device() calls _try_katapult_flash() first (line 170), then _try_make_flash() on failure (lines 175-179); both use device_path passed from USB discovery |
| 4 | Device path is re-verified immediately before flash (after menuconfig + build delay), passwordless sudo is verified before service operations, and all subprocesses except menuconfig have timeouts | VERIFIED | verify_device_path() called at line 351 in flash.py; verify_passwordless_sudo() called at line 358; TIMEOUT_BUILD=300, TIMEOUT_FLASH=60, TIMEOUT_SERVICE=30 with TimeoutExpired handling; menuconfig has no timeout |
| 5 | Console output uses phase labels ([Discovery], [Config], [Build], [Flash]), failures show what failed + command run + likely cause + recovery steps, and a success/failure summary appears at the end | VERIFIED | out.phase() calls throughout flash.py; error messages with Recovery: hints (lines 341, 354, 377, 391); success summary at line 385 with device name, method, elapsed time |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| klipper-flash/errors.py | ServiceError and FlashError exception types | VERIFIED | Lines 38-45: ServiceError and FlashError classes exist, inherit from KlipperFlashError |
| klipper-flash/models.py | FlashResult dataclass with success, method, elapsed_seconds, error_message fields | VERIFIED | Lines 50-56: FlashResult dataclass with all required fields |
| klipper-flash/service.py | KlipperServiceManager context manager with guaranteed restart | VERIFIED | Lines 83-111: klipper_service_stopped() context manager with finally block; 110 lines total |
| klipper-flash/service.py | verify_passwordless_sudo() function | VERIFIED | Lines 14-31: Returns bool, uses sudo -n true with 5s timeout |
| klipper-flash/flasher.py | flash_device() with Katapult-first, make-flash-fallback logic | VERIFIED | Lines 145-185: Implements dual-method strategy; 186 lines total |
| klipper-flash/flasher.py | verify_device_path() that raises DiscoveryError | VERIFIED | Lines 16-29: Checks Path.exists(), raises DiscoveryError with helpful message |
| klipper-flash/output.py | phase() method for phase-labeled output | VERIFIED | Lines 19, 52-54, 67: phase() in Protocol, CliOutput, NullOutput |
| klipper-flash/build.py | TIMEOUT_BUILD constant and timeout support | VERIFIED | Line 15: TIMEOUT_BUILD=300; lines 63-141: run_build() accepts timeout param, handles TimeoutExpired |
| klipper-flash/flash.py | cmd_flash() orchestrator with full workflow | VERIFIED | Lines 177-392: 215-line cmd_flash() function implementing complete workflow |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| flash.py | service.py | klipper_service_stopped context manager | WIRED | Line 365: with klipper_service_stopped() wraps flash operation |
| flash.py | flasher.py | flash_device() call | WIRED | Line 367: flash_result = flash_device(...) with all required params |
| flash.py | discovery.py | scan_serial_devices for interactive selection | WIRED | Line 217: usb_devices = scan_serial_devices() for discovery |
| flash.py | build.py | run_build with timeout | WIRED | Line 337: run_build(klipper_dir, timeout=TIMEOUT_BUILD) |
| flasher.py | katapult/scripts/flashtool.py | subprocess call | WIRED | Lines 52-68: Builds flashtool path, runs python3 flashtool.py with device/firmware paths |
| flasher.py | make flash | subprocess call on failure | WIRED | Lines 114-134: make FLASH_DEVICE with cwd=klipper_dir |
| service.py | systemctl | stop/start klipper | WIRED | Lines 44-50: sudo systemctl stop klipper; lines 66-74: sudo systemctl start klipper |

### Requirements Coverage

All Phase 3 requirements SATISFIED:

| Requirement | Status | Evidence |
|-------------|--------|----------|
| FLSH-01: Katapult attempted first | SATISFIED | flasher.py line 170: _try_katapult_flash() called before fallback |
| FLSH-02: Automatic fallback to make flash | SATISFIED | flasher.py lines 175-179: Fallback on Katapult failure |
| FLSH-03: Uses /dev/serial/by-id/ stable paths | SATISFIED | Device paths from discovery.py USB scan passed through unchanged |
| SRVC-01: Klipper stopped before flash | SATISFIED | service.py line 104: _stop_klipper() called on context entry |
| SRVC-02: Always restarted (success/failure/exception/Ctrl+C) | SATISFIED | service.py lines 107-110: finally block ensures restart |
| SRVC-03: Passwordless sudo verified | SATISFIED | flash.py line 358: verify_passwordless_sudo() called; informational warning if fails |
| DISC-05: Device path re-verified before flash | SATISFIED | flash.py line 351: verify_device_path() called after build |
| CLUX-01: Phase-labeled console output | SATISFIED | flash.py uses out.phase() with [Discovery], [Config], [Build], [Flash] labels |
| CLUX-02: Subprocess timeouts | SATISFIED | TIMEOUT_BUILD=300, TIMEOUT_FLASH=60, TIMEOUT_SERVICE=30; menuconfig intentionally no timeout |
| CLUX-03: Clear error messages with recovery | SATISFIED | flash.py lines 341, 354, 377, 391: Recovery hints on failures |
| CLUX-04: Success/failure summary | SATISFIED | flash.py lines 383-392: Final summary with device name, method, time |

### Anti-Patterns Found

None - No stub patterns, TODOs, or placeholder implementations found in phase 3 code.

### Human Verification Required

#### 1. End-to-End Flash Workflow Test

**Test:** Run python flash.py --device {registered_device} on a Raspberry Pi with Klipper service and a connected MCU board

**Expected:**
- Discovery phase finds the device
- Config phase launches menuconfig (ncurses TUI works)
- Build phase compiles firmware (shows real-time output, reports size)
- Flash phase stops Klipper service, flashes firmware, restarts Klipper
- Success message shows device name, flash method (katapult or make_flash), elapsed time

**Why human:** Requires actual hardware (Pi + MCU board), running Klipper service, and systemctl permissions.

#### 2. Interactive Device Selection

**Test:** Run python flash.py (no --device flag) with multiple registered devices connected

**Expected:**
- Shows numbered list of connected devices
- Prompts for device number selection
- Validates input (rejects non-numbers, out-of-range)
- Proceeds to full flash workflow after selection

**Why human:** Interactive terminal I/O with user input cannot be fully verified without running.

#### 3. Service Restart on Ctrl+C

**Test:** Run flash workflow, press Ctrl+C during the flash operation

**Expected:**
- Klipper service is restarted even though operation was interrupted
- Terminal shows cleanup message
- systemctl status klipper shows service is active

**Why human:** Requires interrupt signal during specific phase, must verify service state after interrupt.

#### 4. Katapult Fallback to make flash

**Test:** Flash a device where Katapult flashtool.py fails

**Expected:**
- First attempt shows Katapult failure message
- Console shows [Flash] Trying make flash as fallback...
- make flash succeeds and firmware is written
- Success summary shows method=make_flash

**Why human:** Requires specific failure scenario setup.

#### 5. Pre-flash Device Verification

**Test:** Start flash workflow, then unplug the device during menuconfig or build phase

**Expected:**
- Build completes successfully
- Pre-flash verification detects device is gone
- Error message: Device no longer connected
- Recovery hint: Reconnect the device and try again
- No attempt to flash, Klipper service not stopped

**Why human:** Requires physical device disconnect at specific timing.

---

## Summary

### Phase 3 Goal Achievement: VERIFIED

All 5 observable truths are verified in the codebase:

1. **Full workflow orchestration** - cmd_flash() implements discover to config to build to flash with --device KEY or interactive selection
2. **Guaranteed service restart** - finally block in context manager ensures Klipper restarts on all code paths
3. **Dual-method flash with fallback** - Katapult tried first, make flash automatic fallback, both use stable USB paths
4. **Pre-flash safety checks** - Device path re-verified, sudo checked, all operations have timeouts (except menuconfig)
5. **Clear UX with phase labels** - [Discovery], [Config], [Build], [Flash] labels, failures show recovery steps, summary at end

### Code Quality

- All modules compile without syntax errors (verified with py_compile)
- All imports resolve correctly (late imports work)
- No stub patterns detected
- No TODO/FIXME comments in phase 3 code
- Proper exception handling throughout
- Timeout protection on all subprocess calls (except menuconfig)
- Context manager ensures resource cleanup

### Integration Completeness

- service.py integrates with flash.py via context manager
- flasher.py integrates with flash.py via flash_device() call
- build.py timeout support consumed by flash.py
- output.py phase() method used throughout workflow
- All data flows through defined dataclass contracts (FlashResult, BuildResult)

### Next Steps

1. Human verification testing - 5 test scenarios documented above require actual hardware
2. Integration test on target Pi - Full end-to-end test with real devices
3. Documentation - User guide for flash workflow, troubleshooting common issues

---

Verified: 2026-01-25T23:30:00Z
Verifier: Claude (gsd-verifier)
