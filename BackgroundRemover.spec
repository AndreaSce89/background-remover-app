# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path
import glob

block_cipher = None

# Determina cartella base
base_path = Path('.')

# Raccogli tutti i binari necessari
binaries = []

# Aggiungi DLL di sistema cruciali per Windows
if sys.platform == 'win32':
    # Trova onnxruntime e sue dipendenze
    try:
        import onnxruntime
        ort_path = Path(onnxruntime.__file__).parent
        
        # Aggiungi tutte le DLL di onnxruntime
        for dll in ort_path.glob('*.dll'):
            binaries.append((str(dll), '.'))
            print(f"Trovata DLL: {dll.name}")
        
        # Aggiungi anche providers
        providers_path = ort_path / 'onnxruntime_providers_shared.dll'
        if providers_path.exists():
            binaries.append((str(providers_path), '.'))
            
    except Exception as e:
        print(f"Warning: onnxruntime non trovato: {e}")

# Aggiungi pymatting se presente
try:
    import pymatting
    pym_path = Path(pymatting.__file__).parent
    # pymatting ha file .c o .pyx compilati
    for ext in ['*.pyd', '*.so', '*.dll']:
        for f in pym_path.rglob(ext):
            rel_path = f.relative_to(pym_path)
            binaries.append((str(f), str(rel_path.parent)))
except:
    pass

# Dati da includere
datas = [
    ('utils', 'utils'),
]

# Cerca modello u2net nelle varie locazioni
model_found = False
for model_path in [
    base_path / 'u2net.onnx',
    Path.home() / '.u2net' / 'u2net.onnx',
]:
    if model_path.exists():
        datas.append((str(model_path), '.' if model_path.parent == base_path else '.u2net'))
        print(f"Incluso modello: {model_path}")
        model_found = True
        break

if not model_found:
    print("WARNING: Modello u2net.onnx non trovato! Verrà scaricato al primo avvio.")

# Hidden imports massivi
hiddenimports = [
    # PyQt5
    'PyQt5',
    'PyQt5.sip',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    
    # rembg
    'rembg',
    'rembg.session_factory',
    'rembg.bg',
    'rembg.cli',
    
    # ONNX Runtime - TUTTE le varianti
    'onnxruntime',
    'onnxruntime.capi',
    'onnxruntime.capi.onnxruntime_pybind11_state',
    'onnxruntime.capi._pybind_state',
    'onnxruntime.capi.onnxruntime_validation',
    
    # Providers ONNX
    'onnxruntime.providers',
    'onnxruntime.providers.cpu',
    'onnxruntime.providers.cuda',
    'onnxruntime.providers.coreml',
    'onnxruntime.providers.directml',
    'onnxruntime.providers.tvm',
    'onnxruntime.providers.nnapi',
    
    # PIL
    'PIL',
    'PIL.Image',
    'PIL.ImageOps',
    'PIL.ImageFilter',
    'PIL.ImageEnhance',
    'PIL.PngImagePlugin',
    'PL.JpegImagePlugin',
    
    # NumPy & SciPy
    'numpy',
    'numpy.core._dtype_ctypes',
    'numpy.core._multiarray_umath',
    'scipy',
    'scipy._lib',
    'scipy._lib.messagestream',
    'scipy.ndimage',
    'scipy.sparse',
    'scipy.sparse.csgraph',
    'scipy.sparse.linalg',
    
    # Image processing
    'pymatting',
    'pymatting.util',
    'pymatting.util.boxfilter',
    'pymatting.foreground',
    'pymatting.alpha',
    'skimage',
    'skimage.filters',
    'skimage.morphology',
    'skimage.measure',
    'skimage.util',
    'imageio',
    'imageio.plugins',
    'imageio.plugins.pillow',
    
    # Altri
    'tqdm',
    'urllib.request',
    'pathlib',
    'traceback',
    'io',
    'subprocess',
]

# Escludi cose inutili che ingrandiscono l'EXE
excludes = [
    'matplotlib',
    'tkinter',
    'PySide2',
    'PySide6',
    'shiboken2',
    'shiboken6',
    'pandas',
    'notebook',
    'pytest',
    'scipy.spatial.cKDTree',  # Se non usato
]

a = Analysis(
    ['main.py'],
    pathex=[str(base_path)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
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
    debug=False,  # Cambia a True per debug PyInstaller
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # IMPORTANTE: False per evitare corruzione DLL
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # IMPORTANTE: True per vedere errori!
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
