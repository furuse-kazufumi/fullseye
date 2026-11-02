# -*- coding: utf-8 -*-
"""polar_gpu の一致の門: optics / photoelastic / sfpolar、mueller_checks、Malus と Fresnel の閉形式。"""
import math

import numpy as np
import pytest

torch = pytest.importorskip("torch")

import lens_gpu as LG  # noqa: E402
import lensfile  # noqa: E402
import optics  # noqa: E402
import photoelastic  # noqa: E402
import polar_gpu as P  # noqa: E402
import raytrace as RT  # noqa: E402
import sfpolar  # noqa: E402

skip_gpu = pytest.mark.skipif(not LG.gpu_available(), reason="CUDA GPU 不在")
INF_ = float("inf")


@pytest.mark.parametrize("kind", ["polarizer", "retarder", "quarter_wave", "half_wave", "rotator"])
def test_jones_elements_match(kind):
    a = np.linspace(-90.0, 180.0, 13)
    got = P.jones_element_batch(kind, a, 57.0).numpy()
    ref = np.stack([optics.jones_element(kind, float(x), 57.0) for x in a])
    np.testing.assert_allclose(got, ref, atol=1e-14)


@pytest.mark.parametrize("kind", ["polarizer", "retarder", "quarter_wave", "half_wave", "rotator", "depolarizer"])
def test_mueller_elements_match_and_are_physical(kind):
    a = np.linspace(-90.0, 180.0, 13)
    got = P.mueller_element_batch(kind, a, 57.0).numpy()
    ref = np.stack([optics.mueller_element(kind, float(x), 57.0) for x in a])
    np.testing.assert_allclose(got, ref, atol=1e-14)
    for m in got:
        c = optics.mueller_checks(m)
        assert c["physical"] and c["passive"]


def test_chain_and_apply_match_cpu_and_malus():
    th = np.linspace(0.0, 180.0, 37)
    pol0 = P.mueller_element_batch("polarizer", 0.0)
    pol1 = P.mueller_element_batch("polarizer", th)
    m = P.chain([pol0, pol1])
    s = torch.as_tensor([1.0, 0.0, 0.0, 0.0], dtype=torch.float64)
    out = P.mueller_apply_batch(m, s).numpy()
    np.testing.assert_allclose(out[:, 0], 0.5 * np.cos(np.radians(th)) ** 2, atol=1e-15)
    ref = np.stack([optics.mueller_apply(optics.mueller_element("polarizer", float(t)) @ optics.mueller_element("polarizer", 0.0),
                                         [1.0, 0.0, 0.0, 0.0]) for t in th])
    np.testing.assert_allclose(out, ref, atol=1e-15)


def test_jones_malus_and_stokes_from_jones():
    th = np.linspace(0.0, 180.0, 37)
    J = P.jones_element_batch("polarizer", th)
    e = torch.as_tensor([1.0 + 0j, 0.0], dtype=torch.complex128)
    out = (J @ e[..., None])[..., 0]
    np.testing.assert_allclose((out.abs() ** 2).sum(-1).numpy(), np.cos(np.radians(th)) ** 2, atol=1e-15)
    v = np.array([[1.0, -1j], [1.0, 2.0 + 1j], [0.3j, 0.0]])
    got = P.stokes_from_jones_batch(torch.as_tensor(v)).numpy()
    np.testing.assert_allclose(got, np.stack([optics.stokes_from_jones(x) for x in v]), atol=1e-15)


def test_jones_to_mueller_equals_mueller_element():
    for kind in ("polarizer", "retarder", "quarter_wave", "half_wave", "rotator"):
        a = np.linspace(0.0, 170.0, 8)
        got = P.jones_to_mueller(P.jones_element_batch(kind, a, 40.0)).numpy()
        ref = P.mueller_element_batch(kind, a, 40.0).numpy()
        np.testing.assert_allclose(got, ref, atol=1e-13)


def test_mueller_apply_refuses_unphysical():
    with pytest.raises(ValueError, match="unphysical"):
        P.mueller_apply_batch(torch.eye(4, dtype=torch.float64), torch.as_tensor([1.0, 2.0, 0.0, 0.0], dtype=torch.float64))


def test_stokes_analyze_matches_scalar():
    s = np.array([[1, 1, 0, 0], [1, -1, 0, 0], [1, 0, 1, 0], [1, 0, 0, 1], [1, 0, 0, 0], [2, 1, 0, 0],
                  [1.0, 0.3, -0.4, 0.2], [1.0, 1e-13, 0.0, 8.7e-17], [3.0, -1.0, -1.0, -1.0]], float)
    r = P.stokes_analyze_batch(torch.as_tensor(s))
    for i, row in enumerate(s):
        c = optics.stokes_analyze(row)
        for k in ("intensity", "dop", "dolp", "docp"):
            assert abs(float(r[k][i]) - c[k]) < 1e-14
        for k in ("azimuth_deg", "ellipticity_deg"):
            if c[k] is None:
                assert math.isnan(float(r[k][i]))
            else:
                assert abs(float(r[k][i]) - c[k]) < 1e-12
        assert float(r["handedness"][i]) == {"right": 1.0, "left": -1.0, "linear": 0.0}[c["handedness"]]


def test_demosaic_matches_cpu_bit_for_bit_scale():
    rng = np.random.default_rng(0)
    raw = rng.random((2, 64, 48))
    got = P.polarization_demosaic_batch(raw).numpy()
    for b in range(2):
        np.testing.assert_allclose(got[b], optics.polarization_demosaic(raw[b]), atol=1e-13)
    lay = ((0.0, 45.0), (135.0, 90.0))
    np.testing.assert_allclose(P.polarization_demosaic_batch(raw[0], lay).numpy(),
                               optics.polarization_demosaic(raw[0], lay), atol=1e-13)


def test_photoelastic_images_match():
    d = np.random.default_rng(1).uniform(-6.0, 6.0, (20, 30))
    th = np.random.default_rng(2).uniform(0.0, 180.0, (20, 30))
    for an in ("camera4", "stokes6"):
        ref = photoelastic.photoelastic_polarization_images(d, th, an, 2.5)
        got = P.photoelastic_images_batch(d, th, an, 2.5).numpy()
        np.testing.assert_allclose(got, ref, atol=1e-13)


def _normals(H=40, W=50):
    y, x = np.mgrid[-0.6:0.6:H * 1j, -0.6:0.6:W * 1j]
    z = np.sqrt(1.0 - x * x - y * y)
    return np.stack([x, y, z], -1)


def test_sfp_render_matches():
    n = _normals()
    for rs, rd in ((1.0, 0.0), (0.0, 1.0), (0.7, 0.3)):
        ref = sfpolar.sfp_render(n, 1.5, rs, rd)
        got = P.sfp_render_batch(n, 1.5, rs, rd).numpy()
        np.testing.assert_allclose(got, ref, atol=1e-13)


@pytest.mark.parametrize("model", ["diffuse", "specular"])
def test_dolp_to_zenith_matches(model):
    rho = np.random.default_rng(3).uniform(0.0, 1.0, (16, 16))
    if model == "diffuse":
        rho = rho * 0.45
    rho[0, 0] = 1.0
    c = sfpolar.dolp_to_zenith(rho, 1.5, model, out_of_range="clamp")
    r = P.dolp_to_zenith_batch(rho, 1.5, model)
    np.testing.assert_allclose(r["zenith_deg"].numpy(), c["zenith_deg"], atol=1e-10)
    np.testing.assert_array_equal(r["n_solutions"].numpy(), c["n_solutions"])


def _interface(n2=1.5):
    return RT.lens_system([{"R": INF_, "t": None, "n": n2, "ap": 100.0}], stop=0, image_mm=10.0)


def _rays_at(theta_deg):
    th = np.radians(np.asarray(theta_deg, float))
    z = torch.zeros(1, 1, len(th), dtype=torch.float64)
    return (z, z, z - 1.0), (z, torch.as_tensor(np.sin(th))[None, None], torch.as_tensor(np.cos(th))[None, None])


def _polarized_rays(lens, Pp, D):
    """瞳の格子を使わず任意の光線で polarized の visitor を通す(閉形式の検算用)。"""
    para = LG.paraxial_batch(lens)

    def fake_launch(_l, px, py, field, p, fill=1.0):
        return Pp, D, torch.zeros_like(Pp[0])

    orig = LG.launch_batch
    LG.launch_batch = fake_launch
    try:
        n = Pp[0].shape[-1]
        b = P.polarized_bundle(lens, field=0.0, rings=1) if n == 7 else None
    finally:
        LG.launch_batch = orig
    return b, para


def test_fresnel_single_surface_closed_form_and_brewster():
    """1 面の s / p の電力透過率が教科書の式に一致。ブルースター角で T_p = 1。"""
    n2 = 1.5
    th = [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, math.degrees(math.atan(n2))]
    lens = LG.compile_lens(_interface(n2), device="cpu")
    Pp, D = _rays_at(th)
    b, _ = _polarized_rays(lens, Pp, D)
    ti = np.radians(th)
    tt = np.arcsin(np.sin(ti) / n2)
    rs = ((np.cos(ti) - n2 * np.cos(tt)) / (np.cos(ti) + n2 * np.cos(tt))) ** 2
    rp = ((n2 * np.cos(ti) - np.cos(tt)) / (n2 * np.cos(ti) + np.cos(tt))) ** 2
    np.testing.assert_allclose(b["T_s_product"][0, 0].numpy(), 1.0 - rs, rtol=1e-13)
    np.testing.assert_allclose(b["T_p_product"][0, 0].numpy(), 1.0 - rp, rtol=1e-13)
    assert abs(float(b["T_p_product"][0, 0, -1]) - 1.0) < 1e-13
    # 入射面は y-z。x 偏光が s、y 偏光が p。Jones の対角が √T
    J = b["jones"][0, 0].numpy()
    np.testing.assert_allclose(np.abs(J[:, 0, 0]), np.sqrt(1.0 - rs), rtol=1e-12)
    np.testing.assert_allclose(np.abs(J[:, 1, 1]), np.sqrt(1.0 - rp), rtol=1e-12)
    assert np.abs(J[:, 0, 1]).max() < 1e-13 and np.abs(J[:, 1, 0]).max() < 1e-13


def test_mirror_is_lossless_and_keeps_field_transverse():
    s = RT.example_system("paraboloid")
    b = P.polarized_bundle(LG.compile_lens(s, device="cpu"), field=0.5, rings=4)
    v = b["valid"][0, 0]
    J = b["jones"][0, 0][v]
    np.testing.assert_allclose(J.det().abs().numpy(), 1.0, atol=1e-12)


@pytest.mark.parametrize("name", ["catalog_doublet", "singlet", "triplet", "paraboloid"])
def test_exit_field_is_transverse_and_mueller_is_physical(name):
    s = lensfile.lens_file_read()["system"] if name == "triplet" else RT.example_system(name)
    f = 14.0 if name == "triplet" else 1.0
    b = P.polarized_bundle(LG.compile_lens(s, [RT.WL_F, RT.WL_C], device="cpu"), field=f, rings=5)
    v = b["valid"]
    assert v.any()
    d = (b["L"], b["M"], b["N"])
    for E in b["E_out"]:
        assert float(torch.nan_to_num(P._dot(E, d)).abs().max()) < 1e-12
    M = P.jones_to_mueller(b["jones"])[v].numpy()
    idx = np.linspace(0, len(M) - 1, 25).astype(int)
    for m in M[idx]:
        c = optics.mueller_checks(m)
        assert c["physical"] and c["pure"] and c["passive"]


def test_unpolarized_transmission_close_to_per_surface_formula():
    """無偏光の透過 (Ts + Tp)/2 と lens_gpu の面ごとの無偏光の積は、1 面なら一致し、多面では 2 次の差だけ。"""
    s = RT.example_system("catalog_doublet")
    lens = LG.compile_lens(s, device="cpu")
    b = P.polarized_bundle(lens, field=1.0, rings=5)
    r = LG.spectral_transmission(lens, field=1.0, rings=5, absorption=False)
    v = b["valid"][0, 0]
    M = P.jones_to_mueller(b["jones"])[0, 0][v]
    t_pol = M[:, 0, 0].numpy()
    t_uni = r["T_ray"][0, 0][v].numpy()
    d = np.abs(t_pol - t_uni)
    assert d.max() < 2e-3
    # 軸上の主光線(法線入射に近い)はほぼ同じ
    assert d[0] < 1e-6


def test_on_axis_plate_does_not_rotate_polarization():
    s = RT.lens_system([{"R": INF_, "t": 5.0, "n": 1.5, "ap": 10.0}, {"R": INF_, "t": 5.0, "n": 1.0}], stop=0)
    b = P.polarized_bundle(LG.compile_lens(s, device="cpu"), field=0.0, rings=3)
    J = b["jones"][0, 0].numpy()
    np.testing.assert_allclose(J, np.tile(np.eye(2) * (1.0 - 0.04), (J.shape[0], 1, 1)), atol=1e-12)


def test_absorption_scales_power():
    s = RT.lens_system([{"R": INF_, "t": 25.0, "n": "H-ZF52A", "ap": 5.0}, {"R": INF_, "t": 5.0, "n": 1.0}], stop=0,
                       wavelength_um=0.5)
    lens = LG.compile_lens(s, device="cpu")
    a = P.polarized_bundle(lens, field=0.0, rings=2, absorption=True)
    b = P.polarized_bundle(lens, field=0.0, rings=2, absorption=False)
    ratio = (P.jones_to_mueller(a["jones"])[0, 0, 0, 0, 0] / P.jones_to_mueller(b["jones"])[0, 0, 0, 0, 0]).item()
    r = LG.spectral_transmission(lens, field=0.0, rings=2, fresnel=False)
    assert ratio < 0.9999
    assert abs(ratio - float(r["T_internal"][0, 0])) < 1e-12


@skip_gpu
def test_gpu_equals_cpu_images():
    rng = np.random.default_rng(0)
    raw = rng.random((2, 64, 48))
    a = P.polarization_demosaic_batch(raw, device="cuda").cpu().numpy()
    b = P.polarization_demosaic_batch(raw).numpy()
    assert np.abs(a - b).max() < 1e-12
