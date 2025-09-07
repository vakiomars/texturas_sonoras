import streamlit as st
import librosa, soundfile as sf
import numpy as np

st.title("Prueba de Generador de Texturas Sonoras")

archivo = st.file_uploader("Sube un audio", type=["wav", "mp3", "flac", "ogg"])
if archivo:
    y, sr = librosa.load(archivo, sr=None)
    st.audio(archivo)

    # ejemplo: duplicar volumen
    y2 = y * 2
    sf.write("salida.wav", y2, sr)
    st.success("Procesado: salida.wav generado")
