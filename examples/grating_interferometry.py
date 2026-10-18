# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""grating_interferometry — 格子干渉の 8 op(gratinginterf)を「1 組の位相ステップから 3 枚の像を取る」筋で一巡する。

    py -3.11 examples/grating_interferometry.py

【この例が解く問題】
X 線の透過像は「どれだけ吸われたか」しか写さない。格子を 2 枚(線源が大きいなら 3 枚)入れて、片方を
1 周期ずらしながら数枚撮ると、各画素で縞の正弦が取れ、その平均・位相・振幅から 3 枚の像が同時に出る:
  透過(平均の比)/ 微分位相(位相のずれ = 屈折角)/ 暗視野(振幅の比 = 画素より小さい構造の小角散乱)。
ここでは、吸収ではほとんど見分けられない「粉の詰まった区画」が暗視野ではっきり浮かぶことを数で見せる。

(1) 設計: 公表の装置(14.4 keV、第 1 格子 4 µm の位相 π 格子)の距離 23.2 mm を閉形式で出し直す。
    線源が 1.5 m の円錐ビームでは距離と分析格子の周期が伸び、線源格子の周期(Lau の条件)が決まる。
(2) 順モデル: 樹脂の球(屈折する)と、同じ平均の吸収で微粉の詰まった区画(散乱する)を並べた試料から、
    試料あり 8 段・基準 6 段の位相ステップを Poisson 雑音つきで作る。
(3) 分離: 2 組から 3 枚を取り出し、真値と比べる。位相の雑音は Poisson の下での式 √2/(V√(N·a)) と比べる。
(4) 暗視野 → 散乱角の広がり σ(ガウス散乱の公表式)と、線拡散係数。
(5) タルボ絨毯と線源: 位相 π の格子の縞の可視度が分数タルボ距離で 4/π になること、2 mm の焦点では縞が消え、
    Lau の条件の線源格子で 2/π まで戻ること。
(6) 較正と積分: 1 周期のステップ数 P を残差の最小で推定し(N = 22 枚で P = 20.85)、微分位相を積分して丸棒の厚さに戻す。
(7) fail-closed: 縞の無い基準・正弦が分けられない走査・1 を超える暗視野・折り返した微分位相を拒否する。

【グラウンドトゥルース】
1. 距離 23.2 mm(Weitkamp ら 2005, Opt. Express 13, 6296 の装置の数値)。
2. 雑音なしの 3 像は機械精度で戻る(試料と基準のステップ数が違っても)。
3. 位相の雑音の標準偏差が Poisson の式と 10 % 以内。
4. 暗視野から戻した σ が、試料に入れた σ と一致する。
5. 絨毯の極大が 4/π(方形波の基本波)、Lau の条件で 2/π(開口 1/2 の |sinc|)。
6. 推定した P が真値 20.85 と 0.05 段以内、積分した厚さが真値と 3 % 以内。
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gratinginterf as GI  # noqa: E402


def _phantom(h=96, w=128, pixel_um=20.0, delta=3.0e-7, mu_per_um=2.0e-5, d_um=23.2e3, p2_um=2.0,
             sigma_powder_urad=15.0):
    """樹脂の球と粉の区画。返り値: (透過, 微分位相 rad, 暗視野, 粉の区画の画素)。"""
    yy, xx = np.mgrid[:h, :w].astype(float)
    r_px = 28.0
    rr = np.hypot(xx - 40.0, yy - 48.0)
    thick_um = 2.0 * np.sqrt(np.clip(r_px * r_px - rr * rr, 0.0, None)) * pixel_um
    trans = np.exp(-mu_per_um * thick_um)
    # 屈折角 α = −δ ∂t/∂x(x は画素の列)。縞の位相 φ = 2π d α / p2。
    dtdx = np.gradient(thick_um, axis=1) / pixel_um
    phi = 2.0 * math.pi * d_um * (-delta * dtdx) / p2_um
    powder = (xx > 84) & (xx < 120) & (yy > 20) & (yy < 76)
    # 粉の区画: 球の中心と同じ平均の吸収になる厚さで置き、散乱だけを足す
    trans = np.where(powder, float(np.exp(-mu_per_um * 2 * r_px * pixel_um * 0.55)), trans)
    k = 2.0 * math.pi ** 2 * (d_um / p2_um) ** 2
    dfm = np.where(powder, math.exp(-k * (sigma_powder_urad * 1e-6) ** 2), 1.0)
    return trans, phi, dfm, powder


def main() -> bool:
    ok = True
    print("(1) 設計")
    d = GI.talbot_grating_design(4.0, energy_kev=14.4, grating="pi", order=1)
    print(f"   14.4 keV・p1 = 4 µm・位相 π・m = 1: d = {d['distance_mm']:.2f} mm(公表 23.2 mm)、"
          f"p2 = {d['analyzer_period_um']:.2f} µm、ξ = {d['correlation_length_um']:.2f} µm")
    ok &= round(d["distance_mm"], 1) == 23.2
    c = GI.talbot_grating_design(4.0, energy_kev=28.0, grating="pi", order=1, source_distance_mm=1500.0)
    print(f"   28 keV・線源 1.5 m: d' = {c['distance_mm']:.2f} mm(平面波 {c['distance_plane_mm']:.2f})、"
          f"M = {c['magnification']:.4f}、p2 = {c['analyzer_period_um']:.4f} µm、"
          f"線源格子 p0 = {c['source_grating_period_um']:.2f} µm")

    print("(2) 順モデル(試料あり 8 段・基準 6 段、1 枚あたり 3000 光子)")
    trans, phi, dfm, powder = _phantom(d_um=d["distance_mm"] * 1e3, p2_um=d["analyzer_period_um"])
    v0, flux = 0.30, 3000.0
    s = GI.grating_stepping_simulate(trans, phi, dfm, n_steps=8, ref_visibility=v0, flux=flux, seed=1)
    r = GI.grating_stepping_simulate(None, n_steps=6, ref_visibility=v0, flux=flux, seed=2, shape=trans.shape)

    print("(3) 分離")
    o = GI.grating_three_image_retrieve(s, r, distance_mm=d["distance_mm"],
                                        analyzer_period_um=d["analyzer_period_um"])
    sphere_mid = (slice(40, 56), slice(30, 50))
    t_mid = float(np.mean(o["transmission"][sphere_mid]))
    t_pow = float(np.mean(o["transmission"][powder]))
    d_mid = float(np.mean(o["darkfield"][sphere_mid]))
    d_pow = float(np.mean(o["darkfield"][powder]))
    print(f"   透過: 球の中央 {t_mid:.3f} / 粉の区画 {t_pow:.3f}(吸収では見分けにくい)")
    print(f"   暗視野: 球の中央 {d_mid:.3f} / 粉の区画 {d_pow:.3f}(粉だけが落ちる)")
    ok &= abs(t_mid - t_pow) < 0.05 and d_pow < d_mid - 0.3
    flat = ~powder & (np.hypot(*np.mgrid[:96, :128] - np.array([48.0, 40.0])[:, None, None]) > 32)
    err = o["dpc_rad"][flat] - phi[flat]
    pred = math.sqrt(2.0 / (8 * flux)) / v0 * math.sqrt(1.0 + 8.0 / 6.0)   # 試料と基準の雑音の和
    print(f"   位相の雑音(空気の画素): 実測 {np.std(err):.4f} rad / Poisson の式 {pred:.4f} rad")
    ok &= 0.9 < float(np.std(err)) / pred < 1.1
    edge = float(np.nanmax(np.abs(o["refraction_urad"])))
    print(f"   球の縁での屈折角の最大 {edge:.2f} µrad(1 µrad = 縞の位相 {d['angular_sensitivity'] * 1e-6:.3f} rad)")

    print("(4) 暗視野 → 散乱角の広がり")
    rel = GI.darkfield_scatter_relation(darkfield=d_pow, distance_mm=d["distance_mm"],
                                        analyzer_period_um=d["analyzer_period_um"], thickness_mm=0.72,
                                        wavelength_nm=d["wavelength_nm"])
    print(f"   σ = {rel['sigma_urad']:.3f} µrad(入れた値 15.000)、ε = {rel['diffusion_coeff_urad2_per_mm']:.3f} µrad²/mm")
    ok &= abs(rel["sigma_urad"] - 15.0) < 0.3

    print("(5) タルボ絨毯と線源")
    cp = GI.talbot_carpet(4.0, energy_kev=28.0, grating="pi", n_z=1601)
    first = cp["z_mm"] <= 2.0 * cp["self_image_mm"][0]           # 最初の極大(m = 1)の周り
    k = int(np.argmax(np.round(np.where(first, cp["visibility"], -1.0), 9)))
    print(f"   位相 π・28 keV: 縞の可視度の最大 {cp['visibility'][k]:.4f}(4/π = {4 / math.pi:.4f})"
          f" at z = {cp['z_mm'][k]:.1f} mm / 分数タルボ距離 {', '.join(f'{z:.1f}' for z in cp['self_image_mm'][:3])} … mm")
    ok &= abs(cp["visibility"][k] - 4 / math.pi) < 2e-3
    g2 = GI.talbot_grating_design(4.0, energy_kev=28.0, source_distance_mm=1200.0)
    no_g0 = GI.talbot_source_visibility(2000.0, 1200.0, g2["distance_mm"], g2["analyzer_period_um"])
    with_g0 = GI.talbot_source_visibility(2000.0, 1200.0, g2["distance_mm"], g2["analyzer_period_um"],
                                          source_grating_period_um=g2["source_grating_period_um"])
    print(f"   焦点 2 mm: 線源格子なし ×{no_g0['visibility_factor']:.3f} → Lau の条件の線源格子"
          f"(p0 = {g2['source_grating_period_um']:.1f} µm、{with_g0['n_slits']} 本)×{with_g0['visibility_factor']:.3f}")
    ok &= no_g0["visibility_factor"] < 0.02 and abs(with_g0["visibility_factor"] - 2 / math.pi) < 1e-9

    print("(6) 較正と積分")
    raw = GI.grating_stepping_simulate(None, n_steps=22, steps_per_period=20.85, ref_visibility=0.25, flux=3000.0,
                                       seed=3, shape=(48, 48))
    est = GI.grating_step_period_estimate(raw, p_step=0.01)
    print(f"   22 枚・1 周期 20.85 段の走査: 推定 P = {est['steps_per_period']:.2f}"
          f"(残差 P = N {est['residual_at_n']:.4f} → {est['residual_min']:.4f})")
    ok &= abs(est["steps_per_period"] - 20.85) <= 0.05
    xb = np.arange(201, dtype=float) - 0.5
    tb = 2.0 * np.sqrt(np.clip(60.0 ** 2 - (xb - 100.0) ** 2, 0.0, None)) * 40.0      # 直径 4.8 mm の丸棒 [µm]
    alpha = -4.0e-7 * np.diff(tb) / 40.0
    phi_rod = np.tile(alpha * d["angular_sensitivity"], (24, 1))
    s_rod = GI.grating_stepping_simulate(None, phi_rod, None, n_steps=8, ref_visibility=0.25, flux=6000.0, seed=4)
    r_rod = GI.grating_stepping_simulate(None, n_steps=8, ref_visibility=0.25, flux=6000.0, seed=5,
                                         shape=phi_rod.shape)
    rod = GI.grating_three_image_retrieve(s_rod, r_rod)
    th = GI.dpc_integrate(rod["dpc_rad"], 40.0, d["distance_mm"], d["analyzer_period_um"], energy_kev=14.4,
                          delta=4.0e-7, baseline="both")["thickness_um"].mean(axis=0)
    t_true = 0.5 * (tb[1:] + tb[:-1])
    err = float(np.max(np.abs(th - t_true)) / t_true.max())
    print(f"   微分位相を積分した丸棒の厚さ: 中央 {th[100] / 1e3:.3f} mm(真値 {t_true[100] / 1e3:.3f})、最大誤差 {err * 100:.2f} %")
    ok &= err < 0.03

    print("(7) fail-closed")
    for label, fn in [
        ("縞の無い基準", lambda: GI.grating_three_image_retrieve(s, np.ones((6, 96, 128)))),
        ("1 周期の 1/100 しか動かしていない走査",
         lambda: GI.grating_three_image_retrieve(GI.grating_stepping_simulate(n_steps=3, steps_per_period=300),
                                                 GI.grating_stepping_simulate(), steps_per_period_sample=300)),
        ("1 を超える暗視野(スカラー)", lambda: GI.darkfield_scatter_relation(darkfield=1.3)),
        ("折り返した微分位相(縞の位相を 8 倍 —— 本当の最大 3.6 rad > π)",
         lambda: GI.dpc_integrate(GI._wrap(phi_rod * 8.0), 40.0, d["distance_mm"], d["analyzer_period_um"],
                                  energy_kev=14.4)),
    ]:
        try:
            fn()
            print(f"   [FAIL] {label} が通った")
            ok = False
        except ValueError as e:
            print(f"   拒否 {label}: {str(e)[:90]}")
    print("\nPASS: 格子干渉の 8 op が公表の距離・Poisson の式・暗視野の公表式・絨毯と Lau の閉形式と一致した"
          if ok else "\nFAIL")
    return bool(ok)


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
