# -*- coding: utf-8 -*-
"""Gates for ``watervision`` (how water looks in inspection images).

Every number is scored against something the op does not share with itself: an explicit Fresnel formula, a second method
(the photon count against the Jacobian of the wavefront map), a paraxial 2 x 2 matrix, a closed form of the wet albedo with its
own quadrature, or a spectral peak. Each family has a probe that breaks the answer on purpose and must be caught.
"""
import math

import numpy as np
import pytest

import watermedia as W
import watervision as V


# ---------------------------------------------------------------- helpers (independent of the module under test)
def fresnel_T(theta_rad, n1, n2):
    """Unpolarised transmittance, written out here (the module computes it with its own helpers)."""
    ci = np.cos(theta_rad)
    st = n1 / n2 * np.sin(theta_rad)
    ct = np.sqrt(1.0 - st * st)
    rs = (n1 * ci - n2 * ct) / (n1 * ci + n2 * ct)
    rp = (n2 * ci - n1 * ct) / (n2 * ci + n1 * ct)
    return 1.0 - 0.5 * (rs * rs + rp * rp)


def _smooth_surface(amp, n=64, length=4.0):
    x = np.arange(n) * length / n
    X, Y = np.meshgrid(x, x)
    return amp * (np.sin(2 * np.pi * 2 * X / length) + 0.6 * np.cos(2 * np.pi * (X + 2 * Y) / length + 0.7)
                  + 0.4 * np.sin(2 * np.pi * 3 * Y / length + 1.1)), length


N_W = float(W.fresnel_water_air(0.0)["n_water"])


# ---------------------------------------------------------------- 1. caustic_irradiance
@pytest.mark.parametrize("zenith", [0.0, 25.0, 50.0])
def test_flat_surface_gives_a_uniform_cos_theta_times_T(zenith):
    for method in ("photon", "wavefront"):
        r = V.caustic_irradiance(np.zeros((16, 16)), 3.0, 1.5, (zenith, 30.0), method=method)
        th = math.radians(zenith)
        expect = math.cos(th) * fresnel_T(th, 1.0, N_W)
        e = r["irradiance"]
        assert abs(e.mean() / expect - 1.0) < 1e-9 and (e.max() - e.min()) < 1e-9
        assert abs(r["flat_irradiance"] / expect - 1.0) < 1e-9


def test_photon_energy_is_conserved_with_periodic_wrap():
    h, length = _smooth_surface(0.03)
    r = V.caustic_irradiance(h, length, 1.0, (30.0, 40.0), ray_density=1)
    assert abs(r["incident_flux"] / r["incident_flux_analytic"] - 1.0) < 1e-9       # the beam through the patch
    # second route: the mean transmittance from the gradients and the written-out Fresnel formula
    n = h.shape[0]
    k = 2 * math.pi * np.fft.fftfreq(n, 1.0 / n) / length
    spec = np.fft.fft2(h)
    hx = np.fft.ifft2(spec * 1j * k[None, :]).real
    hy = np.fft.ifft2(spec * 1j * k[:, None]).real
    d = np.array([math.sin(math.radians(30)) * math.cos(math.radians(40)), math.sin(math.radians(30)) * math.sin(math.radians(40)),
                  -math.cos(math.radians(30))])
    g = d[0] * hx + d[1] * hy - d[2]
    cosi = g / np.sqrt(1 + hx * hx + hy * hy)
    tbar = float((g * fresnel_T(np.arccos(cosi), 1.0, N_W)).sum() / g.sum())
    assert abs(r["mean_transmittance"] / tbar - 1.0) < 1e-6
    cell = (length / n) ** 2
    assert abs(r["floor_flux"] / (r["incident_flux_analytic"] * tbar) - 1.0) < 1e-6         # what lands equals the beam times T
    assert abs(r["irradiance"].sum() * cell / r["floor_flux"] - 1.0) < 1e-9
    assert r["lost_flux_fraction"] == 0.0


def test_non_periodic_patch_loses_photons_and_says_so():
    h, length = _smooth_surface(0.12)
    r = V.caustic_irradiance(h, length, 1.0, (45.0, 0.0), periodic=False)
    assert 0.0 < r["lost_flux_fraction"] < 0.5                  # rays slid off the edge
    assert r["floor_flux"] < r["transmitted_flux"]
    assert abs(r["floor_flux"] / r["transmitted_flux"] - (1.0 - r["lost_flux_fraction"])) < 1e-9


def test_methods_agree_on_a_smooth_surface():
    h, length = _smooth_surface(0.008)
    a = V.caustic_irradiance(h, length, 1.0, (0.0, 0.0), ray_density=2)
    b = V.caustic_irradiance(h, length, 1.0, (0.0, 0.0), method="wavefront", ray_density=1)
    assert not b["fold_mask"].any() and np.isfinite(b["irradiance"]).all()
    rel = float(np.sqrt(np.mean((a["irradiance"] - b["irradiance"]) ** 2)) / a["irradiance"].mean())
    assert rel < 0.02                                           # measured 0.3 %
    assert float(np.ptp(a["irradiance"])) > 0.05                # the surface does focus: the test is not about a flat floor


def test_methods_disagree_only_at_folds_and_the_wavefront_flags_them():
    h, length = _smooth_surface(0.2)
    a = V.caustic_irradiance(h, length, 1.0, (0.0, 0.0), ray_density=4)
    b = V.caustic_irradiance(h, length, 1.0, (0.0, 0.0), method="wavefront", ray_density=2)
    fold = b["fold_mask"]
    assert fold.sum() > 20 and np.isinf(b["irradiance"][fold]).all()    # the map folds: gain unbounded
    assert np.isfinite(a["irradiance"]).all()                    # photons count a finite, large value there
    assert a["irradiance"][fold].mean() > 2.0 * a["irradiance"].mean()
    near = fold.copy()
    for _ in range(3):
        near = near | np.roll(near, 1, 0) | np.roll(near, -1, 0) | np.roll(near, 1, 1) | np.roll(near, -1, 1)
    far = ~near
    rel_far = float(np.sqrt(np.mean((a["irradiance"][far] - b["irradiance"][far]) ** 2)) / a["irradiance"][far].mean())
    assert far.sum() > 1000 and rel_far < 0.15                  # away from folds the two still agree


def test_doubling_the_ray_density_changes_the_photon_result_by_under_one_percent():
    h, length = _smooth_surface(0.05)
    r4 = V.caustic_irradiance(h, length, 1.0, (20.0, 0.0), ray_density=4)["irradiance"]
    r8 = V.caustic_irradiance(h, length, 1.0, (20.0, 0.0), ray_density=8)["irradiance"]
    rel = float(np.sqrt(np.mean((r4 - r8) ** 2)) / r8.mean())
    assert rel < 0.01                                           # measured 0.1 %
    default = V.caustic_irradiance(h, length, 1.0, (20.0, 0.0))                  # the default density is 4
    assert default["ray_density"] == 4 and np.array_equal(default["irradiance"], r4)
    r2 = V.caustic_irradiance(h, length, 1.0, (20.0, 0.0), ray_density=2)["irradiance"]
    assert 0.01 < float(np.sqrt(np.mean((r2 - r4) ** 2)) / r4.mean()) < 0.05      # 2 -> 4 still moves it by about 2 %: the density gate is not vacuous


def test_caustic_refusals():
    h, length = _smooth_surface(0.01)
    bad = h.copy()
    bad[3, 4] = np.nan
    with pytest.raises(ValueError):
        V.caustic_irradiance(bad, length, 1.0, (0.0, 0.0))
    bad[3, 4] = np.inf
    with pytest.raises(ValueError):
        V.caustic_irradiance(bad, length, 1.0, (0.0, 0.0))
    with pytest.raises(ValueError):
        V.caustic_irradiance(h, length, 0.001, (0.0, 0.0))            # the floor is above a crest
    with pytest.raises(ValueError):
        V.caustic_irradiance(h, length, 1.0, (0.0, 0.0, 1.0))         # the light travels up
    with pytest.raises(ValueError):
        V.caustic_irradiance(h, length, 1.0, (95.0, 0.0))
    with pytest.raises(ValueError):
        V.caustic_irradiance(h, length, 1.0, (0.0, 0.0), n_water=1.0)
    with pytest.raises(ValueError):
        V.caustic_irradiance(h, length, 1.0, (0.0, 0.0), method="beam")
    with pytest.raises(ValueError):
        V.caustic_irradiance(h[:3, :3], length, 1.0, (0.0, 0.0))
    with pytest.raises(ValueError):
        V.caustic_irradiance(h, length, 1.0, (0.0, 0.0), method="wavefront", periodic=False)
    with pytest.raises(ValueError):
        V.caustic_irradiance(h, -1.0, 1.0, (0.0, 0.0))


def test_caustic_probe_catches_a_wrong_index():
    h, length = _smooth_surface(0.05)
    a = V.caustic_irradiance(h, length, 1.0, (0.0, 0.0))["irradiance"]
    b = V.caustic_irradiance(h, length, 1.0, (0.0, 0.0), n_water=1.45)["irradiance"]
    assert float(np.sqrt(np.mean((a - b) ** 2)) / a.mean()) > 0.01          # the 1 % gate would catch a wrong n
    flat = V.caustic_irradiance(np.zeros((8, 8)), 1.0, 1.0, (40.0, 0.0))["irradiance"].mean()
    assert abs(flat / (math.cos(math.radians(40)) * fresnel_T(math.radians(40), 1.0, 1.45)) - 1.0) > 1e-3   # and the flat gate too


# ---------------------------------------------------------------- 2. bottle_image
PITCH = 100.0                                   # um
ODD = (1500, 301)


def _bottle(fill, light="backlight", pitch=PITCH, size=None, **kw):
    return V.bottle_image(30.0, 2.5, 150.0, fill, 1.52, 1.333, pixel_pitch_um=pitch, light=light, size=size, **kw)


@pytest.mark.parametrize("light", ["backlight", "frontlight"])
def test_rows_above_and_below_the_line_are_the_empty_and_the_full_section(light):
    half = _bottle(0.5, light)
    empty = _bottle(0.0, light)
    full = _bottle(1.0, light)
    k = half["fill_row_from_top"]
    assert k == 750 and half["liquid_rows"] == 750
    assert np.array_equal(half["image"][:k], empty["image"][:k])          # bit identical
    assert np.array_equal(half["image"][k:], full["image"][k:])
    assert not np.array_equal(empty["image"], full["image"])


def test_central_brightness_ratio_and_band_width_follow_the_closed_forms():
    e = _bottle(0.0, size=ODD)
    f = _bottle(1.0, size=ODD)
    c = 150
    ratio = float(f["image"][100, c] / e["image"][100, c])
    na, ng, nl = 1.0, 1.52, 1.333
    t_air_glass = 1 - ((na - ng) / (na + ng)) ** 2
    t_glass_liq = 1 - ((ng - nl) / (ng + nl)) ** 2
    expect = t_glass_liq ** 2 / t_air_glass ** 2           # the air-glass pair and the glass-air pair cancel; the glass-liquid pairs remain
    assert abs(ratio / expect - 1.0) < 1e-9                  # measured 1.0814
    assert abs(f["central_transmittance_filled"] / f["image"][100, c] - 1.0) < 1e-12
    # the lit band of the filled section: half width alpha / (1 / f - 1 / dc) with the paraxial focal length
    x = f["x_mm"]
    row = f["image"][100]
    half = x[np.nonzero(row[c:] < 0.5 * row[c])[0][0] + c]
    pred = f["band_half_width_mm_paraxial"]
    assert abs(half / pred - 1.0) < 0.15                    # measured about 6 % (spherical aberration shortens the focus)
    thin = W.cylinder_lens_caustic(30.0, 1.52, n_fill=1.333, thickness_wall_mm=2.5)
    assert abs(f["paraxial_efl_mm"] / thin["efl_mm"] - 1.0) < 1e-12
    # the empty section is lit nearly to its edges, the filled one only in the band
    lit_e = (e["image"][100] > 0.5 * e["image"][100, c]).sum()
    lit_f = (f["image"][100] > 0.5 * f["image"][100, c]).sum()
    assert lit_e > 1.5 * lit_f


@pytest.mark.parametrize("light", ["backlight", "frontlight"])
@pytest.mark.parametrize("fill", [0.15, 0.33, 0.5, 0.72, 0.9])
def test_fill_line_row_and_measured_level(light, fill):
    img = _bottle(fill, light)
    expect_row = round(fill * 150.0 / (PITCH / 1000.0))
    assert abs(img["liquid_rows"] - expect_row) <= 1
    for method in ("edge", "brightness"):
        lv = V.fill_level_from_image(img["image"], PITCH, method)
        assert abs(lv["row"] - img["fill_row_from_top"]) <= 1
        assert abs(lv["level_mm"] - fill * 150.0) <= 2 * PITCH / 1000.0
        assert lv["confidence"] > 0.9


def test_bubble_ring_outer_diameter_is_the_magnified_bubble():
    pitch = 50.0
    r_b, z_b = 1.0, 60.0
    img = _bottle(0.5, pitch=pitch, bubbles=[(0.0, z_b, r_b)])
    j = int(round((150.0 - z_b) / (pitch / 1000.0) - 0.5))
    row = img["image"][j]
    x = img["x_mm"]
    plate = float(np.median(row[np.abs(x) < 6.0]))
    dark = np.nonzero((row < 0.5 * plate) & (np.abs(x) < 4.0))[0]
    d_px = int(dark.max() - dark.min() + 1)
    # paraxial 2 x 2 matrix from the bubble centre through the liquid-glass and glass-air surfaces to a pinhole at dc
    R, t, dc, na, ng, nl = 30.0, 2.5, 500.0, 1.0, 1.52, 1.333
    Ri = R - t
    m1 = np.array([[1, Ri / nl], [0, 1]])
    s1 = np.array([[1, 0], [-(nl - ng) / Ri, 1]])
    m2 = np.array([[1, t / ng], [0, 1]])
    s2 = np.array([[1, 0], [-(ng - na) / R, 1]])
    mat = s2 @ m2 @ s1 @ m1
    a_, b_, c_, d_ = mat[0, 0], mat[0, 1], mat[1, 0], mat[1, 1]
    ll = dc - R
    p0 = -r_b * (a_ + ll * c_ / na) / (b_ + ll * d_ / na)
    y_e = a_ * r_b + b_ * p0
    mag = abs(y_e) * dc / (dc - R) / r_b
    expect = 2.0 * r_b * mag / (pitch / 1000.0)
    assert abs(d_px - expect) <= 1.0                           # state: measured 54 px at a pitch of 100 um, here 107 vs 106.7
    assert abs(mag - nl) < 0.05                                # a water-filled tube magnifies a bubble on its axis by about n
    assert abs(d_px - 2.0 * r_b / (pitch / 1000.0)) > 10       # probe: assuming no magnification is caught
    assert img["unresolved_rays"] < 0.001 * img["image"].size


@pytest.mark.parametrize("light", ["backlight", "frontlight"])
def test_no_pixel_exceeds_the_panel_radiance(light):
    img = V.bottle_image(30.0, 2.5, 150.0, 0.6, 1.52, 1.333, meniscus_mm=4.0, pixel_pitch_um=250.0, light=light,
                         bubbles=[(0.0, 50.0, 2.0), (-9.0, 70.0, 1.5)])
    im = img["image"]
    assert im.shape == (600, 276) and np.isfinite(im).all()
    assert im.max() <= 1.0 + 1e-9 and im.min() >= 0.0


def test_meniscus_rows_are_between_the_liquid_and_the_air():
    flat = _bottle(0.5)
    men = _bottle(0.5, meniscus_mm=5.0)
    k = flat["fill_row_from_top"]
    n_men = int(round(5.0 / (PITCH / 1000.0)))
    assert np.array_equal(men["image"][k:], flat["image"][k:])           # below the line nothing changes
    assert not np.array_equal(men["image"][k - n_men:k], flat["image"][k - n_men:k])
    assert np.array_equal(men["image"][:k - n_men], flat["image"][:k - n_men])


def test_bottle_refusals():
    base = dict(radius_mm=30.0, wall_mm=2.5, height_mm=150.0, fill_fraction=0.5, n_glass=1.52, n_liquid=1.333, pixel_pitch_um=500.0)
    with pytest.raises(ValueError):
        V.bottle_image(**{**base, "n_glass": 1.0})
    with pytest.raises(ValueError):
        V.bottle_image(**{**base, "n_liquid": 0.9})
    with pytest.raises(ValueError):
        V.bottle_image(**{**base, "fill_fraction": -0.1})
    with pytest.raises(ValueError):
        V.bottle_image(**{**base, "fill_fraction": 1.1})
    with pytest.raises(ValueError):
        V.bottle_image(**{**base, "wall_mm": 30.0})
    with pytest.raises(ValueError):
        V.bottle_image(**{**base, "meniscus_mm": 100.0})
    with pytest.raises(ValueError):
        V.bottle_image(**base, bubbles=[(0.0, 100.0, 1.0)])           # above the fill line
    with pytest.raises(ValueError):
        V.bottle_image(**base, bubbles=[(27.0, 40.0, 1.0)])           # in the wall
    with pytest.raises(ValueError):
        V.bottle_image(**base, light="sidelight")
    with pytest.raises(ValueError):
        V.bottle_image(**{**base, "camera_distance_mm": 40.0})
    with pytest.raises(ValueError):
        V.bottle_image(**base, n_air=1.6)
    with pytest.raises(ValueError):
        V.bottle_image(**{**base, "radius_mm": float("nan")})


# ---------------------------------------------------------------- 3. fill_level_from_image
def test_fill_level_refuses_constant_flat_and_non_finite_images():
    with pytest.raises(ValueError):
        V.fill_level_from_image(np.full((40, 20), 0.7), 100.0)
    with pytest.raises(ValueError):
        V.fill_level_from_image(_bottle(0.0)["image"], PITCH)         # an empty bottle has no fill line
    with pytest.raises(ValueError):
        V.fill_level_from_image(_bottle(1.0)["image"], PITCH)
    bad = np.tile(np.linspace(0, 1, 20)[:, None], (1, 8))
    bad[2, 2] = np.nan
    with pytest.raises(ValueError):
        V.fill_level_from_image(bad, 100.0)
    with pytest.raises(ValueError):
        V.fill_level_from_image(np.zeros((2, 5)), 100.0)
    with pytest.raises(ValueError):
        V.fill_level_from_image(np.eye(8), -1.0)
    with pytest.raises(ValueError):
        V.fill_level_from_image(np.eye(8), 100.0, "magic")


def test_fill_level_probe_catches_a_shifted_row_and_low_confidence_in_noise():
    img = _bottle(0.5)["image"]
    shifted = np.roll(img, 3, axis=0)
    shifted[:3] = img[:1]
    lv = V.fill_level_from_image(shifted, PITCH)
    assert abs(lv["level_mm"] - 75.0) > 0.25                    # three pixels away: the 1-px gate would catch it
    noise = np.random.default_rng(3).random((200, 30))
    assert V.fill_level_from_image(noise, PITCH)["confidence"] < 0.5
    assert V.fill_level_from_image(img, PITCH)["confidence"] > 0.99


# ---------------------------------------------------------------- 4. wet_surface_appearance
def _r_internal_quad(n):
    from scipy.integrate import quad
    thc = math.asin(1.0 / n)

    def refl(th):
        return 1.0 - fresnel_T(th, n, 1.0)

    inner, _ = quad(lambda th: 2.0 * refl(th) * math.sin(th) * math.cos(th), 0.0, thc, epsabs=1e-13, epsrel=1e-13)
    outer, _ = quad(lambda th: 2.0 * math.sin(th) * math.cos(th), thc, math.pi / 2, epsabs=1e-13, epsrel=1e-13)
    return inner + outer


def test_film_zero_leaves_the_albedo_unchanged():
    a = np.array([0.0, 0.1, 0.5, 0.9, 1.0])
    r = V.wet_surface_appearance(a, 0.3, 0.0, 30.0, 40.0)
    assert np.abs(r["wet_albedo"] - a).max() <= 1e-12 and (r["coverage"] == 0.0).all()
    assert np.abs(r["wet_albedo_rgb"] - a[:, None]).max() <= 1e-12
    assert r["specular_wet"][2] == r["specular_dry"][2]


@pytest.mark.parametrize("a", [0.05, 0.2, 0.5, 0.8, 0.95])
def test_wet_albedo_matches_the_closed_form_with_an_independent_quadrature(a):
    ld = 35.0
    r = V.wet_surface_appearance(a, 0.2, 100.0, 20.0, ld)
    rbar = _r_internal_quad(N_W)
    rs = 1.0 - fresnel_T(math.radians(ld), 1.0, N_W)
    expect = a * (1.0 - rs) * (1.0 - rbar) / (1.0 - a * rbar)
    assert abs(r["wet_albedo"] - expect) < 1e-6
    assert abs(r["internal_reflectance_mean"] - rbar) < 1e-6
    # a third route: r = 1 - (1 - rho_ext) / n^2 with rho_ext the cosine-weighted external reflectance
    from scipy.integrate import quad
    rho_ext, _ = quad(lambda th: 2.0 * (1.0 - fresnel_T(th, 1.0, N_W)) * math.sin(th) * math.cos(th), 0.0, math.pi / 2)
    assert abs(rbar - (1.0 - (1.0 - rho_ext) / N_W ** 2)) < 1e-6


def test_wet_is_darker_than_dry_for_every_albedo_and_darker_for_darker_surfaces():
    a = np.linspace(0.01, 0.99, 99)
    r = V.wet_surface_appearance(a, 0.2, 50.0, 20.0, 30.0)
    assert a.size == 99 and (r["wet_albedo"] < a).all() and r["darker"]
    ratio = r["ratio"]
    assert (np.diff(ratio) > 0).all()                          # the darker the dry surface, the larger the relative loss
    half = V.wet_surface_appearance(0.5, 0.2, 50.0, 20.0, 30.0)["ratio"]
    assert 0.60 < float(half) < 0.72                            # measured 0.673: a grey surface loses a third
    rgb = V.wet_surface_appearance(0.5, 0.2, 50.0, 20.0, 30.0)["wet_albedo_rgb"]
    assert rgb.shape == (3,) and rgb[0] > rgb[2]                # dispersion: the index is lower in the red, so less is trapped


def test_a_wet_film_glosses_the_specular_peak():
    r = V.wet_surface_appearance(0.5, 0.1, 50.0, 40.0, 40.0)
    assert r["specular_wet"] > r["specular_dry"] > 0.0          # at the mirror angle the narrower lobe is brighter
    far = V.wet_surface_appearance(0.5, 0.1, 50.0, 70.0, 40.0)
    assert far["specular_wet"] < far["specular_dry"]            # off the peak the narrower lobe is dimmer
    thin = V.wet_surface_appearance(0.5, 0.1, 1.0, 40.0, 40.0)
    assert 0.0 < float(thin["coverage"]) < 1.0 and r["specular_wet"] > thin["specular_wet"] > thin["specular_dry"] * 0.5


def test_wet_surface_refusals_and_probe():
    for bad in (-0.1, 1.1, float("nan")):
        with pytest.raises(ValueError):
            V.wet_surface_appearance(bad, 0.2, 10.0, 30.0, 30.0)
    with pytest.raises(ValueError):
        V.wet_surface_appearance(0.5, 1.5, 10.0, 30.0, 30.0)
    with pytest.raises(ValueError):
        V.wet_surface_appearance(0.5, 0.2, -1.0, 30.0, 30.0)
    with pytest.raises(ValueError):
        V.wet_surface_appearance(0.5, 0.2, 10.0, 90.0, 30.0)
    with pytest.raises(ValueError):
        V.wet_surface_appearance(0.5, 0.2, 10.0, 30.0, 30.0, n_water=0.9)
    # probe: without the trapped light (r = 0) the ratio would be 1 - R_s, far from the 0.67 of the model
    r = V.wet_surface_appearance(0.5, 0.2, 100.0, 30.0, 30.0)
    no_trap = (1.0 - r["fresnel_light"])
    assert abs(float(r["ratio"]) - no_trap) > 0.2


# ---------------------------------------------------------------- 5. wet_dry_inspection_pair
def _plate(seed=0, n=96):
    rng = np.random.default_rng(seed)
    tex = np.clip(0.6 + 0.05 * rng.standard_normal((n, n)), 0, 1)
    m = np.zeros((n, n), dtype=bool)
    m[36:52, 14:80] = True
    tex[m] = 0.25
    return tex, m


def test_pair_is_identical_where_the_film_is_zero():
    tex, m = _plate()
    p = V.wet_dry_inspection_pair(tex, m, 0.3, 0.0, 40.0, 40.0)
    assert np.array_equal(p["dry"], p["wet"]) and np.array_equal(p["specular_dry"], p["specular_wet"])
    assert p["contrast_dry"] == p["contrast_wet"] and p["coverage"] == 0.0


def test_defect_contrast_moves_the_way_the_model_predicts():
    tex, m = _plate()
    p = V.wet_dry_inspection_pair(tex, m, 0.3, 20.0, 40.0, 40.0)
    assert p["contrast_diffuse_wet"] > p["contrast_diffuse_dry"]            # dark pixels lose proportionally more
    assert abs(p["contrast_diffuse_wet"] / p["predicted_diffuse_contrast_wet"] - 1.0) < 0.01    # the one-step prediction from region means
    assert p["contrast_wet"] > p["contrast_dry"]                              # and with the glints (fewer when wet) the same way
    uni = np.where(m, 0.25, 0.6)                                              # uniform regions: the prediction is exact
    q = V.wet_dry_inspection_pair(uni, m, 0.3, 20.0, 40.0, 40.0)
    assert abs(q["contrast_diffuse_wet"] - q["predicted_diffuse_contrast_wet"]) < 1e-12
    assert q["contrast_diffuse_dry"] == pytest.approx(0.35 / 0.85, abs=1e-12)
    assert p["glint_pixels_wet"] < p["glint_pixels_dry"]


def test_the_highlight_moves_with_the_light_and_the_normals_are_fixed_by_the_seed():
    tex, m = _plate()
    a = V.wet_dry_inspection_pair(tex, m, 0.3, 20.0, 25.0, 40.0)
    b = V.wet_dry_inspection_pair(tex, m, 0.3, 20.0, 55.0, 40.0)
    ga, gb = a["specular_wet"] > 0.5, b["specular_wet"] > 0.5
    assert ga.sum() > 0 and gb.sum() > 0
    overlap = (ga & gb).sum() / min(ga.sum(), gb.sum())
    assert overlap < 0.5                                                      # a different set of facets glints
    assert np.array_equal(a["normals"], b["normals"])                         # same seed, same plate
    c = V.wet_dry_inspection_pair(tex, m, 0.3, 20.0, 25.0, 40.0, seed=5)
    assert not np.array_equal(a["normals"], c["normals"])
    flat = V.wet_dry_inspection_pair(tex, m, 0.0, 20.0, 40.0, 40.0)
    assert np.allclose(flat["normals"][..., 2], 1.0)                          # roughness 0: a flat plate


def test_pair_refusals():
    tex, m = _plate()
    with pytest.raises(ValueError):
        V.wet_dry_inspection_pair(tex, np.zeros_like(m), 0.3, 10.0, 30.0, 30.0)
    with pytest.raises(ValueError):
        V.wet_dry_inspection_pair(tex, np.ones_like(m), 0.3, 10.0, 30.0, 30.0)
    with pytest.raises(ValueError):
        V.wet_dry_inspection_pair(tex, m[:-1], 0.3, 10.0, 30.0, 30.0)
    with pytest.raises(ValueError):
        V.wet_dry_inspection_pair(tex, m.astype(int), 0.3, 10.0, 30.0, 30.0)
    with pytest.raises(ValueError):
        V.wet_dry_inspection_pair(tex * 2.0, m, 0.3, 10.0, 30.0, 30.0)
    with pytest.raises(ValueError):
        V.wet_dry_inspection_pair(tex, m, 0.3, -1.0, 30.0, 30.0)


# ---------------------------------------------------------------- 6. underwater_inspection_image
@pytest.mark.parametrize("water", ["pure", "jerlov_I", "jerlov_3C"])
def test_snr_falls_monotonically_with_distance(water):
    d = np.array([0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0])
    snr = np.array([V.underwater_inspection_image(np.full((9, 9), 0.6), np.full((9, 9), x), water)["snr"][4, 4, 1] for x in d])
    assert snr.size == 8 and (np.diff(snr) < 0).all()


def test_pure_water_at_zero_distance_is_the_clear_water_case():
    r = V.underwater_inspection_image(np.random.default_rng(1).random((6, 6)), np.full((6, 6), 1e-10), "pure")
    assert float(np.abs(r["snr"] / r["snr_clear"] - 1.0).max()) < 1e-9
    far = V.underwater_inspection_image(np.full((6, 6), 0.6), np.full((6, 6), 6.0), "jerlov_3C")
    assert float((far["snr"] / far["snr_clear"]).max()) < 1e-2            # murky water at 6 m is nowhere near clear


def test_direct_signal_matches_the_closed_form_and_the_veil_is_strongest_in_the_centre():
    alb = np.random.default_rng(2).random((20, 30, 3))
    dist = 1.5 + 3.0 * np.random.default_rng(3).random((20, 30))
    r = V.underwater_inspection_image(alb, dist, "jerlov_II")
    att = W.water_attenuation(np.array(W.RGB_WAVELENGTHS_UM), "jerlov_II")
    expect = alb * np.exp(-dist[..., None] * att["c"]) / dist[..., None] ** 2 * np.exp(-dist[..., None] * att["kd"])
    assert np.abs(r["direct"] - expect).max() < 1e-12 * expect.max()
    same = V.underwater_inspection_image(np.full((21, 31), 0.5), np.full((21, 31), 3.0), "jerlov_3C")
    assert same["backscatter"][10, 15, 1] > 1.5 * same["backscatter"][0, 0, 1]
    assert same["snr"][10, 15, 1] < same["snr"][0, 0, 1]                    # so the SNR is worst in the centre
    sep = V.underwater_inspection_image(np.full((21, 31), 0.5), np.full((21, 31), 3.0), "jerlov_3C", camera_distance_m=1.0)
    assert sep["backscatter"][10, 15, 1] < same["backscatter"][10, 15, 1]
    amb = V.underwater_inspection_image(np.full((8, 8), 0.5), np.full((8, 8), 2.0), "jerlov_I", light="ambient", depth_m=5.0)
    assert np.isfinite(amb["snr"]).all() and np.ptp(amb["veil_profile"]) == 0.0


def test_inspection_image_refusals():
    a = np.full((6, 6), 0.5)
    d = np.full((6, 6), 2.0)
    with pytest.raises(ValueError):
        V.underwater_inspection_image(a, np.zeros((6, 6)), "pure")
    with pytest.raises(ValueError):
        V.underwater_inspection_image(a * 3.0, d, "pure")
    with pytest.raises(ValueError):
        V.underwater_inspection_image(a, d, "jerlov_Z")
    with pytest.raises(ValueError):
        V.underwater_inspection_image(a, d, "pure", light="moon")
    with pytest.raises(ValueError):
        V.underwater_inspection_image(a, np.full((5, 6), 2.0), "pure")
    with pytest.raises(ValueError):
        V.underwater_inspection_image(a, d, "pure", lamp_power=0.0)
    with pytest.raises(ValueError):
        V.underwater_inspection_image(np.full((6, 6, 4), 0.5), d, "pure")


# ---------------------------------------------------------------- 7. caustic_floor_segmentation
def _wave_floor(cycles, axis, n=64, length=4.0, amp=0.008):
    x = np.arange(n) * length / n
    X, Y = np.meshgrid(x, x)
    h = amp * np.sin(2 * np.pi * cycles * (X if axis == "x" else Y) / length)
    return V.caustic_irradiance(h, length, 1.0, (0.0, 0.0))["irradiance"]


@pytest.mark.parametrize("method", ["otsu", "fold"])
@pytest.mark.parametrize("cycles,axis", [(5, "x"), (4, "x"), (8, "y")])
def test_segmented_lines_have_the_waves_period(method, cycles, axis):
    e = _wave_floor(cycles, axis, amp=0.01)
    s = V.caustic_floor_segmentation(e, method)
    period = s["period_px_x"] if axis == "x" else s["period_px_y"]
    other = s["period_px_y"] if axis == "x" else s["period_px_x"]
    assert s["dominant_axis"] == axis and math.isnan(other)
    assert abs(period / (64.0 / cycles) - 1.0) < 0.02                       # FFT peak within 2 % (measured: exact)
    assert 0.05 < s["fraction"] < 0.6
    # probe: a different wave number would be caught
    assert abs(period / (64.0 / (cycles + 1)) - 1.0) > 0.02


def test_segmentation_marks_inf_folds_and_refuses_bad_input():
    h, length = _smooth_surface(0.2)
    w = V.caustic_irradiance(h, length, 1.0, (0.0, 0.0), method="wavefront", ray_density=2)
    s = V.caustic_floor_segmentation(w["irradiance"])
    assert s["n_inf"] == int(np.isinf(w["irradiance"]).sum()) > 0 and s["mask"][np.isinf(w["irradiance"])].all()
    with pytest.raises(ValueError):
        V.caustic_floor_segmentation(np.full((16, 16), 1.0))
    bad = np.ones((16, 16))
    bad[0, 0] = np.nan
    with pytest.raises(ValueError):
        V.caustic_floor_segmentation(bad)
    bad[0, 0] = -1.0
    with pytest.raises(ValueError):
        V.caustic_floor_segmentation(bad)
    with pytest.raises(ValueError):
        V.caustic_floor_segmentation(np.ones((4, 4)) + np.eye(4))
    with pytest.raises(ValueError):
        V.caustic_floor_segmentation(np.ones((16, 16)) + np.eye(16), "magic")
    with pytest.raises(ValueError):
        V.caustic_floor_segmentation(np.ones((16,)))


# ---------------------------------------------------------------- registry
def test_watervision_is_registered_in_the_optics_ledger():
    import opsoptics
    names = opsoptics.list_ops("watervision")
    assert len(names) == 7
    assert set(names) == set(V.__all__)
    assert all(opsoptics.OPSOPTICS[n]["module"] == "watervision" for n in names)
