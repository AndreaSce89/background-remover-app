#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image Processor - Versione con modello locale
"""

import os
import sys
import warnings
from pathlib import Path

warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from PIL import Image
from rembg import remove
from rembg.session_factory import new_session


def get_model_path():
    """Trova il percorso del modello u2net"""
    # Se eseguito da PyInstaller
    if getattr(sys, 'frozen', False):
        # Siamo in un exe
        base_path = Path(sys._MEIPASS)
    else:
        # Siamo in sviluppo
        base_path = Path(__file__).parent.parent
    
    # Cerca il modello in vari posti
    possible_paths = [
        base_path / "u2net.onnx",
        base_path / ".u2net" / "u2net.onnx",
        Path.home() / ".u2net" / "u2net.onnx",
    ]
    
    for p in possible_paths:
        if p.exists():
            return str(p)
    
    # Se non trovato, ritorna None (verrà scaricato automaticamente)
    return None


class BackgroundRemover:
    """Versione con supporto modello locale"""
    
    _cache = None
    
    def __init__(self, model="u2net"):
        if BackgroundRemover._cache is None:
            model_path = get_model_path()
            
            if model_path and os.path.exists(model_path):
                # Usa modello locale
                os.environ['U2NET_HOME'] = str(Path(model_path).parent)
            
            BackgroundRemover._cache = new_session(model)
        
        self.session = BackgroundRemover._cache
            
    def remove_background(self, input_path, output_path, quality=95):
        try:
            if not os.path.exists(input_path):
                return False
            
            img = Image.open(input_path)
            
            if img.mode in ('RGBA', 'P', 'LA', 'L'):
                img = img.convert('RGB')
            
            out = remove(img, session=self.session)
            
            if out.mode != 'RGBA':
                out = out.convert('RGBA')
            
            if quality < 100:
                w, h = out.size
                out = out.resize((int(w*quality/100), int(h*quality/100)), Image.Resampling.LANCZOS)
            
            out.save(output_path, 'PNG', optimize=True)
            return True
            
        except Exception as e:
            print(f"Errore: {e}")
            return False
