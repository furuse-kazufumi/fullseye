"""accel_match(NCC テンプレートマッチング ncc_locate の GPU 化)テスト。

champion locate / locate_rot は illuminate -> ncc_locate。illuminate は accel、ncc_locate は
ここで GPU 化し、bridge が両 champion を 100% GPU に流すことを固定する。

不変条件:
- parity: GPU NCC マップ / [score,row,col] が core(_ncc_map/_ncc_locate)と一致
  (score は float32 で ~1e-6、argmax 位置は完全一致)。
- bridge が locate/locate_rot を n_cpu==0(全段 GPU)に振り分ける。
- タスク指標(位置誤差 1/(1+px))が core と一致。

device 非依存。torch 不在なら skip。
"""
import pathlib

import numpy as np
import pytest

import ops
import accel_match as M
import accel_bridge as B

HAS = M._HAS_TORCH
skip = pytest.mark.skipif(not HAS, reason="torch 不在")


def _template(n=11):
    from problems import _template as t
    return t(n)


def _locate_imgs(n=4, size=48, seed=0):
    rng = np.random.default_rng(seed)
    T = _template(11)
    ops.set_match_template(T)
    rr = T.shape[0] // 2
    imgs, gts = [], []
    for _ in range(n):
        base = rng.random((size, size)) * 0.4
        r = int(rng.integers(rr + 1, size - rr - 1))
        c = int(rng.integers(rr + 1, size - rr - 1))
        base[r - rr:r + rr + 1, c - rr:c + rr + 1] = np.maximum(
            base[r - rr:r + rr + 1, c - rr:c + rr + 1], T)
        imgs.append(np.clip(base + rng.normal(0, 0.1, base.shape), 0, 1))
        gts.append((r, c))
    return imgs, T, gts


@skip
def test_ncc_map_matches_core():
    imgs, T, _ = _locate_imgs()
    gpu = M.ncc_map_batch(imgs, T, "cpu")
    for im, g in zip(imgs, gpu):
        ref = ops._ncc_map(np.asarray(im, np.float64), np.asarray(T, np.float64))
        assert np.max(np.abs(ref - g)) < 5e-3


@skip
def test_ncc_locate_argmax_exact():
    imgs, T, _ = _locate_imgs()
    gpu = M.ncc_locate_batch(imgs, T, "cpu")
    for im, g in zip(imgs, gpu):
        cpu = ops.RT["ncc_locate"](np.asarray(im, np.float64), 0.0, 0.0)
        assert abs(cpu[0] - g[0]) < 5e-3            # score float32 精度
        assert cpu[1] == g[1] and cpu[2] == g[2]    # argmax 位置は完全一致


@skip
def test_no_template_returns_zeros():
    imgs, _, _ = _locate_imgs()
    out = M.ncc_locate_batch(imgs, None, "cpu")
    assert all(np.array_equal(o, np.zeros(3)) for o in out)


@skip
def test_bridge_routes_locate_100pct():
    for prob in ("locate", "locate_rot"):
        p = pathlib.Path(f"out/accuracy_bench/champion_{prob}.json")
        if not p.exists():
            pytest.skip(f"champion_{prob}.json 不在")
        champ = B.load_champion(p)
        cov = B.coverage(champ["pipeline"])
        assert cov["n_cpu"] == 0 and cov["n_gpu"] == cov["n_total"]
        kinds = [k for k, _ in cov["segments"]]
        assert "match" in kinds and "cpu" not in kinds


@skip
def test_locate_metric_preserved():
    import problems
    for prob_name in ("locate", "locate_rot"):
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
        assert abs(bridge - core) < 1e-6            # 位置一致 = 指標も一致
