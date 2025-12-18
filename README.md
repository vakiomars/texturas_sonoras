# Texturas Sonoras — Generador de texturas (MVP)

Aplicación en **Streamlit** para transformar un audio corto en una **textura sonora** usable (ambient/loop), pensada para prototipado rápido en videojuegos, cine/TV y música.

## Quick Start (recomendado: `requirements-lite.txt`)

**Linux/macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lite.txt
python -m streamlit run src/app.py
```

**Windows (sin saber código)**

1. Descarga el ZIP desde GitHub y extráelo.
2. Instala Python 3.11+ (marca “Add to PATH”).
3. Doble clic en `run_windows.bat`.
4. Abre `http://localhost:8501`.

### Linux/macOS (one-liner)

```bash
./run.sh
```

(crea/usa `.venv` e instala `requirements-lite.txt`).

### Stack completo (opcional)

```bash
pip install -r requirements.txt
```

## ¿Por qué hay varios `requirements`?

- `requirements-lite.txt`: **camino recomendado** (más liviano) para correr la app en CPU.
- `requirements.txt`: entorno **completo** (más pesado) usado para prototipos, notebooks y dependencias extra.
- `requirements-gpu.txt`: extras **opcionales** para pruebas/experimentos en GPU (ver `tests/test_gpu.py`).

## Qué demuestra este proyecto (Blended Pareto)

Este repo aplica un enfoque **Pareto-first**: prioriza el 20% de decisiones que produce el 80% del valor.

- **Output usable** antes que features “bonitas”: exporta audio listo para probar en un motor o DAW.
- **Producto + DSP** (“blended”): UX simple (subir → ajustar → exportar) con DSP práctico (filtros, granular, loop).
- **Iteración rápida**: scripts y estructura para experimentar sin inflar el repo.

## Output y límites (confirmado por el código)

- Exporta **WAV** (PCM 24-bit) y procesa a **48 kHz** en **mono** (`src/app.py`).
- La UI permite generar hasta **120 s** de duración objetivo para la extensión granular (`MAX_SECONDS=120`).
- Tipos de entrada: WAV/MP3/OGG/FLAC (vía `librosa`).

## Estructura del proyecto (layout real)

```text
.
├── run.sh
├── run_windows.bat
├── requirements-lite.txt
├── requirements.txt
├── requirements-gpu.txt
├── loop_test.py
├── data/
│   ├── raw/
│   └── processed/
├── outputs/
├── src/
│   ├── app.py
│   ├── dsp.py
│   ├── audio_processing.py
│   ├── config.py
│   ├── utils.py
│   └── utils/
│       ├── __init__.py
│       └── audio_processing.py
└── tests/
    └── test_gpu.py
```

## Roadmap (Pareto-first)

- Presets “1-click” (ambiente, ruido, textura mecánica) + export por lote.
- Mejores loops (detección de cruces + métricas de clic) y preescucha A/B.
- Pruebas rápidas con `pytest` para DSP crítico (deterministas y sin assets pesados).
- Empaquetado simple (script/CLI) para integrar en pipelines de audio.
