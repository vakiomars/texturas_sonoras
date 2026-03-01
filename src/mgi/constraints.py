from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import numpy as np

from .metrics import phi_moments, distance_phi, rms, sample_peak, dbfs


EPS = 1e-12


@dataclass
class ViolationReport:
    ok: bool
    reason: str
    alpha_eff: float
    d_phi: float
    phi: np.ndarray
    phi0: np.ndarray
    rms_db: float
    rms0_db: float
    peak_dbfs: float
    peak_ceiling_dbfs: float


@dataclass
class ProjectionReport:
    applied: bool
    scale_energy: float
    scale_headroom: float
    mean_before: float
    mean_after: float
    rms_before: float
    rms_after: float
    peak_before: float
    peak_after: float
    hist_match: bool


@dataclass
class ConstraintConfig:
    """Configura C y Π_C.

    Núcleo (dominio-agnóstico): tolerancias sobre Φ(x).
    Sandbox audio: añade constraints de energía y headroom.
    """

    # Φ(x) = [μ, var, κ, H]
    # Use default_factory to avoid mutable default pitfalls.
    delta_phi: np.ndarray = field(default_factory=lambda: np.array([0.05, 0.05, 2.0, 0.5], dtype=np.float64))
    phi_bins: int = 256
    phi_weights: Optional[np.ndarray] = None

    # Energía: RMS relativo a x0 (en dB)
    rms_tol_db: float = 6.0

    # Headroom (sample-peak). Use a conservative ceiling to indirectly control true-peak.
    peak_ceiling_dbfs: float = -2.0

    # Proyección
    enable_energy_match: bool = True
    enable_hist_match: bool = False  # can be expensive; keep False for now
    hist_bins: int = 512

    # Control activo (α)
    alpha_min: float = 0.05
    backtrack_beta: float = 0.8
    max_backtracks: int = 6


def _histogram_match(x: np.ndarray, ref: np.ndarray, bins: int = 512) -> np.ndarray:
    """Approximate histogram matching using CDF mapping (O(n)).

    Deterministic and reasonably fast for large vectors.
    """
    x = np.asarray(x, dtype=np.float64)
    ref = np.asarray(ref, dtype=np.float64)

    # Use robust range from ref (avoid outliers)
    lo = float(np.quantile(ref, 0.001))
    hi = float(np.quantile(ref, 0.999))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        lo, hi = -1.0, 1.0

    # Histograms
    hx, bx = np.histogram(np.clip(x, lo, hi), bins=bins, range=(lo, hi), density=False)
    hr, br = np.histogram(np.clip(ref, lo, hi), bins=bins, range=(lo, hi), density=False)

    cdf_x = np.cumsum(hx).astype(np.float64)
    cdf_r = np.cumsum(hr).astype(np.float64)
    cdf_x /= (cdf_x[-1] + EPS)
    cdf_r /= (cdf_r[-1] + EPS)

    # Bin centers
    cx = (bx[:-1] + bx[1:]) / 2.0
    cr = (br[:-1] + br[1:]) / 2.0

    # Map x -> u -> y
    # u = CDF_x(x) approximated by interpolating on cx.
    u = np.interp(np.clip(x, lo, hi), cx, cdf_x)
    y = np.interp(u, cdf_r, cr)
    return y.astype(np.float32)


def violation(
    x: np.ndarray,
    x0: np.ndarray,
    cfg: ConstraintConfig,
    *,
    alpha_eff: float,
) -> ViolationReport:
    """Evalúa si x pertenece a C (o está cerca).

    Returns a ViolationReport with the main diagnostics.
    """
    phi0 = phi_moments(x0, bins=cfg.phi_bins)
    phi = phi_moments(x, bins=cfg.phi_bins)
    d = distance_phi(phi, phi0, weights=cfg.phi_weights)

    r = rms(x)
    r0 = rms(x0)
    r_db = dbfs(r)
    r0_db = dbfs(r0)

    p = sample_peak(x)
    p_db = dbfs(p)
    pceil_db = float(cfg.peak_ceiling_dbfs)

    # Component-wise Φ tolerance (more interpretable than a single d)
    dphi = np.abs(phi - phi0)
    phi_ok = bool(np.all(dphi <= cfg.delta_phi))

    rms_ok = bool(abs(r_db - r0_db) <= float(cfg.rms_tol_db))
    peak_ok = bool(p_db <= pceil_db + 1e-9)

    if not peak_ok:
        return ViolationReport(False, "headroom", alpha_eff, d, phi, phi0, r_db, r0_db, p_db, pceil_db)
    if not rms_ok:
        return ViolationReport(False, "energy", alpha_eff, d, phi, phi0, r_db, r0_db, p_db, pceil_db)
    if not phi_ok:
        return ViolationReport(False, "phi", alpha_eff, d, phi, phi0, r_db, r0_db, p_db, pceil_db)
    return ViolationReport(True, "ok", alpha_eff, d, phi, phi0, r_db, r0_db, p_db, pceil_db)


def project(x: np.ndarray, x0: np.ndarray, cfg: ConstraintConfig) -> tuple[np.ndarray, ProjectionReport]:
    """Π_C: devuelve el estado a la región válida.

    Implementación mínima, determinista:
      1) igualar media a x0 (DC)
      2) energy match (RMS) a x0
      3) (opcional) histogram match hacia x0 (para H y κ)
      4) headroom: scale down to peak ceiling

    Returns (x_proj, report)
    """
    x = np.asarray(x, dtype=np.float32)
    x0 = np.asarray(x0, dtype=np.float32)

    mean_before = float(np.mean(x))
    rms_before = float(rms(x))
    peak_before = float(sample_peak(x))

    # 1) mean match
    mu0 = float(np.mean(x0))
    y = (x - mean_before + mu0).astype(np.float32)

    scale_energy = 1.0
    if cfg.enable_energy_match:
        r = float(rms(y))
        r0 = float(rms(x0))
        if r > 0:
            scale_energy = float(r0 / r)
            y = (y * scale_energy).astype(np.float32)

    hist_match = False
    if cfg.enable_hist_match:
        y = _histogram_match(y, x0, bins=int(cfg.hist_bins))
        hist_match = True

    # 4) headroom: down-only
    p = float(sample_peak(y))
    ceiling = float(10.0 ** (cfg.peak_ceiling_dbfs / 20.0))
    scale_headroom = 1.0
    if p > ceiling:
        scale_headroom = float(ceiling / (p + EPS))
        y = (y * scale_headroom).astype(np.float32)

    mean_after = float(np.mean(y))
    rms_after = float(rms(y))
    peak_after = float(sample_peak(y))

    rep = ProjectionReport(
        applied=True,
        scale_energy=scale_energy,
        scale_headroom=scale_headroom,
        mean_before=mean_before,
        mean_after=mean_after,
        rms_before=rms_before,
        rms_after=rms_after,
        peak_before=peak_before,
        peak_after=peak_after,
        hist_match=hist_match,
    )
    return y, rep
