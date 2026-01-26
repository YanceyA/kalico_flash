---
phase: 04-foundation
plan: 05
subsystem: errors
tags: [error-handling, format_error, ERROR_TEMPLATES, gap-closure]

# Dependency graph
requires:
  - phase: 04-01
    provides: format_error(), ERROR_TEMPLATES dict
provides:
  - ServiceError raised with ERROR_TEMPLATES["service_stop_failed"]
  - ServiceError uses ERROR_TEMPLATES["service_start_failed"] for warnings
  - ConfigError raised with format_error() and recovery steps
  - DiscoveryError raised with format_error() and diagnostic commands
affects: [04-04 (flash.py error handling), 05-xx (Moonraker integration)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Template-based error messages: lookup from ERROR_TEMPLATES dict"
    - "Context + recovery pattern: all errors include path context and numbered recovery steps"

key-files:
  created: []
  modified:
    - kalico-flash/service.py
    - kalico-flash/config.py
    - kalico-flash/flasher.py

key-decisions:
  - "Use ERROR_TEMPLATES for service errors (already defined in 04-01)"
  - "Use inline format_error() calls for config/flasher errors (context varies)"
  - "Keep _start_klipper warning pattern (print not raise) but use format_error for consistency"

patterns-established:
  - "Error integration: import format_error + ERROR_TEMPLATES, use at all raise/warning sites"
  - "Recovery guidance: numbered steps for clear user action"

# Metrics
duration: 4min
completed: 2026-01-26
---

# Phase 04 Plan 05: Error Framework Integration into Supporting Modules Summary

**service.py, config.py, flasher.py now use format_error() and ERROR_TEMPLATES for consistent, informative error messages with recovery guidance**

## Performance

- **Duration:** 4 min
- **Started:** 2026-01-26
- **Completed:** 2026-01-26
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Updated service.py to use ERROR_TEMPLATES for all ServiceError raises and warnings
- Updated config.py to use format_error() for all 3 ConfigError raises
- Updated flasher.py to use format_error() for DiscoveryError raise
- All error messages now include context (path, stderr) and numbered recovery steps

## Task Commits

Each task was committed atomically:

1. **Task 1: Update service.py to use format_error() with ERROR_TEMPLATES** - `b87ea92` (feat)
2. **Task 2: Update config.py to use format_error() for ConfigError** - `a977163` (feat)
3. **Task 3: Update flasher.py to use format_error() for DiscoveryError** - `11752eb` (feat)

## Files Modified

| File | Changes |
|------|---------|
| `kalico-flash/service.py` | Import format_error + ERROR_TEMPLATES; 2 raise sites + 3 warning sites use templates |
| `kalico-flash/config.py` | Import format_error; 3 ConfigError raises use format_error with path context |
| `kalico-flash/flasher.py` | Import format_error; 1 DiscoveryError raise uses format_error with device path |

## Decisions Made
- Used ERROR_TEMPLATES lookup for service.py (templates already exist from 04-01)
- Used inline format_error() calls for config.py and flasher.py (error context varies per call site)
- Preserved _start_klipper's warning-not-raise pattern but made output consistent

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## Verification Results

- All 3 modules import without Python syntax errors
- service.py: 6 references to ERROR_TEMPLATES (1 import + 5 uses)
- config.py: 4 references to format_error (1 import + 3 uses)
- flasher.py: 2 references to format_error (1 import + 1 use)

## Next Phase Readiness
- Error framework now integrated into all supporting modules
- Ready for Phase 04-04 (flash.py error integration) if not already done
- All exception raises provide consistent, informative output with recovery guidance

---
*Phase: 04-foundation*
*Completed: 2026-01-26*
