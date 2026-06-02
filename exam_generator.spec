# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 规格：710 型船柴油机自动组卷工具。"""

from pathlib import Path

block_cipher = None
root = Path(SPECPATH)

datas = [
    (str(root / "templates" / "template.docx"), "templates"),
    (str(root / "config.release.yaml"), "."),
]

hiddenimports = [
    "jinja2",
    "jinja2.ext",
    "docxtpl",
    "docxcompose",
    "docxcompose.composer",
    "xlrd",
    "xlrd.biffh",
    "yaml",
]

a = Analysis(
    ["main.py"],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
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
    name="组卷工具",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
