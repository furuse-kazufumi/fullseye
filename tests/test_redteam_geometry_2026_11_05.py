"""敵対的検証 2026-11-05(geometry)の回帰テスト。

どれも「返した値を、独立に計算した真値・不変量と突き合わせる」形にしてある:
- RANSAC が返す内れ値は、返した模型で数え直した内れ値と一致する(G1 / G1b / feat_shot)。
- 縮退判定は尺度に依らない(点群と閾値を同じ倍率で縮めても結果が変わらない)(G9 / G10)。
- 変換の推定は、定義そのもの(R·d_src ∥ d_dst、H と −H は同じ射影)を満たす(G3 / G4 / G7)。
"""
import math

import numpy as np
import pytest
from conftest import requires_backend

import camera as C
import feat_shot
import featmatch
import mosaic
import odometry
import pcseg
import pnp3d
import pose_quat as PQ
import ransac_fit as RF
import reconstruction as RC
import transforms as T
import twoview as TV

K_PNP = np.array([[800.0, 0, 320], [0, 800.0, 240], [0, 0, 1]])


# ── G1: pnp_ransac が返す内れ値は返す姿勢の内れ値 ─────────────────────────────── #
@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_g1_pnp_ransac_mask_belongs_to_returned_pose(seed):
    R = C.rodrigues([0.2, -0.3, 0.1]); t = np.array([0.1, -0.1, 4.0])
    rng = np.random.default_rng(seed)
    X = rng.uniform(-1, 1, (200, 3))
    uv, _ = C.project_points(X, K_PNP, R, t)
    uv = uv + rng.normal(0, 1.0, uv.shape)
    out = rng.random(200) < 0.3
    uv[out] = rng.uniform([0, 0], [640, 480], (out.sum(), 2))
    Rr, tr, mask, info = pnp3d.pnp_ransac(X, uv, K_PNP, thresh=2.0, iters=300, seed=0)
    err = np.linalg.norm(pnp3d._project(X, K_PNP, Rr, tr) - uv, axis=1)
    recomputed = err < 2.0
    assert recomputed.sum() >= 6
    assert np.array_equal(mask, recomputed)
    assert info["n_inliers"] == int(recomputed.sum())
    assert info["inlier_ratio"] == pytest.approx(recomputed.mean())
    assert info["rms"] == pytest.approx(pnp3d.reprojection_error(X[mask], uv[mask], K_PNP, Rr, tr))


# ── G1b: mosaic / reconstruction / feat_shot の兄弟 ───────────────────────────── #
def _mosaic_case():
    rng = np.random.default_rng(0)
    H = np.array([[1.02, 0.03, 4.0], [-0.02, 0.98, -6.0], [2e-5, -1e-5, 1.0]])
    p1 = rng.uniform([0, 0], [480, 640], (300, 2))
    p2 = mosaic._apply_h(H, p1) + rng.normal(0, 0.8, (300, 2))
    out = rng.random(300) < 0.3
    p2[out] = rng.uniform([0, 0], [480, 640], (out.sum(), 2))
    return p1, p2


def test_g1b_mosaic_inliers_belong_to_returned_h():
    p1, p2 = _mosaic_case()
    r = mosaic.proj_match_points_ransac(p1, p2, thresh=2.0, iters=500, seed=0)
    e = np.linalg.norm(mosaic._apply_h(r["H"], p1) - p2, axis=1)
    recomputed = e < 2.0
    assert recomputed.sum() >= 4
    assert np.array_equal(r["inliers"], recomputed)
    assert r["num_inliers"] == int(recomputed.sum())


def _two_view(n=300, noise=0.5, seed=0):
    rng = np.random.default_rng(seed)
    K = C.intrinsic_matrix(500, 500, 320, 240)
    R2 = C.rodrigues([0, 0.2, 0.02]); t2 = np.array([0.5, 0.0, 0.05])
    out = rng.random(n) < 0.3
    X = rng.uniform(-1, 1, (n, 3)) + [0, 0, 5]
    a, _ = C.project_points(X, K); b, _ = C.project_points(X, K, R2, t2)
    a = a + rng.normal(0, noise, a.shape); b = b + rng.normal(0, noise, b.shape)
    b[out] = rng.uniform([0, 0], [640, 480], (out.sum(), 2))
    return a, b, K


def test_g1b_fundamental_inliers_belong_to_returned_f():
    a, b, _ = _two_view()
    r = RC.match_fundamental_matrix_ransac(a, b, thresh=1.0, iters=200, seed=0)
    recomputed = RC._sampson(r["F"], a, b) < 1.0
    assert recomputed.sum() >= 8
    assert np.array_equal(r["inliers"], recomputed)
    assert r["num_inliers"] == int(recomputed.sum())


@pytest.mark.parametrize("iters", [500, 50, 10])
def test_g1b_feat_shot_ransac_rigid_inliers_belong_to_returned_pose(iters):
    # feat_shot は torch(threed extra)の上で解く。torch の無い CI(py3.12/3.14)では飛ばす。
    requires_backend("torch")
    rng = np.random.default_rng(0)
    src = rng.uniform(-1, 1, (200, 3))
    R = C.rodrigues([0.3, -0.2, 0.5]); t = np.array([0.2, 0.1, -0.3])
    dst = src @ R.T + t + rng.normal(0, 0.004, (200, 3))
    pairs = np.column_stack([np.arange(200), np.arange(200)])
    bad = rng.random(200) < 0.3
    pairs[bad, 1] = rng.integers(0, 200, bad.sum())
    Rr, tr, inl, S, D = feat_shot.ransac_rigid(src, dst, pairs, inlier_thr=0.01, iters=iters)
    recomputed = np.linalg.norm(S @ Rr.T + tr - D, axis=1) < 0.01
    assert recomputed.sum() >= 3
    assert np.array_equal(inl, recomputed)


# ── G8: 8 点未満の F は作らない、E のキーは F と揃う ─────────────────────────── #
def test_g8_fundamental_ransac_rejects_fewer_than_8_points():
    a, b, K = _two_view(n=20, noise=0.0)
    with pytest.raises(ValueError):
        RC.match_fundamental_matrix_ransac(a[:7], b[:7])
    with pytest.raises(ValueError):
        RC.match_essential_matrix_ransac(a[:7], b[:7], K)


def test_g8_essential_ransac_keys_match_fundamental():
    a, b, K = _two_view(n=60, noise=0.0)
    rf = RC.match_fundamental_matrix_ransac(a, b, seed=0)
    re = RC.match_essential_matrix_ransac(a, b, K, seed=0)
    assert set(re) == {"E", "inliers", "num_inliers"}
    assert re["num_inliers"] == rf["num_inliers"] == int(np.sum(rf["inliers"]))
    sv = np.linalg.svd(re["E"], compute_uv=False)
    assert sv[2] < 1e-9 * sv[0]


# ── G2: 内れ値率が低くても適応回数の式で 0 割りしない ─────────────────────────── #
def _fm_tables():
    """報告の再現(p6_ransac_zerodiv.py)と同じ乱数列で 3 つの照合表を作る。"""
    rng = np.random.default_rng(0)
    K = C.intrinsic_matrix(500, 500, 320, 240)
    ax = np.array([0.1, 1, 0]) / np.linalg.norm([0.1, 1, 0])
    R2 = C.rodrigues(ax * 0.2); t2 = np.array([0.5, 0.0, 0.05])
    out = {}
    for n_in, n_out in [(300, 0), (300, 700), (300, 3000)]:
        X = rng.uniform(-1, 1, (n_in, 3)) + [0, 0, 5]
        a, _ = C.project_points(X, K); b, _ = C.project_points(X, K, R2, t2)
        oa = rng.uniform([0, 0], [640, 480], (n_out, 2)); ob = rng.uniform([0, 0], [640, 480], (n_out, 2))
        p1 = np.vstack([a, oa]); p2 = np.vstack([b, ob])
        perm = rng.permutation(len(p1))
        out[n_out] = {"kind": "feature_matches", "pts1": p1[perm], "pts2": p2[perm],
                      "image_shape1": (480, 640), "image_shape2": (480, 640)}
    return out


@pytest.mark.parametrize("n_out,seed", [(700, 0), (3000, 1), (700, 1), (3000, 0)])
def test_g2_ransac_low_inlier_ratio_does_not_divide_by_zero(n_out, seed):
    tab = _fm_tables()[n_out]
    r = featmatch.ransac_fundamental(tab, thresh=1.0, seed=seed)
    assert 1 <= r["iterations"] <= 5000
    F = np.asarray(r["F"], float)
    assert np.isfinite(F).all()


# ── G3: point_line_to_hom_mat2d は R·d_src を d_dst に重ねる ─────────────────── #
@pytest.mark.parametrize("ds,dd", [((0, 1), (1, 0)), ((1, 0), (0, 1)), ((1, 1), (1, -1)),
                                   ((0.6, 0.8), (0.8, 0.6)), ((-1, 0.2), (0.3, -2.0))])
def test_g3_point_line_rotation_maps_direction(ds, dd):
    H = T.point_line_to_hom_mat2d((3.0, 4.0), ds, (10.0, -2.0), dd)
    v = H[:2, :2] @ np.asarray(ds, float); v /= np.linalg.norm(v)
    u = np.asarray(dd, float) / np.linalg.norm(dd)
    assert v @ u == pytest.approx(1.0, abs=1e-12)
    assert np.allclose(H[:2, :2] @ [3.0, 4.0] + H[:2, 2], [10.0, -2.0])
    assert np.linalg.det(H[:2, :2]) == pytest.approx(1.0)


# ── G4: point_pluecker_line_to_hom_mat3d は反平行でも d1 を d2 に重ねる ─────── #
@pytest.mark.parametrize("d1,d2", [((1, 0, 0), (0, 1, 0)), ((1, 0, 0), (-1, 0, 0)),
                                   ((0, 0, 1), (0, 0, -1)), ((1, 2, 3), (-1, -2, -3)),
                                   ((1, 1, 0), (1, 1, 0))])
def test_g4_pluecker_rotation_maps_direction(d1, d2):
    Tm = T.point_pluecker_line_to_hom_mat3d(np.zeros(3), {"direction": d1}, np.ones(3), d2)
    R = Tm[:3, :3]
    u1 = np.asarray(d1, float) / np.linalg.norm(d1); u2 = np.asarray(d2, float) / np.linalg.norm(d2)
    assert np.allclose(R @ u1, u2, atol=1e-12)
    assert np.allclose(R.T @ R, np.eye(3), atol=1e-12)
    assert np.linalg.det(R) == pytest.approx(1.0)
    assert np.allclose(Tm[:3, 3], np.ones(3))


# ── G5: dual_quat_trans_line_3d が動く(pose_quat の剛体変換と一致)──────────── #
def test_g5_dual_quat_trans_line_matches_pose_quat():
    dq = PQ.pose_to_dual_quat([0.3, -0.2, 1.1, 20, -35, 50])
    p = np.array([0.4, -1.2, 2.0]); d = np.array([1.0, 2.0, -0.5])
    out = T.dual_quat_trans_line_3d(dq, p, d)
    assert np.allclose(out["point"], PQ.dual_quat_trans_point_3d(dq, *p))
    Rq = PQ.quat_to_hom_mat3d(dq[:4])[:3, :3]
    assert np.allclose(out["direction"], Rq @ d / np.linalg.norm(d))


# ── G6: vector_to_hom_mat3d は剛体(倍率は推定しない)と明記、相似は umeyama_align ─ #
def test_g6_vector_to_hom_mat3d_is_rigid_and_points_to_similarity():
    rng = np.random.default_rng(0)
    P = rng.normal(size=(20, 3)); R = C.rodrigues([0.3, 0.2, -0.1]); t = np.array([1.0, 2, 3])
    Tm = T.vector_to_hom_mat3d(P, P @ R.T + t)
    assert np.allclose(Tm[:3, :3], R) and np.allclose(Tm[:3, 3], t)
    doc = T.vector_to_hom_mat3d.__doc__
    assert "相似" not in doc.splitlines()[0]          # 1 行目で相似を名乗らない
    assert "umeyama_align" in doc
    s, Rs, ts = odometry.umeyama_align(P, 2.0 * P @ R.T + t, with_scale=True)
    assert s == pytest.approx(2.0) and np.allclose(Rs, R)


# ── G7: proj_hom_mat2d_to_pose は H の符号に依らず板をカメラの前に置く ───────── #
@pytest.mark.parametrize("s", [1.0, -1.0, 3.0, -0.25])
def test_g7_homography_sign_does_not_change_pose(s):
    K = C.intrinsic_matrix(800, 800, 320, 240)
    Rp = C.rodrigues([0.2, -0.1, 0.05]); tp = np.array([0.1, -0.05, 2.0])
    Hh = K @ np.column_stack([Rp[:, 0], Rp[:, 1], tp])
    Tm = T.proj_hom_mat2d_to_pose(s * Hh, K)
    assert np.allclose(Tm[:3, :3], Rp, atol=1e-12)
    assert np.allclose(Tm[:3, 3], tp, atol=1e-12)
    assert Tm[2, 3] > 0


# ── G9: 縮退判定は尺度に依らない ────────────────────────────────────────────── #
def _plane_cloud():
    rng = np.random.default_rng(0)
    xy = rng.uniform(-1, 1, (300, 2))
    pl = np.column_stack([xy, 0.1 * xy[:, 0] - 0.2 * xy[:, 1] + 0.5 + rng.normal(0, 0.002, 300)])
    return np.vstack([pl, rng.uniform(-1, 1, (150, 3)) + [0, 0, 0.5]])


@pytest.mark.parametrize("s", [1e-6, 3e-7, 1e-8, 1e6])
def test_g9_fit_plane_ransac_scale_invariant(s):
    P = _plane_cloud()
    _, ref = pcseg.fit_plane_ransac(P, thresh=0.01, iters=200)
    _, inl = pcseg.fit_plane_ransac(P * s, thresh=0.01 * s, iters=200)
    assert ref.sum() >= 300
    assert np.array_equal(inl, ref)


@pytest.mark.parametrize("s", [3e-7, 1e-8, 1e6])
def test_g9_ransac_plane_scale_invariant(s):
    P = _plane_cloud()
    _, ref, info0 = RF.ransac_plane(P, thresh=0.01, iters=200)
    _, m, info = RF.ransac_plane(P * s, thresh=0.01 * s, iters=200)
    assert ref.sum() >= 300 and not info0["degenerate"]
    assert not info["degenerate"]
    assert np.array_equal(m, ref)


@pytest.mark.parametrize("s", [1e-12, 1e-13, 1e-15])
def test_g9_ransac_line_scale_invariant(s):
    rng = np.random.default_rng(1)
    t = rng.uniform(-1, 1, 200)
    L = np.r_[np.c_[t, 0.5 * t, 0.001 * rng.standard_normal(200)], rng.uniform(-1, 1, (100, 3))]
    _, ref, _ = RF.ransac_line(L, thresh=0.01, iters=300, seed=0)
    _, m, info = RF.ransac_line(L * s, thresh=0.01 * s, iters=300, seed=0)
    assert ref.sum() >= 200
    assert not info["degenerate"]
    assert np.array_equal(m, ref)


@pytest.mark.parametrize("s", [1e-4, 1e-6])
def test_g9_feat_shot_ransac_rigid_scale_invariant(s):
    # feat_shot は torch(threed extra)の上で解く。torch の無い CI(py3.12/3.14)では飛ばす。
    requires_backend("torch")
    rng = np.random.default_rng(0)
    src = rng.uniform(-1, 1, (200, 3))
    R = C.rodrigues([0.3, -0.2, 0.5]); t = np.array([0.2, 0.1, -0.3])
    dst = src @ R.T + t
    pairs = np.column_stack([np.arange(200), np.arange(200)])
    bad = rng.random(200) < 0.3
    pairs[bad, 1] = rng.integers(0, 200, bad.sum())
    ref = feat_shot.ransac_rigid(src, dst, pairs, inlier_thr=0.01, iters=500)
    r = feat_shot.ransac_rigid(src * s, dst * s, pairs, inlier_thr=0.01 * s, iters=500)
    assert ref is not None and r is not None
    assert np.allclose(r[0], R, atol=1e-9)
    assert np.array_equal(r[2], ref[2])


# ── G10: fit_sphere_ransac は平行移動に依らない ─────────────────────────────── #
@pytest.mark.parametrize("off", [1e6, 3e6, 1e7])
def test_g10_fit_sphere_ransac_translation_invariant(off):
    rng = np.random.default_rng(0)
    u = rng.normal(size=(300, 3)); u /= np.linalg.norm(u, axis=1, keepdims=True)
    c_true = np.array([0.2, -0.1, 0.3]); r_true = 0.7
    S = c_true + r_true * u + rng.normal(0, 0.002, (300, 1)) * u
    P = np.vstack([S, rng.uniform(-1, 1, (100, 3))])
    c0, r0, inl0 = pcseg.fit_sphere_ransac(P, thresh=0.01, iters=200)
    o = np.array([off, -off, 0.5 * off])
    res = pcseg.fit_sphere_ransac(P + o, thresh=0.01, iters=200)
    assert res is not None
    c, r, inl = res
    assert abs(r - r_true) < 1e-3
    assert np.linalg.norm(c - o - c_true) < 1e-3
    assert abs(int(inl.sum()) - int(inl0.sum())) <= 2


# ── G11: recover_pose の平面判定は視差(基線)に依らない ─────────────────────── #
def _tv_scene(b, kind="general", n=60, sigma=0.0, seed=0):
    rng = np.random.default_rng(seed)
    K = C.intrinsic_matrix(800, 800, 320, 240)
    X = rng.uniform(-1, 1, (n, 3)) * [1, 1, 0.8] + [0, 0, 5]
    if kind == "plane":
        X[:, 2] = 5 + 0.3 * X[:, 0] - 0.2 * X[:, 1]
    R2 = C.rodrigues([0, 0.05, 0])
    t2 = np.zeros(3) if kind == "rotation" else np.array([b, 0, 0])
    a, _ = C.project_points(X, K); c, _ = C.project_points(X, K, R2, t2)
    a = a + rng.normal(0, sigma, a.shape); c = c + rng.normal(0, sigma, c.shape)
    return a, c, K, R2, t2


@pytest.mark.parametrize("b", [0.5, 0.05, 0.01, 0.002])
def test_g11_recover_pose_small_baseline_non_planar_is_solved(b):
    a, c, K, R2, t2 = _tv_scene(b)
    R, t, _ = TV.recover_pose(a, c, K)
    assert np.abs(R - R2).max() < 1e-6
    assert np.linalg.norm(t - t2 / np.linalg.norm(t2)) < 1e-4


@pytest.mark.parametrize("kind,sigma", [("plane", 0.0), ("plane", 0.5), ("rotation", 0.0),
                                        ("rotation", 0.5), ("plane", 2.0)])
def test_g11_recover_pose_still_rejects_planar_and_rotation(kind, sigma):
    a, c, K, _, _ = _tv_scene(0.5, kind=kind, sigma=sigma)
    with pytest.raises(ValueError):
        TV.recover_pose(a, c, K)


def test_g11_planarity_ratio_does_not_scale_with_baseline():
    rs = [TV._planar_degeneracy_ratio(*_tv_scene(b)[:2]) for b in (0.5, 0.05, 0.005)]
    assert len(rs) == 3
    # 雑音のない一般 3-D は基線を 1/100 にしても「平面でない」側に大きく残る
    assert min(rs) > 1e3
    rp = TV._planar_degeneracy_ratio(*_tv_scene(0.5, kind="plane")[:2])
    assert rp < 1.0


# ── G10 の兄弟: measure.fit_circle も重心に寄せる、半径の床は相対量 ────────────── #
def test_g10_sibling_measure_fit_circle_translation_and_scale():
    import measure
    t = np.linspace(0, 6, 40)
    ref = measure.fit_circle(np.c_[2 + 3 * np.sin(t), 5 + 3 * np.cos(t)])
    assert ref["r"] == pytest.approx(3.0, abs=1e-12)
    n_checked = 0
    for off in (1e6, 1e8):
        r = measure.fit_circle(np.c_[off + 2 + 3 * np.sin(t), -off + 5 + 3 * np.cos(t)])
        assert r["r"] == pytest.approx(3.0, abs=1e-6)
        assert r["cy"] - off == pytest.approx(ref["cy"], abs=1e-6)
        n_checked += 1
    assert n_checked == 2
    tiny = measure.fit_circle(np.c_[1e-7 * np.sin(t), 1e-7 * np.cos(t)])   # 半径 1e-7 も円
    assert tiny["r"] == pytest.approx(1e-7, rel=1e-9)


# ── 未再現の疑い(確認して本物だったもの): pose_quat の + 1e-12 ─────────────────── #
@pytest.mark.parametrize("s", [1.0, 1e-6, 1e-12])
def test_pose_quat_spherical_latitude_exact_at_pole_and_small_scale(s):
    r, lon, lat = PQ.convert_point_3d_cart_to_spher(0.0, 0.0, s)
    assert r == pytest.approx(s) and lat == pytest.approx(np.pi / 2, abs=1e-15)
    r, lon, lat = PQ.convert_point_3d_cart_to_spher(s, 0.0, s)
    assert lat == pytest.approx(np.pi / 4, abs=1e-15)
    back = PQ.convert_point_3d_spher_to_cart(r, lon, lat)
    assert np.allclose(back, [s, 0.0, s], rtol=1e-14, atol=0)


@pytest.mark.parametrize("theta", [2.0, 1e-3, 1e-6, 2e-8, 3e-9])
def test_pose_quat_dual_quat_to_screw_round_trip_small_angles(theta):
    dq = PQ.screw_to_dual_quat(0, 0.6, 0.8, 0, 0, 0, theta=theta, d=0.5)
    r = PQ.dual_quat_to_screw(dq)
    assert r["theta"] == pytest.approx(theta, rel=1e-9)
    assert r["d"] == pytest.approx(0.5, rel=1e-9)
    assert np.allclose(r["axis"], [0, 0.6, 0.8], atol=1e-9)


# ── 未再現の疑い(確認して本物だったもの): calib.image_points_to_world_plane の lam < 0 ─ #
def test_image_points_to_world_plane_behind_camera_is_nan():
    import calib
    K = C.intrinsic_matrix(800, 800, 320, 240)
    R = C.rodrigues([-np.pi / 2 + 0.1, 0, 0]); cam = np.array([0, 0, 2.0]); t = -R @ cam
    Tm = np.eye(4); Tm[:3, :3] = R; Tm[:3, 3] = t
    px = np.array([[400.0, 320.0], [100.0, 320.0], [0.0, 320.0]])        # (row, col)
    W = calib.image_points_to_world_plane(K, Tm, px)
    n_checked = 0
    for w, p in zip(W, px):
        ray = R.T @ np.linalg.inv(K) @ np.array([p[1], p[0], 1.0])
        lam = -cam[2] / ray[2]                                            # 独立に解いた交点の係数
        if lam > 0:
            Xc = R @ np.r_[w, 0.0] + t
            assert Xc[2] > 0
            assert np.allclose((K @ Xc)[:2] / Xc[2], p[::-1])
        else:
            assert np.isnan(w).all()
        n_checked += 1
    assert n_checked == 3
    assert np.isnan(W).any() and np.isfinite(W).any()


# ── 未再現の疑い(確認して本物だったもの): Zhang 法のホモグラフィに Hartley 正規化 ─── #
def test_zhang_intrinsics_do_not_depend_on_plane_origin():
    """Zhang の K は平面座標の原点の取り方に依らない(H = H0·T で h1, h2 は不変)。

    同じ画像点で物体座標だけ平行移動しても K は同じはず。正規化なしの DLT は原点が遠いと
    条件が悪く、雑音つきで K が原点の取り方で変わっていた。"""
    import calib
    K = C.intrinsic_matrix(1200, 1200, 640, 480)
    g = np.stack(np.meshgrid(np.arange(9), np.arange(6)), -1).reshape(-1, 2) * 20.0    # mm
    obj = g - g.mean(0)
    rng = np.random.default_rng(3)
    views = []
    for _ in range(8):
        R = C.rodrigues(rng.uniform(-0.5, 0.5, 3)); t = np.array([0.0, 0.0, 500.0])
        uv, _ = C.project_points(np.c_[obj, np.zeros(len(obj))], K, R, t)
        views.append((uv + rng.normal(0, 0.05, uv.shape))[:, ::-1])
    ref = calib.camera_calibration(obj, views)
    n_checked = 0
    for off in (1000.0, 5000.0):
        r = calib.camera_calibration(obj + off, views)
        for k in ("fx", "fy", "cx", "cy"):
            assert r[k] == pytest.approx(ref[k], rel=1e-6), (off, k, r[k], ref[k])
            n_checked += 1
    assert n_checked == 8
    assert ref["fx"] == pytest.approx(1200, rel=5e-3)


@pytest.mark.parametrize("which", ["calib", "transforms"])
def test_normalised_dlt_is_covariant_with_source_translation(which):
    """雑音つきでも、src を平行移動して推定した H' は H·T⁻¹ に一致する(正規化 DLT の性質)。"""
    import calib
    fit = calib._homography_dlt if which == "calib" else T.vector_to_proj_hom_mat2d
    rng = np.random.default_rng(5)
    src = rng.uniform(0, 200, (40, 2))
    Ht = np.array([[1.1, 0.05, 30.0], [-0.04, 0.95, -12.0], [2e-4, -1e-4, 1.0]])
    h = np.c_[src, np.ones(len(src))] @ Ht.T
    dst = h[:, :2] / h[:, 2:] + rng.normal(0, 0.5, (40, 2))
    H0 = fit(src, dst)
    n_checked = 0
    for off in (1e3, 1e5):
        Toff = np.array([[1.0, 0, off], [0, 1.0, -off], [0, 0, 1.0]])
        H1 = fit(src + [off, -off], dst)
        expect = H0 @ np.linalg.inv(Toff)
        assert np.allclose(H1 / H1[2, 2], expect / expect[2, 2], rtol=1e-6, atol=1e-9)
        n_checked += 1
    assert n_checked == 2


def test_g1b_mosaic_refit_never_loses_consensus_of_best_hypothesis():
    """当てはめ直しは RANSAC の目的(合意の数)を悪くしてはいけない。

    mosaic の DLT は正規化なしで、点が少ないと当てはめ直した H が仮説より悪い(13 点中 8 点)。
    返す模型の内れ値は、同じ乱数列で独立に回した最良仮説の内れ値の数を下回らないこと。"""
    n_cases = 0
    for seed in range(40):
        rng = np.random.default_rng(seed)
        p1 = rng.uniform([0, 0], [480, 640], (13, 2))
        p2 = p1 + [3.3, -5.1] + rng.normal(0, 0.7, (13, 2))
        r = mosaic.proj_match_points_ransac(p1, p2, thresh=2.0, iters=200, seed=0)
        # 独立に最良仮説の合意を数える(実装と同じ標本列)
        g = np.random.default_rng(0)
        best = 0
        for _ in range(200):
            idx = g.choice(13, 4, replace=False)
            H = mosaic._homography_dlt(p1[idx], p2[idx])
            if np.isfinite(H).all():
                with np.errstate(all="ignore"):
                    best = max(best, int((np.linalg.norm(mosaic._apply_h(H, p1) - p2, axis=1) < 2.0).sum()))
        assert r["num_inliers"] >= best, (seed, r["num_inliers"], best)
        n_cases += 1
    assert n_cases == 40
