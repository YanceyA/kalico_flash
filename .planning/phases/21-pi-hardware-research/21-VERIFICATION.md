---
phase: 21-pi-hardware-research
verified: 2026-01-31T07:01:14Z
status: passed
score: 5/5 must-haves verified
---

# Phase 21: Pi Hardware Research Verification Report

**Phase Goal:** Resolve all open hardware questions via SSH testing on live Pi with connected boards
**Verified:** 2026-01-31T07:01:14Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | sysfs path resolution algorithm is documented with verified Python code | ✓ VERIFIED | 21-01-SUMMARY.md RES-01 section contains working `resolve_usb_authorized()` function tested on all 4 devices |
| 2 | MCU serial substring persistence across Klipper/Katapult modes is confirmed | ✓ VERIFIED | 21-01-SUMMARY.md RES-02 section documents hex serial identical across modes, verified on live Klipper→Katapult transition |
| 3 | Timing measurements for bootloader entry, sysfs reset, and re-enumeration are recorded | ✓ VERIFIED | 21-01-SUMMARY.md RES-03 section contains table with measured durations: flashtool.py -r ~1367ms, sysfs reset ~1063ms, re-enum ~500ms |
| 4 | flashtool.py -r behavior under all three scenarios is documented | ✓ VERIFIED | 21-01-SUMMARY.md RES-04 section contains behavior table: Klipper running (success), service active (fails), already Katapult (no-op) |
| 5 | Beacon probe exclusion via existing prefix check is confirmed | ✓ VERIFIED | 21-01-SUMMARY.md RES-05 section confirms Beacon uses `usb-Beacon_*` prefix, naturally excluded by `usb-Klipper_`/`usb-katapult_` filter |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.planning/phases/21-pi-hardware-research/21-01-SUMMARY.md` | Consolidated research findings for Phase 22 implementation | ✓ VERIFIED | EXISTS (122 lines), SUBSTANTIVE (complete frontmatter + all 5 RES sections with code/data/decisions), WIRED (referenced by 21-RESEARCH.md, provides implementation constants for Phase 22) |
| `.planning/phases/21-pi-hardware-research/21-RESEARCH.md` | Detailed research log with high-confidence findings | ✓ VERIFIED | EXISTS (279 lines), SUBSTANTIVE (5 architecture patterns with verified code, timing data, pitfalls, metadata), WIRED (source material for SUMMARY.md) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| 21-RESEARCH.md | 21-01-SUMMARY.md | Research distilled into implementation-ready summary | ✓ WIRED | SUMMARY frontmatter lists RESEARCH.md in context; all 5 RES findings from RESEARCH appear in SUMMARY with implementation-ready format (code snippets, constants, decisions) |
| 21-01-SUMMARY.md | Phase 22 implementation | Implementation-ready constants/patterns | ✓ READY | SUMMARY provides: sysfs resolution algorithm (copy-paste ready), serial extraction regex, timing constants (250ms poll/5s timeout), flashtool.py behavior constraints, Beacon exclusion confirmation |

### Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| RES-01: sysfs path resolution | ✓ VERIFIED | SUMMARY RES-01 section: Algorithm documented with working Python code tested on 4 devices. Symlink resolution: /dev/serial/by-id/ → /sys/class/tty/{tty}/device → parent dir → authorized file |
| RES-02: Serial substring matching | ✓ VERIFIED | SUMMARY RES-02 section: Hex serial verified identical across Klipper→Katapult transition on live Octopus Pro. Extraction regex provided: `usb-(?:Klipper\|katapult)_[a-zA-Z0-9]+_([A-Fa-f0-9]+)` |
| RES-03: Timing measurements | ✓ VERIFIED | SUMMARY RES-03 section: Table with measured durations for all operations. Recommended polling: 250ms interval, 5s timeout |
| RES-04: flashtool.py -r behavior | ✓ VERIFIED | SUMMARY RES-04 section: Table documents 3 scenarios (Klipper stopped=success, service active=fail, already Katapult=no-op). Critical finding: service MUST be stopped |
| RES-05: Beacon exclusion | ✓ VERIFIED | SUMMARY RES-05 section: Beacon device name `usb-Beacon_*` naturally excluded by existing discovery filter. No special logic needed |

### Anti-Patterns Found

None. This is a research-only phase with no code implementation. Documentation quality is high.

### Phase-Specific Verification Notes

**Research-Only Phase:** This phase has NO source code to verify. All must-haves are documentation artifacts.

**Verification Approach:**
- Level 1 (Existence): Confirmed 21-01-SUMMARY.md and 21-RESEARCH.md exist
- Level 2 (Substantive): Checked that SUMMARY contains findings for ALL 5 requirements (RES-01 through RES-05) with working code examples, measured data, and implementation-ready constants
- Level 3 (Wired): Verified SUMMARY distills RESEARCH findings into format consumable by Phase 22 (copy-paste-ready algorithms, timing constants, behavioral constraints)

**All 5 Success Criteria from ROADMAP Met:**
1. ✓ sysfs path resolution: `/sys/class/tty/{tty}/device` symlink approach documented with working `resolve_usb_authorized()` function tested on 4 devices
2. ✓ MCU serial substring: Verified identical across Klipper/Katapult modes via live hardware transition on Octopus Pro
3. ✓ Timing measurements: Table with flashtool.py -r (~1.4s), sysfs reset (~1s), re-enum (~0.5s). Recommended polling: 250ms/5s
4. ✓ flashtool.py -r behavior: 3 scenarios tested (Klipper stopped, service active, already Katapult). Key finding: service must be stopped
5. ✓ Beacon probe: Confirmed excluded via `usb-Beacon_*` prefix, no special logic needed

**Implementation Readiness for Phase 22:**
- sysfs resolution algorithm: Copy-paste ready Python code
- Serial extraction regex: Tested pattern provided
- Timing constants: 250ms poll interval, 5s timeout
- Service lifecycle constraint: flashtool.py requires Klipper stopped (existing context manager handles this)
- Beacon exclusion: No additional code needed, existing discovery filter sufficient

**Open Questions Documented:**
- RP2040 bootloader behavior (STM32 verified, RP2040 deferred to avoid disrupting Nitehawk)
- sysfs authorized without sudo (udev rules optimization deferred to v2+)

Both open questions are explicitly documented in SUMMARY with rationale for deferral. They do NOT block Phase 22 implementation (Phase 22 focuses on STM32 detection, RP2040 can be tested later).

---

_Verified: 2026-01-31T07:01:14Z_
_Verifier: Claude (gsd-verifier)_
