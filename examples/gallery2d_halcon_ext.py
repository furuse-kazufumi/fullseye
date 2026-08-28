# -*- coding: utf-8 -*-
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gallery2d_halcon_ext — HALCON 拡充 tier(``hx_`` 一族, category=halcon_ext)を総ざらいで検証する事例 (task: contract-gallery)。

    py -3.11 examples/gallery2d_halcon_ext.py

【平たく言うと(この op 一族は何のためのもの)】
imgevolve の HALCON 拡充 tier は、既存 registry で未カバーだった **実在の HALCON operator** を
genuine な numpy 実装で足したもの。1 ファイルに多分野が同居する:
  - Regions 生成(gen_circle / gen_ellipse / gen_rectangle2 / セクタ / 格子 / 円板 SE …)
  - フィルタ(Gabor / 周波数 low/high/band-pass / 微分 / gray-値の多項式面近似=照明推定)
  - セグメンテーション(char_threshold / histo 谷 / lowlands / plateaus / edge-segments)
  - Region 形態(erosion1 / dilation1 / opening / closing / expand / clip / move / skeleton 分割)
  - XLD 輪郭(sort / clip / split / parallel / union / 円・楕円・矩形フィット / 自己交差 / 距離)
  - 3D 復元(shape-from-shading の光源 tilt/slant/albedo 推定 / disparity→depth)
これらは「進化ノブ a,b∈[0,1] を受け取り 1 つの sort を別の sort へ写す」共通契約 fn(v,a,b) を守る。

【グラウンドトゥルース(数値で嘘を弾く)】
本ファミリの **全 op** を呼び出し、op ごとに次の 3 契約を検証する:
  (1) 有限性     : 出力に NaN/Inf が無い。
  (2) 型(out_sort): image/region → [0,1] の 2-D float 配列 / contour → {shape,cs} dict /
                     feature → 有限スカラ(または配列)。宣言 out_sort と一致する。
  (3) 決定性     : 同じ入力・同じノブなら 2 回の呼び出しがビット一致(乱数 op も固定 seed)。
raise した op は握りつぶさず即 FAIL。加えて効果が既知の代表 6 op には、単なる "動く" を超えた
**強い GT + beat-the-null**(ぼかしは分散を下げる、閾値は二値になる、円フィットは四角より円に良く当たる…)を課す。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402
import ops  # noqa: E402


# --------------------------------------------------------------------------- #
# 入力バッテリ — tests/conftest.py の構成を複製(examples は tests/ を import しない)。 #
# image = [0,1] の 2-D float / region = 二値っぽい 2-D / contour = {shape,(H,W); cs:[Nx2]} #
# --------------------------------------------------------------------------- #
def _image_normal(n: int = 48) -> np.ndarray:
    """conftest.image_bank()['normal'] と同一構成: 勾配 + 円板 + 市松 + 微小ノイズ。"""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    grad = xx / (n - 1)
    disk = ((yy - n * 0.35) ** 2 + (xx - n * 0.4) ** 2) < (n * 0.18) ** 2
    checker = ((xx.astype(int) // 6 + yy.astype(int) // 6) % 2) * 0.15
    rng = np.random.default_rng(20260812)
    return np.clip(0.35 * grad + 0.45 * disk + checker + 0.03 * rng.standard_normal((n, n)), 0, 1)


def _region_disk(n: int = 48) -> np.ndarray:
    """conftest.region_bank()['disk'] と同一構成: 中央の充実円板 region。"""
    yy, xx = np.mgrid[0:n, 0:n]
    return (((yy - n // 2) ** 2 + (xx - n // 2) ** 2) < (n * 0.25) ** 2).astype(np.float64)


def _contour_square(n: int = 48) -> dict:
    """密にサンプルした閉じた正方形 XLD 輪郭(conftest.contour_bank の square を高密度化)。

    RDP 分割・端点切り・平行輪郭・自己交差など点数を要する op に耐えるよう各辺 12 点。
    """
    lo, hi = n * 0.2, n * 0.8
    t = np.linspace(0.0, 1.0, 12, endpoint=False)
    top = np.column_stack([np.full_like(t, lo), lo + (hi - lo) * t])
    right = np.column_stack([lo + (hi - lo) * t, np.full_like(t, hi)])
    bot = np.column_stack([np.full_like(t, hi), hi - (hi - lo) * t])
    left = np.column_stack([hi - (hi - lo) * t, np.full_like(t, lo)])
    poly = np.vstack([top, right, bot, left, top[:1]])  # 端点一致 = 閉曲線
    return {"shape": (n, n), "cs": [poly]}


def input_for(in_sort: str):
    """in_sort に合致する妥当な 1 入力を返す(この一族が使う 3 sort を網羅)。"""
    if in_sort == "image":
        return _image_normal()
    if in_sort == "region":
        return _region_disk()
    if in_sort == "contour":
        return _contour_square()
    raise ValueError(f"予期しない in_sort: {in_sort}")


def _fresh(x):
    """入力の独立コピー(op が入力を破壊しても決定性チェックが汚れないように)。"""
    if isinstance(x, dict):
        return {"shape": x["shape"], "cs": [c.copy() for c in x["cs"]]}
    return np.array(x, copy=True)


def _equal(a, b) -> bool:
    """出力のビット一致(dict 輪郭は cs を要素ごとに比較)。"""
    if isinstance(a, dict) or isinstance(b, dict):
        if not (isinstance(a, dict) and isinstance(b, dict)):
            return False
        if len(a["cs"]) != len(b["cs"]):
            return False
        return all(np.array_equal(np.asarray(x), np.asarray(y)) for x, y in zip(a["cs"], b["cs"]))
    return np.array_equal(np.asarray(a), np.asarray(b))


# --------------------------------------------------------------------------- #
# TARGET: category == 'halcon_ext' の全 op(登録順)。名前は文字列リテラルで列挙       #
# (op→example インデックスが各名を静的に拾えるように)。                            #
# --------------------------------------------------------------------------- #
OPS = [
    "hx_gen_circle", "hx_gen_ellipse", "hx_gen_rectangle2", "hx_gen_checker_region",
    "hx_gen_grid_region", "hx_gabor", "hx_fit_surface1", "hx_fit_surface2",
    "hx_cooc_feature", "hx_full_domain", "hx_mean_shape", "hx_close_edges",
    "hx_close_edges_length", "hx_expand_region", "hx_region_to_mean", "hx_nonmax_dir",
    "hx_char_threshold", "hx_histo_to_thresh", "hx_gen_lowpass", "hx_gen_highpass",
    "hx_gen_bandpass", "hx_erosion1", "hx_dilation1", "hx_opening",
    "hx_closing", "hx_dilation2", "hx_gen_disc_se", "hx_gen_circle_sector",
    "hx_gen_ellipse_sector", "hx_gen_empty_region", "hx_clip_region_rel", "hx_gen_bandfilter",
    "hx_gen_derivative_filter", "hx_fill_interlace", "hx_shade_height_field", "hx_plane_deviation",
    "hx_detect_edge_segments", "hx_gen_image_proto", "hx_get_domain", "hx_region_to_label",
    "hx_rectangle1_domain", "hx_lowlands", "hx_plateaus_center", "hx_move_region",
    "hx_split_skeleton_region", "hx_test_region_point", "hx_test_region_points", "hx_sort_contours",
    "hx_clip_contours", "hx_clip_end_points", "hx_smallest_circle_xld", "hx_smallest_rect1_xld",
    "hx_test_closed_xld", "hx_regress_contours", "hx_moments_any_xld", "hx_split_contours",
    "hx_gen_parallel_contour", "hx_fit_circle_contour", "hx_fit_ellipse_contour", "hx_fit_rectangle2_contour",
    "hx_smallest_rect2_xld", "hx_crop_contours", "hx_dist_ellipse_contour", "hx_test_self_intersect",
    "hx_union_adjacent", "hx_polar_trans_inv", "hx_select_xld_point", "hx_estimate_tilt_lr",
    "hx_estimate_tilt_zc", "hx_estimate_sl_al_lr", "hx_estimate_sl_al_zc", "hx_estimate_al_am",
    "hx_add_noise_contour", "hx_radial_distort_contour", "hx_dist_ellipse_points", "hx_dist_rect2_points",
    "hx_distance_pc", "hx_disparity_to_xyz", "hx_distance_pr", "hx_distance_sc",
    "hx_fuzzy_measure_pairs",
]

# 進化ノブの端と代表値(conftest.KNOBS と同じ)を全 op に通す。
KNOBS = [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0), (0.15, 0.85)]

_EPS = 1e-9


def _assert_typed_finite(name: str, out, out_sort: str) -> None:
    """出力が宣言 out_sort に一致し、有限であることを検証(sort 別)。"""
    if out_sort in ("image", "region"):
        assert not isinstance(out, dict), f"{name}: {out_sort} が dict を返した"
        arr = np.asarray(out, dtype=np.float64)
        assert arr.ndim == 2, f"{name}: {out_sort} の ndim={arr.ndim}(2 を期待)"
        assert np.all(np.isfinite(arr)), f"{name}: {out_sort} に非有限値"
        assert arr.min() >= -_EPS and arr.max() <= 1.0 + _EPS, \
            f"{name}: {out_sort} が [0,1] 外 [{arr.min():.4g},{arr.max():.4g}]"
    elif out_sort == "feature":
        assert not isinstance(out, dict), f"{name}: feature が dict を返した"
        arr = np.asarray(out, dtype=np.float64)
        assert arr.ndim <= 1, f"{name}: feature の ndim={arr.ndim}(スカラ/1-D を期待)"
        assert np.all(np.isfinite(arr)), f"{name}: feature に非有限値"
    elif out_sort == "contour":
        assert isinstance(out, dict) and "cs" in out and "shape" in out, \
            f"{name}: contour が {{shape,cs}} dict でない"
        for c in out["cs"]:
            ca = np.asarray(c, dtype=np.float64)
            assert ca.ndim == 2 and ca.shape[1] == 2, f"{name}: contour の点配列が Nx2 でない"
            assert np.all(np.isfinite(ca)), f"{name}: contour に非有限点"
    else:
        raise AssertionError(f"{name}: 未知の out_sort={out_sort!r}")


def run_contract_battery() -> int:
    """全 op × 全ノブで (1)有限性 (2)型 (3)決定性 を検証。raise は握りつぶさず即失敗。"""
    by = ops._BY_NAME
    # OPS が TARGET(category=halcon_ext)を過不足なく覆うことを先に固定。
    target = [o.name for o in ops.REGISTRY if o.category == "halcon_ext"]
    missing = sorted(set(target) - set(OPS))
    extra = sorted(set(OPS) - set(target))
    assert not missing, f"OPS が取りこぼした halcon_ext op: {missing}"
    assert not extra, f"OPS に halcon_ext 以外が混入: {extra}"
    assert len(OPS) == len(target) == len(set(OPS)), \
        f"件数不一致 OPS={len(OPS)} target={len(target)} (重複?)"

    for name in OPS:
        op = by[name]
        for (a, b) in KNOBS:
            # (1)(2) 有限性 + 型: raise はここで表面化して FAIL。
            out = op.fn(_fresh(input_for(op.in_sort)), a, b)
            _assert_typed_finite(name, out, op.out_sort)
            # (3) 決定性: 独立コピー入力で 2 回、ビット一致。
            out2 = op.fn(_fresh(input_for(op.in_sort)), a, b)
            assert _equal(out, out2), f"{name}: 非決定的(ノブ a={a},b={b} で 2 回の出力が不一致)"
    return len(OPS)


# --------------------------------------------------------------------------- #
# 代表 op の強い GT + beat-the-null(効果が既知のものだけ、"動く" を超えて中身を検証)。 #
# --------------------------------------------------------------------------- #
def run_ground_truth() -> int:
    by = ops._BY_NAME
    img = _image_normal()
    reg = _region_disk()
    n = img.shape[0]
    checks = 0

    # 1) hx_gen_circle: 生成 region は二値、幾何が正しく、ノブ a が半径を単調に制御。
    small = by["hx_gen_circle"].fn(img, 0.0, 0.0)
    big = by["hx_gen_circle"].fn(img, 1.0, 0.0)
    assert set(np.unique(big)) <= {0.0, 1.0}, "gen_circle が二値でない"
    assert big[n // 2, n // 2] == 1.0 and big[0, 0] == 0.0, "gen_circle の中心内/隅外が不成立"
    assert big.sum() > small.sum() * 3, "gen_circle: 半径ノブが面積を増やさない(beat-the-null)"
    checks += 1

    # 2) hx_gabor: DC 除去済みなので平坦画像には無反応(分散≈0)、テクスチャには反応。
    const = np.full((n, n), 0.42)
    resp_tex = by["hx_gabor"].fn(img, 0.3, 0.5)
    resp_flat = by["hx_gabor"].fn(const, 0.3, 0.5)
    assert float(resp_flat.var()) < 1e-12, "gabor が平坦画像に反応した(DC 漏れ)"
    assert float(resp_tex.var()) > 1e-4, "gabor がテクスチャに無反応(beat-the-null: 平坦=0)"
    checks += 1

    # 3) hx_char_threshold: 出力は二値、かつ暗い文字画素を選ぶ=前景平均 < 全体平均。
    seg = by["hx_char_threshold"].fn(img, 0.5, 0.0)
    fg = seg > 0.5
    assert set(np.unique(seg)) <= {0.0, 1.0}, "char_threshold が二値でない"
    assert fg.any(), "char_threshold が何も選ばなかった"
    assert float(img[fg].mean()) < float(img.mean()) - 0.05, \
        "char_threshold が暗部を選べていない(beat-the-null: ランダム選択なら差≈0)"
    checks += 1

    # 4) hx_erosion1 / hx_dilation1: 侵食は面積を減らし膨張は増やす(erode ≤ 原 ≤ dilate、厳密順序)。
    ar_orig = float(reg.sum())
    ar_er = float(by["hx_erosion1"].fn(reg, 0.5, 0.0).sum())
    ar_di = float(by["hx_dilation1"].fn(reg, 0.5, 0.0).sum())
    assert ar_er < ar_orig < ar_di, f"morphology 単調性が破れた erode={ar_er} orig={ar_orig} dilate={ar_di}"
    checks += 1

    # 5) hx_gen_lowpass / hx_gen_highpass: LP は DC(中心)を通し HP は殺す、
    #    かつ LP の通過帯域は遮断ノブ a で単調に広がる。
    lp = by["hx_gen_lowpass"].fn(img, 0.5, 0.0)
    hp = by["hx_gen_highpass"].fn(img, 0.5, 0.0)
    assert lp[n // 2, n // 2] == 1.0 and hp[n // 2, n // 2] == 0.0, "low/high-pass の DC 扱いが逆"
    lp_narrow = by["hx_gen_lowpass"].fn(img, 0.2, 0.0)
    lp_wide = by["hx_gen_lowpass"].fn(img, 0.9, 0.0)
    assert lp_wide.sum() > lp_narrow.sum() * 3, "lowpass: 遮断ノブで通過帯域が広がらない(beat-the-null)"
    checks += 1

    # 6) hx_fit_circle_contour: 円周上の点への円フィット残差 ≈ 0、四角の点には大きい残差。
    t = np.linspace(0.0, 2 * np.pi, 60, endpoint=False)
    circ = {"shape": (n, n), "cs": [np.column_stack([24 + 15 * np.sin(t), 24 + 15 * np.cos(t)])]}
    square = _contour_square(n)
    res_circ = float(by["hx_fit_circle_contour"].fn(circ, 0.5, 0.5))
    res_sq = float(by["hx_fit_circle_contour"].fn(square, 0.5, 0.5))
    assert res_circ < 1e-3, f"円周点への円フィット残差が大きすぎ({res_circ:.4g})"
    assert res_sq > res_circ * 20 + 1e-3, \
        f"円モデルが四角にも同程度に当たっている(beat-the-null) circle={res_circ:.4g} square={res_sq:.4g}"
    checks += 1

    return checks


def main() -> int:
    n_ops = run_contract_battery()
    n_gt = run_ground_truth()
    print(f"PASS: {n_ops} ops exercised, all finite/typed/deterministic; {n_gt} GT checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
