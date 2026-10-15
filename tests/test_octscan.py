# -*- coding: utf-8 -*-
"""octscan(光干渉断層、2026-10-15)の門。

閉形式に対して: 軸分解能 (2 ln 2/π) λ0²/Δλ、深さ範囲 λ0²/(4δλ)、roll-off(画素の箱の |sinc| × ガウス、
波長掃引は線幅のガウス)、ショット雑音律の SNR、分散の広がり √(1 + σ⁴φ₂²)、直交の組の鏡像 tan(δ/2)、
横の点像 √(2 ln 2)·w(z) と共焦点の結合 (1 + u²)^(−1/2) / (−1/4)。
合成に対して: 群屈折率で割った厚さが真値、位相屈折率なら t·n_g/n、折り返し 2 z_max − z。
実測(data/oct_real、CC BY 4.0)に対して: ガラス板の点像の幅、透明層の厚さ(論文の OCT と 2 µm)。
fail-closed: 印の違う表・単調でない k・等間隔でない k・薄すぎる層・散乱で立たない下の面。
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import octscan as O  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SD = {"center_nm": 840.0, "bandwidth_nm": 50.0, "n_pixels": 1024}
PHOT = {"photons_ref_per_pixel": 2e4, "photons_mirror_per_pixel": 1e6}


def _mirror(z, n2=1.05):
    return {"layers": [{"material": 1.0, "thickness_um": 10.0}], "substrate": {"n": n2, "n_group": n2},
            "surface_um": z - 10.0}


def _fwhm(z, y, zmin=20.0):
    y = np.where(z > zmin, y, 0.0)
    i = int(np.argmax(y))
    h = y[i] / 2
    lft, rgt = i, i
    while y[lft] > h:
        lft -= 1
    while y[rgt] > h:
        rgt += 1
    zl = np.interp(h, [y[lft], y[lft + 1]], [z[lft], z[lft + 1]])
    zr = np.interp(h, [y[rgt], y[rgt - 1]], [z[rgt], z[rgt - 1]])
    return zr - zl, z[i]


# --------------------------------------------------------------------------- #
# 閉形式                                                                         #
# --------------------------------------------------------------------------- #
def test_design_closed_forms():
    d = O.oct_design(840.0, 50.0, 2048, grid="k", beam_waist_um=6.0, n_group=1.5)
    assert d["axial_resolution_air_um"] == pytest.approx(2 * math.log(2) / math.pi * 0.84 ** 2 / 0.05, rel=1e-12)
    assert d["axial_resolution_um"] == pytest.approx(d["axial_resolution_air_um"] / 1.5, rel=1e-12)
    assert d["depth_range_air_um"] == pytest.approx(math.pi / (2 * d["dk_pixel"]), rel=1e-12)
    # 深さ範囲の端の roll-off = |sinc(π/2)| × exp(−2σ²z²)
    sig = d["sigma_k_rolloff"]
    z = d["depth_range_air_um"]
    assert d["rolloff_at_depth_range"] == pytest.approx(2 / math.pi * math.exp(-2 * sig ** 2 * z ** 2), rel=1e-9)
    assert d["lateral_resolution_um"] == 12.0
    assert d["depth_of_focus_um"] == pytest.approx(math.pi * 12.0 ** 2 * 1.5 / (2 * 0.84), rel=1e-12)
    # 焦点距離とビーム径から: Δx = (4λ/π)(f/d)
    d2 = O.oct_design(focal_mm=30.0, beam_diameter_mm=2.5)
    assert d2["lateral_resolution_um"] == pytest.approx(4 * 0.84 / math.pi * 30.0 / 2.5, rel=1e-12)


def test_swept_source_6db_depth_is_ln2_lambda2_over_pi_linewidth():
    d = O.oct_design(1310.0, 100.0, 2048, mode="ss", linewidth_nm=0.5)
    assert d["rolloff_6db_air_um"] == pytest.approx(math.log(2) / math.pi * 1.31 ** 2 / 0.0005, rel=0.01)


def test_dispersion_broadening_matches_simulation_and_compensation_restores():
    d = O.oct_design(grid="k", **SD)
    for L in (5.0, 15.0):
        b = O.oct_dispersion_broadening("SILICA", L, 840.0, 50.0)
        it = O.oct_interferogram(_mirror(300.0), grid="k", noise=False, mismatch_material="SILICA",
                                 mismatch_length_mm=L, **SD, **PHOT)
        a = O.oct_ascan(it, window="none", zero_pad=16)
        w, _ = _fwhm(a["z_um"], a["amplitude"])
        assert w / d["axial_resolution_air_um"] == pytest.approx(b["broadening"], rel=0.005)
        c = O.oct_ascan(it, window="none", zero_pad=16, a2=b["a2"], a3=b["a3"], k_center=b["k_center"])
        assert _fwhm(c["z_um"], c["amplitude"])[0] == pytest.approx(d["axial_resolution_air_um"], rel=0.01)
        m = O.oct_dispersion_estimate(it, method="mirror")
        c2 = O.oct_ascan(it, window="none", zero_pad=16, a2=m["a2"], a3=m["a3"], k_center=m["k_center"])
        assert _fwhm(c2["z_um"], c2["amplitude"])[0] == pytest.approx(d["axial_resolution_air_um"], rel=0.02)
    assert 25.0 < O.oct_dispersion_broadening("SILICA", 1.0)["gvd_fs2_per_mm"] < 45.0   # 溶融石英 840 nm ≈ 33


# --------------------------------------------------------------------------- #
# 合成                                                                           #
# --------------------------------------------------------------------------- #
def test_group_index_gives_the_physical_thickness_and_phase_index_does_not():
    film = {"layers": [{"material": "PMMA", "thickness_um": 25.0}, {"material": "POLYCARBONATE", "thickness_um": 40.0}],
            "substrate": {"n": 1.51, "n_group": 1.53}, "surface_um": 300.0}
    it = O.oct_interferogram(film, grid="k", noise=False, **SD, **PHOT)
    a = O.oct_ascan(it, window="hann", zero_pad=8)
    L = O.oct_layer_thickness(a, n_group=["PMMA", "POLYCARBONATE"], n_interfaces=3, z_range_um=(200, 500))
    np.testing.assert_allclose(L["thickness_um"], [25.0, 40.0], atol=0.05)
    # 真値の群遅延(interfaces)と A スキャンの界面の位置
    np.testing.assert_allclose(L["z_opt_um"], [f["group_delay_um"] for f in it["interfaces"]], atol=0.05)


def test_snr_matches_shot_noise_closed_form_on_a_k_linear_spectrometer():
    R = ((1 - 1.02) / 2.02) ** 2
    d = O.oct_design(grid="k", reflectivity=R, photons_mirror_per_pixel=PHOT["photons_mirror_per_pixel"],
                     photons_ref_per_pixel=PHOT["photons_ref_per_pixel"], **SD)
    ro = float(np.interp(400.0, d["rolloff"][:, 0], d["rolloff"][:, 1]))
    m = [O.oct_ascan(O.oct_interferogram(_mirror(400.0, 1.02), grid="k", seed=s, **SD, **PHOT), window="hann",
                     zero_pad=4)["snr_db"] for s in range(4)]
    assert np.mean(m) == pytest.approx(d["snr_db"] + 20 * math.log10(ro), abs=0.4)


def test_klinearize_none_broadens_with_depth_and_cubic_does_not():
    ws = []
    for z in (300.0, 900.0):
        it = O.oct_interferogram(_mirror(z), noise=False, **SD, **PHOT)
        ok = O.oct_ascan(O.oct_k_linearize(it), window="hann", zero_pad=8)
        bad = O.oct_ascan(O.oct_k_linearize(it, method="none"), window="hann", zero_pad=8)
        ws.append((_fwhm(ok["z_um"], ok["amplitude"])[0], _fwhm(bad["z_um"], bad["amplitude"])[0]))
    assert ws[0][0] == pytest.approx(ws[1][0], rel=0.01)
    assert ws[1][1] > 2.5 * ws[0][1] > 2.5 * ws[0][0]


def test_swept_source_nonlinearity_needs_the_k_clock():
    it = O.oct_interferogram(_mirror(600.0), center_nm=1310.0, bandwidth_nm=100.0, mode="ss", sweep_nonlinearity=0.05,
                             noise=False, n_pixels=1024, **PHOT)
    good = O.oct_ascan(O.oct_k_linearize(it), window="none", zero_pad=8)
    k = it["k_rad_per_um"]
    bad = O.oct_ascan(O.oct_k_linearize(it, k_calibration=np.linspace(k[0], k[-1], k.size)), window="none", zero_pad=8)
    d = O.oct_design(1310.0, 100.0, 1024, mode="ss")
    assert _fwhm(good["z_um"], good["amplitude"])[0] == pytest.approx(d["axial_resolution_air_um"], rel=0.01)
    assert _fwhm(bad["z_um"], bad["amplitude"])[0] > 2 * d["axial_resolution_air_um"]


def test_mirror_image_quadrature_and_folding():
    it0 = O.oct_interferogram(_mirror(-250.0), grid="k", noise=False, **SD, **PHOT)
    a = O.oct_ascan(it0, window="hann", zero_pad=4)
    assert _fwhm(a["z_um"], a["amplitude"])[1] == pytest.approx(250.0, abs=0.5)     # 鏡像
    for dphi in (0.05, 0.2):
        itq = O.oct_interferogram(_mirror(-250.0), grid="k", noise=False, reference_phase_rad=math.pi / 2 + dphi,
                                  **SD, **PHOT)
        q = O.oct_ascan(it0, quadrature=itq, window="hann", zero_pad=4)
        z, y = q["z_um"], q["amplitude"]
        assert y[z < -20].max() > y[z > 20].max()                                     # 本物は負の側
        assert 20 * math.log10(y[z > 20].max() / y[z < -20].max()) == pytest.approx(
            20 * math.log10(math.tan(dphi / 2)), abs=0.1)
    zm = O.oct_design(grid="k", **SD)["depth_range_air_um"]
    f = O.oct_ascan(O.oct_interferogram(_mirror(zm + 100.0), grid="k", noise=False, **SD, **PHOT), window="hann",
                    zero_pad=4)
    assert _fwhm(f["z_um"], f["amplitude"])[1] == pytest.approx(zm - 100.0, abs=1.0)


def test_autocorrelation_ghost_at_group_path_and_removed_by_sample_spectrum():
    film = {"layers": [{"material": "PMMA", "thickness_um": 60.0}], "substrate": {"n": 1.70, "n_group": 1.74},
            "surface_um": 400.0}
    it = O.oct_interferogram(film, grid="k", noise=False, **SD, photons_ref_per_pixel=2e4, photons_mirror_per_pixel=5e5)
    ghost = 60.0 * O.oct_dispersion_broadening("PMMA", 0.0)["group_index"]
    a = O.oct_ascan(it, window="hann", zero_pad=8)
    b = O.oct_ascan(it, window="hann", zero_pad=8, dc="reference+sample")
    w = np.abs(a["z_um"] - ghost) < 4
    assert abs(a["z_um"][w][np.argmax(a["amplitude"][w])] - ghost) < 1.0
    assert a["amplitude"][w].max() > 1e3 * b["amplitude"][w].max()


def test_thin_layer_is_refused_below_1p4_psf():
    ng = O.oct_dispersion_broadening("PMMA", 0.0)["group_index"]
    for t, ok in ((4.0, False), (9.0, True)):
        s = {"layers": [{"material": "PMMA", "thickness_um": t}], "substrate": {"n": 1.60, "n_group": 1.63},
             "surface_um": 300.0}
        a = O.oct_ascan(O.oct_interferogram(s, grid="k", noise=False, **SD, **PHOT), window="hann", zero_pad=8)
        lim = 1.4 * a["psf_fwhm_um"] / ng
        assert (t > lim) == ok
        if ok:
            L = O.oct_layer_thickness(a, n_group=["PMMA"], n_interfaces=2, z_range_um=(200, 450))
            assert L["thickness_um"][0] == pytest.approx(t, rel=0.015)
        else:
            with pytest.raises(ValueError):
                O.oct_layer_thickness(a, n_group=["PMMA"], n_interfaces=2, z_range_um=(200, 450))


def test_attenuation_lowers_the_bottom_interface_by_beer_lambert():
    out = []
    for mu in (0.0, 50.0):
        s = {"layers": [{"material": {"n": 1.55, "n_group": 1.58}, "thickness_um": 50.0, "attenuation_per_mm": mu}],
             "substrate": {"n": 1.75, "n_group": 1.80}, "surface_um": 200.0}
        a = O.oct_ascan(O.oct_interferogram(s, grid="k", noise=False, **SD, **PHOT), window="hann", zero_pad=4)
        zb = 200.0 + 1.58 * 50.0
        out.append(a["amplitude"][np.abs(a["z_um"] - zb) < 3].max())
    assert out[1] / out[0] == pytest.approx(math.exp(-50.0 * 0.05), rel=0.01)


def test_bscan_lateral_psf_and_defocus():
    w0 = 5.0
    zr = math.pi * w0 ** 2 * 1.5 / 0.84
    res = {}
    for key, zf, ill in (("focus", 150.0, "point"), ("point", 150.0 + zr, "point"), ("line", 150.0 + zr, "line")):
        s = {"materials": ["air", {"n": 1.5, "n_group": 1.5}], "interfaces_um": [np.array([50.0, 50.0])],
             "surface_um": 100.0, "points": [{"x_um": 100.0, "z_um": 150.0, "amplitude": 0.01}]}
        b = O.oct_bscan_simulate(s, width_um=200.0, n_columns=201, n_pixels=512, beam_waist_um=w0, focus_um=zf,
                                 illumination=ill, noise=False, **PHOT)
        bs = O.oct_bscan(b, dc="reference+sample", zero_pad=4)
        im = 10 ** (bs["image_db"] / 20)
        row = int(np.argmax(im[:, 100] * (bs["z_um"] > 200.0)))
        prof = im[row]
        x = b["x_um"]
        h = prof.max() / 2
        above = np.flatnonzero(prof >= h)
        lo, hi = above[0], above[-1]
        wl = np.interp(h, [prof[hi + 1], prof[hi]], [x[hi + 1], x[hi]]) - np.interp(h, [prof[lo - 1], prof[lo]],
                                                                                       [x[lo - 1], x[lo]])
        res[key] = (wl, prof.max())
    assert res["focus"][0] == pytest.approx(math.sqrt(2 * math.log(2)) * w0, rel=0.03)
    assert res["point"][0] == pytest.approx(math.sqrt(2 * math.log(2)) * w0 * math.sqrt(2), rel=0.03)
    assert res["point"][1] / res["focus"][1] == pytest.approx(2 ** -0.5, rel=0.005)
    assert res["line"][1] / res["focus"][1] == pytest.approx(2 ** -0.25, rel=0.005)


def test_boundaries_follow_lines_and_reference_mode():
    H, W = 120, 60
    yy = np.arange(H)[:, None]
    top = 30 + 0.1 * np.arange(W)
    bot = top + 25
    img = 5 * np.exp(-(yy - top) ** 2 / 2) + 3 * np.exp(-(yy - bot) ** 2 / 2) + 0.3 * np.random.default_rng(0).random((H, W))
    r = O.oct_bscan_boundaries(img, 2, um_per_px=2.0, n_group=1.25)
    np.testing.assert_allclose(r["rows"][0], top, atol=0.3)
    np.testing.assert_allclose(r["rows"][1], bot, atol=0.3)
    np.testing.assert_allclose(r["thickness_um"][0], 25 * 2.0 / 1.25, atol=0.6)
    r2 = O.oct_bscan_boundaries(img, 1, reference_rows=r["rows"][0], offset_px=(10, 40), jump_penalty=1.0)
    np.testing.assert_allclose(r2["rows"][1], bot, atol=0.3)
    with pytest.raises(ValueError):
        O.oct_bscan_boundaries(np.ones((20, 20)))


# --------------------------------------------------------------------------- #
# 実測(CC BY 4.0)                                                               #
# --------------------------------------------------------------------------- #
REAL = os.path.join(ROOT, "data", "oct_real", "paint_sdoct_cc_by.npz")


@pytest.mark.skipif(not os.path.exists(REAL), reason="data/oct_real が無い")
def test_real_paint_clear_coat_matches_the_paper():
    d = np.load(REAL)
    t = O.oct_from_spectra(d["spectra_III-B"].astype(float), d["wavelength_nm"], center_nm=840.0, bandwidth_nm=47.0)
    b = O.oct_bscan(t, dc="smooth", window="hann", zero_pad=2)
    dz = b["dz_um"]
    s = O.oct_bscan_boundaries(b["image_db"][:int(600 / dz)], 1, um_per_px=dz, top_px=int(15 / dz),
                               max_jump_px=3)["rows"][0]
    fl = O.oct_bscan_flatten(b, s, above_um=20.0, below_um=300.0)
    z2 = O.oct_layer_thickness(fl, n_interfaces=1, z_range_um=(50.0, 320.0))["z_opt_um"][0]
    assert (z2 - 20.0) / 1.56 == pytest.approx(99.8, abs=1.5)          # 論文の表 1 の OCT(推定の対応)
    g = d["glass_pair"].astype(float)
    a = O.oct_ascan(O.oct_k_linearize(O.oct_from_spectra(g[1], d["wavelength_nm"], center_nm=840.0,
                                                         bandwidth_nm=47.0)), window="none", dc="smooth", zero_pad=16)
    assert 4.3 < _fwhm(a["z_um"], a["amplitude"], 15.0)[0] < 5.1               # 公称のガウスの 6.6 µm より細い


# --------------------------------------------------------------------------- #
# fail-closed                                                                    #
# --------------------------------------------------------------------------- #
def test_fail_closed():
    it = O.oct_interferogram(_mirror(300.0), noise=False, **SD, **PHOT)
    with pytest.raises(ValueError):
        O.oct_ascan(it)                                        # λ 等間隔のまま(k 線形化していない)
    with pytest.raises(ValueError):
        O.oct_ascan({"kind": "something_else"})
    with pytest.raises(ValueError):
        O.oct_layer_thickness(O.oct_k_linearize(it))           # A スキャンでない表
    with pytest.raises(ValueError):
        O.oct_interferogram(_mirror(300.0), sweep_nonlinearity=0.1)        # 分光器に掃引の非線形
    with pytest.raises(ValueError):
        O.oct_interferogram(_mirror(300.0), mode="ss", sweep_nonlinearity=1.0)
    with pytest.raises(ValueError):
        O.oct_interferogram({"layers": [{"material": "NO_SUCH_GLASS", "thickness_um": 5.0}]})
    with pytest.raises(ValueError):
        O.oct_interferogram({"layers": [{"material": "PMMA", "thickness_um": 5.0}]}, center_nm=1550.0)  # 表の外
    with pytest.raises(ValueError):
        O.oct_from_spectra(np.ones((3, 40)), np.linspace(800, 900, 41))
    with pytest.raises(ValueError):
        O.oct_from_spectra(np.ones(40), np.r_[np.linspace(800, 850, 20), np.linspace(840, 900, 20)])
    with pytest.raises(ValueError):
        O.oct_bscan_simulate({"materials": ["air", 1.5], "interfaces_um": [np.zeros(3), np.ones(3)]})
    q = O.oct_ascan(O.oct_k_linearize(it), quadrature=O.oct_k_linearize(it))
    with pytest.raises(ValueError):
        O.oct_layer_thickness(q)                               # 両側の A スキャン
    with pytest.raises(ValueError):
        O.oct_k_linearize(it, method="spline5")


def test_registry_and_adapter():
    import opsoptics
    assert len(opsoptics.list_ops("oct")) == 13
    assert not [n for n in opsoptics.list_ops("oct") if opsoptics.get(n) is None]
    b = O.oct_bscan_simulate(n_columns=8, n_pixels=256, width_um=100.0)
    img = opsoptics.call("oct_bscan", b)
    assert isinstance(img, np.ndarray) and img.ndim == 2 and np.all(np.isfinite(img))


def test_threshold_knobs_change_the_verdict_on_a_boundary_ascan():
    """拒否のしきい値 4 本は、境界の入力で 2 点振ると判定が変わる(探針 ledger_contracts._oct_edge_ascan と同じ入力)。"""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import ledger_contracts as LC
    a = LC._oct_edge_ascan()
    base = O.oct_layer_thickness(a)
    n0 = base["z_opt_um"].size

    def n(**kw):
        return O.oct_layer_thickness(a, **kw)["z_opt_um"].size
    assert n(min_snr_db=6.0) > n0 > n(min_snr_db=24.0)                  # 雑音の床すれすれの界面
    assert n(dynamic_range_db=40.0) < n0 == n(dynamic_range_db=160.0)    # 最も強い面から 40 dB 以上下の界面
    assert n(min_prominence_db=0.5) == n0 > n(min_prominence_db=1.0)     # 谷から 0.8 dB の肩
    lo = O.oct_layer_thickness(a, min_separation_fwhm=0.7)
    assert lo["separation_limit_um"] == pytest.approx(0.5 * base["separation_limit_um"])
    with pytest.raises(ValueError):                                       # 1.4 倍のすぐ上の肩が 2.8 倍では拒否
        O.oct_layer_thickness(a, min_separation_fwhm=2.8)
