# app/gui/waveform_viewer.py
import os
import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from scipy.io import wavfile
from PyQt6.QtCore import pyqtSignal

class WaveformViewer(QWidget):
    waveformClicked = pyqtSignal()  # 🆕 Signal for mouse click

    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(6, 2))
        self.canvas = FigureCanvas(self.figure)

        # 🆕 Connect mouse click event
        self.canvas.mpl_connect("button_press_event", self._on_click)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def plot_waveform(self, wav_path, start=None, end=None, zoom=False):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        try:
            rate, data = wavfile.read(wav_path)
            if data.ndim > 1:
                data = data[:, 0]  # Use first channel if stereo

            time = np.arange(len(data)) / rate
            ax.plot(time, data, color='lightgray', linewidth=0.8)  # Always show full waveform

            if start is not None and end is not None:
                start_idx = int(start * rate)
                end_idx = int(end * rate)

                start_idx = max(0, start_idx)
                end_idx = min(len(data), end_idx)

                time_segment = np.arange(start_idx, end_idx) / rate
                data_segment = data[start_idx:end_idx]

                ax.plot(time_segment, data_segment, color='steelblue', linewidth=1.2)

                if zoom:
                    ax.set_xlim(start, end)

            ax.set_title("Waveform")
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Amplitude")
            self.figure.tight_layout()
            self.canvas.draw()

        except Exception as e:
            ax.text(0.5, 0.5, f"Error: {e}", ha='center', transform=ax.transAxes)
            self.canvas.draw()

    # 🆕 Handle click event
    def _on_click(self, event):
        if event.button == 1:  # Left click
            self.waveformClicked.emit()