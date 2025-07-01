import os
import numpy as np
import parselmouth
import librosa

# Central cache dictionary for reusable feature computations
_feature_caches = {
    "formants": {},
    "intensity": {},
    "zcr": {},
    "spectral_centroid": {},
    "pitch": {},
    "jitter": {},
    "shimmer": {},
    "hnr": {},
    "rms": {},
    "rolloff": {},
    "bandwidth": {},
    "flatness": {},
    "contrast": {},
    "mfcc": {},
    "cpp": {},
}

formant_mode = "midpoint" 


def clear_all_feature_caches():
    for name, cache in _feature_caches.items():
        cache.clear()
        print(f"🧹 Cleared cache: {name}")

# Intensity (mean dB)
def compute_mean_intensity(wav_path, start_time, end_time):
    # No se cachea porque no se usa en el dispatcher actual
    try:
        print(f"🔍 Computing intensity: {os.path.basename(wav_path)} [{start_time}-{end_time}]")
        snd = parselmouth.Sound(wav_path)
        segment = snd.extract_part(from_time=start_time, to_time=end_time, preserve_times=True)
        intensity = segment.to_intensity()
        valid_vals = intensity.values[intensity.values > 0]
        if valid_vals.size == 0:
            print("⚠️ No positive intensity values.")
            return None
        mean_db = valid_vals.mean()
        print(f"✅ Mean dB: {mean_db}")
        return round(mean_db, 2)
    except Exception as e:
        print(f"❌ Error computing intensity: {e}")
        return None

# Zero Crossing Rate
def compute_zcr(wav_path, start_time, end_time):
    key = (wav_path, round(start_time, 4), round(end_time, 4))
    cache = _feature_caches["zcr"]
    if key in cache:
        return cache[key]
    try:
        snd = parselmouth.Sound(wav_path)
        segment = snd.extract_part(from_time=start_time, to_time=end_time, preserve_times=False)
        samples = segment.values[0]  # mono

        if len(samples) < 2:
            return None

        zero_crossings = np.where(np.diff(np.signbit(samples)))[0]
        duration = segment.duration

        if duration == 0:
            return None

        zcr = len(zero_crossings) / duration
        print(f"🔍 ZCR: {zcr:.2f}")
        cache[key] = round(zcr, 2)
        return cache[key]
    except Exception as e:
        print(f"❌ Error computing ZCR: {e}")
        return None

# Intensity at midpoint
def compute_intensity_at_midpoint(wav_path, start_time, end_time):
    key = (wav_path, round(start_time, 4), round(end_time, 4))
    cache = _feature_caches["intensity"]
    if key in cache:
        return cache[key]
    try:
        midpoint = (start_time + end_time) / 2
        snd = parselmouth.Sound(wav_path)

        pitch_floor = 75
        time_step = 0.01

        intensity = snd.to_intensity(time_step=time_step, minimum_pitch=pitch_floor)
        intensity_value = intensity.get_value(time=midpoint)

        if intensity_value is None or intensity_value <= 0:
            print(f"⚠️ No valid intensity at midpoint ({midpoint}s)")
            return None

        print(f"🔍 Intensity at midpoint: {intensity_value:.2f} dB")
        cache[key] = round(intensity_value, 2)
        return cache[key]
    except Exception as e:
        print(f"❌ Error computing midpoint intensity: {e}")
        return None

# Spectral Centroid
def compute_spectral_centroid(wav_path, start, end):
    key = (wav_path, round(start, 4), round(end, 4))
    cache = _feature_caches["spectral_centroid"]
    if key in cache:
        return cache[key]
    try:
        y, sr = librosa.load(wav_path, sr=None, offset=start, duration=end - start)
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        if centroid.size > 0:
            val = round(np.mean(centroid), 2)
            cache[key] = val
            return val
    except Exception as e:
        print(f"❌ Error computing spectral centroid for {wav_path} [{start}-{end}]: {e}")
    return None

# Formants (F1, F2, F3)
def compute_formants(wav_path, start_time, end_time):
    key = (wav_path, round(start_time, 4), round(end_time, 4), formant_mode)
    cache = _feature_caches["formants"]
    if key in cache:
        print(f"📦 Using cached formants ({formant_mode}) for {os.path.basename(wav_path)} [{start_time}-{end_time}]")
        return cache[key]

    try:
        snd = parselmouth.Sound(wav_path)
        formant = snd.to_formant_burg(time_step=0.01, max_number_of_formants=5, maximum_formant=5500)

        if formant_mode == "midpoint":
            times = [(start_time + end_time) / 2]
        else:  # mean across interval
            times = np.linspace(start_time, end_time, num=5)

        values = []
        for i in range(1, 4):  # F1, F2, F3
            f_vals = [formant.get_value_at_time(i, t) for t in times]
            f_vals = [f for f in f_vals if f is not None and not np.isnan(f)]
            if f_vals:
                mean_f = round(np.mean(f_vals), 2)
                print(f"🔍 F{i} mean: {mean_f} Hz")
                values.append(mean_f)
            else:
                print(f"⚠️ F{i} undefined in interval")
                values.append(None)

        cache[key] = values
        return values
    except Exception as e:
        print(f"❌ Error computing formants: {e}")
        return [None, None, None]

# Pitch (mean F0)
def compute_pitch_mean(wav_path, start_time, end_time):
    key = (wav_path, start_time, end_time)
    cache = _feature_caches['pitch']
    if key in cache:
        return cache[key]
    snd = parselmouth.Sound(wav_path).extract_part(start_time, end_time)
    pitch = snd.to_pitch()
    f0 = pitch.selected_array['frequency']
    valid = f0[f0>0]
    val = float(np.mean(valid)) if valid.size>0 else None
    cache[key] = round(val,2) if val is not None else None
    return cache[key]

# Jitter (local)
def compute_jitter(wav_path, start_time, end_time):
    key = (wav_path, start_time, end_time)
    cache = _feature_caches['jitter']
    if key in cache:
        return cache[key]
    snd = parselmouth.Sound(wav_path)
    segment = snd.extract_part(start_time, end_time)
    pp = segment.to_point_process_cc()
    jitter_local = call(pp, "Get jitter (local)", 0, 0, 0, 0, 0)
    cache[key] = round(jitter_local,4)
    return cache[key]

# Shimmer (local)
def compute_shimmer(wav_path, start_time, end_time):
    key = (wav_path, start_time, end_time)
    cache = _feature_caches['shimmer']
    if key in cache:
        return cache[key]
    snd = parselmouth.Sound(wav_path)
    segment = snd.extract_part(start_time, end_time)
    pp = segment.to_point_process_cc()
    shimmer_local = call(pp, "Get shimmer (local)", 0, 0, 0, 0, 0, 0)
    cache[key] = round(shimmer_local,4)
    return cache[key]

# Harmonic-to-noise ratio
def compute_hnr(wav_path, start_time, end_time):
    key = (wav_path, start_time, end_time)
    cache = _feature_caches['hnr']
    if key in cache:
        return cache[key]
    snd = parselmouth.Sound(wav_path).extract_part(start_time, end_time)
    harm = snd.to_harmonicity()
    mid = (start_time+end_time)/2
    val = harm.get_value_at_time(mid)
    cache[key] = round(val,2) if val is not None else None
    return cache[key]

# RMS energy
def compute_rms(wav_path, start, end):
    key = (wav_path, start, end)
    cache = _feature_caches['rms']
    if key in cache:
        return cache[key]
    y, sr = librosa.load(wav_path, sr=None, offset=start, duration=end-start)
    rms = librosa.feature.rms(y=y)
    val = float(np.mean(rms)) if rms.size>0 else None
    cache[key] = round(val,4) if val is not None else None
    return cache[key]

# Spectral rolloff
def compute_rolloff(wav_path, start, end, roll_percent=0.85):
    key = (wav_path, start, end)
    cache = _feature_caches['rolloff']
    if key in cache:
        return cache[key]
    y, sr = librosa.load(wav_path, sr=None, offset=start, duration=end-start)
    roll = librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=roll_percent)
    val = float(np.mean(roll)) if roll.size>0 else None
    cache[key] = round(val,2) if val is not None else None
    return cache[key]

# Spectral bandwidth
def compute_bandwidth(wav_path, start, end, p=2):
    key = (wav_path, start, end)
    cache = _feature_caches['bandwidth']
    if key in cache:
        return cache[key]
    y, sr = librosa.load(wav_path, sr=None, offset=start, duration=end-start)
    bw = librosa.feature.spectral_bandwidth(y=y, sr=sr, p=p)
    val = float(np.mean(bw)) if bw.size>0 else None
    cache[key] = round(val,2) if val is not None else None
    return cache[key]

# Spectral flatness
def compute_flatness(wav_path, start, end):
    key = (wav_path, start, end)
    cache = _feature_caches['flatness']
    if key in cache:
        return cache[key]
    y, sr = librosa.load(wav_path, sr=None, offset=start, duration=end-start)
    flat = librosa.feature.spectral_flatness(y=y)
    val = float(np.mean(flat)) if flat.size>0 else None
    cache[key] = round(val,4) if val is not None else None
    return cache[key]

# Spectral contrast
def compute_contrast(wav_path, start, end):
    key = (wav_path, start, end)
    cache = _feature_caches['contrast']
    if key in cache:
        return cache[key]
    y, sr = librosa.load(wav_path, sr=None, offset=start, duration=end-start)
    contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
    val = float(np.mean(contrast)) if contrast.size>0 else None
    cache[key] = round(val,2) if val is not None else None
    return cache[key]

# MFCC (mean of first coefficient)
def compute_mfcc1(wav_path, start, end, n_mfcc=13):
    key = (wav_path, start, end)
    cache = _feature_caches['mfcc']
    if key in cache:
        return cache[key]
    y, sr = librosa.load(wav_path, sr=None, offset=start, duration=end-start)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
    val = float(np.mean(mfcc[0])) if mfcc.shape[0]>0 else None
    cache[key] = round(val,2) if val is not None else None
    return cache[key]

# Cepstral Peak Prominence (stub)
def compute_cpp(wav_path, start, end):
    # Requires Praat-specific call; stub for now
    key = (wav_path, start, end)
    cache = _feature_caches['cpp']
    if key in cache:
        return cache[key]
    # placeholder: return None
    cache[key] = None
    return None


# Dispatcher for computing feature values
def compute_feature_value(feature, wav_path, start, end, duration):
    try:
        if feature == "Duration":
            return duration
        elif feature == "Mid Intensity":
            return compute_intensity_at_midpoint(wav_path, start, end)
        elif feature == "ZCR":
            return compute_zcr(wav_path, start, end)
        elif feature == "Spectral Centroid":
            return compute_spectral_centroid(wav_path, start, end)
        elif feature == "F1":
            return compute_formants(wav_path, start, end)[0]
        elif feature == "F2":
            return compute_formants(wav_path, start, end)[1]
        elif feature == "F3":
            return compute_formants(wav_path, start, end)[2]
        elif feature == "Mean F0":
            return compute_pitch_mean(wav_path, start, end)
        elif feature == "Jitter":
            return compute_jitter(wav_path, start, end)
        elif feature == "Shimmer":
            return compute_shimmer(wav_path, start, end)
        elif feature == "HNR":
            return compute_hnr(wav_path, start, end)
        elif feature == "RMS":
            return compute_rms(wav_path, start, end)
        elif feature == "Rolloff":
            return compute_rolloff(wav_path, start, end)
        elif feature == "Bandwidth":
            return compute_bandwidth(wav_path, start, end)
        elif feature == "Flatness":
            return compute_flatness(wav_path, start, end)
        elif feature == "Contrast":
            return compute_contrast(wav_path, start, end)
        elif feature == "MFCC1":
            return compute_mfcc1(wav_path, start, end)
        elif feature == "CPP":
            return compute_cpp(wav_path, start, end)
    except Exception as e:
        print(f"❌ Error computing {feature}: {e}")
    return None
