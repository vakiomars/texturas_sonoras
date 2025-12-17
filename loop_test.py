import librosa
import soundfile as sf
import numpy as np

def make_seamless_loop(y, sr, crossfade_ms=100):
    """
    Recorta a cero-cruce y aplica crossfade al inicio y fin
    para crear un loop seamless.
    """
    crossfade = int(sr * crossfade_ms / 1000)

    # 1. Buscar cero-cruce cerca del inicio y fin
    zero_in = np.where(np.sign(y[:-1]) != np.sign(y[1:]))[0]
    if len(zero_in) == 0:
        return y  # no hay cruce, devolvemos igual
    start = zero_in[0]

    zero_out = np.where(np.sign(y[:-1]) != np.sign(y[1:]))[0]
    end = zero_out[-1] if len(zero_out) > 0 else len(y)

    # 2. Recortar
    y = y[start:end]

    # 3. Aplicar crossfade
    if len(y) < 2 * crossfade:
        return y  # demasiado corto para crossfade

    fade_in = np.linspace(0, 1, crossfade)
    fade_out = np.linspace(1, 0, crossfade)

    y[:crossfade] = y[:crossfade] * fade_in
    y[-crossfade:] = y[-crossfade:] * fade_out

    # Combinar inicio + fin
    y[:crossfade] += y[-crossfade:]

    # Devolver sin duplicar el final
    y = y[:-crossfade]

    # Normalizar
    y = y / (np.max(np.abs(y)) + 1e-9)
    return y.astype(np.float32)

# ---------------------------
# USO DE PRUEBA
# ---------------------------

# Cargar un audio (ejemplo: grabación de río de freesound)
y, sr = librosa.load("tu_audio.wav", sr=48000, mono=True)

# Crear loop
y_loop = make_seamless_loop(y, sr, crossfade_ms=150)

# Guardar resultado
sf.write("loop_ready.wav", y_loop, sr, format="WAV", subtype="PCM_24")

print("✅ Loop generado: loop_ready.wav (reproduce en bucle para comprobar)")
