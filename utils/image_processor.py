#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image Processor - Versione con verifica completa
"""

import os
import sys
import warnings
from pathlib import Path

warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from PIL import Image


def find_model():
    """Trova modello u2net in vari percorsi"""
    if getattr(sys, 'frozen', False):
        # PyInstaller
        base = Path(sys._MEIPASS)
    else:
        # Normale
        base = Path(__file__).parent.parent
    
    paths = [
        base / "u2net.onnx",
        base / ".u2net" / "u2net.onnx",
        Path.home() / ".u2net" / "u2net.onnx",
        Path(os.getcwd()) / "u2net.onnx",
    ]
    
    for p in paths:
        if p.exists():
            print(f"Modello trovato: {p}")
            return str(p)
    
    print("Modello NON trovato, verrà scaricato automaticamente")
    return None


class BackgroundRemover:
    def __init__(self, model="u2net"):
        from rembg.session_factory import new_session
        
        model_path = find_model()
        
        if model_path:
            # Usa modello locale
            model_dir = os.path.dirname(model_path)
            os.environ['U2NET_HOME'] = model_dir
            print(f"U2NET_HOME = {model_dir}")
        
        print("Creazione sessione...")
        self.session = new_session(model)
        print("Sessione creata!")
    
    def remove_background(self, input_path, output_path, quality=95):
        from rembg import remove
        
        try:
            # Verifica input
            if not os.path.exists(input_path):
                print(f"ERRORE: Input non esiste: {input_path}")
                return False
            
            print(f"Elaborazione: {input_path}")
            
            # Crea cartella output
            out_dir = os.path.dirname(output_path)
            if out_dir and not os.path.exists(out_dir):
                try:
                    os.makedirs(out_dir, exist_ok=True)
                    print(f"Creata cartella: {out_dir}")
                except Exception as e:
                    print(f"ERRORE creazione cartella: {e}")
                    return False
            
            # Carica immagine
            try:
                img = Image.open(input_path)
                print(f"Immagine: {img.size}, mode: {img.mode}")
            except Exception as e:
                print(f"ERRORE apertura immagine: {e}")
                return False
            
            # Converti
            if img.mode in ('RGBA', 'P', 'LA', 'L'):
                img = img.convert('RGB')
                print("Convertita in RGB")
            
            # Rimuovi sfondo
            try:
                print("Rimozione sfondo...")
                out = remove(img, session=self.session)
                print("Sfondo rimosso")
            except Exception as e:
                print(f"ERRORE rimozione sfondo: {e}")
                import traceback
                traceback.print_exc()
                return False
            
            # Converti in RGBA
            if out.mode != 'RGBA':
                out = out.convert('RGBA')
                print("Convertita in RGBA")
            
            # Riduci qualità
            if quality < 100:
                w, h = out.size
                new_w = int(w * quality / 100)
                new_h = int(h * quality / 100)
                out = out.resize((new_w, new_h), Image.Resampling.LANCZOS)
                print(f"Ridimensionata a {new_w}x{new_h}")
            
            # Salva
            try:
                print(f"Salvataggio in: {output_path}")
                out.save(output_path, 'PNG', optimize=True)
                
                # Verifica salvataggio
                if os.path.exists(output_path):
                    size = os.path.getsize(output_path)
                    print(f"Salvato! Dimensione: {size} bytes")
                    return True
                else:
                    print("ERRORE: File non creato dopo save()")
                    return False
                    
            except Exception as e:
                print(f"ERRORE salvataggio: {e}")
                import traceback
                traceback.print_exc()
                return False
            
        except Exception as e:
            print(f"ERRORE GENERALE: {e}")
            import traceback
            traceback.print_exc()
            return False
