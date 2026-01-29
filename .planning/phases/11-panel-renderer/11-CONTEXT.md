# Phase 11: Panel Renderer - Context

**Gathered:** 2026-01-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Pure rendering module that produces bordered panels with consistent alignment, ready for TUI integration. Functions return multi-line strings — no screen management, no input handling. Phases 12-14 consume these rendering functions.

</domain>

<decisions>
## Implementation Decisions

### Border & chrome style
- Rounded Unicode corners (╭╮╰╯) with single-line sides (─│)
- Borders use a theme color from the truecolor palette (not dim/neutral)
- 2 characters of padding on each side between border and content
- Max width with centering — panels cap at a max width and center if terminal is wider

### Header formatting
- Spaced uppercase letters in square brackets: `[ D E V I C E S ]`
- Always uppercase regardless of input
- Header text uses an accent color from the palette, distinct from border color
- Header left-aligned in the top border line: `╭[ H E A D E R ]────────────╮`

### Two-column layout
- Content-adaptive column widths — wider column gets more space based on content
- Whitespace gap between columns (no visible divider character)
- Items numbered (#1, #2, etc.) for selection reference
- Rows balanced between columns so both have similar row count

### Step dividers
- Partial width (~60% of content area)
- Label centered in line: `┄┄ Step 1 ┄┄`
- Mid-grey color — visible but doesn't compete with content
- Dashed line character (┄) — lighter than solid border lines

### Claude's Discretion
- Exact max panel width value
- Gap size between columns (2-4 spaces)
- Vertical spacing between panel sections
- How centering works when terminal is narrower than max width

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 11-panel-renderer*
*Context gathered: 2026-01-29*
