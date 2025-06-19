import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QPushButton, QComboBox, QVBoxLayout,
    QHBoxLayout, QLabel, QFileDialog, QTableWidget, QTableWidgetItem,
    QMenuBar, QMenu, QCheckBox, QMessageBox, QInputDialog, QSizePolicy
)

from PyQt6.QtGui import (QKeyEvent, QAction, QColor)
from PyQt6.QtCore import Qt

from app.core.file_loader import load_file_pairs
from app.core.textgrid_parser import extract_intervals
from textgrid import TextGrid

from app.core.audio_player import play_segment

from app.gui.waveform_viewer import WaveformViewer

def shorten_path(path: str, max_chars: int = 60) -> str:
    if len(path) <= max_chars:
        return path
    else:
        return f"{path[:25]}…{path[-30:]}"
    
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vocal Folder (beta)")

        self.file_pairs = []
        self.tier_intervals = []

        self.tier_dropdown = QComboBox()
        self.load_button = QPushButton("Load Folder")
        self.table = QTableWidget()
        self.file_edit_warning_shown = False

        self.edit_checkbox = QCheckBox("Enable Text Editing")
        self.edit_checkbox.stateChanged.connect(self.toggle_table_editing)

        self.folder_label = QLabel("")
        self.folder_label.setStyleSheet("color: gray; margin-left: 10px;")
        self.folder_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.folder_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.folder_label.setMinimumWidth(200)
        self.folder_label.setMaximumHeight(20)
        self.folder_label.setWordWrap(False)
        self.folder_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.table.itemChanged.connect(self.mark_as_modified)
        self.modified_cells = set()

        self.waveform_viewer = WaveformViewer()
        self.waveform_viewer.waveformClicked.connect(self.play_from_waveform)

        self.load_button.clicked.connect(self.load_folder)
        self.tier_dropdown.currentIndexChanged.connect(self.refresh_table)
        self.table.cellClicked.connect(self.on_table_select)
        self.table.currentCellChanged.connect(self.on_table_select)
        self.table.installEventFilter(self)

        self.toggle_table_editing(0)

        self.current_playback = None
        self.selected_segment_info = None  # (wav_path, start_time, end_time)

        # -------------------------
        # UI Layout
        # -------------------------

        # Row 1: Load button + folder path
        top_row1 = QHBoxLayout()

        folder_label = QLabel("Working Directory:")
        folder_label.setStyleSheet("font-weight: bold; margin-right: 5px;")

        self.load_button.setFixedWidth(120)

        top_row1.addWidget(folder_label)
        top_row1.addWidget(self.load_button)
        top_row1.addWidget(self.folder_label)
        top_row1.addStretch()

        # Row 2: Tier selector + edit checkbox
        top_row2 = QHBoxLayout()
        tier_label = QLabel("Select Tier:")
        tier_label.setStyleSheet("font-weight: bold; margin-right: 5px;")
        top_row2.addWidget(tier_label)
        top_row2.addWidget(self.tier_dropdown)
        top_row2.addStretch()
        top_row2.addWidget(self.edit_checkbox)

        # Combine layout
        top_layout = QVBoxLayout()
        top_layout.addLayout(top_row1)
        top_layout.addLayout(top_row2)

        layout = QVBoxLayout()
        layout.addLayout(top_layout)
        layout.addWidget(self.table)
        layout.addWidget(self.waveform_viewer)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self._create_menus()

    def _create_menus(self):
        menubar = self.menuBar()

        edit_menu = menubar.addMenu("Edit")

        undo_action = QAction("Undo", self)
        undo_action.triggered.connect(lambda: self.table.undo())  # May require focus
        redo_action = QAction("Redo", self)
        redo_action.triggered.connect(lambda: self.table.redo())
        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(lambda: self.table.copy())
        paste_action = QAction("Paste", self)
        paste_action.triggered.connect(lambda: self.table.paste())

        # Add actions to Edit menu
        edit_menu.addAction(undo_action)
        edit_menu.addAction(redo_action)
        edit_menu.addSeparator()
        edit_menu.addAction(copy_action)
        edit_menu.addAction(paste_action)

    def load_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if not folder:
            return

        self.file_pairs = load_file_pairs(folder)

        # Mostrar ruta truncada visualmente
        short_path = shorten_path(folder)
        self.folder_label.setText(short_path)
        self.folder_label.setToolTip(folder)

        metrics = self.folder_label.fontMetrics()
        max_width = self.folder_label.width() or 300
        elided_path = metrics.elidedText(folder, Qt.TextElideMode.ElideMiddle, max_width)
        self.folder_label.setText(elided_path)
        self.folder_label.setToolTip(folder)

        tier_name_sets = []
        for _, _, tg_path in self.file_pairs:
            try:
                tg = TextGrid.fromFile(tg_path)
                names = [tier.name for tier in tg.tiers if tier.__class__.__name__ == "IntervalTier"]
                tier_name_sets.append(set(names))
            except Exception as e:
                print(f"Error reading {tg_path}: {e}")

        if not tier_name_sets:
            return

        common_tiers = sorted(set.union(*tier_name_sets))
        self.tier_dropdown.clear()
        self.tier_dropdown.addItems(common_tiers)

    def refresh_table(self):
        if not self.file_pairs:
            return

        selected_tier = self.tier_dropdown.currentText()
        self.tier_intervals = []

        label_has_dash = False  # Detectar etiquetas con guiones

        for name, wav_path, tg_path in self.file_pairs:
            try:
                intervals = extract_intervals(tg_path, tier_name=selected_tier)
                for intv in intervals:
                    label = intv['label']
                    if '-' in label:
                        label_has_dash = True
                    self.tier_intervals.append([
                        name, label, intv['start'], intv['end'], intv['duration']
                    ])
            except Exception as e:
                print(f"Error parsing {tg_path}: {e}")

        if not self.tier_intervals:
            print(f"⚠️ No intervals found for tier: '{selected_tier}'")

        # Preguntar si se quiere dividir en columnas adicionales
        self.split_labels = False
        if label_has_dash:
            reply = QMessageBox.question(
                self,
                "Etiquetas con guiones detectadas",
                "Se han detectado posibles variables en las etiquetas (p. ej. 'b-una_burra-a-b-u-ton-ext-f-fem-jov').\n\n¿Quieres dividirlas en columnas separadas?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.split_labels = True

        # 🛑 Desconectar para evitar disparos falsos
        try:
            self.table.itemChanged.disconnect(self.mark_as_modified)
        except Exception:
            pass

        # Construir encabezados
        base_headers = ["File", "Label"]
        feature_headers = ["Start", "End", "Duration"]
        variable_headers = []

        if self.split_labels:
            max_parts = max(row[1].count("-") + 1 for row in self.tier_intervals)
            variable_headers = [f"Var{i+1}" for i in range(max_parts)]

        headers = base_headers + variable_headers + feature_headers
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(self.tier_intervals))

        for i, row in enumerate(self.tier_intervals):
            self.table.setItem(i, 0, QTableWidgetItem(str(row[0])))  # File
            self.table.setItem(i, 1, QTableWidgetItem(str(row[1])))  # Label

            offset = 2
            if self.split_labels:
                parts = row[1].split("-")
                for k, part in enumerate(parts):
                    self.table.setItem(i, offset + k, QTableWidgetItem(part))
                offset += len(variable_headers)

            self.table.setItem(i, offset + 0, QTableWidgetItem(str(row[2])))  # Start
            self.table.setItem(i, offset + 1, QTableWidgetItem(str(row[3])))  # End
            self.table.setItem(i, offset + 2, QTableWidgetItem(str(row[4])))  # Duration

        self.modified_cells.clear()
        self.table.itemChanged.connect(self.mark_as_modified)

    def on_table_select(self, row, column, *_):
        try:
            header = self.table.horizontalHeaderItem(column).text()
            print(f"🧪 Table clicked: row={row}, column={column}, header={header}")

            entry = self.tier_intervals[row]
            file_name = entry[0]

            # Find matching wav path
            wav_path = None
            for name, wav, _ in self.file_pairs:
                if name == file_name:
                    wav_path = wav
                    break

            if not wav_path:
                print(f"⚠️ Could not find WAV file for: {file_name}")
                return

            start_time = float(entry[2])
            end_time = float(entry[3])

            if header == "File":
                print(f"👆 Selected full file: {file_name}")
                self.waveform_viewer.plot_waveform(wav_path, start=start_time, end=end_time, zoom=False)
                self.selected_segment_info = (wav_path, 0, None)

            elif header == "Label":
                print(f"👆 Selected segment (Label click): {file_name} [{start_time:.2f}s - {end_time:.2f}s]")
                self.waveform_viewer.plot_waveform(wav_path, start=start_time, end=end_time, zoom=True)
                self.selected_segment_info = (wav_path, start_time, end_time)

            else:
                print(f"👆 Selected segment (zoom): {file_name} [{start_time:.2f}s - {end_time:.2f}s]")
                self.waveform_viewer.plot_waveform(wav_path, start=start_time, end=end_time)
                self.selected_segment_info = (wav_path, start_time, end_time)

        except Exception as e:
            print(f"Error selecting row: {e}")

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Tab:
            current_row = self.table.currentRow()
            current_column = self.table.currentColumn()
            if current_row >= 0 and current_column >= 0:
                self.on_table_select(current_row, current_column)
                self.play_from_waveform()
            event.accept()
        else:
            super().keyPressEvent(event)

    def eventFilter(self, source, event):
        if source == self.table and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Tab:
                row = self.table.currentRow()
                col = self.table.currentColumn()

                if row >= 0 and col >= 0:
                    self.on_table_select(row, col)
                    self.play_from_waveform()
                    return True  # prevent default tab behavior

        return super().eventFilter(source, event)

    def play_from_waveform(self):
        try:
            if self.selected_segment_info is None:
                print("⚠️ No segment selected.")
                return

            wav_path, start_time, end_time = self.selected_segment_info

            if self.current_playback:
                self.current_playback.stop()

            print(f"🎵 Playing from waveform: {os.path.basename(wav_path)} [{start_time:.2f}s - {end_time if end_time else 'end'}]")
            self.current_playback = play_segment(wav_path, start_time, end_time)

        except Exception as e:
            print(f"Error in waveform playback: {e}")


    def toggle_editing(self, state):
        is_editable = state == 2
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.AllEditTriggers if is_editable
            else QTableWidget.EditTrigger.NoEditTriggers
        )

    def toggle_table_editing(self, state):
        is_editable = state == 2  # Qt.Checked
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.AllEditTriggers if is_editable else QTableWidget.EditTrigger.NoEditTriggers
        )

    def mark_as_modified(self, item):
        self.modified_cells.add((item.row(), item.column()))

        # 🟡 Aplica color visual a la celda modificada
        item.setBackground(QColor("#FFF3CD"))  # Un color amarillo claro

        # Solo mostrar advertencia si se edita la columna "File" por primera vez
        if item.column() == 0 and not self.file_edit_warning_shown:
            QMessageBox.warning(
                self, "Warning",
                "Changing the filename will rename both the .wav and .TextGrid files."
            )
            self.file_edit_warning_shown = True

    def closeEvent(self, event):
        if self.modified_cells:
            reply = QMessageBox.question(
                self, "Save changes?",
                "You have unsaved changes. Do you want to save them before quitting?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.save_table_edits()
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        event.accept()

    def save_table_edits(self):
        headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
        var_start = headers.index("Label") + 1
        var_end = headers.index("Start") if "Start" in headers else len(headers)

        for row, column in self.modified_cells:
            file_name = self.table.item(row, 0).text().strip()
            label = self.table.item(row, 1).text().strip()

            # Parse variables (between Label and Start)
            variable_values = [self.table.item(row, i).text().strip() for i in range(var_start, var_end)]
            full_label = "-".join(variable_values) if variable_values else label

            start = float(self.table.item(row, headers.index("Start")).text())
            end = float(self.table.item(row, headers.index("End")).text())

            for idx, (name, wav_path, tg_path) in enumerate(self.file_pairs):
                if name == self.tier_intervals[row][0] and name != file_name:
                    dir_path = os.path.dirname(tg_path)
                    new_wav = os.path.join(dir_path, file_name + ".wav")
                    new_tg = os.path.join(dir_path, file_name + ".TextGrid")

                    try:
                        os.rename(wav_path, new_wav)
                        os.rename(tg_path, new_tg)
                        self.file_pairs[idx] = (file_name, new_wav, new_tg)
                        self.tier_intervals[row][0] = file_name
                        print(f"✅ Renamed files to: {file_name}")
                    except Exception as e:
                        QMessageBox.critical(
                            self,
                            "Rename Failed",
                            f"❌ Failed to rename .wav or .TextGrid file:\n\n{e}"
                        )
                        continue  # Skip saving for this row if renaming failed

                elif name == file_name:
                    try:
                        tg = TextGrid.fromFile(tg_path)
                        tier_name = self.tier_dropdown.currentText()
                        tier = tg.getFirst(tier_name)

                        for interval in tier.intervals:
                            if abs(interval.minTime - start) < 0.001 and abs(interval.maxTime - end) < 0.001:
                                interval.mark = full_label
                                break

                        tg.write(tg_path)
                    except Exception as e:
                        print(f"Error saving to {tg_path}: {e}")

    def mouseDoubleClickEvent(self, event):
        # Verifica si se hizo doble clic sobre el header
        pos = event.position().toPoint()
        header = self.table.horizontalHeader()
        logical_index = header.logicalIndexAt(pos)
        
        # Sólo permitir renombrar las columnas extra añadidas dinámicamente
        if self.split_labels and logical_index >= 5:
            current_name = self.table.horizontalHeaderItem(logical_index).text()
            new_name, ok = QInputDialog.getText(self, "Renombrar columna", f"Nuevo nombre para '{current_name}':")
            if ok and new_name.strip():
                self.table.setHorizontalHeaderItem(logical_index, QTableWidgetItem(new_name.strip()))

