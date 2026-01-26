# Phase 5: Moonraker Integration - Context

**Gathered:** 2026-01-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Safety checks and version awareness before flashing — blocking flash during prints, detecting Klipper/firmware versions, graceful degradation when Moonraker unavailable. Does not include Moonraker-based firmware upload or remote flashing capabilities.

</domain>

<decisions>
## Implementation Decisions

### Print Blocking Behavior
- Block completely during active print — no force-override flag
- Paused prints also blocked (user paused is still "in progress")
- Safe states that allow flashing: idle, complete, cancelled, error, standby
- Blocked message is minimal: "Printer is busy — cannot flash during active print"

### Version Display Format
- Table format showing host and MCU versions side by side
- Show all MCUs in multi-MCU setups, not just the target
- Version comparison is informational only — never blocks flash
- Explicit message on mismatch: separate line stating "MCU firmware is behind host Klipper"

### Moonraker Unavailable Handling
- Warn + require confirmation before proceeding
- Warning emphasizes missing info: "Moonraker unreachable — print status and version check unavailable"
- Simple Y/N confirmation prompt: "Continue without safety checks? [y/N]"
- No flag to bypass confirmation — always require interactive confirmation

### Connection Handling
- Default URL: localhost:7125 (no custom URL support — keep it simple)
- Timeout: 5 seconds before declaring unavailable
- No retry: one attempt, then warn

### Claude's Discretion
- Exact table formatting and column widths
- HTTP client implementation details (urllib vs socket)
- Version string parsing approach
- Error message wording beyond decisions above

</decisions>

<specifics>
## Specific Ideas

- Minimal blocked message avoids overwhelming user with print details they already know
- Table format chosen to fit 80-column terminal well and show version comparison clearly
- 5-second timeout is forgiving for slower Pi systems while not adding excessive delay

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-moonraker-integration*
*Context gathered: 2026-01-26*
