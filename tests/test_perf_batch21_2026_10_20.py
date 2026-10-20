"""性能レビュー第21便の旧実装一致ゲート。"""
from __future__ import annotations

import heapq
import hashlib
import itertools
import math

import numpy as np
import pytest
from scipy.special import j0, j1

import agvfleet as AF
import carpath as CP
import cavityoptics as CO
import fiberoptics as FO
import illumdesign as ID
import telecentric as TC
import temsim as TEM


def _fiber_lp_modes_old(v_number):
    V = float(v_number)
    modes = []
    for l in range(400):
        if l == 0:
            cutoffs = [0.0] + list(FO.special.jn_zeros(1, 400))
        elif l == 1:
            cutoffs = list(FO.special.jn_zeros(0, 400))
        else:
            cutoffs = list(FO.special.jn_zeros(l - 1, 400))
        cutoffs = [c for c in cutoffs if c < V]
        if not cutoffs:
            break
        poles = list(FO.special.jn_zeros(l, 400))
        for m, c in enumerate(cutoffs, start=1):
            nxt = min([p for p in poles if p > c + 1e-12] + [V])
            lo, hi = c + 1e-12, min(nxt, V) - 1e-12
            if hi <= lo:
                continue
            flo, fhi = FO._lp_eq(l, V, lo), FO._lp_eq(l, V, hi)
            if not (np.isfinite(flo) and np.isfinite(fhi)) or flo * fhi > 0:
                continue
            for _ in range(80):
                mid = 0.5 * (lo + hi)
                fm = FO._lp_eq(l, V, mid)
                if flo * fm <= 0:
                    hi, fhi = mid, fm
                else:
                    lo, flo = mid, fm
            u = 0.5 * (lo + hi)
            modes.append((l, m, u, math.sqrt(max(V * V - u * u, 0.0)), c))
    return sorted(modes, key=lambda x: -(1.0 - (x[2] / V) ** 2))


@pytest.mark.parametrize("v", [2.0, 5.0, 10.0, 25.0, 60.0])
def test_148_fiber_bisection_stagnation_is_exact(v):
    old = _fiber_lp_modes_old(v)
    new = FO.fiber_lp_modes(v)["modes"]
    assert [(x[0], x[1]) for x in old] == [(x["l"], x["m"]) for x in new]
    np.testing.assert_allclose([(x[2], x[3], x[4]) for x in old],
                               [(x["u"], x["w"], x["cutoff_v"]) for x in new], rtol=0, atol=1e-12)


def _pdh_old(**kwargs):
    L = kwargs.get("length_m", 1.0)
    t1, t2 = kwargs.get("itm_transmittance", .01), kwargs.get("etm_transmittance", .01)
    om, beta, power = kwargs.get("mod_freq_hz", 2e7), kwargs.get("mod_depth", 1.08), kwargs.get("power_w", 1.)
    span, n = kwargs.get("span_linewidths", 6.), kwargs.get("n_points", 1201)
    r1, r2, _, _ = CO._mirrors(t1, t2, 0., 0., "test")
    response = CO.fabry_perot_response(L, 1064., itm_transmittance=t1, etm_transmittance=t2)
    delta = np.linspace(-span * response["linewidth_hz"], span * response["linewidth_hz"], n)
    fw = CO._reflection_coefficient(delta, response["fsr_hz"], r1, r2)
    fp = CO._reflection_coefficient(delta + om, response["fsr_hz"], r1, r2)
    fm = CO._reflection_coefficient(delta - om, response["fsr_hz"], r1, r2)
    pc = j0(beta) ** 2 * power
    ps = j1(beta) ** 2 * power
    return np.stack((delta, 2 * np.sqrt(pc * ps) * np.imag(fw * np.conj(fp) - np.conj(fw) * fm)), axis=1)


def test_150_pdh_reused_phase_matches_three_exponentials():
    kwargs = dict(length_m=.73, itm_transmittance=.013, etm_transmittance=.006,
                  mod_freq_hz=18.7e6, n_points=1201)
    np.testing.assert_allclose(CO.pdh_error_signal(**kwargs), _pdh_old(**kwargs), rtol=0, atol=1e-14)


def _chi_old(kx, ky, lam, cs, df_u, df_v, ang, ps):
    k2 = kx * kx + ky * ky
    alpha = np.arctan2(ky, kx)
    dfa = .5 * (df_u + df_v + (df_u - df_v) * np.cos(2 * (alpha - ang)))
    return math.pi * lam * k2 * dfa - .5 * math.pi * cs * lam ** 3 * k2 * k2 + ps, dfa


def test_158_chi_cartesian_form_including_dc():
    kx, ky = TEM._freq(65, 64, .83)
    old = _chi_old(kx, ky, .0197, 2.7e7, 10053., 9947., .731, .13)
    new = TEM._chi(kx, ky, .0197, 2.7e7, 10053., 9947., .731, .13)
    np.testing.assert_allclose(new[0], old[0], rtol=0, atol=1e-12)
    old_ctf = -np.sin(old[0] + math.asin(.07)) * TEM._envelope(
        np.hypot(kx, ky), old[1], .0197, 2.7e7, .001, 20.)
    new_ctf = -np.sin(new[0] + math.asin(.07)) * TEM._envelope(
        np.hypot(kx, ky), new[1], .0197, 2.7e7, .001, 20.)
    np.testing.assert_allclose(new_ctf, old_ctf, rtol=0, atol=1e-12)


def test_170_axis_bundle_is_evaluated_once(monkeypatch):
    system = TC.telecentric_lens("object")
    old_bundle = TC._bundle
    calls = []
    def counted(s, h, dz, samples):
        calls.append(h)
        return old_bundle(s, h, dz, samples)
    monkeypatch.setattr(TC, "_bundle", counted)
    out = TC.vignetting_vs_field(system, n_points=5, samples=21)
    assert calls.count(0.0) == 1
    assert out[0, 1] == 1.0


def _st_astar_old(g, start, goal, dist, horizon):
    parent = {(start, 0): None}; best = {(start, 0): 0}; closed = set(); tie = itertools.count()
    openl = [(float(dist[start]), 0, 0, next(tie), start, 0)]; generated = 1
    while openl:
        _, nconf, _, _, v, t = heapq.heappop(openl)
        if (v, t) in closed: continue
        closed.add((v, t))
        if v == goal:
            path=[]; node=(v,t)
            while node is not None: path.append(node[0]); node=parent[node]
            return path[::-1], generated
        if t >= horizon: continue
        for dr, dc in AF._MOVES:
            w=(v[0]+dr,v[1]+dc); nt=t+1
            if not (0 <= w[0] < g.shape[0] and 0 <= w[1] < g.shape[1]) or not g[w]: continue
            key=(w,nt)
            if key in closed or nconf >= best.get(key, 1 << 30): continue
            best[key]=nconf; parent[key]=(v,t); generated += 1
            heapq.heappush(openl,(nt+float(dist[w]),nconf,nt,next(tie),w,nt))
    return None, generated


def test_175_horizon_lower_bound_keeps_path_and_reduces_generated(monkeypatch):
    g = np.ones((9, 9), bool); goal = (8, 8); dist = AF.grid_distances(g, goal)
    old_path, old_generated = _st_astar_old(g, (0, 0), goal, dist, 16)
    pushes = 0; real_push = AF.heapq.heappush
    def counted(heap, item):
        nonlocal pushes
        pushes += 1; return real_push(heap, item)
    monkeypatch.setattr(AF.heapq, "heappush", counted)
    new_path = AF._st_astar(g, (0, 0), goal, dist, set(), set(), 16)
    assert new_path == old_path
    assert pushes + 1 < old_generated


def _irradiance_old(points, normals, emitters, directions, intensity, exponent):
    vector = points[:, None, :] - emitters[None, :, :]
    d2 = np.sum(vector * vector, axis=2); d = np.sqrt(d2)
    with np.errstate(invalid="ignore", divide="ignore"):
        unit = vector / d[:, :, None]
        ce = np.sum(unit * directions[None, :, :], axis=2)
        cs = -np.sum(unit * normals[:, None, :], axis=2)
        value = intensity * np.clip(ce, 0, None) ** exponent * np.clip(cs, 0, None) / d2
    return np.where(d2 > 0, value, 0).sum(1)


def test_151_152_irradiance_without_unit_vectors_or_tiled_normals():
    light = ID.light_source(kind="ring", radius_mm=18, height_mm=25, n=24)
    emitters, directions, intensity, exponent = ID._check_light(light)
    points = np.array([[0., 0., 0.], [3., -2., 1.], emitters[0]])
    normals = np.broadcast_to([0., 0., 1.], points.shape)
    np.testing.assert_allclose(ID._irradiance_at(points, normals, emitters, directions, intensity, exponent),
                               _irradiance_old(points, normals, emitters, directions, intensity, exponent),
                               rtol=0, atol=1e-12)
    image = ID.irradiance_map(light, shape=(31, 33))
    assert np.isfinite(image).all()


def test_155_zero_specular_keeps_validation_and_diffuse_result():
    normals = np.zeros((24, 25, 3)); normals[..., 2] = 1
    light = ID.solid_angle_light(30, n=1)
    a = ID.solid_angle_render(normals, light, f0=0, diffuse_albedo=.4, n_samples=64)
    b = ID.solid_angle_render(normals, light, f0=1, diffuse_albedo=.4, n_samples=64)
    expected_diffuse = .4 * math.sin(math.radians(30)) ** 2
    np.testing.assert_allclose(a, expected_diffuse, rtol=0, atol=1e-15)
    np.testing.assert_allclose(b - a, 1.0, rtol=0, atol=1e-15)
    with pytest.raises(ValueError):
        ID.solid_angle_render(normals, light, f0=0, diffuse_albedo=2)


def _tem_power_spectrum_old(image, tile=64, overlap=.5):
    spectra = TEM._tile_spectra(image, tile, overlap)
    return np.fft.fftshift(np.mean(spectra, axis=0))


def test_156_streamed_power_spectrum_matches_stacked_mean():
    image = np.random.default_rng(156).normal(size=(192, 192))
    old = _tem_power_spectrum_old(image)
    np.testing.assert_allclose(TEM.tem_power_spectrum(image, tile=64), old, rtol=0, atol=1e-12)


def test_160_float32_multislice_matches_float64_stack():
    stack = np.random.default_rng(160).normal(size=(5, 32, 32)).astype(np.float32)
    new = TEM.tem_multislice(stack)
    old = TEM.tem_multislice(stack.astype(np.float64))
    for key in ("exit_wave", "intensity", "projection_wave"):
        np.testing.assert_array_equal(new[key], old[key])


def test_164_element_groups_keep_projected_potential():
    atoms = np.array([[1.2, 2.3], [4.5, 3.2], [7.1, 8.2], [5.4, 6.3]])
    elements = ["C", "O", "C", "Si"]
    got = TEM.tem_projected_potential(atoms, elements, shape=32, pixel_A=.8)
    old = _tem_projected_potential_old(atoms, elements, shape=32, pixel_A=.8)
    np.testing.assert_allclose(got, old, rtol=0, atol=1e-12)


def _tem_projected_potential_old(atoms, elements, shape=256, pixel_A=.5):
    xy = np.asarray(atoms, dtype=np.float64)
    ny, nx = (shape, shape) if np.isscalar(shape) else shape
    px = float(pixel_A)
    el = [elements] * len(xy) if isinstance(elements, str) else list(elements)
    kx, ky = TEM._freq(ny, nx, px)
    q = np.hypot(kx, ky)
    transfer = np.sinc(kx * px) ** 2 * np.sinc(ky * px) ** 2
    out = np.zeros((ny, nx), dtype=np.complex128)
    for name in sorted(set(el)):
        idx = np.array([element == name for element in el])
        form = TEM._electron_form_factor(name, q / 2.)
        out += np.fft.fft2(TEM._splat(xy[idx], ny, nx, px)) * form / transfer
    return TEM.POTENTIAL_CONST * np.fft.ifft2(out).real / (px * px)


def test_176_180_hybrid_astar_random_maps_keep_path_and_expansion_sequence():
    expected = [
        (13, "24a0465142cacde2", "996ebd98ce7a9a6f"), (123, "86577c002c41278f", "e7d660f26fc100a9"),
        (13, "36d21aac7b1afc14", "c2010acd2903aaf4"), (27, "79512c2429f292e5", "14f5c8151fd51097"),
        (15, "a511b6b737393c6b", "6244ad65c7abe87d"), (1, "bd66f9a34ae53532", "c318351838478b00"),
        (31, "3bc29dc9e19f8d7c", "c12186100ec65825"), (5, "0e256e568f7b578e", "5ccf6328cdfec492"),
        (39, "52b6a0670397d5e9", "a713579791b37e64"), (15, "e72bf889a8151246", "34c6fefba181d8d9"),
        (135, "08123c2876743787", "4bd0902f62c0bb12"), (153, "39804dc10afb035c", "60c746353fb90cb2"),
        (1, "bd66f9a34ae53532", "c318351838478b00"), (1, "bd66f9a34ae53532", "c318351838478b00"),
        (5, "b56a1e087b39672c", "152aabc369bcd971"), (31, "07d11c63fd638ece", "e2b5bf6c4e3383ed"),
        (5, "82681fd7ec9dc682", "ffaf02eba3952d82"), (33, "7593ec5cba0d719f", "14ff34002eba6f57"),
        (13, "e47a70b53e68881f", "7fcca667d029c921"), (13, "4e739b8f7e036f60", "a623f03e0dfade20"),
    ]
    rng = np.random.default_rng(21176)
    poses = np.array([[1.5, 1.5, .15], [16.5, 16.5, -.2]])
    for want in expected:
        occupancy = rng.random((18, 18)) < .08
        occupancy[1:4, 1:4] = False
        occupancy[-4:-1, -4:-1] = False
        got = CP.car_hybrid_astar(occupancy, poses, radius=2., cell=1., shot_every=2,
                                  max_expansions=20_000, return_tree=True)
        path_hash = hashlib.sha256(np.asarray(got["points"]).tobytes()).hexdigest()[:16]
        tree_hash = hashlib.sha256(np.asarray(got["tree"]).tobytes()).hexdigest()[:16]
        assert (got["n_expanded"], path_hash, tree_hash) == want
