---
phase: 02-build-config-pipeline
plan: 02
subsystem: build
tags: [menuconfig, ncurses, make, subprocess, inherited-stdio]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: errors.py exception hierarchy, models.py dataclasses
  - phase: 02-build-config-pipeline
    plan: 01
    provides: ConfigManager for cache operations
provides:
  - run_menuconfig function with ncurses TUI passthrough
  - run_build function with streaming make output
  - Builder convenience class
  - BuildResult dataclass for build outcomes
affects: [02-03, flash-orchestration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Inherited stdio: subprocess.run without stdin/stdout/stderr args"
    - "KCONFIG_CONFIG env var: absolute path for config file targeting"
    - "Mtime comparison: detect config file changes"
    - "Parallel make: multiprocessing.cpu_count() for -j flag"

key-files:
  created:
    - klipper-flash/build.py
  modified:
    - klipper-flash/errors.py
    - klipper-flash/models.py

key-decisions:
  - "BuildError exception follows existing error hierarchy pattern"
  - "BuildResult uses Optional[str] for firmware_path to handle failed builds"
  - "Mtime detection for config changes handles both new file creation and modification"

patterns-established:
  - "Inherited stdio for TUI passthrough: no PIPE redirection"
  - "Build result dataclass: success flag with optional error/output details"

# Metrics
duration: 2min
completed: 2026-01-25
---

# Phase 02 Plan 02: Build Pipeline Summary

**Build module with menuconfig TUI passthrough and streaming make output using inherited stdio**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-25T07:18:24Z
- **Completed:** 2026-01-25T07:20:36Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- BuildError exception class added to error hierarchy
- BuildResult dataclass with success, firmware_path, firmware_size, elapsed_seconds, error_message
- run_menuconfig function with KCONFIG_CONFIG env var for config file targeting
- Inherited stdio for ncurses TUI passthrough (no PIPE redirection)
- Mtime comparison to detect if config was saved during menuconfig
- run_build function with make clean + make -j parallel compilation
- CPU count detection for optimal parallel jobs
- Firmware size verification from out/klipper.bin after build
- Builder convenience class wrapping both operations

## Task Commits

Each task was committed atomically:

1. **Task 1 & 2: BuildError, BuildResult, and build.py** - `77956f6` (feat)
   - Both tasks combined since build.py was created complete with all functions

## Files Created/Modified
- `klipper-flash/build.py` - run_menuconfig, run_build, Builder class (153 lines)
- `klipper-flash/errors.py` - Added BuildError exception class
- `klipper-flash/models.py` - Added BuildResult dataclass

## Decisions Made
- **Task consolidation:** Tasks 1 and 2 implemented together since build.py was created complete in one pass
- **Inherited stdio pattern:** All subprocess.run calls omit stdin/stdout/stderr to inherit from parent for TUI passthrough and streaming output
- **Absolute path for KCONFIG_CONFIG:** Uses Path.expanduser().absolute() to ensure make menuconfig writes to correct location

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tests passed on first run.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- build.py ready for orchestration layer integration
- run_menuconfig provides TUI passthrough for interactive configuration
- run_build provides streaming output with BuildResult for status reporting
- ConfigManager (02-01) and Builder integrate at higher layer

---
*Phase: 02-build-config-pipeline*
*Completed: 2026-01-25*
