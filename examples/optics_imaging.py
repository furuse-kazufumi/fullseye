# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""optics_imaging — 光学 op(optics)を「検査機を 1 台設計する」筋で一巡する。

    py -3.11 examples/optics_imaging.py

【この例が解く問題】
産業ビジョンの検査機を 1 台、紙の上で設計しきる。ワークは 20 mm 角、
必要分解能 20 µm、センサ画素 3.45 µm。
(1) 幾何: 倍率からレンズ焦点距離と物体距離を決め、ABCD 行列で系全体を
    組んで「本当に結像しているか(B = 0)」を機械的に確かめる。
(2) 深度: 被写界深度と過焦点距離を出し、絞りをどこまで絞れるか決める。
(3) 回折: その絞りでの回折限界 MTF と Airy 径を出し、**絞りすぎると
    被写界深度ではなくボケを買う**ことを数値で示す。
(4) 収差: レンズの波面誤差(Zernike)から RMS/PV/Strehl を出し、
    回折限界(Strehl > 0.8)に入っているか判定する。
(5) 偏光: 金属面のテカりを偏光板で消す構成を Jones と Mueller の
    両方で組み、同じ Stokes ベクトルに一致することを確かめる。
(6) 波動: 開口の遠方回折像と、角スペクトル法による自由空間伝搬の
    可逆性(往復で元に戻る)を確かめる。

【グラウンドトゥルース(数値で嘘を弾く)】
1. thin_lens: 1/f = 1/s + 1/s' が機械精度。倍率 m = -s'/s。
   abcd_matrix の det = 1(同一媒質)、結像面で B = 0。
2. depth_of_field: 過焦点距離 H に合焦すると near = H/2 ちょうど、far = inf。
3. mtf_diffraction: カットオフ = 1/(λN)、その半分で教科書値 0.391。
   airy_pattern: 第 1 暗環が 1.2197 λN。
4. wavefront_stats: 純デフォーカス Z(2,0) の瞳面 RMS は厳密に 1/√3。
5. Jones 経路と Mueller 経路が同じ Stokes ベクトル(1e-14 以内)。
   直交偏光板で透過ちょうど 0。
6. 角スペクトル: 距離 0 は恒等、+z → -z の往復で相対誤差 < 1e-12、
   伝搬でパワー保存。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import optics as O  # noqa: E402


def main():
    ok = True

    # ------------------------------------------------------------------ #
    # 1) 幾何: 倍率 → 焦点距離・物体距離、ABCD で結像を機械確認           #
    # ------------------------------------------------------------------ #
    work_mm = 20.0                                              # 視野 20 mm 角
    focal_mm = 50.0
    # 20 mm の視野を 8.6 mm のセンサ幅へ → 倍率 -0.43 → 物体距離を逆算
    m_target = -0.43
    object_mm = focal_mm * (1.0 - 1.0 / m_target)               # s = f(1 - 1/m)
    lens = O.thin_lens(focal_mm, object_mm)
    image_mm = lens["image_mm"]
    print(f"1) 幾何: f={focal_mm:.1f} mm  物体距離={object_mm:.1f} mm  "
          f"像距離={image_mm:.2f} mm  倍率={lens['magnification']:+.3f}  "
          f"作動距離={lens['working_distance_mm']:.1f} mm")
    assert abs(1.0 / focal_mm - 1.0 / object_mm - 1.0 / image_mm) < 1e-12
    assert abs(lens["magnification"] - m_target) < 1e-9

    system = O.abcd_matrix([("free", object_mm), ("lens", focal_mm),
                            ("free", image_mm)])
    tr = O.abcd_trace(system, height_mm=work_mm / 2.0, angle_mrad=0.0)
    print(f"   ABCD: det={tr['determinant']:.12f}  結像={tr['imaging']}  "
          f"像高={tr['height_mm']:+.3f} mm  (A = 倍率 = {system[0, 0]:+.3f})")
    assert abs(tr["determinant"] - 1.0) < 1e-12                 # 同一媒質
    assert tr["imaging"] is True                                # B = 0 = 共役面
    assert abs(system[0, 0] - m_target) < 1e-9                  # A が倍率そのもの
    assert abs(tr["height_mm"] - m_target * work_mm / 2.0) < 1e-9

    # ------------------------------------------------------------------ #
    # 2) 深度: 許容錯乱円 = 2 画素、絞りごとの被写界深度                   #
    # ------------------------------------------------------------------ #
    coc_mm = 2.0 * 3.45e-3                                      # 2 画素 = 6.9 µm
    print("2) 深度(許容錯乱円 = 2 画素 = %.4f mm):" % coc_mm)
    for n in (2.8, 5.6, 11.0):
        d = O.depth_of_field(focal_mm, n, object_mm, coc_mm)
        print(f"   f/{n:<4} 被写界深度={d['depth_mm']:7.2f} mm  "
              f"(近 {d['near_mm']:.1f} / 遠 {d['far_mm']:.1f})  "
              f"過焦点={d['hyperfocal_mm'] / 1000.0:.2f} m")
        assert d["near_mm"] < object_mm < d["far_mm"]
    # 過焦点距離に合焦させると近限界はちょうど H/2、遠限界は無限大(契約)
    h = O.depth_of_field(focal_mm, 5.6, object_mm, coc_mm)["hyperfocal_mm"]
    at_h = O.depth_of_field(focal_mm, 5.6, h, coc_mm)
    assert abs(at_h["near_mm"] - h / 2.0) < 1e-9 and at_h["far_is_infinite"]

    # ------------------------------------------------------------------ #
    # 3) 回折: 絞るほど深度は増えるが分解能は落ちる、を数値で              #
    # ------------------------------------------------------------------ #
    lam_um, need_um = 0.55, 20.0
    need_cyc_mm = 1000.0 / (2.0 * need_um)                      # 20 µm 線対 → 25 cyc/mm
    print(f"3) 回折(λ={lam_um} µm、必要 {need_cyc_mm:.0f} cyc/mm @ 物体側):")
    for n in (2.8, 5.6, 11.0, 22.0):
        curve = O.mtf_diffraction(n, lam_um, 512)
        cutoff = curve[-1, 0]
        # 物体側 25 cyc/mm は像側では |m| 倍の周波数になる
        f_img = need_cyc_mm / abs(m_target)
        mtf_here = float(np.interp(f_img, curve[:, 0], curve[:, 1]))
        airy_um = 2.0 * 1.2197 * lam_um * n                     # 第 1 暗環の直径
        print(f"   f/{n:<4} カットオフ={cutoff:6.1f} cyc/mm  "
              f"MTF@{f_img:.0f}cyc/mm={mtf_here:.3f}  Airy 径={airy_um:.2f} µm")
        assert 0.0 <= mtf_here <= 1.0
    half = O.mtf_diffraction(5.6, lam_um, 101)
    assert abs(half[50, 1] - 0.3910022) < 1e-6                  # 教科書値
    assert abs(half[-1, 0] - 1000.0 / (lam_um * 5.6)) < 1e-9    # カットオフ
    # 実測 PSF → MTF も同じ土俵に載る(ここでは既知の Gaussian PSF で検算)
    sigma = 1.5
    ax = np.fft.fftfreq(128) * 128
    yy, xx = np.meshgrid(ax, ax, indexing="ij")
    psf = np.exp(-(yy ** 2 + xx ** 2) / (2.0 * sigma ** 2))
    psf /= psf.sum()
    meas = O.psf_to_mtf(psf, 3.45)                              # 画素 3.45 µm
    f_px = meas[:, 0] / 1000.0 * 3.45                           # cyc/mm → cyc/px
    gt = np.exp(-2.0 * np.pi ** 2 * sigma ** 2 * f_px ** 2)
    dev = float(np.abs(meas[:, 1] - gt).max())
    print(f"   psf_to_mtf(σ={sigma} px): 閉形式との最大差 {dev:.2e}")
    assert dev < 1e-3
    airy = O.airy_pattern(257, lam_um, 5.6, 0.05)
    row = airy[128, 128:]
    first_min = next(i for i in range(1, 120)
                     if row[i] < row[i - 1] and row[i] < row[i + 1]) * 0.05
    print(f"   airy_pattern: 第 1 暗環 実測 {first_min:.3f} µm / "
          f"理論 {1.2197 * lam_um * 5.6:.3f} µm")
    assert abs(first_min - 1.2197 * lam_um * 5.6) < 0.06
    assert airy[128, 128] == 1.0

    # ------------------------------------------------------------------ #
    # 4) 収差: 波面誤差 → Strehl(回折限界の判定)                        #
    # ------------------------------------------------------------------ #
    defocus = O.wavefront_stats({(2, 0): 0.1})
    print(f"4) 収差: デフォーカス 0.1 波  RMS={defocus['rms_waves']:.6f} 波 "
          f"(厳密 {0.1 / np.sqrt(3.0):.6f})  PV={defocus['pv_waves']:.3f}  "
          f"Strehl={defocus['strehl']:.4f}  Marechal 有効={defocus['marechal_valid']}")
    assert abs(defocus["rms_waves"] - 0.1 / np.sqrt(3.0)) < 2e-5
    assert abs(defocus["pv_waves"] - 0.2) < 1e-12
    mixed = O.wavefront_stats({(2, 0): 0.03, (2, 2): 0.04, (3, 1): 0.02,
                               (4, 0): 0.015})
    verdict = "回折限界内" if mixed["strehl"] > 0.8 else "回折限界外"
    print(f"   実レンズ風(defocus+astig+coma+spherical): RMS="
          f"{mixed['rms_waves']:.4f} 波  Strehl={mixed['strehl']:.4f} → {verdict}")
    assert mixed["strehl"] > 0.8                                # 設計は合格

    # ------------------------------------------------------------------ #
    # 5) 偏光: テカり消し(直交偏光板)を Jones と Mueller の両方で        #
    # ------------------------------------------------------------------ #
    illum = O.jones_element("polarizer", 0.0)                   # 照明側 0 deg
    analyzer = O.jones_element("polarizer", 90.0)               # 受光側 90 deg
    specular = np.array([1.0 + 0j, 0.0 + 0j])                   # 鏡面反射=偏光保存
    blocked = O.jones_apply(analyzer @ illum, specular)
    print("5) 偏光: 直交配置での鏡面反射の透過強度 = "
          f"{float((np.abs(blocked) ** 2).sum()):.3e}")
    assert (np.abs(blocked) ** 2).sum() < 1e-30                 # 完全に消える
    for angle in (0.0, 30.0, 60.0, 90.0):
        p = O.jones_element("polarizer", angle)
        got = (np.abs(O.jones_apply(p, specular)) ** 2).sum()
        assert abs(got - np.cos(np.radians(angle)) ** 2) < 1e-14   # Malus
    # 同じ素子を Mueller で組み、Jones 経路と一致することを確認
    state = np.array([0.8 + 0.1j, -0.3 + 0.5j])
    q = 37.0
    via_j = O.stokes_from_jones(
        O.jones_apply(O.jones_element("quarter_wave", q), state))
    via_m = O.mueller_apply(O.mueller_element("quarter_wave", q),
                            O.stokes_from_jones(state))
    print(f"   Jones 経路 vs Mueller 経路の Stokes 差 = "
          f"{float(np.abs(via_j - via_m).max()):.2e}")
    assert np.abs(via_j - via_m).max() < 1e-14
    # 拡散反射(無偏光)は偏光板を通っても半分残る = テカりだけが消える
    diffuse = O.mueller_apply(O.mueller_element("polarizer", 90.0),
                              np.array([1.0, 0.0, 0.0, 0.0]))
    an = O.stokes_analyze(diffuse)
    print(f"   無偏光の拡散光: 透過 {an['intensity']:.3f}(半分)  "
          f"偏光度 {an['dop']:.3f}  方位 {an['azimuth_deg']:.1f} deg")
    assert abs(an["intensity"] - 0.5) < 1e-15 and abs(an["dop"] - 1.0) < 1e-14

    # ------------------------------------------------------------------ #
    # 6) 波動: 遠方回折像 と 自由空間伝搬の可逆性                          #
    # ------------------------------------------------------------------ #
    aperture = np.zeros((64, 64))
    aperture[:, 30:34] = 1.0                                    # 4 画素幅スリット
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        far = O.fraunhofer_pattern(aperture, lam_um, 1000.0, 10.0)
    zeros = [far[32, 32 + k] for k in (16, -16, -32)]
    print("6) 波動: 4 画素スリットの回折零点(DC から ±16, -32 bin)= "
          f"{max(abs(z) for z in zeros):.1e}")
    assert max(abs(z) for z in zeros) == 0.0                    # 厳密に 0

    y, x = np.mgrid[0:64, 0:64] / 64.0
    field = (np.exp(-((y - 0.5) ** 2 + (x - 0.5) ** 2) / 0.05)
             * np.exp(2j * np.pi * (0.1 * x + 0.07 * y)))
    same = O.angular_spectrum_propagate(field, lam_um, 0.0, 1.0)
    fwd = O.angular_spectrum_propagate(field, lam_um, 250.0, 1.0)
    back = O.angular_spectrum_propagate(fwd, lam_um, -250.0, 1.0)
    rel = float(np.linalg.norm(back - field) / np.linalg.norm(field))
    p0 = float((np.abs(field) ** 2).sum())
    p1 = float((np.abs(fwd) ** 2).sum())
    print(f"   角スペクトル: 距離 0 は恒等={np.array_equal(same, field)}  "
          f"往復の相対誤差={rel:.2e}  パワー保存={abs(p1 - p0) / p0:.2e}")
    assert np.array_equal(same, field)
    assert rel < 1e-12 and abs(p1 - p0) / p0 < 1e-10

    beam = O.gaussian_beam(50.0, 0.633, 0.0)
    at_zr = O.gaussian_beam(50.0, 0.633, beam["rayleigh_mm"])
    print(f"   ガウシアンビーム: w0=50 µm  Rayleigh={beam['rayleigh_mm']:.2f} mm  "
          f"z=zR で w={at_zr['radius_um']:.3f} µm(√2·w0={50 * np.sqrt(2):.3f})  "
          f"Gouy={at_zr['gouy_deg']:.1f} deg")
    assert abs(at_zr["radius_um"] - 50.0 * np.sqrt(2.0)) < 1e-9
    assert abs(at_zr["gouy_deg"] - 45.0) < 1e-9

    # 視野照度の落ち(cos^4)も設計値として出しておく
    ri = O.relative_illumination(15.0, 4, 4.0)
    print(f"   画面端の照度比(半画角 15 deg, cos^4)= {ri[-1, 1]:.4f}")
    assert abs(ri[0, 1] - 1.0) < 1e-15

    print("PASS: optics 18 op すべてが閉形式のグラウンドトゥルースと一致")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
