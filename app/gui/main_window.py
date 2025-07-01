import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QPushButton, QComboBox, QVBoxLayout,
    QHBoxLayout, QLabel, QFileDialog, QTableWidget, QTableWidgetItem,
    QMenuBar, QMenu, QCheckBox, QMessageBox, QInputDialog, QSizePolicy,
    QHeaderView, QToolButton, QSplitter, QListWidget, QListWidgetItem,
    QApplication, QDialog, QLineEdit, QDialogButtonBox, QGroupBox, QScrollArea, 
    QFormLayout, QFrame, QStackedLayout
)
import numpy as np
import json
import parselmouth
import librosa
from PyQt6.QtGui import (QKeyEvent, QAction, QColor)
from PyQt6.QtCore import (Qt, QPoint, QTimer,QSize)
from app.core.file_loader import load_file_pairs
from app.core.textgrid_parser import extract_intervals
from textgrid import TextGrid
from app.core.audio_player import play_segment
from app.gui.waveform_viewer import WaveformViewer
from PyQt6.QtGui import QIcon
from app.core.feature_extractor import compute_feature_value
from app.utils.filters import (
    get_unique_values_for_column,
    create_filter_menu,
    show_menu_near_column
)
import pandas as pd
from app.utils.external_tools import launch_praat
from app.utils.column_stats_panel import ColumnStatsPanel


def shorten_path(path: str, max_chars: int = 60) -> str:
    if len(path) <= max_chars:
        return path
    else:
        return f"{path[:25]}…{path[-30:]}"
    

def safe_table_operation(func):
    """Decorator for safe table operations"""
    def wrapper(self, *args, **kwargs):
        try:
            if hasattr(self, 'table') and self.table.rowCount() > 0:
                return func(self, *args, **kwargs)
        except Exception as e:
            print(f"Safe table operation failed: {e}")
            return None
    return wrapper


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', '..')
        )
        icon_path = os.path.join(base_dir, 'assets', 'icons', 'vocalfolder_icon.png')
        self.setWindowIcon(QIcon(icon_path))

        # Available features for the table
        self.available_features = [
            "Duration",
            "Mid Intensity",
            "Mean F0",
            "Jitter",
            "Shimmer",
            "HNR",
            "RMS Energy",
            "Spectral Centroid",
            "Spectral Rolloff",
            "Spectral Bandwidth",
            "Spectral Flatness",
            "Spectral Contrast",
            "MFCC1",
            "CPP",
            "ZCR",
            "F1",
            "F2",
            "F3",
        ]
        self.selected_features = set()

        self.variable_column_indices = []
        self.active_filters = {}
        
        # Improved filtering system
        self.filter_update_timer = None
        self.is_filtering = False
        self.cached_unique_values = {}
        self._active_filter_menu = None
        self.filter_debounce_delay = 200  # ms delay for filter updates

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
        self.variable_viewer.setFrameShape(QFrame.Shape.NoFrame)

        self.variable_placeholder_label = QLabel("🔍 No variables detected — labels with '-' will appear here as separate columns")
        self.variable_placeholder_label.setWordWrap(True)
        self.variable_placeholder_label.setStyleSheet("color: #444; font-style: italic; padding: 5px;")
        self.variable_placeholder_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        # Contenedor para controlar tamaño real del QLabel
        self.variable_placeholder = QWidget()
        placeholder_layout = QVBoxLayout(self.variable_placeholder)
        placeholder_layout.addWidget(self.variable_placeholder_label)
        placeholder_layout.setContentsMargins(0, 0, 0, 0)
        placeholder_layout.setSpacing(0)

        self.variable_placeholder.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.variable_placeholder.setMaximumHeight(self.variable_placeholder_label.sizeHint().height() + 10)

        self.variable_viewer.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.variable_viewer.setMaximumHeight(self.variable_viewer.sizeHintForRow(0) * self.variable_viewer.count() + 10)

        if self.variable_viewer.count() == 0:
            self.variable_viewer.setMaximumHeight(0)

        for feat in self.available_features:
            item = QListWidgetItem(feat)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.feature_selector.addItem(item)

        self.feature_selector.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.feature_selector.setMaximumHeight(self.feature_selector.sizeHintForRow(0) * self.feature_selector.count() + 10)

        self.feature_selector.itemChanged.connect(self.update_visible_features)
        self.waveform_viewer.waveformClicked.connect(self.play_from_waveform)

        self.load_button.clicked.connect(self.load_folder)
        self.tier_dropdown.currentIndexChanged.connect(self.on_tier_changed)
        self._need_to_rebuild_vars = True
        self.refresh_table()
        self.table.cellClicked.connect(self.on_table_select)
        self.table.currentCellChanged.connect(self.on_table_select)
        self.table.installEventFilter(self)
        # self.table.horizontalHeader().sectionClicked.connect(self.show_filter_menu)
        header = self.table.horizontalHeader()
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(self.on_header_context_menu)

        self.toggle_table_editing(0)

        self.current_playback = None
        self.selected_segment_info = None

        # UI Layout
        self._setup_ui()
        self._create_menus()

        self.praat_path = None  # Personalized Praat path
        self._load_user_settings()

        self.resize(1200, 800)
    
        self.table.horizontalHeader().sectionClicked.connect(self.on_column_header_clicked)

    def _setup_ui(self):
        """Setup the main UI layout"""
        # Row 1: Load button + folder path
        top_row1 = QHBoxLayout()

        folder_label = QLabel("Working Directory:")
        folder_label.setStyleSheet("font-weight: bold; margin-right: 5px;")

        self.load_button.setFixedWidth(120)

        top_row1.addWidget(folder_label)
        top_row1.addWidget(self.load_button)
        top_row1.addWidget(self.folder_label)
        top_row1.addStretch()

        # Open in Praat button
        self.open_in_praat_button = QPushButton("Open in Praat")
        self.open_in_praat_button.setEnabled(False)
        self.open_in_praat_button.clicked.connect(self.open_in_praat)
        top_row1.addWidget(self.open_in_praat_button)

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
        features_group = QGroupBox("Show Features")
        features_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 3px;
            }
        """)
        features_layout = QVBoxLayout()
        features_layout.setContentsMargins(10, 10, 10, 10)
        features_layout.setSpacing(5)
        features_layout.addWidget(self.feature_selector)
        features_group.setLayout(features_layout)

        # ——— Extracted Variables (single, nicely styled group) ———
        variables_group = QGroupBox("Extracted Variables")
        variables_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 3px;
            }
        """)

        # stack of either the placeholder label or the real list
        self.variable_stack = QStackedLayout()
        self.variable_stack.addWidget(self.variable_placeholder)
        self.variable_stack.addWidget(self.variable_viewer)

        var_layout = QVBoxLayout()
        var_layout.setContentsMargins(10, 10, 10, 10)
        var_layout.setSpacing(5)
        var_layout.addLayout(self.variable_stack)

        variables_group.setLayout(var_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        scroll_layout.setSpacing(25)
        scroll_layout.addWidget(features_group)
        scroll_layout.addWidget(variables_group)
        scroll_layout.addStretch()
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)

        right_panel = QWidget()
        self.right_layout = QVBoxLayout()
        self.right_layout.addWidget(scroll_area)
        self.column_stats_panel = ColumnStatsPanel()
        self.right_layout.addWidget(self.column_stats_panel)

        right_panel.setLayout(self.right_layout)
        self.right_panel = right_panel

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([800, 200])

        self.setCentralWidget(splitter)

        self.variable_viewer.itemDoubleClicked.connect(self.rename_variable_column)
        self._need_to_rebuild_vars = True

    def showEvent(self, event):
        super().showEvent(event)
        self.resize(1600, 900)

    def open_in_praat(self):
        """Open selected file (wav + TextGrid) in Praat using external launcher"""
        try:
            if not hasattr(self, 'selected_file_name') or not self.selected_file_name:
                QMessageBox.warning(self, "No file selected", "Select a row in the table first.")
                return

            for name, wav_path, tg_path in self.file_pairs:
                if name == self.selected_file_name:
                    break
            else:
                QMessageBox.warning(self, "File not found", "Could not locate file paths.")
                return

            success, error = launch_praat(wav_path, tg_path, praat_path=self.praat_path)

            if not success:
                QMessageBox.critical(self, "Failed to Launch Praat", error)

        except Exception as e:
            print(f"❌ Error opening in Praat: {e}")
            QMessageBox.critical(self, "Error", f"Could not open in Praat:\n{e}")

    def on_tier_changed(self, index=None):
        if index is None:
            index = self.tier_dropdown.currentIndex()

        if index < 0 or index >= len(self._raw_tiers):
            return

        tier_name = self._raw_tiers[index]
        self.current_tier = tier_name
        self.refresh_table()

    def _create_menus(self):
        """Create application menus"""
        menubar = self.menuBar()

        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        undo_action = QAction("Undo", self)
        undo_action.triggered.connect(lambda: self.table.undo())
        redo_action = QAction("Redo", self)
        redo_action.triggered.connect(lambda: self.table.redo())
        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(lambda: self.table.copy())
        paste_action = QAction("Paste", self)
        paste_action.triggered.connect(lambda: self.table.paste())

        edit_menu.addAction(undo_action)
        edit_menu.addAction(redo_action)
        edit_menu.addSeparator()
        edit_menu.addAction(copy_action)
        edit_menu.addAction(paste_action)

        # File menu
        file_menu = menubar.addMenu("File")
        export_action = QAction("Export Table to CSV…", self)
        export_action.triggered.connect(self.export_table_to_csv)
        file_menu.addAction(export_action)

        set_path_action = QAction("Set Praat Path…", self)
        set_path_action.triggered.connect(self.set_praat_path)
        file_menu.addAction(set_path_action)
        
        # Filter menu
        filter_menu = menubar.addMenu("Filters")
        clear_filters_action = QAction("Clear All Filters", self)
        clear_filters_action.triggered.connect(self.clear_all_filters)
        filter_menu.addAction(clear_filters_action)

        # Spectrogram menu
        spectrogram_menu = self.menuBar().addMenu("Spectrogram")

        # Color map actions
        cmap_menu = spectrogram_menu.addMenu("Color Map")
        for cmap_name in ['viridis', 'magma', 'plasma', 'gray']:
            action = cmap_menu.addAction(cmap_name)
            action.triggered.connect(lambda checked, cmap=cmap_name: self.set_spec_colormap(cmap))

        # Frequency limits action
        freq_limits_action = spectrogram_menu.addAction("Set Frequency Limits...")
        freq_limits_action.triggered.connect(self.set_spec_freq_limits)

        # Reset frequency limits action
        reset_action = spectrogram_menu.addAction("Reset Frequency Limits")
        reset_action.triggered.connect(self.reset_spec_freq_limits)

        # Features menu
        features_menu = self.menuBar().addMenu("Features")

        # Submenú para modo de extracción de formantes
        formant_mode_menu = features_menu.addMenu("Formant Extraction Mode")

        midpoint_action = formant_mode_menu.addAction("Midpoint (default)")
        midpoint_action.setCheckable(True)
        midpoint_action.setChecked(True)
        midpoint_action.triggered.connect(lambda: self.set_formant_mode("midpoint"))

        mean_action = formant_mode_menu.addAction("Mean over interval")
        mean_action.setCheckable(True)
        mean_action.setChecked(False)
        mean_action.triggered.connect(lambda: self.set_formant_mode("mean"))

        # Para que se comporten como radio buttons
        formant_mode_menu_group = [midpoint_action, mean_action]


    def update_visible_features(self):
        """Update which features are visible in the table"""
        self.selected_features = set()
        for i in range(self.feature_selector.count()):
            item = self.feature_selector.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                self.selected_features.add(item.text())

        self.refresh_table()

    def _show_no_variable_message(self):
        """Display a placeholder message when no variables are detected"""
        item = QListWidgetItem()
        item.setText("🔍 No variables detected — labels with '-' will appear here as separate columns")
        item.setForeground(QColor("#444"))

        font = item.font()
        font.setItalic(True)
        item.setFont(font)

        item.setTextAlignment(Qt.AlignmentFlag.AlignLeft)
        item.setSizeHint(QSize(item.sizeHint().width(), 40))

        self.variable_viewer.addItem(item)

    def build_variable_list(self):
        """Detect and display variables extracted from hyphenated labels."""
        # 1) clear old items
        self.variable_viewer.clear()

        # 2) if no splitting, show placeholder
        if not getattr(self, "split_labels", False) \
        or not getattr(self, "current_data", None) \
        or "Label" not in self.current_data[0]:
            self.variable_stack.setCurrentIndex(0)
            self.variable_viewer.setDisabled(True)
            return

        # 3) gather only the hyphenated rows
        split_rows = [r["Label"].split("-")
                    for r in self.current_data
                    if "-" in r["Label"]]
        if not split_rows:
            self.variable_stack.setCurrentIndex(0)
            self.variable_viewer.setDisabled(True)
            return

        # 4) compute how many VarN columns
        max_parts = max(len(parts) for parts in split_rows)
        self.variable_columns = [f"Var{i+1}" for i in range(max_parts)]

        # 5) show the real list
        self.variable_stack.setCurrentIndex(1)
        self.variable_viewer.setDisabled(False)

        # 6) add each VarN as an UNCHECKED item by default
        for col_name in self.variable_columns:
            item = QListWidgetItem(col_name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.variable_viewer.addItem(item)

        # 7) cap the visible height to 6 rows
        max_visible = min(len(self.variable_columns), 6)
        row_h = self.variable_viewer.sizeHintForRow(0)
        self.variable_viewer.setMaximumHeight(max_visible * row_h + 4)

        # 8) reconnect so toggles rebuild the table
        try:
            self.variable_viewer.itemChanged.disconnect(self.refresh_table)
        except Exception:
            pass
        self.variable_viewer.itemChanged.connect(self.refresh_table)

    def load_folder(self):
        """Load folder containing audio and TextGrid files"""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if not folder:
            return

        try:
            self.file_pairs = load_file_pairs(folder)
            if not self.file_pairs:
                QMessageBox.warning(self, "No Files",
                    "No matching audio and TextGrid files found in the selected folder.")
                return

            # Show truncated folder path
            short_path = shorten_path(folder)
            self.folder_label.setText(short_path)
            self.folder_label.setToolTip(folder)

            # Gather the set of IntervalTier names from each file
            tier_name_sets = []
            for _, _, tg_path in self.file_pairs:
                try:
                    tg = TextGrid.fromFile(tg_path)
                    names = [t.name for t in tg.tiers if t.__class__.__name__ == "IntervalTier"]
                    tier_name_sets.append(set(names))
                except Exception as e:
                    print(f"Error reading {tg_path}: {e}")

            if not tier_name_sets:
                QMessageBox.warning(self, "No Tiers",
                    "No valid IntervalTier found in the TextGrid files.")
                return

            # Compute common tiers and keep their raw names
            self._raw_tiers = sorted(set.union(*tier_name_sets))

            # Populate dropdown as “Tier 1: name”, etc.
            try:
                self.tier_dropdown.currentIndexChanged.disconnect(self.on_tier_changed)
            except Exception:
                pass

            self.tier_dropdown.clear()
            for i, name in enumerate(self._raw_tiers, start=1):
                self.tier_dropdown.addItem(f"Tier {i}: {name}")

            self.tier_dropdown.currentIndexChanged.connect(self.on_tier_changed)

            # Select the first tier by default
            if self._raw_tiers:
                self.tier_dropdown.setCurrentIndex(0)
                self.on_tier_changed()

            # Immediately populate the table
            self.refresh_table()

        except Exception as e:
            print(f"Error loading folder: {e}")
            QMessageBox.warning(self, "Error",
                f"Failed to load folder:\n{e}")

    def refresh_table(self):
        """Refresh the table with current data and settings"""
        self._clear_filter_cache()

        if not self.file_pairs or not hasattr(self, "_raw_tiers"):
            return

        # Determine selected tier...
        idx = self.tier_dropdown.currentIndex()
        if idx < 0 or idx >= len(self._raw_tiers):
            return
        selected_tier = self._raw_tiers[idx]

        self.tier_intervals = []
        label_has_dash = False
        current_data = []

        # Gather intervals & detect hyphens
        for name, wav_path, tg_path in self.file_pairs:
            try:
                intervals = extract_intervals(tg_path, tier_name=selected_tier)
            except ValueError:
                continue

            for intv in intervals:
                lab = intv["label"]
                if "-" in lab:
                    label_has_dash = True
                start = float(intv["start"])
                end   = float(intv["end"])
                dur   = round(end - start, 4)

                self.tier_intervals.append([name, lab, start, end, dur])
                current_data.append({
                    "File": name,
                    "Label": lab,
                    "Start": start,
                    "End": end,
                    "Duration": dur
                })

        if not self.tier_intervals:
            print(f"⚠️ No intervals found for tier '{selected_tier}'")
            return

        # ← Set both the raw data *and* the split flag
        self.current_data = current_data
        self.split_labels = label_has_dash

        # only rebuild the variable‐viewer if our "dash in labels" state actually changed
        if not hasattr(self, '_last_label_dash_state') \
           or self._last_label_dash_state != label_has_dash:
            self.build_variable_list()

        self._last_label_dash_state = label_has_dash

        # …then do the usual table recreation…
        try:
            self.table.itemChanged.disconnect(self.mark_as_modified)
        except Exception:
            pass

        self._build_table_structure()
        self._populate_table_data()

        self.table.itemChanged.connect(self.mark_as_modified)
        self.modified_cells.clear()

        self.update_variable_column_indices()
        if self.active_filters:
            self._apply_all_filters()
        

    def _build_table_structure(self):
        """Build the table structure with headers and columns"""
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

    def _populate_table_data(self):
        """Populate table with data"""
        for i, row in enumerate(self.tier_intervals):
            name, label, start, end, duration = row
            wav_path = self._get_wav_path(name)

            # Basic columns
            self.table.setItem(i, 0, QTableWidgetItem(name))
            self.table.setItem(i, 1, QTableWidgetItem(label))

            offset = 2

            # Variable columns
            if self.split_labels:
                parts = label.split("-")
                for k, part in enumerate(parts):
                    if k < self.variable_viewer.count():
                        variable_item = self.variable_viewer.item(k)
                        if variable_item and variable_item.checkState() == Qt.CheckState.Checked:
                            self.table.setItem(i, offset, QTableWidgetItem(part))
                            offset += 1

            # Feature columns
            feature_index = 0
            for feature in self.available_features:
                if feature not in self.selected_features:
                    continue

                value = compute_feature_value(feature, wav_path, start, end, duration)
                item = QTableWidgetItem(str(value) if value is not None else "")
                self.table.setItem(i, offset + feature_index, item)
                feature_index += 1

    def _get_wav_path(self, name):
        """Get WAV path for a given file name"""
        for file_name, wav_path, _ in self.file_pairs:
            if file_name == name:
                return wav_path
        return None

    def show_filter_menu(self, col):
        """Show filter menu for a column"""
        if (col < 0 or col >= self.table.columnCount() or 
            col not in self.variable_column_indices):
            return

        if self._active_filter_menu is not None:
            return

        try:
            unique_values = get_unique_values_for_column(self.table, col)
            if not unique_values:
                return

            if col not in self.active_filters:
                self.active_filters[col] = set(unique_values)

            def filter_callback(action, column, value=None, state=None):
                if action == "select_all":
                    self.active_filters[column] = set(value)
                elif action == "clear_all":
                    self.active_filters[column] = set()
                elif action == "toggle":
                    if state:
                        self.active_filters[column].add(value)
                    else:
                        self.active_filters[column].discard(value)
                self._queue_filter_update()

            menu = create_filter_menu(self, col, unique_values, self.active_filters, filter_callback)
            if menu:
                self._active_filter_menu = menu
                menu.aboutToHide.connect(self._on_filter_menu_close)
                show_menu_near_column(self.table, menu, col)
        except Exception as e:
            print(f"❌ Error showing filter menu: {e}")

    def _filter_callback(self, action, col, value=None, state=None):
        if action == "select_all":
            # value is the full set passed by create_filter_menu
            vals = value or self.cached_unique_values.get(col, [])
            self.active_filters[col] = set(vals)

        elif action == "clear_all":
            self.active_filters[col] = set()

        elif action == "toggle":
            # **initialize** to the full set on the first toggle
            if col not in self.active_filters:
                self.active_filters[col] = set(self.cached_unique_values.get(col, []))
            s = self.active_filters[col]
            if state:
                s.add(value)
            else:
                s.discard(value)

        # re‐apply filters
        self._queue_filter_update()

    def _on_filter_menu_close(self):
        """Handle filter menu close"""
        self._active_filter_menu = None

    def _select_all_filter_items(self, col, unique_values):
        """Select all items in filter"""
        try:
            self.active_filters[col] = set(unique_values)
            self._queue_filter_update()
        except Exception as e:
            print(f"Error selecting all filter items: {e}")

    def _clear_all_filter_items(self, col):
        """Clear all items in filter"""
        try:
            self.active_filters[col] = set()
            self._queue_filter_update()
        except Exception as e:
            print(f"Error clearing all filter items: {e}")

    def _update_filter_value(self, col, value, checked):
        """Update a single filter value"""
        try:
            if col not in self.active_filters:
                self.active_filters[col] = set()

            if checked:
                self.active_filters[col].add(value)
            else:
                self.active_filters[col].discard(value)

            self._queue_filter_update()
            
        except Exception as e:
            print(f"Error updating filter value: {e}")

    def _queue_filter_update(self):
        """Queue a filter update with debouncing"""
        try:
            # Cancel existing timer
            if self.filter_update_timer is not None:
                self.filter_update_timer.stop()
                self.filter_update_timer = None

            # Create new timer
            self.filter_update_timer = QTimer(self)
            self.filter_update_timer.setSingleShot(True)
            self.filter_update_timer.timeout.connect(self._apply_all_filters)
            self.filter_update_timer.start(self.filter_debounce_delay)
            
        except Exception as e:
            print(f"Error queuing filter update: {e}")

    def _apply_all_filters(self):
        """Apply all active filters using small delayed batches to keep GUI responsive"""
        if self.is_filtering:
            return

        self.is_filtering = True
        self.table.blockSignals(True)

        self._current_filter_batch = 0
        self._total_filter_batches = self.table.rowCount() // 50 + 1
        self._filter_batch_size = 50

        def process_next_batch():
            if self._current_filter_batch >= self._total_filter_batches:
                self.table.blockSignals(False)
                self.is_filtering = False
                self._update_filter_headers()
                self._current_filter_batch = 0
                return

            start_row = self._current_filter_batch * self._filter_batch_size
            end_row = min(start_row + self._filter_batch_size, self.table.rowCount())

            for row in range(start_row, end_row):
                should_hide = self._should_hide_row(row)
                self.table.setRowHidden(row, should_hide)

            self._current_filter_batch += 1
            QTimer.singleShot(1, process_next_batch)  # delay in ms

        QTimer.singleShot(0, process_next_batch)

    def _should_hide_row(self, row):
        """Determine if a row should be hidden based on active filters"""
        try:
            for col, allowed_values in self.active_filters.items():
                if not allowed_values:  # Empty filter = hide all
                    return True
                    
                item = self.table.item(row, col)
                if not item or item.text().strip() not in allowed_values:
                    return True
                    
            return False
        except Exception as e:
            print(f"Error checking row visibility: {e}")
            return False

    def _update_filter_headers(self):
        """Update column headers to show filter status"""
        try:
            for col in self.variable_column_indices:
                header_item = self.table.horizontalHeaderItem(col)
                if not header_item:
                    continue
                    
                # Clean existing filter indicators
                base_text = header_item.text()
                for suffix in [" 🔽", " (filtered)", " (none)"]:
                    base_text = base_text.replace(suffix, "")
                
                # Add appropriate indicator
                if col in self.active_filters:
                    total_unique = len(self.cached_unique_values.get(col, set()))
                    active_count = len(self.active_filters[col])
                    
                    if active_count == 0:
                        header_item.setText(f"{base_text} 🔽 (none)")
                    elif active_count < total_unique:
                        header_item.setText(f"{base_text} 🔽 (filtered)")
                    else:
                        header_item.setText(f"{base_text} 🔽")
                else:
                    header_item.setText(f"{base_text} 🔽")
                    
        except Exception as e:
            print(f"Error updating filter headers: {e}")

    def clear_all_filters(self):
        """Clear all active filters"""
        try:
            # Clear filter state
            self.active_filters.clear()
            self._clear_filter_cache()
            
            # Show all rows
            for row in range(self.table.rowCount()):
                self.table.setRowHidden(row, False)
            
            # Clean up headers
            self._clean_filter_headers()
            
        except Exception as e:
            print(f"Error clearing filters: {e}")

    def _clear_filter_cache(self):
        """Clear the filter cache"""
        self.cached_unique_values.clear()

    def _clean_filter_headers(self):
        """Clean filter indicators from headers"""
        try:
            for col in self.variable_column_indices:
                header_item = self.table.horizontalHeaderItem(col)
                if header_item:
                    base_text = header_item.text()
                    for suffix in [" 🔽", " (filtered)", " (none)"]:
                        base_text = base_text.replace(suffix, "")
                    header_item.setText(f"{base_text} 🔽")
        except Exception as e:
            print(f"Error cleaning filter headers: {e}")

    def update_variable_column_indices(self):
        """Update the list of variable column indices"""
        try:
            self.variable_column_indices = []
            headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
            for i, header in enumerate(headers):
                if header.startswith("Var") and not header.endswith("(filtered)") and not header.endswith("(none)"):
                    self.variable_column_indices.append(i)
        except Exception as e:
            print(f"Error updating variable column indices: {e}")

    def on_table_select(self, row, column, *_):
        """Handle table cell selection"""
        try:
            if row < 0 or column < 0 or row >= len(self.tier_intervals):
                return
            
            header = self.table.horizontalHeaderItem(column)
            if not header:
                return
                
            header_text = header.text()
            print(f"🧪 Table clicked: row={row}, column={column}, header={header_text}")
            
            entry = self.tier_intervals[row]
            file_name = entry[0]
            
            # Find matching wav path
            wav_path = None
            for name, wav, *_ in self.file_pairs:
                if name == file_name:
                    wav_path = wav
                    break
                    
            if not wav_path:
                print(f"⚠️ Could not find WAV file for: {file_name}")
                return
            
            self.selected_file_name = file_name
            self.open_in_praat_button.setEnabled(True)
                
            start_time = float(entry[2])
            end_time = float(entry[3])
            
            if header_text == "File":
                # File column clicked: show full file view with interval highlighted
                print(f"👆 Selected file with interval highlight: {file_name} (highlighting [{start_time:.2f}s - {end_time:.2f}s])")
                
                # Plot full waveform first
                self.waveform_viewer.plot_waveform(wav_path, start=None, end=None, zoom=False)
                
                # Then add highlight for the specific interval
                self.waveform_viewer.highlight_interval(start_time, end_time)
                
                # Set segment info for playback (full file)
                self.selected_segment_info = (wav_path, None, None)
                
            elif header_text == "Interval":
                # Interval column clicked: zoom to interval (existing behavior)
                print(f"👆 Selected segment (Label click): {file_name} [{start_time:.2f}s - {end_time:.2f}s]")
                self.waveform_viewer.plot_waveform(wav_path, start=start_time, end=end_time, zoom=True)
                self.selected_segment_info = (wav_path, start_time, end_time)
                
            else:
                # Other columns clicked: zoom to interval (existing behavior)
                print(f"👆 Selected segment (zoom): {file_name} [{start_time:.2f}s - {end_time:.2f}s]")
                self.waveform_viewer.plot_waveform(wav_path, start=start_time, end=end_time, zoom=True)
                self.selected_segment_info = (wav_path, start_time, end_time)
                
        except Exception as e:
            print(f"Error in table selection: {e}")

    def play_from_waveform(self, time_position=None):
        """
        If time_position is None (e.g. Tab key), play the entire selected segment (or file).
        If time_position is a float, play based on the current selection mode:
        - If full file is selected (start_time=None, end_time=None): play entire file
        - If segment is selected: play 1-second snippet from click position within segment
        """
        try:
            if not self.selected_segment_info:
                print("⚠️ No segment selected for playback")
                return

            wav_path, start_time, end_time = self.selected_segment_info
            
            # Import the updated audio player
            from app.core.audio_player import play_segment, stop_playback
            
            # Stop any existing playback
            stop_playback()

            if time_position is None:
                # Tab key or programmatic call → play full segment (or full file)
                if start_time is None and end_time is None:
                    # Full file playback
                    print(f"🔊 Playing full file: {wav_path}")
                    self.current_playback = play_segment(wav_path, 0.0, None)
                else:
                    # Play the selected interval
                    print(f"🔊 Playing interval: {start_time:.2f}s - {end_time:.2f}s")
                    self.current_playback = play_segment(wav_path, start_time, end_time)
            else:
                # Mouse click on waveform
                click_time = float(time_position)
                
                if start_time is None and end_time is None:
                    # Full file is selected → always play entire file regardless of click position
                    print(f"🔊 Playing full file (clicked at {click_time:.2f}s): {wav_path}")
                    self.current_playback = play_segment(wav_path, 0.0, None)
                else:
                    # Segment is selected → play snippet from click position within segment
                    # Ensure click is within the segment bounds
                    click_time = max(start_time, min(click_time, end_time - 0.1))
                    
                    # Play 1 second from click time, but don't exceed segment bounds
                    snippet_end = min(click_time + 1.0, end_time)
                    
                    print(f"🔊 Playing snippet: {click_time:.2f}s - {snippet_end:.2f}s")
                    self.current_playback = play_segment(wav_path, click_time, snippet_end)

        except Exception as e:
            print(f"❌ Error playing from waveform: {e}")
            import traceback
            traceback.print_exc()

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
        col = item.column()
        header_item = self.table.horizontalHeaderItem(col)
        if not header_item:
            return

        header_text = header_item.text().strip()

        # Only allow modifications to specific columns
        if header_text not in ["File", "Interval"] and not header_text.startswith("Var"):
            return

        self.modified_cells.add((item.row(), col))

        # Visually mark modified cells
        item.setBackground(QColor("#FFF3CD"))

        # Show warning for filename changes
        if col == 0 and not self.file_edit_warning_shown:
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
                        
                        # FIX: Get the actual tier name, not the dropdown display text
                        tier_index = self.tier_dropdown.currentIndex()
                        if tier_index >= 0 and tier_index < len(self._raw_tiers):
                            actual_tier_name = self._raw_tiers[tier_index]
                        else:
                            print(f"⚠️ Invalid tier index: {tier_index}")
                            continue
                        
                        # Find the tier by its actual name
                        tier = None
                        for t in tg.tiers:
                            if t.name == actual_tier_name and t.__class__.__name__ == "IntervalTier":
                                tier = t
                                break
                        
                        if tier is None:
                            print(f"⚠️ Tier '{actual_tier_name}' not found in {tg_path}")
                            continue

                        # Find and update the matching interval
                        interval_found = False
                        for interval in tier.intervals:
                            if abs(interval.minTime - start) < 0.001 and abs(interval.maxTime - end) < 0.001:
                                interval.mark = full_label
                                interval_found = True
                                print(f"✅ Updated interval in {tg_path}: '{interval.mark}' -> '{full_label}'")
                                break
                        
                        if not interval_found:
                            print(f"⚠️ No matching interval found in {tg_path} for times {start}-{end}")
                            continue

                        # Save the TextGrid
                        tg.write(tg_path)
                        print(f"✅ Saved changes to {tg_path}")
                        
                    except Exception as e:
                        print(f"❌ Error saving to {tg_path}: {e}")
                        import traceback
                        traceback.print_exc()

        # Clear the modified cells and reset their visual styling
        for row, col in self.modified_cells:
            item = self.table.item(row, col)
            if item:
                item.setBackground(QColor())  # Reset to default background
        
        self.modified_cells.clear()
        print(f"✅ All changes saved and cleared")

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
        """Export current table to CSV"""
        try:
            if self.table.rowCount() == 0:
                QMessageBox.warning(self, "Export Error", "No data to export.")
                return
                
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Export Table to CSV", 
                "vocal_data.csv", 
                "CSV Files (*.csv)"
            )
            
            if not file_path:
                return
                
            import csv
            
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write headers
                headers = []
                for col in range(self.table.columnCount()):
                    header_item = self.table.horizontalHeaderItem(col)
                    if header_item:
                        # Clean header text
                        header_text = header_item.text()
                        for suffix in [" 🔽", " (filtered)", " (none)"]:
                            header_text = header_text.replace(suffix, "")
                        headers.append(header_text)
                    else:
                        headers.append(f"Column_{col}")
                        
                writer.writerow(headers)
                
                # Write visible rows only
                for row in range(self.table.rowCount()):
                    if not self.table.isRowHidden(row):
                        row_data = []
                        for col in range(self.table.columnCount()):
                            item = self.table.item(row, col)
                            row_data.append(item.text() if item else "")
                        writer.writerow(row_data)
                        
            QMessageBox.information(
                self, 
                "Export Complete", 
                f"Table exported to:\n{file_path}"
            )
            
        except Exception as e:
            print(f"Error exporting table: {e}")
            QMessageBox.critical(self, "Export Error", f"Failed to export table:\n{str(e)}")

    def rename_variable_column(self, item):
        """Rename a variable column"""
        try:
            current_text = item.text()
            new_name, ok = QInputDialog.getText(
                self, 
                "Rename Variable", 
                f"Enter new name for '{current_text}':",
                text=current_text
            )
            
            if ok and new_name.strip() and new_name != current_text:
                item.setText(new_name.strip())
                self.refresh_table()
                
        except Exception as e:
            print(f"Error renaming variable column: {e}")

    def eventFilter(self, obj, event):
        """Handle keyboard shortcuts for table"""
        try:
            if obj == self.table and event.type() == event.Type.KeyPress:
                key = event.key()
                modifiers = event.modifiers()
                
                if key == Qt.Key.Key_Space:
                    # Play selected segment
                    current_row = self.table.currentRow()
                    if current_row >= 0:
                        # Trigger the selection to load the segment info
                        self.on_table_select(current_row, 1)  # Select interval column
                        # Small delay to ensure selection is processed
                        QTimer.singleShot(50, lambda: self.play_from_waveform(None))
                    return True
                    
                elif key == Qt.Key.Key_Escape:
                    # Stop current playback
                    try:
                        from app.core.audio_player import stop_playback
                        stop_playback()
                        print("🛑 Playback stopped via Escape key")
                    except Exception as e:
                        print(f"Error stopping playback: {e}")
                    return True
                    
            return super().eventFilter(obj, event)
            
        except Exception as e:
            print(f"Error in event filter: {e}")
            return False
        
    def _get_settings_path(self):
        return os.path.join(os.path.expanduser("~"), ".vocalfolder_settings.json")

    def _load_user_settings(self):
        try:
            path = self._get_settings_path()
            if os.path.exists(path):
                with open(path, "r") as f:
                    settings = json.load(f)
                    self.praat_path = settings.get("praat_path")
        except Exception as e:
            print(f"⚠️ Could not load settings: {e}")

    def _save_user_settings(self):
        try:
            path = self._get_settings_path()
            with open(path, "w") as f:
                json.dump({"praat_path": self.praat_path}, f)
        except Exception as e:
            print(f"❌ Could not save settings: {e}")

    def set_praat_path(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Praat Executable", "", 
            "Executables (*.app *.exe *praat*)"
        )
        if file_path:
            self.praat_path = file_path
            self._save_user_settings()
            QMessageBox.information(self, "Path Set", f"✅ Praat path saved:\n{file_path}")

    def set_spec_colormap(self, cmap_name):
        self.waveform_viewer.spec_cmap = cmap_name
        # Redibuja si ya hay un archivo cargado
        if self.waveform_viewer.current_wav_path:
            self.waveform_viewer.plot_waveform(
                self.waveform_viewer.current_wav_path,
                zoom=False
            )

    def set_spec_freq_limits(self):
        class FrequencyDialog(QDialog):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setWindowTitle("Set Frequency Limits")

                self.min_input = QLineEdit(str(self.parent().waveform_viewer.spec_freq_min or 0))
                self.max_input = QLineEdit(str(self.parent().waveform_viewer.spec_freq_max or 8000))

                layout = QVBoxLayout()

                min_layout = QHBoxLayout()
                min_layout.addWidget(QLabel("Min frequency (Hz):"))
                min_layout.addWidget(self.min_input)

                max_layout = QHBoxLayout()
                max_layout.addWidget(QLabel("Max frequency (Hz):"))
                max_layout.addWidget(self.max_input)

                layout.addLayout(min_layout)
                layout.addLayout(max_layout)

                buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
                buttons.accepted.connect(self.accept)
                buttons.rejected.connect(self.reject)
                layout.addWidget(buttons)

                self.setLayout(layout)

            def get_values(self):
                try:
                    min_f = int(self.min_input.text())
                    max_f = int(self.max_input.text())
                    if min_f < 0 or max_f <= min_f:
                        raise ValueError
                    return min_f, max_f
                except ValueError:
                    QMessageBox.warning(self, "Invalid input", "Frequencies must be integers and Max > Min.")
                    return None

        # Create and show dialog
        dialog = FrequencyDialog(self)
        if dialog.exec():
            values = dialog.get_values()
            if values:
                min_freq, max_freq = values
                self.waveform_viewer.spec_freq_min = min_freq
                self.waveform_viewer.spec_freq_max = max_freq

                if self.waveform_viewer.current_wav_path:
                    self.waveform_viewer.plot_waveform(
                        self.waveform_viewer.current_wav_path,
                        zoom=False
                    )

    def reset_spec_freq_limits(self):
        self.waveform_viewer.spec_freq_min = 0
        self.waveform_viewer.spec_freq_max = None
        if self.waveform_viewer.current_wav_path:
            self.waveform_viewer.plot_waveform(
                self.waveform_viewer.current_wav_path,
                zoom=False
            )

    def set_formant_mode(self, mode):
        from app.core import feature_extractor
        feature_extractor.formant_mode = mode
        feature_extractor._feature_caches["formants"].clear()
        print(f"🔧 Formant mode set to: {mode}")

        # Update the UI checkboxes
        for action in self.findChildren(QAction):
            if action.text() == "Midpoint (default)":
                action.setChecked(mode == "midpoint")
            elif action.text() == "Mean over interval":
                action.setChecked(mode == "mean")

        # Redraw waveform with new formant mode
        if self.waveform_viewer.current_wav_path:
            self.waveform_viewer.plot_waveform(
                self.waveform_viewer.current_wav_path,
                zoom=False
            )

        # Refresh feature columns to reflect the new formant mode
        self.refresh_feature_columns()

    @safe_table_operation
    def refresh_feature_columns(self):
        """Recalcula los valores de features seleccionados en todas las filas."""
        from app.core.feature_extractor import compute_feature_value

        headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
        feature_cols = {
            header: col
            for col, header in enumerate(headers)
            if header in self.selected_features
        }

        for row_idx, row_data in enumerate(self.tier_intervals):
            name, label, start, end, duration = row_data
            wav_path = self._get_wav_path(name)

            for feature in self.selected_features:
                if feature in feature_cols:
                    col_idx = feature_cols[feature]
                    value = compute_feature_value(feature, wav_path, start, end, duration)
                    item = QTableWidgetItem(str(value) if value is not None else "")
                    self.table.setItem(row_idx, col_idx, item)

    def on_column_header_clicked(self, column_index):
        header_text = self.table.horizontalHeaderItem(column_index).text()
        if header_text in ["File", "Interval"]:
            return

        # Rebuild headers list
        headers = [
            self.table.horizontalHeaderItem(i).text()
            for i in range(self.table.columnCount())
        ]

        # Only include visible (unfiltered) rows
        data = []
        for row in range(self.table.rowCount()):
            if self.table.isRowHidden(row):
                continue

            row_data = {}
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                val = item.text() if item else ""
                # Attempt numeric conversion for non-meta columns
                if headers[col] not in ["File", "Interval"]:
                    try:
                        val = float(val)
                    except ValueError:
                        pass
                row_data[headers[col]] = val
            data.append(row_data)

        df = pd.DataFrame(data)
        self.column_stats_panel.update_stats(df, header_text)

    def on_header_context_menu(self, pos):
        header = self.table.horizontalHeader()
        col    = header.logicalIndexAt(pos)
        if col not in self.variable_column_indices:
            return

        vals = get_unique_values_for_column(self.table, col)
        if not vals:
            return
        self.cached_unique_values[col] = vals

        menu = create_filter_menu(self, col, vals, self.active_filters, self._filter_callback)
        if not menu:
            return

        # compute x offset of the clicked section
        section_pos = header.sectionViewportPosition(col)
        # map to global, placing menu just below the header bar
        global_pos = header.mapToGlobal(QPoint(section_pos, header.height()))
        menu.exec(global_pos)