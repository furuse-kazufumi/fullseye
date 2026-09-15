# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""微細スクラッチの検出と幅計測 —— 幅 1〜3 px の傷を、真値と突き合わせる。

    py -3.11 examples/example_scratch_width.py

【この例が解く問題】
研磨面の線状の傷を (1) `lines_gauss` で見つけ、(2) 傷に直交する測定線を張って
`measure_pairs` で幅を測り、(3) `mm_per_px_from_reference` / `table_px_to_mm` で
mm にする —— という「レシピ」(docs/capabilities/scratch-detection-and-width.md)
を、**幅の真値が分かっている合成の傷**で通す。

【グラウンドトゥルース】
傷は「暗い帯」を画素の被覆率で解析的に描く(帯の幅 w [px] は小数でよい)。
その画像を既知の PSF(ガウス σ=0.7 px)でぼかす。積分法の真値は w そのもの
(輝度欠損の総量は畳み込みで保存される)。基準の帯(幅 40.0 px = 2.000 mm)を
同じ描き方で用意し、そこから mm/px を校正する。

【この例が示すこと(数字は実行時の実測)】
1. `lines_gauss` は幅 1〜5 px のどの傷も輪郭として返す —— が、**幅も極性も返さない**
   (明線を同じ設定で通しても輪郭が出る)。検出と計測は別の op。
2. `measure_pairs` の幅は **傷が細いほど大きい側へ偏る**(対が互いを押し広げる)。
   幅 5 px なら偏り 0.1 px 級だが、幅 1〜2 px では偏りが幅と同じ桁になる。
   しかも空 list ではなく「対が見つかった」と答える。σ を 1.0 → 0.5 にすると
   偏りは縮むが、消えない。
3. **輝度欠損の積分**は幅 1 px でも 1 % 以内で当たる(`poc_crack_width` の結論)。
   画素以下の幅はこちら。
4. mm への換算は校正値を通すだけ —— 校正を公称倍率で置き換えると全部の幅が
   同じ比率でずれる。

EXTEND: 実写なら `render()` の出力を撮影画像に差し替え、`PSF_SIGMA` は
点光源かエッジから実測、`mm_per_px` はスケールバーを `measure_pairs` にかけて出す。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fullseye as fs  # noqa: E402

BG, DEPTH = 0.6, 0.5           # 地の明るさと、傷の暗さ(地からの落ち込み)
PSF_SIGMA = 0.7                # ぼけ [px](既知)
H, W = 64, 128
WIDTHS = (1.0, 1.5, 2.0, 3.0, 5.0)
REF_WIDTH_PX, REF_WIDTH_MM = 40.0, 2.000     # 校正用の基準帯


def render(width_px: float, row_c: float = 31.37, bright: bool = False) -> np.ndarray:
    """中心 row_c、幅 width_px の水平な帯を被覆率で描き、既知 PSF でぼかす。"""
    from scipy.ndimage import gaussian_filter

    r = np.arange(H, dtype=float)
    lo, hi = row_c - width_px / 2.0, row_c + width_px / 2.0
    cov = np.clip(np.minimum(r + 0.5, hi) - np.maximum(r - 0.5, lo), 0.0, 1.0)   # 画素の被覆率
    col = BG + (DEPTH if bright else -DEPTH) * cov
    img = np.tile(col[:, None], (1, W))
    img[:, :8] = BG; img[:, -8:] = BG                                             # 帯の端
    return gaussian_filter(img, PSF_SIGMA)


def width_by_integral(img: np.ndarray, col: int) -> float:
    """列 col の輝度欠損を積分して幅にする(欠損の総量は畳み込みでも保存される)。"""
    return float(np.sum(BG - img[:, col]) / DEPTH)


def width_by_pairs(img: np.ndarray, col: int, sigma: float, length1: float = 14.0) -> float | None:
    """傷に直交(phi=π/2)する測定線 1 本で、極性の違う隣接エッジの対の幅を取る。"""
    meas = fs.ledger.gen_measure_rectangle2(row=H / 2 - 0.5, col=col, phi=np.pi / 2,
                                            length1=length1, length2=5, shape=img.shape)
    pairs = fs.ledger.measure_pairs(img, meas, sigma=sigma, threshold=0.1)
    if not pairs:
        return None
    # 傷は暗いので「立ち下がり → 立ち上がり」の対。極性の順序は op が問わないので確かめる
    p = pairs[0]
    assert p["first_amplitude"] < 0 < p["second_amplitude"], p
    return float(p["width"])


def main() -> None:
    print("=== 微細スクラッチ: 検出(lines_gauss)と幅(measure_pairs / 積分)  真値 w [px]")
    # --- 校正: 基準帯を同じ op で測って mm/px を出す --------------------------------
    ref = render(REF_WIDTH_PX)
    ref_px = width_by_pairs(ref, 64, sigma=1.0, length1=28.0)   # 帯 40 px を跨ぐ長さ
    mm_per_px = fs.ledger.mm_per_px_from_reference(ref_px, REF_WIDTH_MM)
    print(f"校正: 基準帯 {REF_WIDTH_PX:.1f} px を measure_pairs で {ref_px:.3f} px → "
          f"mm/px = {mm_per_px:.5f}(真値 {REF_WIDTH_MM / REF_WIDTH_PX:.5f})")
    assert abs(ref_px - REF_WIDTH_PX) < 0.05, ref_px

    # --- 検出は極性を返さない --------------------------------------------------------
    dark = fs.apply(render(2.0), "lines_gauss", 0.5, 0.5)
    brt = fs.apply(render(2.0, bright=True), "lines_gauss", 0.5, 0.5)
    print(f"lines_gauss: 暗線 {len(dark['cs'])} 輪郭 / 明線 {len(brt['cs'])} 輪郭 "
          "—— どちらも出る(極性も幅も返さない)")
    assert len(dark["cs"]) >= 1 and len(brt["cs"]) >= 1
    top = np.asarray(fs.apply(render(2.0), "tophat", 0.35, 0.5))
    bot = np.asarray(fs.apply(render(2.0), "bothat", 0.35, 0.5))
    print(f"tophat(明るい細部) の暗線への応答 {top.max():.3f} / bothat(暗い細部) {bot.max():.3f}")
    assert top.max() < 1e-9 < bot.max()

    # --- 幅: 真値 vs measure_pairs(σ 1.0 / 0.5)vs 積分 ------------------------------
    print()
    print("| 真値 w [px] | w/σ_psf | lines_gauss 検出 | measure_pairs σ=1.0 | σ=0.5 | 積分法 | 積分法 [mm] |")
    print("|---|---|---|---|---|---|---|")
    rows = []
    for w in WIDTHS:
        img = render(w)
        det = len(fs.apply(img, "lines_gauss", 0.5, 0.5)["cs"])
        p10 = width_by_pairs(img, 64, 1.0)
        p05 = width_by_pairs(img, 64, 0.5)
        integ = width_by_integral(img, 64)
        mm = fs.ledger.table_px_to_mm([{"width": integ}], mm_per_px)[0]["width_mm"]
        rows.append((w, det, p10, p05, integ))
        f = lambda v: "対なし" if v is None else f"{v:.3f} ({v - w:+.3f})"
        print(f"| {w:.1f} | {w / PSF_SIGMA:.2f} | {det} | {f(p10)} | {f(p05)} | {integ:.4f} ({integ - w:+.4f}) | {mm:.4f} |")

    # --- 主張を数字で固定する ----------------------------------------------------------
    for w, det, p10, p05, integ in rows:
        assert det >= 1, f"w={w}: lines_gauss が検出しない"
        assert abs(integ - w) < 0.01 * max(w, 1.0) + 0.005, f"w={w}: 積分法 {integ}"       # 1 % 以内
    # 幅 5 px は measure_pairs で 0.15 px 以内、幅 1〜2 px は偏りが 0.5 px を超える(危険域)
    w5 = [r for r in rows if r[0] == 5.0][0]
    assert w5[2] is not None and abs(w5[2] - 5.0) < 0.15, w5
    thin = [r for r in rows if r[0] <= 2.0]
    assert all(r[2] is not None for r in thin), "細い傷でも「対が見つかった」と答える(失敗を返さない)"
    assert all(r[2] - r[0] > 0.5 for r in thin), [(r[0], r[2]) for r in thin]
    assert all(r[3] - r[0] < r[2] - r[0] for r in thin), "σ を小さくすると偏りは縮む"
    print()
    print("結論: 検出は lines_gauss(極性・幅は返さない)、幅 ≳ 5 px は measure_pairs、"
          "画素級以下の幅は輝度欠損の積分。mm は校正値を通すだけ(公称倍率で置かない)。")
    print("PASS")


if __name__ == "__main__":
    main()
