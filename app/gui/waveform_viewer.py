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

    def plot_waveform(self, wav_path, start=None, end=None):
        print(f"📊 Plotting: {os.path.basename(wav_path)}, start={start}, end={end}")
        self.figure.clear()
        self.canvas.draw()  # 🧼 Clear canvas completely before replotting
        ax = self.figure.add_subplot(111)

        try:
            rate, data = wavfile.read(wav_path)
            if data.ndim > 1:
                data = data[:, 0]  # Use first channel if stereo

            if start is not None and end is not None:
                start_idx = int(start * rate)
                end_idx = int(end * rate)
                data = data[start_idx:end_idx]
                time = np.linspace(start, end, num=len(data))
            else:
                time = np.linspace(0, len(data) / rate, num=len(data))

            ax.plot(time, data, linewidth=0.8, color="steelblue")
            ax.set_xlim(time[0], time[-1])  # ✅ Force axes to match data
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