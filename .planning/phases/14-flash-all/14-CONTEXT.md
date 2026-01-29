# Phase 14: Flash All - Context

**Gathered:** 2026-01-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Batch flash all registered devices in one command. Build all firmware first (Klipper running), then stop Klipper once, flash all devices sequentially, restart once. Includes version check, failure handling, and post-flash verification. Individual device flash workflow is unchanged (Phase 12).

</domain>

<decisions>
## Implementation Decisions

### Version check behavior
- Check versions BEFORE building (parse klippy.log for host and MCU versions)
- If ALL devices match host version: warn and confirm ("All devices already match vX.Y.Z — flash anyway?" Y/N)
- If SOME devices match: offer selective flash — show which match/mismatch, let user choose to flash only outdated ones
- Version check happens first, before any builds start

### Failure & recovery
- Build failure: skip that device, continue building remaining devices, then flash only what built successfully
- Flash failure: no retry, continue flashing remaining devices
- One failure never blocks other devices
- Summary table after batch: device name, pass/fail status, and firmware version
- Failed devices can be re-flashed individually after

### Build phase UX
- Build devices sequentially, one at a time
- Suppress make output (no compiler lines shown)
- Show progress header: "Building 1/3: Octopus Pro..."
- Show tally line after each: "✓ Octopus Pro built (1/3)"
- Same suppressed style for flash phase: "✓ Octopus Pro flashed (1/3)"

### Flash ordering & stagger
- Flash in registration order (order devices were added to registry)
- Default stagger delay: 2 seconds between devices
- Stagger delay configured via Config Screen (Phase 13) — don't show value in pre-flash summary
- Post-flash verification: 30-second timeout waiting for device to reappear as Klipper serial device
- If device doesn't reappear within 30s: mark as failed in summary

### Claude's Discretion
- Exact klippy.log parsing implementation
- How to present the selective flash prompt (version mismatch UI)
- Build/flash error message formatting
- How cached config requirement is enforced (error vs prompt to configure)

</decisions>

<specifics>
## Specific Ideas

- Build tally should feel like a clean checklist: "✓ Device built (1/3)" then "✓ Device built (2/3)"
- Same pattern for flash: "✓ Device flashed (1/3)"
- No verbose output — batch should feel fast and streamlined

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 14-flash-all*
*Context gathered: 2026-01-29*
