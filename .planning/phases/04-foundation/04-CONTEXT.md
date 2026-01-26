# Phase 4: Foundation - Context

**Gathered:** 2026-01-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Core infrastructure for power users: skip-menuconfig workflow (bypass menuconfig when cached config exists), device exclusion (mark devices as non-flashable), and standardized error messages with recovery guidance. No TUI menu, no Moonraker integration, no new commands beyond what's specified.

</domain>

<decisions>
## Implementation Decisions

### Skip flag behavior
- `--skip-menuconfig` / `-s` flag to bypass menuconfig when cached config exists
- If no cached config exists: warn that cache is missing, then launch menuconfig anyway (not hard error)
- No auto-skip mode — always show menuconfig unless user explicitly passes the flag
- Brief confirmation on success: one line like "Using cached config for octopus-pro"
- Always validate cached config MCU type matches registered device — error if mismatch (prevents flashing wrong firmware)

### Device exclusion UX
- Two entry points: ask during `--add-device` wizard ("Is this device flashable?" default Yes) AND provide commands to change later
- Two separate commands: `--exclude-device <key>` and `--include-device <key>` to toggle status
- In `--list-devices` output: excluded devices shown alongside flashable ones with "[excluded]" marker
- Explicit flash attempt on excluded device: hard error and exit, no override option
- Interactive selection menu: excluded devices shown but disabled (greyed out / with note, cannot be selected)

### Error message format
- Plain ASCII only — no Unicode box-drawing characters (maximum compatibility)
- No color — plain text only, no ANSI escape codes
- Recovery steps as numbered lists (1., 2., 3.) per ERR-04 requirement
- Diagnostic commands included inline as copy-paste snippets (e.g., "Run `ls /dev/serial/by-id/` to see connected devices")
- All error messages must fit 80-column terminal and include context (device name, MCU type, path)

### CLI flag design
- Short flags for common operations: `-s` for `--skip-menuconfig`, `-d` for `--device`, etc.
- Kebab-case for multi-word flags: `--skip-menuconfig`, `--add-device`, `--list-devices`
- Standard verbosity for `--help`: flag names, descriptions, and default values (no inline examples)
- Two separate flags for exclusion toggling: `--exclude-device` and `--include-device`

### Claude's Discretion
- Exact wording of error messages and recovery prose
- Which flags get short aliases beyond the core ones discussed
- Internal implementation of MCU validation logic
- Help text phrasing and ordering

</decisions>

<specifics>
## Specific Ideas

- Error messages should feel conversational and helpful, not robotic
- "Using cached config for octopus-pro" is the model for success confirmation — brief, informative, not chatty

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-foundation*
*Context gathered: 2026-01-26*
