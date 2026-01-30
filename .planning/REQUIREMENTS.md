# Requirements: v3.2 Action Dividers

**Defined:** 2026-01-30
**Core Value:** One command to build and flash any registered board — no remembering serial paths, flash commands, or config locations.

## v3.2 Requirements

### Output Protocol

- [x] **OUT-01**: Output Protocol extended with `step_divider()` method for plain dividers
- [x] **OUT-02**: Output Protocol extended with `device_divider(index, total, name)` method for labeled batch dividers
- [x] **OUT-03**: CliOutput renders step divider as `┄` line in panel border color (muted teal #64A0B4)
- [x] **OUT-04**: CliOutput renders device divider as `─── 1/N DeviceName ───` centered label in border color
- [x] **OUT-05**: NullOutput implements both divider methods as no-ops
- [x] **OUT-06**: ASCII fallback uses `---` when terminal does not support Unicode

### Flash Workflow

- [x] **FLASH-01**: cmd_flash() shows step divider between major phases (Discovery, Safety, Config, Build, Flash, Verify)
- [x] **FLASH-02**: Step dividers appear before each phase transition, not within phases

### Add Device Workflow

- [x] **ADD-01**: cmd_add_device() shows step divider before each prompt/section (device selection, global setup, device key, display name, MCU confirm, flash method, exclusion, final confirmation)
- [x] **ADD-02**: Step dividers match mockup placement from dividers.txt

### Remove Device Workflow

- [x] **REM-01**: cmd_remove_device() shows step divider before confirmation prompt and before result

### Flash All Workflow

- [x] **BATCH-01**: cmd_flash_all() shows labeled device divider `─── 1/N DeviceName ───` between each device during build phase
- [x] **BATCH-02**: cmd_flash_all() shows labeled device divider between each device during flash phase
- [x] **BATCH-03**: Step dividers used between major stages (preflight, build, flash, summary)

### Terminal Compatibility

- [x] **TERM-01**: Divider width adapts to terminal width (not hardcoded)
- [x] **TERM-02**: Dividers degrade to ASCII `---` on terminals without Unicode support

## Future Requirements

### Deferred

- **Contextual divider labels** — Show phase name or step description inside step dividers (e.g., `┄┄┄ Build ┄┄┄`)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Dividers inside error messages | Errors have their own formatting via format_error() |
| Dividers during countdown timer | Timer has its own visual pattern |
| Animated or fancy dividers | Conflicts with lightweight, non-intrusive goal |
| Dividers in --list-devices output | Not an action workflow, just a display command |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| OUT-01 | Phase 16 | Complete |
| OUT-02 | Phase 16 | Complete |
| OUT-03 | Phase 16 | Complete |
| OUT-04 | Phase 16 | Complete |
| OUT-05 | Phase 16 | Complete |
| OUT-06 | Phase 16 | Complete |
| TERM-01 | Phase 16 | Complete |
| TERM-02 | Phase 16 | Complete |
| FLASH-01 | Phase 17 | Complete |
| FLASH-02 | Phase 17 | Complete |
| ADD-01 | Phase 17 | Complete |
| ADD-02 | Phase 17 | Complete |
| REM-01 | Phase 17 | Complete |
| BATCH-01 | Phase 17 | Complete |
| BATCH-02 | Phase 17 | Complete |
| BATCH-03 | Phase 17 | Complete |

**Coverage:**
- v3.2 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0 ✓

---
*Requirements defined: 2026-01-30*
*Last updated: 2026-01-30 after roadmap creation*
