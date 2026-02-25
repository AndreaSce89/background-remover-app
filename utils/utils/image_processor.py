#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image Processor - Background Removal usando rembg (U2Net)
"""

import os
import warnings
from pathlib import Path

# Suppressi warning tensorflow/onnx
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from PIL import Image
from rembg import remove
from rembg.session_factory import new_session


class BackgroundRemover:
    """Classe per rimozione sfondo immagini"""
    
    def __init__(self, model_name="u2net"):
        """
        Inizializza il rimuovi sfondo
        
        Args:
            model_name: Nome modello ('u2net', 'u2net_human_seg', 'u2net_cloth_seg')
        """
        self.model_name = model_name
        self.session = None
        self._init_session()
        
    def _init_session(self):
        """Inizializza sessione modello"""
        try:
            self.session = new_session(self.model_name)
        except Exception as e:
            print(f"Errore inizializzazione modello: {e}")
            self.session = None
            
    def remove_background(self, input_path, output_path, quality=95):
        """
        Rimuove lo sfondo da un'immagine
        
        Args:
            input_path: Percorso immagine input
            output_path: Percorso immagine output (PNG)
            quality: Qualità output (1-100)
            
        Returns:
            bool: True se successo, False altrimenti
        """
        try:
            # Verifica file input
            if not os.path.exists(input_path):
                raise FileNotFoundError(f"File non trovato: {input_path}")
                
            # Carica immagine
            input_image = Image.open(input_path)
            
            # Converti in RGB se necessario
            if input_image.mode in ('RGBA', 'P'):
                input_image = input_image.convert('RGB')
            
            # Rimuovi sfondo
            if self.session:
                output_image = remove(input_image, session=self.session)
            else:
                output_image = remove(input_image)
            
            # Converti in RGBA per trasparenza
            if output_image.mode != 'RGBA':
                output_image = output_image.convert('RGBA')
            
            # Ottimizza qualità
            if quality < 100:
                # Riduci dimensioni se qualità < 100
                width, height = output_image.size
                new_width = int(width * quality / 100)
                new_height = int(height * quality / 100)
                output_image = output_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Salva come PNG con trasparenza
            output_image.save(output_path, format='PNG', optimize=True)
            
            return True
            
        except Exception as e:
            print(f"Errore elaborazione {input_path}: {str(e)}")
            return False
            
    def process_batch(self, file_list, output_dir, quality=95, overwrite=False, 
                     progress_callback=None, log_callback=None):
        """
        Elabora batch di immagini
        
        Args:
            file_list: Lista percorsi file input
            output_dir: Cartella output
            quality: Qualità output
            overwrite: Sovrascrivi file esistenti
            progress_callback: Funzione callback(current, total, filename)
            log_callback: Funzione callback(message)
            
        Returns:
            tuple: (success_count, error_count, skipped_count)
        """
        success_count = 0
        error_count = 0
        skipped_count = 0
        
        total = len(file_list)
        
        for idx, input_path in enumerate(file_list, 1):
            filename = os.path.basename(input_path)
            name_without_ext = Path(filename).stem
            output_path = os.path.join(output_dir, f"{name_without_ext}_nobg.png")
            
            # Callback progresso
            if progress_callback:
                progress_callback(idx, total, filename)
                
            # Verifica esistenza
            if os.path.exists(output_path) and not overwrite:
                if log_callback:
                    log_callback(f"⏭️  [{idx}/{total}] {filename} - Saltato (esiste)")
                skipped_count += 1
                continue
            
            # Elabora
            if log_callback:
                log_callback(f"🔄 [{idx}/{total}] Elaborazione: {filename}...")
                
            if self.remove_background(input_path, output_path, quality):
                success_count += 1
                if log_callback:
                    log_callback(f"✅ [{idx}/{total}] {filename} - Completato")
            else:
                error_count += 1
                if log_callback:
                    log_callback(f"❌ [{idx}/{total}] {filename} - Errore")
                    
        return success_count, error_count, skipped_count
