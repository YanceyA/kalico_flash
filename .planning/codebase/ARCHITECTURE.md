# Architecture

**Analysis Date:** 2026-01-25

## Pattern Overview

**Overall:** Modular hierarchical include-based configuration system

**Key Characteristics:**
- Root configuration file (`printer.cfg`) acts as orchestrator, minimal content
- Glob-based include patterns load configs in strict dependency order
- Hardware layer (MCUs, sensors, motors) must load before macros
- Features layer provides optional toggle-able subsystems
- Macros grouped by operational domain (Print, Heating, Beacon, Filament, Home_QGL_Mesh)
- Kalico-specific extensions (motors_sync, danger_options) integrated throughout
- Two-MCU architecture: main Octopus board + Nitehawk36 toolhead board

## Layers

**Root Configuration:**
- Purpose: Define printer kinematics, global constraints, include all subsystems
- Location: `C:\dev_projects\Voron_24_Config_Backup\printer.cfg`
- Contains: `[printer]` kinematics, max_velocity, max_accel, bed heater, extruder, SAVE_CONFIG blocks
- Depends on: All hardware and feature configs (via includes)
- Used by: Klipper daemon loads and parses this first

**Hardware Layer:**
- Purpose: Board definitions, sensor wiring, motor configurations, MCU serial connections
- Location: `C:\dev_projects\Voron_24_Config_Backup\hardware/**/*.cfg`
- Contains: MCU definitions, stepper configs, thermistors, probes, fans, LEDs
- Depends on: None (foundational)
- Used by: All other layers reference hardware definitions
- Key files:
  - `mcu_octopus.cfg` - Main STM32H723 control board, serial connection, board pin aliases
  - `mcu_nitehawk36.cfg` - Toolhead MCU (referenced in extruder pins)
  - `stepper_xy.cfg` - Dual X and dual Y steppers (4WD Monolith gantry), TMC2240 drivers, endstops
  - `stepper_z.cfg` - Quad Z steppers for QGL, no endstops (uses Beacon for homing)
  - `probe_beacon.cfg` - Beacon RevH probe configuration, contact/proximity modes, offsets
  - `sensor_*cfg` - Temperature sensors, accelerometers for motors_sync
  - `fans_*.cfg` - Bed fans, hotend fans, stepper cooling fans
  - `heater_chamber_ptc.cfg` - PTC chamber heater with watermark control
  - `leds_*.cfg` - Case lights and hotend LEDs

**Kalico Extensions:**
- Purpose: Klipper fork-specific features and logging controls
- Location: `C:\dev_projects\Voron_24_Config_Backup\danger_klipper_options.cfg`
- Contains: `[danger_options]` block with logging controls, multi-MCU timeouts
- Depends on: None (loaded early)
- Used by: Affects Klipper daemon behavior globally

**Features Layer:**
- Purpose: Optional toggleable Klipper modules and custom integrations
- Location: `C:\dev_projects\Voron_24_Config_Backup\features/**/*.cfg`
- Contains: Bed mesh config, input shaping, QGL, pause/resume, motion tracking
- Depends on: Hardware (defined first)
- Used by: Macros and runtime control
- Key features:
  - `quad_gantry_level.cfg` - QGL tramming points, 4-corner probe sequence
  - `bed_mesh.cfg` - 50x50 bicubic adaptive mesh, zero reference at center
  - `motors_sync.cfg` - Beacon accelerometer-based XY microstep sync
  - `input_shaper.cfg` - Resonance compensation via tuning
  - `motion_minder.cfg` - Optional motion monitoring
  - `pause_resume.cfg` - Print pause/resume state management
  - KAMP integration (KAMP_Settings.cfg) for adaptive meshing and purging

**Macros Layer:**
- Purpose: G-code automation flows organized by subsystem
- Location: `C:\dev_projects\Voron_24_Config_Backup\macros/**/*.cfg`
- Contains: Gcode macros, conditional logic, parameter handling, Jinja2 templating
- Depends on: Hardware and features (references configfile.config and printer state)
- Used by: Slicer start/end scripts, manual commands, motion workflows
- Organized by domain:
  - `Print/` - PRINT_START, PRINT_END, pause, resume, purge sequences
  - `Beacon/` - Probe compensation macros (_BEACON_SET_NOZZLE_TEMP_OFFSET, etc)
  - `Heating/` - Heat soak, chamber warmup logic
  - `Filament/` - Smart filament change (M600)
  - `Home_QGL_Mesh/` - G32 (full home+QGL+mesh), QUAD_GANTRY_SCAN, CG28 (conditional home)
  - Root-level: Park macros, case lights, motion minder
  - `variables.txt` - Shared constants (nozzle_expansion_coefficient, etc)

**Modules Layer:**
- Purpose: Non-Klipper companion service configurations
- Location: `C:\dev_projects\Voron_24_Config_Backup\modules/**/*.conf`
- Contains: KlipperScreen UI, Crowsnest camera, Sonar reboot handler configs
- Depends on: Moonraker services (not Klipper core)
- Used by: Web dashboard and support services

## Data Flow

**Print Start Sequence:**

1. Slicer invokes `PRINT_START BED_TEMP=60 EXTRUDER_TEMP=210 CHAMBER_TEMP=35`
2. Macro reads parameters, stores in local Jinja2 variables
3. Lights on (SET_LED via hardware/leds_caselight.cfg)
4. Reset any Z offset (SET_GCODE_OFFSET Z=0)
5. SYNC_MOTORS (motors_sync.cfg) - synchronizes XY dual motors via Beacon accelerometer
6. CG28 - Conditional home (checks if homed, homes if not)
7. Bed heating starts async (M140), chamber heating starts async (M141)
8. Hotend pre-heats to 150C (M104) for nozzle wetting
9. Wait for bed to reach target (M190)
10. Z homing via Beacon contact method with calibration (G28 Z METHOD=CONTACT CALIBRATE=1)
11. QUAD_GANTRY_SCAN - QGL leveling using 4 probe points (features/quad_gantry_level.cfg)
12. BED_MESH_CALIBRATE with ADAPTIVE=1 and RUNS=2 - KAMP adaptive mesh
13. Z homing via Beacon proximity mode (final touch-off)
14. Hotend heats to target (M109)
15. Beacon nozzle thermal offset applied (_BEACON_SET_NOZZLE_TEMP_OFFSET)
16. LINE_PURGE - KAMP line purge at print area edge
17. Print begins

**State Management:**

- Conditional logic checks `printer.configfile.settings` and `printer.configfile.config` dictionaries
- Example: `{% if printer.configfile.settings.beacon is defined %}` gates Beacon-specific macros
- Variables stored in `[variables]` section (`variables.txt`): nozzle_expansion_coefficient, applied_offset
- Printer state queries: `printer.toolhead.position`, `printer.motors_sync.applied`, `printer.bed_mesh`
- Configuration boundaries accessed: `printer.configfile.config["stepper_x"]["position_max"]`

**Print End Sequence:**

1. Wait for command buffer to clear (M400)
2. Retract filament (G1 E-15.0)
3. Calculate safe direction to move based on current XY position
4. Remove Beacon thermal offset
5. Move nozzle up (Z), then to parking position
6. Turn off heaters and fans
7. Park toolhead near rear (X=center, Y=rear - 80mm)
8. Disable all but Z steppers
9. Clear bed mesh
10. Motion minder status update
11. Dim case lights

## Key Abstractions

**Beacon Probe Abstraction:**
- Purpose: Single interface for contact homing, proximity homing, thermal compensation
- Examples: `C:\dev_projects\Voron_24_Config_Backup\hardware\probe_beacon.cfg`, `macros/Beacon/beacon_temp_comp.cfg`
- Pattern: Probe offsets (x_offset: 0, y_offset: 19) handled at hardware level, compensation applied in print_start via _BEACON_SET_NOZZLE_TEMP_OFFSET macro
- Uses accelerometer (via motors_sync) for vibration-based microstep tuning

**Multi-Motor Sync Abstraction:**
- Purpose: Dual X and dual Y stepper synchronization to eliminate gantry skew
- Examples: `C:\dev_projects\Voron_24_Config_Backup\features\motors_sync.cfg`, called in `macros/Print/print_start.cfg`
- Pattern: SYNC_MOTORS macro wraps Kalico native motors_sync module, checks if already applied, uses exponential model for microstep displacement
- Uses Beacon accelerometer as vibration sensor for both axes

**Conditional Home Abstraction:**
- Purpose: Only home if not already homed (safety, time optimization)
- Examples: `macros/Home_QGL_Mesh/G32.cfg` (uses CG28), `print_start.cfg` (uses CG28)
- Pattern: CG28 macro checks printer.homed_axes before issuing G28

**Nozzle Thermal Expansion Abstraction:**
- Purpose: Automatically adjust Z offset based on hotend temperature
- Examples: `macros/variables.txt` (stores coefficient), `macros/Print/print_start.cfg` (applies offset), `print_end.cfg` (removes offset)
- Pattern: Linear compensation model using coefficient stored in variables
- Calculation: offset = temperature * nozzle_expansion_coefficient

## Entry Points

**Slicer Integration:**
- Location: `macros/Print/print_start.cfg`, `macros/Print/print_end.cfg`
- Triggers: Slicer start/end G-code scripts (PRINT_START with BED_TEMP, EXTRUDER_TEMP, CHAMBER_TEMP parameters)
- Responsibilities: Full printer warm-up, homing, leveling, calibration sequence
- Return state: Printer ready to print, mesh applied, toolhead at start position

**Manual Command Entry:**
- Location: Various macros in `macros/`
- Triggers: G32 (full home+level+mesh), SYNC_MOTORS, individual component control
- Responsibilities: State validation, emergency safety checks, operator feedback (RESPOND messages)

**Daemon Startup:**
- Location: `printer.cfg` (root), `startup.cfg`
- Triggers: Klipper daemon boot
- Responsibilities: Load all hardware definitions, apply calibration data (SAVE_CONFIG), set idle timeouts
- Idle timeout gcode: `startup.cfg` - turns off heaters, fans, steppers after 30 minutes

**UI Dashboard Integration:**
- Location: `modules/KlipperScreen.conf`, macros provide gcode accessible endpoints
- Triggers: KlipperScreen button presses, web dashboard commands
- Responsibilities: Expose printer state via macro status queries, LED feedback, temperature display

## Error Handling

**Strategy:** Defensive configuration with Kalico danger_options for extended error control

**Patterns:**
- `verify_heater` blocks in printer.cfg for bed and extruder - detect heating failures, timeouts, sensor errors
- `is_non_critical: True` on Beacon probe - allows print to continue if probe malfunctions
- `danger_options.temp_ignore_limits: False` - strict temperature validation (can be overridden for troubleshooting)
- Jinja2 conditional checks in macros guard Beacon-specific logic: `{% if printer.configfile.settings.beacon is defined %}`
- RESPOND TYPE=command messages provide user feedback during critical sequences (heat, sync, homing)

## Cross-Cutting Concerns

**Logging:**
- Kalico danger_options controls log verbosity: `log_bed_mesh_at_startup: False`, `log_startup_info: True`
- Minimal_logging disabled by default (verbose logging enabled)
- Serial reader warnings enabled for debugging

**Validation:**
- Motor tuning via autotune_tmc blocks for each stepper (motor specs defined)
- Heater verification with max_error, check_gain_time, hysteresis thresholds
- Beacon contact max hotend temperature (350C) prevents probe damage

**Authentication:**
- Not applicable (local Klipper on Raspberry Pi, no network auth)

**Multi-MCU Coordination:**
- Octopus main board communicates with Nitehawk36 toolhead board via UART
- Extruder and hotend LEDs hang off Nitehawk36 (referenced as nhk: pins)
- motors_sync uses Beacon accelerometer on main board to coordinate both MCUs
- Kalico danger_options includes multi_mcu_trsync_timeout for synchronization control

---

*Architecture analysis: 2026-01-25*
