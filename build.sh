#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# build.sh — Build "Parakeet Transcriber.app"
#
# Prerequisites (install once):
#   brew install python@3.11 ffmpeg
#
# Usage:
#   chmod +x build.sh
#   ./build.sh
#
# Output:
#   dist/Parakeet Transcriber.app   ← double-click to launch
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
PYTHON="/opt/homebrew/bin/python3.11"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="/opt/homebrew/bin/python3.10"
fi
VENV=".venv-build"
APP_NAME="Parakeet Transcriber"

# ── Sanity checks ─────────────────────────────────────────────────────────────
echo ">>> Checking prerequisites…"

if [[ ! -x "$PYTHON" ]]; then
  if command -v python3 &>/dev/null; then
    PYTHON="$(command -v python3)"
  else
    echo "ERROR: No Python 3 found. Install with:  brew install python@3.11"
    exit 1
  fi
fi

PYVER=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "    Python : $PYTHON ($PYVER)"

if ! command -v ffmpeg &>/dev/null; then
  echo ""
  echo "WARNING: ffmpeg not found on PATH."
  echo "The app will still build, but it will show an error at runtime"
  echo "unless ffmpeg is installed.  Install it with:  brew install ffmpeg"
  echo ""
fi

# ── Virtual environment ───────────────────────────────────────────────────────
echo ""
echo ">>> Creating virtual environment in $VENV …"
"$PYTHON" -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"

echo ">>> Upgrading pip…"
pip install --quiet --upgrade pip

echo ">>> Installing dependencies…"
pip install --quiet -r requirements.txt

echo ">>> Installing PyInstaller…"
pip install --quiet "pyinstaller>=6.0"

# ── Build ─────────────────────────────────────────────────────────────────────
echo ""
echo ">>> Running PyInstaller (this takes a few minutes)…"
echo ""

# Clean previous build artefacts
rm -rf build dist

pyinstaller parakeet.spec \
  --noconfirm \
  --log-level WARN

# ── Post-build ────────────────────────────────────────────────────────────────
APP_PATH="dist/${APP_NAME}.app"

if [[ -d "$APP_PATH" ]]; then

  # ── Patch LC_BUILD_VERSION so macOS 26 applies Tahoe window corners ─────────
  MAIN_BIN="${APP_PATH}/Contents/MacOS/${APP_NAME}"
  if [[ -f "$MAIN_BIN" ]] && command -v vtool &>/dev/null; then
    echo ">>> Patching build version for macOS 26 Tahoe window style…"
    vtool -set-build-version macos 11.0 26.0 -replace -output "$MAIN_BIN" "$MAIN_BIN" 2>/dev/null \
      && echo "    Done." \
      || echo "    WARNING: vtool patch failed (non-fatal)."
    echo ">>> Re-signing app bundle (ad-hoc) after patch…"
    codesign --force --deep --sign - "$APP_PATH" 2>/dev/null \
      && echo "    Done." \
      || echo "    WARNING: codesign failed (non-fatal)."
  else
    echo "    NOTE: vtool not found — skipping macOS 26 window corner patch."
  fi

  # ── Create DMG installer ─────────────────────────────────────────────────────
  DMG_PATH="dist/${APP_NAME}.dmg"
  echo ">>> Creating DMG installer…"
  TMP_DMG_DIR=$(mktemp -d)
  cp -r "$APP_PATH" "$TMP_DMG_DIR/"
  ln -s /Applications "$TMP_DMG_DIR/Applications"
  hdiutil create \
    -volname "${APP_NAME}" \
    -srcfolder "$TMP_DMG_DIR" \
    -ov -format UDZO \
    "$DMG_PATH" &>/dev/null \
    && echo "    Done → $DMG_PATH" \
    || echo "    WARNING: DMG creation failed (non-fatal)."
  rm -rf "$TMP_DMG_DIR"

  echo ""
  echo "╔══════════════════════════════════════════════════════════════════════╗"
  echo "║  Build succeeded!                                                    ║"
  echo "║                                                                      ║"
  echo "║  App:  dist/${APP_NAME}.app"
  echo "║  DMG:  dist/${APP_NAME}.dmg  ← share this"
  echo "║                                                                      ║"
  echo "║  To install: open the DMG → drag app to Applications → done.        ║"
  echo "║  First launch downloads the model (~2.3 GB) — be patient once.      ║"
  echo "╚══════════════════════════════════════════════════════════════════════╝"
  echo ""

  # Open the dist folder in Finder for convenience
  open dist/
else
  echo ""
  echo "ERROR: Build failed — $APP_PATH not found."
  echo "Check the PyInstaller output above for details."
  exit 1
fi
