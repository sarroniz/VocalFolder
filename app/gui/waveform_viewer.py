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
        
        # Store current audio data for highlighting
        self.current_wav_path = None
        self.current_data = None
        self.current_rate = None
        self.current_time = None
        
        # Connect mouse clicks
        self.canvas.mpl_connect("button_press_event", self._on_click)
        
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        # Default parameters for spectrogram
        self.spec_cmap = 'Grays'
        self.spec_freq_min = 0
        self.spec_freq_max = None  # None = auto
    
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
            
            # Store current audio data
            self.current_wav_path = wav_path
            self.current_data = data
            self.current_rate = rate
            self.current_time = time
            
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
            self.spec_ax.specgram(
                data, 
                Fs=rate, 
                NFFT=1024, 
                noverlap=512, 
                cmap=self.spec_cmap
            )
            # Only set y-limits if specified
            if self.spec_freq_max is not None:
                self.spec_ax.set_ylim(self.spec_freq_min, self.spec_freq_max)
            
            # if start is not None and end is not None:
                # translucent red span
                # self.spec_ax.axvspan(start, end, alpha=0.3, color='red')
                
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
    
    def highlight_interval(self, start_time, end_time):
        """
        Add a highlight to an interval without changing the overall view.
        Used when selecting a File cell to show the corresponding interval.
        """
        if (self.current_data is None or self.wave_ax is None or 
            self.spec_ax is None or start_time is None or end_time is None):
            return
            
        try:
            # Clear any existing highlights (remove previous highlight plots)
            self._clear_highlights()
            
            # Add highlight to waveform
            rate = self.current_rate
            si = int(max(0, start_time * rate))
            ei = int(min(len(self.current_data), end_time * rate))
            seg_t = np.arange(si, ei) / rate
            seg_d = self.current_data[si:ei]
            
            # Plot highlighted segment
            highlight_line = self.wave_ax.plot(seg_t, seg_d, color='steelblue', 
                                             linewidth=1.0, alpha=0.8, 
                                             label='_highlight_waveform')[0]
            highlight_line.set_zorder(10)  # Bring to front
            
            # Add highlight to spectrogram
            # highlight_span = self.spec_ax.axvspan(start_time, end_time, 
            #                                     alpha=0.4, color='steelblue', 
            #                                     label='_highlight_spectrogram')
            # highlight_span.set_zorder(10)  # Bring to front
            
            self.canvas.draw()
            
        except Exception as e:
            print(f"Error highlighting interval: {e}")
    
    def _clear_highlights(self):
        """Remove existing highlights from the plot"""
        try:
            if self.wave_ax:
                # Remove highlight lines from waveform
                lines_to_remove = [line for line in self.wave_ax.lines 
                                 if line.get_label() == '_highlight_waveform']
                for line in lines_to_remove:
                    line.remove()
            
            if self.spec_ax:
                # Remove highlight spans from spectrogram
                collections_to_remove = [coll for coll in self.spec_ax.collections 
                                       if hasattr(coll, 'get_label') and 
                                       coll.get_label() == '_highlight_spectrogram']
                for coll in collections_to_remove:
                    coll.remove()
                    
        except Exception as e:
            print(f"Error clearing highlights: {e}")
    
    def clear_all_highlights(self):
        """Public method to clear all highlights"""
        self._clear_highlights()
        self.canvas.draw()
    
    def _on_click(self, event):
        """
        When user clicks on either subplot, emit the time (x-coordinate).
        """
        if event.button == 1 and event.xdata is not None:
            self.waveformClicked.emit(event.xdata)