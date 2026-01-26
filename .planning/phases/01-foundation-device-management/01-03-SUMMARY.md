---
phase: 01-foundation-device-management
plan: 03
subsystem: cli-discovery
tags: [python, discovery, cli, usb, status, cross-reference]

# Dependency graph
requires:
  - 01-01 (errors.py, models.py, output.py, registry.py, discovery.py)
  - 01-02 (flash.py CLI scaffold, add-device wizard)
provides:
  - --list-devices with live USB discovery integration
  - Connection status display ([OK], [--], [??] markers)
  - Unknown device detection with registration prompts
  - --device flag validation (RGST-05)
  - --version flag
  - Config cleanup on device removal
affects: [02-build-pipeline, 03-flash-orchestration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cross-reference registry against live USB scan"
    - "Status markers: [OK] connected, [--] disconnected, [??] unknown"
    - "First-run UX with helpful prompts for empty registry"
    - "Graceful handling of missing /dev/serial/by-id/ on non-Linux"

key-files:
  created: []
  modified:
    - klipper-flash/flash.py

key-decisions:
  - "--device flag validates device exists in registry before flash workflow (not yet implemented)"
  - "Config cleanup on remove-device is optional (prompted, defaults to 'no')"
  - "Unknown USB devices shown at end of list with registration suggestion"

patterns-established:
  - "Read-only operations return 0 even when registry empty"
  - "Module docstring documents architecture and usage examples"
  - "VERSION constant at module level for --version flag"

# Metrics
duration: 5min
completed: 2026-01-25
---

# Phase 1 Plan 3: List-Devices with Discovery Integration Summary

**Complete --list-devices command with USB discovery cross-referencing, connection status markers, unknown device flagging, and CLI polish for Phase 1 completion**

## Performance

- **Duration:** 5 min
- **Started:** 2026-01-25T19:15:00Z
- **Completed:** 2026-01-25T19:20:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Implemented `cmd_list_devices` with full discovery integration:
  - Loads registry and scans /dev/serial/by-id/
  - Cross-references using `find_registered_devices`
  - Shows [OK] with device path for connected boards
  - Shows [--] (disconnected) for registered but absent boards
  - Shows [??] Unknown for unregistered USB devices
  - First-run UX when no registered devices but USB devices exist
  - Graceful handling when no devices at all

- Added CLI polish:
  - `--version` flag showing "klipper-flash v0.1.0"
  - `--device` flag validation (RGST-05): error if device not in registry
  - Optional config cleanup in `--remove-device`
  - Expanded module docstring with usage examples
  - Epilog in help text describing available commands

## Task Commits

Each task was committed atomically:

1. **Task 1: List-devices with discovery integration** - `6348576` (feat)
2. **Task 2: CLI polish and edge cases** - `dd1442a` (feat)

## Files Modified

- `klipper-flash/flash.py`:
  - `cmd_list_devices()` - Full implementation with discovery integration
  - `cmd_remove_device()` - Added optional config file cleanup
  - `build_parser()` - Added --version, improved epilog
  - `main()` - Added --device validation with helpful error
  - Module docstring expanded with architecture documentation

## Phase 1 Requirements Verification

All 14 requirements verified:

| ID | Requirement | Status |
|----|-------------|--------|
| ARCH-01 | No sys.exit() in library modules | PASS |
| ARCH-02 | flash.py is thin wrapper | PASS |
| ARCH-03 | No print() except output.py | PASS |
| ARCH-04 | Hub-and-spoke (registry/discovery independent) | PASS |
| ARCH-05 | Cross-module data via dataclasses | PASS |
| ARCH-06 | No external dependencies | PASS |
| RGST-01 | devices.json with global+devices schema | PASS |
| RGST-02 | --add-device wizard | PASS |
| RGST-03 | --remove-device with confirmation | PASS |
| RGST-04 | --list-devices shows all with status | PASS |
| RGST-05 | --device validates existence | PASS |
| DISC-01 | scan_serial_devices + fnmatch | PASS |
| DISC-02 | Connected show name, unregistered show Unknown | PASS |
| DISC-03 | Unknown flagged with [??] | PASS |
| DISC-04 | Connection status [OK]/[--] | PASS |

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all verification tests passed. Note: USB device scanning returns empty list on Windows dev machine (expected - /dev/serial/by-id/ is Linux-specific).

## Final File Structure

```
klipper-flash/
  flash.py       # CLI entry point (320 lines)
  errors.py      # Exception hierarchy
  models.py      # Dataclass contracts
  output.py      # Pluggable output interface
  registry.py    # JSON persistence
  discovery.py   # USB scanning
```

## Next Phase Readiness

Phase 1 (Foundation & Device Management) is complete. All management commands functional:
- `--add-device` - Interactive registration wizard
- `--list-devices` - Status display with discovery
- `--remove-device` - Confirmed removal with config cleanup
- `--device` - Validates existence, ready for flash workflow

Ready for Phase 2 (Build Pipeline):
- Config caching
- Kconfig extraction
- make menuconfig automation
- Build orchestration

---
*Phase: 01-foundation-device-management*
*Completed: 2026-01-25*
