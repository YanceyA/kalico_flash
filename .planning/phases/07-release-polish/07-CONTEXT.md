# Phase 7: Release Polish - Context

**Gathered:** 2026-01-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver an installation script and documentation so new users can go from `git clone` to first flash. Covers `install.sh` for the `kflash` command, a README with quick start and CLI reference, and a Moonraker Update Manager config snippet. No new runtime features — this phase is purely installation and documentation.

</domain>

<decisions>
## Implementation Decisions

### Install script behavior
- Symlink approach: `install.sh` creates symlink from `~/.local/bin/kflash` to the repo's `flash.py`
- Symlink keeps `git pull` updates automatic — no re-install needed
- Prerequisite checks: verify Python 3.9+, Kalico directory, serial access — **warn** on missing prerequisites but still complete install
- PATH handling: if `~/.local/bin` not in PATH, **offer to add it** (ask user, append to `.bashrc` if yes)
- Uninstall support: `./install.sh --uninstall` removes symlink and any PATH additions
- No `install_script` in Update Manager config — symlink means git pull is sufficient

### README structure & tone
- Middle ground tone: brief context up front, then straight to commands — friendly but not chatty
- Quick Start as numbered steps: 1. Clone, 2. Install, 3. Add device, 4. Flash — linear walkthrough with expected output shown
- Feature overview section with examples: each feature (skip-menuconfig, device exclusion, Moonraker checks, TUI) with usage examples
- Full CLI reference table: every flag, description, and example — single source of truth for all options

### Troubleshooting content
- No troubleshooting section — the tool's inline error messages already provide recovery steps with diagnostic commands
- Skip entirely; error framework from Phase 4 handles this at runtime

### Update Manager config
- Copy-paste `moonraker.conf` snippet in README (not automated by install.sh)
- Update type: `git_repo` — standard for Klipper ecosystem tools
- Track `master` branch
- No `install_script` directive — symlink means git pull is the only update action needed

### Claude's Discretion
- Exact README section ordering beyond the agreed structure
- install.sh implementation details (color output, error handling)
- moonraker.conf snippet field ordering and comments
- Whether to include a LICENSE file or contributing guidelines

</decisions>

<specifics>
## Specific Ideas

- Install should feel like other Klipper ecosystem tools (KIAUH, Katapult) — familiar to the target audience
- README quick start should get a user from clone to first flash in under 5 minutes (per success criteria)
- Feature examples should show real commands with realistic output, not placeholder text

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-release-polish*
*Context gathered: 2026-01-27*
