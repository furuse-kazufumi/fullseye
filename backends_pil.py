"""Pillow (PIL) incorporation — distinctive filters HALCON/the core lack.

Pillow ships classic NPR/enhance filters (emboss, contour, find-edges, edge-
enhance, mode filter, unsharp mask) and tone operators (posterize, solarize,
auto-contrast) that the numpy/HALCON core does not carry. `build()` wraps the
genuinely-distinctive, single-gray-image ones; exception-safe, output in [0,1].
Prefixed `xpil_`; `Op.halcon=""` (they lift Pillow-axis coverage, not HALCON's).
"""
from __future__ import annotations

import numpy as np


def _safe(fn, out_sort=None):
    """Fail-soft wrapper -> the shared, RECORDING guard (backend_safe.guard).

    A failure degrades to a sort-valid fallback exactly as before, but the event
    is now written to the fallback ledger and strict mode re-raises, so a
    permanently broken op can no longer masquerade as a working identity.
    """
    from backend_safe import guard
    return guard(fn, out_sort)


#: lambda で定義された op の説明（lambda に docstring は書けない）。
#: ops.py の登録ループが Op.doc に積む。キーは op 名。
DOCS = {
    "xpil_emboss": (
        "Pillow のエンボス（浮き彫り）フィルタ。``PIL.ImageFilter.EMBOSS`` の固定"
        "3x3 カーネルを掛ける（斜め方向の勾配を検出し、平坦部を中間グレーに"
        "落とす古典的な NPR フィルタ）。\n\n"
        "a, b は未使用（Pillow の ``ImageFilter.EMBOSS`` はパラメータを持たない"
        "固定カーネル）。"
    ),
    "xpil_contour": (
        "Pillow の輪郭抽出フィルタ。``PIL.ImageFilter.CONTOUR`` の固定カーネルで"
        "輪郭線だけを白背景に黒線で残すような効果を作る（ペン画・線画調の"
        "エフェクト）。\n\n"
        "a, b は未使用（固定カーネル）。"
    ),
    "xpil_find_edges": (
        "Pillow のエッジ検出フィルタ。``PIL.ImageFilter.FIND_EDGES`` の固定"
        "カーネル（ラプラシアン系）でエッジを強調する。\n\n"
        "a, b は未使用（固定カーネル）。``xpil_contour`` と似た系統だが係数が"
        "異なり、輪郭より生のエッジ強度に近い出力になる。"
    ),
    "xpil_edge_enhance": (
        "Pillow のエッジ強調フィルタ（強め）。``PIL.ImageFilter.EDGE_ENHANCE_MORE``"
        "の固定カーネルでエッジ付近のコントラストを持ち上げる"
        "（``EDGE_ENHANCE`` より強い版）。\n\n"
        "a, b は未使用（固定カーネル）。"
    ),
    "xpil_smooth_more": (
        "Pillow の平滑化フィルタ（強め）。``PIL.ImageFilter.SMOOTH_MORE`` の"
        "固定カーネルで ``SMOOTH`` よりも強くぼかす。\n\n"
        "a, b は未使用（固定カーネル）。"
    ),
    "xpil_detail": (
        "Pillow のディテール強調フィルタ。``PIL.ImageFilter.DETAIL`` の固定"
        "カーネルで細部のコントラストを持ち上げる（シャープ化に近いが、"
        "エッジよりテクスチャ側を強調する係数）。\n\n"
        "a, b は未使用（固定カーネル）。"
    ),
    "xpil_mode_filter": (
        "最頻値フィルタ。``PIL.ImageFilter.ModeFilter`` で窓内の最頻出画素値に"
        "置き換える（中央値でなく最頻値を取る点がメディアンフィルタと異なる）。\n\n"
        "a が窓サイズを 3/5/7/9 の 4 段階（``3 + 2*int(a*3)``）で振る。b は"
        "未使用。単色の塗りつぶし領域が多い画像（ラベル画像・漫画調画像）の"
        "ノイズ除去に向き、階調が滑らかな自然画像では効果が薄い。"
    ),
    "xpil_unsharp_mask": (
        "Pillow のアンシャープマスク。``PIL.ImageFilter.UnsharpMask`` を呼ぶ"
        "（kornia 版 ``xkor_unsharp`` に対応する CPU 実装）。\n\n"
        "a がぼかし半径（``radius = 1 + 4*a``、範囲 1〜5）、b が強調量"
        "（``percent = int(50 + 200*b)``、範囲 50〜250%）を振る。しきい値は 0"
        "固定（すべての差分を強調対象にする）。"
    ),
    "xpil_posterize": (
        "ポスタリゼーション（階調数の削減）。``PIL.ImageOps.posterize`` を呼び、"
        "各チャンネルの有効ビット数を減らして色数を落とす。\n\n"
        "a が保持ビット数（``bits = 1 + int(a*6)``、範囲 1〜7）を振る。b は"
        "未使用。bits=1 では各チャンネルが 2 値化に近い極端な階調落ちになる。"
    ),
    "xpil_solarize": (
        "ソラリゼーション（フィルム現像の中間反転効果）。``PIL.ImageOps.solarize``"
        "を呼び、しきい値を超える画素値を反転する。\n\n"
        "a がしきい値（``threshold = int(64 + 160*a)``、範囲 64〜224）を振る。"
        "b は未使用。しきい値が低いほど反転される範囲が広がる。"
    ),
    "xpil_autocontrast": (
        "オートコントラスト（ヒストグラムの両端を切ってフルレンジに引き伸ばす）。"
        "``PIL.ImageOps.autocontrast`` を呼ぶ。\n\n"
        "a がカットオフ率（``cutoff = int(a*10)``、範囲 0〜10%。ヒストグラムの"
        "最暗・最明側からそれぞれ何 % を外れ値として無視するか）を振る。b は"
        "未使用。外れ値の影響を抑えつつコントラストを最大限に引き伸ばせる。"
    ),
    "xpil_offset": (
        "画像をトロイダル（周回・wrap-around）にシフトする。"
        "``PIL.ImageChops.offset`` を呼ぶ——画面端からはみ出た画素が反対側の"
        "端に現れる循環シフトで、通常の平行移動と違って画像端が黒くならない。\n\n"
        "a が横方向のシフト量（画像幅に対する比率）、b が縦方向のシフト量"
        "（画像高さに対する比率）を振る。内容の連続性は崩れるため、タイル状の"
        "テクスチャ生成などに向く。"
    ),
    "xpil_contrast": (
        "コントラスト調整（画像の平均輝度を軸にした線形伸縮）。"
        "``PIL.ImageEnhance.Contrast`` を呼ぶ。\n\n"
        "a が強調係数（``factor = 2*a``、範囲 0〜2）を振る。a=0.5 で係数 1.0"
        "（元画像のまま）、a=0 に近づくほど平均輝度一色のグレーに潰れ、a=1 に"
        "近づくほどコントラストが 2 倍まで強調される。b は未使用。"
    ),
}


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    try:
        from PIL import Image, ImageFilter, ImageOps
    except Exception:
        return []

    def _im(v):
        # 0 サイズは**ここで弾く**。Pillow の一部(ImageChops.offset)は 0x0 の
        # 画像でネイティブ側から落ち、**インタプリタごと死ぬ** —— Python 例外に
        # ならないので backend_safe.guard でも捕まえられない(2026-09-05 実測:
        # `xpil_offset` に (0,0) を渡すと exit 127)。全 PIL op がこの入口を
        # 通るので、ここ 1 箇所で族ごと塞ぐ。ValueError にすればガードが記録して
        # sort に合う fallback へ落とす。
        a = np.asarray(v, np.float64)
        if a.size == 0 or min(a.shape[:2] or (0,)) == 0:
            raise ValueError("PIL backend: 0 サイズの画像は扱えない (shape=%r)" % (a.shape,))
        return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), "L")

    def _arr(im):
        return np.asarray(im, np.float64) / 255.0

    def _filt(flt):
        return lambda v, a, b: _arr(_im(v).filter(flt))

    defs = [
        ("xpil_emboss", "artistic", "", IMAGE, IMAGE, _filt(ImageFilter.EMBOSS)),
        ("xpil_contour", "edges", "", IMAGE, IMAGE, _filt(ImageFilter.CONTOUR)),
        ("xpil_find_edges", "edges", "", IMAGE, IMAGE, _filt(ImageFilter.FIND_EDGES)),
        ("xpil_edge_enhance", "gray", "", IMAGE, IMAGE, _filt(ImageFilter.EDGE_ENHANCE_MORE)),
        ("xpil_smooth_more", "smoothing", "", IMAGE, IMAGE, _filt(ImageFilter.SMOOTH_MORE)),
        ("xpil_detail", "gray", "", IMAGE, IMAGE, _filt(ImageFilter.DETAIL)),
        ("xpil_mode_filter", "rank", "", IMAGE, IMAGE,
         lambda v, a, b: _arr(_im(v).filter(ImageFilter.ModeFilter(size=3 + 2 * int(a * 3))))),
        ("xpil_unsharp_mask", "smoothing", "", IMAGE, IMAGE,
         lambda v, a, b: _arr(_im(v).filter(ImageFilter.UnsharpMask(
             radius=1 + 4 * a, percent=int(50 + 200 * b), threshold=0)))),
        ("xpil_posterize", "gray", "", IMAGE, IMAGE,
         lambda v, a, b: _arr(ImageOps.posterize(_im(v), bits=1 + int(a * 6)))),
        ("xpil_solarize", "gray", "", IMAGE, IMAGE,
         lambda v, a, b: _arr(ImageOps.solarize(_im(v), threshold=int(64 + 160 * a)))),
        ("xpil_autocontrast", "gray", "", IMAGE, IMAGE,
         lambda v, a, b: _arr(ImageOps.autocontrast(_im(v), cutoff=int(a * 10)))),
    ]
    try:
        from PIL import ImageChops, ImageEnhance

        defs += [
            ("xpil_offset", "geometry", "", IMAGE, IMAGE,          # toroidal (wrap-around) shift
             lambda v, a, b: _arr(ImageChops.offset(_im(v), int(a * np.asarray(v).shape[1]),
                                                     int(b * np.asarray(v).shape[0])))),
            ("xpil_contrast", "gray", "", IMAGE, IMAGE,            # contrast about the image mean
             lambda v, a, b: _arr(ImageEnhance.Contrast(_im(v)).enhance(2 * a))),
        ]
    except Exception:
        pass
    return [Op(n, c, h, i, o, _safe(f, o)) for (n, c, h, i, o, f) in defs]
