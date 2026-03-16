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

# -------- i18n --------
TEXTS = {
    "es": {
        "page_title": "Texturas Sonoras",
        "title": "Texturas Sonoras",
        "caption": "Demo publica para validar rapido el resultado a partir de una muestra corta. Esta app no depende de IA generativa.",
        "steps": "1. Sube un audio corto\n2. Ajusta controles simples de la textura\n3. Genera, escucha y descarga una version de demo",
        "step1": "Paso 1 - Sube tu audio",
        "upload_label": "Sube tu audio base",
        "input_too_long": "La demo publica admite muestras base cortas. Sube un audio de hasta {max} segundos.",
        "origin": "Origen: {seconds:.2f} s @ {sr} Hz",
        "step2": "Paso 2 - Ajusta el resultado",
        "slider_hpf": "Recorte de graves",
        "slider_lpf": "Recorte de agudos",
        "duration": "Duracion final",
        "grain": "Detalle de textura",
        "overlap": "Suavidad de union",
        "step3": "Paso 3 - Genera",
        "generate_btn": "Generar textura",
        "processing": "Procesando…",
        "step4": "Paso 4 - Escucha y descarga",
        "download_btn": "Descargar audio final en WAV (24-bit/48 kHz)",
        "error_generate": "No se pudo generar la textura con esta muestra. Prueba con otro audio base o un ajuste mas corto.",
        "empty_state": "Sube un archivo de audio de máximo 45 segundos para comenzar",
    },
    "en": {
        "page_title": "Sound Textures",
        "title": "Sound Textures",
        "caption": "Public demo to quickly validate results from a short sample. This app does not rely on generative AI.",
        "steps": "1. Upload a short audio\n2. Adjust simple texture controls\n3. Generate, listen, and download a demo version",
        "step1": "Step 1 - Upload your audio",
        "upload_label": "Upload your base audio",
        "input_too_long": "The public demo accepts short base samples. Upload audio up to {max} seconds.",
        "origin": "Source: {seconds:.2f} s @ {sr} Hz",
        "step2": "Step 2 - Adjust the result",
        "slider_hpf": "Low cut",
        "slider_lpf": "High cut",
        "duration": "Final duration",
        "grain": "Texture detail",
        "overlap": "Blend smoothness",
        "step3": "Step 3 - Generate",
        "generate_btn": "Generate texture",
        "processing": "Processing…",
        "step4": "Step 4 - Listen and download",
        "download_btn": "Download final audio WAV (24-bit/48 kHz)",
        "error_generate": "Could not generate texture from this sample. Try a different audio or shorter settings.",
        "empty_state": "Upload an audio file of up to 45 seconds to begin",
    },
}

params = st.query_params
lang = params.get("lang", "es")
if lang not in TEXTS:
    lang = "es"
t = TEXTS[lang]

# -------- ajustes UI --------
st.set_page_config(page_title=t["page_title"], layout="centered")
st.title(t["title"])
st.caption(t["caption"])
st.markdown(t["steps"])

st.header(t["step1"])
uploaded = st.file_uploader(t["upload_label"], type=["wav", "mp3", "ogg", "flac", "m4a", "aac", "mp4", "3gp", "wma", "webm"])
audio_source = uploaded

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


if audio_source:
    filename = getattr(audio_source, "name", "recording.wav")
    file_format = filename.rsplit(".", 1)[-1].lower() if "." in filename else "wav"

    y, sr = librosa.load(audio_source, sr=SR, mono=True)
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
        st.error(t["input_too_long"].format(max=MAX_INPUT_SECONDS))
        st.stop()

    st.audio(to_wav_bytes(y, sr), format="audio/wav")
    st.info(t["origin"].format(seconds=input_seconds, sr=sr))

    st.header(t["step2"])
    hpf = st.slider(t["slider_hpf"], 20, 200, 80)
    lpf = st.slider(t["slider_lpf"], 2000, 20000, 15000)
    target = st.number_input(t["duration"], min_value=10, max_value=MAX_OUTPUT_SECONDS, value=60)
    grain_ms = st.slider(t["grain"], 50, 500, 300)
    overlap = st.slider(t["overlap"], 0.10, 0.90, 0.75)

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

    st.header(t["step3"])
    if st.button(t["generate_btn"], disabled=st.session_state.busy):
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

            with st.status(t["processing"], expanded=False):
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

            st.header(t["step4"])
            st.audio(to_wav_bytes(y_out, SR), format="audio/wav")
            st.download_button(
                t["download_btn"],
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
            st.error(t["error_generate"])
        finally:
            st.session_state.busy = False
else:
    st.info(t["empty_state"])
