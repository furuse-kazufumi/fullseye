# -*- coding: utf-8 -*-
"""事例: 2-D 幾何オペレータ・ギャラリー (task=geometry) — 全 op を実行し契約を検証する。

    py -3.11 examples/gallery2d_geometry.py

【平たく言うと】
この例は Fullseye の「幾何(geometry)系」オペレータ族をまとめて動かす。族の中身は
5 カテゴリ:
  * geometry     … 画像/領域の回転・拡大縮小・鏡映・アフィン/射影/極座標変換
                   (キャリブレーション・矯正の土台)
  * transform    … 対数極座標・ラドン変換(サイノグラム)などの座標系変換
  * subpix       … 濃淡曲面の臨界点(極大/極小/鞍点/プラトー/低地)をサブピクセル抽出
  * xldgeom      … XLD 輪郭(点列)の幾何量(面積・重心・離心率・向き・軸比)と整形
  * deformation  … 制御点ベースの自由変形(TPS / B-spline FFD / MLS)
いずれも「画素/点をどこへ動かすか」を扱う写像であり、視覚パイプラインの前処理・
姿勢正規化・データ拡張の基盤になる。

【グラウンドトゥルース(GT)で嘘を弾く】
族の *全 op* を呼び、各 op について
  (1) 出力が有限(NaN/Inf 皆無)、
  (2) 宣言 out_sort と一致(image/region → [0,1] の 2-D 実数配列 /
      contour → dict{'shape','cs'} / feature → 有限スカラ・配列)、
  (3) 決定的(同一入力 → ビット一致出力)
を assert する。加えて効果が既知の代表 op には強い GT + beat-the-null を課す:
  * mirror_image      鏡映は画素の置換 → 値の多重集合を保存しつつ入力とは異なる
  * transpose_region  転置は対合(2 回で元へ戻る)かつ 1 回では変化する
  * deform_{tps,ffd,mls}  振幅 a=0 は恒等写像(差≈0)、a=0.8 では明確に変形する
  * sp_local_max_sub_pix  単峰ガウスでは峰の位置を検出、平坦画像では 0 個(null)
  * xg_height_width_ratio 既知バウンディングボックスの縦横比を厳密再現
  * xg_area_center        既知正方形の面積(シューレース)を厳密再現
  * xg_orientation        対角線 → 45°(=0.25)、水平線 → 0°(=0.0)で識別
族の全 op を実行し、契約(有限・型・決定性)と既知効果(GT)を検証する。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402
import ops  # noqa: E402


# --------------------------------------------------------------------------- #
# 各 in_sort に対する有効な入力を作る factory(tests/conftest.py の構成を複製)。   #
# examples は tests/ から import しない規約なので、ここに小さく再実装する。         #
# --------------------------------------------------------------------------- #
def _image(n: int = 48) -> np.ndarray:
    """勾配 + 明るい円板 + 市松 + 微小ノイズの [0,1] 濃淡画像(conftest の 'normal')。"""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    grad = xx / (n - 1)
    disk = ((yy - n * 0.35) ** 2 + (xx - n * 0.4) ** 2) < (n * 0.18) ** 2
    checker = ((xx.astype(int) // 6 + yy.astype(int) // 6) % 2) * 0.15
    noise = 0.03 * np.random.default_rng(20260812).standard_normal((n, n))
    return np.clip(0.35 * grad + 0.45 * disk + checker + noise, 0.0, 1.0)


def _region(n: int = 48) -> np.ndarray:
    """中心円板の二値領域(conftest の 'disk')。"""
    yy, xx = np.mgrid[0:n, 0:n]
    return (((yy - n // 2) ** 2 + (xx - n // 2) ** 2) < (n * 0.25) ** 2).astype(np.float64)


def _contour() -> dict:
    """1 個の閉じた正方形サブ輪郭を持つ XLD 輪郭 dict(conftest の 'square')。"""
    sq = np.array([[6.0, 6.0], [6.0, 20.0], [20.0, 20.0], [20.0, 6.0], [6.0, 6.0]])
    return {"shape": (32, 32), "cs": [sq]}


def input_for(sort: str):
    """in_sort に一致する有効な入力を返す(呼ぶ度に等価だが独立なコピー)。"""
    if sort == "image":
        return _image()
    if sort == "region":
        return _region()
    if sort == "contour":
        return _contour()
    raise AssertionError(f"unexpected in_sort in this family: {sort!r}")


# --------------------------------------------------------------------------- #
# TARGET op 集合 — カテゴリ geometry/xldgeom/transform/subpix/deformation の全 op。 #
# 文字列リテラルで明示列挙(op→example 逆引き索引のため各名がソースに現れる)。       #
# --------------------------------------------------------------------------- #
OPS = [
    # geometry (image -> image / region -> region)
    "rotate_img", "rescale_img", "affine_warp", "sk_swirl", "mirror_image",
    "transpose_region", "rotate_image", "zoom_image_factor", "zoom_image_size",
    "affine_trans_image", "polar_trans_image", "projective_trans_image",
    "projective_trans_image_size", "projective_trans_region", "polar_trans_image_inv",
    "affine_trans_image_size", "polar_trans_image_ext", "affine_trans_region",
    "mirror_region", "zoom_region", "polar_trans_region_inv",
    "xpil_offset", "xcv2_warp_logpolar", "xmh_haar", "xmh_daubechies",
    # subpix (image -> contour)
    "sp_local_max_sub_pix", "sp_local_min_sub_pix", "sp_saddle_points_sub_pix",
    "sp_critical_points_sub_pix", "sp_plateaus", "sp_lowlands_center",
    # xldgeom (contour -> feature / contour -> contour)
    "xg_moments", "xg_area_center", "xg_eccentricity", "xg_orientation",
    "xg_elliptic_axis", "xg_height_width_ratio", "xg_regress_contours",
    "xg_clip_contours", "xg_gen_polygons", "xg_crop_contours",
    # transform / imgtools (image -> image)
    "it_add_image_border", "it_crop_part", "it_crop_rectangle1", "it_change_format",
    "tf_log_polar", "tf_radon_sinogram",
    # deformation (image -> image)
    "deform_tps", "deform_ffd", "deform_mls",
]

# 各 op に与える 2 ノブ(conftest.KNOBS と同値の端点+中間)。
KNOBS = [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0), (0.15, 0.85)]


# --------------------------------------------------------------------------- #
# 契約検証ヘルパ(有限・宣言 out_sort と一致)。                                    #
# --------------------------------------------------------------------------- #
def assert_typed_finite(name: str, out, out_sort: str) -> None:
    if out_sort in ("image", "region"):
        assert isinstance(out, np.ndarray), f"{name}: expected ndarray, got {type(out).__name__}"
        assert out.ndim == 2, f"{name}: expected 2-D array, got {out.ndim}-D"
        assert np.issubdtype(out.dtype, np.floating), f"{name}: expected float dtype, got {out.dtype}"
        assert np.isfinite(out).all(), f"{name}: output has NaN/Inf"
        lo, hi = float(out.min()), float(out.max())
        assert -1e-9 <= lo and hi <= 1.0 + 1e-9, f"{name}: out of [0,1] range [{lo:.4g},{hi:.4g}]"
    elif out_sort == "contour":
        assert isinstance(out, dict), f"{name}: expected contour dict, got {type(out).__name__}"
        assert "cs" in out and "shape" in out, f"{name}: contour dict missing 'cs'/'shape'"
        assert isinstance(out["cs"], list), f"{name}: contour 'cs' is not a list"
        assert len(out["shape"]) == 2, f"{name}: contour 'shape' is not (H,W)"
        for c in out["cs"]:
            arr = np.asarray(c, np.float64)
            assert arr.ndim == 2 and arr.shape[1] == 2, f"{name}: sub-contour not (N,2)"
            assert np.isfinite(arr).all(), f"{name}: contour has NaN/Inf point"
    elif out_sort == "feature":
        arr = np.asarray(out, np.float64)
        assert arr.size >= 1, f"{name}: empty feature output"
        assert np.isfinite(arr).all(), f"{name}: feature has NaN/Inf"
    else:
        raise AssertionError(f"{name}: unexpected out_sort {out_sort!r}")


def same_output(a, b) -> bool:
    """2 出力がビット一致か(dict 輪郭 / 配列 / スカラを網羅)。"""
    if isinstance(a, dict):
        if not isinstance(b, dict):
            return False
        if tuple(a["shape"]) != tuple(b["shape"]):
            return False
        if len(a["cs"]) != len(b["cs"]):
            return False
        return all(np.array_equal(np.asarray(x), np.asarray(y)) for x, y in zip(a["cs"], b["cs"]))
    aa, bb = np.asarray(a), np.asarray(b)
    return aa.shape == bb.shape and np.array_equal(aa, bb)


# --------------------------------------------------------------------------- #
# 1) 全 op を実行し契約(有限・型・決定性)を検証する。                             #
# --------------------------------------------------------------------------- #
def exercise_all() -> int:
    assert len(OPS) == len(set(OPS)), "OPS list has duplicates"
    for name in OPS:
        assert name in ops._BY_NAME, f"{name}: not in registry"
        op = ops._BY_NAME[name]
        assert op.category in ("geometry", "xldgeom", "transform", "subpix", "deformation"), \
            f"{name}: category {op.category!r} is outside the target family"
        for a, b in KNOBS:
            # 決定性: 独立だが等価な入力を 2 度渡してビット一致を要求。
            out1 = op.fn(input_for(op.in_sort), a, b)
            out2 = op.fn(input_for(op.in_sort), a, b)
            assert_typed_finite(name, out1, op.out_sort)
            assert same_output(out1, out2), f"{name}: non-deterministic at a={a},b={b}"
    return len(OPS)


# --------------------------------------------------------------------------- #
# 2) 効果が既知の代表 op に強い GT + beat-the-null を課す。                        #
# --------------------------------------------------------------------------- #
def ground_truth_checks() -> int:
    BY = ops._BY_NAME
    gt = 0

    # (a) mirror_image: 鏡映は画素の置換 → 値の多重集合を保存し、かつ入力とは異なる。
    img = _image()
    for a in (0.0, 0.3, 0.7, 1.0):
        mir = BY["mirror_image"].fn(img.copy(), a, 0.5)
        assert np.array_equal(np.sort(mir.ravel()), np.sort(img.ravel())), \
            "mirror_image changed the pixel value multiset"
        assert not np.array_equal(mir, img), "mirror_image was a no-op (beat-the-null failed)"
    gt += 1

    # (b) transpose_region: 対合(2 回で元へ)かつ 1 回では変化する(=行列転置)。
    yy, xx = np.mgrid[0:48, 0:48]
    asym = (((yy - 24) ** 2 + (xx - 19) ** 2) < 10 ** 2).astype(np.float64)  # 非対称配置
    t1 = BY["transpose_region"].fn(asym.copy(), 0.5, 0.5)
    t2 = BY["transpose_region"].fn(t1.copy(), 0.5, 0.5)
    assert np.array_equal(t1, asym.T), "transpose_region != matrix transpose"
    assert np.array_equal(t2, asym), "transpose_region is not an involution"
    assert not np.array_equal(t1, asym), "transpose_region was a no-op (beat-the-null failed)"
    gt += 1

    # (c) deform_{tps,ffd,mls}: a=0 は恒等(差≈0)、a=0.8 では明確に変形(beat-null)。
    for nm in ("deform_tps", "deform_ffd", "deform_mls"):
        o0 = BY[nm].fn(img.copy(), 0.0, 0.5)
        o8 = BY[nm].fn(img.copy(), 0.8, 0.5)
        assert np.abs(o0 - img).max() < 1e-6, f"{nm}: a=0 is not the identity map"
        assert np.abs(o8 - img).mean() > 1e-2, f"{nm}: a=0.8 barely deforms (beat-the-null failed)"
    gt += 1

    # (d) sp_local_max_sub_pix: 単峰ガウスで峰位置を検出、平坦画像では 0 個(null)。
    r0, c0 = 20, 28
    bump = np.exp(-(((yy - r0) ** 2 + (xx - c0) ** 2) / (2 * 3.0 ** 2))).astype(np.float64)
    mx = BY["sp_local_max_sub_pix"].fn(bump, 0.2, 0.0)
    assert len(mx["cs"]) >= 1, "sp_local_max_sub_pix found no peak on a clear unimodal bump"
    pts = np.array([c[0] for c in mx["cs"]])
    nearest = float(np.min(np.hypot(pts[:, 0] - r0, pts[:, 1] - c0)))
    assert nearest < 1.0, f"sp_local_max_sub_pix peak {nearest:.2f}px from the true maximum"
    flat = np.full((48, 48), 0.4)
    assert len(BY["sp_local_max_sub_pix"].fn(flat, 0.2, 0.0)["cs"]) == 0, \
        "sp_local_max_sub_pix hallucinated maxima on a flat image (beat-the-null failed)"
    gt += 1

    # (e) xg_height_width_ratio: 既知 bbox(rows ptp=30, cols ptp=10)→ 縦横比 3.0。
    r_lo, r_hi, c_lo, c_hi = 10.0, 40.0, 10.0, 20.0
    top = np.column_stack([np.full(11, r_lo), np.linspace(c_lo, c_hi, 11)])
    bot = np.column_stack([np.full(11, r_hi), np.linspace(c_lo, c_hi, 11)])
    lef = np.column_stack([np.linspace(r_lo, r_hi, 11), np.full(11, c_lo)])
    rig = np.column_stack([np.linspace(r_lo, r_hi, 11), np.full(11, c_hi)])
    rect = {"shape": (50, 40), "cs": [np.vstack([top, rig, bot[::-1], lef[::-1]])]}
    ratio = float(BY["xg_height_width_ratio"].fn(rect, 0.5, 0.5))
    assert abs(ratio - 3.0) < 1e-6, f"xg_height_width_ratio={ratio:.4f}, expected 3.0"
    gt += 1

    # (f) xg_area_center: 一辺 20 の正方形 → 面積 400(シューレース)。
    sq = {"shape": (50, 50), "cs": [np.array([[10.0, 10.0], [10.0, 30.0], [30.0, 30.0],
                                               [30.0, 10.0], [10.0, 10.0]])]}
    area = float(BY["xg_area_center"].fn(sq, 0.5, 0.5))
    assert abs(area - 400.0) < 1e-6, f"xg_area_center={area:.4f}, expected 400.0"
    gt += 1

    # (g) xg_orientation: 対角線 → 45°(0.25)、水平線 → 0°(0.0)を識別(beat-null)。
    diag = {"shape": (50, 50), "cs": [np.column_stack([np.arange(5.0, 40.0), np.arange(5.0, 40.0)])]}
    horiz = {"shape": (50, 50), "cs": [np.column_stack([np.full(35, 20.0), np.arange(5.0, 40.0)])]}
    o_diag = float(BY["xg_orientation"].fn(diag, 0.0, 0.0))
    o_horiz = float(BY["xg_orientation"].fn(horiz, 0.0, 0.0))
    assert abs(o_diag - 0.25) < 1e-6, f"xg_orientation(diagonal)={o_diag:.4f}, expected 0.25"
    assert abs(o_horiz - 0.0) < 1e-6, f"xg_orientation(horizontal)={o_horiz:.4f}, expected 0.0"
    gt += 1

    return gt


def main() -> int:
    n = exercise_all()
    k = ground_truth_checks()
    assert n == len(OPS)
    print(f"PASS: {n} ops exercised, all finite/typed/deterministic; {k} GT checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
