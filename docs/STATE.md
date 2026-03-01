# Estado del proyecto — Texturas Sonoras

**Propósito:** motor de *granular synthesis* guiado por lógica espectral para extender/transformar ambientes (audio procedural).

## Qué está funcionando (confirmado)
- Input: audio (WAV/MP3/OGG/FLAC) → se carga, se convierte a mono 48k.
- Pipeline DSP: HPF/LPF (fase-cero) → granular OLA Hann (opcional) → reverb (opcional) → limiter/normalización.
- Output: WAV 24-bit / 48k, descarga inmediata.
- Calidad percibida (según pruebas del usuario): sin clicks, sin cambios abruptos, variación lenta, timbre coherente.

## Riesgos / dudas abiertas
- **Encadenamiento** (output como nuevo input): ¿se degrada? ¿aparecen artefactos? (pendiente de prueba)
- **Duración larga (5–10 min)**: performance + RAM + calidad (pendiente de prueba)
- **Android file uploader**: en alguna versión/entorno abre selector de imágenes en vez de audio (pendiente de reproducir).

## Decisiones técnicas (hasta hoy)
- SR fijo: 48_000 Hz (alineado con motores de juego).
- Límite MVP: 120 s por estabilidad (RAM/hosting).
- Granular OLA con normalización por suma de ventanas para evitar “pumping”.
- Se añadió soporte de **seed** para reproducibilidad.

## Próximas 3 tareas (en orden)
1. **Prueba de encadenamiento**: 10s → 60s → usar 60s como input → repetir 3 veces. Evaluar degradación.
2. **Prueba de 5 minutos**: mismo input, target=300s, medir tiempo + RAM + calidad.
3. **Bug Android**: probar desde Chrome Android; confirmar si el problema viene de `type=` o de deploy.

## Métricas que importan
- Tiempo de generación por minuto (s/min).
- RAM pico por minuto (MB/min).
- Artefactos (clicks, pumping, repeticiones audibles).
- Reproducibilidad (mismo input + seed = mismo output).
