# Phase 27: Documentation & Cleanup - Context

**Gathered:** 2026-02-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Update all project documentation (README, CLAUDE.md, install.sh) and error messages to reflect TUI-only operation. No CLI references should remain. No new features — purely content updates.

</domain>

<decisions>
## Implementation Decisions

### README scope
- Replace CLI reference section with TUI walkthrough — step-by-step of what happens when you run kflash (main screen, actions, device config)
- No visuals (no screenshots, no ASCII mockups) — text descriptions only, TUI is self-explanatory once launched
- Keep "Out of Scope" section as-is
- Remove "Future Plans" section entirely — roadmap lives in .planning/
- Remove all CLI flag references throughout

### Error message tone
- Recovery messages reference TUI action names, not specific keys (e.g., "Use Flash Device from the main menu" not "Press F")
- Keep current verbosity style — just swap CLI references for TUI references, don't change the tone
- Use "kflash" as the command name in recovery messages (not "restart the application")
- Full audit of errors.py — review every error/recovery message, update all CLI references to TUI

### CLAUDE.md updates
- Replace "CLI Commands" section with "TUI Menu" section describing the TUI flow (main screen → actions → what each does)
- Update ALL file descriptions in Repository Structure to reflect current architecture (not just flash.py)
- Remove "Future Plans (v2.0 candidates)" section entirely
- Update "Out of Scope" section to fix inaccurate items (TUI not CLI, flash-all exists) but keep the section

### install.sh cleanup
- Post-install message: simple "Run 'kflash' to start" — nothing more
- Full audit for any CLI flag references — remove them
- Moonraker update manager config: no changes needed (doesn't reference CLI behavior)

### Claude's Discretion
- Exact wording of TUI walkthrough sections
- How to organize the TUI menu documentation in CLAUDE.md
- Which error messages need updating (full audit determines this)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for documentation structure and wording.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 27-documentation-cleanup*
*Context gathered: 2026-02-01*
