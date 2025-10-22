#!/usr/bin/env bash
set -e

APP_NAME="PyCorder"
ENTRY_POINT="main.py"
ICON_PATH="assets/icon-1.png"
PYTHON_VERSION="python3"

echo "=== 🔧 Building $APP_NAME AppImage ==="

# --- Check dependencies ---
for cmd in pyinstaller appimagetool patchelf; do
    if ! command -v $cmd &>/dev/null; then
        echo "❌ Missing: $cmd"
        echo "👉 Install with: sudo apt install -y $cmd"
        exit 1
    fi
done

# --- Clean up old builds ---
rm -rf dist build AppDir "$APP_NAME".AppImage *.spec 2>/dev/null || true

# --- Install Python deps if needed ---
if [ -f "requirements.txt" ]; then
    echo "📦 Installing Python dependencies..."
    pip install --user -r requirements.txt
fi

# --- Build binary with PyInstaller ---
echo "🚀 Running PyInstaller..."
pyinstaller --noconfirm --clean --windowed \
  --name "$APP_NAME" "$ENTRY_POINT" \
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

# --- Create desktop entry ---
cat > AppDir/usr/share/applications/"$APP_NAME".desktop << EOF
[Desktop Entry]
Type=Application
Name=$APP_NAME
Exec=$APP_NAME
Icon=$APP_NAME
Categories=Utility;
Terminal=false
EOF

# Copy .desktop to AppDir root (AppImage requirement)
cp AppDir/usr/share/applications/"$APP_NAME".desktop AppDir/

# --- Copy icon ---
if [ -f "$ICON_PATH" ]; then
    cp "$ICON_PATH" AppDir/usr/share/icons/hicolor/256x256/apps/"$APP_NAME".png
    # Fix: AppImage expects the icon also at root level
    cp "$ICON_PATH" AppDir/"$APP_NAME".png
else
    echo "⚠️  Icon not found at $ICON_PATH"
fi

# --- Build AppImage ---
echo "🧩 Creating AppImage..."
appimagetool AppDir "$APP_NAME"-x86_64.AppImage

# --- Final message ---
echo ""
echo "✅ Done!"
echo "AppImage created: $(pwd)/$APP_NAME-x86_64.AppImage"
echo ""
echo "👉 Run it with:"
echo "   chmod +x $APP_NAME-x86_64.AppImage && ./\$APP_NAME-x86_64.AppImage"
