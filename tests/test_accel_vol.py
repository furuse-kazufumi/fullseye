"""accel_vol(3D volume op の GPU 化)テスト。

進化 champion vol_count / vol_denoise は全段 volume op。ここで 3D 版を core(scipy.ndimage)と
interior<5e-3 で一致させ、accel_bridge がこの 2 champion を単一 GPU 常駐区間へ流すことを固定する。

不変条件:
- parity: 各 vol op が core と interior 一致(gaussian は端からカーネル半径ぶん内側)。
- threshold は core (v>a) とビット一致。
- run_pipeline_vol(常駐)は run_batch_vol 逐次適用とビット一致。
- bridge が vol champion を 100% GPU(vol 区間)に振り分ける。
- **タスク指標保存**(honest 受入基準): vol_count は完全一致、vol_denoise は PSNR がほぼ不変。

device 非依存(CPU torch でも成立)。torch 不在なら skip。
"""
import pathlib

import numpy as np
import pytest

import ops
import accel_vol as V
import accel_bridge as B

HAS = V._HAS_TORCH
skip = pytest.mark.skipif(not HAS, reason="torch 不在")


def _vols(n=2, s=32, seed=0):
    rng = np.random.default_rng(seed)
    return [np.clip(rng.random((s, s, s)), 0, 1) for _ in range(n)]


@skip
@pytest.mark.parametrize("name", list(V.VOL_ACCEL))
def test_parity_interior(name):
    core = V.VOL_ACCEL[name][1]
    a, b = 0.53, 0.49
    vols = _vols()
    m = V._op_margin(name, a)
    got = V.run_batch_vol(name, vols, a, b, "cpu")
    worst = 0.0
    for v, g in zip(vols, got):
        ref = np.clip(ops.RT[core](np.asarray(v, np.float64), a, b), 0, 1)
        worst = max(worst, V._interior_max(ref, np.asarray(g, np.float64), m))
    assert worst < 5e-3, f"{name}: interior {worst:.2e}"


@skip
def test_threshold_bit_exact():
    vols = _vols()
    a = 0.42
    got = V.run_batch_vol("vol_threshold_g", vols, a, 0.0, "cpu")
    for v, g in zip(vols, got):
        assert np.array_equal(np.asarray(g), (np.asarray(v) > a).astype(np.float64))


@skip
def test_run_pipeline_vol_equals_perop():
    vols = _vols()
    steps = [("vol_median_g", 0.5, 0.4), ("vol_erode_g", 0.5, 0.4),
             ("vol_dilate_g", 0.5, 0.4)]
    resident = V.run_pipeline_vol(steps, vols, device="cpu")
    seq = vols
    for name, a, b in steps:
        seq = V.run_batch_vol(name, seq, a, b, "cpu")
    for r, s in zip(resident, seq):
        assert np.array_equal(r, s)


@skip
def test_bridge_routes_vol_champions_100pct():
    for prob in ("vol_denoise", "vol_count"):
        p = pathlib.Path(f"out/accuracy_bench/champion_{prob}.json")
        if not p.exists():
            pytest.skip(f"champion_{prob}.json 不在")
        champ = B.load_champion(p)
        cov = B.coverage(champ["pipeline"])
        assert cov["n_cpu"] == 0 and cov["n_gpu"] == cov["n_total"]
        assert cov["n_gpu_segments"] == 1                 # 単一常駐区間
        assert all(k == "vol" for k, _ in cov["segments"])


@skip
def test_vol_count_metric_exact():
    import problems
    p = pathlib.Path("out/accuracy_bench/champion_vol_count.json")
    if not p.exists():
        pytest.skip("champion 不在")
    champ = B.load_champion(p)
    prob = problems.PROBLEMS["vol_count"]
    cfg = champ["config"]
    stages = ops.decode_by_names(B._STAGE_RE.findall(champ["pipeline"]))
    data = prob.make(cfg.get("n_holdout", 4), cfg["size"], cfg["seed"] + 10_000)
    inp, items = data["input"], data["items"]
    core = prob.score_stages(stages, data)
    bridge = float(np.mean([prob.score_value(B.run(stages, [inp[i]], device="cpu")[0],
                                             items[i]) for i in range(len(inp))]))
    assert abs(bridge - core) < 1e-9                      # count は完全一致


@skip
def test_vol_denoise_metric_preserved():
    import problems
    p = pathlib.Path("out/accuracy_bench/champion_vol_denoise.json")
    if not p.exists():
        pytest.skip("champion 不在")
    champ = B.load_champion(p)
    prob = problems.PROBLEMS["vol_denoise"]
    cfg = champ["config"]
    stages = ops.decode_by_names(B._STAGE_RE.findall(champ["pipeline"]))
    data = prob.make(cfg.get("n_holdout", 4), cfg["size"], cfg["seed"] + 10_000)
    inp, items = data["input"], data["items"]
    core = prob.score_stages(stages, data)
    bridge = float(np.mean([prob.score_value(B.run(stages, [inp[i]], device="cpu")[0],
                                             items[i]) for i in range(len(inp))]))
    assert abs(bridge - core) < 0.5                       # dB PSNR、実測 ~0.06-0.15
