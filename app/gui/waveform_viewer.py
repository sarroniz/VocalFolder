# app/gui/waveform_viewer.py
import os
import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from scipy.io import wavfile
from PyQt6.QtCore import pyqtSignal

class WaveformViewer(QWidget):
    # Emits the click-position in seconds
    waveformClicked = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Create a figure with two rows: waveform (top) and spectrogram (bottom)
        self.figure = Figure(figsize=(6, 4))
        self.canvas = FigureCanvas(self.figure)
        self.wave_ax = None
        self.spec_ax = None

        # Connect mouse clicks
        self.canvas.mpl_connect("button_press_event", self._on_click)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def plot_waveform(self, wav_path, start=None, end=None, zoom=False):
        """
        Draws the waveform and spectrogram stacked.
        - wav_path: path to .wav file
        - start,end: optional segment times in seconds
        - zoom: if True, zoom both axes to [start,end]
        """
        self.figure.clear()
        # top = waveform, bottom = spectrogram
        self.wave_ax = self.figure.add_subplot(211)
        self.spec_ax = self.figure.add_subplot(212, sharex=self.wave_ax)

        try:
            rate, data = wavfile.read(wav_path)
            # if stereo, take first channel
            if data.ndim > 1:
                data = data[:, 0]
            time = np.arange(len(data)) / rate

            # full waveform in light gray
            self.wave_ax.plot(time, data, color='lightgray', linewidth=0.8)

            # highlight segment in blue
            if start is not None and end is not None:
                si = int(max(0, start * rate))
                ei = int(min(len(data), end * rate))
                seg_t = np.arange(si, ei) / rate
                seg_d = data[si:ei]
                self.wave_ax.plot(seg_t, seg_d, color='steelblue', linewidth=1.2)
                if zoom:
                    self.wave_ax.set_xlim(start, end)

            self.wave_ax.set_title("Waveform")
            self.wave_ax.set_ylabel("Amplitude")
            self.wave_ax.spines['top'].set_visible(False)
            self.wave_ax.spines['right'].set_visible(False)

            # spectrogram in default colormap
            self.spec_ax.specgram(data, Fs=rate, NFFT=1024, noverlap=512)
            if start is not None and end is not None:
                # translucent red span
                self.spec_ax.axvspan(start, end, alpha=0.3, color='red')
                if zoom:
                    self.spec_ax.set_xlim(start, end)

            self.spec_ax.set_title("Spectrogram")
            self.spec_ax.set_xlabel("Time (s)")
            self.spec_ax.set_ylabel("Frequency (Hz)")
            self.spec_ax.spines['top'].set_visible(False)
            self.spec_ax.spines['right'].set_visible(False)

            self.figure.tight_layout()
            self.canvas.draw()

        except Exception as e:
            # fallback error display on the waveform axis
            if self.wave_ax is None:
                self.wave_ax = self.figure.add_subplot(111)
            self.wave_ax.text(
                0.5, 0.5, f"Error: {e}",
                ha='center', va='center',
                transform=self.wave_ax.transAxes
            )
            self.canvas.draw()

    def _on_click(self, event):
        """
        When user clicks on either subplot, emit the time (x-coordinate).
        """
        if event.button == 1 and event.xdata is not None:
            self.waveformClicked.emit(event.xdata)