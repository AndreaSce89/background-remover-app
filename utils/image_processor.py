#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image Processor - Versione stabile con fallback
"""

import os
import sys
import warnings
from pathlib import Path

warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# Fix per PyInstaller
if getattr(sys, 'frozen', False):
    # Siamo in un exe
    bundle_dir = sys._MEIPASS
else:
    bundle_dir = os.path.dirname(os.path.abspath(__file__))

# Aggiungi al path se necessario
if bundle_dir not in sys.path:
    sys.path.insert(0, bundle_dir)

from PIL import Image


def get_u2net_path():
    """Trova il modello U2Net in vari percorsi"""
    possible = [
        os.path.join(bundle_dir, "u2net.onnx"),
        os.path.join(bundle_dir, ".u2net", "u2net.onnx"),
        os.path.join(os.path.expanduser("~"), ".u2net", "u2net.onnx"),
        os.path.join(os.path.dirname(bundle_dir), "u2net.onnx"),
    ]
    
    for p in possible:
        if os.path.exists(p):
            return p
    return None


class BackgroundRemover:
    """Rimozione sfondo con U2Net"""
    
    _session = None
    
    def __init__(self, model="u2net"):
        if BackgroundRemover._session is None:
            self._init_session(model)
        self.session = BackgroundRemover._session
    
    def _init_session(self, model):
        """Inizializza la sessione ONNX"""
        try:
            from rembg.session_factory import new_session
            
            # Trova modello locale
            model_path = get_u2net_path()
            
            if model_path:
                # Usa modello locale
                model_dir = os.path.dirname(model_path)
                os.environ['U2NET_HOME'] = model_dir
                
            BackgroundRemover._session = new_session(model)
            
        except Exception as e:
            print(f"Errore inizializzazione sessione: {e}")
            raise
    
    def remove_background(self, input_path, output_path, quality=95):
        """Rimuove sfondo da immagine"""
        try:
            from rembg import remove
            
            # Verifiche
            if not os.path.exists(input_path):
                print(f"File non trovato: {input_path}")
                return False
            
            # Crea cartella output se necessario
            out_dir = os.path.dirname(output_path)
            if out_dir and not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)
            
            # Carica immagine
            img = Image.open(input_path)
            
            # Converti in RGB se necessario
            if img.mode in ('RGBA', 'P', 'LA', 'L'):
                img = img.convert('RGB')
            
            # Rimuovi sfondo
            output = remove(img, session=self.session)
            
            # Assicura RGBA
            if output.mode != 'RGBA':
                output = output.convert('RGBA')
            
            # Riduci se richiesto
            if quality < 100:
                w, h = output.size
                new_w = int(w * quality / 100)
                new_h = int(h * quality / 100)
                output = output.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # Salva
            output.save(output_path, 'PNG', optimize=True)
            return True
            
        except Exception as e:
            print(f"Errore elaborazione: {e}")
            return False
