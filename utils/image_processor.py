#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image Processor - Versione Debug Completo
"""

import os
import sys
import warnings
import traceback

warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# Fix per PyInstaller
if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
else:
    bundle_dir = os.path.dirname(os.path.abspath(__file__))

# Aggiungi al path
if bundle_dir not in sys.path:
    sys.path.insert(0, bundle_dir)

from PIL import Image


def debug_print(msg):
    """Stampa debug su stderr (visibile in console)"""
    print(f"[DEBUG] {msg}", file=sys.stderr, flush=True)


def find_model():
    """Trova modello u2net"""
    debug_print(f"Cerco modello in: {bundle_dir}")
    
    paths = [
        os.path.join(bundle_dir, "u2net.onnx"),
        os.path.join(bundle_dir, ".u2net", "u2net.onnx"),
        os.path.join(os.path.expanduser("~"), ".u2net", "u2net.onnx"),
    ]
    
    for p in paths:
        debug_print(f"  Controllo: {p} -> {'ESISTE' if os.path.exists(p) else 'NO'}")
        if os.path.exists(p):
            return p
    
    return None


class BackgroundRemover:
    def __init__(self, model="u2net"):
        debug_print("Inizializzazione BackgroundRemover...")
        
        # Import qui per catturare errori
        try:
            from rembg.session_factory import new_session
            debug_print("Import new_session OK")
        except Exception as e:
            debug_print(f"ERRORE IMPORT: {e}")
            raise
        
        model_path = find_model()
        
        if model_path:
            model_dir = os.path.dirname(model_path)
            os.environ['U2NET_HOME'] = model_dir
            debug_print(f"U2NET_HOME = {model_dir}")
        else:
            debug_print("Modello non trovato, verrà scaricato")
        
        try:
            debug_print("Creazione sessione...")
            self.session = new_session(model)
            debug_print("Sessione creata con successo!")
        except Exception as e:
            debug_print(f"ERRORE SESSIONE: {e}")
            traceback.print_exc()
            raise
    
    def remove_background(self, input_path, output_path, quality=95):
        try:
            from rembg import remove
        except Exception as e:
            debug_print(f"ERRORE IMPORT remove: {e}")
            return False
        
        debug_print(f"=" * 50)
        debug_print(f"Input:  {input_path}")
        debug_print(f"Output: {output_path}")
        debug_print(f"Quality: {quality}")
        
        # Verifica input
        if not os.path.exists(input_path):
            debug_print(f"ERRORE: Input non esiste!")
            return False
        
        # Crea cartella
        out_dir = os.path.dirname(output_path)
        if out_dir and not os.path.exists(out_dir):
            try:
                os.makedirs(out_dir, exist_ok=True)
                debug_print(f"Creata cartella: {out_dir}")
            except Exception as e:
                debug_print(f"ERRORE cartella: {e}")
                return False
        
        # Carica immagine
        try:
            img = Image.open(input_path)
            debug_print(f"Immagine caricata: {img.size}, mode={img.mode}")
        except Exception as e:
            debug_print(f"ERRORE apertura: {e}")
            return False
        
        # Converti
        if img.mode in ('RGBA', 'P', 'LA', 'L'):
            img = img.convert('RGB')
            debug_print("Convertita in RGB")
        
        # RIMUOVI SFONDO - QUI IL PROBLEMA
        try:
            debug_print("Chiamata remove()...")
            out = remove(img, session=self.session)
            debug_print(f"remove() completata, output size: {out.size}")
        except Exception as e:
            debug_print(f"ERRORE remove(): {e}")
            debug_print("Traceback:")
            traceback.print_exc()
            return False
        
        # Converti RGBA
        if out.mode != 'RGBA':
            out = out.convert('RGBA')
            debug_print("Convertita in RGBA")
        
        # Resize
        if quality < 100:
            w, h = out.size
            new_w = int(w * quality / 100)
            new_h = int(h * quality / 100)
            out = out.resize((new_w, new_h), Image.Resampling.LANCZOS)
            debug_print(f"Ridimensionata a {new_w}x{new_h}")
        
        # Salva
        try:
            debug_print(f"Salvataggio in {output_path}...")
            out.save(output_path, 'PNG', optimize=True)
            
            if os.path.exists(output_path):
                size = os.path.getsize(output_path)
                debug_print(f"SUCCESSO! File creato: {size} bytes")
                return True
            else:
                debug_print("ERRORE: File non esiste dopo save()")
                return False
                
        except Exception as e:
            debug_print(f"ERRORE salvataggio: {e}")
            traceback.print_exc()
            return False
