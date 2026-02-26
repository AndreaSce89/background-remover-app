# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None

base_path = Path('.')

# Trova tutti i binari necessari
binaries = []

# Aggiungi onnxruntime se possibile
try:
    import onnxruntime
    onnx_path = Path(onnxruntime.__file__).parent
    binaries.append((str(onnx_path / 'onnxruntime_providers_shared.dll'), '.'))
except:
    pass

a = Analysis(
    ['main.py'],
    pathex=[str(base_path)],
    binaries=binaries,
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
        'onnxruntime.capi',
        'onnxruntime.capi.onnxruntime_pybind11_state',
        'PIL',
        'PIL.Image',
        'PIL.ImageOps',
        'numpy',
        'numpy.core._dtype_ctypes',
        'scipy',
        'scipy._lib',
        'scipy._lib.messagestream',
        'pymatting',
        'pymatting.util',
        'pymatting.util.boxfilter',
        'skimage',
        'imageio',
        'imageio.plugins',
        'imageio.plugins.pillow',
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
    upx=False,  # DISABILITATO per evitare problemi
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # CAMBIATO: True per vedere errori!
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
