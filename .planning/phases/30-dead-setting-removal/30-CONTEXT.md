# Phase 30: Dead Setting Removal - Context

**Gathered:** 2026-02-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove the unused `config_cache_dir` setting from all locations in the codebase. This is a mechanical cleanup — no new behavior, no UI changes, no user-facing decisions.

</domain>

<decisions>
## Implementation Decisions

### Removal scope
- Delete `config_cache_dir` field from `GlobalConfig` dataclass in models.py
- Remove serialization/deserialization of `config_cache_dir` in registry.py
- Remove `config_cache_dir` option from settings screen in screen.py
- Remove any `config_cache_dir` references in validation.py

### No discussion needed
- All changes are mechanical deletions guided by explicit success criteria
- No ambiguity in what to remove or how

### Claude's Discretion
- Order of file changes
- Whether to clean up any orphaned imports or helpers that only served config_cache_dir

</decisions>

<specifics>
## Specific Ideas

No specific requirements — straightforward deletion task.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 30-dead-setting-removal*
*Context gathered: 2026-02-01*
