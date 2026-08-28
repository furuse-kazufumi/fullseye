# -*- coding: utf-8 -*-
"""gallery2d_region — 2次元「領域(region)」オペレータ族を全て叩いて自己検証するギャラリー例。 (task: region ops family — exercise & validate)

【平たく言うと】
二値マスク(前景=1/背景=0 の 2 次元領域)に対して形を整える道具箱です。
収縮・膨張・開閉(モルフォロジー)、穴埋め、最大成分の抽出、細線化(スケルトン)、
境界抽出、距離変換、外接/内接図形、ランレングス特徴量 … といった HALCON 系の
「region / region-morphology / region-transform」オペレータを一望します。
用途は前処理後のマスク整形・ブロブ選別・形状計測(検査/OCR前処理/顕微鏡/医用など)。

【グラウンドトゥルース(GT)で嘘を弾く】
この族の *全* オペレータを実際に呼び出し、1 つずつ次の契約を機械検証します:
  - 出力が有限(NaN/Inf を含まない)。
  - 宣言された out_sort と一致する(region/image → [0,1] の 2 次元 float 配列、
    region はさらに二値 {0,1}、feature → 有限のスカラ/配列)。
  - 決定的(同じ入力・同じノブ → ビット同一の出力)。
1 つでも例外を投げたら黙って飛ばさず大声で FAIL します。
加えて、効果が既知の代表オペレータには「beat-the-null」な強い GT を課します
(膨張は面積を増やし収縮は減らす/穴埋めは面積を増やす/距離変換は中心が縁より高い/
境界は面積が桁で小さく元領域の部分集合/最大成分選択は小ブロブを消す/反転は厳密補集合)。

    py -3.11 examples/gallery2d_region.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402
import ops  # noqa: E402

# 対象 = ops.REGISTRY のうち category が region / region-morphology / region-transform の
# 全オペレータ。名前がソースに文字列リテラルとして現れる必要がある(op→example 索引用)。
OPS = [
    "reg_erode", "reg_dilate", "reg_open", "reg_close", "fill_holes",
    "select_largest", "remove_small", "invert_region", "dist_transform",
    "region_boundary", "convex_fill", "sk_skeleton", "sk_medial", "sk_convex",
    "sk_thin", "sk_remove_holes", "sk_clear_border", "sk_find_boundaries",
    "cv_dist", "erosion_circle", "dilation_circle", "opening_circle",
    "closing_circle", "erosion_rectangle1", "dilation_rectangle1",
    "opening_rectangle1", "closing_rectangle1", "fill_up", "boundary",
    "skeleton", "thinning", "shape_trans", "select_shape_std", "select_shape",
    "distance_transform", "pruning", "closest_point_transform",
    "junctions_skeleton", "erosion_golay", "dilation_golay", "opening_golay",
    "closing_golay", "erosion_seq", "dilation_seq", "morph_skeleton",
    "thinning_golay", "thinning_seq", "fill_up_shape", "remove_noise_region",
    "smallest_rectangle1", "get_region_contour", "get_region_convex",
    "xsp_chamfer_dist", "xsk2_isotropic_close", "xcv2_hitmiss", "xmh_majority",
    "xmh_bwperim", "xsk3_rank_majority", "r2_inner_circle", "r2_inner_rectangle1",
    "r2_smallest_rectangle1", "r2_smallest_circle", "r2_smallest_rectangle2",
    "r2_sort_region", "r2_union1", "r2_partition_rectangle",
    "r2_runlength_features", "r2_split_skeleton_lines", "r3_background_seg",
    "r3_clip_region", "r3_eliminate_runs", "r3_rank_region", "r3_region_features",
    "r3_runlength_distribution", "r3_select_region_point", "r3_partition_dynamic",
    "r3_polar_trans_region", "r3_label_to_region",
]

# ノブ (a,b) は [0,1]。決定性は 1 組で確認し、契約は複数組で確認する。
KNOBS = [(0.35, 0.65), (0.5, 0.5), (0.15, 0.85), (1.0, 1.0)]
_N = 48


def _rng():
    return np.random.default_rng(20260812)


def input_for(sort: str):
    """in_sort ごとに valid な入力を返す小さな工場(tests/conftest.py の構成を複製)。

    examples は tests/ から import 禁止なので、必要な bank をここに写経する。
    この族は全て in_sort='region' だが、他 sort も来ても壊れないよう用意する。
    """
    n = _N
    if sort == "region":
        yy, xx = np.mgrid[0:n, 0:n]
        return (((yy - n // 2) ** 2 + (xx - n // 2) ** 2) < (n * 0.25) ** 2).astype(np.float64)
    if sort in ("image", "any"):
        yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
        grad = xx / (n - 1)
        disk = ((yy - n * 0.35) ** 2 + (xx - n * 0.4) ** 2) < (n * 0.18) ** 2
        checker = ((xx.astype(int) // 6 + yy.astype(int) // 6) % 2) * 0.15
        return np.clip(0.35 * grad + 0.45 * disk + checker
                       + 0.03 * _rng().standard_normal((n, n)), 0, 1)
    if sort == "color":
        yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
        g = np.clip(xx / (n - 1), 0, 1)
        return np.clip(np.stack([g, 0.7 * g + 0.1, 1 - g], -1), 0, 1)
    if sort == "contour":
        sq = np.array([[6.0, 6.0], [6.0, 20.0], [20.0, 20.0], [20.0, 6.0], [6.0, 6.0]])
        return {"shape": (32, 32), "cs": [sq]}
    raise ValueError(f"input_for: 未対応の sort {sort!r}(この族には出ないはず)")


def _same(x, y) -> bool:
    """決定性判定: 配列はビット同一、dict は cs 同一、スカラは ==。"""
    if isinstance(x, np.ndarray) or isinstance(y, np.ndarray):
        xa, ya = np.asarray(x), np.asarray(y)
        if xa.shape != ya.shape:
            return False
        return bool(np.array_equal(xa, ya))
    if isinstance(x, dict) and isinstance(y, dict):
        cx, cy = x.get("cs", []), y.get("cs", [])
        return len(cx) == len(cy) and all(np.array_equal(a, b) for a, b in zip(cx, cy))
    return x == y


def _check_contract(name, op, out) -> None:
    """out が op.out_sort の契約を満たすか(有限・型・値域)を検証。違反は AssertionError。"""
    os_ = op.out_sort
    if os_ in ("region", "image"):
        assert isinstance(out, np.ndarray), f"{name}: out_sort={os_} だが ndarray でない ({type(out)})"
        assert out.ndim == 2, f"{name}: 2 次元でない (ndim={out.ndim})"
        assert np.issubdtype(out.dtype, np.floating), f"{name}: float 配列でない (dtype={out.dtype})"
        assert np.isfinite(out).all(), f"{name}: 非有限値(NaN/Inf)を含む"
        mn, mx = float(out.min()), float(out.max())
        assert -1e-9 <= mn and mx <= 1 + 1e-9, f"{name}: 値域 [0,1] 外 (min={mn}, max={mx})"
        if os_ == "region":
            uniq = np.unique(out)
            assert set(np.round(uniq, 9)).issubset({0.0, 1.0}), \
                f"{name}: region 出力が二値でない (unique[:5]={uniq[:5]})"
    elif os_ == "feature":
        arr = np.asarray(out, dtype=float)
        assert arr.size >= 1, f"{name}: feature が空"
        assert np.isfinite(arr).all(), f"{name}: feature に非有限値"
    else:
        raise AssertionError(f"{name}: 想定外の out_sort={os_!r}(この族は region/image/feature のみ)")


def main() -> int:
    BY = ops._BY_NAME

    # --- 名前集合が TARGET と一致することを確認(op→example 索引の健全性) --- #
    cats = ("region", "region-morphology", "region-transform")
    target = [o.name for o in ops.REGISTRY if o.category in cats]
    missing = sorted(set(target) - set(OPS))
    extra = sorted(set(OPS) - set(target))
    assert not missing, f"OPS に不足: {missing}"
    assert not extra, f"OPS に余分: {extra}"
    assert len(OPS) == len(set(OPS)), "OPS に重複あり"
    assert len(OPS) == len(target), f"件数不一致: OPS={len(OPS)} target={len(target)}"

    # --- 全オペレータを叩いて契約(有限/型/値域)+ 決定性を検証 --- #
    failed = []
    for name in OPS:
        op = BY[name]
        inp = input_for(op.in_sort)
        try:
            for (a, b) in KNOBS:
                out = op.fn(inp.copy() if isinstance(inp, np.ndarray) else dict(inp), a, b)
                _check_contract(name, op, out)
            # 決定性: 同一入力・同一ノブ → ビット同一
            a, b = KNOBS[0]
            o1 = op.fn(inp.copy(), a, b)
            o2 = op.fn(inp.copy(), a, b)
            assert _same(o1, o2), f"{name}: 非決定的(同一入力で出力が変化)"
        except Exception as e:  # 契約違反・例外は握りつぶさず記録して後で大声で落とす
            failed.append((name, f"{type(e).__name__}: {e}"))

    if failed:
        print("FAIL: 以下のオペレータが契約検証で落ちました:")
        for name, err in failed:
            print(f"  - {name}: {err}")
        return 1

    # --- 効果が既知の代表オペレータへ強い GT(beat-the-null)を課す --- #
    n = _N
    yy, xx = np.mgrid[0:n, 0:n]
    disk = (((yy - n // 2) ** 2 + (xx - n // 2) ** 2) < (n * 0.25) ** 2).astype(np.float64)
    disk_area = float(disk.sum())
    gt = 0

    # GT1 invert_region = 厳密な二値補集合。
    inv = BY["invert_region"].fn(disk.copy(), 0.5, 0.5)
    assert np.array_equal(inv > 0.5, disk <= 0.5), "invert_region が補集合になっていない"
    assert abs(inv.sum() - (n * n - disk_area)) < 1e-9, "invert_region の面積が補集合と一致しない"
    gt += 1

    # GT2 膨張は面積を増やし、収縮は減らす(単調 / beat-the-null: 元 disk と有意差)。
    dil = float(BY["reg_dilate"].fn(disk.copy(), 0.5, 0.5).sum())
    ero = float(BY["reg_erode"].fn(disk.copy(), 0.5, 0.5).sum())
    assert dil > disk_area > ero, f"膨張/収縮の面積順序が不正: dilate={dil} disk={disk_area} erode={ero}"
    assert dil > disk_area * 1.15 and ero < disk_area * 0.85, "膨張/収縮の変化量が小さすぎる(効いていない)"
    gt += 1

    # GT3 距離変換は領域中心が縁より高い(距離のピークが内側)。
    dt = BY["distance_transform"].fn(disk.copy(), 0.5, 0.5)
    center = float(dt[n // 2, n // 2])
    near_edge = float(dt[n // 2, n // 2 + int(n * 0.25) - 2])
    assert center > near_edge + 0.3, f"距離変換の中心({center:.3f})が縁({near_edge:.3f})より高くない"
    gt += 1

    # GT4 穴埋め: 内部に穴を空けた円環を埋めると面積が増え、中実円に戻る。
    annulus = disk.copy()
    annulus[(((yy - n // 2) ** 2 + (xx - n // 2) ** 2) < (n * 0.10) ** 2)] = 0.0
    ann_area = float(annulus.sum())
    filled = float(BY["fill_holes"].fn(annulus.copy(), 0.5, 0.5).sum())
    assert filled > ann_area, f"fill_holes が穴を埋めていない: {ann_area} -> {filled}"
    assert abs(filled - disk_area) < 1e-9, "fill_holes 後が中実円の面積に一致しない"
    gt += 1

    # GT5 境界抽出: 薄いリング(面積が桁で小さい)で、かつ元領域の部分集合。
    bnd = BY["region_boundary"].fn(disk.copy(), 0.5, 0.5)
    assert 0 < bnd.sum() < disk_area * 0.4, f"境界が薄いリングでない (sum={bnd.sum()}, disk={disk_area})"
    assert np.all((bnd > 0.5) <= (disk > 0.5)), "境界が元領域の部分集合になっていない"
    gt += 1

    # GT6 最大成分選択: 2 ブロブ(小+大)から小ブロブを消して大ブロブだけ残す。
    two = np.zeros((n, n))
    two[(((yy - 12) ** 2 + (xx - 12) ** 2) < 7 ** 2)] = 1.0    # 小
    large = (((yy - 32) ** 2 + (xx - 32) ** 2) < 11 ** 2)      # 大
    two[large] = 1.0
    sel = BY["select_largest"].fn(two.copy(), 0.5, 0.5)
    assert sel.sum() < two.sum(), "select_largest が何も削っていない"
    assert np.array_equal(sel > 0.5, large), "select_largest が大ブロブのみを残していない"
    gt += 1

    print(f"PASS: {len(OPS)} ops exercised, all finite/typed/deterministic; {gt} GT checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
