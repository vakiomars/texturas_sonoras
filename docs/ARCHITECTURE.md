# Arquitectura (actual y objetivo)

## Actual (MVP Streamlit)
- UI: `src/app.py` (Streamlit)
- DSP/Pipeline: `src/dsp.py`
  - Filtros: HPF/LPF Butterworth + `filtfilt`
  - Granular: OLA con Hann + normalización por suma de ventanas
  - Reverb: opcional (Pedalboard)
  - Limiter: pico simple (-1 dB)
- I/O: carga con `librosa.load(..., sr=48000, mono=True)` y export WAV PCM_24.

## Núcleo (MGI) — estructura, no plugin
Se añadió un núcleo agnóstico al dominio bajo `src/mgi/`:

- `src/mgi/metrics.py`: \(\Phi\) (momentos + entropía) y distancia \(d\).
- `src/mgi/constraints.py`: conjunto válido \(C\) y proyección \(\Pi_C\).
- `src/mgi/operator.py`: operador iterativo **activo** (backtracking sobre \(\alpha\) + \(\Pi_C\)).

Audio sigue siendo sandbox (adapter): el transformador \(T\) vive en `src/dsp.py`.

## Problema que estamos resolviendo (visión)
Motor procedural que genera **ambientes dinámicos** controlados por estado del juego (play/pause/escena), evitando:
- bibliotecas enormes
- loops cortos repetitivos
- assets pesados en móviles

## Objetivo v1 (runtime por bloques, no por archivos largos)
**Idea:** generar audio en *chunks* (p.ej. 2–5 s) y mantener un **ring buffer**.

### Componentes
1. `Engine` (core)
   - `init(sample, sr, seed)`
   - `set_params(density, evolution, jitter, ... )`
   - `render(n_samples) -> np.ndarray` (bloque)
   - `reset(seed=None)`

2. `Scheduler` (estado del juego)
   - Estados: `STOP`, `RUN`, `PAUSE`
   - Eventos: `SCENE_CHANGE`, `PLAYER_STOP`, `PLAYER_START`
   - En `PAUSE`: no genera (o genera a cero)

3. `Adapter` (integración)
   - CLI: generar WAV por bloques y escribir a disco (para testing)
   - API: endpoint local (para integrar con Unity/Unreal)
   - Fase futura: VST / Unity native plugin

### Principios
- Nunca concatenar arrays grandes en loops.
- Reproducibilidad: **input + seed + params → output determinístico**.
- Latencia: chunks pequeños.
- Memoria: ring buffer fijo.

## Roadmap técnico
- v0.1: seed en granular + pruebas de encadenamiento y 5–10 min.
- v0.2: modo streaming (render por bloques) + ring buffer.
- v0.3: API local (FastAPI) para integración.
- v1.0: plugin/SDK.
