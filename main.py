#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Background Remover - GUI Stabile
Popup errori, log automatico, nessun CMD richiesto
"""

import sys
import os

# Fix path PyInstaller
if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
else:
    bundle_dir = os.path.dirname(os.path.abspath(__file__))

if bundle_dir not in sys.path:
    sys.path.insert(0, bundle_dir)

# Import logger prima di tutto
from logger import get_logger, AppLogger
logger = get_logger()

# PyQt5
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QListWidget,
    QProgressBar, QMessageBox, QSpinBox, QGroupBox, QTextEdit,
    QSystemTrayIcon, QMenu, QAction
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QMetaObject, Q_ARG
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QIcon, QFont

# Blocca output console su Windows
if sys.platform == 'win32':
    try:
        import ctypes
        ctypes.windll.kernel32.FreeConsole()
    except:
        pass


class WorkerThread(QThread):
    """Thread elaborazione con segnali thread-safe"""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int, str)  # current, total, filename
    finished_signal = pyqtSignal(dict)  # stats
    error_signal = pyqtSignal(str, str)  # title, message
    
    def __init__(self, file_paths, output_dir, quality):
        super().__init__()
        self.file_paths = file_paths
        self.output_dir = output_dir
        self.quality = quality
        self._is_running = True
        
    def run(self):
        try:
            from utils.image_processor import BackgroundRemover
            
            # Inizializza AI
            self.log_signal.emit("🧠 Inizializzazione AI...")
            try:
                remover = BackgroundRemover()
                self.log_signal.emit("✅ AI Pronta!")
            except Exception as e:
                logger.error("Inizializzazione AI fallita", e)
                self.error_signal.emit(
                    "Errore AI", 
                    f"Impossibile caricare l'intelligenza artificiale.\n\n"
                    f"Dettaglio: {str(e)}\n\n"
                    f"Verificare l'installazione e riavviare."
                )
                self.finished_signal.emit({'error': True, 'message': str(e)})
                return
            
            # Elaborazione
            def progress_callback(current, total, filename):
                if not self._is_running:
                    raise InterruptedError("Utente interrotto")
                self.progress_signal.emit(current, total, filename)
                self.log_signal.emit(f"🔄 [{current}/{total}] {filename}")
            
            stats = remover.batch_process(
                self.file_paths,
                self.output_dir,
                self.quality,
                callback=progress_callback
            )
            
            self.finished_signal.emit(stats)
            
        except InterruptedError:
            logger.info("Elaborazione interrotta dall'utente")
            self.finished_signal.emit({'interrupted': True})
        except Exception as e:
            logger.error("Errore thread elaborazione", e)
            self.error_signal.emit(
                "Errore Critico",
                f"Si è verificato un errore imprevisto:\n\n{str(e)}\n\n"
                f"Consultare il file di log per dettagli:\n{logger.get_log_path()}"
            )
            self.finished_signal.emit({'error': True, 'message': str(e)})
    
    def stop(self):
        self._is_running = False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Background Remover Pro")
        self.setMinimumSize(1000, 800)
        
        # Stile
        self.setStyleSheet("""
            QMainWindow { background-color: #f5f5f5; }
            QGroupBox { 
                font-weight: bold; 
                border: 2px solid #4CAF50; 
                border-radius: 8px; 
                margin-top: 10px; 
                padding-top: 10px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QPushButton { 
                padding: 10px 20px; 
                border-radius: 6px; 
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton#start { background-color: #4CAF50; color: white; }
            QPushButton#start:hover { background-color: #45a049; }
            QPushButton#start:disabled { background-color: #cccccc; }
            QPushButton#clear { background-color: #f44336; color: white; }
            QPushButton#clear:hover { background-color: #da190b; }
            QPushButton#browse { background-color: #2196F3; color: white; }
            QPushButton#log { background-color: #FF9800; color: white; }
            QProgressBar { 
                border: 2px solid #4CAF50; 
                border-radius: 5px; 
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk { background-color: #4CAF50; }
            QTextEdit { 
                border: 2px solid #ddd; 
                border-radius: 5px; 
                font-family: Consolas, monospace;
                font-size: 11px;
            }
        """)
        
        self.files_list = []
        self.worker = None
        
        self.setup_ui()
        self.setup_tray()
        
        # Log iniziale
        logger.info("=" * 70)
        logger.info("APPLICAZIONE AVVIATA")
        logger.info(f"Log file: {logger.get_log_path()}")
        logger.info("=" * 70)
        
        self.statusBar().showMessage(f"Pronto - Log: {logger.get_log_path()}")
        
    def setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setToolTip("Background Remover")
        
        tray_menu = QMenu()
        show_action = QAction("Mostra", self)
        show_action.triggered.connect(self.show)
        exit_action = QAction("Esci", self)
        exit_action.triggered.connect(self.close)
        
        tray_menu.addAction(show_action)
        tray_menu.addAction(exit_action)
        self.tray.setContextMenu(tray_menu)
        
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # HEADER
        header = QLabel("🖼️ Background Remover Pro")
        header.setFont(QFont("Segoe UI", 20, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("color: #4CAF50; margin-bottom: 10px;")
        layout.addWidget(header)
        
        # INPUT GROUP
        in_group = QGroupBox("📂 Cartella Input (trascina qui o clicca Sfoglia)")
        in_layout = QHBoxLayout()
        self.in_edit = QLineEdit()
        self.in_edit.setPlaceholderText("C:\\Users\\Nome\\Immagini...")
        self.in_edit.setMinimumHeight(35)
        btn_browse_in = QPushButton("Sfoglia...")
        btn_browse_in.setObjectName("browse")
        btn_browse_in.clicked.connect(self.browse_input)
        in_layout.addWidget(self.in_edit)
        in_layout.addWidget(btn_browse_in)
        in_group.setLayout(in_layout)
        layout.addWidget(in_group)
        
        # OUTPUT GROUP
        out_group = QGroupBox("💾 Cartella Output (lascia vuoto per sottocartella 'nobg')")
        out_layout = QHBoxLayout()
        self.out_edit = QLineEdit()
        self.out_edit.setPlaceholderText("Opzionale - verrà creata automaticamente...")
        self.out_edit.setMinimumHeight(35)
        btn_browse_out = QPushButton("Sfoglia...")
        btn_browse_out.setObjectName("browse")
        btn_browse_out.clicked.connect(self.browse_output)
        out_layout.addWidget(self.out_edit)
        out_layout.addWidget(btn_browse_out)
        out_group.setLayout(out_layout)
        layout.addWidget(out_group)
        
        # SETTINGS
        settings = QHBoxLayout()
        
        # Qualità
        qual_box = QGroupBox("⚙️ Qualità")
        qual_layout = QHBoxLayout()
        self.qual_spin = QSpinBox()
        self.qual_spin.setRange(10, 100)
        self.qual_spin.setValue(95)
        self.qual_spin.setSuffix("%")
        self.qual_spin.setMinimumHeight(35)
        qual_layout.addWidget(self.qual_spin)
        qual_box.setLayout(qual_layout)
        settings.addWidget(qual_box)
        
        # Info
        info_box = QGroupBox("ℹ️ Info")
        info_layout = QHBoxLayout()
        self.info_label = QLabel("Nessuna immagine caricata")
        info_layout.addWidget(self.info_label)
        info_box.setLayout(info_layout)
        settings.addWidget(info_box, stretch=1)
        
        layout.addLayout(settings)
        
        # FILE LIST (drop area)
        self.list_widget = QListWidget()
        self.list_widget.setAcceptDrops(True)
        self.list_widget.setMinimumHeight(150)
        self.list_widget.setMaximumHeight(200)
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.dragEnterEvent = self.drag_enter
        self.list_widget.dragMoveEvent = self.drag_move
        self.list_widget.dropEvent = self.drop
        self.list_widget.setStyleSheet("""
            QListWidget { 
                border: 2px dashed #4CAF50; 
                border-radius: 8px;
                background-color: #fafafa;
            }
            QListWidget::item { padding: 5px; }
            QListWidget::item:alternate { background-color: #f0f0f0; }
        """)
        layout.addWidget(QLabel("📋 File caricati (trascina immagini o cartelle qui):"))
        layout.addWidget(self.list_widget)
        
        # PROGRESS
        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.setFormat("%p% - %v/%m file")
        layout.addWidget(self.progress)
        
        # LOG AREA
        log_group = QGroupBox("📜 Log operazioni")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(180)
        self.log_text.setPlaceholderText("Qui appariranno i messaggi di log...")
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # BUTTONS
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶️ AVVIA ELABORAZIONE")
        self.start_btn.setObjectName("start")
        self.start_btn.setMinimumHeight(50)
        self.start_btn.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.start_btn.clicked.connect(self.start_processing)
        
        btn_clear = QPushButton("🗑️ PULISCI")
        btn_clear.setObjectName("clear")
        btn_clear.setMinimumHeight(50)
        btn_clear.clicked.connect(self.clear_all)
        
        btn_log = QPushButton("📁 APRI LOG")
        btn_log.setObjectName("log")
        btn_log.setMinimumHeight(50)
        btn_log.clicked.connect(self.open_log)
        
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(btn_clear)
        btn_layout.addWidget(btn_log)
        layout.addLayout(btn_layout)
        
        # FOOTER
        footer = QLabel("💡 Trascina una cartella nell'area sopra o clicca 'Sfoglia' per iniziare")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(footer)
        
    def drag_enter(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.list_widget.setStyleSheet("""
                QListWidget { 
                    border: 2px dashed #2196F3; 
                    background-color: #e3f2fd;
                }
            """)
    
    def drag_move(self, event):
        event.acceptProposedAction()
    
    def drop(self, event):
        self.list_widget.setStyleSheet("""
            QListWidget { 
                border: 2px dashed #4CAF50; 
                border-radius: 8px;
                background-color: #fafafa;
            }
        """)
        
        paths = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                self.in_edit.setText(path)
                self.scan_folder(path)
                return
            elif path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp')):
                paths.append(path)
        
        if paths:
            self.add_files(paths)
    
    def browse_input(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleziona cartella immagini")
        if folder:
            self.in_edit.setText(folder)
            self.scan_folder(folder)
    
    def scan_folder(self, folder):
        self.files_list.clear()
        self.list_widget.clear()
        
        extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp')
        count = 0
        
        try:
            for f in os.listdir(folder):
                if f.lower().endswith(extensions):
                    path = os.path.join(folder, f)
                    self.files_list.append(path)
                    self.list_widget.addItem(f"📄 {f}")
                    count += 1
        except Exception as e:
            self.show_error("Errore scansione", f"Impossibile leggere cartella:\n{str(e)}")
            return
        
        self.info_label.setText(f"{count} immagini trovate")
        self.log(f"📂 Scansionata: {folder}")
        self.log(f"   Trovate: {count} immagini")
        
        if count == 0:
            self.show_warning("Nessuna immagine", 
                "Nessuna immagine trovata nella cartella.\n"
                "Formati supportati: PNG, JPG, JPEG, BMP, TIFF, WEBP")
    
    def add_files(self, paths):
        for p in paths:
            if p not in self.files_list:
                self.files_list.append(p)
                self.list_widget.addItem(f"📄 {os.path.basename(p)}")
        
        self.info_label.setText(f"{len(self.files_list)} immagini totali")
        self.log(f"📎 Aggiunti {len(paths)} file")
    
    def browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleziona cartella output")
        if folder:
            self.out_edit.setText(folder)
    
    def log(self, msg):
        """Aggiunge log alla UI"""
        self.log_text.append(msg)
        # Auto-scroll
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        # Anche su file logger
        logger.info(msg.replace("📂 ", "").replace("📎 ", "").replace("🔄 ", "")
                   .replace("✅ ", "").replace("❌ ", "").replace("📜 ", ""))
    
    def start_processing(self):
        if not self.files_list:
            self.show_warning("Nessuna immagine", 
                "Carica prima delle immagini!\n\n"
                "Trascina una cartella o clicca 'Sfoglia'")
            return
        
        # Determina output
        output = self.out_edit.text().strip()
        if not output:
            input_dir = self.in_edit.text().strip()
            if input_dir:
                output = os.path.join(input_dir, "nobg_output")
            else:
                self.show_error("Errore", "Specificare cartella output o input")
                return
        
        # Verifica/crea output
        try:
            os.makedirs(output, exist_ok=True)
            test_file = os.path.join(output, ".write_test")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
        except Exception as e:
            self.show_error("Errore cartella", 
                f"Impossibile scrivere nella cartella output:\n{output}\n\n{str(e)}")
            return
        
        self.out_edit.setText(output)
        
        # UI ready
        self.start_btn.setEnabled(False)
        self.start_btn.setText("⏳ ELABORAZIONE IN CORSO...")
        self.progress.setMaximum(len(self.files_list))
        self.progress.setValue(0)
        self.log_text.clear()
        
        self.log("=" * 50)
        self.log("🚀 AVVIO ELABORAZIONE BATCH")
        self.log(f"   File: {len(self.files_list)}")
        self.log(f"   Output: {output}")
        self.log(f"   Qualità: {self.qual_spin.value()}%")
        self.log("=" * 50)
        
        # Ferma thread precedente se esiste
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(1000)
        
        # Crea nuovo worker
        self.worker = WorkerThread(
            self.files_list.copy(),
            output,
            self.qual_spin.value()
        )
        
        # Connetti segnali (thread-safe)
        self.worker.log_signal.connect(self.on_worker_log)
        self.worker.progress_signal.connect(self.on_worker_progress)
        self.worker.finished_signal.connect(self.on_worker_finished)
        self.worker.error_signal.connect(self.on_worker_error)
        
        self.worker.start()
    
    def on_worker_log(self, msg):
        """Riceve log dal worker (thread-safe)"""
        if QThread.currentThread() != self.thread():
            QMetaObject.invokeMethod(self, "log", 
                Qt.QueuedConnection, 
                Q_ARG(str, msg))
        else:
            self.log(msg)
    
    def on_worker_progress(self, current, total, filename):
        """Aggiorna progresso (thread-safe)"""
        def update():
            self.progress.setValue(current)
            self.progress.setFormat(f"%p% - {current}/{total} - {filename[:30]}")
            self.statusBar().showMessage(f"Elaborazione: {filename}")
        
        if QThread.currentThread() != self.thread():
            QMetaObject.invokeMethod(self, "progress_callback", 
                Qt.QueuedConnection,
                Q_ARG(int, current),
                Q_ARG(int, total),
                Q_ARG(str, filename))
        else:
            update()
    
    def progress_callback(self, current, total, filename):
        self.progress.setValue(current)
        self.progress.setFormat(f"%p% - {current}/{total}")
        self.statusBar().showMessage(f"Elaborazione: {filename[:50]}")
    
    def on_worker_finished(self, stats):
        """Elaborazione terminata"""
        self.start_btn.setEnabled(True)
        self.start_btn.setText("▶️ AVVIA ELABORAZIONE")
        
        if stats.get('error'):
            self.show_error("Errore Elaborazione", 
                f"Si è verificato un errore:\n{stats.get('message', 'Unknown')}")
            return
        
        if stats.get('interrupted'):
            self.show_warning("Interrotto", "Elaborazione interrotta dall'utente")
            return
        
        # Successo
        success = stats.get('success', 0)
        total = stats.get('total', 0)
        failed = stats.get('failed', 0)
        
        self.progress.setValue(total)
        self.statusBar().showMessage(f"Completato: {success}/{total}")
        
        if failed == 0:
            self.show_success("Completato!", 
                f"✅ Tutte le immagini elaborate con successo!\n\n"
                f"Totali: {total}\n"
                f"Successo: {success}\n"
                f"Output: {self.out_edit.text()}")
        else:
            # Mostra errori specifici
            errors = stats.get('errors', [])
            error_text = "\n".join([f"• {e['file']}: {e['error'][:50]}" for e in errors[:5]])
            if len(errors) > 5:
                error_text += f"\n... e altri {len(errors)-5} errori"
            
            reply = QMessageBox.question(self, "Completato con errori",
                f"⚠️ Elaborazione parziale:\n\n"
                f"Successo: {success}/{total}\n"
                f"Falliti: {failed}\n\n"
                f"Errori:\n{error_text}\n\n"
                f"Vuoi aprire il file di log per i dettagli completi?",
                QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                self.open_log()
    
    def on_worker_error(self, title, message):
        """Errore critico dal worker"""
        self.start_btn.setEnabled(True)
        self.start_btn.setText("▶️ AVVIA ELABORAZIONE")
        self.show_error(title, message)
    
    def clear_all(self):
        """Pulisce tutto"""
        self.files_list.clear()
        self.list_widget.clear()
        self.log_text.clear()
        self.in_edit.clear()
        self.out_edit.clear()
        self.progress.setValue(0)
        self.info_label.setText("Nessuna immagine caricata")
        self.statusBar().showMessage("Pronto")
        
        if self.worker and self.worker.isRunning():
            self.worker.stop()
        
        logger.info("Pulizia interfaccia")
    
    def open_log(self):
        """Apre cartella log"""
        log_path = logger.get_log_path()
        log_dir = os.path.dirname(log_path)
        
        if os.path.exists(log_path):
            # Apri file con notepad
            os.system(f'notepad "{log_path}"')
        else:
            # Apri cartella
            os.startfile(log_dir) if os.path.exists(log_dir) else self.show_error(
                "Log non trovato", f"Impossibile trovare: {log_dir}")
    
    def show_error(self, title, message):
        QMessageBox.critical(self, f"❌ {title}", message)
        logger.error(f"POPUP ERRORE: {title} - {message}")
    
    def show_warning(self, title, message):
        QMessageBox.warning(self, f"⚠️ {title}", message)
        logger.warning(f"POPUP AVVISO: {title} - {message}")
    
    def show_success(self, title, message):
        QMessageBox.information(self, f"✅ {title}", message)
        logger.success(f"POPUP SUCCESSO: {title} - {message}")
    
    def closeEvent(self, event):
        """Chiusura applicazione"""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(self, "Conferma",
                "Elaborazione in corso. Vuoi interrompere e uscire?",
                QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                self.worker.stop()
                self.worker.wait(2000)
            else:
                event.ignore()
                return
        
        logger.close()
        event.accept()


def main():
    # Crea applicazione
    app = QApplication(sys.argv)
    app.setApplicationName("Background Remover Pro")
    app.setApplicationVersion("3.0")
    
    # Font di sistema
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Crea finestra
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
