#!/usr/bin/env bash
# install.sh - Install kalico-flash as 'kflash' command
#
# Usage:
#   ./install.sh             Install kflash to ~/.local/bin
#   ./install.sh --uninstall Remove kflash symlink

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
COMMAND_NAME="kflash"
TARGET="${SCRIPT_DIR}/kflash.py"

# Color support
if [[ -t 1 ]] && command -v tput &>/dev/null && [[ $(tput colors 2>/dev/null || echo 0) -ge 8 ]]; then
    GREEN=$(tput setaf 2)
    YELLOW=$(tput setaf 3)
    RESET=$(tput sgr0)
else
    GREEN=""
    YELLOW=""
    RESET=""
fi

success() { echo "${GREEN}$1${RESET}"; }
warn() { echo "${YELLOW}$1${RESET}"; }

# Handle --uninstall
if [[ "${1:-}" == "--uninstall" ]]; then
    rm -f "${BIN_DIR}/${COMMAND_NAME}"
    success "Removed ${COMMAND_NAME}"
    exit 0
fi

# Prerequisite checks (warn only, don't fail)

# Python 3.9+ check
if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)" 2>/dev/null; then
    warn "Warning: Python 3.9+ recommended (current version may be older)"
fi

# Kalico directory check
if [[ ! -d "${HOME}/klipper" ]]; then
    warn "Warning: ~/klipper not found - install Kalico before using kflash"
fi

# Serial access check (dialout group)
if ! groups 2>/dev/null | grep -q dialout; then
    warn "Warning: User not in 'dialout' group - may need: sudo usermod -aG dialout \$USER"
fi

# Installation

# Create bin directory (idempotent)
mkdir -p "${BIN_DIR}"

# Make kflash.py executable
chmod +x "${TARGET}"

# Create symlink (idempotent with -sfn)
ln -sfn "${TARGET}" "${BIN_DIR}/${COMMAND_NAME}"

# PATH check and offer to fix
if [[ ":${PATH}:" != *":${BIN_DIR}:"* ]]; then
    warn "Warning: ${BIN_DIR} is not in your PATH"

    read -p "Add to ~/.bashrc? [y/N] " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'
        if ! grep -qF "${PATH_LINE}" "${HOME}/.bashrc" 2>/dev/null; then
            echo "" >> "${HOME}/.bashrc"
            echo "# Added by kalico-flash installer" >> "${HOME}/.bashrc"
            echo "${PATH_LINE}" >> "${HOME}/.bashrc"
            success "Added to ~/.bashrc"
            warn "Run 'source ~/.bashrc' or open a new terminal"
        else
            success "Already in ~/.bashrc"
        fi
    else
        warn "Skipped. Add manually: export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
fi

# Success message
success "Installed ${COMMAND_NAME} -> ${TARGET}"
echo "Run 'kflash' to start"
