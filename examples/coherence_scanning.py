# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""coherence_scanning — コヒーレンス走査干渉(interferometry)op を「段差のある表面を
1 台の干渉顕微鏡で測る」筋で一巡し、**既存の位相シフト法が壊れる点**を同じ表面で
数値に出す。

    py -3.11 examples/coherence_scanning.py

【この例が解く問題】
微細な段差(サブミクロン)を持つ表面の高さを測る。fullseye には既に位相シフト法
(`fringe`)があり、位相から高さを出す — 精密だが**位相は 2π の周期を持つ**ので、
λ/4 を超える段差は「別のもっともらしい数」になって返る。ここでは位相ではなく
**コヒーレンス包絡線のピーク**で高さを出す経路を通し、その不定性が無いことを
同一の合成表面で確かめる。

(1) 設計: 光源のスペクトル幅からコヒーレンス長・縦分解能・走査ステップの上限
    (Nyquist)・スタックのメモリ量を先に出す。**ハードウェアを買う前の計算**。
(2) 前方モデル: 既知高さ z0 の z 走査干渉信号 a + b·V(z-z0)·cos(4π(z-z0)/λ) を
    合成する。「4π」は往復(double pass)で、1 縞 = λ/2 の高さ。
(3) 包絡線: 直流台座を抜いてから Hilbert 包絡線を取る。**抜かないと返るのは
    台座であって包絡線ではない**ことを数値で見る。
(4) 推定量 4 種: ピーク / 重心 / 放物線 / ガウス。雑音なしでの偏りと、雑音を
    入れたときの順位が**逆転する**ことを表にする。
(5) 高さマップ: (Z,H,W) 走査スタック → 高さマップ + 変調度マップ(= 反射率)。
(6) ★突き合わせ: **同じ段差**を位相シフト法(既存 fringe)とコヒーレンス法に
    かけ、λ/4 を境に位相法が λ/2 の整数倍だけ間違い、コヒーレンス法が耐える
    ことを表にする。
(7) クロマティック共焦点: 走査せずスペクトルのピーク波長 → 高さ。
(8) fail-closed: Nyquist 割れ・走査外の表面・包絡線の無い信号を拒否すること、
    そして拒否しなければ**黙って 76% 間違う**ことを実際に見せる。

【グラウンドトゥルース(数値で嘘を弾く)】
1. 包絡線ピークは z0 ちょうど。解析包絡線 + ガウス当てはめは機械精度(3e-14)。
2. 台座を抜かない包絡線の誤差 = 台座そのもの(0.5)。
3. 反射率は包絡線を定数倍するだけで、ピーク位置を動かさない。
4. 位相シフト法の誤差は λ/2 の**整数倍**(= 縞次数の飛び)。
5. コヒーレンス長 = (4 ln2/π)λ²/Δλ(OPD 基準)、走査軸ではその半分。
6. クロマティック共焦点の高さは (λ_peak - λ_ref)·分散で厳密。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dsp                                                       # noqa: E402
import fringe                                                    # noqa: E402
import interferometry as I                                       # noqa: E402

LAM = 0.60          # um
SIGMA = 1.2         # um (envelope sigma; FWHM 2.826 um)
DZ = 0.05           # um
NP = 241            # planes -> 12.0 um scan


def main():
    z = DZ * np.arange(NP)

    # ------------------------------------------------------------------ #
    # 1) 設計: 買う前に決まってしまう限界                                  #
    # ------------------------------------------------------------------ #
    d = I.csi_design(wavelength_um=LAM, bandwidth_um=0.10, z_range_um=12.0,
                     width_px=320, height_px=240)
    print("1) 設計(λ=%.2f um, Δλ=%.2f um, 320x240 画素, 12 um 走査):" %
          (LAM, 0.10))
    print(f"   コヒーレンス長(OPD 基準)  = {d['coherence_length_um']:.4f} um")
    print(f"   包絡線 FWHM(走査軸)      = {d['envelope_fwhm_um']:.4f} um"
          f"  ← 往復なので OPD の半分")
    print(f"   縞周期 λ/2                 = {d['fringe_period_um']:.4f} um")
    print(f"   走査ステップ上限(Nyquist) = {d['max_z_step_um']:.4f} um"
          f"  推奨 {d['recommended_z_step_um']:.4f} um")
    print(f"   捕捉範囲(可視度 30% 以上)= {d['capture_range_um']:.4f} um")
    print(f"   スタック {d['n_planes']} 面 = {d['stack_megabytes']:.0f} MB"
          f"  上限内={d['stack_within_cap']}")
    print(f"   位相シフト法の一意段差      = {d['phase_unambiguous_step_um']:.4f} um"
          f"  ← コヒーレンス法にはこの制限が無い")
    assert d["envelope_fwhm_um"] == d["coherence_length_um"] / 2.0
    assert d["max_z_step_um"] == LAM / 4.0

    # ------------------------------------------------------------------ #
    # 2) 前方モデル + 3) 包絡線                                            #
    # ------------------------------------------------------------------ #
    z0 = 6.025                                          # 走査面の間に置く
    sig = I.csi_signal_simulate(z0, 0.0, DZ, NP, LAM, envelope_fwhm_um=None,
                                envelope_sigma_um=SIGMA)
    truth = 0.4 * np.exp(-0.5 * ((z - z0) / SIGMA) ** 2)
    env_on = I.csi_envelope(sig, remove_bias=True)
    env_off = I.csi_envelope(sig, remove_bias=False)
    err_on = float(np.abs(env_on - truth).max())
    err_off = float(np.abs(env_off - truth).max())
    err_dsp = float(np.abs(dsp.envelope(sig) - truth).max())
    print(f"\n2-3) 走査信号(真の高さ {z0} um)と包絡線:")
    print(f"   台座を抜く    : 解析包絡線との最大誤差 {err_on:.3e}")
    print(f"   台座を抜かない: 同 {err_off:.3f}  ← 返っているのは台座そのもの")
    print(f"   dsp.envelope をそのまま掛けた場合も同じ {err_dsp:.3f}"
          f"  = csi_envelope が足しているのはこの 1 点だけ")
    assert err_on < 1e-6 and err_off > 0.4
    assert abs(err_dsp - err_off) < 1e-12

    # ------------------------------------------------------------------ #
    # 4) 推定量 4 種の偏り — 雑音で順位が逆転する                           #
    # ------------------------------------------------------------------ #
    clean, noisy = {}, {}
    for mode in I.ESTIMATORS:
        errs = [I.csi_peak_position(
            I.csi_signal_simulate(6.0 + f * DZ, 0.0, DZ, NP, LAM,
                                  envelope_fwhm_um=None, envelope_sigma_um=SIGMA),
            DZ, 0.0, LAM, mode=mode) - (6.0 + f * DZ)
            for f in (0.0, 0.25, 0.5, 0.75)]
        clean[mode] = max(abs(e) for e in errs)
        errs = [I.csi_peak_position(
            I.csi_signal_simulate(6.0 + (t % 13) * DZ / 13.0, 0.0, DZ, NP, LAM,
                                  envelope_fwhm_um=None, envelope_sigma_um=SIGMA,
                                  noise=0.01, seed=t),
            DZ, 0.0, LAM, mode=mode) - (6.0 + (t % 13) * DZ / 13.0)
            for t in range(200)]
        noisy[mode] = float(np.sqrt(np.mean(np.square(errs))))
    print("\n4) 推定量の偏り(左=雑音なし最大誤差、右=雑音 1% の RMS、200 試行):")
    for mode in I.ESTIMATORS:
        print(f"   {mode:<10s} {clean[mode]:.3e} um    {noisy[mode]:.4f} um")
    print(f"   雑音なしは gaussian が parabolic の "
          f"{clean['parabolic'] / clean['gaussian']:.0f} 倍精密、"
          f"雑音下では centroid が parabolic の "
          f"{noisy['parabolic'] / noisy['centroid']:.1f} 倍精密 = **順位が逆転する**")
    assert clean["gaussian"] < clean["parabolic"]
    assert noisy["centroid"] < noisy["parabolic"]

    # 重心法の固有の弱点: 走査窓の中でどこに表面があるかで偏る
    bias = {zz: I.csi_peak_position(
        I.csi_signal_simulate(zz, 0.0, DZ, NP, LAM, envelope_fwhm_um=None,
                              envelope_sigma_um=SIGMA),
        DZ, 0.0, LAM, mode="centroid", max_edge_envelope=1.0) - zz
        for zz in (2.0, 6.0, 10.0)}
    print("   ただし centroid は窓の中の位置で偏る: "
          + "  ".join(f"z0={k:.0f} um → {v:+.4f}" for k, v in bias.items()))
    assert bias[2.0] > 0.15 > abs(bias[6.0])

    # ------------------------------------------------------------------ #
    # 5) 高さマップと変調度マップ                                          #
    # ------------------------------------------------------------------ #
    yy, xx = np.mgrid[0:32, 0:32]
    height = 5.0 + 2.0 * xx / 31.0                        # 5.0 - 7.0 um の傾斜
    refl = 0.3 + 0.6 * yy / 31.0                          # 反射率は縦に変える
    stack = I.csi_stack_simulate(height, 0.0, DZ, NP, LAM, envelope_fwhm_um=None,
                                 envelope_sigma_um=SIGMA, reflectivity=refl)
    hmap = I.csi_height_map(stack, DZ, 0.0, LAM, mode="gaussian")
    cmap = I.csi_contrast_map(stack)
    rms = float(np.sqrt(np.mean((hmap - height) ** 2)))
    print(f"\n5) 走査スタック {stack.shape} → 高さマップ:")
    print(f"   高さ RMS 誤差 {rms:.3e} um(反射率が 0.3〜0.9 で変わっても不変)")
    print(f"   変調度マップ vs 0.4×反射率: 最大誤差 "
          f"{float(np.abs(cmap - 0.4 * refl).max()):.3e}")
    assert rms < 5e-6
    # 走査の端に寄せると同じ推定量が 3 桁悪化する = 精度は推定量でなく走査の設計
    wide = 2.0 + 8.0 * xx / 31.0
    rms_wide = float(np.sqrt(np.mean((I.csi_height_map(
        I.csi_stack_simulate(wide, 0.0, DZ, NP, LAM, envelope_fwhm_um=None,
                             envelope_sigma_um=SIGMA),
        DZ, 0.0, LAM, max_edge_envelope=1.0) - wide) ** 2)))
    print(f"   同じ表面を 2.0-10.0 um に広げると RMS {rms_wide:.3e} um "
          f"({rms_wide / rms:.0f} 倍悪化)= 端で包絡線が切れるため。"
          f"精度は推定量でなく**走査範囲の設計**で決まる")

    # ------------------------------------------------------------------ #
    # 6) ★ 位相シフト法との突き合わせ                                      #
    # ------------------------------------------------------------------ #
    gain = 4.0 * np.pi / LAM                              # rad/um(往復)
    print(f"\n6) 同じ段差を両方式で測る(λ/4={LAM / 4:.2f} um, λ/2={LAM / 2:.2f} um):")
    print("   真の段差 | 位相シフト法(既存 fringe)  | コヒーレンス法(新規)")
    broke = []
    for h in (0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 1.00):
        hh = np.zeros((16, 32))
        hh[:, 16:] = h
        imgs = fringe.synthesize_fringes(hh, n_steps=4, freq=0.0,
                                         phase_gain=gain, bias=0.5, amplitude=0.4)
        rec = fringe.decode_fringe(imgs, k=1.0 / gain)
        psi = float(rec[:, 16:].mean() - rec[:, :16].mean())

        st = I.csi_stack_simulate(hh + 5.0, 0.0, DZ, NP, LAM,
                                  envelope_fwhm_um=None, envelope_sigma_um=SIGMA)
        cm = I.csi_height_map(st, DZ, 0.0, LAM, mode="gaussian")
        csi = float(cm[:, 16:].mean() - cm[:, :16].mean())

        tag = ""
        if abs(psi - h) > 1e-6:
            orders = (psi - h) / (LAM / 2.0)
            tag = f"  ← λ/2 の {round(orders):+d} 倍だけ間違い"
            broke.append(h)
            assert abs(orders - round(orders)) < 1e-6      # 縞次数ちょうど
        print(f"   {h:.3f} um | {psi:+.4f} (誤差 {psi - h:+.4f}) | "
              f"{csi:+.4f} (誤差 {csi - h:+.4f}){tag}")
        assert abs(csi - h) < 1e-4                          # コヒーレンス法は常に正しい
    print(f"   位相法が壊れ始めた段差 = {min(broke):.2f} um = λ/4。"
          f"**例外も NaN も出ず、もっともらしい数が返る**のが要点")
    assert min(broke) == 0.20 and 0.15 not in broke

    # ------------------------------------------------------------------ #
    # 7) クロマティック共焦点(走査しない)                                 #
    # ------------------------------------------------------------------ #
    print("\n7) クロマティック共焦点(スペクトルのピーク波長 = 高さ):")
    for zt in (-15.0, 0.0, 4.25, 18.0):
        sp = I.chromatic_confocal_simulate(zt, 500.0, 0.5, 401, 0.20, 600.0,
                                           peak_fwhm_nm=4.0)
        got = I.chromatic_confocal_height(sp, 500.0, 0.5, 0.20, 600.0)
        print(f"   真の高さ {zt:+7.2f} um → {got:+.9f} um  誤差 {got - zt:+.1e}")
        assert abs(got - zt) < 1e-11
    print("   Hilbert 変換を使わない(3 点の局所当てはめ)ので、包絡線の切れが"
          "効かず、帯の端 2 bin でも厳密")

    # ------------------------------------------------------------------ #
    # 8) fail-closed — 拒否しなければ黙って間違う                          #
    # ------------------------------------------------------------------ #
    print("\n8) fail-closed(拒否しなかった場合に何が返るかを添える):")
    refused = 0
    for tag, fn in (
        ("走査ステップが λ/4 以上(折り返し)",
         lambda: I.csi_peak_position(sig, 0.16, 0.0, LAM)),
        ("表面が走査範囲の外",
         lambda: I.csi_signal_simulate(20.0, 0.0, DZ, NP, LAM,
                                       envelope_fwhm_um=None,
                                       envelope_sigma_um=SIGMA)),
        ("包絡線を持たない信号(正弦波)",
         lambda: I.csi_peak_position(np.sin(np.linspace(0, 8 * np.pi, 256)),
                                     DZ, 0.0, LAM)),
        ("定数信号",
         lambda: I.csi_peak_position(np.full(64, 3.0), DZ, 0.0, LAM)),
        ("単位の取り違え(文字列 '0.05')",
         lambda: I.csi_peak_position(sig, "0.05", 0.0, LAM)),
        ("bool を長さとして渡す",
         lambda: I.csi_peak_position(sig, True, 0.0, LAM)),
        ("NaN 混入",
         lambda: I.csi_envelope(np.where(np.arange(NP) == 7, np.nan, sig))),
        ("小さい入力から巨大割当(2^21 要素の 0 バイト view)",
         lambda: I.csi_envelope(np.broadcast_to(np.uint8(1), (1 << 21,)))),
    ):
        try:
            fn()
            print(f"   [FAIL] {tag}: 拒否されなかった")
            return False
        except ValueError as exc:
            refused += 1
            print(f"   拒否 {tag}: {str(exc).split(' — ')[0][:78]}")
    assert refused == 8

    edge = I.csi_signal_simulate(0.5, 0.0, DZ, NP, LAM, envelope_fwhm_um=None,
                                 envelope_sigma_um=SIGMA)
    try:
        I.csi_peak_position(edge, DZ, 0.0, LAM)
        print("   [FAIL] 端で切れた包絡線が拒否されなかった")
        return False
    except ValueError:
        lied = I.csi_peak_position(edge, DZ, 0.0, LAM, max_edge_envelope=1.0)
        print(f"   拒否 端で切れた包絡線: 見張りを外すと真値 0.500 um に対して "
              f"{lied:.4f} um を返す(有限・もっともらしい・{abs(lied - 0.5) / 0.5 * 100:.0f}% 間違い)")
        assert abs(lied - 0.5) > 0.3

    print("\nPASS: interferometry 9 op すべてが閉形式のグラウンドトゥルースと一致し、"
          "位相シフト法が壊れる領域で正しい高さを返した")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
