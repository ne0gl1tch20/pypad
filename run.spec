# -*- mode: python ; coding: utf-8 -*-

from importlib.util import find_spec

hiddenimports = []
if find_spec("PySide6.Qsci") is not None:
    hiddenimports.append("PySide6.Qsci")

# Exclude heavyweight optional/dev stacks that are not required at runtime.
# They can be pulled in transitively by optional AI SDK dependencies.
excludes = [
    "IPython",
    "ipykernel",
    "ipywidgets",
    "jupyter",
    "jupyter_client",
    "jupyter_core",
    "matplotlib",
    "matplotlib_inline",
    "pytest",
    "_pytest",
    "black",
    "setuptools",
    "wheel",
    "pip",
    "mypy",
    "PySide6.QtQuick",
    "PySide6.QtQuickWidgets",
    "PySide6.QtQml",
    "PySide6.QtPositioning",
]

a = Analysis(
    ['src\\run.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('plugins', 'plugins'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    [],
    exclude_binaries=True,
    name='run',
    debug=False,
    version='assets\\version_info.txt',
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='run',
)
