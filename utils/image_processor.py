#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image Processor - Versione stabile con debug completo
"""

import os
import sys
import warnings
import traceback
from pathlib import Path

warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from PIL import Image
from rembg import remove
from rembg.session_factory import new_session


def get_model_path():
    """Trova il percorso del modello u2net"""
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent.parent
    
    possible_paths = [
        base_path / "u2net.onnx",
        base_path / ".u2net" / "u2net.onnx",
        Path.home() / ".u2net" / "u2net.onnx",
    ]
    
    for p in possible_paths:
        if p.exists():
            return str(p)
    
    return None


class BackgroundRemover:
    """Versione con error handling completo"""
    
    _cache = None
    
    def __init__(self, model="u2net"):
        if BackgroundRemover._cache is None:
            model_path = get_model_path()
            
            if model_path:
                os.environ['U2NET_HOME'] = str(Path(model_path).parent)
            
            BackgroundRemover._cache = new_session(model)
        
        self.session = BackgroundRemover._cache
            
    def remove_background(self, input_path, output_path, quality=95):
        try:
            # Verifica input
            if not os.path.exists(input_path):
                print(f"ERRORE: File non trovato: {input_path}")
                return False
            
            # Verifica cartella output
            out_dir = os.path.dirname(output_path)
            if out_dir and not os.path.exists(out_dir):
                try:
                    os.makedirs(out_dir, exist_ok=True)
                    print(f"Creata cartella: {out_dir}")
                except Exception as e:
                    print(f"ERRORE: Impossibile creare cartella {out_dir}: {e}")
                    return False
            
            # Carica immagine
            try:
                img = Image.open(input_path)
                print(f"Immagine caricata: {img.size}, mode: {img.mode}")
            except Exception as e:
                print(f"ERRORE: Impossibile aprire immagine: {e}")
                return False
            
            # Converti
            if img.mode in ('RGBA', 'P', 'LA', 'L'):
                img = img.convert('RGB')
                print(f"Convertita in RGB")
            
            # Rimuovi sfondo
            try:
                print("Avvio rimozione sfondo...")
                out = remove(img, session=self.session)
                print("Sfondo rimosso")
            except Exception as e:
                print(f"ERRORE: Rimozione sfondo fallita: {e}")
                traceback.print_exc()
                return False
            
            # Converti in RGBA
            if out.mode != 'RGBA':
                out = out.convert('RGBA')
                print("Convertita in RGBA")
            
            # Riduci qualità
            if quality < 100:
                w, h = out.size
                out = out.resize((int(w*quality/100), int(h*quality/100)), Image.Resampling.LANCZOS)
                print(f"Ridimensionata a {quality}%")
            
            # Salva
            try:
                print(f"Salvataggio in: {output_path}")
                out.save(output_path, 'PNG', optimize=True)
                print(f"OK: Salvato con successo")
                return True
            except Exception as e:
                print(f"ERRORE: Salvataggio fallito: {e}")
                traceback.print_exc()
                return False
            
        except Exception as e:
            print(f"ERRORE GENERICO: {e}")
            traceback.print_exc()
            return False
