# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_interferometry_step — 白色干渉計(コヒーレンス走査、`interferometry` 族)で
**ナノメートルの段差をどこまで正確に測れるか**を、偏りと散らばりに分けて数字にする PoC。

    py -3.11 examples/poc_interferometry_step.py

【この PoC が答える問い】
半導体・精密加工の表面計測でいちばん素朴な問い —「50 nm の段差を、この装置で、
何 nm の確からしさで測れるのか」。カタログの「分解能 0.1 nm」ではなく、
**既知の段差を仕込んで測り返し、偏り(bias)と散らばり(std)を別々に出す**。

`examples/coherence_scanning.py` が「9 op が閉形式の真値と一致すること」を見るのに対し、
こちらは **1 つの測定量(段差)に絞って不確かさを積み上げる**。重ならないように、
雑音なしの一致確認は最小限にとどめてある。

(1) 設計: `csi_design` で走査ステップ上限・包絡線幅・捕捉範囲を先に決める。
(2) 系統誤差ゼロの確認: 雑音なしで 4 種類の段差を測り、モデル誤差の床を見る。
(3) ★繰り返し測定: 雑音の種を変えて 40 回測り、**偏りと散らばりを分ける**。
(4) ★ゼロ点との比較: 素朴な「包絡線の最大サンプル」(`peak`)に対して
    サブサンプル推定(`gaussian` / `centroid`)がどれだけ上回るか。
(5) 走査ステップ掃引: 細かくすれば良くなるのか。Nyquist ぎりぎりは安全か。
(6) 雑音掃引: 精度がどう崩れ、**どこで測れなくなるか**。
(7) 系統誤差探し: 段差が λ/2 の整数倍に近いと位相が巻き戻る、はず — を確かめる。

【グラウンドトゥルース(自分で仕込んだ真値)】
段差は `csi_stack_simulate` に渡す高さマップの左右差そのもの。測定値は
`csi_height_map` の左右平均差。真値は 0.050 / 0.100 / 0.200 / 0.500 µm。

【結果の要点(本文の print が正、以下は道しるべ)】
- 雑音なしの床は 1e-4 nm 未満。段差 500 nm でも桁が変わらない。
- 雑音 1%(振幅比)で、段差によらず偏り数 nm・散らばり ~10 nm。
  **不確かさは段差の大きさにほぼ依存しない**(相対誤差ではなく絶対誤差の世界)。
- ゼロ点 `peak` の誤差は走査格子への丸め残差 dz·round(段差/dz) − 段差 に厳密一致
  する(最悪 ±走査ステップ/2)。雑音を減らしても消えない **構造を持った嘘**。
- 走査ステップは細かくしても良くならない。Nyquist 上限 λ/4 = 0.15 µm の手前
  0.14 µm で既に雑音なし誤差 +14 nm。**上限は安全な動作点ではない**。
- `centroid` は散らばりが `gaussian` の 1/3〜1/5 なのに、雑音とともに **段差を
  縮めるゲイン誤差**を持つ(雑音 3% で 0.55、10% で 0.20)。繰り返し測定だけでは
  捕まらない。
- **λ/2 の巻き戻りは出ない。** 予想が外れた側が、この族を足した理由そのもの。

【この PoC で分かった fullseye 側の穴 → 末尾の「所見」節】
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fringe                                                    # noqa: E402
import interferometry as I                                       # noqa: E402

LAM = 0.60          # µm  光源中心波長
DLAM = 0.10         # µm  スペクトル幅
Z_RANGE = 12.0      # µm  走査全長
DZ = 0.05           # µm  既定の走査ステップ
NP = 241            # 面数(0.05 × 240 = 12.0 µm)
BASE = 6.0          # µm  低い側の高さ = 走査の中央(端の切断を避ける)
PH, PW = 12, 12     # 段差の左右パッチ(12×12 画素ずつ、合計 12×24)
STEPS = (0.050, 0.100, 0.200, 0.500)     # µm  仕込む段差
N_TRIAL = 40        # 繰り返し測定の回数(seed を変える)

# 包絡線幅は設計から取る(設計値と前方モデルを一致させておく。
# ここを手打ちの定数にすると「設計を無視した数字」になってしまう)
DESIGN = I.csi_design(wavelength_um=LAM, bandwidth_um=DLAM, z_range_um=Z_RANGE,
                      width_px=2 * PW, height_px=PH)
FWHM = DESIGN["envelope_fwhm_um"]


def make_stack(step_um, noise, seed, dz=DZ, n_planes=NP):
    """左半分 BASE、右半分 BASE+step の段差表面から走査スタックを合成する。

    戻り値は (真の高さマップ, zscan スタック)。真値は自分で作った配列そのもので、
    op から貰った数ではない。
    """
    truth = np.full((PH, 2 * PW), BASE)
    truth[:, PW:] += step_um
    stack = I.csi_stack_simulate(truth, 0.0, dz, n_planes, LAM,
                                 envelope_fwhm_um=FWHM, noise=noise, seed=seed)
    return truth, stack


def measure_step(step_um, noise, seed, mode="gaussian", dz=DZ, n_planes=NP):
    """段差を 1 回測る。戻り値は (測定した段差 [µm], 拒否された画素の割合)。

    画素単位の拒否(変調度不足など)は `on_invalid="fill"` で NaN にし、
    **何割が拒否されたかを数える**。ここを raise のままにすると雑音掃引の
    後半が例外で落ちて「測れない領域」の形が見えなくなる。
    """
    _, stack = make_stack(step_um, noise, seed, dz, n_planes)
    hmap = I.csi_height_map(stack, dz, 0.0, LAM, mode=mode, on_invalid="fill")
    rejected = float(np.isnan(hmap).mean())
    if rejected == 1.0:
        return float("nan"), rejected
    lo = np.nanmean(hmap[:, :PW])
    hi = np.nanmean(hmap[:, PW:])
    return float(hi - lo), rejected


def repeat(step_um, noise, mode="gaussian", dz=DZ, n_planes=NP, n=N_TRIAL):
    """seed を変えて n 回測り、偏り・散らばり・拒否率を返す(単位 nm)。

    「誤差 2 nm」ではなく「偏り +0.3 nm、標準偏差 1.8 nm」を出すための関数。
    偏りは系統誤差(何度測っても消えない)、散らばりは統計誤差(平均すれば減る)。
    """
    vals, rej = [], []
    for seed in range(1, n + 1):
        v, r = measure_step(step_um, noise, seed, mode, dz, n_planes)
        vals.append(v)
        rej.append(r)
    v = np.asarray(vals, dtype=np.float64)
    ok = ~np.isnan(v)
    if ok.sum() < 2:
        return float("nan"), float("nan"), float(np.mean(rej)), int(ok.sum())
    bias_nm = (float(np.mean(v[ok])) - step_um) * 1000.0
    std_nm = float(np.std(v[ok], ddof=1)) * 1000.0
    return bias_nm, std_nm, float(np.mean(rej)), int(ok.sum())


def main():
    t_all = time.perf_counter()

    # ------------------------------------------------------------------ #
    # 1) 設計 — 測る前に決まってしまう限界                                  #
    # ------------------------------------------------------------------ #
    print("1) 設計(λ=%.2f µm, Δλ=%.2f µm, 走査 %.1f µm, %d×%d 画素):"
          % (LAM, DLAM, Z_RANGE, PH, 2 * PW))
    print("   包絡線 FWHM(走査軸)      = %.4f µm" % FWHM)
    print("   縞周期 λ/2                 = %.4f µm" % DESIGN["fringe_period_um"])
    print("   走査ステップ上限(Nyquist) = %.4f µm  推奨 %.4f µm"
          % (DESIGN["max_z_step_um"], DESIGN["recommended_z_step_um"]))
    print("   捕捉範囲(可視度 30%%)     = %.4f µm" % DESIGN["capture_range_um"])
    print("   位相シフト法の一意段差      = %.4f µm  ← 本 PoC の段差 0.500 µm は"
          " この 3.3 倍" % DESIGN["phase_unambiguous_step_um"])
    # 走査の中央に置いた表面が捕捉範囲の内側にあること(端の切断は別の失敗モード)
    assert BASE - DESIGN["capture_range_um"] > 0.0
    assert BASE + max(STEPS) + DESIGN["capture_range_um"] < Z_RANGE

    # ------------------------------------------------------------------ #
    # 2) 雑音なし — モデル誤差の床(ここが 0 でなければ以降は全部無意味)     #
    # ------------------------------------------------------------------ #
    print("\n2) 雑音なしで測った段差(系統誤差の床):")
    print("   仕込んだ段差 |        測定値 |        誤差")
    floor_nm = 0.0
    for step in STEPS:
        got, _ = measure_step(step, 0.0, 0)
        err_nm = (got - step) * 1000.0
        floor_nm = max(floor_nm, abs(err_nm))
        print("   %8.1f nm | %12.6f µm | %+12.3e nm" % (step * 1000, got, err_nm))
    print("   床 = %.3e nm。段差 500 nm でも桁が変わらない = 誤差は段差に比例しない"
          % floor_nm)
    assert floor_nm < 0.05          # 雑音が無ければ 0.05 nm 以内

    # ------------------------------------------------------------------ #
    # 3) ★繰り返し測定 — 偏りと散らばりを分ける                            #
    # ------------------------------------------------------------------ #
    print("\n3) 雑音 1%%(振幅比)で %d 回測り直した結果 [nm]:" % N_TRIAL)
    print("   仕込んだ段差 |     偏り |  標準偏差 | 平均の標準誤差 | 偏りは有意か")
    rep = {}
    for step in STEPS:
        bias, std, _, n_ok = repeat(step, 0.01)
        rep[step] = (bias, std)
        sem = std / np.sqrt(n_ok)
        sig = "有意" if abs(bias) > 2 * sem else "雑音と区別できない"
        print("   %8.1f nm | %+8.2f | %9.2f | %14.2f | %s"
              % (step * 1000, bias, std, sem, sig))
    stds = [rep[s][1] for s in STEPS]
    print("   標準偏差は段差 50 nm と 500 nm で %.2f 倍しか変わらない"
          " = **不確かさは段差の大きさでなく光と画素数で決まる**"
          % (max(stds) / min(stds)))
    assert max(stds) / min(stds) < 2.0
    # 偏りは散らばりよりずっと小さい = この推定量は「ずれている」のではなく「ばらつく」
    assert all(abs(rep[s][0]) < rep[s][1] for s in STEPS)

    # 画素数を増やせば散らばりだけが減る(偏りは減らない)ことの確認
    single = np.array([measure_step(0.100, 0.01, s)[0] for s in range(1, 21)])
    _, stack = make_stack(0.100, 0.01, 1)
    hmap = I.csi_height_map(stack, DZ, 0.0, LAM, on_invalid="fill")
    px_std_nm = float(np.nanstd(hmap - make_stack(0.100, 0.0, 0)[0])) * 1000.0
    pred_nm = px_std_nm * np.sqrt(2.0 / (PH * PW))
    print("   1 画素あたりの散らばり %.1f nm → %d 画素の左右平均差の予測 %.1f nm、"
          "実測 %.1f nm(√N 則どおり)"
          % (px_std_nm, PH * PW, pred_nm, float(np.std(single, ddof=1)) * 1000))
    assert 0.5 < pred_nm / (float(np.std(single, ddof=1)) * 1000) < 2.0

    # ------------------------------------------------------------------ #
    # 4) ★ゼロ点(包絡線の最大サンプル)との比較                            #
    # ------------------------------------------------------------------ #
    print("\n4) ゼロ点 = 素朴な最大サンプル(`peak`)vs サブサンプル推定:")
    print("   走査ステップ 0.04 µm(段差 100 nm は 2.5 ステップ = 格子に載らない):")
    for mode in ("peak", "parabolic", "gaussian", "centroid"):
        got, _ = measure_step(0.100, 0.0, 0, mode=mode, dz=0.04, n_planes=301)
        print("      %-10s 雑音なし誤差 %+11.3e nm" % (mode, (got - 0.100) * 1000))
    peak_err = (measure_step(0.100, 0.0, 0, "peak", dz=0.04, n_planes=301)[0]
                - 0.100) * 1000
    gauss_err = (measure_step(0.100, 0.0, 0, "gaussian", dz=0.04, n_planes=301)[0]
                 - 0.100) * 1000
    print("   `peak` の誤差 %+.1f nm はちょうど走査ステップの半分(%.1f nm)。"
          % (peak_err, 0.04 * 1000 / 2))
    print("   サブサンプル推定は同じ走査データから %+.3e nm を返す = "
          "ゼロ点に対して %.0f 桁の改善。"
          % (gauss_err, np.log10(abs(peak_err) / max(abs(gauss_err), 1e-12))))
    assert abs(abs(peak_err) - 20.0) < 1e-6      # = dz/2 ちょうど
    assert abs(gauss_err) < 0.05

    # ゼロ点の誤差は雑音でも「小さな揺らぎ」でもなく、走査格子への丸め残差そのもの
    print("   ★`peak` の誤差は雑音由来ではない。走査格子への丸め残差"
          " dz·round(段差/dz) − 段差 に厳密一致する:")
    for dz, npl in ((0.02, 601), (0.04, 301), (0.05, 241), (0.08, 151),
                    (0.10, 121), (0.12, 101)):
        got, _ = measure_step(0.100, 0.0, 0, "peak", dz=dz, n_planes=npl)
        # numpy の round は偶数丸め。2.5 → 2 になるので予測もそれに合わせる
        pred = (dz * float(np.round(0.100 / dz)) - 0.100) * 1000
        print("      走査ステップ %.2f µm(段差 = %5.2f ステップ)→ 誤差 %+6.1f nm"
              "  予測 %+6.1f nm" % (dz, 0.100 / dz, (got - 0.100) * 1000, pred))
        assert abs((got - 0.100) * 1000 - pred) < 1e-6
    print("      → 最悪でステップの半分(%.1f nm @ 0.04 µm)。雑音を 0 にしても"
          "消えず、走査を細かくしないと減らない = **系統誤差**。" % (0.04 * 1000 / 2))

    # ------------------------------------------------------------------ #
    # 5) 走査ステップ掃引 — 細かくすれば良くなるのか                        #
    # ------------------------------------------------------------------ #
    print("\n5) 走査ステップを振る(走査全長 12 µm 固定、段差 100 nm、雑音 1%):")
    print("   z step | 面数 | 雑音なし誤差 |     偏り |  標準偏差 | 1 回の所要")
    sweep = {}
    for dz, npl in ((0.02, 601), (0.04, 301), (0.05, 241), (0.08, 151),
                    (0.10, 121), (0.12, 101), (0.14, 86)):
        clean, _ = measure_step(0.100, 0.0, 0, dz=dz, n_planes=npl)
        t0 = time.perf_counter()
        bias, std, _, _ = repeat(0.100, 0.01, dz=dz, n_planes=npl, n=16)
        dt = (time.perf_counter() - t0) / 16
        sweep[dz] = (clean - 0.100) * 1000
        print("   %6.2f | %4d | %+12.3f nm | %+8.2f | %9.2f | %7.1f ms"
              % (dz, npl, sweep[dz], bias, std, dt * 1000))
    print("   ★細かくしても良くならない。0.02 µm(601 面)は 0.10 µm(121 面)と同等で、"
          "計算量だけ 5 倍。局所当てはめは argmax 近傍 3 点しか見ないため。")
    print("   ★Nyquist 上限 λ/4 = %.2f µm の手前 0.14 µm で、雑音が無いのに誤差 %+.1f nm。"
          "**上限は安全な動作点ではない**(推奨 %.3f µm = λ/8 に余裕がある理由)。"
          % (DESIGN["max_z_step_um"], sweep[0.14], DESIGN["recommended_z_step_um"]))
    assert abs(sweep[0.14]) > 5.0          # Nyquist 手前で既に nm オーダーを外す
    assert max(abs(sweep[d]) for d in (0.02, 0.04, 0.05, 0.08, 0.10)) < 0.05
    # Nyquist を割ると拒否される(黙って間欠的に間違うより拒否を選んでいる)
    try:
        measure_step(0.100, 0.0, 0, dz=0.16, n_planes=76)
        print("   [FAIL] Nyquist 割れが拒否されなかった")
        return False
    except ValueError as exc:
        print("   走査ステップ 0.16 µm(> λ/4)は拒否: %s"
              % str(exc).split(" — ")[0][:72])

    # ------------------------------------------------------------------ #
    # 6) ★雑音掃引 — どこで測れなくなるか                                  #
    # ------------------------------------------------------------------ #
    print("\n6) 雑音を振る(段差 100 nm、%d 回)。"
          "総合誤差 = √(偏り² + 標準偏差²):" % N_TRIAL)
    print("   雑音 |            gaussian             |           centroid"
          "             | 画素拒否")
    print("        |    偏り  標準偏差    総合        |    偏り  標準偏差    総合")
    limit_nm = 0.100 * 1000 * 0.10          # 段差の 10% を「測れた」の線とする
    boundary = {}
    for noise in (0.002, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.50):
        row = {}
        rej = 0.0
        for mode in ("gaussian", "centroid"):
            b, s, r, _ = repeat(0.100, noise, mode=mode)
            row[mode] = (b, s, float(np.hypot(b, s)))
            rej = r
        for mode in ("gaussian", "centroid"):
            if row[mode][2] <= limit_nm:
                boundary[mode] = noise
        print("   %5.3f | %+7.2f %8.2f %8.2f nm | %+7.2f %8.2f %8.2f nm | %5.1f%%"
              % (noise, *row["gaussian"], *row["centroid"], 100 * rej))
    print("   測れなくなる境目(総合誤差が段差の 10%% = %.0f nm を超える点):"
          % limit_nm)
    for mode in ("gaussian", "centroid"):
        print("      %-9s 雑音 %.3f までは 10%% 以内" % (mode, boundary[mode]))
    assert boundary["gaussian"] <= 0.01 and boundary["centroid"] <= 0.01

    # ★散らばりが小さいことは正しさの証拠にならない
    print("\n   ★`centroid` は散らばりが 1 桁小さいのに、雑音とともに"
          "**段差そのものを縮める**:")
    print("   雑音 | 段差 50 nm | 100 nm | 200 nm | 500 nm |  ゲイン(測定/真値)")
    for noise in (0.0, 0.01, 0.03, 0.10):
        gains, cells = [], []
        for step in STEPS:
            b, _, _, _ = repeat(step, noise, mode="centroid", n=16)
            gains.append((step * 1000 + b) / (step * 1000))
            cells.append("%+7.1f" % b)
        print("   %4.2f | %s | %.4f ± %.4f"
              % (noise, " | ".join(cells), float(np.mean(gains)),
                 float(np.std(gains))))
    g_lo = np.mean([(s * 1000 + repeat(s, 0.0, mode="centroid", n=4)[0])
                    / (s * 1000) for s in STEPS])
    g_hi = np.mean([(s * 1000 + repeat(s, 0.10, mode="centroid", n=16)[0])
                    / (s * 1000) for s in STEPS])
    print("   ゲインが段差 4 種でほぼ揃う = これはオフセットではなく**倍率の誤差**。"
          "雑音 0 で %.3f、雑音 10%% で %.3f まで落ちる。" % (g_lo, g_hi))
    print("   繰り返し測定の再現性(std %.1f nm)だけを見ると最良の推定量に見えるので、"
          "**再現性を精度と読み替えるとここで嘘をつく**。"
          % repeat(0.100, 0.10, mode="centroid", n=16)[1])
    assert g_lo > 0.999 and g_hi < 0.9      # 雑音で倍率が落ちる

    # ------------------------------------------------------------------ #
    # 7) 系統誤差探し — λ/2 の巻き戻りは出るか                              #
    # ------------------------------------------------------------------ #
    print("\n7) 段差を λ/2 = %.2f µm の整数倍に近づける(位相の巻き戻りを探す):"
          % (LAM / 2))
    print("   段差 | 段差/(λ/2) | コヒーレンス法の誤差 | 位相シフト法の誤差")
    gain_rad = 4.0 * np.pi / LAM                       # rad/µm(往復)
    worst_csi = 0.0
    wrapped = []
    for step in (0.10, 0.149, 0.151, 0.299, 0.300, 0.301, 0.599, 0.600, 0.900):
        csi, _ = measure_step(step, 0.0, 0)
        truth = np.full((PH, 2 * PW), 0.0)
        truth[:, PW:] = step
        imgs = fringe.synthesize_fringes(truth, n_steps=4, freq=0.0,
                                         phase_gain=gain_rad, bias=0.5,
                                         amplitude=0.4)
        rec = fringe.decode_fringe(imgs, k=1.0 / gain_rad)
        psi = float(rec[:, PW:].mean() - rec[:, :PW].mean())
        worst_csi = max(worst_csi, abs(csi - step))
        note = ""
        if abs(psi - step) > 1e-6:
            orders = (psi - step) / (LAM / 2)
            note = "  = λ/2 × %+d(縞次数の飛び)" % round(orders)
            wrapped.append(step)
        print("   %.3f |   %6.3f    | %+13.3e nm | %+10.4f µm%s"
              % (step, step / (LAM / 2), (csi - step) * 1000, psi - step, note))
    print("   ★予想は外れた。**コヒーレンス法では λ/2 の巻き戻りが一度も出ない**"
          "(最悪 %.3e nm)。" % (worst_csi * 1000))
    print("   包絡線には周期が無いので巻き戻る対象が存在しない。同じ表面で位相シフト法は"
          " λ/4 = %.3f µm を超えた %d 点すべてで縞次数を飛ばしている。"
          % (LAM / 4, len(wrapped)))
    print("   「出るはずのものが出ない」ことが、この族を `fringe` の隣に置いた理由。")
    assert worst_csi * 1000 < 0.05
    assert 0.149 not in wrapped and 0.151 in wrapped   # 境界は λ/4 ちょうど

    # ------------------------------------------------------------------ #
    # 所見 — 想定と違ったこと / 途中で自分が間違えたこと                     #
    # ------------------------------------------------------------------ #
    print("\n所見(想定と違ったこと):")
    print("   (a) λ/2 の巻き戻りを探して見つからなかった。7) のとおり、これは"
          "バグではなく包絡線法の定義そのもの。予想を書いた側が間違っていた。")
    print("   (b) 最初、画素ごとの誤差を λ/2 で丸めて数えたら 0/±1 次に 3 割が"
          "落ちたので「縞次数の飛びだ」と読んだ。ヒストグラムを引いたら"
          "±λ/2 に広がった単峰で、丸めた瞬間に 3 本の柱に見えていただけだった。"
          "**量子化を主張する前に丸めていない分布を見る**。")
    print("   (c) 走査を細かくすれば精度が上がる、は成り立たない(5)。局所当てはめは"
          "3 点しか見ないので、面数を 5 倍にしても散らばりは変わらず時間だけ増える。")
    print("   (d) 再現性が最良の推定量が最良とは限らない(6)。`centroid` は std が"
          "1 桁小さいまま段差を 3 割縮める。真値を仕込まない繰り返し測定では"
          "検出できない種類の誤りで、これが「真値は自分で決める」規律の根拠。")
    print("\n所見(fullseye の穴):")
    print("   (e) `csi_design` は `max_z_step_um` = %.3f µm(λ/4)を返すが、5) の"
          "とおりその手前 0.14 µm で既に雑音なし誤差 %+.1f nm が出る"
          "(0.02〜0.12 µm はいずれも %.3f nm 以内)。`recommended_z_step_um` = %.3f µm"
          "(λ/8)を使えば実用上問題ないが、**上限と実用限界の差が返り値からは"
          "読めない**。"
          % (DESIGN["max_z_step_um"], sweep[0.14],
             max(abs(sweep[d]) for d in (0.02, 0.04, 0.05, 0.08, 0.10, 0.12)),
             DESIGN["recommended_z_step_um"]))
    print("   (f) `on_invalid=\"fill\"` の画素拒否率は返り値に出ず、NaN を自分で"
          "数えるしかない(6 の右端列)。雑音 5% で 3 割、20% で 5 割が落ちており、"
          "拒否率は測定の信頼度そのもの。拒否数を返す口があると下流で使いやすい。")

    print("\n総所要 %.1f 秒" % (time.perf_counter() - t_all))
    print("\nPASS: 既知の段差 50/100/200/500 nm に対し、雑音なしで %.3f nm 以内、"
          "雑音 1%% で偏り %.1f nm 以内・標準偏差 %.1f nm 以内で測り返した"
          % (floor_nm, max(abs(rep[s][0]) for s in STEPS),
             max(rep[s][1] for s in STEPS)))
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
