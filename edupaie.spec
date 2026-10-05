# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller - build one-file d'EduPaie (Windows)."""

from pathlib import Path

ROOT = Path(SPECPATH)  # noqa: F821
ICON = ROOT / "resources" / "icons" / "app.ico"

datas = [
    (str(ROOT / "resources"), "resources"),
    (str(ROOT / "src" / "edupaie" / "data" / "migrations"), "edupaie/data/migrations"),
    (str(ROOT / "src" / "edupaie" / "ui" / "theme.qss"), "edupaie/ui"),
]

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=["PySide6.QtSvg"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "pydoc", "pydoc_data"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="EduPaie",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    icon=str(ICON) if ICON.exists() else None,
)