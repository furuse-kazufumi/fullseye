# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: ガラスと鏡面の光学を閉じた式で解く(界面・吸収・平板・分散)。

やりたいこと: 「窓ガラスはどれだけ通すのか」「偏光板で映り込みが消える角度は」
「金はなぜ黄色いのか」「プリズムはなぜ虹を作るのか」を、絵ではなく**数字**で出す。
どれも光線追跡を必要としない閉じた式で、公開値と突き合わせられる。

使う op(glassmirror 10 つ全部): fresnel_dielectric / fresnel_conductor /
brewster_angle_deg / critical_angle_deg / metal_optical_constants /
metal_mirror_rgb / beer_lambert_transmittance / slab_transmittance /
refract_rays / prism_min_deviation_deg。

検証(GT): すべて閉じた式・公開値との一致で固定する。
  * 垂直入射の反射率 = ((n1−n2)/(n1+n2))²(空気→BK7 で 0.04)。
  * Brewster 角 atan(n2/n1) で **p 偏光が厳密に 0**(偏光板で映り込みが消える角度)。
  * 臨界角を超えた入射は **厳密に 1.0**(全反射)。
  * 吸収 0・垂直入射の平板は T = 2n/(n²+1)(多重反射を数え上げた既知の結果)。
  * 屈折は Snell を満たし、全反射は**光線ごと**にマスクされる。
  * プリズムの最小偏角は短波長ほど大きい(正常分散)。

beat-the-null: 金属の色を「塗る」零点との対比 —— ここでは n,k から反射スペクトルを
計算して等色関数に通すだけで、金は R>G>B の黄金色に、銀はほぼ中性になる。
色をどこにも書いていないのに材質の違いが出ることが、塗る方式との差である。
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from glassmirror import (METALS, beer_lambert_transmittance, brewster_angle_deg,
                         critical_angle_deg, fresnel_conductor, fresnel_dielectric,
                         metal_mirror_rgb, metal_optical_constants,
                         prism_min_deviation_deg, refract_rays, slab_transmittance)


def main() -> None:
    print("=" * 78)
    print("ガラスと鏡面の光学: 界面・吸収・平板・分散")
    print("=" * 78)

    # --- 1) 誘電体の界面 ---------------------------------------------------
    n_glass = 1.5168                                      # N-BK7 の d 線
    r0 = float(fresnel_dielectric(1.0, 1.0, n_glass))
    want = ((1.0 - n_glass) / (1.0 + n_glass)) ** 2
    brew = brewster_angle_deg(1.0, n_glass)
    rp = float(fresnel_dielectric(np.cos(np.radians(brew)), 1.0, n_glass, "p"))
    rs = float(fresnel_dielectric(np.cos(np.radians(brew)), 1.0, n_glass, "s"))
    print(f"垂直入射の反射率          : {r0:.9f}  (閉じた式 {want:.9f})")
    print(f"Brewster 角               : {brew:.4f}°  → p 偏光 {rp:.2e} / s 偏光 {rs:.4f}")
    assert abs(r0 - want) < 1e-12 and abs(rp) < 1e-15 and rs > 0.05

    crit = critical_angle_deg(n_glass, 1.0)
    beyond = fresnel_dielectric(np.cos(np.radians([crit + 0.001, crit + 5.0])), n_glass, 1.0)
    print(f"臨界角(ガラス→空気)      : {crit:.4f}°  → 超えた先の反射率 {beyond}")
    assert np.all(beyond == 1.0)

    # --- 2) 金属の色は n,k から出る ---------------------------------------
    w = np.array([450.0, 550.0, 650.0])
    print("金属           R(450/550/650)        線形 sRGB")
    rgbs = {}
    for metal in METALS:
        n, k = metal_optical_constants(metal, w)
        R = fresnel_conductor(1.0, n, k)
        rgbs[metal] = metal_mirror_rgb(metal, 1.0)
        print(f"  {metal:3s}          {np.round(R, 3)}      {np.round(rgbs[metal], 3)}")
    assert rgbs["au"][0] > rgbs["au"][1] > rgbs["au"][2]          # 金は黄金色
    assert float(np.ptp(rgbs["ag"])) < 0.08                       # 銀は中性
    assert np.all(fresnel_conductor(1.0, *metal_optical_constants("ag", w)) > 0.9)

    # --- 3) ガラスの体積と平行平板 -----------------------------------------
    t_clear = float(slab_transmittance(1.0, 1.0, n_glass, 3.0, 0.0))
    t_known = 2.0 * n_glass / (n_glass ** 2 + 1.0)
    inner = float(beer_lambert_transmittance(10.0, 0.1))
    print(f"平板の透過(吸収 0)       : {t_clear:.9f}  (既知値 2n/(n²+1) = {t_known:.9f})")
    print(f"Beer–Lambert  σL=1        : {inner:.9f}  (exp(-1) = {np.exp(-1.0):.9f})")
    assert abs(t_clear - t_known) < 1e-12 and abs(inner - np.exp(-1.0)) < 1e-12
    thick = [float(slab_transmittance(1.0, 1.0, n_glass, 19.0, s)) for s in (0.0, 0.002, 0.02)]
    print(f"19 mm 板の透過 σ=0/0.002/0.02 : {np.round(thick, 4)}  (単調に減る)")
    assert thick[0] > thick[1] > thick[2]

    # --- 4) 屈折(光線ごとの全反射)----------------------------------------
    ang = np.radians(np.array([10.0, 30.0, 60.0]))
    d = np.stack([np.sin(ang), np.zeros_like(ang), -np.cos(ang)], -1)
    nrm = np.tile(np.array([0.0, 0.0, 1.0]), (3, 1))
    out_in, tir_in = refract_rays(d, nrm, 1.0, n_glass)
    st = np.linalg.norm(np.cross(out_in, nrm), axis=-1)
    print(f"空気→ガラス Snell 残差    : {float(np.abs(n_glass * st - np.sin(ang)).max()):.2e}")
    assert np.allclose(n_glass * st, np.sin(ang), atol=1e-12) and not tir_in.any()
    _out, tir_out = refract_rays(d, nrm, n_glass, 1.0)
    print(f"ガラス→空気 全反射のマスク : {tir_out.tolist()}  (60° だけ全反射)")
    assert tir_out.tolist() == [False, False, True]

    # --- 5) プリズムの分散 --------------------------------------------------
    lines = np.array([486.1, 587.6, 656.3])               # F / d / C 線
    dev = prism_min_deviation_deg(lines, 60.0, "N-BK7")
    print(f"最小偏角 F/d/C            : {np.round(dev, 3)}°  (短波長ほど大きく曲がる)")
    assert np.all(np.diff(dev) < 0.0) and abs(dev[1] - 38.6) < 0.3

    print(f"PASS: 垂直入射 {r0:.4f}・Brewster で p 偏光 0・全反射 1.0 厳密・"
          f"平板 {t_clear:.4f}=2n/(n²+1)・Snell 残差 1e-12 未満・分散 {dev[0] - dev[2]:.3f}° —— "
          "すべて閉じた式と公開値に一致")


if __name__ == "__main__":
    main()
