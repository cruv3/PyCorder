#!/usr/bin/env bash
set -e

APP_NAME="PyCorder"
ENTRY_POINT="main.py"
ICON_PATH="assets/icon.png"
PYTHON_VERSION="python3"
LOCAL_OUTPUT_DIR="app"
INSTALL_DIR="/opt/$APP_NAME"
DESKTOP_FILE="/usr/share/applications/$APP_NAME.desktop"

echo "=== 🔧 Building and Installing $APP_NAME AppImage ==="

# --- Check dependencies ---
for cmd in pyinstaller appimagetool patchelf; do
    if ! command -v $cmd &>/dev/null; then
        echo "❌ Missing: $cmd"
        echo "👉 Install with: sudo apt install -y $cmd"
        exit 1
    fi
done

# --- Clean up old builds ---
echo "🧹 Cleaning old build artifacts..."
rm -rf dist build AppDir "$APP_NAME".AppImage *.spec 2>/dev/null || true
sudo rm -f "$DESKTOP_FILE" "/usr/local/bin/$APP_NAME" 2>/dev/null || true

# --- Install Python deps if needed ---
if [ -f "requirements.txt" ]; then
    echo "📦 Installing Python dependencies..."
    pip install --user -r requirements.txt
fi

# --- Build binary with PyInstaller (with icon) ---
echo "🚀 Running PyInstaller..."
pyinstaller --noconfirm --clean --windowed \
  --name "$APP_NAME" "$ENTRY_POINT" \
  --icon "$ICON_PATH" \
  --add-data "assets:assets"

# --- Create AppDir structure ---
echo "📁 Creating AppDir structure..."
mkdir -p AppDir/usr/bin
mkdir -p AppDir/usr/share/applications
mkdir -p AppDir/usr/share/icons/hicolor/256x256/apps

# --- Copy app files ---
cp -r dist/"$APP_NAME"/* AppDir/usr/bin/

# --- Create AppRun ---
cat > AppDir/AppRun << EOF
#!/bin/bash
HERE=\$(dirname "\$(readlink -f "\$0")")
export PATH="\$HERE/usr/bin:\$PATH"
exec "\$HERE/usr/bin/$APP_NAME" "\$@"
EOF
chmod +x AppDir/AppRun

# --- Create desktop entry for inside AppImage ---
cat > AppDir/usr/share/applications/"$APP_NAME".desktop << EOF
[Desktop Entry]
Type=Application
Name=$APP_NAME
Exec=$APP_NAME
Icon=$APP_NAME
Categories=Utility;
Terminal=false
EOF
cp AppDir/usr/share/applications/"$APP_NAME".desktop AppDir/

# --- Copy icon ---
if [ -f "$ICON_PATH" ]; then
    cp "$ICON_PATH" AppDir/usr/share/icons/hicolor/256x256/apps/"$APP_NAME".png
    cp "$ICON_PATH" AppDir/"$APP_NAME".png
else
    echo "⚠️  Icon not found at $ICON_PATH"
fi

# --- Build AppImage ---
echo "🧩 Creating AppImage..."
appimagetool AppDir "$APP_NAME"-x86_64.AppImage

# --- Copy AppImage to project folder ---
mkdir -p "$LOCAL_OUTPUT_DIR"
cp "$APP_NAME"-x86_64.AppImage "$LOCAL_OUTPUT_DIR/$APP_NAME.AppImage"

# --- Install AppImage system-wide ---
echo ""
echo "📦 Installing AppImage to $INSTALL_DIR ..."
sudo mkdir -p "$INSTALL_DIR"
sudo cp "$APP_NAME"-x86_64.AppImage "$INSTALL_DIR/$APP_NAME.AppImage"
sudo cp "$ICON_PATH" "$INSTALL_DIR/$APP_NAME.png"

# --- Install Icon ---
if [ -f "$ICON_PATH" ]; then
    sudo mkdir -p "/usr/share/icons/hicolor/256x256/apps"
    sudo cp "$ICON_PATH" "/usr/share/icons/hicolor/256x256/apps/$APP_NAME.png"
fi

# --- Create desktop entry system-wide ---
echo "🖥️  Creating desktop shortcut..."
sudo bash -c "cat > $DESKTOP_FILE" << EOF
[Desktop Entry]
Type=Application
Name=$APP_NAME
Exec=$INSTALL_DIR/$APP_NAME.AppImage
Icon=$INSTALL_DIR/$APP_NAME.png
Categories=Utility;
Terminal=false
StartupNotify=true
EOF

# --- Symlink for CLI access ---
echo "🔗 Creating symlink..."
sudo ln -sf "$INSTALL_DIR/$APP_NAME.AppImage" "/usr/local/bin/$APP_NAME"

# --- Refresh desktop database ---
sudo update-desktop-database &>/dev/null || true

# --- Final cleanup ---
echo "🧹 Cleaning up build directories..."
rm -rf dist build AppDir *.spec 2>/dev/null || true

echo ""
echo "✅ Installation complete!"
echo "AppImage copies:"
echo "  • Local:   $(pwd)/$LOCAL_OUTPUT_DIR/$APP_NAME.AppImage"
echo "  • System:  $INSTALL_DIR/$APP_NAME.AppImage"
echo ""
echo "You can now start $APP_NAME via:"
echo "  • Application menu / search"
echo "  • Command line:  $APP_NAME"
