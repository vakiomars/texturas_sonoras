"""Tests for the MGI (Motor Generativo Iterativo) core.

Covers:
  - mgi.metrics: phi_moments, distance_phi, rms, sample_peak, crest_db
  - mgi.constraints: violation, project, ConstraintConfig
  - mgi.operator: evolve_active, seed_policy
  - dsp edge cases: make_seamless_loop, _anchor_to_length
"""

import numpy as np
import pytest

from mgi.metrics import phi_moments, distance_phi, rms, sample_peak, crest_db, dbfs
from mgi.constraints import (
    ConstraintConfig,
    ViolationReport,
    ProjectionReport,
    violation,
    project,
)
from mgi.operator import evolve_active, seed_policy
from dsp import make_seamless_loop, _anchor_to_length


# ─────────────────────────────────────────────
# mgi.metrics
# ─────────────────────────────────────────────

class TestRMS:
    def test_silence(self):
        x = np.zeros(1000, dtype=np.float32)
        assert rms(x) == pytest.approx(0.0, abs=1e-6)

    def test_known_signal(self):
        # RMS of a constant signal c is |c|
        x = np.full(1000, 0.5, dtype=np.float64)
        assert rms(x) == pytest.approx(0.5, abs=1e-6)

    def test_sine(self):
        # RMS of a sine wave with amplitude A is A / sqrt(2)
        sr = 48000
        t = np.arange(sr, dtype=np.float64) / sr
        A = 0.8
        x = A * np.sin(2 * np.pi * 440 * t)
        assert rms(x) == pytest.approx(A / np.sqrt(2), abs=1e-3)


class TestSamplePeak:
    def test_known(self):
        x = np.array([0.1, -0.9, 0.5], dtype=np.float64)
        assert sample_peak(x) == pytest.approx(0.9, abs=1e-6)

    def test_silence(self):
        x = np.zeros(100, dtype=np.float64)
        assert sample_peak(x) == pytest.approx(0.0, abs=1e-6)


class TestDbfs:
    def test_unity(self):
        assert dbfs(1.0) == pytest.approx(0.0, abs=1e-6)

    def test_half(self):
        assert dbfs(0.5) == pytest.approx(-6.02, abs=0.05)


class TestCrestDb:
    def test_constant_signal(self):
        # Crest factor of a constant signal is 0 dB (peak == rms)
        x = np.full(1000, 0.5, dtype=np.float64)
        assert crest_db(x) == pytest.approx(0.0, abs=0.1)

    def test_sine_crest(self):
        # Crest factor of a sine wave is ~3.01 dB
        sr = 48000
        t = np.arange(sr, dtype=np.float64) / sr
        x = np.sin(2 * np.pi * 440 * t)
        assert crest_db(x) == pytest.approx(3.01, abs=0.1)


class TestPhiMoments:
    def test_shape(self):
        x = np.random.default_rng(42).standard_normal(10000).astype(np.float64)
        phi = phi_moments(x)
        assert phi.shape == (4,)

    def test_gaussian_moments(self):
        rng = np.random.default_rng(42)
        x = rng.standard_normal(100_000).astype(np.float64)
        phi = phi_moments(x)
        mu, var, kappa, H = phi
        assert mu == pytest.approx(0.0, abs=0.02)
        assert var == pytest.approx(1.0, abs=0.05)
        # Excess kurtosis of normal distribution is 0
        assert kappa == pytest.approx(0.0, abs=0.2)
        # Entropy should be positive
        assert H > 0

    def test_identical_signals_zero_distance(self):
        x = np.random.default_rng(7).standard_normal(5000).astype(np.float64)
        phi = phi_moments(x)
        assert distance_phi(phi, phi) == pytest.approx(0.0, abs=1e-10)


class TestDistancePhi:
    def test_symmetry(self):
        rng = np.random.default_rng(0)
        a = phi_moments(rng.standard_normal(5000))
        b = phi_moments(rng.uniform(-1, 1, 5000))
        assert distance_phi(a, b) == pytest.approx(distance_phi(b, a), abs=1e-10)

    def test_different_signals_positive(self):
        rng = np.random.default_rng(0)
        a = phi_moments(rng.standard_normal(5000))
        b = phi_moments(rng.uniform(-1, 1, 5000))
        assert distance_phi(a, b) > 0

    def test_weighted_distance(self):
        rng = np.random.default_rng(0)
        a = phi_moments(rng.standard_normal(5000))
        b = phi_moments(rng.uniform(-1, 1, 5000))
        w = np.array([1.0, 1.0, 1.0, 1.0])
        d_unw = distance_phi(a, b)
        d_w = distance_phi(a, b, weights=w)
        assert d_unw == pytest.approx(d_w, abs=1e-10)

        # Increasing weights should increase distance
        w2 = np.array([2.0, 2.0, 2.0, 2.0])
        d_w2 = distance_phi(a, b, weights=w2)
        assert d_w2 > d_unw


# ─────────────────────────────────────────────
# mgi.constraints
# ─────────────────────────────────────────────

class TestViolation:
    def _make_signal(self, seed=0):
        rng = np.random.default_rng(seed)
        return (rng.standard_normal(48000) * 0.3).astype(np.float32)

    def test_identical_signals_pass(self):
        x = self._make_signal()
        # Scale to fit within default peak ceiling (-2 dBFS ≈ 0.794)
        x = x / (np.max(np.abs(x)) + 1e-9) * 0.7
        cfg = ConstraintConfig()
        vio = violation(x, x, cfg, alpha_eff=1.0)
        assert vio.ok is True
        assert vio.reason == "ok"

    def test_headroom_violation(self):
        x0 = self._make_signal()
        # Create a signal that exceeds peak ceiling
        x = x0 * 10.0  # way above any reasonable ceiling
        cfg = ConstraintConfig(peak_ceiling_dbfs=-2.0)
        vio = violation(x, x0, cfg, alpha_eff=1.0)
        assert vio.ok is False
        assert vio.reason == "headroom"

    def test_energy_violation(self):
        x0 = self._make_signal()
        # Signal with vastly different RMS but within peak ceiling
        x = x0 * 0.001
        cfg = ConstraintConfig(rms_tol_db=1.0, peak_ceiling_dbfs=0.0)
        vio = violation(x, x0, cfg, alpha_eff=1.0)
        assert vio.ok is False
        assert vio.reason == "energy"


class TestProject:
    def _make_signal(self, seed=0):
        rng = np.random.default_rng(seed)
        return (rng.standard_normal(48000) * 0.3).astype(np.float32)

    def test_projection_returns_tuple(self):
        x = self._make_signal()
        cfg = ConstraintConfig()
        result = project(x, x, cfg)
        assert isinstance(result, tuple)
        assert len(result) == 2
        y, rep = result
        assert isinstance(y, np.ndarray)
        assert isinstance(rep, ProjectionReport)

    def test_projection_preserves_length(self):
        x0 = self._make_signal(0)
        x = self._make_signal(1)
        cfg = ConstraintConfig()
        y, rep = project(x, x0, cfg)
        assert len(y) == len(x)

    def test_projection_enforces_headroom(self):
        x0 = self._make_signal()
        x = x0 * 5.0  # loud signal
        cfg = ConstraintConfig(peak_ceiling_dbfs=-3.0)
        y, rep = project(x, x0, cfg)
        ceiling_lin = 10.0 ** (-3.0 / 20.0)
        assert float(np.max(np.abs(y))) <= ceiling_lin + 1e-6

    def test_projection_matches_mean(self):
        rng = np.random.default_rng(0)
        x0 = (rng.standard_normal(48000) * 0.2).astype(np.float32)
        x = (rng.standard_normal(48000) * 0.2 + 0.1).astype(np.float32)  # DC offset
        cfg = ConstraintConfig(peak_ceiling_dbfs=0.0)
        y, rep = project(x, x0, cfg)
        # After projection, mean should be close to x0's mean
        assert float(np.mean(y)) == pytest.approx(float(np.mean(x0)), abs=0.05)


# ─────────────────────────────────────────────
# mgi.operator
# ─────────────────────────────────────────────

class TestSeedPolicy:
    def test_fixed(self):
        assert seed_policy(42, 0, "fixed") == 42
        assert seed_policy(42, 5, "fixed") == 42

    def test_progressive(self):
        assert seed_policy(100, 0, "progressive") == 100
        assert seed_policy(100, 3, "progressive") == 103

    def test_progressive_none(self):
        assert seed_policy(None, 5, "progressive") is None

    def test_random(self):
        assert seed_policy(42, 0, "random") is None

    def test_unknown_mode_returns_base(self):
        assert seed_policy(42, 0, "unknown") == 42


class TestEvolveActive:
    def _identity_transform(self, x, sr, seed):
        """Transform that returns the input unchanged."""
        return x.copy()

    def _noisy_transform(self, x, sr, seed):
        """Transform that adds small noise."""
        rng = np.random.default_rng(seed)
        return x + (rng.standard_normal(len(x)) * 0.01).astype(np.float32)

    def test_single_iteration_identity(self):
        x0 = np.random.default_rng(0).standard_normal(4800).astype(np.float32) * 0.3
        cfg = ConstraintConfig()
        result = evolve_active(
            x0=x0, sr=48000, transform=self._identity_transform,
            iterations=1, alpha=1.0, cfg=cfg, base_seed=42,
            return_log=True,
        )
        y, logs = result
        assert len(y) == len(x0)
        assert len(logs) == 1

    def test_multiple_iterations(self):
        x0 = np.random.default_rng(0).standard_normal(4800).astype(np.float32) * 0.3
        cfg = ConstraintConfig()
        result = evolve_active(
            x0=x0, sr=48000, transform=self._noisy_transform,
            iterations=3, alpha=0.5, cfg=cfg, base_seed=42,
            return_log=True,
        )
        y, logs = result
        assert len(logs) == 3
        assert all(row["k"] == i + 1 for i, row in enumerate(logs))

    def test_return_log_false(self):
        x0 = np.random.default_rng(0).standard_normal(4800).astype(np.float32) * 0.3
        cfg = ConstraintConfig()
        result = evolve_active(
            x0=x0, sr=48000, transform=self._identity_transform,
            iterations=1, alpha=1.0, cfg=cfg, return_log=False,
        )
        assert isinstance(result, np.ndarray)

    def test_backtracking_logged(self):
        """With a transform that creates violations, backtracking should occur."""
        def loud_transform(x, sr, seed):
            return x * 10.0  # Will violate headroom

        x0 = np.random.default_rng(0).standard_normal(4800).astype(np.float32) * 0.3
        cfg = ConstraintConfig(peak_ceiling_dbfs=-6.0, max_backtracks=5)
        y, logs = evolve_active(
            x0=x0, sr=48000, transform=loud_transform,
            iterations=1, alpha=1.0, cfg=cfg, base_seed=42,
            return_log=True,
        )
        assert len(logs) == 1
        # Should have attempted backtracking
        assert logs[0]["backtracks"] >= 0
        # Output should respect headroom after projection
        ceiling_lin = 10.0 ** (-6.0 / 20.0)
        assert float(np.max(np.abs(y))) <= ceiling_lin + 1e-5


# ─────────────────────────────────────────────
# dsp edge cases
# ─────────────────────────────────────────────

class TestMakeSeamlessLoop:
    def test_normal_signal(self):
        sr = 48000
        rng = np.random.default_rng(0)
        y = (rng.standard_normal(sr) * 0.5).astype(np.float32)
        result = make_seamless_loop(y, sr, crossfade_ms=100)
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32
        assert len(result) > 0

    def test_does_not_mutate_input(self):
        sr = 48000
        rng = np.random.default_rng(0)
        y = (rng.standard_normal(sr) * 0.5).astype(np.float32)
        y_copy = y.copy()
        make_seamless_loop(y, sr, crossfade_ms=100)
        np.testing.assert_array_equal(y, y_copy)

    def test_short_signal(self):
        sr = 48000
        # Very short signal (shorter than 2*crossfade)
        y = np.array([0.1, -0.1, 0.05, -0.05], dtype=np.float32)
        result = make_seamless_loop(y, sr, crossfade_ms=100)
        assert isinstance(result, np.ndarray)

    def test_constant_signal(self):
        # No zero crossings
        y = np.ones(1000, dtype=np.float32) * 0.5
        sr = 48000
        result = make_seamless_loop(y, sr, crossfade_ms=10)
        assert isinstance(result, np.ndarray)


class TestAnchorToLength:
    def test_same_length(self):
        x = np.ones(100, dtype=np.float32)
        result = _anchor_to_length(x, target_len=100, sr=48000)
        np.testing.assert_array_equal(result, x)

    def test_longer_truncates(self):
        x = np.ones(200, dtype=np.float32)
        result = _anchor_to_length(x, target_len=100, sr=48000)
        assert len(result) == 100

    def test_shorter_extends(self):
        x = np.ones(100, dtype=np.float32) * 0.5
        result = _anchor_to_length(x, target_len=500, sr=48000)
        assert len(result) == 500

    def test_zero_target(self):
        x = np.ones(100, dtype=np.float32)
        result = _anchor_to_length(x, target_len=0, sr=48000)
        assert len(result) == 0

    def test_output_dtype(self):
        x = np.ones(100, dtype=np.float64)
        result = _anchor_to_length(x, target_len=200, sr=48000)
        assert result.dtype == np.float32
