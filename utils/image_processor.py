#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image Processor - Versione Veloce con Cache
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
    """Cache globale per istanza unica"""
    
    _cache = None
    
    def __init__(self, model="u2net"):
        if BackgroundRemover._cache is None:
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
            
        except Exception:
            return False
