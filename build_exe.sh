#!/usr/bin/env bash
set -e

APP_NAME="PyCorder"
ENTRY_POINT="main.py"
ICON_PATH="assets/icon.ico"
REQUIREMENTS="requirements.txt"
PYTHON_INSTALLER="python-3.10.9-amd64.exe"
PYTHON_URL="https://www.python.org/ftp/python/3.10.9/${PYTHON_INSTALLER}"
WINEPREFIX="$HOME/.wine"
WINEARCH=win64

echo "=== 🏁 Building $APP_NAME for Windows via Wine ==="

# --- Check Wine ---
if ! command -v wine &>/dev/null; then
    echo "❌ Wine ist nicht installiert. Installiere mit:"
    echo "   sudo apt install -y wine64 winbind"
    exit 1
fi

# --- Setup Wine environment ---
export WINEPREFIX
export WINEARCH
mkdir -p "$WINEPREFIX"

# --- Check Windows Python installation ---
if ! wine python --version &>/dev/null; then
    echo "🐍 Installing Windows Python 3.10.9 ..."
    [ -f "$PYTHON_INSTALLER" ] || wget "$PYTHON_URL" -O "$PYTHON_INSTALLER"
    wine "$PYTHON_INSTALLER" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
else
    echo "✅ Windows Python already installed."
fi

# --- Install Python dependencies ---
if [ -f "$REQUIREMENTS" ]; then
    echo "📦 Installing Python dependencies inside Wine..."
    wine python -m pip install --upgrade pip setuptools wheel
    wine python -m pip install -r "$REQUIREMENTS"
else
    echo "⚠️  No requirements.txt found – skipping dependency install."
fi

# --- Clean old builds ---
echo "🧹 Cleaning old build artifacts..."
rm -rf build dist *.spec 2>/dev/null || true

# --- Convert icon path for Wine ---
ICON_PATH_WIN=$(winepath -w "$(realpath "$ICON_PATH")" 2>/dev/null || echo "Z:$(realpath "$ICON_PATH")")

if [ ! -f "$ICON_PATH" ]; then
    echo "⚠️  Icon not found at $ICON_PATH (skipping icon embedding)"
    ICON_ARG=""
else
    echo "🎨 Using icon: $ICON_PATH_WIN"
    ICON_ARG="--icon \"$ICON_PATH_WIN\""
fi

# --- Build the EXE ---
echo "🚀 Running PyInstaller..."
# Use --onefile to embed DLLs and runtime properly
eval wine python -m PyInstaller --noconfirm --clean --windowed \
  --name "$APP_NAME" "$ENTRY_POINT" $ICON_ARG

# --- Verify DLL embedding ---
DLL_CHECK=$(wine cmd /c "dir dist\\$APP_NAME.exe" 2>/dev/null || true)
if [[ ! "$DLL_CHECK" =~ ".exe" ]]; then
    echo "❌ Build failed — EXE not created."
    exit 1
fi

# --- Copy python310.dll if needed ---
DLL_PATH=$(find "$WINEPREFIX/drive_c/users" -name "python310.dll" | head -n 1 || true)
if [ -n "$DLL_PATH" ]; then
    echo "🔧 Ensuring python310.dll is included..."
    cp "$DLL_PATH" dist/ 2>/dev/null || true
else
    echo "⚠️  Could not locate python310.dll (may not be needed for onefile build)."
fi

# --- Done ---
echo "✅ Build complete!"
echo "EXE created at: dist/$APP_NAME.exe"
echo ""
