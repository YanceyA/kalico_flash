# Roadmap: kalico-flash

## Milestones

- ✅ **v1.0 MVP** - Phases 1-3 (shipped 2026-01-25)
- ✅ **v2.0 Public Release** - Phases 4-7 (shipped 2026-01-27)
- ✅ **v2.1 TUI Color Theme** - Phases 8-9 (shipped 2026-01-29)
- ✅ **v3.0 TUI Redesign & Flash All** - Phases 10-14 (shipped 2026-01-30)
- ✅ **v3.1 Config Validation** - Phase 15 (shipped 2026-01-30)
- 🚧 **v3.2 Action Dividers** - Phases 16-17 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-3) - SHIPPED 2026-01-25</summary>

### Phase 1: Foundation
**Goal**: Device registry, USB discovery, config caching
**Plans**: 3 plans

Plans:
- [x] 01-01: Device registry with atomic JSON persistence
- [x] 01-02: USB discovery with pattern matching
- [x] 01-03: Config caching with MCU validation

### Phase 2: Build & Flash
**Goal**: Firmware build pipeline and dual-method flash
**Plans**: 3 plans

Plans:
- [x] 02-01: Build pipeline with menuconfig passthrough
- [x] 02-02: Service lifecycle context manager
- [x] 02-03: Dual-method flash (Katapult + make flash)

### Phase 3: CLI & Output
**Goal**: Command-line interface with structured output
**Plans**: 2 plans

Plans:
- [x] 03-01: CLI argument parsing and command routing
- [x] 03-02: Phase-labeled output with error formatting

</details>

<details>
<summary>✅ v2.0 Public Release (Phases 4-7) - SHIPPED 2026-01-27</summary>

### Phase 4: Interactive Menu
**Goal**: TUI menu with numbered options and setup wizard
**Plans**: 3 plans

Plans:
- [x] 04-01: TUI menu with Unicode/ASCII box drawing
- [x] 04-02: Setup wizard for first-run configuration
- [x] 04-03: Settings submenu for path configuration

### Phase 5: Safety & Verification
**Goal**: Print blocking and post-flash verification
**Plans**: 3 plans

Plans:
- [x] 05-01: Moonraker integration for print status
- [x] 05-02: Host vs MCU version comparison
- [x] 05-03: Post-flash verification polling

### Phase 6: Power User Features
**Goal**: Skip-menuconfig and device exclusion
**Plans**: 2 plans

Plans:
- [x] 06-01: Skip-menuconfig flag for cached configs
- [x] 06-02: Device exclusion for non-flashable devices

### Phase 7: Documentation & Deployment
**Goal**: Installation script and public documentation
**Plans**: 4 plans

Plans:
- [x] 07-01: Installation script (kflash command)
- [x] 07-02: README with Quick Start guide
- [x] 07-03: CLI Reference documentation
- [x] 07-04: Moonraker Update Manager integration

</details>

<details>
<summary>✅ v2.1 TUI Color Theme (Phases 8-9) - SHIPPED 2026-01-29</summary>

### Phase 8: Theme System
**Goal**: Semantic color theming with terminal detection
**Plans**: 1 plan

Plans:
- [x] 08-01: Theme module with capability detection

### Phase 9: Colored Output
**Goal**: Apply theme to all TUI elements
**Plans**: 2 plans

Plans:
- [x] 09-01: Colored messages and device markers
- [x] 09-02: Bold prompts and error headers

</details>

<details>
<summary>✅ v3.0 TUI Redesign & Flash All (Phases 10-14) - SHIPPED 2026-01-30</summary>

### Phase 10: Truecolor & ANSI Utilities
**Goal**: RGB palette with fallback and ANSI-aware string utils
**Plans**: 2 plans

Plans:
- [x] 10-01: Truecolor RGB palette with 3-tier fallback
- [x] 10-02: ANSI-aware string utilities

### Phase 11: Panel Renderer
**Goal**: Panel-based layout with rounded borders
**Plans**: 1 plan

Plans:
- [x] 11-01: Panel renderer with rounded borders

### Phase 12: Main Screen Redesign
**Goal**: Panel-based main screen with numbered devices
**Plans**: 3 plans

Plans:
- [x] 12-01: Status and devices panels
- [x] 12-02: Actions panel with numbered references
- [x] 12-03: Countdown timer with keypress cancel

### Phase 13: Config Screen
**Goal**: Settings screen with persistence
**Plans**: 1 plan

Plans:
- [x] 13-01: Config screen with type-dispatched editing

### Phase 14: Flash All
**Goal**: Batch flash with continue-on-failure
**Plans**: 1 plan

Plans:
- [x] 14-01: Flash All with build-then-flash architecture

</details>

<details>
<summary>✅ v3.1 Config Validation (Phase 15) - SHIPPED 2026-01-30</summary>

### Phase 15: Config Validation
**Goal**: Input validation for all TUI settings
**Plans**: 1 plan

Plans:
- [x] 15-01: Path and numeric validation with reject-and-reprompt

</details>

### 🚧 v3.2 Action Dividers (In Progress)

**Milestone Goal:** Add lightweight step dividers to all action workflows for visual separation between steps

#### Phase 16: Divider Implementation
**Goal**: Extend Output Protocol with divider rendering methods
**Depends on**: Phase 15
**Requirements**: OUT-01, OUT-02, OUT-03, OUT-04, OUT-05, OUT-06, TERM-01, TERM-02
**Success Criteria** (what must be TRUE):
  1. Output Protocol defines step_divider() and device_divider() methods
  2. CliOutput renders light dashed divider (┄) in muted teal border color
  3. CliOutput renders labeled device divider (─── 1/N DeviceName ───) in border color
  4. NullOutput implements both divider methods as no-ops
  5. Dividers adapt to terminal width (not hardcoded 80 chars)
  6. Dividers degrade to ASCII (---) on non-Unicode terminals
**Plans**: 1 plan

Plans:
- [x] 16-01: Add divider rendering pipeline and Output Protocol methods

#### Phase 17: Workflow Integration
**Goal**: Wire dividers into all command workflows
**Depends on**: Phase 16
**Requirements**: FLASH-01, FLASH-02, ADD-01, ADD-02, REM-01, BATCH-01, BATCH-02, BATCH-03
**Success Criteria** (what must be TRUE):
  1. Flash workflow shows step dividers between Discovery, Safety, Config, Build, Flash, Verify phases
  2. Add Device workflow shows step dividers before each prompt section
  3. Remove Device workflow shows step dividers before confirmation and result
  4. Flash All shows labeled device dividers between each device in build and flash phases
  5. Flash All shows step dividers between major stages (preflight, build, flash, summary)
  6. Dividers appear only between sections, never during countdown timers or inside errors
**Plans**: TBD

Plans:
- [ ] 17-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 16 → 17

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 3/3 | Complete | 2026-01-25 |
| 2. Build & Flash | v1.0 | 3/3 | Complete | 2026-01-25 |
| 3. CLI & Output | v1.0 | 2/2 | Complete | 2026-01-25 |
| 4. Interactive Menu | v2.0 | 3/3 | Complete | 2026-01-26 |
| 5. Safety & Verification | v2.0 | 3/3 | Complete | 2026-01-27 |
| 6. Power User Features | v2.0 | 2/2 | Complete | 2026-01-27 |
| 7. Documentation & Deployment | v2.0 | 4/4 | Complete | 2026-01-27 |
| 8. Theme System | v2.1 | 1/1 | Complete | 2026-01-29 |
| 9. Colored Output | v2.1 | 2/2 | Complete | 2026-01-29 |
| 10. Truecolor & ANSI Utilities | v3.0 | 2/2 | Complete | 2026-01-29 |
| 11. Panel Renderer | v3.0 | 1/1 | Complete | 2026-01-29 |
| 12. Main Screen Redesign | v3.0 | 3/3 | Complete | 2026-01-30 |
| 13. Config Screen | v3.0 | 1/1 | Complete | 2026-01-30 |
| 14. Flash All | v3.0 | 1/1 | Complete | 2026-01-30 |
| 15. Config Validation | v3.1 | 1/1 | Complete | 2026-01-30 |
| 16. Divider Implementation | v3.2 | 1/1 | Complete | 2026-01-30 |
| 17. Workflow Integration | v3.2 | 0/TBD | Not started | - |
