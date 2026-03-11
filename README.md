# Texturas Sonoras

Genera texturas sonoras largas a partir de un audio corto.

Texturas Sonoras te permite subir una muestra breve y obtener una versión extendida y coherente, útil para ambientación, diseño sonoro, capas musicales, prototipos de videojuegos y exploración creativa con material propio.

## Qué hace

La app toma un audio corto como punto de partida y genera una textura más larga que conserva el carácter general del material original. Puedes limpiar el sonido, extenderlo, añadir ambiente, preparar un loop continuo y descargar el resultado en WAV.

## Casos de uso

- Ambientacion
- Ambientación
- Sound design
- Música
- Prototipos para videojuegos
- Exploración con grabaciones propias

## Cómo usarlo

1. Sube tu audio.
2. Ajusta el resultado con los controles de la app.
3. Genera y descarga el WAV final.

## Ejecutar local

### Linux / Mac

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-lite.txt
streamlit run src/app.py
```

Si prefieres un arranque directo:

```bash
./run.sh
```

### Windows

1. Instala Python 3.11 o superior.
2. Haz doble clic en `run_windows.bat`.
3. Abre `http://localhost:8501`.

## Demo / deploy

Para desplegarlo en Streamlit Cloud, la opción recomendada es usar `requirements-lite.txt` para evitar instalaciones más pesadas. Si hace falta, puedes renombrarlo temporalmente a `requirements.txt` para el deploy.

## Nota técnica

Internamente, Texturas Sonoras combina extensión granular, limpieza de señal, ambiente opcional y un motor iterativo de control que ayuda a estabilizar el resultado final.

## Estructura del proyecto

```text
texturas_sonoras/
  src/
    app.py
    dsp.py
    mgi/
  docs/
    STATE.md
    ARCHITECTURE.md
    WORKLOG.md
    OPERATOR.md
  tests/
  scripts/
  requirements-lite.txt
  requirements.txt
  pyproject.toml
```

## Licencia

Copyright © 2025–2026 Andrés Mahecha.

La intención es avanzar hacia una licencia dual en el futuro: una opción open source limitada y otra comercial.
