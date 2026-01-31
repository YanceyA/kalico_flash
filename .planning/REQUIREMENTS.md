# Requirements: v3.3 Config Device

**Defined:** 2026-01-31
**Core Value:** One command to build and flash any registered board — no remembering serial paths, flash commands, or config locations.

## v3.3 Requirements

### Menu Integration

- [ ] **MENU-01**: "Config device" appears as main menu action with "E" key
- [ ] **MENU-02**: Device selection prompt shows numbered list of registered devices (like Flash/Remove)

### Config Device Screen

- [ ] **CDEV-01**: Config screen shows device identity panel at top (MCU type, serial pattern — read-only)
- [ ] **CDEV-02**: Config screen shows editable fields panel with numbered options and current values
- [ ] **CDEV-03**: Screen uses same two-panel visual pattern as global config screen (separate TUI branch)

### Field Editing

- [ ] **EDIT-01**: User can edit display name (text input, reject empty)
- [ ] **EDIT-02**: User can edit device key (text input, validate uniqueness, validate format)
- [ ] **EDIT-03**: User can cycle flash method (default → katapult → make_flash)
- [ ] **EDIT-04**: User can toggle include/exclude status
- [ ] **EDIT-05**: User can launch make menuconfig for this device's cached config

### Key Rename

- [ ] **KEY-01**: Key rename validates new key is unique in registry
- [ ] **KEY-02**: Key rename migrates cached config directory to new key name
- [ ] **KEY-03**: Key rename uses atomic registry save (single save cycle, not delete+add)

### Persistence

- [ ] **SAVE-01**: All edits collected in memory, saved on screen exit (collect-then-save pattern)
- [ ] **SAVE-02**: Registry updated atomically (existing temp file + fsync + rename pattern)

### Visual Consistency

- [ ] **VIS-01**: Step dividers between sections in config device flow
- [ ] **VIS-02**: Screen follows Minimalist Zen aesthetic consistent with existing panels

## Future Requirements

### Deferred

- **Serial pattern editing** — Auto-generated from hardware, free-text editing breaks device matching
- **MCU editing** — Hardware-derived, not user-changeable

## Out of Scope

| Feature | Reason |
|---------|--------|
| MCU type editing | Hardware-derived, not a user property |
| Serial pattern free-text editing | Auto-generated glob, manual editing breaks matching silently |
| Key aliases after rename | Complexity for no benefit — old key stops working |
| Bulk device editing | Single device at a time is sufficient |
| CLI flag for config device | TUI-only action, consistent with config screen |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| MENU-01 | Phase 20 | Pending |
| MENU-02 | Phase 20 | Pending |
| CDEV-01 | Phase 18 | Complete |
| CDEV-02 | Phase 18 | Complete |
| CDEV-03 | Phase 18 | Complete |
| EDIT-01 | Phase 19 | Complete |
| EDIT-02 | Phase 19 | Complete |
| EDIT-03 | Phase 19 | Complete |
| EDIT-04 | Phase 19 | Complete |
| EDIT-05 | Phase 19 | Complete |
| KEY-01 | Phase 18 | Complete |
| KEY-02 | Phase 19 | Complete |
| KEY-03 | Phase 19 | Complete |
| SAVE-01 | Phase 19 | Complete |
| SAVE-02 | Phase 18 | Complete |
| VIS-01 | Phase 20 | Pending |
| VIS-02 | Phase 18 | Complete |

**Coverage:**
- v3.3 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0

---
*Requirements defined: 2026-01-31*
*Last updated: 2026-01-31 after roadmap creation*
