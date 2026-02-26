#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image Processor - VERSIONE CORRETTA E COMPLETA
Fix: creazione cartella output e attributo model_name
"""

import os
import sys
import warnings
import traceback
import time

warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['ONNXRUNTIME_DISABLE_COREML'] = '1'

# Fix path PyInstaller
if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
else:
    bundle_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if bundle_dir not in sys.path:
    sys.path.insert(0, bundle_dir)


def log(msg):
    """Log su stderr (visibile in console)"""
    print(f"[IMGPROC] {msg}", file=sys.stderr, flush=True)


def ensure_model():
    """Scarica modello u2net se mancante"""
    model_dir = os.path.join(os.path.expanduser("~"), ".u2net")
    model_path = os.path.join(model_dir, "u2net.onnx")
    
    if os.path.exists(model_path):
        size = os.path.getsize(model_path) / 1024 / 1024
        log(f"Modello trovato: {model_path} ({size:.1f} MB)")
        return model_path
    
    log("Modello NON trovato, download in corso...")
    os.makedirs(model_dir, exist_ok=True)
    
    try:
        import urllib.request
        import ssl
        
        # Bypass SSL per evitare errori su Windows/EXE
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        url = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx"
        log(f"Download da: {url}")
        
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
        urllib.request.install_opener(opener)
        
        urllib.request.urlretrieve(url, model_path)
        
        if os.path.exists(model_path):
            size = os.path.getsize(model_path) / 1024 / 1024
            log(f"Download OK: {size:.1f} MB")
            return model_path
            
    except Exception as e:
        log(f"ERRORE download: {e}")
    
    return None


class BackgroundRemover:
    def __init__(self, model="u2net"):
        log(f"Inizializzazione BackgroundRemover (modello: {model})")
        
        # FIX: Salva model_name per fallback
        self.model_name = model
        self.session = None
        self.fallback_mode = False
        
        # Import rembg
        try:
            from rembg.session_factory import new_session
            log("Import rembg OK")
        except Exception as e:
            log(f"ERRORE import rembg: {e}")
            raise
        
        # Trova/Scarica modello
        model_path = ensure_model()
        if not model_path:
            raise FileNotFoundError("Impossibile trovare o scaricare u2net.onnx")
        
        # Imposta path modello
        os.environ['U2NET_HOME'] = os.path.dirname(model_path)
        log(f"U2NET_HOME={os.environ['U2NET_HOME']}")
        
        # Crea sessione ONNX
        try:
            log("Creazione sessione ONNX...")
            self.session = new_session(model)
            log("Sessione creata con SUCCESSO!")
        except Exception as e:
            log(f"ERRORE sessione: {e}")
            log(traceback.format_exc())
            raise
    
    def remove_background(self, input_path, output_path, quality=95):
        log(f"{'='*60}")
        log(f"INPUT:  {input_path}")
        log(f"OUTPUT: {output_path}")
        
        # Verifica input esiste
        if not os.path.exists(input_path):
            log(f"ERRORE: File input non esiste!")
            return False
        
        # ===================================================================
        # FIX CRITICO: Crea cartella output con path assoluto normalizzato
        # ===================================================================
        try:
            # Normalizza path (fix per slash/backslash misti)
            output_path = os.path.normpath(os.path.abspath(output_path))
            out_dir = os.path.dirname(output_path)
            
            log(f"Creazione cartella: {out_dir}")
            
            # Crea cartella se non esiste (exist_ok=True evita race condition)
            if out_dir and not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)
                log(f"Cartella creata: {out_dir}")
            
            # Verifica cartella esista davvero
            if not os.path.exists(out_dir):
                log(f"ERRORE CRITICO: Cartella non creata!")
                return False
                
        except Exception as e:
            log(f"ERRORE creazione cartella: {e}")
            log(traceback.format_exc())
            return False
        
        # Processa immagine
        try:
            from PIL import Image
            from rembg import remove
            
            # Carica
            log("Apertura immagine...")
            img = Image.open(input_path)
            log(f"Dimensioni: {img.size}, Mode: {img.mode}")
            
            # Converti in RGB se necessario
            if img.mode in ('RGBA', 'P', 'LA', 'L'):
                img = img.convert('RGB')
                log("Convertita in RGB")
            
            # Rimuovi sfondo
            log("Rimozione sfondo in corso...")
            start = time.time()
            output = remove(img, session=self.session)
            elapsed = time.time() - start
            log(f"Rimozione completata in {elapsed:.2f}s")
            
            # Ridimensiona se quality < 100
            if quality < 100:
                w, h = output.size
                new_w = int(w * quality / 100)
                new_h = int(h * quality / 100)
                output = output.resize((new_w, new_h), Image.Resampling.LANCZOS)
                log(f"Ridimensionata: {new_w}x{new_h}")
            
            # Assicura RGBA per PNG con trasparenza
            if output.mode != 'RGBA':
                output = output.convert('RGBA')
            
            # ===================================================================
            # SALVATAGGIO CON VERIFICA
            # ===================================================================
            log(f"Salvataggio in: {output_path}")
            output.save(output_path, 'PNG', optimize=True)
            
            # Verifica file creato
            if os.path.exists(output_path):
                size = os.path.getsize(output_path) / 1024
                log(f"SUCCESSO! File salvato: {size:.1f} KB")
                return True
            else:
                log("ERRORE: File non trovato dopo salvataggio!")
                return False
                
        except Exception as e:
            log(f"ERRORE processing: {e}")
            log(traceback.format_exc())
            
            # Tentativo fallback
            log("Tentativo fallback...")
            return self._remove_fallback(input_path, output_path)
    
    def _remove_fallback(self, input_path, output_path):
        """Fallback usando rembg CLI"""
        log("FALLBACK SUBPROCESS")
        
        try:
            python_exe = sys.executable
            
            # FIX: usa self.model_name che ora esiste
            cmd = [
                python_exe, "-m", "rembg", "i",
                "-m", self.model_name,
                "-o", output_path,
                input_path
            ]
            
            log(f"CMD: {' '.join(cmd)}")
            
            import subprocess
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            log(f"Return code: {result.returncode}")
            if result.stderr:
                log(f"Stderr: {result.stderr[:200]}")
            
            if result.returncode == 0 and os.path.exists(output_path):
                log("Fallback SUCCESS!")
                return True
            else:
                log(f"Fallback FAILED")
                return False
                
        except Exception as e:
            log(f"Fallback error: {e}")
            return False
