import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
                             QListWidget, QListWidgetItem, QLabel, QProgressBar, QMessageBox, QMenuBar, QLineEdit)
from PyQt6.QtCore import QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QIcon, QDesktopServices, QAction
from sql_parser_logic.SqlParserLogic import SqlParser

# --- STYLESHEET ---
STYLESHEET = """
    QWidget {
        background-color: #2E2E2E;
        color: #F0F0F0;
        font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', sans-serif;
        font-size: 14px;
    }
    QPushButton {
        background-color: #555555;
        border: 1px solid #777777;
        padding: 8px;
        border-radius: 4px;
    }
    QPushButton:hover {
        background-color: #666666;
    }
    QPushButton:pressed {
        background-color: #444444;
    }
    QPushButton:disabled {
        background-color: #404040;
        color: #888888;
    }
    QLineEdit {
        background-color: #3C3C3C;
        border: 1px solid #555555;
        padding: 6px;
        border-radius: 4px;
    }
    QListWidget {
        background-color: #3C3C3C;
        border: 1px solid #555555;
        border-radius: 4px;
    }
    QListWidget::item:hover {
        background-color: #4A4A4A;
    }
    QListWidget::item:selected {
        background-color: #007ACC;
        color: white;
    }
    QLabel {
        font-size: 14px;
    }
    QProgressBar {
        border: 1px solid #555555;
        border-radius: 4px;
        text-align: center;
        background-color: #3C3C3C;
    }
    QProgressBar::chunk {
        background-color: #007ACC;
        border-radius: 3px;
    }
    QMenuBar {
        background-color: #3C3C3C;
    }
    QMenuBar::item {
        background: transparent;
        padding: 4px 8px;
    }
    QMenuBar::item:selected {
        background: #555555;
    }
    QMenu {
        background-color: #3C3C3C;
        border: 1px solid #555555;
    }
    QMenu::item:selected {
        background-color: #007ACC;
    }
"""

class ParserWorker(QThread):
    finished = pyqtSignal(object, list)
    error = pyqtSignal(str)

    def __init__(self, filepath):
        super().__init__()
        self.filepath = filepath

    def run(self):
        try:
            parser = SqlParser(self.filepath, show_progress=False)
            tables = parser.build_index()
            self.finished.emit(parser, tables)
        except Exception as e:
            self.error.emit(str(e))

class ExportWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(object) # Will emit the output path
    error = pyqtSignal(str)

    def __init__(self, parser, tables):
        super().__init__()
        self.parser = parser
        self.tables = tables
        self.output_path = None

    def run(self):
        try:
            for i, table in enumerate(self.tables):
                path = self.parser.process_table(table)
                if path and self.output_path is None:
                    self.output_path = path
                self.progress.emit(i + 1)
            self.finished.emit(self.output_path)
        except Exception as e:
            self.error.emit(str(e))

class SqlParserGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.parser = None
        self.filepath = None
        self.output_path = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle('SQL Parser Plus')
        self.setGeometry(100, 100, 600, 600)
        self.setStyleSheet(STYLESHEET)

        # --- Icons ---
        self.file_icon = self.style().standardIcon(QApplication.style().StandardPixmap.SP_FileIcon)
        self.index_icon = self.style().standardIcon(QApplication.style().StandardPixmap.SP_ArrowRight)
        self.export_icon = self.style().standardIcon(QApplication.style().StandardPixmap.SP_DialogSaveButton)
        self.open_folder_icon = self.style().standardIcon(QApplication.style().StandardPixmap.SP_DirOpenIcon)

        # --- Menu Bar ---
        self.menu_bar = QMenuBar(self)
        help_menu = self.menu_bar.addMenu('Help')
        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

        # --- Layout ---
        self.layout = QVBoxLayout()
        self.layout.setMenuBar(self.menu_bar)

        # File Selection
        self.btn_select_file = QPushButton(' 1. Select SQL File')
        self.btn_select_file.setIcon(self.file_icon)
        self.btn_select_file.clicked.connect(self.select_file)
        self.layout.addWidget(self.btn_select_file)

        self.lbl_file = QLabel('No file selected.')
        self.layout.addWidget(self.lbl_file)

        # Indexing
        self.btn_index = QPushButton(' 2. Index Tables')
        self.btn_index.setIcon(self.index_icon)
        self.btn_index.clicked.connect(self.start_indexing)
        self.btn_index.setEnabled(False)
        self.layout.addWidget(self.btn_index)

        # Search Bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search tables...")
        self.search_bar.textChanged.connect(self.filter_tables)
        self.search_bar.setEnabled(False)
        self.layout.addWidget(self.search_bar)

        # Table List and Selection Buttons
        self.table_list = QListWidget()
        self.table_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.layout.addWidget(self.table_list)

        selection_layout = QHBoxLayout()
        self.btn_select_all = QPushButton('Select All Visible')
        self.btn_select_all.clicked.connect(self.select_all)
        self.btn_select_all.setEnabled(False)
        selection_layout.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton('Deselect All')
        self.btn_deselect_all.clicked.connect(self.deselect_all)
        self.btn_deselect_all.setEnabled(False)
        selection_layout.addWidget(self.btn_deselect_all)
        self.layout.addLayout(selection_layout)

        # Export
        self.btn_export = QPushButton(' 3. Export Selected Tables')
        self.btn_export.setIcon(self.export_icon)
        self.btn_export.clicked.connect(self.export_tables)
        self.btn_export.setEnabled(False)
        self.layout.addWidget(self.btn_export)

        # Post-Export
        self.btn_open_folder = QPushButton('Open Output Folder')
        self.btn_open_folder.setIcon(self.open_folder_icon)
        self.btn_open_folder.clicked.connect(self.open_output_folder)
        self.btn_open_folder.setEnabled(False)
        self.layout.addWidget(self.btn_open_folder)

        # Status and Progress
        self.lbl_status = QLabel('Status: Idle')
        self.layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.layout.addWidget(self.progress_bar)

        self.setLayout(self.layout)

    def select_file(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Open SQL File", "", "SQL Files (*.sql);;All Files (*)")
        if filepath:
            self.filepath = filepath
            self.lbl_file.setText(f"File: {Path(self.filepath).name}")
            self.lbl_status.setText('Status: File selected. Ready to index.')
            self.btn_index.setEnabled(True)
            self.btn_export.setEnabled(False)
            self.btn_select_all.setEnabled(False)
            self.btn_deselect_all.setEnabled(False)
            self.btn_open_folder.setEnabled(False)
            self.search_bar.setEnabled(False)
            self.search_bar.clear()
            self.table_list.clear()
            self.progress_bar.setValue(0)

    def start_indexing(self):
        self.lbl_status.setText('Status: Indexing...')
        self.btn_index.setEnabled(False)
        self.btn_select_file.setEnabled(False)
        self.worker = ParserWorker(self.filepath)
        self.worker.finished.connect(self.on_parsing_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_parsing_finished(self, parser, tables):
        self.parser = parser
        self.btn_select_file.setEnabled(True)
        if tables:
            self.lbl_status.setText(f'Status: Indexing complete. Found {len(tables)} tables.')
            for table in tables:
                item = QListWidgetItem(table)
                self.table_list.addItem(item)
            self.btn_export.setEnabled(True)
            self.btn_select_all.setEnabled(True)
            self.btn_deselect_all.setEnabled(True)
            self.search_bar.setEnabled(True)
        else:
            self.lbl_status.setText('Status: Indexing complete. No tables found.')
            QMessageBox.information(self, "No Tables Found", "Could not find any tables in the selected file.")
            self.btn_index.setEnabled(True)

    def filter_tables(self, text):
        for i in range(self.table_list.count()):
            item = self.table_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def select_all(self):
        for i in range(self.table_list.count()):
            item = self.table_list.item(i)
            if not item.isHidden():
                item.setSelected(True)

    def deselect_all(self):
        self.table_list.clearSelection()

    def export_tables(self):
        selected_items = self.table_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Tables Selected", "Please select at least one table to export.")
            return
        tables_to_export = [item.text() for item in selected_items]
        self.progress_bar.setMaximum(len(tables_to_export))
        self.lbl_status.setText(f'Status: Exporting {len(tables_to_export)} tables...')
        self.btn_export.setEnabled(False)
        self.btn_select_file.setEnabled(False)
        self.btn_index.setEnabled(False)
        self.btn_open_folder.setEnabled(False)
        self.search_bar.setEnabled(False)
        self.export_worker = ExportWorker(self.parser, tables_to_export)
        self.export_worker.progress.connect(self.update_progress)
        self.export_worker.finished.connect(self.on_export_finished)
        self.export_worker.error.connect(self.on_error)
        self.export_worker.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def on_export_finished(self, output_path):
        self.output_path = output_path
        self.lbl_status.setText('Status: Export complete.')
        QMessageBox.information(self, "Export Complete", "Selected tables have been exported successfully.")
        self.btn_export.setEnabled(True)
        self.btn_select_file.setEnabled(True)
        self.btn_index.setEnabled(True)
        self.search_bar.setEnabled(True)
        if self.output_path:
            self.btn_open_folder.setEnabled(True)
        self.progress_bar.setValue(0)

    def on_error(self, error_message):
        self.lbl_status.setText(f'Status: Error - {error_message}')
        QMessageBox.critical(self, "An Error Occurred", error_message)
        self.btn_export.setEnabled(True)
        self.btn_select_file.setEnabled(True)
        self.btn_index.setEnabled(True)
        self.search_bar.setEnabled(True)

    def open_output_folder(self):
        if self.output_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_path)))

    def show_about_dialog(self):
        QMessageBox.about(self, "About SQL Parser Plus",
            """
            <b>SQL Parser Plus</b>
            <p>A tool to convert large SQL dumps into CSV files.</p>
            <p>For more information, visit the <a href='https://github.com/ytisf/SQL-Parser-Plus-Plus'>GitHub repository</a>.</p>
            """
        )

def main():
    app = QApplication(sys.argv)
    gui = SqlParserGUI()
    gui.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
