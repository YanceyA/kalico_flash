# Phase 27 Plan 01: Documentation Cleanup Summary

**One-liner:** Rewrote README, CLAUDE.md, and install.sh to reflect TUI-only operation with zero CLI references

## Completed Tasks

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Rewrite README.md for TUI-only operation | 26cd64d | README.md |
| 2 | Rewrite CLAUDE.md for TUI architecture | 61a6b27 | CLAUDE.md |
| 3 | Update install.sh post-install message | 74f1c77 | install.sh |

## What Was Done

- **README.md**: Removed CLI Reference table, Skip Menuconfig section, all flag examples. Replaced Quick Start with single `kflash` command. Documented TUI actions. Updated Device Exclusion to reference Config Device screen. Changed all CLI references to TUI.
- **CLAUDE.md**: Replaced CLI Commands with TUI Menu section. Updated Repository Structure to match actual 18 files in kflash/ package. Described tui.py dispatch architecture. Removed Future Plans section. Updated Out of Scope (removed implemented features like batch flash, added TUI label).
- **install.sh**: Changed post-install message from "Run 'kflash --help' to get started" to "Run 'kflash' to start".

## Deviations from Plan

None -- plan executed exactly as written.

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Used `--` for em-dashes in markdown | Consistent with existing style, no ambiguity with CLI flags since none remain |

## Metrics

- **Duration:** ~3 minutes
- **Completed:** 2026-02-01
- **Tasks:** 3/3
