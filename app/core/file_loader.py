# app/core/file_loader.py

import os

def load_file_pairs(folder_path):
    files = os.listdir(folder_path)
    wavs = {os.path.splitext(f)[0]: os.path.join(folder_path, f)
            for f in files if f.endswith('.wav')}
    grids = {os.path.splitext(f)[0]: os.path.join(folder_path, f)
             for f in files if f.endswith('.TextGrid')}

    paired = []
    for name in sorted(wavs.keys()):
        if name in grids:
            paired.append((name, wavs[name], grids[name]))

    return paired  # List of tuples: (basename, wav_path, textgrid_path)