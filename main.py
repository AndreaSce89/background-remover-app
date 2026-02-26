#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Background Remover App - Versione Stabile e Veloce
"""

import sys
import os
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem, QFileDialog,
    QProgressBar, QTextEdit, QGroupBox, QSpinBox, QCheckBox,
    QMessageBox, QSplitter, QStatusBar, QMenuBar, QAction,
    QDialog, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings
from PyQt5.QtGui import QFont

# Import utils
from utils.image_processor import BackgroundRemover


class ProcessingThread(QThread):
    """Thread per elaborazione immagini"""
    progress_updated = pyqtSignal(int, int, str)
    file_processed = pyqtSignal(str, bool, str)
    processing_finished = pyqtSignal(int, int)
    log_message = pyqtSignal(str)
    
    def __init__(self, file_paths, output_dir, quality=95, overwrite=False):
        super().__init__()
        self.file_paths = file_paths.copy()  # Copia per sicurezza
        self.output_dir = str(output_dir)
        self.quality = int(quality)
        self.overwrite = bool(overwrite)
        self.is_running = True
        self.remover = None
        
    def run(self):
        """Elabora tutte le immagini"""
        total = len(self.file_paths)
        success_count = 0
        error_count = 0
        
        # Inizializza remover nel thread
        try:
            self.remover = BackgroundRemover()
        except Exception as e:
            self.log_message.emit(f"❌ Errore inizializzazione AI: {str(e)}")
            self.processing_finished.emit(0, total)
            return
        
        self.log_message.emit(f"🚀 Avvio elaborazione di {total} immagini...")
        self.log_message.emit(f"📁 Output: {self.output_dir}")
        self.log_message.emit("-" * 40)
        
        for idx, file_path in enumerate(self.file_paths, 1):
            if not self.is_running:
                self.log_message.emit("⚠️ Interrotto")
                break
                
            filename = os.path.basename(file_path)
            self.progress_updated.emit(idx, total, filename)
            
            try:
                output_path = os.path.join(
                    self.output_dir, 
                    f"{Path(filename).stem}_nobg.png"
                )
                
                # Controlla se esiste
                if os.path.exists(output_path) and not self.overwrite:
                    self.file_processed.emit(filename, True, "Saltato")
                    self.log_message.emit(f"⏭️  [{idx}/{total}] {filename} - Esiste già")
                    continue
                
                # Elabora
                self.log_message.emit(f"🔄 [{idx}/{total}] {filename}...")
                success = self.remover.remove_background(file_path, output_path, self.quality)
                
                if success:
                    success_count += 1
                    self.file_processed.emit(filename, True, "OK")
                    self.log_message.emit(f"✅ [{idx}/{total}] {filename} - OK")
                else:
                    error_count += 1
                    self.file_processed.emit(filename, False, "Errore")
                    self.log_message.emit(f"❌ [{idx}/{total}] {filename} - Errore")
                    
            except Exception as e:
                error_count += 1
                self.file_processed.emit(filename, False, str(e)[:50])
                self.log_message.emit(f"❌ [{idx}/{total}] {filename} - {str(e)[:50]}")
        
        self.log_message.emit("-" * 40)
        self.log_message.emit(f"🏁 Finito! OK: {success_count} | Errori: {error_count}")
        self.processing_finished.emit(success_count, error_count)
    
    def stop(self):
        self.is_running = False


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Informazioni")
        self.setFixedSize(400, 250)
        
        layout = QVBoxLayout(self)
        
        title = QLabel("🖼️ Background Remover")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        info = QLabel("""
        <p style='text-align: center;'>
        <b>Versione 1.0</b><br><br>
        Rimozione sfondi con AI locale<br>
        (U2Net - ONNX Runtime)<br><br>
        Nessuna API esterna richiesta
        </p>
        """)
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)
        
        btn = QDialogButtonBox(QDialogButtonBox.Ok)
        btn.accepted.connect(self.accept)
        layout.addWidget(btn)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🖼️ Background Remover")
        self.setMinimumSize(800, 600)
        
        self.settings = QSettings("BackgroundRemover", "App")
        self.input_files = []
        self.output_dir = ""
        self.processing_thread = None
        
        self.load_settings()
        self.setup_ui()
        self.apply_styles()
        
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        main = QVBoxLayout(central)
        main.setSpacing(10)
        main.setContentsMargins(15, 15, 15, 15)
        
        # Header
        header = QLabel("🖼️ Background Remover")
        f = QFont()
        f.setPointSize(20)
        f.setBold(True)
        header.setFont(f)
        header.setAlignment(Qt.AlignCenter)
        main.addWidget(header)
        
        # Splitter
        split = QSplitter(Qt.Vertical)
        main.addWidget(split, 1)
        
        # === PANNELLO SUPERIORE ===
        top = QWidget()
        top_layout = QHBoxLayout(top)
        top_layout.setSpacing(10)
        
        # Input
        input_box = QGroupBox("📂 Immagini")
        input_v = QVBoxLayout(input_box)
        
        btn_img = QPushButton("📁 Seleziona Immagini")
        btn_img.setMinimumHeight(45)
        btn_img.clicked.connect(self.select_images)
        input_v.addWidget(btn_img)
        
        self.lbl_count = QLabel("0 immagini")
        self.lbl_count.setAlignment(Qt.AlignCenter)
        input_v.addWidget(self.lbl_count)
        
        self.list_files = QListWidget()
        input_v.addWidget(self.list_files)
        
        btn_clear = QPushButton("🗑️ Svuota")
        btn_clear.clicked.connect(self.clear_files)
        input_v.addWidget(btn_clear)
        
        top_layout.addWidget(input_box, 1)
        
        # Settings
        set_box = QGroupBox("⚙️ Impostazioni")
        set_v = QVBoxLayout(set_box)
        
        btn_out = QPushButton("📂 Cartella Output")
        btn_out.setMinimumHeight(40)
        btn_out.clicked.connect(self.select_output)
        set_v.addWidget(btn_out)
        
        self.lbl_out = QLabel("Non selezionata")
        self.lbl_out.setWordWrap(True)
        set_v.addWidget(self.lbl_out)
        
        set_v.addSpacing(15)
        
        qual_box = QHBoxLayout()
        qual_box.addWidget(QLabel("Qualità:"))
        self.spin_qual = QSpinBox()
        self.spin_qual.setRange(50, 100)
        self.spin_qual.setValue(95)
        self.spin_qual.setSuffix("%")
        qual_box.addWidget(self.spin_qual)
        qual_box.addStretch()
        set_v.addLayout(qual_box)
        
        self.chk_over = QCheckBox("Sovrascrivi esistenti")
        set_v.addWidget(self.chk_over)
        
        set_v.addStretch()
        
        info = QLabel("🤖 AI: U2Net (Locale)")
        info.setStyleSheet("color: green; font-weight: bold;")
        info.setAlignment(Qt.AlignCenter)
        set_v.addWidget(info)
        
        top_layout.addWidget(set_box, 1)
        
        split.addWidget(top)
        
        # === PANNELLO INFERIORE ===
        bot = QWidget()
        bot_v = QVBoxLayout(bot)
        bot_v.setSpacing(8)
        
        prog_box = QGroupBox("📊 Progresso")
        prog_v = QVBoxLayout(prog_box)
        
        self.prog = QProgressBar()
        self.prog.setTextVisible(True)
        prog_v.addWidget(self.prog)
        
        self.lbl_curr = QLabel("Pronto")
        self.lbl_curr.setAlignment(Qt.AlignCenter)
        prog_v.addWidget(self.lbl_curr)
        
        bot_v.addWidget(prog_box)
        
        log_box = QGroupBox("📝 Log")
        log_v = QVBoxLayout(log_box)
        
        self.log_txt = QTextEdit()
        self.log_txt.setReadOnly(True)
        self.log_txt.setMaximumBlockCount(100)  # Limita log per performance
        log_v.addWidget(self.log_txt)
        
        bot_v.addWidget(log_box)
        
        self.btn_go = QPushButton("🚀 AVVIA")
        self.btn_go.setMinimumHeight(50)
        self.btn_go.setFont(QFont("Arial", 11, QFont.Bold))
        self.btn_go.clicked.connect(self.start)
        self.btn_go.setEnabled(False)
        bot_v.addWidget(self.btn_go)
        
        split.addWidget(bot)
        split.setSizes([250, 350])
        
        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Pronto")
        
        # Menu
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        
        act_open = QAction("📁 Apri", self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self.select_images)
        file_menu.addAction(act_open)
        
        act_exit = QAction("❌ Esci", self)
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)
        
        help_menu = menubar.addMenu("Aiuto")
        act_about = QAction("ℹ️ Info", self)
        act_about.triggered.connect(self.show_about)
        help_menu.addAction(act_about)
        
    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #f0f0f0; }
            QGroupBox { font-weight: bold; border: 2px solid #ccc; border-radius: 6px; margin-top: 8px; padding-top: 8px; background: white; }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
            QPushButton { background: #e0e0e0; border: 2px solid #bbb; border-radius: 4px; padding: 6px 12px; font-weight: bold; }
            QPushButton:hover { background: #d0d0d0; }
            QPushButton:disabled { background: #f0f0f0; color: #999; }
            QListWidget { border: 2px solid #ddd; border-radius: 4px; background: #fafafa; }
            QProgressBar { border: 2px solid #ddd; border-radius: 4px; text-align: center; }
            QProgressBar::chunk { background-color: #4CAF50; }
            QTextEdit { border: 2px solid #ddd; border-radius: 4px; background: #2d2d2d; color: #f0f0f0; font-family: Consolas; font-size: 10px; }
        """)
        
    def load_settings(self):
        self.output_dir = str(self.settings.value("output_dir", ""))
        if self.output_dir:
            self.lbl_out.setText(f"📁 {self.output_dir[:30]}...")
        
    def save_settings(self):
        self.settings.setValue("output_dir", self.output_dir)
        
    def select_images(self):
        try:
            files, _ = QFileDialog.getOpenFileNames(
                self,
                "Seleziona Immagini",
                "",
                "Immagini (*.png *.jpg *.jpeg *.bmp *.tiff *.webp)"
            )
            
            if files:
                # Filtra solo immagini valide
                valid = [f for f in files if self.is_valid_image(f)]
                self.input_files = valid
                self.update_list()
                self.log(f"📂 Caricate {len(valid)} immagini")
                self.check_ready()
                
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Errore: {str(e)}")
            
    def is_valid_image(self, path):
        """Verifica se file è un'immagine valida"""
        ext = Path(path).suffix.lower()
        return ext in {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp'}
            
    def update_list(self):
        self.list_files.clear()
        for f in self.input_files:
            item = QListWidgetItem(f"📷 {os.path.basename(f)}")
            item.setToolTip(f)
            self.list_files.addItem(item)
        self.lbl_count.setText(f"{len(self.input_files)} immagini")
        
    def clear_files(self):
        self.input_files = []
        self.list_files.clear()
        self.lbl_count.setText("0 immagini")
        self.check_ready()
        self.log("🗑️ Svuotato")
        
    def select_output(self):
        try:
            d = QFileDialog.getExistingDirectory(
                self,
                "Cartella Output",
                self.output_dir or str(Path.home())
            )
            if d:
                self.output_dir = str(d)
                self.lbl_out.setText(f"📁 {d[:30]}...")
                self.save_settings()
                self.check_ready()
                self.log(f"📂 Output: {d}")
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Errore: {str(e)}")
            
    def check_ready(self):
        """CORREZIONE BUG: usa bool() esplicito"""
        has_files = len(self.input_files) > 0
        has_output = bool(self.output_dir) and self.output_dir != ""
        
        ready = bool(has_files and has_output)
        self.btn_go.setEnabled(ready)  # Ora è sempre bool!
        
        if ready:
            self.status.showMessage(f"✅ Pronto: {len(self.input_files)} img")
        else:
            self.status.showMessage("⏳ Seleziona immagini e cartella")
            
    def start(self):
        if not self.input_files or not self.output_dir:
            QMessageBox.warning(self, "Attenzione", "Manca qualcosa!")
            return
            
        try:
            self.btn_go.setEnabled(False)
            self.btn_go.setText("⏳ In corso...")
            
            self.prog.setMaximum(len(self.input_files))
            self.prog.setValue(0)
            
            self.thread = ProcessingThread(
                self.input_files,
                self.output_dir,
                int(self.spin_qual.value()),
                bool(self.chk_over.isChecked())
            )
            
            self.thread.progress_updated.connect(self.on_progress)
            self.thread.file_processed.connect(self.on_file_done)
            self.thread.processing_finished.connect(self.on_finish)
            self.thread.log_message.connect(self.log)
            
            self.thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Errore avvio: {str(e)}")
            self.btn_go.setEnabled(True)
            self.btn_go.setText("🚀 AVVIA")
            
    def on_progress(self, curr, tot, name):
        self.prog.setValue(curr)
        self.lbl_curr.setText(f"{name} ({curr}/{tot})")
        
    def on_file_done(self, name, ok, msg):
        for i in range(self.list_files.count()):
            item = self.list_files.item(i)
            if name in item.text():
                icon = "✅" if ok else "❌"
                item.setText(f"{icon} {name} - {msg}")
                break
                
    def on_finish(self, ok, err):
        self.btn_go.setEnabled(True)
        self.btn_go.setText("🚀 AVVIA")
        self.lbl_curr.setText("Completato")
        
        QMessageBox.information(
            self, 
            "Finito", 
            f"<b>Completato!</b><br>✅ OK: {ok}<br>❌ Errori: {err}"
        )
        
        self.status.showMessage(f"🏁 Finito: {ok} OK, {err} errori")
        
    def log(self, msg):
        t = datetime.now().strftime("%H:%M:%S")
        self.log_txt.append(f"[{t}] {msg}")
        # Auto-scroll
        sb = self.log_txt.verticalScrollBar()
        sb.setValue(sb.maximum())
        
    def show_about(self):
        AboutDialog(self).exec_()
        
    def closeEvent(self, event):
        if self.thread and self.thread.isRunning():
            r = QMessageBox.question(self, "Uscire?", "Interrompere?", 
                                     QMessageBox.Yes | QMessageBox.No)
            if r == QMessageBox.Yes:
                self.thread.stop()
                self.thread.wait(2000)
                event.accept()
            else:
                event.ignore()
        else:
            self.save_settings()
            event.accept()


def main():
    # Fix DPI
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName("BackgroundRemover")
    
    w = MainWindow()
    w.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
