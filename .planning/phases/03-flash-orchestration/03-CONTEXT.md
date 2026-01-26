# Phase 3: Flash & Orchestration - Context

**Gathered:** 2026-01-25
**Status:** Ready for planning

<domain>
## Phase Boundary

One command to build and flash any registered board with guaranteed klipper service restart on all code paths. Orchestrates: discover device, configure, build, stop klipper, flash, restart klipper. Service lifecycle enforced by context manager with finally block.

</domain>

<decisions>
## Implementation Decisions

### Workflow flow
- No confirmation prompt before flash — user specified --device, that's the intent
- Always run full cycle (menuconfig -> build -> flash) — no --flash-only shortcut
- Interactive device menu if no --device flag provided — numbered list, user picks
- Trust the user on printer state — no Moonraker API check for active prints

### Failure handling
- Auto-fallback from Katapult to make flash with notice: "Katapult failed, trying make flash..."
- Minimal error output on flash failure — just "Flash failed" + exit code
- Fail immediately if device path disappears before flash — no wait/retry
- Let sudo prompt for password normally if passwordless not configured

### Console output
- Phase labels use `[Phase] message` format (e.g., `[Build] Running make clean...`)
- Stream make build output in real-time — noisy but transparent
- Success summary at end: device name, flash method used, elapsed time
- Single output mode — no --quiet flag

### Flash behavior
- 60 second timeout for flash operations
- Always try Katapult flashtool.py first, fall back to make flash
- Always use /dev/serial/by-id/ stable symlinks for flash commands
- Wait up to 10 seconds for device to reconnect after flash, confirm success

### Claude's Discretion
- Exact phase label wording for each workflow step
- Format of elapsed time display
- How to detect Katapult vs make flash failure modes

</decisions>

<specifics>
## Specific Ideas

- Dev environment available: SSH to Pi at 192.168.50.50 for testing

</specifics>

<deferred>
## Deferred Ideas

- Dev environment setup for running tests from terminal — useful for development workflow but outside flash orchestration scope

</deferred>

---

*Phase: 03-flash-orchestration*
*Context gathered: 2026-01-25*
