# src/app.py
import streamlit as st
import numpy as np
import librosa

from dsp import (
    to_wav_bytes,
    make_seamless_loop,
    evolve_texture,
    has_reverb_support,
)

# -------- ajustes UI --------
st.set_page_config(page_title="Texturas Sonoras — Prototipo Elegante", layout="centered")
st.title("🎶 Generador de Texturas Sonoras (Prototipo Elegante)")
st.caption("48 kHz / 24-bit • Granular OLA Hann • Filtros fase-cero • Reverb opcional • MGI activo (α + Π_C)")

uploaded = st.file_uploader("🎵 Sube un archivo (WAV/MP3/OGG/FLAC)", type=["wav", "mp3", "ogg", "flac"])

# límites seguros de RAM (≈ 10 MB por minuto mono float32 @48 kHz)
MAX_SECONDS = 120  # 2 min para MVP estable
SR = 48000


def _mem_ok(target_s: int) -> bool:
    est_bytes = int(target_s * SR) * 4  # float32
    # aquí podrías leer RAM real; como MVP usamos un umbral fijo (~500 MB)
    return est_bytes < 500 * 1024 * 1024


if uploaded:
    # Cargar a mono 48 kHz para coherencia con motores de juego
    y, sr = librosa.load(uploaded, sr=SR, mono=True)
    st.audio(to_wav_bytes(y, sr), format="audio/wav")
    st.info(f"Origen: {len(y)/sr:.2f} s @ {sr} Hz")

    st.subheader("🎚 Limpieza")
    hpf = st.slider("Corte graves (Hz)", 20, 200, 80)
    lpf = st.slider("Corte agudos (Hz)", 2000, 20000, 15000)

    st.subheader("🌊 Extensión granular")
    do_gran = st.checkbox("Extender con granular OLA")
    if do_gran:
        target = st.number_input("Duración objetivo (s)", min_value=10, max_value=MAX_SECONDS, value=60)
        grain_ms = st.slider("Tamaño del grano (ms)", 50, 500, 300)
        overlap = st.slider("Solapamiento", 0.10, 0.90, 0.75)
        rand_pos = st.slider("Aleatoriedad de posición", 0.00, 0.30, 0.10)
        pitch_rand = st.slider("Pitch rand (± semitonos)", 0.00, 1.00, 0.10)

        if not _mem_ok(int(target)):
            st.warning("⚠️ Esa duración estimada puede agotar memoria. Reduce ‘Duración objetivo’.")
            target = min(int(target), 60)
    else:
        # defaults coherentes si no hay granular
        target = float(len(y) / SR)
        grain_ms = 300
        overlap = 0.75
        rand_pos = 0.10
        pitch_rand = 0.0

    st.subheader("🏞 Reverb ambiental")
    do_rev = st.checkbox("Añadir reverb (sutil)")

    if do_rev and not has_reverb_support():
        st.warning("Reverb no disponible: instala `pedalboard` (`pip install pedalboard`). Se procesará sin reverb.")

    if do_rev:
        room = st.slider("Tamaño de sala", 0.0, 1.0, 0.25)
        wet = st.slider("Mezcla (wet)", 0.0, 0.3, 0.07)
        damp = st.slider("Damping", 0.0, 1.0, 0.2)
    else:
        room = 0.25
        wet = 0.07
        damp = 0.2

    st.subheader("🔁 Loop")
    loop_option = st.checkbox("🔁 Hacer loop seamless", value=False)
    crossfade_ms = st.slider("Duración crossfade (ms)", 50, 500, 150)

    # ==============================
    # Evolutive Controls (v2)
    # ==============================
    st.markdown("## Evolutive Operator Controls")

    iterations = st.number_input("Iterations (K)", min_value=1, max_value=20, value=1)
    alpha = st.slider("Alpha (Preservation ↔ Diffusion)", 0.0, 1.0, 1.0, 0.05)
    seed_mode2 = st.selectbox("Seed Mode", ["fixed", "progressive", "random"], index=0)
    base_seed = int(st.number_input("Base seed", min_value=0, max_value=2_147_483_647, value=1234))

    st.markdown("### MGI (activo): restricciones + control")
    use_active = st.checkbox("Usar MGI activo (recomendado para validación científica)", value=True)
    return_log = st.checkbox("Guardar bitácora por iteración (CSV)", value=True)

    if use_active:
        peak_ceiling_dbfs = st.slider("Headroom (sample peak ceiling, dBFS)", -12.0, -0.5, -2.0, 0.5)
        rms_tol_db = st.slider("Tolerancia RMS vs x0 (dB)", 0.5, 18.0, 6.0, 0.5)
        st.caption("Nota: usamos sample-peak con margen (dBFS) como proxy conservador de true-peak.")

        st.markdown("**Φ(x) tolerancias (momentos/entropía)**")
        d_mu = st.number_input("δ_mu", min_value=0.0, max_value=1.0, value=0.05, step=0.01)
        d_var = st.number_input("δ_var", min_value=0.0, max_value=2.0, value=0.05, step=0.01)
        d_kurt = st.number_input("δ_kurt", min_value=0.0, max_value=20.0, value=2.0, step=0.5)
        d_H = st.number_input("δ_entropy", min_value=0.0, max_value=5.0, value=0.5, step=0.1)
        enable_hist = st.checkbox("Histogram-match hacia x0 (lento; experimental)", value=False)

        st.markdown("**Control activo de α (backtracking)**")
        alpha_min = st.slider("α_min", 0.0, 0.5, 0.05, 0.01)
        beta = st.slider("β (reducción multiplicativa)", 0.1, 0.99, 0.8, 0.01)
        max_back = st.slider("Máx backtracks", 0, 20, 6, 1)

    if st.button("✨ Procesar"):
        # Import local para no romper si el usuario ejecuta solo dsp.py
        from mgi import ConstraintConfig

        theta = dict(
            hpf_hz=float(hpf),
            lpf_hz=float(lpf),
            do_granular=bool(do_gran),
            target_s=float(target),
            grain_ms=float(grain_ms),
            overlap=float(overlap),
            rand_pos=float(rand_pos),
            pitch_rand_semitones=float(pitch_rand),
            do_reverb=bool(do_rev),
            room=float(room),
            wet=float(wet),
            damping=float(damp),
            # Legacy limiter is sample-peak; in MGI-active we disable it and let Π_C handle stability.
            do_limiter=not bool(use_active),
            post_peak=0.95,
            post_peak_mode="force",
        )

        cfg = None
        if use_active:
            cfg = ConstraintConfig(
                delta_phi=np.array([float(d_mu), float(d_var), float(d_kurt), float(d_H)], dtype=np.float64),
                rms_tol_db=float(rms_tol_db),
                peak_ceiling_dbfs=float(peak_ceiling_dbfs),
                enable_hist_match=bool(enable_hist),
                alpha_min=float(alpha_min),
                backtrack_beta=float(beta),
                max_backtracks=int(max_back),
            )

        with st.status("Procesando…", expanded=False):
            out = evolve_texture(
                y,
                SR,
                theta=theta,
                base_seed=base_seed,
                iterations=int(iterations),
                alpha=float(alpha),
                seed_mode=str(seed_mode2),
                use_active=bool(use_active),
                constraint_config=cfg,
                return_log=bool(return_log),
            )

            if return_log:
                y_out, logs = out
            else:
                y_out, logs = out, []

            if loop_option:
                y_out = make_seamless_loop(y_out, SR, crossfade_ms=int(crossfade_ms))

        st.audio(to_wav_bytes(y_out, SR), format="audio/wav")

        if logs:
            st.markdown("### Bitácora por iteración (MGI)")
            # Prefer pandas if available; otherwise fall back to pure-python CSV.
            try:
                import pandas as pd

                df = pd.DataFrame(logs)
                st.dataframe(df, use_container_width=True)
                csv_bytes = df.to_csv(index=False).encode("utf-8")
            except Exception:
                import csv
                import io

                st.dataframe(logs, use_container_width=True)
                buf = io.StringIO()
                w = csv.DictWriter(buf, fieldnames=list(logs[0].keys()))
                w.writeheader()
                w.writerows(logs)
                csv_bytes = buf.getvalue().encode("utf-8")

            st.download_button(
                "⬇️ Descargar métricas (CSV)",
                csv_bytes,
                file_name="mgi_metrics.csv",
                mime="text/csv",
            )
        st.download_button(
            "⬇️ Descargar WAV (24-bit/48 kHz)",
            to_wav_bytes(y_out, SR),
            file_name="textura.wav",
            mime="audio/wav",
        )
else:
    st.info("Sube un audio para habilitar el motor.")
