# Quick Task 012: Menuconfig Prompt After Add Device

## One-liner
Y/n prompt after device registration offers immediate menuconfig with config caching

## What Was Done

Added a post-registration menuconfig prompt to `cmd_add_device` in `kflash/flash.py`. After successfully registering a device, the user is now asked "Run menuconfig now to configure firmware? (Y/n)" with default=True. Accepting launches menuconfig for the new device and caches the resulting config. Declining returns success silently.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add menuconfig prompt after device registration | 9cd8ded | kflash/flash.py |

## Implementation Details

- Uses `out.step_divider()` before the prompt for visual separation
- Loads global config from registry to get `klipper_dir`
- Creates `ConfigManager` for the new device key
- Loads cached config if exists, otherwise starts fresh
- Calls `run_menuconfig()` directly (not full `cmd_build`) -- menuconfig only, no compilation
- Saves config to cache via `config_mgr.save_cached_config()` if menuconfig saved
- All errors are caught and warned -- device registration is never rolled back
- Works from all entry points: CLI `--add-device`, TUI Add Device, TUI Config Device unregistered path

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- Local import verification passed
- Pi SSH unavailable (connection timeout) -- manual Pi testing deferred
