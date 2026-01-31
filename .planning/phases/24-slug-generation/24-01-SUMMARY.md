# Phase 24 Plan 01: Slug Generation Summary

**One-liner:** Pure slug generator with Unicode folding, dot-to-hyphen conversion, and collision suffixing in validation.py

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement generate_device_key() | 581ac0f | kflash/validation.py |

## What Was Built

Added `generate_device_key(name, registry) -> str` to `kflash/validation.py`. The function:

- Normalizes Unicode via NFKD decomposition and ASCII folding
- Converts dots, spaces, and underscores to hyphens
- Strips non-alphanumeric/non-hyphen characters
- Collapses consecutive hyphens
- Truncates to 64 characters with clean edges
- Raises ValueError on empty result
- Appends numeric suffix (-2, -3, ...) on registry collision

## Deviations from Plan

**1. [Rule 1 - Bug] Dot handling missing from plan spec**

- **Found during:** Task 1 verification
- **Issue:** Plan specified stripping `[^a-z0-9-]` which removes dots, but "v1.1" should become "v1-1" not "v11"
- **Fix:** Added `.replace(".", "-")` before the strip regex
- **Files modified:** kflash/validation.py

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Dots converted to hyphens (not stripped) | "Octopus Pro v1.1" -> "octopus-pro-v1-1" matches success criteria |

## Verification

- All smoke tests passed on Pi (basic slug, special chars, hyphen collapse, truncation, empty ValueError, collision)
- `--list-devices` works without regression

## Duration

~3 minutes
