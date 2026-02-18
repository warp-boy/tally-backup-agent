#!/usr/bin/env bash
set -euo pipefail

# Build Windows EXEs and NSIS installer using Wine on macOS/Linux host.
# Usage: ./build_with_wine.sh --python-msi /path/to/python-3.11.6-amd64.exe
# Requires: wine, wget or curl, unzip

WINEPREFIX=${WINEPREFIX:-$HOME/.wine-winbuild}
PY_MSI=""
OUTDIR=${OUTDIR:-$(pwd)/release}
# Ensure PYTHON_EXE has a default to avoid unbound-variable errors under 'set -u'
PYTHON_EXE=${PYTHON_EXE:-C:\\Python311\\python.exe}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --python-msi) PY_MSI="$2"; shift 2 ;;
    --out) OUTDIR="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if ! command -v wine >/dev/null 2>&1; then
  echo "wine not found on PATH. Install Wine and retry." >&2
  exit 1
fi

mkdir -p "$OUTDIR"
echo "Using WINEPREFIX=$WINEPREFIX"
export WINEPREFIX

WORK=$(mktemp -d)
pushd "$WORK"
if [ -z "$PY_MSI" ]; then
  echo "No --python-msi supplied; downloading Python embeddable zip (preferred for Wine)."
  PY_VER="3.11.6"
  EMBED_URL="https://www.python.org/ftp/python/${PY_VER}/python-${PY_VER}-embed-amd64.zip"
  echo "Downloading $EMBED_URL"
  curl -L -o python-embed.zip "$EMBED_URL"
  echo "Extracting embeddable Python to Wine C:\\Python311"
  mkdir -p "$WINEPREFIX/drive_c/Python311"
  unzip -oq python-embed.zip -d "$WINEPREFIX/drive_c/Python311"
  # Adjust python311._pth so embeddable Python can import site and site-packages
  PTH="$WINEPREFIX/drive_c/Python311/python311._pth"
  if [ -f "$PTH" ]; then
    echo "Modifying python311._pth to include Lib and Lib\\site-packages and enable import site"
    cat > "$PTH" <<'PTHEOF'
Lib
.
Lib\site-packages
import site
PTHEOF
  fi
  # The embeddable package may not include pip; fetch get-pip.py and run it
  echo "Downloading get-pip.py"
  curl -L -o get-pip.py https://bootstrap.pypa.io/get-pip.py
  echo "Installing pip into embeddable Python"
  wine "C:\\Python311\\python.exe" get-pip.py || {
    echo "get-pip.py failed; trying with ensurepip" >&2
    wine "C:\\Python311\\python.exe" -m ensurepip --default-pip || true
  }
  PYTHON_EXE="C:\\Python311\\python.exe"

else
  echo "Using supplied Python installer: $PY_MSI"
  echo "Installing Python into Wine C:\\Python311"
  # Try running the installer quietly; many official installers accept /quiet flags
  wine "$PY_MSI" /quiet InstallAllUsers=1 TargetDir="C:\\Python311" PrependPath=0 Include_pip=1 || \
    wine msiexec /i "$PY_MSI" /quiet || true
  PYTHON_EXE="C:\\Python311\\python.exe"
fi

PIP_CMD="wine $PYTHON_EXE -m pip"

echo "Upgrading pip and installing build dependencies inside Wine Python"
wine "$PYTHON_EXE" -m pip install --upgrade pip setuptools wheel || true
wine "$PYTHON_EXE" -m pip install -r "$(pwd)/../../requirements.txt" pyinstaller || true

echo "Running PyInstaller builds"
wine "$PYTHON_EXE" -m PyInstaller --onefile --name TallyBackupAgent --noconsole "$(pwd)/../../agent/service_wrapper.py"
wine "$PYTHON_EXE" -m PyInstaller --onefile --name TallyBackupInstaller --noconsole "$(pwd)/../../tools/installer_gui.py"

echo "Installing NSIS inside Wine"
NSIS_EXE="nsis-setup.exe"
NSIS_URL="https://prdownloads.sourceforge.net/nsis/nsis-3.08.1-setup.exe"
curl -L -o "$NSIS_EXE" "$NSIS_URL"
wine "$NSIS_EXE" /S

MAKENSIS="C:\\Program Files (x86)\\NSIS\\makensis.exe"
echo "Running makensis to produce installer"
wine "$MAKENSIS" "$(pwd)/../../packaging/install.nsi"

echo "Collecting artifacts"
mkdir -p "$OUTDIR"
cp -v dist/TallyBackupAgent.exe "$OUTDIR/" || true
cp -v dist/TallyBackupInstaller.exe "$OUTDIR/" || true
ls -la "$OUTDIR"

popd
rm -rf "$WORK"

echo "Build complete. Artifacts placed in: $OUTDIR"
