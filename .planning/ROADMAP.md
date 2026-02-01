# Roadmap: kalico-flash v4.1

## Milestones

- v1.0 through v4.0: Shipped (phases 1-27)
- v4.1 Flash All Safety & Cleanup: Phases 28-30 (in progress)

## Phases

- [ ] **Phase 28: Flash All Preflight** - Preflight checks and duplicate guard before batch loop
- [ ] **Phase 29: Flash Workflow Hardening** - MCU cross-check and build error surfacing
- [ ] **Phase 30: Dead Setting Removal** - Remove unused config_cache_dir from codebase

## Phase Details

### Phase 28: Flash All Preflight
**Goal**: Flash All fails fast on environment problems and prevents duplicate device targeting
**Depends on**: Nothing (first phase in milestone)
**Requirements**: SAFE-01, SAFE-02, SAFE-04
**Success Criteria** (what must be TRUE):
  1. Flash All aborts before flashing any device if Klipper dir, Makefile, make, or Katapult flashtool are missing
  2. Flash All prompts user for confirmation when Moonraker is unreachable, matching single-device behavior
  3. Flash All skips a device when its resolved USB path was already used by a prior device in the batch, and reports the skip
**Plans**: TBD

Plans:
- [ ] 28-01: TBD

### Phase 29: Flash Workflow Hardening
**Goal**: Flash workflows detect MCU mismatches and surface build failures clearly
**Depends on**: Phase 28
**Requirements**: SAFE-03, DBUG-01
**Success Criteria** (what must be TRUE):
  1. Single-device flash warns and requires confirmation when USB-derived MCU type does not match registry entry
  2. Flash All skips a device and reports it when USB-derived MCU type does not match registry entry
  3. MCU cross-check is skipped gracefully when extraction returns None (best-effort)
  4. Flash All shows last 20 lines of build output inline when a build fails, and full output is available in BuildResult.error_output
**Plans**: TBD

Plans:
- [ ] 29-01: TBD

### Phase 30: Dead Setting Removal
**Goal**: config_cache_dir setting no longer exists anywhere in the codebase
**Depends on**: Nothing (independent cleanup)
**Requirements**: CONF-01
**Success Criteria** (what must be TRUE):
  1. GlobalConfig in models.py has no config_cache_dir field
  2. Registry serialization in registry.py neither reads nor writes config_cache_dir
  3. Settings screen in screen.py does not show config_cache_dir option
  4. Validation in validation.py has no config_cache_dir references
**Plans**: TBD

Plans:
- [ ] 30-01: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 28. Flash All Preflight | v4.1 | 0/? | Not started | - |
| 29. Flash Workflow Hardening | v4.1 | 0/? | Not started | - |
| 30. Dead Setting Removal | v4.1 | 0/? | Not started | - |
