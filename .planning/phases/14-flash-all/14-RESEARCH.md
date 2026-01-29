# Phase 14: Flash All - Research

**Researched:** 2026-01-29
**Domain:** Batch firmware build/flash orchestration (Python 3.9+ stdlib)
**Confidence:** HIGH

## Summary

Phase 14 adds a "Flash All" command that builds firmware for all registered devices, then stops Klipper once, flashes all devices sequentially, and restarts once. The entire implementation is internal orchestration of existing modules — no new libraries or external tools needed.

The codebase already has all building blocks: `run_build()` for compilation, `ConfigManager` for per-device configs, `klipper_service_stopped()` context manager for service lifecycle, `flash_device()` for flashing, `wait_for_device()` for post-flash verification, and `moonraker.py` for version checking. The work is composing these into a batch workflow with progress reporting, continue-on-failure semantics, and a summary table.

**Primary recommendation:** Create a new `cmd_flash_all()` function in `flash.py` that orchestrates the batch workflow in 5 sequential stages: validate configs, version check, build all, flash all (inside single `klipper_service_stopped()`), and display summary table.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib | 3.9+ | Everything | Project constraint: no external deps |
| `time.sleep()` | stdlib | Stagger delay between flashes | Simple, reliable |
| `time.monotonic()` | stdlib | Elapsed time tracking | Already used in build/flash |

### Supporting
No new libraries needed. All required functionality exists in the codebase.

### Alternatives Considered
None — stdlib-only is a locked project constraint.

## Architecture Patterns

### Recommended Function Structure

```
cmd_flash_all() in flash.py
├── Stage 1: Validate (all devices have cached configs)
├── Stage 2: Version check (compare MCU vs host)
├── Stage 3: Build all (sequential, suppressed output)
│   └── Per-device: load config → validate MCU → run_build()
├── Stage 4: Flash all (inside single klipper_service_stopped())
│   └── Per-device: flash_device() → wait_for_device() → stagger delay
└── Stage 5: Summary table
```

### Pattern 1: Batch Result Tracking
**What:** A dataclass to track per-device status across build and flash stages.
**When to use:** Any multi-device operation that needs a summary.
**Example:**
```python
@dataclass
class BatchDeviceResult:
    device_key: str
    device_name: str
    config_ok: bool = False
    build_ok: bool = False
    flash_ok: bool = False
    verify_ok: bool = False
    version_before: Optional[str] = None
    version_after: Optional[str] = None
    error_message: Optional[str] = None
    skipped: bool = False  # User chose to skip (version match)
```

### Pattern 2: Continue-on-Failure Loop
**What:** Try each device, catch failures, record result, continue to next.
**When to use:** Batch operations where one failure shouldn't stop others.
**Example:**
```python
results: list[BatchDeviceResult] = []
for i, entry in enumerate(devices):
    result = BatchDeviceResult(device_key=entry.key, device_name=entry.name)
    try:
        # build or flash
        result.build_ok = True
    except Exception as e:
        result.error_message = str(e)
    results.append(result)
    out.info("Build", f"{'✓' if result.build_ok else '✗'} {entry.name} built ({i+1}/{total})")
```

### Pattern 3: Single Service Stop Window
**What:** Use existing `klipper_service_stopped()` context manager, flash ALL devices inside it.
**When to use:** Flash All — minimizes Klipper downtime.
**Example:**
```python
with klipper_service_stopped(out=out):
    for i, (entry, result) in enumerate(flash_queue):
        if i > 0:
            time.sleep(stagger_delay)
        # flash_device() + wait_for_device()
```

### Pattern 4: Suppressed Build Output
**What:** Redirect subprocess stdout/stderr to DEVNULL during batch builds.
**When to use:** Flash All builds — user wants tally, not compiler output.
**Important:** Current `run_build()` uses inherited stdio. For batch mode, need to suppress. Two options:
1. Add `quiet` parameter to `run_build()` that uses `capture_output=True`
2. Create a wrapper that temporarily redirects

**Recommendation:** Add `quiet: bool = False` parameter to `run_build()`. When True, use `capture_output=True` instead of inherited stdio. This is minimal, backward-compatible.

### Anti-Patterns to Avoid
- **Parallel builds:** Klipper shares a single `.config` and `out/` directory. Cannot build multiple devices in parallel — must be sequential with config swap per device.
- **Nested service stops:** Never nest `klipper_service_stopped()` — it's not reentrant. The flash-all function must manage the single stop/start itself.
- **Early exit on failure:** Don't abort the batch on first build/flash failure. Continue to next device.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Config loading | Custom config loader | `ConfigManager.load_cached_config()` | Already handles XDG paths, atomic copy |
| MCU validation | Direct config parsing | `ConfigManager.validate_mcu()` | Handles prefix matching |
| Flash operation | Direct subprocess | `flash_device()` | Handles fallback, timeout, logging |
| Device verification | Manual polling | `wait_for_device()` | Handles prefix check, timeout |
| Version comparison | String comparison | `is_mcu_outdated()` | Handles git describe parsing |
| Service lifecycle | Manual systemctl | `klipper_service_stopped()` | Guarantees restart on all paths |

**Key insight:** Every building block already exists. Phase 14 is pure orchestration.

## Common Pitfalls

### Pitfall 1: Shared Klipper .config During Sequential Builds
**What goes wrong:** Building device A writes `.config` to klipper dir. Building device B overwrites it. If B fails mid-build, klipper dir has B's partial config.
**Why it happens:** `ConfigManager` copies cached config to `klipper_dir/.config` before each build.
**How to avoid:** This is actually fine — `ConfigManager.load_cached_config()` copies FROM cache TO klipper dir before each build. Each device's cached config is independent. Just call `load_cached_config()` before each build.
**Warning signs:** Build failures with wrong MCU — means config wasn't swapped.

### Pitfall 2: Firmware Path Collision
**What goes wrong:** All builds produce `~/klipper/out/klipper.bin`. Building device B overwrites device A's firmware before A is flashed.
**Why it happens:** Single build output directory.
**How to avoid:** Build ALL first, but copy/rename firmware after each build. Or build-then-flash sequentially. Given the design (build all, then flash all), must save firmware per device.
**Recommendation:** After each successful build, copy `klipper.bin` to a temp location keyed by device (e.g., `/tmp/kalico-flash/{device-key}/klipper.bin`). Flash from that copy.

### Pitfall 3: Device Path Changes After Klipper Stop
**What goes wrong:** USB serial paths in `/dev/serial/by-id/` may change when Klipper releases serial ports.
**Why it happens:** Klipper holds serial ports open; stopping it releases them. Some boards reset.
**How to avoid:** Re-scan USB devices AFTER stopping Klipper, before flashing. Match by serial_pattern, not by previously-discovered path.

### Pitfall 4: Stagger Delay Placement
**What goes wrong:** Delay before first device or after last device wastes time.
**Why it happens:** Loop structure.
**How to avoid:** Only delay between devices (not before first or after last): `if i > 0: time.sleep(stagger_delay)`.

### Pitfall 5: Version Check Requires Klipper Running
**What goes wrong:** MCU versions from Moonraker require Klipper to be running and communicating with MCUs.
**Why it happens:** Moonraker API queries Klipper which queries MCUs.
**How to avoid:** Do version check BEFORE stopping Klipper (already planned). Version check is in Stage 2, Klipper stops in Stage 4. This ordering is correct.

### Pitfall 6: Summary Table After Klipper Restart
**What goes wrong:** Want to show post-flash versions in summary, but Klipper needs time to reconnect to MCUs after restart.
**Why it happens:** Klipper restart doesn't immediately query all MCUs.
**How to avoid:** Two options: (a) wait a few seconds after restart then query Moonraker, or (b) skip post-flash version in summary (just show pass/fail). Recommendation: show pass/fail status. Post-flash versions are aspirational — Klipper may take 10-30s to fully reconnect to all MCUs.

## Code Examples

### Build Phase with Suppressed Output and Tally
```python
def _batch_build(devices, config_mgrs, klipper_dir, out):
    """Build firmware for all devices, suppressing make output."""
    total = len(devices)
    results = []
    for i, (entry, config_mgr) in enumerate(zip(devices, config_mgrs)):
        out.info("Build", f"Building {i+1}/{total}: {entry.name}...")

        # Load this device's cached config into klipper dir
        config_mgr.load_cached_config()

        # Build with suppressed output
        build_result = run_build(klipper_dir, quiet=True)

        if build_result.success:
            # Save firmware copy for later flashing
            firmware_copy = _save_firmware_copy(entry.key, build_result.firmware_path)
            out.success(f"{entry.name} built ({i+1}/{total})")
            results.append((entry, firmware_copy, True))
        else:
            out.warn(f"{entry.name} build failed ({i+1}/{total})")
            results.append((entry, None, False))

    return results
```

### Flash Phase Inside Single Service Stop
```python
def _batch_flash(flash_queue, klipper_dir, katapult_dir, stagger_delay, out):
    """Flash all built devices with single Klipper stop/start."""
    total = len(flash_queue)
    results = []

    with klipper_service_stopped(out=out):
        # Re-scan devices after Klipper stop
        usb_devices = scan_serial_devices()

        for i, (entry, firmware_path) in enumerate(flash_queue):
            if i > 0:
                time.sleep(stagger_delay)

            # Find device by pattern (path may have changed)
            usb_device = match_device(entry.serial_pattern, usb_devices)
            if usb_device is None:
                results.append((entry, False, "Device not found"))
                continue

            flash_result = flash_device(
                device_path=usb_device.path,
                firmware_path=firmware_path,
                katapult_dir=katapult_dir,
                klipper_dir=klipper_dir,
            )

            if flash_result.success:
                verified, _, error = wait_for_device(entry.serial_pattern, timeout=30.0)
                results.append((entry, verified, error))
                out.success(f"{entry.name} flashed ({i+1}/{total})")
            else:
                results.append((entry, False, flash_result.error_message))
                out.warn(f"{entry.name} flash failed ({i+1}/{total})")

    return results
```

### Summary Table
```python
def _print_summary(results, out):
    """Print batch flash summary table."""
    out.info("Summary", "")
    out.info("Summary", f"{'Device':<20} {'Build':>6} {'Flash':>6} {'Verify':>7}")
    out.info("Summary", f"{'-'*20} {'-'*6} {'-'*6} {'-'*7}")
    for r in results:
        build = "PASS" if r.build_ok else "FAIL"
        flash = "PASS" if r.flash_ok else ("SKIP" if not r.build_ok else "FAIL")
        verify = "PASS" if r.verify_ok else ("SKIP" if not r.flash_ok else "FAIL")
        out.info("Summary", f"{r.device_name:<20} {build:>6} {flash:>6} {verify:>7}")
```

### Version Check with Selective Flash
```python
def _version_check(devices, host_version, mcu_versions, out):
    """Check versions and let user select which to flash."""
    all_match = True
    match_status = {}
    for entry in devices:
        ver = get_mcu_version_for_device(entry.mcu)
        if ver and not is_mcu_outdated(host_version, ver):
            match_status[entry.key] = "current"
        else:
            match_status[entry.key] = "outdated"
            all_match = False

    if all_match:
        if not out.confirm("All devices match host version. Flash anyway?", default=False):
            return []  # User cancelled
        return devices  # Flash all

    # Some match, some don't — offer selective
    outdated = [e for e in devices if match_status[e.key] == "outdated"]
    current = [e for e in devices if match_status[e.key] == "current"]

    out.info("Version", f"{len(outdated)} outdated, {len(current)} current")
    for e in outdated:
        out.info("Version", f"  [outdated] {e.name}")
    for e in current:
        out.info("Version", f"  [current]  {e.name}")

    if out.confirm("Flash only outdated devices?", default=True):
        return outdated
    return devices  # Flash all
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-device Klipper restart | Single stop/start for batch | Phase 14 | Reduces downtime from N*restart to 1*restart |
| Interactive menuconfig per device | skip_menuconfig with cached configs | Phase 13 | Enables unattended batch builds |

## Open Questions

1. **Firmware storage between build and flash**
   - What we know: All builds output to `~/klipper/out/klipper.bin`, overwriting each other.
   - What's unclear: Best temp directory pattern on Raspberry Pi (tmpfs at `/tmp` vs persistent).
   - Recommendation: Use `tempfile.mkdtemp(prefix="kalico-flash-")` for the batch session. Copy `klipper.bin` after each build. Clean up after batch completes. `/tmp` on RPi is typically tmpfs (RAM-backed), which is fine for small firmware files (<1MB each).

2. **Post-flash version reporting**
   - What we know: Klipper needs time to reconnect to MCUs after restart.
   - What's unclear: How long to wait before Moonraker can report updated MCU versions.
   - Recommendation: Don't wait for post-flash version in the summary. Show build/flash/verify status only. Users can check versions via the main screen after Klipper stabilizes.

3. **Registration order**
   - What we know: Context says "flash in registration order (order devices were added to registry)."
   - What's unclear: Current registry uses a dict (JSON object) which doesn't guarantee insertion order in the file, though Python 3.7+ dicts maintain insertion order.
   - Recommendation: Use `registry.load().devices` dict iteration order, which preserves insertion order in Python 3.9+. The JSON file sorts keys alphabetically (`sort_keys=True` in `_atomic_write_json`), so actual order is **alphabetical by key**, not insertion order. Either change to use a list in JSON, or accept alphabetical order. Recommend: accept alphabetical order — it's deterministic and predictable. Document this as "alphabetical by device key" rather than "registration order."

4. **Quiet build mode**
   - What we know: `run_build()` currently uses inherited stdio (no PIPE).
   - What's unclear: Whether adding `quiet` parameter is the cleanest approach.
   - Recommendation: Add `quiet: bool = False` to `run_build()`. When True, pass `capture_output=True` to subprocess. Minimal change, backward-compatible.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: All source files in `kflash/` read and analyzed
- `flash.py` `cmd_flash()` — existing single-device workflow (lines 399-998)
- `build.py` `run_build()` — build implementation (lines 63-141)
- `service.py` `klipper_service_stopped()` — service context manager (lines 141-172)
- `flasher.py` `flash_device()` — flash implementation (lines 154-228)
- `tui.py` `wait_for_device()` — verification (lines 590-646)
- `moonraker.py` — version checking functions
- `config.py` `ConfigManager` — per-device config management
- `models.py` — all dataclass contracts
- `registry.py` — device registry and global config persistence

### Secondary (MEDIUM confidence)
- `14-CONTEXT.md` — user decisions constraining implementation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib only, all tools exist in codebase
- Architecture: HIGH — orchestration of existing modules, patterns clear
- Pitfalls: HIGH — identified from direct code analysis (shared .config, firmware path collision, device re-scan)

**Research date:** 2026-01-29
**Valid until:** 2026-02-28 (stable domain, no external dependencies)
