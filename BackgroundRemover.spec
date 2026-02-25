# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None

# Percorso base
base_path = Path('.')

# Analisi dei file
a = Analysis(
    ['main.py'],
    pathex=[str(base_path)],
    binaries=[],
    datas=[
        ('utils', 'utils'),
    ],
    hiddenimports=[
        'rembg',
        'rembg.session_factory',
        'onnxruntime',
        'PIL',
        'PyQt5.sip',
        'numpy',
        'scipy',
        'scipy._lib',
        'scipy._lib.array_api_compat',
        'scipy.sparse',
        'pymatting',
        'pymatting.util',
        'pymatting.util.boxfilter',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'tkinter',
        'unittest',
        'pydoc',
        'email',
        'http',
        'html',
        'xml',
        'ssl',
        'asyncio',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Aggiungi metadati mancanti
import pymatting
import rembg
import scipy

# PyZ (compressione)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Eseguibile
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BackgroundRemover',
    debug=False,
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

# Per macOS crea .app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='BackgroundRemover.app',
        icon=None,
        bundle_identifier='com.backgroundremover.app',
    )
