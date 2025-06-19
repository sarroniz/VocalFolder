from pydub import AudioSegment
import simpleaudio as sa

def play_segment(wav_path, start_time=0, end_time=None):
    try:
        audio = AudioSegment.from_wav(wav_path)

        if end_time is None:
            segment = audio[start_time * 1000:]
        else:
            segment = audio[start_time * 1000:end_time * 1000]

        play_obj = sa.play_buffer(
            segment.raw_data,
            num_channels=segment.channels,
            bytes_per_sample=segment.sample_width,
            sample_rate=segment.frame_rate
        )
        return play_obj
    except Exception as e:
        print(f"Playback error: {e}")
        return None