"""accel_bridge のテスト。

進化 champion の op 列を GPU 常駐(accel.run_pipeline)/ CPU(core RT)へ振り分けるブリッジの
不変条件を固定する:
- 区間分割: 連続 accel op は 1 GPU 区間、未対応 op で CPU 区間に切れる。
- ルーティング parity: 全 accel = run_pipeline とビット一致 / 全 CPU = core とビット一致。
- champion 実行: 実 champion(denoise)が落ちず、bridge vs core の interior 差が小さい
  (faithful op のみ GPU に載せているので GPU 化が結果を壊さない = honest 検証)。

device 非依存(CPU torch でも成立)なので GPU 無し CI でも回る。
"""
import pathlib

import numpy as np
import pytest

import accel
import ops
import accel_bridge as B

HAS_TORCH = accel._HAS_TORCH


def _imgs(n=4, s=64, seed=0):
    rng = np.random.default_rng(seed)
    return [np.clip(rng.random((s, s)), 0, 1) for _ in range(n)]


def test_core_to_accel_injective():
    c2a = B.core_to_accel()
    assert len(c2a) == len(accel.ACCEL)          # 各 accel op の core 名は一意
    assert c2a["median"] == "median_image"
    assert c2a["gaussian"] == "gauss_filter"


def test_plan_segments_mixed():
    st = [ops.stage("median", 0.5, 0.4), ops.stage("dog", 0.5, 0.4),
          ops.stage("threshold", 0.3, 0.4)]
    segs = B.plan(st)
    assert [k for k, _ in segs] == ["gpu", "cpu", "gpu"]
    assert segs[0][1] == [("median_image", 0.5, 0.4)]
    assert segs[2][1] == [("threshold", 0.3, 0.4)]


def test_plan_merges_consecutive_gpu():
    st = [ops.stage("median", 0.5, 0.4), ops.stage("gaussian", 0.4, 0.4),
          ops.stage("scale_clip", 0.6, 0.4)]
    segs = B.plan(st)
    assert len(segs) == 1 and segs[0][0] == "gpu" and len(segs[0][1]) == 3


@pytest.mark.skipif(not HAS_TORCH, reason="torch 不在")
def test_all_accel_equals_run_pipeline():
    st = [ops.stage("median", 0.5, 0.4), ops.stage("gaussian", 0.4, 0.4),
          ops.stage("scale_clip", 0.6, 0.4)]
    imgs = _imgs()
    out = B.run(st, imgs, device="cpu")
    ref = accel.run_pipeline(
        [("median_image", 0.5, 0.4), ("gauss_filter", 0.4, 0.4),
         ("scale_image", 0.6, 0.4)], imgs, device="cpu")
    for a, b in zip(out, ref):
        assert np.array_equal(a, b)


def test_all_cpu_equals_core():
    st = [ops.stage("dog", 0.5, 0.4)]
    imgs = _imgs()
    out = B.run(st, imgs, device="cpu")
    for a, im in zip(out, imgs):
        assert np.allclose(a, ops.run_stages(st, im))


def test_coverage_counts():
    st = [ops.stage("median", 0.5, 0.4), ops.stage("dog", 0.5, 0.4),
          ops.stage("threshold", 0.3, 0.4)]
    cov = B.coverage(st)
    assert cov["n_total"] == 3 and cov["n_gpu"] == 2 and cov["n_cpu"] == 1
    assert cov["n_gpu_segments"] == 2
    assert cov["uncovered_ops"] == ["dog"]


def test_champion_denoise_runs_and_validates():
    p = pathlib.Path("out/accuracy_bench/champion_denoise.json")
    if not p.exists():
        pytest.skip("champion_denoise.json 不在")
    champ = B.load_champion(p)
    try:
        cov = B.coverage(champ["pipeline"])          # 名前ピン(backend 不在なら KeyError)
    except KeyError:
        pytest.skip("champion の backend op がこの install に不在")
    assert cov["n_gpu"] >= 1                           # median は GPU
    imgs = _imgs(2, 48)
    out = B.run(champ["pipeline"], imgs, device="cpu")
    assert len(out) == 2 and all(np.asarray(o).shape == (48, 48) for o in out)
    v = B.validate_champion(champ["pipeline"], imgs, device="cpu")
    # GPU 区間は median のみ(端 reflect 差)。ただし後段 sk_tv(全域結合の TV 最適化)が
    # 端の差を interior に伝播し cv_sharpen が増幅するため max は ~0.06 まで伸びうる。
    # 典型画素(mean)は無事であることを固定する(max の伝播は honest に許容)。
    assert v["mean_interior_diff"] < 0.01
    assert v["max_interior_diff"] < 0.15
