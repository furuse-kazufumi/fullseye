# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""薄膜の計算を 1 か所(filmoptics の特性行列)に寄せた回(2026-10-15)の門。

外から持ち込む真値:
  * Airy の閉じた式(1 層、ここに独立に書く)—— op の特性行列と別の式。
  * λ/4 積層の閉形式(Macleod §2.4): 入射側から H(LH)^N の反射率 ((1 − Y)/(1 + Y))²、Y = n_H^{2N+2} / (n_L^{2N} n_s)。
  * 傾いた面を垂直入射の模型で読むと、膜厚は d cosθ_膜内 と読まれる(位相 2π n d cosθ / λ のずれ)。
  * 吸収の無い積層で R + T = 1(透過は別の式 4 η₀ Re η_s / |η₀B + C|² から)。
  * 直入射では s と p が区別できない(どちらのアドミッタンスも N になる)。
"""
from __future__ import annotations

import math

import numpy as np
import pytest

import filmoptics as F
import glassmirror as G
import materials as M
import matappear as MA
import opassist


def _nk(name, lam):
    n, k = M._nk(M._record(name, "t"), np.asarray(lam, float) / 1000.0, "t")[:2]
    return n + 1j * k


def _airy(lam, d, n0, n1, n2, cos0, pol):
    """1 層の Airy の式(N = n + ik、位相 e^{2iβ}、減衰の枝 Im(N cos θ) ≥ 0)。op と独立に書く。"""
    s0 = math.sqrt(1.0 - cos0 * cos0)

    def cs(n):
        c = np.sqrt(1.0 - (n0 * s0 / n) ** 2 + 0j)
        return np.where((n * c).imag < 0, -c, c)

    c1, c2 = cs(n1), cs(n2)
    if pol == "s":
        r1 = (n0 * cos0 - n1 * c1) / (n0 * cos0 + n1 * c1)
        r2 = (n1 * c1 - n2 * c2) / (n1 * c1 + n2 * c2)
    else:
        r1 = (n1 * cos0 - n0 * c1) / (n1 * cos0 + n0 * c1)
        r2 = (n2 * c1 - n1 * c2) / (n2 * c1 + n1 * c2)
    ph = np.exp(4j * np.pi * n1 * d * c1 / lam)
    return np.abs((r1 + r2 * ph) / (1 + r1 * r2 * ph)) ** 2


# --------------------------------------------------------------------------- #
# 1 か所に寄せたこと                                                             #
# --------------------------------------------------------------------------- #
def test_matappear_calls_the_one_film_core(monkeypatch):
    """matappear の 2 op は filmoptics の特性行列を呼ぶ(別の式を持たない)。呼ばれた回数で確かめる。"""
    calls = []
    real = F._stack_rt

    def spy(*a, **k):
        calls.append(a[6])
        return real(*a, **k)

    monkeypatch.setattr(F, "_stack_rt", spy)
    MA.thin_film_reflectance([500.0, 600.0], 100.0, 1.5, "SI")
    assert calls == ["s", "p"]
    calls.clear()
    MA.thin_film_rgb(np.dstack([np.zeros((2, 2)), np.zeros((2, 2)), np.ones((2, 2))]), polarization="p")
    assert calls == ["p"]
    src = open(MA.__file__, encoding="utf-8").read()
    assert "def fresnel(" not in src and "def _cos_in(" not in src      # 第二の実装を戻さない


def test_matappear_and_filmoptics_agree_exactly_including_multilayer():
    lam = np.linspace(400.0, 800.0, 41)
    stack = [("TIO2_AMORPHOUS", 60.0), ("SIO2", 95.0), ("TIO2_AMORPHOUS", 60.0)]
    for ang, pol in ((0.0, "unpolarized"), (50.0, "s"), (50.0, "p")):
        a = MA.thin_film_reflectance(lam, stack[0][1], stack[0][0], "N-BK7", cos_theta=math.cos(math.radians(ang)),
                                     polarization=pol, under_layers=stack[1:])
        b = F.multilayer_reflectance(stack, "N-BK7", wavelengths_nm=lam, angle_deg=ang, polarization=pol)[:, 1]
        assert float(np.max(np.abs(a - b))) < 1e-14


# --------------------------------------------------------------------------- #
# 第二の実装(Airy の式)と                                                       #
# --------------------------------------------------------------------------- #
def test_core_matches_the_airy_formula_on_metal_and_dispersive_films():
    lam = np.linspace(400.0, 750.0, 36)
    ti = _nk("TI", lam)
    tio2 = _nk("TIO2_AMORPHOUS", lam)
    worst = 0.0
    cases = [(90.0, tio2, "TIO2_AMORPHOUS"), (150.0, np.full(lam.shape, 1.63 + 0j), 1.63),
             (40.0, np.full(lam.shape, 2.0 + 0.3j), 2.0 + 0.3j)]
    assert len(cases) == 3
    for d, n1, spec in cases:
        for cos0 in (1.0, 0.7, 0.3):
            for pol in ("s", "p"):
                a = MA.thin_film_reflectance(lam, d, spec, "TI", cos_theta=cos0, polarization=pol)
                b = _airy(lam, d, 1.0, n1, ti, cos0, pol)
                worst = max(worst, float(np.max(np.abs(a - b))))
    assert worst < 1e-12, worst


# --------------------------------------------------------------------------- #
# 欠陥 4: thin_film_rgb が膜厚の場・光源・波長の格子・光源の分光を受ける            #
# --------------------------------------------------------------------------- #
def _flat(h, w, tilt_deg=0.0):
    t = math.radians(tilt_deg)
    N = np.zeros((h, w, 3))
    N[..., 0] = math.sin(t)
    N[..., 2] = math.cos(t)
    return N


def test_rgb_takes_a_thickness_field_pixel_by_pixel():
    d = np.array([[60.0, 90.0, 120.0], [150.0, 200.0, 0.0]])
    img = MA.thin_film_rgb(_flat(2, 3, 20.0), thickness_nm=d, n_film="TIO2_AMORPHOUS", n_sub="TI")
    assert img.shape == (2, 3, 3)
    for i in range(2):
        for j in range(3):
            one = MA.thin_film_rgb(_flat(1, 1, 20.0), thickness_nm=float(d[i, j]), n_film="TIO2_AMORPHOUS", n_sub="TI")
            assert np.max(np.abs(img[i, j] - one[0, 0])) < 1e-14
    assert np.ptp(img.reshape(-1, 3), axis=0).max() > 0.1                # 膜厚で色が変わる
    with pytest.raises(ValueError, match="field of shape"):
        MA.thin_film_rgb(_flat(2, 3), thickness_nm=np.ones((3, 2)))
    with pytest.raises(ValueError, match=">= 0"):
        MA.thin_film_rgb(_flat(2, 3), thickness_nm=-d)


def test_rgb_light_direction_uses_the_half_vector():
    N = _flat(2, 2, 35.0)
    sky = MA.thin_film_rgb(N, thickness_nm=120.0, n_film=1.46, n_sub="SI")
    coax = MA.thin_film_rgb(N, thickness_nm=120.0, n_film=1.46, n_sub="SI", light=(0.0, 0.0, 1.0))
    normal = MA.thin_film_rgb(_flat(2, 2, 0.0), thickness_nm=120.0, n_film=1.46, n_sub="SI")
    assert np.max(np.abs(coax - normal)) < 1e-14                         # 同軸照明 = 垂直入射の色
    assert np.max(np.abs(sky - normal)) > 0.01                           # 天空照明は面の傾きで色が動く
    L = np.array([math.sin(math.radians(60.0)), 0.0, math.cos(math.radians(60.0))])
    oblique = MA.thin_film_rgb(N, thickness_nm=120.0, n_film=1.46, n_sub="SI", light=L)
    ref = MA.spectrum_to_srgb(np.asarray(MA.FILM_RGB_NM),
                              MA.thin_film_reflectance(np.asarray(MA.FILM_RGB_NM), 120.0, 1.46, "SI",
                                                       cos_theta=math.cos(math.radians(30.0))))
    assert np.max(np.abs(oblique[0, 0] - ref)) < 1e-12                   # h·l = cos 30°
    with pytest.raises(ValueError, match="opposite"):
        MA.thin_film_rgb(N, light=(0.0, 0.0, -1.0))


def test_rgb_takes_a_wavelength_grid_and_an_illuminant():
    N = _flat(1, 1)
    with pytest.raises(ValueError, match="not extrapolated"):
        MA.thin_film_rgb(N, thickness_nm=90.0, n_film="TIO2", n_sub="TI")   # ルチルの表は 430 nm から
    grid = np.linspace(430.0, 720.0, 59)
    a = MA.thin_film_rgb(N, thickness_nm=90.0, n_film="TIO2", n_sub="TI", nm=grid)
    ref = MA.spectrum_to_srgb(grid, MA.thin_film_reflectance(grid, 90.0, "TIO2", "TI"))
    assert np.max(np.abs(a[0, 0] - ref)) < 1e-14
    flat = np.ones_like(grid)
    b = MA.thin_film_rgb(N, thickness_nm=90.0, n_film="TIO2", n_sub="TI", nm=grid, illuminant=flat)
    assert np.max(np.abs(a - b)) > 1e-3
    with pytest.raises(ValueError, match="strictly increasing"):
        MA.thin_film_rgb(N, nm=grid[::-1])


def test_rgb_defaults_are_unchanged():
    """新しい引数を渡さなければ、以前の値(380〜720 nm・D65・天空照明・無偏光)と同じ。"""
    rng_free = np.array([[0.0, 0.3, 0.954], [0.5, -0.2, 0.84]])
    N = (rng_free / np.linalg.norm(rng_free, axis=1, keepdims=True)).reshape(1, 2, 3)
    grid = np.linspace(380.0, 720.0, 69)
    got = MA.thin_film_rgb(N, thickness_nm=350.0)
    for j in range(2):
        c = abs(float(N[0, j, 2]))
        ref = MA.spectrum_to_srgb(grid, _airy(grid, 350.0, 1.0, np.full(69, 1.33 + 0j), np.full(69, 1.0 + 0j), c, "s")
                                  * 0.5 + _airy(grid, 350.0, 1.0, np.full(69, 1.33 + 0j), np.full(69, 1.0 + 0j), c, "p") * 0.5)
        assert np.max(np.abs(got[0, j] - ref)) < 1e-12


# --------------------------------------------------------------------------- #
# 物理の門                                                                       #
# --------------------------------------------------------------------------- #
def test_tilted_surface_read_at_normal_incidence_is_short_by_d_one_minus_cos_theta_film():
    """傾いた面の膜厚を垂直入射の模型で読むと −d(1 − cos θ_膜内) だけ薄く読む(分散なし・実数の n で縞の位置が厳密)。"""
    lam = np.linspace(450.0, 800.0, 351)
    nf, d = 1.8, 700.0
    for th in (20.0, 40.0, 60.0):
        c0 = math.cos(math.radians(th))
        spec = np.column_stack([lam, MA.thin_film_reflectance(lam, d, nf, 1.45, cos_theta=c0)])
        fit = F.film_thickness_fit(spec, nf, 1.45, 300.0, 1000.0, angle_deg=0.0, fit_scale=True)
        sin_f = math.sin(math.radians(th)) / nf
        predicted = -d * (1.0 - math.sqrt(1.0 - sin_f ** 2))
        got = fit["thickness_nm"] - d
        assert abs(got - predicted) < 0.05 * abs(predicted) + 0.2, (th, got, predicted)


def test_quarter_wave_stack_matches_the_closed_form_with_table_indices():
    """入射側から H(LH)^N の λ/4 積層(非晶質 TiO2 / SiO2、石英の上)を Macleod の閉形式と比べる。"""
    lam0 = 550.0
    nH = float(_nk("TIO2_AMORPHOUS", [lam0])[0].real)
    nL = float(_nk("SIO2", [lam0])[0].real)
    ns = float(_nk("SILICA", [lam0])[0].real)
    for N in (0, 1, 3, 5):
        under = [("SIO2", lam0 / 4 / nL), ("TIO2_AMORPHOUS", lam0 / 4 / nH)] * N
        R = float(MA.thin_film_reflectance([lam0], lam0 / 4 / nH, "TIO2_AMORPHOUS", "SILICA", under_layers=under)[0])
        Y = nH ** (2 * N + 2) / (nL ** (2 * N) * ns)
        assert abs(R - ((1 - Y) / (1 + Y)) ** 2) < 2e-6, (N, R)          # k(550) ≈ 1e-7 の吸収だけ
    assert R > 0.95                                                       # 11 層で高反射の鏡


def test_lossless_stack_conserves_energy_and_normal_incidence_has_no_polarization():
    lam = np.linspace(450.0, 700.0, 26)
    for ang in (0.0, 30.0, 65.0):
        for pol in ("s", "p"):
            R = MA.thin_film_reflectance(lam, 120.0, 2.1, 1.52, cos_theta=math.cos(math.radians(ang)), polarization=pol,
                                         under_layers=[(1.38, 80.0), (1.9, 40.0)])
            T = F.multilayer_reflectance([(2.1, 120.0), (1.38, 80.0), (1.9, 40.0)], 1.52, wavelengths_nm=lam,
                                         angle_deg=ang, polarization=pol, quantity="transmittance")[:, 1]
            assert float(np.max(np.abs(R + T - 1.0))) < 1e-12
    s = MA.thin_film_reflectance(lam, 90.0, "TIO2_AMORPHOUS", "TI", polarization="s")
    p = MA.thin_film_reflectance(lam, 90.0, "TIO2_AMORPHOUS", "TI", polarization="p")
    assert float(np.max(np.abs(s - p))) < 1e-15
    s60 = MA.thin_film_reflectance(lam, 90.0, "TIO2_AMORPHOUS", "TI", cos_theta=0.5, polarization="s")
    p60 = MA.thin_film_reflectance(lam, 90.0, "TIO2_AMORPHOUS", "TI", cos_theta=0.5, polarization="p")
    assert float(np.max(np.abs(s60 - p60))) > 0.05                        # 斜めでは分かれる


def test_sign_convention_is_stated_and_negative_k_is_refused():
    with pytest.raises(ValueError, match=r"N = n \+ ik"):
        MA.thin_film_reflectance(550.0, 100.0, 1.5, 2.2 - 3.0j)
    with pytest.raises(ValueError, match=r"N = n \+ ik"):
        F.multilayer_reflectance([(2.0 - 0.1j, 50.0)], "SI")
    assert "N = n − ik" in MA.thin_film_reflectance.__doc__


# --------------------------------------------------------------------------- #
# 金属の基板は k > 0(プリセット・材料表)                                         #
# --------------------------------------------------------------------------- #
_METAL_WORDS = ("チタン", "アルミ", "金属", "銅", "銀", "ステンレス", "titanium", "alumin", "metal")


def test_film_presets_name_metal_substrates_by_material_and_those_have_k():
    lam = np.linspace(400.0, 720.0, 17)
    seen = 0
    for op in ("thin_film_reflectance", "thin_film_rgb"):
        for label, kw in opassist.presets(op).items():
            sub = kw.get("n_sub", 1.0)
            says_metal = any(w in label.lower() for w in _METAL_WORDS)
            if isinstance(sub, str):
                rec = M._record(sub, "t")
                if rec["class"] == "metal":
                    assert float(_nk(sub, lam).imag.min()) > 0.5, (op, label)
                    seen += 1
                assert says_metal == (rec["class"] == "metal"), (op, label, sub)
            else:
                assert not says_metal, (op, label, sub)                  # 金属の基板を数値で書かない
                assert complex(sub).imag == 0.0
            assert np.all(np.isfinite(np.asarray(MA.thin_film_reflectance(lam, **{k: v for k, v in kw.items()
                                                                                if k != "light"}))))
    assert seen >= 4                                                      # 焼き色 ×2・陽極酸化 ×2


def test_tio2_records_cover_films_and_both_rutile_rays():
    rec = M._record("TIO2_AMORPHOUS", "t")
    lam = np.linspace(380.0, 780.0, 41)
    n = _nk("TIO2_AMORPHOUS", lam)
    assert rec["class"] == "film" and float(n.real.min()) > 2.0
    assert float(_nk("TIO2_AMORPHOUS", [350.0])[0].imag) > 0.01           # 紫外の吸収端の手前で k > 0
    o, e = _nk("TIO2", [589.0])[0].real, _nk("TIO2_RUTILE_E", [589.0])[0].real
    assert e - o > 0.25                                                   # ルチルは正の一軸性(複屈折 ≈ 0.29)
    a = float(_nk("TIO2_ANATASE", [550.0])[0].real)
    assert float(_nk("TIO2_AMORPHOUS", [550.0])[0].real) < a < float(o) + 0.1
    assert M._record("TIO2_RUTILE_O", "t")["name"] == "TIO2"
    assert M._record("TIO2_FILM", "t")["name"] == "TIO2_AMORPHOUS"


# --------------------------------------------------------------------------- #
# 欠陥 8: 金属の既定は実測の表                                                    #
# --------------------------------------------------------------------------- #
def test_metal_default_is_the_measured_table_and_the_coarse_table_stays_selectable():
    w = np.linspace(400.0, 780.0, 39)
    for m in G.MEASURED_METALS:
        n, k = G.metal_optical_constants(m, w)
        nk = _nk(m.upper(), w)
        assert np.array_equal(n, nk.real) and np.array_equal(k, nk.imag)
    n_t, _ = G.metal_optical_constants("cu", w, source="table")
    n_m, _ = G.metal_optical_constants("cu", w)
    assert float(np.max(np.abs(n_t - n_m))) > 0.1                          # 粗い表は別物として残す
    ag = G.metal_mirror_rgb("ag")
    assert float(ag.min() / ag.max()) > 0.98                               # 実測の銀はほぼ中性
    ag_t = G.metal_mirror_rgb("ag", source="table")
    assert float(ag_t.min() / ag_t.max()) < 0.95                           # 粗い表の銀は黄ばむ
    with pytest.raises(ValueError, match="not extrapolated"):
        G.metal_optical_constants("ag", 3000.0)                            # 実測の表の外は外挿しない
