# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""GPU の無い環境・cuCIM の無い環境と共存できること(GPU 経路は明示指定のときだけ)。

3 つの環境で同じ契約を守る:

* CuPy が無い(``py -3.11`` 素の環境、CI)— ``available()`` は False、``apply(device="cuda")``
  は CPU の ``api.apply`` と同じ値、``run_allowed`` は黙って CPU に落ちず拒否する。
* CuPy はあるが GPU が見えない — 同上(``available()`` を偽にして確かめる)。
* cuCIM が無い / ``GPU_SHADOW_SKIMAGE=0`` — ``skimage`` は本物のまま(GPU 版へ向けない)。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gpu_shadow as G  # noqa: E402


def _an_allowed_registry_op():
    """許可リストにあり、ops.RT で呼べる op を 1 つ(``apply`` が GPU を選びうる条件)。"""
    import importlib
    rt = importlib.import_module("ops").RT
    for name in sorted(G.allowed_ops()):
        if name in rt:
            return name
    pytest.skip("no allow-listed registry op")


@pytest.fixture
def no_device(monkeypatch):
    """CuPy はあっても GPU が見えない環境を作る。"""
    monkeypatch.setattr(G, "available", lambda: False)
    monkeypatch.setattr(G, "_CUCIM", [])
    yield


def test_apply_without_a_device_is_the_cpu_path(no_device):
    import api
    name = _an_allowed_registry_op()
    x = np.linspace(0.0, 1.0, 64 * 64).reshape(64, 64)
    want = api.apply(x.copy(), name, 0.5, 0.5)
    got = G.apply(x.copy(), name, 0.5, 0.5, device="cuda")
    np.testing.assert_array_equal(np.asarray(got), np.asarray(want))


def test_run_allowed_without_a_device_refuses(no_device):
    name = _an_allowed_registry_op()
    with pytest.raises(G.GpuAutoError, match="no CUDA device"):
        G.run_allowed(name, np.zeros((8, 8)), 0.5, 0.5)


def test_skimage_is_not_routed_without_a_device(no_device):
    assert G._skimage_routed() is False
    assert G._twin_of("skimage.filters") is None
    # numpy / scipy の表は GPU の有無で変わらない(実際に使うかは available() が決める)
    assert G._twin_of("scipy.ndimage") == "cupyx.scipy.ndimage"


def test_skimage_routing_can_be_switched_off(monkeypatch):
    monkeypatch.setenv("GPU_SHADOW_SKIMAGE", "0")
    monkeypatch.setattr(G, "_CUCIM", [])
    assert G._cucim_available() is False
    assert G._twin_of("skimage.morphology") is None


def test_skimage_routes_to_cucim_only_when_it_imports(monkeypatch):
    """cuCIM が import できるときだけ ``cucim.skimage.*`` を指す(できなければ None)。"""
    monkeypatch.setattr(G, "_CUCIM", [])
    routed = G._skimage_routed()
    twin = G._twin_of("skimage.filters")
    if routed:
        assert twin == "cucim.skimage.filters"
    else:
        assert twin is None


def test_importing_the_shim_does_not_touch_the_real_modules():
    """shim を読んでも本物の ``sys.modules`` の numpy / skimage は差し替わらない。"""
    import numpy
    assert sys.modules["numpy"] is numpy
    if "skimage" in sys.modules:
        assert sys.modules["skimage"].__name__ == "skimage"
