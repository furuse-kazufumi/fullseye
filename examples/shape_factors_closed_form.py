# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""shape_factors_closed_form — 形状特徴を、閉形式の真値で採点する。

    py -3.11 examples/shape_factors_closed_form.py

【この例が示すこと】
面積・充填率・コンパクトさ・円形度には**厳密な真値**がある。矩形なら面積は
``w·h``、外接矩形との比は 1、``周囲長²/(4π・面積)`` は ``(w+h)²/(π·w·h)``。
円なら円形度は 1。だから、これらの op は「それらしい絵」ではなく**数で**採点できる。

採点すると 3 つのことが出る:

1. 面積・充填率・矩形度は**厳密に一致**する(丸め誤差 0)
2. ★**コンパクトさは 2026-09-26 まで頭打ちだった** —— ``min(1, C/10)`` で、
   幅 2 px の傷なら長さ 80 以上が**全部 1.0**。傷や割れという、いちばん見たい
   領域で「形が違うのに同じ数」が返っていた
3. ★**周囲長の推定には、解像度を上げても消えないバイアスが在る** ——
   しかも 2 つある推定量が**逆の形で外す**。どちらを使うかは測定の規約であって、
   片方が正しいという話ではない(``docs/KNOWN_ISSUES.md`` §50)

3 がこの例の眼目である。「もっと細かく撮れば合う」は、ここでは成り立たない。

EXTEND: 自分の形で採点するなら `truth_for_rect` を差し替える。
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fullseye as fs  # noqa: E402


def rect(h: int, w: int, n: int = 160, top: int = 20, left: int = 20):
    reg = np.zeros((n, n))
    reg[top:top + h, left:left + w] = 1.0
    return reg


def disc(r: float, n: int | None = None):
    n = int(2 * r + 8) if n is None else n
    yy, xx = np.mgrid[:n, :n]
    c = n / 2.0
    return (((yy - c) ** 2 + (xx - c) ** 2) <= r * r).astype(np.float64)


def feat(name: str, reg: np.ndarray) -> float:
    return float(np.ravel(np.asarray(fs.apply(reg, name), np.float64))[0])


def truth_for_rect(h: int, w: int, n: int):
    """矩形の閉形式。周囲長は連続形の ``2(h+w)``。"""
    area = float(h * w)
    return {"area_frac": area / (n * n), "rectangularity": 1.0,
            "compactness": (2.0 * (h + w)) ** 2 / (4.0 * np.pi * area)}


def exact_features() -> list:
    rows = []
    for h, w in ((24, 16), (40, 40), (8, 60), (2, 100)):
        n = 160
        want = truth_for_rect(h, w, n)
        reg = rect(h, w, n)
        rows.append((h, w, {k: (want[k], feat(k, reg)) for k in want}))
    return rows


def compactness_no_longer_saturates() -> list:
    """★長さを伸ばしたとき、数が伸び続けること(直す前は 1.0 で止まった)。"""
    out = []
    for length in (10, 40, 80, 110, 140):
        reg = rect(2, length, 200)
        out.append((length, feat("compactness", reg)))
    return out


def the_perimeter_bias_does_not_vanish() -> list:
    """★解像度を上げても消えないバイアス。2 つの推定量が逆の形で外す。"""
    from skimage import measure as skm

    rows = []
    for r in (12, 24, 48, 96):
        d = disc(r).astype(np.uint8)
        true_p = 2.0 * np.pi * r
        rows.append(("円 r=%d" % r, skm.perimeter(d) / true_p,
                     skm.perimeter_crofton(d) / true_p))
    for side in (16, 64, 128):
        reg = np.zeros((side + 8, side + 8), np.uint8)
        reg[4:4 + side, 4:4 + side] = 1
        true_p = 4.0 * side
        rows.append(("正方形 %d" % side, skm.perimeter(reg) / true_p,
                     skm.perimeter_crofton(reg) / true_p))
    return rows


def main() -> int:
    print("1) 閉形式で厳密に採れるもの(矩形)")
    print("%9s %-16s %14s %14s %10s" % ("形", "特徴", "真値", "実測", "差"))
    for h, w, got in exact_features():
        for k, (want, is_) in sorted(got.items()):
            d = abs(want - is_)
            ok = d < (1e-9 if k != "compactness" else 0.25)
            print("%9s %-16s %14.6f %14.6f %10.2e%s"
                  % ("%dx%d" % (h, w), k, want, is_, d, "" if ok else "  ★"))
            if k != "compactness":
                assert d < 1e-9, "%s が閉形式と合わない(%g)" % (k, d)

    print()
    print("2) コンパクトさは頭打ちしない(幅 2 px の傷の長さを伸ばす)")
    prev = 0.0
    for length, got in compactness_no_longer_saturates():
        print("   長さ %3d -> %8.4f" % (length, got))
        assert got > prev + 0.5, (
            "長さ %d で数が伸びていない —— 頭打ちが戻っている" % length)
        prev = got
    assert prev > 10.0, "いちばん細長い傷でも %g しか出ていない" % prev

    print()
    print("3) 周囲長のバイアスは解像度では消えず、2 つの推定量が逆の形で外す")
    print("   %-12s %12s %12s" % ("形", "perimeter", "crofton"))
    for name, p, pc in the_perimeter_bias_does_not_vanish():
        print("   %-12s %11.4f %12.4f" % (name, p, pc))
    rows = the_perimeter_bias_does_not_vanish()
    circles = [r for r in rows if r[0].startswith("円")]
    squares = [r for r in rows if r[0].startswith("正方形")]
    # 円では perimeter が外し続け、crofton が寄っていく。
    assert circles[-1][1] > 1.03, "円で perimeter のバイアスが消えている(改善?)"
    assert abs(circles[-1][2] - 1.0) < 0.01, "円で crofton が寄っていない"
    # 正方形では逆。
    assert abs(squares[-1][1] - 1.0) < 0.01, "正方形で perimeter が寄っていない"
    assert squares[-1][2] < 0.97, "正方形で crofton のバイアスが消えている(改善?)"
    print()
    print("   -> どちらか一方が『正しい周囲長』ではない。円形度・コンパクトさの")
    print("      絶対値は、この規約の選択に載っている(docs/KNOWN_ISSUES.md §50)。")

    print()
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
