"""GPU device 選択の公開契約 / Public device-selection contract."""
from __future__ import annotations

import numpy as np
import pytest

import api


def test_auto_resolves_to_cpu_without_cuda(monkeypatch):
    torch = pytest.importorskip("torch")
    monkeypatch.delenv("FULLSEYE_DEVICE", raising=False)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert api.resolve_device("auto") == "cpu"


def test_environment_overrides_argument(monkeypatch):
    monkeypatch.setenv("FULLSEYE_DEVICE", "cpu")
    assert api.resolve_device("cuda") == "cpu"


def test_explicit_cuda_is_not_refused_at_the_entrance(monkeypatch):
    """N117(2026-09-20)の契約: CUDA の無い機械での device="cuda" は入口で拒まず、op ごとに
    説明つきで台帳に記録して CPU で続く。raise 方針ではその説明つきの RuntimeError。"""
    torch = pytest.importorskip("torch")
    monkeypatch.delenv("FULLSEYE_DEVICE", raising=False)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert api.resolve_device("cuda") == "cuda"
    assert api.cuda_available() is False
    api.reset_gpu()
    with pytest.raises(RuntimeError, match="CUDA is not available here"):
        api.apply(np.random.default_rng(1).random((16, 16)), "gaussian", device="cuda", on_error="raise")
    api.reset_gpu()


def test_auto_cpu_is_bit_identical(monkeypatch):
    torch = pytest.importorskip("torch")
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
    torch = pytest.importorskip("torch")
    if not torch.cuda.is_available():
        pytest.skip("CUDA is unavailable")
    monkeypatch.delenv("FULLSEYE_DEVICE", raising=False)
    assert api.resolve_device("auto") == "cuda"


# ---- 0.9.0(ユーザー決定 2026-11-03): 既定は cpu、GPU は明示したときだけ ------------------------ #
# 理由 = 計測の再現性。CUDA のある機械で同じ呼び出しが黙って GPU で走ると値が変わりうるうえ、GPU 経路は
# CI で検査されない。下の 3 本は「CUDA がある」と偽った機械でも既定の呼び出しが GPU に触れないことを見る。

def test_default_device_is_cpu_on_every_entry():
    import inspect
    from fullseye.mcp import server
    for fn in (api.apply, api.run_pipeline, api.resolve_device, server._run_op, server._stage):
        assert inspect.signature(fn).parameters["device"].default == "cpu", fn.__qualname__


def test_default_resolves_to_cpu_even_when_cuda_is_available(monkeypatch):
    monkeypatch.delenv("FULLSEYE_DEVICE", raising=False)
    monkeypatch.setattr(api, "cuda_available", lambda: True)
    assert api.resolve_device() == "cpu"
    # 明示した auto / cuda と環境変数 auto だけが GPU を選ぶ(#239 の resolve_device("auto") は不変)
    assert api.resolve_device("auto") == "cuda"
    assert api.resolve_device("cuda") == "cuda"
    monkeypatch.setenv("FULLSEYE_DEVICE", "auto")
    assert api.resolve_device() == "cuda"


def test_default_apply_never_attempts_the_gpu(monkeypatch):
    """対照つき: 既定の呼び出しは GPU を試みない / ``device="auto"`` は試みる(偽の accel で数える)。"""
    import sys
    import types
    import warnings
    calls = []

    def _run_batch(*a, **k):
        calls.append(1)
        raise RuntimeError("fake GPU kernel")

    fake = types.SimpleNamespace(ACCEL={"gaussian_gpu": (None, "gaussian", None)}, run_batch=_run_batch)
    monkeypatch.setitem(sys.modules, "accel", fake)
    monkeypatch.delenv("FULLSEYE_DEVICE", raising=False)
    monkeypatch.setattr(api, "cuda_available", lambda: True)
    image = np.random.default_rng(3).random((32, 32))
    api.reset_gpu()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            default = api.apply(image, "gaussian")
            assert calls == [], "the default call reached the GPU path"
            assert np.array_equal(default, api.apply(image, "gaussian", device="cpu"))
            # control: an explicit request does try the GPU. ★2026-11-04(統合 GPU): 第 5 便の auto は
            # 実測の損益分岐で 32x32 を CPU に残すので、対照は auto でなく cuda で取る(既定 cpu の検査は不変)。
            api.apply(image, "gaussian", device="cuda")
        assert calls, "control failed: device='cuda' never tried the (fake) GPU, so the check above proves nothing"
    finally:
        api.reset_gpu()
