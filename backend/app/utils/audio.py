import os
import subprocess
import tempfile
from pathlib import Path


class AudioConverter:
    @staticmethod
    def webm_to_wav(audio_bytes: bytes) -> Path:
        tmp_webm = tempfile.NamedTemporaryFile(suffix=".webm", delete=False)
        tmp_wav_path = Path(tmp_webm.name).with_suffix(".wav")
        try:
            tmp_webm.write(audio_bytes)
            tmp_webm.flush()
            tmp_webm.close()

            cmd = [
                "ffmpeg",
                "-i",
                tmp_webm.name,
                "-ar",
                "16000",
                "-ac",
                "1",
                "-f",
                "wav",
                "-y",
                str(tmp_wav_path),
            ]
            proc = subprocess.run(cmd, check=False, capture_output=True)
            if proc.returncode != 0:
                stderr = proc.stderr.decode("utf-8", errors="ignore")
                raise RuntimeError(f"ffmpeg conversion failed: {stderr}")
            return tmp_wav_path
        finally:
            if os.path.exists(tmp_webm.name):
                os.unlink(tmp_webm.name)
