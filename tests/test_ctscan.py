# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""CT スキャン方式の門。真値は楕円体の閉形式の投影で、投影器を通らない。

方式ごとに「再構成の誤差」と「投影と逆投影の随伴性」を測る。上限は実測から決め、定数や
空の入力で通らないように、再構成が定数の場合の誤差(``rmse(truth, truth.mean())``)も並べて
下回ることを見る。
"""
from __future__ import annotations

import numpy as np
import pytest

import ctscan
import tomography
import tomography_gpu


SIZE = 32


def rmse(a, b):
    return float(np.sqrt(np.mean((a - b) ** 2)))


def adjoint_gap(geom, seed=0):
    rng = np.random.default_rng(seed)
    x = rng.random(geom["vol_shape"])
    y = rng.random((geom["n_views"], geom["n_v"], geom["n_u"]))
    lhs = float(np.sum(ctscan.ct_forward_project(x, geom, device="cpu") * y))
    rhs = float(np.sum(x * ctscan.ct_adjoint_project(y, geom, device="cpu")))
    assert lhs != 0.0
    return abs(lhs - rhs) / abs(lhs)


@pytest.fixture(scope="module")
def truth():
    return ctscan.shepp_logan_3d(SIZE)


@pytest.fixture(scope="module")
def flat_truth():
    return ctscan.ellipsoid_phantom((1, 96, 96))


def half_fan_deg(n_u=64):
    return float(np.rad2deg(np.arctan(n_u / 2.0 * 2.0 / (6.0 * SIZE))))


# (名前, 幾何の引数, FDK の RMSE の上限)。上限は実測の 1.15 倍前後。
FDK_SCANS = [
    ("cone", dict(scan="cone", n_views=90, n_u=64, n_v=64, vol_shape=SIZE), 0.075),
    ("cone_arc", dict(scan="cone", n_views=90, n_u=64, n_v=64, vol_shape=SIZE, detector="arc"), 0.075),
    ("helical", dict(scan="helical", n_views=240, n_u=64, n_v=24, vol_shape=SIZE, pitch=0.5), 0.075),
    ("laminography", dict(scan="laminography", n_views=90, n_u=64, n_v=64, vol_shape=SIZE,
                          tilt_deg=60.0, du=1.0, dv=1.0), 0.095),
    ("laminography_cone", dict(scan="laminography", n_views=90, n_u=64, n_v=64, vol_shape=SIZE,
                               tilt_deg=60.0, dso=200.0, dsd=400.0), 0.095),
    ("short_scan", dict(scan="cone", n_views=60, n_u=64, n_v=64, vol_shape=SIZE,
                        arc_deg=182.0 + 2.0 * half_fan_deg()), 0.08),
    ("offset_detector", dict(scan="cone", n_views=90, n_u=50, n_v=64, vol_shape=SIZE,
                             offset_u=14.0), 0.08),
    ("parallel_360", dict(scan="parallel", n_views=90, n_u=64, n_v=32, vol_shape=SIZE,
                          arc_deg=360.0, du=1.0, dv=1.0), 0.075),
]


@pytest.mark.parametrize("name,kwargs,limit", FDK_SCANS, ids=[s[0] for s in FDK_SCANS])
def test_fdk_recovers_the_phantom_on_every_scan(name, kwargs, limit, truth):
    geom = ctscan.ct_scan_geometry(**kwargs)
    proj = ctscan.ellipsoid_projections(geom, device="cpu")
    rec = ctscan.fdk_reconstruct(proj, geom, device="cpu")
    assert rmse(rec, truth) < limit
    assert rmse(rec, truth) < 0.5 * rmse(truth, truth.mean())
    # 振幅の絶対値が合う: 脳室の外の灰質は 0.2、頭蓋の内側の平均で見る
    inner = truth > 0.15
    assert abs(float(rec[inner].mean()) - float(truth[inner].mean())) < 0.05


@pytest.mark.parametrize("detector", ["flat", "arc"])
def test_fan_beam_recovers_the_slice(detector, flat_truth):
    geom = ctscan.ct_scan_geometry("fan", n_views=240, n_u=192, n_v=1, vol_shape=(1, 96, 96),
                                   detector=detector)
    rec = ctscan.fdk_reconstruct(ctscan.ellipsoid_projections(geom, device="cpu"), geom, device="cpu")
    assert rmse(rec, flat_truth) < 0.09
    assert rmse(rec, flat_truth) < 0.3 * rmse(flat_truth, flat_truth.mean())


def test_splitting_the_work_does_not_change_the_answer(monkeypatch):
    """VRAM に載らない寸法の経路(分割)を、numpy の核で強制して通す。"""
    geom = ctscan.ct_scan_geometry("cone", n_views=20, n_u=40, n_v=40, vol_shape=20)
    proj = ctscan.ellipsoid_projections(geom, device="cpu")
    whole = ctscan.fdk_reconstruct(proj, geom, device="cpu")
    fp = ctscan.ct_forward_project(whole, geom, device="cpu")
    adj = ctscan.ct_adjoint_project(fp, geom, device="cpu")
    monkeypatch.setattr(tomography_gpu, "CPU_BATCH_SAMPLES", 2000)
    monkeypatch.setattr(tomography_gpu._Numpy, "fits", lambda self, n: False)
    assert np.max(np.abs(ctscan.fdk_reconstruct(proj, geom, device="cpu") - whole)) < 1e-12
    assert np.max(np.abs(ctscan.ct_forward_project(whole, geom, device="cpu") - fp)) < 1e-12
    assert np.max(np.abs(ctscan.ct_adjoint_project(fp, geom, device="cpu") - adj)) < 1e-9


def test_rays_that_miss_the_volume_are_exactly_zero():
    geom = ctscan.ct_scan_geometry("cone", n_views=4, n_u=128, n_v=128, vol_shape=8)
    fp = ctscan.ct_forward_project(np.ones((8, 8, 8)), geom, device="cpu")
    assert fp[:, 0, 0].max() == 0.0
    assert fp[:, 64, 64].min() > 7.0


@pytest.mark.parametrize("name,kwargs", [
    ("cone", dict(scan="cone", n_views=12, n_u=24, n_v=24, vol_shape=12)),
    ("cone_arc", dict(scan="cone", n_views=12, n_u=24, n_v=24, vol_shape=12, detector="arc")),
    ("helical", dict(scan="helical", n_views=12, n_u=24, n_v=8, vol_shape=12)),
    ("laminography", dict(scan="laminography", n_views=12, n_u=24, n_v=24, vol_shape=12)),
    ("tomosynthesis", dict(scan="tomosynthesis", n_views=7, n_u=24, n_v=24, vol_shape=12)),
    ("fan", dict(scan="fan", n_views=12, n_u=24, n_v=1, vol_shape=(1, 12, 12))),
    ("parallel", dict(scan="parallel", n_views=12, n_u=24, n_v=12, vol_shape=12, du=1.0, dv=1.0)),
    ("short", dict(scan="cone", n_views=12, n_u=24, n_v=24, vol_shape=12, arc_deg=230.0)),
    ("offset", dict(scan="cone", n_views=12, n_u=24, n_v=24, vol_shape=12, offset_u=6.0)),
], ids=lambda v: v if isinstance(v, str) else "")
def test_projector_and_its_transpose_are_adjoint(name, kwargs):
    assert adjoint_gap(ctscan.ct_scan_geometry(**kwargs)) < 1e-12


def test_projector_converges_to_the_closed_form():
    """格子を 2 倍にすると、離散の投影と閉形式の差が縮む(投影器の定義が真値に向かう)。"""
    errors = []
    for n in (32, 64):
        geom = ctscan.ct_scan_geometry("cone", n_views=6, n_u=2 * n, n_v=2 * n, vol_shape=n)
        exact = ctscan.ellipsoid_projections(geom, device="cpu")
        discrete = ctscan.ct_forward_project(ctscan.shepp_logan_3d(n), geom, device="cpu")
        assert exact.max() > 1.0
        errors.append(rmse(discrete, exact) / exact.max())
    assert errors[0] < 0.03
    assert errors[1] < 0.7 * errors[0]


def test_the_chord_of_a_sphere_is_its_diameter():
    geom = ctscan.ct_scan_geometry("cone", n_views=1, n_u=33, n_v=33, vol_shape=32)
    sphere = [(0.0, 0.0, 0.0, 0.5, 0.5, 0.5, 0.0, 1.0)]
    p = ctscan.ellipsoid_projections(geom, sphere, device="cpu")
    assert p[0, 16, 16] == pytest.approx(16.0, rel=1e-12)
    assert p[0, 0, 0] == 0.0


def test_cone_midplane_matches_parallel_beam(truth):
    """中央面ではコーンビームは平行ビームの FBP と整合する(コーン角 0 の極限)。"""
    n = 48
    vol = ctscan.shepp_logan_3d(n)
    cone = ctscan.ct_scan_geometry("cone", n_views=120, n_u=96, n_v=96, vol_shape=n, dso=4000.0,
                                   dsd=8000.0)
    par = ctscan.ct_scan_geometry("parallel", n_views=120, n_u=96, n_v=48, vol_shape=n, du=1.0,
                                  dv=1.0, arc_deg=360.0)
    a = ctscan.fdk_reconstruct(ctscan.ellipsoid_projections(cone, device="cpu"), cone, device="cpu")
    b = ctscan.fdk_reconstruct(ctscan.ellipsoid_projections(par, device="cpu"), par, device="cpu")
    assert rmse(a[n // 2 - 2], b[n // 2 - 2]) < 0.01 * float(vol.max())


DEFRISE = [(0.0, 0.0, -0.6 + 0.3 * k, 0.75, 0.75, 0.06, 0.0, 1.0) for k in range(5)]


def _defrise_error(dso, n=48):
    """円盤を積んだ Defrise ファントムの、中央から離れた面と中央面の誤差。"""
    geom = ctscan.ct_scan_geometry("cone", n_views=120, n_u=128, n_v=128, vol_shape=n, dso=dso,
                                   dsd=2.0 * dso)
    truth = ctscan.ellipsoid_phantom(n, DEFRISE)
    rec = ctscan.fdk_reconstruct(ctscan.ellipsoid_projections(geom, DEFRISE, device="cpu"), geom,
                                 device="cpu")
    mid = n // 2
    return rmse(rec[mid - 2:mid + 3], truth[mid - 2:mid + 3]), rmse(rec, truth)


def test_feldkamp_artifact_grows_with_cone_angle():
    errors = [_defrise_error(d)[1] for d in (800.0, 200.0, 70.0)]
    assert errors[0] < errors[1] < errors[2]
    assert errors[2] > 1.3 * errors[0]


def test_short_scan_needs_the_minimum_arc():
    geom = ctscan.ct_scan_geometry("cone", n_views=30, n_u=64, n_v=64, vol_shape=SIZE, arc_deg=150.0)
    proj = ctscan.ellipsoid_projections(geom, device="cpu")
    with pytest.raises(ValueError, match="short-scan minimum"):
        ctscan.fdk_reconstruct(proj, geom, device="cpu")
    assert ctscan.fdk_reconstruct(proj, geom, device="cpu", allow_incomplete=True).shape == (SIZE,) * 3


def test_parker_weights_of_a_conjugate_pair_sum_to_one():
    gamma = np.linspace(-0.2, 0.2, 41)
    half = 0.25
    beta = np.linspace(0.0, np.pi + 2.0 * half, 2001)
    w = ctscan._parker(beta, gamma, half)
    for j, g in enumerate(gamma):
        b = beta[beta < np.pi - 2.0 * g]
        conj = b + np.pi + 2.0 * g
        keep = (conj >= 0.0) & (conj <= np.pi + 2.0 * half)
        w1 = np.interp(b[keep], beta, w[:, j])
        w2 = np.interp(conj[keep], beta, w[:, 40 - j])
        assert np.max(np.abs(w1 + w2 - 1.0)) < 0.02


def test_displaced_detector_weights_sum_to_one():
    gamma = np.linspace(-0.1, 0.3, 81)
    w = ctscan._displaced(gamma, 1.0)
    inside = np.abs(gamma) <= 0.1 + 1e-12
    pair = np.interp(-gamma[inside], gamma, w)
    assert np.max(np.abs(w[inside] + pair - 1.0)) < 1e-3
    assert w[0] == pytest.approx(0.0, abs=1e-12)
    assert w[-1] == 1.0


def test_few_views_iterative_beats_fbp_and_tv_beats_sirt(flat_truth):
    geom = ctscan.ct_scan_geometry("fan", n_views=20, n_u=192, n_v=1, vol_shape=(1, 96, 96))
    proj = ctscan.ellipsoid_projections(geom, device="cpu")
    fbp = rmse(ctscan.fdk_reconstruct(proj, geom, device="cpu"), flat_truth)
    sirt = rmse(ctscan.sirt_reconstruct(proj, geom, n_iter=40, device="cpu"), flat_truth)
    os_sart = rmse(ctscan.os_sart_reconstruct(proj, geom, n_iter=10, n_subsets=5, device="cpu"),
                   flat_truth)
    tv = rmse(ctscan.tv_reconstruct(proj, geom, n_iter=120, device="cpu"), flat_truth)
    assert sirt < 0.6 * fbp
    assert os_sart < 0.6 * fbp
    assert tv < 0.8 * sirt


def test_limited_angle_iterative_beats_fbp(flat_truth):
    geom = ctscan.ct_scan_geometry("fan", n_views=40, n_u=192, n_v=1, vol_shape=(1, 96, 96),
                                   arc_deg=120.0)
    proj = ctscan.ellipsoid_projections(geom, device="cpu")
    fbp = rmse(ctscan.fdk_reconstruct(proj, geom, device="cpu", allow_incomplete=True), flat_truth)
    sirt = rmse(ctscan.sirt_reconstruct(proj, geom, n_iter=40, device="cpu"), flat_truth)
    assert sirt < fbp


def test_sirt_residual_falls_monotonically():
    geom = ctscan.ct_scan_geometry("fan", n_views=30, n_u=96, n_v=1, vol_shape=(1, 48, 48))
    proj = ctscan.ellipsoid_projections(geom, device="cpu")
    residuals = []

    def record(k, x):
        residuals.append(rmse(ctscan.ct_forward_project(x, geom, device="cpu"), proj))

    ctscan.sirt_reconstruct(proj, geom, n_iter=12, nonnegative=False, device="cpu", on_iter=record)
    assert len(residuals) == 12
    assert all(b <= a * 1.0001 for a, b in zip(residuals, residuals[1:]))
    assert residuals[-1] < 0.5 * residuals[0]


def test_tomosynthesis_focuses_a_plane_and_has_no_formula():
    """焦点の面では対象の形が出て、面から離れると薄れる(深さ方向の分解能が有限)。"""
    n = 24
    disc = [(0.3, 0.1, 0.0, 0.2, 0.2, 0.12, 0.0, 1.0), (-0.3, -0.2, 0.0, 0.25, 0.1, 0.12, 0.0, 1.0)]
    geom = ctscan.ct_scan_geometry("tomosynthesis", n_views=11, n_u=48, n_v=48, vol_shape=n,
                                   arc_deg=60.0, start_deg=-30.0)
    truth = ctscan.ellipsoid_phantom(n, disc)
    proj = ctscan.ellipsoid_projections(geom, disc, device="cpu")
    with pytest.raises(ValueError, match="tomosynthesis"):
        ctscan.fdk_reconstruct(proj, geom, device="cpu")
    rec = ctscan.sirt_reconstruct(proj, geom, n_iter=20, device="cpu")
    mid = n // 2
    corr = float(np.corrcoef(rec[mid].ravel(), truth[mid].ravel())[0, 1])
    assert corr > 0.8
    assert rec[mid].std() > 1.5 * rec[1].std()


def test_dual_energy_separates_two_materials():
    n = 24
    water = [(0.0, 0.0, 0.0, 0.7, 0.7, 0.7, 0.0, 1.0)]
    metal = [(0.2, 0.1, 0.0, 0.2, 0.2, 0.2, 0.0, 1.0)]
    geom = ctscan.ct_scan_geometry("cone", n_views=60, n_u=48, n_v=48, vol_shape=n)
    pw = ctscan.ellipsoid_projections(geom, water, device="cpu")
    pm = ctscan.ellipsoid_projections(geom, metal, device="cpu")
    mu_low, mu_high = (0.5, 2.0), (0.3, 0.7)
    low = mu_low[0] * pw + mu_low[1] * pm
    high = mu_high[0] * pw + mu_high[1] * pm
    out = ctscan.ct_dual_energy_reconstruct(low, high, geom, mu_low, mu_high, device="cpu")
    assert out["condition"] > 1.0
    assert rmse(out["basis_0"], ctscan.ellipsoid_phantom(n, water)) < 0.1
    assert rmse(out["basis_1"], ctscan.ellipsoid_phantom(n, metal)) < 0.08
    with pytest.raises(ValueError, match="do not separate"):
        ctscan.ct_dual_energy_reconstruct(low, high, geom, (1.0, 2.0), (2.0, 4.0), device="cpu")


def test_constant_and_zero_inputs_do_not_pass_as_good():
    geom = ctscan.ct_scan_geometry("cone", n_views=12, n_u=24, n_v=24, vol_shape=12)
    zero = np.zeros((12, 24, 24))
    assert np.all(ctscan.fdk_reconstruct(zero, geom, device="cpu") == 0.0)
    truth = ctscan.shepp_logan_3d(12)
    proj = ctscan.ellipsoid_projections(geom, device="cpu")
    wrong = ctscan.fdk_reconstruct(proj * 0.0 + 1.0, geom, device="cpu")
    assert rmse(wrong, truth) > 1.5 * rmse(ctscan.fdk_reconstruct(proj, geom, device="cpu"), truth)


@pytest.mark.parametrize("fn", [ctscan.fdk_reconstruct, ctscan.sirt_reconstruct,
                                ctscan.os_sart_reconstruct, ctscan.tv_reconstruct,
                                ctscan.ct_adjoint_project])
def test_reconstructions_refuse_bad_projections(fn):
    geom = ctscan.ct_scan_geometry("cone", n_views=4, n_u=8, n_v=8, vol_shape=4)
    with pytest.raises(ValueError, match="empty"):
        fn(np.zeros((0, 8, 8)), geom, device="cpu")
    with pytest.raises(ValueError, match="shape"):
        fn(np.zeros((8, 4, 8)), geom, device="cpu")
    with pytest.raises(ValueError, match="non-finite"):
        fn(np.full((4, 8, 8), np.nan), geom, device="cpu")
    with pytest.raises(ValueError, match="ct_scan_geometry"):
        fn(np.zeros((4, 8, 8)), {"scan": "cone"}, device="cpu")


def test_geometry_refuses_nonsense():
    with pytest.raises(ValueError, match="scan"):
        ctscan.ct_scan_geometry("mri")
    with pytest.raises(ValueError, match="inside"):
        ctscan.ct_scan_geometry("cone", vol_shape=32, dso=10.0)
    with pytest.raises(ValueError, match="dsd"):
        ctscan.ct_scan_geometry("cone", vol_shape=32, dso=200.0, dsd=100.0)
    with pytest.raises(ValueError, match="helical"):
        ctscan.ct_scan_geometry("cone", arc_deg=720.0)
    with pytest.raises(ValueError, match="one detector row"):
        ctscan.ct_scan_geometry("fan", n_v=4, vol_shape=(1, 8, 8))
    with pytest.raises(ValueError, match="off the detector"):
        ctscan.ct_scan_geometry("cone", n_u=16, offset_u=9.0, n_v=16, vol_shape=8)


def test_parallel_kernels_equal_tomography_on_the_cpu():
    """GPU 経路の定義の確認: 共通の核を numpy で回すと tomography の核と一致する。"""
    img = tomography.ellipse_phantom(64, supersample=2)
    ang = np.linspace(0.0, 180.0, 90, endpoint=False)
    sino = tomography.radon_transform(img, ang)
    geom = tomography_gpu.parallel_slice_geometry(ang, sino.shape[1], (64, 64), 1)
    mine = tomography_gpu.forward_project(img[None], geom, device="cpu")[:, 0]
    assert np.max(np.abs(mine - sino)) < 1e-9 * sino.max()

    rec = tomography.filtered_backprojection(sino, ang, size=64)
    d_theta = tomography._span_weight(ang, None, "t")
    filt = tomography._filter_projections(sino, "ramp", 1.0)
    back = tomography_gpu.voxel_backproject(filt[:, None, :], geom, np.full(90, d_theta),
                                            device="cpu", strict_u=True)[0]
    assert np.max(np.abs(back - rec)) < 1e-9


def test_filter_matches_tomography_on_the_cpu():
    rng = np.random.default_rng(1)
    sino = rng.random((6, 40))
    for kind in ("ramp", "hann", "shepp-logan"):
        mine = tomography_gpu.filter_rows(sino, kind, 0.8, device="cpu")
        assert np.max(np.abs(mine - tomography._filter_projections(sino, kind, 0.8))) < 1e-12


def test_device_contract(monkeypatch):
    monkeypatch.setenv("FULLSEYE_DEVICE", "cpu")
    assert tomography_gpu.resolve_device("cuda") == "cpu"
    monkeypatch.delenv("FULLSEYE_DEVICE")
    with pytest.raises(ValueError, match="device"):
        tomography_gpu.resolve_device("gpu")


def test_ops_are_registered_and_compose_with_the_volume_family():
    import api
    import opstomography
    assert not opstomography.missing()
    for name in ctscan.CTSCAN:
        assert name in opstomography.OPSTOMOGRAPHY
        assert hasattr(api, name)
    geom = ctscan.ct_scan_geometry("cone", n_views=30, n_u=48, n_v=48, vol_shape=24)
    rec = ctscan.fdk_reconstruct(ctscan.ellipsoid_projections(geom, device="cpu"), geom, device="cpu")
    labels = np.asarray(api.vol_threshold(rec, 0.5)) if hasattr(api, "vol_threshold") else rec > 0.5
    assert 0 < int(np.count_nonzero(labels)) < rec.size


def _gpu_ready():
    if tomography_gpu.resolve_device("auto") != "cuda":
        return False
    return True


gpu = pytest.mark.skipif(not _gpu_ready(), reason="needs a CUDA torch")


@pytest.mark.gpu
@gpu
def test_gpu_matches_cpu_on_the_parallel_routes():
    img = tomography.ellipse_phantom(128, supersample=2)
    ang = np.linspace(0.0, 180.0, 120, endpoint=False)
    sino = tomography.radon_transform(img, ang)
    assert np.max(np.abs(tomography_gpu.radon_transform(img, ang, device="cuda") - sino)) < 5e-3
    rec = tomography.filtered_backprojection(sino, ang)
    assert np.max(np.abs(tomography_gpu.filtered_backprojection(sino, ang, device="cuda") - rec)) < 5e-3


@pytest.mark.gpu
@gpu
def test_gpu_matches_cpu_on_cone_fdk():
    geom = ctscan.ct_scan_geometry("cone", n_views=60, n_u=64, n_v=64, vol_shape=32)
    proj = ctscan.ellipsoid_projections(geom, device="cuda")
    assert np.max(np.abs(proj - ctscan.ellipsoid_projections(geom, device="cpu"))) < 5e-3
    a = ctscan.fdk_reconstruct(proj, geom, device="cuda")
    b = ctscan.fdk_reconstruct(proj, geom, device="cpu")
    assert np.max(np.abs(a - b)) < 5e-3


@pytest.mark.gpu
@gpu
def test_gpu_transpose_is_adjoint_in_double():
    geom = ctscan.ct_scan_geometry("cone", n_views=12, n_u=24, n_v=24, vol_shape=12)
    rng = np.random.default_rng(0)
    x = rng.random(geom["vol_shape"])
    y = rng.random((12, 24, 24))
    lhs = np.sum(tomography_gpu.forward_project(x, geom, device="cuda", double=True) * y)
    rhs = np.sum(x * tomography_gpu.adjoint_project(y, geom, device="cuda", double=True))
    assert abs(lhs - rhs) / abs(lhs) < 1e-10
