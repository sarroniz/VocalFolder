import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QPushButton, QComboBox, QVBoxLayout,
    QHBoxLayout, QLabel, QFileDialog, QTableWidget, QTableWidgetItem
)
from app.core.file_loader import load_file_pairs
from app.core.textgrid_parser import extract_intervals
from textgrid import TextGrid

from app.core.audio_player import play_segment

from app.gui.waveform_viewer import WaveformViewer

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vocal Folder (beta)")

        self.file_pairs = []
        self.tier_intervals = []

        self.tier_label = QLabel("Tier:")
        self.tier_dropdown = QComboBox()
        self.load_button = QPushButton("Load Folder")
        self.table = QTableWidget()

        self.waveform_viewer = WaveformViewer()
        self.waveform_viewer.waveformClicked.connect(self.play_from_waveform)

        self.load_button.clicked.connect(self.load_folder)
        self.tier_dropdown.currentIndexChanged.connect(self.refresh_table)
        self.table.cellClicked.connect(self.on_table_select)

        self.current_playback = None
        self.selected_segment_info = None  # (wav_path, start_time, end_time)

        # Layout
        top_row = QHBoxLayout()
        top_row.addWidget(self.tier_label)
        top_row.addWidget(self.tier_dropdown)
        top_row.addWidget(self.load_button)

        layout = QVBoxLayout()
        layout.addLayout(top_row)
        layout.addWidget(self.table)
        layout.addWidget(self.waveform_viewer)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def load_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if not folder:
            return

        self.file_pairs = load_file_pairs(folder)

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

        for name, wav_path, tg_path in self.file_pairs:
            try:
                intervals = extract_intervals(tg_path, tier_name=selected_tier)
                for intv in intervals:
                    self.tier_intervals.append([
                        name, intv['label'], intv['start'], intv['end'], intv['duration']
                    ])
            except Exception as e:
                print(f"Error parsing {tg_path}: {e}")

        if not self.tier_intervals:
            print(f"⚠️ No intervals found for tier: '{selected_tier}'")

        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["File", "Label", "Start", "End", "Duration"])
        self.table.setRowCount(len(self.tier_intervals))
        for i, row in enumerate(self.tier_intervals):
            for j, val in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(str(val)))

    def on_table_select(self, row, column):
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
                self.waveform_viewer.plot_waveform(wav_path, start=None, end=None)
                self.selected_segment_info = (wav_path, 0, None)

            elif header == "Label":
                print(f"👆 Selected segment (Label click): {file_name} [{start_time:.2f}s - {end_time:.2f}s]")
                self.waveform_viewer.plot_waveform(wav_path, start=start_time, end=end_time)  # full waveform
                self.selected_segment_info = (wav_path, start_time, end_time)

            else:
                print(f"👆 Selected segment (zoom): {file_name} [{start_time:.2f}s - {end_time:.2f}s]")
                self.waveform_viewer.plot_waveform(wav_path, start=start_time, end=end_time)
                self.selected_segment_info = (wav_path, start_time, end_time)

        except Exception as e:
            print(f"Error selecting row: {e}")

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