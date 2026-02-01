# Requirements: kalico-flash v4.1

**Defined:** 2026-02-01
**Core Value:** One command to build and flash any registered board — no remembering serial paths, flash commands, or config locations.

## v4.1 Requirements

### Flash All Safety

- [ ] **SAFE-01**: Flash All calls `_preflight_flash()` (or batch-safe variant) once before entering the batch loop — fails early if Klipper dir, Makefile, make command, or Katapult flashtool are missing
- [ ] **SAFE-02**: Flash All prompts for confirmation when Moonraker is unreachable (`get_print_status()` returns None), matching the single-device flow behavior
- [ ] **SAFE-03**: Hardware MCU cross-check before flashing — derive MCU type from connected USB device via `extract_mcu_from_serial()` and compare to registry `entry.mcu`. Single-device interactive: warn and require confirmation on mismatch. Flash All: skip device and report mismatch. Best-effort (skip check if extraction returns None).
- [ ] **SAFE-04**: Flash All tracks used USB paths (`used_paths: set[str]`) to prevent the same physical USB device being targeted by two different registry entries

### Flash All Debuggability

- [ ] **DBUG-01**: Flash All captures build stdout/stderr and on failure shows the last 20 lines inline in the batch summary. Full output stored in `BuildResult.error_output`.

### Settings Cleanup

- [ ] **CONF-01**: Remove `config_cache_dir` setting from GlobalConfig (models.py), registry serialization (registry.py), settings UI (screen.py), and validation (validation.py). `get_config_dir()` continues using XDG convention.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Unit tests | Deferred — separate milestone |
| Non-interactive/batch mode (`--yes`, `--force`) | CLI deprecated, TUI is inherently interactive |
| `build_flash_candidates()` refactor (finding 4) | Post-beta cleanup, not a bug fix |
| Config cache dir implementation | Removing the dead setting instead |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SAFE-01 | — | Pending |
| SAFE-02 | — | Pending |
| SAFE-03 | — | Pending |
| SAFE-04 | — | Pending |
| DBUG-01 | — | Pending |
| CONF-01 | — | Pending |

**Coverage:**
- v4.1 requirements: 6 total
- Mapped to phases: 0
- Unmapped: 6 ⚠️

---
*Requirements defined: 2026-02-01*
*Last updated: 2026-02-01 after initial definition*
