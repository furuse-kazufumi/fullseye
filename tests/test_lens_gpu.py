# -*- coding: utf-8 -*-
"""lens_gpu の一致の門: ``raytrace`` / ``lensimage`` / ``lensrender`` / ``materials`` と閉形式。

CPU の torch で常に回す(``device="cpu"``)。GPU の項は CUDA が無ければ skip。
門の数値: 近軸は相対 1e-10、実光線は float64 で位置 1e-9 mm。
"""
import math

import numpy as np
import pytest

torch = pytest.importorskip("torch")

import lens_gpu as G  # noqa: E402
import lensfile  # noqa: E402
import lensimage  # noqa: E402
import lensrender  # noqa: E402
import materials  # noqa: E402
import raytrace as RT  # noqa: E402

skip_gpu = pytest.mark.skipif(not G.gpu_available(), reason="CUDA GPU 不在")
SCALARS = ("efl", "bfl", "ffl", "pp_front", "pp_rear", "image_mm", "magnification", "ep_position", "ep_radius",
           "xp_position", "xp_radius", "fno", "na_image", "lagrange")


def triplet():
    return lensfile.lens_file_read()["system"]


def asphere_poly():
    return RT.lens_system([{"R": 40.0, "t": 6.0, "n": "N-BK7", "ap": 12.0, "k": -0.8, "asph": (1.2e-6, -3e-9, 1e-12)},
                           {"R": -120.0, "t": None, "n": 1.0, "asph": (2e-6,), "a2": 1e-4}], stop=0)


def odd_asphere():
    return RT.lens_system([{"R": 60.0, "t": 5.0, "n": "N-BK7", "ap": 10.0, "odd": (1e-4, 2e-4, 3e-6)},
                           {"R": -80.0, "t": 90.0, "n": 1.0}], stop=0)


def finite_object():
    return RT.lens_system([{"R": 51.68, "t": 5.0, "n": (1.5168, 64.17), "ap": 12.5},
                           {"R": INF_, "t": None, "n": 1.0}], stop=0, object_mm=300.0)


def perturbed_surface():
    return RT.lens_system([{"R": 61.47, "t": 6.0, "n": "N-BK7", "ap": 12.5, "decenter": (0.1, -0.05), "tilt": (0.2, 0.1)},
                           {"R": -44.64, "t": 2.5, "n": "N-SF2", "tilt": (-0.1, 0.05)},
                           {"R": -129.94, "t": None, "n": 1.0, "decenter": (0.0, 0.03)}], stop=1)


def curved_image():
    return RT.lens_system([{"R": 61.47, "t": 6.0, "n": "N-BK7", "ap": 12.5},
                           {"R": -44.64, "t": 2.5, "n": "N-SF2"},
                           {"R": -129.94, "t": 92.0, "n": 1.0}], stop=0, image_R=-90.0, image_k=0.1)


def two_mirror():
    return RT.lens_system([{"R": -400.0, "t": 150.0, "n": 1.0, "k": -1.0, "ap": 40.0, "mirror": True},
                           {"R": -140.0, "t": 200.0, "n": 1.0, "k": -3.0, "mirror": True}], stop=0)


INF_ = float("inf")
SYSTEMS = {
    "singlet": lambda: RT.example_system("singlet"),
    "catalog_doublet": lambda: RT.example_system("catalog_doublet"),
    "doublet": lambda: RT.example_system("doublet"),
    "asphere": lambda: RT.example_system("asphere"),
    "paraboloid": lambda: RT.example_system("paraboloid"),
    "sphere_mirror": lambda: RT.example_system("sphere_mirror"),
    "triplet": triplet,
    "asphere_poly": asphere_poly,
    "odd_asphere": odd_asphere,
    "finite_object": finite_object,
    "perturbed_surface": perturbed_surface,
    "curved_image": curved_image,
    "two_mirror": two_mirror,
}
FIELD = {"singlet": 2.0, "catalog_doublet": 1.0, "doublet": 1.0, "asphere": 1.0, "paraboloid": 0.5, "sphere_mirror": 0.5,
         "triplet": 14.0, "asphere_poly": 1.5, "odd_asphere": 1.0, "finite_object": 5.0, "perturbed_surface": 1.0,
         "curved_image": 1.0, "two_mirror": 0.1}
WL = [RT.WL_F, RT.WL_D, RT.WL_C]
#: 放物面(k = -1)の軸近くでは CPU の 2 次方程式の解が桁落ちする(test_conic_root_beats_cpu_on_a_paraboloid)。
#: 差は lens_gpu の誤差でなく CPU の丸めなので、この処方だけ門を実測の桁に合わせる。
POSITION_TOL = {"two_mirror": 5e-8, "paraboloid": 5e-8}


def rel(a, b):
    a, b = float(a), float(b)
    if math.isinf(a) or math.isinf(b):
        return 0.0 if a == b else float("inf")
    return abs(a - b) / max(abs(b), 1e-12)


@pytest.mark.parametrize("name", sorted(SYSTEMS))
def test_paraxial_matches_cpu(name):
    s = SYSTEMS[name]()
    lens = G.compile_lens(s, WL, device="cpu")
    p = G.paraxial_batch(lens)
    for w, wl in enumerate(WL):
        q = RT.paraxial_trace(RT.with_wavelength(s, wl))
        for k in SCALARS:
            assert rel(p[k][0, w], q[k]) < 1e-10, (k, wl, float(p[k][0, w]), q[k])
        np.testing.assert_allclose(p["marginal_y"][0, w].numpy(), q["marginal"]["y"], rtol=1e-10, atol=1e-12)
        np.testing.assert_allclose(p["chief_u"][0, w].numpy(), q["chief"]["u"], rtol=1e-10, atol=1e-12)


@pytest.mark.parametrize("name", sorted(SYSTEMS))
def test_real_rays_match_trace_rays(name):
    s = SYSTEMS[name]()
    for wl in (RT.WL_F, RT.WL_C):
        cpu = RT.ray_bundle(s, field=FIELD[name], rings=6, wavelength_um=wl)
        P = torch.as_tensor(cpu["points"][:, 0, :])
        D = torch.as_tensor(cpu["dirs"][:, 0, :])
        # raytrace の像面は設計波長のものなので trace_batch の既定と揃う
        lens = G.compile_lens(s, [wl], device="cpu")
        tr = G.trace_batch(lens, tuple(P[..., j][None, None] for j in range(3)),
                           tuple(D[..., j][None, None] for j in range(3)), points=True)
        v = tr["valid"][0, 0].numpy()
        ref = RT.trace_rays(s, cpu["points"][:, 0, :], cpu["dirs"][:, 0, :], wavelength_um=wl)
        np.testing.assert_array_equal(v, ref["valid"])
        assert v.any()
        got = tr["points"][0, 0].numpy()
        tol = POSITION_TOL.get(name, 1e-9)
        assert np.nanmax(np.abs(got[v][:, -1, :] - ref["points"][v][:, -1, :])) < tol
        assert np.nanmax(np.abs(tr["dirs"][0, 0].numpy()[v] - ref["dirs"][v])) < tol
        assert np.nanmax(np.abs(tr["opl"][0, 0].numpy()[v] - ref["opl"][v])) < max(tol, 1e-8)
        assert np.isnan(got[~v][:, -1, :]).all()


def test_gate_detects_a_wrong_lens():
    """負の対照: 近軸の差が厳密に 0 に出るのは式が同じだからで、門が盲目だからではない。"""
    s = triplet()
    lens = G.compile_lens(s, device="cpu")
    lens.c_par = lens.c_par * (1.0 + 1e-9)
    lens.c = lens.c * (1.0 + 1e-9)
    q = RT.paraxial_trace(s)
    assert rel(G.paraxial_batch(lens)["efl"][0, 0], q["efl"]) > 1e-10
    b = G.bundle_batch(lens, field=14.0, rings=6)
    c = RT.ray_bundle(s, field=14.0, rings=6)
    v = b["valid"][0, 0].numpy() & c["valid"]
    assert np.abs(b["y"][0, 0].numpy()[v] - c["image_xy"][v, 1]).max() > 1e-9


def test_conic_root_beats_cpu_on_a_paraboloid():
    """50 桁の 10 進で解いた交点と比べる: lens_gpu は 1e-11 mm 以内、CPU はそれより悪い(隠さず固定する)。"""
    from decimal import Decimal as Dd, getcontext
    getcontext().prec = 50
    s = RT.lens_system([{"R": -400.0, "t": None, "n": 1.0, "k": -1.0, "ap": 40.0, "mirror": True}], stop=0)
    P = np.array([[26.666666666666668, -0.01745331, -10.0]])
    D = np.array([[0.0, 0.0017453283658983088, 0.9999984769132877]])
    x, y, z = (Dd(float(v)) for v in P[0])
    L, M, N = (Dd(float(v)) for v in D[0])
    c = Dd(-1) / Dd(400)
    A = c * (L * L + M * M)
    B = 2 * (c * (x * L + y * M) - N)
    C = c * (x * x + y * y) - 2 * z
    disc = (B * B - 4 * A * C).sqrt()
    exact = min(((-B - disc) / (2 * A), (-B + disc) / (2 * A)), key=abs)
    cpu_t = float(RT._intersect_conic(P, D, -1.0 / 400.0, -1.0)[0])
    lens = G.compile_lens(s, device="cpu")
    t = G._hit_conic(*(torch.as_tensor(P[:, j])[None, None] for j in range(3)),
                     *(torch.as_tensor(D[:, j])[None, None] for j in range(3)),
                     lens.c[:, None, :1], lens.k[0])
    mine = float(t[0, 0, 0])
    assert abs(Dd(mine) - exact) < Dd("1e-11")
    assert abs(Dd(cpu_t) - exact) > Dd("1e-10")


def test_tir_and_vignetting_masks_mean_the_same():
    """全反射とケラレが起きる処方で、valid が 1 本ずつ同じ。"""
    s = RT.lens_system([{"R": INF_, "t": 10.0, "n": 1.8, "ap": 30.0}, {"R": 12.0, "t": None, "n": 1.0, "ap": 9.0}], stop=0)
    y = np.linspace(-25.0, 25.0, 501)
    P = np.stack([np.zeros_like(y), y, np.full_like(y, -5.0)], 1)
    D = np.tile([0.0, 0.0, 1.0], (len(y), 1))
    ref = RT.trace_rays(s, P, D, image_mm=20.0)
    assert (~ref["valid"]).sum() > 50 and ref["valid"].sum() > 50
    lens = G.compile_lens(s, device="cpu")
    tr = G.trace_batch(lens, tuple(torch.as_tensor(P[:, j])[None, None] for j in range(3)),
                       tuple(torch.as_tensor(D[:, j])[None, None] for j in range(3)), image_mm=[[20.0]])
    np.testing.assert_array_equal(tr["valid"][0, 0].numpy(), ref["valid"])


@pytest.mark.parametrize("name", sorted(SYSTEMS))
def test_bundle_and_spot_match(name):
    s = SYSTEMS[name]()
    lens = G.compile_lens(s, device="cpu")
    b = G.bundle_batch(lens, field=FIELD[name], rings=6, pupil_fill=0.99)
    st = G.spot_stats_batch(b)
    c = RT.spot_stats(s, field=FIELD[name], rings=6, pupil_fill=0.99)
    assert int(st["n_rays"][0, 0]) == c["n_rays"]
    tol = POSITION_TOL.get(name, 1e-9)
    assert abs(float(st["rms_radius"][0, 0]) - c["rms_radius"]) < tol
    assert abs(float(st["geo_radius"][0, 0]) - c["geo_radius"]) < tol
    assert abs(float(b["chief_y"][0, 0]) - c["chief_y"]) < tol


@pytest.mark.parametrize("name", ["singlet", "catalog_doublet", "triplet", "asphere_poly", "perturbed_surface"])
def test_chromatic_matches_cpu(name):
    s = SYSTEMS[name]()
    wls = list(np.linspace(0.47, 0.68, 9))
    c = RT.chromatic_shift(s, wavelengths=[float(w) for w in wls], field=FIELD[name], rings=6)
    r = G.chromatic_batch(G.compile_lens(s, wls, device="cpu"), field=FIELD[name], rings=6)
    for w, row in enumerate(c["per_wavelength"]):
        assert rel(r["bfl"][0, w], row["bfl"]) < 1e-10
        assert abs(float(r["chief_height"][0, w]) - row["chief_height"]) < 1e-9
        assert abs(float(r["rms_spot"][0, w]) - row["rms_spot"]) < 1e-9
        assert int(r["n_rays"][0, w]) == row["n_rays"]
    assert abs(float(r["axial_color"][0]) - c["axial_color"]) < 1e-9
    assert abs(float(r["lateral_color"][0]) - c["lateral_color"]) < 1e-9
    assert abs(float(r["rms_polychromatic"][0]) - c["rms_polychromatic"]) < 1e-9
    assert abs(float(r["efl_range"][0]) - c["efl_range"]) < 1e-9


def test_paraxial_color_closed_form_thin_achromat_like():
    """単レンズの軸上色収差は BFL の差。近軸の主光線の高さは f tan θ に近い(薄肉)。"""
    s = RT.lens_system([{"R": 100.0, "t": 0.0, "n": "N-BK7", "ap": 5.0}, {"R": -100.0, "t": None, "n": 1.0}], stop=0)
    wl = [RT.WL_F, RT.WL_C]
    lens = G.compile_lens(s, wl, device="cpu")
    pc = G.paraxial_color(lens, field=1.0)
    nf, nc = RT.refractive_index("N-BK7", RT.WL_F), RT.refractive_index("N-BK7", RT.WL_C)
    ff, fc = 50.0 / (nf - 1.0), 50.0 / (nc - 1.0)                   # 1/f = (n-1) 2/R
    assert abs(float(pc["axial_color"][0]) - (ff - fc)) < 1e-9
    fd = 50.0 / (RT.refractive_index("N-BK7") - 1.0)
    # 薄肉レンズの主光線は曲がらない: 高さは基準像面までの距離 × tan θ で波長に依らない
    assert abs(float(pc["lateral_color"][0])) < 1e-9
    assert abs(float(pc["chief_height"][0, 0]) - fd * math.tan(math.radians(1.0))) < 1e-9


def test_paraxial_closed_forms():
    # 単一屈折面 n'/s' = n/s + (n'-n)/R
    n2, R, s_obj = 1.6, 30.0, 200.0
    s = RT.lens_system([{"R": R, "t": None, "n": n2, "ap": 5.0}], stop=0, object_mm=s_obj)
    p = G.paraxial_batch(G.compile_lens(s, device="cpu"))
    sp = n2 / (1.0 / s_obj * -1.0 + (n2 - 1.0) / R)
    assert rel(p["image_mm"][0, 0], sp) < 1e-12
    # 厚肉レンズ
    th = RT.thick_lens(R1=50.0, R2=-70.0, thickness=8.0, index=1.5)
    s = RT.lens_system([{"R": 50.0, "t": 8.0, "n": 1.5, "ap": 10.0}, {"R": -70.0, "t": None, "n": 1.0}], stop=0)
    p = G.paraxial_batch(G.compile_lens(s, device="cpu"))
    for k in ("efl", "bfl", "ffl", "pp_front", "pp_rear"):
        assert rel(p[k][0, 0], th[k]) < 1e-12, k
    # 鏡 f = -R/2
    p = G.paraxial_batch(G.compile_lens(RT.example_system("sphere_mirror"), device="cpu"))
    assert rel(p["efl"][0, 0], 100.0) < 1e-12


def test_real_rays_closed_forms():
    # 放物面鏡は軸上で無収差: 全光線が焦点へ
    lens = G.compile_lens(RT.example_system("paraboloid"), device="cpu")
    b = G.bundle_batch(lens, field=0.0, rings=6)
    assert float(b["x"].abs().max()) < 1e-9 and float(b["y"].abs().max()) < 1e-9
    # Descartes の平凸双曲面: 軸上で無収差
    lens = G.compile_lens(RT.example_system("asphere"), device="cpu")
    b = G.bundle_batch(lens, field=0.0, rings=6)
    assert float(torch.hypot(b["x"], b["y"]).max()) < 1e-9
    # 平面での Snell: 全光線 sinθ' = sinθ / n
    s = RT.lens_system([{"R": INF_, "t": None, "n": 1.5, "ap": 50.0}], stop=0, image_mm=10.0)
    th = np.radians(np.linspace(1.0, 40.0, 11))
    lens = G.compile_lens(s, device="cpu")
    Px = torch.zeros(1, 1, 11, dtype=torch.float64)
    tr = G.trace_batch(lens, (Px, Px, Px - 1.0),
                       (Px, torch.as_tensor(np.sin(th))[None, None], torch.as_tensor(np.cos(th))[None, None]))
    np.testing.assert_allclose(tr["M"][0, 0].numpy(), np.sin(th) / 1.5, rtol=1e-13)


@pytest.mark.parametrize("name", ["singlet", "catalog_doublet", "triplet", "asphere_poly"])
def test_opd_matches_cpu(name):
    s = SYSTEMS[name]()
    px, py, w, v = RT.opd_samples(s, field=FIELD[name], size=33, wavelength_um=RT.WL_F)
    o = G.opd_batch(G.compile_lens(s, [RT.WL_F], device="cpu"), field=FIELD[name], size=33)
    np.testing.assert_array_equal(o["valid"][0, 0].numpy(), v)
    assert np.nanmax(np.abs(o["opd"][0, 0].numpy()[v] - w[v])) < 1e-6      # 波。1 波 ≈ 5e-4 mm → 5e-10 mm


@pytest.mark.parametrize("name", ["asphere", "catalog_doublet", "triplet"])
def test_mtf_matches_through_focus(name):
    s = SYSTEMS[name]()
    wl = RT.WL_D
    f = [10.0, 30.0, 60.0]
    c = lensimage.through_focus_mtf(s, frequency_cpmm=f, defocus_mm=[0.0], field=FIELD[name], wavelength_um=wl, size=128)
    m = G.mtf_batch(G.compile_lens(s, [wl], device="cpu"), field=FIELD[name], size=128, frequency_cpmm=f)
    assert not bool(m["aliased"].any())
    np.testing.assert_allclose(m["tangential"][0, 0].numpy(), c["tangential"][0], atol=1e-8)
    np.testing.assert_allclose(m["sagittal"][0, 0].numpy(), c["sagittal"][0], atol=1e-8)


@pytest.mark.parametrize("name,field", [("catalog_doublet", 1.0), ("triplet", 14.0), ("asphere", 1.0), ("singlet", 0.0)])
def test_monte_carlo_matches_cpu_trial_by_trial(name, field):
    """同じ seed で案ごとに一致。CPU のループを数百回まわして突き合わせる。"""
    s = SYSTEMS[name]()
    n = 200
    tol = {"radius_pct": 0.5, "thickness_mm": 0.05, "index": 0.001, "decenter_mm": 0.02, "tilt_deg": 0.05}
    sysf = RT._freeze_solves(s)
    rng = np.random.default_rng(3)
    if sysf["image_mm"] is not None:
        img = sysf["image_mm"]
    elif sysf["surfaces"][-1]["t"] is not None:
        img = sysf["surfaces"][-1]["t"]
    else:
        img = None
    efl, rms = [], []
    for _ in range(n):
        q = RT._perturbed(sysf, rng, tol)
        p = RT.paraxial_trace(q)
        st = RT.spot_stats(q, field=field, rings=6, pupil_fill=0.99, image_mm=p["image_mm"] if img is None else img)
        efl.append(p["efl"])
        rms.append(st["rms_radius"])
    r = G.tolerance_monte_carlo(s, tol, trials=n, seed=3, field=field, device="cpu")
    assert r["failed"] == 0
    np.testing.assert_allclose(r["efl_trial"], efl, rtol=1e-10)
    assert np.max(np.abs(r["rms_trial"] - rms)) < 1e-9


def test_mtf_flags_aliased_like_cpu_refuses():
    s = RT.example_system("singlet")
    with pytest.raises(ValueError, match="aliased"):
        lensimage.through_focus_mtf(s, frequency_cpmm=[10.0], defocus_mm=[0.0], field=2.0, size=96)
    m = G.mtf_batch(G.compile_lens(s, device="cpu"), field=2.0, size=96, frequency_cpmm=[10.0])
    assert bool(m["aliased"][0, 0]) and math.isnan(float(m["tangential"][0, 0, 0]))


def test_monte_carlo_summary_matches_tolerance_analysis():
    s = RT.example_system("catalog_doublet")
    c = RT.tolerance_analysis(s, trials=50, seed=5, field=1.0)
    r = G.tolerance_monte_carlo(s, trials=50, seed=5, field=1.0, device="cpu")
    assert r["compensator"] == c["compensator"]
    for k in ("mean", "std", "p5", "p95", "worst"):
        assert abs(r["efl"][k] - c["efl"][k]) < 1e-9
        assert abs(r["rms_spot"][k] - c["rms_spot"][k]) < 1e-9


def test_chunking_does_not_change_the_answer():
    s = triplet()
    a = G.tolerance_monte_carlo(s, trials=30, seed=1, field=14.0, device="cpu", chunk=30)
    b = G.tolerance_monte_carlo(s, trials=30, seed=1, field=14.0, device="cpu", chunk=7)
    np.testing.assert_array_equal(a["rms_trial"], b["rms_trial"])


@pytest.mark.parametrize("medium", ["N-BK7", "SAPPHIRE", "PMMA", (1.62, 36.0), 1.5, RT.glass(1.7, 40.0), "WATER"])
def test_index_array_matches_scalar(medium):
    wl = np.linspace(0.45, 0.75, 31)
    got = G.index_array(medium, wl)
    ref = [RT.refractive_index(medium, float(w)) for w in wl]
    np.testing.assert_allclose(got, ref, rtol=1e-14)


def test_index_array_refuses_what_scalar_refuses():
    with pytest.raises(ValueError):
        G.index_array("N-BK7", [0.2, 0.5])
    with pytest.raises(ValueError):
        G.index_array((1.5, 60.0), [0.5, 1.2])


def test_offset_gain_matches_index_offset():
    wl = np.array([0.45, 0.55, 0.7])
    for medium in ((1.62041, 60.32), "N-BK7", 1.6, RT.glass(1.6, 40.0)):
        d = 7e-4
        ref = [RT.refractive_index(RT._index_offset(medium, d), float(w)) for w in wl]
        got = G.index_array(medium, wl) + d * G._offset_gain(medium, wl)
        np.testing.assert_allclose(got, ref, rtol=1e-13)


def test_spectral_transmission_plate_closed_form():
    """平行平板の垂直入射: T = (1 − R)²、内部は exp(−αt)。materials と同じ定義。"""
    d = 25.0
    g = "H-ZF52A"                                       # 可視で k > 0 のデータがある硝材
    wl = np.linspace(0.45, 0.70, 6)
    s = RT.lens_system([{"R": INF_, "t": d, "n": g, "ap": 5.0}, {"R": INF_, "t": 5.0, "n": 1.0}], stop=0,
                       wavelength_um=0.55)
    r = G.spectral_transmission(G.compile_lens(s, wl, device="cpu"), field=0.0, rings=3)
    n = RT.refractive_index
    R = np.array([((n(g, float(w)) - 1.0) / (n(g, float(w)) + 1.0)) ** 2 for w in wl])
    np.testing.assert_allclose(r["T_fresnel"][0].numpy(), (1.0 - R) ** 2, rtol=1e-12)
    inner = materials.material_transmittance(g, d, wl.min() * 1e3, wl.max() * 1e3, 6, include_fresnel=False)
    assert inner[:, 1].min() < 0.999                     # 吸収が効く題材であること(1 同士の一致は門にならない)
    np.testing.assert_allclose(r["T_internal"][0].numpy(), inner[:, 1], rtol=1e-9)


def test_spectral_transmission_fresnel_matches_lensrender():
    """lensrender.trace_sensor_rays(fresnel=True) の光線を逆向きに打って、同じ透過率に。"""
    s = RT.example_system("catalog_doublet")
    px = np.array([[0.0, 0.0], [0.3, 0.1], [-0.2, 0.4]])
    q = lensrender.trace_sensor_rays(s, pixel_xy_mm=px, wavelength_um=RT.WL_D, fresnel=True)
    ok = q["valid"].ravel() if "valid" in q else np.ones(q["origin"][..., 0].size, bool)
    O = q["origin"].reshape(-1, 3)[ok]
    D = -q["direction"].reshape(-1, 3)[ok]
    T = q["transmission"].ravel()[ok]
    assert len(T) > 10
    lens = G.compile_lens(s, [RT.WL_D], device="cpu")
    logF = {"v": 0.0}

    def visit(i, info):
        if i < lens.S and info["cos_t"] is not None:
            n1, n2, ci, ct = info["n1"], info["n2"], info["cos_i"], info["cos_t"]
            rs = ((n1 * ci - n2 * ct) / (n1 * ci + n2 * ct)) ** 2
            rp = ((n1 * ct - n2 * ci) / (n1 * ct + n2 * ci)) ** 2
            logF["v"] = logF["v"] + torch.log(1.0 - 0.5 * (rs + rp))

    # 起点は第 1 面の点。少し手前へ戻してから打つ
    O2 = O - 5.0 * D
    tr = G.trace_batch(lens, tuple(torch.as_tensor(O2[:, j])[None, None] for j in range(3)),
                       tuple(torch.as_tensor(D[:, j])[None, None] for j in range(3)), visitor=visit)
    got = torch.exp(logF["v"])[0, 0].numpy()
    keep = tr["valid"][0, 0].numpy()
    assert keep.sum() > 10
    np.testing.assert_allclose(got[keep], T[keep], rtol=1e-11)


def test_spectral_transmission_counts_lost_rays_as_zero():
    s = RT.example_system("catalog_doublet")
    r = G.spectral_transmission(G.compile_lens(s, device="cpu"), field=1.0, rings=6)
    b = RT.ray_bundle(s, field=1.0, rings=6)
    assert abs(float(r["valid_fraction"][0, 0]) - b["valid"].mean()) < 1e-12
    assert float(r["T"][0, 0]) <= float(r["valid_fraction"][0, 0])


@pytest.mark.parametrize("bad,msg", [
    ({"surfaces": [{"f": 50.0, "t": None}], "stop": 0, "ap": 5.0}, "ideal"),
])
def test_refuses_ideal_lens(bad, msg):
    s = RT.lens_system([{"f": 50.0, "t": None, "ap": 5.0}], stop=0)
    with pytest.raises(ValueError, match=msg):
        G.compile_lens(s, device="cpu")


def test_refuses_unbatched_paths():
    s = RT.with_aiming(RT.example_system("catalog_doublet"), "stop")
    lens = G.compile_lens(s, device="cpu")
    with pytest.raises(ValueError, match="paraxial aim"):
        G.bundle_batch(lens, field=1.0)
    with pytest.raises(ValueError):
        G.compile_lens(RT.example_system("singlet"), device="nonsense")
    with pytest.raises(ValueError):
        G.compile_lens(RT.example_system("singlet"), dtype="float16", device="cpu")


def test_float32_error_is_bounded_and_reported():
    """float32 は桁が悪い。上限を置いて、黙って良くなったり悪くなったりしないように。"""
    s = RT.example_system("catalog_doublet")
    a = G.bundle_batch(G.compile_lens(s, device="cpu", dtype="float32"), field=1.0, rings=6)
    b = G.bundle_batch(G.compile_lens(s, device="cpu"), field=1.0, rings=6)
    v = (a["valid"] & b["valid"]).numpy()
    e = np.abs(a["y"].numpy().astype(float) - b["y"].numpy())[v].max()
    assert 1e-9 < e < 1e-3


def test_auto_device_keeps_a_small_call_on_the_cpu():
    """1 回だけ小さく呼ぶと GPU は負ける(docs/perf)。auto は小さい仕事を GPU へ送らない。"""
    assert G._device("auto", 127).startswith("cpu")
    assert str(G.compile_lens(RT.example_system("singlet"), device="auto").device) == "cpu"


@skip_gpu
@pytest.mark.parametrize("name", ["catalog_doublet", "triplet", "asphere_poly"])
def test_gpu_equals_cpu(name):
    s = SYSTEMS[name]()
    c = G.bundle_batch(G.compile_lens(s, WL, device="cpu"), field=FIELD[name], rings=6)
    g = G.bundle_batch(G.compile_lens(s, WL, device="cuda"), field=FIELD[name], rings=6)
    v = c["valid"].numpy()
    np.testing.assert_array_equal(g["valid"].cpu().numpy(), v)
    assert np.abs(g["y"].cpu().numpy()[v] - c["y"].numpy()[v]).max() < 1e-9
