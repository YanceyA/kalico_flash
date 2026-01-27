---
phase: 07-release-polish
plan: 02
subsystem: documentation
tags: [readme, documentation, moonraker, update-manager]

dependency_graph:
  requires:
    - 07-01 # install.sh (referenced in README)
  provides:
    - Complete README.md for public release
    - CLI command reference
    - Moonraker Update Manager config
  affects:
    - Users following Quick Start
    - Moonraker dashboard update integration

tech_stack:
  added: []
  patterns:
    - README structure: Title > Quick Start > Features > CLI Reference > Installation > Updates > Uninstall

file_tracking:
  key_files:
    created: []
    modified:
      - README.md

decisions:
  - id: no-troubleshooting
    choice: "Skip troubleshooting section entirely"
    reason: "Inline error messages from Phase 4 error framework provide recovery steps"
    source: CONTEXT.md decision

metrics:
  duration: "2 minutes"
  completed: "2026-01-27"
---

# Phase 7 Plan 02: README Documentation Summary

Public-release README with Quick Start, CLI Reference, and Moonraker Update Manager integration.

## What Was Built

Rewrote README.md from 253 lines of development documentation to 244 lines of user-focused release documentation.

### Quick Start (4 steps)
1. Clone repository
2. Install (`./install.sh`)
3. Add device (`kflash --add-device`)
4. Flash (`kflash`)

Each step includes copy-paste commands and expected output.

### Features Section
Documented with examples:
- Interactive TUI Menu (shows actual menu output)
- Skip Menuconfig (`-s` flag usage)
- Device Exclusion (`--exclude-device`/`--include-device`)
- Print Safety (blocks during active prints)
- Version Display (host vs MCU versions)
- Post-Flash Verification (device reappearance check)

### CLI Reference Table
All 10 commands documented:

| Command | Description |
|---------|-------------|
| `kflash` | Interactive menu |
| `kflash -d KEY` | Flash specific device |
| `kflash -d KEY -s` | Flash, skip menuconfig |
| `kflash --add-device` | Register new device |
| `kflash --list-devices` | Show registered devices |
| `kflash --remove-device KEY` | Remove device |
| `kflash --exclude-device KEY` | Mark non-flashable |
| `kflash --include-device KEY` | Mark flashable |
| `kflash --version` | Show version |
| `kflash --help` | Show help |

### Moonraker Update Manager
Copy-paste ready snippet:

```ini
[update_manager kalico-flash]
type: git_repo
path: ~/kalico-flash
origin: https://github.com/USER/kalico-flash.git
primary_branch: master
is_system_service: False
```

### Uninstall Instructions
Clean removal with `./install.sh --uninstall`, plus manual cleanup commands for repo and config.

## Decisions Made

| Decision | Rationale | Affected Files |
|----------|-----------|----------------|
| No troubleshooting section | Error templates from Phase 4 provide inline recovery | README.md |
| USER as GitHub placeholder | User replaces with their fork URL | README.md |
| Features with examples | Shows real commands and output, not abstract descriptions | README.md |

## Deviations from Plan

None - plan executed exactly as written.

## Task Summary

| Task | Commits | Files Modified |
|------|---------|----------------|
| Rewrite README.md | 1be3dae | README.md |

## Success Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| DOC-01: Clear installation instructions | PASS | Installation section with steps |
| DOC-02: Quick start gets user to first flash | PASS | 4-step Quick Start |
| DOC-03: All CLI commands documented | PASS | 10-command table |
| DOC-04: Common errors have troubleshooting | PASS | Inline error messages (per CONTEXT.md) |
| DOC-05: Update and uninstall instructions | PASS | Sections present |
| DOC-06: Moonraker Update Manager example | PASS | Copy-paste snippet |

## Next Phase Readiness

**What comes next:** Plan 07-03 (arg parser and code cleanup)

**Blockers:** None

**Dependencies satisfied:** install.sh exists and is referenced correctly in README

---

*Plan completed: 2026-01-27*
