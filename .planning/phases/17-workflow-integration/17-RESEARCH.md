# Phase 17: Workflow Integration - Research

**Researched:** 2026-01-31
**Domain:** Workflow integration of divider rendering into CLI command workflows
**Confidence:** HIGH

## Summary

This phase integrates the divider methods (`step_divider()` and `device_divider()`) from Phase 16 into all command workflows. The codebase has four main command workflows: `cmd_flash()`, `cmd_add_device()`, `cmd_remove_device()`, and `cmd_flash_all()`. Each workflow has distinct phase transitions where dividers should appear.

The work is straightforward: identify phase boundaries in each command function and insert `out.step_divider()` or `out.device_divider()` calls at the appropriate points. The challenge is placement precision — dividers must appear between sections, never during countdown timers, progress dots, or inside error blocks.

**Primary recommendation:** Insert dividers immediately before phase transitions (before the first `out.phase()` call of each new stage). For Flash All batch operations, use `device_divider()` between devices during build and flash loops. Never insert dividers between error display and user prompts, or during polling/countdown operations.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib | 3.9+ | Everything | Project constraint: no external deps |
| output.py Protocol | Current | Divider methods | Phase 16 deliverable |
| panels.py | Current | Divider rendering | Phase 16 deliverable |

No new libraries needed — all infrastructure is in place from Phase 16.

## Architecture Patterns

### Existing Workflow Structure

```
flash.py command functions follow this pattern:
  1. Registry/config loading
  2. [Phase X] out.phase("X", "message") → first message of phase
  3. Phase operations (validation, scanning, building, etc.)
  4. [Phase Y] out.phase("Y", "message") → next phase
  5. Error handling via out.error_with_recovery()
```

### Pattern 1: Phase Boundary Dividers

**What:** Insert `out.step_divider()` before major phase transitions.
**Where:** Immediately before the first `out.phase()` call that starts a new conceptual phase.
**When to use:** Between Discovery→Safety, Safety→Config, Config→Build, Build→Flash, Flash→Verify.

**Example from cmd_flash() (lines 460-941):**
```python
# Phase 1: Discovery
out.phase("Discovery", "Scanning for USB devices...")
# ... discovery logic ...

# INSERT DIVIDER HERE before Safety
out.step_divider()
# Moonraker Safety Check
print_status = get_print_status()

# INSERT DIVIDER HERE before Version
out.step_divider()
# Version Information
if host_version:
    out.phase("Version", f"Host: ...")

# INSERT DIVIDER HERE before Config
out.step_divider()
# === Phase 2: Config ===
out.phase("Config", f"Loading config for {entry.name}...")

# INSERT DIVIDER HERE before Build
out.step_divider()
# === Phase 3: Build ===
out.phase("Build", "Running make clean + make...")

# INSERT DIVIDER HERE before Flash
out.step_divider()
# === Phase 4: Flash ===
out.phase("Flash", "Verifying device connection...")
```

### Pattern 2: Device Batch Dividers

**What:** Insert `out.device_divider(index, total, name)` between each device in batch operations.
**Where:** Inside the `for` loop during Flash All build and flash phases.
**When to use:** Between devices in `cmd_flash_all()` build loop (line 1144) and flash loop (line 1194).

**Example from cmd_flash_all():**
```python
# Build phase
for i, (entry, result) in enumerate(zip(flash_list, results)):
    if i > 0:  # Skip before first device
        out.device_divider(i + 1, total, entry.name)
    print(f"  Building {i + 1}/{total}: {entry.name}...")
    # ... build logic ...

# Flash phase
flash_idx = 0
with klipper_service_stopped(out=out):
    for entry, result in built_results:
        if flash_idx > 0:  # Skip before first device
            out.device_divider(flash_idx + 1, flash_total, entry.name)
        flash_idx += 1
        # ... flash logic ...
```

### Pattern 3: Wizard Step Dividers

**What:** Insert `out.step_divider()` before each prompt section in the add-device wizard.
**Where:** Before prompts for: global config, device key, display name, MCU, flash method, exclusion.
**When to use:** In `cmd_add_device()` between wizard steps (lines 1548-1820).

**Example from cmd_add_device():**
```python
# After device selection
out.info("Selected", truncate_serial(selected.filename))

# INSERT DIVIDER before global config
out.step_divider()
if not registry_data.devices:
    out.info("Setup", "First device registration...")
    klipper_dir = out.prompt("Klipper source directory", ...)

# INSERT DIVIDER before device key
out.step_divider()
device_key = None
for attempt in range(3):
    key_input = out.prompt("Device key ...", ...)

# INSERT DIVIDER before display name
out.step_divider()
display_name = out.prompt("Display name ...", ...)

# INSERT DIVIDER before MCU
out.step_divider()
detected_mcu = extract_mcu_from_serial(...)
```

### Pattern 4: Removal Workflow Dividers

**What:** Insert `out.step_divider()` before confirmation prompt and before result.
**Where:** In `cmd_remove_device()` before `out.confirm()` and after registry operation.
**When to use:** Simple two-divider pattern (line 1292, 1298).

**Example from cmd_remove_device():**
```python
# After loading entry
entry = registry.get(device_key)

# INSERT DIVIDER before confirmation
out.step_divider()
if not out.confirm(f"Remove '{device_key}' ({entry.name})?"):
    out.info("Registry", "Removal cancelled")
    return 0

# INSERT DIVIDER before result
out.step_divider()
registry.remove(device_key)
out.success(f"Removed '{device_key}'")
```

### Anti-Patterns to Avoid

- **Divider inside error blocks:** Never insert dividers between `error_with_recovery()` and the return statement — breaks error formatting.
- **Divider during polling:** Never insert dividers inside `wait_for_device()` countdown loop (line 701) — disrupts progress dots.
- **Divider after final message:** Never insert divider after the last `out.success()` before return — wastes vertical space.
- **Divider before first phase:** Never insert divider at the very start of a command — the TUI menu or CLI invocation provides visual separation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Custom divider rendering | ASCII art strings | `out.step_divider()` | Protocol-level, theme-aware, Unicode fallback |
| Device separators | Print blank lines | `out.device_divider()` | Labeled, centered, tier-aware color |
| Phase headers | Print "====" | Existing `out.phase()` + dividers | Consistent with current pattern |

## Common Pitfalls

### Pitfall 1: Dividers Inside Error Handling

**What goes wrong:** Divider appears between error message and recovery guidance, breaking the formatted error block.

**Why it happens:** Error formatting in `errors.py` produces a multi-line block that should be atomic. Inserting dividers splits it visually.

**How to avoid:** Never insert dividers inside `except` blocks or between `error_with_recovery()` and `return`.

**Warning signs:**
- Divider call immediately after `out.error_with_recovery()`
- Divider inside `except` block before re-raise or return

### Pitfall 2: Dividers During Countdown Timers

**What goes wrong:** Progress dots (e.g., `wait_for_device()` line 728) get interrupted by divider lines mid-countdown.

**Why it happens:** `wait_for_device()` prints dots on the same line (`print(".", end="", flush=True)`). A divider would appear mid-line.

**How to avoid:** Never insert dividers inside polling loops or countdown functions. Only before or after the entire operation.

**Warning signs:**
- Divider inside `while` loop that prints progress
- Divider between `print(..., end="", flush=True)` calls

### Pitfall 3: Dividers in Batch Flash All Summary

**What goes wrong:** Dividers appear inside the summary table (line 1247), breaking columnar alignment.

**Why it happens:** Summary uses fixed-width columns (`out.info("", "  Device  Build  Flash  Verify")`). Dividers would disrupt the table.

**How to avoid:** Insert dividers before the summary header or after the entire table, never inside.

**Warning signs:**
- Divider inside the `for result in results:` loop (line 1252)
- Divider between summary header and first row

### Pitfall 4: Redundant Dividers

**What goes wrong:** Two dividers appear back-to-back when phases collapse (e.g., skip menuconfig).

**Why it happens:** Conditional blocks (like `if skip_menuconfig:` line 808) might skip phase content but leave divider calls.

**How to avoid:** Place dividers at phase boundaries that always execute, not inside conditional branches.

**Warning signs:**
- Divider inside `if not skip_menuconfig:` block AND before it
- Divider before phase that might be skipped entirely

## Code Examples

### Flash Workflow Dividers (cmd_flash)

**Current state (line 460):**
```python
# === Phase 1: Discovery ===
out.phase("Discovery", "Scanning for USB devices...")
```

**After integration:**
```python
# === Phase 1: Discovery ===
out.phase("Discovery", "Scanning for USB devices...")
# ... discovery logic ...

# Safety check (no phase label, but major transition)
out.step_divider()
print_status = get_print_status()

# Version info
out.step_divider()
if host_version:
    out.phase("Version", f"Host: ...")

# === Phase 2: Config ===
out.step_divider()
out.phase("Config", f"Loading config for {entry.name}...")
# ... config logic ...

# === Phase 3: Build ===
out.step_divider()
out.phase("Build", "Running make clean + make...")
# ... build logic ...

# === Phase 4: Flash ===
out.step_divider()
out.phase("Flash", "Verifying device connection...")
```

### Add Device Wizard Dividers (cmd_add_device)

**Current state (line 1548):**
```python
out.info("Selected", truncate_serial(selected.filename))

# Step 3: Global config (first run only)
if not registry_data.devices:
    out.info("Setup", "First device registration...")
```

**After integration:**
```python
out.info("Selected", truncate_serial(selected.filename))

out.step_divider()
# Step 3: Global config (first run only)
if not registry_data.devices:
    out.info("Setup", "First device registration...")
    klipper_dir = out.prompt(...)

out.step_divider()
# Step 4: Device key
device_key = None
for attempt in range(3):
    key_input = out.prompt(...)

out.step_divider()
# Step 5: Display name
display_name = out.prompt(...)

out.step_divider()
# Step 6: MCU auto-detection
detected_mcu = extract_mcu_from_serial(...)

out.step_divider()
# Step 8: Flash method
flash_method = None
for attempt in range(3):
    method_input = out.prompt(...)

out.step_divider()
# Step 9: Ask if device is flashable
exclude_from_flash = out.confirm(...)

out.step_divider()
# Step 10: Create and save
entry = DeviceEntry(...)
registry.add(entry)
out.success(f"Registered '{device_key}'...")
```

### Remove Device Dividers (cmd_remove_device)

**Current state (line 1277):**
```python
entry = registry.get(device_key)
if entry is None:
    template = ERROR_TEMPLATES["device_not_registered"]
    out.error_with_recovery(...)
    return 1

if not out.confirm(f"Remove '{device_key}' ({entry.name})?"):
    out.info("Registry", "Removal cancelled")
    return 0

registry.remove(device_key)
out.success(f"Removed '{device_key}'")
```

**After integration:**
```python
entry = registry.get(device_key)
if entry is None:
    template = ERROR_TEMPLATES["device_not_registered"]
    out.error_with_recovery(...)
    return 1

out.step_divider()
if not out.confirm(f"Remove '{device_key}' ({entry.name})?"):
    out.info("Registry", "Removal cancelled")
    return 0

out.step_divider()
registry.remove(device_key)
out.success(f"Removed '{device_key}'")
```

### Flash All Batch Dividers (cmd_flash_all)

**Current state (line 1139):**
```python
out.phase("Flash All", f"Building firmware for {len(flash_list)} device(s)...")
temp_dir = tempfile.mkdtemp(prefix="kalico-flash-")
total = len(flash_list)

try:
    for i, (entry, result) in enumerate(zip(flash_list, results)):
        print(f"  Building {i + 1}/{total}: {entry.name}...")
```

**After integration:**
```python
out.phase("Flash All", f"Building firmware for {len(flash_list)} device(s)...")
temp_dir = tempfile.mkdtemp(prefix="kalico-flash-")
total = len(flash_list)

try:
    for i, (entry, result) in enumerate(zip(flash_list, results)):
        if i > 0:
            out.device_divider(i + 1, total, entry.name)
        print(f"  Building {i + 1}/{total}: {entry.name}...")
        # ... build ...

    # === Stage 4: Flash all ===
    out.step_divider()
    out.phase("Flash All", f"Flashing {len(built_results)} device(s)...")

    # ... preflight ...

    flash_idx = 0
    flash_total = len(built_results)
    with klipper_service_stopped(out=out):
        for entry, result in built_results:
            if flash_idx > 0:
                out.device_divider(flash_idx + 1, flash_total, entry.name)
            flash_idx += 1
            # ... flash ...

    out.phase("Service", "Klipper restarted")

finally:
    # ... cleanup ...

# === Stage 5: Summary table ===
out.step_divider()
out.phase("Flash All", "Summary:")
out.info("", "  Device                Build   Flash   Verify")
```

### Flash All Major Stage Dividers

```python
# Stage 1: Validation (no divider — first stage)
out.phase("Flash All", "Validating cached configs...")

# Stage 2: Version check
out.step_divider()
host_version = get_host_klipper_version(klipper_dir)

# Stage 3: Build all
out.step_divider()
out.phase("Flash All", f"Building firmware for {len(flash_list)} device(s)...")

# Stage 4: Flash all
out.step_divider()
out.phase("Flash All", f"Flashing {len(built_results)} device(s)...")

# Stage 5: Summary
out.step_divider()
out.phase("Flash All", "Summary:")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No visual separation | Phase-labeled output only | Pre-Phase 16 | Workflow stages blur together |
| Manual print("\n---\n") | Protocol-level dividers | Phase 16 | Consistent, theme-aware |
| No batch device separation | device_divider() labels | Phase 17 | Flash All clarity |

## Workflow Mapping

### cmd_flash() — 6 Divider Placements

| Line | Before | Divider Type | After |
|------|--------|--------------|-------|
| ~724 | Discovery complete | step_divider() | Safety check |
| ~750 | Safety OK | step_divider() | Version info |
| ~797 | Version info | step_divider() | Config phase |
| ~879 | Config validated | step_divider() | Build phase |
| ~900 | Build complete | step_divider() | Flash phase |
| ~940 | Flash complete | (none) | Success/Error — no divider after final message |

**Key exclusions:**
- No divider during `wait_for_device()` countdown (line 941)
- No divider inside error blocks (lines 284, 322, 354, 383, etc.)

### cmd_add_device() — 7 Divider Placements

| Line | Before | Divider Type | After |
|------|--------|--------------|-------|
| ~1548 | Device selected | step_divider() | Global config prompt |
| ~1686 | Global config saved | step_divider() | Device key prompt |
| ~1720 | Device key accepted | step_divider() | Display name prompt |
| ~1726 | Display name entered | step_divider() | MCU detection |
| ~1744 | Serial pattern shown | step_divider() | Flash method prompt |
| ~1805 | Flash method set | step_divider() | Exclusion prompt |
| ~1810 | Exclusion answered | step_divider() | Final success |

**Matches dividers.txt mockup (lines 32-61):** Dividers before each major prompt section.

### cmd_remove_device() — 2 Divider Placements

| Line | Before | Divider Type | After |
|------|--------|--------------|-------|
| ~1282 | Entry loaded | step_divider() | Confirmation prompt |
| ~1296 | Confirmed removal | step_divider() | Success message |

### cmd_flash_all() — 3 Stage Dividers + N Device Dividers

**Major stages:**
| Line | Before | Divider Type | After |
|------|--------|--------------|-------|
| ~1082 | Validation complete | step_divider() | Version check |
| ~1138 | Version check done | step_divider() | Build phase |
| ~1172 | Build complete | step_divider() | Flash phase |
| ~1246 | Flash complete | step_divider() | Summary table |

**Device dividers:**
- Build loop (line ~1144): Insert `device_divider(i+1, total, entry.name)` when `i > 0`
- Flash loop (line ~1194): Insert `device_divider(flash_idx+1, flash_total, entry.name)` when `flash_idx > 0`

**Key exclusion:**
- No divider inside summary table loop (line 1252) — breaks columnar layout

## Placement Rules Summary

### DO Insert Dividers:
1. ✅ Before major phase transitions (Discovery→Safety→Config→Build→Flash)
2. ✅ Before each wizard step in add-device workflow
3. ✅ Before confirmation prompts in remove-device
4. ✅ Between devices in Flash All build/flash loops
5. ✅ Between major stages in Flash All (preflight→build→flash→summary)

### DON'T Insert Dividers:
1. ❌ Inside error handling blocks (`except`, after `error_with_recovery()`)
2. ❌ During countdown timers (`wait_for_device()` polling loop)
3. ❌ Inside summary tables (Flash All results table)
4. ❌ After the final success/error message before return
5. ❌ Inside conditional blocks that might skip entirely (e.g., inside `if skip_menuconfig:`)

## Open Questions

1. **Should Flash All version check section get a divider?**
   - What we know: Line 1082-1127 version check has complex conditional output (outdated vs current devices).
   - Recommendation: Yes — insert `out.step_divider()` before `host_version = get_host_klipper_version()` (line 1083). It's a major preflight stage.

2. **Should Safety check section in cmd_flash get a phase label?**
   - What we know: Line 725 Moonraker safety check has no `out.phase()` call, just direct logic.
   - Recommendation: No phase label needed (current code doesn't use one), but divider before it provides visual separation. Keep it unlabeled.

3. **Should device_divider show 0-based or 1-based index?**
   - What we know: Build loop uses `i+1` (1-based), flash loop uses `flash_idx+1` (1-based).
   - Recommendation: Use 1-based (`device_divider(i+1, total, ...)`) to match user-facing numbering.

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `kflash/flash.py` (cmd_flash, cmd_add_device, cmd_remove_device, cmd_flash_all)
- Direct code inspection: `kflash/output.py` (Protocol methods from Phase 16)
- Direct code inspection: `kflash/panels.py` (render_step_divider, render_device_divider from Phase 16)
- Direct code inspection: `kflash/tui.py` (wait_for_device polling pattern)
- Mockup reference: `.working/UI-working/dividers.txt` (add-device wizard placement)

### Secondary (MEDIUM confidence)
- Requirements: Phase 17 objective from user-provided context (FLASH-01, ADD-01, REM-01, BATCH-01/02/03)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all infrastructure exists from Phase 16
- Architecture patterns: HIGH — clear insertion points identified from code inspection
- Pitfalls: HIGH — specific anti-patterns identified from workflow analysis
- Placement rules: HIGH — line-level mapping completed for all four workflows

**Research date:** 2026-01-31
**Valid until:** 2026-03-02 (stable domain, implementation-ready)
