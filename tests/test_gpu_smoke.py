import time

import pytest


def test_gpu_smoke_if_available():
    """Smoke test: only runs if CUDA is available.

    This repo is used across environments where CUDA may not be present.
    """
    try:
        import torch
    except Exception as e:
        pytest.skip(f"torch no disponible: {e}")

    if not torch.cuda.is_available():
        pytest.skip("CUDA no disponible en este entorno")

    size = 1024
    a = torch.rand(size, size, device="cuda")
    b = torch.rand(size, size, device="cuda")

    torch.cuda.synchronize()
    start = time.time()
    _ = torch.mm(a, b)
    torch.cuda.synchronize()
    end = time.time()

    assert (end - start) >= 0.0
