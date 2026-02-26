#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image Processor - Versione Ultra-Stabile
Gestione completa errori, retry automatici, validazione output
"""

import os
import sys
import warnings
import traceback
import time
import shutil
from pathlib import Path

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

# Import logger
try:
    from logger import get_logger
    logger = get_logger()
except:
    class FakeLogger:
        def info(self, m): print(f"[INFO] {m}", file=sys.stderr)
        def debug(self, m): print(f"[DEBUG] {m}", file=sys.stderr)
        def error(self, m, e=None): print(f"[ERRORE] {m}", file=sys.stderr)
        def success(self, m): print(f"[OK] {m}", file=sys.stderr)
        def warning(self, m): print(f"[WARN] {m}", file=sys.stderr)
    logger = FakeLogger()


def ensure_model():
    """Scarica modello con retry e verifica"""
    model_dir = Path.home() / ".u2net"
    model_path = model_dir / "u2net.onnx"
    
    logger.info(f"Verifica modello: {model_path}")
    
    if model_path.exists():
        size_mb = model_path.stat().st_size / 1024 / 1024
        if size_mb > 150:  # Verifica dimensione minima (~176MB)
            logger.success(f"Modello trovato: {size_mb:.1f} MB")
            return str(model_path)
        else:
            logger.warning("Modello troppo piccolo, riscarico...")
            model_path.unlink()
    
    # Download con retry
    os.makedirs(model_dir, exist_ok=True)
    
    urls = [
        "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx",
        "https://huggingface.co/danielgatis/rembg/resolve/main/u2net.onnx",
    ]
    
    for attempt, url in enumerate(urls, 1):
        try:
            logger.info(f"Tentativo download {attempt}/{len(urls)}...")
            import urllib.request
            import ssl
            
            # Bypass SSL
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            opener = urllib.request.build_opener(
                urllib.request.HTTPSHandler(context=ctx)
            )
            urllib.request.install_opener(opener)
            
            # Download con timeout
            urllib.request.urlretrieve(url, model_path)
            
            # Verifica
            if model_path.exists() and model_path.stat().st_size > 160000000:
                size_mb = model_path.stat().st_size / 1024 / 1024
                logger.success(f"Download OK: {size_mb:.1f} MB")
                return str(model_path)
            else:
                logger.error("Download incompleto")
                if model_path.exists():
                    model_path.unlink()
                    
        except Exception as e:
            logger.error(f"Download fallito: {url[:50]}...", e)
    
    raise FileNotFoundError("Impossibile scaricare modello u2net")


class BackgroundRemover:
    def __init__(self, model="u2net"):
        logger.info("=" * 70)
        logger.info("Inizializzazione BackgroundRemover")
        
        self.model_name = model
        self.session = None
        self.fallback_mode = False
        
        # 1. Verifica rembg
        try:
            from rembg.session_factory import new_session
            logger.info("✓ rembg importato")
        except Exception as e:
            logger.error("✗ Import rembg fallito", e)
            raise RuntimeError("rembg non disponibile. Reinstallare: pip install rembg")
        
        # 2. Verifica/Scarica modello
        model_path = ensure_model()
        os.environ['U2NET_HOME'] = str(Path(model_path).parent)
        
        # 3. Crea sessione ONNX
        try:
            logger.info("Creazione sessione AI...")
            self.session = new_session(model)
            logger.success("Sessione AI creata con successo!")
        except Exception as e:
            logger.error("Creazione sessione fallita", e)
            raise RuntimeError("AI non inizializzata. Verificare installazione onnxruntime.")
        
        logger.info("=" * 70)
    
    def remove_background(self, input_path, output_path, quality=95):
        """
        Rimuove sfondo con validazione completa
        
        Returns:
            dict: {
                'success': bool,
                'output_path': str or None,
                'error': str or None,
                'size_kb': float or None
            }
        """
        result = {
            'success': False,
            'output_path': None,
            'error': None,
            'size_kb': None
        }
        
        logger.info(f"{'─' * 70}")
        logger.info(f"ELABORAZIONE: {os.path.basename(input_path)}")
        
        # VALIDAZIONE INPUT
        if not os.path.exists(input_path):
            result['error'] = f"File input non trovato: {input_path}"
            logger.error(result['error'])
            return result
        
        # PREPARAZIONE OUTPUT
        try:
            output_path = os.path.normpath(os.path.abspath(output_path))
            out_dir = os.path.dirname(output_path)
            
            # Crea cartella con retry
            for attempt in range(3):
                try:
                    os.makedirs(out_dir, exist_ok=True)
                    break
                except Exception as e:
                    if attempt == 2:
                        raise
                    time.sleep(0.1)
            
            # Verifica scrivibile
            test_file = os.path.join(out_dir, ".write_test")
            try:
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
            except Exception as e:
                result['error'] = f"Cartella non scrivibile: {out_dir}"
                logger.error(result['error'], e)
                return result
            
            logger.info(f"Output: {output_path}")
            
        except Exception as e:
            result['error'] = f"Errore preparazione output: {str(e)}"
            logger.error(result['error'], e)
            return result
        
        # ELABORAZIONE
        try:
            from PIL import Image
            from rembg import remove
            
            # Carica immagine
            logger.debug("Apertura immagine...")
            img = Image.open(input_path)
            logger.info(f"Dimensioni: {img.size}, Mode: {img.mode}")
            
            # Converti se necessario
            if img.mode in ('RGBA', 'P', 'LA', 'L', '1'):
                img = img.convert('RGB')
                logger.debug("Convertita in RGB")
            
            # Rimuovi sfondo
            logger.info("Rimozione sfondo in corso...")
            start = time.time()
            output = remove(img, session=self.session)
            elapsed = time.time() - start
            logger.success(f"Rimozione completata in {elapsed:.2f}s")
            
            # Ridimensiona se richiesto
            if quality < 100:
                w, h = output.size
                new_w = max(1, int(w * quality / 100))
                new_h = max(1, int(h * quality / 100))
                output = output.resize((new_w, new_h), Image.Resampling.LANCZOS)
                logger.info(f"Ridimensionata: {new_w}x{new_h}")
            
            # Assicura RGBA
            if output.mode != 'RGBA':
                output = output.convert('RGBA')
            
            # SALVATAGGIO con verifica
            logger.debug("Salvataggio...")
            output.save(output_path, 'PNG', optimize=True)
            
            # VERIFICA FINALE
            if not os.path.exists(output_path):
                result['error'] = "File non creato dopo salvataggio"
                logger.error(result['error'])
                return result
            
            size_bytes = os.path.getsize(output_path)
            if size_bytes < 100:  # File troppo piccolo = corrotto
                result['error'] = f"File creato ma troppo piccolo ({size_bytes} bytes)"
                logger.error(result['error'])
                os.remove(output_path)
                return result
            
            size_kb = size_bytes / 1024
            logger.success(f"File salvato: {size_kb:.1f} KB")
            
            result['success'] = True
            result['output_path'] = output_path
            result['size_kb'] = size_kb
            return result
            
        except Exception as e:
            result['error'] = f"Errore elaborazione: {str(e)}"
            logger.error(result['error'], e)
            return result
    
    def batch_process(self, file_paths, output_dir, quality=95, callback=None):
        """
        Elaborazione batch con report dettagliato
        
        Args:
            file_paths: lista path input
            output_dir: cartella output
            quality: qualità output
            callback: funzione(progress, current_file, total)
        
        Returns:
            dict: statistiche elaborazione
        """
        stats = {
            'total': len(file_paths),
            'success': 0,
            'failed': 0,
            'errors': [],
            'outputs': []
        }
        
        logger.info("=" * 70)
        logger.info(f"AVVIO BATCH: {stats['total']} immagini")
        logger.info(f"Output: {output_dir}")
        logger.info("=" * 70)
        
        os.makedirs(output_dir, exist_ok=True)
        
        for idx, input_path in enumerate(file_paths, 1):
            filename = os.path.basename(input_path)
            base = os.path.splitext(filename)[0]
            output_path = os.path.join(output_dir, f"{base}_nobg.png")
            
            if callback:
                callback(idx, stats['total'], filename)
            
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
        
        logger.info("=" * 70)
        logger.info(f"BATCH COMPLETATO: {stats['success']}/{stats['total']} successo")
        if stats['failed'] > 0:
            logger.warning(f"Falliti: {stats['failed']}")
        logger.info("=" * 70)
        
        return stats
