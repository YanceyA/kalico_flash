# Phase 14 Plan 01: Flash All Batch Orchestration Summary

**One-liner:** BatchDeviceResult dataclass, quiet build mode, and 5-stage cmd_flash_all() with continue-on-failure and single Klipper stop

## What Was Built

- `BatchDeviceResult` dataclass in models.py tracking per-device config/build/flash/verify status
- `quiet` parameter on `run_build()` to suppress stdout/stderr during batch builds
- `cmd_flash_all()` in flash.py implementing 5-stage batch orchestration:
  1. Validate all flashable devices have cached configs
  2. Version check with Moonraker — prompt if all/some devices already current
  3. Sequential quiet builds with firmware copies to temp directory
  4. Single `klipper_service_stopped()` wrapping all flash operations with stagger delay
  5. Summary table with Build/Flash/Verify pass/fail/skip per device

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Continue-on-failure for both build and flash | One device error must never block remaining devices |
| Firmware copied to temp dir per device | Avoids path collision when building sequentially for different MCUs |
| Re-scan USB after Klipper stop and after each flash | Device paths may change; fresh scan ensures correct targeting |
| Moonraker unavailable gracefully skips version check | Flash All should work even without Moonraker running |

## Commits

| Hash | Description |
|------|-------------|
| 1af247d | feat(14-01): add BatchDeviceResult dataclass and quiet build mode |
| b7e39b8 | feat(14-01): implement cmd_flash_all() batch orchestration |

## Files Modified

- `kflash/models.py` — Added BatchDeviceResult dataclass
- `kflash/build.py` — Added quiet parameter to run_build()
- `kflash/flash.py` — Added cmd_flash_all() function (~230 lines)

## Deviations from Plan

None -- plan executed exactly as written.

## Verification

- [x] BatchDeviceResult exists with all required fields (device_key, device_name, config_ok, build_ok, flash_ok, verify_ok, error_message, skipped)
- [x] run_build() accepts quiet=False and suppresses output when True via capture_output
- [x] cmd_flash_all() implements all 5 stages
- [x] Build failures don't prevent other devices from building or flashing
- [x] Flash failures don't prevent remaining devices from flashing
- [x] Firmware copied to temp dir after each build
- [x] Single klipper_service_stopped() wraps all flash operations
- [x] USB devices re-scanned after Klipper stop
- [x] Post-flash verification uses wait_for_device() with 30s timeout
- [x] Summary table printed after batch completes
