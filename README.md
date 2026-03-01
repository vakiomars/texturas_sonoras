# Texturas Sonoras

Generador de texturas sonoras (MVP) basado en **granular synthesis (OLA Hann)** con limpieza HPF/LPF, reverb opcional y export a **WAV 24-bit / 48 kHz**.

Incluye un núcleo **MGI (Motor Generativo Iterativo)**: operador iterativo con ancla \(\alpha\), restricciones \(C\), proyección \(\Pi_C\) y **control activo** (backtracking sobre \(\alpha\)) para estabilidad (headroom + energía + huella estadística).

## Qué es (en una línea)
Subes un audio corto (p.ej. 10s) y el motor genera una textura más larga manteniendo coherencia timbral (sin clicks ni cortes perceptibles en pruebas).

---

## Ejecutar local (Linux/Mac)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-lite.txt
streamlit run src/app.py
```

### One-liner
```bash
./run.sh
```

## Ejecutar local (Windows)
1. Instala Python 3.11+
2. Doble clic en `run_windows.bat`
3. Abre `http://localhost:8501`

---

## Deploy en Streamlit Cloud (recomendado)
Para evitar builds pesados, usa `requirements-lite.txt`.
- Opción simple: renombra `requirements-lite.txt` a `requirements.txt` para el deploy.

---

## Estructura
```
texturas_sonoras/
  src/
    app.py              # UI Streamlit
    dsp.py              # DSP (filtros, granular, reverb, export)
    mgi/                # núcleo MGI (Φ, d, C, Π_C, operador activo)
      metrics.py        # Φ(x), d(x,y), RMS, peak, crest
      constraints.py    # C, violation(), project() (Π_C)
      operator.py       # evolve_active() (backtracking + Π_C)
  docs/
    STATE.md            # estado actual + tareas
    ARCHITECTURE.md     # arquitectura actual/objetivo
    WORKLOG.md          # bitácora mínima por sesión
    OPERATOR.md         # definición canónica del operador MGI
  tests/
    test_determinism.py # reproducibilidad granular
    test_gpu_smoke.py   # smoke test CUDA
    test_mgi.py         # tests del núcleo MGI
  scripts/
    loop_test.py        # test manual de loop seamless
  requirements-lite.txt
  requirements.txt
  pyproject.toml
```

---

## Control del proyecto (para no olvidar)
- Lee `docs/STATE.md` (qué funciona, qué falta, qué probar)
- Escribe 5 líneas por sesión en `docs/WORKLOG.md`
- Registra cambios en `CHANGELOG.md`

---

## Licencia
Copyright © 2025–2026 Andrés Mahecha.

(Plan: licencia dual más adelante: open-source limitado + comercial.)
