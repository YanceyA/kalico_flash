# Phase 6: User Experience - Context

**Gathered:** 2026-01-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Interactive menu-driven workflow for CLI users running `kflash` without arguments. Includes TUI menu with numbered options, menu loop behavior, post-flash device verification, Unicode/ASCII terminal detection, and non-TTY environment handling. Does not include installation scripts or documentation (Phase 7).

</domain>

<decisions>
## Implementation Decisions

### Menu Navigation
- Setup-first option order: Add, List, Flash, Remove, Settings, Exit — natural onboarding flow for new users
- Return to menu silently after actions — show success message, then menu reappears immediately (no "Press Enter")
- Exit confirmation only during active flash — if flash is in progress, confirm before exiting; otherwise exit immediately
- Confirm before Flash and Remove operations — both are destructive/significant actions

### Flash Verification
- 30 second timeout for device reappearance — more forgiving for slower bootloaders or USB hubs
- Progress dots feedback while waiting — "Verifying...." adding dots every few seconds
- Wrong prefix is failure — if device reappears as katapult_ instead of expected Klipper_, treat as failure with recovery steps
- Recovery guidance on timeout: physical checks first (check USB, try unplug/replug), then diagnostic commands (`ls /dev/serial/by-id/`, `dmesg | tail`)

### Terminal Rendering
- Unicode detection via LANG/LC_ALL — if contains 'UTF-8', use Unicode box drawing; otherwise ASCII
- Subtle colors — highlight selection numbers, dim borders; enhances without requiring color support
- ASCII fallback uses dashes and pipes — `+------+`, `|text|`, standard ASCII box drawing
- No manual ASCII override — auto-detection is sufficient

### Error States
- Non-TTY falls back to --help — show usage information and exit successfully (not error)
- Ctrl+C is context-dependent — during flash: return to menu (dangerous to exit mid-operation); during simple actions like list: exit program
- Action failures show error + suggestion — display error with context and actionable suggestion, then return to menu

### Claude's Discretion
- Exact menu dimensions and spacing
- Color palette choices (which ANSI colors for highlights)
- Polling interval during verification (within 30s total)
- Invalid input handling approach (inline vs redraw)

</decisions>

<specifics>
## Specific Ideas

No specific product references mentioned — open to standard CLI/TUI patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-user-experience*
*Context gathered: 2026-01-27*
