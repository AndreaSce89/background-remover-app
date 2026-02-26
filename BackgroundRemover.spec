# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None

base_path = Path('.')

a = Analysis(
    ['main.py'],
    pathex=[str(base_path)],
    binaries=[],
    datas=[
        ('utils', 'utils'),
        ('u2net.onnx', '.'),
    ],
    hiddenimports=[
        'PyQt5',
        'PyQt5.QtWidgets',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.sip',
        'rembg',
        'rembg.session_factory',
        'rembg.bg',
        'onnxruntime',
        'PIL',
        'PIL.Image',
        'PIL.ImageOps',
        'numpy',
        'scipy',
        'scipy._lib',
        'pymatting',
        'pymatting.util',
        'skimage',
        'imageio',
        'tqdm',
    ],
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
