# Changelog

## Unreleased
- Added: soporte de **seed** para granular (reproducibilidad)
- Fixed: `make_seamless_loop` selecciona cero-cruces correctamente
- Added: docs `STATE.md`, `ARCHITECTURE.md`, `WORKLOG.md`
- Added: núcleo **MGI** (`src/mgi/`) con \(\Phi\), \(d\), \(C\), \(\Pi_C\) y operador activo (backtracking sobre \(\alpha\)).
- Changed: `evolve_texture` usa MGI activo por defecto (puede desactivarse con `use_active=False`).
- Changed: pipeline DSP evita normalización forzada en modo MGI (\(\Pi_C\) controla energía + headroom).
- Added: bitácora por iteración (CSV) desde la UI.

## 0.1.0 (beta)
- MVP Streamlit: carga audio → filtros → granular → reverb → WAV 24-bit
