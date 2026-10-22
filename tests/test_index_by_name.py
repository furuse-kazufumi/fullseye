# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""屈折率を数で受けていた op が材料名も受ける(2026-10-15)+ (nd, vd) の Cauchy 近似の範囲の門。

外から持ち込む真値: N-BK7 の n_d = 1.5168(カタログ公表値)、水の n_d ≈ 1.3330(20 °C)、Brewster 角 atan(n)。
数で渡したときの値は以前と 1 ビットも変わらないこと(後方互換)も門にする。
"""
from __future__ import annotations

import math

import numpy as np
import pytest

import deflectometry as D
import lensopt as LO
import materials as M
import raytrace as RT
import sfpolar as SP
import surfacelib as SL


# --------------------------------------------------------------------------- #
# materials._index_of                                                           #
# --------------------------------------------------------------------------- #
def test_index_of_reads_the_table_and_passes_numbers_through():
    assert abs(M._index_of("N-BK7", "t") - 1.5168) < 1e-4                 # カタログの n_d
    assert abs(M._index_of("WATER", "t") - 1.3330) < 1e-3
    assert M._index_of(1.5, "t") == 1.5 and M._index_of((1.5168, 64.17), "t") == (1.5168, 64.17)
    assert abs(M._index_of("N-BK7", "t", wavelength_nm=1000.0) - 1.5075) < 1e-3
    with pytest.raises(ValueError, match="metal"):
        M._index_of("AL", "t")
    with pytest.raises(ValueError, match="absorbs"):
        M._index_of("SI", "t")                                            # Si は d 線で k = 0.02
    with pytest.raises(ValueError, match="unknown material"):
        M._index_of("UNOBTAINIUM", "t")


# --------------------------------------------------------------------------- #
# 4 つの族                                                                       #
# --------------------------------------------------------------------------- #
def test_sfpolar_takes_a_material_name_and_numbers_are_unchanged():
    z = np.linspace(0.0, 89.0, 90)
    nd = M._index_of("N-BK7", "t")
    for model in ("specular", "diffuse"):
        a = SP.sfp_dolp_model(z, "N-BK7", model=model)
        b = SP.sfp_dolp_model(z, nd, model=model)
        assert np.array_equal(a, b)
    peak = SP.sfp_dolp_model(math.degrees(math.atan(nd)), "N-BK7")
    assert abs(float(peak) - 1.0) < 1e-12                                # Brewster 角で DoLP = 1
    r = SP.dolp_to_zenith(0.2, "WATER", model="diffuse")
    assert r["refractive_index"] == M._index_of("WATER", "t")
    with pytest.raises(ValueError, match="metal"):
        SP.sfp_dolp_model(30.0, "AG")


def test_deflectometry_back_reflection_takes_a_material_name():
    h = np.zeros((24, 24))
    rig = D.deflectometry_rig(field_mm=10.0)
    a = D.deflectometry_render(h, rig, back_thickness_mm=1.0, refractive_index="N-BK7")
    b = D.deflectometry_render(h, rig, back_thickness_mm=1.0, refractive_index=M._index_of("N-BK7", "t"))
    assert len(a) == len(b) >= 1
    assert all(np.array_equal(x, y) for x, y in zip(a, b))
    with pytest.raises(ValueError, match="metal"):
        D.deflectometry_render(h, rig, back_thickness_mm=1.0, refractive_index="CU")


def test_bend_singlet_takes_a_glass_name():
    a = LO.bend_singlet(100.0, "N-BK7")
    b = LO.bend_singlet(100.0, RT.refractive_index("N-BK7"))
    assert a["R1"] == pytest.approx(b["R1"], rel=1e-12) and a["R2"] == pytest.approx(b["R2"], rel=1e-12)


def test_surfacelib_index_arguments_take_material_names():
    N = np.dstack([np.zeros((3, 3)), np.zeros((3, 3)), np.ones((3, 3))])
    base = np.array([0.4, 0.3, 0.2])
    nw, npm, nb = M._index_of("WATER", "t"), M._index_of("PMMA", "t"), M._index_of("N-BK7", "t")
    assert np.array_equal(SL.wetness(base, 1.0, "WATER"), SL.wetness(base, 1.0, nw))
    assert np.array_equal(SL.clearcoat_shade(base, N, ior="PMMA"), SL.clearcoat_shade(base, N, ior=npm))
    a = SL.rough_transmission(np.array([1.0, 0.7]), 0.3, 1.0, "N-BK7")
    b = SL.rough_transmission(np.array([1.0, 0.7]), 0.3, 1.0, nb)
    assert len(a) == len(b) == 2
    assert all(np.array_equal(x, y) for x, y in zip(a, b))
    assert np.array_equal(SL.wetness(base, 1.0, 1.33), SL.wetness(base, 1.0, 1.33))   # 数はそのまま
    with pytest.raises(ValueError, match="metal"):
        SL.wetness(base, 1.0, "AU")


# --------------------------------------------------------------------------- #
# raytrace.refractive_index の (nd, vd) 近似の範囲                                 #
# --------------------------------------------------------------------------- #
def test_nd_vd_cauchy_is_refused_outside_its_declared_range():
    nd, vd = 1.5168, 64.17
    g = RT.glass(nd, vd)
    for wl in (0.40, RT.WL_F, RT.WL_D, RT.WL_C, 0.80):
        assert RT.refractive_index((nd, vd), wl) == float(g["A"] + g["B"] / wl ** 2)   # 範囲内は以前の値のまま
        assert RT.refractive_index(g, wl) == float(g["A"] + g["B"] / wl ** 2)
    assert abs(RT.refractive_index((nd, vd)) - nd) < 1e-12
    for wl in (0.365, 0.39, 0.81, 1.064, 1.55):
        with pytest.raises(ValueError, match="Cauchy range"):
            RT.refractive_index((nd, vd), wl)
        with pytest.raises(ValueError, match="Cauchy range"):
            RT.refractive_index(g, wl)
    assert abs(RT.refractive_index("N-BK7", 1.55) - 1.5007) < 1e-3       # 名前で引けば赤外も正しい
    worst = max(abs(RT.refractive_index((nd, vd), w) - RT.refractive_index("N-BK7", w))
                for w in np.linspace(0.40, 0.80, 41))
    assert worst < 5e-4                                                    # 宣言した範囲での食い違い(docstring の数字)
