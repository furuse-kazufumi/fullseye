# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""threshold_family_agreement — 12 通りの自動しきい値に、同じ絵を見せる。

    py -3.11 examples/threshold_family_agreement.py

【この例が示すこと】
「どの二値化を使うか」は好みで選ばれがちだが、**族としての約束**が 1 つある:
*region になるのは明るい側* 。しきい値の位置が方法ごとに違うのは構わない ——
向きが違うと、次の段(面積・重心・良否判定)が**黙って別のものを測る**。

ここでは値が 2 種類しかない板(明部ちょうど 400 px)を 12 の方法に見せ、

1. 大域の自動しきい値は**全部 400 px で一致する**(方法が違っても答えが割れない)
2. 局所適応(Niblack / Bernsen / 局所大津)は数は違うが**向きは同じ**
3. ★向きが逆だと何が起きるか —— 面積が 400 から 3,696 へ、9.2 倍。例外も警告も
   出ず、「もっともらしい数」が返る

を見せる。3 がこの例の眼目である。

★**この例は実際に 3 本の op の欠陥を見つけた**(2026-09-26)。SimpleITK 由来の
`xsitk_huang_thresh` / `xsitk_maxentropy_thresh` / `xsitk_moments_thresh` が、
兄弟 op の補集合を返していた。ITK の ``insideValue`` は**しきい値以下**の側
(暗い方)に付くので、`(img, 1, 0, bins)` は「暗い側を前景にする」という意味
だった。既存の門は「二値であること」「全 0/全 1 でないこと」しか見ていなかった
ので、**どちらの向きでも通っていた**。

EXTEND: `fullseye.apply(im, "<方法名>")` で同じ表を自分の画像に対して作れる。
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fullseye as fs  # noqa: E402
import ops as _ops  # noqa: E402

SIDE, BOX, FG = 64, 20, 400

#: 大域の自動しきい値。板では**ちょうど箱**を返すべきもの。
GLOBAL = ["otsu", "binary_threshold", "auto_threshold", "sk_otsu", "cv_otsu",
          "sk_yen", "sk_li", "xsitk_huang_thresh", "xsitk_maxentropy_thresh",
          "xsitk_moments_thresh"]
#: 局所適応。窓の中で決めるので平らな面では数が外れてよい —— 向きだけ揃っていること。
LOCAL = ["sk_sauvola", "sk_niblack", "xmh_bernsen", "xsk3_rank_otsu"]


def plate(bg: float = 0.0, fg: float = 1.0) -> np.ndarray:
    """値が 2 種類しかない板。明部はちょうど 400 px。"""
    im = np.full((SIDE, SIDE), float(bg))
    im[22:22 + BOX, 22:22 + BOX] = float(fg)
    return im


BOX_MASK = np.zeros((SIDE, SIDE), bool)
BOX_MASK[22:22 + BOX, 22:22 + BOX] = True


def measure(name: str, im: np.ndarray):
    """(前景 px, 箱の中の被覆率, 箱の外の被覆率)。届かない op は None。"""
    if name not in _ops.RT:
        return None
    r = np.asarray(_ops.RT[name](im.copy(), 0.5, 0.5), np.float64) > 0.5
    return int(r.sum()), float(r[BOX_MASK].mean()), float(r[~BOX_MASK].mean())


def what_a_flipped_region_costs():
    """★向きが逆だと、面積はどう嘘をつくか。"""
    r = np.asarray(fs.apply(plate(), "otsu"), np.float64) > 0.5
    # 次の段は向きを知らない —— 渡された region の面積を素直に返すだけ。
    npx = float(r.size)
    right = float(np.ravel(fs.apply(r.astype(np.float64), "area_frac"))[0]) * npx
    wrong = float(np.ravel(fs.apply((~r).astype(np.float64), "area_frac"))[0]) * npx
    return right, wrong


def main() -> int:
    im = plate()
    print("値が 2 種類の板(明部 %d px)に、12 の自動しきい値を見せる" % FG)
    print()
    print("%-26s %7s %9s %9s  %s" % ("方法", "前景px", "箱の中", "箱の外", ""))

    agreed, missing = [], []
    for name in GLOBAL:
        m = measure(name, im)
        if m is None:
            missing.append(name)
            continue
        n, ins, out = m
        mark = "一致" if n == FG else "★ずれ"
        print("%-26s %7d %8.1f%% %8.1f%%  %s" % (name, n, 100 * ins, 100 * out, mark))
        agreed.append((name, n))

    print()
    for name in LOCAL:
        m = measure(name, im)
        if m is None:
            missing.append(name)
            continue
        n, ins, out = m
        assert ins > out + 0.4, "%s の向きが逆(中 %.2f / 外 %.2f)" % (name, ins, out)
        print("%-26s %7d %8.1f%% %8.1f%%  局所(数は外れてよい・向きは同じ)"
              % (name, n, 100 * ins, 100 * out))

    assert agreed, "しきい値 op が 1 つも届かなかった"
    for name, n in agreed:
        assert n == FG, "%s が %d px(期待 %d)—— 大域の自動しきい値が割れている" % (name, n, FG)

    print()
    right, wrong = what_a_flipped_region_costs()
    print("向きが逆だと面積はこう嘘をつく:")
    print("  明るい側を region に   -> 面積 %6.0f  (正しい)" % right)
    print("  暗い側を region に     -> 面積 %6.0f  (%.1f 倍。例外も警告も出ない)"
          % (wrong, wrong / max(1.0, right)))
    assert abs(right - FG) < 1e-9, "正しい側の面積が %g" % right
    assert wrong > right * 5, "補集合が目立たない板になっている(探針が弱い)"

    if missing:
        print()
        print("この環境に届かなかった方法: %s" % ", ".join(missing))
    print()
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
