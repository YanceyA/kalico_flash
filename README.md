# kalico-flash

One-command firmware building and flashing for Kalico/Klipper USB boards.

## Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/USER/kalico-flash.git ~/kalico-flash
   cd ~/kalico-flash
   ```

2. **Install:**
   ```bash
   ./install.sh
   ```
   Expected output: `Installed kflash -> /home/pi/kalico-flash/kalico-flash/flash.py`

3. **Add your first device:**
   ```bash
   kflash --add-device
   ```
   Follow the wizard to register a connected board.

4. **Flash:**
   ```bash
   kflash
   ```
   Select your device from the menu, or use `kflash -d DEVICE_KEY` directly.

## Features

### Interactive TUI Menu

Run `kflash` with no arguments to get an interactive menu:

```
kflash

  kalico-flash v0.1.0

  1) Flash a device
  2) Add new device
  3) List devices
  4) Remove device
  5) Settings
  6) Exit

  Select [1-6]:
```

### Skip Menuconfig

Use `-s` to skip the menuconfig TUI when a cached config exists:

```bash
kflash -d octopus-pro -s
```

This uses the previously saved config, validates the MCU, builds, and flashes in one step. If no cached config exists, menuconfig launches anyway with a warning.

### Device Exclusion

Mark devices that shouldn't be flashed (like Beacon probes that manage their own firmware):

```bash
kflash --exclude-device beacon
```

Excluded devices appear in listings with `[excluded]` but aren't selectable for flashing. To re-enable:

```bash
kflash --include-device beacon
```

### Print Safety

kalico-flash checks Moonraker before flashing. If a print is in progress:

```
[Safety] Printer state: printing - 47% complete
ERROR: Printer busy
  Print in progress: benchy.gcode (47%)

Recovery:
  1. Wait for current print to complete
  2. Or cancel print in Fluidd/Mainsail dashboard
  3. Then re-run flash command
```

If Moonraker is unreachable, you're warned and asked to confirm before proceeding.

### Version Display

Before flashing, kalico-flash shows host Klipper version and MCU firmware versions:

```
[Version] Host Klipper: v0.12.0-299-g1a2b3c4d
[Version]   [*] MCU main: v0.12.0-250-g5e6f7a8b
[Version]   [ ] MCU nhk: v0.12.0-250-g5e6f7a8b
```

The `*` marks the MCU being flashed. If the MCU firmware is behind the host version, you'll see a warning recommending the update.

### Post-Flash Verification

After flashing, kalico-flash waits up to 30 seconds for the device to reappear with its Klipper serial identity:

```
[Flash] Flashing firmware...
[Verify] Waiting for device to reappear...
[Verify] Device confirmed at: /dev/serial/by-id/usb-Klipper_stm32h723xx_...
[OK] Flashed Octopus Pro v1.1 via katapult in 8.2s
```

If the device doesn't reappear or reappears with the wrong serial prefix, you'll get specific recovery steps.

## CLI Reference

| Command | Description | Example |
|---------|-------------|---------|
| `kflash` | Interactive menu | `kflash` |
| `kflash -d KEY` | Flash specific device | `kflash -d octopus-pro` |
| `kflash -d KEY -s` | Flash, skip menuconfig | `kflash -d octopus-pro -s` |
| `kflash --add-device` | Register new device | `kflash --add-device` |
| `kflash --list-devices` | Show registered devices | `kflash --list-devices` |
| `kflash --remove-device KEY` | Remove device | `kflash --remove-device old-board` |
| `kflash --exclude-device KEY` | Mark non-flashable | `kflash --exclude-device beacon` |
| `kflash --include-device KEY` | Mark flashable | `kflash --include-device beacon` |
| `kflash --version` | Show version | `kflash --version` |
| `kflash --help` | Show help | `kflash --help` |

**Short flags:**
- `-d KEY` is shorthand for `--device KEY`
- `-s` is shorthand for `--skip-menuconfig`

## Installation

### Requirements

- **Python 3.9+** (stdlib only, no pip dependencies)
- **Raspberry Pi** or similar Linux SBC running Klipper/Moonraker
- **Klipper source** at `~/klipper` (or custom path, configured on first run)
- **Katapult** at `~/katapult` (optional, for preferred flash method)
- **Passwordless sudo** for service control (standard on MainsailOS/FluiddPi)
- **USB-connected boards** (CAN bus devices not supported)

### Install Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/USER/kalico-flash.git ~/kalico-flash
   ```

2. Run the install script:
   ```bash
   cd ~/kalico-flash
   ./install.sh
   ```

The install script:
- Creates a symlink from `~/.local/bin/kflash` to the flash.py entry point
- Checks prerequisites (Python version, Klipper directory, serial access) and warns if issues found
- Offers to add `~/.local/bin` to your PATH if not already present

Because the install uses a symlink, updates via `git pull` take effect immediately without re-running the installer.

### Verify Installation

```bash
kflash --version
```

Expected output: `kalico-flash v0.1.0`

## Automatic Updates

Add to `moonraker.conf` for automatic updates through Fluidd/Mainsail:

```ini
[update_manager kalico-flash]
type: git_repo
path: ~/kalico-flash
origin: https://github.com/USER/kalico-flash.git
primary_branch: master
is_system_service: False
```

After adding, restart Moonraker:

```bash
sudo systemctl restart moonraker
```

kalico-flash will then appear in the Update Manager section of your dashboard. Updates are applied via `git pull` - no service restart needed since kflash is a CLI tool, not a daemon.

## Uninstall

To remove kalico-flash:

```bash
cd ~/kalico-flash
./install.sh --uninstall
```

This removes the `kflash` symlink from `~/.local/bin`. The repository and any cached configs remain and can be deleted manually:

```bash
rm -rf ~/kalico-flash
rm -rf ~/.config/kalico-flash
```

To remove the Update Manager entry, delete the `[update_manager kalico-flash]` section from `moonraker.conf` and restart Moonraker.

## Supported Boards

Tested with:
- **BTT Octopus Pro v1.1** - STM32H723, USB, 128KB bootloader
- **LDO Nitehawk 36** - RP2040, USB, 16KB bootloader

Should work with any USB-connected board that:
- Appears in `/dev/serial/by-id/` with `Klipper_` or `katapult_` prefix
- Supports `make flash` or Katapult flashing

CAN bus devices are not supported - USB only.

## How It Works

When you run `kflash`, the tool executes four phases:

1. **Discovery** - Scans `/dev/serial/by-id/` for USB serial devices, matches against registered device patterns
2. **Config** - Loads cached menuconfig settings, optionally launches menuconfig for review, validates MCU type
3. **Build** - Runs `make clean` + `make -j$(nproc)` with timeout protection
4. **Flash** - Stops Klipper service, flashes via Katapult (or `make flash` fallback), verifies device reappears, restarts Klipper

The Klipper service is guaranteed to restart even if flashing fails or you press Ctrl+C.

## License

This project is provided as-is for personal use with Klipper/Kalico 3D printing setups.

## Acknowledgments

Built for [Kalico](https://docs.kalico.gg), a Klipper fork with advanced input shaping features.
