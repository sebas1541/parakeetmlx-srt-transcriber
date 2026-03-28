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
    icon=None,
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
