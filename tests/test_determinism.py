import numpy as np

from dsp import granular_extend


def test_granular_determinism_same_seed():
    sr = 48000
    # Señal de entrada: ruido filtrado corto (simula textura base)
    rng = np.random.default_rng(0)
    y = rng.standard_normal(int(sr * 1.0)).astype(np.float32) * 0.1

    out1 = granular_extend(y, sr, target_duration_s=2.0, grain_ms=200, overlap=0.75, rand_pos=0.1, seed=1234)
    out2 = granular_extend(y, sr, target_duration_s=2.0, grain_ms=200, overlap=0.75, rand_pos=0.1, seed=1234)

    assert out1.shape == out2.shape
    # Exactitud bit-a-bit en numpy (debería ser igual si todo es determinista)
    assert np.array_equal(out1, out2)


def test_granular_determinism_different_seed_changes_output():
    sr = 48000
    rng = np.random.default_rng(0)
    y = rng.standard_normal(int(sr * 1.0)).astype(np.float32) * 0.1

    out1 = granular_extend(y, sr, target_duration_s=2.0, grain_ms=200, overlap=0.75, rand_pos=0.1, seed=1)
    out2 = granular_extend(y, sr, target_duration_s=2.0, grain_ms=200, overlap=0.75, rand_pos=0.1, seed=2)

    assert not np.array_equal(out1, out2)
