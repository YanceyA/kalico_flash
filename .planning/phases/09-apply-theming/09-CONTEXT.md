# Phase 9: Apply Theming - Context

**Gathered:** 2026-01-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Integrate theme.py styles into output messages, TUI menus, and error formatting. The theme infrastructure exists (Phase 8) — this phase applies it across the codebase.

</domain>

<decisions>
## Implementation Decisions

### Message Formatting
- Bracket style: `[OK]`, `[FAIL]`, `[!!]`, `[phase]` — square brackets with text (KIAUH style)
- Color scope: Only the bracket is colored, message text stays default
- Spacing: Single space after bracket (`[OK] Message here`)
- Phase bracket color: Blue (distinct from cyan info)

### Menu Visuals
- Title: Bold + cyan
- Borders/separators: Cyan (match title color)
- Prompt text ("Enter choice:"): Bold
- Option numbers: Bold (`[1]` in bold, description in default)

### Device Markers
- Distinct colors per marker type
- `[R]` (registered): Green — device is ready
- `[N]` (new/unregistered): Yellow — needs registration
- `[B]` (blocked/busy): Yellow — caution, unavailable

### Screen Clearing Behavior
- Clear screen on menu entry
- After success/error outcomes: Show feedback, then pause
- Pause duration: 5 seconds (static, not countdown)
- Pause prompt: "Returning in 5s... (press any key)"
- Any keypress during pause: Cancel timer, return immediately
- Navigation actions (settings, back): No pause, immediate transition

### Claude's Discretion
- Exact ANSI code sequences for colors
- How to handle terminal width edge cases
- Timeout implementation details (select vs threading)

</decisions>

<specifics>
## Specific Ideas

- KIAUH-style bracket formatting as the reference
- Feedback pause creates a "read the result" moment before menu refresh
- Keypress cancellation makes it non-blocking for experienced users

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-apply-theming*
*Context gathered: 2026-01-28*
