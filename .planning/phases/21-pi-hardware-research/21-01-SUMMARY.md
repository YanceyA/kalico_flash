---
phase: 21-pi-hardware-research
plan: 01
status: complete
subsystem: hardware-research
tags: [sysfs, usb, katapult, bootloader, serial-matching, timing]
depends_on: []
affects: [22-core-detection-engine]
tech-stack:
  added: []
  patterns: [sysfs-symlink-resolution, serial-substring-matching, usb-reset-via-authorized]
key-files:
  created: []
  modified: []
decisions:
  - id: D-21-01
    description: "Use /sys/class/tty/{name}/device symlink for sysfs resolution (not udevadm)"
    rationale: "Pure Python stdlib, no external binary dependency, tested on all 4 devices"
  - id: D-21-02
    description: "Use sudo for sysfs authorized file writes"
    rationale: "MainsailOS has passwordless sudo; udev rules optimization deferred to v2+"
  - id: D-21-03
    description: "Match devices across modes via hex serial substring, not prefix"
    rationale: "Prefix changes between Klipper/katapult; serial number is stable hardware ID"
metrics:
  duration: "~10 minutes (research was pre-completed; this plan formalizes findings)"
  completed: 2026-01-31
---

# Phase 21 Plan 01: Pi Hardware Research Summary

**One-liner:** Live Pi SSH testing confirmed sysfs resolution algorithm, serial substring persistence, USB reset timing, flashtool.py -r behavior, and Beacon exclusion -- all five research requirements satisfied with HIGH confidence.

## What Was Done

All five research requirements (RES-01 through RES-05) were answered via live SSH testing on a Raspberry Pi with four connected USB devices: STM32H723 (Octopus Pro), RP2040 (Nitehawk), STM32F411, and Beacon probe. Every finding was directly observed and verified with working Python code.

## Key Findings (Implementation-Ready for Phase 22)

### RES-01: sysfs Path Resolution

Algorithm: `/dev/serial/by-id/` symlink -> real tty -> `/sys/class/tty/{tty}/device` -> parent dir -> `authorized` file.

```python
import os

def resolve_usb_authorized(serial_by_id_path: str) -> str:
    real_dev = os.path.realpath(serial_by_id_path)
    tty_name = os.path.basename(real_dev)
    sysfs_link = f"/sys/class/tty/{tty_name}/device"
    iface_path = os.path.realpath(sysfs_link)
    usb_dev_path = os.path.dirname(iface_path)
    return os.path.join(usb_dev_path, "authorized")
```

Tested on all 4 devices. Interface path ends with colon-separated config (e.g., `3-1:1.0`); parent is USB device level.

### RES-02: Serial Substring Matching

Format: `usb-{Klipper|katapult}_{mcu_type}_{serial}-if00`

Hex serial is identical across Klipper and Katapult modes. Verified on live Klipper-to-Katapult transition with Octopus Pro.

Extraction regex: `usb-(?:Klipper|katapult)_[a-zA-Z0-9]+_([A-Fa-f0-9]+)` (case-insensitive)

Cross-mode pattern: `usb-*_{mcu_type}_{serial}*`

### RES-03: Timing Constants

| Operation | Duration |
|-----------|----------|
| flashtool.py -r (bootloader entry + re-enum) | ~1,367 ms |
| sysfs deauthorize + reauthorize | ~1,063 ms (500ms sleep) |
| Re-enumeration after reauthorize | ~500 ms |
| flashtool.py -r on already-Katapult | <100 ms |

**Recommended polling:** 250ms interval, 5s timeout.

### RES-04: flashtool.py -r Behavior

| Scenario | Result | Exit Code |
|----------|--------|-----------|
| Klipper running, service stopped | Success, enters bootloader | 0 |
| Klipper running, service active | Fails "Serial device in use" | 1 |
| Already in Katapult | Success (no-op) | 0 |

Critical: Klipper service MUST be stopped before flashtool.py calls. Existing `klipper_service_stopped()` context manager handles this.

### RES-05: Beacon Probe Exclusion

Beacon device name: `usb-Beacon_Beacon_RevH_...` -- does NOT match `usb-Klipper_` or `usb-katapult_` prefix. Naturally excluded by existing discovery filter. No special exclusion logic needed.

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| D-21-01 | Use sysfs symlink approach, not udevadm | Pure Python stdlib, no external dependency |
| D-21-02 | Use sudo for authorized file writes | Standard on MainsailOS; udev rules deferred |
| D-21-03 | Match across modes via serial substring | Prefix changes between modes; serial is stable |

## Deviations from Plan

None -- plan executed exactly as written.

## Open Questions

1. **RP2040 bootloader entry behavior** -- STM32H723 verified with flashtool.py -r. RP2040 may use BOOTSEL instead of Katapult. Not tested to avoid disrupting Nitehawk. Document as "STM32 verified, RP2040 TBD" for Phase 22.

2. **sysfs authorized without sudo** -- udev rules could potentially grant group write access. Deferred to v2+ optimization.

## Files Changed

None -- research-only phase. No source code was created or modified.

## Next Phase Readiness

Phase 22 (Core Detection Engine) can proceed with:
- Verified sysfs resolution algorithm (copy directly)
- Serial extraction regex (tested)
- Timing constants for polling (250ms/5s)
- Knowledge that flashtool.py -r requires Klipper stopped
- Confidence that Beacon is auto-excluded
