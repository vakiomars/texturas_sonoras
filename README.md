# texturas_sonoras
Generador de texturas sonoras

Este proyecto es un **MVP (Producto Mínimo Viable)** de una aplicación que genera **texturas sonoras** a partir de algoritmos y procesamiento de audio.
El objetivo es ofrecer una herramienta útil para **videojuegos, cine, TV, VR/AR y producción musical**, reduciendo costos de grabación y almacenamiento.

## 🚀 Instalación

Clona este repositorio en tu máquina local:

```bash
git clone https://github.com/vakiomars/texturas_sonoras.git
cd texturas_sonoras

Crea un entorno virtual recomendado

python3 -m venv venv
source venv/bin/activate   # En Linux/Mac
venv\Scripts\activate      # En Windows

Instala las dependencias:

pip install -r requirements.txt

▶️ Uso

Ejecuta la aplicación con:

streamlit run src/app.py
```

## 🎛️ Uso

Recomendado (one-liner):

```bash
./run.sh
```

Manual:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m streamlit run src/app.py
```

## Windows (sin saber código)

1. Descarga el ZIP desde GitHub y extráelo.
2. Instala Python 3.11+ (marca “Add to PATH” durante la instalación).
3. Haz doble clic en `run_windows.bat`.
4. Abre `http://localhost:8501` en tu navegador.

## 📦 Output

- WAV, 48 kHz
- Máximo de salida: 120 s
- Input recomendado: ≤ 20 s (soporta hasta 60 s)
📂 Estructura del Proyecto
texturas_sonoras/
│── requirements.txt      # Dependencias del proyecto
│── README.md             # Este archivo
│── .gitignore            # Archivos ignorados por git
│── tests/
│   └── test_gpu.py       # Script de verificación (GPU/CUDA)
└── src/                  # Código fuente
    │── app.py            # Interfaz principal en Streamlit (entrypoint)
    │── dsp.py            # Procesamiento DSP (filtros, granular, export WAV)
    │── audio_processing.py
    │── config.py
    │── utils.py
    └── __init__.py

⚖️ Licencia

Copyright © 2025 Andrés Mahecha

Este proyecto se distribuye inicialmente bajo Copyright.
En futuras versiones públicas pasará a un modelo de Licencia Dual (Open Source + Comercial).
