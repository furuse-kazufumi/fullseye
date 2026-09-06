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
   決まり、画像の総輝度はガウス輝点の積分 ``a·2πσ²`` の和に一致する。
   ``speckle_quality`` の斑点径推定は FWHM(``1.1774 × diameter_px``)に 5 % 以内で乗る。
2. **場の量は閉形式で検算できる**(``piv_velocity_gradient`` /
   ``piv_q_criterion`` / ``piv_swirling_strength`` / ``piv_strain_rate`` /
   ``piv_flow_magnitude``)—— 剛体回転 ω・一様膨張 s・単純せん断 g は線形場なので
   差分が厳密に当たり、Q = ω² / -s² / 0、λ_ci = ω / 0 / 0、ひずみ = 0 / 2s / g。
3. **窓変形**(``piv_deform_pass``)—— 窓の中で変位が変わる渦で、整数ずらしの
   多段より誤差が下がるか(下がらなければ隠さず印字)。
4. **Q 基準は閾値の産物になりうる** —— 渦の面積を閾値で振って併記する。
5. **既にある場の採点**(``correlation_quality``)—— 正しい場は ZNCC ≈ 1、
   一部を壊すとそこだけ落ちる。ゲインとオフセットに不変。
6. **アンサンブル相関**(``piv_ensemble_correlate``)—— 粒子が少なく雑音が多い
   定常流で、1 対ずつの平均より真値に近づく。
7. **時間統計**(``piv_time_statistics``)—— 場全体を揺らした列(``piv_synth_sequence``)
   で、時間 RMS が「各対の場の中央値の RMS」と一致する。
8. **ピークロッキング**(``piv_peak_locking``)—— 同じ場で centroid の c0 が gauss3 を上回る。
9. **可視化**(``piv_flow_to_rgbimage`` / ``piv_line_integral_convolution``)——
   右・上・左・下の 4 方向が決まった色に写り、LIC の縞は流れの向きに伸びる。

読み方: 各節の「真値」「測定」「差」を並べて印字し、末尾の assert が閾値。速さは
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


def rankine_like_vortex(rows, cols, gamma=700.0, core=28.0):
    """芯は剛体回転(角速度 ω = γ / 2π core²)、外は 1/r の渦。非圧縮(発散 0)。"""
    dy_c, dx_c = rows - CY, cols - CX
    r = np.hypot(dy_c, dx_c)
    r_safe = np.maximum(r, 1e-9)
    v_t = np.where(r < core, gamma * r / (2.0 * np.pi * core ** 2),
                   gamma / (2.0 * np.pi * r_safe))
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


def run() -> dict:
    t0 = time.perf_counter()
    out = {}

    # ------------------------------------------------------------------ 1
    print("=== 1. 粒子像の合成と、斑点の品質 ===")
    density, diam = 0.02, 2.5
    img, pos = pivops.piv_synth_particles((H, W), density=density, diameter_px=diam,
                                          seed=3, intensity=(0.6, 1.0))
    n_want = int(round(density * H * W))
    # 真値: 粒子は画像の外側 3σ まで撒かれる。画像内に落ちる期待個数 × 平均輝度 ×
    # ガウス輝点の積分 2πσ² が総輝度になる(縁で切れる分は 3σ の外だけなので無視できる)
    sigma = diam / 2.0
    pad = 3.0 * sigma
    inside = (H * W) / ((H + 2 * pad) * (W + 2 * pad))
    sum_want = n_want * inside * 0.8 * 2.0 * np.pi * sigma ** 2
    sum_got = float(img.sum())
    print(f"  粒子数 {len(pos)}(真値 {n_want})/ 総輝度 {sum_got:.1f}"
          f"(期待 {sum_want:.1f}、差 {100 * (sum_got / sum_want - 1):+.2f} %)")
    sq = dic.speckle_quality(img)
    fwhm = 2.0 * np.sqrt(2.0 * np.log(2.0)) * sigma       # = 1.1774 × diameter_px
    print(f"  speckle_quality: 斑点径 {sq['mean_blob_diameter_px']:.3f} px"
          f"(FWHM の真値 {fwhm:.3f})/ MIG {sq['mig']:.4f} / 被覆 {sq['coverage']:.3f}")
    out["particles"] = {"n": len(pos), "n_want": n_want,
                        "sum_rel_err": sum_got / sum_want - 1.0,
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
    print(f"  |v| = ω r の最大誤差 {mag_err:.1e} / 発散(膨張)= {2 * s:.3f} → "
          f"{pivops.piv_velocity_gradient(linear_field('expansion', s))['divergence'].mean():.4f}")
    out["field_closed_form_max_err"] = field_err
    out["magnitude_max_err"] = mag_err

    # ------------------------------------------------------------------ 3
    print("\n=== 3. 窓変形 —— 窓の中で変位が変わる渦で、多段(整数ずらし)と比べる ===")
    a, b, truth = pivops.piv_synth_pair((H, W), rankine_like_vortex,
                                        density=0.02, diameter_px=2.5, seed=7)
    mflow, minfo = pivops.piv_multipass(a, b, windows=(64, 32), overlap=0.5)
    mt = pivops.piv_sample_at_windows(truth, minfo)
    ms = pivops.piv_error_stats(mflow, mt)
    dflow, dinfo = pivops.piv_deform_pass(a, b, mflow, minfo, window=32, overlap=0.5)
    dt = pivops.piv_sample_at_windows(truth, dinfo)
    ds = pivops.piv_error_stats(dflow, dt)
    print(f"  多段 64→32      RMS {ms['rms']:.4f} px  偏り ({ms['bias_dy']:+.4f}, {ms['bias_dx']:+.4f})")
    print(f"  + 窓変形 32     RMS {ds['rms']:.4f} px  偏り ({ds['bias_dy']:+.4f}, {ds['bias_dx']:+.4f})"
          f"  (deformed={dinfo['deformed']})")
    # 芯の縁(勾配が折れる r ≈ 28 px)に誤差が集中する。そこでの改善を別に出す
    rr = np.hypot(dinfo["rows"][:, None] - CY, dinfo["cols"][None, :] - CX)
    band = (rr > 16) & (rr < 44)
    e_m = np.hypot(*(mflow - mt))[band]
    e_d = np.hypot(*(dflow - dt))[band]
    print(f"  芯の縁(16<r<44 px)の誤差 RMS  多段 {np.sqrt(np.mean(e_m ** 2)):.4f}"
          f" → 窓変形 {np.sqrt(np.mean(e_d ** 2)):.4f} px")
    out["deform"] = {"multipass_rms": ms["rms"], "deform_rms": ds["rms"],
                     "band_rms_multipass": float(np.sqrt(np.mean(e_m ** 2))),
                     "band_rms_deform": float(np.sqrt(np.mean(e_d ** 2)))}

    # ------------------------------------------------------------------ 4
    print("\n=== 4. 測った場の Q 基準 —— 芯は ω² に近づき、面積は閾値で変わる ===")
    omega = 700.0 / (2.0 * np.pi * 28.0 ** 2)          # 芯の角速度 [rad/frame]
    step = dinfo["step"]
    q_meas = pivops.piv_q_criterion(dflow, spacing=step)
    q_true = pivops.piv_q_criterion(dt, spacing=step)
    ci = np.unravel_index(int(np.argmin(rr)), rr.shape)
    print(f"  芯の Q: 測定 {q_meas[ci]:+.2e} / 真値格子 {q_true[ci]:+.2e} / 閉形式 ω² {omega ** 2:+.2e}")
    print(f"  {'閾値 Q >':>10} {'面積(格子数)':>14}")
    areas = {}
    for frac in (0.0, 0.1, 0.3, 0.5):
        thr = frac * omega ** 2
        areas[frac] = int(np.sum(q_meas > thr))
        print(f"  {thr:>10.1e} {areas[frac]:>14d}")
    print("  → 「Q > 0」の面積と「Q > 0.5 ω²」の面積は別物。閾値を書かない渦図は読めない。")
    out["q_core"] = {"measured": float(q_meas[ci]), "closed_form": omega ** 2,
                     "area_by_threshold": areas}

    # ------------------------------------------------------------------ 5
    print("\n=== 5. 既にある変位場の採点(ZNCC)—— 正しい場は 1、壊した所だけ落ちる ===")
    ua, ub, utruth = pivops.piv_synth_pair((H, W), (1.3, -2.6), density=0.02, seed=11)
    uflow, uinfo = pivops.piv_cross_correlate(ua, ub, window=32, overlap=0.5)
    z_ok = dic.correlation_quality(ua, ub, uflow, uinfo, subset=31)
    z_dense = dic.correlation_quality(ua, ub, utruth, subset=31)      # 画素ごとの真値場
    bad = uflow.copy()
    bad[:, 5:9, 5:9] += 3.0                                           # 4x4 窓だけ 3 px ずらす
    z_bad = dic.correlation_quality(ua, ub, bad, uinfo, subset=31)
    # 壊した窓の中心の画素と、健全な領域
    r0, r1 = int(uinfo["rows"][5]), int(uinfo["rows"][8])
    c0, c1 = int(uinfo["cols"][5]), int(uinfo["cols"][8])
    broken = np.nanmedian(z_bad[r0:r1, c0:c1])
    healthy = np.nanmedian(z_bad[150:220, 150:220])
    # ゲイン・オフセット不変: cur を 1.7 倍 + 0.2 しても同じ採点
    z_gain = dic.correlation_quality(ua, ub * 1.7 + 0.2, uflow, uinfo, subset=31)
    print(f"  相関で測った場   ZNCC 中央値 {np.nanmedian(z_ok):.5f}")
    print(f"  画素ごとの真値場 ZNCC 中央値 {np.nanmedian(z_dense):.5f}")
    print(f"  4x4 窓を 3 px 壊す → 壊した領域 {broken:.4f} / 健全領域 {healthy:.4f}")
    print(f"  ゲイン 1.7 + オフセット 0.2 → 差の最大 {np.nanmax(np.abs(z_gain - z_ok)):.1e}")
    out["zncc"] = {"measured": float(np.nanmedian(z_ok)), "truth": float(np.nanmedian(z_dense)),
                   "broken": float(broken), "healthy": float(healthy),
                   "gain_invariance": float(np.nanmax(np.abs(z_gain - z_ok)))}

    # ------------------------------------------------------------------ 6
    print("\n=== 6. アンサンブル相関 —— 粒子が少なく雑音の多い定常流 ===")
    disp = (2.3, -1.7)
    frames, seq_truth = pivops.piv_synth_sequence((H, W), disp, n_frames=8, density=0.004,
                                                  diameter_px=2.5, seed=5, noise_sigma=0.15)
    assert len(frames) == 8 and np.allclose(seq_truth[0], disp[0]) and np.allclose(seq_truth[1], disp[1])
    eflow, einfo = pivops.piv_ensemble_correlate(frames, window=32, overlap=0.5)
    et = pivops.piv_sample_at_windows(seq_truth, einfo)
    es = pivops.piv_error_stats(eflow, et)
    pair_flows = [pivops.piv_cross_correlate(frames[k], frames[k + 1], 32, 0.5)[0]
                  for k in range(len(frames) - 1)]
    avg = np.nanmean(np.stack(pair_flows), axis=0)
    ps = pivops.piv_error_stats(np.nan_to_num(avg, nan=0.0), et)
    print(f"  1 対ずつ測って平均({einfo['pairs']} 対) RMS {ps['rms']:.4f} px"
          f"  偏り ({ps['bias_dy']:+.4f}, {ps['bias_dx']:+.4f})")
    print(f"  相関を足してから探す           RMS {es['rms']:.4f} px"
          f"  偏り ({es['bias_dy']:+.4f}, {es['bias_dx']:+.4f})")
    out["ensemble"] = {"pair_mean_rms": ps["rms"], "ensemble_rms": es["rms"]}

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
          f" / 仕込み (1.5, 2.0)")
    print(f"  時間 RMS  窓の中央値 ({got_rms[0]:.4f}, {got_rms[1]:.4f})"
          f" / 対ごとの中央値の RMS ({ref_rms[0]:.4f}, {ref_rms[1]:.4f})"
          f" / 仕込み σ={jit}(標本 {ts['n_pairs']} 個なので ±25 % は揺れる)")
    print(f"  レイノルズ応力 <u'v'> 中央値 {np.nanmedian(ts['reynolds']):+.4f}"
          f"(独立な揺れなので 0 前後)/ 乱れ強さ {np.nanmedian(ts['turbulence_intensity']):.3f}")
    out["time_stats"] = {"n_pairs": ts["n_pairs"], "mean_gap": float(np.max(np.abs(got_mean - ref_mean))),
                         "rms_gap": float(np.max(np.abs(got_rms - ref_rms))), "rms_got": got_rms.tolist()}

    # ------------------------------------------------------------------ 8
    print("\n=== 8. ピークロッキング —— 同じ場で推定法だけ変える ===")
    # 小数部が一様に散る場(線形ランプ)。窓を 3/4 重ねて 29x29 = 841 本にする
    def ramp(rows, cols):
        return 0.5 + 0.017 * rows, -1.0 + 0.023 * cols
    ra, rb, rtruth = pivops.piv_synth_pair((H, W), ramp, density=0.02, seed=13)
    c0s = {}
    for mode in pivops.PEAK_MODES:
        rf, rinfo = pivops.piv_cross_correlate(ra, rb, 32, 0.75, peak=mode)
        c0s[mode] = pivops.piv_peak_locking(rf, bins=20)
    pl_truth = pivops.piv_peak_locking(pivops.piv_sample_at_windows(rtruth, rinfo), bins=20)
    print(f"  {'推定法':<12} {'c0':>8}   (一様なら 1 前後。真値格子 {pl_truth['c0']:.2f})")
    for mode, pl in c0s.items():
        assert pl["hist"].shape == (2, 20)
        print(f"  {mode:<12} {pl['c0']:>8.2f}   小数部の平均 {pl['frac_mean']:.3f}")
    print("  → centroid は整数へ引き寄せるので小数部の分布が偏り、c0 が跳ね上がる。")
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
        rgb = pivops.piv_flow_to_rgbimage(fl, scale=2.0)         # 明度 1 = 2 px
        got = tuple(np.round(rgb[3, 3], 3))
        rgb_err = max(rgb_err, float(np.max(np.abs(rgb[3, 3] - want_rgb[name]))))
        print(f"  {name:<8} → RGB {got}   期待 {want_rgb[name]}")
    # 明度 = 速さ / scale(向きは問わない)
    rgb_v = pivops.piv_flow_to_rgbimage(dflow, scale=4.0)
    bright_err = float(np.max(np.abs(rgb_v.max(axis=-1) - np.clip(pivops.piv_flow_magnitude(dflow) / 4.0, 0, 1))))
    print(f"  明度 = |v| / scale の最大誤差 {bright_err:.1e}(scale=4 px)")
    lic_h = pivops.piv_line_integral_convolution(np.stack([np.zeros((16, 16)), np.ones((16, 16))]),
                                                 length=12, upsample=4, seed=1)
    lic_v = pivops.piv_line_integral_convolution(np.stack([np.ones((16, 16)), np.zeros((16, 16))]),
                                                 length=12, upsample=4, seed=1)
    def aniso(im):
        """行方向の変化 / 列方向の変化。横縞なら小さく、縦縞なら大きい。"""
        return float(np.mean(np.abs(np.diff(im, axis=1)))) / float(np.mean(np.abs(np.diff(im, axis=0))))
    an_h, an_v = aniso(lic_h), aniso(lic_v)
    print(f"  LIC 形状 {lic_h.shape}(16x16 を 4 倍)/ 値域 [{lic_h.min():.2f}, {lic_h.max():.2f}]")
    print(f"  横流れ: 横方向の変化/縦方向の変化 = {an_h:.3f}(縞が横に伸びる → 1 より小さい)")
    print(f"  縦流れ: 同じ比 = {an_v:.3f}(→ 1 より大きい)")
    out["visual"] = {"rgb_max_err": rgb_err, "brightness_max_err": bright_err,
                     "lic_aniso_horizontal": an_h, "lic_aniso_vertical": an_v}

    elapsed = time.perf_counter() - t0
    out["elapsed_s"] = elapsed
    print(f"\n所要 {elapsed:.2f} 秒")

    # ---- 自己検査(速さではなく正しさだけを assert する)---------------------
    p = out["particles"]
    assert p["n"] == p["n_want"], p
    assert abs(p["sum_rel_err"]) < 0.03, p
    assert abs(p["blob_rel_err"]) < 0.05, p
    assert field_err < 1e-9, field_err                     # 線形場は差分が厳密
    assert mag_err < 1e-12, mag_err
    assert ds["rms"] < 0.30 and ms["rms"] < 0.30, (ds, ms)
    assert out["deform"]["band_rms_deform"] < out["deform"]["band_rms_multipass"], out["deform"]
    assert 0.5 * omega ** 2 < q_meas[ci] < 1.5 * omega ** 2, (q_meas[ci], omega ** 2)
    assert areas[0.0] > areas[0.5], areas                  # 閾値で面積が変わる
    z = out["zncc"]
    assert z["measured"] > 0.99 and z["truth"] > 0.99, z
    assert z["broken"] < 0.8 < z["healthy"], z
    assert z["gain_invariance"] < 1e-9, z
    assert es["rms"] < ps["rms"] and es["rms"] < 0.1, (es["rms"], ps["rms"])
    assert ts["n_pairs"] == len(tframes) - 1
    assert out["time_stats"]["mean_gap"] < 0.02 and out["time_stats"]["rms_gap"] < 0.03, out["time_stats"]
    assert c0s["centroid"]["c0"] > 3.0 * c0s["gauss3"]["c0"], out["peak_locking"]
    assert rgb_err < 1e-9 and bright_err < 1e-9, (rgb_err, bright_err)
    assert lic_h.shape == (64, 64) and 0.0 <= lic_h.min() and lic_h.max() <= 1.0
    assert an_h < 0.5 and an_v > 2.0, (an_h, an_v)
    print("PASS")
    return out


if __name__ == "__main__":
    result = run()
    print({k: (v if not isinstance(v, dict) else {kk: (round(vv, 5) if isinstance(vv, float) else vv)
                                                  for kk, vv in v.items()})
           for k, v in result.items()})
