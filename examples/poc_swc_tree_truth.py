# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""本物の木で骨格計測を採点する —— NeuroMorpho の SWC を真値に、投影が何を壊すかを測る。

    py -3.11 examples/poc_swc_tree_truth.py

:mod:`poc_vessel_network` は**合成した木**を真値に、細線化と分岐点計数を採点した。
ここでは**実物の木**(NeuroMorpho.Org の SWC = 節点ごとに座標・半径・親 id)を真値にする。
SWC は構造制約を持つ(根は 1 つ / 親 id < 子 id / 節点数 = 辺数 + 1)ので、それ自体が門に
なる。そして SWC は 3 次元だが、画像計測は**投影**の上で走る —— 投影で何が壊れるかを、
同じ木を回して測る。

この PoC が測る唯一の主張:

    **Sholl 交点数(原点中心の球と枝の交点)は 3 次元では構成的に回転不変(整数が 1 つも
    動かない)だが、投影して円で数えると角度で動く。分岐点の数も投影では交差が偽の分岐に
    化け、その数は視線の角度で変わる —— 「木の計測」の精度は木でなく視線が決めている。**

検査する恒等式(下の assert、当てはめた数字は無い):

1. SWC の構造制約: 根(親 −1)がちょうど 1 つ / 親 id < 子 id / 節点数 = 辺数 + 1 / id 一意。
2. 3 次元 Sholl は**回転で整数が 1 つも動かない**(原点からの距離が回転不変だから)。
   12 回転すべてで `np.array_equal`。
3. 分岐点の真値 = 子を 2 つ以上持つ節点の数(SWC から直接)。ケーブル総長 = Σ|子 − 親|。
4. fullseye の op(:func:`treemorph.tree_from_swc` / ``tree_morphometry`` / ``tree_sholl``)が、
   この PoC の自前の計算と**整数まで一致**する(分岐・節点・3-D と投影の Sholl)。PoC は op の
   実例であり、同時に op の第 2 実装になっている。

素材が無ければ(`FULLSEYE_NEUROMORPHO_DIR` に `*.swc` が無ければ)、同じ構造制約を満たす
合成の木で回り、その旨を印字する。NeuroMorpho.Org のデータは CC BY 4.0
(RRID:SCR_002145、Tecuatl, Ljungquist & Ascoli 2024)、リポジトリには同梱しない。
"""
from __future__ import annotations

import glob
import os
import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402
import treemorph as TM  # noqa: E402

N_PIX = 512
N_ROT = 12
SHOLL_STEP = 20.0     # [µm]


# --------------------------------------------------------------------------- #
# SWC                                                                          #
# --------------------------------------------------------------------------- #
def read_swc(path: str):
    rows = []
    for ln in open(path, encoding="utf-8", errors="replace"):
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        f = ln.split()
        rows.append((int(f[0]), int(f[1]), float(f[2]), float(f[3]), float(f[4]), float(f[5]), int(f[6])))
    ids = np.array([r[0] for r in rows]); typ = np.array([r[1] for r in rows])
    xyz = np.array([[r[2], r[3], r[4]] for r in rows]); rad = np.array([r[5] for r in rows])
    par = np.array([r[6] for r in rows])
    return ids, typ, xyz, rad, par


def check_swc(ids, par):
    """★門 1: 構造制約。壊れていれば ValueError(この PoC は壊れた木を採点しない)。"""
    if len(set(ids.tolist())) != ids.size:
        raise ValueError("SWC: id が重複")
    roots = int(np.sum(par == -1))
    if roots != 1:
        raise ValueError("SWC: 根が %d 個" % roots)
    pos = {int(i): k for k, i in enumerate(ids)}
    for i, p in zip(ids, par):
        if p != -1 and not (p < i):
            raise ValueError("SWC: 親 id %d が子 id %d 以上" % (p, i))
        if p != -1 and int(p) not in pos:
            raise ValueError("SWC: 親 %d が無い" % p)
    n_edges = int(np.sum(par != -1))
    assert ids.size == n_edges + 1
    return {"nodes": int(ids.size), "edges": n_edges, "root": roots}


def synthetic_swc(seed=0, n=1500):
    """構造制約を満たす合成の木(3 次元、枝分かれ確率つきのランダムウォーク)。"""
    rng = np.random.default_rng(seed)
    xyz = [np.zeros(3)]; rad = [6.0]; par = [-1]; typ = [1]
    tips = [(0, rng.standard_normal(3))]
    while len(xyz) < n and tips:
        k = int(rng.integers(len(tips)))
        i, d = tips.pop(k)
        d = d + 0.3 * rng.standard_normal(3); d /= np.linalg.norm(d)
        j = len(xyz)
        xyz.append(xyz[i] + 6.0 * d); rad.append(max(0.4, rad[i] * 0.98)); par.append(i); typ.append(3)
        if rng.random() < 0.025 and len(tips) < 40:       # 分岐(先端が増えすぎたら止める)
            e = rng.standard_normal(3); e /= np.linalg.norm(e)
            tips.append((j, d + 0.8 * e)); tips.append((j, d - 0.8 * e))
        else:                                             # 枝は途切れない(節点数で止まる)
            tips.append((j, d))
    ids = np.arange(1, len(xyz) + 1)
    par = np.array([-1 if p == -1 else p + 1 for p in par])
    return ids, np.array(typ), np.array(xyz), np.array(rad), par


# --------------------------------------------------------------------------- #
# 厳密な量(SWC から直接)                                                       #
# --------------------------------------------------------------------------- #
def segments(ids, xyz, par):
    pos = {int(i): k for k, i in enumerate(ids)}
    child = np.array([k for k, p in enumerate(par) if p != -1])
    parent = np.array([pos[int(par[k])] for k in child])
    return parent, child


def n_bifurcations(par, ids):
    cnt = {}
    for p in par:
        if p != -1:
            cnt[int(p)] = cnt.get(int(p), 0) + 1
    return int(sum(1 for v in cnt.values() if v >= 2))


def sholl_3d(xyz, parent, child, radii):
    """原点(根)中心の球 r と枝(親–子の線分)の交点数。線分の両端が球の内外に分かれれば 1 交点。"""
    d = np.linalg.norm(xyz, axis=1)
    dp, dc = d[parent], d[child]
    return np.array([int(np.sum((dp - r) * (dc - r) < 0)) for r in radii])


def sholl_2d(xy, parent, child, radii):
    d = np.linalg.norm(xy, axis=1)
    dp, dc = d[parent], d[child]
    return np.array([int(np.sum((dp - r) * (dc - r) < 0)) for r in radii])


def rotation(rng):
    q = rng.standard_normal(4); q /= np.linalg.norm(q)
    a, b, c, d = q
    return np.array([[a*a+b*b-c*c-d*d, 2*(b*c-a*d), 2*(b*d+a*c)],
                     [2*(b*c+a*d), a*a-b*b+c*c-d*d, 2*(c*d-a*b)],
                     [2*(b*d-a*c), 2*(c*d+a*b), a*a-b*b-c*c+d*d]])


def rot_z(theta):
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


# --------------------------------------------------------------------------- #
# 投影と画像計測                                                                #
# --------------------------------------------------------------------------- #
def render(xyz, rad, parent, child, n_pix=N_PIX):
    """x–y へ正射影し、半径つきの管として塗る(視線 = z)。"""
    xy = xyz[:, :2]
    lo, hi = xy.min(0), xy.max(0)
    scale = (n_pix - 16) / max(float((hi - lo).max()), 1e-9)
    img = np.zeros((n_pix, n_pix), bool)
    yy, xx = np.mgrid[0:n_pix, 0:n_pix]
    for p, c in zip(parent, child):
        a = (xy[p] - lo) * scale + 8; b = (xy[c] - lo) * scale + 8
        r = max(1.0, 0.5 * (rad[p] + rad[c]) * scale)
        n = max(2, int(np.ceil(np.linalg.norm(b - a))))
        for t in np.linspace(0, 1, n):
            q = a + t * (b - a)
            x0, x1 = int(max(0, q[0] - r - 1)), int(min(n_pix, q[0] + r + 2))
            y0, y1 = int(max(0, q[1] - r - 1)), int(min(n_pix, q[1] + r + 2))
            sub = (xx[y0:y1, x0:x1] - q[0]) ** 2 + (yy[y0:y1, x0:x1] - q[1]) ** 2 <= r * r
            img[y0:y1, x0:x1] |= sub
    return img, scale


def to_swc_text(ids, typ, xyz, rad, par) -> str:
    """配列の木を SWC の本文に戻す(合成の木を op に渡すため)。"""
    return "\n".join("%d %d %.9f %.9f %.9f %.6f %d" % (i, t, x[0], x[1], x[2], r, p)
                     for i, t, x, r, p in zip(ids, typ, xyz, rad, par))


def main() -> None:
    d = os.environ.get("FULLSEYE_NEUROMORPHO_DIR", "")
    files = sorted(glob.glob(os.path.join(d, "*.swc"))) if d else []
    if files:
        trees = [(os.path.basename(f), read_swc(f), "実データ") for f in files[:3]]
    else:
        trees = [("合成 %d" % s, synthetic_swc(seed=s), "合成") for s in range(2)]

    rows = []
    for name, (ids, typ, xyz, rad, par), kind in trees:
        info = check_swc(ids, par)
        parent, child = segments(ids, xyz, par)
        xyz0 = xyz - xyz[0]                                   # 根(soma)を原点に
        cable = float(np.sum(np.linalg.norm(xyz0[child] - xyz0[parent], axis=1)))
        n_bif = n_bifurcations(par, ids)
        rmax = float(np.linalg.norm(xyz0, axis=1).max())
        radii = np.arange(SHOLL_STEP, rmax, SHOLL_STEP)
        base = sholl_3d(xyz0, parent, child, radii)

        # ★門 4: fullseye の op が自前の計算と整数まで一致する(op の実例 + 第 2 実装)
        tree = TM.tree_from_swc(to_swc_text(ids, typ, xyz, rad, par))
        m = TM.tree_morphometry(tree)
        assert (m["nodes"], m["edges"], m["bifurcations"]) == (info["nodes"], info["edges"], n_bif), m
        assert abs(m["cable_length"] - cable) < 1e-6 * cable, (m["cable_length"], cable)
        assert np.array_equal(TM.tree_sholl(tree, radii=radii)["crossings"], base)
        assert np.array_equal(TM.tree_sholl(tree, radii=radii, plane="xy")["crossings"],
                              sholl_2d(xyz0[:, :2], parent, child, radii))

        # ★門 2: 3 次元 Sholl は回転で整数が 1 つも動かない
        rng = np.random.default_rng(0)
        for _ in range(N_ROT):
            R = rotation(rng)
            assert np.array_equal(sholl_3d(xyz0 @ R.T, parent, child, radii), base)

        # 投影の Sholl(円)は動く: 同じ 12 回転で最大の差
        proj = np.stack([sholl_2d((xyz0 @ rotation(rng).T)[:, :2], parent, child, radii) for _ in range(N_ROT)])
        proj_spread = int((proj.max(0) - proj.min(0)).max())
        proj_bias = float(np.mean(proj.mean(0) - base))

        # 投影の分岐点: 視線を z 軸まわりに 12 角度振って fs.skeleton_nodes で数える
        junc = []
        for k in range(N_ROT):
            img, scale = render(xyz0 @ rot_z(2 * np.pi * k / N_ROT).T, rad, parent, child)
            fn = fs.skeleton_nodes(img)
            junc.append((fn["n_junctions"], fn["n_endpoints"], fn["skeleton_length"] / scale))
        junc = np.array(junc, float)
        rows.append((name, kind, info, n_bif, cable, base, proj_spread, proj_bias, junc))
        print("%-22s [%s] 節点 %d 辺 %d 分岐(真値) %d ケーブル %.0f µm | 3-D Sholl: %d 半径・%d 回転で不変 |"
              " 投影 Sholl: 角度で最大 %d 交点動く(平均バイアス %+.1f) | 投影の分岐 %d〜%d 個(視線 12 角度)、"
              "骨格長/ケーブル %.2f〜%.2f"
              % (name[:22], kind, info["nodes"], info["edges"], n_bif, cable, len(radii), N_ROT,
                 proj_spread, proj_bias, int(junc[:, 0].min()), int(junc[:, 0].max()),
                 junc[:, 2].min() / cable, junc[:, 2].max() / cable))

    # ---- 図: 先頭の木で、投影 + 骨格 / Sholl 曲線 / 分岐数 vs 角度 ----------------
    name, (ids, typ, xyz, rad, par), kind = trees[0]
    parent, child = segments(ids, xyz, par); xyz0 = xyz - xyz[0]
    img, scale = render(xyz0, rad, parent, child)
    sk = np.asarray(fs.apply(img.astype(float), "skeleton")) > 0.5
    view = np.repeat(img[..., None].astype(float), 3, axis=2)
    view[sk] = (1.0, 0.25, 0.0)
    figs.save_grid("swc_projection", [img.astype(float), view], ["x–y 投影(半径つき)", "細線化を重ねる"],
                   title="%s(%s)—— 分岐の真値 %d 個、投影の分岐 %d〜%d 個"
                         % (name, kind, rows[0][3], int(rows[0][8][:, 0].min()), int(rows[0][8][:, 0].max())), ncols=2)
    rmax = float(np.linalg.norm(xyz0, axis=1).max()); radii = np.arange(SHOLL_STEP, rmax, SHOLL_STEP)
    rng = np.random.default_rng(3)
    series = [("3-D(回転で不変)", radii, rows[0][5].astype(float))]
    for k in range(3):
        series.append(("投影 %d" % (k + 1), radii, sholl_2d((xyz0 @ rotation(rng).T)[:, :2], parent, child, radii).astype(float)))
    figs.save_plot("sholl_3d_vs_projected", series, xlabel="半径 [µm]", ylabel="交点数",
                   title="Sholl: 3 次元は不変、投影は角度で動く",
                   caption="3-D の交点数は %d 回転で整数が 1 つも動かない。投影(円)は角度で最大 %d 交点動き、平均で %+.1f。"
                           % (N_ROT, rows[0][6], rows[0][7]))
    ang = np.arange(N_ROT, dtype=float) * (360.0 / N_ROT)
    figs.save_plot("junctions_vs_view", [("投影の分岐(skeleton_nodes)", ang, rows[0][8][:, 0]),
                                         ("真値(SWC)", np.array([0.0, ang[-1]]), np.array([float(rows[0][3])] * 2))],
                   xlabel="視線の角度 [deg]", ylabel="分岐点の数",
                   title="分岐点の数は木でなく視線が決める",
                   caption="真値 %d 個に対し投影は %d〜%d 個。余分は枝の交差が細線化で分岐に化けたもの。"
                           % (rows[0][3], int(rows[0][8][:, 0].min()), int(rows[0][8][:, 0].max())))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    real = [r for r in rows if r[1] == "実データ"]
    print("\nPASS%s: %d 本の木で op(tree_from_swc / tree_morphometry / tree_sholl)が自前の計算と整数まで一致し、SWC の構造制約と 3-D Sholl の回転不変(%d 回転・整数一致)が通り、投影では Sholl が最大 %d 交点、"
          "分岐点が真値 %s に対し %s 個まで動いた。" % ("" if real else "(合成)", len(rows), N_ROT,
                                                     max(r[6] for r in rows),
                                                     "/".join(str(r[3]) for r in rows),
                                                     "/".join("%d〜%d" % (r[8][:, 0].min(), r[8][:, 0].max()) for r in rows)))


if __name__ == "__main__":
    main()
