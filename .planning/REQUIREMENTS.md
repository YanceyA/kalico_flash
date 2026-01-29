# Requirements: v3.0 TUI Redesign & Flash All

**Defined:** 2026-01-29
**Core Value:** One command to build and flash any registered board — no remembering serial paths, flash commands, or config locations.

## v3.0 Requirements

### Theme & Rendering

- [x] **REND-01**: Truecolor RGB palette with 3-tier fallback (truecolor > ANSI 256 > ANSI 16)
- [x] **REND-02**: ANSI-aware string utilities (strip_ansi, display_width, pad_to_width)
- [x] **REND-03**: Panel renderer with rounded borders (curved corners), configurable width
- [x] **REND-04**: Two-column layout rendering within panels
- [x] **REND-05**: Spaced letter panel headers (e.g. [ D E V I C E S ])
- [x] **REND-06**: Step dividers (mid-grey partial-width with step labels)
- [x] **REND-07**: Terminal width detection and adaptive panel sizing

### TUI Layout

- [x] **TUI-04**: Status panel at top showing last command result
- [x] **TUI-05**: Device panel with devices grouped by status (Registered/New/Blocked)
- [x] **TUI-06**: Numbered device references (#1, #2, #3) usable across actions
- [x] **TUI-07**: Device rows showing name, truncated serial path, version, status icon
- [x] **TUI-08**: Host Klipper version displayed in device panel footer
- [x] **TUI-09**: Actions panel with two-column layout and bullets
- [x] **TUI-10**: Screen refresh after every command completes (return to full menu)
- [x] **TUI-11**: Refresh Devices action replaces List Devices
- [x] **TUI-12**: Config screen as dedicated cleared screen with own status panel
- [x] **TUI-13**: Config screen shows settings with numbered rows and current values
- [x] **TUI-14**: Config screen refreshes after each setting change

### Flash All

- [x] **FALL-01**: Flash All Registered Devices command in action menu
- [x] **FALL-02**: Build all firmware first, then stop Klipper once, flash all, restart once
- [x] **FALL-03**: Pre-flash version check — compare MCU versions to host version
- [x] **FALL-04**: Prompt user if all MCU versions already match host (proceed or exit)
- [x] **FALL-05**: Validate all devices have cached configs before starting
- [x] **FALL-06**: Sequential flash with staggered output (configurable delay, default 1s)
- [x] **FALL-07**: Continue-on-failure — if one device fails, continue to next
- [x] **FALL-08**: Summary table after batch completion (device, status, version)
- [x] **FALL-09**: Post-flash verification per device (reappears as Klipper)

### Config & Settings

- [x] **CONF-01**: Skip menuconfig setting (default false) — auto-skip if valid cached config
- [x] **CONF-02**: Stagger delay setting for Flash All (default 1s)
- [x] **CONF-03**: Return delay setting — countdown before returning to menu (default 5s)
- [x] **CONF-04**: Countdown with keypress cancel — any key skips timer, returns immediately
- [x] **CONF-05**: Settings persisted in registry JSON (global section)

## Future Requirements

### Deferred

- **SHA256 change detection** — Skip rebuild when config unchanged
- **--no-clean flag** — Incremental builds
- **CAN bus support** — Different discovery mechanism

## Out of Scope

| Feature | Reason |
|---------|--------|
| Rich/Textual/curses dependency | Stdlib only constraint — pure ANSI codes |
| Real-time animated spinners | Would require threading/async, overkill for build output |
| Mouse support | SSH terminals vary, keyboard sufficient |
| Resizable panels during execution | Redraw on completion is sufficient |
| Per-device flash method override in Flash All | All devices use standard Katapult-first fallback |
| Parallel flash (multiple devices simultaneously) | USB serial is sequential, kernel locking issues |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| REND-01 | Phase 10 | Complete |
| REND-02 | Phase 10 | Complete |
| REND-03 | Phase 11 | Complete |
| REND-04 | Phase 11 | Complete |
| REND-05 | Phase 11 | Complete |
| REND-06 | Phase 11 | Complete |
| REND-07 | Phase 10 | Complete |
| TUI-04 | Phase 12 | Complete |
| TUI-05 | Phase 12 | Complete |
| TUI-06 | Phase 12 | Complete |
| TUI-07 | Phase 12 | Complete |
| TUI-08 | Phase 12 | Complete |
| TUI-09 | Phase 12 | Complete |
| TUI-10 | Phase 12 | Complete |
| TUI-11 | Phase 12 | Complete |
| TUI-12 | Phase 13 | Complete |
| TUI-13 | Phase 13 | Complete |
| TUI-14 | Phase 13 | Complete |
| FALL-01 | Phase 14 | Complete |
| FALL-02 | Phase 14 | Complete |
| FALL-03 | Phase 14 | Complete |
| FALL-04 | Phase 14 | Complete |
| FALL-05 | Phase 14 | Complete |
| FALL-06 | Phase 14 | Complete |
| FALL-07 | Phase 14 | Complete |
| FALL-08 | Phase 14 | Complete |
| FALL-09 | Phase 14 | Complete |
| CONF-01 | Phase 13 | Complete |
| CONF-02 | Phase 13 | Complete |
| CONF-03 | Phase 13 | Complete |
| CONF-04 | Phase 13 | Complete |
| CONF-05 | Phase 13 | Complete |

**Coverage:**
- v3.0 requirements: 32 total
- Mapped to phases: 32
- Unmapped: 0

---
*Requirements defined: 2026-01-29*
*Last updated: 2026-01-29 after Phase 14 completion*
