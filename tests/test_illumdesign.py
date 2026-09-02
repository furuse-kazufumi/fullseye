# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""illumdesign — closed forms for lights, irradiance and defect contrast.

* An isotropic point source at height h over a plane gives ``E(r) = I0 cos³θ
  / h²`` and a Lambertian emitter the cos⁴ law — both reproduced to 1e-12.
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
* The design table: a rough (scattering) defect on a glossy surface wants dark
  field, a smooth facet wants the ring elevation that mirrors it into the
  camera (dark field scores near zero for it — the physics, spelled out), an
  edge wants a backlight; every bad input is a ``ValueError``.
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
    ys = (0.5 - (np.arange(9) + 0.5) / 9) * 80.0
    xs = ((np.arange(9) + 0.5) / 9 - 0.5) * 80.0
    X, Y = np.meshgrid(xs, ys)
    cos = h / np.sqrt(X * X + Y * Y + h * h)
    iso = ID.light_source("point", height_mm=h, intensity=3.0, cos_exponent=0.0)
    assert np.allclose(ID.irradiance_map(iso, size_mm=(80.0, 80.0), shape=(9, 9)), 3.0 * cos ** 3 / (h * h), rtol=1e-12, atol=0)
    lam = ID.light_source("point", height_mm=h, intensity=3.0)
    assert np.allclose(ID.irradiance_map(lam, size_mm=(80.0, 80.0), shape=(9, 9)), 3.0 * cos ** 4 / (h * h), rtol=1e-12, atol=0)


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
    # a high ring shifted +15 mm in x puts the irradiance peak on the +x side — the
    # mis-aim shows in peak_offset_px (a grazing ring peaks at the map edge instead)
    high = ID.light_source("ring", radius_mm=60.0, height_mm=100.0, n=24)
    off = ID.light_source("custom", emitters=high["emitters"] + np.array([15.0, 0.0, 0.0]), directions=high["directions"])
    assert ID.illumination_uniformity(ID.irradiance_map(off, size_mm=(50, 50), shape=(48, 48)))["peak_offset_px"][1] > 4


def test_height_map_tilts_normals_bump_flank_facing_a_bar_light_is_brighter():
    # one-sided light (a bar at +y): the flank facing it brightens, the far flank darkens.
    # (under a symmetric ring the first-order tilt terms cancel — that is the physics, not a bug)
    bar = ID.light_source("bar", radius_mm=100.0, height_mm=20.0, n=9, length_mm=60.0)
    H = W = 41
    ys = (0.5 - (np.arange(H) + 0.5) / H) * 20.0
    xs = ((np.arange(W) + 0.5) / W - 0.5) * 20.0
    X, Y = np.meshgrid(xs, ys)
    bump = 0.5 * np.exp(-(X * X + Y * Y) / 8.0)
    flat = ID.irradiance_map(bar, size_mm=(20, 20), shape=(H, W))
    relief = ID.irradiance_map(bar, size_mm=(20, 20), shape=(H, W), height=bump)
    c = H // 2
    near, far = c - 4, c + 4                       # row index grows toward -y; the bar sits at +y
    assert relief[near, c] > flat[near, c] * 1.3
    assert relief[far, c] < flat[far, c] * 0.7
    assert abs(relief[c, c] - flat[c, c]) / flat[c, c] < 0.05


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
    lt = ID.light_source("coaxial", radius_mm=1.0, height_mm=2000.0, n=1)    # far away: light ∥ view
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
    lt = ID.light_source("coaxial", radius_mm=60.0, height_mm=150.0, n=16)   # light along the view: glare
    matte = ID.defect_contrast(lt, surface="matte", slopes_deg=[5.0])
    glossy = ID.defect_contrast(lt, surface="mirror", slopes_deg=[5.0])
    assert matte["pigment"] == pytest.approx(1.0 / 3.0, abs=0.02)
    assert glossy["pigment"] < matte["pigment"] * 0.5
    assert glossy["regime"] == "bright_field" and matte["regime"] == "dark_field"


def test_backlight_gives_no_irradiance_on_an_opaque_top_face_but_lights_from_below():
    lt = ID.light_source("backlight", radius_mm=40.0, height_mm=30.0, n=6)
    top = ID.irradiance_map(lt, size_mm=(20, 20), shape=(8, 8))
    assert np.all(top == 0.0)
    assert np.all(ID.irradiance_map(lt, size_mm=(20, 20), shape=(8, 8), facing="down") > 0.0)
    with pytest.raises(ValueError):
        ID.irradiance_map(lt, facing="sideways")
    assert lt["emitters"].shape == (36, 3) and np.all(lt["emitters"][:, 2] == -30.0)


def test_design_table_dark_field_for_scatter_matched_elevation_for_a_facet():
    s = ID.illumination_design(surface="glossy", defect="scatter")
    assert s["rule_of_thumb"] == "ring_dark_field_20deg"
    assert s["recommended"] in ("ring_dark_field_20deg", "coaxial")    # bright-field glare can win on paper
    dark = [r for r in s["ranking"] if r["candidate"] == "ring_dark_field_20deg"][0]
    assert dark["scatter_contrast"] > 0.15                              # glossy paint: modest (0.22)
    assert dark["scatter_contrast"] > [r for r in s["ranking"] if r["candidate"] == "dome"][0]["scatter_contrast"]
    d = ID.illumination_design(surface="satin", defect="topographic", slope_deg=10.0)
    names = [r["candidate"] for r in d["ranking"]]
    assert d["recommended"] == names[0]
    assert d["ranking"][0]["score"] >= d["ranking"][-1]["score"]
    assert d["rule_of_thumb"].startswith("ring_best_")                 # satin: too rough for coaxial glare
    g = ID.illumination_design(surface="glossy", defect="topographic", slope_deg=10.0)
    assert g["recommended"].startswith("ring_")                          # the 70 deg ring mirrors the facet in
    coax = [r for r in g["ranking"] if r["candidate"] == "coaxial"][0]
    assert coax["background_uniformity"] > 0.95                          # the area source covers the field
    # a smooth 10 deg facet does not light up in dark field: the low ring scores near zero
    low = [r for r in d["ranking"] if r["candidate"] == "ring_dark_field_20deg"][0]
    assert low["defect_contrast"] < 0.05
    assert any(n.startswith("ring_best_") for n in names) and g["best_ring_elevation_deg"] == 70.0
    e = ID.illumination_design(surface="matte", defect="edge")
    assert e["recommended"] == "backlight" and e["agrees_with_rule"]
    p = ID.illumination_design(surface="glossy", defect="pigment")
    assert p["rule_of_thumb"] == "dome"
    m = ID.illumination_design(surface="mirror", defect="topographic", slope_deg=10.0)
    assert m["rule_of_thumb"] == "coaxial" and m["recommended"] == "coaxial"
    # rough (scattering) defect on a mirror-like finish: dark field wins by a wide margin
    ms = ID.illumination_design(surface="mirror", defect="scatter")
    dark = [r for r in ms["ranking"] if r["candidate"] == "ring_dark_field_20deg"][0]
    assert dark["scatter_contrast"] > 0.85
    assert ms["recommended"] in ("ring_dark_field_20deg", "dome", "coaxial")
    sat = ID.illumination_design(surface="satin", defect="topographic", slope_deg=10.0)
    assert sat["recommended"].startswith("ring_best_") and sat["agrees_with_rule"]


# --------------------------------------------------------------------------- #
# ledger                                                                       #
# --------------------------------------------------------------------------- #
ILLUM_OPS = ["light_source", "irradiance_map", "illumination_uniformity", "defect_contrast",
             "lighting_sweep", "illumination_design"]


def test_illumination_category_is_registered_and_returns_declared_types():
    import opsoptics
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import chain_fuzz
    assert opsoptics.list_ops("illumination") == ILLUM_OPS
    lt = ID.light_source()
    args = {"light_source": (), "irradiance_map": (lt, (20, 20), (8, 8)),
            "illumination_uniformity": (ID.irradiance_map(lt, (20, 20), (8, 8)),),
            "defect_contrast": (lt,), "lighting_sweep": ("glossy", 10.0, [20.0, 50.0]),
            "illumination_design": ()}
    for name in ILLUM_OPS:
        meta = opsoptics.info(name)
        assert meta["module"] == "illumdesign" and meta["func"] is getattr(ID, name) and meta["doc"]
        val = opsoptics.call(name, *args[name])
        assert chain_fuzz.TYPE_CHECKS[meta["out"]](val), (name, meta["out"], type(val).__name__)
    names = {o[0] for o in chain_fuzz.catalog() if o[1] == "optics"}
    assert set(ILLUM_OPS) <= names


@pytest.mark.parametrize("name", ["irradiance_map", "defect_contrast"])
def test_light_consuming_ops_refuse_a_random_table(name):
    rng = np.random.default_rng(5)
    for bad in ([1, 2, 3], {"x": 1.0}, {"emitters": [[0, 0, 1]]}, rng.random(4).tolist(),
                {"emitters": [[0, 0, 1]], "directions": [[0, 0, 0]]}):
        with pytest.raises(ValueError):
            getattr(ID, name)(bad)


def test_facade_exports_every_illumination_op():
    import api
    import fullseye
    for name in ILLUM_OPS:
        assert name in api.__all__ and name in fullseye.__all__, name


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
    lambda: ID.defect_contrast(ID.light_source(), n_azimuth=0),
])
def test_invalid_inputs_are_value_errors(bad):
    with pytest.raises(ValueError):
        bad()
