#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File Handler - Gestione file e validazione
"""

import os
from pathlib import Path


class FileHandler:
    """Gestisce operazioni su file"""
    
    # Estensioni supportate
    SUPPORTED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp'}
    
    @staticmethod
    def is_valid_image(file_path):
        """
        Verifica se il file è un'immagine supportata
        
        Args:
            file_path: Percorso del file
            
        Returns:
            bool: True se valido
        """
        if not os.path.isfile(file_path):
            return False
            
        ext = Path(file_path).suffix.lower()
        return ext in FileHandler.SUPPORTED_EXTENSIONS
    
    @staticmethod
    def get_output_filename(input_path, suffix="_nobg", output_ext=".png"):
        """
        Genera nome file output
        
        Args:
            input_path: Percorso file input
            suffix: Suffisso da aggiungere
            output_ext: Estensione output
            
        Returns:
            str: Nome file output
        """
        stem = Path(input_path).stem
        return f"{stem}{suffix}{output_ext}"
    
    @staticmethod
    def scan_directory(directory, recursive=False):
        """
        Scansiona directory per immagini
        
        Args:
            directory: Percorso directory
            recursive: Scansione ricorsiva
            
        Returns:
            list: Lista percorsi immagini
        """
        images = []
        
        if recursive:
            for root, _, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    if FileHandler.is_valid_image(file_path):
                        images.append(file_path)
        else:
            for file in os.listdir(directory):
                file_path = os.path.join(directory, file)
                if FileHandler.is_valid_image(file_path):
                    images.append(file_path)
                    
        return sorted(images)
    
    @staticmethod
    def ensure_dir(directory):
        """
        Crea directory se non esiste
        
        Args:
            directory: Percorso directory
        """
        os.makedirs(directory, exist_ok=True)
    
    @staticmethod
    def get_file_size(file_path):
        """
        Ottiene dimensione file in formato leggibile
        
        Args:
            file_path: Percorso file
            
        Returns:
            str: Dimensione formattata
        """
        size = os.path.getsize(file_path)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    @staticmethod
    def filter_valid_images(file_list):
        """
        Filtra lista file mantenendo solo immagini valide
        
        Args:
            file_list: Lista percorsi file
            
        Returns:
            list: Lista file validi
        """
        return [f for f in file_list if FileHandler.is_valid_image(f)]
