# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""treemorph — SWC の構造の約束・木の数え上げの恒等式・Sholl の回転不変と積分の閉形式。

真値は 3 種類: (1) SWC の約束(根 1 つ・親 id < 子 id・節点 = 辺 + 1)を破った入力は拒む、
(2) 数え上げの恒等式(先端 = 1 + Σ(子 − 1))と手で数えられる木の厳密値、(3) Sholl の
回転不変(整数が 1 つも動かない)と、曲線の下の面積 = Σ|d_子 − d_親| を段の和(第 2 実装)で。
乱数の木だけでは対称性の破れを隠すので、手で数えられる構造の木でも確かめる。
"""
from __future__ import annotations

import glob
import math
import os

import numpy as np
import pytest

import treemorph as T

# 根 1 から x 軸に 3 節(長さ 10 ずつ)、節 3 で 2 本に分かれる。
Y_SWC = """# a Y
1 1 0 0 0 5 -1
2 3 10 0 0 1 1
3 3 20 0 0 1 2
4 3 30 10 0 1 3
5 3 30 -10 0 1 3
"""


def _random_tree(n=400, seed=0):
    rng = np.random.default_rng(seed)
    lines = ["1 1 0 0 0 3 -1"]
    pts = [np.zeros(3)]
    for i in range(2, n + 1):
        p = int(rng.integers(1, i))
        x = pts[p - 1] + rng.normal(0, 5, 3)
        pts.append(x)
        lines.append("%d 3 %.6f %.6f %.6f 1 %d" % (i, x[0], x[1], x[2], p))
    return "\n".join(lines)


def _rotation(seed):
    q, _ = np.linalg.qr(np.random.default_rng(seed).normal(size=(3, 3)))
    return q * np.sign(np.linalg.det(q))


# ---- 構造の約束 ------------------------------------------------------------
def test_y_tree_counts_by_hand():
    t = T.tree_from_swc(Y_SWC)
    m = T.tree_morphometry(t)
    assert (m["nodes"], m["edges"], m["bifurcations"], m["tips"]) == (5, 4, 1, 2)
    assert m["cable_length"] == pytest.approx(20 + 2 * math.sqrt(200))
    assert m["max_path_length"] == pytest.approx(20 + math.sqrt(200))
    assert m["max_radial"] == pytest.approx(math.sqrt(1000))


@pytest.mark.parametrize("bad", [
    "1 1 0 0 0 1 -1\n1 3 1 0 0 1 1",            # id の重複
    "1 1 0 0 0 1 -1\n2 3 1 0 0 1 -1",           # 根が 2 つ
    "1 3 1 0 0 1 2\n2 1 0 0 0 1 -1",            # 親 id >= 子 id
    "1 1 0 0 0 1 -1\n3 3 1 0 0 1 2",            # 親が無い
    "1 1 0 0 0 -1 -1",                          # 負の半径
    "1 1 nan 0 0 1 -1",                         # 非有限
    "1 1 0 0 0 1",                              # 欄が足りない
    "# only a comment\n",                       # 節点ゼロ
])
def test_swc_promises_are_refused_not_repaired(bad):
    with pytest.raises(ValueError):
        T.tree_from_swc(bad)


def test_non_string_and_missing_file_are_refused():
    with pytest.raises(ValueError):
        T.tree_from_swc(123)
    with pytest.raises(ValueError):
        T.tree_from_swc("no_such_neuron_42.swc")


def test_rows_in_any_order_give_the_same_morphometry():
    lines = Y_SWC.strip().splitlines()
    shuffled = "\n".join([lines[0]] + lines[1:][::-1])
    a = T.tree_morphometry(T.tree_from_swc(Y_SWC))
    b = T.tree_morphometry(T.tree_from_swc(shuffled))
    assert a == b


def test_tip_identity_holds_on_random_multifurcating_trees():
    for seed in range(5):
        m = T.tree_morphometry(T.tree_from_swc(_random_tree(300, seed)))
        assert m["nodes"] == m["edges"] + 1 and m["tips"] >= 1


def test_morphometry_refuses_a_non_tree():
    with pytest.raises(ValueError):
        T.tree_morphometry({"xyz": np.zeros((3, 3))})
    with pytest.raises(ValueError):
        T.tree_morphometry({"xyz": np.zeros((2, 3)), "parent_index": np.array([-1, -1]), "root": 0})


# ---- Sholl ------------------------------------------------------------------
def test_y_tree_sholl_by_hand():
    t = T.tree_from_swc(Y_SWC)
    s = T.tree_sholl(t, radii=[5, 15, 25, 31])
    # r=5: 区間 (0,10) の 1 本 / r=15: (10,20) の 1 本 / r=25: 分かれた 2 本 (20, √1000) / r=31: 2 本
    assert s["crossings"].tolist() == [1, 1, 2, 2]


def test_3d_sholl_does_not_move_under_rotation():
    t = T.tree_from_swc(_random_tree(500, 3))
    base = T.tree_sholl(t, n_radii=40)
    for seed in range(12):
        R = _rotation(seed)
        tr = dict(t, xyz=t["xyz"] @ R.T)
        assert np.array_equal(T.tree_sholl(tr, radii=base["radii"])["crossings"], base["crossings"])


def test_projected_sholl_does_move_under_rotation():
    t = T.tree_from_swc(_random_tree(500, 3))
    r = T.tree_sholl(t, n_radii=40)["radii"]
    outs = [T.tree_sholl(dict(t, xyz=t["xyz"] @ _rotation(s).T), radii=r, plane="xy")["crossings"]
            for s in range(6)]
    assert any(not np.array_equal(outs[0], o) for o in outs[1:])


def test_integral_is_the_closed_form_and_a_riemann_sum_converges_to_it():
    t = T.tree_from_swc(_random_tree(400, 1))
    xyz, pidx = t["xyz"], t["parent_index"]
    d = np.linalg.norm(xyz - xyz[t["root"]], axis=1)
    k = np.flatnonzero(pidx >= 0)
    closed = float(np.abs(d[k] - d[pidx[k]]).sum())
    s = T.tree_sholl(t, n_radii=20)
    assert s["integral"] == pytest.approx(closed, rel=1e-12)
    dense = T.tree_sholl(t, n_radii=20000)
    step = dense["radii"][1] - dense["radii"][0]
    riemann = float(dense["crossings"].sum() * step)              # 中点則(殻は幅 step の中点)
    assert riemann == pytest.approx(closed, rel=2e-3)


@pytest.mark.parametrize("kw", [{"plane": "xw"}, {"radii": [3, 2]}, {"radii": [0, 1]},
                                {"radii": [[1, 2]]}, {"radii": [1, np.nan]}, {"n_radii": 0}])
def test_sholl_refuses(kw):
    with pytest.raises(ValueError):
        T.tree_sholl(T.tree_from_swc(Y_SWC), **kw)


def test_real_neuromorpho_files_keep_their_promises():
    # 場所は NEUROMORPHO_DIR、無ければ repo の 2 つ上の data/neuromorpho(手元の絶対パスを書かない)
    base = os.environ.get("NEUROMORPHO_DIR") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "data", "neuromorpho")
    files = sorted(glob.glob(os.path.join(base, "*.swc")))
    if not files:
        pytest.skip("NeuroMorpho SWC files are not bundled")
    for f in files:
        t = T.tree_from_swc(f)
        m = T.tree_morphometry(t)
        s = T.tree_sholl(t, n_radii=30)
        assert m["nodes"] == m["edges"] + 1
        d = np.linalg.norm(t["xyz"] - t["xyz"][t["root"]], axis=1)
        k = np.flatnonzero(t["parent_index"] >= 0)
        assert s["integral"] == pytest.approx(float(np.abs(d[k] - d[t["parent_index"][k]]).sum()), rel=1e-12)



# ---------------------------------------------------------------- 走行長(ERL)
def _path(n=101, step=1.0):
    """x 軸に沿った n 節点の鎖。ケーブル長 (n-1)·step。"""
    lines = ["1 1 0 0 0 1 -1"] + ["%d 3 %.6f 0 0 1 %d" % (k, (k - 1) * step, k - 1) for k in range(2, n + 1)]
    return T.tree_from_swc("\n".join(lines))


def _y_tree():
    """根から 10 節点の幹、そこで 2 本に分かれ各 10 節点(全長 30)。"""
    lines = ["1 1 0 0 0 1 -1"]
    for k in range(2, 12):
        lines.append("%d 3 %d 0 0 1 %d" % (k, k - 1, k - 1))
    for b, dy in ((0, 1), (1, -1)):
        for j in range(10):
            k = 12 + b * 10 + j
            p = 11 if j == 0 else k - 1
            lines.append("%d 3 %d %d 0 1 %d" % (k, 11 + j, dy * (j + 1), p))
    return T.tree_from_swc("\n".join(lines))


def _brute_runs(tree, labels, background=0):
    """第 2 実装: 辺を 1 本ずつ見て、同じラベルの節点どうしを素朴に併合。"""
    pidx = np.asarray(tree["parent_index"])
    xyz = np.asarray(tree["xyz"], float)
    n = len(pidx)
    group = list(range(n))
    for _ in range(n):
        for k in range(n):
            p = pidx[k]
            if p >= 0 and labels[k] == labels[p] and labels[k] != background:
                g = min(group[k], group[p])
                group[k] = group[p] = g
    out = {}
    for k in range(n):
        p = pidx[k]
        if p >= 0 and labels[k] == labels[p] and labels[k] != background:
            out[group[k]] = out.get(group[k], 0.0) + float(np.linalg.norm(xyz[k] - xyz[p]))
    return sorted(out.values())


def test_run_length_of_an_intact_skeleton_is_its_cable():
    t = _y_tree()
    L = T.tree_morphometry(t)["cable_length"]            # 枝の最初の辺は斜め(√2)なので 30 ではない
    r = T.tree_run_length(t, np.full(31, 7))
    assert r["erl"] == pytest.approx(L) and r["runs"] == 1 and r["cut_edges"] == 0


def test_equally_spaced_cuts_on_a_path_give_exactly_the_closed_form():
    """走行 m+1 本がそれぞれ 10 辺、切れ目の辺が m 本: erl = (m+1)·10² / L(L = 11(m+1) − 1)。"""
    for m in (1, 3, 4, 9):
        n = 11 * (m + 1)
        t = _path(n)
        lab = np.arange(n) // 11 + 1
        r = T.tree_run_length(t, lab)
        L = float(n - 1)
        assert r["cut_edges"] == m and r["runs"] == m + 1 and r["cable_length"] == pytest.approx(L)
        assert r["erl"] == pytest.approx((m + 1) * 100.0 / L)
        assert sum(r["run_lengths"]) + r["cut_cable"] == pytest.approx(L)      # 切れ目の辺は誰の走行でもない


def test_erl_bounds_and_conservation_on_random_cuts_of_a_tree():
    t = _y_tree()
    rng = np.random.default_rng(0)
    for _ in range(20):
        lab = rng.integers(1, 5, 31)
        r = T.tree_run_length(t, lab)
        assert sorted(r["run_lengths"].tolist()) == pytest.approx(_brute_runs(t, lab), abs=1e-12)
        L = r["cable_length"]
        assert sum(r["run_lengths"]) + r["cut_cable"] + r["background_cable"] == pytest.approx(L)
        if r["runs"]:
            assert r["erl"] <= r["max_run"] + 1e-12
            kept = sum(r["run_lengths"])
            assert r["erl"] >= kept ** 2 / (L * r["runs"]) - 1e-12        # Cauchy–Schwarz


def test_uniform_random_cuts_match_the_dirichlet_expectation():
    """長さ L の道を m 点で一様に切ると E[Σ l_i²] = 2L²/(m+2)。1 万回の平均で 2 % 以内。"""
    L, m = 1.0, 3
    rng = np.random.default_rng(1)
    t = _path(1001, 0.001)                 # 1000 辺、長さ 1.0
    acc = 0.0
    trials = 4000
    for _ in range(trials):
        cuts = np.sort(rng.integers(1, 1000, m))       # 切る辺(節点 k と k-1 の間)
        lab = np.searchsorted(cuts, np.arange(1001), side="right") + 1
        acc += T.tree_run_length(t, lab)["erl"]
    assert acc / trials == pytest.approx(2 * L / (m + 2), rel=0.03)


def test_background_and_merged_labels_are_lost_cable():
    t = _path(11)                          # 長さ 10
    lab = np.ones(11, int)
    lab[5] = 0                             # 1 節点が背景: 両側の辺 2 本が失われる
    r = T.tree_run_length(t, lab)
    assert r["background_edges"] == 2 and r["background_cable"] == pytest.approx(2.0)
    assert sorted(r["run_lengths"].tolist()) == [4.0, 4.0] and r["erl"] == pytest.approx(32 / 10)
    r2 = T.tree_run_length(t, np.ones(11, int), zero_labels=[1])
    assert r2["erl"] == 0.0 and r2["merged_runs"] == 1 and r2["runs"] == 1


def test_run_length_is_invariant_to_relabelling():
    t = _y_tree()
    lab = np.random.default_rng(2).integers(1, 4, 31)
    perm = np.array([0, 30, 10, 20])
    a, b = T.tree_run_length(t, lab), T.tree_run_length(t, perm[lab])
    assert a["erl"] == pytest.approx(b["erl"]) and sorted(a["run_lengths"]) == pytest.approx(sorted(b["run_lengths"]))


@pytest.mark.parametrize("bad", [np.ones(30, int), np.full(31, 1.5), "labels", np.full(31, np.nan)])
def test_run_length_refuses_bad_labels(bad):
    with pytest.raises(ValueError):
        T.tree_run_length(_y_tree(), bad)
