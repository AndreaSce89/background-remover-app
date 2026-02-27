#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Background Remover Pro v3.4 - FIX TEMP + SPOSTAMENTO
Elabora in cartella temporanea, poi sposta nella destinazione scelta
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

# Fix path PyInstaller
if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
else:
    bundle_dir = os.path.dirname(os.path.abspath(__file__))

if bundle_dir not in sys.path:
    sys.path.insert(0, bundle_dir)

# Logger
from logger import get_logger
logger = get_logger()

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QListWidget,
    QProgressBar, QMessageBox, QSpinBox, QGroupBox, QTextEdit,
    QListWidgetItem, QMenu, QAction, QAbstractItemView
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QMetaObject, Q_ARG
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QFont, QPixmap

# Nascondi console
if sys.platform == 'win32':
    try:
        import ctypes
        ctypes.windll.kernel32.FreeConsole()
    except:
        pass


# =============================================================================
# FORMATI SUPPORTATI
# =============================================================================
SUPPORTED_FORMATS = (
    '.png', '.jpg', '.jpeg', '.jpe', '.jfif',
    '.bmp', '.dib', '.gif', '.tiff', '.tif',
    '.webp', '.raw', '.arw', '.cr2', '.nrw',
    '.k25', '.nef', '.orf', '.raf', '.rw2',
    '.sr2', '.srf', '.srw', '.x3f', '.dng',
    '.pef', '.ptx', '.pxn', '.r3d', '.3fr',
    '.erf', '.mef', '.mos', '.qtk', '.rdc'
)


class WorkerThread(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int, str)
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str, str)
    
    def __init__(self, file_paths, output_dir, quality):
        super().__init__()
        self.file_paths = file_paths
        self.output_dir = output_dir
        self.quality = quality
        self._is_running = True
        
    def run(self):
        try:
            from utils.image_processor import BackgroundRemover
            
            self.log_signal.emit("🧠 Inizializzazione AI...")
            try:
                remover = BackgroundRemover()
                self.log_signal.emit("✅ AI Pronta!")
            except Exception as e:
                logger.error("AI init failed", e)
                self.error_signal.emit("Errore AI", str(e))
                self.finished_signal.emit({'error': True, 'message': str(e)})
                return
            
            def progress_cb(current, total, filename):
                if not self._is_running:
                    raise InterruptedError
                self.progress_signal.emit(current, total, filename)
                self.log_signal.emit(f"🔄 [{current}/{total}] {filename}")
            
            stats = remover.batch_process(
                self.file_paths,
                self.output_dir,
                self.quality,
                callback=progress_cb
            )
            
            self.finished_signal.emit(stats)
            
        except InterruptedError:
            self.finished_signal.emit({'interrupted': True})
        except Exception as e:
            logger.error("Worker error", e)
            self.error_signal.emit("Errore", str(e))
            self.finished_signal.emit({'error': True, 'message': str(e)})
    
    def stop(self):
        self._is_running = False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Background Remover Pro v3.4")
        self.setMinimumSize(1100, 850)
        
        self.files_list = []
        self.worker = None
        
        self.setup_ui()
        
        logger.info("=" * 70)
        logger.info("APPLICAZIONE AVVIATA v3.4")
        logger.info("=" * 70)
        
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # HEADER
        header = QLabel("🖼️ Background Remover Pro")
        header.setFont(QFont("Segoe UI", 22, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("color: #4CAF50; margin-bottom: 15px;")
        layout.addWidget(header)
        
        # =================================================================
        # SEZIONE INPUT
        # =================================================================
        in_group = QGroupBox("📂 Seleziona Immagini")
        in_layout = QVBoxLayout()
        
        path_layout = QHBoxLayout()
        self.in_edit = QLineEdit()
        self.in_edit.setPlaceholderText("Clicca 'Sfoglia Cartella' o 'Aggiungi File'...")
        self.in_edit.setReadOnly(True)
        self.in_edit.setMinimumHeight(35)
        
        btn_folder = QPushButton("📁 Cartella")
        btn_folder.setToolTip("Carica TUTTE le immagini da una cartella")
        btn_folder.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 8px;")
        btn_folder.clicked.connect(self.browse_folder)
        
        btn_files = QPushButton("📄 File")
        btn_files.setToolTip("Aggiungi singole immagini")
        btn_files.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; padding: 8px;")
        btn_files.clicked.connect(self.browse_files)
        
        btn_clear_in = QPushButton("🗑️")
        btn_clear_in.setToolTip("Pulisci lista")
        btn_clear_in.setStyleSheet("background-color: #f44336; color: white;")
        btn_clear_in.setMaximumWidth(50)
        btn_clear_in.clicked.connect(self.clear_all)
        
        path_layout.addWidget(self.in_edit, stretch=1)
        path_layout.addWidget(btn_folder)
        path_layout.addWidget(btn_files)
        path_layout.addWidget(btn_clear_in)
        
        in_layout.addLayout(path_layout)
        
        formats_label = QLabel(
            f"Formati supportati: {', '.join(SUPPORTED_FORMATS[:8])}... "
            f"(e altri {len(SUPPORTED_FORMATS)-8} formati)"
        )
        formats_label.setStyleSheet("color: #666; font-size: 10px;")
        formats_label.setWordWrap(True)
        in_layout.addWidget(formats_label)
        
        in_group.setLayout(in_layout)
        layout.addWidget(in_group)
        
        # =================================================================
        # LISTA FILE
        # =================================================================
        list_group = QGroupBox(f"📋 File caricati (0)")
        list_layout = QVBoxLayout()
        
        self.list_widget = QListWidget()
        self.list_widget.setMinimumHeight(200)
        self.list_widget.setMaximumHeight(300)
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        
        self.list_widget.setStyleSheet("""
            QListWidget {
                border: 2px solid #ddd;
                border-radius: 8px;
                background-color: #fafafa;
                alternate-background-color: #f0f0f0;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #4CAF50;
                color: white;
            }
        """)
        self.list_widget.setAlternatingRowColors(True)
        
        self.list_widget.setAcceptDrops(True)
        self.list_widget.dragEnterEvent = self.drag_enter
        self.list_widget.dragMoveEvent = self.drag_move
        self.list_widget.dropEvent = self.drop
        
        list_layout.addWidget(self.list_widget)
        
        list_btn_layout = QHBoxLayout()
        
        btn_remove_sel = QPushButton("❌ Rimuovi selezionati")
        btn_remove_sel.clicked.connect(self.remove_selected)
        
        btn_preview = QPushButton("👁️ Anteprima")
        btn_preview.clicked.connect(self.preview_selected)
        
        self.list_count_label = QLabel("0 file selezionati")
        self.list_count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        list_btn_layout.addWidget(btn_remove_sel)
        list_btn_layout.addWidget(btn_preview)
        list_btn_layout.addStretch()
        list_btn_layout.addWidget(self.list_count_label)
        
        list_layout.addLayout(list_btn_layout)
        list_group.setLayout(list_layout)
        self.list_group = list_group
        layout.addWidget(list_group)
        
        # =================================================================
        # OUTPUT
        # =================================================================
        out_group = QGroupBox("💾 Cartella Output")
        out_layout = QHBoxLayout()
        
        self.out_edit = QLineEdit()
        self.out_edit.setPlaceholderText("Lascia vuoto per creare sottocartella 'nobg_output' vicino alle immagini...")
        
        btn_out = QPushButton("Sfoglia...")
        btn_out.setStyleSheet("background-color: #2196F3; color: white;")
        btn_out.clicked.connect(self.browse_output)
        
        btn_auto = QPushButton("🔄 Auto")
        btn_auto.setToolTip("Genera automaticamente vicino all'input")
        btn_auto.clicked.connect(self.auto_output)
        
        out_layout.addWidget(self.out_edit, stretch=1)
        out_layout.addWidget(btn_out)
        out_layout.addWidget(btn_auto)
        
        out_group.setLayout(out_layout)
        layout.addWidget(out_group)
        
        # =================================================================
        # IMPOSTAZIONI
        # =================================================================
        settings_layout = QHBoxLayout()
        
        qual_group = QGroupBox("⚙️ Qualità")
        qual_layout = QHBoxLayout()
        self.qual_spin = QSpinBox()
        self.qual_spin.setRange(10, 100)
        self.qual_spin.setValue(95)
        self.qual_spin.setSuffix("%")
        self.qual_spin.setMinimumWidth(80)
        qual_layout.addWidget(self.qual_spin)
        qual_group.setLayout(qual_layout)
        settings_layout.addWidget(qual_group)
        
        info_group = QGroupBox("ℹ️ Stato")
        info_layout = QHBoxLayout()
        self.status_label = QLabel("Pronto - carica immagini")
        self.status_label.setStyleSheet("color: #666;")
        info_layout.addWidget(self.status_label)
        info_group.setLayout(info_layout)
        settings_layout.addWidget(info_group, stretch=1)
        
        layout.addLayout(settings_layout)
        
        # =================================================================
        # PROGRESSO
        # =================================================================
        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.setFormat("Pronto")
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #4CAF50;
                border-radius: 6px;
                text-align: center;
                height: 30px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        layout.addWidget(self.progress)
        
        # =================================================================
        # LOG
        # =================================================================
        log_group = QGroupBox("📜 Log operazioni")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', monospace;
                font-size: 10px;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # =================================================================
        # BOTTONI PRINCIPALI
        # =================================================================
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶️ AVVIA ELABORAZIONE")
        self.start_btn.setMinimumHeight(55)
        self.start_btn.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        self.start_btn.clicked.connect(self.start_processing)
        
        btn_open_log = QPushButton("📁 Apri Log")
        btn_open_log.setMinimumHeight(55)
        btn_open_log.setStyleSheet("background-color: #FF9800; color: white;")
        btn_open_log.clicked.connect(self.open_log)
        
        btn_help = QPushButton("❓ Aiuto")
        btn_help.setMinimumHeight(55)
        btn_help.setStyleSheet("background-color: #9C27B0; color: white;")
        btn_help.clicked.connect(self.show_help)
        
        btn_layout.addWidget(self.start_btn, stretch=2)
        btn_layout.addWidget(btn_open_log)
        btn_layout.addWidget(btn_help)
        layout.addLayout(btn_layout)
        
        footer = QLabel(f"💡 Log: {logger.get_log_path()}")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: #888; font-size: 10px; margin-top: 5px;")
        layout.addWidget(footer)
        
    # =================================================================
    # DRAG & DROP
    # =================================================================
    def drag_enter(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def drag_move(self, event):
        event.acceptProposedAction()
    
    def drop(self, event):
        added = 0
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                added += self.add_folder_files(path)
            elif self.is_image_file(path):
                self.add_single_file(path)
                added += 1
        
        self.update_list_display()
        self.log(f"📥 Aggiunti {added} file da drag & drop")
    
    # =================================================================
    # GESTIONE FILE
    # =================================================================
    def is_image_file(self, path):
        ext = os.path.splitext(path)[1].lower()
        return ext in SUPPORTED_FORMATS and os.path.isfile(path)
    
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, 
            "Seleziona cartella con immagini"
        )
        if folder:
            folder = os.path.normpath(folder)
            count = self.add_folder_files(folder)
            if count > 0:
                self.in_edit.setText(f"📁 {folder[:50]}...")
                self.auto_output()
            else:
                QMessageBox.information(
                    self,
                    "Nessuna immagine",
                    f"Nessuna immagine trovata in:\n{folder}"
                )
    
    def browse_files(self):
        filter_str = "Immagini (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp);;Tutti i file (*.*)"
        
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Seleziona immagini",
            "",
            filter_str
        )
        
        if files:
            added = 0
            for f in files:
                f = os.path.normpath(f)
                if self.is_image_file(f):
                    if f not in self.files_list:
                        self.files_list.append(f)
                        added += 1
            
            self.update_list_display()
            self.log(f"📎 Aggiunti {added} file singoli")
            
            if self.files_list and not self.out_edit.text():
                self.auto_output()
    
    def add_folder_files(self, folder):
        count = 0
        try:
            for entry in os.scandir(folder):
                if entry.is_file() and self.is_image_file(entry.path):
                    if entry.path not in self.files_list:
                        self.files_list.append(entry.path)
                        count += 1
        except Exception as e:
            self.show_error("Errore lettura cartella", str(e))
            return 0
        
        self.update_list_display()
        self.log(f"📂 Cartella: {folder}")
        self.log(f"   Trovate: {count} immagini")
        return count
    
    def add_single_file(self, path):
        if path not in self.files_list and self.is_image_file(path):
            self.files_list.append(path)
            return True
        return False
    
    def update_list_display(self):
        self.list_widget.clear()
        
        for i, path in enumerate(self.files_list, 1):
            filename = os.path.basename(path)
            item = QListWidgetItem(f"{i:3d}. 📄 {filename}")
            item.setToolTip(path)
            item.setData(Qt.UserRole, path)
            self.list_widget.addItem(item)
        
        count = len(self.files_list)
        self.list_group.setTitle(f"📋 File caricati ({count})")
        self.status_label.setText(f"{count} file pronti")
        self.update_selection_count()
        self.start_btn.setEnabled(count > 0)
    
    def update_selection_count(self):
        selected = len(self.list_widget.selectedItems())
        self.list_count_label.setText(f"{selected}/{len(self.files_list)} selezionati")
    
    def remove_selected(self):
        selected = self.list_widget.selectedItems()
        if not selected:
            return
        
        for item in selected:
            path = item.data(Qt.UserRole)
            if path in self.files_list:
                self.files_list.remove(path)
        
        self.update_list_display()
        self.log(f"🗑️ Rimossi {len(selected)} file")
    
    def clear_all(self):
        self.files_list.clear()
        self.list_widget.clear()
        self.log_text.clear()
        self.in_edit.clear()
        self.out_edit.clear()
        
        self.progress.setValue(0)
        self.progress.setMaximum(100)
        self.progress.setFormat("Pronto")
        
        self.status_label.setText("Pronto - carica immagini")
        self.start_btn.setEnabled(False)
        self.start_btn.setText("▶️ AVVIA ELABORAZIONE")
        self.list_group.setTitle("📋 File caricati (0)")
        self.list_count_label.setText("0 file selezionati")
        
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(1000)
        
        logger.info("Pulizia completa")
    
    def preview_selected(self):
        selected = self.list_widget.selectedItems()
        if not selected:
            QMessageBox.information(self, "Anteprima", "Seleziona un'immagine")
            return
        
        path = selected[0].data(Qt.UserRole)
        
        from PyQt5.QtWidgets import QDialog, QVBoxLayout
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Anteprima: {os.path.basename(path)}")
        dialog.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(dialog)
        label = QLabel()
        pixmap = QPixmap(path)
        
        if pixmap.width() > 780 or pixmap.height() > 580:
            pixmap = pixmap.scaled(780, 580, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        info = QLabel(f"Dimensioni: {pixmap.width()}x{pixmap.height()}")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)
        
        dialog.exec_()
    
    def show_context_menu(self, position):
        menu = QMenu()
        
        remove_action = QAction("❌ Rimuovi", self)
        remove_action.triggered.connect(self.remove_selected)
        menu.addAction(remove_action)
        
        preview_action = QAction("👁️ Anteprima", self)
        preview_action.triggered.connect(self.preview_selected)
        menu.addAction(preview_action)
        
        menu.exec_(self.list_widget.mapToGlobal(position))
    
    # =================================================================
    # OUTPUT
    # =================================================================
    def browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleziona cartella output")
        if folder:
            folder = os.path.normpath(folder)
            self.out_edit.setText(folder)
            self.log(f"💾 Output scelto: {folder}")
    
    def auto_output(self):
        if not self.files_list:
            return
        
        first_file = self.files_list[0]
        input_dir = os.path.dirname(first_file)
        
        base_output = os.path.join(input_dir, "nobg_output")
        output_dir = base_output
        counter = 1
        
        while os.path.exists(output_dir) and os.listdir(output_dir):
            output_dir = f"{base_output}_{counter}"
            counter += 1
        
        output_dir = os.path.normpath(output_dir)
        self.out_edit.setText(output_dir)
        self.log(f"🔄 Output auto: {output_dir}")
    
    # =================================================================
    # ELABORAZIONE - FIX DEFINITIVO: TEMP + SPOSTAMENTO
    # =================================================================
    def start_processing(self):
        """Elabora in cartella temporanea, poi sposta nella destinazione scelta"""
        if not self.files_list:
            self.show_warning("Nessun file", "Carica almeno un'immagine!")
            return
        
        output_user = self.out_edit.text().strip()
        if not output_user:
            self.auto_output()
            output_user = self.out_edit.text()
        
        # =================================================================
        # STRATEGIA: Elabora in temp, poi sposta nel percorso scelto
        # =================================================================
        
        # Cartella temporanea sicura (sempre funziona)
        temp_dir = tempfile.mkdtemp(prefix="bg_remover_")
        logger.info(f"Temp dir: {temp_dir}")
        
        # Salva percorso finale desiderato
        final_output = os.path.normpath(output_user.strip('"').strip("'"))
        
        # UI
        self.start_btn.setEnabled(False)
        self.start_btn.setText("⏳ ELABORAZIONE...")
        self.progress.setMaximum(len(self.files_list))
        self.progress.setValue(0)
        
        self.log_text.clear()
        self.log("=" * 50)
        self.log("🚀 AVVIO ELABORAZIONE")
        self.log(f"📊 File: {len(self.files_list)}")
        self.log(f"💾 Output finale: {final_output}")
        self.log(f"   (Elaborazione in: {temp_dir})")
        self.log("=" * 50)
        
        # Ferma worker precedente
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(1000)
        
        # Crea worker che elabora in temp
        self.worker = WorkerThread(
            self.files_list.copy(),
            temp_dir,  # Elabora qui
            self.qual_spin.value()
        )
        
        # Connetti segnali
        self.worker.log_signal.connect(self.on_log)
        self.worker.progress_signal.connect(self.on_progress)
        
        # Gestione fine elaborazione con spostamento
        def on_finished_move(stats):
            self.start_btn.setEnabled(True)
            self.start_btn.setText("▶️ AVVIA ELABORAZIONE")
            
            if stats.get('error'):
                self.show_error("Errore", stats.get('message', 'Errore'))
                # Pulisci temp
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
                return
            
            # Sposta file da temp a destinazione finale
            self.log("📁 Spostamento file nella cartella scelta...")
            try:
                # Crea cartella finale se non esiste
                os.makedirs(final_output, exist_ok=True)
                
                # Sposta tutti i file elaborati
                moved = 0
                for f in os.listdir(temp_dir):
                    if f.endswith('_nobg.png'):
                        src = os.path.join(temp_dir, f)
                        dst = os.path.join(final_output, f)
                        shutil.move(src, dst)
                        moved += 1
                
                # Pulisci temp
                shutil.rmtree(temp_dir)
                
                self.log(f"✅ Spostati {moved} file in: {final_output}")
                self.show_success(
                    "Completato!",
                    f"Elaborate {stats.get('success', 0)} immagini\n"
                    f"Salvate in: {final_output}"
                )
                self.out_edit.setText(final_output)
                
            except Exception as move_e:
                logger.error("Errore spostamento", move_e)
                self.show_error(
                    "Errore spostamento",
                    f"Elaborazione OK ma impossibile spostare in:\n{final_output}\n\n"
                    f"File temporanei in: {temp_dir}\n"
                    f"Errore: {str(move_e)}"
                )
        
        self.worker.finished_signal.connect(on_finished_move)
        self.worker.error_signal.connect(self.on_error)
        
        self.worker.start()
    
    def on_log(self, msg):
        if QThread.currentThread() != self.thread():
            QMetaObject.invokeMethod(self, "log", Qt.QueuedConnection, Q_ARG(str, msg))
        else:
            self.log(msg)
    
    def log(self, msg):
        self.log_text.append(msg)
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        clean_msg = msg.replace("🔄 ", "").replace("✅ ", "").replace("❌ ", "")
        logger.info(clean_msg)
    
    def on_progress(self, current, total, filename):
        self.progress.setValue(current)
        self.progress.setFormat(f"%p% - {current}/{total}")
        self.status_label.setText(f"Elaborazione: {current}/{total}")
    
    def on_error(self, title, message):
        self.start_btn.setEnabled(True)
        self.start_btn.setText("▶️ AVVIA ELABORAZIONE")
        self.show_error(title, message)
    
    def open_log(self):
        log_path = logger.get_log_path()
        if os.path.exists(log_path):
            os.system(f'notepad "{log_path}"')
        else:
            self.show_error("Log non trovato", log_path)
    
    def show_help(self):
        QMessageBox.information(
            self,
            "Aiuto",
            "📖 GUIDA\n\n"
            "1. 📁 Cartella: carica TUTTE le immagini\n"
            "2. 📄 File: seleziona singole immagini\n"
            "3. 💾 Sfoglia: scegli DOVE salvare\n"
            "4. Elaborazione avviene in temp, poi sposta\n\n"
            "Il percorso scelto viene SEMPRE rispettato!"
        )
    
    def show_error(self, title, msg):
        QMessageBox.critical(self, f"❌ {title}", msg)
        logger.error(f"ERROR: {title} - {msg[:100]}")
    
    def show_warning(self, title, msg):
        QMessageBox.warning(self, f"⚠️ {title}", msg)
        logger.warning(f"WARN: {title} - {msg[:100]}")
    
    def show_success(self, title, msg):
        QMessageBox.information(self, f"✅ {title}", msg)
        logger.success(f"OK: {title}")
    
    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "Conferma", "Interrompere elaborazione?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
            self.worker.stop()
            self.worker.wait(2000)
        
        logger.close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Background Remover Pro")
    app.setStyle('Fusion')
    
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
