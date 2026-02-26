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

from utils.image_processor import BackgroundRemover


class ProcessingThread(QThread):
    """Thread per elaborazione immagini"""
    progress_updated = pyqtSignal(int, int, str)
    file_processed = pyqtSignal(str, bool, str)
    processing_finished = pyqtSignal(int, int)
    log_message = pyqtSignal(str)
    
    def __init__(self, file_paths, output_dir, quality=95, overwrite=False):
        super().__init__()
        self.file_paths = list(file_paths)
        self.output_dir = str(output_dir)
        self.quality = int(quality)
        self.overwrite = bool(overwrite)
        self.is_running = True
        self.remover = None
        
    def run(self):
        total = len(self.file_paths)
        success_count = 0
        error_count = 0
        
        try:
            self.remover = BackgroundRemover()
        except Exception as e:
            self.log_message.emit(f"❌ Errore AI: {str(e)}")
            self.processing_finished.emit(0, total)
            return
        
        self.log_message.emit(f"🚀 Avvio {total} immagini...")
        self.log_message.emit("-" * 30)
        
        for idx, file_path in enumerate(self.file_paths, 1):
            if not self.is_running:
                break
                
            filename = os.path.basename(file_path)
            self.progress_updated.emit(idx, total, filename)
            
            try:
                output_path = os.path.join(
                    self.output_dir, 
                    f"{Path(filename).stem}_nobg.png"
                )
                
                if os.path.exists(output_path) and not self.overwrite:
                    self.file_processed.emit(filename, True, "Saltato")
                    self.log_message.emit(f"⏭️ [{idx}/{total}] {filename} - Esiste")
                    continue
                
                self.log_message.emit(f"🔄 [{idx}/{total}] {filename}...")
                
                success = self.remover.remove_background(file_path, output_path, self.quality)
                
                if success:
                    success_count += 1
                    self.file_processed.emit(filename, True, "OK")
                    self.log_message.emit(f"✅ [{idx}/{total}] OK")
                else:
                    error_count += 1
                    self.file_processed.emit(filename, False, "Errore")
                    self.log_message.emit(f"❌ [{idx}/{total}] Errore")
                    
            except Exception as e:
                error_count += 1
                self.file_processed.emit(filename, False, "Err")
                self.log_message.emit(f"❌ [{idx}/{total}] {str(e)[:30]}")
        
        self.log_message.emit("-" * 30)
        self.log_message.emit(f"🏁 OK:{success_count} Err:{error_count}")
        self.processing_finished.emit(success_count, error_count)
    
    def stop(self):
        self.is_running = False


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Info")
        self.setFixedSize(350, 200)
        
        layout = QVBoxLayout(self)
        
        title = QLabel("🖼️ Background Remover v1.0")
        f = QFont()
        f.setPointSize(14)
        f.setBold(True)
        title.setFont(f)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        info = QLabel("Rimozione sfondi con AI U2Net\nNessuna API esterna")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)
        
        btn = QDialogButtonBox(QDialogButtonBox.Ok)
        btn.accepted.connect(self.accept)
        layout.addWidget(btn)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # INIZIALIZZA PRIMA LE VARIABILI
        self.settings = QSettings("BackgroundRemover", "App")
        self.input_files = []
        self.output_dir = ""
        self.thread = None
        
        # POI CREA UI
        self.setup_ui()
        
        # INFINE CARICA IMPOSTAZIONI
        self.load_settings()
        
    def setup_ui(self):
        self.setWindowTitle("🖼️ Background Remover")
        self.setMinimumSize(750, 550)
        
        central = QWidget()
        self.setCentralWidget(central)
        
        main = QVBoxLayout(central)
        main.setSpacing(10)
        main.setContentsMargins(12, 12, 12, 12)
        
        # Header
        hdr = QLabel("🖼️ Background Remover")
        f = QFont()
        f.setPointSize(18)
        f.setBold(True)
        hdr.setFont(f)
        hdr.setAlignment(Qt.AlignCenter)
        main.addWidget(hdr)
        
        # Splitter
        split = QSplitter(Qt.Vertical)
        main.addWidget(split, 1)
        
        # === PANNELLO SUPERIORE ===
        top = QWidget()
        top_l = QHBoxLayout(top)
        top_l.setSpacing(10)
        
        # Box immagini
        box_img = QGroupBox("📂 Immagini")
        v_img = QVBoxLayout(box_img)
        
        btn_sel = QPushButton("📁 Seleziona")
        btn_sel.setMinimumHeight(40)
        btn_sel.clicked.connect(self.on_select)
        v_img.addWidget(btn_sel)
        
        self.lbl_count = QLabel("0 immagini")
        self.lbl_count.setAlignment(Qt.AlignCenter)
        v_img.addWidget(self.lbl_count)
        
        self.list_files = QListWidget()
        v_img.addWidget(self.list_files)
        
        btn_clr = QPushButton("🗑️ Svuota")
        btn_clr.clicked.connect(self.on_clear)
        v_img.addWidget(btn_clr)
        
        top_l.addWidget(box_img, 1)
        
        # Box settings
        box_set = QGroupBox("⚙️ Opzioni")
        v_set = QVBoxLayout(box_set)
        
        btn_out = QPushButton("📂 Cartella Output")
        btn_out.setMinimumHeight(35)
        btn_out.clicked.connect(self.on_output)
        v_set.addWidget(btn_out)
        
        # IMPORTANTE: crea lbl_out QUI
        self.lbl_out = QLabel("Non selezionata")
        self.lbl_out.setWordWrap(True)
        v_set.addWidget(self.lbl_out)
        
        v_set.addSpacing(10)
        
        h_qual = QHBoxLayout()
        h_qual.addWidget(QLabel("Qualità:"))
        self.spin_qual = QSpinBox()
        self.spin_qual.setRange(50, 100)
        self.spin_qual.setValue(95)
        self.spin_qual.setSuffix("%")
        h_qual.addWidget(self.spin_qual)
        h_qual.addStretch()
        v_set.addLayout(h_qual)
        
        self.chk_over = QCheckBox("Sovrascrivi")
        v_set.addWidget(self.chk_over)
        
        v_set.addStretch()
        
        lbl_ai = QLabel("🤖 AI: U2Net")
        lbl_ai.setStyleSheet("color: green; font-weight: bold;")
        lbl_ai.setAlignment(Qt.AlignCenter)
        v_set.addWidget(lbl_ai)
        
        top_l.addWidget(box_set, 1)
        
        split.addWidget(top)
        
        # === PANNELLO INFERIORE ===
        bot = QWidget()
        bot_l = QVBoxLayout(bot)
        bot_l.setSpacing(8)
        
        box_prog = QGroupBox("📊 Progresso")
        v_prog = QVBoxLayout(box_prog)
        
        self.prog = QProgressBar()
        v_prog.addWidget(self.prog)
        
        self.lbl_curr = QLabel("Pronto")
        self.lbl_curr.setAlignment(Qt.AlignCenter)
        v_prog.addWidget(self.lbl_curr)
        
        bot_l.addWidget(box_prog)
        
        box_log = QGroupBox("📝 Log")
        v_log = QVBoxLayout(box_log)
        
        self.log_txt = QTextEdit()
        self.log_txt.setReadOnly(True)
        self.log_txt.setMaximumBlockCount(50)
        v_log.addWidget(self.log_txt)
        
        bot_l.addWidget(box_log)
        
        # IMPORTANTE: crea btn_go QUI
        self.btn_go = QPushButton("🚀 AVVIA")
        self.btn_go.setMinimumHeight(45)
        self.btn_go.setFont(QFont("Arial", 10, QFont.Bold))
        self.btn_go.clicked.connect(self.on_start)
        self.btn_go.setEnabled(False)
        bot_l.addWidget(self.btn_go)
        
        split.addWidget(bot)
        split.setSizes([200, 300])
        
        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Pronto")
        
        # Menu
        mb = self.menuBar()
        mfile = mb.addMenu("File")
        
        aopen = QAction("📁 Apri", self)
        aopen.setShortcut("Ctrl+O")
        aopen.triggered.connect(self.on_select)
        mfile.addAction(aopen)
        
        aexit = QAction("❌ Esci", self)
        aexit.setShortcut("Ctrl+Q")
        aexit.triggered.connect(self.close)
        mfile.addAction(aexit)
        
        mhelp = mb.addMenu("Aiuto")
        aabout = QAction("ℹ️ Info", self)
        aabout.triggered.connect(self.show_about)
        mhelp.addAction(aabout)
        
        # Stili minimali per velocità
        self.setStyleSheet("""
            QMainWindow { background: #f5f5f5; }
            QGroupBox { font-weight: bold; border: 1px solid #ccc; border-radius: 4px; margin-top: 6px; padding-top: 6px; background: white; }
            QGroupBox::title { subcontrol-origin: margin; left: 6px; padding: 0 3px; }
            QPushButton { background: #e8e8e8; border: 1px solid #bbb; border-radius: 3px; padding: 5px; font-weight: bold; }
            QPushButton:hover { background: #ddd; }
            QPushButton:disabled { background: #f0f0f0; color: #888; }
            QListWidget { border: 1px solid #ddd; background: #fafafa; }
            QProgressBar { border: 1px solid #ddd; text-align: center; }
            QProgressBar::chunk { background: #4CAF50; }
            QTextEdit { border: 1px solid #ddd; background: #2d2d2d; color: #eee; font-family: Consolas; font-size: 9px; }
        """)
        
    def load_settings(self):
        """CARICATA DOPO setup_ui, quindi lbl_out ESISTE"""
        saved = self.settings.value("output_dir", "")
        if saved:
            self.output_dir = str(saved)
            # Tronca per display
            display = self.output_dir[:25] + "..." if len(self.output_dir) > 25 else self.output_dir
            self.lbl_out.setText(f"📁 {display}")
        
    def save_settings(self):
        self.settings.setValue("output_dir", self.output_dir)
        
    def on_select(self):
        try:
            files, _ = QFileDialog.getOpenFileNames(
                self, "Seleziona", "", "Immagini (*.png *.jpg *.jpeg *.bmp *.tiff *.webp)"
            )
            if files:
                # Filtra validi
                valid = []
                for f in files:
                    ext = Path(f).suffix.lower()
                    if ext in {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp'}:
                        valid.append(f)
                
                self.input_files = valid
                self.update_list()
                self.add_log(f"📂 {len(valid)} immagini")
                self.check_ready()
        except Exception as e:
            QMessageBox.critical(self, "Errore", str(e))
            
    def update_list(self):
        self.list_files.clear()
        for f in self.input_files:
            self.list_files.addItem(f"📷 {os.path.basename(f)}")
        self.lbl_count.setText(f"{len(self.input_files)} immagini")
        
    def on_clear(self):
        self.input_files = []
        self.list_files.clear()
        self.lbl_count.setText("0 immagini")
        self.check_ready()
        self.add_log("🗑️ Svuotato")
        
    def on_output(self):
        try:
            d = QFileDialog.getExistingDirectory(self, "Output", str(Path.home()))
            if d:
                self.output_dir = d
                display = d[:25] + "..." if len(d) > 25 else d
                self.lbl_out.setText(f"📁 {display}")
                self.save_settings()
                self.check_ready()
                self.add_log(f"📂 {d}")
        except Exception as e:
            QMessageBox.critical(self, "Errore", str(e))
            
    def check_ready(self):
        # CONVERSIONE ESPLICITA A BOOL
        has_files = len(self.input_files) > 0
        has_dir = bool(self.output_dir) and self.output_dir != ""
        
        is_ready = bool(has_files and has_dir)
        self.btn_go.setEnabled(is_ready)
        
        if is_ready:
            self.status.showMessage(f"✅ Pronto: {len(self.input_files)} img")
        else:
            self.status.showMessage("⏳ Seleziona immagini e cartella")
            
    def on_start(self):
        if not self.input_files or not self.output_dir:
            QMessageBox.warning(self, "Attenzione", "Manca qualcosa!")
            return
            
        try:
            self.btn_go.setEnabled(False)
            self.btn_go.setText("⏳ ...")
            
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
            self.thread.log_message.connect(self.add_log)
            
            self.thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Avvio fallito: {str(e)}")
            self.btn_go.setEnabled(True)
            self.btn_go.setText("🚀 AVVIA")
            
    def on_progress(self, curr, tot, name):
        self.prog.setValue(curr)
        self.lbl_curr.setText(f"{name[:20]} ({curr}/{tot})")
        
    def on_file_done(self, name, ok, msg):
        for i in range(self.list_files.count()):
            item = self.list_files.item(i)
            if name in item.text():
                icon = "✅" if ok else "❌"
                item.setText(f"{icon} {name[:25]} - {msg}")
                break
                
    def on_finish(self, ok, err):
        self.btn_go.setEnabled(True)
        self.btn_go.setText("🚀 AVVIA")
        self.lbl_curr.setText("Completato")
        
        QMessageBox.information(self, "Finito", f"✅ OK: {ok}\n❌ Err: {err}")
        self.status.showMessage(f"🏁 OK:{ok} Err:{err}")
        
    def add_log(self, msg):
        t = datetime.now().strftime("%H:%M:%S")
        self.log_txt.append(f"[{t}] {msg}")
        # Scroll
        sb = self.log_txt.verticalScrollBar()
        sb.setValue(sb.maximum())
        
    def show_about(self):
        AboutDialog(self).exec_()
        
    def closeEvent(self, event):
        if self.thread and self.thread.isRunning():
            r = QMessageBox.question(self, "Uscire?", "Interrompere elaborazione?")
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
    # Ottimizzazioni per velocità
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    # Disabilita animazioni per velocità
    if hasattr(Qt, 'AA_DontShowIconsInMenus'):
        QApplication.setAttribute(Qt.AA_DontShowIconsInMenus, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName("BackgroundRemover")
    
    w = MainWindow()
    w.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
