# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PIV の派生 op を一巡する —— 場の量・可視化・採点・アンサンブル・時間統計を、閉形式の真値で検算する。

``examples/piv_flow_from_particles.py`` が「2 枚から変位場を出す」本筋なら、こちらは
**出た変位場をどう読むか**の道具箱を一つずつ、答えを知っている入力で確かめる例。

★EXTEND: 実験の粒子画像に差し替えるなら、節 3(1 対)は ``a``/``b`` を、
節 6〜8(画像列)は ``frames`` を ``imgio.load`` の返りに置き換える。真値 ``truth`` を
使う assert はそのとき落とし、代わりに節 5 の ZNCC 採点と節 4 の閾値掃引が残る ——
真値が無くても「どこが信じられるか」だけは言える、というのがこの例の主眼。

この例が示すこと(グラウンドトゥルース):

1. **粒子像の合成**(``piv_synth_particles``)—— 粒子数は ``density × 画素数`` で
   決まり、画像の総輝度はガウス輝点の積分 ``a·2πσ²`` の和に一致し、孤立粒子の
   輝度重心は返された連続座標に 0.05 px 以内で乗る。``speckle_quality`` の斑点径
   推定は FWHM(``1.1774 × diameter_px``)に 5 % 以内で乗る。
2. **場の量は閉形式で検算できる**(``piv_velocity_gradient`` /
   ``piv_q_criterion`` / ``piv_swirling_strength`` / ``piv_strain_rate`` /
   ``piv_flow_magnitude``)—— 剛体回転 ω・一様膨張 s・単純せん断 g は線形場なので
   差分が厳密に当たり、Q = ω² / -s² / 0、λ_ci = ω / 0 / 0、ひずみ = 0 / 2s / g。
3. **窓変形**(``piv_deform_pass``)—— 窓の中で変位が変わる滑らかな渦
   (Lamb–Oseen)で、整数ずらしの多段より誤差が下がる。
4. **Q 基準は閾値の産物になりうる** —— 芯の Q は ω² に乗り、渦の面積は閾値で変わる。
5. **既にある場の採点**(``correlation_quality``)—— 正しい場は ZNCC ≈ 1、
   一部を壊すとそこだけ落ちる。ゲインとオフセットに不変。
6. **アンサンブル相関**(``piv_ensemble_correlate``)—— 粒子が少なく雑音が多い
   定常流(``piv_synth_sequence``)で、1 対ずつの平均より外れ本数が減り中央誤差が下がる。
   **RMS は両方とも外れ値に支配される**ので、RMS だけ見ると差が見えない(隠さず印字)。
7. **時間統計**(``piv_time_statistics``)—— 場全体を揺らした列で、時間 RMS が
   「各対の場の中央値の RMS」という独立な経路と一致する。
8. **ピークロッキング**(``piv_peak_locking``)—— 同じ場で centroid の c0 が gauss3 を上回る。
9. **可視化**(``piv_flow_to_rgbimage`` / ``piv_line_integral_convolution``)——
   右・上・左・下の 4 方向が決まった色に写り、LIC の縞は流れの向きに伸びる。

読み方: 各節で「真値」「測定」「差」を並べて印字し、末尾の assert が閾値。速さは
印字するだけで assert しない。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

# リポジトリ直下を通す(この例は ``fullseye`` を import しないのでパスフックが効かない)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dic                                                       # noqa: E402
import pivops                                                    # noqa: E402

H = W = 256
CY, CX = (H - 1) / 2.0, (W - 1) / 2.0
GAMMA, RC = 900.0, 40.0                     # Lamb–Oseen 渦の循環と芯半径 [px]
OMEGA = GAMMA / (2.0 * np.pi * RC ** 2)     # 芯の角速度 [rad/frame](r→0 の極限)


def lamb_oseen_vortex(rows, cols):
    """滑らかな渦 v_t = γ/(2πr)·(1 - exp(-(r/rc)²))。非圧縮(発散 0)。

    芯の縁で勾配が折れる Rankine 渦と違い、どこでも滑らかなので**窓変形が効く**
    (折れ目は変形では追えない —— それは piv_flow_from_particles.py が扱う話)。
    """
    dy_c, dx_c = rows - CY, cols - CX
    r = np.hypot(dy_c, dx_c)
    r_safe = np.maximum(r, 1e-9)
    v_t = GAMMA / (2.0 * np.pi * r_safe) * (1.0 - np.exp(-(r / RC) ** 2))
    return v_t * (-dx_c / r_safe), v_t * (dy_c / r_safe)


def linear_field(kind, amount, n=24):
    """閉形式の線形場を格子に置く。``(2, n, n)`` の ``(dy, dx)``。

    ★EXTEND: 自分の解析場を試すなら、ここに ``(dy, dx)`` を返す分岐を足す。
    """
    y, x = np.mgrid[0:n, 0:n].astype(np.float64)
    y -= (n - 1) / 2.0
    x -= (n - 1) / 2.0
    if kind == "rotation":          # u = -ω y, v = ω x
        return np.stack([amount * x, -amount * y])
    if kind == "expansion":         # u = s x, v = s y
        return np.stack([amount * y, amount * x])
    if kind == "shear":             # u = g y, v = 0
        return np.stack([np.zeros_like(x), amount * y])
    raise ValueError(kind)


def _isolated_centroid_error(img, pos, sigma, min_gap=8.0, half=3):
    """孤立した粒子(最近傍が min_gap px より遠い)の輝度重心と真の位置の差。"""
    d2 = np.sum((pos[:, None, :] - pos[None, :, :]) ** 2, axis=-1)
    np.fill_diagonal(d2, np.inf)
    inside = ((pos[:, 0] > half + 3) & (pos[:, 0] < img.shape[0] - half - 4)
              & (pos[:, 1] > half + 3) & (pos[:, 1] < img.shape[1] - half - 4))
    iso = np.nonzero((np.sqrt(d2.min(axis=1)) > min_gap) & inside)[0]
    err, peaks = [], []
    for i in iso:
        py, px = pos[i]
        r, c = int(round(py)), int(round(px))
        win = img[r - half:r + half + 1, c - half:c + half + 1]
        yy, xx = np.mgrid[r - half:r + half + 1, c - half:c + half + 1]
        err.append([(win * yy).sum() / win.sum() - py, (win * xx).sum() / win.sum() - px])
        peaks.append(float(win.max()))
    err = np.array(err)
    return len(iso), float(np.sqrt(np.mean(np.sum(err ** 2, axis=1)))), min(peaks), max(peaks)


def _anisotropy(im, lag):
    """横方向の変化 / 縦方向の変化(lag 画素差)。横縞なら 1 より小、縦縞なら大。"""
    dx = float(np.mean(np.abs(im[:, lag:] - im[:, :-lag])))
    dy = float(np.mean(np.abs(im[lag:] - im[:-lag])))
    return dx / dy


def run() -> dict:
    t0 = time.perf_counter()
    out = {}

    # ------------------------------------------------------------------ 1
    print("=== 1. 粒子像の合成と、斑点の品質 ===")
    density, diam = 0.02, 2.5
    img, pos = pivops.piv_synth_particles((H, W), density=density, diameter_px=diam,
                                          seed=3, intensity=(0.6, 1.0))
    n_want = int(round(density * H * W))
    # 真値: 粒子は画像の外側 3×直径 まで撒かれる(縁で欠けた粒子のバイアス避け)。
    # 画像内に落ちる期待個数 × 平均輝度 0.8 × ガウス輝点の積分 2πσ² が総輝度
    sigma = diam / 2.0
    pad = 3.0 * diam
    inside = (H * W) / ((H + 2 * pad) * (W + 2 * pad))
    sum_want = n_want * inside * 0.8 * 2.0 * np.pi * sigma ** 2
    sum_got = float(img.sum())
    n_iso, cen_rms, pk_lo, pk_hi = _isolated_centroid_error(img, pos, sigma)
    print(f"  粒子数 {len(pos)}(真値 {n_want})/ 総輝度 {sum_got:.1f}"
          f"(期待 {sum_want:.1f}、差 {100 * (sum_got / sum_want - 1):+.2f} %)")
    print(f"  孤立粒子 {n_iso} 個の輝度重心と真の位置の差 RMS {cen_rms:.4f} px"
          f" / 頂点輝度 {pk_lo:.3f}..{pk_hi:.3f}(輝度範囲 0.6..1.0 × 副画素の落ち)")
    sq = dic.speckle_quality(img)
    fwhm = 2.0 * np.sqrt(2.0 * np.log(2.0)) * sigma       # = 1.1774 × diameter_px
    print(f"  speckle_quality: 斑点径 {sq['mean_blob_diameter_px']:.3f} px"
          f"(FWHM の真値 {fwhm:.3f})/ MIG {sq['mig']:.4f} / 被覆 {sq['coverage']:.3f}")
    out["particles"] = {"n": len(pos), "n_want": n_want,
                        "sum_rel_err": sum_got / sum_want - 1.0,
                        "centroid_rms_px": cen_rms, "n_isolated": n_iso,
                        "blob_rel_err": sq["mean_blob_diameter_px"] / fwhm - 1.0}

    # ------------------------------------------------------------------ 2
    print("\n=== 2. 場の量を閉形式で検算(線形場は差分が厳密に当たる)===")
    print(f"  {'場':<10} {'Q':>10} {'真値':>10} {'λ_ci':>8} {'真値':>6} {'ひずみ':>8} {'真値':>6} {'|渦度|':>8} {'真値':>6}")
    om, s, g = 0.01, 0.01, 0.02
    want = {"rotation": (om, om * om, om, 0.0, 2 * om),
            "expansion": (s, -s * s, 0.0, 2 * s, 0.0),
            "shear": (g, 0.0, 0.0, g, g)}
    field_err = 0.0
    for kind, (amt, q_w, sw_w, st_w, vo_w) in want.items():
        f = linear_field(kind, amt)
        grad = pivops.piv_velocity_gradient(f, spacing=1.0)
        q = pivops.piv_q_criterion(f, 1.0)
        sw = pivops.piv_swirling_strength(f, 1.0)
        st = pivops.piv_strain_rate(f, 1.0)
        vo = np.abs(grad["vorticity"])
        # 個別 op は一括 op と同じ値を返す(同じ 4 微分から出る)
        assert np.allclose(q, grad["q"]) and np.allclose(sw, grad["swirl"]) \
            and np.allclose(st, grad["strain_rate"])
        e = max(abs(float(q.mean()) - q_w), abs(float(sw.mean()) - sw_w),
                abs(float(st.mean()) - st_w), abs(float(vo.mean()) - vo_w),
                float(q.std()), float(sw.std()), float(st.std()), float(vo.std()))
        field_err = max(field_err, e)
        print(f"  {kind:<10} {q.mean():>+10.2e} {q_w:>+10.2e} {sw.mean():>8.4f} {sw_w:>6.3f}"
              f" {st.mean():>8.4f} {st_w:>6.3f} {vo.mean():>8.4f} {vo_w:>6.3f}")
    # 速さ |v| = ω r は剛体回転で厳密
    f_rot = linear_field("rotation", om)
    yy, xx = np.mgrid[0:24, 0:24].astype(np.float64) - 11.5
    mag = pivops.piv_flow_magnitude(f_rot)
    mag_err = float(np.max(np.abs(mag - om * np.hypot(yy, xx))))
    div_exp = float(pivops.piv_velocity_gradient(linear_field("expansion", s))["divergence"].mean())
    print(f"  |v| = ω r の最大誤差 {mag_err:.1e} / 一様膨張の発散 = 2s = {2 * s:.3f} → {div_exp:.4f}")
    out["field_closed_form_max_err"] = field_err
    out["magnitude_max_err"] = mag_err

    # ------------------------------------------------------------------ 3
    print("\n=== 3. 窓変形 —— 窓の中で変位が変わる滑らかな渦で、多段(整数ずらし)と比べる ===")
    a, b, truth = pivops.piv_synth_pair((H, W), lamb_oseen_vortex,
                                        density=0.02, diameter_px=2.5, seed=7)
    print(f"  Lamb–Oseen 渦: 芯半径 {RC:.0f} px / 最大変位 {np.hypot(*truth).max():.2f} px"
          f" / 窓 32 の中で変位が最大 {32 * OMEGA:.2f} px 変わる")
    sflow, sinfo = pivops.piv_cross_correlate(a, b, window=32, overlap=0.5)
    ss = pivops.piv_error_stats(sflow, pivops.piv_sample_at_windows(truth, sinfo))
    mflow, minfo = pivops.piv_multipass(a, b, windows=(64, 32), overlap=0.5)
    mt = pivops.piv_sample_at_windows(truth, minfo)
    ms = pivops.piv_error_stats(mflow, mt)
    dflow, dinfo = pivops.piv_deform_pass(a, b, mflow, minfo, window=32, overlap=0.5)
    dt = pivops.piv_sample_at_windows(truth, dinfo)
    ds = pivops.piv_error_stats(dflow, dt)
    d2flow, d2info = pivops.piv_deform_pass(a, b, dflow, dinfo, window=32, overlap=0.5)
    ds2 = pivops.piv_error_stats(d2flow, pivops.piv_sample_at_windows(truth, d2info))
    print(f"  {'段':<24} {'RMS [px]':>9} {'偏り dy':>9} {'偏り dx':>9} {'ピーク比':>9}")
    for label, st_, inf in (("単段 32", ss, sinfo), ("多段 64→32", ms, minfo),
                            ("+ 窓変形 32", ds, dinfo), ("+ 窓変形 32(2 回目)", ds2, d2info)):
        print(f"  {label:<24} {st_['rms']:>9.4f} {st_['bias_dy']:>+9.4f} {st_['bias_dx']:>+9.4f}"
              f" {np.nanmedian(inf['peak_ratio']):>9.2f}")
    print("  → 変形で相関ピークが立ち直る(ピーク比が上がる)ので誤差が下がる。")
    out["deform"] = {"single_rms": ss["rms"], "multipass_rms": ms["rms"],
                     "deform_rms": ds["rms"], "deform2_rms": ds2["rms"]}

    # ------------------------------------------------------------------ 4
    print("\n=== 4. 測った場の Q 基準 —— 芯は ω² に乗り、面積は閾値で変わる ===")
    step = dinfo["step"]
    q_meas = pivops.piv_q_criterion(dflow, spacing=step)
    q_true = pivops.piv_q_criterion(dt, spacing=step)
    rr = np.hypot(dinfo["rows"][:, None] - CY, dinfo["cols"][None, :] - CX)
    ci = np.unravel_index(int(np.argmin(rr)), rr.shape)
    print(f"  芯の Q: 測定 {q_meas[ci]:+.2e} / 真値を同じ格子で差分 {q_true[ci]:+.2e}"
          f" / 閉形式 ω² {OMEGA ** 2:+.2e}(格子 {step} px の差分は芯の外まで平均するので少し低い)")
    print(f"  {'閾値 Q >':>10} {'面積 測定':>10} {'面積 真値':>10}")
    areas = {}
    for frac in (0.0, 0.1, 0.3, 0.5):
        thr = frac * OMEGA ** 2
        areas[frac] = (int(np.sum(q_meas > thr)), int(np.sum(q_true > thr)))
        print(f"  {thr:>10.1e} {areas[frac][0]:>10d} {areas[frac][1]:>10d}")
    print("  → 「Q > 0」の面積と「Q > 0.5 ω²」の面積は 4 倍違う。閾値を書かない渦図は読めない。")
    out["q_core"] = {"measured": float(q_meas[ci]), "truth_grid": float(q_true[ci]),
                     "closed_form": OMEGA ** 2, "area_by_threshold": areas}

    # ------------------------------------------------------------------ 5
    print("\n=== 5. 既にある変位場の採点(ZNCC)—— 正しい場は 1、壊した所だけ落ちる ===")
    ua, ub, utruth = pivops.piv_synth_pair((H, W), (1.3, -2.6), density=0.02, seed=11)
    uflow, uinfo = pivops.piv_cross_correlate(ua, ub, window=32, overlap=0.5)
    z_ok = dic.correlation_quality(ua, ub, uflow, uinfo, subset=31)
    z_dense = dic.correlation_quality(ua, ub, utruth, subset=31)      # 画素ごとの真値場
    bad = uflow.copy()
    bad[:, 5:9, 5:9] += 3.0                                           # 4x4 窓だけ 3 px ずらす
    z_bad = dic.correlation_quality(ua, ub, bad, uinfo, subset=31)
    r0, r1 = int(uinfo["rows"][5]), int(uinfo["rows"][8])
    c0, c1 = int(uinfo["cols"][5]), int(uinfo["cols"][8])
    broken = float(np.nanmedian(z_bad[r0:r1, c0:c1]))
    healthy = float(np.nanmedian(z_bad[150:220, 150:220]))
    # ゲイン・オフセット不変: cur を 1.7 倍 + 0.2 しても同じ採点
    z_gain = dic.correlation_quality(ua, ub * 1.7 + 0.2, uflow, uinfo, subset=31)
    print(f"  相関で測った場   ZNCC 中央値 {np.nanmedian(z_ok):.5f}")
    print(f"  画素ごとの真値場 ZNCC 中央値 {np.nanmedian(z_dense):.5f}")
    print(f"  4x4 窓を 3 px 壊す → 壊した領域 {broken:.4f} / 健全領域 {healthy:.4f}")
    print(f"  ゲイン 1.7 + オフセット 0.2 → 差の最大 {np.nanmax(np.abs(z_gain - z_ok)):.1e}")
    print(f"  測れなかった画素(縁)の割合 {np.isnan(z_ok).mean():.3f}(サブセット 31 の半分 = 15 px の額縁)")
    out["zncc"] = {"measured": float(np.nanmedian(z_ok)), "truth": float(np.nanmedian(z_dense)),
                   "broken": broken, "healthy": healthy,
                   "gain_invariance": float(np.nanmax(np.abs(z_gain - z_ok)))}

    # ------------------------------------------------------------------ 6
    print("\n=== 6. アンサンブル相関 —— 粒子が少なく(窓に 3 個)雑音の多い定常流 ===")
    disp = (2.3, -1.7)
    frames, seq_truth = pivops.piv_synth_sequence((H, W), disp, n_frames=16, density=0.003,
                                                  diameter_px=2.5, seed=5, noise_sigma=0.1)
    assert len(frames) == 16 and np.allclose(seq_truth[0], disp[0]) and np.allclose(seq_truth[1], disp[1])
    eflow, einfo = pivops.piv_ensemble_correlate(frames, window=32, overlap=0.5)
    et = pivops.piv_sample_at_windows(seq_truth, einfo)
    es = pivops.piv_error_stats(eflow, et)
    pair_flows = np.stack([pivops.piv_cross_correlate(frames[k], frames[k + 1], 32, 0.5)[0]
                           for k in range(len(frames) - 1)])
    avg = np.nan_to_num(np.nanmean(pair_flows, axis=0), nan=0.0)
    ps = pivops.piv_error_stats(avg, et)
    inner = (slice(1, -1), slice(1, -1))
    out_e = float(np.mean(np.hypot(*(eflow - et))[inner] > 1.0))
    out_p = float(np.mean(np.hypot(*(avg - et))[inner] > 1.0))
    print(f"  {'方法':<30} {'中央誤差':>9} {'外れ(>1px)':>11} {'RMS':>8}")
    print(f"  {'1 対ずつ測って平均(' + str(einfo['pairs']) + ' 対)':<30} {ps['median_abs']:>9.3f}"
          f" {100 * out_p:>10.0f}% {ps['rms']:>8.3f}")
    print(f"  {'相関を足してから探す':<30} {es['median_abs']:>9.3f} {100 * out_e:>10.0f}% {es['rms']:>8.3f}")
    print("  → 弱いピークが同じ場所に積み上がり、外れ本数が桁で減る。RMS はどちらも"
          "残った外れ値(探索上限 8 px まで飛ぶ)に支配されるので、RMS だけでは差が見えない。")
    out["ensemble"] = {"pair_mean_median": ps["median_abs"], "ensemble_median": es["median_abs"],
                       "pair_mean_outlier": out_p, "ensemble_outlier": out_e,
                       "pair_mean_rms": ps["rms"], "ensemble_rms": es["rms"]}

    # ------------------------------------------------------------------ 7
    print("\n=== 7. 時間統計 —— 場全体を揺らした列の RMS を、独立な経路で検算 ===")
    jit = 0.3
    tframes, ttruth = pivops.piv_synth_sequence((192, 192), (1.5, 2.0), n_frames=12,
                                                density=0.02, seed=9, jitter=jit)
    ts = pivops.piv_time_statistics(tframes, window=32, overlap=0.5)
    # 独立な検算: 各対の場は「一様 + そのコマの揺れ」なので、場の中央値 = その対の変位。
    # その時間 RMS が、窓ごとの時間 RMS の中央値と一致するはず(揺れは場全体で共通)
    per_pair = np.array([[np.nanmedian(f[0]), np.nanmedian(f[1])] for f in
                         (pivops.piv_cross_correlate(tframes[k], tframes[k + 1], 32, 0.5)[0]
                          for k in range(len(tframes) - 1))])
    ref_mean = per_pair.mean(axis=0)
    ref_rms = per_pair.std(axis=0)
    got_mean = np.array([np.nanmedian(ts["mean"][0]), np.nanmedian(ts["mean"][1])])
    got_rms = np.array([np.nanmedian(ts["rms"][0]), np.nanmedian(ts["rms"][1])])
    print(f"  対の数 {ts['n_pairs']}(真値 {len(tframes) - 1})")
    print(f"  時間平均  窓の中央値 ({got_mean[0]:.4f}, {got_mean[1]:.4f})"
          f" / 対ごとの中央値の平均 ({ref_mean[0]:.4f}, {ref_mean[1]:.4f})"
          f" / 仕込み (1.5, 2.0) + 揺れの平均")
    print(f"  時間 RMS  窓の中央値 ({got_rms[0]:.4f}, {got_rms[1]:.4f})"
          f" / 対ごとの中央値の RMS ({ref_rms[0]:.4f}, {ref_rms[1]:.4f})"
          f" / 仕込み σ={jit}(標本 {ts['n_pairs']} 個なので ±25 % は揺れる)")
    print(f"  レイノルズ応力 <u'v'> 中央値 {np.nanmedian(ts['reynolds']):+.4f}"
          f"(独立な揺れなので 0 前後)/ 乱れ強さ {np.nanmedian(ts['turbulence_intensity']):.3f}")
    out["time_stats"] = {"n_pairs": ts["n_pairs"], "mean_gap": float(np.max(np.abs(got_mean - ref_mean))),
                         "rms_gap": float(np.max(np.abs(got_rms - ref_rms))), "rms_got": got_rms.tolist()}

    # ------------------------------------------------------------------ 8
    print("\n=== 8. ピークロッキング —— 同じ場で推定法だけ変える ===")

    def ramp(rows, cols):
        """小数部が一様に散る線形ランプ。"""
        return 0.5 + 0.017 * rows, -1.0 + 0.023 * cols

    # 窓を 3/4 重ねて 29x29 = 841 本にする(20 階級 × 2 成分で 1 階級 42 本)
    ra, rb, rtruth = pivops.piv_synth_pair((H, W), ramp, density=0.02, seed=13)
    c0s = {}
    for mode in pivops.PEAK_MODES:
        rf, rinfo = pivops.piv_cross_correlate(ra, rb, 32, 0.75, peak=mode)
        c0s[mode] = pivops.piv_peak_locking(rf, bins=20)
    pl_truth = pivops.piv_peak_locking(pivops.piv_sample_at_windows(rtruth, rinfo), bins=20)
    print(f"  {'推定法':<12} {'c0':>8}   (一様なら 1 前後。真値を格子に落とすと {pl_truth['c0']:.2f} —— "
          "格子が離散なので真値も一様ではない)")
    for mode, pl in c0s.items():
        assert pl["hist"].shape == (2, 20)
        print(f"  {mode:<12} {pl['c0']:>8.2f}   小数部の平均 {pl['frac_mean']:.3f}")
    print("  → centroid は整数へ引き寄せるので小数部の分布が偏り、c0 が 2 桁跳ね上がる。")
    out["peak_locking"] = {m: pl["c0"] for m, pl in c0s.items()}
    out["peak_locking"]["truth"] = pl_truth["c0"]

    # ------------------------------------------------------------------ 9
    print("\n=== 9. 可視化 —— 4 方向の色と、LIC の縞の向き ===")
    dirs = {"右(+x)": (0.0, 2.0), "上(-y)": (-2.0, 0.0), "左(-x)": (0.0, -2.0), "下(+y)": (2.0, 0.0)}
    want_rgb = {"右(+x)": (1.0, 0.0, 0.0), "上(-y)": (0.5, 1.0, 0.0),
                "左(-x)": (0.0, 1.0, 1.0), "下(+y)": (0.5, 0.0, 1.0)}
    rgb_err = 0.0
    for name, (dy, dx) in dirs.items():
        fl = np.zeros((2, 6, 6))
        fl[0], fl[1] = dy, dx
        rgb = pivops.piv_flow_to_rgbimage(fl, scale=2.0)         # 明度 1 = 2 px(図ごとに固定)
        got = tuple(float(v) for v in np.round(rgb[3, 3], 3))
        rgb_err = max(rgb_err, float(np.max(np.abs(rgb[3, 3] - want_rgb[name]))))
        print(f"  {name:<8} → RGB {got}   期待 {want_rgb[name]}")
    # 明度 = 速さ / scale(向きは問わない)
    rgb_v = pivops.piv_flow_to_rgbimage(dflow, scale=4.0)
    bright_err = float(np.max(np.abs(rgb_v.max(axis=-1)
                                     - np.clip(pivops.piv_flow_magnitude(dflow) / 4.0, 0, 1))))
    print(f"  明度 = |v| / scale の最大誤差 {bright_err:.1e}(scale=4 px)")
    flat = np.zeros((16, 16))
    lic_h = pivops.piv_line_integral_convolution(np.stack([flat, flat + 1.0]), length=12, upsample=4, seed=1)
    lic_v = pivops.piv_line_integral_convolution(np.stack([flat + 1.0, flat]), length=12, upsample=4, seed=1)
    an = {(k, lag): _anisotropy(im, lag) for k, im in (("h", lic_h), ("v", lic_v)) for lag in (1, 2)}
    print(f"  LIC 形状 {lic_h.shape}(16x16 を 4 倍)/ 値域 [{lic_h.min():.2f}, {lic_h.max():.2f}]")
    print(f"  横流れ: 横方向の変化 / 縦方向の変化 = {an['h', 1]:.3f}(隣接)/ {an['h', 2]:.3f}(2 画素おき)")
    print(f"  縦流れ: 同じ比                     = {an['v', 1]:.3f}(隣接)/ {an['v', 2]:.3f}(2 画素おき)")
    print("  → 縞は流れの向きに伸びる。隣接画素で比が鈍いのは、積分の歩幅が格子の半分"
          "(= upsample/2 出力画素)で、upsample=4 では隣り合う画素が雑音を共有しないため。")
    out["visual"] = {"rgb_max_err": rgb_err, "brightness_max_err": bright_err,
                     "lic_aniso_h_lag2": an["h", 2], "lic_aniso_v_lag2": an["v", 2]}

    elapsed = time.perf_counter() - t0
    out["elapsed_s"] = elapsed
    print(f"\n所要 {elapsed:.2f} 秒")

    # ---- 自己検査(速さではなく正しさだけを assert する)---------------------
    p = out["particles"]
    assert p["n"] == p["n_want"], p
    assert abs(p["sum_rel_err"]) < 0.02, p
    assert p["n_isolated"] >= 10 and p["centroid_rms_px"] < 0.05, p
    assert abs(p["blob_rel_err"]) < 0.05, p
    assert field_err < 1e-9, field_err                     # 線形場は差分が厳密
    assert mag_err < 1e-12, mag_err
    assert abs(div_exp - 2 * s) < 1e-12
    assert ds["rms"] < ms["rms"] < 0.15, out["deform"]     # 窓変形は多段より良い
    assert ds2["rms"] < ds["rms"], out["deform"]
    assert abs(q_meas[ci] - q_true[ci]) < 0.2 * OMEGA ** 2, out["q_core"]
    assert 0.6 * OMEGA ** 2 < q_meas[ci] < 1.2 * OMEGA ** 2, out["q_core"]
    assert areas[0.0][0] > 2 * areas[0.5][0], areas         # 閾値で面積が変わる
    z = out["zncc"]
    assert z["measured"] > 0.99 and z["truth"] > 0.99, z
    assert z["broken"] < 0.5 < 0.99 < z["healthy"], z
    assert z["gain_invariance"] < 1e-9, z
    en = out["ensemble"]
    assert en["ensemble_median"] < 0.2 and en["ensemble_median"] < en["pair_mean_median"] / 3, en
    assert en["ensemble_outlier"] < en["pair_mean_outlier"] / 3, en
    assert ts["n_pairs"] == len(tframes) - 1
    assert out["time_stats"]["mean_gap"] < 0.02 and out["time_stats"]["rms_gap"] < 0.03, out["time_stats"]
    assert abs(got_rms.mean() - jit) < 0.5 * jit, got_rms   # 標本 11 個なので緩い
    assert c0s["gauss3"]["c0"] < 3.0 and c0s["centroid"]["c0"] > 10.0 * c0s["gauss3"]["c0"], out["peak_locking"]
    assert rgb_err < 1e-9 and bright_err < 1e-9, (rgb_err, bright_err)
    assert lic_h.shape == (64, 64) and 0.0 <= lic_h.min() and lic_h.max() <= 1.0
    assert an["h", 2] < 0.3 and an["v", 2] > 3.0, an
    print("PASS")
    return out


if __name__ == "__main__":
    result = run()
    for k, v in result.items():
        print(f"{k}: {v}")
