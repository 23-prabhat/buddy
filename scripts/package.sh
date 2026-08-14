#!/usr/bin/env bash
# Packaging helpers for Linux (and notes for Windows).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
DIST="$ROOT/dist"
mkdir -p "$DIST"

echo "==> bro package helper"
echo "Root: $ROOT"

# Source distribution via hatch/pip if available
if command -v uv >/dev/null 2>&1; then
  echo "==> Building wheel/sdist with uv"
  uv build --out-dir "$DIST" 2>/dev/null || python -m build -o "$DIST" 2>/dev/null || {
    echo "wheel build optional — creating source tarball"
    tar --exclude='.venv' --exclude='.git' --exclude='dist' --exclude='__pycache__' \
      --exclude='.pytest_cache' --exclude='.env' \
      -czf "$DIST/bro-src.tar.gz" -C "$ROOT" .
  }
else
  tar --exclude='.venv' --exclude='.git' --exclude='dist' --exclude='__pycache__' \
    --exclude='.pytest_cache' --exclude='.env' \
    -czf "$DIST/bro-src.tar.gz" -C "$ROOT" .
fi

# AppImage-oriented layout note
cat > "$DIST/PACKAGING.md" <<'EOF'
# Packaging

## Linux source tarball
`bro-src.tar.gz` — extract, create venv, `pip install -r requirements.txt`, run `python -m bro`.

## Debian / RPM (manual)
1. Install system deps: python3, tesseract, portaudio (optional), espeak-ng (optional TTS)
2. Install Python deps into venv
3. Desktop entry:

```
[Desktop Entry]
Name=AI Assistant
Exec=/opt/bro/.venv/bin/python /opt/bro/main.py
Type=Application
Terminal=false
Categories=Utility;
```

## AppImage
Use `python-appimage` or `pyinstaller` + `appimagetool` when ready for distribution:

```
pyinstaller -F -w -n bro main.py
# then wrap with appimagetool
```

## Windows installer
```
pip install pyinstaller
pyinstaller -F -w -n bro main.py
# wrap exe with Inno Setup or NSIS
```

EOF

echo "==> Done. Artifacts in $DIST"
ls -la "$DIST"
