# Requirements: kalico-flash v4.0

**Defined:** 2026-01-31
**Core Value:** One command to build and flash any registered board — no remembering serial paths, flash commands, or config locations.

## v4.0 Requirements

Requirements for CLI removal and device key internalization.

### CLI Removal

- [ ] **CLI-01**: `kflash` launches directly into TUI menu with no argument parsing
- [ ] **CLI-02**: Running `kflash --device X` or any old flag prints a friendly migration message and exits
- [ ] **CLI-03**: All argparse setup, `_parse_args()`, and flag-driven command routing removed from flash.py
- [ ] **CLI-04**: Late-import branches that only existed for CLI code paths removed

### Key Internalization

- [ ] **KEY-01**: New devices get auto-generated slug key from display name (e.g., "Octopus Pro v1.1" to `octopus-pro-v1-1`)
- [ ] **KEY-02**: Slug collision handling appends numeric suffix (`-2`, `-3`) when key already exists
- [ ] **KEY-03**: Add-device wizard no longer prompts for device key — only display name
- [ ] **KEY-04**: Device config screen removes key edit option and hides internal key entirely
- [ ] **KEY-05**: All user-facing output shows `entry.name` instead of `entry.key`
- [ ] **KEY-06**: Existing devices.json keys preserved as-is (no migration, no re-derivation)

### Documentation & Cleanup

- [ ] **DOC-01**: README updated to remove CLI reference section, document TUI-only usage
- [ ] **DOC-02**: CLAUDE.md updated to remove CLI commands section
- [ ] **DOC-03**: Error/recovery messages updated to reference TUI actions instead of CLI flags
- [ ] **DOC-04**: install.sh updated if needed (kflash symlink stays, just remove any flag references)

## Future Requirements

- SHA256 change detection to skip rebuild when config unchanged
- --no-clean flag for incremental builds (becomes TUI toggle)
- CAN bus device support

## Out of Scope

| Feature | Reason |
|---------|--------|
| Re-derive existing keys from names | Breaks config cache directory matching, unnecessary risk |
| Let users edit auto-generated keys | Defeats simplification purpose |
| Keep any CLI flags "just in case" | Two code paths forever, maintenance burden |
| Generate keys from MCU type or serial | Not human-meaningful, confusing cache directories |
| Prompt user to confirm auto-generated key | Friction for zero value |
| Data migration script for devices.json | Existing keys already valid internal identifiers |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLI-01 | Phase 26 | Pending |
| CLI-02 | Phase 26 | Pending |
| CLI-03 | Phase 26 | Pending |
| CLI-04 | Phase 26 | Pending |
| KEY-01 | Phase 24 | Complete |
| KEY-02 | Phase 24 | Complete |
| KEY-03 | Phase 25 | Pending |
| KEY-04 | Phase 25 | Pending |
| KEY-05 | Phase 25 | Pending |
| KEY-06 | Phase 25 | Pending |
| DOC-01 | Phase 27 | Pending |
| DOC-02 | Phase 27 | Pending |
| DOC-03 | Phase 27 | Pending |
| DOC-04 | Phase 27 | Pending |

**Coverage:**
- v4.0 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0

---
*Requirements defined: 2026-01-31*
*Last updated: 2026-01-31 after roadmap creation*
