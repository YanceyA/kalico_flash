# Phase 4 Plan 1: Error Message Framework Summary

Standardized error formatting with context and recovery guidance for actionable error messages.

## Completion Status

| Task | Name | Commit | Status |
|------|------|--------|--------|
| 1 | Add error formatting utilities to errors.py | b402af1 | Done |
| 2 | Add error_with_recovery() to Output protocol | a217d76 | Done |
| 3 | Add context attributes to exception classes | 789536a | Done |

**Duration:** ~3 minutes (07:22:05 - 07:24:46 UTC)

## What Was Built

### Error Formatting Infrastructure (errors.py)

**format_error() function:**
- Produces plain ASCII output wrapped to 80 columns
- Accepts error_type, message, optional context dict, optional recovery prose
- Context dict converted to natural prose (e.g., "Affected: device 'octopus-pro', MCU 'stm32h723'.")
- Recovery text wrapped to 80 columns as prose paragraphs

**ERROR_TEMPLATES dict (12 templates):**
- Build errors: build_failed, menuconfig_failed
- Device errors: device_not_registered, device_not_connected
- MCU errors: mcu_mismatch
- Service errors: service_stop_failed, service_start_failed
- Flash errors: flash_failed, katapult_not_found
- Moonraker errors (Phase 5 placeholder): moonraker_unavailable, printer_busy
- Exclusion errors: device_excluded

### Output Protocol Extension (output.py)

**error_with_recovery() method:**
- Added to Output protocol signature
- Implemented in CliOutput using format_error() from errors module
- Empty implementation in NullOutput for testing/programmatic use
- Existing error() method preserved for backward compatibility

### New Exception Classes (errors.py)

**DeviceNotFoundError enhancement:**
- Added `connected` attribute (keyword-only) to distinguish registry miss from USB miss

**ConfigMismatchError (new):**
- Raised when cached config MCU differs from registered device MCU
- Attributes: expected_mcu, actual_mcu, device_key

**ExcludedDeviceError (new):**
- Raised when attempting to flash an excluded device
- Attribute: device_key

## Key Files

| File | Changes |
|------|---------|
| kalico-flash/errors.py | +format_error(), +ERROR_TEMPLATES, +ConfigMismatchError, +ExcludedDeviceError, enhanced DeviceNotFoundError |
| kalico-flash/output.py | +error_with_recovery() on Output/CliOutput/NullOutput |

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

- Python syntax check: passed
- Import test: passed
- 80-column wrap test: passed (all output lines <= 80 chars)
- No ANSI colors or Unicode in output: verified

## Dependencies Provided

- **For 04-02 (Device Exclusion):** ExcludedDeviceError class ready
- **For 04-03 (Skip Menuconfig):** ConfigMismatchError class ready
- **For all modules:** format_error() and error_with_recovery() provide consistent error output

---

*Plan: 04-01 | Phase: 04-foundation | Completed: 2026-01-26*
