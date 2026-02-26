#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image Processor - Versione Ultra-Robusta
Gestisce errori onnxruntime e rembg con fallback
"""

import os
import sys
import warnings
import traceback
import io
import subprocess

warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['ONNXRUNTIME_DISABLE_COREML'] = '1'  # Evita problemi CoreML su Windows

# Fix path PyInstaller
if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
else:
    bundle_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if bundle_dir not in sys.path:
    sys.path.insert(0, bundle_dir)


def debug(msg):
    """Debug su stderr"""
    print(f"[IMGPROC] {msg}", file=sys.stderr, flush=True)


def ensure_model():
    """Scarica modello se mancante"""
    model_dir = os.path.join(os.path.expanduser("~"), ".u2net")
    model_path = os.path.join(model_dir, "u2net.onnx")
    
    if os.path.exists(model_path):
        debug(f"Modello trovato: {model_path}")
        return model_path
    
    debug("Modello non trovato, tentativo download...")
    os.makedirs(model_dir, exist_ok=True)
    
    # URL ufficiale
    url = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx"
    
    try:
        import urllib.request
        debug(f"Download da {url}...")
        urllib.request.urlretrieve(url, model_path)
        debug(f"Download completato: {model_path}")
        return model_path
    except Exception as e:
        debug(f"Download fallito: {e}")
        return None


class BackgroundRemover:
    def __init__(self, model="u2net"):
        debug("Inizializzazione BackgroundRemover...")
        
        self.session = None
        self.fallback_mode = False
        
        # Prova import rembg
        try:
            import rembg
            from rembg.session_factory import new_session
            debug(f"rembg versione: {rembg.__version__ if hasattr(rembg, '__version__') else 'unknown'}")
        except Exception as e:
            debug(f"ERRORE import rembg: {e}")
            raise ImportError(f"rembg non disponibile: {e}")
        
        # Verifica/Scarica modello
        model_path = ensure_model()
        
        # Prova creazione sessione con gestione errori dettagliata
        errors = []
        
        # Tentativo 1: Sessione normale
        try:
            debug("Tentativo 1: new_session standard...")
            self.session = new_session(model)
            debug("Sessione creata con successo!")
            return
        except Exception as e:
            errors.append(f"Standard: {e}")
            debug(f"Fallito tentativo 1: {e}")
        
        # Tentativo 2: Forza CPU
        try:
            debug("Tentativo 2: forzando CPU...")
            os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
            import onnxruntime as ort
            ort.set_default_logger_severity(3)
            self.session = new_session(model)
            debug("Sessione CPU creata!")
            return
        except Exception as e:
            errors.append(f"CPU: {e}")
            debug(f"Fallito tentativo 2: {e}")
        
        # Tentativo 3: Fallback a subprocess
        debug("Tentativo 3: Modalità subprocess fallback...")
        self.fallback_mode = True
        self.model_name = model
        debug("Fallback mode attivato - userà rembg CLI")
    
    def remove_background(self, input_path, output_path, quality=95):
        debug(f"{'='*50}")
        debug(f"Input: {input_path}")
        debug(f"Output: {output_path}")
        
        if not os.path.exists(input_path):
            debug(f"ERRORE: File input non esiste!")
            return False
        
        # Crea cartella output
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        
        # Modalità fallback (subprocess)
        if self.fallback_mode:
            return self._remove_fallback(input_path, output_path)
        
        # Modalità normale
        try:
            from PIL import Image
            from rembg import remove
            
            # Carica
            debug("Apertura immagine...")
            img = Image.open(input_path)
            debug(f"Dimensioni: {img.size}, Mode: {img.mode}")
            
            # Converti se necessario
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Rimuovi sfondo
            debug("Rimozione sfondo...")
            output = remove(img, session=self.session)
            debug(f"Output size: {output.size}")
            
            # Ridimensiona se necessario
            if quality < 100:
                w, h = output.size
                new_w = int(w * quality / 100)
                new_h = int(h * quality / 100)
                output = output.resize((new_w, new_h), Image.Resampling.LANCZOS)
                debug(f"Ridimensionata a: {new_w}x{new_h}")
            
            # Salva
            debug(f"Salvataggio in {output_path}...")
            output.save(output_path, 'PNG')
            
            if os.path.exists(output_path):
                size = os.path.getsize(output_path)
                debug(f"SUCCESSO! File: {size} bytes")
                return True
            else:
                debug("ERRORE: File non creato!")
                return False
                
        except Exception as e:
            debug(f"ERRORE processing: {e}")
            debug(traceback.format_exc())
            
            # Se fallisce, prova fallback
            if not self.fallback_mode:
                debug("Tentativo fallback...")
                return self._remove_fallback(input_path, output_path)
            return False
    
    def _remove_fallback(self, input_path, output_path):
        """Fallback usando rembg come subprocess"""
        debug("USING FALLBACK SUBPROCESS")
        
        try:
            # Trova python exe
            python_exe = sys.executable
            
            # Comando rembg
            cmd = [
                python_exe, "-m", "rembg", "i",
                "-m", self.model_name,
                input_path,
                output_path
            ]
            
            debug(f"CMD: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            debug(f"Return code: {result.returncode}")
            debug(f"Stdout: {result.stdout[:200]}")
            debug(f"Stderr: {result.stderr[:200]}")
            
            if result.returncode == 0 and os.path.exists(output_path):
                debug("Fallback SUCCESS!")
                return True
            else:
                debug(f"Fallback FAILED: {result.stderr}")
                return False
                
        except Exception as e:
            debug(f"Fallback error: {e}")
            return False
