# Roadmap: kalico-flash v2.0

**Milestone:** v2.0 Public Release
**Created:** 2026-01-26
**Phases:** 4 (continuing from v1.0 phases 1-3)
**Requirements:** 55 total, 100% mapped

## Overview

v2.0 transforms kalico-flash from a working tool into a polished public release. The roadmap delivers safety checks (never flash during a print), verification (know the flash succeeded), and user experience improvements (interactive menu, better errors). All features gracefully degrade when optional services are unavailable.

Four phases move from foundation (skip-menuconfig, device exclusion, error messages) through Moonraker integration (print safety, version detection) to user experience (TUI menu, post-flash verification) and release polish (installation script, documentation).

---

## Phase 4: Foundation

**Goal:** Establish core infrastructure for power users and error handling

**Dependencies:** v1.0 complete (phases 1-3)

**Requirements:** SKIP-01, SKIP-02, SKIP-03, SKIP-04, SKIP-05, EXCL-01, EXCL-02, EXCL-03, EXCL-04, EXCL-05, ERR-01, ERR-02, ERR-03, ERR-04, ERR-05, ERR-06

**Plans:** 5 plans

Plans:
- [x] 04-01-PLAN.md — Error message framework with context and recovery guidance
- [x] 04-02-PLAN.md — Device exclusion schema with backward-compatible registry
- [x] 04-03-PLAN.md — Skip-menuconfig flag and device exclusion CLI commands
- [ ] 04-04-PLAN.md — [Gap closure] Integrate error framework into flash.py error paths
- [ ] 04-05-PLAN.md — [Gap closure] Update supporting modules with format_error()

**Success Criteria:**

1. User can run `kflash --device octopus-pro -s` and skip menuconfig when cached config exists
2. User sees helpful error with recovery steps when running `--skip-menuconfig` without cached config
3. User can register Beacon probe as non-flashable and it appears in list but not flash selection
4. User sees numbered recovery steps with copy-paste diagnostic commands on any error
5. All error messages fit on 80-column terminal and include context (device name, MCU type, path)

---

## Phase 5: Moonraker Integration

**Goal:** Users have safety checks and version awareness before flashing

**Dependencies:** Phase 4 (error messages for Moonraker failure scenarios)

**Requirements:** SAFE-01, SAFE-02, SAFE-03, SAFE-04, SAFE-05, SAFE-06, VER-01, VER-02, VER-03, VER-04, VER-05, VER-06, VER-07

**Success Criteria:**

1. User attempting to flash during active print sees "Print in progress: filename (45%)" and flash is blocked
2. User can flash when Moonraker reports idle, complete, cancelled, or error state
3. User sees warning and confirmation prompt when Moonraker is unreachable (not blocked)
4. User sees host Klipper version vs MCU firmware version before flash, with indication if update needed
5. User with multiple MCUs sees version info for the specific MCU being flashed

---

## Phase 6: User Experience

**Goal:** Interactive users have menu-driven workflow and flash verification

**Dependencies:** Phase 5 (Moonraker for print check), Phase 4 (error messages for verification failures)

**Requirements:** TUI-01, TUI-02, TUI-03, TUI-04, TUI-05, TUI-06, TUI-07, TUI-08, VERIFY-01, VERIFY-02, VERIFY-03, VERIFY-04, VERIFY-05, VERIFY-06

**Success Criteria:**

1. User running `kflash` with no args sees numbered menu: Flash, List devices, Add device, Remove device, Settings, Exit
2. User can navigate menu, complete actions, and return to menu (not exit) until choosing Exit
3. User receives confirmation message with device path after successful flash, or recovery steps if device does not reappear within 15 seconds
4. User sees box-drawn menu in UTF-8 terminals, clean ASCII menu over legacy SSH connections
5. User in non-TTY environment (piped input, cron) sees helpful error instead of broken menu

---

## Phase 7: Release Polish

**Goal:** New users can install and learn the tool from documentation

**Dependencies:** Phase 6 (all features complete for documentation)

**Requirements:** INST-01, INST-02, INST-03, INST-04, INST-05, INST-06, DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06

**Success Criteria:**

1. User can run `./install.sh` and have working `kflash` command without sudo
2. User sees clear feedback on install success, including warning if ~/.local/bin not in PATH
3. User following README quick start can go from git clone to first flash in under 5 minutes
4. User encountering common errors can find troubleshooting entry in README
5. User can configure Moonraker Update Manager to auto-update kalico-flash

---

## Progress

| Phase | Name | Requirements | Status |
|-------|------|--------------|--------|
| 4 | Foundation | 16 | In Progress (5 plans, 3 complete) |
| 5 | Moonraker Integration | 13 | Pending |
| 6 | User Experience | 14 | Pending |
| 7 | Release Polish | 12 | Pending |

**Total:** 55 requirements mapped, 0 complete

---

## Requirement Coverage

All 55 v2.0 requirements mapped to exactly one phase:

| Category | Phase | Requirements |
|----------|-------|--------------|
| Skip Menuconfig | 4 | SKIP-01 to SKIP-05 (5) |
| Device Exclusion | 4 | EXCL-01 to EXCL-05 (5) |
| Error Messages | 4 | ERR-01 to ERR-06 (6) |
| Safety Checks | 5 | SAFE-01 to SAFE-06 (6) |
| Version Detection | 5 | VER-01 to VER-07 (7) |
| TUI Menu | 6 | TUI-01 to TUI-08 (8) |
| Post-Flash Verification | 6 | VERIFY-01 to VERIFY-06 (6) |
| Installation | 7 | INST-01 to INST-06 (6) |
| Documentation | 7 | DOC-01 to DOC-06 (6) |

**Coverage:** 55/55 (100%)

---
*Roadmap created: 2026-01-26*
*Last updated: 2026-01-26*
