# Phase 2: Build & Config Pipeline - Context

**Gathered:** 2026-01-25
**Status:** Ready for planning

<domain>
## Phase Boundary

User can configure firmware via menuconfig and build it, with per-device config caching and MCU validation preventing wrong-board firmware. Config is cached to XDG directory, menuconfig shows on every build, output streams in real-time, and MCU mismatches are hard-blocked.

</domain>

<decisions>
## Implementation Decisions

### Config caching behavior
- No cached config = force menuconfig (no skip option for first-time)
- Cache location: `~/.config/klipper-flash/{device-name}/.config` (XDG standard)
- If cached config is older than klipper/.config: warn with timestamps, prompt which to use
- `--reconfigure` flag deletes cached config and forces fresh menuconfig

### Menuconfig interaction
- Menuconfig shows automatically on every build (not skippable)
- Full ncurses TUI via `make menuconfig` — standard Klipper experience
- If user exits without saving: prompt "Continue with previous config?" (requires existing cache)
- Non-TTY terminal: fail with clear error "Menuconfig requires interactive terminal"

### Build output presentation
- Full streaming output — show all compiler lines as they happen
- Pass through raw make/gcc output with no modification or highlighting
- `make clean` runs before every build (always fresh, no incremental)
- Success summary: "Built klipper.bin (24.5 KB) in 45s at /path/to/klipper.bin"

### Validation & edge cases
- MCU type mismatch (config vs registry): hard block with clear message, no override
- Missing klipper directory: prompt user for correct path
- Build failure: show make output, exit with non-zero (no retry prompt)
- Klipper source path: global config only (same path for all devices)

### Claude's Discretion
- Exact XDG path resolution (XDG_CONFIG_HOME vs default)
- How to detect menuconfig save vs cancel
- Timestamp comparison logic for config staleness
- MCU type extraction from .config file format

</decisions>

<specifics>
## Specific Ideas

- Familiar workflow: menuconfig every time mirrors manual `cd klipper && make menuconfig && make` experience
- Always-clean builds avoid subtle incremental build bugs that plague Klipper firmware development
- Hard MCU validation prevents the common mistake of flashing wrong firmware to a board

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-build-config-pipeline*
*Context gathered: 2026-01-25*
