# -*- coding: utf-8 -*-
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gallery2d_morphology — モルフォロジー(形態学)op 一族を総なめで叩き、契約とGTで検証する (task: morphology-gallery)。

    py -3.11 examples/gallery2d_morphology.py

【平たく言うと】
モルフォロジー(数理形態学)は、画像の明るい/暗い塊の「形」を構造要素(SE, 近傍窓)で
削る・盛る操作の一族。基本は erosion(収縮=局所min)/ dilation(膨張=局所max)、その
合成が opening(小さな明点を消す)/ closing(小さな暗穴を埋める)。差分をとると
top-hat(SEより小さい明ディテール抽出)/ black-hat(暗ディテール抽出)/ morphological
gradient(境界応答=エッジ)になる。粒径解析・欠陥検出・照明ムラ補正・文字/血管抽出など
「特定サイズの構造だけ残す/消す」用途の土台。この op 一族(erode/dilate/open/close/
tophat/blackhat/gradient と、その skimage / OpenCV / scipy / 面積・直径・再構成・骨格
派生)を **全て** 実行し、数値で検証する。

【グラウンドトゥルース(数値で嘘を弾く)】
一族の全 op に対して普遍契約(有限・宣言 out_sort 一致・[0,1] 値域・決定性=同一入力で
ビット一致)を課す。加えて効果が理論的に既知の代表 op には強い GT + beat-the-null:
1. erosion は anti-extensive: 出力 <= 入力(全画素)かつ 平均が真に減る(平坦画像との差)。
2. dilation は extensive: 出力 >= 入力(全画素)かつ 平均が真に増える。
3. 順序律(同一 SE): erosion <= opening <= 入力 <= closing <= dilation(全画素)。
4. top-hat は SE より小さい明点を強く拾う: 小明点領域の応答 >> 平坦背景(beat-the-null)。
5. morphological gradient は境界で応答: エッジ帯の応答 >> 平坦内部(beat-the-null)。
6. black-hat は SE より小さい暗点を強く拾う: 小暗点領域の応答 >> 平坦背景(beat-the-null)。

全 op が in_sort='image'/out_sort='image'。SE サイズは knob a→(3,5,7,9) で最小 3 なので
どの knob でも必ず効果が出る(恒等ではない)。真値は SE と単調・順序律から決まる閉形式的性質。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402
import ops  # noqa: E402

BY = {o.name: o for o in ops.REGISTRY}
EPS = 1e-9


# --------------------------------------------------------------------------- #
# per-sort 入力ファクトリ（tests/conftest.py の bank 構築を複製。examples は     #
# tests/ から import 禁止のため、必要な sort の生成をここに写経する）。          #
# --------------------------------------------------------------------------- #
def _rng():
    return np.random.default_rng(20260812)


def input_for(sort: str):
    """in_sort に対応する妥当な入力を返す(conftest の canonical variant を複製)。"""
    n = 48
    if sort in ("image", "any"):
        yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
        grad = xx / (n - 1)
        disk = ((yy - n * 0.35) ** 2 + (xx - n * 0.4) ** 2) < (n * 0.18) ** 2
        checker = ((xx.astype(int) // 6 + yy.astype(int) // 6) % 2) * 0.15
        return np.clip(0.35 * grad + 0.45 * disk + checker
                       + 0.03 * _rng().standard_normal((n, n)), 0, 1)
    if sort == "region":
        yy, xx = np.mgrid[0:n, 0:n]
        return (((yy - n // 2) ** 2 + (xx - n // 2) ** 2) < (n * 0.25) ** 2).astype(np.float64)
    if sort == "color":
        g = input_for("image")
        return np.clip(np.stack([g, 0.7 * g + 0.1, 1 - g], -1), 0, 1)
    if sort == "contour":
        sq = np.array([[6.0, 6.0], [6.0, 20.0], [20.0, 20.0], [20.0, 6.0], [6.0, 6.0]])
        return {"shape": (32, 32), "cs": [sq]}
    if sort == "volume":
        zz, vy, vx = np.mgrid[0:8, 0:24, 0:24]
        return np.clip(0.5 + 0.3 * np.sin(vx / 3.0) * np.cos(vy / 4.0) * (zz / 8.0), 0, 1)
    raise ValueError(f"input_for: 未対応の sort {sort!r}")


def _gt_image():
    """GT 用の決定的画像: 平坦 + 縦エッジ + 小さな明点 + 小さな暗点(ノイズ無し)。"""
    g = np.full((48, 48), 0.3)
    g[:, 24:] = 0.7               # 列24に縦エッジ(0.3 -> 0.7)
    g[8:11, 8:11] = 0.95          # 左の平坦域に小さな明点(3x3, SE7 より小)
    g[38:41, 38:41] = 0.05        # 右の平坦域に小さな暗点(3x3)
    return g


# --------------------------------------------------------------------------- #
# TARGET: category=='morphology' の全 op（string literal で明示 = op→example 索引用）。
# --------------------------------------------------------------------------- #
OPS = [
    "gerode", "gdilate", "gopen", "gclose", "tophat", "bothat", "morph_grad",
    "sk_area_opening", "cv_open", "cv_close", "cv_tophat", "cv_gradient",
    "cv_blackhat", "cv_erode", "cv_dilate", "gray_erosion", "gray_dilation",
    "gray_opening", "gray_closing", "gray_opening_shape", "gray_closing_shape",
    "gray_tophat", "gray_bothat", "gray_erosion_shape", "gray_dilation_shape",
    "gray_opening_rect", "gray_closing_rect", "xsk2_reconstruction",
    "xsk2_diameter_opening", "xsk3_area_closing", "xsk3_diameter_closing",
    "f2_gray_skeleton", "f2_gray_inside",
]


def _assert_out_sort(name: str, out, out_sort: str) -> None:
    """宣言された out_sort に出力が一致することを検証(この一族は全て image)。"""
    if out_sort in ("image", "region"):
        a = np.asarray(out, float)
        assert a.ndim == 2, f"{name}: out_sort={out_sort} だが ndim={a.ndim}(2-D 期待)"
        assert np.isfinite(a).all(), f"{name}: 非有限値(NaN/Inf)を含む"
        assert a.min() >= -EPS and a.max() <= 1 + EPS, \
            f"{name}: 値域外 [{a.min():.4g},{a.max():.4g}](image/region は [0,1] 期待)"
    elif out_sort == "contour":
        assert isinstance(out, dict) and "cs" in out, f"{name}: contour は 'cs' 付き dict 期待"
    elif out_sort == "feature":
        a = np.asarray(out, float)
        assert np.isfinite(a).all(), f"{name}: feature が非有限"
    else:
        raise AssertionError(f"{name}: 未知の out_sort {out_sort!r}")


def main() -> int:
    # --- 事前健全性: OPS が TARGET(registry の morphology 全 op)と厳密一致 ---
    target = [o.name for o in ops.REGISTRY if o.category == "morphology"]
    assert set(OPS) == set(target), \
        f"OPS が morphology カテゴリと不一致: 欠={set(target)-set(OPS)} 余={set(OPS)-set(target)}"
    assert len(OPS) == len(set(OPS)) == len(target), "OPS に重複、または TARGET と件数不一致"

    # --- 全 op 普遍契約: 有限 / out_sort 一致 / [0,1] / 決定性(ビット一致) ---
    for name in OPS:
        op = BY[name]
        x = input_for(op.in_sort)
        try:
            o1 = op.fn(input_for(op.in_sort), 0.5, 0.5)
            o2 = op.fn(input_for(op.in_sort), 0.5, 0.5)
        except Exception as e:  # 落ちた op は握りつぶさず大声で失敗
            raise AssertionError(f"op {name!r} が例外を送出: {type(e).__name__}: {e}") from e
        _assert_out_sort(name, o1, op.out_sort)
        a1, a2 = np.asarray(o1, float), np.asarray(o2, float)
        assert a1.shape == a2.shape and np.array_equal(a1, a2), \
            f"{name}: 非決定的(同一入力で出力がビット不一致)"
    print(f"契約OK: {len(OPS)} op すべて 有限 / out_sort 一致 / [0,1] / 決定的。")

    # --- 強い GT + beat-the-null(効果が理論的に既知の代表 op)---
    gt = _gt_image()
    gt_checks = 0

    # 1. erosion は anti-extensive(出力 <= 入力)かつ平均が真に減る
    er = np.asarray(BY["gerode"].fn(gt.copy(), 0.0, 0.0))   # SE 3x3
    assert (er <= gt + EPS).all(), "gerode: anti-extensive 違反(出力 > 入力の画素あり)"
    assert er.mean() < gt.mean() - 1e-4, "gerode: 平均が減っていない(効果なし=null)"
    gt_checks += 1

    # 2. dilation は extensive(出力 >= 入力)かつ平均が真に増える
    di = np.asarray(BY["gdilate"].fn(gt.copy(), 0.0, 0.0))
    assert (di >= gt - EPS).all(), "gdilate: extensive 違反(出力 < 入力の画素あり)"
    assert di.mean() > gt.mean() + 1e-4, "gdilate: 平均が増えていない(効果なし=null)"
    gt_checks += 1

    # 3. 順序律(同一 SE): erosion <= opening <= 入力 <= closing <= dilation
    op_ = np.asarray(BY["gopen"].fn(gt.copy(), 0.0, 0.0))
    cl = np.asarray(BY["gclose"].fn(gt.copy(), 0.0, 0.0))
    assert (er <= op_ + EPS).all() and (op_ <= gt + EPS).all() \
        and (gt <= cl + EPS).all() and (cl <= di + EPS).all(), \
        "morphology 順序律違反: erosion<=opening<=in<=closing<=dilation が破れた"
    gt_checks += 1

    # 4. top-hat: SE より小さい明点を強く拾う(小明点領域 >> 平坦背景)
    th = np.asarray(BY["tophat"].fn(gt.copy(), 0.5, 0.0))    # SE 7x7 > 3x3 明点
    th_spot = th[8:11, 8:11].mean()
    th_flat = th[18:30, 30:40].mean()                        # 特徴の無い平坦域
    assert th_spot > th_flat + 0.1, \
        f"tophat: 小明点応答が平坦背景を上回らない(spot={th_spot:.3f} flat={th_flat:.3f})"
    gt_checks += 1

    # 5. morphological gradient: 境界で応答(エッジ帯 >> 平坦内部)
    mg = np.asarray(BY["morph_grad"].fn(gt.copy(), 0.0, 0.0))  # SE 3x3
    mg_edge = mg[15:35, 22:27].mean()                        # 列24 エッジ周辺(明暗点を避けた行)
    mg_interior = mg[18:30, 30:40].mean()                    # 平坦内部
    assert mg_edge > mg_interior + 0.1, \
        f"morph_grad: エッジ応答が平坦内部を上回らない(edge={mg_edge:.3f} interior={mg_interior:.3f})"
    gt_checks += 1

    # 6. black-hat: SE より小さい暗点を強く拾う(小暗点領域 >> 平坦背景)
    bh = np.asarray(BY["bothat"].fn(gt.copy(), 0.5, 0.0))
    bh_spot = bh[38:41, 38:41].mean()
    bh_flat = bh[18:28, 30:37].mean()
    assert bh_spot > bh_flat + 0.1, \
        f"bothat: 小暗点応答が平坦背景を上回らない(spot={bh_spot:.3f} flat={bh_flat:.3f})"
    gt_checks += 1

    print(f"PASS: {len(OPS)} ops exercised, all finite/typed/deterministic; {gt_checks} GT checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
