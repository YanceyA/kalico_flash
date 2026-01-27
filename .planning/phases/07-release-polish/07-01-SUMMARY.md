---
phase: 07-release-polish
plan: 01
subsystem: install
tags: [bash, symlink, xdg, path]

# Dependency graph
requires:
  - phase: 06-user-experience
    provides: Complete CLI with all commands working
provides:
  - install.sh script for user-facing installation
  - kflash command name in --help output
affects: [07-02-readme, 07-03-update-manager]

# Tech tracking
tech-stack:
  added: []
  patterns: [XDG-compliant ~/.local/bin, idempotent bash scripting]

key-files:
  created: [install.sh]
  modified: [kalico-flash/flash.py]

key-decisions:
  - "Symlink to flash.py rather than wrapper script for simplicity"
  - "Warn-only prerequisite checks (Python, ~/klipper, dialout) - don't block install"
  - "Don't remove PATH entry on uninstall - may affect other tools"

patterns-established:
  - "XDG ~/.local/bin for user executables"
  - "ln -sfn for idempotent symlink creation"

# Metrics
duration: 3min
completed: 2026-01-27
---

# Phase 7 Plan 1: Install Script Summary

**Bash install script with XDG-compliant symlink to ~/.local/bin/kflash and argparse prog name fix**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-27T09:14:05Z
- **Completed:** 2026-01-27T09:17:19Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created install.sh with idempotent symlink creation
- PATH detection with offer to add to ~/.bashrc
- --uninstall flag for clean removal
- Fixed argparse prog name so --help shows `kflash` not `flash.py`

## Task Commits

Each task was committed atomically:

1. **Task 1: Create install.sh with symlink and PATH handling** - `956e12c` (feat)
2. **Task 2: Update argparse prog name to kflash** - `1cbe355` (fix)

## Files Created/Modified

- `install.sh` - Installation script with symlink creation, PATH handling, uninstall support
- `kalico-flash/flash.py` - Changed `prog="flash.py"` to `prog="kflash"` in ArgumentParser

## Decisions Made

1. **Symlink over wrapper script** - Direct symlink to flash.py is simpler than a wrapper script; Python shebang handles execution correctly
2. **Warn-only prerequisite checks** - Script warns about Python 3.9+, missing ~/klipper, and dialout group membership but doesn't fail; user may be setting up on a fresh system
3. **Don't remove PATH on uninstall** - Per RESEARCH.md guidance, PATH entry may be used by other tools; only remove the symlink

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- **Windows line endings**: Tested script on Pi had CRLF endings causing `/usr/bin/env: 'bash\r'` error. Fixed with `sed -i 's/\r$//'`. This is a testing artifact, not a code issue - git will handle line ending conversion.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- install.sh ready for documentation in README (07-02)
- kflash command name ready for Moonraker Update Manager config (07-03)
- All success criteria met:
  - INST-01: install.sh creates working kflash symlink
  - INST-02: Install uses ~/.local/bin (no sudo)
  - INST-03: Clear feedback on success
  - INST-04: Warns if bin directory not in PATH
  - INST-05: --uninstall removes symlink
  - INST-06: Idempotent (safe to run multiple times)

---
*Phase: 07-release-polish*
*Completed: 2026-01-27*
