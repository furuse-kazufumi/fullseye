"""accel の平滑系 GPU op(sk_tv=Chambolle TV / simulate_defocus=box mean)テスト。

denoise champion = median -> sk_tv -> simulate_defocus -> cv_sharpen。median/cv_sharpen は既存、
ここで sk_tv(計算重・GPU 向き)と simulate_defocus を加え denoise を **4/4=100% GPU 常駐**にする。

不変条件:
- simulate_defocus は uniform_filter(_k(a))= box mean なので interior faithful(<5e-3)。
- sk_tv は skimage denoise_tv_chambolle を忠実移植 → interior <5e-3。
- bridge が denoise を 4/4 単一常駐区間に振り分ける。

device 非依存。torch 不在なら skip。
"""
import pathlib

import numpy as np
import pytest

import accel
import ops
import accel_bridge as B

HAS = accel._HAS_TORCH
skip = pytest.mark.skipif(not HAS, reason="torch 不在")


def _imgs(n=3, s=48, seed=0):
    rng = np.random.default_rng(seed)
    return [np.clip(rng.random((s, s)), 0, 1) for _ in range(n)]


@skip
@pytest.mark.parametrize("a", [0.3, 0.85])
def test_simulate_defocus_faithful(a):
    imgs = _imgs()
    got = accel.run_batch("simulate_defocus", imgs, a, 0.0, "cpu")
    for im, g in zip(imgs, got):
        ref = np.clip(ops.RT["simulate_defocus"](np.asarray(im, np.float64), a, 0.0), 0, 1)
        assert np.max(np.abs(ref[3:-3, 3:-3] - np.asarray(g)[3:-3, 3:-3])) < 5e-3


@skip
@pytest.mark.parametrize("a", [0.38, 0.6])
def test_sk_tv_faithful(a):
    """Chambolle TV の GPU 移植が skimage と interior 一致(<5e-3)。"""
    imgs = _imgs()
    got = accel.run_batch("sk_tv", imgs, a, 0.0, "cpu")
    for im, g in zip(imgs, got):
        ref = np.clip(ops.RT["sk_tv"](np.asarray(im, np.float64), a, 0.0), 0, 1)
        assert np.max(np.abs(ref[3:-3, 3:-3] - np.asarray(g)[3:-3, 3:-3])) < 5e-3


@skip
def test_bridge_routes_denoise_full():
    p = pathlib.Path("out/accuracy_bench/champion_denoise.json")
    if not p.exists():
        pytest.skip("champion_denoise.json 不在")
    champ = B.load_champion(p)
    try:
        cov = B.coverage(champ["pipeline"])
    except KeyError:
        pytest.skip("backend op 不在")
    assert cov["n_gpu"] == 4 and cov["n_cpu"] == 0
    assert cov["n_gpu_segments"] == 1                       # median+sk_tv+defocus+sharpen が単一常駐
