---
phase: 04-foundation
plan: 04
subsystem: error-handling
tags: [error-messages, user-experience, recovery-steps]

dependency_graph:
  requires:
    - "04-01: Error framework (format_error, ERROR_TEMPLATES, error_with_recovery)"
  provides:
    - "Integrated error framework across all flash.py error paths"
    - "Numbered recovery steps for all error templates"
  affects:
    - "Phase 5/6: Future error paths will follow same pattern"

tech_stack:
  added: []
  patterns:
    - "ERROR_TEMPLATES for centralized error messaging"
    - "error_with_recovery() for structured error output"
    - "Numbered recovery steps (1., 2., 3.) for user guidance"

key_files:
  created: []
  modified:
    - "kalico-flash/errors.py"
    - "kalico-flash/flash.py"

decisions:
  - id: "numbered-recovery-format"
    choice: "Use numbered steps (1., 2., 3.) instead of prose paragraphs"
    rationale: "Scannable, actionable, easier to follow in terminal output"

metrics:
  duration: "~15 minutes"
  completed: "2026-01-26"
---

# Phase 04 Plan 04: Error Framework Integration Summary

**One-liner:** All flash.py error paths now use error_with_recovery() with numbered recovery steps and device context.

## What Was Built

This plan completed the error framework integration by:
1. Converting all 12 ERROR_TEMPLATES recovery text to numbered steps
2. Wiring error_with_recovery() into all flash.py error paths
3. Ensuring users see actionable numbered recovery steps for every error

## Key Changes

### ERROR_TEMPLATES Numbered Steps (errors.py)

All 12 templates now use numbered recovery format:
- build_failed: 4 steps (check output, verify config, check toolchain, clean+retry)
- menuconfig_failed: 3 steps (install ncurses, verify directory, try direct)
- device_not_registered: 3 steps (list devices, add device, check spelling)
- device_not_connected: 3 steps (check USB, list devices, re-register)
- mcu_mismatch: 3 steps (run without skip, update registration, verify config)
- service_stop_failed: 3 steps (check status, verify sudo, try manual)
- service_start_failed: 3 steps (start manually, check logs, note firmware OK)
- flash_failed: 4 steps (power cycle, check bootloader, check DFU, retry)
- katapult_not_found: 3 steps (note fallback, install at path, verify)
- moonraker_unavailable: 4 steps (check status, restart, verify API, note continue)
- printer_busy: 4 steps (wait, check dashboard, use --force, cancel print)
- device_excluded: 3 steps (include device, list devices, note reason)

### flash.py Error Path Conversions

**Build/Config errors (8 sites):**
- cmd_build: menuconfig exit, cache failure, MCU mismatch, validation error, build failed
- cmd_flash: Same 5 sites duplicated in flash workflow

**Device errors (8 sites):**
- cmd_build: device not found
- cmd_flash: no registered devices, all excluded, device not found, device not connected
- cmd_remove_device, cmd_exclude_device, cmd_include_device: device not found

**Flash/Service errors (3 sites):**
- cmd_flash: device disconnected (DiscoveryError), operation error (Exception), flash failed (FlashResult)

**Simple errors preserved as out.error() (~13 sites):**
- "Interactive terminal required" - informational
- "Global config not set" - simple instruction
- "No USB devices found" - simple action
- "Too many invalid selections/inputs" - user input errors
- "MCU type is required" - validation
- Generic exception fallback - catch-all

## Metrics

| Metric | Value |
|--------|-------|
| error_with_recovery() calls | 22 |
| Remaining out.error() calls | 13 |
| Templates with numbered steps | 12/12 |
| Commits | 4 |

## Commits

| Hash | Description |
|------|-------------|
| 6e77b2a | Convert ERROR_TEMPLATES to numbered recovery steps |
| 813db82 | Convert Build/Config errors to error_with_recovery() |
| 7e41b87 | Convert Device errors to error_with_recovery() |
| 2bed25a | Convert Flash/Service errors to error_with_recovery() |

## Deviations from Plan

None - plan executed exactly as written.

## Testing Performed

- Verified all 12 ERROR_TEMPLATES have numbered recovery steps
- Verified ERROR_TEMPLATES import present in flash.py (5 import sites)
- Verified 22 error_with_recovery() calls in flash.py
- Verified 13 simple out.error() calls remain
- Verified Python imports work without errors

## Next Phase Readiness

**Ready for:** Phase 04-05 (if exists) or Phase 05

**Dependencies satisfied:**
- All error paths now use consistent error framework
- Users see numbered recovery steps with context

**No blockers identified.**
