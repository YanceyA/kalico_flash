# kalico-flash

One-command firmware building and flashing for Kalico/Klipper USB boards.

## Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/<your-org>/kalico-flash.git ~/kalico-flash
   cd ~/kalico-flash
   ```

2. **Install:**
   ```bash
   ./install.sh
   ```
   Expected output: `Installed kflash -> /home/pi/kalico-flash/kflash.py`

3. **Run kflash:**
   ```bash
   kflash
   ```
   The TUI guides you through adding your first device and flashing.

## Features

### Interactive TUI

Run `kflash` to launch the full-screen TUI. The main screen displays:

- **Status panel** -- registered devices with connection status and firmware versions
- **Actions panel** -- available operations

Available actions:

- **Flash Device (F)** -- select a connected device, run menuconfig, build, and flash
- **Flash All (A)** -- flash all connected (non-excluded) devices sequentially
- **Add Device (N)** -- register a new USB device with interactive prompts for name and MCU
- **Remove Device (X)** -- remove a registered device
- **Config Device (C)** -- edit device settings (name, MCU, flash method, exclusion)
- **Refresh Devices (R)** -- re-scan USB devices and update the status panel
- **Quit (Q)** -- exit

### Device Exclusion

Mark devices that should not be flashed (like Beacon probes that manage their own firmware). Use **Config Device** from the main menu to toggle a device's excluded status.

Excluded devices appear in the status panel with `[excluded]` but are not selectable for flashing.

### Flash Method and Fallback

kalico-flash uses **Katapult** by default. Each device can store a preferred flash method during registration, and the global default is Katapult.

If **flash fallback** is enabled, a failed Katapult flash will automatically fall back to `make flash`. If disabled, flashing is strict (Katapult-only).

You can toggle fallback in the Settings menu:

```
Settings -> Toggle flash fallback (Katapult -> make flash)
```

### Unknown Device Blocking

Only Klipper/Katapult USB devices are eligible for registration. Devices that do not appear with a `usb-Klipper_` or `usb-katapult_` prefix are shown as **blocked** and cannot be added or flashed.

### Print Safety

kalico-flash checks Moonraker before flashing. If a print is in progress, you will see an error with the print name and progress percentage.

Recovery:
1. Wait for the current print to complete
2. Or cancel the print in Fluidd/Mainsail dashboard
3. Then use Flash Device from the main menu

If Moonraker is unreachable, you are warned and asked to confirm before proceeding.

### Version Display

Before flashing, kalico-flash shows host Klipper version and MCU firmware versions:

```
[Version] Host Klipper: v0.12.0-299-g1a2b3c4d
[Version]   [*] MCU main: v0.12.0-250-g5e6f7a8b
[Version]   [ ] MCU nhk: v0.12.0-250-g5e6f7a8b
```

The `*` marks the MCU being flashed. If the MCU firmware is behind the host version, you will see a warning recommending the update.

### Post-Flash Verification

After flashing, kalico-flash waits up to 30 seconds for the device to reappear with its Klipper serial identity:

```
[Flash] Flashing firmware...
[Verify] Waiting for device to reappear...
[Verify] Device confirmed at: /dev/serial/by-id/usb-Klipper_stm32h723xx_...
[OK] Flashed Octopus Pro v1.1 via katapult in 8.2s
```

If the device does not reappear or reappears with the wrong serial prefix, you will get specific recovery steps.

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
   git clone https://github.com/<your-org>/kalico-flash.git ~/kalico-flash
   ```

2. Run the install script:
   ```bash
   cd ~/kalico-flash
   ./install.sh
   ```

The install script:
- Creates a symlink from `~/.local/bin/kflash` to the kflash.py entry point
- Checks prerequisites (Python version, Klipper directory, serial access) and warns if issues found
- Offers to add `~/.local/bin` to your PATH if not already present

Because the install uses a symlink, updates via `git pull` take effect immediately without re-running the installer.

### Verify Installation

```bash
kflash
```

The TUI header displays the current version.

## Automatic Updates

Add to `moonraker.conf` for automatic updates through Fluidd/Mainsail:

```ini
[update_manager kalico-flash]
type: git_repo
path: ~/kalico-flash
origin: https://github.com/<your-org>/kalico-flash.git
primary_branch: main  # or your repo's default branch
is_system_service: False
```

After adding, restart Moonraker:

```bash
sudo systemctl restart moonraker
```

kalico-flash will then appear in the Update Manager section of your dashboard. Updates are applied via `git pull` - no service restart needed since kflash is a TUI tool, not a daemon.

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

When you launch `kflash` and select Flash Device, the tool executes four phases:

1. **Discovery** - Scans `/dev/serial/by-id/` for USB serial devices, matches against registered device patterns
2. **Config** - Loads cached menuconfig settings, launches menuconfig for review, validates MCU type

   **Config loading behavior:**

   | Scenario | What happens |
   |----------|-------------|
   | Device has cached config | Loads saved settings into menuconfig |
   | Device has no cached config | Clears any stale `.config` so menuconfig starts fresh |
   | Device removed, config kept | Re-adding loads the kept cached config |
   | Device removed, config deleted | Re-adding starts menuconfig fresh |
3. **Build** - Runs `make clean` + `make -j$(nproc)` with timeout protection
4. **Flash** - Stops Klipper service, flashes via the preferred method, optionally falls back to `make flash`, verifies device reappears, restarts Klipper

The Klipper service is guaranteed to restart even if flashing fails or you press Ctrl+C.

## License

This project is provided as-is for personal use with Klipper/Kalico 3D printing setups.

## Acknowledgments

Built for [Kalico](https://docs.kalico.gg), a Klipper fork with advanced input shaping features.
