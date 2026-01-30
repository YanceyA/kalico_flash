# Requirements: v3.1 Config Validation

**Defined:** 2026-01-30
**Core Value:** One command to build and flash any registered board — no remembering serial paths, flash commands, or config locations.

## v3.1 Requirements

### Path Validation

- [ ] **PATH-01**: klipper_dir setting validates expanded path exists as directory
- [ ] **PATH-02**: klipper_dir setting validates directory contains `Makefile` (confirms Klipper source)
- [ ] **PATH-03**: katapult_dir setting validates expanded path exists as directory
- [ ] **PATH-04**: katapult_dir setting validates directory contains `scripts/flashtool.py` (confirms Katapult source)
- [ ] **PATH-05**: config_cache_dir setting validates expanded path exists as directory
- [ ] **PATH-06**: Invalid path rejected with clear error message, user re-prompted for new value
- [ ] **PATH-07**: Path validation expands `~` before checking existence

### Numeric Validation

- [ ] **NUM-01**: stagger_delay rejects values outside 0–30 seconds with error and re-prompt
- [ ] **NUM-02**: return_delay rejects values outside 0–60 seconds with error and re-prompt
- [ ] **NUM-03**: Non-numeric input rejected with error and re-prompt

## Future Requirements

### Deferred

- **Registry JSON integrity** — Handle corrupt/malformed JSON, missing fields, wrong types on load
- **Device entry validation** — Validate MCU types, serial patterns, device keys when adding devices

## Out of Scope

| Feature | Reason |
|---------|--------|
| Auto-create missing directories | User should create intentionally; existence-only check for config_cache_dir |
| Registry JSON schema validation | Separate concern, defer to future milestone |
| Device field validation at add time | Separate concern, defer to future milestone |
| Runtime path re-validation before flash | Validated at config time is sufficient; paths don't move between settings changes |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PATH-01 | Phase 15 | Pending |
| PATH-02 | Phase 15 | Pending |
| PATH-03 | Phase 15 | Pending |
| PATH-04 | Phase 15 | Pending |
| PATH-05 | Phase 15 | Pending |
| PATH-06 | Phase 15 | Pending |
| PATH-07 | Phase 15 | Pending |
| NUM-01 | Phase 15 | Pending |
| NUM-02 | Phase 15 | Pending |
| NUM-03 | Phase 15 | Pending |

**Coverage:**
- v3.1 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0

---
*Requirements defined: 2026-01-30*
*Last updated: 2026-01-30 after initial definition*
