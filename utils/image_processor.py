#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image Processor - VERSIONE DEFINITIVA
Fix: path Windows corretti, validazione output, retry
"""

import os
import sys
import warnings
import traceback
import time
from pathlib import Path

warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# Fix path
if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
else:
    bundle_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if bundle_dir not in sys.path:
    sys.path.insert(0, bundle_dir)

try:
    from logger import get_logger
    logger = get_logger()
except:
    class FakeLogger:
        def info(self, m): print(f"[INFO] {m}", file=sys.stderr)
        def debug(self, m): print(f"[DEBUG] {m}", file=sys.stderr)
        def error(self, m, e=None): print(f"[ERROR] {m}", file=sys.stderr)
        def success(self, m): print(f"[OK] {m}", file=sys.stderr)
    logger = FakeLogger()


def ensure_model():
    """Scarica modello con retry"""
    model_dir = Path.home() / ".u2net"
    model_path = model_dir / "u2net.onnx"
    
    if model_path.exists() and model_path.stat().st_size > 160000000:
        return str(model_path)
    
    os.makedirs(model_dir, exist_ok=True)
    
    try:
        import urllib.request
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        urllib.request.urlretrieve(
            "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx",
            model_path
        )
        return str(model_path)
    except Exception as e:
        logger.error("Model download failed", e)
        raise


class BackgroundRemover:
    def __init__(self, model="u2net"):
        logger.info("=" * 60)
        logger.info("Inizializzazione AI...")
        
        self.model_name = model
        
        try:
            from rembg.session_factory import new_session
        except Exception as e:
            raise RuntimeError(f"rembg non installato: {e}")
        
        model_path = ensure_model()
        os.environ['U2NET_HOME'] = str(Path(model_path).parent)
        
        try:
            self.session = new_session(model)
            logger.success("AI Pronta!")
        except Exception as e:
            raise RuntimeError(f"Sessione AI fallita: {e}")
        
        logger.info("=" * 60)
    
    def remove_background(self, input_path, output_path, quality=95):
        """
        ELABORAZIONE CON FIX PATH WINDOWS
        """
        result = {
            'success': False,
            'output_path': None,
            'error': None,
            'size_kb': None
        }
        
        # FIX 1: Normalizza input
        input_path = os.path.normpath(os.path.abspath(input_path))
        
        logger.info(f"Elaborazione: {os.path.basename(input_path)}")
        
        # Verifica input
        if not os.path.exists(input_path):
            result['error'] = f"File non trovato: {input_path}"
            logger.error(result['error'])
            return result
        
        # FIX 2: Prepara output con path Windows corretto
        try:
            # Normalizza e converte in path assoluto
            output_path = os.path.normpath(os.path.abspath(output_path))
            out_dir = os.path.dirname(output_path)
            
            logger.debug(f"Output dir: {out_dir}")
            
            # Crea cartella con retry
            for attempt in range(5):
                try:
                    # Usa Path per creazione robusta
                    Path(out_dir).mkdir(parents=True, exist_ok=True)
                    
                    # Verifica creazione
                    if os.path.exists(out_dir):
                        break
                    
                    time.sleep(0.2)
                    
                except Exception as e:
                    if attempt == 4:
                        raise
                    time.sleep(0.2)
            
            # Doppia verifica
            if not os.path.exists(out_dir):
                result['error'] = f"Cartella non creata: {out_dir}"
                logger.error(result['error'])
                return result
            
            # Test scrittura
            test_file = os.path.join(out_dir, "test_write.tmp")
            try:
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
            except Exception as e:
                result['error'] = f"Cartella non scrivibile: {out_dir}"
                logger.error(result['error'], e)
                return result
            
            logger.success(f"Cartella OK: {out_dir}")
            
        except Exception as e:
            result['error'] = f"Errore cartella: {str(e)}"
            logger.error(result['error'], e)
            return result
        
        # Elaborazione
        try:
            from PIL import Image
            from rembg import remove
            
            # Carica
            img = Image.open(input_path)
            logger.info(f"Dimensioni: {img.size}, Mode: {img.mode}")
            
            # Converti
            if img.mode in ('RGBA', 'P', 'LA', 'L', '1'):
                img = img.convert('RGB')
            
            # Rimuovi sfondo
            logger.info("Rimozione sfondo...")
            output = remove(img, session=self.session)
            
            # Ridimensiona
            if quality < 100:
                w, h = output.size
                new_w = max(1, int(w * quality / 100))
                new_h = max(1, int(h * quality / 100))
                output = output.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # RGBA
            if output.mode != 'RGBA':
                output = output.convert('RGBA')
            
            # SALVATAGGIO
            logger.debug(f"Salvataggio: {output_path}")
            output.save(output_path, 'PNG', optimize=True)
            
            # Verifica
            if not os.path.exists(output_path):
                result['error'] = "File non creato dopo save"
                logger.error(result['error'])
                return result
            
            size = os.path.getsize(output_path)
            if size < 100:
                os.remove(output_path)
                result['error'] = f"File troppo piccolo ({size} bytes)"
                logger.error(result['error'])
                return result
            
            result['success'] = True
            result['output_path'] = output_path
            result['size_kb'] = size / 1024
            logger.success(f"OK: {result['size_kb']:.1f} KB")
            return result
            
        except Exception as e:
            result['error'] = f"Errore: {str(e)}"
            logger.error(result['error'], e)
            return result
    
    def batch_process(self, file_paths, output_dir, quality=95, callback=None):
        """Elaborazione batch"""
        stats = {
            'total': len(file_paths),
            'success': 0,
            'failed': 0,
            'errors': [],
            'outputs': []
        }
        
        # FIX: Normalizza output dir
        output_dir = os.path.normpath(os.path.abspath(output_dir))
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"Batch: {stats['total']} file → {output_dir}")
        
        for idx, input_path in enumerate(file_paths, 1):
            filename = os.path.basename(input_path)
            base = os.path.splitext(filename)[0]
            output_path = os.path.join(output_dir, f"{base}_nobg.png")
            
            if callback:
                try:
                    callback(idx, stats['total'], filename)
                except InterruptedError:
                    logger.info("Interrotto dall'utente")
                    break
            
            result = self.remove_background(input_path, output_path, quality)
            
            if result['success']:
                stats['success'] += 1
                stats['outputs'].append(result['output_path'])
            else:
                stats['failed'] += 1
                stats['errors'].append({
                    'file': filename,
                    'error': result['error']
                })
        
        logger.info(f"Completato: {stats['success']}/{stats['total']}")
        return stats
