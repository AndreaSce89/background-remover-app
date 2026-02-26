#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Background Remover - Main Application
Versione con verifica pre-elaborazione cartella output
"""

import sys
import os
import traceback

# Fix path PyInstaller
if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
else:
    bundle_dir = os.path.dirname(os.path.abspath(__file__))

if bundle_dir not in sys.path:
    sys.path.insert(0, bundle_dir)

# Forza stderr visibile
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                            QFileDialog, QListWidget, QProgressBar, QMessageBox,
                            QSpinBox, QGroupBox, QTextEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QDragEnterEvent, QDropEvent


def debug(msg):
    """Debug su stderr"""
    print(f"[MAIN] {msg}", file=sys.stderr, flush=True)


class ProcessingThread(QThread):
    log_message = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    file_processed = pyqtSignal(str, bool, str)
    processing_finished = pyqtSignal(int, int)
    
    def __init__(self, file_paths, output_dir, quality=95):
        super().__init__()
        self.file_paths = file_paths
        self.output_dir = output_dir
        self.quality = quality
        self._is_running = True
        
    def run(self):
        debug(f"Thread avviato: {len(self.file_paths)} files")
        debug(f"Output dir: {self.output_dir}")
        
        # ===================================================================
        # FIX: Verifica e crea cartella output PRIMA di tutto
        # ===================================================================
        try:
            abs_output = os.path.normpath(os.path.abspath(self.output_dir))
            if not os.path.exists(abs_output):
                debug(f"Creazione cartella output: {abs_output}")
                os.makedirs(abs_output, exist_ok=True)
            
            # Verifica permessi scrittura
            test_file = os.path.join(abs_output, ".test_write")
            try:
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                debug("Cartella output verificata: OK")
            except Exception as e:
                self.log_message.emit(f"❌ ERRORE PERMESSI: {str(e)}")
                debug(f"Errore permessi: {e}")
                self.processing_finished.emit(0, len(self.file_paths))
                return
                
        except Exception as e:
            self.log_message.emit(f"❌ ERRORE CARTELLA: {str(e)}")
            debug(f"Errore cartella: {e}")
            self.processing_finished.emit(0, len(self.file_paths))
            return
        
        # Import processor
        try:
            from utils.image_processor import BackgroundRemover
        except Exception as e:
            err = f"Import fallito: {e}"
            debug(err)
            self.log_message.emit(f"❌ {err[:100]}")
            self.processing_finished.emit(0, len(self.file_paths))
            return
        
        # Init AI
        try:
            self.log_message.emit("🧠 Caricamento AI...")
            remover = BackgroundRemover()
            self.log_message.emit("✅ AI Pronta!")
        except Exception as e:
            err = f"AI Error: {e}"
            debug(err)
            self.log_message.emit(f"❌ {err[:100]}")
            self.processing_finished.emit(0, len(self.file_paths))
            return
        
        # Process files
        total = len(self.file_paths)
        success = 0
        
        for idx, path in enumerate(self.file_paths, 1):
            if not self._is_running:
                break
            
            filename = os.path.basename(path)
            base = os.path.splitext(filename)[0]
            out_path = os.path.join(self.output_dir, f"{base}_nobg.png")
            
            self.log_message.emit(f"{'─'*40}")
            self.log_message.emit(f"🔄 [{idx}/{total}] {filename}")
            debug(f"[{idx}/{total}] {filename}")
            
            try:
                result = remover.remove_background(path, out_path, self.quality)
                
                if result:
                    size = os.path.getsize(out_path) / 1024
                    self.log_message.emit(f"✅ Fatto ({size:.1f} KB)")
                    self.file_processed.emit(path, True, out_path)
                    success += 1
                else:
                    self.log_message.emit(f"❌ Fallito")
                    self.file_processed.emit(path, False, "")
                    
            except Exception as e:
                debug(f"Errore: {traceback.format_exc()}")
                self.log_message.emit(f"❌ Errore: {str(e)[:50]}")
                self.file_processed.emit(path, False, "")
            
            self.progress_updated.emit(int((idx/total)*100))
        
        self.log_message.emit(f"{'─'*40}")
        self.log_message.emit(f"🏁 Completato: {success}/{total}")
        debug(f"Finito: {success}/{total}")
        self.processing_finished.emit(success, total)
    
    def stop(self):
        self._is_running = False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Background Remover Pro v2.1")
        self.setMinimumSize(900, 700)
        self.files_list = []
        self.thread = None
        
        self.setup_ui()
        debug("MainWindow inizializzata")
        
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Input
        g1 = QGroupBox("📂 Cartella Input")
        h1 = QHBoxLayout()
        self.in_edit = QLineEdit()
        self.in_edit.setPlaceholderText("Trascina cartella qui...")
        b1 = QPushButton("Sfoglia...")
        b1.clicked.connect(self.browse_input)
        h1.addWidget(self.in_edit)
        h1.addWidget(b1)
        g1.setLayout(h1)
        layout.addWidget(g1)
        
        # Output
        g2 = QGroupBox("💾 Cartella Output")
        h2 = QHBoxLayout()
        self.out_edit = QLineEdit()
        self.out_edit.setPlaceholderText("Lascia vuoto per sottocartella 'output'")
        b2 = QPushButton("Sfoglia...")
        b2.clicked.connect(self.browse_output)
        h2.addWidget(self.out_edit)
        h2.addWidget(b2)
        g2.setLayout(h2)
        layout.addWidget(g2)
        
        # Quality
        q = QHBoxLayout()
        q.addWidget(QLabel("Qualità:"))
        self.qual = QSpinBox()
        self.qual.setRange(10, 100)
        self.qual.setValue(95)
        self.qual.setSuffix("%")
        q.addWidget(self.qual)
        q.addStretch()
        layout.addLayout(q)
        
        # File list
        self.list_w = QListWidget()
        self.list_w.setAcceptDrops(True)
        self.list_w.dragEnterEvent = self.drag_enter
        self.list_w.dropEvent = self.drop
        layout.addWidget(QLabel("Files:"))
        layout.addWidget(self.list_w)
        
        # Progress
        self.prog = QProgressBar()
        layout.addWidget(self.prog)
        
        # Log
        layout.addWidget(QLabel("Log:"))
        self.log = QTextEdit()
        self.log.setMaximumHeight(200)
        self.log.setReadOnly(True)
        layout.addWidget(self.log)
        
        # Buttons
        btn = QHBoxLayout()
        self.start_btn = QPushButton("▶️ AVVIA")
        self.start_btn.setStyleSheet("font-size: 14px; padding: 10px; background: #4CAF50; color: white;")
        self.start_btn.clicked.connect(self.start)
        
        clear = QPushButton("🗑️ Pulisci")
        clear.clicked.connect(self.clear)
        
        btn.addWidget(self.start_btn)
        btn.addWidget(clear)
        layout.addLayout(btn)
        
        # Status
        self.status = QLabel("Pronto")
        layout.addWidget(self.status)
    
    def drag_enter(self, e):
        if e.mimeData().hasUrls():
            e.accept()
    
    def drop(self, e):
        for url in e.mimeData().urls():
            p = url.toLocalFile()
            if os.path.isdir(p):
                self.load_folder(p)
            elif p.lower().endswith(('.png', '.jpg', '.jpeg')):
                self.add_file(p)
    
    def browse_input(self):
        f = QFileDialog.getExistingDirectory(self, "Seleziona input")
        if f:
            self.load_folder(f)
    
    def load_folder(self, folder):
        self.in_edit.setText(folder)
        self.files_list.clear()
        self.list_w.clear()
        
        for f in os.listdir(folder):
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                p = os.path.join(folder, f)
                self.files_list.append(p)
                self.list_w.addItem(f"📄 {f}")
        
        msg = f"Trovate {len(self.files_list)} immagini"
        self.status.setText(msg)
        debug(msg)
    
    def add_file(self, p):
        if p not in self.files_list:
            self.files_list.append(p)
            self.list_w.addItem(os.path.basename(p))
    
    def browse_output(self):
        f = QFileDialog.getExistingDirectory(self, "Seleziona output")
        if f:
            self.out_edit.setText(f)
    
    def start(self):
        if not self.files_list:
            QMessageBox.warning(self, "Attenzione", "Nessuna immagine!")
            return
        
        # Determina cartella output
        out = self.out_edit.text().strip()
        if not out:
            out = os.path.join(self.in_edit.text(), "output_nobg")
        
        # Normalizza path
        out = os.path.normpath(os.path.abspath(out))
        
        self.start_btn.setEnabled(False)
        self.prog.setValue(0)
        self.log.clear()
        
        self.thread = ProcessingThread(self.files_list.copy(), out, self.qual.value())
        self.thread.log_message.connect(self.log.append)
        self.thread.progress_updated.connect(self.prog.setValue)
        self.thread.processing_finished.connect(self.done)
        self.thread.start()
    
    def done(self, success, total):
        self.start_btn.setEnabled(True)
        self.status.setText(f"Completato: {success}/{total}")
        
        if success == total:
            QMessageBox.information(self, "Fatto!", f"Successo: {success}/{total}")
        elif success > 0:
            QMessageBox.warning(self, "Parziale", f"Successo: {success}/{total}")
        else:
            QMessageBox.critical(self, "Errore", 
                "Nessuna immagine elaborata!\n\n"
                "Esegui da CMD per vedere l'errore:\n"
                "cd cartella_exe\nBackgroundRemover.exe")
    
    def clear(self):
        self.files_list.clear()
        self.list_w.clear()
        self.log.clear()
        self.in_edit.clear()
        self.out_edit.clear()
        self.prog.setValue(0)


def main():
    debug(f"Avvio: {sys.executable}")
    debug(f"Frozen: {getattr(sys, 'frozen', False)}")
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    w = MainWindow()
    w.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
