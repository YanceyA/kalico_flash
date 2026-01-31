# Phase 20: Menu Integration - Context

**Gathered:** 2026-01-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the device config screen (Phase 19) into the main menu. Users press "E" to select a device and enter the config screen. No new editing capabilities — this phase connects existing pieces.

</domain>

<decisions>
## Implementation Decisions

### Selection flow
- Show all registered devices (connected and disconnected)
- Auto-select if only one device registered (skip selection prompt)
- Device list shows just numbered names, no connection status indicators
- After exiting config screen, return to main menu (not device list)
- Cancel at device selection returns to main menu

### Key binding
- "E" key triggers config device flow (case-insensitive)
- Actions panel label: "E) Config Device"
- Panel ordering: Flash > Flash All > Add > Config > Remove > Settings > Quit

### Divider placement
- Step divider between device selection and config screen
- Step divider after config screen exits, before main menu redraws
- Dividers are unlabeled (plain lines)
- No new dividers inside config screen itself (Phase 19 handled internal dividers)

### Edge cases
- No devices registered: show "No devices registered. Use Add Device first." then return to menu
- Save overwrites without conflict checking (single-user Pi scenario)
- Brief success summary shown after saving changes (e.g., "Saved: renamed key, updated flash method") before returning to menu

### Claude's Discretion
- Exact summary message format
- How the auto-select single-device case communicates to the user
- Internal wiring details (function signatures, error propagation)

</decisions>

<specifics>
## Specific Ideas

- Device selection prompt should match the existing Flash/Remove selection style exactly
- Summary message should list what actually changed, not a generic "saved" message

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 20-menu-integration*
*Context gathered: 2026-01-31*
