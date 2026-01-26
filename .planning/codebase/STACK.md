# Technology Stack

**Analysis Date:** 2026-01-25

## Languages

**Primary:**
- Klipper Configuration (`.cfg`) - Klipper/Kalico hardware and macro definitions for 3D printer control
- Gcode - Motion commands and print operations
- Python - Backend control and extensions via Kalico fork

**Secondary:**
- Bash - Automation and deployment scripts (`autocommit.sh`)
- Shell - System integration and commands

## Runtime

**Environment:**
- Kalico (Klipper fork) - Extended Klipper firmware with advanced features
  - Repository: https://docs.kalico.gg
  - Replaces mainline Klipper with enhanced capabilities (danger_options, motors_sync, MPC heating)

**Host Operating System:**
- Linux (printer host - typical Raspberry Pi or equivalent SBC)
- Runs Klipper/Kalico, Moonraker, Fluidd/Mainsail

**Hardware:**
- STM32H723xx MCU (Octopus main board via USB serial)
- RP2040 MCU (Nitehawk36 toolhead board via USB serial)

## Frameworks & Core Software

**Printer Control:**
- Klipper - Real-time firmware for 3D printer motion control
- Kalico - Enhanced Klipper fork with extended features

**Web/UI Framework:**
- Moonraker - Klipper API server and plugin host (Python)
- Fluidd - Web UI frontend (served via Moonraker)
- Mainsail - Alternative web UI (compatible)
- KlipperScreen - Touchscreen UI (Python/Qt)

**Camera/Streaming:**
- Crowsnest - Multi-camera streaming and MJPEG server

**Testing & Tuning:**
- ShakeTune - Resonance and vibration analysis
- Klipper TMC Autotune - Stepper motor current optimization

## Key Dependencies

**Critical (Installed via Moonraker):**
- Beacon Klipper - Surface scanner probe integration (dev channel, Python, requirements.txt)
- Motors-sync - Dual motor XY synchronization using accelerometer data
- klipper_tmc_autotune - TMC stepper driver parameter tuning
- Klippain-ShakeTune - Resonance tuning framework (beta channel)
- MotionMinder - Linear rail maintenance tracking
- klipper-led_effect - RGB LED control with effects

**Web/UI:**
- KlipperScreen - Touchscreen interface (Git-based, virtualenv, requirements.txt)
- Fluidd - Web interface (web-deployed)
- Crowsnest - Camera streaming (Git-based, managed service)

**External Services (Optional):**
- Spoolman - Filament spool tracking service (external HTTP service at `http://192.168.50.50:7912/`)

**Probe & Sensors:**
- Beacon Surface Scanner RevH - USB serial-connected eddy current probe

## Configuration Files

**Root Configuration:**
- `printer.cfg` - Main configuration entry point with includes
  - Uses glob patterns: `hardware/**/*.cfg`, `macros/**/*.cfg`, `features/**/*.cfg`, `modules/**/*.cfg`

**Moonraker (API/Plugin Host):**
- `moonraker.conf` - Moonraker server, plugins, and update_manager configuration
  - Server: port 7125 (default)
  - Web directory: `/home/yanceya/printer_data`
  - File manager: object processing enabled for KAMP

**Web Streaming:**
- `crowsnest.conf` - Camera streaming configuration (ustreamer, mjpg)
  - Supports multiple cameras via ports 8080-8083
  - Device: `/dev/v4l/by-id/usb-046d_HD_Webcam_C525_...` (Logitech C525)

**UI (KlipperScreen):**
- `KlipperScreen.conf` - Touchscreen UI configuration (auto-generated sections preserved)

**Monitoring:**
- `sonar.conf` - Sonar monitoring configuration

## Build & Deployment

**Installation Scripts:**
- Each Moonraker-managed plugin has its own `install.sh`
- Beacon Klipper: Python requirements install via pip
- KlipperScreen: System dependencies + virtualenv
- Spoolman: Zip-based deployment with virtualenv

**Auto-deployment:**
- `autocommit.sh` - Automated configuration backup script
  - Backs up `~/printer_data/config` to git repo
  - Triggers on changes
  - Pushes to `main` branch (PR target is `master`)

**Validation Commands:**
```bash
# Syntax check
~/klipper/scripts/check_klippy.py printer.cfg

# Motion verification
~/klipper/scripts/calc_estimate.py -c printer.cfg

# Deployment
RESTART  # Fluidd/Moonraker console command

# Verification
STATUS   # Check load and errors
```

## Platform Requirements

**Development/Modification:**
- Text editor (any - config files are plain text .cfg format)
- Git (for version control and autocommit)
- SSH access to printer host
- Bash/shell for running validation scripts

**Production:**
- Linux SBC (Raspberry Pi 4+, Orange Pi, etc.)
- 2+ GB RAM recommended
- Python 3.8+ environment
- USB connections for MCUs and peripherals
- Network connectivity for Moonraker API and UI

**MCU Firmware:**
- Klipper/Kalico firmware compiled for STM32H723 (Octopus board)
- Klipper/Kalico firmware compiled for RP2040 (Nitehawk36 board)

## Environment Configuration

**Hardware Serial Ports:**
- Main MCU: `/dev/serial/by-id/usb-Klipper_stm32h723xx_...` (Octopus)
- Toolhead MCU: `/dev/serial/by-id/usb-Klipper_rp2040_...` (Nitehawk36)
- Beacon Probe: `/dev/serial/by-id/usb-Beacon_Beacon_RevH_...`
- Webcam: `/dev/v4l/by-id/usb-046d_HD_Webcam_C525_...`

**File Paths:**
- Config: `~/printer_data/config/` (default, symlink to git repo in autocommit)
- Gcode queue: `~/printer_data/gcodes/`
- Logs: `~/printer_data/logs/`
- Spoolman database: Assumed at `~/Spoolman/`

**Network:**
- Moonraker API: `http://localhost:7125` (or printer hostname)
- Spoolman: `http://192.168.50.50:7912/` (fixed IP, LAN)
- CORS domains configured: `*.local`, `*.lan`, `tools.annex.engineering`, `app.fluidd.xyz`

## Extended Features (Kalico-Specific)

**Model Predictive Control (MPC):**
- Bed heater: MPC instead of PID (400W heater)
- Extruder: MPC instead of PID (100W heater)
- Block heat capacity, sensor responsiveness, fan transfer coefficients auto-tuned

**Beacon Integration:**
- Thermal expansion compensation via coil temperature
- Contact-based homing with calibration
- Proximity-based homing for repetitive moves
- Eddy current sensing independent of nozzle cleanliness

**Motor Synchronization (motors-sync):**
- Dual X motors: synchronized via Beacon accelerometer feedback
- Dual Y motors: synchronized via Beacon accelerometer feedback
- Exponential displacement model with calibrated coefficients

**Quad Gantry Leveling (QGL):**
- 4 independent Z steppers (stepper_z, z1, z2, z3)
- Automated leveling with adaptive mesh

**Danger Options (Kalico):**
- Autosave recursive includes for SAVE_CONFIG blocks
- Logging control options
- Multi-MCU synchronization timeout tuning
- Temperature limit override capability

---

*Stack analysis: 2026-01-25*
