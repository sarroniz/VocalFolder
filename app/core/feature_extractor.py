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
}

formant_mode = "midpoint" 


def clear_all_feature_caches():
    for name, cache in _feature_caches.items():
        cache.clear()
        print(f"🧹 Cleared cache: {name}")


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


def compute_feature_value(feature, wav_path, start, end, duration):
    """Dispatcher for computing a feature value"""
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
    except Exception as e:
        print(f"❌ Error computing {feature}: {e}")
    return None