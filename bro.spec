# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for bro (Linux binary / Windows bro.exe)."""

from __future__ import annotations

import sys
from pathlib import Path

block_cipher = None
ROOT = Path(SPECPATH).resolve()
SRC = ROOT / "src"

hiddenimports = [
    "bro",
    "bro.__main__",
    "bro.apps.desktop.main",
    "bro.apps.desktop.ui.main_window",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
]

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(SRC), str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / ".env.example"), "."),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="bro",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI app (PySide6)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
