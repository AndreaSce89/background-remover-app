#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image Processor - Versione Ultra-Veloce
"""

import os
import warnings
from pathlib import Path

warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from PIL import Image
from rembg import remove
from rembg.session_factory import new_session


class BackgroundRemover:
    """Versione con sessione cached per velocità"""
    
    _session_cache = None  # Cache globale
    
    def __init__(self, model_name="u2net"):
        self.model_name = model_name
        
        # Usa cache se disponibile
        if BackgroundRemover._session_cache is None:
            BackgroundRemover._session_cache = new_session(model_name)
        
        self.session = BackgroundRemover._session_cache
            
    def remove_background(self, input_path, output_path, quality=95):
        try:
            if not os.path.exists(input_path):
                return False
            
            # Carica
            img = Image.open(input_path)
            
            # Converti
            if img.mode in ('RGBA', 'P', 'LA', 'L'):
                img = img.convert('RGB')
            
            # Rimuovi (usa sessione cached)
            out = remove(img, session=self.session)
            
            # RGBA
            if out.mode != 'RGBA':
                out = out.convert('RGBA')
            
            # Resize se necessario
            if quality < 100:
                w, h = out.size
                out = out.resize((int(w*quality/100), int(h*quality/100)), Image.Resampling.LANCZOS)
            
            # Salva
            out.save(output_path, 'PNG', optimize=True)
            return True
            
        except Exception:
            return False
