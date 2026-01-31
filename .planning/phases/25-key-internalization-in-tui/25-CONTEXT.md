# Phase 25: Key Internalization in TUI - Context

**Gathered:** 2026-02-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Device keys become invisible internal identifiers. Users interact only with display names throughout the TUI. No key prompt in add-device wizard, no key editing in config screen, all output shows display names not keys. No legacy migration needed — system is not yet deployed, all keys will be auto-generated.

</domain>

<decisions>
## Implementation Decisions

### Add-device flow
- Remove key prompt entirely — system generates key silently via `generate_device_key()`
- Never show the generated key to the user; confirmation says "Device added" with display name only
- Duplicate display name check: case-insensitive comparison against existing device names
- If duplicate name detected: reject and re-prompt ("You already have a device named 'X'. Enter a different name.")
- Prompt order unchanged: Name → MCU → serial pattern

### Display name rendering
- Device panel rows show name + MCU type: `1. Octopus Pro v1.1 (stm32h723) [connected]`
- Flash output uses display name in brackets: `[Octopus Pro v1.1] Building...`
- Truncate display names to 20 characters with `...` suffix in bracketed output contexts
- Flash All batch results use table-aligned columnar layout: Name | Status | Time

### Key visibility policy
- Key exists in devices.json (dict key) and config cache paths — both are internal implementation details
- Key never appears in any TUI output, error messages, or user-facing text
- Error messages reference device by display name only: "Flash failed for 'Octopus Pro v1.1'"
- Config cache directory continues using key-based folder names (`~/.config/kalico-flash/configs/{key}/`)

### Claude's Discretion
- Exact wording of duplicate name rejection message
- How MCU type is styled in device panel rows (parentheses, color, etc.)
- Alignment and spacing in batch results table

</decisions>

<specifics>
## Specific Ideas

- No legacy/migration concerns — treat all devices as having auto-generated keys
- The key is a pure internal identifier; the display name is the user's mental model

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 25-key-internalization-in-tui*
*Context gathered: 2026-02-01*
