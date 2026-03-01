from __future__ import annotations

from dataclasses import asdict
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

from .constraints import ConstraintConfig, ProjectionReport, ViolationReport, violation, project
from .metrics import rms, sample_peak, crest_db, phi_moments, distance_phi


def seed_policy(base_seed: Optional[int], k: int, mode: str = "fixed") -> Optional[int]:
    """Seed policy controller (deterministic)."""
    if mode == "fixed":
        return base_seed
    if mode == "progressive":
        return None if base_seed is None else int(base_seed) + int(k)
    if mode == "random":
        return None
    return base_seed


def evolve_active(
    *,
    x0: np.ndarray,
    sr: int,
    transform: Callable[[np.ndarray, int, Optional[int]], np.ndarray],
    iterations: int,
    alpha: float,
    cfg: ConstraintConfig,
    base_seed: Optional[int] = None,
    seed_mode: str = "fixed",
    embed_anchor: Optional[Callable[[np.ndarray, int, int], np.ndarray]] = None,
    return_log: bool = False,
) -> tuple[np.ndarray, List[Dict]] | np.ndarray:
    """MGI operator (active): backtracking on α + Π_C.

    Mathematical form:
      z_{k+1} = T(x_k; θ, s_k)
      x~_{k+1}(α) = (1-α) x0_hat + α z_{k+1}
      α* = backtrack(α) until candidate is within C (or max tries)
      x_{k+1} = Π_C(x~_{k+1}(α*))

    Notes:
      - This function is domain-agnostic; "transform" implements T.
      - Audio sandbox passes a DSP transform.
      - The projection acts on the state that feeds the next iteration.
    """

    x0 = np.asarray(x0, dtype=np.float32)
    xk = x0.copy()

    logs: List[Dict] = []

    for k in range(1, int(iterations) + 1):
        sk = seed_policy(base_seed, k, seed_mode)
        zk = transform(xk, sr, sk)
        zk = np.asarray(zk, dtype=np.float32)

        # Anchor embedding to match transform output domain
        if embed_anchor is not None:
            x0_hat = embed_anchor(x0, len(zk), sr)
        else:
            # default: truncate/pad zeros (not ideal but safe)
            if len(x0) >= len(zk):
                x0_hat = x0[: len(zk)].astype(np.float32)
            else:
                x0_hat = np.pad(x0, (0, len(zk) - len(x0))).astype(np.float32)

        alpha_eff = float(alpha)
        vio: ViolationReport | None = None
        candidate = None
        backtracks = 0

        for attempt in range(int(cfg.max_backtracks) + 1):
            candidate = (1.0 - alpha_eff) * x0_hat + alpha_eff * zk
            vio = violation(candidate, x0_hat, cfg, alpha_eff=alpha_eff)
            if vio.ok:
                break
            # backtrack
            backtracks += 1
            alpha_eff = max(float(cfg.alpha_min), alpha_eff * float(cfg.backtrack_beta))

        if candidate is None or vio is None:
            raise RuntimeError(f"Backtracking failed at iteration {k}: no valid candidate produced")
        x_next, proj = project(candidate, x0_hat, cfg)

        # Diagnostics
        row = {
            "k": k,
            "seed": sk,
            "alpha_req": float(alpha),
            "alpha_eff": float(alpha_eff),
            "backtracks": int(backtracks),
            "violation_ok": bool(vio.ok),
            "violation_reason": str(vio.reason),
            "d_phi": float(vio.d_phi),
            "rms_db": float(vio.rms_db),
            "rms0_db": float(vio.rms0_db),
            "peak_dbfs": float(vio.peak_dbfs),
            "peak_ceiling_dbfs": float(vio.peak_ceiling_dbfs),
            "crest_db": float(crest_db(x_next)),
            "proj_scale_energy": float(proj.scale_energy),
            "proj_scale_headroom": float(proj.scale_headroom),
            "proj_hist_match": bool(proj.hist_match),
            "proj_rms": float(rms(x_next)),
            "proj_peak": float(sample_peak(x_next)),
        }
        logs.append(row)
        xk = x_next

    return (xk, logs) if return_log else xk
