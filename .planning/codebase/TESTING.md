# Testing Patterns

**Analysis Date:** 2026-01-25

## Test Framework

**Runner:**
- Not automated; Klipper lacks a built-in test framework for configurations
- Manual validation via command-line tools and interactive testing

**Assertion Library:**
- Not applicable; configuration is validated syntactically, not logically

**Run Commands:**
```bash
# Syntax validation
~/klipper/scripts/check_klippy.py printer.cfg              # Validate configuration syntax

# Motion limit verification (if altering speeds/accelerations)
~/klipper/scripts/calc_estimate.py -c printer.cfg          # Calculate motion estimates

# Deploy changes
RESTART                                                     # Restart Klipper from Fluidd/Moonraker console

# Verify clean load
STATUS                                                      # Check for startup errors from printer console
```

## Test File Organization

**Location:**
- No formal test directory structure
- Testing is performed interactively on live printer hardware
- Configuration backups stored in `config_backups/` (timestamped by Moonraker)

**Naming:**
- Configuration files use descriptive names matching their function: `print_start.cfg`, `beacon_temp_comp.cfg`
- Test macros (if any) would follow naming convention: `TEST_*` prefix
- Example found: `macros/Home_QGL_Mesh/TEST.cfg`

**Structure:**
```
macros/
├── Print/              # Print lifecycle macros
├── Beacon/             # Probe calibration macros
├── Heating/            # Heating control macros
├── Home_QGL_Mesh/      # Homing and leveling macros
│   └── TEST.cfg        # Test/utility macros
└── variables.txt       # Persistent test data storage
```

## Test Structure

**Manual Testing Flow:**

Before deploying configuration changes, follow this sequence from `CLAUDE.md`:

1. **Syntax Validation:**
   ```bash
   ~/klipper/scripts/check_klippy.py printer.cfg
   ```
   - Verifies all sections, options, and macro syntax are valid
   - Catches typos, missing dependencies, invalid pin definitions
   - Must pass before any printer restart

2. **Motion Verification:**
   ```bash
   ~/klipper/scripts/calc_estimate.py -c printer.cfg
   ```
   - Required if modifying stepper settings, velocities, or accelerations
   - Validates motor speed/acceleration limits are realistic
   - Prevents hardware damage from unreachable speed targets

3. **Configuration Load Test:**
   - Issue `RESTART` from Fluidd/Moonraker console
   - Klipper loads configuration and connects to MCUs
   - Monitor Klipper logs for errors during startup

4. **Status Verification:**
   - Execute `STATUS` command from printer console
   - Confirms no critical errors during initialization
   - Checks that all configured hardware detected (MCUs, sensors, fans)

5. **Functional Testing:**
   - For macro changes: Test with dry-run or isolated invocation
   - Use `FIRMWARE_RESTART` as safety net (immediate halt if issues)
   - Example: Test `PRINT_START` without printing, verify all steps execute

**Patterns:**

Test execution pattern for macros:
```
1. Load macro with syntax validation: check_klippy.py
2. Restart Klipper: RESTART command
3. Invoke macro: Macro_Name [PARAMS]
4. Monitor output: Check RESPOND messages and motion
5. Verify state: Use STATUS or query-specific subsystems
6. Rollback if needed: Revert file and RESTART
```

Conditional testing example from `beacon_temp_comp.cfg`:
```jinja2
{% if printer.toolhead.homed_axes != "xyz" %}
  G28  # Home if not already homed
{% endif %}

{% if printer.quad_gantry_level is defined and not printer.quad_gantry_level.applied %}
  QUAD_GANTRY_LEVEL  # Perform QGL if enabled and not applied
{% endif %}
```

## Mocking

**Framework:**
- Not applicable; Klipper doesn't support mock objects or dependency injection
- Hardware simulation possible but not configured in this repository

**Patterns:**
- Conditional code execution based on printer capabilities:
  ```jinja2
  {% if printer.configfile.settings.beacon is defined %}
    _BEACON_SET_NOZZLE_TEMP_OFFSET
  {% endif %}
  ```
- Allows safe execution on printers without Beacon probe
- Similar pattern for optional features (KAMP, input_shaper, quad_gantry_level)

**What to Mock:**
- N/A—Klipper configurations run directly on hardware
- Testing involves actual MCU communication and sensor reads
- Cannot mock sensor readings, motor movement, or hardware state

**What NOT to Mock:**
- N/A—Same reasoning as above
- All hardware interaction is real-time and synchronous

## Fixtures and Factories

**Test Data:**
- Persistent variables stored in `macros/variables.txt` (INI-format file)
- Example fixture:
  ```ini
  [Variables]
  nozzle_expansion_applied_offset = 0
  nozzle_expansion_coefficient = 0.04
  ```

- Beacon calibration data stored as auto-saved config block:
  ```cfg
  #*# [beacon model default]
  #*# model_coef = 1.441092980020675, ...
  #*# model_temp = 21.432079
  ```

**Location:**
- `macros/variables.txt`: User-defined persistent variables
- `printer.cfg` SAVE_CONFIG block: Auto-tuned hardware parameters (bed mesh, probe model, MPC parameters)
- `config_backups/printer-YYYYMMDD_HHMMSS.cfg`: Timestamped snapshots for regression testing

**Setup Pattern:**
```jinja2
# Load variables from persistent storage
{% set svv = printer.save_variables.variables %}

# Read previously calibrated values
{% set nozzle_expansion_coefficient = svv.nozzle_expansion_coefficient|default(0)|float %}

# Read macro-local variables
{% set reference_z = printer["gcode_macro BEACON_CALIBRATE_NOZZLE_TEMP_OFFSET"].reference_z|default(0)|float %}
```

**Teardown Pattern:**
- No explicit teardown; state persisted via `SAVE_VARIABLE`
- Example: `SAVE_VARIABLE VARIABLE=nozzle_expansion_applied_offset VALUE=0` (reset offset after print)

## Coverage

**Requirements:**
- No automated coverage tracking configured
- Manual review: Verify all code paths exercised at least once before production

**View Coverage:**
- Manual inspection via:
  ```bash
  grep -r "^gcode:" macros/  # Find all macro entry points
  grep -r "{% if" macros/    # Find all conditional branches
  grep "RESPOND" *.cfg       # Trace status messages to verify execution paths
  ```

**Coverage Gaps Found:**
- No formal testing of edge cases (printer already homed, out of bounds movements, etc.)
- Handled via conditionals: `{% if printer.toolhead.homed_axes != "xyz" %}`
- Error tolerance relies on Klipper runtime validation

## Test Types

**Unit Tests:**
- Not applicable in Klipper configuration context
- Individual macros can be invoked in isolation to verify behavior
- Example: Test `PARKCENTER` macro independently without print cycle
- Verification: Check toolhead position after execution via `STATUS` command

**Integration Tests:**
- Test macro chains (e.g., `PRINT_START` → all sub-steps execute correctly)
- Verify hardware state transitions:
  - `PRINT_START`: Lights on → Motors sync → Home → Heat → Mesh → Purge
  - `PRINT_END`: Retract → Park → Cool → Lights off
- Check data flow: Variables saved and retrieved correctly

**E2E Tests:**
- Full print cycle with real G-code from slicer (SuperSlicer)
- Trigger: Upload .gcode file to printer and execute
- Success criteria:
  - Print starts without errors
  - `PRINT_START` completes all initialization steps
  - Print executes motion commands correctly
  - `PRINT_END` cleans up state properly

**Hardware Validation:**
- `BEACON_CALIBRATE_NOZZLE_TEMP_OFFSET`: Full calibration cycle with nozzle movement, temperature changes, probe sampling
- `QUAD_GANTRY_SCAN`: Verify all four Z steppers level correctly
- `BED_MESH_CALIBRATE`: Probe entire bed, verify mesh generated with adaptive mode
- Motion verification: `calc_estimate.py` confirms stepper accelerations achievable

## Common Patterns

**Conditional Macro Execution:**

Safe invocation pattern—skip if feature not configured:
```jinja2
{% if printer.configfile.settings.beacon is defined %}
  _BEACON_SET_NOZZLE_TEMP_OFFSET
{% endif %}
```

**Parameter Handling with Defaults:**

```jinja2
{% set BED_TEMP = params.BED_TEMP|default(60)|float %}
{% set EXTRUDER_TEMP = params.EXTRUDER_TEMP|default(190)|float %}
```

Test by invoking with and without parameters:
```
PRINT_START                                     # Uses all defaults
PRINT_START BED_TEMP=80 EXTRUDER_TEMP=210     # Override defaults
```

**Async Testing (Temperature Waits):**

Macros with temperature waits must complete within timeout:
```jinja2
TEMPERATURE_WAIT SENSOR=extruder MINIMUM={temp} MAXIMUM={temp + 2}
```

Test by:
1. Verify heater can reach target temperature within reasonable time
2. Verify TEMPERATURE_WAIT doesn't hang indefinitely
3. Monitor thermal response time via logs

**Error Handling via Conditionals:**

Safe positioning logic prevents out-of-bounds moves:
```jinja2
{% if printer.toolhead.position.x < (max_x - 20) %}
  {% set x_safe = 20.0 %}
{% else %}
  {% set x_safe = -20.0 %}
{% endif %}
```

Test by:
1. Execute at various toolhead positions
2. Verify safety margin always maintained
3. Check no axis limit violation errors

**Variable Persistence:**

Test variable save/restore cycle:
```
# Save variable
SAVE_VARIABLE VARIABLE=test_var VALUE=123

# Retrieve and verify
[Macro execution reads: svv.test_var = 123]
```

**State Restoration:**

Verify state is properly saved and restored:
```jinja2
SAVE_GCODE_STATE NAME=MYSTATE
# Perform operations
RESTORE_GCODE_STATE NAME=MYSTATE
```

Test by checking position, feedrate, and other state after restore.

## Validation Checklist

Before deploying configuration changes to printer:

1. **Syntax Check:** `check_klippy.py printer.cfg` passes
2. **Motion Calc:** `calc_estimate.py -c printer.cfg` passes (if speeds/accel changed)
3. **Load Test:** `RESTART` completes without errors
4. **Status Check:** `STATUS` shows no critical errors
5. **Macro Test:** Invoke affected macros with test parameters
6. **Hardware Test:** Verify sensor reads and motor movement if relevant
7. **Integration Test:** Run `PRINT_START` dry-run through completion
8. **Backup:** Manual `autocommit.sh` or rely on Moonraker's auto-backup

## Known Limitations

- No unit testing framework; all tests are integration/system-level
- No continuous integration pipeline configured
- Manual testing required for all changes (no automated regression suite)
- Configuration changes deployed to live hardware immediately (high risk if untested)
- No canary deployments or staged rollouts

---

*Testing analysis: 2026-01-25*
