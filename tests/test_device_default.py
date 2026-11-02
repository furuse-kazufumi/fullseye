"""GPU device 選択の公開契約 / Public device-selection contract."""
from __future__ import annotations

import numpy as np
import pytest

import api


def test_auto_resolves_to_cpu_without_cuda(monkeypatch):
    import torch
    monkeypatch.delenv("FULLSEYE_DEVICE", raising=False)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert api.resolve_device("auto") == "cpu"


def test_environment_overrides_argument(monkeypatch):
    monkeypatch.setenv("FULLSEYE_DEVICE", "cpu")
    assert api.resolve_device("cuda") == "cpu"


def test_explicit_cuda_is_not_refused_at_the_entrance(monkeypatch):
    """N117(2026-09-20)の契約: CUDA の無い機械での device="cuda" は入口で拒まず、op ごとに
    説明つきで台帳に記録して CPU で続く。raise 方針ではその説明つきの RuntimeError。"""
    import torch
    monkeypatch.delenv("FULLSEYE_DEVICE", raising=False)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert api.resolve_device("cuda") == "cuda"
    assert api.cuda_available() is False
    api.reset_gpu()
    with pytest.raises(RuntimeError, match="CUDA is not available here"):
        api.apply(np.random.default_rng(1).random((16, 16)), "gaussian", device="cuda", on_error="raise")
    api.reset_gpu()


def test_auto_cpu_is_bit_identical(monkeypatch):
    import torch
    monkeypatch.delenv("FULLSEYE_DEVICE", raising=False)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    image = np.random.default_rng(7).random((31, 29))
    expected = api.apply(image, "gaussian", device="cpu")
    actual = api.apply(image, "gaussian", device="auto")
    assert np.array_equal(actual, expected)


def test_gpu_ledger_count_matches_accelerator_registries():
    """台帳側と実装側を別経路で数え、GPU行の欠落を拒否する。"""
    import accel
    import accel_match
    import accel_typed
    import accel_vol
    from tools import opdocs
    records = opdocs._records()[0]
    ledger_count = sum(bool(row.get("gpu_accel")) for row in records)
    implementation_count = (len(accel.ACCEL) + len(accel_vol.VOL_ACCEL) + len(accel_match.MATCH_ACCEL)
                            + len(accel.NARY_ACCEL) + len(accel_typed.TYPED_ACCEL))
    assert ledger_count == implementation_count


@pytest.mark.gpu
def test_cuda_auto_resolves_on_gpu(monkeypatch):
    import torch
    if not torch.cuda.is_available():
        pytest.skip("CUDA is unavailable")
    monkeypatch.delenv("FULLSEYE_DEVICE", raising=False)
    assert api.resolve_device("auto") == "cuda"
