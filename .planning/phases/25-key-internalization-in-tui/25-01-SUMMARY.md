---
phase: 25-key-internalization-in-tui
plan: 01
subsystem: tui-wizard
tags: [device-key, add-device, slug-generation, ux]
dependency_graph:
  requires: [24-slug-generation]
  provides: [auto-key-generation-in-wizard]
  affects: [25-02]
tech_stack:
  added: []
  patterns: [auto-slug-from-display-name]
key_files:
  created: []
  modified: [kflash/flash.py]
decisions:
  - id: d25-01-01
    decision: "Load registry once at start of name prompt section, reuse for both duplicate check and pattern overlap"
    rationale: "Avoids redundant registry.load() call"
metrics:
  duration: "3 minutes"
  completed: "2026-02-01"
---

# Phase 25 Plan 01: Remove Key Prompt and Wire Auto-Key Generation

**One-liner:** Replaced manual device key prompt with silent auto-generation via generate_device_key() in add-device wizard.

## What Was Done

### Task 1: Remove key prompt, add duplicate name check, wire generate_device_key()

- Deleted the entire device key prompt loop (Step 4 in wizard) that asked users for a key like "octopus-pro"
- Replaced with a display name prompt that includes:
  - Empty input rejection
  - Case-insensitive duplicate name check against all existing devices
  - 3-attempt limit with helpful error messages
- After name is accepted, `generate_device_key(display_name, registry)` auto-generates a unique slug
- ValueError from generate_device_key caught with user-friendly message
- Success message changed from `Registered '{key}' ({name})` to `Device '{name}' added successfully.`
- Removed redundant `registry.load()` call in pattern overlap section

**Commit:** c9697a8

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed redundant registry.load() call**
- **Found during:** Task 1
- **Issue:** After moving registry_data load earlier for the duplicate name check, the original load at the pattern overlap section became redundant
- **Fix:** Removed the duplicate call, reusing the earlier load
- **Files modified:** kflash/flash.py

## Verification

- "Device key" prompt text no longer appears in any wizard prompt
- `generate_device_key` imported and called in cmd_add_device
- Case-insensitive duplicate name check uses `{e.name.lower() for e in ...}`
- `device_key` still passed to DeviceEntry creation via `key=device_key`
- Success message shows display name only

## Next Phase Readiness

Plan 25-02 can proceed -- it handles the remaining TUI locations where device keys are exposed to users.
