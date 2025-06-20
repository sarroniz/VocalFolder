import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QPushButton, QComboBox, QVBoxLayout,
    QHBoxLayout, QLabel, QFileDialog, QTableWidget, QTableWidgetItem,
    QMenuBar, QMenu, QCheckBox, QMessageBox, QInputDialog, QSizePolicy,
    QHeaderView, QToolButton, QSplitter, QListWidget, QListWidgetItem
)
import numpy as np
import parselmouth
import librosa
from PyQt6.QtGui import (QKeyEvent, QAction, QColor)
from PyQt6.QtCore import (Qt, QPoint)
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
    
def compute_mean_intensity(wav_path, start_time, end_time):
    try:
        print(f"🔍 Computing intensity: {os.path.basename(wav_path)} [{start_time}-{end_time}]")
        snd = parselmouth.Sound(wav_path)
        segment = snd.extract_part(from_time=start_time, to_time=end_time, preserve_times=True)
        intensity = segment.to_intensity()
        valid_vals = intensity.values[intensity.values > 0]
        if valid_vals.size == 0:
            print("⚠️ No positive intensity values.")
            return None
        mean_db = valid_vals.mean()
        print(f"✅ Mean dB: {mean_db}")
        return round(mean_db, 2)
    except Exception as e:
        print(f"❌ Error computing intensity: {e}")
        return None

def compute_zcr(wav_path, start_time, end_time):
    try:
        snd = parselmouth.Sound(wav_path)
        segment = snd.extract_part(from_time=start_time, to_time=end_time, preserve_times=False)
        samples = segment.values[0]  # mono

        if len(samples) < 2:
            return None

        zero_crossings = np.where(np.diff(np.signbit(samples)))[0]
        duration = segment.duration

        if duration == 0:
            return None

        zcr = len(zero_crossings) / duration
        print(f"🔍 ZCR: {zcr:.2f}")
        return round(zcr, 2)
    except Exception as e:
        print(f"❌ Error computing ZCR: {e}")
        return None

def compute_intensity_at_midpoint(wav_path, start_time, end_time):
    try:
        midpoint = (start_time + end_time) / 2
        snd = parselmouth.Sound(wav_path)

        # Puedes ajustar estos valores si lo deseas
        pitch_floor = 75  # typical for adult male speakers
        time_step = 0.01  # smaller for finer analysis

        intensity = snd.to_intensity(time_step=time_step, minimum_pitch=pitch_floor)
        intensity_value = intensity.get_value(time=midpoint)

        if intensity_value is None or intensity_value <= 0:
            print(f"⚠️ No valid intensity at midpoint ({midpoint}s)")
            return None

        print(f"🔍 Intensity at midpoint: {intensity_value:.2f} dB")
        return round(intensity_value, 2)

    except Exception as e:
        print(f"❌ Error computing midpoint intensity: {e}")
        return None
    

def compute_spectral_centroid(wav_path, start, end):
    try:
        y, sr = librosa.load(wav_path, sr=None, offset=start, duration=end - start)
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        if centroid.size > 0:
            return round(np.mean(centroid), 2)
    except Exception as e:
        print(f"❌ Error computing spectral centroid for {wav_path} [{start}-{end}]: {e}")
    return None
    
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Available features for the table
        # These are the features that can be computed and displayed in the table
        self.available_features = ["Duration", "Mid Intensity", "ZCR", "Spectral Centroid"]
        self.selected_features = set()  # Start with no features selected

        self.variable_column_indices = []
        self.active_filters = {}

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
        self.feature_selector = QListWidget()
        self.feature_selector.setMaximumWidth(200)
        self.feature_selector.setSelectionMode(QListWidget.SelectionMode.MultiSelection)

        self.variable_viewer = QListWidget()
        self.variable_viewer.setMaximumWidth(200)
        self.variable_viewer.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.variable_viewer.setDisabled(True)
        self.variable_viewer.addItem("🔍 No variables detected")

        for feat in self.available_features:
            item = QListWidgetItem(feat)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.feature_selector.addItem(item)

        self.feature_selector.itemChanged.connect(self.update_visible_features)
        self.waveform_viewer.waveformClicked.connect(self.play_from_waveform)

        self.load_button.clicked.connect(self.load_folder)
        self.tier_dropdown.currentIndexChanged.connect(self.on_tier_changed)
        self._need_to_rebuild_vars = True
        self.refresh_table()
        self.table.cellClicked.connect(self.on_table_select)
        self.table.currentCellChanged.connect(self.on_table_select)
        self.table.installEventFilter(self)
        self.table.horizontalHeader().sectionClicked.connect(self.show_filter_menu)


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

        # Left panel (table + waveform viewer)
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.addLayout(top_layout)
        left_layout.addWidget(self.table)
        left_layout.addWidget(self.waveform_viewer)
        left_panel.setLayout(left_layout)

        # Right panel (feature selector + variable viewer)
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Show Features:"))
        right_layout.addWidget(self.feature_selector)

        right_layout.addWidget(self.variable_viewer)

        right_layout.addStretch()
        right_panel.setLayout(right_layout)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([800, 200])

        self.setCentralWidget(splitter)

        self.variable_viewer.itemDoubleClicked.connect(self.rename_variable_column)
        self._need_to_rebuild_vars = True
        self._create_menus()

        self.resize(1200, 800)

    def showEvent(self, event):
        super().showEvent(event)
        self.resize(1600, 900)

    def on_tier_changed(self):
        # next refresh_table() will rebuild the Var… list
        self._need_to_rebuild_vars = True
        self.refresh_table()

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

        # Export menu
        file_menu = menubar.addMenu("File")
        export_action = QAction("Export Table to CSV…", self)
        export_action.triggered.connect(self.export_table_to_csv)
        file_menu.addAction(export_action)

    def update_visible_features(self):
        self.selected_features = set()
        for i in range(self.feature_selector.count()):
            item = self.feature_selector.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                self.selected_features.add(item.text())

        self.refresh_table()  # Re-render table with updated visible columns

    def build_variable_list(self):
        # block signals so we don’t immediately retrigger refresh_table()
        self.variable_viewer.blockSignals(True)
        self.variable_viewer.clear()

        if self.split_labels:
            max_parts = max(row[1].count("-") + 1 for row in self.tier_intervals)
            self.variable_viewer.setDisabled(False)
            for i in range(max_parts):
                item = QListWidgetItem(f"Var{i+1}")
                item.setFlags(
                    Qt.ItemFlag.ItemIsEnabled |
                    Qt.ItemFlag.ItemIsUserCheckable |
                    Qt.ItemFlag.ItemIsSelectable
                )
                item.setCheckState(Qt.CheckState.Unchecked)
                self.variable_viewer.addItem(item)
        else:
            self.variable_viewer.addItem("🔍 No variables detected")
            self.variable_viewer.setDisabled(True)

        self.variable_viewer.blockSignals(False)
        # now connect its signal so clicking a var triggers refresh_table()
        self.variable_viewer.itemChanged.connect(self.refresh_table)

    def load_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if not folder:
            return

        self.file_pairs = load_file_pairs(folder)

        # Shows truncated folder path in the label
        short_path = shorten_path(folder)
        self.folder_label.setText(short_path)
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
        self.on_tier_changed() 

    def refresh_table(self):
        if not self.file_pairs:
            return

        selected_tier = self.tier_dropdown.currentText()
        self.tier_intervals = []

        label_has_dash = False

        for name, wav_path, tg_path in self.file_pairs:
            try:
                intervals = extract_intervals(tg_path, tier_name=selected_tier)
                for intv in intervals:
                    label = intv['label']
                    if '-' in label:
                        label_has_dash = True
                    start = float(intv['start'])
                    end = float(intv['end'])
                    duration = round(end - start, 4)

                    self.tier_intervals.append([
                        name, label, start, end, duration
                    ])
            except Exception as e:
                print(f"Error parsing {tg_path}: {e}")

        if not self.tier_intervals:
            print(f"⚠️ No intervals found for tier: '{selected_tier}'")

        # Decide whether to split variables automatically
        self.split_labels = label_has_dash

        # only rebuild Var… checkboxes when the tier selection actually changes
        if self._need_to_rebuild_vars:
            self.build_variable_list()
            self._need_to_rebuild_vars = False

        try:
            self.table.itemChanged.disconnect(self.mark_as_modified)
        except Exception:
            pass

        base_headers = ["File", "Interval"]
        feature_headers = [f for f in self.available_features if f in self.selected_features]
        variable_headers = []

        if self.split_labels:
            variable_headers = [
                self.variable_viewer.item(i).text()
                for i in range(self.variable_viewer.count())
                if self.variable_viewer.item(i).checkState() == Qt.CheckState.Checked
            ]

        headers = base_headers + variable_headers + feature_headers
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(self.tier_intervals))
        self.table.verticalHeader().setMinimumSectionSize(30)

        for i, row in enumerate(self.tier_intervals):
            name, label, start, end, duration = row
            wav_path = self._get_wav_path(name)

            self.table.setItem(i, 0, QTableWidgetItem(name))   # File
            self.table.setItem(i, 1, QTableWidgetItem(label))  # Label

            offset = 2
            if self.split_labels:
                parts = label.split("-")
                for k, part in enumerate(parts):
                    variable_item = self.variable_viewer.item(k)
                    if variable_item and variable_item.checkState() == Qt.CheckState.Checked:
                        self.table.setItem(i, offset, QTableWidgetItem(part))
                        offset += 1


            feature_index = 0
            for feature in self.available_features:
                if feature not in self.selected_features:
                    continue

                if feature == "Duration":
                    value = duration

                elif feature == "Mid Intensity":
                    value = compute_intensity_at_midpoint(wav_path, start, end)

                elif feature == "ZCR":
                    value = compute_zcr(wav_path, start, end)

                elif feature == "Spectral Centroid":
                    value = compute_spectral_centroid(wav_path, start, end)

                else:
                    value = ""

                item = QTableWidgetItem(str(value) if value is not None else "")
                self.table.setItem(i, offset + feature_index, item)
                feature_index += 1

        self.modified_cells.clear()
        self.table.itemChanged.connect(self.mark_as_modified)

        # Update variable column indices
        self.update_variable_column_indices()

        if self.variable_column_indices:
            self.add_filter_buttons_to_headers(
                min(self.variable_column_indices),
                max(self.variable_column_indices) + 1
            )

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

            elif header == "Interval":
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
    
    def show_filter_menu(self, col):
        if col not in getattr(self, "variable_column_indices", []):
            return

        unique_values = set()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, col)
            if item:
                unique_values.add(item.text())

        if col not in self.active_filters:
            self.active_filters[col] = set(unique_values)

        menu = QMenu(self)
        for val in sorted(unique_values):
            action = QAction(val, self)
            action.setCheckable(True)
            action.setChecked(val in self.active_filters[col])
            action.toggled.connect(lambda checked, v=val, c=col: self._apply_column_filter(c, v, checked))
            menu.addAction(action)

        header = self.table.horizontalHeader()
        section_pos = header.sectionViewportPosition(col)
        global_pos = self.table.mapToGlobal(header.pos()) + QPoint(section_pos, header.height())
        menu.exec(global_pos)

    def add_filter_buttons_to_headers(self, variable_start_idx, variable_end_idx):
        self.variable_column_indices = list(range(variable_start_idx, variable_end_idx))
        header = self.table.horizontalHeader()
        header.sectionClicked.connect(self.show_filter_menu)

    def update_variable_column_indices(self):
        self.variable_column_indices = []
        headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
        for i, header in enumerate(headers):
            if header.startswith("Var"):
                self.variable_column_indices.append(i)

    def _get_wav_path(self, file_name):
        for name, wav, _ in self.file_pairs:
            if name == file_name:
                return wav
        return None

    def _apply_column_filter(self, col, value, checked):
        if col not in self.active_filters:
            self.active_filters[col] = set()

        if checked:
            self.active_filters[col].add(value)
        else:
            self.active_filters[col].discard(value)

        allowed_values = self.active_filters[col]
        for row in range(self.table.rowCount()):
            item = self.table.item(row, col)
            if item:
                self.table.setRowHidden(row, item.text() not in allowed_values)

        # Cambia el nombre del header si hay filtro activo
        header_item = self.table.horizontalHeaderItem(col)
        base_text = header_item.text().replace(" 🔽", "").replace(" 🔽 (filtered)", "")
        if len(self.active_filters[col]) < len(set(self.table.item(r, col).text() for r in range(self.table.rowCount()) if self.table.item(r, col))):
            header_item.setText(f"{base_text} 🔽 (filtered)")
        else:
            header_item.setText(f"{base_text} 🔽")

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
        var_start = headers.index("Interval") + 1
        var_end = headers.index("Start") if "Start" in headers else len(headers)

        for row, column in self.modified_cells:
            file_name = self.table.item(row, 0).text().strip()
            label = self.table.item(row, 1).text().strip()

            # Parse variables (between Label and Start)
            variable_values = [self.table.item(row, i).text().strip() for i in range(var_start, var_end)]
            full_label = "-".join(variable_values) if variable_values else label

            start = float(self.tier_intervals[row][2])
            end = float(self.tier_intervals[row][3])

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

    def export_table_to_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "", "CSV Files (*.csv)")
        if not path:
            return

        try:
            headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]

            with open(path, "w", encoding="utf-8") as f:
                # Write headers
                f.write(",".join(headers) + "\n")

                # Write rows
                for row in range(self.table.rowCount()):
                    row_data = []
                    for col in range(self.table.columnCount()):
                        item = self.table.item(row, col)
                        value = item.text() if item else ""
                        value = value.replace(",", " ")  # avoid breaking CSV
                        row_data.append(value)
                    f.write(",".join(row_data) + "\n")

            QMessageBox.information(self, "Export Successful", f"Table exported successfully to:\n{path}")

        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"❌ Error exporting CSV:\n\n{e}")

    def rename_variable_column(self, item):
        old_name = item.text()
        new_name, ok = QInputDialog.getText(self, "Rename Variable", f"Rename '{old_name}' to:")
        if ok and new_name.strip():
            item.setText(new_name.strip())

            # Actualiza también los headers si ya están en la tabla
            headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
            if old_name in headers:
                col_idx = headers.index(old_name)
                self.table.setHorizontalHeaderItem(col_idx, QTableWidgetItem(new_name.strip()))


