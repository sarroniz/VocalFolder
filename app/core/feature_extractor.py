import os
import numpy as np
import parselmouth
import librosa

def compute_mean_intensity(wav_path, start_time, end_time):
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
        return round(zcr, 2)
    except Exception as e:
        print(f"❌ Error computing ZCR: {e}")
        return None

def compute_intensity_at_midpoint(wav_path, start_time, end_time):
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
        return round(intensity_value, 2)

    except Exception as e:
        print(f"❌ Error computing midpoint intensity: {e}")
        return None

def compute_spectral_centroid(wav_path, start, end):
    try:
        y, sr = librosa.load(wav_path, sr=None, offset=start, duration=end - start)
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        if centroid.size > 0:
            return round(np.mean(centroid), 2)
    except Exception as e:
        print(f"❌ Error computing spectral centroid for {wav_path} [{start}-{end}]: {e}")
    return None

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
    except Exception as e:
        print(f"❌ Error computing {feature}: {e}")
    return None