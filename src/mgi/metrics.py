from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np


EPS = 1e-12


def rms(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=np.float64)
    return float(np.sqrt(np.mean(x * x) + EPS))


def sample_peak(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=np.float64)
    return float(np.max(np.abs(x)) + EPS)


def dbfs(amplitude: float) -> float:
    return 20.0 * math.log10(max(float(amplitude), EPS))


def crest_db(x: np.ndarray) -> float:
    return dbfs(sample_peak(x)) - dbfs(rms(x))


def _entropy_hist(x: np.ndarray, bins: int = 256, clip: float = 0.999) -> float:
    """Entropy of amplitude histogram (domain-agnostic, but meaningful for signals).

    - Uses fixed bin count.
    - Clips to avoid bin blow-up from outliers.
    """
    x = np.asarray(x, dtype=np.float64)
    x = np.clip(x, -clip, clip)
    hist, _ = np.histogram(x, bins=bins, range=(-clip, clip), density=False)
    p = hist.astype(np.float64)
    p = p / (np.sum(p) + EPS)
    p = np.maximum(p, EPS)
    return float(-np.sum(p * np.log(p)))


def _kurtosis_excess(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=np.float64)
    mu = float(np.mean(x))
    v = float(np.var(x) + EPS)
    m4 = float(np.mean((x - mu) ** 4))
    return float(m4 / (v * v) - 3.0)


def phi_moments(x: np.ndarray, *, bins: int = 256) -> np.ndarray:
    """Φ(x) = [μ, σ², κ, H] (momentos + entropía de histograma).

    This is the domain-agnostic structural fingerprint used in the scientific branch.
    """
    x = np.asarray(x, dtype=np.float64)
    mu = float(np.mean(x))
    var = float(np.var(x))
    kappa = _kurtosis_excess(x)
    H = _entropy_hist(x, bins=bins)
    return np.array([mu, var, kappa, H], dtype=np.float64)


def distance_phi(phi_a: np.ndarray, phi_b: np.ndarray, *, weights: np.ndarray | None = None) -> float:
    """d(x,y) = || W(Φ(x) - Φ(y)) ||_2"""
    a = np.asarray(phi_a, dtype=np.float64)
    b = np.asarray(phi_b, dtype=np.float64)
    diff = a - b
    if weights is not None:
        w = np.asarray(weights, dtype=np.float64)
        diff = diff * w
    return float(np.sqrt(np.sum(diff * diff)))
