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
st.set_page_config(page_title="Texturas Sonoras", layout="centered")
st.title("Texturas Sonoras")
st.caption("Convierte un audio corto en una textura más larga, suave y lista para escuchar o descargar.")
st.markdown(
    "1. Sube un audio corto\n"
    "2. Ajusta el carácter del resultado\n"
    "3. Genera y descarga una textura más larga"
)

st.header("Paso 1 - Sube tu audio")
uploaded = st.file_uploader("Sube tu audio base", type=["wav", "mp3", "ogg", "flac"])

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

    st.header("Paso 2 - Ajusta el resultado")
    st.subheader("Limpieza del sonido")
    hpf = st.slider("Recorte de graves", 20, 200, 80)
    lpf = st.slider("Recorte de agudos", 2000, 20000, 15000)

    st.subheader("Extensión")
    do_gran = st.checkbox("Extender audio")
    if do_gran:
        target = st.number_input("Duración final", min_value=10, max_value=MAX_SECONDS, value=60)
        grain_ms = st.slider("Detalle de textura", 50, 500, 300)
        overlap = st.slider("Suavidad de unión", 0.10, 0.90, 0.75)
        rand_pos = st.slider("Variación de fragmentos", 0.00, 0.30, 0.10)
        pitch_rand = st.slider("Variación de tono", 0.00, 1.00, 0.10)

        if not _mem_ok(int(target)):
            st.warning("⚠️ Esa duración estimada puede agotar memoria. Reduce 'Duración final'.")
            target = min(int(target), 60)
    else:
        # defaults coherentes si no hay granular
        target = float(len(y) / SR)
        grain_ms = 300
        overlap = 0.75
        rand_pos = 0.10
        pitch_rand = 0.0

    st.subheader("Ambiente")
    do_rev = st.checkbox("Añadir ambiente")

    if do_rev and not has_reverb_support():
        st.warning("Reverb no disponible: instala `pedalboard` (`pip install pedalboard`). Se procesará sin reverb.")

    if do_rev:
        room = st.slider("Tamaño del espacio", 0.0, 1.0, 0.25)
        wet = st.slider("Cantidad de ambiente", 0.0, 0.3, 0.07)
        damp = st.slider("Suavidad del ambiente", 0.0, 1.0, 0.2)
    else:
        room = 0.25
        wet = 0.07
        damp = 0.2

    st.subheader("Loop")
    loop_option = st.checkbox("Preparar loop continuo", value=False)
    crossfade_ms = st.slider("Suavidad del loop", 50, 500, 150)

    st.caption("Si solo quieres probar la app, no necesitas tocar estas opciones.")
    with st.expander("Opciones avanzadas (solo si quieres ajustar más)"):
        st.caption("Estas opciones te permiten ajustar con más detalle la transformación y la estabilidad del resultado.")
        st.markdown("### Estabilidad y control fino")
        iterations = st.number_input("Pasadas de evolución", min_value=1, max_value=20, value=1)
        alpha = st.slider("Intensidad de transformación", 0.0, 1.0, 1.0, 0.05)
        seed_mode2 = st.selectbox("Variación", ["fixed", "progressive", "random"], index=0)
        base_seed = int(st.number_input("Semilla base", min_value=0, max_value=2_147_483_647, value=1234))
        use_active = st.checkbox("Usar control extra para mantener un resultado más estable", value=True)
        return_log = st.checkbox("Guardar detalle del proceso por paso (CSV)", value=True)

        if use_active:
            peak_ceiling_dbfs = st.slider("Margen de pico (dBFS)", -12.0, -0.5, -2.0, 0.5)
            rms_tol_db = st.slider("Tolerancia de nivel RMS frente al audio original (dB)", 0.5, 18.0, 6.0, 0.5)
            st.caption("Usamos control de sample-peak con margen como referencia conservadora de estabilidad.")

            st.markdown("**Tolerancias de análisis**")
            d_mu = st.number_input("δ_mu", min_value=0.0, max_value=1.0, value=0.05, step=0.01)
            d_var = st.number_input("δ_var", min_value=0.0, max_value=2.0, value=0.05, step=0.01)
            d_kurt = st.number_input("δ_kurt", min_value=0.0, max_value=20.0, value=2.0, step=0.5)
            d_H = st.number_input("δ_entropy", min_value=0.0, max_value=5.0, value=0.5, step=0.1)
            enable_hist = st.checkbox("Ajustar distribución hacia el audio original (más lento)", value=False)

            st.markdown("**Ajuste de intensidad en cada intento**")
            alpha_min = st.slider("α_min", 0.0, 0.5, 0.05, 0.01)
            beta = st.slider("β (reducción multiplicativa)", 0.1, 0.99, 0.8, 0.01)
            max_back = st.slider("Máximo de reajustes", 0, 20, 6, 1)

    st.header("Paso 3 - Genera")
    if st.button("Generar textura"):
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

        st.header("Paso 4 - Escucha y descarga")
        st.audio(to_wav_bytes(y_out, SR), format="audio/wav")

        if logs:
            st.markdown("### Detalle del proceso por iteración")
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
                "Descargar detalle del proceso (CSV)",
                csv_bytes,
                file_name="mgi_metrics.csv",
                mime="text/csv",
            )
        st.download_button(
            "Descargar audio final en WAV (24-bit/48 kHz)",
            to_wav_bytes(y_out, SR),
            file_name="textura.wav",
            mime="audio/wav",
        )
else:
    st.info("Sube un audio para comenzar.")
