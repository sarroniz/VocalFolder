# Vocal Folder

**Vocal Folder** is a dynamic annotation browser and audio segmentation toolkit for phonetic research. It allows you to load `.wav` + `.TextGrid` pairs, browse annotations, view waveforms, and play back segments directly from the UI — all without scripting.

---

## ✅ Features (Stable MVP)

- [x] **Folder Loader**: parse `.wav` + `.TextGrid` file pairs
- [x] **Smart Path Display**: working directory shown and shortened in header
- [x] **Dynamic Tier Selection**: automatically adapts to tier names in your files
- [x] **Interval Table**: displays `File`, `Label`, `Start`, `End`, `Duration`
- [x] **Waveform Viewer**: full and zoomed segment views
- [x] **Click-to-Action**:
  - Click “File” → shows entire waveform
  - Click “Label” → zooms in and allows segment playback
  - Click any other column → zooms into that segment
- [x] **Tab-to-Play**: press `Tab` to replay selected segment
- [x] **Playback Management**: no overlapping playback
- [x] **Structured Label Parsing**:
  - Automatically detects `-`-separated label structures (e.g. `b-una_burra-a-fem-ton-ext`)
  - Presents variable components (`Var1`, `Var2`, ...) in a dedicated sidebar
  - User can toggle visibility via checkboxes
  - Column headers are editable (e.g. rename `Var1` to `Context`)
- [x] **Visual Editing Mode**:
  - Enable/disable editable table cells
  - Modified cells are highlighted
  - Editing filename triggers rename of `.wav` + `.TextGrid` pair
  - Save prompt before closing modified session
- [x] **Feature Selector**: toggle display of acoustic features:
  - Duration
  - Intensity at midpoint
  - Zero Crossing Rate (ZCR)
  - Spectral Centroid
- [x] **Acoustic feature computation**: runs on-demand per visible row
- [x] **Column Filtering**: Excel-style dropdown filters for variable columns

---

## 🧭 Roadmap

- [ ] Waveform overlays for full tiers and annotations
- [ ] Additional acoustic features (e.g., F1, F2, spectral tilt)
- [ ] Batch processing and caching of acoustic measures
- [ ] Advanced filtering (e.g., duration thresholds, logical operators)
- [ ] Export only visible/filtered rows to CSV
- [ ] Undo/redo per-cell history
- [ ] Preferences panel (e.g., playback speed, feature settings)
- [ ] Tagging system (mark segments as validated, ambiguous, etc.)
- [ ] Dark mode UI toggle

---

## 🖼 Screenshot

<p align="center">
  <img src="assets/screenshots/vocalfolder_main_ui.png" alt="Vocal Folder UI" width="700">
</p>

---

## 🛠️ Tech Stack

- Python 3.10+
- PyQt6
- `librosa` (for spectral analysis)
- `parselmouth` (for Praat-compatible intensity and pitch analysis)
- `matplotlib` (for waveform rendering)
- `textgrid` (or `praatio`) for annotation parsing
- `numpy`, `scipy`

---

## 🚀 Run Locally

```bash
git clone https://github.com/YOUR_USERNAME/vocal-folder.git
cd vocal-folder
pip install -r requirements.txt
python app/main.py