# Codebase Structure

**Analysis Date:** 2026-01-25

## Directory Layout

```
C:\dev_projects\Voron_24_Config_Backup/
├── printer.cfg                           # Root configuration file (entry point)
├── startup.cfg                           # Daemon startup and idle timeout handlers
├── danger_klipper_options.cfg            # Kalico fork extensions
├── hardware/                             # Board, stepper, sensor, fan configurations
│   ├── mcu_octopus.cfg                  # Main Octopus STM32H723 MCU
│   ├── mcu_nitehawk36.cfg               # Toolhead Nitehawk36 MCU
│   ├── stepper_xy.cfg                   # X/X1 and Y/Y1 dual motors (4WD gantry)
│   ├── stepper_z.cfg                    # Z/Z1/Z2/Z3 quad motors for QGL
│   ├── probe_beacon.cfg                 # Beacon RevH contact/proximity probe
│   ├── sensor_accelerometers.cfg        # Beacon accelerometer (motors_sync)
│   ├── sensor_bed.cfg                   # Bed thermistor
│   ├── sensor_temp_chamber.cfg          # Chamber thermistor
│   ├── sensor_temp_mpc.cfg              # Ambient temperature (for extruder MPC)
│   ├── fans_bed.cfg                     # Bed heater cooling fans
│   ├── fans_hotend.cfg                  # Hotend cooling fan
│   ├── fans_print_cooling.cfg           # Part cooling fan
│   ├── fans_octopus_stepper.cfg         # Stepper motor cooling fans
│   ├── fans_ptc_heater.cfg              # PTC chamber heater cooling
│   ├── heater_chamber_ptc.cfg           # PTC chamber heater control
│   ├── leds_caselight.cfg               # Case lighting LEDs
│   └── leds_hotend.cfg                  # Hotend status LEDs
├── macros/                               # G-code automation flows
│   ├── variables.txt                    # Shared constants (nozzle_expansion_coefficient)
│   ├── beacon.cfg                       # Beacon macro wrapper/dispatcher
│   ├── case_lights.cfg                  # Lighting control macros
│   ├── fan_tach_monitor.cfg             # Fan speed monitoring
│   ├── motion_minder.cfg                # Motion tracking wrapper
│   ├── park_bed.cfg                     # Park at bed center
│   ├── park_center.cfg                  # Park at XY center
│   ├── Print/                           # Print workflow macros
│   │   ├── print_start.cfg              # PRINT_START - pre-print setup sequence
│   │   ├── print_end.cfg                # PRINT_END - post-print cleanup
│   │   ├── print_pause.cfg              # PRINT_PAUSE workflow
│   │   ├── print_resume.cfg             # PRINT_RESUME workflow
│   │   ├── print_cancel.cfg             # PRINT_CANCEL error handling
│   │   ├── print_park_toolhead.cfg      # Park toolhead safely
│   │   ├── print_pause_layers.cfg       # Pause at layer X
│   │   └── print_extrude_retract.cfg    # Extrude/retract sequences
│   ├── Beacon/                          # Beacon probe-specific macros
│   │   └── beacon_temp_comp.cfg         # Thermal expansion compensation
│   ├── Heating/                         # Temperature control macros
│   │   └── heat_soak.cfg                # Chamber and bed preheat sequences
│   ├── Filament/                        # Filament management
│   │   └── smart-m600.cfg               # Smart filament change (M600)
│   └── Home_QGL_Mesh/                   # Homing and leveling workflows
│       ├── G32.cfg                      # Full homing + QGL + mesh sequence
│       ├── CQGL.cfg                     # Conditional QGL
│       ├── quad_gantry_scan.cfg         # QGL with enhanced parking
│       ├── bed_mesh_calibrate_default.cfg # Default mesh calibration
│       └── TEST.cfg                     # Diagnostic test macros
├── features/                             # Optional toggleable Klipper features
│   ├── quad_gantry_level.cfg            # QGL definition (4 corner points, tolerance)
│   ├── bed_mesh.cfg                     # Bed mesh configuration (50x50 bicubic)
│   ├── motors_sync.cfg                  # Beacon-based XY motor sync (Kalico)
│   ├── input_shaper.cfg                 # Resonance compensation tuning
│   ├── motion_minder.cfg                # Motion tracking integration
│   ├── KAMP_Settings.cfg                # KAMP adaptive mesh and purge settings
│   ├── pause_resume.cfg                 # Print pause/resume state machine
│   ├── exclude_object.cfg               # Object exclusion support
│   ├── force_move.cfg                   # FORCE_MOVE emergency bypass
│   ├── save_variables.cfg               # Persistent variable storage
│   ├── config_backup.cfg                # Configuration backup triggers
│   ├── gcode_arcs.cfg                   # Arc command support
│   ├── display_status.cfg               # Status message display
│   ├── respond.cfg                      # Response message system
│   ├── shake_tune.cfg                   # ShakeTune resonance analysis
│   └── skew_correction.cfg              # Skew correction support
├── modules/                              # Non-Klipper companion configs
│   ├── KlipperScreen.conf               # Touch UI configuration
│   ├── crowsnest.conf                   # Camera streaming service
│   └── sonar.conf                       # Reboot handler
├── config_backups/                      # Auto-generated timestamped snapshots
│   └── printer-YYYYMMDD_HHMMSS.cfg    # Backup copies (managed by autocommit.sh)
├── K-ShakeTune/                         # ShakeTune analysis results directory
│   └── *.cfg                            # Generated tuning configs (not committed)
├── KAMP/                                # KAMP library configs
│   └── KAMP_Settings.cfg               # Referenced in features/
├── adxl_results/                        # ADXL accelerometer tuning data
│   └── *.csv                            # Raw accelerometer traces
├── ShakeTune_results/                   # ShakeTune resonance analysis plots
│   └── *.png/*.csv                      # Analysis visualizations
├── .planning/                           # GSD planning documents
│   └── codebase/                       # Codebase analysis output
└── .git/                               # Version control
```

## Directory Purposes

**printer.cfg:**
- Purpose: Root configuration file, entry point for Klipper daemon
- Contains: Printer kinematics (CoreXY), motion limits, bed heater, extruder, SAVE_CONFIG block
- Minimal content by design - includes all subsystems via glob patterns
- Key global settings: max_velocity: 400, max_accel: 15000, max_z_velocity: 30

**startup.cfg:**
- Purpose: Daemon initialization and idle timeout handlers
- Contains: `[idle_timeout]` gcode (turn off heaters/fans/steppers after 1800s), `[virtual_sdcard]` (print queue), `[gcode_shell_command]` (shutdown handlers)

**danger_klipper_options.cfg:**
- Purpose: Kalico fork-specific extensions
- Contains: Logging controls (log_bed_mesh_at_startup: False), multi-MCU timeouts, autosave_includes settings
- Not used in mainline Klipper - Kalico only

**hardware/:**
- Purpose: Physical device definitions - boards, motors, sensors, fans, heaters, probes
- Organization: Files grouped by component type (mcu_*, stepper_*, sensor_*, fans_*, heater_*, leds_*, probe_*)
- Key principles:
  - MCU definitions first (mcu_octopus.cfg, mcu_nitehawk36.cfg)
  - Stepper configs define motor control and endstops/homing
  - Sensor configs define thermistors and accelerometers
  - Probe config defines Beacon RevH with offsets and homing modes
- Loaded via `[include hardware/**/*.cfg]` glob pattern

**macros/:**
- Purpose: G-code automation flows organized by operational domain
- Organization:
  - `Print/` - Print workflow (start, end, pause, resume, cancel)
  - `Beacon/` - Probe-specific compensation and control
  - `Heating/` - Temperature ramp and soak sequences
  - `Filament/` - Filament change and management
  - `Home_QGL_Mesh/` - Homing, leveling, and mesh calibration
  - Root level - General utilities (park, lights, motion tracking)
- `variables.txt` - Shared constants (not a macro, loaded as `[include macros/variables.txt]` implicitly via glob)
- Loaded via `[include macros/**/*.cfg]` glob pattern
- All files use `[gcode_macro NAME]` sections with Jinja2 templating

**features/:**
- Purpose: Optional toggleable Klipper modules that can be included/excluded by changing include order in printer.cfg
- Organization: One feature per file (quad_gantry_level.cfg, bed_mesh.cfg, motors_sync.cfg, etc.)
- Key features:
  - **quad_gantry_level.cfg** - Defines `[quad_gantry_level]` with 4 probe points, tolerance, max_adjust
  - **bed_mesh.cfg** - Defines `[bed_mesh]` with 50x50 bicubic, zero_reference_position, adaptive settings
  - **motors_sync.cfg** - Kalico-specific motors sync with macro wrapper (SYNC_MOTORS)
  - **input_shaper.cfg** - Resonance compensation (if tuned via ShakeTune)
  - **KAMP_Settings.cfg** - Adaptive mesh and line purge macros
  - **pause_resume.cfg** - State machine for PAUSE/RESUME workflows
- Comment out or move lines in printer.cfg to disable features
- Loaded via `[include features/**/*.cfg]` glob pattern

**modules/:**
- Purpose: Non-Klipper companion service configurations (not Klipper core)
- Contains: KlipperScreen UI config, Crowsnest camera streaming, Sonar reboot handler
- Not loaded by printer.cfg (separate config files for Moonraker services)

**config_backups/:**
- Purpose: Auto-generated timestamped snapshots of complete printer config
- Managed by: autocommit.sh script (runs daily or manually)
- Naming: printer-YYYYMMDD_HHMMSS.cfg
- Use case: Version control recovery, diff analysis of config drift

**K-ShakeTune/, KAMP/, adxl_results/, ShakeTune_results/:**
- Purpose: Data and analysis outputs from tuning tools
- K-ShakeTune: Generated Klipper configs from ShakeTune analysis
- KAMP: Library macros for adaptive meshing and purging
- adxl_results, ShakeTune_results: Raw and visualized resonance data
- Not manually edited - generated by tools or external libraries

## Key File Locations

**Entry Points:**
- `C:\dev_projects\Voron_24_Config_Backup\printer.cfg` - Klipper daemon loads first, orchestrates all includes
- `C:\dev_projects\Voron_24_Config_Backup\startup.cfg` - Runs on daemon startup, sets idle timeouts
- `C:\dev_projects\Voron_24_Config_Backup\macros\Print\print_start.cfg` - Slicer invokes PRINT_START
- `C:\dev_projects\Voron_24_Config_Backup\macros\Print\print_end.cfg` - Slicer invokes PRINT_END

**Configuration:**
- `C:\dev_projects\Voron_24_Config_Backup\danger_klipper_options.cfg` - Kalico fork options
- `C:\dev_projects\Voron_24_Config_Backup\hardware\mcu_octopus.cfg` - MCU serial connection, board pins
- `C:\dev_projects\Voron_24_Config_Backup\features\quad_gantry_level.cfg` - QGL probe points and tolerance
- `C:\dev_projects\Voron_24_Config_Backup\features\bed_mesh.cfg` - Mesh resolution and algorithm

**Core Logic:**
- `C:\dev_projects\Voron_24_Config_Backup\hardware\stepper_xy.cfg` - Dual X/Y motor definitions
- `C:\dev_projects\Voron_24_Config_Backup\hardware\probe_beacon.cfg` - Beacon homing and offsets
- `C:\dev_projects\Voron_24_Config_Backup\features\motors_sync.cfg` - XY synchronization via accelerometer
- `C:\dev_projects\Voron_24_Config_Backup\macros\Home_QGL_Mesh\G32.cfg` - Full home+QGL+mesh command
- `C:\dev_projects\Voron_24_Config_Backup\macros\Beacon\beacon_temp_comp.cfg` - Thermal expansion compensation

**Testing/Tuning:**
- `C:\dev_projects\Voron_24_Config_Backup\macros\Home_QGL_Mesh\TEST.cfg` - Diagnostic test macros
- `C:\dev_projects\Voron_24_Config_Backup\adxl_results\` - ADXL accelerometer traces (from MEASURE_AXES_NOISE)
- `C:\dev_projects\Voron_24_Config_Backup\ShakeTune_results\` - Resonance analysis plots

## Naming Conventions

**Files:**
- Hardware configs: `component_type_descriptor.cfg` (e.g., `fans_bed.cfg`, `stepper_xy.cfg`, `probe_beacon.cfg`)
- Macro configs: `domain/macro_name.cfg` (e.g., `Print/print_start.cfg`, `Beacon/beacon_temp_comp.cfg`)
- MCU configs: `mcu_boardname.cfg` (e.g., `mcu_octopus.cfg`, `mcu_nitehawk36.cfg`)
- Feature configs: `feature_name.cfg` (e.g., `quad_gantry_level.cfg`, `bed_mesh.cfg`)
- Snake_case for all filenames (lowercase with underscores)

**Directories:**
- Functional grouping: `Beacon/`, `Print/`, `Heating/`, `Filament/`, `Home_QGL_Mesh/`
- PascalCase for macro subsystem directories
- Lowercase for hardware, features, modules
- One-level deep (no nested subdirectories except macros)

**Sections:**
- `[gcode_macro NAME]` - All G-code macros in UPPERCASE (e.g., PRINT_START, SYNC_MOTORS, G32)
- `[stepper_*]`, `[stepper_*1]` - Multiple motors (X, X1, Y, Y1, Z, Z1, Z2, Z3)
- `[tmc2240 stepper_*]` - Driver config matches motor name
- `[autotune_tmc stepper_*]` - Tuning config matches motor name
- `[heater_bed]`, `[extruder]` - Standard Klipper section names
- `[beacon]` - Probe section (Kalico)
- `[quad_gantry_level]`, `[bed_mesh]` - Leveling/meshing sections
- `[motors_sync]` - Motors sync section (Kalico)
- `[constants]` - Global constants in printer.cfg

## Where to Add New Code

**New Feature (Kalico Extension):**
- Create file: `C:\dev_projects\Voron_24_Config_Backup\features\feature_name.cfg`
- Define `[feature_name]` section with parameters
- Add `[include features/feature_name.cfg]` line to `printer.cfg` after existing feature includes
- Example: If adding a new heater, add `C:\dev_projects\Voron_24_Config_Backup\features\heater_custom.cfg` with `[heater_generic custom_name]` section

**New Hardware Component:**
- Create file: `C:\dev_projects\Voron_24_Config_Backup\hardware\component_type_descriptor.cfg`
- Define sections: `[component_section]`, `[tmc_driver component]` (if stepper), `[autotune_tmc component]` (if stepper)
- Pattern: Use existing files as templates (e.g., copy `hardware/stepper_xy.cfg` structure for new stepper)
- Already included via glob `[include hardware/**/*.cfg]` - no printer.cfg changes needed

**New Macro:**
- Create file: `C:\dev_projects\Voron_24_Config_Backup\macros\DOMAIN\macro_name.cfg`
- Define `[gcode_macro MACRO_NAME]` section with gcode block
- Use Jinja2 templating for conditionals: `{% if printer.configfile.settings.beacon is defined %}`
- Store reusable values in `C:\dev_projects\Voron_24_Config_Backup\macros\variables.txt` `[variables]` section
- Already included via glob `[include macros/**/*.cfg]` - no printer.cfg changes needed
- Example structure:
  ```
  [gcode_macro NEW_MACRO]
  description: What this macro does
  gcode:
    {% set var = params.PARAM|default(value)|type %}
    # Logic here
    RESPOND TYPE=command MSG='Status message'
  ```

**New Utilities/Helpers:**
- Root-level utility macros: `C:\dev_projects\Voron_24_Config_Backup\macros\utility_name.cfg`
- Shared constants: Add to `C:\dev_projects\Voron_24_Config_Backup\macros\variables.txt` `[variables]` section
- Reusable sensor helpers: `C:\dev_projects\Voron_24_Config_Backup\hardware\sensor_name.cfg`
- Already auto-included by glob patterns

**Conditional Logic (Kalico-specific):**
- Use Kalico danger_options: Add settings to `C:\dev_projects\Voron_24_Config_Backup\danger_klipper_options.cfg`
- Pattern: `[danger_options]` section with boolean/numeric settings
- In macros, check: `{% if printer.configfile.settings.component is defined %}` before using that component

## Special Directories

**config_backups/:**
- Purpose: Auto-generated by autocommit.sh
- Generated: Yes (via script)
- Committed: Yes (snapshots stored in git history)
- Management: autocommit.sh runs daily at midnight, backs up `~/printer_data/config` to repo
- Retention: All backups kept (for git history diff analysis)

**K-ShakeTune/:**
- Purpose: Generated Klipper configs from ShakeTune analysis
- Generated: Yes (by ShakeTune plugin output)
- Committed: No (local tuning artifact)
- Refresh: Rerun `SHAPER_CALIBRATE` command to regenerate

**KAMP/:**
- Purpose: KAMP library configs (not Klipper core)
- Generated: No (installed via Moonraker plugin)
- Committed: No (external plugin, not in this repo)
- Referenced by: `features/KAMP_Settings.cfg` includes this directory's macros

**adxl_results/, ShakeTune_results/:**
- Purpose: Tuning data and analysis outputs
- Generated: Yes (by `MEASURE_AXES_NOISE` and ShakeTune)
- Committed: Yes (diagnostic data)
- Refresh: Rerun calibration commands to update

**.planning/codebase/:**
- Purpose: GSD codebase analysis documents
- Generated: Yes (by /gsd:map-codebase command)
- Committed: Yes (planning references)
- Updated: Manually by /gsd:map-codebase command

---

*Structure analysis: 2026-01-25*
