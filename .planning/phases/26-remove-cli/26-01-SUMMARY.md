---
phase: 26-remove-cli
plan: 01
subsystem: cli-entry-point
tags: [tui, argparse-removal, cleanup]
depends_on:
  requires: [25-key-internalization-in-tui]
  provides: [pure-tui-entry-point, simplified-error-recovery]
  affects: [27-final-cleanup]
tech-stack:
  added: []
  patterns: [tui-only-launcher]
key-files:
  created: []
  modified: [kflash/flash.py, kflash/errors.py, kflash/tui.py]
decisions:
  - id: d26-01-01
    description: "main() is a thin TTY check + run_menu() launcher with no arg parsing"
  - id: d26-01-02
    description: "All recovery text uses TUI hints (Press A/D/etc) instead of CLI flags"
metrics:
  duration: "~5 min"
  completed: 2026-02-01
---

# Phase 26 Plan 01: Remove CLI Infrastructure Summary

**One-liner:** Deleted argparse/CLI infrastructure from flash.py, making kflash a pure TUI application with no argument parsing.

## What Was Done

### Task 1: Delete CLI infrastructure and dead code from flash.py
- Deleted `import argparse` and `build_parser()` function (92-157)
- Deleted `cmd_exclude_device()` and `cmd_include_device()` (dead code since TUI uses registry.set_flashable() directly)
- Rewrote `main()` as a 26-line thin launcher: TTY check + run_menu()
- Removed `from_tui` parameter from `cmd_build()` and `cmd_flash()`
- Removed `from_menu` parameter from `cmd_list_devices()`
- Replaced all CLI-worded hints with TUI equivalents
- Updated module docstring to reflect TUI-only operation
- Removed `from_tui=True` kwarg from tui.py caller

### Task 2: Simplify recovery text in errors.py to TUI-only
- Merged `_TUI_RECOVERY_OVERRIDES` into base `ERROR_TEMPLATES`
- Deleted `_TUI_RECOVERY_OVERRIDES` dict
- Simplified `get_recovery_text()` to single-line return (no branching)
- Replaced CLI flag references (`--add-device`, `--include-device`, `--skip-menuconfig`) with TUI action hints

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| d26-01-01 | main() is thin TTY check + run_menu() | No CLI flags needed; TUI handles all interaction |
| d26-01-02 | Recovery text always uses TUI hints | No CLI exists; dual-path branching is dead code |

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 483429f | Remove CLI infrastructure and dead code from flash.py |
| 2 | f94d2f0 | Simplify recovery text in errors.py to TUI-only |

## Verification

- Module imports cleanly: `from kflash import flash` succeeds
- No "argparse" in flash.py
- No "from_tui" or "from_menu" in any kflash/*.py
- No "_TUI_RECOVERY_OVERRIDES" in errors.py
- main() is 26 lines (thin launcher)
- cmd_exclude_device and cmd_include_device deleted
