# Phase 12: TUI Main Screen - Context

**Gathered:** 2026-01-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Panel-based main screen with live device status and action navigation. Users see Status, Device, and Actions panels, select actions via single keypress, and the screen refreshes after every command. This phase wires the panel renderer (Phase 11) into the interactive TUI loop. Config screen (Phase 13) and Flash All logic (Phase 14) are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Screen layout & flow
- Panel order top-to-bottom: Status → Devices → Actions
- Full clear + redraw on each refresh (no cursor positioning)
- Fixed panel width, centered in terminal
- If terminal is too short, just let it scroll — no truncation logic

### Device display
- Section headers inside the device panel for groups: Registered, New, Blocked
- Status icons: ● green = connected, ○ grey = disconnected (two states only)
- Long serial paths truncated in the middle with ellipsis (keep start and end visible)
- Host Klipper version displayed in device panel footer

### Actions panel
- Actions: Flash Device, Add Device, Remove Device, Refresh Devices, Config, Flash All, Quit
- Flash All included as placeholder even before Phase 14 is built
- Single keypress input (no Enter required)
- Key letter highlighted within the action word (e.g., the "F" in "Flash Device" is styled)
- Device-targeting actions (Flash, Remove): after pressing action key, type device number from device panel

### Status panel
- First launch: welcome message with brief hint
- After commands: shows last result with action name (e.g., "Flash Device: Octopus Pro flashed successfully")
- Color-coded results: green for success, red for error, yellow for warning
- Error display: summary line only, no output snippets

### Claude's Discretion
- Exact welcome message text and hint content
- Panel spacing and padding between panels
- How device number input prompt appears after action key
- Fixed panel width value
- Color shades for status icons and result text
- Two-column arrangement within actions panel

</decisions>

<specifics>
## Specific Ideas

No specific references — open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 12-tui-main-screen*
*Context gathered: 2026-01-29*
