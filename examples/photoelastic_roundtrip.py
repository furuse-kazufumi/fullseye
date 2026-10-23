# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""photoelastic_roundtrip — 光弾性の族を一巡する呼び出し例(応力場 → 縞 → 偏光像 → 応力)。

    py -3.11 examples/photoelastic_roundtrip.py

1. 直径圧縮の円板と穴のある板(Kirsch)の応力場を閉形式で作る。
2. 主応力差と等傾角 → 応力光学則で位相差(rad・nm・縞次数を並べて返す)。
3. 平面・円偏光器の暗視野の縞(等色線と等傾線)を描く。
4. 円偏光照明の試料を 6 強度の偏光計で撮った像から、位相差と主軸を閉形式で戻す。
5. 波長 3 本の折り返した位相から、1 波長を超える位相差(nm)の次数を決める。
6. Si(100) ウェハでは同じ応力でも結晶方位で複屈折が変わる(係数は出典つきの表から)。

どの段も真値と突き合わせ、ずれを数字で出す。``FULLSEYE_FIGURE_DIR`` があれば図を書く。
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import photoelastic as pe  # noqa: E402

THICK_M = 0.006          # 板厚 6 mm(引数は m)
C_PA = 5e-11             # 応力光学係数 [Pa^-1](樹脂の桁)
LAMBDA_M = 5.5e-7        # 550 nm(引数は m)


def main():
    ok = True

    # 1-2. 円板: 応力場 → 主応力 → 位相差
    disc = pe.brazilian_disc_stress(radius_m=0.025, thickness_m=THICK_M, load_n=500.0, size=161)
    inside = disc["inside"]
    p = pe.principal_stress(disc["sxx"], disc["syy"], disc["txy"])
    ret = pe.photoelastic_retardation(p["difference"], THICK_M, C_PA, LAMBDA_M)
    c = 80
    print("disc centre: sigma_x %.4f MPa (closed form %.4f), sigma_y %.4f MPa (closed form %.4f)"
          % (disc["sxx"][c, c] / 1e6, disc["centre_sxx"] / 1e6, disc["syy"][c, c] / 1e6,
             disc["centre_syy"] / 1e6))
    print("disc centre: fringe order %.3f, retardation %.1f nm, material fringe value %.0f N/m"
          % (ret["fringe_order"][c, c], ret["retardation_nm"][c, c], ret["fringe_value_n_per_m"]))
    nm_from_rad = pe.retardation_convert(ret["delta_rad"][c, c], "rad", "nm", 550.0)
    ok &= abs(nm_from_rad - ret["retardation_nm"][c, c]) < 1e-9
    print("  rad -> nm through the wavelength agrees with the returned nm: %s"
          % (abs(nm_from_rad - ret["retardation_nm"][c, c]) < 1e-9))

    # 3. 偏光器の縞
    dark_circ = pe.polariscope_intensity(ret["delta_rad"], p["angle_deg"], "circular_dark")
    dark_plane = pe.polariscope_intensity(ret["delta_rad"], p["angle_deg"], "plane_dark", polarizer_deg=0.0)
    n_dark = int(np.sum(inside & (dark_circ < 1e-3)))
    print("circular dark field: %d pixels darker than 1e-3 (isochromatics N = 0, 1, 2 ...)" % n_dark)

    # 4. 6 強度の偏光計 → 位相差と主軸(1/2 波長まで一意)
    images = pe.photoelastic_polarization_images(ret["delta_rad"], p["angle_deg"], "stokes6")
    est = pe.photoelastic_phase_estimate(images, "stokes6")
    m = inside & (ret["delta_rad"] > 0.05) & (ret["delta_rad"] < np.pi - 0.05)
    back = est["delta_rad"] * LAMBDA_M / (2 * np.pi * THICK_M * C_PA)
    rel = float(np.max(np.abs(back[m] - p["difference"][m]) / p["difference"][m]))
    ang = float(np.max(np.abs((est["axis_deg"] - p["angle_deg"] + 90.0) % 180.0 - 90.0)[m]))
    print("polarimeter -> sigma1 - sigma2: max relative error %.2e over %d unwrapped pixels; "
          "axis error %.2e deg" % (rel, int(m.sum()), ang))
    ok &= rel < 1e-6 and ang < 1e-6
    wrapped_px = int(np.sum(inside & (ret["delta_rad"] > np.pi)))
    print("  %d pixels exceed half a wave: a single wavelength cannot order them" % wrapped_px)

    # 5. 3 波長で次数を決める(分散なしの仮定)
    lams = [450.0, 532.0, 633.0]
    true_nm = ret["retardation_nm"]
    folded = []
    for lam in lams:
        e = pe.photoelastic_phase_estimate(
            pe.photoelastic_polarization_images(2 * np.pi * true_nm / lam, p["angle_deg"], "stokes6"),
            "stokes6")
        folded.append(e["delta_rad"])
    un = pe.retardation_unwrap_multiwavelength(folded, lams, 3000.0)
    sel = inside & (true_nm < 3000.0)
    err_nm = float(np.max(np.abs(un["retardation_nm"][sel] - true_nm[sel])))
    print("three wavelengths -> retardation: max error %.2e nm up to %.0f nm (min margin %.1f nm)"
          % (err_nm, float(true_nm[sel].max()), float(un["margin_nm"][sel].min())))
    ok &= err_nm < 1e-6

    # Kirsch: 穴の縁で 3S
    kp = pe.kirsch_plate_stress(hole_radius_m=0.004, remote_stress_pa=1e6, half_width_m=0.02, size=161)
    edge = float(pe.kirsch_plate_stress(0.004, 1e6, x=[0.0], y=[0.004])["stt"][0])
    print("Kirsch: hoop stress at the hole edge (90 deg) = %.6f S (closed form 3)" % (edge / 1e6))
    ok &= abs(edge / 1e6 - 3.0) < 1e-12
    kp_p = pe.principal_stress(kp["sxx"], kp["syy"], kp["txy"])

    # 6. Si(100): 同じ純せん断でも方位で複屈折が変わる
    si = pe.silicon_piezo_optic_coefficients("stoehr2020")
    print("Si piezo-optic coefficients (%s): pi11-pi12 = %.3g /Pa, pi44 = %.3g /Pa"
          % (si["source"], si["pi11_minus_pi12"], si["pi44"]))
    phis = np.arange(0.0, 91.0, 15.0)
    dns = [float(pe.cubic_photoelastic_birefringence(0.0, 0.0, 1e7, si["pi11_minus_pi12"], si["pi44"], 3.5,
                                                      crystal_angle_deg=f)["delta_n"]) for f in phis]
    for f, dn in zip(phis, dns):
        print("  crystal angle %4.0f deg: delta_n = %.4e" % (f, dn))
    ratio = max(dns) / min(dns)
    print("  max/min = %.4f (= |pi11-pi12| / |pi44| = %.4f)"
          % (ratio, abs(si["pi11_minus_pi12"] / si["pi44"])))
    biref = pe.retardation_from_birefringence(max(dns), 525e-6, 1.55e-6)
    print("  525 um wafer at 1550 nm: %.3f waves" % float(biref["fringe_order"]))

    figs.save_grid(
        "photoelastic_roundtrip",
        [np.where(inside, dark_plane, 0.0), np.where(inside, dark_circ, 0.0),
         np.where(inside, est["delta_rad"], 0.0), np.where(sel, un["retardation_nm"], 0.0),
         np.where(kp["inside"], kp_p["difference"] / 1e6, 0.0)],
        ["plane polariscope, dark (isoclinics + isochromatics)", "circular polariscope, dark",
         "delta from the polarimeter [rad] (folded at pi)", "retardation from 3 wavelengths [nm] (< 3000 nm)",
         "Kirsch: sigma1 - sigma2 [MPa]"],
        title="photoelastic family: stress field -> fringes -> images -> stress",
        caption="Closed-form fields, polariscope intensities and the closed-form inversion; "
                "numbers in the console are compared with the truth.")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
