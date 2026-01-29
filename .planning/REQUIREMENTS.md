# Requirements: v3.0 TUI Redesign & Flash All

**Defined:** 2026-01-29
**Core Value:** One command to build and flash any registered board — no remembering serial paths, flash commands, or config locations.

## v3.0 Requirements

### Theme & Rendering

- [x] **REND-01**: Truecolor RGB palette with 3-tier fallback (truecolor > ANSI 256 > ANSI 16)
- [x] **REND-02**: ANSI-aware string utilities (strip_ansi, display_width, pad_to_width)
- [ ] **REND-03**: Panel renderer with rounded borders (curved corners), configurable width
- [ ] **REND-04**: Two-column layout rendering within panels
- [ ] **REND-05**: Spaced letter panel headers (e.g. [ D E V I C E S ])
- [ ] **REND-06**: Step dividers (mid-grey partial-width with step labels)
- [x] **REND-07**: Terminal width detection and adaptive panel sizing

### TUI Layout

- [ ] **TUI-04**: Status panel at top showing last command result
- [ ] **TUI-05**: Device panel with devices grouped by status (Registered/New/Blocked)
- [ ] **TUI-06**: Numbered device references (#1, #2, #3) usable across actions
- [ ] **TUI-07**: Device rows showing name, truncated serial path, version, status icon
- [ ] **TUI-08**: Host Klipper version displayed in device panel footer
- [ ] **TUI-09**: Actions panel with two-column layout and bullets
- [ ] **TUI-10**: Screen refresh after every command completes (return to full menu)
- [ ] **TUI-11**: Refresh Devices action replaces List Devices
- [ ] **TUI-12**: Config screen as dedicated cleared screen with own status panel
- [ ] **TUI-13**: Config screen shows settings with numbered rows and current values
- [ ] **TUI-14**: Config screen refreshes after each setting change

### Flash All

- [ ] **FALL-01**: Flash All Registered Devices command in action menu
- [ ] **FALL-02**: Build all firmware first, then stop Klipper once, flash all, restart once
- [ ] **FALL-03**: Pre-flash version check — compare MCU versions to host version
- [ ] **FALL-04**: Prompt user if all MCU versions already match host (proceed or exit)
- [ ] **FALL-05**: Validate all devices have cached configs before starting
- [ ] **FALL-06**: Sequential flash with staggered output (configurable delay, default 1s)
- [ ] **FALL-07**: Continue-on-failure — if one device fails, continue to next
- [ ] **FALL-08**: Summary table after batch completion (device, status, version)
- [ ] **FALL-09**: Post-flash verification per device (reappears as Klipper)

### Config & Settings

- [ ] **CONF-01**: Skip menuconfig setting (default false) — auto-skip if valid cached config
- [ ] **CONF-02**: Stagger delay setting for Flash All (default 1s)
- [ ] **CONF-03**: Return delay setting — countdown before returning to menu (default 5s)
- [ ] **CONF-04**: Countdown with keypress cancel — any key skips timer, returns immediately
- [ ] **CONF-05**: Settings persisted in registry JSON (global section)

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
| REND-01 | Phase 10 | Pending |
| REND-02 | Phase 10 | Pending |
| REND-03 | Phase 11 | Pending |
| REND-04 | Phase 11 | Pending |
| REND-05 | Phase 11 | Pending |
| REND-06 | Phase 11 | Pending |
| REND-07 | Phase 10 | Pending |
| TUI-04 | Phase 12 | Pending |
| TUI-05 | Phase 12 | Pending |
| TUI-06 | Phase 12 | Pending |
| TUI-07 | Phase 12 | Pending |
| TUI-08 | Phase 12 | Pending |
| TUI-09 | Phase 12 | Pending |
| TUI-10 | Phase 12 | Pending |
| TUI-11 | Phase 12 | Pending |
| TUI-12 | Phase 13 | Pending |
| TUI-13 | Phase 13 | Pending |
| TUI-14 | Phase 13 | Pending |
| FALL-01 | Phase 14 | Pending |
| FALL-02 | Phase 14 | Pending |
| FALL-03 | Phase 14 | Pending |
| FALL-04 | Phase 14 | Pending |
| FALL-05 | Phase 14 | Pending |
| FALL-06 | Phase 14 | Pending |
| FALL-07 | Phase 14 | Pending |
| FALL-08 | Phase 14 | Pending |
| FALL-09 | Phase 14 | Pending |
| CONF-01 | Phase 13 | Pending |
| CONF-02 | Phase 13 | Pending |
| CONF-03 | Phase 13 | Pending |
| CONF-04 | Phase 13 | Pending |
| CONF-05 | Phase 13 | Pending |

**Coverage:**
- v3.0 requirements: 32 total
- Mapped to phases: 32
- Unmapped: 0

---
*Requirements defined: 2026-01-29*
*Last updated: 2026-01-29 after roadmap creation*
