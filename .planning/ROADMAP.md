# Roadmap: v3.0 TUI Redesign & Flash All

## Overview

Redesign the TUI with panel-based layout using truecolor theming, ANSI-aware rendering utilities, and bordered panels, then add a batch Flash All command. Phases build bottom-up: rendering primitives, panel module, TUI integration, config screen, and finally batch flash orchestration.

## Phases

- [x] **Phase 10: Rendering Foundation** - Truecolor theme upgrade, ANSI string utilities, terminal width detection
- [x] **Phase 11: Panel Renderer** - Panel module with bordered panels, two-column layout, step dividers
- [x] **Phase 12: TUI Main Screen** - Panel-based main screen with status, devices, and actions panels
- [x] **Phase 13: Config Screen & Settings** - Dedicated config screen with settings persistence and countdown timer
- [x] **Phase 14: Flash All** - Batch flash command with build-then-flash architecture

## Phase Details

### Phase 10: Rendering Foundation
**Goal**: ANSI-aware string utilities and truecolor theme provide the rendering primitives all panels depend on
**Depends on**: Phase 9 (v2.1 theme module exists)
**Requirements**: REND-01, REND-02, REND-07
**Success Criteria** (what must be TRUE):
  1. Theme detects terminal color capability and selects truecolor, 256-color, or ANSI 16 palette automatically
  2. `strip_ansi()` removes all escape sequences; `display_width()` returns visible character count; `pad_to_width()` pads to exact visible width regardless of embedded ANSI codes
  3. Terminal width is detected at render time and available to downstream panel code
**Plans:** 1 plan
Plans:
- [x] 10-01-PLAN.md — Truecolor theme upgrade + ANSI string utilities

### Phase 11: Panel Renderer
**Goal**: Pure rendering module produces bordered panels with consistent alignment, ready for TUI integration
**Depends on**: Phase 10
**Requirements**: REND-03, REND-04, REND-05, REND-06
**Success Criteria** (what must be TRUE):
  1. `render_*_panel()` functions return multi-line strings with rounded Unicode borders (curved corners) that align correctly with colored content
  2. Two-column layout renders within panels with even spacing
  3. Panel headers display spaced letters (e.g. `[ D E V I C E S ]`) centered in top border
  4. Step dividers render as mid-grey partial-width lines with step labels
**Plans:** 1 plan
Plans:
- [x] 11-01-PLAN.md — Create panels.py with render_panel, render_two_column, render_step_divider, center_panel

### Phase 12: TUI Main Screen
**Goal**: Users see a panel-based main screen with live device status and can navigate all actions
**Depends on**: Phase 11
**Requirements**: TUI-04, TUI-05, TUI-06, TUI-07, TUI-08, TUI-09, TUI-10, TUI-11
**Success Criteria** (what must be TRUE):
  1. Main screen shows Status panel (last command result), Device panel (grouped by Registered/New/Blocked), and Actions panel (two-column with bullets)
  2. Devices are numbered (#1, #2, #3) and numbers are usable for device selection across actions
  3. Each device row shows name, truncated serial path, version, and status icon; host Klipper version appears in device panel footer
  4. Screen refreshes after every command completes, returning user to full panel menu
  5. Refresh Devices action replaces List Devices in action menu
**Plans:** 2 plans
Plans:
- [x] 12-01-PLAN.md — Screen data model, device aggregation, and panel rendering
- [x] 12-02-PLAN.md — Wire panel screen into interactive TUI loop with keypress input

### Phase 13: Config Screen & Settings
**Goal**: Users can view and change settings through a dedicated config screen, with all settings persisted and a countdown timer for post-command return
**Depends on**: Phase 11 (panel renderer for config screen layout)
**Requirements**: TUI-12, TUI-13, TUI-14, CONF-01, CONF-02, CONF-03, CONF-04, CONF-05
**Success Criteria** (what must be TRUE):
  1. Config screen renders as its own cleared screen with status panel and numbered settings rows showing current values
  2. User can toggle skip-menuconfig, set stagger delay, and set return delay; screen refreshes after each change
  3. All settings persist in registry JSON global section and survive tool restart
  4. After any command completes, a configurable countdown displays before returning to menu; any keypress skips the countdown immediately
**Plans:** 2 plans
Plans:
- [x] 13-01-PLAN.md — GlobalConfig extension, config screen rendering and interaction
- [x] 13-02-PLAN.md — Countdown timer with keypress cancel, wired into action dispatch

### Phase 14: Flash All
**Goal**: Users can flash all registered devices in one command with minimal Klipper downtime
**Depends on**: Phase 12 (TUI integration for menu entry), Phase 13 (skip-menuconfig and stagger delay settings)
**Requirements**: FALL-01, FALL-02, FALL-03, FALL-04, FALL-05, FALL-06, FALL-07, FALL-08, FALL-09
**Success Criteria** (what must be TRUE):
  1. Flash All appears in action menu and builds all firmware first (Klipper running), then stops Klipper once, flashes all devices sequentially, restarts once
  2. Before flashing, version check compares all MCU versions to host; if all match, user is prompted to proceed or exit
  3. All devices must have cached configs before batch starts; flash proceeds with configurable stagger delay between devices
  4. If one device fails, remaining devices still flash; a summary table shows device name, status, and version after batch completes
  5. Each device is verified post-flash (reappears as Klipper serial device)
**Plans:** 2 plans
Plans:
- [x] 14-01-PLAN.md — Core orchestration: BatchDeviceResult, quiet builds, cmd_flash_all()
- [x] 14-02-PLAN.md — Wire Flash All into TUI dispatch

## Progress

**Execution Order:** 10 > 11 > 12 > 13 > 14

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 10. Rendering Foundation | 1/1 | ✓ Complete | 2026-01-29 |
| 11. Panel Renderer | 1/1 | ✓ Complete | 2026-01-29 |
| 12. TUI Main Screen | 2/2 | ✓ Complete | 2026-01-29 |
| 13. Config Screen & Settings | 2/2 | ✓ Complete | 2026-01-29 |
| 14. Flash All | 2/2 | ✓ Complete | 2026-01-29 |
