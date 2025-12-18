# src/app.py
from pathlib import Path

import streamlit as st
import numpy as np
from dsp import (
    to_wav_bytes,
    process_natural_texture,
    make_seamless_loop,
)
from audio_processing import load_audio_uploaded, SUPPORTED_EXTENSIONS

# -------- ajustes UI --------
st.set_page_config(page_title="Texturas Sonoras — Prototipo Elegante", layout="centered")
st.title("🎶 Generador de Texturas Sonoras (Prototipo Elegante)")
st.caption("48 kHz / 24-bit • Granular OLA Hann • Filtros fase-cero • Reverb opcional • Limitador -1 dBTP")

uploaded_main = st.file_uploader(
    "🎵 Sube un archivo (WAV/MP3/OGG/FLAC)",
    type=["wav", "mp3", "ogg", "flac"],
)
with st.expander("📱 Android: si no te deja cargar audio…"):
    uploaded_any = st.file_uploader(
        "Sube el archivo desde el selector completo",
        type=None,
        key="uploader_any",
    )
uploaded = uploaded_main or uploaded_any

# límites seguros de RAM (≈ 10 MB por minuto mono float32 @48 kHz)
MAX_SECONDS = 120  # 2 min para MVP estable
SR = 48000

def _mem_ok(target_s: int) -> bool:
    est_bytes = int(target_s * SR) * 4  # float32
    # aquí podrías leer RAM real; como MVP usamos un umbral fijo (~500 MB)
    return est_bytes < 500 * 1024 * 1024

if uploaded:
    ext = Path(uploaded.name).suffix.lower().lstrip(".")
    if uploaded_any:
        if ext not in {"wav", "mp3", "ogg", "flac"}:
            st.error("Convierte a WAV/MP3 o exporta como WAV desde tu grabadora")
            st.stop()
    else:
        if ext not in SUPPORTED_EXTENSIONS:
            st.error("Convierte a WAV/MP3 o exporta como WAV desde tu grabadora")
            st.stop()

    st.caption(f"Archivo: {uploaded.name} · {uploaded.size} bytes · MIME: {uploaded.type}")

    # Cargar a mono 48 kHz para coherencia con motores de juego
    y, sr = load_audio_uploaded(uploaded, target_sr=SR)
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

    st.subheader("🏞 Reverb ambiental")
    do_rev = st.checkbox("Añadir reverb (sutil)")

    if do_rev:
        room = st.slider("Tamaño de sala", 0.0, 1.0, 0.25)
        wet = st.slider("Mezcla (wet)", 0.0, 0.3, 0.07)
        damp = st.slider("Damping", 0.0, 1.0, 0.2)
    else:
        room = 0.25; wet = 0.07; damp = 0.2

    st.subheader("🔁 Loop")
    loop_option = st.checkbox("🔁 Hacer loop seamless", value=False)
    crossfade_ms = st.slider("Duración crossfade (ms)", 50, 500, 150)
    if st.button("✨ Procesar"):
        with st.status("Procesando…", expanded=False):
            y_out = process_natural_texture(
                y, SR,
                hpf_hz=float(hpf),
                lpf_hz=float(lpf),
                do_granular=bool(do_gran),
                target_s=float(target) if do_gran else float(len(y)/SR),
                grain_ms=float(grain_ms) if do_gran else 300.0,
                overlap=float(overlap) if do_gran else 0.75,
                rand_pos=float(rand_pos) if do_gran else 0.10,
                pitch_rand_semitones=float(pitch_rand) if do_gran else 0.0,
                do_reverb=bool(do_rev),
                room=float(room),
                wet=float(wet),
                damping=float(damp),
                do_limiter=True,
            )
            if loop_option:
                y_out = make_seamless_loop(y_out, SR, crossfade_ms=int(crossfade_ms))
        st.audio(to_wav_bytes(y_out, SR), format="audio/wav")
        st.download_button("⬇️ Descargar WAV (24-bit/48 kHz)", to_wav_bytes(y_out, SR), file_name="textura.wav", mime="audio/wav")
