# Phase 7: Release Polish - Research

**Researched:** 2026-01-27
**Scope:** Install script, README documentation, Moonraker Update Manager integration
**Confidence:** HIGH (patterns verified against official Moonraker docs and Klipper ecosystem tools)

## Executive Summary

Phase 7 delivers installation and documentation for kalico-flash. Research confirms the planned approach aligns with Klipper ecosystem conventions: symlink-based installation to `~/.local/bin` (XDG-compliant), `git_repo` type for Moonraker Update Manager, and README-centric documentation with quick start focus.

Key findings:
1. **Install script**: Symlink approach is correct; use `ln -sfn` for idempotency; `~/.local/bin` is XDG standard for user executables
2. **Update Manager**: `is_system_service: False` is the correct setting for tools that don't need service restarts
3. **Troubleshooting**: CONTEXT.md decision to skip troubleshooting section is validated - error templates in `errors.py` already provide comprehensive recovery guidance
4. **README structure**: Quick start should be 4 numbered steps with copy-paste commands and expected output

---

## Installation Script Patterns

### Klipper Ecosystem Conventions

Research into KIAUH, Katapult, and moonraker-timelapse reveals a common pattern:

| Tool | Install Method | Symlink? | Update Manager |
|------|---------------|----------|----------------|
| KIAUH | Clone + run directly | No | Not applicable |
| Katapult | Clone + make | No | `git_repo` |
| moonraker-timelapse | Clone + config | No | `git_repo` with `managed_services` |
| crowsnest | Clone + installer | Yes | `git_repo` |

**Insight:** Most tools run directly from clone directory (`./tool/script.sh`). kalico-flash's symlink approach to create a `kflash` command is a convenience enhancement, not the norm. This is fine - it matches user expectations from Phase 6 context discussion.

Sources:
- [KIAUH GitHub](https://github.com/dw-0/kiauh) - Direct execution model
- [Katapult GitHub](https://github.com/Arksine/katapult) - Clone and build
- [moonraker-timelapse installation](https://raw.githubusercontent.com/mainsail-crew/moonraker-timelapse/main/docs/installation.md) - Clone with Update Manager

### XDG Base Directory Compliance

The `~/.local/bin` directory is the XDG-specified location for user executables:

> "User-specific executable files may be stored in $HOME/.local/bin. Distributions should ensure this directory shows up in the UNIX $PATH environment variable."
> - [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir/latest/)

**Key point:** There is no `XDG_BIN_HOME` environment variable. The spec hardcodes `~/.local/bin` as the user bin location, mirroring how `~/.local` is the user equivalent of `/usr/local`.

**PATH handling:** Not all distributions add `~/.local/bin` to PATH by default. The install script must:
1. Check if `~/.local/bin` is in PATH
2. Warn user if not
3. Offer to add it (per CONTEXT.md decision)

### Idempotent Bash Script Techniques

From [How to write idempotent Bash scripts](https://arslan.io/2019/07/03/how-to-write-idempotent-bash-scripts/):

**Directory creation:**
```bash
mkdir -p ~/.local/bin  # -p prevents error if exists
```

**Symlink creation:**
```bash
ln -sfn /path/to/source /path/to/target
# -s: symbolic link
# -f: remove existing target
# -n: don't follow existing symlink (prevents creating link inside directory)
```

**PATH modification check:**
```bash
if [[ ":${PATH}:" != *":${HOME}/.local/bin:"* ]]; then
    # Not in PATH - offer to add
fi
```

The colon-wrapping technique (`":${PATH}:"` with `*":dir:"*`) prevents partial matches (e.g., `/usr/local/bin` matching `/usr/local/binet`).

**File modification idempotency:**
```bash
if ! grep -qF 'export PATH="$HOME/.local/bin:$PATH"' ~/.bashrc; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
fi
```

### Uninstall Support

CONTEXT.md specifies `./install.sh --uninstall` (single script with flag) rather than separate `uninstall.sh`.

Implementation:
```bash
#!/usr/bin/env bash
if [[ "$1" == "--uninstall" ]]; then
    # Remove symlink
    rm -f ~/.local/bin/kflash
    # Optionally warn about PATH entry (don't remove - may affect other tools)
    exit 0
fi
# ... normal install
```

**Decision:** Don't automatically remove PATH addition on uninstall. User may have added it for other tools. Just remove the symlink.

---

## Moonraker Update Manager Configuration

### Official Configuration Format

From [Moonraker Configuration Documentation](https://moonraker.readthedocs.io/en/latest/configuration/):

For a simple git repo that doesn't require service restarts:

```ini
[update_manager kalico-flash]
type: git_repo
path: ~/kalico-flash
origin: https://github.com/USER/kalico-flash.git
primary_branch: master
is_system_service: False
```

**Key fields:**

| Field | Value | Rationale |
|-------|-------|-----------|
| `type` | `git_repo` | Standard for Klipper ecosystem tools |
| `path` | `~/kalico-flash` | Where user cloned the repo |
| `origin` | GitHub URL | For update detection |
| `primary_branch` | `master` | Per CONTEXT.md decision |
| `is_system_service` | `False` | No service restart needed after update |

**Not needed:**
- `managed_services`: kalico-flash doesn't run as a service
- `virtualenv`: No Python venv (stdlib only)
- `requirements`: No pip dependencies
- `install_script`: Symlink means `git pull` is sufficient (per CONTEXT.md)
- `system_dependencies`: No apt packages required at runtime

### Comparison with Similar Tools

**moonraker-timelapse:**
```ini
[update_manager timelapse]
type: git_repo
primary_branch: main
path: ~/moonraker-timelapse
origin: https://github.com/mainsail-crew/moonraker-timelapse.git
managed_services: klipper moonraker
```

**crowsnest:**
```ini
[update_manager crowsnest]
type: git_repo
path: ~/crowsnest
origin: https://github.com/mainsail-crew/crowsnest.git
primary_branch: nightly
```

kalico-flash is simpler than these - no service management, no dependencies.

Sources:
- [Moonraker Configuration](https://moonraker.readthedocs.io/en/latest/configuration/)
- [moonraker-timelapse docs](https://github.com/mainsail-crew/moonraker-timelapse/blob/main/docs/installation.md)
- [Update Manager API](https://moonraker.readthedocs.io/en/latest/external_api/update_manager/)

---

## README Documentation Patterns

### Best Practices for Quick Start

From [README Best Practices](https://github.com/jehna/readme-best-practices) and [Make a README](https://www.makeareadme.com/):

1. **Keep it short**: "A quick introduction of the minimal setup you need to get a hello world up & running"
2. **Copy-paste ready**: Include actual commands user can run
3. **Show expected output**: User knows they're on track
4. **No tutorial sprawl**: Link to detailed docs if needed

**Recommended quick start structure:**
```markdown
## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/USER/kalico-flash.git
   cd kalico-flash
   ```

2. Install:
   ```bash
   ./install.sh
   ```

3. Add your first device:
   ```bash
   kflash --add-device
   ```

4. Flash:
   ```bash
   kflash
   ```
```

### CLI Reference Format

For DOC-03 (all CLI commands documented), use a table format:

```markdown
## CLI Reference

| Command | Description | Example |
|---------|-------------|---------|
| `kflash` | Interactive menu | `kflash` |
| `kflash -d KEY` | Flash specific device | `kflash -d octopus-pro` |
| `kflash -d KEY -s` | Flash with skip-menuconfig | `kflash -d octopus-pro -s` |
| `kflash --add-device` | Register new device | `kflash --add-device` |
| ... | ... | ... |
```

### Troubleshooting Decision Validation

CONTEXT.md decision: "No troubleshooting section - the tool's inline error messages already provide recovery steps."

**Validation:** Reviewed `errors.py` and confirmed ERROR_TEMPLATES provides comprehensive coverage:

| Error Category | Template Key | Recovery Steps |
|---------------|--------------|----------------|
| Build failures | `build_failed`, `menuconfig_failed` | Toolchain check, directory verification |
| Device issues | `device_not_registered`, `device_not_connected` | USB check, registration commands |
| MCU mismatch | `mcu_mismatch` | Config verification |
| Service errors | `service_stop_failed`, `service_start_failed` | systemctl commands |
| Flash failures | `flash_failed`, `verification_timeout` | Bootloader entry, USB check |
| Moonraker | `moonraker_unavailable`, `printer_busy` | Service check, API verification |

Each template includes:
- Numbered recovery steps
- Diagnostic commands to copy/paste
- Context-aware messaging

**Conclusion:** README troubleshooting section would duplicate error framework. Skip per CONTEXT.md decision. DOC-04 requirement ("Common errors have troubleshooting entries") is satisfied by the inline error messages.

---

## Python Script Execution

### Shebang Best Practice

kalico-flash's `flash.py` currently has:
```python
#!/usr/bin/env python3
```

This is correct per [Python Shebang Best Practices](https://www.datacamp.com/tutorial/python-shebang):
- Uses `env` for portability across systems
- Specifies `python3` explicitly (not bare `python`)
- Works with virtual environments if activated

**No changes needed** to `flash.py` for install script to work.

### Symlink Execution

When `kflash` symlink points to `flash.py`:
1. User runs `kflash`
2. Shell follows symlink to `~/kalico-flash/kalico-flash/flash.py`
3. Shebang `#!/usr/bin/env python3` invokes Python interpreter
4. Script executes with correct working directory

**Important:** The symlink should point to the inner `kalico-flash/flash.py`, not the repo root.

---

## Implementation Recommendations

### Install Script Structure

```bash
#!/usr/bin/env bash
set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
COMMAND_NAME="kflash"
TARGET="${SCRIPT_DIR}/kalico-flash/flash.py"

# Handle --uninstall
if [[ "${1:-}" == "--uninstall" ]]; then
    rm -f "${BIN_DIR}/${COMMAND_NAME}"
    echo "Removed ${COMMAND_NAME}"
    exit 0
fi

# Prerequisite checks (warn only, per CONTEXT.md)
check_python_version
check_kalico_directory
check_serial_access

# Create bin directory
mkdir -p "${BIN_DIR}"

# Create symlink (idempotent)
ln -sfn "${TARGET}" "${BIN_DIR}/${COMMAND_NAME}"

# PATH check
if [[ ":${PATH}:" != *":${BIN_DIR}:"* ]]; then
    warn_and_offer_path_fix
fi

echo "Installed ${COMMAND_NAME}"
```

### Update Manager Snippet for README

```ini
# Add to moonraker.conf for automatic updates
[update_manager kalico-flash]
type: git_repo
path: ~/kalico-flash
origin: https://github.com/USER/kalico-flash.git
primary_branch: master
is_system_service: False
```

### README Section Order

Based on best practices and CONTEXT.md decisions:

1. **Title + one-line description**
2. **Quick Start** (4 numbered steps)
3. **Features** (with examples)
4. **CLI Reference** (table)
5. **Installation** (detailed)
6. **Update Manager** (Moonraker config)
7. **Uninstall**

---

## Pitfalls and Warnings

### PATH Not Updated in Current Session

After adding `~/.local/bin` to `~/.bashrc`, the current shell session won't see it until:
- User runs `source ~/.bashrc`, or
- User opens a new terminal

Install script should print this reminder.

### Symlink Points to Wrong Location

The repo structure is:
```
kalico-flash/           # repo root
  kalico-flash/         # source directory
    flash.py            # entry point
  install.sh            # install script (to be created)
```

Symlink must point to `kalico-flash/kalico-flash/flash.py`, not `kalico-flash/flash.py` (doesn't exist at repo root).

### Git Pull May Change Requirements

Future versions might add dependencies. The Update Manager config has no `install_script`, so users would need to re-run install manually if that happens. For v1.0 (stdlib only), this is fine.

### argparse prog Name

Current `flash.py` has:
```python
parser = argparse.ArgumentParser(
    prog="flash.py",
    ...
)
```

This should be updated to `prog="kflash"` so help text shows the correct command name after installation.

---

## Confidence Assessment

| Area | Confidence | Source Quality |
|------|------------|----------------|
| Install script patterns | HIGH | Official XDG spec, bash best practices |
| Update Manager config | HIGH | Official Moonraker docs |
| README structure | HIGH | Industry best practices, ecosystem examples |
| Troubleshooting skip | HIGH | Verified error templates in codebase |
| Symlink approach | MEDIUM | Less common in ecosystem but valid |

---

## Sources

### Official Documentation
- [Moonraker Configuration](https://moonraker.readthedocs.io/en/latest/configuration/) - Update Manager options
- [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir/latest/) - `~/.local/bin` standard
- [Python Shebang Best Practices](https://www.datacamp.com/tutorial/python-shebang) - `#!/usr/bin/env python3`

### Klipper Ecosystem Examples
- [KIAUH GitHub](https://github.com/dw-0/kiauh) - Install patterns
- [Katapult GitHub](https://github.com/Arksine/katapult) - Clone-based tool
- [moonraker-timelapse](https://github.com/mainsail-crew/moonraker-timelapse) - Update Manager example

### Best Practices
- [How to write idempotent Bash scripts](https://arslan.io/2019/07/03/how-to-write-idempotent-bash-scripts/) - Idempotency techniques
- [README Best Practices](https://github.com/jehna/readme-best-practices) - Documentation structure
- [Make a README](https://www.makeareadme.com/) - Quick start guidelines

---

*Phase: 07-release-polish*
*Research completed: 2026-01-27*
