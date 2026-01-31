# Phase 26: Remove CLI - Context

**Gathered:** 2026-02-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove all CLI/argparse elements from flash.py so kflash launches directly into TUI with no argument parsing. The tool is not publicly released, so no migration messaging is needed — old flags are simply ignored by never inspecting sys.argv.

</domain>

<decisions>
## Implementation Decisions

### Flag handling
- Never inspect sys.argv — main() calls TUI directly, no parsing of any kind
- No migration message for old flags — program is unreleased, no expectations to manage
- Non-TTY handling: Claude's discretion (likely error and exit since TUI requires terminal)

### TUI launch behavior
- main() goes straight to TUI — no pre-flight checks, TUI handles its own setup/error states
- Entry point stays in flash.py — becomes a thin main() -> tui.run() launcher
- __main__ block remains in flash.py (kflash symlink continues to work)

### Cleanup scope
- Remove all dead code: argparse, build_parser(), _parse_args(), CLI-only imports
- Keep functions that TUI actually calls — audit before deleting
- Refactor CLI command functions (cmd_*) to work better as internal functions if warranted
- Late-import branches that only existed for CLI code paths should be removed

### Claude's Discretion
- Whether to rename CliOutput (evaluate if renaming adds clarity or is just noise)
- Non-TTY error message wording
- Which cmd_* functions need refactoring vs are fine as-is
- __main__ block structure

</decisions>

<specifics>
## Specific Ideas

- "I want to keep what is used by the TUI and remove dead code. If it makes sense to refactor CLI command functions to work better internally I want to explore and address that."
- flash.py should become a thin launcher — the heavy lifting is already in tui.py and other modules

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 26-remove-cli*
*Context gathered: 2026-02-01*
