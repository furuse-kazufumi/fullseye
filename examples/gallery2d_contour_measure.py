# -*- coding: utf-8 -*-
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gallery2d_contour_measure — 輪郭・1次元計測・テンプレート照合の 2D op 一族を総なめ検証する。(task: gallery/contract)

【平たく言うと(この一族は何のためのop群か)】
この例は Fullseye の 2D オペレータ registry のうち category が
``contour`` / ``measure1d`` / ``matching`` の op を **全て** 1 本で実行して検証する。
- contour  … 画像から下位画素(sub-pixel)輪郭を抽出し、選別・平滑・幾何変換・領域化する
              XLD 系(HALCON 流の eXtended Line Description)輪郭処理。
- measure1d … 計測線(measure rectangle/arc)に沿って輝度プロファイルを取り、
              エッジ位置・エッジ対・しきい値交差数を測る 1 次元計測。
- matching … テンプレート(NCC/形状)を画像内で探し出す照合。

【グラウンドトゥルース(GT: 数値で嘘を弾く)】
すべての op について「有限(NaN/Inf なし)」「宣言された out_sort に一致
(image/region → [0,1] の 2次元 float、contour → dict、feature/match → 有限スカラ/配列)」
「決定的(同一入力 → ビット一致)」を assert する。加えて代表 6 op には効果が既知の
**強い GT + beat-the-null**(平坦画像ではエッジが立たない/計測が 0、輪郭→領域は 2値で
面積>0、計測射影は入力の定数値を復元、など)を課す。例外を投げた op は握り潰さず
即座に大声で失敗させる(silent skip 禁止)。

【この例が検証すること】
一族の **全 op** を実際に呼び、上記の契約(finite / typed / deterministic)+ 6 件の
挙動 GT を満たすことを確認する。1 つでも破れれば非ゼロ終了する本物の検査。

    py -3.11 examples/gallery2d_contour_measure.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402
import ops  # noqa: E402

BY = {o.name: o for o in ops.REGISTRY}  # name -> op（重複名は登録順で上書き=RT/_BY_NAME と同じ正準解決）


# --------------------------------------------------------------------------- #
# 入力ファクトリ — tests/conftest.py の各 sort バンクを最小複製（examples は     #
# tests/ を import しない規約のため、有効入力の作り方をここに写し取る）。         #
#   image  = [0,1] の 2次元 float / region = 2値っぽい 2次元 / color = HxWx3 /   #
#   contour = {'shape':(H,W), 'cs':[ (N,2) 点列, ... ]}                          #
# 決定的にするため seed を固定（conftest と同じ 20260812）。                      #
# --------------------------------------------------------------------------- #
_N = 48
_SEED = 20260812


def _image(n: int = _N) -> np.ndarray:
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    grad = xx / (n - 1)
    disk = ((yy - n * 0.35) ** 2 + (xx - n * 0.4) ** 2) < (n * 0.18) ** 2
    checker = ((xx.astype(int) // 6 + yy.astype(int) // 6) % 2) * 0.15
    rng = np.random.default_rng(_SEED)
    return np.clip(0.35 * grad + 0.45 * disk + checker + 0.03 * rng.standard_normal((n, n)), 0, 1)


def _region(n: int = _N) -> np.ndarray:
    yy, xx = np.mgrid[0:n, 0:n]
    return (((yy - n // 2) ** 2 + (xx - n // 2) ** 2) < (n * 0.25) ** 2).astype(np.float64)


def _color(n: int = _N) -> np.ndarray:
    g = _image(n)
    return np.clip(np.stack([g, 0.7 * g + 0.1, 1 - g], -1), 0, 1)


def _square_contour() -> dict:
    sq = np.array([[6.0, 6.0], [6.0, 20.0], [20.0, 20.0], [20.0, 6.0], [6.0, 6.0]])
    return {"shape": (32, 32), "cs": [sq]}


def input_for(sort: str):
    """sort に対応する有効入力を返す（毎回新規生成 = 呼び出し側が破壊しても安全）。"""
    if sort == "image":
        return _image()
    if sort == "region":
        return _region()
    if sort == "color":
        return _color()
    if sort == "contour":
        return _square_contour()
    raise KeyError(f"入力ファクトリが未対応の in_sort: {sort!r}")


def _copy_input(x):
    """conftest.copy_input と同じく、dict(contour) と ndarray を深めにコピー。"""
    if isinstance(x, dict):
        return {"shape": x["shape"], "cs": [np.array(c, copy=True) for c in x["cs"]]}
    return np.array(x, copy=True)


# --------------------------------------------------------------------------- #
# TARGET op 名 — 明示的な文字列リテラル一覧（op→example 逆引き索引のため、       #
# 各 op 名がソースに literally 出現する）。category ∈ {contour, measure1d,        #
# matching} の distinct な op 全 32 件（registry の raw 件数は 33 だが            #
# edges_sub_pix が core + backend override の二重登録で、_BY_NAME は最後=正準の   #
# 1 つに解決するため distinct は 32）。                                          #
# --------------------------------------------------------------------------- #
OPS = [
    "edges_sub_pix",                 # image -> contour   下位画素エッジ抽出（Canny系のsub-pixel）
    "select_contours",               # contour -> contour 長さ等で輪郭を選別
    "smooth_contours",               # contour -> contour 輪郭を平滑化
    "fit_line_contours",             # contour -> contour 輪郭を直線当てはめ
    "contours_to_region",            # contour -> region  輪郭を領域(2値)へ
    "ncc_locate",                    # image -> match     正規化相互相関でテンプレ位置
    "shape_locate",                  # image -> match     形状ベース照合で位置
    "sk_find_contours",              # image -> contour   等高線抽出(marching squares)
    "lines_gauss",                   # image -> contour   Steger 線抽出(Gauss微分)
    "select_contours_xld",           # contour -> contour XLD 輪郭の選別
    "smooth_contours_xld",           # contour -> contour XLD 輪郭の平滑
    "gen_region_contour_xld",        # contour -> region  XLD 輪郭 → 領域
    "close_contours_xld",            # contour -> contour 開輪郭を閉じる
    "affine_trans_contour_xld",      # contour -> contour アフィン変換
    "projective_trans_contour_xld",  # contour -> contour 射影変換
    "polar_trans_contour_xld",       # contour -> contour 極座標変換
    "shape_trans_xld",               # contour -> contour 形状変換(凸包/外接矩形等)
    "threshold_sub_pix",             # image -> contour   下位画素しきい値輪郭
    "zero_crossing_sub_pix",         # image -> contour   ゼロ交差(LoG)輪郭
    "lines_facet",                   # image -> contour   facet モデル線抽出
    "gen_region_polygon_xld",        # contour -> region  多角形塗り → 領域
    "affine_trans_polygon_xld",      # contour -> contour 多角形のアフィン変換
    "gen_contour_region_xld",        # region -> contour  領域境界 → 輪郭
    "select_shape_xld",              # contour -> contour 形状特徴で輪郭選別
    "contour_point_num_xld",         # contour -> feature 輪郭点数
    "edges_color_sub_pix",           # color -> contour   カラー下位画素エッジ
    "lines_color",                   # color -> contour   カラー線抽出
    "m1_measure_projection",         # image -> feature   計測線上の輝度射影(平均)
    "m1_measure_pos",                # image -> contour   計測線上のエッジ位置
    "m1_measure_thresh",             # image -> feature   しきい値交差数
    "m1_measure_pairs",              # image -> feature   エッジ対の数
    "m1_fuzzy_measure_pos",          # image -> contour   ファジー計測のエッジ位置
]


# --------------------------------------------------------------------------- #
# 契約チェック用ヘルパ（finite / typed / deterministic）                        #
# --------------------------------------------------------------------------- #
def _assert_finite_and_typed(name: str, out, out_sort: str) -> None:
    if out_sort == "contour":
        assert isinstance(out, dict), f"{name}: contour は dict のはず、実際 {type(out).__name__}"
        assert "cs" in out and "shape" in out, f"{name}: contour dict に 'shape'/'cs' が無い: {list(out)}"
        assert len(out["shape"]) == 2, f"{name}: contour shape は 2 次元のはず: {out['shape']}"
        for c in out["cs"]:
            arr = np.asarray(c, dtype=np.float64)
            assert np.isfinite(arr).all(), f"{name}: 輪郭点に NaN/Inf"
            if arr.size:
                assert arr.ndim == 2 and arr.shape[-1] == 2, f"{name}: 輪郭点は (N,2) のはず: {arr.shape}"
    elif out_sort == "region":
        arr = np.asarray(out, dtype=np.float64)
        assert arr.ndim == 2, f"{name}: region は 2 次元 float のはず: shape={arr.shape}"
        assert np.isfinite(arr).all(), f"{name}: region に NaN/Inf"
        assert arr.min() >= -1e-9 and arr.max() <= 1 + 1e-9, \
            f"{name}: region 値域は [0,1] のはず: [{arr.min()},{arr.max()}]"
    elif out_sort in ("feature", "match"):
        arr = np.asarray(out, dtype=np.float64)
        assert np.isfinite(arr).all(), f"{name}: {out_sort} に NaN/Inf: {out}"
    else:
        raise AssertionError(f"{name}: この例が想定しない out_sort={out_sort!r}")


def _equal(a, b) -> bool:
    """dict(contour) を含めてビット一致で比較。"""
    if isinstance(a, dict) or isinstance(b, dict):
        if not (isinstance(a, dict) and isinstance(b, dict)):
            return False
        if list(a.keys()) != list(b.keys()) or a["shape"] != b["shape"]:
            return False
        if len(a["cs"]) != len(b["cs"]):
            return False
        return all(np.array_equal(np.asarray(x), np.asarray(y)) for x, y in zip(a["cs"], b["cs"]))
    return np.array_equal(np.asarray(a), np.asarray(b))


def _npts(contour_dict: dict) -> int:
    return int(sum(len(c) for c in contour_dict["cs"]))


# --------------------------------------------------------------------------- #
# 代表 6 op の強い GT + beat-the-null                                           #
# --------------------------------------------------------------------------- #
def _ground_truth_checks() -> int:
    checks = 0

    # GT1: contours_to_region — 閉じた正方形輪郭は「2値」領域になり画素>0。
    #       beat-the-null: 空輪郭は 0 画素 → 入力に応じて領域が生まれる。
    sq = _square_contour()
    reg = np.asarray(BY["contours_to_region"].fn(_copy_input(sq), 0.5, 0.5), dtype=np.float64)
    assert set(np.unique(reg).tolist()).issubset({0.0, 1.0}), "contours_to_region は 2値領域のはず"
    n_sq = float(reg.sum())
    n_empty = float(np.asarray(
        BY["contours_to_region"].fn({"shape": (32, 32), "cs": []}, 0.5, 0.5), dtype=np.float64).sum())
    assert n_sq > 0 and n_empty == 0 and n_sq > n_empty, \
        f"contours_to_region beat-null 失敗: 正方形={n_sq} 空={n_empty}"
    checks += 1

    # GT2: gen_region_contour_xld — XLD 輪郭も同様に 2値領域化、空は 0。
    reg2 = np.asarray(BY["gen_region_contour_xld"].fn(_copy_input(sq), 0.5, 0.5), dtype=np.float64)
    assert set(np.unique(reg2).tolist()).issubset({0.0, 1.0}), "gen_region_contour_xld は 2値のはず"
    n2 = float(reg2.sum())
    n2e = float(np.asarray(
        BY["gen_region_contour_xld"].fn({"shape": (32, 32), "cs": []}, 0.5, 0.5), dtype=np.float64).sum())
    assert n2 > 0 and n2e == 0, f"gen_region_contour_xld beat-null 失敗: 正方形={n2} 空={n2e}"
    checks += 1

    # GT3: edges_sub_pix — 構造のある画像ではエッジが立ち、平坦画像では 1 点も出ない。
    img = _image()
    flat = np.full((_N, _N), 0.42)
    e_img = _npts(BY["edges_sub_pix"].fn(np.array(img, copy=True), 0.5, 0.5))
    e_flat = _npts(BY["edges_sub_pix"].fn(np.array(flat, copy=True), 0.5, 0.5))
    assert e_img > 20 and e_flat == 0, f"edges_sub_pix beat-null 失敗: 画像={e_img} 平坦={e_flat}"
    checks += 1

    # GT4: threshold_sub_pix — 同上（しきい値輪郭）。平坦では輪郭 0。
    t_img = _npts(BY["threshold_sub_pix"].fn(np.array(img, copy=True), 0.5, 0.5))
    t_flat = _npts(BY["threshold_sub_pix"].fn(np.array(flat, copy=True), 0.5, 0.5))
    assert t_img > 0 and t_flat == 0, f"threshold_sub_pix beat-null 失敗: 画像={t_img} 平坦={t_flat}"
    checks += 1

    # GT5: m1_measure_thresh — 計測線上のしきい値交差数。平坦画像では交差 0（beat-null）。
    c_img = float(BY["m1_measure_thresh"].fn(np.array(img, copy=True), 0.5, 0.5))
    c_flat = float(BY["m1_measure_thresh"].fn(np.array(flat, copy=True), 0.5, 0.5))
    assert c_img >= 1 and c_flat == 0, f"m1_measure_thresh beat-null 失敗: 画像={c_img} 平坦={c_flat}"
    checks += 1

    # GT6: m1_measure_projection — 計測線上の輝度射影は「入力の定数値」を復元する。
    #       beat-the-null: 出力が入力に依らず一定なら差は 0 になるはず → 実際は入力を追う。
    p_lo = float(BY["m1_measure_projection"].fn(np.full((_N, _N), 0.2), 0.5, 0.5))
    p_hi = float(BY["m1_measure_projection"].fn(np.full((_N, _N), 0.8), 0.5, 0.5))
    assert abs(p_lo - 0.2) < 0.05 and abs(p_hi - 0.8) < 0.05, \
        f"m1_measure_projection は定数を復元するはず: 0.2->{p_lo} 0.8->{p_hi}"
    assert (p_hi - p_lo) > 0.5, f"m1_measure_projection beat-null 失敗: 入力に反応せず (Δ={p_hi - p_lo})"
    checks += 1

    return checks


# --------------------------------------------------------------------------- #
def main() -> int:
    # registry の TARGET set を再計算し、OPS が過不足なく一致するか自己検証。
    cats = ("contour", "measure1d", "matching")
    target = []
    for o in ops.REGISTRY:
        if o.category in cats and o.name not in target:
            target.append(o.name)
    missing = sorted(set(target) - set(OPS))
    extra = sorted(set(OPS) - set(target))
    assert not missing, f"OPS が TARGET を取りこぼし: {missing}"
    assert not extra, f"OPS に TARGET 外の名前: {extra}"
    assert len(OPS) == len(set(OPS)) == len(target), \
        f"件数不一致: OPS={len(OPS)} unique={len(set(OPS))} target={len(target)}"

    failures = []
    for name in OPS:
        op = ops._BY_NAME[name]
        x = input_for(op.in_sort)
        try:
            out1 = op.fn(_copy_input(x), 0.5, 0.5)
        except Exception as e:  # 例外は握り潰さず記録して大声で失敗させる
            failures.append(f"{name}: RAISED {type(e).__name__}: {e}")
            continue
        # 契約1: 有限 + 宣言 out_sort に一致
        _assert_finite_and_typed(name, out1, op.out_sort)
        # 契約2: 決定的（同一入力 → ビット一致）
        out2 = op.fn(_copy_input(x), 0.5, 0.5)
        assert _equal(out1, out2), f"{name}: 非決定的（同一入力で出力が異なる）"

    if failures:
        raise SystemExit("FAIL: 例外を投げた op があります:\n  " + "\n  ".join(failures))

    n_gt = _ground_truth_checks()

    print(f"PASS: {len(OPS)} ops exercised, all finite/typed/deterministic; {n_gt} GT checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
