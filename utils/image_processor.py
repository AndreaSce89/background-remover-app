#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image Processor - Versione Ottimizzata
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
    """Rimozione sfondo con caching sessione"""
    
    def __init__(self, model_name="u2net"):
        self.model_name = model_name
        self._session = None
        
    @property
    def session(self):
        """Lazy loading della sessione"""
        if self._session is None:
            self._session = new_session(self.model_name)
        return self._session
            
    def remove_background(self, input_path, output_path, quality=95):
        """Rimuove sfondo da immagine"""
        try:
            # Verifica file
            if not os.path.exists(input_path):
                return False
            
            # Carica e processa
            img = Image.open(input_path)
            
            # Converti se necessario
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Rimuovi sfondo (usa sessione cached)
            out = remove(img, session=self.session)
            
            # Converti in RGBA
            if out.mode != 'RGBA':
                out = out.convert('RGBA')
            
            # Riduci se necessario
            if quality < 100:
                w, h = out.size
                new_w = int(w * quality / 100)
                new_h = int(h * quality / 100)
                out = out.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # Salva
            out.save(output_path, 'PNG', optimize=True)
            return True
            
        except Exception:
            return False
