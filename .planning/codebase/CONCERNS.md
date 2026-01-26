# Codebase Concerns

**Analysis Date:** 2026-01-25

## Tech Debt

**Commented-out heater_bed MPC control:**
- Issue: `[heater_bed]` section in `printer.cfg` line 43 has `#control: mpc` commented out, but MPC parameters are present in SAVE_CONFIG block. This creates inconsistency—either MPC is active (relying on auto-saved config) or it's disabled but tuning data persists unused.
- Files: `printer.cfg` (lines 43-46)
- Impact: Unclear whether bed heater actually uses MPC control or falls back to PID. Creates confusion during troubleshooting and potential thermal behavior mismatches if config is reloaded.
- Fix approach: Uncomment `#control: mpc` or remove MPC parameters from SAVE_CONFIG block. Verify bed heating performance after decision.

**Commented-out autotune_tmc for extruder:**
- Issue: `[autotune_tmc extruder]` section in `printer.cfg` (lines 103-105) is fully commented out. Motor model is defined but tuning is disabled.
- Files: `printer.cfg` (lines 103-105)
- Impact: Extruder motor may not be optimally tuned. If tuning is intentionally disabled, the comment explaining why is missing.
- Fix approach: Re-enable tuning with `#[autotune_tmc extruder]` to the active block, or document why tuning is disabled.

**Disabled Z-stepper autotune across all four Z motors:**
- Issue: All four Z-stepper autotune blocks (`[autotune_tmc stepper_z*]`) are commented out in `hardware/stepper_z.cfg` (lines 23, 41, 59, 77).
- Files: `hardware/stepper_z.cfg` (lines 23, 41, 59, 77)
- Impact: Z-steppers run with manual run_current=1.0 instead of optimized values. This may cause skipped steps, noise, or insufficient holding torque on a four-stepper system critical for QGL.
- Fix approach: Enable at least one tuning session to establish optimal Z-stepper currents, then document the results.

**Commented-out chamber temperature wait:**
- Issue: `M191 S{CHAMBER_TEMP}` in `macros/Print/print_start.cfg` line 34 is commented out, preventing thermal chamber soak.
- Files: `macros/Print/print_start.cfg` (line 34)
- Impact: Print start sequence does not wait for chamber to reach target temperature. Prints may start before chamber equilibrates, causing adhesion or first-layer quality issues on cold beds.
- Fix approach: Uncomment line 34 or document why chamber wait is disabled. If disabled intentionally (e.g., PTC chamber doesn't require soak), add comment explaining decision.

**Unused G4 dwell command:**
- Issue: `#G4 P60000` in `macros/Print/print_start.cfg` line 36 is commented out. This was likely a thermal soak timer.
- Files: `macros/Print/print_start.cfg` (line 36)
- Impact: Dead code cluttering macro. If removed, macro becomes cleaner; if needed, should be uncommented.
- Fix approach: Either uncomment if thermal stabilization is required, or remove entirely.

**Commented-out alternate Z homing method:**
- Issue: Lines 29-30 in `macros/Print/print_start.cfg` show a commented-out proximity-mode Z homing (`#G28 method=proximity calibrate=0`). Current config uses contact mode.
- Files: `macros/Print/print_start.cfg` (lines 29-30)
- Impact: No clear reason documented for rejecting proximity homing. If contact mode was problematic, history is lost.
- Fix approach: Document why contact method is preferred, or if proximity should be tested, create a conditional variant.

**Chopper tune disabled in root config:**
- Issue: `#[include chopper_tune.cfg]` in `printer.cfg` line 1 is commented out.
- Files: `printer.cfg` (line 1)
- Impact: Chopper resonance tuning is not loaded. If tuning data exists but is not applied, vibration control may be suboptimal.
- Fix approach: Either enable if tuning is available, or confirm that it's intentionally disabled (e.g., no resonances detected).

## Known Issues

**Beacon serial hardcoded with specific device ID:**
- Issue: `beacon` probe configuration uses absolute serial path `/dev/serial/by-id/usb-Beacon_Beacon_RevH_FC2690B64E5737374D202020FF0A4026-if00` in `hardware/probe_beacon.cfg` line 6.
- Files: `hardware/probe_beacon.cfg` (line 6)
- Trigger: If Beacon probe is replaced or the USB connection changes, this hardcoded ID will fail and Klipper will not load. Device path must be manually updated.
- Workaround: Keep backup of the old device ID comment nearby; use `/dev/serial/by-path/*` if available as fallback.

**Nitehawk toolhead MCU endpoint hardcoded:**
- Issue: Nitehawk MCU is configured to connect via `nhk:` alias throughout extruder and LED configs, but the serial connection endpoint is not visible in the provided files (likely in `hardware/mcu_nitehawk36.cfg`).
- Files: Extruder pins `nhk:gpio23`, `nhk:gpio24`, etc. in `printer.cfg`; Hardware definitions across multiple files
- Trigger: If Nitehawk MCU serial path changes or device fails, all pins referencing `nhk:` will fail silently until endpoint is updated.
- Workaround: Document the Nitehawk serial path clearly; test toolhead connectivity regularly.

**Beacon contact calibration temperature hardcoded to 150°C:**
- Issue: `variable_beacon_contact_calibration_temp: 150` in `macros/Beacon/beacon_temp_comp.cfg` line 2 is the reference temp for thermal expansion calculations.
- Files: `macros/Beacon/beacon_temp_comp.cfg` (line 2)
- Trigger: If nozzle is heated above 150°C without re-calibrating, thermal expansion offset calculations will be skewed. Only applies at print temps near this setpoint.
- Workaround: If using significantly different print temperatures, re-run calibration macro `BEACON_CALIBRATE_NOZZLE_TEMP_OFFSET`.

**QGL retry tolerance is tight (0.008mm):**
- Issue: `quad_gantry_level` in `features/quad_gantry_level.cfg` line 21 sets `retry_tolerance: 0.008` with `retries: 5`.
- Files: `features/quad_gantry_level.cfg` (lines 21, 20)
- Trigger: QGL may fail if mechanical slack, worn screws, or thermal drift prevent achieving 0.008mm across all four corners. Retries will exhaust without leveling.
- Workaround: Increase tolerance to 0.010-0.015mm if QGL frequently fails. Inspect gantry mechanics for play.

## Security Considerations

**Tailscale IP addresses hardcoded in moonraker.conf:**
- Risk: Moonraker CORS and trusted_clients include specific tailscale peer IPs (100.83.130.56, 100.86.124.17, etc.) in `moonraker.conf` lines 22-25.
- Files: `moonraker.conf` (lines 22-25)
- Current mitigation: Tailscale provides encryption and authentication; however, hardcoded IPs are inflexible if Tailscale network changes.
- Recommendations: Consider using Tailscale hostname instead of IP where supported; document why these specific devices need access; rotate or remove IPs for devices no longer in use.

**Spoolman server URL hardcoded:**
- Risk: `moonraker.conf` line 53 hardcodes Spoolman endpoint to `http://192.168.50.50:7912/` (unencrypted HTTP).
- Files: `moonraker.conf` (line 53)
- Current mitigation: Local network only; however, if network is compromised, filament inventory could be manipulated.
- Recommendations: Use HTTPS if Spoolman supports it; validate Spoolman certificate; document the trust boundary of this IP.

**GitHub token guidance in autocommit.sh:**
- Risk: `autocommit.sh` line 89 includes commented-out example showing how to embed GitHub token in git remote URL for CI/CD automation.
- Files: `autocommit.sh` (line 89)
- Current mitigation: Example is commented and token field is redacted (`XXXXXXXXXXX`); not currently in use.
- Recommendations: If automation requires authentication, use GitHub App or SSH key authentication instead of personal tokens; never commit tokens to repo; use environment variables for CI/CD pipelines.

**Moonraker allows all origins from app.fluidd.xyz:**
- Risk: `moonraker.conf` line 19 sets `*://app.fluidd.xyz` as trusted CORS origin.
- Files: `moonraker.conf` (line 19)
- Current mitigation: Fluidd is the standard UI; however, any XSS vulnerability in Fluidd would have printer access.
- Recommendations: Monitor Fluidd releases for security patches; consider pinning to specific Fluidd version or URL; validate HTTP vs HTTPS.

## Performance Bottlenecks

**Beacon probe uses 5mm/s speed with 500ms settling time:**
- Problem: `hardware/probe_beacon.cfg` line 14-15 sets `speed: 5` and `z_settling_time: 500` (half-second dwell).
- Files: `hardware/probe_beacon.cfg` (lines 14-15)
- Cause: Ultra-conservative settings ensure probe stability but extend probing time significantly. Each mesh point takes ~1 second of settle time alone.
- Improvement path: After verifying mechanical stability, gradually increase speed to 10-15mm/s and reduce settling to 100-200ms. Re-validate mesh quality after changes.

**Bed mesh 50×50 with bicubic interpolation:**
- Problem: `printer.cfg` SAVE_CONFIG block defines 50×50 mesh (2500 points) with bicubic tension=0.4.
- Files: `printer.cfg` (lines 222-227)
- Cause: Large mesh increases probing time (~40 minutes for full 50×50 with Beacon). Bicubic interpolation is computationally heavier than linear.
- Improvement path: Use adaptive meshing via KAMP (already configured). For full-bed prints, consider 30×30 or 40×40 with tension=0.5 for balance between accuracy and speed.

**Motors sync using Beacon accelerometer on every print start:**
- Problem: `macros/Print/print_start.cfg` line 21 calls `SYNC_MOTORS` before every print, which runs vibration analysis and recalibration.
- Files: `macros/Print/print_start.cfg` (line 21)
- Cause: Motors sync is a relatively slow operation (30-60 seconds). If steppers are already well-synchronized, this adds overhead.
- Improvement path: After confirming sync stability over several prints, modify macro to call `SYNC_MOTORS FORCE_RUN=0` by default (skip if already applied). Add periodic full sync (e.g., weekly manual command).

**Input shaper frequencies may need re-measurement:**
- Problem: `features/input_shaper.cfg` defines fixed frequencies (X: 91.4Hz, Y: 66.4Hz) without timestamps or conditions.
- Files: `features/input_shaper.cfg` (lines 2-5)
- Cause: Frequencies are hardcoded and may drift if gantry mass or spring stiffness changes (e.g., after adding tools or parts).
- Improvement path: Document when shaper was last calibrated; set calendar reminder to re-measure every 3-6 months or after major hardware changes; consider using ShakeTune integration for periodic updates.

## Fragile Areas

**Multi-MCU synchronization with Nitehawk toolhead:**
- Files: Extruder definitions in `printer.cfg`, Nitehawk MCU config (referenced but not fully visible)
- Why fragile: System relies on reliable serial communication between Octopus board and Nitehawk MCU. If Nitehawk USB becomes unstable (loose connector, bad cable), entire toolhead becomes unresponsive but Octopus may still boot.
- Safe modification: Always test Nitehawk connectivity before starting a print (check `STATUS` in console). Keep backup of last known Nitehawk serial ID. Monitor logs for "MCU 'nhk' shutdown" messages.
- Test coverage: No explicit test macros visible for Nitehawk heartbeat or comms health check.

**Beacon thermal expansion compensation macros:**
- Files: `macros/Beacon/beacon_temp_comp.cfg` (130+ lines of nested Jinja2 logic)
- Why fragile: Complex nested conditionals rely on multiple saved variables and config state. If `BEACON_CALIBRATE_NOZZLE_TEMP_OFFSET` is not run after first use, expansion coefficient is zero and offset won't apply.
- Safe modification: Always run calibration macro after major config changes. Test thermal offset by printing at 0°C delta from reference (should be zero offset) and at ±50°C (should show measurable offset).
- Test coverage: Macros assume `save_variables` is enabled. If disabled, thermal offset will fail silently.

**Quad gantry level with four Z-steppers and single Beacon probe:**
- Files: `features/quad_gantry_level.cfg`, `hardware/stepper_z.cfg`
- Why fragile: QGL relies on one Beacon probe to measure four corners. If any Z-stepper loses synchronization (skips a step), that corner's correction will be wrong, and subsequent meshes will be off. The system will not detect this error; it will simply probe an already-tilted gantry.
- Safe modification: Before and after QGL, visually inspect gantry gap with feeler gauges at all four corners to verify actual tilt. Check `quad_gantry_level` logs for retry counts; high retries indicate mechanical slop.
- Test coverage: No built-in gantry health check before QGL. Recommend manual inspection macro.

**PRINT_START sequence has multiple conditional branches:**
- Files: `macros/Print/print_start.cfg`
- Why fragile: Macro contains conditionals on `printer.configfile.settings.beacon` to decide whether to apply thermal offsets. If Beacon config is corrupted or unloaded, macro silently skips offset and prints with no expansion compensation.
- Safe modification: Add explicit error check at start: `{% if not printer.configfile.settings.beacon %}` then `RESPOND TYPE=error MSG="Beacon not configured"` and abort.
- Test coverage: Macro should be tested with both `beacon` defined and undefined to ensure graceful fallback.

**Bed and extruder MPC control parameters stored only in SAVE_CONFIG:**
- Files: `printer.cfg` SAVE_CONFIG block (lines 140-151)
- Why fragile: MPC tuning parameters (block_heat_capacity, sensor_responsiveness, fan_ambient_transfer) exist only in auto-saved config. If this block is accidentally deleted or corrupted, heaters revert to default MPC or PID with poor performance.
- Safe modification: Before editing SAVE_CONFIG, create a backup snapshot. Re-run MPC tuning if suspicious behavior appears. Document tuning date in a comment above the block.
- Test coverage: Bed and extruder temperature response curves should be tested after any config reload to verify MPC tuning is still applied.

## Scaling Limits

**Single Beacon probe for bed leveling and XY motor sync:**
- Current capacity: Beacon handles both mesh probing and accelerometer-based motor synchronization simultaneously.
- Limit: If probe becomes unreliable or is damaged, both leveling and motor sync fail. No fallback to manual mesh or stepper alignment.
- Scaling path: Add second redundant probe (Z-endstop switch) for contact backup; implement fallback mesh using stored previous mesh if probing fails; consider sensorless homing for X/Y if stepper drivers support it.

**Hardcoded print start/end macro logic:**
- Current capacity: Single PRINT_START and PRINT_END macro handles all print scenarios (bed temp, chamber temp, Beacon offsets, KAMP meshing).
- Limit: Adding new steps (e.g., purge tower, additional sensors) requires editing the macro directly; no parameterization for variant workflows.
- Scaling path: Refactor PRINT_START into modular step macros (heat, home, mesh, purge); allow slicer to call only needed steps or add conditional variables for feature toggles.

**QGL retries exhaust without diagnostic feedback:**
- Current capacity: 5 retries with 0.008mm tolerance. If all 5 fail, QGL aborts without clear reason.
- Limit: User must manually investigate whether issue is mechanical (gantry slop) or sensor-related (Beacon noise).
- Scaling path: Add diagnostic macro `QGL_DIAGNOSE` that measures each corner individually and reports which axis(es) are out of tolerance; log vibration data from Beacon accelerometer during QGL to detect mechanical resonance.

## Dependencies at Risk

**Beacon Klipper (dev channel):**
- Risk: `moonraker.conf` line 86 pins Beacon to `channel: dev`, which receives bleeding-edge updates.
- Impact: Breaking changes in dev branch could disable leveling/probing without warning. Config may become incompatible after an update.
- Migration plan: Pin Beacon to `channel: main` or specific release tag; test updates in staging before applying to production printer. Monitor Beacon GitHub issues for reported incompatibilities.

**Model Predictive Control (MPC) heater model:**
- Risk: `printer.cfg` uses MPC for both bed and extruder. MPC is a Kalico-specific extension, not in mainline Klipper.
- Impact: If Klipper fork (Kalico) is abandoned or incompatible with future updates, heaters would need re-tuning for PID control.
- Migration plan: Keep manual PID tuning data as fallback (commented or in backup). Test PID performance periodically to ensure fallback is viable. Monitor Kalico development status.

**Motors_sync feature (Kalico-specific):**
- Risk: `features/motors_sync.cfg` and `SYNC_MOTORS` macro depend on Kalico's motor synchronization extension.
- Impact: Not compatible with mainline Klipper. If forced migration occurs, XY motor sync logic would need external replacement (e.g., stepper current DACs).
- Migration plan: Keep documentation of sync model coefficients (stored in SAVE_CONFIG). Periodically test manual motor tuning as fallback. Monitor Kalico adoption and support status.

**Beacon serial connection stability:**
- Risk: Hardcoded `/dev/serial/by-id/` path is stable but depends on udev. If system is reimaged or USB stack changes, device path may shift.
- Impact: Probe becomes unreachable; all probing/leveling fails until path is corrected.
- Migration plan: Use `/dev/serial/by-path/` as fallback if available; document both paths in config; create quick-reference card with common Beacon serial IDs on this machine.

## Missing Critical Features

**No redundant Z-leveling method:**
- Problem: Entire Z-leveling system depends on Beacon probe. If Beacon fails (USB disconnect, sensor malfunction), printer cannot home Z or mesh.
- Blocks: Prints cannot start; emergency homing becomes risky.
- Alternative: Add Z-endstop (e.g., NPN switch or limit switch) as mechanical fallback; implement conditional home logic that tries Beacon first, falls back to switch.

**No automatic mesh validation:**
- Problem: After `BED_MESH_CALIBRATE`, there is no check that the mesh is sane (no NaN values, no extreme peaks/valleys that might cause crashes).
- Blocks: A corrupted mesh (e.g., from Beacon noise spike) may not be caught until print head crashes.
- Alternative: Add macro `VALIDATE_MESH` that checks all mesh points are within reasonable range and raises alert if outliers detected.

**No Nitehawk MCU heartbeat monitor:**
- Problem: Toolhead MCU health is not explicitly monitored. If Nitehawk loses USB power mid-print, extruder becomes unresponsive but print continues with no offset applied.
- Blocks: Skipped layers, tool crashes on next movement.
- Alternative: Implement `gcode_macro CHECK_HOTEND_COMMS` that pings Nitehawk with a safe command (e.g., LED status query) before print starts; log MCU temperature regularly to detect comms loss.

**No bed temperature overshoot detection:**
- Problem: Heater verification only checks that temperature is within range; does not warn if bed overshoots (e.g., heater stuck on).
- Blocks: If bed heats uncontrollably, first indication is warped print or damaged parts.
- Alternative: Add threshold check in PRINT_START: if bed reaches target + 10°C before extruder finishes heating, raise alert and cut heater power.

## Test Coverage Gaps

**Beacon thermal expansion compensation untested with variable ambient:**
- What's not tested: Macro calculates nozzle expansion offset using stored `nozzle_expansion_coefficient` calibrated at ~21.4°C (stored in Beacon model). If room temperature is significantly different (e.g., winter workshop), actual expansion may differ.
- Files: `macros/Beacon/beacon_temp_comp.cfg`
- Risk: Prints with cold nozzle may have dimensional errors; worst case, first layer adhesion varies with ambient.
- Priority: Medium - Affects dimensional accuracy and first-layer quality.

**QGL mechanical slop not detected:**
- What's not tested: QGL can complete successfully even if gantry has excessive side-play. Probe measures Z height only, not gantry deflection or sag during XY motion.
- Files: `features/quad_gantry_level.cfg`, `hardware/stepper_z.cfg`
- Risk: If gantry bends under nozzle pressure during printing, leveling becomes invalid and print quality suffers.
- Priority: High - Directly impacts print quality and part accuracy.

**Motors sync applied but not verified:**
- What's not tested: `SYNC_MOTORS` macro runs calibration and updates step model, but there is no post-sync verification that steppers actually synchronized.
- Files: `features/motors_sync.cfg`, `macros/Print/print_start.cfg`
- Risk: If sync fails silently, XY motors remain out of sync and cause ringing, vibration, or positioning errors.
- Priority: High - Sync is run every print; undetected failure cascades to all subsequent prints.

**Extruder pressure advance not calibrated:**
- What's not tested: `printer.cfg` sets `pressure_advance_smooth_time: 0.01` but no PA value is stored. Macro relies on slicer-provided values.
- Files: `printer.cfg` (line 75)
- Risk: If slicer default is wrong, first prints exhibit stringing or over-extrusion at corners.
- Priority: Medium - Affects part appearance; easy to tune once detected.

**Input shaper frequencies not validated against actual machine resonance:**
- What's not tested: Shaper frequencies (X: 91.4Hz, Y: 66.4Hz) are loaded without verification that current gantry/toolhead configuration still exhibits those resonances.
- Files: `features/input_shaper.cfg`
- Risk: If toolhead has changed (heavier tool, different nozzle), resonance frequencies may have shifted, and shaper settings are now mismatched.
- Priority: Medium - Affects print quality; inexpensive to re-tune with ShakeTune.

**Cold-start print without full homing:**
- What's not tested: If printer is powered on and `PRINT_START` is called without prior `G28` or `QUAD_GANTRY_LEVEL`, macro includes `CG28` (conditional home) but does not explicitly verify QGL is applied before meshing.
- Files: `macros/Print/print_start.cfg` (lines 23, 42)
- Risk: If conditional home succeeds but QGL is skipped (e.g., due to Beacon timeout), print starts with un-leveled gantry.
- Priority: High - Silent failure leads to crashed prints.

---

*Concerns audit: 2026-01-25*
