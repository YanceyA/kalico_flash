# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-29)

**Core value:** One command to build and flash any registered board — no remembering serial paths, flash commands, or config locations.
**Current focus:** v3.0 TUI Redesign & Flash All

## Current Position

Milestone: v3.0 TUI Redesign & Flash All
Phase: Not started (defining requirements)
Plan: —
Status: **Defining requirements**
Last activity: 2026-01-29 — Milestone v3.0 started

## v3.0 Roadmap

(Pending — roadmap creation in progress)

## Accumulated Decisions

| Phase | Decision | Rationale |
|-------|----------|-----------|
| — | Truecolor RGB with ANSI 16 fallback | Modern palette from mockups, graceful degradation |
| — | Flash All: stop klipper once | Faster than per-device restart cycle |
| — | Truncated serial path in device panel | Recognizable, fits panel width |
| — | Show existing config settings + new delays | No new directory settings, add skip_menuconfig + timing |
| — | Stdlib only maintained | Pure ANSI codes, no Rich/Textual dependency |

## Shipped Milestones

| Version | Name | Phases | Shipped |
|---------|------|--------|---------|
| v1.0 | MVP | 1-3 | 2026-01-25 |
| v2.0 | Public Release | 4-7 | 2026-01-27 |
| v2.1 | TUI Color Theme | 8-9 | 2026-01-29 |

See: .planning/MILESTONES.md for full history

## Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 001 | Add version match confirmation dialog | 2026-01-28 | 446821f | [001-version-match-confirmation](./quick/001-version-match-confirmation/) |
| 002 | Display MCU versions in list/flash menus | 2026-01-28 | 173141b | [002-mcu-version-display](./quick/002-mcu-version-display/) |

## Session Continuity

Last session: 2026-01-29
Stopped at: Milestone initialization
Resume file: None
Next step: Define requirements and create roadmap

---
*Last updated: 2026-01-29 after v3.0 milestone start*
