#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Background Remover - Main Application
Versione: Console + GUI con stderr visibile
"""

import sys
import os
import io
import traceback

# Fix per PyInstaller - imposta path prima di tutto
if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
else:
    bundle_dir = os.path.dirname(os.path.abspath(__file__))

if bundle_dir not in sys.path:
    sys.path.insert(0, bundle_dir)

# Forza stderr su console (cruciale per debug EXE)
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                            QFileDialog, QListWidget, QProgressBar, QMessageBox,
                            QSpinBox, QGroupBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QDragEnterEvent, QDropEvent


def debug_log(msg):
    """Stampa debug sia su stderr che su file di log"""
    full_msg = f"[DEBUG {os.getpid()}] {msg}"
    print(full_msg, file=sys.stderr, flush=True)
    
    # Log su file per sicurezza
    try:
        log_path = os.path.join(os.path.expanduser("~"), "bg_remover_debug.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"{full_msg}\n")
    except:
        pass


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
        debug_log("=" * 60)
        debug_log("THREAD AVVIATO")
        debug_log(f"File: {len(self.file_paths)}")
        debug_log(f"Output: {self.output_dir}")
        debug_log(f"Python: {sys.executable}")
        debug_log(f"Frozen: {getattr(sys, 'frozen', False)}")
        debug_log(f"Bundle dir: {bundle_dir}")
        
        # Lista moduli disponibili
        try:
            import pkgutil
            mods = [m.name for m in pkgutil.iter_modules()]
            debug_log(f"Moduli trovati: {len(mods)}")
            if 'rembg' in mods:
                debug_log("✓ rembg disponibile")
            if 'onnxruntime' in mods:
                debug_log("✓ onnxruntime disponibile")
        except Exception as e:
            debug_log(f"Errore scan moduli: {e}")
        
        # Import processor con try/except dettagliato
        try:
            debug_log("Import BackgroundRemover...")
            from utils.image_processor import BackgroundRemover
            debug_log("Import OK")
        except Exception as e:
            err_msg = f"Import fallito: {str(e)}\n{traceback.format_exc()}"
            debug_log(err_msg)
            self.log_message.emit(f"❌ {err_msg[:200]}")
            self.processing_finished.emit(0, len(self.file_paths))
            return
        
        # Inizializza AI
        try:
            self.log_message.emit("🧠 Caricamento AI...")
            debug_log("Inizializzazione AI...")
            remover = BackgroundRemover()
            debug_log("AI Pronta!")
            self.log_message.emit("✅ AI pronta!")
        except Exception as e:
            err_msg = f"AI Error: {str(e)}\n{traceback.format_exc()}"
            debug_log(err_msg)
            self.log_message.emit(f"❌ {err_msg[:200]}")
            self.processing_finished.emit(0, len(self.file_paths))
            return
        
        # Processa files
        total = len(self.file_paths)
        success_count = 0
        
        self.log_message.emit(f"🚀 Avvio {total} immagini...")
        debug_log(f"Inizio processing {total} files")
        
        for idx, file_path in enumerate(self.file_paths, 1):
            if not self._is_running:
                debug_log("Thread interrotto dall'utente")
                break
            
            filename = os.path.basename(file_path)
            base_name = os.path.splitext(filename)[0]
            output_path = os.path.join(self.output_dir, f"{base_name}_nobg.png")
            
            self.log_message.emit(f"{'-'*40}")
            self.log_message.emit(f"🔄 [{idx}/{total}] {filename}...")
            debug_log(f"[{idx}/{total}] Processing: {file_path}")
            
            try:
                debug_log(f"Chiamata remove_background...")
                result = remover.remove_background(file_path, output_path, self.quality)
                
                if result and os.path.exists(output_path):
                    size = os.path.getsize(output_path)
                    msg = f"✅ Fatto! ({size/1024:.1f} KB)"
                    self.log_message.emit(msg)
                    self.file_processed.emit(file_path, True, output_path)
                    success_count += 1
                    debug_log(f"SUCCESSO: {output_path}")
                else:
                    msg = "❌ remove_background fallito (return False)"
                    self.log_message.emit(msg)
                    self.file_processed.emit(file_path, False, "")
                    debug_log("FALLITO: remove_background ha restituito False")
                    
            except Exception as e:
                err_msg = f"❌ Errore: {str(e)}"
                self.log_message.emit(err_msg[:100])
                self.file_processed.emit(file_path, False, "")
                debug_log(f"ECCEZIONE: {traceback.format_exc()}")
            
            progress = int((idx / total) * 100)
            self.progress_updated.emit(progress)
        
        debug_log(f"FINITO. Successi: {success_count}/{total}")
        self.log_message.emit(f"{'-'*40}")
        self.log_message.emit(f"🏁 Completato: {success_count}/{total}")
        self.processing_finished.emit(success_count, total)
    
    def stop(self):
        self._is_running = False
        self.wait(1000)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Background Remover Pro")
        self.setMinimumSize(800, 600)
        self.files_list = []
        self.processing_thread = None
        
        self.setup_ui()
        debug_log("MainWindow inizializzata")
        
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Gruppo Input
        input_group = QGroupBox("📂 Cartella Input")
        input_layout = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Trascina cartella qui o clicca Sfoglia...")
        self.input_btn = QPushButton("Sfoglia...")
        self.input_btn.clicked.connect(self.browse_input)
        input_layout.addWidget(self.input_edit)
        input_layout.addWidget(self.input_btn)
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # Gruppo Output
        output_group = QGroupBox("💾 Cartella Output")
        output_layout = QHBoxLayout()
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Cartella di destinazione...")
        self.output_btn = QPushButton("Sfoglia...")
        self.output_btn.clicked.connect(self.browse_output)
        output_layout.addWidget(self.output_edit)
        output_layout.addWidget(self.output_btn)
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        # Qualità
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("Qualità:"))
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(10, 100)
        self.quality_spin.setValue(95)
        self.quality_spin.setSuffix("%")
        quality_layout.addWidget(self.quality_spin)
        quality_layout.addStretch()
        layout.addLayout(quality_layout)
        
        # Lista files
        self.list_widget = QListWidget()
        self.list_widget.setAcceptDrops(True)
        self.list_widget.dragEnterEvent = self.dragEnterEvent
        self.list_widget.dragMoveEvent = self.dragEnterEvent
        self.list_widget.dropEvent = self.dropEvent
        layout.addWidget(QLabel("Files:"))
        layout.addWidget(self.list_widget)
        
        # Progress
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        
        # Log
        layout.addWidget(QLabel("Log:"))
        self.log_widget = QListWidget()
        self.log_widget.setMaximumHeight(200)
        layout.addWidget(self.log_widget)
        
        # Bottoni
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("▶️ AVVIA")
        self.start_btn.setStyleSheet("font-size: 14px; padding: 10px; background: #4CAF50; color: white;")
        self.start_btn.clicked.connect(self.start_processing)
        
        self.clear_btn = QPushButton("🗑️ Pulisci")
        self.clear_btn.clicked.connect(self.clear_all)
        
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.clear_btn)
        layout.addLayout(btn_layout)
        
        # Status
        self.status_label = QLabel("Pronto")
        layout.addWidget(self.status_label)
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                self.input_edit.setText(path)
                self.scan_folder(path)
            elif path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
                if path not in self.files_list:
                    self.files_list.append(path)
                    self.list_widget.addItem(os.path.basename(path))
    
    def browse_input(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleziona cartella input")
        if folder:
            self.input_edit.setText(folder)
            self.scan_folder(folder)
    
    def scan_folder(self, folder):
        self.files_list.clear()
        self.list_widget.clear()
        extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff')
        
        for file in os.listdir(folder):
            if file.lower().endswith(extensions):
                full_path = os.path.join(folder, file)
                self.files_list.append(full_path)
                self.list_widget.addItem(f"📄 {file}")
        
        self.log_message(f"📂 {len(self.files_list)} immagini trovate")
        debug_log(f"Scansionata cartella: {folder}, trovati {len(self.files_list)} files")
    
    def browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleziona cartella output")
        if folder:
            self.output_edit.setText(folder)
    
    def log_message(self, msg):
        self.log_widget.addItem(msg)
        self.log_widget.scrollToBottom()
    
    def start_processing(self):
        if not self.files_list:
            QMessageBox.warning(self, "Attenzione", "Nessuna immagine caricata!")
            return
        
        output_dir = self.output_edit.text().strip()
        if not output_dir:
            # Usa sottocartella "output" nella cartella input
            input_dir = self.input_edit.text()
            output_dir = os.path.join(input_dir, "output_nobg")
        
        os.makedirs(output_dir, exist_ok=True)
        self.output_edit.setText(output_dir)
        
        self.start_btn.setEnabled(False)
        self.progress.setValue(0)
        
        debug_log("=" * 60)
        debug_log("AVVIO PROCESSING")
        
        self.processing_thread = ProcessingThread(
            self.files_list.copy(),
            output_dir,
            self.quality_spin.value()
        )
        self.processing_thread.log_message.connect(self.log_message)
        self.processing_thread.progress_updated.connect(self.progress.setValue)
        self.processing_thread.processing_finished.connect(self.on_finished)
        self.processing_thread.start()
    
    def on_finished(self, success, total):
        self.start_btn.setEnabled(True)
        self.status_label.setText(f"Completato: {success}/{total}")
        
        if success == total:
            QMessageBox.information(self, "Fatto!", f"Elaborate {success} immagini con successo!")
        elif success > 0:
            QMessageBox.warning(self, "Completato con errori", 
                              f"Successo: {success}/{total}\nControlla il log per i dettagli.")
        else:
            QMessageBox.critical(self, "Errore", 
                               "Nessuna immagine elaborata!\n\nLancia da CMD per vedere l'errore:\n"
                               "cd cartella_exe\nBackgroundRemover.exe")
    
    def clear_all(self):
        self.files_list.clear()
        self.list_widget.clear()
        self.log_widget.clear()
        self.progress.setValue(0)
        self.input_edit.clear()
        self.output_edit.clear()
    
    def closeEvent(self, event):
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.stop()
        event.accept()


def main():
    debug_log("=" * 60)
    debug_log("APPLICAZIONE AVVIATA")
    debug_log(f"Args: {sys.argv}")
    debug_log(f"CWD: {os.getcwd()}")
    
    # Crea QApplication
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Mostra finestra
    window = MainWindow()
    window.show()
    
    debug_log("Finestra mostrata, entering main loop...")
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
