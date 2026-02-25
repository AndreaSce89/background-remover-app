#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Background Remover App - Batch Image Background Removal Tool
Applicazione desktop per rimozione massiva sfondi immagini
"""

import sys
import os
import threading
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem, QFileDialog,
    QProgressBar, QTextEdit, QGroupBox, QSpinBox, QCheckBox,
    QMessageBox, QSplitter, QFrame, QStatusBar, QMenuBar, QAction,
    QDialog, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings
from PyQt5.QtGui import QIcon, QFont, QPalette, QColor

# Import utils
from utils.image_processor import BackgroundRemover
from utils.file_handler import FileHandler


class ProcessingThread(QThread):
    """Thread per l'elaborazione delle immagini senza bloccare la UI"""
    progress_updated = pyqtSignal(int, int, str)  # current, total, filename
    file_processed = pyqtSignal(str, bool, str)   # filename, success, message
    processing_finished = pyqtSignal(int, int)    # success_count, error_count
    log_message = pyqtSignal(str)
    
    def __init__(self, file_paths, output_dir, quality=100, overwrite=False):
        super().__init__()
        self.file_paths = file_paths
        self.output_dir = output_dir
        self.quality = quality
        self.overwrite = overwrite
        self.is_running = True
        self.remover = BackgroundRemover()
        
    def run(self):
        """Elabora tutte le immagini"""
        total = len(self.file_paths)
        success_count = 0
        error_count = 0
        
        self.log_message.emit(f"🚀 Avvio elaborazione di {total} immagini...")
        self.log_message.emit(f"📁 Cartella output: {self.output_dir}")
        self.log_message.emit(f"⚙️ Qualità: {self.quality}% | Sovrascrivi: {'Sì' if self.overwrite else 'No'}")
        self.log_message.emit("-" * 50)
        
        for idx, file_path in enumerate(self.file_paths, 1):
            if not self.is_running:
                self.log_message.emit("⚠️ Elaborazione interrotta dall'utente")
                break
                
            filename = os.path.basename(file_path)
            self.progress_updated.emit(idx, total, filename)
            
            try:
                # Verifica file esistente
                output_path = os.path.join(
                    self.output_dir, 
                    f"{Path(filename).stem}_nobg.png"
                )
                
                if os.path.exists(output_path) and not self.overwrite:
                    self.file_processed.emit(filename, True, "Saltato (file esistente)")
                    self.log_message.emit(f"⏭️  [{idx}/{total}] {filename} - Saltato (esiste già)")
                    continue
                
                # Processa immagine
                self.log_message.emit(f"🔄 [{idx}/{total}] Elaborazione: {filename}...")
                success = self.remover.remove_background(file_path, output_path, self.quality)
                
                if success:
                    success_count += 1
                    self.file_processed.emit(filename, True, "Completato")
                    self.log_message.emit(f"✅ [{idx}/{total}] {filename} - Completato")
                else:
                    error_count += 1
                    self.file_processed.emit(filename, False, "Errore elaborazione")
                    self.log_message.emit(f"❌ [{idx}/{total}] {filename} - Errore")
                    
            except Exception as e:
                error_count += 1
                self.file_processed.emit(filename, False, str(e))
                self.log_message.emit(f"❌ [{idx}/{total}] {filename} - Errore: {str(e)}")
        
        self.log_message.emit("-" * 50)
        self.log_message.emit(f"🏁 Completato! Successi: {success_count} | Errori: {error_count}")
        self.processing_finished.emit(success_count, error_count)
    
    def stop(self):
        self.is_running = False


class AboutDialog(QDialog):
    """Dialog Informazioni"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Informazioni")
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout(self)
        
        title = QLabel("🖼️ Background Remover App")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        info_text = """
        <p style='text-align: center;'>
        <b>Versione:</b> 1.0.0<br><br>
        <b>Descrizione:</b><br>
        Tool desktop per la rimozione massiva degli sfondi<br>
        dalle immagini utilizzando AI locale (U2Net).<br><br>
        <b>Tecnologie:</b><br>
        • Python 3.8+<br>
        • PyQt5<br>
        • rembg (U2Net)<br>
        • Pillow<br><br>
        <b>Licenza:</b> MIT<br>
        <b>Autore:</b> AI Assistant
        </p>
        """
        info = QLabel(info_text)
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class MainWindow(QMainWindow):
    """Finestra principale dell'applicazione"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🖼️ Background Remover - Batch Processing")
        self.setMinimumSize(900, 700)
        
        # Settings
        self.settings = QSettings("BackgroundRemover", "App")
        self.input_files = []
        self.output_dir = ""
        self.processing_thread = None
        
        # Carica impostazioni salvate
        self.load_settings()
        
        # Setup UI
        self.setup_ui()
        self.apply_styles()
        
    def setup_ui(self):
        """Configura l'interfaccia utente"""
        # Widget centrale
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principale
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # === HEADER ===
        header = QLabel("🖼️ Background Remover")
        header_font = QFont()
        header_font.setPointSize(24)
        header_font.setBold(True)
        header.setFont(header_font)
        header.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header)
        
        subtitle = QLabel("Rimozione massiva sfondi immagini con AI locale")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #666; font-size: 12px; margin-bottom: 10px;")
        main_layout.addWidget(subtitle)
        
        # === SPLITTER ===
        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter, 1)
        
        # === PANELLO SUPERIORE: Input ===
        top_panel = QWidget()
        top_layout = QHBoxLayout(top_panel)
        top_layout.setSpacing(15)
        
        # Gruppo Selezione File
        input_group = QGroupBox("📂 Selezione Immagini")
        input_layout = QVBoxLayout(input_group)
        
        btn_select = QPushButton("📁 Seleziona Immagini")
        btn_select.setObjectName("primaryButton")
        btn_select.setMinimumHeight(50)
        btn_select.clicked.connect(self.select_images)
        input_layout.addWidget(btn_select)
        
        self.lbl_image_count = QLabel("Nessuna immagine selezionata")
        self.lbl_image_count.setAlignment(Qt.AlignCenter)
        self.lbl_image_count.setStyleSheet("color: #666; padding: 10px;")
        input_layout.addWidget(self.lbl_image_count)
        
        # Lista immagini
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        input_layout.addWidget(self.list_widget)
        
        btn_clear = QPushButton("🗑️ Svuota Lista")
        btn_clear.clicked.connect(self.clear_list)
        input_layout.addWidget(btn_clear)
        
        top_layout.addWidget(input_group, 1)
        
        # Gruppo Output e Impostazioni
        settings_group = QGroupBox("⚙️ Impostazioni Output")
        settings_layout = QVBoxLayout(settings_group)
        
        # Cartella output
        btn_output = QPushButton("📂 Seleziona Cartella Output")
        btn_output.setMinimumHeight(40)
        btn_output.clicked.connect(self.select_output_dir)
        settings_layout.addWidget(btn_output)
        
        self.lbl_output_dir = QLabel("Non selezionata")
        self.lbl_output_dir.setWordWrap(True)
        self.lbl_output_dir.setStyleSheet("color: #666; padding: 5px;")
        settings_layout.addWidget(self.lbl_output_dir)
        
        settings_layout.addSpacing(20)
        
        # Qualità
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("Qualità PNG:"))
        self.spin_quality = QSpinBox()
        self.spin_quality.setRange(1, 100)
        self.spin_quality.setValue(95)
        self.spin_quality.setSuffix("%")
        quality_layout.addWidget(self.spin_quality)
        quality_layout.addStretch()
        settings_layout.addLayout(quality_layout)
        
        # Sovrascrivi
        self.chk_overwrite = QCheckBox("Sovrascrivi file esistenti")
        self.chk_overwrite.setChecked(False)
        settings_layout.addWidget(self.chk_overwrite)
        
        settings_layout.addStretch()
        
        # Info modello
        model_info = QLabel("🤖 Modello: U2Net (Locale)")
        model_info.setStyleSheet("color: #2ecc71; font-weight: bold;")
        model_info.setAlignment(Qt.AlignCenter)
        settings_layout.addWidget(model_info)
        
        top_layout.addWidget(settings_group, 1)
        
        splitter.addWidget(top_panel)
        
        # === PANELLO INFERIORE: Log e Progresso ===
        bottom_panel = QWidget()
        bottom_layout = QVBoxLayout(bottom_panel)
        bottom_layout.setSpacing(10)
        
        # Barra progresso
        progress_group = QGroupBox("📊 Avanzamento")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(30)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% - %v/%m")
        progress_layout.addWidget(self.progress_bar)
        
        self.lbl_current = QLabel("Pronto")
        self.lbl_current.setAlignment(Qt.AlignCenter)
        progress_layout.addWidget(self.lbl_current)
        
        bottom_layout.addWidget(progress_group)
        
        # Log
        log_group = QGroupBox("📝 Log Operazioni")
        log_layout = QVBoxLayout(log_group)
        
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setLineWrapMode(QTextEdit.WidgetWidth)
        log_layout.addWidget(self.txt_log)
        
        bottom_layout.addWidget(log_group)
        
        # Pulsante Avvia
        self.btn_start = QPushButton("🚀 AVVIA ELABORAZIONE")
        self.btn_start.setObjectName("startButton")
        self.btn_start.setMinimumHeight(60)
        self.btn_start.setFont(QFont("Arial", 12, QFont.Bold))
        self.btn_start.clicked.connect(self.start_processing)
        self.btn_start.setEnabled(False)
        bottom_layout.addWidget(self.btn_start)
        
        splitter.addWidget(bottom_panel)
        splitter.setSizes([300, 400])
        
        # === STATUS BAR ===
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Pronto")
        
        # === MENU ===
        self.setup_menu()
        
    def setup_menu(self):
        """Configura il menu"""
        menubar = self.menuBar()
        
        # Menu File
        file_menu = menubar.addMenu("File")
        
        action_open = QAction("📁 Apri Immagini", self)
        action_open.setShortcut("Ctrl+O")
        action_open.triggered.connect(self.select_images)
        file_menu.addAction(action_open)
        
        action_output = QAction("📂 Seleziona Output", self)
        action_output.triggered.connect(self.select_output_dir)
        file_menu.addAction(action_output)
        
        file_menu.addSeparator()
        
        action_exit = QAction("❌ Esci", self)
        action_exit.setShortcut("Ctrl+Q")
        action_exit.triggered.connect(self.close)
        file_menu.addAction(action_exit)
        
        # Menu Aiuto
        help_menu = menubar.addMenu("Aiuto")
        
        action_about = QAction("ℹ️ Informazioni", self)
        action_about.triggered.connect(self.show_about)
        help_menu.addAction(action_about)
        
    def apply_styles(self):
        """Applica stili CSS moderni"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f6fa;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dcdde1;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: white;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #2c3e50;
            }
            
            QPushButton {
                background-color: #ecf0f1;
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                color: #2c3e50;
            }
            
            QPushButton:hover {
                background-color: #d5dbdb;
                border-color: #95a5a6;
            }
            
            QPushButton:pressed {
                background-color: #bdc3c7;
            }
            
            QPushButton:disabled {
                background-color: #ecf0f1;
                color: #95a5a6;
                border-color: #dcdde1;
            }
            
            QPushButton#primaryButton {
                background-color: #3498db;
                color: white;
                border-color: #2980b9;
                font-size: 14px;
            }
            
            QPushButton#primaryButton:hover {
                background-color: #2980b9;
            }
            
            QPushButton#startButton {
                background-color: #27ae60;
                color: white;
                border-color: #229954;
                font-size: 16px;
            }
            
            QPushButton#startButton:hover {
                background-color: #229954;
            }
            
            QPushButton#startButton:disabled {
                background-color: #95a5a6;
                border-color: #7f8c8d;
            }
            
            QListWidget {
                border: 2px solid #dcdde1;
                border-radius: 6px;
                padding: 5px;
                background-color: #fafafa;
                alternate-background-color: #f0f0f0;
            }
            
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #eee;
            }
            
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            
            QProgressBar {
                border: 2px solid #dcdde1;
                border-radius: 6px;
                text-align: center;
                font-weight: bold;
            }
            
            QProgressBar::chunk {
                background-color: #27ae60;
                border-radius: 4px;
            }
            
            QTextEdit {
                border: 2px solid #dcdde1;
                border-radius: 6px;
                padding: 10px;
                background-color: #2c3e50;
                color: #ecf0f1;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
            }
            
            QSpinBox {
                padding: 5px;
                border: 2px solid #dcdde1;
                border-radius: 4px;
            }
            
            QCheckBox {
                spacing: 8px;
            }
            
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            
            QLabel {
                color: #2c3e50;
            }
            
            QMenuBar {
                background-color: #f5f6fa;
                border-bottom: 1px solid #dcdde1;
            }
            
            QMenuBar::item:selected {
                background-color: #3498db;
                color: white;
            }
            
            QStatusBar {
                background-color: #34495e;
                color: white;
                padding: 5px;
            }
        """)
        
    def load_settings(self):
        """Carica impostazioni salvate"""
        self.output_dir = self.settings.value("output_dir", "")
        
    def save_settings(self):
        """Salva impostazioni"""
        self.settings.setValue("output_dir", self.output_dir)
        
    def select_images(self):
        """Apre dialog selezione multipla immagini"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Seleziona Immagini",
            "",
            "Immagini (*.png *.jpg *.jpeg *.bmp *.tiff *.webp);;Tutti i file (*.*)"
        )
        
        if files:
            self.input_files = files
            self.update_file_list()
            self.log(f"📂 Caricate {len(files)} immagini")
            self.check_ready()
            
    def update_file_list(self):
        """Aggiorna la lista visibile"""
        self.list_widget.clear()
        for file_path in self.input_files:
            item = QListWidgetItem(f"📷 {os.path.basename(file_path)}")
            item.setToolTip(file_path)
            self.list_widget.addItem(item)
            
        self.lbl_image_count.setText(f"🖼️ {len(self.input_files)} immagini selezionate")
        
    def clear_list(self):
        """Svuota la lista"""
        self.input_files = []
        self.list_widget.clear()
        self.lbl_image_count.setText("Nessuna immagine selezionata")
        self.check_ready()
        self.log("🗑️ Lista svuotata")
        
    def select_output_dir(self):
        """Seleziona cartella output"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Seleziona Cartella Output",
            self.output_dir or os.path.expanduser("~")
        )
        
        if dir_path:
            self.output_dir = dir_path
            self.lbl_output_dir.setText(f"📁 {dir_path}")
            self.save_settings()
            self.check_ready()
            self.log(f"📂 Output impostato: {dir_path}")
            
    def check_ready(self):
        """Verifica se pronto per elaborazione"""
        ready = len(self.input_files) > 0 and self.output_dir
        self.btn_start.setEnabled(ready)
        
        if ready:
            self.status_bar.showMessage(f"✅ Pronto: {len(self.input_files)} immagini → {self.output_dir}")
        else:
            self.status_bar.showMessage("⏳ Seleziona immagini e cartella output")
            
    def start_processing(self):
        """Avvia elaborazione"""
        if not self.input_files or not self.output_dir:
            QMessageBox.warning(self, "Attenzione", "Seleziona immagini e cartella output!")
            return
            
        # Disabilita controlli
        self.btn_start.setEnabled(False)
        self.btn_start.setText("⏳ ELABORAZIONE IN CORSO...")
        
        # Reset progresso
        self.progress_bar.setMaximum(len(self.input_files))
        self.progress_bar.setValue(0)
        
        # Avvia thread
        self.processing_thread = ProcessingThread(
            self.input_files,
            self.output_dir,
            self.spin_quality.value(),
            self.chk_overwrite.isChecked()
        )
        
        self.processing_thread.progress_updated.connect(self.update_progress)
        self.processing_thread.file_processed.connect(self.on_file_processed)
        self.processing_thread.processing_finished.connect(self.on_finished)
        self.processing_thread.log_message.connect(self.log)
        
        self.processing_thread.start()
        
    def update_progress(self, current, total, filename):
        """Aggiorna barra progresso"""
        self.progress_bar.setValue(current)
        self.lbl_current.setText(f"🔄 {filename} ({current}/{total})")
        
    def on_file_processed(self, filename, success, message):
        """Callback file processato"""
        # Aggiorna lista visivamente
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if filename in item.text():
                icon = "✅" if success else "❌"
                item.setText(f"{icon} {filename} - {message}")
                break
                
    def on_finished(self, success_count, error_count):
        """Callback elaborazione completata"""
        self.btn_start.setEnabled(True)
        self.btn_start.setText("🚀 AVVIA ELABORAZIONE")
        self.lbl_current.setText("✅ Completato")
        
        # Messaggio riepilogo
        msg = QMessageBox(self)
        msg.setWindowTitle("Elaborazione Completata")
        msg.setIcon(QMessageBox.Information)
        msg.setText(f"<b>Elaborazione completata!</b><br><br>"
                   f"✅ Successi: {success_count}<br>"
                   f"❌ Errori: {error_count}")
        msg.exec_()
        
        self.status_bar.showMessage(f"🏁 Completato: {success_count} successi, {error_count} errori")
        
    def log(self, message):
        """Aggiunge messaggio al log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.txt_log.append(f"[{timestamp}] {message}")
        # Scrolla in fondo
        scrollbar = self.txt_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def show_about(self):
        """Mostra dialog informazioni"""
        dialog = AboutDialog(self)
        dialog.exec_()
        
    def closeEvent(self, event):
        """Gestisce chiusura applicazione"""
        if self.processing_thread and self.processing_thread.isRunning():
            reply = QMessageBox.question(
                self, "Conferma",
                "Elaborazione in corso. Vuoi interrompere e uscire?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.processing_thread.stop()
                self.processing_thread.wait(2000)
                event.accept()
            else:
                event.ignore()
        else:
            self.save_settings()
            event.accept()


def main():
    """Entry point"""
    # Fix per PyQt su Windows
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName("Background Remover")
    app.setApplicationVersion("1.0.0")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
