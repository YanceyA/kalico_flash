# Quick Task 009: Flash-All Config Validation Guard

**One-liner:** Blocked-device filtering, MCU mismatch detection, and config age display in flash-all Stage 1

## What Was Done

### Task 1: Config age display helper
- Added `get_cache_age_display()` to `ConfigManager` in `kflash/config.py`
- Returns human-readable strings: "N minutes ago", "N hours ago", "N days ago"
- Configs 90+ days old append "(recommend review)"
- Commit: `b35cacd`

### Task 2: Hardened flash-all Stage 1 validation
- Enhanced `cmd_flash_all` in `kflash/flash.py` with three new checks:
  1. **Blocked device filter:** Uses existing `_build_blocked_list` / `_blocked_reason_for_entry` to skip blocked devices with warning. Aborts if all blocked.
  2. **MCU validation:** Loads each cached config, calls `validate_mcu()`, aborts with clear guidance on mismatch. Wraps in try/except ConfigError for corrupt configs.
  3. **Config age display:** Shows age for each validated device, warns on stale (90+ day) configs without blocking.
- Validation order: flashable check -> blocked filter -> missing config -> MCU match -> age display
- Single-device `cmd_flash` completely unchanged
- Commit: `60aa5f8`

## Deviations from Plan

None - plan executed exactly as written.

## Files Modified

| File | Change |
|------|--------|
| `kflash/config.py` | Added `get_cache_age_display()` method, `import time` |
| `kflash/flash.py` | Enhanced Stage 1 with blocked filter, MCU validation, age display |
