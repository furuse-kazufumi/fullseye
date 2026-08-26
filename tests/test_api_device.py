"""公開 API(api.run_pipeline / api.apply)の device 引数テスト。

device="cpu"(既定)は従来どおり core を鎖状適用(挙動不変)。device!="cpu" は accel_bridge の
GPU 常駐経路(未対応 op は CPU、torch/GPU 不在なら静かに CPU フォールバック)。GPU の実結果は
CPU-torch と一致することを別途確認済(accel/accel_vol/accel_match/accel_region の各テスト +
loco venv での cuda vs cpu 照合 = region/volume は bit 一致、float 系は float32 epsilon)。
ここでは API 層の配線(既定不変・graceful fallback)を固定する。
"""
import numpy as np
import pytest

import api
import ops


def _img(s=48, seed=0):
    return np.clip(np.random.default_rng(seed).random((s, s)), 0, 1)


def test_run_pipeline_cpu_unchanged():
    """device='cpu' は core を素の鎖状適用したのと一致(既存挙動の回帰)。"""
    img = _img()
    stages = [("gauss_filter", 0.4, 0.4), ("sobel_amp", 0.5, 0.4), ("threshold", 0.3, 0.4)]
    got = api.run_pipeline(img, stages, device="cpu")
    v = api._coerce_input(img, api._resolve("gauss_filter"))
    for name, a, b in stages:
        v = ops.RT[name](v, a, b)
    assert np.array_equal(got, v)


def test_run_pipeline_device_graceful():
    """device='cuda' は落ちず、正しい形の結果を返す(GPU 不在なら CPU にフォールバック)。"""
    img = _img()
    stages = [("median_image", 0.5, 0.4), ("gauss_filter", 0.4, 0.4)]
    out = api.run_pipeline(img, stages, device="cuda")
    assert out.shape == img.shape and np.isfinite(out).all()


def test_apply_cpu_unchanged():
    img = _img()
    got = api.apply(img, "median_image", 0.5, 0.4, device="cpu")
    assert np.array_equal(got, ops.RT["median_image"](img, 0.5, 0.4))


def test_apply_device_graceful():
    img = _img()
    out = api.apply(img, "median_image", 0.5, 0.4, device="cuda")
    assert out.shape == img.shape and np.isfinite(out).all()
