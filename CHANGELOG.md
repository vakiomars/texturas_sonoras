# Changelog

## Unreleased
### Added
- rama canónica paper-faithful definida y congelada para trabajo futuro
- alcance de product launch week documentado

### Changed
- interfaz de la app reescrita para que el flujo sea más claro y orientado a producto
- opciones avanzadas mejor explicadas en la interfaz
- README reescrito para posicionamiento de lanzamiento

### Fixed
- loop final ahora usa scaling down-only en lugar de normalización forzada
- reverb ya no amplifica el resultado para forzar peak
- se eliminó el doble scaling contradictorio en la pipeline DSP

## 0.1.0-beta
- MVP Streamlit: carga audio → filtros → granular → reverb → WAV 24-bit
