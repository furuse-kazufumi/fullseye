# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""複眼は光場センサ —— 神経重ね合わせで「重ねると頑健になる」を光学で測る。

    py -3.11 examples/poc_compound_eye.py

ハエの複眼(アポジション眼)は、個眼(ommatidium)ごとに少しずつ違う方向を
見る。個眼アレイ＝マイクロレンズアレイであり、複眼はプレノプティック・カメラと
**同じ 4 次元光場**をサンプリングしている。そしてショウジョウバエには
**神経重ね合わせ(neural superposition)** がある —— 隣接する 6 個の個眼の
photoreceptor(R1–R6)が**外界の同一点**を見て信号をプールする。これは同じ方向を
複数サンプルで冗長取得する光学であり、開口合成(synthetic aperture)の生物実装だ。

この PoC が測る唯一の主張:

    **同一点を N サンプルで重ね合わせると、独立ノイズは √N で落ちる。ただし
    √N が成り立つのは小さい N だけで、大開口では飽和する —— 重ねはタダではない。**

これは上位計画 "Beelzebub"(多数のハエ全脳コネクトームを重ね合わせる超個体モデル)の
核心仮説「重畳数 N に対する頑健性のスケーリング則」を、コネクトームに触る前に
**光学ドメインで先に実測**したもの。集団知能は必ず得をするとは限らない(重ねても
効かない条件がある)という警句への、測れる形での応答でもある。

EXTEND: 実データに差し替えるなら :func:`ommatidial_scene` だけを差し替える。以降は
光場配列 ``(V, U, H, W)`` と真値スロープ地図 ``(H, W)`` の 2 つしか見ていない。実写の
プレノプティック生フレーム(マイクロレンズアレイ式カメラの出力)は
:func:`lightfield.lf_from_mla` で整流済みフレームから ``(V, U, H, W)`` に復号できる
(マイクロレンズ中心のサブピクセル較正は同モジュールの範囲外)。真値つきの光場は
HCI 4D Light Field Benchmark(Honauer et al., ACCV 2016)が最も近い。

**データはこのリポジトリに同梱しない。** ここで使う光場は既知スロープから合成した
テストベッド(:func:`lightfield.lf_synthesize`)で、外部データセットは要らない。

この PoC が使う物理:

    スロープ s = 角度インデックス 1 ステップあたりの画素シフト [px/view]。
    半径 r の円形開口が選ぶ視点数 N。等重み平均は N 視点の平均なので、
    独立ノイズの標準偏差は理想的には 1/√N に落ちる(sum(w^2)=1/N)。

実測(2026-09-13、9x9x64x64・単層透過・視点あたり SNR=2.0、seed 固定):

    半径 r   視点 N   SNR 利得   √N
      0        1      1.00      1.00
      1        5      2.25      2.24     ← ハエの神経重ね合わせ(~6)はこの領域
      2       13      3.57      3.61
      3       29      4.82      5.39
      4       49      5.33      7.00     ← √N から明確に飽和(補間誤差は平均化されない)

    小開口では √N がほぼ厳密。大開口では shift-and-add の補間誤差(視点間で相関する)が
    独立ノイズのように消えず、利得が √N を下回って飽和する。ハエが ~6 個(半径 1)で
    止めているのは、利得がまだ √N のまま伸びる領域 —— 進化は膝の手前で降りている。

参考: M. F. Land, D.-E. Nilsson, *Animal Eyes* (Oxford, 2012);
神経重ね合わせ = Kirschfeld (1967)。複眼とプレノプティックの等価性 = Ng et al. (2005)。
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import lightfield as L  # noqa: E402

ANGULAR = (9, 9)          # 9x9 の個眼アレイ(視点グリッド)
SHAPE = (64, 64)          # 各サブアパーチャ像(=個眼が見る網膜像)の画素
V_C = (ANGULAR[0] - 1) // 2
U_C = (ANGULAR[1] - 1) // 2


# ---------------------------------------------------------------------------- #
#  シーン(差し替え点)                                                          #
# ---------------------------------------------------------------------------- #
def ommatidial_scene(slopes, *, occlusion, seed, coverage=0.55):
    """既知スロープの層から光場を作る。返り値 = ((V,U,H,W), 真値スロープ地図(H,W))。"""
    lf, smap = L.lf_synthesize(slopes=slopes, angular=ANGULAR, shape=SHAPE,
                               occlusion=occlusion, coverage=coverage, seed=seed)
    return np.asarray(lf), np.asarray(smap)


def two_depth_scene(near_slope, far_slope, *, seed_near, seed_far):
    """手前/奥の 2 深度を左右に貼り合わせた光場(細かい交錯の無い、曖昧さの小さい距離).

    ``lf_synthesize`` の遮蔽合成は細かいランダムマスクで焦点度窓が深度をまたぎ、
    強い視差の前景に引きずられる(実測: 全画素が最大スロープに張り付く)。ここでは
    半導体の「手前の部品/奥の基板」のように **大きく分かれた 2 領域** にして、
    アレイが領域ごとの距離を出せることを見る(境界±数画素は視差でにじむ)。
    """
    near, _ = L.lf_synthesize(slopes=(near_slope,), angular=ANGULAR, shape=SHAPE,
                              occlusion=False, seed=seed_near)
    far, _ = L.lf_synthesize(slopes=(far_slope,), angular=ANGULAR, shape=SHAPE,
                             occlusion=False, seed=seed_far)
    near = np.asarray(near); far = np.asarray(far)
    half = SHAPE[1] // 2
    lf = far.copy()
    lf[..., :half] = near[..., :half]     # 左=手前, 右=奥
    truth = np.full(SHAPE, far_slope, dtype=float)
    truth[:, :half] = near_slope
    return lf, truth, half


def add_photoreceptor_noise(lf, per_view_snr, *, seed):
    """個眼ごとに独立なガウスノイズを足す(光子ショット/読み出しノイズの代理)。"""
    rng = np.random.default_rng(seed)
    sig = float(np.asarray(L.lf_subaperture(lf, v=V_C, u=U_C)).std())
    noise_std = sig / per_view_snr
    noisy = lf + rng.normal(0.0, noise_std, size=lf.shape)
    return noisy, sig, noise_std


# ---------------------------------------------------------------------------- #
#  第 1 章 —— 複眼を光学設計する(プレノプティック系として)                      #
# ---------------------------------------------------------------------------- #
def chapter_optical_design():
    """複眼スケールのプレノプティック系を設計し、角度/空間分解能と深度精度を出す。

    複眼とプレノプティック・カメラは同じ光場を採る。ここでは Fullseye の仮想光学設計
    ``lf_plenoptic_design`` で「個眼ピッチ↔マイクロレンズピッチ」の対応をとった系を
    サイジングし、視点数(=重ね合わせに使える冗長度)と深度分解能を読む。
    """
    d = L.lf_plenoptic_design(focal_mm=12.0, f_number=4.0, object_mm=120.0,
                              pixel_um=3.45, mla_pitch_um=31.05,
                              sensor_px=(1152, 1152))
    print("== 第1章: 複眼スケールのプレノプティック光学設計 ==")
    print("  角度分解能(個眼あたり方向数) : %d x %d  (exact %.3f)"
          % (d["angular_v"], d["angular_u"], d["angular_exact"]))
    print("  空間分解能(個眼数=サブ像画素) : %d x %d" % (d["spatial_h"], d["spatial_w"]))
    print("  視点数 n_views               : %d" % d["n_views"])
    print("  基線 baseline                : %.4f mm" % d["baseline_mm"])
    print("  リフォーカス利得 refocus_gain : %.3f  (= 角度分解能)" % d["refocus_gain"])
    print("  深度精度 depth_precision     : %.3f mm  @ %d mm" % (d["depth_precision_mm"], 120))
    return d


# ---------------------------------------------------------------------------- #
#  第 2 章 —— 神経重ね合わせ = 開口合成。SNR の N-スケーリングを測る                #
# ---------------------------------------------------------------------------- #
def chapter_superposition_scaling():
    """同一点を N 個眼で重ねると独立ノイズが √N で落ちる —— どこまで成り立つか。"""
    slope = 1.0
    lf, _ = ommatidial_scene((slope,), occlusion=False, seed=1)  # 透過単層 = 曖昧さ無し
    noisy, sig, nstd = add_photoreceptor_noise(lf, per_view_snr=2.0, seed=0)
    clean = np.asarray(L.lf_subaperture(lf, v=V_C, u=U_C))

    print("\n== 第2章: 神経重ね合わせの N-スケーリング ==")
    print("  信号 std=%.4f / ノイズ std=%.4f / 視点あたり SNR=%.2f" % (sig, nstd, sig / nstd))
    print("  半径 r  視点 N   RMS(重ね-真)   SNR利得   √N")
    rows = []
    base_rms = None
    single_view = None
    pooled_full = None
    for r in (0, 1, 2, 3, 4):
        mask = np.asarray(L.lf_aperture_mask(angular=ANGULAR, shape="circle",
                                             radius=r, normalize=True))
        n = int((mask > 0).sum())
        pooled = np.asarray(L.lf_synthetic_aperture(noisy, slope=slope, mask=mask,
                                                    reduce="mean"))
        rms = float(np.sqrt(np.mean((pooled - clean) ** 2)))
        if base_rms is None:
            base_rms = rms
            single_view = pooled
        pooled_full = pooled
        gain = base_rms / rms
        rows.append((r, n, rms, gain, float(np.sqrt(n))))
        print("   %d      %2d     %.4f        %.2f     %.2f" % (r, n, rms, gain, np.sqrt(n)))

    figs.save_plot(
        "compound_eye_scaling",
        [("実測 SNR 利得", [r[1] for r in rows], [r[3] for r in rows]),
         ("√N(独立ノイズの理想)", [r[1] for r in rows], [r[4] for r in rows])],
        xlabel="重ね合わせた個眼数 N", ylabel="SNR 利得(=RMS の逆比)",
        title="神経重ね合わせ: √N は小開口だけ、大開口で飽和",
        caption="ハエの神経重ね合わせ ~6(半径1)は √N が厳密に成り立つ領域。")
    figs.save_grid(
        "compound_eye_superposition",
        [clean, single_view, pooled_full],
        captions=["真の像(ノイズ無し)", "個眼 1 枚(視点あたり SNR 2.0)",
                  "神経重ね合わせ(半径4・49視点)"],
        title="個眼 1 枚 → 重ね合わせ", gray=True)
    return rows


# ---------------------------------------------------------------------------- #
#  第 3 章 —— アレイでこそ距離が出る(1 個眼には視差が無い)                        #
# ---------------------------------------------------------------------------- #
def chapter_depth_needs_the_array():
    """深度は光場アレイの性質。手前/奥の 2 領域をノイズ下でも距離画像として分離する。"""
    near_slope, far_slope = 2.0, 0.5     # 手前=視差大, 奥=視差小
    lf, truth, half = two_depth_scene(near_slope, far_slope, seed_near=11, seed_far=22)
    noisy, _sig, _n = add_photoreceptor_noise(lf, per_view_snr=6.0, seed=5)

    sweep = tuple(np.linspace(-0.5, 2.5, 31))
    dmap, sharp = L.lf_depth_from_focus(noisy, slopes=sweep, window=9,
                                        measure="laplacian", subpixel=True)
    dmap = np.asarray(dmap); sharp = np.asarray(sharp)
    conf = sharp > np.percentile(sharp, 50)
    # 境界 ±8px は視差でにじむので内部だけで層を測る
    near_m = np.zeros(SHAPE, bool); near_m[8:-8, 8:half - 8] = True
    far_m = np.zeros(SHAPE, bool); far_m[8:-8, half + 8:-8] = True
    err = float(np.sqrt(np.mean((dmap[(near_m | far_m) & conf]
                                 - truth[(near_m | far_m) & conf]) ** 2)))
    layer_hit = {near_slope: float(np.median(dmap[near_m & conf])),
                 far_slope: float(np.median(dmap[far_m & conf]))}

    aif = np.asarray(L.lf_all_in_focus(noisy, dmap, n_levels=16))

    print("\n== 第3章: アレイでこそ距離が出る(手前部品/奥基板) ==")
    print("  焦点度スイープ深度 RMSE(領域内部・信頼画素) : %.3f  [px/view]" % err)
    for s, hit in layer_hit.items():
        tag = "手前" if s == near_slope else "奥"
        print("    %s slope=%+.2f -> 推定中央値 %+.3f" % (tag, s, hit))

    figs.save_grid(
        "compound_eye_depth",
        [truth, dmap, aif],
        captions=["真の距離(手前=左/奥=右)", "推定距離(焦点度スイープ)",
                  "全焦点像(各画素を自分の距離で合焦)"],
        title="ノイズ下でもアレイは距離画像を出す",
        signed=[True, True, False], gray=[False, False, True])
    return err, layer_hit, near_slope, far_slope


# ---------------------------------------------------------------------------- #
#  第 4 章 —— 重ねはタダではない(遮蔽と mean/median)                            #
# ---------------------------------------------------------------------------- #
def chapter_pooling_is_not_free():
    """少数視点を塞ぐ遮蔽者は median なら貫けるが、半数を超えると保証は消える。"""
    # 背景(遠, slope 0.3)+ 手前の遮蔽者(近, slope 3.0)を低 coverage で = 少数派の遮蔽。
    bg_slope = 0.3
    lf, truth = ommatidial_scene((bg_slope, 3.0), occlusion=True, seed=7, coverage=0.25)
    center = np.asarray(L.lf_subaperture(lf, v=V_C, u=U_C))
    hidden = (np.abs(truth - bg_slope) > 1e-6)   # 中心視点で前景に隠れた背景画素
    mask = np.asarray(L.lf_aperture_mask(angular=ANGULAR, shape="circle",
                                         radius=4, normalize=True))
    mean_pool = np.asarray(L.lf_synthetic_aperture(lf, slope=bg_slope, mask=mask,
                                                   reduce="mean"))
    med_pool = np.asarray(L.lf_synthetic_aperture(lf, slope=bg_slope, mask=mask,
                                                  reduce="median"))
    # 隠れた背景の真値 = 遮蔽なしで同じ背景層だけ合成したもの
    bg_only, _ = ommatidial_scene((bg_slope,), occlusion=False, seed=7)
    bg_truth = np.asarray(L.lf_subaperture(bg_only, v=V_C, u=U_C))

    def rms_hidden(img):
        return float(np.sqrt(np.mean((img[hidden] - bg_truth[hidden]) ** 2))) if hidden.any() else 0.0

    r_center, r_mean, r_med = rms_hidden(center), rms_hidden(mean_pool), rms_hidden(med_pool)
    frac = float(hidden.mean())
    print("\n== 第4章: 重ねはタダではない(遮蔽) ==")
    print("  隠れた背景を覆う前景の面積 : %.1f%%" % (100 * frac))
    print("  隠れ画素の RMS vs 真の背景 : 中心1枚=%.3f  mean重ね=%.3f  median重ね=%.3f"
          % (r_center, r_mean, r_med))

    figs.save_grid(
        "compound_eye_occlusion",
        [center, mean_pool, med_pool, bg_truth],
        captions=["個眼 1 枚(前景に隠れる)", "mean 重ね(前景が滲む)",
                  "median 重ね(前景を貫いて背景)", "隠れた背景の真値"],
        title="median は少数派の遮蔽者を捨てる —— 半数を超えると保証は消える",
        gray=True)
    return r_center, r_mean, r_med, frac


def main():
    with warnings.catch_warnings():
        warnings.simplefilter("error")     # 黙ったゼロ割・NaN を出させない
        design = chapter_optical_design()
        scaling = chapter_superposition_scaling()
        depth_err, layer_hit, near_slope, far_slope = chapter_depth_needs_the_array()
        occ_center, occ_mean, occ_med, occ_frac = chapter_pooling_is_not_free()

    # ---- 自己検査 ---------------------------------------------------------- #
    # 第1章: 光学設計は教科書どおり(リフォーカス利得 = 角度分解能)。
    assert abs(design["refocus_gain"] - design["angular_exact"]) < 0.15, \
        "リフォーカス利得が角度分解能に一致しない"
    assert design["depth_precision_mm"] > 0, "深度精度が非正"

    # 第2章: 利得は単調増加、半径1(=ハエの ~6)は √N がほぼ厳密、
    #         大開口(半径4)は √N から明確に飽和する(重ねはタダではない)。
    gains = [g for _r, _n, _rms, g, _s in scaling]
    assert gains == sorted(gains), "重ねるほど SNR 利得が増える、が崩れた"
    r1 = next(row for row in scaling if row[0] == 1)
    assert abs(r1[3] - r1[4]) < 0.15, "半径1(ハエ域)で √N から外れすぎ"
    r4 = next(row for row in scaling if row[0] == 4)
    assert r4[3] < 0.85 * r4[4], "大開口が √N で伸び続けた(飽和の膝が無い=非物理)"

    # 第3章: ノイズ下でも手前(視差大)と奥(視差小)を距離として分離できる。
    assert layer_hit[near_slope] > layer_hit[far_slope] + 0.5, \
        "手前と奥の距離が分離できていない"
    assert depth_err < 0.2, "領域内部の深度 RMSE が大きすぎる(アレイが距離を出せていない)"

    # 第4章: 遮蔽は少数派(coverage 0.25 < 半数)、median は貫いて背景に近い。
    assert occ_frac < 0.5, "遮蔽が半数超 = median の保証域外(前提が崩れている)"
    assert occ_med < occ_mean, "median が mean より隠れ背景に近くない"
    assert occ_med < occ_center, "median が中心1枚より隠れ背景に近くない"

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))

    # ★PoC の門(tests/test_poc_scripts_run.py)は exit 0 に加えて "PASS" の印字を
    #   要求する(合否を計算したのに捨てる門を防ぐ規約)。以前は "OK:" と書いていて、
    #   台帳に登録した瞬間に「exit 0 だが PASS を印字していない」で落ちた。
    print("\nPASS: 複眼=光場、神経重ね合わせの N-スケーリング(膝つき)、"
          "アレイの距離画像、median の透視 —— すべて実測で確認。")


if __name__ == "__main__":
    main()
