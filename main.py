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
    QProgressBar, QPlainTextEdit, QGroupBox, QSpinBox, QCheckBox,
    QMessageBox, QSplitter, QStatusBar, QMenuBar, QAction,
    QDialog, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings
from PyQt5.QtGui import QFont

# Import posticipato per velocità
# from utils.image_processor import BackgroundRemover


class ProcessingThread(QThread):
    """Thread per elaborazione"""
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
        # Import qui per evitare rallentamenti all'avvio
        from utils.image_processor import BackgroundRemover
        
        total = len(self.file_paths)
        success_count = 0
        error_count = 0
        
        try:
            self.log_message.emit("🧠 Caricamento AI...")
            self.remover = BackgroundRemover()
        except Exception as e:
            self.log_message.emit(f"❌ Errore AI: {str(e)}")
            self.processing_finished.emit(0, total)
            return
        
        self.log_message.emit(f"🚀 Avvio {total} immagini...")
        self.log_message.emit("-" * 25)
        
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
                    self.log_message.emit(f"⏭️ [{idx}/{total}] Saltato")
                    continue
                
                self.log_message.emit(f"🔄 [{idx}/{total}] {filename[:20]}...")
                
                success = self.remover.remove_background(file_path, output_path, self.quality)
                
                if success:
                    success_count += 1
                    self.file_processed.emit(filename, True, "OK")
                    self.log_message.emit(f"✅ OK")
                else:
                    error_count += 1
                    self.file_processed.emit(filename, False, "Err")
                    self.log_message.emit(f"❌ Errore")
                    
            except Exception as e:
                error_count += 1
                self.file_processed.emit(filename, False, "Err")
                self.log_message.emit(f"❌ {str(e)[:20]}")
        
        self.log_message.emit("-" * 25)
        self.log_message.emit(f"🏁 OK:{success_count} Err:{error_count}")
        self.processing_finished.emit(success_count, error_count)
    
    def stop(self):
        self.is_running = False


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Info")
        self.setFixedSize(300, 150)
        
        layout = QVBoxLayout(self)
        
        title = QLabel("🖼️ Background Remover v1.0")
        f = QFont()
        f.setPointSize(12)
        f.setBold(True)
        title.setFont(f)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        info = QLabel("AI U2Net - Nessuna API esterna")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)
        
        btn = QDialogButtonBox(QDialogButtonBox.Ok)
        btn.accepted.connect(self.accept)
        layout.addWidget(btn)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Variabili prima di tutto
        self.settings = QSettings("BackgroundRemover", "App")
        self.input_files = []
        self.output_dir = ""
        self.thread = None
        
        # UI
        self.setup_ui()
        
        # Impostazioni DOPO che UI esiste
        self.load_settings()
        
    def setup_ui(self):
        self.setWindowTitle("🖼️ Background Remover")
        self.setMinimumSize(700, 500)
        
        central = QWidget()
        self.setCentralWidget(central)
        
        main = QVBoxLayout(central)
        main.setSpacing(8)
        main.setContentsMargins(10, 10, 10, 10)
        
        # Header
        hdr = QLabel("🖼️ Background Remover")
        f = QFont()
        f.setPointSize(16)
        f.setBold(True)
        hdr.setFont(f)
        hdr.setAlignment(Qt.AlignCenter)
        main.addWidget(hdr)
        
        # Splitter
        split = QSplitter(Qt.Vertical)
        main.addWidget(split, 1)
        
        # === SUPERIORE ===
        top = QWidget()
        top_l = QHBoxLayout(top)
        top_l.setSpacing(8)
        
        # Immagini
        box_img = QGroupBox("📂 Immagini")
        v_img = QVBoxLayout(box_img)
        
        btn_sel = QPushButton("📁 Seleziona")
        btn_sel.setMinimumHeight(35)
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
        
        # Opzioni
        box_set = QGroupBox("⚙️ Opzioni")
        v_set = QVBoxLayout(box_set)
        
        btn_out = QPushButton("📂 Cartella Output")
        btn_out.setMinimumHeight(30)
        btn_out.clicked.connect(self.on_output)
        v_set.addWidget(btn_out)
        
        # lbl_out CREATO QUI
        self.lbl_out = QLabel("Non selezionata")
        self.lbl_out.setWordWrap(True)
        v_set.addWidget(self.lbl_out)
        
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
        
        # === INFERIORE ===
        bot = QWidget()
        bot_l = QVBoxLayout(bot)
        bot_l.setSpacing(6)
        
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
        
        # QPlainTextEdit invece di QTextEdit per setMaximumBlockCount
        self.log_txt = QPlainTextEdit()
        self.log_txt.setReadOnly(True)
        self.log_txt.setMaximumBlockCount(100)  # Ora funziona!
        v_log.addWidget(self.log_txt)
        
        bot_l.addWidget(box_log)
        
        # btn_go CREATO QUI
        self.btn_go = QPushButton("🚀 AVVIA")
        self.btn_go.setMinimumHeight(40)
        self.btn_go.setFont(QFont("Arial", 10, QFont.Bold))
        self.btn_go.clicked.connect(self.on_start)
        self.btn_go.setEnabled(False)
        bot_l.addWidget(self.btn_go)
        
        split.addWidget(bot)
        split.setSizes([180, 250])
        
        # Status
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
        
        # Stili minimali
        self.setStyleSheet("""
            QMainWindow { background: #f0f0f0; }
            QGroupBox { font-weight: bold; border: 1px solid #bbb; border-radius: 3px; margin-top: 5px; padding-top: 5px; background: white; }
            QGroupBox::title { subcontrol-origin: margin; left: 5px; padding: 0 2px; }
            QPushButton { background: #e0e0e0; border: 1px solid #aaa; border-radius: 3px; padding: 4px; font-weight: bold; }
            QPushButton:hover { background: #d5d5d5; }
            QPushButton:disabled { background: #f0f0f0; color: #999; }
            QListWidget { border: 1px solid #ccc; background: #fafafa; }
            QProgressBar { border: 1px solid #ccc; text-align: center; }
            QProgressBar::chunk { background: #4CAF50; }
            QPlainTextEdit { border: 1px solid #ccc; background: #2d2d2d; color: #eee; font-family: Consolas; font-size: 9px; }
        """)
        
    def load_settings(self):
        """DOPO che UI esiste"""
        saved = self.settings.value("output_dir", "")
        if saved:
            self.output_dir = str(saved)
            disp = self.output_dir[:20] + "..." if len(self.output_dir) > 20 else self.output_dir
            self.lbl_out.setText(f"📁 {disp}")
        
    def save_settings(self):
        self.settings.setValue("output_dir", self.output_dir)
        
    def on_select(self):
        try:
            files, _ = QFileDialog.getOpenFileNames(
                self, "Seleziona", "", 
                "Immagini (*.png *.jpg *.jpeg *.bmp *.tiff *.webp)"
            )
            if files:
                valid = [f for f in files if Path(f).suffix.lower() in 
                        {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp'}]
                self.input_files = valid
                self.update_list()
                self.add_log(f"📂 {len(valid)} img")
                self.check_ready()
        except Exception as e:
            QMessageBox.critical(self, "Errore", str(e))
            
    def update_list(self):
        self.list_files.clear()
        for f in self.input_files:
            self.list_files.addItem(f"📷 {os.path.basename(f)}")
        self.lbl_count.setText(f"{len(self.input_files)} img")
        
    def on_clear(self):
        self.input_files = []
        self.list_files.clear()
        self.lbl_count.setText("0 img")
        self.check_ready()
        self.add_log("🗑️ Svuotato")
        
    def on_output(self):
        try:
            d = QFileDialog.getExistingDirectory(self, "Output", str(Path.home()))
            if d:
                self.output_dir = d
                disp = d[:20] + "..." if len(d) > 20 else d
                self.lbl_out.setText(f"📁 {disp}")
                self.save_settings()
                self.check_ready()
                self.add_log(f"📂 {d}")
        except Exception as e:
            QMessageBox.critical(self, "Errore", str(e))
            
    def check_ready(self):
        # BOOL esplicito
        has_f = len(self.input_files) > 0
        has_d = bool(self.output_dir) and self.output_dir != ""
        ready = bool(has_f and has_d)
        
        self.btn_go.setEnabled(ready)
        
        if ready:
            self.status.showMessage(f"✅ {len(self.input_files)} img pronte")
        else:
            self.status.showMessage("⏳ Seleziona img e cartella")
            
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
            QMessageBox.critical(self, "Errore", f"Avvio: {str(e)}")
            self.btn_go.setEnabled(True)
            self.btn_go.setText("🚀 AVVIA")
            
    def on_progress(self, curr, tot, name):
        self.prog.setValue(curr)
        self.lbl_curr.setText(f"{name[:15]} ({curr}/{tot})")
        
    def on_file_done(self, name, ok, msg):
        for i in range(self.list_files.count()):
            item = self.list_files.item(i)
            if name in item.text():
                icon = "✅" if ok else "❌"
                item.setText(f"{icon} {name[:20]}")
                break
                
    def on_finish(self, ok, err):
        self.btn_go.setEnabled(True)
        self.btn_go.setText("🚀 AVVIA")
        self.lbl_curr.setText("Finito")
        
        QMessageBox.information(self, "Finito", f"✅ OK: {ok}\n❌ Err: {err}")
        self.status.showMessage(f"🏁 OK:{ok} Err:{err}")
        
    def add_log(self, msg):
        t = datetime.now().strftime("%H:%M:%S")
        self.log_txt.appendPlainText(f"[{t}] {msg}")
        # Scroll
        sb = self.log_txt.verticalScrollBar()
        sb.setValue(sb.maximum())
        
    def show_about(self):
        AboutDialog(self).exec_()
        
    def closeEvent(self, event):
        if self.thread and self.thread.isRunning():
            r = QMessageBox.question(self, "Uscire?", "Interrompere?")
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
    # Ottimizzazioni velocità
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
