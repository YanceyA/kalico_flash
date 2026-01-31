# Plan: Soft-deprecate CLI hints in favor of TUI action prompts

## Goal
When error/hint messages are shown in a TUI context, recommend the TUI action (e.g., "Press A to add a device") instead of the CLI command (e.g., `kflash --add-device`). CLI commands remain valid and are still shown in CLI-only contexts (argparse help, `--help`, non-TTY).

## Mapping of CLI hints to TUI equivalents

| # | File:Line | Current message | TUI replacement | Context |
|---|-----------|----------------|-----------------|---------|
| 1 | `flash.py:295` | `"Run --add-device first."` | `"Press A to add a device."` | Reachable from TUI |
| 2 | `flash.py:445` | `"Run --add-device first."` | `"Press A to add a device."` | Reachable from TUI |
| 3 | `flash.py:536` | `"kflash --list-devices"` / `"kflash --add-device"` | `"Press D to refresh devices"` / `"Press A to add a device"` | Recovery text — may be TUI |
| 4 | `flash.py:674` | `"run \`kflash --include-device {key}\`"` | Generic: `"This device is excluded from flashing."` (no CLI ref) | Reachable from TUI |
| 5 | `flash.py:1078` | `"Run --add-device first."` | `"Press A to add a device."` | flash_all, TUI only |
| 6 | `flash.py:1094` | `"Use --add-device to register boards."` | `"Press A to register a MCU."` | flash_all, TUI only |
| 7 | `flash.py:1129` | `"Run 'kflash -d <device>' for each..."` | `"Flash each device individually first (press F)."` | flash_all, TUI only |
| 8 | `flash.py:1149` | `"Run 'kflash -d <device>' for each..."` | `"Flash each mismatched device individually to reconfigure (press F)."` | flash_all, TUI only |
| 9 | `flash.py:1160` | `"consider running 'kflash -d {key}' to review"` | `"consider flashing individually to review config"` | flash_all, TUI only |
| 10 | `flash.py:1533` | `"Run --add-device to register a board."` | `"Press A to register a MCU."` | Has `from_menu` guard — only shows in CLI |
| 11 | `flash.py:1603` | `"Use --add-device to register unknown devices."` | Already guarded by `from_menu` — CLI only | No change needed |
| 12 | `flash.py:1803` | `"used with --device flag"` | Shown during add-device wizard — keep as-is (informational) | No change |
| 13 | `errors.py:97-98` | `"kflash --list-devices"` / `"kflash --add-device"` | Needs `from_menu` variant | Template system |
| 14 | `errors.py:108` | `"re-register with \`--add-device\`"` | Needs `from_menu` variant | Template system |
| 15 | `errors.py:116` | `"Run without --skip-menuconfig"` | Only relevant in CLI mode | No change |
| 16 | `errors.py:206-207` | `"kflash --include-device"` / `"kflash --list-devices"` | Needs TUI variant | Template system |
| 17 | `tui.py:467` | `"Run with --help for usage information."` | Remove or change to `"Run 'kflash' for the interactive menu."` | Non-TTY fallback |

## Implementation approach

### Strategy: Pass a `from_tui: bool` flag to functions that emit user-facing hints

For messages in `flash.py` that are only reachable from TUI flows (items 5-9 above, all in `flash_all`), just change the strings directly since `flash_all` is TUI-only.

For messages reachable from both CLI and TUI (items 1-4, 13-14, 16), add a `from_tui` parameter or check an existing context flag to select the appropriate message.

### Files to modify

1. **`kflash/flash.py`** — Update ~10 message strings with TUI-aware alternatives
2. **`kflash/errors.py`** — Add TUI-variant recovery text to error templates (items 13, 14, 16)
3. **`kflash/tui.py`** — Update line 467

### Detailed changes

**flash.py — flash_all function (TUI-only, direct string changes):**
- Line 1078: `"Global config not set. Run --add-device first."` -> `"Global config not set. Press A to add a device first."`
- Line 1094: `"No flashable devices registered. Use --add-device to register boards."` -> `"No flashable devices registered. Press A to register a MCU."`
- Line 1129: `"Run 'kflash -d <device>' for each to configure before using Flash All."` -> `"Flash each device individually and save config before using Flash All."`
- Line 1149: `"Run 'kflash -d <device>' for each mismatched device to reconfigure."` -> `"Flash each mismatched device individually to reconfigure."`
- Line 1160: `"consider running 'kflash -d {entry.key}' to review"` -> `"consider flashing individually to review config"`

**flash.py — dual-context functions (need `from_tui` param or context check):**
- Lines 295, 445: These are in functions called from both CLI and TUI paths. Add conditional: if TUI context -> `"Press A to add a device first."`, else keep CLI text.
- Line 536: Recovery text in discovery — add TUI-aware variant.
- Line 674: `--include-device` hint — generic: `"This device is excluded from flashing."`

**errors.py — template system:**
- Add a `tui_recovery` field or a formatting function that swaps CLI commands for TUI hints when `from_tui=True`.

**tui.py:467:**
- Change to `"Run 'kflash' to launch the interactive menu."` or remove.

## Verification
- Run `kflash` on the Pi and trigger each error scenario to verify TUI messages show correctly
- Run `kflash --list-devices` and other CLI commands to verify CLI messages are unchanged
- `grep -r "kflash -\|--add-device\|--list-devices\|--remove-device\|--include-device" kflash/` to confirm no un-updated CLI references in TUI paths
