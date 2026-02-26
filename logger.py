#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Logger Module - Gestione log su file e popup errori
"""

import os
import sys
import time
import traceback
from datetime import datetime

class AppLogger:
    def __init__(self):
        self.log_file = None
        self.log_path = os.path.join(
            os.path.expanduser("~"), 
            "BackgroundRemover_Logs",
            f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        self._ensure_log_dir()
        self._open_log()
        
    def _ensure_log_dir(self):
        log_dir = os.path.dirname(self.log_path)
        os.makedirs(log_dir, exist_ok=True)
        
    def _open_log(self):
        try:
            self.log_file = open(self.log_path, "w", encoding="utf-8", buffering=1)
            self._write("=" * 70)
            self._write(f"Background Remover - Log Avviato")
            self._write(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            self._write(f"Utente: {os.getlogin()}")
            self._write(f"PID: {os.getpid()}")
            self._write("=" * 70)
        except Exception as e:
            print(f"ERRORE LOG: {e}", file=sys.stderr)
            
    def _write(self, msg):
        timestamp = time.strftime('%H:%M:%S')
        line = f"[{timestamp}] {msg}"
        
        # Sempre su stderr (visibile se console aperta)
        print(line, file=sys.stderr, flush=True)
        
        # Su file
        if self.log_file:
            try:
                self.log_file.write(line + "\n")
                self.log_file.flush()
            except:
                pass
                
    def info(self, msg):
        self._write(f"INFO: {msg}")
        
    def debug(self, msg):
        self._write(f"DEBUG: {msg}")
        
    def error(self, msg, exception=None):
        self._write(f"ERRORE: {msg}")
        if exception:
            self._write(f"DETTAGLIO: {str(exception)}")
            self._write(f"TRACEBACK:\n{traceback.format_exc()}")
            
    def success(self, msg):
        self._write(f"SUCCESSO: {msg}")
        
    def warning(self, msg):
        self._write(f"AVVISO: {msg}")
        
    def get_log_path(self):
        return self.log_path
        
    def get_last_errors(self, n=10):
        """Restituisce ultimi N errori per popup"""
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                errors = [l.strip() for l in lines if "ERRORE:" in l or "TRACEBACK:" in l]
                return errors[-n:] if errors else ["Nessun errore registrato"]
        except:
            return ["Impossibile leggere log"]
            
    def close(self):
        if self.log_file:
            self._write("=" * 70)
            self._write("SESSIONE TERMINATA")
            self._write("=" * 70)
            self.log_file.close()
            self.log_file = None

# Singleton logger
_logger = None

def get_logger():
    global _logger
    if _logger is None:
        _logger = AppLogger()
    return _logger
