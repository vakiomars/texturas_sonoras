from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf


SUPPORTED_EXTENSIONS = {"wav", "mp3", "ogg", "flac", "m4a", "aac", "mp4", "3gp"}
MOBILE_EXTENSIONS = {"m4a", "aac", "mp4", "3gp"}


def load_audio_uploaded(uploaded_file, target_sr: int = 48000) -> tuple[np.ndarray, int]:
    name = getattr(uploaded_file, "name", "") or ""
    ext = Path(name).suffix.lower().lstrip(".")
    suffix = f".{ext}" if ext else ""

    raw = uploaded_file.getbuffer() if hasattr(uploaded_file, "getbuffer") else uploaded_file.read()
    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(raw)
            tmp_path = tmp.name

        try:
            y, sr = librosa.load(tmp_path, sr=target_sr, mono=True)
            return y.astype(np.float32), target_sr
        except Exception:
            if ext not in MOBILE_EXTENSIONS:
                raise

        from pydub import AudioSegment
        import imageio_ffmpeg

        AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()
        audio = AudioSegment.from_file(tmp_path)
        buf = io.BytesIO()
        audio.export(buf, format="wav")
        buf.seek(0)
        data, sr = sf.read(buf, dtype="float32", always_2d=True)
        y = data.mean(axis=1)
        if sr != target_sr:
            y = librosa.resample(y, orig_sr=sr, target_sr=target_sr)
        return y.astype(np.float32), target_sr
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
