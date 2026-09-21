# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 枝の縄張り ―― 骨格が「どこ」かだけでなく「どの枝が近いか」を体積に配ると、枝ごとの体積と半径が測れる

EM 連続断面から切り出したニューロン(樹状突起)は、骨格化すれば**枝のグラフ**になる(``skeletonize_vol`` →
``skeleton_graph3d``)。しかし形態計測が要るのはグラフの上の数字だけではない —— **枝ごとの体積・表面・半径**
(ケーブル理論の区画パラメータ)は、体積の各 voxel が**どの枝に属するか**を決めて初めて数えられる。距離変換は
「最近の骨格まで何 voxel か」(値)を返すが、「**どの**骨格 voxel が最近か」(向き)を捨てるので、そのままでは
枝の縄張りは引けない。この PoC は 2026-09-21 に足した 3 op のうち 2 つでその穴を埋める:

* ``vol_nearest_label``: 枝 id を載せた骨格を seed に、空間の全 voxel へ最近の枝 id を配る(ボロノイ分割)。
  分割片(``vol_rle_components`` で片ごとに持った領域)の中に切り出せば、枝の縄張り = 枝ごとの体積。
* ``vol_nearest_seed_vector``: 表面の各 voxel から最近の骨格への変位。その長さが**その場所の半径**。

**主張は 1 つだけ**: 真値の枝ラベルを持つ合成の樹状突起(半径の違う 5 本の枝 + 分断された 1 片 + ごみ 6 個)で、
枝の縄張り(voxel 単位の一致率)と枝ごとの体積・半径が、値だけの古典(接合点の周りを球で切って連結成分に分ける)
より真値に近い。古典は球の半径をどう選んでも「分けられない」か「体積を捨てる」のどちらかになる —— 向きが要る証拠。

図:
1. ``territories``: z 方向の投影 —— 真値の枝ラベル | 骨格 | ボロノイの縄張り(vol_nearest_label)| 接合点を球で
   切った古典(灰 = 捨てた体積)。
2. ``territory_turning``: 表面 voxel を枝の色で塗って回す GIF(灰 = ``vol_rle_components`` で落としたごみ)。
3. ``radius_recovery``: 枝ごとの真の半径 vs 測った半径(表面→骨格の変位長 / 骨格上の距離変換)。
4. ``branch_numbers``: 枝ごとの真値と測定(体積・半径)、古典との比較表。

データ: 合成(真値が要るため)。走らせ方: ``py -3.11 examples/poc_em_branch_territory.py``
(図は ``out/figures/poc_em_branch_territory/``)。
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import fullseye as fs  # noqa: E402
import examplefig as figs  # noqa: E402
import volops  # noqa: E402
import volregion  # noqa: E402
import medial  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
PALETTE = np.array([(0.95, 0.35, 0.30), (0.30, 0.65, 0.95), (0.35, 0.85, 0.40), (0.95, 0.75, 0.20),
                    (0.80, 0.40, 0.90), (0.20, 0.85, 0.85), (0.95, 0.55, 0.65), (0.60, 0.60, 0.95)])
GREY = (0.45, 0.45, 0.45)

# 真値の樹状突起: 枝 = (始点 (z,y,x), 終点 (z,y,x), 半径)。1〜5 が 1 本の木、6 は分断された片(別の連結成分)
BRANCHES = [
    ((28, 44, 10), (28, 44, 100), 4.0),      # 1 幹
    ((28, 44, 40), (10, 18, 62), 2.5),       # 2 枝 A(幹の x=40 から)
    ((28, 44, 40), (46, 20, 28), 2.0),       # 3 枝 C(同じ接合点から反対側へ)
    ((28, 44, 70), (46, 74, 96), 3.0),       # 4 枝 B(幹の x=70 から)
    ((19, 31, 51), (4, 48, 80), 1.5),        # 5 枝 A の途中から出る細い枝
    ((12, 72, 15), (14, 82, 45), 2.0),       # 6 分断された片(木に触れない)
]
SHAPE = (56, 88, 112)
MIN_VOLUME = 300                              # これ未満の連結成分はごみとして落とす(voxel)


# --------------------------------------------------------------------------- #
# 合成データ                                                                    #
# --------------------------------------------------------------------------- #
def _segment_distance(pts, a, b):
    """点群 pts (N,3) から線分 ab までの距離。"""
    a, b = np.asarray(a, float), np.asarray(b, float)
    ab = b - a
    t = np.clip(((pts - a) @ ab) / float(ab @ ab), 0.0, 1.0)
    return np.linalg.norm(pts - (a + t[:, None] * ab), axis=1)


def synthetic_dendrite(seed: int = 0):
    """真値つきの合成: 管の和(前景)と、前景 voxel ごとの「最近の枝の軸」のラベル、ごみの塊。"""
    rng = np.random.default_rng(seed)
    zz, yy, xx = np.indices(SHAPE)
    pts = np.column_stack([zz.ravel(), yy.ravel(), xx.ravel()]).astype(float)
    dist = np.stack([_segment_distance(pts, a, b) for a, b, _ in BRANCHES], 1)            # (N, K)
    radii = np.array([r for _, _, r in BRANCHES])
    inside = (dist <= radii[None, :]).any(1)
    truth = np.where(inside, dist.argmin(1) + 1, 0).reshape(SHAPE).astype(np.int64)         # 最近の軸 = 縄張りの真値
    vol = (truth > 0).astype(np.float64)
    # ごみ: 木にも片にも触れない小さな塊(半径 1.2〜2.0 → 体積 < MIN_VOLUME)
    dmin = dist.min(1).reshape(SHAPE)
    debris = np.zeros(SHAPE, bool)
    n_debris = 0
    while n_debris < 6:
        c = rng.integers([4, 4, 4], [SHAPE[0] - 4, SHAPE[1] - 4, SHAPE[2] - 4])
        r = rng.uniform(1.2, 2.0)
        if dmin[tuple(c)] < r + 6:
            continue
        ball = ((zz - c[0]) ** 2 + (yy - c[1]) ** 2 + (xx - c[2]) ** 2) <= r * r
        if (ball & (debris | (vol > 0))).any():
            continue
        debris |= ball
        n_debris += 1
    vol[debris] = 1.0
    return vol, truth, debris


# --------------------------------------------------------------------------- #
# 測る                                                                          #
# --------------------------------------------------------------------------- #
def keep_large_components(vol, min_volume):
    """vol_rle_components で片ごとに持ち、体積で選ぶ(密なラベル体積を作らない)。"""
    regions = volregion.vol_rle_components(vol, connectivity=26)
    volumes = [volregion.vol_rle_volume(r) for r in regions]
    kept = [r for r, v in zip(regions, volumes) if v >= min_volume]
    mask = np.zeros(vol.shape, bool)
    for r in kept:
        mask |= volregion.vol_rle_decode(r) > 0.5
    return mask, sorted(volumes, reverse=True), len(kept)


def match_labels(pred, truth):
    """予測ラベル → 真値ラベル(重なりの多数決)。返り値 (対応表, 対応後の予測)。"""
    ids = [int(i) for i in np.unique(pred) if i != 0]
    mapping = {}
    for i in ids:
        t = truth[pred == i]
        t = t[t > 0]
        mapping[i] = int(np.bincount(t).argmax()) if len(t) else 0
    out = np.zeros_like(pred)
    for i, t in mapping.items():
        out[pred == i] = t
    return mapping, out


def junction_cut(mask, skel, branches, radius):
    """値だけの古典: 接合点の周りを半径 radius の球で削り、残りを連結成分に分ける。削った分は未割当(0)。"""
    junction = skel & ~branches
    if radius > 0:
        rr = int(np.ceil(radius))
        z, y, x = np.mgrid[-rr:rr + 1, -rr:rr + 1, -rr:rr + 1]
        ball = (z * z + y * y + x * x) <= radius * radius
        cut = mask & ~ndi.binary_dilation(junction, structure=ball)
    else:
        cut = mask.copy()
    labels, _n = volops.vol_label(cut.astype(np.float64), 26)
    return labels.astype(np.int64)


def surface(mask):
    return mask & ~ndi.binary_erosion(mask, structure=ndi.generate_binary_structure(3, 1), border_value=0)


# --------------------------------------------------------------------------- #
# 図                                                                            #
# --------------------------------------------------------------------------- #
def project_labels(lab, over=None, base=None):
    """z 方向の投影: 各 (y, x) で最初に当たるラベルの色。over(bool)は白で重ねる。
    base(bool)を渡すと、その前景で最初に当たる voxel を見る(ラベル 0 = 灰 = 未割当)。"""
    fg = (lab > 0) if base is None else base
    has = fg.any(0)
    first = np.argmax(fg, axis=0)
    yy, xx = np.indices(lab.shape[1:])
    top = np.where(has, lab[first, yy, xx], 0)
    rgb = np.zeros(lab.shape[1:] + (3,))
    for i in np.unique(top):
        if i > 0:
            rgb[top == i] = PALETTE[(i - 1) % len(PALETTE)]
    rgb[has & (top == 0)] = GREY
    if over is not None:
        rgb[over.any(0)] = 1.0
    return rgb


def turning_gif(mask, assigned, debris, size):
    """表面 voxel を縄張りの色で塗り、ごみを灰で敷いて回す。"""
    zs, ys, xs = np.nonzero(surface(mask))
    P = np.column_stack([xs, ys, zs]).astype(float)
    C = PALETTE[(assigned[zs, ys, xs] - 1) % len(PALETTE)]
    C[assigned[zs, ys, xs] == 0] = GREY
    dz, dy, dx = np.nonzero(debris)
    bg = np.column_stack([dx, dy, dz]).astype(float)
    X = np.ones((1, len(P)))
    return fs.ledger.points_activity_video(P, X, colors=C, size=size, aspect=1.0, pitch=20.0, substeps=48,
                                           point_px=2, gain=3.0, background=bg)


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.time()
    vol, truth, debris = synthetic_dendrite()
    radii = {k + 1: r for k, (_, _, r) in enumerate(BRANCHES)}
    print("DATA: synthetic dendrite %s, %d branches (radius %s), 1 detached piece, 6 debris blobs" % (
        SHAPE, len(BRANCHES) - 1, ", ".join("%.1f" % radii[k] for k in range(1, len(BRANCHES)))))

    # 1. 片ごとの領域(RLE)→ 体積で選ぶ
    mask, volumes, n_kept = keep_large_components(vol, MIN_VOLUME)
    print("vol_rle_components: %d components, volumes %s -> kept %d (>= %d voxels), dropped %d debris" % (
        len(volumes), volumes[:2] + ["..."] + volumes[-2:], n_kept, MIN_VOLUME, len(volumes) - n_kept))
    assert n_kept == 2 and len(volumes) - n_kept == 6
    assert (mask == (truth > 0)).all()                                    # 残したのは木と片だけ、ごみは全部落ちた

    # 2. 骨格 → 枝ラベル → グラフ
    skel = medial.skeletonize_vol(mask)
    dt = volops.vol_distance_transform(mask.astype(np.float64))
    graph = medial.skeleton_graph3d(skel, distance=dt, min_branch_len=6.0)
    branches = medial.skeleton_branches3d(skel, min_length=4)
    blab, n_branches = volops.vol_label(branches.astype(np.float64), 26)
    blab = blab.astype(np.int64)
    print("skeleton: %d voxels; graph %d nodes / %d edges / %d components / %d cycles (%d hairs pruned); %d branch labels" % (
        int(skel.sum()), graph["n_nodes"], graph["n_edges"], graph["n_components"], graph["n_cycles"],
        graph["n_pruned_branches"], n_branches))
    assert graph["n_components"] == 2 and graph["n_cycles"] == 0

    # 3. 縄張り: 枝 id を最近の骨格 voxel から空間へ配り、片の中に切る
    territory = volops.vol_nearest_label(blab)
    territory[~mask] = 0
    mapping, assigned = match_labels(territory, truth)
    acc = float((assigned[mask] == truth[mask]).mean())
    print("territory (vol_nearest_label): voxel agreement with the true nearest axis %.3f; %d skeleton branches (a trunk is cut at every junction) map onto %d true branches" % (
        acc, len(mapping), len(set(mapping.values()))))

    # 4. 枝ごとの体積と半径(向き = 表面→骨格の変位、値 = 骨格上の距離変換)
    vec = volops.vol_nearest_seed_vector(skel.astype(np.float64))
    rlen = np.linalg.norm(vec, axis=0)
    surf = surface(mask)
    rows, r_true, r_vec, r_edt, v_err = [], [], [], [], []
    for k in range(1, len(BRANCHES) + 1):
        tv = int((truth == k).sum())
        av = int((assigned == k).sum())
        # 表面 voxel の中心は境界の半 voxel 内側にあるので、変位長 + 0.5 が半径(離散化の既知の偏り、表にも書く)
        rv = float(rlen[surf & (assigned == k)].mean()) + 0.5 if (surf & (assigned == k)).any() else float("nan")
        on_skel = skel & (assigned == k)
        re = float(dt[on_skel].mean()) if on_skel.any() else float("nan")
        r_true.append(radii[k]); r_vec.append(rv); r_edt.append(re); v_err.append(abs(av - tv) / tv)
        rows.append(["branch %d%s" % (k, " (detached piece)" if k == 6 else ""), "%.1f" % radii[k], "%.2f" % rv, "%.2f" % re,
                     "%d" % tv, "%d" % av, "%+.1f %%" % (100.0 * (av - tv) / tv)])
        print("  branch %d: true r %.1f  surface->skeleton+0.5 %.2f  edt on skeleton %.2f  volume true %d assigned %d (%+.1f %%)" % (
            k, radii[k], rv, re, tv, av, 100.0 * (av - tv) / tv))
    r_true, r_vec, r_edt, v_err = map(np.array, (r_true, r_vec, r_edt, v_err))
    order = np.argsort(r_true)                                            # 図の折れ線は半径の順に

    # 5. 値だけの古典: 接合点の周りを球で切る(半径を振る)
    cut_rows, cut_best = [], None
    cut_labels = {}
    for R in (0.0, 2.0, 4.0, 6.0):
        lab = junction_cut(mask, skel, branches, R)
        _m, a = match_labels(lab, truth)
        lost = float((lab[mask] == 0).mean())
        ok = float((a[mask] == truth[mask]).mean())
        n_cc = len(np.unique(lab)) - 1
        cut_rows.append(["junction cut, ball r=%.0f" % R, "-", "-", "-", "-", "%d pieces" % n_cc, "agree %.3f, unassigned %.1f %%" % (ok, 100 * lost)])
        cut_labels[R] = a
        print("  junction cut r=%.0f: %d pieces, agreement %.3f, unassigned %.1f %%" % (R, n_cc, ok, 100 * lost))
        if cut_best is None or ok > cut_best[1]:
            cut_best = (R, ok, lost)

    # 真値: 縄張りは古典のどの球より一致し、半径は 2 法とも 0.5 voxel 以内、体積は 15 % 以内
    assert acc >= 0.9, acc
    assert acc > cut_best[1] + 0.02, (acc, cut_best)
    assert np.all(np.abs(r_vec - r_true) <= 0.5) and np.all(np.abs(r_edt - r_true) <= 0.5), (r_vec, r_edt)
    assert np.all(v_err <= 0.15), v_err
    print("ORDER: territory agreement %.3f (vol_nearest_label) > %.3f (best junction cut, r=%.0f, which also leaves %.1f %% unassigned)" % (
        acc, cut_best[1], cut_best[0], 100 * cut_best[2]))

    # 図
    if figs.enabled():
        figs.save_grid("territories",
                       [project_labels(truth), project_labels(blab, over=skel & ~branches),
                        project_labels(assigned), project_labels(cut_labels[4.0], base=mask)],
                       captions=["true territory (nearest axis)", "skeleton branches (skeletonize_vol -> skeleton_branches3d), white = junctions",
                                 "vol_nearest_label territory (agreement %.3f)" % acc,
                                 "junction cut, ball r=4 (grey = volume thrown away)"],
                       ncols=2, gray=[False] * 4,
                       caption="z projection of the synthetic dendrite: every voxel gets the branch whose skeleton is nearest, so the branch volumes can be counted; cutting balls around the junctions instead either fails to separate the branches or throws volume away")
        frames = turning_gif(mask, assigned, debris, 180 if REDUCED else 320)
        figs.save_gif("territory_turning", frames, fps=12.0,
                      caption="the surface voxels coloured by branch territory (vol_nearest_label on the labelled skeleton), turning; grey = the 6 debris blobs that vol_rle_components dropped by volume")
        lim = (0.0, max(r_true.max(), np.nanmax(r_vec), np.nanmax(r_edt)) + 0.5)
        figs.save_plot("radius_recovery",
                       [("surface -> skeleton displacement + 0.5 (vol_nearest_seed_vector)", r_true[order], r_vec[order]),
                        ("distance transform on the skeleton (classic)", r_true[order], r_edt[order]),
                        ("identity", np.array(lim), np.array(lim))],
                       xlabel="true radius [voxel]", ylabel="measured radius [voxel]",
                       title="per-branch radius: max error %.2f (displacement) / %.2f (classic) voxel" % (np.abs(r_vec - r_true).max(), np.abs(r_edt - r_true).max()),
                       caption="both readings recover the radius of every branch to within half a voxel (the surface voxel centre sits half a voxel inside the boundary, hence the +0.5); the displacement gives a radius at every surface voxel, the classic only on the skeleton",
                       xlim=lim, ylim=lim)
        figs.save_table("branch_numbers", ["branch", "true r", "r (surface->skel + 0.5)", "r (edt on skel)", "true voxels", "assigned voxels", "volume error"],
                        rows + cut_rows, title="branch territories: vol_nearest_label vs junction cutting",
                        caption="volume per branch comes from the territory; the junction-cut rows show that no ball radius separates the branches without throwing volume away")
        assert not figs.errors(), figs.errors()
    print("elapsed %.0fs" % (time.time() - t0))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
