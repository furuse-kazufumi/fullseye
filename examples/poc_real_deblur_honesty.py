# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""実写のブレを取る —— 指標を変えると勝者が 3 通りに入れ替わる。

真値を**実写そのもの**にして、劣化だけ自分で作ります(``scikit-image`` 同梱の
``camera``、CC0。長さ 11 px・角 20 度の直線ブレ + σ=0.004 の雑音)。
こうすると **本物の細部**に対して「どれだけ戻せたか」を dB で言えます ——
合成の格子模様やガウシアン斑点では出ない、実写の細かい枝や手すりが相手です。

この PoC が言いたいのは「脱畳み込みは効かない」ではありません。
**何を良いとするかを決めないと、どれが良いかは決まらない**、です。
同じ 7 通りの結果に 3 つの物差しを当てると、**3 つとも違う勝者**が出ます。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点は強い**。何もしない(ブレたまま)で PSNR **24.04 dB**。
   既定に近い ``nsr=0.005`` の Wiener は 23.66 dB で、**ゼロ点に負ける**。
2. ★★**相手を弱く見せない**。1 節で止めると「Wiener は駄目」と書けてしまう。
   ``nsr`` を振ると 0.0005 で 19.18 dB、0.02 で **25.40 dB** —— 正しく調整した
   Wiener はゼロ点を **+1.36 dB** 上回る。**ノブを固定した比較は比較ではない**。
3. ★★**ノブのほうが手法より効く**。``nsr`` を動かすだけで 19.18 -> 25.40 dB
   (**6.22 dB**)動くのに対し、「脱畳み込みをするかしないか」の差は 1.36 dB。
   **4.6 倍**。疑似カラーで「配色より写し方が効く」と出たのと同じ形。
4. ★★**指標を変えると勝者が入れ替わる —— 3 つの物差しに 3 人の勝者**。
   7 通りの結果に同じ 3 指標を当てると、**別々の手法**が 1 位になる。
   * **PSNR**(真値に近いか)—— 正しい PSF の Wiener、25.40 dB。
   * **勾配エネルギー**(鋭く見えるか)—— ``iv_motion_deblur`` の 0.2986。
     この手法の PSNR は 20.42 dB で **7 手法中 6 位**、PSNR の 1 位より
     **-4.98 dB**。しかもその絵の勾配は**真値 0.1936 の 1.54 倍**で、
     ★**真値より鋭い絵が「いちばん良い」と選ばれる**。
   * **``sk_blur_effect``**(参照なしのぼけ推定)—— ``iv_unsharp_deblur`` が
     0.2946。この手法の PSNR は 22.14 dB で 5 位、1 位より **-3.26 dB**。
   ★この指標の名誉のために書いておくと、**真値そのものは 0.2885 で
   全手法より良い**と正しく判定している —— つまり ``blur_effect`` は
   「ぼけているか」は測れていて、それでも **選ばせると 3.26 dB 損をする**。
   **鋭さは真値への近さの代理にならない**。絵を見て選ぶ、も同じ穴に落ちる。
5. ★**間違った PSF は、中身が大きく悪くなるのに見た目は良くなる**。
   長さを 11 -> 21 px と間違えると PSNR は **18.56 dB**(正しい 25.40 から
   -6.84 dB、何もしない 24.04 dB より -5.48 dB)。なのに勾配エネルギーは
   0.2649 と真値の 1.37 倍で、「よく効いた」ように見える。
6. ★**崖(雑音)**。正しい PSF でも、雑音が増えると利得は消える ——
   σ=0 で +1.52 dB、0.004 で +1.36、0.008 で +0.91、**0.016 で +0.05 dB**。
   1.6 % の雑音で「脱畳み込みをする意味」がゼロになる。
7. ★**崖(ブレ長)は両端で落ちる**。利得は L=3 で +0.86、L=5 で **+1.59**(最大)、
   L=11 で +1.36、L=25 で +0.52。**小さいブレは取るものが無く、大きいブレは
   情報が消えている** —— 中間にだけ意味がある、というのは先に予想できる。

EXTEND: 自前の撮影に差し替えるなら :func:`load` を置き換えます。**本物の
ブレ写真**を使う場合、真値が無いので 1〜3・5〜7 節の dB は測れません
(測れるのは 4 節の鋭さ指標だけ)—— そして 4 節が言うとおり、
**鋭さ指標だけで選ぶと真値から遠いほうを選ぶ**。だから実務では
「真値が撮れる条件(三脚 + 短時間露光)を 1 枚だけ撮って、劣化は自分で作る」
のがいちばん強い。この PoC の構成そのものが、その手順です。

出典: ``scikit-image`` 同梱の ``camera``(CC0、撮影 Lav Varshney)。
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

#: 仕込む劣化(長さ[px] / 角度[度] / 雑音の σ)
BLUR_LEN, BLUR_DEG, NOISE = 11, 20.0, 0.004

#: ``nsr`` の掃引(Wiener の正則化ノブ)
NSR_GRID = (0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1)

#: 既定に近い、よく使われてしまう値
NSR_NAIVE = 0.005


def load():
    """真値にする実写。無ければ fail-closed で落ちる。"""
    return realdata.load_gray("camera")


def motion_psf(length, angle_deg):
    """直線ブレの点像分布 ``(2L+1, 2L+1)``、総和 1。"""
    L = int(length)
    size = 2 * L + 1
    k = np.zeros((size, size), np.float64)
    c = size // 2
    t = np.radians(float(angle_deg))
    for i in range(L):
        d = i - (L - 1) / 2.0
        k[int(round(c - d * np.sin(t))), int(round(c + d * np.cos(t)))] += 1.0
    return k / k.sum()


def degrade(truth, length=BLUR_LEN, angle=BLUR_DEG, sigma=NOISE, seed=3):
    """真値に**既知の**ブレと雑音を掛ける。返すのは ``(劣化画像, PSF)``。"""
    p = motion_psf(length, angle)
    b = ndi.convolve(truth, p, mode="reflect")
    rng = np.random.default_rng(seed)
    return np.clip(b + rng.normal(0.0, float(sigma), b.shape), 0.0, 1.0), p


def psnr(a, truth):
    e = np.clip(np.asarray(a, np.float64), 0.0, 1.0) - truth
    return float(10.0 * np.log10(1.0 / max(float((e ** 2).mean()), 1e-20)))


def grad_energy(a):
    v = np.clip(np.asarray(a, np.float64), 0.0, 1.0)
    return float(np.hypot(ndi.sobel(v, 0), ndi.sobel(v, 1)).mean())


def blur_effect(a):
    """参照なしのぼけ推定(0 = 鋭い .. 1 = ぼけている)。"""
    return float(np.asarray(fs.apply(np.clip(np.asarray(a, np.float64), 0, 1),
                                     "sk_blur_effect")))


def best_wiener(blur, psf, truth):
    """``nsr`` を振って**いちばん良い**結果を返す(相手を弱く見せないため)。"""
    out = []
    for nsr in NSR_GRID:
        r = fs.cx_wiener_deconvolve(blur, psf, nsr=nsr)
        out.append((nsr, psnr(r, truth), r))
    nsr, val, img = max(out, key=lambda t: t[1])
    return nsr, val, img, [(n, v) for n, v, _r in out]


def main() -> None:
    t0 = time.perf_counter()
    truth = load()
    blur, psf = degrade(truth)
    null_db = psnr(blur, truth)

    print("真値 = 実写(scikit-image camera、%dx%d、CC0)" % truth.shape)
    print("  仕込んだ劣化: 直線ブレ %d px / %.0f 度 + 雑音 σ=%.3f"
          % (BLUR_LEN, BLUR_DEG, NOISE))
    print("  ゼロ点(何もしない)%.2f dB" % null_db)

    # --- 1, 2, 3 ------------------------------------------------------------ #
    naive = psnr(fs.cx_wiener_deconvolve(blur, psf, nsr=NSR_NAIVE), truth)
    nsr_best, wien_db, wien, sweep = best_wiener(blur, psf, truth)
    lo = min(v for _n, v in sweep)
    print("\n1-3. ノブを固定した比較は比較ではない")
    print("   nsr=%.4f(よく使われる値)で %.2f dB —— ゼロ点 %.2f dB に%s"
          % (NSR_NAIVE, naive, null_db, "負ける" if naive < null_db else "勝つ"))
    for n, v in sweep:
        print("     nsr=%.4f  %6.2f dB%s" % (n, v, "  <- 最良" if n == nsr_best else ""))
    print("   最良 nsr=%.4f で %.2f dB(ゼロ点比 %+.2f dB)"
          % (nsr_best, wien_db, wien_db - null_db))
    print("   ★ノブで動く幅 %.2f dB に対し、脱畳み込みの利得は %.2f dB —— %.1f 倍"
          % (wien_db - lo, wien_db - null_db,
             (wien_db - lo) / max(wien_db - null_db, 1e-9)))
    assert naive < null_db, (naive, null_db)          # 固定ノブでは負ける
    assert wien_db > null_db, (wien_db, null_db)      # 振れば勝つ
    assert (wien_db - lo) > 3.0 * (wien_db - null_db), (wien_db, lo, null_db)

    # --- 4, 5 --------------------------------------------------------------- #
    wrong_len = fs.cx_wiener_deconvolve(blur, motion_psf(21, BLUR_DEG), nsr=nsr_best)
    wrong_ang = fs.cx_wiener_deconvolve(blur, motion_psf(BLUR_LEN, 50.0), nsr=nsr_best)
    cands = [
        ("何もしない", blur),
        ("Wiener 正しい PSF", wien),
        ("Wiener 長さ違い 21", wrong_len),
        ("Wiener 角度違い 50", wrong_ang),
        ("unsharp", fs.apply(blur, "iv_unsharp_deblur")),
        ("motion_deblur", fs.apply(blur, "iv_motion_deblur")),
        ("Richardson-Lucy", fs.apply(blur, "iv_richardson_lucy")),
    ]
    rows = [(nm, psnr(v, truth), grad_energy(v), blur_effect(v)) for nm, v in cands]
    t_grad, t_blur = grad_energy(truth), blur_effect(truth)
    print("\n4-5. 指標を変えると勝者が入れ替わる")
    print("     手法                 PSNR      勾配エネルギー   blur_effect")
    for nm, a, g, b in rows:
        print("     %-18s %6.2f dB   %10.4f   %10.4f" % (nm, a, g, b))
    print("     %-18s %9s   %10.4f   %10.4f" % ("(真値そのもの)", "inf", t_grad, t_blur))
    win_psnr = max(rows, key=lambda r: r[1])[0]
    win_grad = max(rows, key=lambda r: r[2])[0]
    win_blur = min(rows, key=lambda r: r[3])[0]
    print("   勝者: PSNR -> %s / 勾配エネルギー -> %s / blur_effect -> %s"
          % (win_psnr, win_grad, win_blur))
    by = dict((r[0], r) for r in rows)
    print("   ★勾配エネルギーの最高は真値の %.2f 倍。"
          % (by[win_grad][2] / t_grad))
    print("   ★参照なし指標が選ぶ手法の PSNR: 勾配 -> %.2f dB(1 位より %+.2f)、"
          "blur_effect -> %.2f dB(%+.2f)。"
          % (by[win_grad][1], by[win_grad][1] - wien_db,
             by[win_blur][1], by[win_blur][1] - wien_db))
    print("   ★ただし blur_effect は真値そのもの(%.4f)を全手法より良いと判定 —— "
          "「ぼけているか」は測れていて、それでも選ばせると損をする。" % t_blur)
    print("   ★長さを間違えた PSF: %.2f dB —— 正しい PSF から %+.2f dB、"
          "何もしないより %+.2f dB。なのに見た目はいちばん鋭い。"
          % (by["Wiener 長さ違い 21"][1],
             by["Wiener 長さ違い 21"][1] - wien_db,
             by["Wiener 長さ違い 21"][1] - null_db))
    # ★守るのは「どれが勝つか」ではなく**勝者が物差しごとに違う**こと。
    #   手法名を固定すると、実装が良くなっただけで落ちる門になる。
    assert win_psnr == "Wiener 正しい PSF", win_psnr
    assert len({win_psnr, win_grad, win_blur}) == 3, (win_psnr, win_grad, win_blur)
    assert by[win_grad][2] > 1.4 * t_grad, (by[win_grad][2], t_grad)
    # 参照なし指標が選ぶ手法は、PSNR では大きく劣る
    assert by[win_grad][1] < wien_db - 3.0, (by[win_grad][1], wien_db)
    assert by[win_blur][1] < wien_db - 2.0, (by[win_blur][1], wien_db)
    # ただし真値そのものは blur_effect でも正しく最良(指標を不当に貶めない)
    assert t_blur < min(r[3] for r in rows), (t_blur, min(r[3] for r in rows))
    assert by["Wiener 長さ違い 21"][1] < null_db - 3.0, by["Wiener 長さ違い 21"]

    # --- 6 ------------------------------------------------------------------ #
    print("\n6. 崖(雑音)—— 正しい PSF でも利得は消える")
    noise_rows = []
    for sg in (0.0, 0.001, 0.002, 0.004, 0.008, 0.016):
        b2, p2 = degrade(truth, sigma=sg)
        _n, v, _i, _s = best_wiener(b2, p2, truth)
        z = psnr(b2, truth)
        noise_rows.append((sg, v, z, v - z))
        print("   σ=%.4f  Wiener %6.2f dB / ゼロ点 %6.2f dB / 差 %+5.2f"
              % (sg, v, z, v - z))
    assert noise_rows[0][3] > 1.2, noise_rows[0]
    assert noise_rows[-1][3] < 0.3, noise_rows[-1]

    # --- 7 ------------------------------------------------------------------ #
    print("\n7. 崖(ブレ長)—— 両端で落ちる")
    len_rows = []
    for L in (3, 5, 7, 11, 17, 25):
        b2, p2 = degrade(truth, length=L)
        _n, v, _i, _s = best_wiener(b2, p2, truth)
        z = psnr(b2, truth)
        len_rows.append((L, v, z, v - z))
        print("   L=%2d  Wiener %6.2f dB / ゼロ点 %6.2f dB / 差 %+5.2f"
              % (L, v, z, v - z))
    gains = [r[3] for r in len_rows]
    peak = len_rows[int(np.argmax(gains))][0]
    print("   利得の山は L=%d(+%.2f dB)。小さいブレは取るものが無く、"
          "大きいブレは情報が消えている。" % (peak, max(gains)))
    assert gains[0] < max(gains) and gains[-1] < max(gains), gains
    assert 5 <= peak <= 11, peak

    # --- 図 ------------------------------------------------------------------ #
    figs.save_grid(
        "restore",
        [truth, blur, np.clip(np.asarray(wien, np.float64), 0, 1),
         np.clip(np.asarray(wrong_len, np.float64), 0, 1)],
        ["真値(実写 camera)", "ブレ + 雑音(%.2f dB)" % null_db,
         "Wiener 正しい PSF(%.2f dB)" % wien_db,
         "Wiener 長さ違い(%.2f dB)" % by["Wiener 長さ違い 21"][1]],
        title="いちばん鋭く見えるのが、いちばん真値から遠い", ncols=2,
        caption="長さを間違えた PSF は勾配エネルギーが真値の %.2f 倍。"
                % (by[win_grad][2] / t_grad))

    figs.save_plot(
        "nsr",
        [("PSNR [dB]", [n for n, _v in sweep], [v for _n, v in sweep]),
         ("ゼロ点", [n for n, _v in sweep], [null_db] * len(sweep))],
        xlabel="nsr(Wiener の正則化)", ylabel="PSNR [dB]",
        title="ノブのほうが手法より効く(%.2f dB 対 %.2f dB)"
              % (wien_db - lo, wien_db - null_db),
        caption="固定した nsr で比べると、正しい PSF でもゼロ点に負ける。")

    figs.save_plot(
        "cliffs",
        [("雑音 σ に対する利得 [dB]", [r[0] * 1000 for r in noise_rows],
          [r[3] for r in noise_rows])],
        xlabel="雑音 σ x1000", ylabel="ゼロ点に対する利得 [dB]",
        title="1.6 % の雑音で、脱畳み込みは何も買わない",
        caption="σ=0 で +%.2f dB、σ=0.016 で +%.2f dB。"
                % (noise_rows[0][3], noise_rows[-1][3]))

    figs.save_table(
        "metrics",
        ["手法", "PSNR", "勾配", "blur_effect"],
        [[nm, "%.2f" % a, "%.4f" % g, "%.4f" % b] for nm, a, g, b in rows]
        + [["(真値)", "inf", "%.4f" % t_grad, "%.4f" % t_blur]],
        title="3 つの物差し、3 人の勝者", col_w=120,
        caption="参照なし指標が選ぶ手法は PSNR で 3〜5 dB 劣る。")

    print("\n所見")
    print("  * ゼロ点 %.2f dB。固定 nsr=%.3f の Wiener は %.2f dB で負ける。"
          % (null_db, NSR_NAIVE, naive))
    print("  * nsr を振れば %.2f dB(+%.2f)。ただしノブの幅 %.2f dB のほうが "
          "%.1f 倍大きい。" % (wien_db, wien_db - null_db, wien_db - lo,
                               (wien_db - lo) / max(wien_db - null_db, 1e-9)))
    print("  * 勝者は物差しごとに違う: PSNR %s / 勾配 %s / blur_effect %s。"
          "参照なし指標の選択は %.2f dB / %.2f dB 損。"
          % (win_psnr, win_grad, win_blur,
             wien_db - by[win_grad][1], wien_db - by[win_blur][1]))
    print("  * 長さ違いの PSF は %.2f dB(ゼロ点より %+.2f)なのに見た目は最良。"
          % (by["Wiener 長さ違い 21"][1],
             by["Wiener 長さ違い 21"][1] - null_db))
    print("  * 崖: 雑音 σ=0.016 で利得 +%.2f dB、ブレ長の山は L=%d。"
          % (noise_rows[-1][3], peak))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
