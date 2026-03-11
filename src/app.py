# src/app.py
import json
import sys
from datetime import datetime, timezone

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
st.caption(
    "Demo publica para validar rapido el resultado a partir de una muestra corta. "
    "Esta app no depende de IA generativa."
)
st.markdown(
    "1. Sube un audio corto\n"
    "2. Ajusta controles simples de la textura\n"
    "3. Genera, escucha y descarga una version de demo"
)

st.header("Paso 1 - Sube tu audio")
uploaded = st.file_uploader("Sube tu audio base", type=["wav", "mp3"])

MAX_INPUT_SECONDS = 45
MAX_OUTPUT_SECONDS = 90
SR = 48000


def log_event(event, **kwargs):
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
    }
    payload.update(kwargs)
    print(json.dumps(payload, ensure_ascii=True), file=sys.stdout, flush=True)


if "busy" not in st.session_state:
    st.session_state.busy = False


if uploaded:
    filename = uploaded.name
    file_format = filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"

    # Cargar a mono 48 kHz para coherencia con motores de juego
    y, sr = librosa.load(uploaded, sr=SR, mono=True)
    input_seconds = len(y) / sr

    log_event(
        "upload_received",
        filename=filename,
        input_seconds=round(input_seconds, 4),
        format=file_format,
    )

    if input_seconds > MAX_INPUT_SECONDS:
        log_event(
            "validation_failed",
            filename=filename,
            input_seconds=round(input_seconds, 4),
            format=file_format,
            error_type="input_too_long",
        )
        st.error(
            "La demo publica admite muestras base cortas. "
            f"Sube un audio de hasta {MAX_INPUT_SECONDS} segundos."
        )
        st.stop()

    st.audio(to_wav_bytes(y, sr), format="audio/wav")
    st.info(f"Origen: {input_seconds:.2f} s @ {sr} Hz")

    st.header("Paso 2 - Ajusta el resultado")
    hpf = st.slider("Recorte de graves", 20, 200, 80)
    lpf = st.slider("Recorte de agudos", 2000, 20000, 15000)
    target = st.number_input("Duracion final", min_value=10, max_value=MAX_OUTPUT_SECONDS, value=60)
    grain_ms = st.slider("Detalle de textura", 50, 500, 300)
    overlap = st.slider("Suavidad de union", 0.10, 0.90, 0.75)

    rand_pos = 0.10
    pitch_rand = 0.0
    do_rev = False
    room = 0.25
    wet = 0.07
    damp = 0.2
    loop_option = False
    iterations = 1
    alpha = 1.0
    seed_mode2 = "fixed"
    base_seed = 1234
    use_active = True
    return_log = False
    peak_ceiling_dbfs = -2.0
    rms_tol_db = 6.0
    d_mu = 0.05
    d_var = 0.05
    d_kurt = 2.0
    d_H = 0.5
    enable_hist = False
    alpha_min = 0.05
    beta = 0.8
    max_back = 6
    do_gran = True

    st.header("Paso 3 - Genera")
    if st.button("Generar textura", disabled=st.session_state.busy):
        # Import local para no romper si el usuario ejecuta solo dsp.py
        from mgi import ConstraintConfig

        st.session_state.busy = True
        try:
            log_event(
                "generation_started",
                filename=filename,
                input_seconds=round(input_seconds, 4),
                output_seconds=float(target),
                format=file_format,
            )

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
                    y_out = make_seamless_loop(y_out, SR, crossfade_ms=150)

            log_event(
                "generation_finished",
                filename=filename,
                input_seconds=round(input_seconds, 4),
                output_seconds=round(len(y_out) / SR, 4),
                format=file_format,
            )

            st.header("Paso 4 - Escucha y descarga")
            st.audio(to_wav_bytes(y_out, SR), format="audio/wav")
            st.download_button(
                "Descargar audio final en WAV (24-bit/48 kHz)",
                to_wav_bytes(y_out, SR),
                file_name="textura.wav",
                mime="audio/wav",
            )
        except Exception as exc:
            log_event(
                "generation_failed",
                filename=filename,
                input_seconds=round(input_seconds, 4),
                output_seconds=float(target),
                format=file_format,
                error_type=type(exc).__name__,
            )
            st.error("No se pudo generar la textura con esta muestra. Prueba con otro audio base o un ajuste mas corto.")
        finally:
            st.session_state.busy = False
else:
    st.info("Sube un audio para comenzar.")
