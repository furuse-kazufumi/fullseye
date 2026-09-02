# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""lens_design_demo — raytrace(design)12 op で singlet と doublet を実光線で比べる。

    py -3.11 examples/lens_design_demo.py

【この例が解く問題】
optics の近軸計算は「f=100 の f/4 レンズ」までは決めてくれるが、その処方が
**実際にどれだけボケるか**は面を 1 枚ずつ実光線で通さないと分からない。
同じ f≈100 / f/4 の平凸 singlet(BK7)と貼り合わせ achromat doublet(BK7/SF2)を
同じ手順で通し、設計者が見る表を出す:
(1) 近軸表: EFL / BFL / 主点 / 瞳 / f 値(paraxial_trace)。閉形式 thick_lens と
    面ごとの追跡が 1e-9 で一致することを機械的に確かめる。
(2) Seidel 表: 面ごとの S_I..S_V と色収差 C_L / C_T(seidel_coefficients)。
    行の和が total に一致し、doublet の軸上色収差が singlet より小さいことを確認。
(3) スポット: 軸上 / 5 deg の RMS 半径(spot_stats、spot_diagram、ray_fan)。
    doublet が両方で singlet に勝つ。
(4) 波面: OPD 地図(opd_map)→ Zernike(wavefront_from_opd)→ RMS/PV/Strehl。
    singlet の OPD は非負(Welford 符号: W040 = +S_I/8)で、Zernike (4,0) > 0。
(5) 公差: Monte-Carlo で rms_spot の p95 と、最も効くパラメータ(tolerance_analysis)。
    seed を固定した 2 回の実行が一致(決定性)。

【グラウンドトゥルース(数値で嘘を弾く)】
1. thick_lens(50,-50,5,1.5168) と paraxial_trace の EFL/BFL/主点が 1e-9 で一致。
   singlet の EFL = 100.000 (1e-6)、f/4、入射瞳半径 12.5。
2. 放物面鏡(k=-1)は軸上で完全結像: RMS スポット < 1e-9 mm、OPD < 1e-6 波。
   同半径の球面鏡は RMS 0.119 mm(球面収差)。
3. Seidel per_surface の和 = total(1e-12)。
4. singlet の opd_map >= 0、最大 11.56 波、S_I/8 = 11.29 波。
5. tolerance_analysis(seed=1) は決定的、failed = 0、感度 1 位は R(面 0)。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import raytrace as RT  # noqa: E402

INF = float("inf")


def _paraxial_table(name, system):
    p = RT.paraxial_trace(system)
    print(f"   {name:8s} EFL={p['efl']:8.3f}  BFL={p['bfl']:8.3f}  "
          f"PP'={p['pp_rear']:7.3f}  EP r={p['ep_radius']:5.2f}  f/{p['fno']:.2f}  "
          f"XP z={p['xp_position']:8.3f}")
    return p


def _seidel_table(name, system, field):
    se = RT.seidel_coefficients(system, field=field)
    print(f"   {name} (field {field:.0f} deg)  surface   S_I      S_II     S_III    S_IV     S_V      C_L      C_T")
    for r in se["per_surface"]:
        print("      " + f"{r['surface']:>7d} " + " ".join(f"{r[k]:8.4f}" for k in
                                                          ("S_I", "S_II", "S_III", "S_IV", "S_V", "C_L", "C_T")))
    t = se["total"]
    print("      " + "  total " + " ".join(f"{t[k]:8.4f}" for k in
                                          ("S_I", "S_II", "S_III", "S_IV", "S_V", "C_L", "C_T")))
    for k in t:
        assert abs(sum(r[k] for r in se["per_surface"]) - t[k]) < 1e-12, k
    return se


def main() -> bool:
    print("== lens_design_demo: singlet vs doublet, real rays ==")
    singlet = RT.example_system("singlet")
    doublet = RT.example_system("doublet")
    # 硝材モデル: BK7 の d 線と F-C 分散を再現する 2 項 Cauchy
    bk7 = RT.glass(1.5168, 64.17)
    dn = RT.refractive_index(bk7, RT.WL_F) - RT.refractive_index(bk7, RT.WL_C)
    print(f"   glass BK7: n_d={RT.refractive_index(bk7):.4f}  n_F-n_C={dn:.6f}  "
          f"(=(n_d-1)/V_d={(1.5168 - 1) / 64.17:.6f})")
    assert abs(dn - (1.5168 - 1) / 64.17) < 1e-12

    # (1) 近軸表 + 閉形式との一致
    print("1) paraxial")
    ps = _paraxial_table("singlet", singlet)
    pd_ = _paraxial_table("doublet", doublet)
    assert abs(ps["efl"] - 100.0) < 1e-6 and abs(ps["fno"] - 4.0) < 1e-9
    assert abs(pd_["efl"] - 96.63) < 0.5           # measured 2026-09-03: 96.626 mm
    tl = RT.thick_lens(50.0, -50.0, 5.0, 1.5168)
    pt = RT.paraxial_trace(RT.lens_system([{"R": 50, "t": 5, "n": 1.5168, "ap": 10},
                                           {"R": -50, "t": None, "n": 1.0}]))
    for k in ("efl", "bfl", "ffl", "pp_front", "pp_rear"):
        assert abs(tl[k] - pt[k]) < 1e-9, k
    print(f"   thick_lens vs trace (biconvex 50/-50, t=5): EFL {tl['efl']:.6f} == {pt['efl']:.6f}")
    # 放物面鏡 = 軸上完全結像の対照
    para = RT.example_system("paraboloid")
    sph = RT.example_system("sphere_mirror")
    rms_para = RT.spot_stats(para)["rms_radius"]
    rms_sph = RT.spot_stats(sph)["rms_radius"]
    opd_para = np.nanmax(np.abs(RT.opd_map(para, fill=np.nan)))
    print(f"   paraboloid f/2: rms={rms_para:.1e} mm, |OPD|max={opd_para:.1e} waves  |  "
          f"sphere mirror: rms={rms_sph:.4f} mm")
    assert rms_para < 1e-9 and opd_para < 1e-6 and rms_sph > 0.05

    # (2) Seidel 表
    print("2) Seidel (mm x 8; W040 = S_I/8)")
    ses = _seidel_table("singlet", singlet, 5.0)
    sed = _seidel_table("doublet", doublet, 5.0)
    ratio = abs(ses["total"]["C_L"]) / abs(sed["total"]["C_L"])
    print(f"   axial colour |C_L|: singlet {abs(ses['total']['C_L']):.5f}  doublet "
          f"{abs(sed['total']['C_L']):.5f}  -> {ratio:.2f}x smaller")
    assert ratio > 4.5                                 # measured 4.78x

    # (3) スポット
    print("3) spot RMS radius [mm]")
    rows = {}
    for name, s in (("singlet", singlet), ("doublet", doublet)):
        r0 = RT.spot_stats(s)["rms_radius"]
        r5 = RT.spot_stats(s, field=5.0)["rms_radius"]
        rows[name] = (r0, r5)
        print(f"   {name:8s} on-axis {r0:.4f}   5 deg {r5:.4f}")
    assert rows["doublet"][0] < rows["singlet"][0] and rows["doublet"][1] < rows["singlet"][1]
    xy = RT.spot_diagram(singlet, rings=6)
    fan = RT.ray_fan(singlet, n=7)
    assert np.isfinite(xy).all() and np.allclose(fan[:, 1], -fan[::-1, 1], atol=1e-12)
    print(f"   singlet spot_diagram {xy.shape[0]} rays; ray_fan edge {fan[-1, 1]:+.4f} mm (antisymmetric)")

    # (4) 波面
    print("4) wavefront (OPD -> Zernike)")
    w = RT.opd_map(singlet)
    assert w.min() >= 0.0 and abs(w.max() - 11.56) < 0.05
    print(f"   singlet OPD: min {w.min():.3f}  max {w.max():.3f} waves  (S_I/8 = "
          f"{RT.seidel_coefficients(singlet)['waves']['S_I'] / 8:.3f})")
    for name, s in (("singlet", singlet), ("doublet", doublet)):
        z = RT.wavefront_from_opd(s)
        print(f"   {name:8s} Z(4,0)={z['zernike'][(4, 0)]:+.4f}  rms(direct)={z['rms_opd_direct']:.3f}  "
              f"PV={z['pv_opd_direct']:.3f} waves  Strehl={z['strehl']:.2e} (marechal_valid={z['marechal_valid']})")
        assert z["zernike"][(4, 0)] > 0.0

    # (5) 公差
    print("5) tolerances (40 trials, seed 1)")
    t1 = RT.tolerance_analysis(singlet, trials=40, seed=1)
    t2 = RT.tolerance_analysis(singlet, trials=40, seed=1)
    assert json.dumps(t1, sort_keys=True) == json.dumps(t2, sort_keys=True)
    assert t1["failed"] == 0
    print(f"   rms_spot nominal {t1['nominal']['rms_spot']:.4f}  mean {t1['rms_spot']['mean']:.4f}  "
          f"p95 {t1['rms_spot']['p95']:.4f}  worst {t1['rms_spot']['worst']:.4f}   "
          f"EFL p5..p95 {t1['efl']['p5']:.2f}..{t1['efl']['p95']:.2f}")
    top = t1["sensitivity"][0]
    print(f"   most sensitive: surface {top['surface']} {top['parameter']} "
          f"(+/-{top['tolerance']}): dEFL={top['d_efl']:+.3f} dRMS={top['d_rms_spot']:+.5f}")
    assert top["parameter"] == "R" and top["surface"] == 0
    assert np.isfinite(t1["rms_spot"]["p95"])

    print("PASS: raytrace design 12 op — singlet/doublet の近軸・Seidel・スポット・波面・公差が真値と一致")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
