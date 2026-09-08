# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""実写の免疫染色を色で分ける —— 見張り役が、見張るべき誤りにだけ盲目だった。

染色したスライドの RGB を色素ごとの濃度に分ける「色分離」(colour
deconvolution、Ruifrok & Johnston 2001)は、Beer-Lambert から光学密度
``OD = -log10(I/I0)`` が濃度の線形和になることだけを使う、素直な線形代数です。
素直だからこそ、**何が正しさを保証していて、何が保証していないか**が
はっきり分かれます。

この PoC は実写の免疫染色像(``scikit-image`` 同梱、ヘマトキシリン + DAB)を
通して、**「モデルが合っているか」を見張っているつもりの量が、いちばん
起こりやすい誤りに構造的に盲目**であることを数字で示します。

★この回で ``stain_unmix`` / ``stain_recompose`` / ``stain_vectors_from_patches``
を新設しました。``spec_unmix`` は 3 チャネルを**設計上拒否**する
(色と分光キューブを取り違えないため)ので、RGB の染色分離は入口が無かった。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **合成では完璧に分かれる**。片方の染色だけを濃度 1.0 で合成して解き直すと、
   回収は H 1.0000 / DAB 0.0000(逆も同じ)。**線形代数としては正しい**ので、
   合成データだけを見ていると「解けている」で終わる。
2. **実写では物理的にありえない値が出る**。H の濃度は最小 **-4.446** まで
   振れ、負になる画素は **11.51 %**。負の濃度は「その色素が光を出した」と
   いう意味なので存在しない —— **モデルが合っていない場所の目印**。
3. **染色ベクトルは装置ごとに違う**。既定値は Ruifrok & Johnston の公表値だが、
   H と DAB の角度は 37.1 度しか離れていない(内積 0.7979、完成した 3x3 の
   条件数 2.98)。**もともと悪条件**で、片方の濃い所がもう片方に漏れる。
4. ★★**残差チャネルは、平面内の誤りに完全に盲目**。H のベクトルを DAB の
   ほうへ ±20 度回すと、濃度の中央値は H 0.0471 -> 0.1348(**2.9 倍**)、
   DAB 0.3590 -> 0.1836(0.51 倍)と大きく動くのに、残差の絶対中央値は
   **0.0345 のまま 1 桁も動かない**。理由は幾何で言える —— 2 本の染色が
   張る平面は H を平面内で回しても変わらないので、平面に直交する残差は
   定義上動かない。**「あてはまりの良さ」を見張っているつもりの量が、
   いちばん起こりやすい誤り(ベクトルのずれ)だけを見ていない**。
5. ★★**回した染色自身の負率も盲目**。H を回しても H が負になる画素は
   **11.51 % で完全に不変**(これも幾何: H の双対ベクトルの向きは
   「DAB と残差に直交」で決まり、H を平面内で回しても向きは変わらない ——
   変わるのは長さだけなので、符号は 1 画素も変わらない)。
6. ★★**動くのは「もう一方」の負率だけ**。DAB が負になる画素は
   -20 度で 0.00 %、0 度で 0.18 %、+10 度で 7.66 %、+20 度で **30.38 %**。
   つまり **H のずれを見張れるのは DAB の負率**であって、H 自身の負率でも
   残差でもない。**見張り役は、自分ではなく相方を見る**。
   ただし単調なので**片側の上限しか出ない**(この画像では「公表値より
   +5 度以上ずれてはいない」までは言えるが、-20 度側は区別できない)。
7. **再構成は検算になる**。``clip=False`` で解いた濃度を
   :func:`fullseye.stain_recompose` に戻すと、最大誤差 1e-06(``eps`` の床)、
   中央 2.2e-16。**丸めていない限り往復は厳密**なので、「往復が合った」は
   モデルが正しい証拠にならない —— 4 節と同じ話で、
   **何を検算しているかを言わないと検算にならない**。

EXTEND: 自前のスライドに差し替えるなら :func:`load` を置き換えます。
**染色ベクトルは必ず測り直すこと** —— 単染色のスライドを撮って
:func:`fullseye.stain_vectors_from_patches` に通せば ``(K, 3)`` が出ます。
測り直せないときは、6 節のやり方(**相方の負率**を角度に対して掃く)で
公表値がどれだけずれているかを片側だけ絞れます。

出典: ``scikit-image`` 同梱の ``immunohistochemistry``
(No known copyright restrictions)。手法は A. C. Ruifrok & D. A. Johnston,
"Quantification of histochemical staining by color deconvolution",
*Anal. Quant. Cytol. Histol.* 23, 291 (2001)。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402
import realdata                                                  # noqa: E402

#: 使う染色の組(ヘマトキシリン + DAB)
PRESET = "H-DAB"

#: 染色ベクトルをずらす角度[度]。H を DAB のほうへ平面内で回す
ANGLES = (-20.0, -10.0, -5.0, -2.0, 0.0, 2.0, 5.0, 10.0, 20.0)


def load():
    """実写の免疫染色像。無ければ fail-closed で落ちる。"""
    return realdata.load_rgb("immunohistochemistry")


def base_vectors():
    """公表値を正規化して返す ``(2, 3)``。"""
    m = np.asarray(fs.STAIN_VECTORS[PRESET], np.float64)
    return m / np.linalg.norm(m, axis=1, keepdims=True)


def rotate_in_plane(m, deg):
    """1 本目を、2 本と直交する軸まわりに ``deg`` 度回す(= 平面内で回す)。"""
    axis = np.cross(m[0], m[1])
    axis = axis / np.linalg.norm(axis)
    t = np.radians(float(deg))
    v = m[0] * np.cos(t) + np.cross(axis, m[0]) * np.sin(t)
    return np.vstack([v / np.linalg.norm(v), m[1]])


def main() -> None:
    t0 = time.perf_counter()
    img = load()
    m = base_vectors()
    full = fs.specops._stain_matrix(PRESET)
    dot = float(m[0] @ m[1])

    print("実写の免疫染色像(scikit-image immunohistochemistry、%dx%d)" % img.shape[:2])
    print("  染色 %s / H·DAB = %.4f(角度 %.1f 度)/ 完成した 3x3 の条件数 %.2f"
          % (PRESET, dot, np.degrees(np.arccos(dot)), np.linalg.cond(full)))

    # --- 1 ----------------------------------------------------------------- #
    print("\n1. 合成では完璧に分かれる(線形代数としては正しい)")
    pure = []
    for k, nm in ((0, "H"), (1, "DAB")):
        conc = np.zeros((32, 32, 3))
        conc[..., k] = 1.0
        synth = np.asarray(fs.stain_recompose(conc, PRESET))
        got = np.asarray(fs.stain_unmix(synth, PRESET, clip=False))
        pure.append((nm, float(got[..., 0].mean()), float(got[..., 1].mean()),
                     float(got[..., 2].mean())))
        print("   %-3s だけ濃度 1.0 -> 回収 H %.4f / DAB %.4f / 残差 %.4f"
              % pure[-1])
    assert abs(pure[0][1] - 1.0) < 1e-9 and abs(pure[0][2]) < 1e-9, pure[0]
    assert abs(pure[1][2] - 1.0) < 1e-9 and abs(pure[1][1]) < 1e-9, pure[1]

    # --- 2 ----------------------------------------------------------------- #
    c0 = np.asarray(fs.stain_unmix(img, PRESET, clip=False))
    neg_h = 100.0 * float((c0[..., 0] < 0).mean())
    print("\n2. 実写では物理的にありえない値が出る")
    print("   濃度 H %.3f 〜 %.3f / DAB %.3f 〜 %.3f / 残差 %.3f 〜 %.3f"
          % (c0[..., 0].min(), c0[..., 0].max(), c0[..., 1].min(),
             c0[..., 1].max(), c0[..., 2].min(), c0[..., 2].max()))
    print("   H が負になる画素 %.2f %%(負の濃度は「色素が光を出した」の意味)"
          % neg_h)
    assert c0[..., 0].min() < -1.0 and neg_h > 1.0, (c0[..., 0].min(), neg_h)

    # --- 3-6 ---------------------------------------------------------------- #
    print("\n3-6. 染色ベクトルを平面内で回す(装置が違えばこれだけずれる)")
    print("     角度   H 中央   DAB 中央   残差|中央|   H が負   DAB が負")
    rows = []
    for d in ANGLES:
        c = np.asarray(fs.stain_unmix(img, rotate_in_plane(m, d), clip=False))
        rows.append((d, float(np.median(c[..., 0])), float(np.median(c[..., 1])),
                     float(np.median(np.abs(c[..., 2]))),
                     100.0 * float((c[..., 0] < 0).mean()),
                     100.0 * float((c[..., 1] < 0).mean())))
        print("     %+5.0f  %7.4f  %8.4f  %10.4f  %7.2f %%  %8.2f %%" % rows[-1])

    by_d = dict((r[0], r) for r in rows)
    h_med = np.array([r[1] for r in rows])
    resid = np.array([r[3] for r in rows])
    neg_a = np.array([r[4] for r in rows])
    neg_b = np.array([r[5] for r in rows])

    print("\n   H の中央値は %.4f -> %.4f(%.2f 倍)動く。"
          % (by_d[-20.0][1], by_d[20.0][1], by_d[20.0][1] / by_d[-20.0][1]))
    print("   ★残差の絶対中央値は %.4f 〜 %.4f(幅 %.3g)—— **1 桁も動かない**。"
          % (resid.min(), resid.max(), resid.max() - resid.min()))
    print("   ★回した染色 H 自身の負率も %.2f 〜 %.2f %%(幅 %.3g)—— **不変**。"
          % (neg_a.min(), neg_a.max(), neg_a.max() - neg_a.min()))
    print("   ★動くのは相方 DAB の負率だけ: %.2f %% -> %.2f %%(%.0f 倍)"
          % (by_d[-20.0][5], by_d[20.0][5],
             by_d[20.0][5] / max(by_d[2.0][5], 1e-9)))
    # 4 節: 残差は平面内の回転に対して定義上不変
    assert resid.max() - resid.min() < 1e-6, resid
    # 5 節: 回した染色自身の負率も不変(双対ベクトルの向きが変わらない)
    assert neg_a.max() - neg_a.min() < 1e-6, neg_a
    # 6 節: 相方の負率だけが動き、しかも単調
    assert np.all(np.diff(neg_b) >= -1e-9), neg_b
    assert by_d[20.0][5] > 20.0 and by_d[-20.0][5] < 0.01, (by_d[20.0][5], by_d[-20.0][5])
    assert abs(h_med[-1] / h_med[0] - 1.0) > 1.0, h_med

    # --- 7 ----------------------------------------------------------------- #
    rec = np.asarray(fs.stain_recompose(c0, PRESET))
    err = np.abs(rec - img)
    print("\n7. 再構成(clip しない濃度からの往復)")
    print("   最大誤差 %.3g / 中央 %.3g —— 往復が合っても、4 節の誤りは見えない"
          % (err.max(), np.median(err)))
    assert err.max() < 1e-4, err.max()

    # --- 図 ----------------------------------------------------------------- #
    def band(a):
        v = np.asarray(a, np.float64)
        lo, hi = np.quantile(v, 0.01), np.quantile(v, 0.99)
        return np.clip((v - lo) / max(hi - lo, 1e-9), 0, 1)

    cc = np.asarray(fs.stain_unmix(img, PRESET))
    figs.save_grid(
        "separation",
        [img, band(cc[..., 0]), band(cc[..., 1]), band(cc[..., 2])],
        ["実写(H + DAB)", "ヘマトキシリン", "DAB", "残差(どちらでもない)"],
        title="色分離 —— 残差は「どちらでもない量」を集める", ncols=2,
        caption="残差はモデルの外に出た量。だが平面内の誤りには盲目(下の図)。")

    c20 = np.asarray(fs.stain_unmix(img, rotate_in_plane(m, 20.0)))
    figs.save_grid(
        "blind",
        [band(cc[..., 0]), band(c20[..., 0]),
         band(np.abs(cc[..., 2])), band(np.abs(c20[..., 2]))],
        ["H(公表値)", "H(+20 度ずらした)",
         "残差(公表値)", "残差(+20 度ずらした)"],
        title="濃度は変わるのに、残差は変わらない", ncols=2,
        caption="H の中央値は %.4f -> %.4f。残差の絶対中央値は %.4f のまま。"
                % (by_d[0.0][1], by_d[20.0][1], by_d[0.0][3]))

    figs.save_plot(
        "diagnostics",
        [("残差 |中央| x100", list(ANGLES), [100 * r[3] for r in rows]),
         ("H が負 [%]", list(ANGLES), [r[4] for r in rows]),
         ("DAB が負 [%]", list(ANGLES), [r[5] for r in rows])],
        xlabel="染色ベクトルのずれ [度]", ylabel="見張り役の値",
        title="見張り役は、自分ではなく相方を見る",
        caption="残差と自分の負率は平坦。動くのは相方の負率だけ。")

    figs.save_table(
        "sweep",
        ["度", "H 中央", "DAB 中央", "残差", "DAB が負 [%]"],
        [["%+.0f" % d, "%.4f" % a, "%.4f" % b, "%.4f" % r, "%.2f" % nb]
         for d, a, b, r, _na, nb in rows],
        title="ベクトルをずらしたとき", col_w=105,
        caption="濃度は 2.9 倍動くのに残差は 4 桁目まで同じ。")

    print("\n所見")
    print("  * 合成なら完璧に分かれる(漏れ 0.0000)。実写では H が %.3f まで負に振れる。"
          % c0[..., 0].min())
    print("  * H と DAB は 37.1 度しか離れておらず、もともと悪条件(条件数 %.2f)。"
          % np.linalg.cond(full))
    print("  * ★残差は ±20 度で %.4f のまま動かない(平面内の回転に定義上不変)。"
          % resid[0])
    print("  * ★回した染色自身の負率も %.2f %% で不変。動くのは相方だけ"
          "(%.2f %% -> %.2f %%)。" % (neg_a[0], by_d[-20.0][5], by_d[20.0][5]))
    print("  * 往復の再構成は最大 %.3g —— 「往復が合った」は正しさの証拠ではない。"
          % err.max())
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
