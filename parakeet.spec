# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Parakeet Transcriber

import os
import glob
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# ── Locate site-packages ──────────────────────────────────────────────────────
import site, sysconfig
_sp = next(
    (p for p in site.getsitepackages() if "site-packages" in p and os.path.isdir(p)),
    sysconfig.get_path("purelib"),
)

# ── Collect key packages ──────────────────────────────────────────────────────
_pkgs = [
    "mlx",
    "mlx_whisper",
    "parakeet_mlx",
    "huggingface_hub",
    "fastapi",
    "uvicorn",
    "starlette",
    "anyio",
    "httpx",
    "multipart",
    "soundfile",
    "webview",
    "pyobjc",
]

all_datas    = []
all_binaries = []
all_hidden   = []

# ── Bundle ffmpeg so end users need nothing installed ─────────────────────────
import shutil as _shutil
_ffmpeg_src = (
    _shutil.which("ffmpeg") or
    next((p for p in ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"]
          if os.path.isfile(p)), None)
)
if _ffmpeg_src:
    all_binaries.append((_ffmpeg_src, "."))
    print(f"[spec] Bundling ffmpeg from {_ffmpeg_src}")
else:
    print("[spec] WARNING: ffmpeg not found — it will not be bundled")

for pkg in _pkgs:
    try:
        d, b, h = collect_all(pkg)
        all_datas    += d
        all_binaries += b
        all_hidden   += h
    except Exception as e:
        print(f"[spec] WARNING: could not collect {pkg}: {e}")

# ── Sweep for stray version.txt / METADATA files ──────────────────────────────
if _sp:
    for pattern in ["*/version.txt", "*/VERSION", "*/METADATA"]:
        for filepath in glob.glob(os.path.join(_sp, pattern)):
            dest = os.path.relpath(os.path.dirname(filepath), _sp)
            all_datas.append((filepath, dest))

# ── Extra hidden imports ──────────────────────────────────────────────────────
all_hidden += [
    "mlx.core", "mlx.nn", "mlx.optimizers", "mlx.utils",
    "mlx_whisper",
    "parakeet_mlx",
    "soundfile",
    "uvicorn.logging", "uvicorn.loops", "uvicorn.loops.auto",
    "uvicorn.protocols", "uvicorn.protocols.http", "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets", "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan", "uvicorn.lifespan.on",
    "multipart", "multipart.multipart",
    "email.mime.text", "email.mime.multipart", "email.mime.base",
    "importlib.metadata", "pkg_resources",
]

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "cv2", "torch", "tensorflow", "gradio"],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="Parakeet Transcriber",
    debug=False, strip=False, upx=False,
    console=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=False,
    name="Parakeet Transcriber",
)

app = BUNDLE(
    coll,
    name="Parakeet Transcriber.app",
    icon="icon.icns",
    bundle_identifier="com.parakeet.transcriber",
    info_plist={
        "CFBundleName": "Parakeet Transcriber",
        "CFBundleDisplayName": "Parakeet Transcriber",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1",
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,
        "NSAppTransportSecurity": {"NSAllowsArbitraryLoads": True},
    },
)
