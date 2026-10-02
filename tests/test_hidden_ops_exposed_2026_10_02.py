"""公開経路の無かった 18 本を ``fs.<名前>`` から出した門(2026-10-02、名前の無い非公開関数の棚卸し)。

どの関数も既存の型つき台帳の約束(台帳 = その実装モジュールの集合)に合わず、facade から出した。
各本に定理か第 2 実装の門を 1 つ以上置く(「走った」でなく「答えが合う」)。
"""
import importlib.util
import math
import warnings

import numpy as np
import pytest
from scipy import ndimage

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import fullseye as fs

NAMES = (
    "ncc_map_3d", "gradient_normals", "subpixel_refine_edges", "min_max_gray_n",
    "gen_gauss_bandpass", "apply_bandpass", "gaussians_to_mesh", "ensure_gray", "ensure_color",
    "dilation2", "get_bounding_box_object_model_3d", "normals_to_gradients", "integrate_gradients",
    "triangulate_points", "rel_pose_to_essential_matrix", "pyr_down", "image_pyramid",
    "rotational_symmetry_score",
)


def test_all_eighteen_are_public_and_documented():
    import api
    for n in NAMES:
        f = getattr(fs, n)
        assert callable(f) and n in fs.__all__ and n in api.__all__, n
        assert (f.__doc__ or "").strip(), "%s に docstring が無い" % n


# ---- 3-D 正規化相互相関 --------------------------------------------------------- #
def _ncc_naive(v, t, z, y, x):
    a = v[z:z + t.shape[0], y:y + t.shape[1], x:x + t.shape[2]].ravel()
    b = t.ravel()
    a = a - a.mean()
    b = b - b.mean()
    return float(a @ b / np.sqrt((a @ a) * (b @ b)))


@pytest.mark.skipif(importlib.util.find_spec("torch") is None,
                    reason="ncc_map_3d は torch の optional backend を使う(CI の full suite には torch が無い)")
def test_ncc_map_3d_peaks_at_the_cut_out_and_matches_a_naive_loop():
    rng = np.random.default_rng(0)
    v = rng.random((20, 22, 24))
    t = v[5:10, 6:11, 7:12].copy()
    m = np.asarray(fs.ncc_map_3d([v], t)[0])
    peak = np.unravel_index(int(np.argmax(m)), m.shape)
    assert m[peak] == pytest.approx(1.0, abs=1e-6)
    # 返りの添字はテンプレートの中心(7, 8, 9)= 左上 (5, 6, 7) + 半径 2
    assert tuple(int(i) for i in peak) == (7, 8, 9)
    for z, y, x in [(0, 0, 0), (3, 9, 4), (10, 12, 15)]:
        assert m[z + 2, y + 2, x + 2] == pytest.approx(_ncc_naive(v, t, z, y, x), abs=1e-5)


# ---- 勾配の単位法線とサブピクセルの端 -------------------------------------------- #
def _sigmoid_edge(edge, H=32, W=32):
    x = np.indices((H, W))[1].astype(float)
    return 1 / (1 + np.exp(-(x - edge) / 0.8))


def test_gradient_normals_are_unit_and_point_across_the_edge():
    g, ny, nx = fs.gradient_normals(_sigmoid_edge(15.5))
    on = g > 1e-6
    assert np.allclose(np.hypot(ny, nx)[on], 1.0, atol=1e-12)
    assert np.allclose(nx[on], 1.0, atol=1e-9)              # 右へ明るくなる → 法線は +x
    g0, ny0, nx0 = fs.gradient_normals(np.zeros((8, 8)))
    assert np.isfinite(ny0).all() and np.isfinite(nx0).all()


def test_subpixel_edge_is_exact_at_the_half_pixel_and_close_elsewhere():
    pts = np.array([[r, 15.0] for r in range(5, 27)] + [[r, 16.0] for r in range(5, 27)])
    for edge, tol in ((15.5, 1e-9), (15.3, 0.15), (15.8, 0.15)):
        g, ny, nx = fs.gradient_normals(_sigmoid_edge(edge))
        ref = fs.subpixel_refine_edges(pts, g, ny, nx)
        assert abs(ref[:, 1].mean() - edge) <= tol, (edge, ref[:, 1].mean())


# ---- 画素ごとの最小・最大 --------------------------------------------------------- #
def test_min_max_gray_n_is_the_stack_minimum_and_maximum():
    stack = [np.random.default_rng(i).random((6, 7)) for i in range(4)]
    r = fs.min_max_gray_n(stack)
    assert np.array_equal(r["min"], np.min(stack, axis=0)) and np.array_equal(r["max"], np.max(stack, axis=0))


# ---- 周波数の帯域通過 ------------------------------------------------------------- #
def test_apply_bandpass_scales_a_pure_sinusoid_by_the_mask_value():
    H = W = 64
    m = fs.gen_gauss_bandpass((H, W), 0.02, 0.2)
    x = np.indices((H, W))[1]
    for k in (2, 8, 20):
        img = np.cos(2 * np.pi * k * x / W)
        out = np.asarray(fs.apply_bandpass(img, m), float)
        assert np.allclose(out, m[0, k] * img, atol=1e-9), k


# ---- 色の揃え --------------------------------------------------------------------- #
def test_ensure_gray_and_color_round_trip_shapes():
    rgb = np.random.default_rng(2).random((5, 6, 3))
    g = fs.ensure_gray(rgb)
    assert g.shape == (5, 6)
    assert np.array_equal(fs.ensure_gray(g), g)
    c = fs.ensure_color(g)
    assert c.shape == (5, 6, 3) and np.array_equal(c[..., 0], c[..., 2])


# ---- 参照点つき膨張 --------------------------------------------------------------- #
def test_dilation2_with_a_centred_reference_is_plain_dilation():
    rng = np.random.default_rng(3)
    region = rng.random((30, 30)) > 0.93
    se = np.ones((3, 5), bool)
    got = fs.dilation2(region, se, row=1, col=2)
    assert np.array_equal(got, ndimage.binary_dilation(region, structure=se))


def test_moving_the_reference_point_translates_the_result_by_one_pixel():
    region = np.zeros((20, 20), bool)
    region[8:12, 6:10] = True
    se = np.ones((1, 3), bool)
    a = fs.dilation2(region, se, row=0, col=1)
    b = fs.dilation2(region, se, row=0, col=2)
    shifted = [np.array_equal(b, np.roll(a, s, axis=1)) for s in (-1, 1)]
    assert sum(shifted) == 1                                   # ちょうど 1 画素の並進


# ---- 外接箱 ----------------------------------------------------------------------- #
def test_bounding_box_is_the_coordinate_wise_extremes():
    p = np.random.default_rng(5).normal(size=(100, 3))
    d = fs.get_bounding_box_object_model_3d(p)
    assert np.allclose(d["min"], p.min(0)) and np.allclose(d["max"], p.max(0))
    assert np.allclose(d["extent"], p.max(0) - p.min(0))


# ---- 法線 → 勾配 → 高さ(Frankot–Chellappa) ------------------------------------- #
def test_frankot_chellappa_is_exact_for_a_periodic_band_limited_surface():
    H, W = 48, 64
    y, x = np.indices((H, W)).astype(float)
    z = np.sin(2 * np.pi * x / W) * np.cos(2 * np.pi * 2 * y / H)
    zx = np.cos(2 * np.pi * x / W) * (2 * np.pi / W) * np.cos(2 * np.pi * 2 * y / H)
    zy = -np.sin(2 * np.pi * x / W) * np.sin(2 * np.pi * 2 * y / H) * (2 * np.pi * 2 / H)
    n = np.dstack([-zx, -zy, np.ones_like(z)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    p, q = fs.normals_to_gradients(n)
    assert np.allclose(p, zx, atol=1e-12) and np.allclose(q, zy, atol=1e-12)
    zr = fs.integrate_gradients(p, q)
    assert np.abs(zr - (z - z.mean())).max() < 1e-10


# ---- 二視点の幾何 ----------------------------------------------------------------- #
def _two_views():
    K = np.array([[500, 0, 320], [0, 500, 240], [0, 0, 1.0]])
    a = 0.1
    R = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
    t = np.array([[-0.5], [0.02], [0.03]])
    P1 = K @ np.hstack([np.eye(3), np.zeros((3, 1))])
    P2 = K @ np.hstack([R, t])
    X = np.random.default_rng(2).uniform([-1, -1, 4], [1, 1, 8], (20, 3))
    Xh = np.hstack([X, np.ones((20, 1))])
    u1 = (P1 @ Xh.T).T
    u2 = (P2 @ Xh.T).T
    return P1, P2, X, u1[:, :2] / u1[:, 2:], u2[:, :2] / u2[:, 2:], R, t.ravel()


def test_triangulation_is_exact_without_noise():
    P1, P2, X, u1, u2, _, _ = _two_views()
    assert np.abs(fs.triangulate_points(P1, P2, u1, u2) - X).max() < 1e-9


def test_essential_matrix_satisfies_the_epipolar_constraint_and_has_singular_values_s_s_0():
    _, _, X, _, _, R, t = _two_views()
    E = fs.rel_pose_to_essential_matrix(R, t)
    x1 = X / X[:, 2:]
    X2 = (R @ X.T).T + t
    x2 = X2 / X2[:, 2:]
    assert np.abs(np.einsum("ni,ij,nj->n", x2, E, x1)).max() < 1e-12
    s = np.linalg.svd(E, compute_uv=False)
    assert s[0] == pytest.approx(s[1], rel=1e-12) and s[2] < 1e-12 * s[0]


# ---- 画像のピラミッド ------------------------------------------------------------- #
def test_pyramid_halves_and_keeps_a_constant_constant():
    im = np.random.default_rng(1).random((65, 50))
    shapes = [a.shape for a in fs.image_pyramid(im, 4)]
    assert shapes[0] == (65, 50)
    for (h0, w0), (h1, w1) in zip(shapes, shapes[1:]):
        assert h1 == (h0 + 1) // 2 and w1 == (w0 + 1) // 2
    assert np.ptp(fs.pyr_down(np.full((32, 32), 0.7))) == pytest.approx(0.0, abs=1e-12)


# ---- 回転対称 --------------------------------------------------------------------- #
def test_a_fourfold_cloud_scores_zero_for_divisors_of_four_only():
    base = np.array([[1.0, 0.2, 0.0], [1.5, -0.1, 0.3], [0.7, 0.4, -0.2]])
    pts = []
    for a in np.linspace(0, 2 * np.pi, 4, endpoint=False):
        Rz = np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])
        pts.append(base @ Rz.T)
    P = np.concatenate(pts)
    s = {k: float(fs.rotational_symmetry_score(P, [0, 0, 0], [0, 0, 1], k)) for k in (2, 3, 4)}
    assert s[4] < 1e-9 and s[2] < 1e-9 and s[3] > 0.5, s


# ---- ガウシアン → メッシュ(open3d が在るときだけ)-------------------------------- #
@pytest.mark.skipif(importlib.util.find_spec("open3d") is None or importlib.util.find_spec("torch") is None,
                    reason="open3d と torch が要る")
def test_gaussians_on_a_unit_sphere_mesh_to_radius_one():
    import torch
    rng = np.random.default_rng(7)
    n = 3000
    v = rng.normal(size=(n, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    g = {"means": torch.tensor(v, dtype=torch.float32), "scales": torch.full((n, 3), math.log(0.03)),
         "quats": torch.tensor(np.tile([1.0, 0, 0, 0], (n, 1)), dtype=torch.float32),
         "opacities": torch.full((n,), 3.0), "sh0": torch.full((n, 1, 3), 0.5)}
    mesh, pcd = fs.gaussians_to_mesh(g, log=lambda *a, **k: None)
    r = np.linalg.norm(np.asarray(mesh.vertices), axis=1)
    assert abs(np.median(r) - 1.0) < 0.01
    assert len(np.asarray(pcd.points)) > 0


# ---- 3-D の合成パイプライン(pipeline3d、fs.<名前> へ出した 6 本)----------------- #
PIPELINE3D = ("register_pointclouds", "align_cad_to_scan", "measure_plane", "inspect_roundness",
              "match_sdf", "register_auto")


def test_pipeline3d_names_are_public():
    import api
    for n in PIPELINE3D:
        assert callable(getattr(fs, n)) and n in fs.__all__ and n in api.__all__, n


def test_measure_plane_recovers_a_tilted_plane_exactly_and_measures_known_flatness():
    """雑音なしの平面は法線が厳密・平面度 0。±h の 2 値の段差を足すと PV = 2h·cosθ(θ = 法線と z の角)。"""
    rng = np.random.default_rng(0)
    xy = rng.uniform(-1, 1, (400, 2))
    n_true = np.array([0.3, -0.2, 1.0])
    n_true /= np.linalg.norm(n_true)
    z = -(n_true[0] * xy[:, 0] + n_true[1] * xy[:, 1]) / n_true[2]
    P = np.c_[xy, z]
    r = fs.measure_plane(P)
    assert abs(abs(float(np.dot(r["normal"], n_true))) - 1.0) < 1e-10
    assert r["flatness_rms"] < 1e-10 and r["pv"] < 1e-10
    # 各点を法線方向に +h と −h へ複製: 散布行列は元 + 2N h² n nᵀ で固有ベクトルは不変 → 直交距離の
    # 最小二乗平面は厳密に元の面、符号つき残差は ±h ちょうど(PV = 2h、RMS = h)。
    # 2026-10-02 の回帰: 符号なし距離で PV を出していた版は PV ≈ 0(max|d| − min|d| = h − h)を返す。
    h = 0.01
    r2 = fs.measure_plane(np.vstack([P + h * n_true, P - h * n_true]))
    assert r2["pv"] == pytest.approx(2 * h, rel=1e-9)
    assert r2["flatness_rms"] == pytest.approx(h, rel=1e-9)


def test_inspect_roundness_on_a_perfect_sphere():
    rng = np.random.default_rng(1)
    d = rng.normal(size=(500, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    P = np.array([1.0, -2.0, 0.5]) + 3.0 * d
    r = fs.inspect_roundness(P)
    assert np.allclose(r["center"], [1.0, -2.0, 0.5], atol=1e-9)
    assert r["radius"] == pytest.approx(3.0, abs=1e-9)
    assert r["roundness_pv"] < 1e-9 and r["rms"] < 1e-9


def test_pipeline3d_stand_in_raises_a_clear_import_error():
    import api
    f = api._pipeline3d_missing("measure_plane", ImportError("no torch"))
    with pytest.raises(ImportError, match="pipeline3d"):
        f(np.zeros((3, 3)))

