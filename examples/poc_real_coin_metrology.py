# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""実写のコイン写真で数えて測る —— 当たっている答えに、余裕があるとは限らない。

``scikit-image`` 同梱の ``coins``(ポンペイ出土のギリシャ硬貨、303x384)は
「照明が斜めに落ちているので大域しきい値では駄目」という例として有名です。
実際に背景を測ると、行方向で 0.427 -> 0.161、列方向で 0.331 -> 0.059 と
はっきり傾いています。ところが**素の大域 Otsu は 24 枚をちょうど当てます**。

この PoC が言いたいのは「有名な話は嘘だった」ではありません。
**当たっている答えを見ても、余裕がどれだけあるかは分からない**、です。
勾配をあと 0.05 足すだけで 24 -> 22 に落ちますし、枚数が合っている状態でも
個々の面積は最大 46 % ずれ、そのずれは**画面の上下と r = -0.90 で相関します**。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **真値は 24 枚**。決め方を 1 つに頼らない —— (a) 面積の平坦域:
   面積のしきいを 50 から 800 まで 16 倍動かしても 24 のまま(0 なら 96、
   1200 なら 18 なので、平坦域は本物)、(b) 独立な経路として Hough 円
   変換が投票のしきい 0.30〜0.50 で 24 個、(c) Sobel + 穴埋めでも 24。
   **3 つが一致したものを真値と呼ぶ**。
2. **有名な照明勾配は、数え上げを壊していない**。素の大域 Otsu + 穴埋め +
   面積 150 で 24 枚ちょうど。前処理は要らなかった。
3. ★★**当たっているが、余裕が無い**。同じ形の勾配を上から足していくと、
   +0.05 で早くも 24 -> 22 枚。つまり実写はすでに崖の縁に立っており、
   **答えが合っていることは余裕があることの証明にならない**。
   崖は幾何から予測できる: いちばん暗い側のコインと背景の差が、
   大域しきい値をまたぐところで落ちる。
4. ★★**中央値は動かないのに、個々は 46 % ずれる**。勾配 +0.30 のとき
   面積の中央値は -0.27 % しか動かないのに、いちばん動いたコインは
   -24.20 %、+0.40 では -46.02 %。**代表値で報告すると、壊れているのに
   壊れていないように見える**。
5. ★★**誤差には位置の指紋がある**。面積のずれと行位置の相関は
   +0.05 で -0.878、+0.10 で -0.901。真の面積は画面のどこに置いたかに
   依らないので、**この相関はまるごと誤差**。1 つの数字(中央値・CV)に
   まとめると消えるが、位置に対して並べると一目で出る。
6. ★**「前処理を足せば安全」ではない**。``gray_tophat`` で背景を落とすと
   枚数は 23 枚と 1 枚落ち、しかも面積の中央値が 1501 -> 428 と
   **3.5 分の 1 になる**(既定の構造要素がコインの内側まで削るため)。
   勾配 +0.40 では素の 19 枚に対し 23 枚と粘るが、そのときの面積は
   -23.4 %。**枚数の頑健さと寸法の頑健さは別の話**で、片方だけ見て
   「効いた」と言ってはいけない。
7. **「blob の個数」は規約を言わないと数字にならない**。同じ二値画像で
   4 近傍なら 126、8 近傍(``blob_label`` / ``blob_count`` の既定)なら 96。
   3 割違う。面積で絞る前の生の個数を報告するときは、必ず近傍を添える。
8. ★**もっともらしい追加条件が精度を下げる**。「コインは丸いのだから
   円形度で絞ろう」とすると 24 -> 21 枚。接している 2 枚と縁が欠けた 1 枚が
   落ちる。**円形度は真値に近づける道具ではなく、別の仮定**。

EXTEND: 自前の撮影に差し替えるなら :func:`load` を置き換えます。真値の枚数が
無い場合、1 節は使えませんが 3〜5 節(既知の勾配を足して、答えがどれだけ動くか)
はそのまま回せます —— **真値が無くても「余裕」は測れる**、というのがこの PoC の
持ち帰りどころです。

出典: ``scikit-image`` 同梱の ``coins``(No known copyright restrictions)。
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

L = fs.ledger

#: 面積のしきい[px^2]。1 節の平坦域から選ぶ(50〜800 のどこでも同じ答え)
AREA_MIN = 150.0

#: 真値。1 節で 3 つの独立な経路の一致として確かめる
TRUE_N = 24


def load():
    """実写のコイン写真。無ければ fail-closed で落ちる。"""
    return realdata.load_gray("coins")


def segment(a, flatten=False):
    """大域 Otsu -> 穴埋め -> 連結成分 -> 特徴量。返すのは ``(特徴, 採用, マスク)``。"""
    if flatten:
        a = np.asarray(fs.run_pipeline(a, ["gray_tophat"]))
    m = np.asarray(fs.run_pipeline(a, ["otsu"])) > 0.5
    m = np.asarray(fs.run_pipeline(m.astype(np.float64), ["fill_holes"])) > 0.5
    f = L.blob_features(np.asarray(L.blob_label(m)))
    return f, f["area"] >= AREA_MIN, m


def gradient_of(a):
    """背景(各行・各列の暗いほう 4 割)の中央値で照明の傾きを測る。"""
    rows = np.array([np.median(r[r <= np.quantile(r, 0.4)]) for r in a])
    cols = np.array([np.median(c[c <= np.quantile(c, 0.4)]) for c in a.T])
    return rows, cols


# --------------------------------------------------------------------------- #
# 1. 真値を 3 つの独立な経路の一致で決める
# --------------------------------------------------------------------------- #
def section_truth(img):
    f, _k, m = segment(img)
    plateau = [(a, int((f["area"] >= a).sum()))
               for a in (0, 50, 100, 150, 200, 400, 800, 1200)]

    # (b) Hough 円変換 —— 投票のしきいを振っても同じ数になるか
    acc = np.asarray(fs.run_pipeline(img, ["hough_circle_trans"]), np.float64)
    hough = []
    for k in (0.30, 0.35, 0.40, 0.45, 0.50):
        pk = acc >= k * acc.max()
        lab, n = ndi.label(pk, structure=np.ones((3, 3)))
        # 1 個の円が複数の峰に割れないよう、面積 1 の点は峰として数えない
        sz = ndi.sum(pk, lab, range(1, n + 1))
        hough.append((k, int((sz >= 1).sum())))

    # (c) 勾配の大きさ(Sobel)からの閉領域 —— しきいの決め方が (a) と独立
    edge = np.asarray(fs.run_pipeline(img, ["sobel_amp"]), np.float64)
    em = np.asarray(fs.run_pipeline(edge, ["otsu"])) > 0.5
    em = ndi.binary_fill_holes(em)
    fe = L.blob_features(np.asarray(L.blob_label(em)))
    n_sobel = int((fe["area"] >= AREA_MIN).sum())
    return plateau, hough, n_sobel, f, m


# --------------------------------------------------------------------------- #
# 3-5. 勾配を足して余裕を測る
# --------------------------------------------------------------------------- #
def section_margin(img):
    H, W = img.shape
    ramp = np.linspace(0.0, 1.0, H)[:, None] * np.ones((1, W))
    f0, k0, _m = segment(img)
    cen0 = np.stack([f0["row"][k0], f0["col"][k0]], 1)
    a0 = f0["area"][k0]
    rows = []
    for g in (0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40):
        a = np.clip(img * (1.0 - g * ramp), 0.0, 1.0)
        f, k, _m2 = segment(a)
        cen = np.stack([f["row"][k], f["col"][k]], 1)
        ar = f["area"][k]
        rel, pos = [], []
        for c0, aa0 in zip(cen0, a0):
            if not len(cen):
                continue
            d = np.hypot(*(cen - c0).T)
            j = int(np.argmin(d))
            if d[j] < 8.0:                      # 同じコインとみなす距離
                rel.append(ar[j] / aa0 - 1.0)
                pos.append(c0[0])
        rel = np.asarray(rel)
        worst = float(rel[np.argmax(np.abs(rel))]) if len(rel) else float("nan")
        corr = (float(np.corrcoef(pos, rel)[0, 1])
                if len(rel) > 3 and rel.std() > 0 else float("nan"))
        rows.append((g, int(k.sum()), len(rel),
                     float(np.median(rel)) if len(rel) else float("nan"),
                     worst, corr))
    return rows


# --------------------------------------------------------------------------- #
# 6. 前処理を足すとどうなるか
# --------------------------------------------------------------------------- #
def section_flatten(img):
    H, W = img.shape
    ramp = np.linspace(0.0, 1.0, H)[:, None] * np.ones((1, W))
    f0, k0, _m = segment(img)
    f0f, k0f, _mf = segment(img, flatten=True)
    base, basef = np.median(f0["area"][k0]), np.median(f0f["area"][k0f])
    rows = []
    for g in (0.0, 0.20, 0.40, 0.60, 0.80):
        a = np.clip(img * (1.0 - g * ramp), 0.0, 1.0)
        f, k, _ = segment(a)
        ff, kf, _ = segment(a, flatten=True)
        rows.append((g, int(k.sum()),
                     100.0 * (np.median(f["area"][k]) / base - 1.0) if k.any() else float("nan"),
                     int(kf.sum()),
                     100.0 * (np.median(ff["area"][kf]) / basef - 1.0) if kf.any() else float("nan")))
    return base, basef, rows


def main() -> None:
    t0 = time.perf_counter()
    img = load()
    rows_bg, cols_bg = gradient_of(img)
    print("実写のコイン写真(scikit-image coins、%dx%d)" % img.shape)
    print("  背景の傾き: 行 %.3f -> %.3f / 列 %.3f -> %.3f"
          % (rows_bg[0], rows_bg[-1], cols_bg[0], cols_bg[-1]))

    # --- 1 ---------------------------------------------------------------- #
    plateau, hough, n_sobel, f, mask = section_truth(img)
    print("\n1. 真値を 3 つの独立な経路の一致で決める")
    print("   (a) 面積の平坦域: "
          + " / ".join("%d->%d" % p for p in plateau))
    print("   (b) Hough 円: " + " / ".join("%.2f->%d" % h for h in hough))
    print("   (c) Sobel + 穴埋め: %d" % n_sobel)
    flat_counts = set(n for a, n in plateau if 50 <= a <= 800)
    hough_counts = set(n for _k, n in hough)
    print("   -> 平坦域 %s / Hough %s / Sobel %d"
          % (sorted(flat_counts), sorted(hough_counts), n_sobel))
    assert flat_counts == {TRUE_N}, plateau
    assert hough_counts == {TRUE_N}, hough
    assert n_sobel == TRUE_N, n_sobel

    # --- 2 ---------------------------------------------------------------- #
    k = f["area"] >= AREA_MIN
    print("\n2. 有名な照明勾配は、数え上げを壊していない")
    print("   素の大域 Otsu + 穴埋め + 面積 %.0f -> %d 枚(真値 %d)"
          % (AREA_MIN, int(k.sum()), TRUE_N))
    print("   面積 %.0f 〜 %.0f(中央 %.0f)/ 直径 %.1f 〜 %.1f px"
          % (f["area"][k].min(), f["area"][k].max(), np.median(f["area"][k]),
             f["equiv_diameter"][k].min(), f["equiv_diameter"][k].max()))
    assert int(k.sum()) == TRUE_N, int(k.sum())

    # --- 3-5 -------------------------------------------------------------- #
    marg = section_margin(img)
    print("\n3-5. 勾配を足して余裕を測る(真の枚数も面積も変わらないはず)")
    print("   足す勾配  枚数  照合  面積の中央変化  最悪のコイン  行位置との相関")
    for g, n, mm, med, worst, corr in marg:
        print("   %+.2f     %3d   %3d   %+7.2f %%      %+7.2f %%     %s"
              % (g, n, mm, 100 * med, 100 * worst,
                 "  ----" if not np.isfinite(corr) else "%+.3f" % corr))
    by_g = dict((g, (n, med, worst, corr)) for g, n, _m, med, worst, corr in marg)
    assert by_g[0.0][0] == TRUE_N, by_g[0.0]
    assert by_g[0.05][0] < TRUE_N, by_g[0.05]          # 余裕が 0.05 しかない
    assert abs(by_g[0.30][1]) < 0.01, by_g[0.30]       # 中央値は動かない
    assert abs(by_g[0.30][2]) > 0.20, by_g[0.30]       # 個々は 20 % 以上ずれる
    assert by_g[0.05][3] < -0.8 and by_g[0.10][3] < -0.8, (by_g[0.05], by_g[0.10])

    # --- 6 ---------------------------------------------------------------- #
    base, basef, flat = section_flatten(img)
    print("\n6. 前処理(gray_tophat)を足すとどうなるか")
    print("   勾配 0 での面積の中央: 素 %.0f / 平坦化 %.0f(%.2f 倍)"
          % (base, basef, basef / base))
    for g, n, dm, nf, dmf in flat:
        print("   +%.2f  素 n=%2d 面積 %+6.1f %%  |  平坦化 n=%2d 面積 %+6.1f %%"
              % (g, n, dm, nf, dmf))
    assert basef < 0.5 * base, (base, basef)           # 寸法を壊す
    assert flat[2][3] > flat[2][1], flat[2]            # 枚数だけは粘る

    # --- 7 ---------------------------------------------------------------- #
    n4 = ndi.label(mask)[1]
    n8 = int(np.asarray(L.blob_label(mask)).max())
    n_op = float(np.asarray(fs.run_pipeline(mask.astype(np.float64),
                                            ["blob_count"])))
    print("\n7. 「blob の個数」は規約を言わないと数字にならない")
    print("   4 近傍 %d / 8 近傍 %d / blob_count op %.0f(= 8 近傍)"
          % (n4, n8, n_op))
    assert n8 == int(n_op) and n4 > n8, (n4, n8, n_op)

    # --- 8 ---------------------------------------------------------------- #
    print("\n8. もっともらしい追加条件が精度を下げる")
    circ_rows = []
    for c in (0.5, 0.6, 0.7, 0.8, 0.9):
        n = int((k & (f["circularity"] >= c)).sum())
        circ_rows.append((c, n))
    print("   円形度で絞る: " + " / ".join("%.1f->%d" % c for c in circ_rows))
    assert circ_rows[2][1] < TRUE_N, circ_rows        # 0.7 で真値を割る

    # --- 図 ---------------------------------------------------------------- #
    lab = np.asarray(L.blob_label(mask))
    keep_ids = f["label"][k]
    kept = np.isin(lab, keep_ids)
    figs.save_grid(
        "scene",
        [img, mask.astype(np.float64), kept.astype(np.float64)],
        ["実写(背景が斜めに暗い)", "大域 Otsu + 穴埋め",
         "面積 %.0f で絞った %d 枚" % (AREA_MIN, int(k.sum()))],
        title="有名な照明勾配は、数え上げを壊していない", ncols=3,
        caption="背景は行 %.3f -> %.3f。それでも素の大域 Otsu が真値 %d 枚を当てる。"
                % (rows_bg[0], rows_bg[-1], TRUE_N))

    H, W = img.shape
    ramp = np.linspace(0.0, 1.0, H)[:, None] * np.ones((1, W))
    figs.save_grid(
        "margin",
        [img, np.clip(img * (1.0 - 0.05 * ramp), 0, 1),
         np.clip(img * (1.0 - 0.30 * ramp), 0, 1)],
        ["そのまま(%d 枚)" % by_g[0.0][0],
         "+0.05(%d 枚)" % by_g[0.05][0],
         "+0.30(%d 枚)" % by_g[0.30][0]],
        title="答えが合っていても、余裕は 0.05 しかない", ncols=3,
        caption="見た目はほとんど変わらないのに 2 枚落ちる。")

    figs.save_plot(
        "drift",
        [("面積の中央変化 [%]", [g for g, *_ in marg],
          [100 * med for _g, _n, _m, med, _w, _c in marg]),
         ("最悪のコイン [%]", [g for g, *_ in marg],
          [100 * w for _g, _n, _m, _med, w, _c in marg])],
        xlabel="足した勾配", ylabel="面積の変化 [%]",
        title="中央値は動かないのに、個々は 46 % ずれる",
        caption="代表値で報告すると、壊れているのに壊れていないように見える。")

    figs.save_table(
        "truth",
        ["決め方", "結果"],
        [["面積の平坦域 (50〜800)", "%d 枚" % sorted(flat_counts)[0]],
         ["Hough 円 (投票 0.30〜0.50)", "%d 個" % sorted(hough_counts)[0]],
         ["Sobel + 穴埋め", "%d 枚" % n_sobel],
         ["4 近傍で数えた生の個数", "%d" % n4],
         ["8 近傍で数えた生の個数", "%d" % n8]],
        title="真値は 3 つの独立な経路の一致で決める",
        caption="生の個数は近傍の規約で 3 割違う。")

    print("\n所見")
    print("  * 真値 %d 枚を面積の平坦域・Hough・Sobel の 3 経路が一致で示す。"
          % TRUE_N)
    print("  * 素の大域 Otsu が %d 枚を当てる。前処理は要らなかった。"
          % int(k.sum()))
    print("  * ただし余裕は 0.05 —— 勾配をわずかに足すと %d 枚に落ちる。"
          % by_g[0.05][0])
    print("  * +0.30 で中央値は %+.2f %% しか動かないのに、最悪のコインは "
          "%+.2f %%。誤差は行位置と相関 %+.3f(+0.10 のとき)。"
          % (100 * by_g[0.30][1], 100 * by_g[0.30][2], by_g[0.10][3]))
    print("  * gray_tophat は枚数を粘らせるが面積を %.2f 倍にする。"
          % (basef / base))
    print("  * 生の連結成分は 4 近傍 %d / 8 近傍 %d。円形度 0.7 で絞ると %d 枚。"
          % (n4, n8, circ_rows[2][1]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
