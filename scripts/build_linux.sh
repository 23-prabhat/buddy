#!/usr/bin/env bash
# Build a standalone Linux binary: dist/bro
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
DIST="$ROOT/dist"
mkdir -p "$DIST"

echo "==> bro Linux binary build"
echo "Root: $ROOT"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PY="$ROOT/.venv/bin/python"
  PIP="$ROOT/.venv/bin/pip"
else
  PY="python3"
  PIP="pip3"
fi

echo "==> Ensuring PyInstaller"
"$PY" -m pip install -q "pyinstaller>=6.0"

echo "==> Building onefile binary (bro)"
"$PY" -m PyInstaller \
  --noconfirm \
  --clean \
  --distpath "$DIST" \
  --workpath "$ROOT/build/pyinstaller" \
  "$ROOT/bro.spec"

# Also keep a convenient shell wrapper next to the binary
cat > "$DIST/bro.sh" <<'EOF'
#!/usr/bin/env bash
# Run the packaged bro binary (same directory as this script).
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$DIR/bro"
if [[ ! -x "$BIN" ]]; then
  echo "error: bro binary not found at $BIN" >&2
  echo "Run: ./scripts/build_linux.sh" >&2
  exit 1
fi
# Optional: load .env from cwd or alongside binary
for f in "$PWD/.env" "$DIR/.env"; do
  if [[ -f "$f" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$f"
    set +a
    break
  fi
done
exec "$BIN" "$@"
EOF
chmod +x "$DIST/bro.sh" "$DIST/bro" 2>/dev/null || chmod +x "$DIST/bro.sh"

echo "==> Done"
ls -lh "$DIST/bro" "$DIST/bro.sh" 2>/dev/null || ls -lh "$DIST"
echo
echo "Run:  ./dist/bro.sh"
echo "  or: ./dist/bro"
