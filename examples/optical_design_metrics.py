# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""optical_design_metrics — 理想レンズ面と、PSF から読む設計の指標(囲みエネルギー・子午/球欠 MTF・スルーフォーカス MTF)。

    py -3.11 examples/optical_design_metrics.py

【この例が見せること】
逐次光学設計ソフトの定番を、Fullseye の op で一巡する(短い呼び出し例。PoC ではない)。
(1) 理想レンズ面: ``raytrace.lens_system([{"f": 50.0, "t": None, "ap": 2.5}])`` は薄肉レンズの法則を厳密に実行する。
    平行光が f に集まり、有限物体がガウスの結像公式の位置と倍率に結像する。収差が 0 なので PSF は Airy になる。
(2) ``encircled_energy`` / ``energy_radii``: その PSF の囲みエネルギー。第 1 暗環 1.2197 λN の中に 83.8 %(Born & Wolf)。
(3) ``mtf_tangential_sagittal``: 同じ PSF の子午/球欠 MTF は回折限界の閉形式と一致し、軸上では 2 本が重なる。
    絞った単レンズを 8 度の視野で見ると非点収差で 2 本が割れる。
(4) ``through_focus_mtf``: 像面を動かしたときの MTF(Hopkins の閉形式と照合)。
(5) ``with_aiming`` / ``ray_aiming`` / ``set_vignetting``: 実光線の照準とケラレ係数。三枚玉の軸上では近軸の入射瞳へ打つと瞳の縁
    217 本中 48 本が絞りで失われるが、絞りの点へ狙えば 0 本になる。ケラレ係数 VCY=0.3 は瞳の高さを 0.7 倍にし、
    ``set_vignetting`` は開口から係数を求める。

【真値】
理想レンズの焦点誤差(1e-12 mm 級)、結像公式 s' = f s/(s-f) と m = -s'/s、Airy の囲みエネルギー 83.8 %、
円形瞳の MTF の閉形式 (2/π)(arccos x − x √(1−x²))、絞り上の光線の位置(狙った点との差 1e-11 以内)、
ケラレ係数 1−VCY の瞳の高さ(0.7)。
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lensfile as LF  # noqa: E402
import lensimage as LI  # noqa: E402
import optics as O  # noqa: E402
import raytrace as RT  # noqa: E402


def main():
    # (1) 理想レンズ: f = 50 mm、半径 2.5 mm の絞り = f/10
    f = 50.0
    lens = RT.lens_system([{"f": f, "t": None, "ap": 2.5}], stop=0)
    para = RT.paraxial_trace(lens)
    spot = RT.spot_stats(lens)
    print("理想レンズ f=%.1f: efl=%.12f bfl=%.12f  スポット RMS=%.2e mm" % (f, para["efl"], para["bfl"], spot["rms_radius"]))
    assert abs(para["bfl"] - f) < 1e-12 and spot["rms_radius"] < 1e-12
    s = 200.0
    near = RT.lens_system([{"f": f, "t": None, "ap": 2.5}], stop=0, object_mm=s, field=2.0)
    p2 = RT.paraxial_trace(near)
    sp = f * s / (s - f)
    print("物体 %.0f mm: 像距離 %.9f (公式 %.9f)  倍率 %.9f (−s'/s = %.9f)"
          % (s, p2["image_mm"], sp, p2["magnification"], -sp / s))
    assert abs(p2["image_mm"] - sp) < 1e-9 and abs(p2["magnification"] + sp / s) < 1e-9

    # (2) 囲みエネルギー: 収差 0 の PSF = Airy。PSF は 1.5 um の画素に面積積分する
    pitch = 1.5
    psf = LI.psf_from_opd(lens, size=128, oversample=8, pixel_pitch_um=pitch)
    lam, N = lens["wavelength_um"], 10.0
    ee = O.encircled_energy(psf, pitch, samples=400, max_radius_um=6 * lam * N)
    ring = 1.2197 * lam * N
    e1 = float(np.interp(ring, ee[:, 0], ee[:, 1]))
    rad = O.energy_radii(psf, pitch, (0.5, 0.8, 0.9))
    print("第 1 暗環 r=%.3f um の囲みエネルギー %.2f %%(Airy 83.8 %%)  50/80/90 %% 半径 %s um"
          % (ring, 100 * e1, [round(v, 2) for v in rad["radius_um"]]))
    assert abs(e1 - 0.838) < 0.01
    # 四角のエネルギー: 同じ半幅の円を含むので、いつも囲みエネルギー以上
    sq = O.ensquared_energy(psf, pitch, samples=400, max_half_width_um=6 * lam * N)
    w = 5.0
    e_sq, e_ci = float(np.interp(w, sq[:, 0], sq[:, 1])), float(np.interp(w, ee[:, 0], ee[:, 1]))
    print("半幅 %.1f um の四角に %.2f %% / 同じ半径の円に %.2f %%" % (w, 100 * e_sq, 100 * e_ci))
    assert e_sq >= e_ci

    # (3) 子午/球欠 MTF: 回折限界の閉形式と、非点収差での分離
    fine = LI.psf_from_opd(lens, size=128, oversample=4)               # 点標本の細かい PSF(画素の開口を含めない)
    dx = lam * N * 127 / (127 * 4 + (127 * 4) % 2)
    m = O.mtf_tangential_sagittal(fine, dx)
    cut = 1e3 / (lam * N)
    x = m["tangential"][:, 0] / cut
    sel = (x > 0) & (x < 1)
    ref = (2 / math.pi) * (np.arccos(x[sel]) - x[sel] * np.sqrt(1 - x[sel] ** 2))
    err = float(np.max(np.abs(m["tangential"][sel, 1] - ref)))
    print("回折限界 MTF の閉形式との最大差 %.2e(カットオフ %.1f cycles/mm)" % (err, cut))
    assert err < 2e-3
    singlet = RT.lens_system([{"R": 51.68, "t": 5.0, "n": (1.5168, 64.17), "ap": 2.0},
                              {"R": "inf", "t": None, "n": 1.0}], stop=0)

    # (4) スルーフォーカス MTF(単レンズ、軸上と 8 度)
    for fld in (0.0, 8.0):
        r = LI.through_focus_mtf(singlet, field=fld, frequency_cpmm=[30.0], defocus_mm=[-0.5, 0.0, 0.5])
        print("単レンズ 視野 %.0f 度, 30 cycles/mm, 像面 -0.5/0/+0.5 mm: 子午 %s 球欠 %s"
              % (fld, np.round(r["tangential"][:, 0], 3).tolist(), np.round(r["sagittal"][:, 0], 3).tolist()))
        if fld == 0.0:
            assert np.max(np.abs(r["tangential"] - r["sagittal"])) < 1e-6        # 回転対称: 2 本が重なる
        else:
            assert np.max(np.abs(r["tangential"] - r["sagittal"])) > 0.05        # 非点収差で割れる

    # (5) 実光線の照準とケラレ係数(同梱の三枚玉。f ≈ 50 mm、f/5、視野 0 / 14 / 20 度)
    triplet = LF.lens_file_read(None)["system"]
    aimed = RT.with_aiming(triplet, "stop")                              # 以後の解析は光線を絞りの点へ狙う
    for fld in (0.0, 14.0, 20.0):
        old = RT.ray_aiming(triplet, field=fld, aim="paraxial")
        new = RT.ray_aiming(aimed, field=fld)
        so, sn = RT.spot_stats(triplet, field=fld), RT.spot_stats(aimed, field=fld)
        print("三枚玉 視野 %4.1f 度: 近軸の照準 %d/%d 本を絞りで失い RMS %.2f um → 実光線の照準 %d 本失い RMS %.2f um(狙いの残差 %.1e)"
              % (fld, old["n_lost"], old["n_rays"], 1e3 * so["rms_radius"], new["n_lost"], 1e3 * sn["rms_radius"],
                 new["max_residual"]))
        assert new["n_lost"] == 0 and new["max_residual"] < 1e-11
    assert RT.ray_aiming(triplet, field=0.0, aim="paraxial")["n_lost"] == 48
    cut = RT.ray_aiming(aimed, field=14.0, vignetting={"vcy": 0.3})
    ext = cut["stop_y"][1] - cut["stop_y"][0]
    print("ケラレ係数 VCY=0.3: 絞り上の瞳の高さは %.6f 倍(1 − VCY = 0.7)" % (ext / 2.0))
    assert abs(ext / 2.0 - 0.7) < 1e-9
    surf = [dict(s) for s in triplet["surfaces"]]
    for i, a in {0: 8.5, 1: 8.0, 2: 4.0, 4: 6.4, 5: 6.8}.items():       # 周辺の視野で光線を切るレンズ口径
        surf[i]["ap"] = a
    clipped = RT.lens_system(surf, stop=triplet["stop"], object_mm=triplet["object_mm"],
                             wavelength_um=triplet["wavelength_um"], image_mm=triplet["image_mm"])
    vig = RT.set_vignetting(clipped, fields=[0.0, 14.0, 20.0], mode="grid")
    four = RT.set_vignetting(clipped, fields=[0.0, 14.0, 20.0], mode="four")
    for r4, r in zip(four["vignetting"], vig["vignetting"]):
        print("  視野 %4.1f 度: 4 本の周辺光線 VDY=%+.4f VCX=%.4f VCY=%.4f / 格子 VDY=%+.4f VCX=%.4f VCY=%.4f"
              % (r["field"], r4["vdy"], r4["vcx"], r4["vcy"], r["vdy"], r["vcx"], r["vcy"]))
        assert RT.ray_aiming(vig, field=r["field"])["n_lost"] == 0
        assert r["vcy"] >= r4["vcy"] - 1e-12            # 格子の方が厳しい
    print("PASS")


if __name__ == "__main__":
    main()
