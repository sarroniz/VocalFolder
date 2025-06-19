# Vocal Folder

**Vocal Folder** is a dynamic annotation browser and audio segmentation toolkit for phonetic research. It allows you to load `.wav` + `.TextGrid` pairs, browse annotations, view waveforms, and play back segments directly from the UI.

---

## ✅ Features (MVP Complete)

- [x] Folder loader: parse `.wav` + `.TextGrid` file pairs
- [x] Dynamic tier selection (adapts to user project)
- [x] Table view of intervals: File, Label, Start, End, Duration
- [x] Waveform viewer with segment highlighting
- [x] Click-to-select behavior:
  - Click "File": shows full waveform
  - Click "Label": shows full waveform, plays interval on waveform click
  - Click elsewhere: zooms into interval
- [x] Playback integration: prevents overlapping playback

---

## 🧭 Roadmap

- [ ] Add waveform segment highlighting (visual overlays)
- [ ] Filtering by label type or duration
- [ ] CSV export of segments + acoustic features
- [ ] Spectrogram overlay toggle
- [ ] Basic acoustic analysis (e.g. intensity, ZCR, tilt)
- [ ] Undo/redo and manual tier editing
- [ ] Preferences panel (e.g., playback speed, tier order)

---

## 🛠️ Tech Stack

- Python 3.10+
- PyQt6
- matplotlib
- scipy / numpy
- [praatio](https://github.com/timmahrt/praatIO) (optional for TextGrid parsing)

---

## 🚀 Run Locally

```bash
python app/main.py