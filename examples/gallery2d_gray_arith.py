# -*- coding: utf-8 -*-
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gallery2d_gray_arith — 濃淡・階調変換・算術・定義域(domain)op 一族を総なめで叩き、契約を検証する。 (task: gray_arithmetic)

    py -3.11 examples/gallery2d_gray_arith.py

【平たく言うと(この op 族は何のためのもの)】
画像の「明るさ・コントラスト・階調」を作り替える単項の点/近傍変換の一族。
- gray / intensity-transform … ガンマ・反転・シグモイド・ヒストグラム平坦化・CLAUDE… もとい CLAHE 等の階調曲線。
- arithmetic … 画素値そのものへ数学関数を掛ける(sqrt/log/exp/sin/pow/ビット演算…)。
- domain … 画像の「定義域(有効領域)」を広げる/切り出す・ビット面操作など。
いずれも入力 image(2-D float, [0,1])を受け、同型の image を返す「1 枚 → 1 枚」の変換。

【グラウンドトゥルース(数値で嘘を弾く)】
族の全 op について、族不変条件(image→image)+ op 契約を機械検証する:
  1. 出力は 2-D の float ndarray で、入力と同じ形状(この族は形状保存)。
  2. 有限(NaN/Inf なし)。強度画像なので非負、かつ暴走しない(min≥0, max≤2; 対数系の
     わずかな 1.0 超えは許容)。
  3. 決定的(同じ入力→ビット同一出力。進化の holdout 採点が依存する)。
さらに効果が既知の代表 6 op には強い GT + beat-the-null を課す(単に「動く」で終わらせない):
  invert=1-x / cv_trunc=min(x,閾) / it_bit_rshift は暗くする / equ_histo_image は単調かつ
  コントラスト増 / sk_adjust_log は暗部を持ち上げる / scale_clip はフルレンジへ引き伸ばす。

族の **全 op** を明示リスト OPS(op→example 索引のため名前を逐語で列挙)で回し、
1 つでも例外を投げたら握り潰さず大声で落ちる。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import warnings  # noqa: E402

import numpy as np  # noqa: E402

import ops  # noqa: E402

warnings.filterwarnings("ignore")  # backend の境界/非推奨警告は本題でないので黙らせる

BY = ops._BY_NAME  # name -> Op

# 検証対象カテゴリ(このファイルが担当する op 族)。
TARGET_CATS = {"gray", "intensity-transform", "arithmetic", "domain"}

# --------------------------------------------------------------------------- #
# 族の全 op を、名前の文字列リテラルとして明示列挙(op→example 索引が拾えるように)。 #
# 末尾で ops.REGISTRY から算出した実集合と厳密一致することを assert する。            #
# --------------------------------------------------------------------------- #
OPS = [
    # gray / intensity-transform(階調曲線・コントラスト強調)
    "gamma", "invert", "scale_clip", "equalize", "sigmoid", "clahe",
    "sk_adapthist", "sk_enhance_contrast", "sk_autolevel", "sk_adjust_log",
    "cv_clahe", "cv_trunc",
    # arithmetic(画素値への数学関数・ビット演算)
    "abs_image", "sqrt_image", "exp_image", "log_image", "sin_image",
    "cos_image", "asin_image", "acos_image", "atan_image", "gamma_image",
    "pow_image", "invert_image", "scale_image", "equ_histo_image",
    "illuminate", "scale_image_max", "equ_histo_image_rect", "tan_image",
    "bit_not", "monotony",
    # 拡張(xcv/xpil/xsp/xmh/xsk3/xkor …)
    "xcv_detail_enhance", "xpil_edge_enhance", "xpil_detail", "xpil_posterize",
    "xpil_solarize", "xpil_autocontrast", "xpil_contrast", "xsp_detrend_flatten",
    "xmh_soft", "xsk3_rank_subtract_mean", "xsk3_rank_equalize",
    "xsk3_integral_image", "xkor_clahe",
    # f2 / it(LUT・ビット面・定義域 domain 操作)
    "f2_lut_trans", "f2_expand_domain", "f2_bit_slice",
    "it_bit_lshift", "it_bit_rshift", "it_bit_mask", "it_convert_image_type",
    "it_full_domain", "it_crop_domain",
]

# 各 op を 4 通りの knob で叩く(finite/determinism を複数点で確かめる)。
KNOBS = [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0), (0.15, 0.85)]


def _base_image(n: int = 48) -> np.ndarray:
    """conftest.image_bank()['normal'] と同一構成の代表 image(2-D float in [0,1])。

    勾配 + 円板 + 市松 + 微小ノイズ。決定的(固定 seed)。
    """
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    grad = xx / (n - 1)
    disk = ((yy - n * 0.35) ** 2 + (xx - n * 0.4) ** 2) < (n * 0.18) ** 2
    checker = ((xx.astype(int) // 6 + yy.astype(int) // 6) % 2) * 0.15
    rng = np.random.default_rng(20260812)
    return np.clip(0.35 * grad + 0.45 * disk + checker + 0.03 * rng.standard_normal((n, n)), 0, 1)


# 基準画像は一度だけ作り、以後は copy を配る(op が in-place 変更しても汚染しない)。
_IMG = _base_image()


def input_for(sort: str):
    """conftest の各 sort の代表入力を複製して返す(この族は 'image' のみを使う)。

    op が入力を破壊しても呼び出し間で干渉しないよう、毎回まっさらな配列を返す。
    他 sort も conftest の構成に倣って用意してある(将来 in_sort が増えても壊れないように)。
    """
    if sort == "image":
        return _IMG.copy()
    if sort == "region":
        n = 48
        yy, xx = np.mgrid[0:n, 0:n]
        return (((yy - n // 2) ** 2 + (xx - n // 2) ** 2) < (n * 0.25) ** 2).astype(np.float64)
    if sort == "color":
        g = _IMG
        return np.clip(np.stack([g, 0.7 * g + 0.1, 1 - g], -1), 0, 1)
    if sort == "contour":
        sq = np.array([[6.0, 6.0], [6.0, 20.0], [20.0, 20.0], [20.0, 6.0], [6.0, 6.0]])
        return {"shape": (32, 32), "cs": [sq]}
    if sort == "volume":
        zz, vy, vx = np.mgrid[0:8, 0:24, 0:24]
        return np.clip(0.5 + 0.3 * np.sin(vx / 3.0) * np.cos(vy / 4.0) * (zz / 8.0), 0, 1)
    raise ValueError(f"input_for: 未対応 sort {sort!r}(この族には現れないはず)")


def exercise_all() -> int:
    """族の全 op を叩き、契約(有限・型・形状・定義域・決定性)を assert する。

    例外を投げた op は握り潰さず即座に AssertionError として噴き上げる。
    """
    ref_shape = _IMG.shape
    for name in OPS:
        assert name in BY, f"未知の op 名: {name}(レジストリに無い)"
        op = BY[name]
        # 族不変条件: この族は宣言上すべて image -> image。
        assert op.category in TARGET_CATS, f"{name}: category {op.category!r} が対象外"
        assert op.in_sort == "image" and op.out_sort == "image", (
            f"{name}: この族は image->image のはずが {op.in_sort}->{op.out_sort}")

        for a, b in KNOBS:
            try:
                out = op.fn(input_for(op.in_sort), a, b)
            except Exception as e:  # noqa: BLE001 — 落ちた op は隠さず大声で失敗させる
                raise AssertionError(f"{name} が knob ({a},{b}) で例外: {type(e).__name__}: {e}") from e

            # 宣言 out_sort=image に一致: 2-D の float ndarray、入力と同形状(形状保存の族)。
            assert isinstance(out, np.ndarray), f"{name}: 出力が ndarray でない ({type(out)})"
            assert out.ndim == 2, f"{name}: 出力が 2-D でない (ndim={out.ndim})"
            assert np.issubdtype(out.dtype, np.floating), f"{name}: 出力 dtype が float でない ({out.dtype})"
            assert out.shape == ref_shape, f"{name}: 形状 {out.shape} != 入力 {ref_shape}"
            # 有限。
            assert np.isfinite(out).all(), (
                f"{name}: 非有限値 {int((~np.isfinite(out)).sum())} 個 (knob {a},{b})")
            # 定義域: 強度画像は非負・暴走しない(対数系のわずかな 1.0 超えは許容し max<=2)。
            amin, amax = float(out.min()), float(out.max())
            assert amin >= -1e-6, f"{name}: 負の強度 min={amin} (knob {a},{b})"
            assert amax <= 2.0 + 1e-6, f"{name}: 強度が暴走 max={amax} (knob {a},{b})"
            # 決定的: 同じ入力・同じ knob → ビット同一。
            again = op.fn(input_for(op.in_sort), a, b)
            assert np.array_equal(out, again, equal_nan=True), (
                f"{name}: 非決定的(同一入力で出力が変わった, knob {a},{b})")

    return len(OPS)


def ground_truth_checks() -> int:
    """効果が既知の代表 op へ、強い GT + beat-the-null(恒等コピーでは通らない検査)。"""
    img = _IMG
    k = 0

    # 1. invert: 出力は 1 - 入力(点反転)。null=恒等コピーは相関 +1、反転は -1。
    o = np.asarray(BY["invert"].fn(img.copy(), 0.5, 0.5))
    assert np.allclose(o, 1.0 - img, atol=1e-9), "invert が 1-x になっていない"
    assert np.corrcoef(o.ravel(), img.ravel())[0, 1] < -0.99, "invert が入力と反相関でない(beat-null)"
    k += 1

    # 2. cv_trunc: 閾値での切り詰め out=min(x, 閾)。恒等でなく本当に頭を刈っている。
    o = np.asarray(BY["cv_trunc"].fn(img.copy(), 0.5, 0.5))
    thr = float(o.max())
    assert np.allclose(o, np.minimum(img, thr), atol=1e-9), "cv_trunc が min(x,閾) でない"
    assert np.all(o <= img + 1e-9), "cv_trunc が値を増やしている(切り詰めでない)"
    assert thr < float(img.max()) - 0.05, "cv_trunc が実際には切り詰めていない(beat-null)"
    k += 1

    # 3. it_bit_rshift: 右シフトは強度を下げる。null=恒等は平均不変、右シフトは半減以下。
    o = np.asarray(BY["it_bit_rshift"].fn(img.copy(), 0.5, 0.5))
    assert np.all(o <= img + 1e-9), "it_bit_rshift が値を増やしている(暗くならない)"
    assert o.mean() < 0.5 * img.mean(), "it_bit_rshift の暗化が弱い(beat-null: 平均が半減未満)"
    k += 1

    # 4. equ_histo_image: ヒストグラム平坦化は入力に対し単調非減少 + コントラスト増。
    o = np.asarray(BY["equ_histo_image"].fn(img.copy(), 0.5, 0.5))
    order = np.argsort(img, axis=None, kind="stable")
    sorted_out = o.ravel()[order]
    assert np.all(np.diff(sorted_out) >= -1e-9), "equ_histo_image が単調でない(順位が入れ替わった)"
    assert o.std() > 1.2 * img.std(), "equ_histo_image でコントラストが増えていない(beat-null)"
    k += 1

    # 5. sk_adjust_log: 対数補正は暗部を持ち上げる。null=恒等は平均不変、log は明るくなる。
    o = np.asarray(BY["sk_adjust_log"].fn(img.copy(), 0.5, 0.5))
    assert o.mean() > img.mean() + 0.05, "sk_adjust_log が明るくしていない(beat-null)"
    k += 1

    # 6. scale_clip: min-max 引き伸ばしでフルレンジ [0,1] へ。null=恒等は元レンジ(<1)のまま。
    o = np.asarray(BY["scale_clip"].fn(img.copy(), 0.5, 0.5))
    assert o.min() < 0.01 and o.max() > 0.99, "scale_clip がフルレンジに達していない"
    assert (o.max() - o.min()) > (float(img.max()) - float(img.min())) + 1e-6, \
        "scale_clip がレンジを広げていない(beat-null)"
    k += 1

    return k


def main() -> int:
    # OPS が族の実集合と厳密一致することを実行時に検証(取りこぼし/余分を弾く)。
    target = sorted(o.name for o in ops.REGISTRY if o.category in TARGET_CATS)
    listed = sorted(OPS)
    missing = sorted(set(target) - set(listed))
    extra = sorted(set(listed) - set(target))
    assert not missing, f"OPS に不足: {missing}"
    assert not extra, f"OPS に余分: {extra}"
    assert len(OPS) == len(set(OPS)), "OPS に重複がある"
    assert len(OPS) == len(target), f"件数不一致: OPS={len(OPS)} target={len(target)}"

    n = exercise_all()
    k = ground_truth_checks()

    print(f"PASS: {n} ops exercised, all finite/typed/deterministic; {k} GT checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
