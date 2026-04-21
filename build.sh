#!/usr/bin/env bash
# ============================================================
#  Infac P4 — Windows EXE Build Script
#  Run this on Windows via Git Bash or WSL.
#  PyInstaller must execute on Windows to produce a .exe.
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo " Infac P4 - Windows Build"
echo "============================================================"
echo ""

# ── Detect Python ────────────────────────────────────────────
PYTHON=""
for cmd in python python3; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON="$cmd"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "[ERROR] Python not found. Install Python 3.10+ and add it to PATH."
    exit 1
fi

echo "[INFO] Using Python: $($PYTHON --version)"

# ── Create venv if missing ───────────────────────────────────
if [ ! -f "venv/Scripts/python.exe" ] && [ ! -f "venv/bin/python" ]; then
    echo "[INFO] Creating virtual environment..."
    $PYTHON -m venv venv
fi

# ── Activate venv (Git Bash on Windows vs Linux/macOS) ───────
if [ -f "venv/Scripts/activate" ]; then
    # shellcheck disable=SC1091
    source venv/Scripts/activate
elif [ -f "venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source venv/bin/activate
else
    echo "[ERROR] Could not find venv activation script."
    exit 1
fi

echo "[INFO] Virtual environment activated."

# ── Upgrade pip silently ─────────────────────────────────────
python -m pip install --upgrade pip --quiet

# ── Install / verify dependencies ───────────────────────────
echo "[INFO] Installing dependencies..."
pip install -r requirements.txt --quiet

# ── Install PyInstaller if missing ───────────────────────────
if ! command -v pyinstaller &>/dev/null; then
    echo "[INFO] Installing PyInstaller..."
    pip install pyinstaller --quiet
fi

echo "[INFO] PyInstaller: $(pyinstaller --version)"

# ── Clean previous build artefacts ──────────────────────────
echo "[INFO] Cleaning previous build..."
rm -rf build/InfacP4
rm -f  dist/InfacP4.exe

# ── Run PyInstaller ──────────────────────────────────────────
echo ""
echo "[INFO] Building InfacP4.exe — this may take a few minutes..."
echo ""

pyinstaller main.spec --clean --noconfirm

# ── Verify output ────────────────────────────────────────────
if [ -f "dist/InfacP4.exe" ]; then
    SIZE=$(du -sh dist/InfacP4.exe | cut -f1)
    echo ""
    echo "============================================================"
    echo " Build complete!"
    echo " Output : dist/InfacP4.exe  ($SIZE)"
    echo "============================================================"
    echo ""
    echo "NOTE: First launch on Windows may take 5-15 seconds while"
    echo "      the app extracts itself to a temporary directory."
else
    echo ""
    echo "[ERROR] Build failed — dist/InfacP4.exe not found."
    echo "        Check the PyInstaller output above for details."
    exit 1
fi
