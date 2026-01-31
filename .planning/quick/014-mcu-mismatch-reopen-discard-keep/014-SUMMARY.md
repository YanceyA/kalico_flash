# Quick 014: MCU Mismatch Re-open/Discard/Keep Summary

**One-liner:** Replace MCU mismatch "press Enter" with interactive R/D/K loop deferring cache save until after validation

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | ea4b23b | Add mcu_mismatch_choice to output protocol |
| 2 | 327490e | R/D/K mismatch loop in cmd_add_device |
| 3 | 538417b | R/D/K mismatch loop in TUI config screen |

## Changes

### output.py
- Added `mcu_mismatch_choice(actual_mcu, expected_mcu, device_key)` to Output Protocol, CliOutput, NullOutput
- CliOutput shows warning and prompts R/D/K in a loop
- NullOutput returns 'k' (keep) as safe non-interactive default

### flash.py (cmd_add_device)
- Deferred `save_cached_config()` until after MCU validation passes or user picks Keep
- Added `had_cache` flag before menuconfig to enable Discard restore
- Replaced mismatch warning+Enter with R/D/K loop
- Fixed all `out.warning()` calls to `out.warn()`

### tui.py (_device_config_screen)
- Same deferred-save pattern with inline R/D/K prompt using theme colors
- Added `had_cache` flag before menuconfig
- Discard restores old cache or clears klipper .config if none existed

## Deviations from Plan

None - plan executed exactly as written.

## Duration

~3 minutes
