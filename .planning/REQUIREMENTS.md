# Requirements: kalico-flash v2.0

**Defined:** 2026-01-26
**Core Value:** One command to build and flash any registered board — no remembering serial paths, flash commands, or config locations.

## v2.0 Requirements

Requirements for public release. Each maps to roadmap phases.

### TUI Menu

- [ ] **TUI-01**: Running `kflash` with no args shows numbered main menu
- [ ] **TUI-02**: Menu options: Flash, List devices, Add device, Remove device, Settings, Exit
- [ ] **TUI-03**: After completing an action, return to main menu (not exit)
- [ ] **TUI-04**: Invalid input shows error and re-prompts (max 3 attempts)
- [ ] **TUI-05**: Exit on `0`, `q`, or Ctrl+C
- [ ] **TUI-06**: Non-TTY environments skip menu with helpful error
- [ ] **TUI-07**: Settings submenu: Change Klipper dir, Change Katapult dir, View settings
- [ ] **TUI-08**: Unicode box drawing with ASCII fallback for legacy terminals

### Safety Checks

- [ ] **SAFE-01**: Before stopping Klipper, query Moonraker for print status
- [ ] **SAFE-02**: Block flash if `print_stats.state` is `printing` or `paused`
- [ ] **SAFE-03**: Error message shows print filename and progress percentage
- [ ] **SAFE-04**: Allow flash if printer is idle, complete, cancelled, or error state
- [ ] **SAFE-05**: If Moonraker unreachable, warn and prompt user to confirm continue
- [ ] **SAFE-06**: Moonraker URL configurable in settings (default: localhost:7125)

### Post-Flash Verification

- [ ] **VERIFY-01**: After flash, wait for device to reappear in `/dev/serial/by-id/`
- [ ] **VERIFY-02**: Poll interval 500ms, timeout 15 seconds
- [ ] **VERIFY-03**: Confirm device has `Klipper_` prefix (not `katapult_`)
- [ ] **VERIFY-04**: Success message shows device path
- [ ] **VERIFY-05**: If timeout, show warning with numbered recovery steps
- [ ] **VERIFY-06**: Klipper still restarted even if verification fails

### Skip Menuconfig

- [ ] **SKIP-01**: `--skip-menuconfig` / `-s` flag skips TUI if cached config exists
- [ ] **SKIP-02**: Error with helpful message if no cached config
- [ ] **SKIP-03**: MCU validation still runs (prevents config/device mismatch)
- [ ] **SKIP-04**: Flag works with `--device KEY`
- [ ] **SKIP-05**: TUI menu offers skip option as y/n prompt before flash

### Error Messages

- [ ] **ERR-01**: All error paths include contextual recovery guidance
- [ ] **ERR-02**: Messages include specific diagnostic commands to copy/paste
- [ ] **ERR-03**: No generic "operation failed" without explanation
- [ ] **ERR-04**: Recovery steps are numbered and actionable
- [ ] **ERR-05**: Messages fit on standard 80-column terminal
- [ ] **ERR-06**: Error categories: Build, Device not found, Moonraker, MCU mismatch, Service control, Flash

### Version Detection

- [ ] **VER-01**: Show host Klipper version before flash (from git describe)
- [ ] **VER-02**: Show MCU firmware version before flash (from Moonraker API)
- [ ] **VER-03**: Indicate whether update is needed (commit count comparison)
- [ ] **VER-04**: Default prompt answer reflects recommendation (Y if outdated, N if current)
- [ ] **VER-05**: Gracefully handle unreachable Moonraker (skip check, warn user)
- [ ] **VER-06**: Gracefully handle unresponsive MCU (skip check, proceed)
- [ ] **VER-07**: Works with multiple MCUs (checks the one being flashed)

### Installation

- [ ] **INST-01**: `install.sh` creates working `kflash` symlink
- [ ] **INST-02**: Install works without sudo (uses ~/.local/bin)
- [ ] **INST-03**: Provides clear feedback on success
- [ ] **INST-04**: Warns if bin directory not in PATH
- [ ] **INST-05**: `uninstall.sh` cleanly removes symlink
- [ ] **INST-06**: Both scripts are idempotent (safe to run multiple times)

### Documentation

- [ ] **DOC-01**: README has clear installation instructions
- [ ] **DOC-02**: Quick start gets user from zero to first flash
- [ ] **DOC-03**: All CLI commands documented with examples
- [ ] **DOC-04**: Common errors have troubleshooting entries
- [ ] **DOC-05**: Update and uninstall instructions included
- [ ] **DOC-06**: Moonraker Update Manager integration example

### Device Exclusion

- [ ] **EXCL-01**: Registry supports `flashable: false` flag on devices
- [ ] **EXCL-02**: Non-flashable devices shown in `--list-devices` with indicator
- [ ] **EXCL-03**: Non-flashable devices excluded from flash device selection
- [ ] **EXCL-04**: `--add-device` wizard asks if device is flashable
- [ ] **EXCL-05**: Beacon probe can be registered as non-flashable

## Out of Scope

Explicitly excluded from v2.0. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Katapult first-time installation | Too many board variations, high brick risk |
| CAN bus device support | Different workflow, significant complexity |
| SHA256 config change detection | Nice optimization but not essential for v2.0 |
| Multi-device batch flash | Edge case, adds complexity |
| Moonraker plugin / web UI | Future enhancement, CLI is primary interface |
| Firmware rollback | Requires version tracking infrastructure |
| curses-based TUI | Adds complexity, Windows issues, print/input sufficient |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TUI-01 | Phase 6 | Pending |
| TUI-02 | Phase 6 | Pending |
| TUI-03 | Phase 6 | Pending |
| TUI-04 | Phase 6 | Pending |
| TUI-05 | Phase 6 | Pending |
| TUI-06 | Phase 6 | Pending |
| TUI-07 | Phase 6 | Pending |
| TUI-08 | Phase 6 | Pending |
| SAFE-01 | Phase 5 | Complete |
| SAFE-02 | Phase 5 | Complete |
| SAFE-03 | Phase 5 | Complete |
| SAFE-04 | Phase 5 | Complete |
| SAFE-05 | Phase 5 | Complete |
| SAFE-06 | Phase 5 | N/A (out of scope) |
| VERIFY-01 | Phase 6 | Pending |
| VERIFY-02 | Phase 6 | Pending |
| VERIFY-03 | Phase 6 | Pending |
| VERIFY-04 | Phase 6 | Pending |
| VERIFY-05 | Phase 6 | Pending |
| VERIFY-06 | Phase 6 | Pending |
| SKIP-01 | Phase 4 | Complete |
| SKIP-02 | Phase 4 | Complete |
| SKIP-03 | Phase 4 | Complete |
| SKIP-04 | Phase 4 | Complete |
| SKIP-05 | Phase 4 | Complete |
| ERR-01 | Phase 4 | Complete |
| ERR-02 | Phase 4 | Complete |
| ERR-03 | Phase 4 | Complete |
| ERR-04 | Phase 4 | Complete |
| ERR-05 | Phase 4 | Complete |
| ERR-06 | Phase 4 | Complete |
| VER-01 | Phase 5 | Complete |
| VER-02 | Phase 5 | Complete |
| VER-03 | Phase 5 | Complete |
| VER-04 | Phase 5 | N/A (informational only) |
| VER-05 | Phase 5 | Complete |
| VER-06 | Phase 5 | Complete |
| VER-07 | Phase 5 | Complete |
| INST-01 | Phase 7 | Pending |
| INST-02 | Phase 7 | Pending |
| INST-03 | Phase 7 | Pending |
| INST-04 | Phase 7 | Pending |
| INST-05 | Phase 7 | Pending |
| INST-06 | Phase 7 | Pending |
| DOC-01 | Phase 7 | Pending |
| DOC-02 | Phase 7 | Pending |
| DOC-03 | Phase 7 | Pending |
| DOC-04 | Phase 7 | Pending |
| DOC-05 | Phase 7 | Pending |
| DOC-06 | Phase 7 | Pending |
| EXCL-01 | Phase 4 | Complete |
| EXCL-02 | Phase 4 | Complete |
| EXCL-03 | Phase 4 | Complete |
| EXCL-04 | Phase 4 | Complete |
| EXCL-05 | Phase 4 | Complete |

**Coverage:**
- v2.0 requirements: 55 total
- Mapped to phases: 55
- Unmapped: 0

---
*Requirements defined: 2026-01-26*
*Last updated: 2026-01-27 after Phase 5 completion*
