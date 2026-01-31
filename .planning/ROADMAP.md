# Roadmap: kalico-flash

## Milestones

- ✅ **v1.0 MVP** - Phases 1-3 (shipped 2026-01-25)
- ✅ **v2.0 Public Release** - Phases 4-7 (shipped 2026-01-27)
- ✅ **v2.1 TUI Color Theme** - Phases 8-9 (shipped 2026-01-29)
- ✅ **v3.0 TUI Redesign & Flash All** - Phases 10-14 (shipped 2026-01-30)
- ✅ **v3.1 Config Validation** - Phase 15 (shipped 2026-01-30)
- ✅ **v3.2 Action Dividers** - Phases 16-17 (shipped 2026-01-31)
- ✅ **v3.3 Config Device** - Phases 18-20 (shipped 2026-01-31)
- ✅ **v3.4 Check Katapult** - Phases 21-23 (shipped 2026-01-31, feature parked)

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

<details>
<summary>✅ v3.2 Action Dividers (Phases 16-17) - SHIPPED 2026-01-31</summary>

#### Phase 16: Divider Implementation
**Goal**: Extend Output Protocol with divider rendering methods
**Depends on**: Phase 15
**Requirements**: OUT-01, OUT-02, OUT-03, OUT-04, OUT-05, OUT-06, TERM-01, TERM-02
**Success Criteria** (what must be TRUE):
  1. Output Protocol defines step_divider() and device_divider() methods
  2. CliOutput renders light dashed divider in muted teal border color
  3. CliOutput renders labeled device divider in border color
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
**Plans**: 2 plans

Plans:
- [x] 17-01: Add step dividers to cmd_flash, cmd_add_device, cmd_remove_device
- [x] 17-02: Add step and device dividers to cmd_flash_all

</details>

<details>
<summary>✅ v3.3 Config Device (Phases 18-20) - SHIPPED 2026-01-31</summary>

- [x] Phase 18: Foundation & Screen (2/2 plans) — completed 2026-01-31
- [x] Phase 19: Edit Interaction (1/1 plan) — completed 2026-01-31
- [x] Phase 20: Menu Integration (1/1 plan) — completed 2026-01-31

</details>

### v3.4 Check Katapult (Shipped 2026-01-31 — Feature Parked)

- [x] Phase 21: Pi Hardware Research (1/1 plans) — completed 2026-01-31
- [x] Phase 22: Core Detection Engine (1/1 plans) — completed 2026-01-31
- [x] Phase 23: TUI Integration (1/1 plans) — completed 2026-01-31

*Feature implemented and tested but parked — code retained in flasher.py, UI trigger removed. See milestones/v3.4-ROADMAP.md for details.*

### v4.0 Remove CLI & Internalize Device Keys (Planned)

**Milestone Goal:** Remove all CLI/argparse elements and make device keys auto-generated internal identifiers — the tool operates exclusively through TUI

#### Phase 24: Slug Generation
**Goal**: New devices get filesystem-safe keys auto-derived from display names
**Depends on**: Phase 23
**Requirements**: KEY-01, KEY-02
**Success Criteria** (what must be TRUE):
  1. `generate_device_key()` converts "Octopus Pro v1.1" to `octopus-pro-v1-1` (lowercase, hyphens, stripped edges)
  2. When a slug collides with an existing registry key, a numeric suffix is appended (`-2`, `-3`) until unique
  3. Edge cases handled: empty result after strip rejected, long names truncated to 64 chars, path-traversal characters stripped
**Plans**: TBD

Plans:
- [ ] 24-01: Add generate_device_key() to validation.py with slugification and collision handling

#### Phase 25: Key Internalization in TUI
**Goal**: Device keys are invisible internal identifiers — users interact only with display names
**Depends on**: Phase 24
**Requirements**: KEY-03, KEY-04, KEY-05, KEY-06
**Success Criteria** (what must be TRUE):
  1. Add-device wizard prompts only for display name — no key prompt, system generates key silently
  2. Device config screen has no key edit option (setting removed from DEVICE_SETTINGS)
  3. All user-facing output (device lists, flash messages, batch results) shows `entry.name` not `entry.key`
  4. Existing devices.json keys preserved exactly as-is — no re-derivation or migration on load
**Plans**: TBD

Plans:
- [ ] 25-01: Remove key prompt from add-device wizard, wire generate_device_key()
- [ ] 25-02: Remove key edit from device config screen, replace entry.key with entry.name in all output

#### Phase 26: Remove CLI
**Goal**: kflash launches directly into TUI with no argument parsing
**Depends on**: Phase 25
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04
**Success Criteria** (what must be TRUE):
  1. Running `kflash` with no arguments on a TTY launches the TUI menu directly
  2. Running `kflash --device X` or any old flag prints a friendly migration message and exits cleanly (no traceback)
  3. `build_parser()`, `_parse_args()`, and all argparse imports are deleted from flash.py
  4. Late-import branches that only existed for CLI code paths are removed
**Plans**: TBD

Plans:
- [ ] 26-01: Delete argparse, simplify main() to TUI launcher with migration message for old flags

#### Phase 27: Documentation & Cleanup
**Goal**: All docs and error messages reflect TUI-only operation
**Depends on**: Phase 26
**Requirements**: DOC-01, DOC-02, DOC-03, DOC-04
**Success Criteria** (what must be TRUE):
  1. README has no CLI reference section — documents TUI-only usage with kflash entry point
  2. CLAUDE.md CLI Commands section replaced with TUI Menu section
  3. Error recovery messages reference TUI actions ("Press F to flash") instead of CLI flags ("--device KEY")
  4. install.sh has no flag references (kflash symlink preserved)
**Plans**: TBD

Plans:
- [ ] 27-01: Update README, CLAUDE.md, install.sh for TUI-only operation
- [ ] 27-02: Audit and update error templates and recovery messages in errors.py

## Progress

**Execution Order:**
Phases execute in numeric order: 21 → 22 → 23 → 24 → 25 → 26 → 27

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
| 17. Workflow Integration | v3.2 | 2/2 | Complete | 2026-01-31 |
| 18. Foundation & Screen | v3.3 | 2/2 | Complete | 2026-01-31 |
| 19. Edit Interaction | v3.3 | 1/1 | Complete | 2026-01-31 |
| 20. Menu Integration | v3.3 | 1/1 | Complete | 2026-01-31 |
| 21. Pi Hardware Research | v3.4 | 1/1 | Complete (parked) | 2026-01-31 |
| 22. Core Detection Engine | v3.4 | 1/1 | Complete (parked) | 2026-01-31 |
| 23. TUI Integration | v3.4 | 1/1 | Complete (parked) | 2026-01-31 |
| 24. Slug Generation | v4.0 | 0/1 | Not started | - |
| 25. Key Internalization in TUI | v4.0 | 0/2 | Not started | - |
| 26. Remove CLI | v4.0 | 0/1 | Not started | - |
| 27. Documentation & Cleanup | v4.0 | 0/2 | Not started | - |
