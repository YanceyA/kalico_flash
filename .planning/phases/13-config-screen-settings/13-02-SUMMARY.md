---
phase: 13-config-screen-settings
plan: 02
subsystem: tui-countdown
tags: [tui, countdown, keypress, cross-platform]
depends_on:
  requires: [13-01-config-screen]
  provides: [countdown-timer, keypress-wait]
  affects: [14-flash-all]
tech-stack:
  added: []
  patterns: [platform-branching-for-input, select-based-timeout]
key-files:
  created: []
  modified: [kflash/tui.py]
decisions:
  - id: 13-02-01
    decision: "Countdown only after flash/add/remove, not after refresh/config/quit"
    rationale: "Only destructive or lengthy actions need output review time"
metrics:
  duration: "2 min"
  completed: "2026-01-29"
---

# Phase 13 Plan 02: Countdown Timer Summary

**One-liner:** Cross-platform countdown timer using select (Unix) / msvcrt (Windows) polling, wired into post-action dispatch for flash/add/remove commands.

## What Was Done

### Task 1: Countdown timer with cross-platform keypress detection
- Added `_wait_for_key(timeout)` with platform branching: `msvcrt.kbhit()` on Windows, `select.select()` on Unix with termios raw mode
- Added `_countdown_return(seconds)` that displays decremental countdown with theme styling, skippable by any keypress
- Wired countdown into flash, add-device, and remove-device action handlers using `registry.load().global_config.return_delay`
- No countdown after refresh (`d`), config screen (`c`), or quit (`q`)

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| cd98bd1 | feat | Countdown timer with cross-platform keypress cancellation |

## Next Phase Readiness

Phase 13 complete. Ready for Phase 14 (Flash All).
