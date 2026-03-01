"""Manual loop test (not a pytest test).

This file is intentionally *not* part of automated test runs.
Run it manually:
  python scripts/loop_test.py tu_audio.wav
"""

import os
import sys

# Allow running from project root without installing the package
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from dsp import make_seamless_loop


def main():
    import soundfile as sf
    try:
        import librosa
    except Exception as e:
        raise SystemExit(f"librosa no disponible: {e}")

    if len(sys.argv) < 2:
        raise SystemExit("Uso: python scripts/loop_test.py <input.wav>")
    in_path = sys.argv[1]

    y, sr = librosa.load(in_path, sr=48000, mono=True)
    y_loop = make_seamless_loop(y, sr, crossfade_ms=150)
    sf.write("loop_ready.wav", y_loop, sr, format="WAV", subtype="PCM_24")
    print("Loop generado: loop_ready.wav (reproduce en bucle para comprobar)")


if __name__ == "__main__":
    main()
