# Vocal Folder

Vocal Folder is an interactive platform for browsing, editing, and analyzing time-aligned phonetic annotations in speech recordings. It enables researchers to load `.wav` and `.TextGrid` files in bulk, browse and edit annotations across multiple tiers, and visualize waveforms with segment-level zoom — all from a single unified interface. The app supports structured label parsing, customizable column views, and real-time audio playback of annotated segments. Users can extract acoustic features such as duration, intensity, zero-crossing rate, and spectral centroid without writing any code. Whether you’re auditing annotations, preparing data for analysis, or exploring phonetic patterns, Vocal Folder streamlines the workflow and eliminates the need for manual Praat scripting.

---

## ✅ Features (Implemented)

- [x] **Folder Loader**: parses `.wav` + `.TextGrid` file pairs
- [x] **Smart Path Display**: shows working directory path (shortened in header)
- [x] **Tier Selection**: dynamically lists tiers available in loaded files
- [x] **Annotation Table**: displays `File`, `Label`, `Start`, `End`, `Duration`
- [x] **Waveform Viewer**: shows full waveform and zoomed segments
- [x] **Interactive Navigation**:
  - Click “File” → full waveform
  - Click “Label” or other columns → zoom to segment and enable playback
  - `Tab` key → plays currently selected segment
- [x] **Structured Label Parsing**:
  - Automatically splits hyphenated labels (e.g. `b-una_burra-a-fem`)
  - Displays `Var1`, `Var2`, etc. as toggleable columns
  - Variable headers are editable (e.g. rename `Var2` to `Gender`)
- [x] **Feature Selector**:
  - Choose which acoustic features to display:
    - Duration
    - Midpoint Intensity (via Praat/Parselmouth)
    - Zero-Crossing Rate (ZCR)
    - Spectral Centroid (via Librosa)
- [x] **Filter System**:
  - Excel-style dropdown filters for any visible variable column
  - Filter status reflected in header (🔽 / 🔽 filtered)
- [x] **Editable Table Mode**:
  - Toggle cell editing on/off
  - Visual highlight of unsaved edits (light yellow)
  - Auto-save edits to `.TextGrid`
  - If filename is edited, renames both `.wav` and `.TextGrid` to match
- [x] **CSV Export**: saves current table (including edits and selected columns) to CSV
    - [x] Export filtered rows only

---

## 🔧 In Progress / Upcoming

- [ ] Waveform overlays for all intervals in selected tier
- [ ] Additional acoustic features: F1/F2, spectral tilt, intensity range
- [ ] Batch processing and caching of feature extraction
- [ ] Undo/redo history per cell
- [ ] User preferences (e.g., default tier, filter persistence, playback settings)
- [ ] Visual tagging (e.g., mark intervals as good/bad/ambiguous/etc.)

---

## 🖼 Screenshot

<p align="center">
  <img src="assets/screenshots/vocalfolder_main_ui.png" alt="Vocal Folder UI" width="700">
</p>

---

## 🛠️ Tech Stack

- Python 3.10+
- PyQt6
- [`parselmouth`](https://parselmouth.readthedocs.io/) for intensity extraction
- [`librosa`](https://librosa.org/) for spectral features
- [`textgrid`](https://pypi.org/project/textgrid/) for annotation parsing
- `numpy`, `scipy`, `matplotlib`

---

## 🚀 Run Locally

```bash
git clone https://github.com/YOUR_USERNAME/vocal-folder.git
cd vocal-folder
pip install -r requirements.txt
python app/main.py