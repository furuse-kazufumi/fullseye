# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""illumdesign — closed forms for lights, irradiance and defect contrast.

* A point source at height h over a plane gives ``E(r) = I0 cos³θ / h²``
  (inverse square × emitter cosine × surface cosine) — reproduced to 1e-12.
* A ring of n emitters aimed at the origin gives, on axis, ``n I0 cos θ / d²``
  with ``cos θ = h/d`` — one line of algebra, checked exactly.
* Dome illumination is uniform (min/max > 0.9 over 80 % of a part a third of
  the dome radius) while a low ring is not.
* The GGX lobe used for the camera radiance is the same function as
  ``specularity.brdf_microfacet`` (compared at random geometry to 1e-12).
* On a glossy surface a facet of slope s mirrors a ring light into an on-axis
  camera when the light's zenith angle is 2s: the sweep's best elevation is
  ``90° − 2s`` within one grid step, for s = 10° and 20°.
* Coaxial light on a matte surface: a tilted Lambertian facet is darker by
  ``cos s``; Michelson contrast ``(cos s − 1)/(cos s + 1)`` — checked.
* Backlight: a flat opaque part plane receives nothing from below (E = 0).
* The design table ranks dark field first for a topographic defect on a glossy
  surface and reports agreement with the rule of thumb; every bad input is a
  ``ValueError``.
"""
import math
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import illumdesign as ID  # noqa: E402
import specularity  # noqa: E402


def test_point_source_inverse_square_cosine_cubed():
    h = 100.0
    lt = ID.light_source("point", height_mm=h, intensity=3.0)
    irr = ID.irradiance_map(lt, size_mm=(80.0, 80.0), shape=(9, 9))
    ys = (0.5 - (np.arange(9) + 0.5) / 9) * 80.0
    xs = ((np.arange(9) + 0.5) / 9 - 0.5) * 80.0
    X, Y = np.meshgrid(xs, ys)
    r2 = X * X + Y * Y
    cos = h / np.sqrt(r2 + h * h)
    expect = 3.0 * cos ** 3 / (h * h)
    assert np.allclose(irr, expect, rtol=1e-12, atol=0)


def test_ring_on_axis_closed_form_and_elevation():
    R, h, n = 60.0, 80.0, 24
    lt = ID.light_source("ring", radius_mm=R, height_mm=h, n=n, intensity=2.0)
    assert lt["elevation_deg"] == pytest.approx(math.degrees(math.atan2(h, R)))
    irr = ID.irradiance_map(lt, size_mm=(1e-6, 1e-6), shape=(1, 1))
    d = math.hypot(R, h)
    cos = h / d
    # aimed at the origin: emitter cosine = 1 on axis; surface cosine = h/d
    assert irr[0, 0] == pytest.approx(n * 2.0 * cos / d ** 2, rel=1e-9)
    # lensed LED (cos^4) aimed at the origin: same on axis, less off axis
    lt4 = ID.light_source("ring", radius_mm=R, height_mm=h, n=n, intensity=2.0, cos_exponent=4.0)
    m1 = ID.irradiance_map(lt, size_mm=(60, 60), shape=(33, 33))
    m4 = ID.irradiance_map(lt4, size_mm=(60, 60), shape=(33, 33))
    assert m4[16, 16] == pytest.approx(m1[16, 16], rel=1e-9)
    assert m4[0, 0] < m1[0, 0]


def test_dome_is_uniform_and_low_ring_is_not():
    dome = ID.light_source("dome", radius_mm=150.0, n=400)
    u_dome = ID.illumination_uniformity(ID.irradiance_map(dome, size_mm=(50, 50), shape=(48, 48)))
    ring = ID.light_source("ring", radius_mm=60.0, height_mm=15.0, n=24)
    u_ring = ID.illumination_uniformity(ID.irradiance_map(ring, size_mm=(50, 50), shape=(48, 48)))
    assert u_dome["uniformity"] > 0.9
    assert u_ring["uniformity"] < u_dome["uniformity"]
    assert u_dome["cv"] < 0.05
    assert u_dome["peak_offset_px"] == (0, 0) or abs(u_dome["peak_offset_px"][0]) + abs(u_dome["peak_offset_px"][1]) <= 24


def test_height_map_tilts_normals_dent_wall_is_darker_under_grazing_light():
    ring = ID.light_source("ring", radius_mm=100.0, height_mm=20.0, n=36)
    H = W = 41
    ys = (0.5 - (np.arange(H) + 0.5) / H) * 20.0
    xs = ((np.arange(W) + 0.5) / W - 0.5) * 20.0
    X, Y = np.meshgrid(xs, ys)
    bump = 0.5 * np.exp(-(X * X + Y * Y) / 8.0)
    flat = ID.irradiance_map(ring, size_mm=(20, 20), shape=(H, W))
    relief = ID.irradiance_map(ring, size_mm=(20, 20), shape=(H, W), height=bump)
    # the bump's flanks face the ring on one side (brighter) and away on the other (darker)
    assert relief.max() > flat.max() * 1.05
    assert relief.min() < flat.min() * 0.95
    # the top of the bump is flat: same irradiance as the plane to first order
    assert abs(relief[H // 2, W // 2] - flat[H // 2, W // 2]) / flat[H // 2, W // 2] < 0.05


def test_ggx_lobe_matches_specularity_brdf_microfacet():
    rng = np.random.default_rng(3)
    for _ in range(20):
        n = rng.normal(size=3); n[2] = abs(n[2]) + 0.5; n /= np.linalg.norm(n)
        l = rng.normal(size=3); l[2] = abs(l[2]) + 0.2; l /= np.linalg.norm(l)
        v = rng.normal(size=3); v[2] = abs(v[2]) + 0.2; v /= np.linalg.norm(v)
        h = l + v; h /= np.linalg.norm(h)
        rough, f0 = float(rng.uniform(0.1, 1.0)), float(rng.uniform(0.0, 1.0))
        mine = ID._ggx(np.array([n @ l]), np.array([n @ v]), np.array([n @ h]), np.array([v @ h]), rough, f0)[0]
        ref = specularity.brdf_microfacet(n[None, None, :], l, v, roughness=rough, f0=f0)[0, 0]
        assert mine == pytest.approx(ref, rel=1e-12, abs=1e-15)


@pytest.mark.parametrize("slope", [10.0, 20.0])
def test_sweep_peaks_where_the_facet_mirrors_the_light_into_the_camera(slope):
    sw = ID.lighting_sweep(surface="mirror", slope_deg=slope, elevations_deg=[float(v) for v in range(30, 90, 2)],
                           radius_mm=60.0, camera_height_mm=1000.0)
    best = sw[int(np.argmax(sw[:, 1])), 0]
    assert abs(best - (90.0 - 2.0 * slope)) <= 2.0, (slope, best)
    assert sw.shape[1] == 2 and np.all(sw[:, 1] >= 0)


def test_coaxial_on_matte_gives_the_lambertian_cosine_contrast():
    lt = ID.light_source("coaxial", radius_mm=10.0, height_mm=2000.0, n=1)   # far away: light ∥ view
    dc = ID.defect_contrast(lt, surface={"albedo": 0.6, "roughness": 1.0, "f0": 0.0},
                            slopes_deg=[15.0], camera=(0.0, 0.0, 2000.0), n_azimuth=4)
    c = math.cos(math.radians(15.0))
    expect = (c - 1.0) / (c + 1.0)                                         # Lambert: L ∝ n·l = cos s
    row = dc["per_slope"][0]
    assert row["mean"] == pytest.approx(expect, abs=2e-3)
    assert row["signed_at_max"] < 0
    assert dc["regime"] == "dark_field"                                    # no specular at all
    # pigment at half albedo: (1 - 0.5)/(1 + 0.5) = 1/3 with no glare
    assert dc["pigment"] == pytest.approx(1.0 / 3.0, abs=1e-9)


def test_glare_dilutes_pigment_contrast():
    lt = ID.light_source("ring", radius_mm=60.0, height_mm=200.0, n=24)   # bright field on a glossy surface
    matte = ID.defect_contrast(lt, surface="matte", slopes_deg=[5.0])
    glossy = ID.defect_contrast(lt, surface="mirror", slopes_deg=[5.0])
    assert matte["pigment"] == pytest.approx(1.0 / 3.0, abs=0.02)
    assert glossy["pigment"] < matte["pigment"] * 0.8
    assert glossy["regime"] == "bright_field"


def test_backlight_gives_no_irradiance_on_an_opaque_top_face_but_lights_from_below():
    lt = ID.light_source("backlight", radius_mm=40.0, height_mm=30.0, n=6)
    top = ID.irradiance_map(lt, size_mm=(20, 20), shape=(8, 8))
    assert np.all(top == 0.0)
    assert lt["emitters"].shape == (36, 3) and np.all(lt["emitters"][:, 2] == -30.0)


def test_design_table_prefers_dark_field_for_topographic_on_glossy():
    d = ID.illumination_design(surface="glossy", defect="topographic", slope_deg=10.0)
    names = [r["candidate"] for r in d["ranking"]]
    assert d["recommended"] == names[0]
    assert d["ranking"][0]["score"] >= d["ranking"][-1]["score"]
    assert d["rule_of_thumb"] == "ring_dark_field_20deg"
    assert any(n.startswith("ring_best_") for n in names)
    e = ID.illumination_design(surface="matte", defect="edge")
    assert e["recommended"] == "backlight" and e["agrees_with_rule"]
    p = ID.illumination_design(surface="glossy", defect="pigment")
    assert p["rule_of_thumb"] == "dome"


@pytest.mark.parametrize("bad", [
    lambda: ID.light_source("laser"),
    lambda: ID.light_source("ring", radius_mm=0.0),
    lambda: ID.light_source("ring", n=0),
    lambda: ID.light_source("ring", tilt_deg=120.0),
    lambda: ID.light_source("point", position=(0, 0, -5)),
    lambda: ID.light_source("custom"),
    lambda: ID.light_source("custom", emitters=[[0, 0, 1]], directions=[[0, 0, 0]]),
    lambda: ID.light_source("backlight", n=100),
    lambda: ID.irradiance_map({"x": 1}),
    lambda: ID.irradiance_map(ID.light_source(), size_mm=(0, 10)),
    lambda: ID.irradiance_map(ID.light_source(), shape=(4, 4), height=np.zeros((3, 3))),
    lambda: ID.illumination_uniformity(np.full((4, 4), -1.0)),
    lambda: ID.illumination_uniformity(np.zeros((4, 4))),
    lambda: ID.defect_contrast(ID.light_source(), surface="velvet"),
    lambda: ID.defect_contrast(ID.light_source(), surface={"gloss": 1}),
    lambda: ID.defect_contrast(ID.light_source(), slopes_deg=[95.0]),
    lambda: ID.defect_contrast(ID.light_source(), camera=(0, 0, -1)),
    lambda: ID.lighting_sweep(elevations_deg=[0.0]),
    lambda: ID.lighting_sweep(kind="dome"),
    lambda: ID.illumination_design(defect="crack"),
])
def test_invalid_inputs_are_value_errors(bad):
    with pytest.raises(ValueError):
        bad()
