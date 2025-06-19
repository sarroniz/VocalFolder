# Vocal Folder

**Vocal Folder** is a dynamic annotation browser and audio segmentation toolkit for phonetic research. It allows you to load `.wav` + `.TextGrid` pairs, browse annotations, view waveforms, and play back segments directly from the UI — all without scripting.

---

## ✅ Features (MVP Complete)

- [x] Folder loader: parse `.wav` + `.TextGrid` file pairs
- [x] Display selected working directory in header
- [x] Dynamic tier selection (adapts to user project)
- [x] Table view of intervals: File, Label, Start, End, Duration
- [x] Smart detection of structured labels (e.g. `b-una_burra-a-b-u-ton-ext-f-fem-jov`)
  - Optional parsing of label into variable columns
  - Header names are editable (e.g. `var1`, `var2` → `place`, `gender`, etc.)
- [x] Waveform viewer with segment zoom
- [x] Click-to-select behavior:
  - Click “File”: shows full waveform
  - Click “Label”: shows full waveform, plays segment on waveform click
  - Click anywhere else: zooms into selected segment
- [x] Playback integration: prevents overlapping playback
- [x] Tab key triggers playback for selected segment
- [x] Tier-aware segment editing
  - Edits tracked visually (light yellow)
  - Option to rename `.wav` + `.TextGrid` if filename is changed
  - Save prompt before closing

---

## 🧭 Roadmap

- [ ] Waveform overlays for labeled intervals
- [ ] Filtering by label type, variable, or duration
- [ ] Acoustic feature extraction: duration, intensity, F1, F2, ZCR, tilt
- [ ] CSV export of filtered intervals and features
- [ ] Spectrogram overlay toggle
- [ ] Undo/redo support and per-cell history
- [ ] Preferences panel (e.g., default tier, playback speed, export config)
- [ ] File renaming rules based on metadata

---

## 🖼 Screenshot

<p align="center">
  <img src="assets/screenshots/vocalfolder_main_ui.png" alt="Vocal Folder UI" width="700">
</p>

---

## 🛠️ Tech Stack

- Python 3.10+
- PyQt6
- matplotlib (for waveform rendering)
- scipy / numpy
- [textgrid](https://pypi.org/project/textgrid/) or [praatio](https://github.com/timmahrt/praatIO) for parsing
- [parselmouth](https://parselmouth.readthedocs.io/) (optional for acoustic features)

---

## 🚀 Run Locally

```bash
git clone https://github.com/YOUR_USERNAME/vocal-folder.git
cd vocal-folder
pip install -r requirements.txt
python app/main.py