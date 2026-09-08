# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""実写のテクスチャを回す —— 「回転不変」は、それが要らない素材でだけ成り立つ。

材質を見分けるとき、撮る向きは選べません。だから記述子には「回転不変」が
求められます。ここでは実写のテクスチャ 3 枚(``scikit-image`` 同梱の
``brick`` / ``grass`` / ``gravel``、いずれも CC0)を**既知の角度で回して**、
記述子が自分自身からどれだけ離れるかを測ります。

**測る前に基準を決めます** —— 「素材どうしの距離」です。回転で動く量が
素材間の距離を超えたら、**回した自分より別の素材のほうが近い**ことになり、
分類は原理的に成り立ちません。合成の縞模様では出ない、実写の異方性が相手です。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **基準を先に置く**。既定の符号化(``'default'``)で素材間の χ² 距離は
   brick-grass 0.0593 / brick-gravel 0.0580 / grass-gravel **0.0125**。
   いちばん近い 2 つ(草と砂利)の 0.0125 が、この課題の**分解能**。
2. ★★**異方な素材は、5 度回すだけで壊れる**。brick は 15 度で 0.0600、
   60 度で **0.1205** —— 分解能の **9.6 倍**。つまり **brick を 60 度回すと、
   草と砂利を見分けるより遠くへ行く**。一方 grass / gravel は 0.0005〜0.0024
   (分解能の 0.17 / 0.19 倍)で、実質的に不変。
3. ★**犯人は補間ではない**(対照群 2 つ)。
   * 補間だけの寄与 —— +7 度回して -7 度戻すと brick 0.03685 /
     grass 0.00077 / gravel 0.00063。
   * 補間ゼロの厳密 90 度(``np.rot90``)—— brick は **0.08501** で、
     それでも分解能の 6.8 倍。**補間を消しても壊れる**。
4. ★**異方性は独立に測れて、順位を説明する**。構造テンソルの局所一貫性
   (中央値)は brick 0.917 / grass 0.308 / gravel 0.320、勾配方向の大域的な
   偏り R は brick 0.309 / grass 0.027 / gravel 0.029。**唯一 10 倍違うのが
   brick** で、それが唯一壊れる素材。
5. ★★**「回転不変」な符号化に替えても 1 を割らない**。``b`` で
   ``method`` を選べるようにして測ると、回転ずれ / 分解能 の比は
   ``'default'`` 9.64 -> ``'ror'`` 5.49 -> ``'uniform'`` **1.72**。
   等方な 2 つは 0.17 -> 0.02 と **10 倍**良くなるのに、brick は
   **1 を下回らない**。理由は原理的で、LBP の回転不変性は**局所パターンの
   巡回**に対する不変性であって、**素材そのものの向きの分布**は消せない。
   ★``'nri_uniform'``(回転不変ではない uniform)は 4.24 で、
   「uniform だから良い」のではなく「回転不変だから良い」ことも確かめられる。
6. **``b`` は本当に何もしていなかった**。この PoC を書くまで ``sk_lbp`` の
   ``method`` は ``'default'`` 固定で、``b`` は未使用だった(``hough_circle_trans``
   と同じ形)。**選べなければ下げようがない**ので割り当てた
   (``b=0.5`` は従来と完全に同一)。

つまり、この族について言えるのは「回転不変です」ではなく
**「等方な素材については回転不変で、異方な素材については向きの情報が
そのまま残る」**。前者は回転不変性が要らない場面、後者は要る場面です。

EXTEND: 自前の素材に差し替えるなら :data:`MATERIALS` を置き換えます。
**基準(素材間の距離)を必ず先に測ること** —— 回転ずれの絶対値だけを見ても
「大きい」か「小さい」かは決まりません。異方性が疑わしいときは 4 節の
R(勾配方向の大域的な偏り)を先に見ると、どの素材が壊れるかを**測る前に**
言い当てられます。

出典: ``scikit-image`` 同梱の ``brick`` / ``grass`` / ``gravel``
(いずれも CC0Textures 由来、CC0)。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402
import realdata                                                  # noqa: E402

#: 使う実写テクスチャ(すべて CC0)
MATERIALS = ("brick", "grass", "gravel")

#: 掃引する回転角[度]
ANGLES = (5, 15, 30, 45, 60, 90)

#: ``sk_lbp`` の ``b`` -> 符号化(backends の表と同じ区切り)
METHODS = (("default", 0.5), ("ror", 0.7), ("uniform", 0.8), ("nri_uniform", 0.95))

#: ヒストグラムのビン数
NBINS = 32


def crop(a):
    """回転で欠けない内接正方形を切る(縁の外挿を測らないため)。"""
    h, w = a.shape
    s = int(min(h, w) / np.sqrt(2)) // 2 * 2
    r0, c0 = (h - s) // 2, (w - s) // 2
    return a[r0:r0 + s, c0:c0 + s]


def rotate(a, deg):
    if deg == 0:
        return crop(a)
    return crop(ndi.rotate(a, float(deg), reshape=False, order=3, mode="reflect"))


def lbp_hist(a, b=0.5):
    """``sk_lbp`` の出力をヒストグラムにして正規化する。"""
    m = np.asarray(fs.apply(a, "sk_lbp", 0.5, float(b)), np.float64)
    h, _e = np.histogram(m, bins=NBINS, range=(float(m.min()), float(m.max())))
    return h / max(h.sum(), 1)


def chi2(p, q):
    return float(0.5 * ((p - q) ** 2 / np.maximum(p + q, 1e-12)).sum())


def anisotropy(a):
    """構造テンソルの局所一貫性(中央値)と、勾配方向の大域的な偏り ``R``。"""
    gy, gx = np.gradient(a)
    jxx = ndi.gaussian_filter(gx * gx, 4)
    jyy = ndi.gaussian_filter(gy * gy, 4)
    jxy = ndi.gaussian_filter(gx * gy, 4)
    tr = jxx + jyy
    det = jxx * jyy - jxy * jxy
    d = np.sqrt(np.maximum(tr * tr - 4 * det, 0.0))
    coh = np.where(tr > 1e-12, d / np.maximum(tr, 1e-12), 0.0)
    ang = np.arctan2(gy, gx) * 2.0                 # 向きは 180 度で同一
    return float(np.median(coh)), float(np.abs(np.mean(np.exp(1j * ang))))


def main() -> None:
    t0 = time.perf_counter()
    imgs = dict((m, realdata.load_gray(m)) for m in MATERIALS)
    print("実写テクスチャ 3 枚(scikit-image、CC0)")
    for m in MATERIALS:
        print("  %-8s %s  平均 %.3f  標準偏差 %.3f"
              % (m, imgs[m].shape, imgs[m].mean(), imgs[m].std()))

    # --- 1 ------------------------------------------------------------------ #
    base = dict((m, lbp_hist(crop(imgs[m]))) for m in MATERIALS)
    pairs = [(a, b, chi2(base[a], base[b]))
             for i, a in enumerate(MATERIALS) for b in MATERIALS[i + 1:]]
    res = min(p[2] for p in pairs)
    print("\n1. 基準 —— 素材どうしの距離(これが分解能)")
    for a, b, d in pairs:
        print("   %-7s vs %-7s  chi2 %.5f%s"
              % (a, b, d, "   <- いちばん近い = 分解能" if d == res else ""))

    # --- 2 ------------------------------------------------------------------ #
    print("\n2. 回転で自分自身からどれだけ離れるか(分解能 %.5f と比べる)" % res)
    print("   素材      " + "  ".join("%7d" % d for d in ANGLES) + "   最大/分解能")
    drift = {}
    for m in MATERIALS:
        row = [chi2(base[m], lbp_hist(rotate(imgs[m], d))) for d in ANGLES]
        drift[m] = row
        print("   %-8s " % m + "  ".join("%7.4f" % v for v in row)
              + "   %8.2f" % (max(row) / res))
    assert max(drift["brick"]) / res > 5.0, drift["brick"]
    for m in ("grass", "gravel"):
        assert max(drift[m]) / res < 0.5, (m, drift[m])

    # --- 3 ------------------------------------------------------------------ #
    print("\n3. 対照群 —— 犯人は補間ではない")
    ctrl = {}
    for m in MATERIALS:
        a = imgs[m]
        rt = ndi.rotate(ndi.rotate(a, 7.0, reshape=False, order=3, mode="reflect"),
                        -7.0, reshape=False, order=3, mode="reflect")
        only_interp = chi2(base[m], lbp_hist(crop(rt)))
        exact90 = chi2(base[m], lbp_hist(crop(np.rot90(a))))
        ctrl[m] = (only_interp, exact90)
        print("   %-8s 補間だけ(+7/-7 度)%.5f  /  厳密 90 度(rot90、補間なし)"
              "%.5f(分解能の %.2f 倍)" % (m, only_interp, exact90, exact90 / res))
    assert ctrl["brick"][1] / res > 3.0, ctrl["brick"]
    assert ctrl["brick"][1] > 2.0 * ctrl["brick"][0], ctrl["brick"]

    # --- 4 ------------------------------------------------------------------ #
    print("\n4. 異方性は独立に測れて、順位を説明する")
    aniso = {}
    for m in MATERIALS:
        coh, r = anisotropy(crop(imgs[m]))
        aniso[m] = (coh, r)
        print("   %-8s 局所一貫性 中央 %.3f  /  勾配方向の大域的な偏り R = %.3f"
              % (m, coh, r))
    assert aniso["brick"][1] > 5.0 * max(aniso["grass"][1], aniso["gravel"][1]), aniso

    # --- 5 ------------------------------------------------------------------ #
    print("\n5. 「回転不変」な符号化に替えても 1 を割らない")
    print("   method        分解能    " + "  ".join("%-8s" % m for m in MATERIALS))
    ratios = {}
    for name, bval in METHODS:
        bs = dict((m, lbp_hist(crop(imgs[m]), bval)) for m in MATERIALS)
        r2 = min(chi2(bs[a], bs[b])
                 for i, a in enumerate(MATERIALS) for b in MATERIALS[i + 1:])
        row = []
        for m in MATERIALS:
            d = max(chi2(bs[m], lbp_hist(rotate(imgs[m], g), bval)) for g in ANGLES)
            row.append(d / max(r2, 1e-12))
        ratios[name] = row
        print("   %-12s %.5f  " % (name, r2)
              + "  ".join("%8.2f" % v for v in row))
    assert ratios["uniform"][0] < 0.3 * ratios["default"][0], ratios
    assert ratios["uniform"][0] > 1.0, ratios["uniform"]      # それでも 1 を割らない
    assert ratios["uniform"][1] < 0.1 and ratios["uniform"][2] < 0.1, ratios
    assert ratios["nri_uniform"][0] > ratios["uniform"][0], ratios

    # --- 6 ------------------------------------------------------------------ #
    same = np.array_equal(np.asarray(fs.apply(crop(imgs["brick"]), "sk_lbp", 0.5, 0.5)),
                          np.asarray(fs.apply(crop(imgs["brick"]), "sk_lbp", 0.5, 0.0)))
    print("\n6. b=0.5(既定)と b=0.0 は同じ符号化 'default': %s" % ("はい" if same else "いいえ"))
    assert same

    # --- 図 ------------------------------------------------------------------ #
    figs.save_grid(
        "textures",
        [crop(imgs["brick"]), rotate(imgs["brick"], 60),
         crop(imgs["grass"]), rotate(imgs["grass"], 60)],
        ["brick 0 度", "brick 60 度(自分から %.4f)" % drift["brick"][4],
         "grass 0 度", "grass 60 度(自分から %.4f)" % drift["grass"][4]],
        title="同じ 60 度でも、壊れるのは向きを持つ素材だけ", ncols=2,
        caption="分解能(草と砂利の距離)は %.5f。brick はその %.1f 倍動く。"
                % (res, drift["brick"][4] / res))

    figs.save_plot(
        "drift",
        [(m, list(ANGLES), [v / res for v in drift[m]]) for m in MATERIALS]
        + [("分解能 = 1.0", list(ANGLES), [1.0] * len(ANGLES))],
        xlabel="回転角 [度]", ylabel="自分からのずれ / 分解能",
        title="1.0 を超えたら、回した自分より別の素材のほうが近い",
        caption="brick だけが 1 を大きく超える(最大 %.1f 倍)。"
                % (max(drift["brick"]) / res))

    figs.save_plot(
        "methods",
        [(m, [i for i in range(len(METHODS))], [ratios[n][k] for n, _b in METHODS])
         for k, m in enumerate(MATERIALS)]
        + [("1.0", [i for i in range(len(METHODS))], [1.0] * len(METHODS))],
        xlabel="符号化(0=default 1=ror 2=uniform 3=nri_uniform)",
        ylabel="最大ずれ / 分解能",
        title="回転不変な符号化でも brick は 1 を割らない",
        caption="等方な 2 つは 10 倍良くなる。異方性は符号化では消せない。")

    figs.save_table(
        "summary",
        ["素材", "R(向きの偏り)", "既定", "uniform"],
        [[m, "%.3f" % aniso[m][1], "%.2f" % ratios["default"][k],
          "%.2f" % ratios["uniform"][k]] for k, m in enumerate(MATERIALS)],
        title="向きの偏りが、そのまま壊れやすさ", col_w=115,
        caption="単位はどれも「分解能に対する比」。1 を超えたら分類は成り立たない。")

    print("\n所見")
    print("  * 分解能(草と砂利の距離)%.5f。brick は 60 度で %.4f = %.1f 倍。"
          % (res, drift["brick"][4], drift["brick"][4] / res))
    print("  * 補間ゼロの厳密 90 度でも %.5f(%.1f 倍)—— 補間のせいではない。"
          % (ctrl["brick"][1], ctrl["brick"][1] / res))
    print("  * 向きの偏り R は brick %.3f 対 grass %.3f / gravel %.3f。"
          % (aniso["brick"][1], aniso["grass"][1], aniso["gravel"][1]))
    print("  * 回転不変な符号化で %.2f -> %.2f 倍まで下がるが、1 は割らない。"
          % (ratios["default"][0], ratios["uniform"][0]))
    print("  * 等方な 2 つは %.2f -> %.2f / %.2f -> %.2f 倍。"
          % (ratios["default"][1], ratios["uniform"][1],
             ratios["default"][2], ratios["uniform"][2]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
