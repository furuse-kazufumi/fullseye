# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_astro_photometry — 何枚重ねると、星の明るさは何 % の精度で測れるか。

    py -3.11 examples/poc_astro_photometry.py

【この PoC が答える問い】
``examples/astro_stacking.py`` は astrostack 14 op を一通り通した。こちらは
**測光精度という 1 本の軸だけ**に絞って、観測者が実際に決めたい 1 つの数字
——「今夜は何枚撮れば済むのか」—— を出す。問いは 4 つに分けた。

    問 1  枚数を振ると測光誤差は落ちるか。落ち方は **1/√N** か。
    問 2  宇宙線が開口に当たったとき、単純平均と κ-σ でどれだけ違うか。
    問 3  (独立な検算)drizzle は総フラックスを保存するか。保存するなら、
          **合成を経由しない別経路**で測った明るさは一致するか。
    問 4  lucky imaging の選別は、測光精度に効くのか。

【なぜ数字が信じられるのか】
星の位置とフラックスは ``synth_starfield`` / ``synth_frame_series`` が
**こちらの指定どおりに**置いたもの(ガウシアン PSF は erf による画素の厳密積分)。
だから「合っている / いない」ではなく「**カタログの値に対して何 % ずれた**」を
そのまま書ける。検出も挟まない —— 開口の中心には真値の座標を直接与えるので、
ここで測っているのは測光の誤差だけで、検出のずれが混ざらない。

【実測(この 1 本を走らせて得た数字。seed 固定なのでどの機械でも再現する。所要 5.7 s)】
 段 0  雑音を切った期待値画像に対する開口測光の系統誤差 = 中央 **-0.0126 %**
       (最大 0.0129 %)。以降の誤差はすべてこの床の上に乗っている。
 段 1  孤立星 22 個 x 反復 256/N 回 x 3 星野(標本 5632〜352 個):

           N   反復  標本   中央 |e|    95 % 点 |e|  改善(中央) 改善(95 %) 理論 √N
            1   256   5632   0.6350 %    1.9028 %      1.000      1.000     1.000
            2   128   2816   0.4471 %    1.3434 %      1.420      1.416     1.414
            4    64   1408   0.3138 %    0.9548 %      2.023      1.993     2.000
            8    32    704   0.2353 %    0.6441 %      2.699      2.954     2.828
           16    16    352   0.1616 %    0.4892 %      3.929      3.890     4.000

       ★ **1/√N は成立**(8 通りすべてで理論からのずれ 最大 4.6 %)。予想と違った
       のは「どこかで頭打ちになるだろう」と思っていたのに **ならなかった**こと ——
       16 枚の 0.1616 % は段 0 の床 0.0126 % のまだ 13 倍上で、この設定では
       枚数を増やす価値が残っている(頭打ちは 160 枚あたりから、の意)。
 段 2  8 枚のうち **1 枚だけ**、各星の開口の中へ +8000 e- を 1 発ずつ置いた
       (汚染率 12.5 %):

           汚染なし 単純平均   中央 +0.4501 %   最大 0.6657 %   棄却率 0.00000
           汚染なし κ-σ        中央 +0.3140 %   最大 0.5804 %   棄却率 0.05378
           汚染あり 単純平均   中央 **+5.8944 %** 最大 8.1748 % 棄却率 0.00000
           汚染あり 中央値     中央 +0.3745 %   最大 0.8296 %   棄却率 0.00000
           汚染あり κ-σ        中央 +0.2974 %   最大 0.5804 %   棄却率 0.05380

       単純平均は 1/N しか薄まらないので 8 枚でも 5.9 % 残る。κ-σ は
       **汚染ありの +0.2974 % が汚染なしの +0.3140 % と区別できない**ところまで
       戻す。★ ただし **棄却率は 0.05378 → 0.05380 でほぼ動かない** ——
       仕込んだ 6 画素は 224x224x8 = 401408 画素の 1.5e-5 でしかない。
       「棄却率が上がったから効いた」という言い方は、この量では成り立たない。
 段 3  独立な検算。drizzle の総フラックス保存 = 倍率 3 通り x pixfrac 3 通りで
       最悪 **相対 6.11e-14**(float64 の丸めの桁)。その保存則を使って
       **合成を通らない経路**でも測る —— 2 倍 drizzle した ``sci/wht`` の上で
       半径も 2 倍にすると 中央 +0.4609 %、合成経由は +0.4501 %、差 **0.0108 %**。
 段 4  FWHM 3.0 px の良 6 枚に FWHM 9.0 px の悪 6 枚(σ = 3.82 px)を混ぜた。
       ``lucky_select(keep_fraction=0.5)`` は **良い 6 枚をちょうど当てた**
       (点 0.085〜0.088 vs 0.008〜0.011、重なりゼロ)。ただし御利益は
       **開口半径で 30 倍変わる**(孤立星 7 個、中央値):

           開口 r=12 px (悪い側 3.1 σ)  混合 -0.489 %   選別後 +0.108 %
           開口 r= 6 px (悪い側 1.6 σ)  混合 -16.859 %  選別後 +0.185 %
           開口 r= 3 px (悪い側 0.8 σ)  混合 -41.312 %  選別後 -7.793 %

       ★ **これが予想と一番違った点。**「悪いフレームは捨てるべき」は測光では
       無条件に正しくない —— 開口を PSF に対して十分広く取れるなら、ぼけた
       フレームも**同じ明るさを持っている**(r=12 では差 0.597 %)。逆に開口を
       絞ると選別なしでは 17〜41 % 外す。捨てる代償は雑音で、良いフレーム 96 枚を
       使い星ごとの平均を引いて雑音だけを取り出すと 6 枚合成 0.3585 % vs
       12 枚合成 0.2674 % = **1.341 倍**(理論 √2 = 1.414)。

【この PoC で自分が間違えて、直した点(消さずに残す)】
1. **drizzle の明るさを 1/4 にした。** ``scale=2`` なら画素が 4 倍になるので
   明るさも 1/4 だろうと決めて ``flux/4`` と書き、-74.89 % を出した。誤り ——
   drizzle が保存するのは**総フラックス**(段 3 の 6.11e-14 がそれ)なので、
   1 画素あたりが 1/4 になっても星の総和は変わらない。割り算を外して +0.46 %。
   **直前に自分で書いた保存則の検算が、直後の自分の間違いを弾いた**。
2. **95 % 点が 1/√N から +27 % 外れて assert が落ちた。** 最初は N によらず
   反復 16 回に固定していたので、N=16 も N=1 も標本 352 個。95 % 点はその 5 %
   側の裾で、実質 18 個ほどで決まる統計だった。持ち駒 256 枚を使い切って
   反復を ``256/N`` 回にし(N=1 なら 5632 標本)、さらに星の明るさの幅を
   4 倍(8000〜40000 e-)から 2.5 倍(12000〜30000 e-)に絞って
   「一番暗い星だけが裾を作る」状態をやめたら、ずれは 4.6 % に収まった。
   ★ 教訓: **中央値が合っていても 95 % 点は合っていないことがある**。裾の統計は
   標本数を中央値と同じ感覚で決めてはいけない。
3. **枚数半減の √2 が 0.947 倍に見えた。** 段 4 で、1 回の合成・孤立星 8 個の
   rms を「雑音」と呼んで良 6 枚(0.306 %)と良 12 枚(0.324 %)を比べ、
   理論と逆向きの 0.947 倍を出した。あの rms は星ごとの系統ずれと雑音の和で、
   標本 8 個では雑音だけを取り出せない。段 1 と同じく反復を積んで
   **星ごとの平均を引いた**ら 1.341 倍(理論 1.414)になった。
   ★ 「理論と違う数字が出た」の大半は理論の反証ではなく**測り方の問題**。
4. **「孤立」の閾値が測定量そのものを決めていた。** 最初は背景環を 8〜18 px に
   取り、孤立を ``nn > 2*r_outer = 36 px`` としたら 18 星中 3 個しか残らず統計に
   ならなかった。環を 8〜12 px に詰めて ``nn > 24 px`` にすると 20 星中 6〜9 個
   残る。混み合った星まで入れた系統誤差は最大 **281 %**(開口が隣の星を丸ごと
   拾う)、孤立星だけなら **0.0129 %** —— 同じ op、同じ画像で 4 桁違う。
   「測光の誤差は X %」と言う前に、何を孤立と呼ぶかを書かないと数字が意味を持たない。

【fullseye 側に見つかった穴(この PoC の副産物・いずれも実害あり)】
* ``drizzle_resample`` の docstring に **入力座標 → 出力座標の対応が書かれていない**。
  出来上がった ``sci`` の上で測光するには star が何処に来るか必要なのに、
  規約が無いので毎回自分で導くことになる。実測で確定した関係は
  ``out = in * scale + (scale - 1) / 2``(雑音を切った 1 星の重心で、
  scale=2 → 52.632 予測 52.632、scale=3 → 79.198 予測 79.198 と**完全一致**)。
  これは 1 行 docstring に足せば済む(``shifts`` を渡した場合も同じか、は未検証)。
* ``synth_frame_series`` は同じ星野を撮り直すために ``field_seed`` を ``seed`` に
  固定する(``field_seed`` を渡すと ValueError)。設計としては正しいが、そのため
  **「同じ星野・違うシーイング」の列を 1 呼び出しでは作れない**。段 4 では
  ``synth_starfield(field_seed=固定, fwhm_px=別)`` を 104 回手で並べた。
  ``fwhm_px`` にフレームごとの値(配列)を許せば、lucky imaging の実験が 1 行で書ける
  (``fwhm_jitter`` は決定的な三角波なので「良い群 / 悪い群」の二峰は作れない)。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import astrostack as A  # noqa: E402
import examplefig as figs  # noqa: E402

SHAPE = (224, 224)
N_STARS = 20
FWHM = 3.2                              # シーイング(σ = 1.359 px)
SKY, READ = 60.0, 5.0                   # 背景 [e-] と読み出し雑音 [e- rms]
FLUX_MIN, FLUX_MAX = 12000.0, 30000.0   # 明るさの幅を 2.5 倍に絞る(理由は段 1 の注)
MARGIN = 20.0
R_AP, R_IN, R_OUT = 6.0, 8.0, 12.0      # 開口 / 背景環(r = 4.4 σ なので開口損失は無視できる)
ISO_PX = 2.0 * R_OUT                    # 「孤立」の定義: 背景環に隣が入らないこと
N_POOL, N_MAX = 256, 16                 # 1 星野あたりの持ち駒と、掃引する最大枚数
FIELDS = (2026, 4242, 777)              # 3 つの独立な星野(標本を増やすため)
CR_FLUX = 8000.0                        # 仕込む宇宙線 1 発の電子数


def _isolated(truth):
    """最近傍まで :data:`ISO_PX` 以上離れた星の bool マスク。

    開口が隣を拾うと「測光の誤差」ではなく「星表の混み具合」を測ってしまう。
    背景環の外半径の 2 倍で切れば、環にも隣が入らない。
    """
    r, c = truth["rows"], truth["cols"]
    sep = np.hypot(r[:, None] - r[None, :], c[:, None] - c[None, :])
    np.fill_diagonal(sep, np.inf)
    return sep.min(axis=1) > ISO_PX


def _rel_err(image, centers, fluxes, r_ap=R_AP, r_in=R_IN, r_out=R_OUT):
    """既知フラックスに対する開口測光の相対誤差 ``(measured - true) / true``。"""
    phot = A.aperture_photometry(image, centers, r_aperture=r_ap,
                                 r_inner=r_in, r_outer=r_out)
    return np.array([(p["flux"] - f) / f for p, f in zip(phot, fluxes)])


def _stack_mean(chunk):
    """1 枚なら素通し、2 枚以上なら単純平均(``sigma_clip_stack`` は 2 枚以上を要求)。"""
    return chunk[0] if len(chunk) == 1 else A.sigma_clip_stack(chunk, mode="mean")[0]


def main():
    timing = {}

    # ------------------------------------------------------------------ #
    # 0) 正解の供給源と、測光そのものの系統誤差(= 以降の誤差の床)         #
    # ------------------------------------------------------------------ #
    t0 = time.perf_counter()
    fields = []
    for seed in FIELDS:
        frames, truth = A.synth_frame_series(
            shape=SHAPE, n_frames=N_POOL, dither_px=0.0, n_stars=N_STARS,
            fwhm_px=FWHM, sky=SKY, read_sigma=READ, flux_min=FLUX_MIN,
            flux_max=FLUX_MAX, margin_px=MARGIN, seed=seed)
        iso = _isolated(truth)
        fields.append((frames, truth, iso))
    timing["段0 合成"] = time.perf_counter() - t0
    n_iso = sum(int(iso.sum()) for _, _, iso in fields)
    print(f"0) 同じ空を撮り直した列を 3 本: 各 {N_POOL} 枚 x {SHAPE}  "
          f"空 {SKY:.0f} e-  読み出し {READ:.0f} e-  FWHM {FWHM} px  ディザ 0 "
          f"(位置合わせを挟まないので、測っているのは測光の誤差だけ)")
    print(f"   星 {3 * N_STARS} 個のうち、最近傍まで {ISO_PX:.0f} px 以上ある"
          f"**孤立星 {n_iso} 個**だけを採点対象にする")

    # 測光 op 自体の系統誤差 —— 雑音を切った期待値画像で測る。
    # これより下は雑音をいくら減らしても届かない床なので、先に高さを知っておく。
    floor = []
    for _, truth, iso in fields:
        ctr = np.stack([truth["rows"], truth["cols"]], axis=1)[iso]
        floor.append(_rel_err(truth["noiseless"], ctr, truth["fluxes"][iso]))
    floor = np.concatenate(floor)
    print(f"   雑音を切った 1 枚(truth['noiseless'])での系統誤差: 中央 "
          f"{100 * np.median(floor):+.4f} % / 最大 {100 * np.abs(floor).max():.4f} % "
          f"= **これが床**。開口 r={R_AP:.0f} px は σ の "
          f"{R_AP / (FWHM / A.FWHM_PER_SIGMA):.1f} 倍なので開口損失が効かない")
    assert np.abs(floor).max() < 5e-4, floor        # 床は 0.05 % 未満

    # ------------------------------------------------------------------ #
    # 1) 枚数を振る —— 測光誤差は 1/√N で落ちるか                           #
    # ------------------------------------------------------------------ #
    t0 = time.perf_counter()
    counts = (1, 2, 4, 8, 16)
    stats = {}
    for n in counts:
        pooled = []
        reps = N_POOL // n                  # 持ち駒を使い切る = 標本を最大化する
        for frames, truth, iso in fields:
            ctr = np.stack([truth["rows"], truth["cols"]], axis=1)[iso]
            ftrue = truth["fluxes"][iso]
            for j in range(reps):           # 互いに素なフレーム = 独立な観測
                stack = _stack_mean(frames[j * n:(j + 1) * n])
                pooled.append(np.abs(_rel_err(stack, ctr, ftrue)))
        pooled = np.concatenate(pooled)
        stats[n] = (float(np.median(pooled)), float(np.percentile(pooled, 95)),
                    int(pooled.size), reps)
    timing["段1 枚数掃引"] = time.perf_counter() - t0

    print(f"1) 枚数 vs 測光誤差(単純平均で合成、開口の中心は**真値の座標**"
          f"、標本は孤立星 {n_iso} x 反復 {N_POOL}/N 回 = "
          f"{stats[1][2]}〜{stats[16][2]} 個):")
    print("     N   反復  標本   中央 |e|    95 % 点 |e|  改善(中央) 改善(95 %)  理論 √N")
    for n in counts:
        med, p95, size, reps = stats[n]
        print(f"    {n:2d}  {reps:4d} {size:6d}  {100 * med:7.4f} %  {100 * p95:8.4f} %    "
              f"{stats[1][0] / med:6.3f}     {stats[1][1] / p95:6.3f}    {np.sqrt(n):6.3f}")
    for n in counts[1:]:
        for k, label in ((0, "中央値"), (1, "95 % 点")):
            got = stats[1][k] / stats[n][k]
            dev = got / np.sqrt(n) - 1.0
            assert abs(dev) < 0.10, (n, label, got, dev)
    worst = max(abs(stats[1][k] / stats[n][k] / np.sqrt(n) - 1.0)
                for n in counts[1:] for k in (0, 1))
    print(f"   → **1/√N は成立**(中央値・95 % 点の 8 通りすべてで理論からのずれ "
          f"最大 {100 * worst:.1f} %)。16 枚の 0.15 % は段 0 の床 "
          f"{100 * abs(np.median(floor)):.4f} % の {abs(np.median(stats[16][0] / np.median(floor))):.0f} 倍"
          f"上にあるので、**まだ頭打ちではない**(枚数を増やす価値が残っている)")
    # 図: 実測 2 本(中央値・95 % 点)と、1 枚の実測から引いた 1/√N の外挿を
    #     重ねる。3 本が重なることが「1/√N は成立」の中身そのもの。
    figs.save_plot(
        "stack_scaling",
        [("中央 |e|", counts, [100 * stats[n][0] for n in counts]),
         ("95 % 点 |e|", counts, [100 * stats[n][1] for n in counts]),
         ("1/√N(1 枚からの外挿)", counts,
          [100 * stats[1][0] / np.sqrt(n) for n in counts])],
        xlabel="合成枚数 N", ylabel="測光誤差 [%]",
        title="枚数を増やすと測光誤差はどう落ちるか",
        caption="中央値の実測と 1/√N の外挿がほぼ重なる。段 0 の床 "
                "%.4f %% にはまだ遠い。" % (100 * abs(np.median(floor))))

    # ------------------------------------------------------------------ #
    # 2) ゼロ点 —— 宇宙線が開口に当たったら、単純平均と κ-σ でどれだけ違うか #
    # ------------------------------------------------------------------ #
    t0 = time.perf_counter()
    frames, truth, iso = fields[0]
    ctr = np.stack([truth["rows"], truth["cols"]], axis=1)[iso]
    ftrue = truth["fluxes"][iso]
    base = list(frames[:8])
    struck = [f.copy() for f in base]
    rng = np.random.default_rng(31)
    for i in np.flatnonzero(iso):           # 孤立星 1 個につき 1 発、8 枚のどれかに
        k = int(rng.integers(0, len(struck)))
        row = int(round(truth["rows"][i])) + int(rng.integers(-3, 4))
        col = int(round(truth["cols"][i])) + int(rng.integers(-3, 4))
        struck[k][row, col] += CR_FLUX
    print(f"2) 宇宙線: 8 枚のうち **1 枚だけ**に +{CR_FLUX:.0f} e- を、"
          f"各星の開口(r={R_AP:.0f} px)の中へ 1 発ずつ置いた"
          f"(汚染率 1/8 = 12.5 %、位置は自分で決めたので分かっている)")
    rows = []
    for label, src, mode in (("汚染なし 単純平均", base, "mean"),
                             ("汚染なし κ-σ", base, "sigma_clip"),
                             ("汚染あり 単純平均", struck, "mean"),
                             ("汚染あり 中央値", struck, "median"),
                             ("汚染あり κ-σ", struck, "sigma_clip")):
        stack, accepted = A.sigma_clip_stack(src, mode=mode, kappa=3.0)
        err = _rel_err(stack, ctr, ftrue)
        rows.append((label, float(np.median(err)), float(np.abs(err).max()),
                     1.0 - float(accepted.mean())))
        print(f"     {label:<18s} 中央 {100 * rows[-1][1]:+8.4f} %   "
              f"最大 |{100 * rows[-1][2]:7.4f} %|   棄却率 {rows[-1][3]:.5f}")
    figs.save_table("cosmic_ray",
                    ["条件", "中央 [%]", "最大 |e| [%]", "棄却率"],
                    [[lab, "%+.4f" % (100 * med), "%.4f" % (100 * mx),
                      "%.5f" % rej] for lab, med, mx, rej in rows],
                    title="宇宙線 12.5 %% 汚染(8 枚中 1 枚、開口 r=%.0f px)" % R_AP,
                    caption="単純平均だけが 5.9 % 残る。κ-σ は汚染なしと区別できない"
                            "ところまで戻すが、棄却率はほとんど動かない。")
    clean_mean, clean_clip, cr_mean, cr_med, cr_clip = rows
    assert cr_mean[1] > 0.04                        # 単純平均は 4 % 以上ずれる
    assert abs(cr_clip[1]) < 0.01                   # κ-σ は 1 % 未満まで戻す
    assert cr_clip[2] < 0.2 * cr_mean[2]            # 最大誤差も 1/5 以下
    assert abs(cr_clip[1] - clean_clip[1]) < 0.002  # 汚染ありと汚染なしが区別できない
    print(f"   → 単純平均の誤差 {100 * cr_mean[1]:+.4f} % は "
          f"1 枚ぶんの汚染 / 8 枚 —— **枚数では消えず 1/N でしか薄まらない**。"
          f"κ-σ は {100 * cr_clip[1]:+.4f} % で、汚染なしの "
          f"{100 * clean_clip[1]:+.4f} % と区別できないところまで戻す"
          f"(中央値合成も {100 * cr_med[1]:+.4f} % で効くが、"
          f"雑音は平均の √(π/2) 倍うるさい)")
    print(f"   棄却率は汚染ありもなしも {cr_clip[3]:.5f} で動かない —— "
          f"仕込んだのは {int(iso.sum())} 画素、母数は {8 * SHAPE[0] * SHAPE[1]} 画素なので"
          f"寄与は {iso.sum() / (8 * SHAPE[0] * SHAPE[1]):.1e}。"
          f"**「棄却率が上がったから効いた」とは言えない**(効いたかは誤差で見る)")
    timing["段2 宇宙線"] = time.perf_counter() - t0

    # ------------------------------------------------------------------ #
    # 3) 独立な検算 —— drizzle の総フラックス保存と、合成を通らない測光      #
    # ------------------------------------------------------------------ #
    t0 = time.perf_counter()
    want = float(np.mean([f.sum() for f in base]))
    worst_rel = 0.0
    for pixfrac in (1.0, 0.7, 0.4):
        for scale in (1.0, 2.0, 3.0):
            sci, _ = A.drizzle_resample(base, scale=scale, pixfrac=pixfrac)
            worst_rel = max(worst_rel, abs(float(sci.sum()) - want) / want)
    print(f"3) 独立な検算 その 1 —— drizzle の総フラックス保存: 倍率 3 通り x "
          f"pixfrac 3 通りの 9 通りで最悪 相対 {worst_rel:.2e}(float64 の丸めの桁)")
    assert worst_rel < 1e-12

    # その 2: 保存則が本当なら、2 倍 drizzle した格子の上で半径も 2 倍にして
    # 測り直した明るさは、合成経由の値と一致するはずである。
    # ★ ここで一度間違えた: 「scale=2 だから明るさも 1/4」と思って flux/4 を書き、
    #    -74.89 % を出した。保存則(上の 6.1e-14)がそれを弾いた。画素あたりの
    #    明るさは 1/4 になるが、星の**総和**は変わらない。
    scale = 2.0
    sci, wht = A.drizzle_resample(base, scale=scale, pixfrac=1.0)
    science = np.where(wht > 1e-9, sci / np.maximum(wht, 1e-9), 0.0)
    # 入力座標 x の画素中心は、出力格子では (x + 0.5) * scale - 0.5 に移る
    ctr_d = ctr * scale + (scale - 1.0) / 2.0
    err_d = _rel_err(science, ctr_d, ftrue, r_ap=R_AP * scale,
                     r_in=R_IN * scale, r_out=R_OUT * scale)
    stack_mean, _ = A.sigma_clip_stack(base, mode="mean")
    err_s = _rel_err(stack_mean, ctr, ftrue)
    print(f"   その 2 —— 合成を通らない経路: {scale:.0f} 倍 drizzle した sci/wht の上で"
          f"半径も {scale:.0f} 倍にして測ると 中央 {100 * np.median(err_d):+.4f} %。"
          f"合成経由は {100 * np.median(err_s):+.4f} % —— 差 "
          f"{100 * abs(np.median(err_d) - np.median(err_s)):.4f} %")
    assert abs(np.median(err_d) - np.median(err_s)) < 0.01
    assert np.allclose(wht, 1.0, atol=1e-12)        # pixfrac=1・ディザ 0 なら被覆は厳密に 1
    timing["段3 drizzle"] = time.perf_counter() - t0

    # ------------------------------------------------------------------ #
    # 4) lucky imaging —— 悪いフレームを混ぜる。選別は測光に効くのか        #
    # ------------------------------------------------------------------ #
    t0 = time.perf_counter()
    field_seed, fw_good, fw_bad = 99, 3.0, 9.0

    def _one(fwhm_px, seed):
        """同じ星野(``field_seed`` 固定)を、指定のシーイングで 1 枚撮る。"""
        return A.synth_starfield(
            shape=SHAPE, n_stars=N_STARS, fwhm_px=fwhm_px, sky=SKY,
            read_sigma=READ, flux_min=FLUX_MIN, flux_max=FLUX_MAX,
            margin_px=MARGIN, field_seed=field_seed, seed=seed)

    good = [_one(fw_good, 100 + k)[0] for k in range(96)]
    bad = [_one(fw_bad, 200 + k)[0] for k in range(6)]
    _, ltruth = _one(fw_good, 100)
    _, btruth = _one(fw_bad, 200)
    # 同じ星野であることを先に確かめる(ここが違うと以降の比較が全部無意味)
    assert np.allclose(ltruth["rows"], btruth["rows"])
    assert np.allclose(ltruth["fluxes"], btruth["fluxes"])
    liso = _isolated(ltruth)
    lctr = np.stack([ltruth["rows"], ltruth["cols"]], axis=1)[liso]
    lflux = ltruth["fluxes"][liso]

    mixed = good[:6] + bad                  # 良 6 + 悪 6
    keep, scores = A.lucky_select(mixed, keep_fraction=0.5)
    print(f"4) lucky imaging: FWHM {fw_good} px の良 6 枚に FWHM {fw_bad} px の悪 6 枚を混ぜた。"
          f"点は 良 {scores[:6].min():.3f}〜{scores[:6].max():.3f} / "
          f"悪 {scores[6:].min():.3f}〜{scores[6:].max():.3f}(重なりなし)")
    print(f"   keep_fraction=0.5 が選んだのは {sorted(int(i) for i in keep)} = "
          f"**良い 6 枚をちょうど当てた**(``field_seed`` 固定なので座標も"
          f"フラックスも良悪で同一 —— 上で assert 済み。孤立星 "
          f"{int(liso.sum())} 個で採点する)")
    assert sorted(int(i) for i in keep) == list(range(6))
    assert scores[:6].min() > scores[6:].max()

    sigma_bad = fw_bad / A.FWHM_PER_SIGMA
    print(f"   ただし御利益は **開口半径で決まる**(悪い側の σ = {sigma_bad:.2f} px):")
    print("     開口 r          全 12 枚(混合)      選別後 6 枚(= 良 6)     良い 12 枚")
    lucky_stack = _stack_mean([mixed[i] for i in keep])
    mixed_stack = _stack_mean(mixed)
    good12_stack = _stack_mean(good[:12])
    table = {}
    for r_ap, r_in, r_out in ((12.0, 15.0, 22.0), (6.0, 8.0, 12.0), (3.0, 8.0, 12.0)):
        cells = []
        for stack in (mixed_stack, lucky_stack, good12_stack):
            e = _rel_err(stack, lctr, lflux, r_ap=r_ap, r_in=r_in, r_out=r_out)
            cells.append((float(np.median(e)), float(np.sqrt((e ** 2).mean()))))
        table[r_ap] = cells
        print(f"     {r_ap:4.0f} px ({r_ap / sigma_bad:.1f} σ) " + " ".join(
            f"中央 {100 * m:+8.3f} % rms {100 * sd:6.3f} %" for m, sd in cells))
    # 図: 御利益が開口半径で 30 倍変わる、という段 4 の要点そのもの。
    r_axis = [3.0, 6.0, 12.0]
    figs.save_plot(
        "aperture_tradeoff",
        [("全 12 枚(混合)", r_axis, [100 * table[r][0][0] for r in r_axis]),
         ("選別後 6 枚", r_axis, [100 * table[r][1][0] for r in r_axis]),
         ("良い 12 枚", r_axis, [100 * table[r][2][0] for r in r_axis])],
        xlabel="開口半径 [px]", ylabel="測光誤差 中央値 [%]",
        title="lucky 選別の御利益は開口半径で決まる",
        caption="開口を広く取れるなら、ぼけたフレームも同じ明るさを持っている"
                "(r=12 では 3 本が重なる)。")
    # 図: 良いフレームと悪いフレームの現物。対数で伸ばさないと空しか写らない。
    figs.save_grid(
        "lucky_frames",
        [np.log10(np.maximum(good[0], 1.0)), np.log10(np.maximum(bad[0], 1.0)),
         np.log10(np.maximum(lucky_stack, 1.0)),
         np.log10(np.maximum(mixed_stack, 1.0))],
        ["良 1 枚 FWHM %.1f px" % fw_good, "悪 1 枚 FWHM %.1f px" % fw_bad,
         "選別後 6 枚の合成", "混合 12 枚の合成"],
        title="lucky imaging(表示は log10 電子数)",
        caption="悪いほうは星が広がっている。混合の合成は芯の周りに裾が残る。")
    # 開口が広いほど、混合の劣化は小さい(ぼけても総フラックスは残っているから)
    assert abs(table[12.0][0][0]) < abs(table[6.0][0][0]) < abs(table[3.0][0][0])
    assert abs(table[6.0][1][0]) < 0.01     # r=6 では選別が誤差を 1 % 未満に戻す
    print(f"   → r=12 px(悪い側の {12.0 / sigma_bad:.1f} σ)では混合と選別の差は"
          f"わずか {100 * abs(table[12.0][0][0] - table[12.0][1][0]):.3f} % —— "
          f"**開口を十分広く取れるなら、ぼけたフレームも同じ明るさを持っている**。"
          f"r=6 px では {100 * abs(table[6.0][0][0]):.1f} % ずれるので選別が必須。"
          f"「悪いフレームは捨てるべき」は測光では条件つき")
    # 捨てることの代償 —— 枚数が半分になるぶん雑音は √2 倍。
    # ★ ここで一度 assert を落とした: 上の表の rms(1 回の合成・孤立星 8 個)で
    #   良 6 枚 0.306 % vs 良 12 枚 0.324 % = **0.947 倍**が出た。理論 1.414 の
    #   反証ではなく、あの rms が「星ごとの系統ずれ」と「雑音」を足したもので、
    #   標本 8 個では雑音だけを取り出せない、という意味だった。段 1 と同じく
    #   **反復を積んで星ごとの平均を引く**と、初めて雑音だけが残る。
    noise = {}
    for n in (6, 12):
        reps = len(good) // n
        e = np.array([_rel_err(_stack_mean(good[j * n:(j + 1) * n]), lctr, lflux)
                      for j in range(reps)])            # (reps, n_star)
        noise[n] = (float(np.sqrt(((e - e.mean(axis=0)) ** 2).mean())), reps)
    ratio = noise[6][0] / noise[12][0]
    print(f"   代償(良いフレームだけ {len(good)} 枚を使い、星ごとの平均を引いて"
          f"**雑音だけ**を取り出した): 6 枚合成 x {noise[6][1]} 回 = "
          f"{100 * noise[6][0]:.4f} %  vs  12 枚合成 x {noise[12][1]} 回 = "
          f"{100 * noise[12][0]:.4f} %  → {ratio:.3f} 倍(理論 √2 = "
          f"{np.sqrt(2):.3f})—— **選別は雑音を √2 払って系統誤差を買う取引**")
    assert abs(ratio / np.sqrt(2) - 1.0) < 0.12, (noise, ratio)
    timing["段4 lucky"] = time.perf_counter() - t0

    # ------------------------------------------------------------------ #
    # 5) 速さ(assert しない。正しさだけを assert し、時間は印字に留める)   #
    # ------------------------------------------------------------------ #
    print("5) 速さ(参考値・assert しない):  " + "  ".join(
        f"{k} {v:.2f} s" for k, v in timing.items())
        + f"  合計 {sum(timing.values()):.2f} s")

    print(f"PASS: 孤立星 {n_iso} 個 x 反復 {N_POOL}/N 回 x 3 星野で、"
          f"測光誤差は 1 枚 {100 * stats[1][0]:.4f} % → 16 枚 {100 * stats[16][0]:.4f} %"
          f"(1/√N から最大 {100 * worst:.1f} % のずれ)。宇宙線 12.5 % 汚染で"
          f"単純平均 {100 * cr_mean[1]:+.2f} % に対し κ-σ {100 * cr_clip[1]:+.2f} %。"
          f"drizzle の総フラックス保存 {worst_rel:.1e} と、その保存則を使った"
          f"独立経路の測光が合成経由と {100 * abs(np.median(err_d) - np.median(err_s)):.4f} % "
          f"以内で一致。lucky 選別は良い 6 枚を完全に当てたが、"
          f"効き目は開口 r=12 px で {100 * abs(table[12.0][0][0]):.3f} %、"
          f"r=6 px で {100 * abs(table[6.0][0][0]):.1f} % と 30 倍違う")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
