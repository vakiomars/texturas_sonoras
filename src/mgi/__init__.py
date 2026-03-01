"""Motor Generativo Iterativo (MGI) — core agnóstico al dominio.

Este paquete implementa:
  - Descriptor estructural Φ(x)
  - Distancia d(x,y)
  - Conjunto válido C (restricciones)
  - Proyección Π_C
  - Operador iterativo activo (backtracking sobre α)

Audio es un *adapter* que provee un transformador T (DSP/granular, etc.).
"""

from .metrics import phi_moments, distance_phi, rms, sample_peak, crest_db
from .constraints import ConstraintConfig, ProjectionReport, ViolationReport
from .operator import evolve_active

__all__ = [
    "phi_moments",
    "distance_phi",
    "rms",
    "sample_peak",
    "crest_db",
    "ConstraintConfig",
    "ProjectionReport",
    "ViolationReport",
    "evolve_active",
]
