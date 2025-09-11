# src/dsp.py
from __future__ import annotations
import io
import numpy as np
import soundfile as sf
from scipy.signal import butter, filtfilt

# Opcional: mejor resampling si hay soxr (librosa ya lo usa por defecto si está)
try:
    import librosa
    _HAS_LIBROSA = True
except Exception:
    _HAS_LIBROSA = False

# Reverb (Pedalboard) opcional
try:
    from pedalboard import Pedalboard, Reverb
    _HAS_PEDALBOARD = True
except Exception:
    _HAS_PEDALBOARD = False


EPS = 1e-9


# -------- utilidades robustas --------
def _fix_length_np(x: np.ndarray, size: int) -> np.ndarray:
    """Recorta o rellena con ceros hasta 'size' (evita depender de librosa.util.fix_length)."""
    n = len(x)
    if n == size:
        return x
    if n > size:
        return x[:size]
    out = np.zeros(size, dtype=x.dtype)
    out[:n] = x
    return out


def normalize_peak(y: np.ndarray, peak: float = 0.95) -> np.ndarray:
    m = float(np.max(np.abs(y)) + EPS)
    return (y / m * peak).astype(np.float32)


# -------- filtros fase-cero --------
def highpass(y: np.ndarray, sr: int, cutoff_hz: float = 80.0) -> np.ndarray:
    nyq = sr / 2.0
    c = float(np.clip(cutoff_hz, 10.0, nyq - 10.0))
    b, a = butter(4, c / nyq, btype="high", analog=False)
    return filtfilt(b, a, y).astype(np.float32)


def lowpass(y: np.ndarray, sr: int, cutoff_hz: float = 15000.0) -> np.ndarray:
    nyq = sr / 2.0
    c = float(np.clip(cutoff_hz, 1000.0, nyq - 10.0))
    b, a = butter(4, c / nyq, btype="low", analog=False)
    return filtfilt(b, a, y).astype(np.float32)


# -------- granular OLA estable --------
def granular_extend(
    y: np.ndarray,
    sr: int,
    target_duration_s: float = 30.0,
    grain_ms: float = 300.0,
    overlap: float = 0.75,
    rand_pos: float = 0.10,
    pitch_rand_semitones: float = 0.0,
) -> np.ndarray:
    """
    Extiende 'y' con granular OLA usando ventana Hann y normalización de solapamientos.
    - Ventana Hann + suma de pesos -> amplitud estable (evita 'pumping').
    - 'rand_pos' añade jitter leve para evitar patrones.
    - Pitch aleatorio con librosa.effects.pitch_shift (librosa 0.10+: sr keyword).
    """
    assert sr > 0
    grain_len = int(sr * (grain_ms / 1000.0))
    grain_len = max(grain_len, 32)

    if len(y) < grain_len:
        y = _fix_length_np(y, grain_len)

    hop = max(int(grain_len * (1.0 - float(overlap))), 1)
    target_samples = max(int(target_duration_s * sr), grain_len + 1)

    out = np.zeros(target_samples, dtype=np.float32)
    wsum = np.zeros(target_samples, dtype=np.float32)  # acumulador de pesos (para normalizar OLA)
    window = np.hanning(grain_len).astype(np.float32)

    pos = 0
    max_start = max(1, len(y) - grain_len)

    rng = np.random.default_rng()
    use_pitch = _HAS_LIBROSA and (pitch_rand_semitones > 0.0)

    while pos < target_samples - grain_len:
        start = rng.integers(0, max_start)
        if rand_pos > 0:
            jitter = rng.uniform(-rand_pos, rand_pos)
            start = int(start * (1.0 + jitter))
            start = int(np.clip(start, 0, max_start - 1))

        grain = y[start:start + grain_len].astype(np.float32)
        if len(grain) != grain_len:
            grain = _fix_length_np(grain, grain_len)

        if use_pitch:
            shift = float(rng.uniform(-pitch_rand_semitones, pitch_rand_semitones))
            # librosa 0.10+: sr es keyword; usa soxr_hq si está disponible
            grain = librosa.effects.pitch_shift(grain, n_steps=shift, sr=sr)
            grain = _fix_length_np(grain, grain_len)

        win_grain = grain * window
        out[pos:pos + grain_len] += win_grain
        wsum[pos:pos + grain_len] += window
        pos += hop

    # Normalización por suma de ventanas para evitar modulación de ganancia
    wsum = np.maximum(wsum, EPS)
    out = (out / wsum).astype(np.float32)
    return normalize_peak(out, 0.95)


# -------- reverb y dinámicas --------
def reverb_ambient(y: np.ndarray, sr: int, room: float = 0.25, wet: float = 0.07, damping: float = 0.2) -> np.ndarray:
    if not _HAS_PEDALBOARD:
        return y
    board = Pedalboard([Reverb(room_size=float(room), wet_level=float(wet), damping=float(damping))])
    y2 = board(y.astype(np.float32), sr)
    return normalize_peak(y2, 0.95)


def limiter_true_peak(y: np.ndarray, ceiling_db: float = -1.0) -> np.ndarray:
    # Limitador simple basado en pico, con margen de -1 dB
    peak = float(np.max(np.abs(y)) + EPS)
    ceiling_lin = 10.0 ** (ceiling_db / 20.0)
    return (y / peak * ceiling_lin).astype(np.float32)


# -------- I/O --------
def to_wav_bytes(y: np.ndarray, sr: int) -> io.BytesIO:
    buf = io.BytesIO()
    sf.write(buf, y, sr, format="WAV", subtype="PCM_24")
    buf.seek(0)
    return buf


# -------- pipeline de alto nivel --------
def process_natural_texture(
    y: np.ndarray,
    sr: int,
    *,
    hpf_hz: float,
    lpf_hz: float,
    do_granular: bool,
    target_s: float,
    grain_ms: float,
    overlap: float,
    rand_pos: float,
    pitch_rand_semitones: float,
    do_reverb: bool,
    room: float,
    wet: float,
    damping: float,
    do_limiter: bool = True,
) -> np.ndarray:
    # 1) limpieza
    y2 = highpass(y, sr, hpf_hz)
    y2 = lowpass(y2, sr, lpf_hz)

    # 2) granular (opcional)
    if do_granular:
        y2 = granular_extend(
            y2, sr,
            target_duration_s=target_s,
            grain_ms=grain_ms,
            overlap=overlap,
            rand_pos=rand_pos,
            pitch_rand_semitones=pitch_rand_semitones,
        )

    # 3) reverb (opcional)
    if do_reverb:
        y2 = reverb_ambient(y2, sr, room=room, wet=wet, damping=damping)

    # 4) limitador + normalización
    if do_limiter:
        y2 = limiter_true_peak(y2, ceiling_db=-1.0)

    return normalize_peak(y2, 0.95)
