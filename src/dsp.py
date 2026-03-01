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
    """Normalize *up or down* so that max(abs(y)) == peak.

    Note: for scientific/iterative runs you typically want "down-only" scaling
    (never amplify), handled elsewhere (Pi_C / constraints).
    """
    m = float(np.max(np.abs(y)) + EPS)
    return (y / m * peak).astype(np.float32)


def scale_down_to_peak(y: np.ndarray, peak: float = 0.95) -> np.ndarray:
    """Scale *down only* so that max(abs(y)) <= peak."""
    m = float(np.max(np.abs(y)) + EPS)
    if m <= peak:
        return y.astype(np.float32)
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
    seed: int | None = None,
    peak_ceiling: float = 0.95,
    normalize_mode: str = "force",  # "force" (legacy) or "down_only" (canonical)
) -> np.ndarray:
    """
    Extiende 'y' con granular OLA usando ventana Hann y normalización de solapamientos.
    - Ventana Hann + suma de pesos -> amplitud estable (evita 'pumping').
    - 'rand_pos' añade jitter leve para evitar patrones.
    - Pitch aleatorio con librosa.effects.pitch_shift (librosa 0.10+: sr keyword).
    """
    if sr <= 0:
        raise ValueError(f"Sample rate must be positive, got {sr}")
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

    # RNG determinístico (si seed se define) para poder reproducir exactamente
    # el mismo resultado en juego/producción.
    rng = np.random.default_rng(seed)
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

    # Legacy behavior: force to a fixed peak (can amplify).
    # Canonical behavior: only scale down (preserves energy statistics better).
    if normalize_mode == "down_only":
        return scale_down_to_peak(out, float(peak_ceiling))
    return normalize_peak(out, float(peak_ceiling))


# -------- reverb y dinámicas --------
def has_reverb_support() -> bool:
    """Return True if pedalboard is available for reverb processing."""
    return _HAS_PEDALBOARD


def reverb_ambient(y: np.ndarray, sr: int, room: float = 0.25, wet: float = 0.07, damping: float = 0.2) -> np.ndarray:
    if not _HAS_PEDALBOARD:
        return y
    board = Pedalboard([Reverb(room_size=float(room), wet_level=float(wet), damping=float(damping))])
    y2 = board(y.astype(np.float32), sr)
    return normalize_peak(y2, 0.95)


def limiter_true_peak(y: np.ndarray, ceiling_db: float = -1.0) -> np.ndarray:
    """Legacy: sample-peak limiter (name kept for backwards compat).

    WARNING: This is NOT a true-peak limiter.
    """
    peak = float(np.max(np.abs(y)) + EPS)
    ceiling_lin = 10.0 ** (ceiling_db / 20.0)
    return (y / peak * ceiling_lin).astype(np.float32)


def limiter_sample_peak(y: np.ndarray, ceiling_db: float = -1.0) -> np.ndarray:
    """Sample-peak limiter (preferred explicit name)."""
    return limiter_true_peak(y, ceiling_db=ceiling_db)


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
    seed: int | None = None,
    do_reverb: bool,
    room: float,
    wet: float,
    damping: float,
    do_limiter: bool = True,
    post_peak: float | None = 0.95,
    post_peak_mode: str = "force",  # "force" or "down_only"
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
            seed=seed,
            peak_ceiling=float(post_peak or 0.95),
            normalize_mode=str(post_peak_mode),
        )

    # 3) reverb (opcional)
    if do_reverb:
        y2 = reverb_ambient(y2, sr, room=room, wet=wet, damping=damping)

    # 4) limitador + normalización
    if do_limiter:
        # Sample-peak limiting only (legacy). Avoid forcing a higher peak afterwards.
        y2 = limiter_sample_peak(y2, ceiling_db=-1.0)

    # Optional post scaling.
    if post_peak is None:
        return y2.astype(np.float32)
    if post_peak_mode == "down_only":
        return scale_down_to_peak(y2, float(post_peak))
    return normalize_peak(y2, float(post_peak))

def make_seamless_loop(y, sr, crossfade_ms=100):
    """
    Ajusta un audio para que pueda repetirse en bucle sin cortes perceptibles.
    - Busca cero-cruces.
    - Aplica crossfade corto entre inicio y fin.
    - Normaliza.
    """
    crossfade = int(sr * crossfade_ms / 1000)

    # Buscar cero-cruces y elegir un recorte que reduzca discontinuidad.
    zc = np.where(np.sign(y[:-1]) != np.sign(y[1:]))[0]
    if len(zc) == 0:
        return y.astype(np.float32)

    # Inicio: primer cero-cruce
    start = int(zc[0])

    # Fin: último cero-cruce que deje espacio para el crossfade
    latest = len(y) - crossfade - 1
    zc_end = zc[zc < latest]
    end = int(zc_end[-1]) if len(zc_end) else len(y)

    # Recortar (copy to avoid mutating the caller's array)
    y = y[start:end].copy()

    # Crossfade (overlap-add simple)
    if len(y) < 2 * crossfade:
        return y.astype(np.float32)

    fade_in = np.linspace(0, 1, crossfade)
    fade_out = np.linspace(1, 0, crossfade)

    y[:crossfade] *= fade_in
    y[-crossfade:] *= fade_out
    y[:crossfade] += y[-crossfade:]
    y = y[:-crossfade]

    # Normalizar
    y = y / (np.max(np.abs(y)) + 1e-9)
    return y.astype(np.float32)


# ==============================
# Iterative Evolutive Operator
# ==============================

from mgi.operator import seed_policy


def evolve_texture(
    x0,
    sr,
    theta: dict,
    base_seed=None,
    iterations: int = 1,
    alpha: float = 1.0,
    seed_mode: str = "fixed",
    *,
    use_active: bool = True,
    constraint_config=None,
    return_log: bool = False,
):
    """
    Iterative evolutive operator.

    x_{k+1} = (1-alpha)*x0 + alpha*T(x_k; theta, seed_k)

    where T is process_natural_texture.
    """

    # Active MGI operator (recommended): backtracking on α + Π_C.
    if use_active:
        from mgi import ConstraintConfig
        from mgi.operator import evolve_active

        cfg = constraint_config if constraint_config is not None else ConstraintConfig()

        def _T(xk, sr_local, seed_k):
            # For the state evolution we avoid "force" peak normalization.
            # Let Π_C enforce energy + headroom.
            theta2 = dict(theta)
            theta2.setdefault("do_limiter", False)
            theta2.setdefault("post_peak", None)
            theta2.setdefault("post_peak_mode", "down_only")
            return process_natural_texture(xk, sr=sr_local, seed=seed_k, **theta2)

        return evolve_active(
            x0=np.asarray(x0, dtype=np.float32),
            sr=int(sr),
            transform=_T,
            iterations=int(iterations),
            alpha=float(alpha),
            cfg=cfg,
            base_seed=None if base_seed is None else int(base_seed),
            seed_mode=str(seed_mode),
            embed_anchor=lambda a, L, sr_: _anchor_to_length(a, target_len=L, sr=sr_, xfade_ms=50),
            return_log=bool(return_log),
        )

    # Legacy operator: simple iterative chaining + anchor mix
    xk = np.asarray(x0, dtype=np.float32).copy()
    for k in range(iterations):
        sk = seed_policy(base_seed, k, seed_mode)
        yk = process_natural_texture(xk, sr=sr, **theta, seed=sk)
        L = len(yk)
        x0_hat = _anchor_to_length(x0, target_len=L, sr=sr, xfade_ms=50)
        yk = (1 - alpha) * x0_hat + alpha * yk
        xk = yk
    return (xk, []) if return_log else xk


def _anchor_to_length(x: np.ndarray, target_len: int, sr: int, xfade_ms: int = 50) -> np.ndarray:
    """Map the anchor x (x0) to target_len, preserving its character.

    Strategy:
      - If x is longer: truncate.
      - If x is shorter: loop/tiling with overlap-add crossfade to avoid hard seams.

    This keeps the operator's domain consistent: len(x_{k+1}) == len(T(...)).
    """
    x = np.asarray(x, dtype=np.float32)
    if target_len <= 0:
        return np.zeros(0, dtype=np.float32)
    if len(x) == target_len:
        return x
    if len(x) > target_len:
        return x[:target_len]

    # Loop with OLA crossfade
    n = len(x)
    xfade = int(sr * (xfade_ms / 1000.0))
    xfade = int(np.clip(xfade, 0, max(0, n // 2)))
    if xfade <= 0:
        reps = int(np.ceil(target_len / n))
        return np.tile(x, reps)[:target_len].astype(np.float32)

    hop = n - xfade
    hop = max(hop, 1)

    # Window: flat with raised-cosine fades at both ends
    w = np.ones(n, dtype=np.float32)
    fade = np.linspace(0.0, 1.0, xfade, dtype=np.float32)
    w[:xfade] = fade
    w[-xfade:] = fade[::-1]

    out = np.zeros(target_len, dtype=np.float32)
    wsum = np.zeros(target_len, dtype=np.float32)

    pos = 0
    while pos < target_len:
        end = min(pos + n, target_len)
        sl = end - pos
        out[pos:end] += x[:sl] * w[:sl]
        wsum[pos:end] += w[:sl]
        pos += hop

    out /= np.maximum(wsum, EPS)
    return out.astype(np.float32)
