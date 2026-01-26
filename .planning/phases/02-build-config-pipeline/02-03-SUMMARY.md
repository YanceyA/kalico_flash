---
phase: 02-build-config-pipeline
plan: 03
subsystem: flash-cli
tags: [orchestration, wiring, build-workflow, mcu-validation]

# Dependency graph
requires:
  - phase: 02-build-config-pipeline
    plan: 01
    provides: ConfigManager for config caching and MCU validation
  - phase: 02-build-config-pipeline
    plan: 02
    provides: run_menuconfig, run_build for build operations
provides:
  - cmd_build orchestrator function in flash.py
  - Working --device flag that runs complete build cycle
  - MCU validation before build execution
affects: [03-flash-orchestration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Orchestration function: multi-step workflow with validation gates"
    - "Late imports: maintain fast CLI startup by importing inside functions"

key-files:
  created: []
  modified:
    - klipper-flash/flash.py

key-decisions:
  - "cmd_build uses late imports to maintain fast CLI startup"
  - "MCU validation runs after menuconfig, before build"
  - "Config caching happens after menuconfig save"
  - "Unsaved config prompts user confirmation before continuing"

patterns-established:
  - "5-step build orchestration: load config -> menuconfig -> cache config -> validate MCU -> build"
  - "MCU mismatch blocks build with clear error message"

# Metrics
duration: 2min
completed: 2026-01-25
---

# Phase 02 Plan 03: Wire Build Orchestrator Summary

**cmd_build function wiring config.py and build.py into flash.py CLI for complete build workflow**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-25T07:25:00Z
- **Completed:** 2026-01-25T07:27:00Z
- **Tasks:** 3 (all combined into single atomic change)
- **Files modified:** 1

## Accomplishments
- cmd_build function with 5-step orchestration flow
- ConfigManager integration for per-device config caching
- run_menuconfig with ncurses TUI passthrough
- Config caching after menuconfig save
- MCU validation before build (blocks on mismatch)
- run_build with streaming output and result reporting
- Replaced "Flash workflow not yet implemented" with working build
- --device flag now triggers complete build cycle

## Task Commits

Each task was committed atomically:

1. **Tasks 1-3: cmd_build orchestrator** - `c5a200d` (feat)
   - All three tasks implemented as single cohesive change since they form one atomic feature

## Files Modified
- `klipper-flash/flash.py` - Added cmd_build function (88 lines), replaced --device handler

## Key Wiring Established

| From | To | Via |
|------|-----|-----|
| flash.py | config.py | `from config import ConfigManager` |
| flash.py | build.py | `from build import run_menuconfig, run_build` |
| cmd_build | validate_mcu | `config_mgr.validate_mcu(entry.mcu)` |
| --device flag | cmd_build | `return cmd_build(registry, args.device, out)` |

## Decisions Made
- **Late imports inside cmd_build:** Follows existing pattern in flash.py (lines 126, 177, 314-317) for fast CLI startup
- **MCU validation after menuconfig:** User can see/fix config before validation blocks build
- **Unsaved config confirmation:** Prompts user to continue or cancel if menuconfig exits without saving

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all verifications passed on first run.

## Phase 2 Completion Status

All three plans in Phase 2 complete:
- 02-01: config.py with XDG caching and MCU parsing
- 02-02: build.py with menuconfig TUI passthrough and make build
- 02-03: flash.py wiring for complete build workflow

**Phase 2 gaps closed:**
- Gap 1: --device flag now runs build cycle (was "not yet implemented")
- Gap 2: MCU validation runs before build execution

## Next Phase Readiness
- Build workflow complete and working through --device flag
- Ready for Phase 3: Flash Orchestration (service safety, flash execution)
- Device registry, config caching, and build all functional

---
*Phase: 02-build-config-pipeline*
*Completed: 2026-01-25*
