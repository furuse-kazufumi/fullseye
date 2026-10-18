# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""illumdesign の照明系(ケーラー / クリティカル)と同軸落射の門: 閉形式・壊して確かめる探針・fail-closed。"""
from __future__ import annotations

import copy
import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import illumdesign as ID  # noqa: E402


def _filament(n=64, periods=4):
    """コイルの縞(明 1.0 / 暗 0.3)の光源の放射輝度。"""
    xx = np.arange(n)[None, :] * np.ones((n, 1))
    return 0.3 + 0.7 * (np.sin(xx / n * 2.0 * math.pi * periods) > 0.0)


def _inner(img, frac=0.5):
    H, W = img.shape
    h, w = int(H * frac / 2), int(W * frac / 2)
    return img[H // 2 - h:H // 2 + h + 1, W // 2 - w:W // 2 + w + 1]


# --------------------------------------------------------------------------- #
# 共役の帳簿                                                                    #
# --------------------------------------------------------------------------- #
def test_kohler_images_the_field_stop_and_critical_images_the_source():
    K = ID.illumination_train("kohler")
    C = ID.illumination_train("critical")
    assert abs(K["field_stop_to_specimen"][0][1]) < 1e-9 and K["source_magnification"] is None
    assert abs(C["source_to_specimen"][0][1]) < 1e-9 and C["field_stop_magnification"] is None
    # ケーラー: 光源は開口絞り(コンデンサの前側焦点面)に結像 → 標本では無限遠(source→specimen の D = 0)
    assert abs(K["source_to_specimen"][1][1]) < 1e-12
    # 視野の直径 = 視野絞り × |M|(薄肉レンズの閉形式: M = −v / L)
    s1, fc, fk = 30.0, 20.0, 10.0
    s1p = 1.0 / (1.0 / fc - 1.0 / s1)
    Lobj = s1p + fk
    v = 1.0 / (1.0 / fk - 1.0 / Lobj)
    assert abs(K["field_stop_magnification"] - (-v / Lobj)) < 1e-12
    assert abs(K["field_diameter_mm"] - 6.0 * v / Lobj) < 1e-12


def test_kohler_na_is_the_smaller_of_aperture_and_source_image():
    # 光源の像(半径 1 mm × 2 = 2 mm)が開口絞り(半径 3 mm)より小さい → NA = 2 / f_cond
    K = ID.illumination_train("kohler")
    assert abs(K["illumination_na"] - 2.0 / 10.0) < 1e-9
    K2 = ID.illumination_train("kohler", source_mm=8.0, aperture_stop_mm=3.0)
    assert abs(K2["illumination_na"] - 1.5 / 10.0) < 1e-9                               # 開口絞りで決まる


# --------------------------------------------------------------------------- #
# 視野の均一度                                                                  #
# --------------------------------------------------------------------------- #
def test_kohler_hides_the_filament_critical_copies_it():
    fil = _filament()
    K = ID.illumination_train("kohler", source_mm=8.0, aperture_stop_mm=3.0)
    C = ID.illumination_train("critical")
    Ek = ID.illumination_field(K, fil, shape=(65, 65), n_pupil=24)
    Ec = ID.illumination_field(C, fil, shape=(65, 65), n_pupil=24)
    ck = _inner(Ek)
    cc = _inner(Ec)
    assert ck.std() / ck.mean() < 1e-9                                                  # ケーラー: 縞は写らない
    assert cc.std() / cc.mean() > 0.2                                                   # クリティカル: 写る
    # クリティカルの像 = 光源の地図を |M| 倍に引き伸ばしたもの(倒立)。行の中央の断面で相関をとる
    M = C["source_magnification"]
    half = 0.65 * C["field_diameter_mm"]
    xs = np.linspace(-half, half, 65)
    xsrc = xs / M
    r = 0.5 * C["source_mm"]
    inside = np.abs(xsrc) < 0.8 * r
    u = (xsrc[inside] + r) / (2 * r) * (fil.shape[1] - 1)
    ref = np.interp(u, np.arange(fil.shape[1]), fil[fil.shape[0] // 2])
    got = Ec[32, inside]
    assert np.corrcoef(ref, got)[0, 1] > 0.95


def test_uniform_source_gives_L_pi_NA_squared():
    K = ID.illumination_train("kohler")
    E = ID.illumination_field(K, None, shape=(9, 9), n_pupil=96)
    na = K["illumination_na"]
    assert abs(E[4, 4] / (math.pi * na * na) - 1.0) < 0.01


def test_kohler_field_edge_sits_at_field_stop_times_magnification():
    K = ID.illumination_train("kohler")
    E = ID.illumination_field(K, None, shape=(3, 201), n_pupil=32, field_mm=1.0)
    row = E[1]
    xs = np.linspace(-1.0, 1.0, 201)
    half = 0.5 * row.max()
    right = xs[100:][np.argmax(row[100:] < half)]
    assert abs(right - 0.5 * K["field_diameter_mm"]) < 2.0 * (xs[1] - xs[0])


def test_probe_moving_the_condenser_breaks_kohler_uniformity():
    """壊して確かめる: 開口絞りをコンデンサの前側焦点面から外すと、光源の縞が視野に漏れる。"""
    fil = _filament()
    K = ID.illumination_train("kohler", source_mm=8.0, aperture_stop_mm=3.0)
    bad = copy.deepcopy(K)
    for e in bad["elements"]:
        if e["name"] in ("condenser", "specimen"):
            e["z_mm"] += 4.0
    E = ID.illumination_field(bad, fil, shape=(65, 65), n_pupil=24, field_mm=0.65)
    c = _inner(E)
    assert c.std() / c.mean() > 1e-3


# --------------------------------------------------------------------------- #
# 同軸落射                                                                      #
# --------------------------------------------------------------------------- #
def test_round_trip_is_RT_and_peaks_at_quarter():
    C = ID.coaxial_illumination(reflectance=0.5, absorptance=0.0)
    assert C["round_trip"] == 0.25 and C["max_round_trip"] == 0.25 and C["optimum_reflectance"] == 0.5
    Rs = np.linspace(0.05, 0.9, 87)
    rt = [ID.coaxial_illumination(reflectance=float(r), absorptance=0.06)["round_trip"] for r in Rs]
    assert abs(Rs[int(np.argmax(rt))] - 0.47) < 0.011                                    # (1 − A)/2
    assert max(rt) <= (1 - 0.06) ** 2 / 4 + 1e-12


def test_default_round_trip_matches_the_optscene_coaxial_light():
    """optscene の同軸の光(splitter_reflectance 0.5 / splitter_transmittance 0.5、往復 1/4)と同じ値を返す。"""
    C = ID.coaxial_illumination()
    assert C["round_trip"] == 0.25
    assert (C["splitter_reflectance"], C["splitter_transmittance"]) == (0.5, 0.5)
    assert C["splitter_reflectance"] * C["splitter_transmittance"] == C["round_trip"]
    dark = ID.coaxial_illumination(absorptance=0.5)                                     # T = 0: 予算で暗い
    assert dark["round_trip"] == 0.0 and np.max(dark["image"]) == 0.0 and dark["uniformity"] is None


def test_mirror_part_images_the_panel_scaled_by_one_plus_h_over_H():
    n = 40
    yy, xx = np.mgrid[0:n, 0:n]
    panel = 0.5 + 0.5 * (xx / (n - 1))                                                   # 左 0.5 → 右 1.0 の傾斜
    C = ID.coaxial_illumination(reflectance=0.5, absorptance=0.0, panel_mm=60.0, panel_distance_mm=60.0,
                                camera_distance_mm=200.0, field_mm=20.0, panel_radiance=panel, shape=(41, 41))
    s = 1.0 + 60.0 / 200.0
    assert C["panel_scale"] == pytest.approx(s)
    xs = np.linspace(-20.0, 20.0, 41)
    ref = 0.25 * (0.5 + 0.5 * (xs * s / 60.0 + 0.5))
    assert np.max(np.abs(C["image"][20] - ref)) < 1e-9
    T = ID.coaxial_illumination(panel_radiance=panel, telecentric=True, reflectance=0.5, absorptance=0.0,
                                shape=(41, 41))
    assert T["panel_scale"] == 1.0
    assert np.max(np.abs(T["image"][20] - 0.25 * (0.5 + 0.5 * (xs / 60.0 + 0.5)))) < 1e-9


def test_vignetting_edge_closed_form():
    C = ID.coaxial_illumination(panel_mm=30.0, field_mm=20.0, shape=(3, 401))
    xs = np.linspace(-20.0, 20.0, 401)
    lit = xs[C["image"][1] > 0]
    assert abs(lit.max() - C["vignetting_edge_mm"]) <= (xs[1] - xs[0])
    assert C["vignetting_edge_mm"] == pytest.approx(15.0 / 1.3)
    assert C["uniformity"]["cv"] > 0.3                                                 # 視野の端が暗い


def test_matte_centre_matches_the_rectangle_closed_form():
    C = ID.coaxial_illumination(part="matte", shape=(5, 5), n_panel=200, field_mm=1.0)
    assert abs(C["image"][2, 2] / C["matte_centre_closed"] - 1.0) < 2e-3


def test_ghost_ratio_and_offset():
    C = ID.coaxial_illumination(reflectance=0.5, absorptance=0.0, back_reflectance=0.04, plate_thickness_mm=2.0,
                                plate_index=1.5)
    assert C["ghost_ratio"] == pytest.approx(0.25 * 0.04 / 0.5)
    tr = math.asin(math.sin(math.radians(45)) / 1.5)
    assert C["ghost_offset_mm"] == pytest.approx(2 * 2.0 * math.tan(tr) * math.cos(math.radians(45)))


# --------------------------------------------------------------------------- #
# fail-closed                                                                  #
# --------------------------------------------------------------------------- #
def test_fail_closed():
    with pytest.raises(ValueError, match="kind"):
        ID.illumination_train("nelson")
    with pytest.raises(ValueError, match="real source image"):
        ID.illumination_train(source_distance_mm=15.0)
    for bad in ("6", True, float("nan"), -1.0):
        with pytest.raises(ValueError):
            ID.illumination_train(field_stop_mm=bad)
    with pytest.raises(ValueError):
        ID.illumination_field({"elements": []})
    K = ID.illumination_train()
    with pytest.raises(ValueError, match="non-negative"):
        ID.illumination_field(K, -np.ones((4, 4)))
    with pytest.raises(ValueError, match="exceeds"):
        ID.illumination_field(K, shape=(4096, 4096), n_pupil=64)
    with pytest.raises(ValueError, match="<= 1"):
        ID.coaxial_illumination(reflectance=0.7, absorptance=0.4)
    with pytest.raises(ValueError, match="closer"):
        ID.coaxial_illumination(panel_distance_mm=300.0)
    with pytest.raises(ValueError, match="part"):
        ID.coaxial_illumination(part="glossy")
    with pytest.raises(ValueError, match="telecentric"):
        ID.coaxial_illumination(telecentric=1)
