#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image Processor - Background Removal usando rembg (U2Net)
"""

import os
import sys
import warnings
import traceback
import logging
from pathlib import Path

# Setup logging
logger = logging.getLogger(__name__)

# Suppressi warning
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

try:
    from PIL import Image
    logger.info("PIL importato")
except Exception as e:
    logger.error(f"ERRORE import PIL: {e}")
    raise

try:
    from rembg import remove
    from rembg.session_factory import new_session
    logger.info("rembg importato")
except Exception as e:
    logger.error(f"ERRORE import rembg: {e}")
    raise


class BackgroundRemover:
    """Classe per rimozione sfondo immagini"""
    
    def __init__(self, model_name="u2net"):
        logger.info(f"Inizializzazione BackgroundRemover con modello {model_name}")
        self.model_name = model_name
        self.session = None
        self._init_session()
        
    def _init_session(self):
        """Inizializza sessione modello"""
        try:
            logger.info("Creazione sessione U2Net...")
            self.session = new_session(self.model_name)
            logger.info("Sessione creata con successo")
        except Exception as e:
            logger.error(f"Errore creazione sessione: {e}")
            logger.error(traceback.format_exc())
            self.session = None
            
    def remove_background(self, input_path, output_path, quality=95):
        """
        Rimuove lo sfondo da un'immagine
        """
        logger.info(f"Elaborazione: {input_path}")
        
        try:
            # Verifica file input
            if not os.path.exists(input_path):
                raise FileNotFoundError(f"File non trovato: {input_path}")
            
            logger.info(f"File esiste: {os.path.getsize(input_path)} bytes")
            
            # Carica immagine
            logger.info("Apertura immagine...")
            input_image = Image.open(input_path)
            logger.info(f"Immagine: {input_image.size}, mode: {input_image.mode}")
            
            # Converti in RGB se necessario
            if input_image.mode in ('RGBA', 'P'):
                input_image = input_image.convert('RGB')
                logger.info("Convertita in RGB")
            
            # Rimuovi sfondo
            logger.info("Rimozione sfondo...")
            if self.session:
                output_image = remove(input_image, session=self.session)
            else:
                output_image = remove(input_image)
            logger.info("Sfondo rimosso")
            
            # Converti in RGBA
            if output_image.mode != 'RGBA':
                output_image = output_image.convert('RGBA')
            
            # Ottimizza qualità
            if quality < 100:
                width, height = output_image.size
                new_width = int(width * quality / 100)
                new_height = int(height * quality / 100)
                output_image = output_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                logger.info(f"Ridimensionata a {new_width}x{new_height}")
            
            # Salva
            logger.info(f"Salvataggio in: {output_path}")
            output_image.save(output_path, format='PNG', optimize=True)
            logger.info("Salvato con successo")
            
            return True
            
        except Exception as e:
            logger.error(f"Errore elaborazione {input_path}: {str(e)}")
            logger.error(traceback.format_exc())
            return False
