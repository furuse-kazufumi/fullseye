# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""segworld の門: truth を画像・ラベルから数え直す(レンズの面積、ボロノイの辺と面積は scipy.spatial と総当たりの半平面、
影は部品と交わらない、質感は平均が同じで周期が測れる、照明は割り算で雑音だけ残り大域閾値が壊れる、細い構造は点–線分の
総当たりとスタジアムの面積)。"""
from __future__ import annotations

import math

import numpy as np
import pytest
from scipy.spatial import Voronoi

import segeval as SE
import segworld as SW


# ───────────────────────── 道具(独立な経路) ─────────────────────────
def otsu_threshold(img):
    """ヒストグラムの Otsu(自前、256 段)。"""
    hist, edges = np.histogram(img, bins=256, range=(0.0, 1.0))
    mids = 0.5 * (edges[1:] + edges[:-1])
    w0 = np.cumsum(hist)
    w1 = hist.sum() - w0
    m0 = np.cumsum(hist * mids) / np.maximum(w0, 1)
    m1 = (np.sum(hist * mids) - np.cumsum(hist * mids)) / np.maximum(w1, 1)
    var = w0 * w1 * (m0 - m1) ** 2
    return float(mids[int(np.argmax(var))])


def best_jaccard_against_mask(mask_pred, truth_mask):
    """予測のマスクとその補集合のうち、真のマスクと Jaccard が高い方(閾値の向きを問わない)。"""
    a = SE.seg_dice_jaccard(mask_pred, truth_mask)["jaccard"]
    b = SE.seg_dice_jaccard(~mask_pred, truth_mask)["jaccard"]
    return max(a, b)


def clip_segment(p, q, lo, hi):
    """線分 p→q を矩形(両軸とも lo 以上 hi 以下)で切った長さ(Liang–Barsky)。"""
    d = q - p
    t0, t1 = 0.0, 1.0
    for k in range(2):
        for sign, bound in ((-1.0, lo[k]), (1.0, hi[k])):
            pk = sign * d[k]
            qk = sign * (bound - p[k]) if sign > 0 else p[k] - bound
            if abs(pk) < 1e-15:
                if qk < 0:
                    return 0.0
                continue
            t = qk / pk
            if pk < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
    return float(np.hypot(*d)) * max(t1 - t0, 0.0)


def voronoi_edge_length_scipy(seeds, size):
    """scipy.spatial.Voronoi の稜線(無限のものは遠くまで伸ばす)を矩形で切った長さの和。"""
    h, w = size
    lo, hi = np.array([-0.5, -0.5]), np.array([h - 0.5, w - 0.5])
    vor = Voronoi(seeds)
    center = seeds.mean(axis=0)
    far = 10.0 * (h + w)
    total = 0.0
    for (a, b), (va, vb) in zip(vor.ridge_points, vor.ridge_vertices):
        if va >= 0 and vb >= 0:
            p, q = vor.vertices[va], vor.vertices[vb]
        else:
            v = vor.vertices[va if va >= 0 else vb]
            t = seeds[b] - seeds[a]
            t = t / np.linalg.norm(t)
            n = np.array([-t[1], t[0]])
            mid = 0.5 * (seeds[a] + seeds[b])
            if np.dot(mid - center, n) < 0:
                n = -n
            p, q = v, v + n * far
        total += clip_segment(np.asarray(p, float), np.asarray(q, float), lo, hi)
    return total


# ───────────────────────── 1. 触れ合う粒 ─────────────────────────
@pytest.mark.parametrize("n,ov,seed", [(10, 0.2, 0), (6, 0.0, 1), (12, 0.45, 2)])
def test_blobs_overlap_equals_lens_closed_form_and_pixel_recount(n, ov, seed):
    wld = SW.world_blobs_touching(n, ov, seed)
    T, lab, cm = wld["truth"], wld["labels"], wld["count_map"]
    r, C = T["radius"], T["centers"]
    assert lab.max() == n and len(np.unique(lab)) == n + 1
    # 画素の数え直し(独立: 円の不等式を全部の対で直接)
    yy, xx = np.mgrid[0:lab.shape[0], 0:lab.shape[1]]
    inside = [(yy - c[0]) ** 2 + (xx - c[1]) ** 2 <= r * r for c in C]
    assert len(inside) == n
    assert np.array_equal(sum(m.astype(int) for m in inside), cm)
    lens_px = 0
    for a, b in T["pairs"]:
        lens_px += int(np.sum(inside[a] & inside[b]))
    assert lens_px == int(np.sum(cm >= 2))                          # 鎖なので三重の重なりは無い
    assert np.all(cm <= 2)
    # 閉形式との差は境界の画素数のオーダー(各レンズの周囲 4 r θ)
    if ov > 0:
        assert len(T["pairs"]) > 0
        d = 2 * r * (1 - ov)
        peri = len(T["pairs"]) * 4 * r * math.acos(d / (2 * r))
        assert abs(lens_px - T["lens_area"].sum()) <= 0.5 * peri + 2
        assert T["overlap_measured"] > 0
    else:
        assert T["lens_area"].sum() == 0.0 and T["overlap_measured"] == 0.0
    # 各ラベルの面積 = πr² − Σ レンズ/2(周囲の画素数の半分まで)、Σ ラベル = 和集合
    areas_px = np.bincount(lab.ravel(), minlength=n + 1)[1:]
    assert np.all(np.abs(areas_px - T["areas"]) <= 0.5 * 2 * math.pi * r + 2)
    assert areas_px.sum() == int(np.sum(cm > 0))
    assert abs(int(np.sum(cm > 0)) - T["union_area"]) <= 0.5 * n * 2 * math.pi * r + 2
    # 重なった画素は和集合の画素より明るい側(細胞の見た目)、背景は暗い
    im = wld["image"]
    assert im[cm == 0].mean() < im[cm == 1].mean()


def test_blobs_overlap_knob_is_monotone_and_too_many_blobs_raise():
    m = [SW.world_blobs_touching(8, ov, 0)["truth"]["overlap_measured"] for ov in (0.0, 0.15, 0.3, 0.45)]
    assert m[0] == 0.0 and m[1] < m[2] < m[3]
    with pytest.raises(ValueError):
        SW.world_blobs_touching(200, 0.0, 0, size=(64, 64), radius=14.0)


# ───────────────────────── 2. ボロノイ結晶粒 ─────────────────────────
@pytest.mark.parametrize("n,seed,jit", [(36, 0, 0.8), (20, 3, 0.3), (50, 7, 0.95)])
def test_voronoi_edges_and_areas_match_scipy_and_pixels(n, seed, jit):
    wld = SW.world_grains_voronoi(n, seed, jitter=jit)
    T, lab = wld["truth"], wld["labels"]
    h, w = lab.shape
    assert len(np.unique(lab)) == n and lab.min() == 1
    assert T["areas"].sum() == pytest.approx(h * w, abs=1e-6)        # 分割なので面積の和 = 矩形
    L_scipy = voronoi_edge_length_scipy(T["seeds"], (h, w))
    assert T["edge_length_total"] == pytest.approx(L_scipy, rel=1e-9, abs=1e-6)
    # 画素の面積 = 多角形の面積 ± 周囲の画素数(各セルの最近傍の判定を自分で引く)
    yy, xx = np.mgrid[0:h, 0:w]
    S = T["seeds"]
    d2 = (yy[None] - S[:, 0, None, None]) ** 2 + (xx[None] - S[:, 1, None, None]) ** 2
    assert np.array_equal(np.argmin(d2, axis=0) + 1, lab)
    px = np.bincount(lab.ravel(), minlength=n + 1)[1:]
    assert len(px) == n
    for k in range(n):
        poly = T["polygons"][k]
        peri = float(np.sum(np.hypot(*(np.roll(poly, -1, axis=0) - poly).T)))
        assert abs(px[k] - T["areas"][k]) <= 0.75 * peri + 2
    # 割れ目(4 近傍でラベルが変わる対)の数は L と √2 L の間(向き θ の線分が横切る割れ目 = ℓ(|cos θ| + |sin θ|))
    cracks = int(np.sum(lab[:, 1:] != lab[:, :-1])) + int(np.sum(lab[1:, :] != lab[:-1, :]))
    E = T["n_edges"]
    assert T["edge_length_total"] - 2 * E <= cracks <= math.sqrt(2) * T["edge_length_total"] + 2 * E
    # 粒界までの距離の閉形式: 割れ目に接する画素は 1 以内(隣との距離 1 の間を線が通る)、4 近傍が全部同じラベルの画素は
    # 1/√2 以上(法線 n の成分の最大は 1/√2 以上なので、それより近い線は必ずどれかの隣を向こう側に置く)
    ed = wld["edge_distance"]
    touch = np.zeros(lab.shape, bool)
    touch[:, 1:] |= lab[:, 1:] != lab[:, :-1]
    touch[:, :-1] |= lab[:, 1:] != lab[:, :-1]
    touch[1:, :] |= lab[1:, :] != lab[:-1, :]
    touch[:-1, :] |= lab[1:, :] != lab[:-1, :]
    assert ed[touch].max() <= 1.0 + 1e-9 and ed[~touch].min() >= 1.0 / math.sqrt(2.0) - 1e-9
    assert wld["image"][touch].mean() < wld["image"][~touch].mean()


def test_voronoi_cells_rejects_coincident_seeds():
    with pytest.raises(ValueError):
        SW.voronoi_cells([[3.0, 3.0], [3.0, 3.0]], (32, 32))


# ───────────────────────── 3. 影のある部品 ─────────────────────────
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_parts_area_closed_form_shadow_disjoint_and_lit_side_brighter(seed):
    wld = SW.world_parts_with_shadow(seed)
    T, lab, sh, im = wld["truth"], wld["labels"], wld["shadow"], wld["image"]
    n = T["n_parts"]
    assert lab.max() == n and len(T["parts"]) == n
    px = np.bincount(lab.ravel(), minlength=n + 1)[1:]
    for k, p in enumerate(T["parts"]):
        peri = 2 * (p["w"] + p["h"]) + sum(2 * math.pi * r for _u, _v, r in p["holes"])
        assert abs(px[k] - T["areas"][k]) <= 0.75 * peri + 2
        assert len(p["holes"]) >= 1
    assert not np.any(sh & (lab > 0)) and sh.sum() == T["shadow_area"] > 0
    # 影 = 部品を光の向きにずらした集合 − 部品(自分でずらして数え直す)
    dy, dx = T["shadow_offset"]
    body = lab > 0
    shifted = np.zeros_like(body)
    shifted[max(dy, 0):body.shape[0] + min(dy, 0), max(dx, 0):body.shape[1] + min(dx, 0)] = \
        body[max(-dy, 0):body.shape[0] + min(-dy, 0), max(-dx, 0):body.shape[1] + min(-dx, 0)]
    assert np.array_equal(sh, shifted & ~body)
    assert (dy, dx) == (int(round(9.0 * math.sin(math.radians(T["light_angle"])))), int(round(9.0 * math.cos(math.radians(T["light_angle"])))))
    # 影は背景より暗い、部品の光に向く側はその反対側より明るい
    bg = ~body & ~sh
    assert im[sh].mean() < im[bg].mean() - 0.15
    yy, xx = np.mgrid[0:lab.shape[0], 0:lab.shape[1]]
    L = np.array([math.sin(math.radians(T["light_angle"])), math.cos(math.radians(T["light_angle"]))])
    for k, p in enumerate(T["parts"]):
        s = -((yy - p["center"][0]) * L[0] + (xx - p["center"][1]) * L[1])
        m = lab == k + 1
        assert im[m & (s > 0)].mean() > im[m & (s < 0)].mean() + 0.1
    # 閾値が欺かれる世界: 大域 Otsu の Jaccard は 0.8 未満(暗い側か影のどちらかを失う)
    th = otsu_threshold(im)
    assert best_jaccard_against_mask(im > th, body) < 0.8


# ───────────────────────── 4. 質感だけ違う領域 ─────────────────────────
@pytest.mark.parametrize("n,seed", [(2, 0), (3, 1), (4, 2)])
def test_texture_regions_share_the_mean_but_differ_in_std_and_period(n, seed):
    wld = SW.world_texture_regions(seed, n_regions=n)
    T, lab, im = wld["truth"], wld["labels"], wld["image"]
    assert lab.min() == 1 and lab.max() == n and len(T["specs"]) == n
    means = np.array([im[lab == k + 1].mean() for k in range(n)])
    stds = np.array([im[lab == k + 1].std() for k in range(n)])
    assert np.all(np.abs(means - T["mean"]) < 0.012)
    for k, sp in enumerate(T["specs"]):
        assert stds[k] == pytest.approx(sp["std"], rel=0.12)
    assert stds[1] > 2.5 * stds[0]
    # 縞の周期: 法線に沿って平均を引いた値の符号の変わる回数 → 周期 = 2 × 長さ / 回数
    yy, xx = np.mgrid[0:lab.shape[0], 0:lab.shape[1]]
    for k, sp in enumerate(T["specs"]):
        if sp["kind"] != "stripes":
            continue
        th = math.radians(sp["angle"])
        s = xx * math.cos(th) + yy * math.sin(th)
        m = lab == k + 1
        bins = np.round(s[m] - s[m].min()).astype(int)
        prof = np.bincount(bins, weights=im[m] - T["mean"]) / np.maximum(np.bincount(bins), 1)
        prof = np.convolve(prof, np.ones(3) / 3, mode="same")
        cross = int(np.sum(np.sign(prof[1:]) != np.sign(prof[:-1])))
        assert cross > 4
        assert 2.0 * (len(prof) - 1) / cross == pytest.approx(sp["period"], rel=0.15)
    # 閾値では切れない世界: 大域 Otsu のどの領域に対する Jaccard も 0.6 未満
    th = otsu_threshold(im)
    for k in range(n):
        assert best_jaccard_against_mask(im > th, lab == k + 1) < 0.6


# ───────────────────────── 5. 照明の勾配 ─────────────────────────
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_gradient_world_breaks_global_threshold_but_not_flat_field_or_local(seed):
    wld = SW.world_gradient_illumination(seed)
    T, lab, im, I, R = wld["truth"], wld["labels"], wld["image"], wld["illumination"], wld["reflectance_map"]
    n = T["n_objects"]
    assert lab.max() == n
    px = np.bincount(lab.ravel(), minlength=n + 1)[1:]
    for k, o in enumerate(T["objects"]):
        if o["kind"] == "rect":
            assert px[k] == T["areas"][k]                              # 整数の矩形はちょうど
        else:
            assert abs(px[k] - T["areas"][k]) <= 0.75 * 2 * math.pi * o["radius"] + 2
    # 照明の閉形式を自分で引き、割り算で雑音だけが残る(クリップされた画素は除く)
    h, w = lab.shape
    yy, xx = np.mgrid[0:h, 0:w]
    I2 = T["i0"] + T["gradient"][0] * xx / (w - 1) + T["gradient"][1] * yy / (h - 1)
    assert np.allclose(I2, I)
    ok = (im > 0.0) & (im < 1.0)
    resid = (im - I * R)[ok]
    assert ok.mean() > 0.9 and abs(resid.mean()) < 0.003 and resid.std() == pytest.approx(T["noise"], rel=0.1)
    body = lab > 0
    th = otsu_threshold(im)
    j_global = best_jaccard_against_mask(im > th, body)
    flat = np.clip(im / I, 0.0, 1.5)
    j_flat = best_jaccard_against_mask(flat > otsu_threshold(np.clip(flat, 0, 1)), body)
    # 局所閾値(ブロックの平均 − k·σ、自前)
    from scipy.ndimage import uniform_filter
    loc = uniform_filter(im, 31)
    j_local = best_jaccard_against_mask(im < loc - 0.08, body)
    assert j_global < 0.75 < 0.9 < j_flat and j_local > 0.85, (j_global, j_flat, j_local)


# ───────────────────────── 6. 細い構造 ─────────────────────────
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_thin_structures_masks_recount_by_point_segment_distance(seed):
    wld = SW.world_thin_structures(seed)
    T, lab, im, D = wld["truth"], wld["labels"], wld["image"], wld["distance"]
    n = T["n"]
    assert lab.max() == n and len(T["polylines"]) == n
    h, w = lab.shape
    yy, xx = np.mgrid[0:h, 0:w]
    px = np.bincount(lab.ravel(), minlength=n + 1)[1:]
    for k, P in enumerate(T["polylines"]):
        # 点–線分の距離の総当たり(独立な式: 射影の係数をクリップ)
        best = np.full((h, w), np.inf)
        for a, b in zip(P[:-1], P[1:]):
            ab = b - a
            t = np.clip(((yy - a[0]) * ab[0] + (xx - a[1]) * ab[1]) / (ab @ ab), 0, 1)
            best = np.minimum(best, np.sqrt((yy - a[0] - t * ab[0]) ** 2 + (xx - a[1] - t * ab[1]) ** 2))
        wk = T["widths"][k]
        assert np.array_equal(lab == k + 1, best <= wk / 2)
        assert T["lengths"][k] == pytest.approx(float(np.sum(np.hypot(*(np.diff(P, axis=0)).T))))
        if T["kinds"][k] == "line":
            assert abs(px[k] - T["areas_stadium"][k]) <= 0.75 * (2 * T["lengths"][k] + math.pi * wk) + 2
        assert px[k] > 0
    assert set(T["kinds"]) == {"line", "crack"} and T["length_total"] == pytest.approx(T["lengths"].sum())
    assert np.allclose(D[lab > 0].max(), max(T["widths"]) / 2, atol=0.5) and np.all(D[lab == 0] > 0.5)
    # 細いほど薄い: 幅 1 の線は幅 3 の線より明るい、どれも背景より暗い
    bg = im[lab == 0].mean()
    dark = {wk: im[lab == k + 1].mean() for k, wk in enumerate(T["widths"])}
    assert len(dark) == 3
    assert dark[1.0] > dark[2.0] > dark[3.0] and dark[1.0] < bg - 0.1


# ───────────────────────── 異常入力 ─────────────────────────
@pytest.mark.parametrize("call", [
    lambda: SW.world_blobs_touching(0),
    lambda: SW.world_blobs_touching(5, 0.9),
    lambda: SW.world_blobs_touching(5, 0.2, size=(8, 8)),
    lambda: SW.world_blobs_touching(5, 0.2, radius=1.0),
    lambda: SW.world_blobs_touching(5, 0.2, seed="x"),
    lambda: SW.world_grains_voronoi(1),
    lambda: SW.world_grains_voronoi(10, jitter=1.0),
    lambda: SW.world_grains_voronoi(10, boundary_width=0.0),
    lambda: SW.world_parts_with_shadow(n_parts=0),
    lambda: SW.world_parts_with_shadow(shadow_length=-1.0),
    lambda: SW.world_texture_regions(n_regions=5),
    lambda: SW.world_texture_regions(noise=0.0),
    lambda: SW.world_gradient_illumination(gradient=(0.5, 0.5)),
    lambda: SW.world_gradient_illumination(reflectance=1.0),
    lambda: SW.world_thin_structures(widths=()),
    lambda: SW.world_thin_structures(widths=(0.1,)),
    lambda: SW.world_thin_structures(noise=float("nan")),
])
def test_bad_inputs_raise(call):
    with pytest.raises(ValueError):
        call()
