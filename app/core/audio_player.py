from pydub import AudioSegment
import simpleaudio as sa
import threading
import time

class AudioPlayer:
    def __init__(self):
        self.current_playback = None
        self.is_playing = False
        
    def stop(self):
        """Stop current playback"""
        if self.current_playback and self.is_playing:
            try:
                self.current_playback.stop()
                self.is_playing = False
                print("🛑 Playback stopped")
            except Exception as e:
                print(f"Error stopping playback: {e}")
                
    def play_segment(self, wav_path, start_time=0.0, end_time=None):
        """
        Play the given wav_path from start_time to end_time (in seconds).
        If end_time is None, play until the end of the file.
        Returns the AudioPlayer instance for chaining.
        """
        # Stop any existing playback first
        self.stop()
        
        try:
            print(f"🔊 Loading audio: {wav_path}")
            audio = AudioSegment.from_wav(wav_path)
            
            # Convert times to milliseconds and validate
            start_ms = max(0, int(start_time * 1000))
            
            if end_time is None:
                end_ms = len(audio)
                print(f"🔊 Playing from {start_time:.2f}s to end ({len(audio)/1000:.2f}s)")
            else:
                end_ms = min(len(audio), int(end_time * 1000))
                print(f"🔊 Playing from {start_time:.2f}s to {end_time:.2f}s")
            
            # Ensure we have a valid segment
            if end_ms <= start_ms:
                print(f"⚠️ Invalid segment: start={start_ms}ms, end={end_ms}ms")
                # Fallback: play 1 second from start
                end_ms = min(start_ms + 1000, len(audio))
                print(f"🔄 Fallback: playing {start_ms}ms to {end_ms}ms")
            
            # Extract the segment
            segment = audio[start_ms:end_ms]
            
            if len(segment) == 0:
                print("⚠️ Empty audio segment")
                return self
            
            # Ensure we have audio data
            print(f"🎵 Segment duration: {len(segment)/1000:.2f}s")
            print(f"🎵 Channels: {segment.channels}, Sample rate: {segment.frame_rate}")
            
            # Play the segment
            self.current_playback = sa.play_buffer(
                segment.raw_data,
                num_channels=segment.channels,
                bytes_per_sample=segment.sample_width,
                sample_rate=segment.frame_rate
            )
            
            self.is_playing = True
            
            # Start a thread to monitor playback completion
            threading.Thread(target=self._monitor_playback, daemon=True).start()
            
            return self
            
        except Exception as e:
            print(f"❌ Playback error: {e}")
            import traceback
            traceback.print_exc()
            self.is_playing = False
            return self
    
    def _monitor_playback(self):
        """Monitor playback completion in a separate thread"""
        try:
            if self.current_playback:
                self.current_playback.wait_done()
                self.is_playing = False
                print("✅ Playback completed")
        except Exception as e:
            print(f"Error monitoring playback: {e}")
            self.is_playing = False

# Global audio player instance
_audio_player = AudioPlayer()

def play_segment(wav_path, start_time=0.0, end_time=None):
    """
    Convenience function that uses the global audio player.
    Play the given wav_path from start_time to end_time (in seconds).
    If end_time is None, play until the end of the file.
    """
    return _audio_player.play_segment(wav_path, start_time, end_time)

def stop_playback():
    """Stop any current playback"""
    _audio_player.stop()