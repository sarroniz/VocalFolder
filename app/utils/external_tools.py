import subprocess
import platform
import shutil
import os

def launch_praat(wav_path, tg_path, praat_path=None):
    """
    Try to launch Praat with given wav and TextGrid.
    Returns (success: bool, error_message: str)
    """
    try:
        system = platform.system()

        if praat_path and os.path.exists(praat_path):
            cmd = [praat_path, wav_path, tg_path]
        elif system == "Darwin":
            cmd = ["open", "-a", "Praat", wav_path, tg_path]
        elif system == "Windows":
            praat_exe = shutil.which("Praat.exe") or shutil.which("praat.exe")
            if not praat_exe:
                return False, "Could not find 'Praat.exe'. Set the path via File > Set Praat Path…"
            cmd = [praat_exe, wav_path, tg_path]
        else:  # Linux
            praat_bin = shutil.which("praat")
            if not praat_bin:
                return False, "Could not find 'praat' in PATH. Set the path via File > Set Praat Path…"
            cmd = [praat_bin, wav_path, tg_path]

        print(f"📤 Launching: {' '.join(cmd)}")
        subprocess.Popen(cmd)
        return True, ""

    except Exception as e:
        return False, f"Error launching Praat: {e}"