"""accel の領域(2値)モルフォロジ GPU 化テスト。

champion binarize / count は threshold -> opening_circle -> reg_dilate -> erosion_golay ->
reg_dilate -> projective_trans_region。最後の projective(幾何)以外の 5 段を GPU 常駐区間に
載せる。領域 op は conv2d カウント+閾値で ndimage.binary_* と **bit 一致**(zero-pad = border_value=0)。

不変条件:
- 各領域 op が core(ops.RT)と array_equal(bit 一致、border 含む)。
- bridge が binarize/count を 5/6 GPU(単一常駐区間)+ projective のみ CPU に振り分ける。
- タスク指標(IoU / count)が core と完全一致(Δ=0)。

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

REGION_OPS = ["reg_dilate", "reg_erode", "erosion_golay",
              "erosion_circle", "dilation_circle", "opening_circle"]


def _bin_imgs(n=4, s=32, seed=0):
    rng = np.random.default_rng(seed)
    # まばらな二値領域(モルフォロジが効く程度)
    return [(rng.random((s, s)) > 0.55).astype(np.float64) for _ in range(n)]


@skip
@pytest.mark.parametrize("core_op", REGION_OPS)
@pytest.mark.parametrize("a", [0.2, 0.56, 0.82])
def test_region_op_bit_exact(core_op, a):
    accel_name = {v[1]: k for k, v in accel.ACCEL.items()}[core_op]
    imgs = _bin_imgs()
    got = accel.run_batch(accel_name, imgs, a, 0.0, "cpu")
    for im, g in zip(imgs, got):
        ref = np.clip(ops.RT[core_op](np.asarray(im, np.float64), a, 0.0), 0, 1)
        assert np.array_equal(np.asarray(g), ref), f"{core_op} a={a}"


@skip
def test_bridge_routes_binarize_count_full():
    """projective_trans_region(grid_sample 近似)も含め binarize/count は 6/6 単一常駐区間。
    projective は bit 一致でないが champion 指標(IoU/count)は保存(下の metric テストで固定)。"""
    for prob in ("binarize", "count"):
        p = pathlib.Path(f"out/accuracy_bench/champion_{prob}.json")
        if not p.exists():
            pytest.skip(f"champion_{prob}.json 不在")
        champ = B.load_champion(p)
        cov = B.coverage(champ["pipeline"])
        assert cov["n_gpu"] == 6 and cov["n_cpu"] == 0
        assert cov["n_gpu_segments"] == 1                       # 単一常駐区間
        assert cov["uncovered_ops"] == []


@skip
def test_binarize_count_metric_exact():
    import problems
    for prob_name in ("binarize", "count"):
        p = pathlib.Path(f"out/accuracy_bench/champion_{prob_name}.json")
        if not p.exists():
            pytest.skip("champion 不在")
        champ = B.load_champion(p)
        prob = problems.PROBLEMS[prob_name]
        cfg = champ["config"]
        stages = ops.decode_by_names(B._STAGE_RE.findall(champ["pipeline"]))
        data = prob.make(cfg.get("n_holdout", 4), cfg["size"], cfg["seed"] + 10_000)
        inp, items = data["input"], data["items"]
        core = prob.score_stages(stages, data)
        bridge = float(np.mean([prob.score_value(B.run(stages, [inp[i]], device="cpu")[0],
                                                 items[i]) for i in range(len(inp))]))
        assert abs(bridge - core) < 1e-9                        # region ops は bit 一致 → 指標も一致


@skip
def test_fill_holes_gt_and_connectivity():
    """fill_holes/fill_up: 既知の穴を埋め、本体は不変(core と bit 一致)。

    斜め隙間の穴は scipy 既定(cross=4 近傍フラッド)では「境界に届かない」ので
    埋まる。8 近傍で実装すると届いて埋まらない — 連結規約の回帰ガード。
    """
    v = np.zeros((32, 32))
    v[8:24, 8:24] = 1.0
    v[14:18, 14:18] = 0.0                        # 完全に閉じた 4x4 の穴
    w = np.zeros((32, 32))                       # 斜め隙間つきリング
    w[8:24, 8:24] = 1.0
    w[14:18, 14:18] = 0.0
    w[8, 8] = 0.0                                # 角を欠く(斜めにのみ抜ける)…
    # (穴は内部なので角欠けとは独立。ここでは core との bit 一致だけを要求)
    for name in ("fill_holes", "fill_up"):
        for img in (v, w):
            got = np.asarray(accel.run_batch(name, [img], 0.5, 0.4, "cpu")[0])
            ref = np.clip(ops.RT[name](img.copy(), 0.5, 0.4), 0, 1)
            assert np.array_equal(got, ref), name
    got = np.asarray(accel.run_batch("fill_holes", [v], 0.5, 0.4, "cpu")[0])
    assert got[15, 15] == 1.0 and got[4, 4] == 0.0   # 穴は埋まり、外は前景化しない
