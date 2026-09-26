# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""optics_four_f_processor — レンズに微分を計算させる(4f 光学プロセッサ)。

    py -3.11 examples/optics_four_f_processor.py
    py -3.11 examples/optics_four_f_processor.py --save four_f.png
    py -3.11 examples/optics_four_f_processor.py --morph morph.gif

【この例が解く問題】
2 枚のレンズの間に 1 枚フィルタを置くと、**光が空間微分を実行する**。GPU も
畳み込みカーネルも要らず、光が通り抜ける時間で終わる —— これが光コンピューティング
の最小構成である。この例は、その系が本当に微分になっていることを**閉形式の真値**
だけで確かめ、フィルタを連続に回すと出力が原画 → 1 階微分 → 2 階微分へ滑らかに
移る様子を動画にする。

【グラウンドトゥルース(外部の参照値を一つも使わない)】
1. 恒等フィルタ → 出力は入力の **180 度回転**。2 枚のレンズがそれぞれ*前向きの*
   フーリエ変換を行い ``F{F{u}}(x) = u(-x)`` だから。離散でも添字の写像
   ``n -> (-n) mod N`` で厳密。「フーリエ面で掛けるだけ」の計算との違いがここ。
2. ``(i2πf)^n`` → **n 階の空間微分**。ガウシアンの微分はエルミート多項式で
   閉形式に書けるので、そのまま採点できる。
3. 渦位相板 ``exp(imφ)`` の**巻き数が整数 m**(閉路上の位相差の和 / 2π)。
   浮動小数の計算なのに整数で採点できるのは、巻き数が位相的な量だから。
4. ``lowpass + highpass = 1``(同じ半径なら厳密に、境界の画素まで)。
5. ``|H| = 1`` のフィルタは総パワーを保つ(Parseval)。
6. 片側位相(ヒルベルト)は実数偶関数を**奇関数**に変える —— ただし偶数長の
   ナイキストのビンを 0 にしないと残差が出る(64x64 / w=8 で 1.6e-09、
   128x128 / w=14 で 4.1e-12 —— この例が構成つきで数字を出す)。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import optics as O  # noqa: E402

N = 128
PITCH = 1.0
W = 14.0


def _grid(n=N, pitch=PITCH):
    x = (np.arange(n) - n // 2) * pitch
    return np.meshgrid(x, x, indexing="xy")


def _gaussian():
    X, Y = _grid()
    return np.exp(-(X * X + Y * Y) / (W * W)), X, Y


def _rot180(a):
    return np.roll(a[::-1, ::-1], 1, axis=(0, 1))


def _hermite_derivative(order, X, u):
    """ガウシアン ``exp(-x^2/w^2)`` の x 方向 n 階微分(閉形式)。"""
    t = X / W
    herm = {1: 2.0 * t, 2: 4.0 * t * t - 2.0, 3: 8.0 * t ** 3 - 12.0 * t}[order]
    return (-1.0 / W) ** order * herm * u


def _test_target(n=N):
    """検分しやすい合成標的: 斜めのエッジ・細線・点・円。

    ★乱数では作らない —— 一様・対称な入力は、軸の取り違えや反転の抜けを隠す。
    """
    X, Y = _grid(n)
    img = np.zeros((n, n), dtype=float)
    img[(X + Y) > 12.0] = 1.0                       # 斜めのエッジ
    img[np.abs(X + 26.0) < 1.0] = 1.0               # 細い縦線
    img[(X - 30.0) ** 2 + (Y + 28.0) ** 2 < 9.0] = 1.0   # 点
    r = np.sqrt((X + 24.0) ** 2 + (Y - 26.0) ** 2)
    img[(r > 9.0) & (r < 12.0)] = 1.0               # 円環
    return img


def report():
    u, X, _ = _gaussian()
    # ★数字は構成で変わる。どの構成で測ったかを必ず併記する —— 併記しないと
    #   説明文が別の実行の数字を引いたまま残る(2026-09-26 にこの例で踏んだ)。
    print("構成: %d x %d 画素、画素ピッチ %.1f um、ガウシアン半幅 w = %.1f"
          % (N, N, PITCH, W))

    print("=== 1. 4f 系は結像するが、像は 180 度回る ===")
    ident = O.four_f_filter(u, O.fourier_plane_filter(N, "identity"))
    print("  恒等フィルタの出力 vs 入力の 180 度回転 : 最大絶対差 %.2g" %
          np.abs(ident - _rot180(u)).max())
    print("  (ビット一致ではない —— FFT の往復が 1e-16 の屑を乗せる)")
    blocked = O.four_f_filter(u, O.fourier_plane_filter(N, "block"))
    print("  フーリエ面を塞いだ出力の最大絶対値     : %.17g  ← 厳密にゼロ" %
          np.abs(blocked).max())

    print("\n=== 2. レンズが微分を計算する(真値 = ガウシアン微分の閉形式) ===")
    c = slice(12, -12)
    for order in (1, 2, 3):
        h = O.fourier_plane_filter(N, "derivative_x", order=order,
                                   pixel_pitch_um=PITCH)
        got = O.four_f_filter(u, h, invert=False).real
        truth = _hermite_derivative(order, X, u)
        rel = np.abs(got[c, c] - truth[c, c]).max() / np.abs(truth).max()
        print("  %d 階微分 : 相対誤差 %.2g" % (order, rel))
    print("  高階ほど誤差が増えるのは、ガウシアンが厳密に帯域制限されていない分")
    print("  (打ち切り)が階数で増幅されるから —— レンズの性能ではなく標本化の話。")

    print("\n=== 3. 渦位相板の巻き数は整数(浮動小数でも整数で採点できる) ===")
    for m in (1, 2, -3, 5):
        h = O.fourier_plane_filter(N, "vortex", charge=m)
        t = np.linspace(0.0, 2.0 * np.pi, 1441, endpoint=False)
        r = 20
        ii = np.round(r * np.sin(t)).astype(int) % N
        jj = np.round(r * np.cos(t)).astype(int) % N
        ph = np.angle(h[ii, jj])
        d = np.diff(np.concatenate([ph, ph[:1]]))
        d = (d + np.pi) % (2.0 * np.pi) - np.pi
        print("  charge = %+d -> 巻き数 %.9f" % (m, d.sum() / (2.0 * np.pi)))

    print("\n=== 4. 相補なフィルタは厳密に 1 に足される ===")
    for frac in (0.1, 0.25, 0.5, 1.0):
        lp = O.fourier_plane_filter(N, "lowpass", radius_frac=frac)
        hp = O.fourier_plane_filter(N, "highpass", radius_frac=frac)
        print("  radius_frac = %.2f : max|lowpass + highpass - 1| = %.17g"
              % (frac, np.abs(lp + hp - 1.0).max()))
    print("  境界の画素をどちらに入れるかが 2 通りあると、ここは厳密に 1 にならない")
    print("  —— だから補集合は op の中で作る(呼び出し側に 1 - lowpass を書かせない)。")

    print("\n=== 5. 位相だけのフィルタはパワーを保つ(Parseval) ===")
    fy = np.fft.fftfreq(N, d=PITCH)[:, None]
    fx = np.fft.fftfreq(N, d=PITCH)[None, :]
    h = np.exp(-2j * np.pi * (3.0 * fx + 5.0 * fy))
    out = O.four_f_filter(u, h, invert=False)
    p_in = float((np.abs(u) ** 2).sum())
    print("  |H| = 1 の平行移動フィルタ : 相対パワー変化 %.2g"
          % (abs(float((np.abs(out) ** 2).sum()) - p_in) / p_in))

    print("\n=== 6. ナイキストのビン —— 1 画素が対称性を桁で壊す ===")
    hh = O.fourier_plane_filter(N, "hilbert_x")
    o1 = O.four_f_filter(u, hh, invert=False)
    print("  片側位相の出力の奇対称の残差        : %.2g" %
          np.abs(o1 + np.roll(o1[:, ::-1], 1, axis=1)).max())
    broken = hh.copy()
    broken[:, N // 2] = -1j * (-1.0)      # ナイキスト列を戻す(欠陥を再現)
    o2 = O.four_f_filter(u, broken, invert=False)
    print("  ナイキスト列を残した場合(欠陥)    : %.2g" %
          np.abs(o2 + np.roll(o2[:, ::-1], 1, axis=1)).max())
    print("  fftfreq は偶数長で -1/2 だけを返し、対になる +1/2 が無い。")
    print("  この 1 列を 0 にしないと、片側位相は奇対称を厳密に満たさない。")
    print("  ★壊れ方の大きさは構成で変わる: 64x64 / w=8 なら 2.3e-16 -> 1.6e-09")
    print("    (7 桁)、この 128x128 / w=14 では 4 桁。標本が細かいほど")
    print("    ナイキスト付近に載る中身が減るので、差は小さく出る。")


def save_figure(path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    img = _test_target()
    kinds = [("identity", {}), ("derivative_x", {"order": 1}),
             ("derivative_y", {"order": 1}), ("laplacian", {}),
             ("hilbert_x", {}), ("vortex", {"charge": 1}),
             ("lowpass", {"radius_frac": 0.12}), ("highpass", {"radius_frac": 0.12})]
    fig, ax = plt.subplots(3, 3, figsize=(9.6, 9.6))
    ax[0, 0].imshow(img, cmap="gray"); ax[0, 0].set_title("入力(合成標的)")
    for a, (kind, kw) in zip(ax.ravel()[1:], kinds):
        h = O.fourier_plane_filter(N, kind, pixel_pitch_um=PITCH, **kw)
        out = np.abs(O.four_f_filter(img, h, invert=False))
        a.imshow(out, cmap="magma")
        a.set_title("%s%s" % (kind, (" " + str(kw)) if kw else ""), fontsize=9)
    for a in ax.ravel():
        a.set_xticks([]); a.set_yticks([])
    fig.suptitle("4f 光学プロセッサ —— フーリエ面の 1 枚が計算を決める")
    plt.tight_layout()
    plt.savefig(path, dpi=90, bbox_inches="tight")
    plt.close()
    print("図を書いた: %s" % path)


def save_morph(path, frames=48):
    """★動きが本質: 微分の階数を**連続に**上げると出力が滑らかに移る。

    ``H = (i2πf)^s`` の指数 s を実数にすると分数階微分になる。0 → 1 → 2 と
    通すと、原画 → 縁 → 2 階微分へ途切れずに変わる。静止画では「3 枚の別の絵」
    にしか見えないものが、連続な 1 本の族であることが目で分かる。
    """
    import imageio.v2 as imageio

    img = _test_target()
    fy = np.fft.fftfreq(N, d=PITCH)[:, None]
    fx = np.fft.fftfreq(N, d=PITCH)[None, :]
    seq = []
    for k in range(frames):
        s = 2.0 * k / (frames - 1)                      # 0 → 2 階
        with np.errstate(divide="ignore", invalid="ignore"):
            # ★(1, N) のまま渡すと four_f_filter が「2x2 未満」で断る。
            #   場と同じ格子に広げる —— 断ってくれる op のおかげで気づけた。
            h = (2j * np.pi * fx) ** s * np.ones((N, 1))
        h = np.asarray(h, dtype=np.complex128)
        h[~np.isfinite(h)] = 0.0
        out = np.abs(O.four_f_filter(img, h, invert=False))
        m = out.max()
        seq.append((255.0 * out / m if m > 0 else out).astype(np.uint8))
    imageio.mimsave(path, seq, duration=0.06, loop=0)
    print("動画を書いた: %s (%d フレーム、分数階微分 0 -> 2)" % (path, frames))


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--save", metavar="PNG", help="8 種のフィルタの出力を 1 枚に")
    p.add_argument("--morph", metavar="GIF", help="分数階微分 0->2 の連続変化")
    a = p.parse_args()
    report()
    # ★図・動画は opt-in。既定で出さないのは、CI が図の生成時間を払わないため。
    if a.save:
        save_figure(a.save)
    if a.morph:
        save_morph(a.morph)
    return 0


if __name__ == "__main__":
    sys.exit(main())
