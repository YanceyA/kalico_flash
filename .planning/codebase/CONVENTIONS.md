# Coding Conventions

**Analysis Date:** 2026-01-25

## Naming Patterns

**Files:**
- Lowercase snake_case with `.cfg` extension
- Pattern: `[subsystem]_[component].cfg` or `[subsystem].cfg`
- Examples: `fans_bed.cfg`, `probe_beacon.cfg`, `mcu_octopus.cfg`, `print_start.cfg`
- Subdirectories follow subsystem organization: `Beacon/`, `Print/`, `Heating/`, `Home_QGL_Mesh/`, `Filament/`

**Sections:**
- Lowercase snake_case for all section headers
- Examples: `[gcode_macro PRINT_START]`, `[heater_bed]`, `[controller_fan BedFans]`
- Macro names: UPPERCASE (e.g., `PRINT_START`, `PARKCENTER`, `SYNC_MOTORS`, `_BEACON_SET_NOZZLE_TEMP_OFFSET`)
- Private/internal macros prefixed with underscore: `_BEACON_REMOVE_NOZZLE_TEMP_OFFSET`, `_CLIENT_RETRACT`

**Variables:**
- Lowercase snake_case for Jinja2 variables: `beacon_contact_calibration_temp`, `nozzle_expansion_coefficient`
- Descriptive prefixes for context: `z_speed`, `safe_home_x`, `applied_offset`, `temp_offset`
- User-facing variables in `[gcode_macro]` blocks: lowercase snake_case (e.g., `variable_beacon_contact_expansion_multiplier`)

**Parameters:**
- UPPERCASE_WITH_SPACES in macro invocations: `BED_TEMP`, `EXTRUDER_TEMP`, `CHAMBER_TEMP`, `RESET=True`
- Access via `params.PARAM_NAME|default(...)|type` pattern

**Configuration Values:**
- Stored in `[constants]` section in `printer.cfg` or within `[gcode_macro ...]` variable blocks
- Example from `printer.cfg`: `run_current_xy: 1.2`

## Code Style

**Formatting:**
- Indentation: Exactly 2 spaces (never tabs)
- No trailing whitespace
- Configuration key-value pairs: key on left, value on right
- Comments aligned with code when practical

**Line Length:**
- Configurable lines can extend beyond 80 characters for readability
- Jinja2 template logic: no strict limit, but break complex conditionals across lines for clarity

**Linting:**
- No automated linter configured
- Manual validation via Klipper's built-in syntax checker: `~/klipper/scripts/check_klippy.py printer.cfg`

## Import Organization

**Include Order:**
- Root `printer.cfg` uses glob-based `[include]` directives
- Order matters—dependencies must be defined before use
- Pattern used in `printer.cfg`:
  1. Startup configuration: `[include startup.cfg]`
  2. Danger options: `[include danger_klipper_options.cfg]`
  3. Hardware: `[include hardware/**/*.cfg]` (MCU pins, sensors, fans, probes)
  4. Macros: `[include macros/**/*.cfg]` (gcode macros organized by subsystem)
  5. Features: `[include features/**/*.cfg]` (optional modules: bed_mesh, KAMP, input_shaper, etc.)
  6. Service configs: `[include modules/**/*.cfg]` (KlipperScreen, Moonraker, Crowsnest)
  7. Tuning and KAMP: `[include K-ShakeTune/*.cfg]`, `[include KAMP/KAMP_Settings.cfg]`

**Path Aliases:**
- No path aliases used; files referenced by full relative paths from root
- Beacon probe MCU references: `nhk:gpio13`, `nhk:gpio23` (secondary MCU pins prefixed with `nhk:`)

## Error Handling

**Strategy:**
- Validation happens at configuration load time via Klipper syntax checker
- Runtime errors communicated via `RESPOND` macro messages
- Status messages output to console/web UI: `RESPOND TYPE=command MSG='...'`
- No exception handling in Klipper configs (not applicable to declarative configuration)

**Patterns:**
- Conditional checks using Jinja2 `{% if %}` blocks to skip unsupported features:
  ```
  {% if printer.configfile.settings.beacon is defined %}
    _BEACON_REMOVE_NOZZLE_TEMP_OFFSET
  {% endif %}
  ```
- Safe defaults for optional parameters: `params.PARAM|default(value)|type`
- Example: `{% set BED_TEMP = params.BED_TEMP|default(60)|float %}`

**Logging & Monitoring:**
- Danger options control logging verbosity: `log_bed_mesh_at_startup: False`, `log_startup_info: True`
- Status feedback via `RESPOND` messages during macro execution (e.g., "Waiting for bed to heat")
- Telemetry logging available via `[telemetry]` section (enabled in auto-saved config blocks)

## Commenting

**When to Comment:**
- Explain "why" not "what"—configuration keys are self-documenting
- Add comments for non-obvious values or derived calculations
- Comment complex Jinja2 logic and conditional branches
- Document section boundaries for large feature groups

**Style:**
- Single-line comments: `# Comment text` (space after `#`)
- Subsection dividers: `#####################################################################` (all-caps divider rule for new subsystems)
- Examples from codebase:
  ```
  #####################################################################
  #   Bed Heater
  #####################################################################

  # Reset nozzle thermal expansion offset
  ```

**JSDoc/TSDoc:**
- Not used; not applicable to Klipper configuration language
- Descriptions provided in gcode_macro `description:` field:
  ```
  [gcode_macro CANCEL_PRINT]
  description: Cancel the actual running print
  ```

## Function Design

**Macro Size:**
- Range: 7 to 237 lines (observed in codebase)
- Smaller macros (under 50 lines): Focused single-purpose workflows
- Larger macros (100+ lines): Complex multi-step calibration routines with extensive internal logic
- Example sizes:
  - `PARKCENTER`: 7 lines (simple positioning)
  - `PRINT_START`: 70 lines (multi-step print workflow)
  - `BEACON_CALIBRATE_NOZZLE_TEMP_OFFSET`: 237 lines (complex calibration with Jinja2 loops and conditionals)

**Parameters:**
- Passed via `params.NAME` dictionary in macro gcode block
- Always use `|default(value)` filter to handle missing parameters
- Type conversion: `|float`, `|int`, `|lower` filters
- Example: `{% set TEMP = params.TEMP|int %}`

**Return Values:**
- Macros perform actions (motion, heating) rather than returning values
- Data persistence via `SAVE_VARIABLE` (stored in `variables.txt`)
- Status communicated via `RESPOND` messages or LCD display updates

**Calling Patterns:**
- Macros invoke other macros directly: `SYNC_MOTORS`, `CG28`, `QUAD_GANTRY_SCAN`
- Conditional macro invocation based on printer state:
  ```
  {% if printer.configfile.settings.beacon is defined %}
    _BEACON_SET_NOZZLE_TEMP_OFFSET
  {% endif %}
  ```

## Module Design

**Macro Organization:**
- Grouped by subsystem in `macros/` subdirectories
- `Print/`: Print lifecycle (start, end, pause, cancel, resume)
- `Beacon/`: Probe calibration and thermal compensation
- `Heating/`: Temperature management
- `Home_QGL_Mesh/`: Homing, leveling, mesh calibration
- `Filament/`: Filament handling and M600 smart pause

**Public vs. Private Macros:**
- Public: Named with UPPERCASE (invoked by slicers or user commands)
  - `PRINT_START`, `PRINT_END`, `CANCEL_PRINT`, `SYNC_MOTORS`
- Private: Prefixed with underscore and lowercase (internal use only)
  - `_BEACON_SET_NOZZLE_TEMP_OFFSET`, `_CLIENT_RETRACT`
  - Used when macro provides infrastructure for public macros

**Configuration Blocks:**
- Hardware configuration isolated in `hardware/` directory
- Feature toggles in `features/` (included or excluded via `printer.cfg`)
- Constants centralized in `[constants]` section of root config or in macro `variable_*:` blocks

**Reusability:**
- Shared variables stored in `macros/variables.txt` (Klipper's persistent variable system)
- Common calculations extracted into helper macros (e.g., `_BEACON_PROBE_NOZZLE_TEMP_OFFSET`)
- No code duplication; coordinate calculations repeated in similar macros as needed (no DRY principle strictly enforced)

## Auto-Generated Blocks

**SAVE_CONFIG Section:**
- Located at end of `printer.cfg` starting with `#*# <----- SAVE_CONFIG ----->`
- Never manually edited; only modified by Klipper calibration commands
- Contains: bed mesh data, probe models, heater MPC parameters, stepper input shaper tuning
- Rewritten by: `BED_MESH_CALIBRATE`, `PROBE`, `PID_CALIBRATE` commands, etc.
- Protected from git changes by `.gitignore` (recommended practice, though not verified in this repo)

## Special Conventions

**Thermal Compensation:**
- Beacon nozzle expansion coefficient stored as variable: `nozzle_expansion_coefficient`
- Temperature offset calculations use multipliers: `beacon_contact_expansion_multiplier`
- Applied offsets tracked and removed to prevent accumulation: `nozzle_expansion_applied_offset`

**Positioning & Homing:**
- Absolute positioning mode: `G90` (used in most macros)
- Relative positioning: `G91` (used temporarily in `PRINT_END`)
- Z hop strategy: Calculate safe distance based on current position relative to max bounds
- Safe positions use formulas: `X{printer.toolhead.axis_maximum.x/2}` (computed at runtime)

**State Management:**
- Gcode state saved/restored: `SAVE_GCODE_STATE NAME=STATE_NAME`, `RESTORE_GCODE_STATE NAME=STATE_NAME`
- Example: `PARKCENTER` saves/restores state around positioning
- Idle timeout restored: `SET_IDLE_TIMEOUT TIMEOUT={saved_timeout}`

---

*Convention analysis: 2026-01-25*
