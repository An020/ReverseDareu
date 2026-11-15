#!/usr/bin/env bash
# DAREU Windows Application Runner under Wine on Arch Linux / Omarchy
# Used as fallback or for vendor firmware flashing

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
APP_DIR="${PROJECT_ROOT}/extracted/app"
WINE_PREFIX="${HOME}/.local/share/dareu-wine"

echo "=== DAREU Wine Compatibility Runner ==="

if ! command -v wine >/dev/null 2>&1; then
    echo "Error: 'wine' is not installed. Install via: sudo pacman -S wine wine-mono"
    exit 1
fi

mkdir -p "${WINE_PREFIX}"

export WINEPREFIX="${WINE_PREFIX}"
export WINEARCH=win32
export WINEDLLOVERRIDES="mscoree=d;mshtml=d"

# Ensure hidraw permissions exist
if [ -c /dev/hidraw0 ] && [ ! -w /dev/hidraw0 ]; then
    echo "Warning: Current user does not have write access to /dev/hidraw*."
    echo "Apply udev rules from ${PROJECT_ROOT}/udev/99-dareu.rules"
fi

echo "Initializing Wine prefix: ${WINE_PREFIX}..."
wineboot -u

echo "Launching DAREU Driver..."
cd "${APP_DIR}"
exec wine "DareuDriver.exe" "$@"
