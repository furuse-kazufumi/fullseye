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

pytest.importorskip("torch", reason="accel bridge routes into the torch batch path — "
                    "without torch every op is honestly CPU-only and the GPU-plan "
                    "invariants below are vacuous (CI runs without torch)")

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
    # rotate_img = scipy order=3 B-spline(IIR 前置フィルタ)で bit-faithful な
    # GPU 化が不能と判定済みの恒久 CPU op(dog は 2026-08-31 に GPU 化されたので交代)
    st = [ops.stage("median", 0.5, 0.4), ops.stage("rotate_img", 0.5, 0.4),
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
    st = [ops.stage("rotate_img", 0.5, 0.4)]
    imgs = _imgs()
    out = B.run(st, imgs, device="cpu")
    for a, im in zip(out, imgs):
        assert np.allclose(a, ops.run_stages(st, im))


def test_coverage_counts():
    st = [ops.stage("median", 0.5, 0.4), ops.stage("rotate_img", 0.5, 0.4),
          ops.stage("threshold", 0.3, 0.4)]
    cov = B.coverage(st)
    assert cov["n_total"] == 3 and cov["n_gpu"] == 2 and cov["n_cpu"] == 1
    assert cov["n_gpu_segments"] == 2
    assert cov["uncovered_ops"] == ["rotate_img"]


def test_dog_is_gpu_covered():
    """dog は 2026-08-31 の symmetric パディング修正で GPU 化された(回帰ガード)。"""
    cov = B.coverage([ops.stage("dog", 0.5, 0.4)])
    assert cov["n_gpu"] == 1 and cov["uncovered_ops"] == []


def test_champion_denoise_runs():
    p = pathlib.Path("out/accuracy_bench/champion_denoise.json")
    if not p.exists():
        pytest.skip("champion_denoise.json 不在")
    champ = B.load_champion(p)
    try:
        cov = B.coverage(champ["pipeline"])          # 名前ピン(backend 不在なら KeyError)
    except KeyError:
        pytest.skip("champion の backend op がこの install に不在")
    assert cov["n_gpu"] >= 1                           # median は GPU
    out = B.run(champ["pipeline"], _imgs(2, 48), device="cpu")
    assert len(out) == 2 and all(np.asarray(o).shape == (48, 48) for o in out)
    for o in out:
        assert np.isfinite(o).all() and o.min() >= 0.0 and o.max() <= 1.0


def test_champion_denoise_metric_preserved():
    """真の合否 = GPU ルーティングが champion の **タスク指標(PSNR)** を保つか。

    pixel は median の端差 → 後段 sk_tv(全域 TV)伝播で ~0.06 ずれるが、PSNR は保たれる
    はず(実測 ±0.01 dB)。pixel の bit 一致でなく metric 保存が honest な受入基準。
    """
    import problems
    p = pathlib.Path("out/accuracy_bench/champion_denoise.json")
    if not p.exists():
        pytest.skip("champion_denoise.json 不在")
    champ = B.load_champion(p)
    try:
        stages = ops.decode_by_names(B._STAGE_RE.findall(champ["pipeline"]))
    except KeyError:
        pytest.skip("champion の backend op がこの install に不在")
    prob = problems.PROBLEMS["denoise"]
    cfg = champ["config"]
    data = prob.make(cfg.get("n_holdout", 4), cfg["size"], cfg["seed"] + 10_000)
    inp, items = data["input"], data["items"]
    core = prob.score_stages(stages, data)
    bridge = float(np.mean([prob.score_value(B.run(stages, [inp[i]], device="cpu")[0],
                                             items[i]) for i in range(len(inp))]))
    # 4/4 全段 GPU(median+sk_tv+simulate_defocus+cv_sharpen)。sk_tv(Chambolle、per-image
    # freeze で skimage を bit 再現)・simulate_defocus/mean(symmetric)も faithful なので PSNR は不変。
    assert abs(bridge - core) < 0.05                   # dB PSNR、実測 ~0.01
