---
phase: 15-config-validation
plan: 01
subsystem: tui-settings
tags: [validation, input-handling, tui]
dependency-graph:
  requires: [13-01]
  provides: [settings-input-validation]
  affects: []
tech-stack:
  added: []
  patterns: [validation-loop-with-reprompt, pure-validator-functions]
key-files:
  created: [kflash/validation.py]
  modified: [kflash/tui.py, kflash/screen.py]
decisions:
  - id: 15-01-A
    description: "Late import of validators inside branches"
    rationale: "Consistent with existing lazy-import pattern in tui.py"
metrics:
  duration: "~3 min"
  completed: 2026-01-30
---

# Phase 15 Plan 01: Config Validation Summary

**One-liner:** Pure validator functions for path existence/file checks and numeric range enforcement, wired into TUI settings edit with re-prompt loops.

## What Was Done

### Task 1: Create validation.py with pure validator functions
- `validate_numeric_setting()`: parses float, checks min/max range, returns (ok, value, error)
- `validate_path_setting()`: expands tilde, checks dir exists, checks expected files per setting key (Makefile for klipper_dir, scripts/flashtool.py for katapult_dir)
- **Commit:** e2116ab

### Task 2: Wire validation into TUI settings edit flow
- Replaced one-shot input with `while True` validation loops for numeric and path settings
- Added `min`/`max` keys to SETTINGS definitions in screen.py (stagger_delay: 0-30, return_delay: 0-60)
- Invalid input prints themed error message and re-prompts
- Empty input or Ctrl+C breaks loop without saving (cancel behavior)
- Path settings store original user input (with tilde), not expanded path
- **Commit:** 1630889

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| 15-01-A | Late import of validators inside branches | Consistent with existing lazy-import pattern in tui.py |

## Verification

All requirements satisfied:
- PATH-01 through PATH-07: Invalid paths rejected with specific error messages, re-prompted
- NUM-01 through NUM-03: Out-of-range and non-numeric values rejected, re-prompted
- Empty input cancels gracefully
- Tilde expanded for validation, stored as-is
