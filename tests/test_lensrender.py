# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""lensrender: photograph a 3-D scene through the lens prescription (sensor-side ray tracing).

Gates, each against a closed form, a published relation, a second implementation or the existing ops:

* the backward trace is the exact reverse of ``raytrace.ray_bundle`` (1e-9 mm, 1e-12 in direction) - and the
  gate is shown to fail when the refraction indices are not swapped;
* an ideal lens with the pupil centre is the perspective pinhole (1e-9), and the error of a small aperture shrinks with it;
* the plane / sphere / triangle shading: texture lookups, the sphere silhouette, Lambertian energy (1e-12), shadows, spectral albedo;
* the photograph: the irradiance of a white plane is ``pi L sin^2(alpha)`` (closed form), photon counts follow
  ``E dlambda A t (lambda / hc) QE`` within 3 sigma of 50 shot-noise repeats, the edges of a checkerboard follow
  ``lensimage.distortion_map``, the relative illumination follows ``lensimage`` (state the numbers), the width of a defocused edge is the
  disc-blur closed form, the cat's eye is the intersection of two discs (closed form), the lateral colour follows ``raytrace.chromatic_shift``;
* a brute-force scalar renderer written in this file (no helper shared with the module) gives the same irradiance to 1e-9.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

import lensimage as LI
import lensrender as LR
import raytrace as RT
import raytrace3d as R3

INF = float("inf")
RS = [22.01359, -435.76044, -22.21328, 20.29192, 79.6836, -18.39533]
TS = [3.25896, 6.00755, 0.99997, 4.75041, 2.95208, None]
NS = [1.62041, 1.0, 1.62004, 1.0, 1.62041, 1.0]
D_SCENE = {"type": "directional", "to_light": (0.0, 0.0, 1.0), "irradiance_W_m2_nm": 1.0}


def triplet(rear=6.0, aim="stop", object_mm=INF, stop_ap=4.0):
    return RT.lens_system([{"R": RS[i], "t": TS[i], "n": NS[i], "ap": (stop_ap if i == 0 else rear)} for i in range(6)],
                          stop=0, aim=aim, object_mm=object_mm)


def ideal(f=50.0, ap=5.0, object_mm=1000.0):
    return RT.lens_system([{"f": f, "t": None, "ap": ap}], stop=0, object_mm=object_mm)


def baffled(f=50.0, a1=5.0, a2=5.0, tb=20.0, d=1000.0):
    """An ideal lens with a round baffle tb behind it: mechanical vignetting with a stigmatic image (closed form)."""
    return RT.lens_system([{"f": f, "t": tb, "ap": a1}, {"R": INF, "t": None, "n": 1.0, "ap": a2}], stop=0, object_mm=d)


def disc_overlap(r1, r2, dist):
    if dist >= r1 + r2:
        return 0.0
    if dist <= abs(r1 - r2):
        return math.pi * min(r1, r2) ** 2
    a = r1 * r1 * math.acos((dist * dist + r1 * r1 - r2 * r2) / (2 * dist * r1))
    b = r2 * r2 * math.acos((dist * dist + r2 * r2 - r1 * r1) / (2 * dist * r2))
    c = 0.5 * math.sqrt((-dist + r1 + r2) * (dist + r1 - r2) * (dist - r1 + r2) * (dist + r1 + r2))
    return a + b - c


def plane_scene(albedo=0.5, z=-1000.0, ambient=0.0, **kw):
    return LR.lens_scene([dict({"type": "plane", "z_mm": z, "albedo": albedo}, **kw)], [D_SCENE], ambient=ambient)


# --------------------------------------------------------------------------- exit pupil
def test_exit_pupil_samples_weights_area_and_determinism():
    s = triplet()
    para = RT.paraxial_trace(s)
    for pat in ("hexapolar", "halton"):
        a = LR.exit_pupil_samples(s, 300, pat)
        b = LR.exit_pupil_samples(s, 300, pat)
        assert a["n"] >= 100 and a["xy_mm"].shape == (a["n"], 2)
        assert np.array_equal(a["xy_mm"], b["xy_mm"]) and np.array_equal(a["weights_mm2"], b["weights_mm2"])
        assert abs(a["area_ratio"] - math.pi / 4) < 1e-12                     # the weights are the disc area (pi R^2) over (2R)^2
        assert abs(a["weights_mm2"].sum() - math.pi * para["xp_radius"] ** 2) < 1e-9
        assert np.max(np.hypot(a["xy_mm"][:, 0], a["xy_mm"][:, 1])) <= para["xp_radius"] * (1 + 1e-12)
        assert abs(a["radius_mm"] - para["xp_radius"]) < 1e-12
        assert abs(a["z_mm"] - (sum(t for t in TS[:-1]) + para["xp_position"])) < 1e-12
    h = LR.exit_pupil_samples(s, 4096, "halton")
    assert abs(h["square_acceptance"] / (math.pi / 4) - 1.0) < 0.01             # the disc is pi/4 of the enclosing square
    assert LR.exit_pupil_samples(s, 61, "hexapolar")["n"] == 61                # 1 + 3 r (r + 1) with r = 4
    assert LR.exit_pupil_samples(s, 1, "halton")["n"] == 1


def test_exit_pupil_hexapolar_centre_and_ring_counts():
    e = LR.exit_pupil_samples(ideal(), 37, "hexapolar")
    assert e["n"] == 37 and np.allclose(e["xy_mm"][0], 0.0)
    r = np.hypot(e["xy_mm"][:, 0], e["xy_mm"][:, 1])
    assert int((r > 1e-12).sum()) == 36 and len(np.unique(np.round(r, 9))) == 4     # centre + rings of 6, 12, 18


def test_exit_pupil_refuses_what_it_cannot_sample():
    tele = RT.lens_system([{"R": INF, "t": 50.0, "n": 1.0, "ap": 2.0}, {"f": 50.0, "t": None, "ap": 20.0}], stop=0, object_mm=INF)
    with pytest.raises(ValueError, match="exit pupil is at infinity"):
        LR.exit_pupil_samples(tele, 8)
    with pytest.raises(ValueError):
        LR.exit_pupil_samples(triplet(), 8, "random")
    with pytest.raises(ValueError):
        LR.exit_pupil_samples(triplet(), 0)
    with pytest.raises(ValueError):
        LR.exit_pupil_samples({"surfaces": []}, 8)


# --------------------------------------------------------------------------- the backward trace
def _forward_rows(s, fields, rings=6):
    out = []
    for fld in fields:
        b = RT.ray_bundle(s, field=fld, rings=rings)
        v = b["valid"]
        pts, dirs = b["points"][v], b["dirs"][v]
        geo = LR._geometry(s, s["wavelength_um"])
        img, dl = pts[:, -1, :], dirs[:, -1, :]
        pp = img + ((geo["z_xp"] - img[:, 2]) / dl[:, 2])[:, None] * dl           # the forward ray at the exit-pupil plane
        out.append((img, pp, pts[:, 1, :], dirs[:, 0, :], geo))
    return out


def test_backward_trace_reverses_ray_bundle():
    asp = RT.lens_system([{"R": 40.0, "t": 4.0, "n": 1.6, "k": -0.8, "asph": (1e-6, -2e-9), "ap": 8.0},
                          {"R": -60.0, "t": 25.0, "n": 1.0, "ap": 8.0}], stop=0, object_mm=INF)
    worst_p, worst_d, count = 0.0, 0.0, 0
    for s, fields in ((triplet(), (0.0, 7.0, 12.0)), (asp, (0.0, 3.0))):
        for img, pp, p_in, d_in, geo in _forward_rows(s, fields):
            P = img.copy()
            Dv = pp - img
            Dv /= np.linalg.norm(Dv, axis=1, keepdims=True)
            o, d, tr, ok, tir = LR._trace_back(s, geo, P, Dv)
            assert ok.all() and not tir.any()
            count += len(P)
            worst_p = max(worst_p, float(np.abs(o - p_in).max()))
            worst_d = max(worst_d, float(np.abs(d + d_in).max()))
    assert count > 200
    assert worst_p < 1e-9 and worst_d < 1e-12, (worst_p, worst_d)


def test_reversibility_gate_fails_without_swapped_indices():
    """The probe: use the forward refraction ratio instead of the reversed one and the same gate must fail by a lot."""
    s = triplet()
    img, pp, p_in, d_in, geo = _forward_rows(s, (7.0,))[0]
    Dv = pp - img
    Dv /= np.linalg.norm(Dv, axis=1, keepdims=True)
    bad = dict(geo)
    bad["na"], bad["nb"] = geo["nb"], geo["na"]
    o, d, tr, ok, tir = LR._trace_back(s, bad, img.copy(), Dv)
    assert ok.sum() > 10
    assert np.nanmax(np.abs(o[ok] - p_in[ok])) > 1e-3 or np.nanmax(np.abs(d[ok] + d_in[ok])) > 1e-3


def test_trace_sensor_rays_public_op_matches_one_forward_ray():
    s = triplet()
    img, pp, p_in, d_in, geo = _forward_rows(s, (10.0,))[0]
    r = LR.trace_sensor_rays(s, [img[7, :2]], [pp[7, :2]])
    assert r["origin"].shape == (1, 1, 3) and not r["vignetted"].any()
    assert np.abs(r["origin"][0, 0] - p_in[7]).max() < 1e-9
    assert np.abs(r["direction"][0, 0] + d_in[7]).max() < 1e-12
    assert r["transmission"][0, 0] == 1.0                                      # Fresnel-free by default
    assert abs(r["z_pupil_mm"] - geo["z_xp"]) < 1e-12 and abs(r["z_sensor_mm"] - geo["z_img"]) < 1e-12


def test_fresnel_transmission_closed_form_and_off_by_default():
    n = 1.5
    s = RT.lens_system([{"R": 60.0, "t": 5.0, "n": n, "ap": 6.0}, {"R": INF, "t": None, "n": 1.0, "ap": 6.0}], stop=0, object_mm=INF)
    pup = np.array([[0.0, 0.0]])
    on = LR.trace_sensor_rays(s, [[0.0, 0.0]], pup, fresnel=True)
    r1 = ((n - 1) / (n + 1)) ** 2
    assert abs(on["transmission"][0, 0] - (1 - r1) ** 2) < 1e-9               # normal incidence on both surfaces
    off = LR.trace_sensor_rays(s, [[0.0, 0.0]], pup, fresnel=False)
    assert off["transmission"][0, 0] == 1.0
    edge = LR.trace_sensor_rays(s, [[0.0, 0.0]], [[0.0, 4.5]], fresnel=True)
    assert 0.5 < edge["transmission"][0, 0] < (1 - r1) ** 2                    # oblique rays lose more
    with pytest.raises(ValueError):
        LR.trace_sensor_rays(s, fresnel="yes")


def test_total_internal_reflection_is_flagged_and_lost():
    # a flat surface into glass, the sensor in the glass: a backward ray steeper than the critical angle cannot get out
    s = RT.lens_system([{"R": INF, "t": None, "n": 1.5, "ap": 10.0}], stop=0, object_mm=INF, image_mm=5.0)
    geo = LR._geometry(s, s["wavelength_um"])
    crit = math.degrees(math.asin(1.0 / 1.5))
    P0 = np.tile([0.0, 0.0, geo["z_img"]], (2, 1))
    ang = np.radians([crit - 1.0, crit + 1.0])
    D = np.stack([np.zeros(2), np.sin(ang), -np.cos(ang)], 1)
    o, d, tr, ok, tir = LR._trace_back(s, geo, P0, D)
    assert ok.tolist() == [True, False] and tir.tolist() == [False, True]
    assert np.isnan(o[1]).all() and tr[1] == 0.0
    # the ray that gets out obeys Snell's law: 1.5 sin(crit - 1) = sin(theta_out)
    assert abs(math.sin(math.acos(-d[0, 2])) - 1.5 * math.sin(ang[0])) < 1e-12


def test_trace_sensor_rays_refuses_bad_input():
    s = triplet()
    with pytest.raises(ValueError):
        LR.trace_sensor_rays(s, [[0.0, float("nan")]])
    with pytest.raises(ValueError):
        LR.trace_sensor_rays(s, [0.0, 1.0])
    with pytest.raises(ValueError):
        LR.trace_sensor_rays(s, wavelength_um=-1.0)
    with pytest.raises(ValueError):
        LR.trace_sensor_rays(s, defocus_mm=float("inf"))
    with pytest.raises(ValueError):
        LR.trace_sensor_rays(s, pupil_xy_mm=np.zeros((0, 2)))


def test_pinhole_limit_of_an_ideal_lens():
    f, d = 50.0, 1000.0
    s = ideal(f, 5.0, d)
    para = RT.paraxial_trace(s)
    m = para["magnification"]
    px = np.array([[0.0, 0.0], [0.3, 0.0], [0.0, -0.8], [0.5, 0.4]])
    r = LR.trace_sensor_rays(s, px, [[0.0, 0.0]])
    o, dd = r["origin"][:, 0], r["direction"][:, 0]
    t = (-d - o[:, 2]) / dd[:, 2]
    hit = (o + t[:, None] * dd)[:, :2]
    assert np.abs(hit - px / m).max() < 1e-9                                  # the perspective pinhole, by the paraxial magnification
    pup = LR.exit_pupil_samples(s, 19, "hexapolar")["xy_mm"]
    spread = []
    for dz in (0.0, 0.1, 0.2):                                                 # every pupil point meets the same object point; a defocused sensor spreads them
        ra = LR.trace_sensor_rays(s, px, pup, defocus_mm=dz)
        oo, d2 = ra["origin"], ra["direction"]
        tt = (-d - oo[..., 2]) / d2[..., 2]
        h2 = (oo + tt[..., None] * d2)[..., :2]
        spread.append(float(np.ptp(h2[1], axis=0).max()))
    assert spread[0] < 1e-9 and spread[1] > 1e-3 and abs(spread[2] / spread[1] - 2.0) < 1e-2, spread
    # a real lens with the aperture shrunk to a pinhole: the error against the paraxial magnification falls like the field squared (distortion)
    err = []
    for hgt in (0.2, 0.02):
        tri = triplet(stop_ap=1e-4)
        efl = RT.paraxial_trace(tri)["efl"]
        dd = LR.trace_sensor_rays(tri, [[0.0, hgt]], [[0.0, 0.0]])["direction"][0, 0]
        err.append(abs(abs(dd[1] / dd[2]) * efl / hgt - 1.0))
    assert len(err) == 2 and err[1] < 1e-4 and err[1] < err[0] / 50.0, err


def test_vignetted_fraction_follows_raytrace_vignetting():
    """The share of the exit pupil that gets through at a field, against ``ray_bundle``'s valid share (aim = stop)."""
    s = triplet(rear=6.0, aim="stop")
    pup = LR.exit_pupil_samples(s, 400, "hexapolar")
    worst = 0.0
    for fld in (10.0, 15.0):
        b = RT.ray_bundle(s, field=fld, rings=12)
        fr_rt = float(b["valid"].mean())
        cr = RT.chief_ray(s, fld)
        r = LR.trace_sensor_rays(s, [[cr["image_x"], cr["image_y"]]], pup["xy_mm"])
        fr_me = float(np.sum(pup["weights_mm2"] * (~r["vignetted"][0])) / pup["area_mm2"])
        worst = max(worst, abs(fr_me / fr_rt - 1.0))
        assert 0.4 < fr_rt < 1.0
    assert worst < 0.02, worst                                                 # 1.7 % at 15 degrees (0.04 % at 10)


# --------------------------------------------------------------------------- scene
def _bilinear_ref(tex, X, Y, size):
    """Independent texture lookup (texel centres at (i + 0.5) / N), scalar."""
    H, W = tex.shape
    c = (X / size[0] + 0.5) * W - 0.5
    r = (0.5 - Y / size[1]) * H - 0.5
    c = min(max(c, 0.0), W - 1.0)
    r = min(max(r, 0.0), H - 1.0)
    c0, r0 = min(int(math.floor(c)), W - 2), min(int(math.floor(r)), H - 2)
    fc, fr = c - c0, r - r0
    return ((1 - fr) * ((1 - fc) * tex[r0, c0] + fc * tex[r0, c0 + 1]) + fr * ((1 - fc) * tex[r0 + 1, c0] + fc * tex[r0 + 1, c0 + 1]))


def test_checkerboard_plane_gives_the_texture_at_the_pinhole_projection():
    f, d = 50.0, 1000.0
    s = ideal(f, 5.0, d)
    m = RT.paraxial_trace(s)["magnification"]
    n, sq = 8, 5.0
    tex = np.kron(np.indices((n, n)).sum(axis=0) % 2, np.ones((16, 16))) * 0.8 + 0.1
    scene = LR.lens_scene([{"type": "plane", "z_mm": -d, "size_mm": (n * sq, n * sq), "albedo": tex}], [D_SCENE])
    rng = np.random.default_rng(3)
    px = np.stack([rng.uniform(-0.12, 0.12, 40), rng.uniform(-0.12, 0.12, 40)], 1)
    r = LR.trace_sensor_rays(s, px, [[0.0, 0.0]])
    o, dd = r["origin"][:, 0], r["direction"][:, 0]
    rad = LR.scene_radiance(o, dd, scene, 0.588)["radiance"][:, 0]
    X = px / m
    ref = np.array([_bilinear_ref(tex, X[i, 0], X[i, 1], (n * sq, n * sq)) * 1.0 / math.pi for i in range(40)])
    assert len(rad) == 40 and np.isfinite(rad).all()
    assert np.abs(rad - ref).max() < 1e-9 and ref.std() > 0.05, np.abs(rad - ref).max()


def test_sphere_silhouette_radius_matches_the_projection():
    f, d, a = 50.0, 1000.0, 20.0
    s = ideal(f, 5.0, d)
    sp = RT.paraxial_trace(s)["image_mm"]
    pitch, nn = 0.02, 161
    g = (np.arange(nn) - (nn - 1) / 2) * pitch
    X, Y = np.meshgrid(g, g)
    px = np.stack([X.ravel(), Y.ravel()], 1)
    scene = LR.lens_scene([{"type": "sphere", "center_mm": (0.0, 0.0, -d), "radius_mm": a, "albedo": 0.5}], [D_SCENE])
    r = LR.trace_sensor_rays(s, px, [[0.0, 0.0]])
    res = LR.scene_radiance(r["origin"][:, 0], r["direction"][:, 0], scene, 0.588)
    area_px = int(res["hit"].sum())
    r_px = math.sqrt(area_px / math.pi)
    pred_px = sp * math.tan(math.asin(a / d)) / pitch                          # the cone of the silhouette meets the sensor
    assert area_px > 500 and abs(r_px - pred_px) < 0.5, (r_px, pred_px)


def test_lambertian_never_exceeds_E_rho_over_pi_and_shadows_work():
    rho, E = 0.62, 3.7
    scene = LR.lens_scene([{"type": "plane", "z_mm": -500.0, "albedo": rho},
                           {"type": "sphere", "center_mm": (0.0, 0.0, -400.0), "radius_mm": 30.0, "albedo": rho}],
                          [{"type": "directional", "to_light": (0.2, 0.3, 1.0), "irradiance_W_m2_nm": E}])
    rng = np.random.default_rng(5)
    dd = rng.normal(size=(4000, 3))
    dd[:, 2] = -np.abs(dd[:, 2]) - 0.5
    o = np.zeros((4000, 3))
    out = LR.scene_radiance(o, dd, scene, [0.55])
    L = out["radiance"][out["hit"], 0]
    assert len(L) == 4000
    assert L.max() <= E * rho / math.pi * (1 + 1e-12)
    # the plane right behind the sphere (seen along the light direction) is in shadow: zero radiance, ambient off
    lv = np.array([0.2, 0.3, 1.0])
    lv /= np.linalg.norm(lv)
    c = np.array([0.0, 0.0, -400.0])
    hitp = c - lv * ((c[2] + 500.0) / lv[2])                                    # the plane point on the line from the light through the centre
    org = hitp + np.array([0.0, 0.0, 200.0])
    dr = (hitp - org) / np.linalg.norm(hitp - org)
    lit = LR.scene_radiance([org], [dr], scene, [0.55])["radiance"][0, 0]
    sc_ns = LR.lens_scene([{"type": "plane", "z_mm": -500.0, "albedo": rho},
                           {"type": "sphere", "center_mm": (0.0, 0.0, -400.0), "radius_mm": 30.0, "albedo": rho}],
                          [{"type": "directional", "to_light": (0.2, 0.3, 1.0), "irradiance_W_m2_nm": E}], shadows=False)
    unlit = LR.scene_radiance([org], [dr], sc_ns, [0.55])["radiance"][0, 0]
    assert lit == 0.0 and unlit > 0.1 * E * rho / math.pi
    # a surface facing the light reaches the bound exactly
    face = LR.scene_radiance([[0.0, 0.0, 0.0]], [[0.0, 0.0, -1.0]], LR.lens_scene([{"type": "plane", "z_mm": -50.0, "albedo": rho}], [D_SCENE]), 0.55)
    assert abs(face["radiance"][0, 0] - rho / math.pi) < 1e-15


def test_specular_lobe_normalisation_and_point_light_inverse_square():
    ks, sh = 0.4, 50.0
    sc = LR.lens_scene([{"type": "plane", "z_mm": -100.0, "albedo": 0.0, "specular": ks, "shininess": sh}],
                       [{"type": "directional", "to_light": (0.0, 0.0, 1.0), "irradiance_W_m2_nm": 1.0}])
    # looking straight down the light: n . h = 1, the lobe peak ks (s + 2) / (2 pi)
    pk = LR.scene_radiance([[0.0, 0.0, 0.0]], [[0.0, 0.0, -1.0]], sc, 0.55)["radiance"][0, 0]
    assert abs(pk - ks * (sh + 8.0) / (8.0 * math.pi)) < 1e-12
    # integrated over the outgoing hemisphere the lobe returns ks (energy-conserving Blinn lobe, cos(theta_l) = 1)
    th = np.linspace(0.0, 0.5 * math.pi - 1e-6, 4001)
    ph = np.linspace(0.0, 2 * math.pi, 361)[:-1]
    T, P_ = np.meshgrid(th, ph, indexing="ij")
    dirs = np.stack([np.sin(T) * np.cos(P_), np.sin(T) * np.sin(P_), -np.cos(T)], -1).reshape(-1, 3)
    # the camera direction v_out = -dir; rays travel to the surface, so the outgoing direction is -dir
    L = LR.scene_radiance(np.zeros_like(dirs) + np.array([0.0, 0.0, 0.0]), dirs, sc, 0.55)["radiance"][:, 0].reshape(T.shape)
    integral = np.trapezoid(np.mean(L, axis=1) * np.cos(th) * np.sin(th) * 2 * math.pi, th)
    assert abs(integral - ks) < 0.05 * ks, integral                           # the normalised lobe's albedo is ks to a few per cent
    p1 = LR.lens_scene([{"type": "plane", "z_mm": -100.0, "albedo": 1.0}], [{"type": "point", "position_mm": (0.0, 0.0, -50.0), "intensity_W_sr_nm": 2.0}])
    p2 = LR.lens_scene([{"type": "plane", "z_mm": -100.0, "albedo": 1.0}], [{"type": "point", "position_mm": (0.0, 0.0, 0.0), "intensity_W_sr_nm": 2.0}])
    a = LR.scene_radiance([[0.0, 0.0, -10.0]], [[0.0, 0.0, -1.0]], p1, 0.55)["radiance"][0, 0]
    b = LR.scene_radiance([[0.0, 0.0, -10.0]], [[0.0, 0.0, -1.0]], p2, 0.55)["radiance"][0, 0]
    assert abs(a / b - 4.0) < 1e-9                                            # 100 mm and 50 mm: inverse square


def test_spectral_albedo_rgb_anchors_and_tabulated_range():
    sc = LR.lens_scene([{"type": "sphere", "center_mm": (0, 0, -100.0), "radius_mm": 20.0, "albedo": (0.8, 0.5, 0.2)}], [D_SCENE])
    ray = ([[0.0, 0.0, 0.0]], [[0.0, 0.0, -1.0]])
    got = [LR.scene_radiance(*ray, sc, w)["radiance"][0, 0] * math.pi for w in (0.61, 0.54, 0.465)]
    assert np.allclose(got, [0.8, 0.5, 0.2], atol=1e-12)
    mid = LR.scene_radiance(*ray, sc, 0.575)["radiance"][0, 0] * math.pi
    assert 0.5 < mid < 0.8
    tab = LR.lens_scene([{"type": "sphere", "center_mm": (0, 0, -100.0), "radius_mm": 20.0, "albedo": {"nm": [500, 600], "value": [0.2, 0.6]}}], [D_SCENE])
    assert abs(LR.scene_radiance(*ray, tab, 0.55)["radiance"][0, 0] * math.pi - 0.4) < 1e-12
    with pytest.raises(ValueError, match="no extrapolation"):
        LR.scene_radiance(*ray, tab, 0.7)
    il = np.array([[400.0, 1.0], [500.0, 1.0], [600.0, 2.0], [700.0, 2.0]])
    base = LR.scene_radiance(*ray, sc, 0.65)["radiance"][0, 0]
    shaped = LR.scene_radiance(*ray, sc, 0.65, illuminant=il)["radiance"][0, 0]
    ref550 = np.interp(550.0, il[:, 0], il[:, 1])
    assert abs(shaped / base - np.interp(650.0, il[:, 0], il[:, 1]) / ref550) < 1e-12
    with pytest.raises(ValueError, match="no extrapolation"):
        LR.scene_radiance(*ray, sc, 0.65, illuminant=il[:2])


def test_mesh_moller_trumbore_matches_the_analytic_plane_and_the_barycentric_edges():
    V = np.array([[-10.0, -10.0, -100.0], [10.0, -10.0, -100.0], [10.0, 10.0, -100.0], [-10.0, 10.0, -100.0]])
    F = np.array([[0, 1, 2], [0, 2, 3]])
    mesh = LR.lens_scene([{"type": "mesh", "vertices_mm": V, "faces": F, "albedo": 0.5}], [D_SCENE])
    flat = LR.lens_scene([{"type": "plane", "z_mm": -100.0, "size_mm": (20.0, 20.0), "albedo": 0.5}], [D_SCENE])
    rng = np.random.default_rng(1)
    o = np.zeros((500, 3))
    d = np.stack([rng.uniform(-0.1, 0.1, 500), rng.uniform(-0.1, 0.1, 500), -np.ones(500)], 1)
    a = LR.scene_radiance(o, d, mesh, 0.55)
    b = LR.scene_radiance(o, d, flat, 0.55)
    assert a["hit"].sum() == 500 and np.array_equal(a["hit"], b["hit"])
    assert np.abs(a["t_mm"] - b["t_mm"]).max() < 1e-9 and np.abs(a["radiance"] - b["radiance"]).max() < 1e-12
    out = LR.scene_radiance([[0, 0, 0], [0, 0, 0]], [[0.11, 0, -1.0], [0, 0, 1.0]], mesh, 0.55)   # beyond the edge; behind the camera
    assert not out["hit"].any() and np.isinf(out["t_mm"]).all()
    with pytest.raises(ValueError, match="degenerate"):
        LR.lens_scene([{"type": "mesh", "vertices_mm": V, "faces": np.array([[0, 1, 1]])}])


def test_scene_builder_refuses_bad_scenes():
    for bad in ([{"type": "cube"}], [{"type": "sphere", "center_mm": (0, 0, -1), "radius_mm": -1.0}],
                [{"type": "sphere", "center_mm": (0, 0), "radius_mm": 1.0}], [{"type": "plane", "z_mm": -1, "colour": 1}],
                [{"type": "plane", "z_mm": -1, "albedo": -0.1}], [{"type": "plane", "z_mm": -1, "albedo": np.ones((3, 3))}],
                [{"type": "mesh", "vertices_mm": np.zeros((3, 3)), "faces": np.array([[0, 1, 5]])}]):
        with pytest.raises(ValueError):
            LR.lens_scene(bad)
    with pytest.raises(ValueError):
        LR.lens_scene([], [{"type": "spot"}])
    with pytest.raises(ValueError, match="in front of the lens"):
        LR.lens_scene([], [], sources=[{"position_mm": (0, 0, 5.0)}])
    with pytest.raises(ValueError):
        LR.scene_radiance([[0, 0, 0]], [[0, 0, 0]], LR.lens_scene(), 0.55)         # zero-length direction
    with pytest.raises(ValueError):
        LR.scene_radiance([[0, 0, 0]], [[0, 0, -1.0], [0, 0, -1.0]], LR.lens_scene(), 0.55)
    nan = LR.scene_radiance([[0, 0, 0], [np.nan, 0, 0]], [[0, 0, -1.0], [0, 0, -1.0]], LR.lens_scene(), 0.55)
    assert np.isfinite(nan["radiance"][0]).all() and np.isnan(nan["radiance"][1]).all()
    assert len(LR.lens_scene()["objects"]) == 2


# --------------------------------------------------------------------------- the photograph
def test_white_plane_irradiance_is_pi_L_sin2_and_photons_follow_the_closed_form():
    f, d, ap = 50.0, 1000.0, 5.0
    s = ideal(f, ap, d)
    sp = RT.paraxial_trace(s)["image_mm"]
    rho, wl = 0.5, 0.588
    scene = plane_scene(rho)
    pitch_um, t_exp, qe = 10.0, 1e-4, 0.55
    sens = {"size": (5, 5), "pixel_pitch_um": pitch_um, "qe": qe, "full_well": 65535.0, "read_noise_e": 0.0, "dark_e": 0.0, "bits": 16}
    r = LR.render_scene_through_lens(s, scene, sens, pupil_samples=256, wavelengths=[wl], exposure_s=t_exp, add_noise=False, band_nm=100.0)
    L = rho * 1.0 / math.pi                                                    # D_SCENE has E = 1 at normal incidence
    E_closed = math.pi * L * ap ** 2 / (ap ** 2 + sp ** 2)                     # pi L sin^2(alpha), the exit pupil is the lens
    assert abs(r["irradiance_W_m2_nm"][0][2, 2] / E_closed - 1.0) < 1e-3
    e_closed = E_closed * 100.0 * (pitch_um * 1e-6) ** 2 * t_exp * (wl * 1e-6 / (6.62607015e-34 * 299792458.0)) * qe
    assert abs(r["electrons_mean"][2, 2] / e_closed - 1.0) < 1e-3
    # 50 shot-noise repeats: the mean of the repeats is within 3 sigma of the expected electrons (counts are 1 e- per DN here)
    reps = np.array([LR.render_scene_through_lens(s, scene, sens, pupil_samples=16, wavelengths=[wl], exposure_s=t_exp, seed=k, band_nm=100.0)["image"][2, 2]
                     for k in range(50)]) * 65535.0
    mean_e = r["electrons_mean"][2, 2]
    assert mean_e > 200 and abs(reps.mean() - mean_e) < 3.0 * math.sqrt(mean_e / 50.0) + 0.5, (reps.mean(), mean_e)


def test_point_source_of_an_ideal_lens_is_one_pixel_with_the_closed_form_photon_count():
    f, d, ap = 50.0, 1000.0, 3.0
    s = ideal(f, ap, d)
    I, wl, t_exp, qe, pitch = 1.2e-8, 0.588, 1e-3, 0.5, 8.0
    sc = LR.lens_scene([], [], sources=[{"position_mm": (0.0, 0.0, -d), "intensity_W_sr_nm": I}])
    sens = {"size": (9, 9), "pixel_pitch_um": pitch, "qe": qe, "full_well": 65535.0, "read_noise_e": 0.0, "bits": 16}
    r = LR.render_scene_through_lens(s, sc, sens, wavelengths=[wl], exposure_s=t_exp, add_noise=False, band_nm=10.0)
    e = r["electrons_mean"]
    omega = 2.0 * math.pi * (1.0 - d / math.hypot(d, ap))                       # solid angle of the lens disc from the source
    e_closed = I * omega * 10.0 * t_exp * (wl * 1e-6 / (6.62607015e-34 * 299792458.0)) * qe
    assert e[4, 4] / e.sum() > 1.0 - 1e-9                                      # a single pixel
    assert abs(e[4, 4] / e_closed - 1.0) < 1e-6, (e[4, 4], e_closed)
    reps = np.array([LR.render_scene_through_lens(s, sc, sens, wavelengths=[wl], exposure_s=t_exp, seed=k, band_nm=10.0)["image"][4, 4]
                     for k in range(50)]) * 65535.0
    assert e_closed > 1000 and abs(reps.mean() - e_closed) < 3.0 * math.sqrt(e_closed / 50.0) + 0.5


def _edges(row, level=None):
    lo, hi = row.min(), row.max()
    mid = 0.5 * (lo + hi) if level is None else level
    k = np.nonzero((row[:-1] - mid) * (row[1:] - mid) < 0)[0]
    return k + (mid - row[k]) / (row[k + 1] - row[k])


def test_checkerboard_edges_follow_the_distortion_map():
    s = RT.lens_system([{"R": INF, "t": 12.0, "n": 1.0, "ap": 1.2}, {"R": 28.0, "t": 3.5, "n": (1.5168, 64.17), "ap": 15.0},
                        {"R": -120.0, "t": None, "n": 1.0, "ap": 15.0}], stop=0, object_mm=1000.0)
    para = RT.paraxial_trace(s)
    pitch, W = 12.0, 1201
    dm = LI.distortion_map(s, (3, W), pitch, fields=np.linspace(0.0, 160.0, 9))
    n, sq = 32, 20.0
    tex = np.tile(np.kron([[0.1, 0.9], [0.9, 0.1]], np.ones((20, 20))), (n // 2, n // 2))
    sc = LR.lens_scene([{"type": "plane", "point_mm": (0.0, 10.0, -1000.0), "size_mm": (n * sq, n * sq), "albedo": tex}], [D_SCENE])
    r = LR.render_scene_through_lens(s, sc, {"size": (3, W), "pixel_pitch_um": pitch}, pupil_samples=48, wavelengths=[0.588], add_noise=False, oversample=2)
    cols = _edges(r["electrons_mean"][1])
    cx = (W - 1) / 2
    xs = (cols - cx)                                                          # pixels, upright: increases with object x
    m = para["magnification"]
    X = np.arange(-n / 2 * sq, n / 2 * sq + 1, sq)
    ideal_px, pred_px = [], []
    for x in X:
        ri = abs(m * x)
        rr = ri + sum(c * ri ** p for c, p in zip(dm["coefficients"], dm["powers"]))
        ideal_px.append(math.copysign(ri, x) / (pitch * 1e-3))
        pred_px.append(math.copysign(rr, x) / (pitch * 1e-3))
    ideal_px, pred_px = np.array(ideal_px), np.array(pred_px)
    keep = np.abs(pred_px) < cx - 2
    ideal_px, pred_px = ideal_px[keep], pred_px[keep]
    assert len(xs) == len(pred_px) == 15
    assert np.abs(xs - pred_px).max() < 0.3, np.abs(xs - pred_px).max()
    assert np.abs(pred_px - ideal_px).max() > 4.0                              # the distortion is 5 px at the outer edge: not a vacuous gate
    # three field heights: the outer pair of edges at about 3 / 5 px of barrel
    far = np.abs(pred_px) > 90
    assert int(far.sum()) >= 4 and np.abs(xs[far] - pred_px[far]).max() < 0.3


def test_relative_illumination_follows_lensimage_to_two_percent_up_to_seven_tenths_field():
    s = triplet(rear=6.0, aim="stop")
    para = RT.paraxial_trace(s)
    pitch, W = 24.0, 801
    sc = LR.lens_scene([{"type": "plane", "z_mm": -20000.0, "albedo": 0.5}], [D_SCENE])
    r = LR.render_scene_through_lens(s, sc, {"size": (3, W), "pixel_pitch_um": pitch}, pupil_samples=200, wavelengths=[0.588],
                                     add_noise=False, pupil_pattern="hexapolar")
    E = r["irradiance_W_m2_nm"][0][1]
    cx = (W - 1) / 2
    diffs, fields = [], []
    for frac in (0.3, 0.5, 0.7):
        col = int(cx + frac * cx)
        fld = LI._field_for_radius(para, (col - cx) * pitch * 1e-3, True)
        ri = LI._relative_illumination(s, para, [0.0, fld], True, rings=12)[-1]
        diffs.append(abs(E[col] / E[int(cx)] / ri - 1.0))
        fields.append(fld)
    assert len(diffs) == 3 and fields[-1] > 7.0
    assert max(diffs) < 0.02, diffs                                            # 0.3 %, 0.8 %, 1.6 % at 3.3, 5.5, 7.7 degrees
    # beyond that the two models part: lensimage uses cos^4 of the object-space angle, the render the image-space one (3.2 % at 8.7 degrees)
    col = int(cx + 0.8 * cx)
    fld = LI._field_for_radius(para, (col - cx) * pitch * 1e-3, True)
    far = abs(E[col] / E[int(cx)] / LI._relative_illumination(s, para, [0.0, fld], True, rings=12)[-1] - 1.0)
    assert 0.01 < far < 0.06, far


def _edge_width_px(row, pitch):
    n = (row - row[:20].mean()) / (row[-20:].mean() - row[:20].mean())
    xs = (np.arange(len(row)) - (len(row) - 1) / 2) * pitch

    def cross(level):
        k = np.nonzero((n[:-1] < level) & (n[1:] >= level))[0][0]
        return xs[k] + (level - n[k]) / (n[k + 1] - n[k]) * (xs[k + 1] - xs[k])

    return (cross(0.9) - cross(0.1)) / pitch


def test_defocused_edge_width_is_the_disc_blur_closed_form():
    f, R = 50.0, 6.0
    s = ideal(f, R, 1000.0)
    sprime = lambda dist: f * dist / (dist - f)                                # noqa: E731
    pitch_um, W = 5.0, 301
    t2 = np.zeros((2, 4000))
    t2[:, 2000:] = 1.0
    widths, preds = [], []
    for dobj in (800.0, 1300.0):
        sc = LR.lens_scene([{"type": "plane", "z_mm": -dobj, "size_mm": (40.0, 40.0), "albedo": t2}], [D_SCENE])
        r = LR.render_scene_through_lens(s, sc, {"size": (3, W), "pixel_pitch_um": pitch_um}, pupil_samples=256, wavelengths=[0.588],
                                         add_noise=False, focus_mm=1000.0, oversample=2)
        widths.append(_edge_width_px(r["electrons_mean"][1], pitch_um * 1e-3))
        rho = R * abs(sprime(dobj) - sprime(1000.0)) / sprime(dobj)           # radius of the blur disc on the sensor
        x = np.linspace(-rho, rho, 200001)
        esf = 0.5 + (x * np.sqrt(np.clip(rho ** 2 - x ** 2, 0, None)) / rho ** 2 + np.arcsin(x / rho)) / math.pi
        preds.append((np.interp(0.9, esf, x) - np.interp(0.1, esf, x)) / (pitch_um * 1e-3))
    assert len(widths) == 2 and min(preds) > 19.0
    assert max(abs(w - p) for w, p in zip(widths, preds)) < 0.3, (widths, preds)
    # nearer is blurrier than the focus, and the focus is sharp: depth of field
    sc = LR.lens_scene([{"type": "plane", "z_mm": -1000.0, "size_mm": (40.0, 40.0), "albedo": t2}], [D_SCENE])
    sharp = LR.render_scene_through_lens(s, sc, {"size": (3, W), "pixel_pitch_um": pitch_um}, pupil_samples=64, wavelengths=[0.588],
                                         add_noise=False, focus_mm=1000.0, oversample=2)
    assert _edge_width_px(sharp["electrons_mean"][1], pitch_um * 1e-3) < 3.0 < min(widths)


def test_point_source_defocus_disc_diameter_is_two_delta_NA():
    f, d, ap = 50.0, 1000.0, 5.0
    s = ideal(f, ap, d)
    para = RT.paraxial_trace(s)
    pitch = 5.0
    sc = LR.lens_scene([], [], sources=[{"position_mm": (0.0, 0.0, -d), "intensity_W_sr_nm": 1e-3}])
    worst = 0.0
    for dz in (0.5, 1.0, 2.0):
        r = LR.render_scene_through_lens(s, sc, {"size": (201, 201), "pixel_pitch_um": pitch}, wavelengths=[0.588], defocus_mm=dz,
                                         add_noise=False, source_rings=40)
        e = r["electrons_mean"]
        plate = np.median(e[e > 0.5 * e.max()])
        dia = 2.0 * math.sqrt((e > 0.5 * plate).sum() / math.pi)
        pred = 2.0 * dz * para["na_image"] * 1000.0 / pitch
        worst = max(worst, abs(dia - pred))
        assert pred > 15
    assert worst < 1.0, worst


def test_cats_eye_is_the_intersection_of_two_discs_and_equals_the_vignetting():
    f, a1, a2, tb, d = 50.0, 5.0, 5.0, 20.0, 1000.0
    s = baffled(f, a1, a2, tb, d)
    sp = f * d / (d - f)
    k = tb / sp
    pup = LR.exit_pupil_samples(s, 2000, "hexapolar")
    rows = []
    for H in (100.0, 200.0):
        Iy = H * sp / d
        closed = disc_overlap(a1, a2 / (1 - k), k * Iy / (1 - k)) / (math.pi * a1 ** 2)
        b = LR.bokeh_shape(s, (0.0, H), 2.0, 1500)
        cr = RT.chief_ray(s, H)
        tr = LR.trace_sensor_rays(s, [[cr["image_x"], cr["image_y"]]], pup["xy_mm"])
        gate2 = float(np.sum(pup["weights_mm2"] * (~tr["vignetted"][0])) / pup["area_mm2"])
        rows.append((closed, b["area_ratio"], gate2, b["vignetting_factor"], b["symmetry_error_mm"]))
        assert b["polygon_xy_mm"].shape[1] == 2 and b["mask"].any() and b["mask"].shape == (64, 64)
    assert len(rows) == 2 and rows[1][0] < 0.7 < rows[0][0]
    for closed, area, g2, vf, sym in rows:
        assert abs(area / closed - 1.0) < 0.05 and abs(g2 / closed - 1.0) < 0.01 and abs(vf / closed - 1.0) < 0.05
        assert abs(area / g2 - 1.0) < 0.05
        assert sym < 1e-9                                                      # symmetric about the meridional plane
    # the same through the whole renderer: the footprint of a rendered point source
    foot = []
    for H in (0.0, 200.0):
        cen = tuple(LR.bokeh_shape(s, (0.0, H), 2.0, 800)["centroid_xy_mm"])
        sc = LR.lens_scene([], [], sources=[{"position_mm": (0.0, H, -d), "intensity_W_sr_nm": 1e-3}])
        r = LR.render_scene_through_lens(s, sc, {"size": (161, 161), "pixel_pitch_um": 5.0, "center_mm": cen}, wavelengths=[0.588],
                                         defocus_mm=2.0, add_noise=False, source_rings=60)
        e = r["electrons_mean"]
        foot.append(float((e > 0.5 * np.percentile(e[e > 0], 90)).sum()))
    assert abs(foot[1] / foot[0] / rows[1][0] - 1.0) < 0.05, (foot, rows[1][0])


def test_lateral_colour_follows_chromatic_shift():
    s = RT.lens_system([{"R": INF, "t": 20.0, "n": 1.0, "ap": 1.0}, {"R": 28.0, "t": 3.5, "n": (1.5168, 64.17), "ap": 15.0},
                        {"R": -120.0, "t": None, "n": 1.0, "ap": 15.0}], stop=0, object_mm=1000.0)
    m = RT.paraxial_trace(s)["magnification"]
    pitch, H = 15.0, 401
    Y = 2.1 / abs(m)                                                          # an edge at 0.7 of the 3 mm half height
    cs = RT.chromatic_shift(s, field=Y)
    tex = np.zeros((400, 400))
    tex[:200, :] = 0.9
    tex[200:, :] = 0.1
    sc = LR.lens_scene([{"type": "plane", "point_mm": (0.0, Y, -1000.0), "size_mm": (200.0, 200.0), "albedo": tex}], [D_SCENE])
    r = LR.render_scene_through_lens(s, sc, {"size": (H, 3), "pixel_pitch_um": pitch}, pupil_samples=64, add_noise=False, oversample=2)
    e = r["electrons_per_wavelength"][:, :, 1]
    cy = (H - 1) / 2
    ys = []
    for j in range(3):
        cr_ = _edges(e[j])
        ys.append((cr_[np.argmin(np.abs(cr_ - (cy - 2.1 / (pitch * 1e-3))))] - cy) * pitch * 1e-3)
    shift_px = (ys[0] - ys[2]) / (pitch * 1e-3)
    ref_px = cs["lateral_color"] / (pitch * 1e-3)
    assert abs(ref_px) > 0.8 and abs(shift_px - ref_px) < 0.3, (shift_px, ref_px)    # about 1 px of lateral colour, matched to 0.02 px


def test_render_is_deterministic_and_the_noiseless_image_ignores_the_seed():
    s = triplet(object_mm=1000.0)
    sc = LR.lens_scene()
    sens = {"size": (12, 16), "pixel_pitch_um": 12.0}
    a = LR.render_scene_through_lens(s, sc, sens, pupil_samples=8, seed=3)
    b = LR.render_scene_through_lens(s, sc, sens, pupil_samples=8, seed=3)
    c = LR.render_scene_through_lens(s, sc, sens, pupil_samples=8, seed=4)
    assert np.array_equal(a["image"], b["image"]) and np.array_equal(a["channels"], b["channels"])
    assert np.array_equal(a["image_noiseless"], c["image_noiseless"]) and np.array_equal(a["electrons_mean"], c["electrons_mean"])
    assert not np.array_equal(a["image"], c["image"]) and a["image"].max() > 0
    n0 = LR.render_scene_through_lens(s, sc, sens, pupil_samples=8, seed=3, add_noise=False)
    assert np.array_equal(n0["image"], n0["image_noiseless"])
    u = LR.render_scene_through_lens(s, sc, sens, pupil_samples=8, seed=3, output="uint16")
    assert u["image"].dtype == np.uint16 and u["image"].max() <= (1 << 12) - 1


def test_every_render_knob_changes_the_picture():
    s = triplet(object_mm=1000.0)
    scene = LR.lens_scene()
    sens = {"size": (10, 12), "pixel_pitch_um": 15.0}
    base = LR.render_scene_through_lens(s, scene, sens, pupil_samples=8, add_noise=False, focus_mm=1000.0)["electrons_mean"]
    variants = {
        "defocus": dict(defocus_mm=1.5), "pupil_samples": dict(pupil_samples=30), "exposure": dict(exposure_s=3e-4),
        "oversample": dict(oversample=3), "wavelengths": dict(wavelengths=[0.45, 0.6]), "pattern": dict(pupil_pattern="hexapolar"),
        "jitter": dict(pupil_jitter=False), "focus": dict(focus_mm=2000.0),
        "illuminant": dict(illuminant=np.array([[400.0, 1.0], [700.0, 3.0]])),
    }
    diffs = {}
    for name, kw in variants.items():
        kw2 = dict(add_noise=False, focus_mm=1000.0)
        kw2.update(dict(pupil_samples=8))
        kw2.update(kw)
        diffs[name] = float(np.abs(LR.render_scene_through_lens(s, scene, sens, **kw2)["electrons_mean"] - base).max() / base.max())
    assert len(diffs) == 9
    dead = [k for k, v in diffs.items() if v < 1e-6]
    assert dead == [], diffs
    sens2 = dict(sens, qe=0.3)
    assert abs(LR.render_scene_through_lens(s, scene, sens2, pupil_samples=8, add_noise=False, focus_mm=1000.0)["electrons_mean"].sum() / base.sum() - 0.5) < 1e-9


def test_pupil_transmission_is_the_disc_overlap_of_the_baffled_pupil():
    f, a1, a2, tb, d = 50.0, 5.0, 3.5, 20.0, 1000.0
    s = baffled(f, a1, a2, tb, d)
    sp = f * d / (d - f)
    k = tb / sp
    sc = plane_scene(0.5, z=-1000.0)
    r = LR.render_scene_through_lens(s, sc, {"size": (3, 3), "pixel_pitch_um": 4000.0}, pupil_samples=2000, wavelengths=[0.588], add_noise=False,
                                     pupil_pattern="hexapolar")
    pt = r["pupil_transmission"]
    closed = disc_overlap(a1, a2 / (1 - k), k * 4.0 / (1 - k)) / (math.pi * a1 ** 2)   # a pixel 4 mm off axis
    assert pt[1, 1] == pytest.approx(1.0, abs=1e-12) and 0.5 < closed < 0.95
    assert abs(pt[0, 1] / closed - 1.0) < 0.01 and abs(pt[1, 0] / closed - 1.0) < 0.01 and abs(pt[2, 1] / closed - 1.0) < 0.01


# --------------------------------------------------------------------------- the second implementation
def _brute_irradiance(surfs, nglass, z_img, z_xp, r_xp, uv, sx, sy, tex, plane_z, size, E, rho_scale):
    """Scalar renderer: spherical surfaces, vector Snell, a textured plane, a light along the axis. Shares nothing with lensrender."""
    zv, z = [], 0.0
    for s in surfs:
        zv.append(z)
        z += s["t"] if s["t"] is not None else 0.0
    ns_before = [1.0] + [s["n"] for s in surfs[:-1]]
    ns_after = [s["n"] for s in surfs]
    total = 0.0
    for (u, v) in uv:
        P = [sx, sy, z_img]
        T = [u * r_xp, v * r_xp, z_xp]
        D = [T[0] - P[0], T[1] - P[1], T[2] - P[2]]
        dist = math.sqrt(sum(c * c for c in D))
        D = [c / dist for c in D]
        weight = (abs(T[2] - P[2]) / dist) ** 2 / dist ** 2
        alive = True
        for i in range(len(surfs) - 1, -1, -1):
            Rr = surfs[i]["R"]
            c = [0.0, 0.0, zv[i] + Rr]
            oc = [P[k] - c[k] for k in range(3)]
            b = sum(oc[k] * D[k] for k in range(3))
            cc = sum(x * x for x in oc) - Rr * Rr
            disc = b * b - cc
            if disc < 0:
                alive = False
                break
            sq = math.sqrt(disc)
            tt = None
            for t in sorted((-b - sq, -b + sq)):
                Q = [P[k] + t * D[k] for k in range(3)]
                if t >= -1e-12 and (Q[2] - c[2]) * Rr < 0:                     # the cap that contains the vertex
                    tt = t
                    break
            if tt is None:
                alive = False
                break
            Q = [P[k] + tt * D[k] for k in range(3)]
            if math.hypot(Q[0], Q[1]) > surfs[i]["ap"]:
                alive = False
                break
            nrm = [(Q[k] - c[k]) / abs(Rr) for k in range(3)]
            if sum(nrm[k] * D[k] for k in range(3)) > 0:
                nrm = [-x for x in nrm]
            ci = -sum(nrm[k] * D[k] for k in range(3))
            eta = ns_after[i] / ns_before[i]
            s2 = eta * eta * (1 - ci * ci)
            if s2 > 1:
                alive = False
                break
            ct = math.sqrt(1 - s2)
            D = [eta * D[k] + (eta * ci - ct) * nrm[k] for k in range(3)]
            P = Q
        if not alive:
            continue
        t = (plane_z - P[2]) / D[2]
        X, Y = P[0] + t * D[0], P[1] + t * D[1]
        if abs(X) > size[0] / 2 or abs(Y) > size[1] / 2:
            continue
        L = rho_scale * _bilinear_ref(tex, X, Y, size) * E / math.pi
        total += L * weight
    return total


def test_second_implementation_scalar_renderer_matches_to_1e9():
    surfs = [{"R": 30.0, "t": 5.0, "n": 1.6, "ap": 5.0}, {"R": -45.0, "t": 15.0, "n": 1.0, "ap": 8.0}, {"R": -80.0, "t": None, "n": 1.0, "ap": 9.0}]
    sysd = RT.lens_system([dict(s) for s in surfs], stop=0, object_mm=INF)
    para = RT.paraxial_trace(sysd)
    z_last = 5.0 + 15.0
    z_img = z_last + para["image_mm"]
    z_xp = z_last + para["xp_position"]
    rng = np.random.default_rng(11)
    uv = []
    while len(uv) < 200:
        p = rng.uniform(-1, 1, 2)
        if p @ p <= 1:
            uv.append(p)
    uv = np.array(uv)
    tex = rng.uniform(0.1, 0.9, (40, 40))
    size = (900.0, 900.0)
    scene = LR.lens_scene([{"type": "plane", "z_mm": -2000.0, "size_mm": size, "albedo": tex}], [dict(D_SCENE, irradiance_W_m2_nm=1.3)])
    H, W, pitch = 12, 16, 60.0
    r = LR.render_scene_through_lens(sysd, scene, {"size": (H, W), "pixel_pitch_um": pitch}, pupil_uv=uv, wavelengths=[0.588],
                                     pupil_jitter=False, add_noise=False)
    irr = r["irradiance_W_m2_nm"][0]
    pix = [(int(a), int(b)) for a, b in zip(rng.integers(0, H, 20), rng.integers(0, W, 20))]
    worst = 0.0
    nalive = 0
    for (row, col) in pix:
        sx = -(col - (W - 1) / 2) * pitch * 1e-3
        sy = (row - (H - 1) / 2) * pitch * 1e-3
        ref = _brute_irradiance(surfs, None, z_img, z_xp, para["xp_radius"], uv, sx, sy, tex, -2000.0, size, 1.3, 1.0) * (math.pi * para["xp_radius"] ** 2 / len(uv))
        nalive += ref > 0
        worst = max(worst, abs(irr[row, col] - ref) / ref)
    assert len(pix) == 20 and nalive == 20
    assert worst < 1e-9, worst


# --------------------------------------------------------------------------- ghosts
def test_ghost_overlay_zero_reflectance_is_exactly_zero_and_the_energy_is_r2_times_transmission():
    s = triplet()
    pitch, n = 150.0, 600
    sens = {"size": (n, n), "pixel_pitch_um": pitch}
    z = LR.render_ghost_overlay(s, light_xy_mm=(1.0, 1.5), distance_mm=1000.0, sensor=sens, wavelengths=[0.588], reflectance=0.0, focus_mm=1000.0)
    assert z["overlay_electrons"].shape == (n, n) and z["overlay_electrons"].max() == 0.0 and z["overlay_electrons"].min() == 0.0
    assert z["image_electrons"].sum() > 0 and z["ghosts"] == []
    r = 0.04
    g = LR.render_ghost_overlay(s, light_xy_mm=(1.0, 1.5), distance_mm=1000.0, sensor=sens, wavelengths=[0.588], reflectance=r, focus_mm=1000.0, max_ghosts=15)
    assert len(g["ghosts"]) >= 12
    worst_closed, worst_energy, fitting = 0.0, 0.0, 0
    for row in g["ghosts"]:
        a, b = row["i"], row["j"]                                              # six refracting surfaces: record index = surface index
        closed = r * r * (1 - r) ** (2 * (b - a) - 2)                          # R_i R_j, and (b - a) - 1 surfaces crossed twice
        worst_closed = max(worst_closed, abs(row["energy_ratio"] / closed - 1.0))
        far = math.hypot(row["centroid_px"][0] - (n - 1) / 2, row["centroid_px"][1] - (n - 1) / 2) + 3.0 * row["radius_px"]
        if far < 0.95 * n / 2:                                                 # the whole ghost is on the sensor
            fitting += 1
            worst_energy = max(worst_energy, abs(row["spread_power_ratio"] / row["power_ratio"] - 1.0))
    assert worst_closed < 1e-9, worst_closed
    assert fitting >= 3 and worst_energy < 0.05, (fitting, worst_energy)       # the overlay carries energy_ratio x reach


def test_ghost_overlay_position_matches_raytrace3d():
    s = RT.lens_system([{"R": 60.0, "t": 6.0, "n": 1.5168, "ap": 8.0}, {"R": -60.0, "t": None, "n": 1.0, "ap": 8.0}], stop=0, object_mm=1000.0)
    pitch, n = 40.0, 300
    sens = {"size": (n, n), "pixel_pitch_um": pitch}
    light = (0.0, 12.0)
    g = LR.render_ghost_overlay(s, light_xy_mm=light, distance_mm=1000.0, sensor=sens, wavelengths=[0.588], reflectance=0.04, rings=14)
    assert len(g["ghosts"]) == 1                                               # two surfaces: one pair
    row = g["ghosts"][0]
    s3 = R3.noncoaxial_system(RT.with_wavelength(s, 0.588))
    ga = R3.ghost_analysis(s3, coatings={"R": 0.04}, field=light, rings=6)
    cen = np.array(ga["ghosts"][0]["centroid_xy"])
    cy, cx = (n - 1) / 2.0, (n - 1) / 2.0
    ref_px = np.array([cy + cen[1] / (pitch * 1e-3), cx - cen[0] / (pitch * 1e-3)])
    assert np.abs(np.array(row["centroid_px"]) - ref_px).max() < 0.5
    # and the brightest pixels of ghost_image for the same pair
    gi = R3.ghost_image(s3, coatings={"R": 0.04}, field=light, size=129, rings=14, log=False)
    assert gi.shape == (129, 129) and gi.max() > 0
    mp = np.array(g["main_image_px"])
    off_px = np.array(row["offset_px"])
    assert np.abs(np.array(row["centroid_px"]) - (mp + off_px)).max() < 1e-9
    base = np.ones((n, n))
    g2 = LR.render_ghost_overlay(s, light_xy_mm=light, distance_mm=1000.0, sensor=sens, wavelengths=[0.588], reflectance=0.04, rings=14, base_electrons=base)
    assert np.allclose(g2["electrons_with_ghosts"], base + g2["overlay_electrons"])


def test_ghost_overlay_refuses_bad_input():
    s = triplet()
    with pytest.raises(ValueError):
        LR.render_ghost_overlay(s)                                             # no light, no scene source
    with pytest.raises(ValueError):
        LR.render_ghost_overlay(s, light_xy_mm=(0.0, 0.0), reflectance=1.5)
    with pytest.raises(ValueError):
        LR.render_ghost_overlay(s, light_xy_mm=(0.0,))
    with pytest.raises(ValueError):
        LR.render_ghost_overlay(s, light_xy_mm=(0.0, 0.0), distance_mm=-5.0)
    with pytest.raises(ValueError):
        LR.render_ghost_overlay(s, light_xy_mm=(0.0, 0.0), base_electrons=np.zeros((2, 2)), sensor={"size": (8, 8)})


# --------------------------------------------------------------------------- comparing prescriptions
def _slanted_edge_scene(z=-1000.0):
    n = 600
    yy, xx = np.mgrid[0:n, 0:n]
    ang = math.radians(5.0)
    tex = np.where((xx - n / 2) * math.cos(ang) + (yy - n / 2) * math.sin(ang) > 0, 0.9, 0.1).astype(float)
    return LR.lens_scene([{"type": "plane", "z_mm": z, "size_mm": (12.0, 12.0), "albedo": tex}], [D_SCENE])


def test_compare_prescriptions_orders_the_pictures_like_spot_stats():
    good = triplet(object_mm=1000.0)
    bad = RT.lens_system([{"R": RS[i] * (1.0 if i != 3 else 1.5), "t": TS[i], "n": NS[i], "ap": (4.0 if i == 0 else 6.0)} for i in range(6)],
                         stop=0, aim="stop", object_mm=1000.0)
    sens = {"size": (60, 60), "pixel_pitch_um": 8.0}
    out = LR.render_compare_prescriptions([good, bad], _slanted_edge_scene(), sens, labels=["good", "detuned"], edge_roi=(10, 50, 10, 50),
                                          pupil_samples=48, wavelengths=[0.588], add_noise=False, focus_mm=1000.0, oversample=2)
    t = out["table"]
    assert len(t) == 2 and out["labels"] == ["good", "detuned"] and len(out["images"]) == 2
    spots = [RT.spot_stats(sy, field=0.0, rings=6)["rms_radius"] for sy in (good, bad)]
    assert spots[0] < spots[1]
    assert t[0]["rms_spot_um"][0] < t[1]["rms_spot_um"][0]                     # the table orders the prescriptions as spot_stats does
    assert np.argsort([r["rms_spot_um"][0] for r in t]).tolist() == np.argsort(spots).tolist()
    assert all(abs(r["rms_spot_um"][0] - 1000.0 * sp_) < 1e-9 for r, sp_ in zip(t, spots))
    # the rendered slanted edge agrees: the sharper prescription has the narrower 10-90 % edge
    assert t[0]["edge_width_10_90_px"] < t[1]["edge_width_10_90_px"]
    assert all(np.isfinite(r["relative_illumination_corner"]) and np.isfinite(r["distortion_pct"]) for r in t)
    with pytest.raises(ValueError):
        LR.render_compare_prescriptions([good], _slanted_edge_scene(), sens)
    with pytest.raises(ValueError):
        LR.render_compare_prescriptions([good, bad], _slanted_edge_scene(), sens, labels=["only one"])


# --------------------------------------------------------------------------- refusals
def test_render_refuses_what_it_cannot_do():
    s = triplet()
    sc = LR.lens_scene()
    for bad in (dict(sensor={"size": (0, 4)}), dict(sensor={"pixel_pitch_um": -1.0}), dict(sensor={"qe": 1.5}), dict(sensor={"colour": 1}),
                dict(pupil_samples=0), dict(wavelengths=[0.5, 0.5]), dict(wavelengths=[100.0]), dict(exposure_s=0.0), dict(seed=-1),
                dict(oversample=0), dict(pupil_pattern="grid"), dict(output="png"), dict(add_noise="yes"), dict(focus_mm=-5.0),
                dict(illuminant=np.array([[500.0, 1.0], [510.0, 1.0]])), dict(pupil_uv=np.array([[2.0, 0.0]]))):
        with pytest.raises(ValueError):
            LR.render_scene_through_lens(s, sc, **bad)
    with pytest.raises(ValueError):
        LR.render_scene_through_lens(s, {"kind": "other"})
    with pytest.raises(ValueError):
        LR.render_scene_through_lens(s, sc, {"size": (4096, 4096)}, pupil_samples=8192, oversample=16)
    tilted = RT.lens_system([{"R": 40.0, "t": 4.0, "n": 1.5, "ap": 6.0, "tilt": (0.0, 0.5)}, {"R": INF, "t": None, "n": 1.0, "ap": 6.0}], stop=0)
    srcs = LR.lens_scene([], [], sources=[{"position_mm": (0.0, 5.0, -500.0)}])
    with pytest.raises(ValueError, match="axisymmetric"):
        LR.render_scene_through_lens(tilted, srcs, {"size": (4, 4)}, pupil_samples=4)
    with pytest.raises(ValueError, match="axisymmetric"):
        LR.bokeh_shape(tilted)
    with pytest.raises(ValueError):
        LR.bokeh_shape(triplet(), (0.0, 8.0, 1.0))
    with pytest.raises(ValueError, match="fully vignetted"):
        LR.bokeh_shape(triplet(rear=2.0), (0.0, 40.0), 1.0, 200)


def test_default_calls_of_every_op_run():
    s = RT.lens_system()
    assert LR.exit_pupil_samples(s)["n"] > 0
    assert LR.trace_sensor_rays(s)["origin"].shape[:2] == (2, 7)
    assert LR.scene_radiance()["radiance"].shape == (5, 3)
    assert LR.lens_scene()["kind"] == "lens_scene"
    out = LR.render_scene_through_lens(s)
    assert out["image"].shape == (48, 64) and out["channels"].shape == (3, 48, 64)
    assert LR.bokeh_shape(s)["area_mm2"] > 0
    assert len(LR.render_compare_prescriptions(sensor={"size": (12, 16)}, pupil_samples=4)["table"]) == 2
    assert LR.render_ghost_overlay(RT.lens_system(), light_xy_mm=(0.0, 5.0))["overlay_electrons"].shape == (48, 64)
