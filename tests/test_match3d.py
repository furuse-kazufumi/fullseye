"""match3d(3D マッチング・マトリクス)テスト。data 構造 × 2D 手法 × 変換。

位相相関(FFT)/ 形状ベース(勾配方向=輪郭マッチング、コントラスト不変)/ splat 変換 /
点群 NCC。GPU 速度は docs/BENCH_VS_OPENCV 系で別途(phase 18-28× / shape 68-89× vs CPU)。
device 非依存。torch 不在なら skip。
"""
import numpy as np
import pytest

import match3d as X

HAS = X._HAS_TORCH
skip = pytest.mark.skipif(not HAS, reason="torch 不在")


@skip
def test_phase_corr_recovers_shift():
    a = np.random.default_rng(0).random((32, 32, 32))
    s = (5, -3, 7)
    b = np.roll(a, s, axis=(0, 1, 2))
    sh = X.match_phase_3d(a, b, "cpu")
    assert tuple(-x for x in sh) == s or sh == s          # 符号規約差は許容


@skip
def test_shape_based_contrast_invariant():
    """勾配方向マッチングは弱コントラスト(0.4×)でも定位する = 強度不変。"""
    z, y, x = np.ogrid[-4:5, -4:5, -4:5]
    T = np.exp(-(x * x + y * y + z * z) / 8.0)
    rng = np.random.default_rng(1)
    scene = rng.random((48, 48, 48)) * 0.3
    d, h, w = 30, 12, 22
    scene[d - 4:d + 5, h - 4:h + 5, w - 4:w + 5] += 0.4 * T
    r = X.match_shape_3d(np.clip(scene, 0, 1), T, "cpu", mc=0.02)
    assert abs(r[1] - d) + abs(r[2] - h) + abs(r[3] - w) < 1.5


@skip
def test_gaussians_to_voxel_peaks_at_means():
    means = np.array([[0.3, 0.5, 0.7]])
    vol = X.gaussians_to_voxel(means, [0.03], [1.0], 32,
                               (np.zeros(3), np.ones(3)), "cpu")
    pk = np.unravel_index(np.argmax(vol), vol.shape)
    exp = tuple(int(m * 31) for m in means[0])
    assert sum(abs(p - e) for p, e in zip(pk, exp)) <= 2


@skip
def test_points_to_voxel_and_mip():
    rng = np.random.default_rng(2)
    pts = rng.random((500, 3))
    vol = X.points_to_voxel(pts, 24, (np.zeros(3), np.ones(3)), "cpu")
    assert vol.shape == (24, 24, 24) and vol.sum() > 0
    mips = X.voxel_to_mips(vol)
    assert len(mips) == 3 and all(m.shape == (24, 24) for m in mips)


@skip
def test_pca_recovers_rotation():
    """異方性雲を既知の回転+並進 → PCA 主軸整列で復元(残差≈0)。回転を扱う列。"""
    rng = np.random.default_rng(0)
    model = rng.normal(0, 1, (800, 3)) * np.array([3.0, 1.0, 0.4])
    th, th2 = 0.6, 0.3
    Rz = np.array([[np.cos(th), -np.sin(th), 0], [np.sin(th), np.cos(th), 0], [0, 0, 1]])
    Ry = np.array([[np.cos(th2), 0, np.sin(th2)], [0, 1, 0], [-np.sin(th2), 0, np.cos(th2)]])
    Rt = Rz @ Ry
    scene = (Rt @ model.T).T + np.array([2.0, 1.0, -1.0])
    R, t = X.match_pca(scene, model)
    resid = np.mean(np.linalg.norm(scene - ((R @ model.T).T + t), axis=1))
    assert resid < 0.05


@skip
def test_mip_2d_locates():
    """MIP 投影 → 2D NCC で 3D 位置を冗長推定(変換=直交 MIP、次元削減)。"""
    z, y, x = np.ogrid[-4:5, -4:5, -4:5]
    T = np.exp(-(x * x + y * y + z * z) / 8.0)
    N = 48
    rng = np.random.default_rng(1)
    scene = rng.random((N, N, N)) * 0.2
    d, h, w = 30, 14, 20
    scene[d - 4:d + 5, h - 4:h + 5, w - 4:w + 5] += T
    mvol = np.zeros((N, N, N))
    mvol[N // 2 - 4:N // 2 + 5, N // 2 - 4:N // 2 + 5, N // 2 - 4:N // 2 + 5] = T
    pos = X.match_mip_2d(np.clip(scene, 0, 1), mvol, "cpu")
    assert abs(pos[0] - d) + abs(pos[1] - h) + abs(pos[2] - w) < 2


@skip
def test_chamfer_robust_to_occlusion():
    """chamfer/距離場: 球殻テンプレで定位。テンプレ半分遮蔽でも定位(部分・遮蔽頑健)。"""
    z, y, x = np.ogrid[-6:7, -6:7, -6:7]
    rr = np.sqrt(x * x + y * y + z * z)
    T = (np.abs(rr - 4) < 1.2).astype(float)
    N = 56
    rng = np.random.default_rng(0)
    scene = rng.random((N, N, N)) * 0.15
    d, h, w = 34, 18, 26
    scene[d - 6:d + 7, h - 6:h + 7, w - 6:w + 7] += T
    scene = np.clip(scene, 0, 1)
    r = X.match_chamfer_3d(scene, T, "cpu", thr=0.3)
    assert abs(r[1] - d) + abs(r[2] - h) + abs(r[3] - w) <= 1
    Tp = T.copy(); Tp[:, :, 7:] = 0                       # 半分遮蔽
    r2 = X.match_chamfer_3d(scene, Tp, "cpu", thr=0.3)
    assert abs(r2[1] - d) + abs(r2[2] - h) + abs(r2[3] - w) <= 2


def _box(center, sz):
    c = np.array(center, float); s = np.array(sz, float) / 2
    v = np.array([[cx, cy, cz]
                  for cx in (c[0] - s[0], c[0] + s[0])
                  for cy in (c[1] - s[1], c[1] + s[1])
                  for cz in (c[2] - s[2], c[2] + s[2])])
    f = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1],
                  [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
    return v, f


@skip
def test_mesh_to_voxel_matches_translation():
    """mesh 行を接続: box を voxelize → 平行移動を phase-corr で復元。"""
    b = (np.zeros(3), np.ones(3))
    v1, f = _box([0.4, 0.5, 0.5], [0.3, 0.15, 0.15])
    v2, _ = _box([0.5, 0.55, 0.45], [0.3, 0.15, 0.15])
    vol1 = X.mesh_to_voxel(v1, f, 40, b)
    vol2 = X.mesh_to_voxel(v2, f, 40, b)
    sh = tuple(-x for x in X.match_phase_3d(vol1, vol2, "cpu"))
    true = tuple(int(round((c2 - c1) * 39))
                 for c1, c2 in zip([0.4, 0.5, 0.5], [0.5, 0.55, 0.45]))
    assert sum(abs(a - t) for a, t in zip(sh, true)) <= 2


@skip
def test_depth_to_points_backprojection():
    """depth 行を接続: 傾き平面の逆投影が妥当な point cloud を出す。"""
    H = W = 64
    yy, xx = np.mgrid[0:H, 0:W]
    depth = 0.5 + 0.3 * (xx / W)
    pts = X.depth_to_points(depth, fx=50, fy=50, cx=W / 2, cy=H / 2)
    assert len(pts) == H * W
    assert 0.49 < pts[:, 2].min() < 0.51 and 0.79 < pts[:, 2].max() < 0.81


@skip
def test_points_ncc_locates_cluster():
    """構造ある点群: 疎な背景 + 既知位置の密クラスタ。model=クラスタ点で定位。"""
    rng = np.random.default_rng(3)
    bg = rng.random((1500, 3))
    c = np.array([0.65, 0.35, 0.55])
    cluster = c + rng.normal(0, 0.03, (400, 3))
    scene = np.vstack([bg, cluster])
    res = X.match_points_ncc(scene, cluster, 32, (np.zeros(3), np.ones(3)), "cpu")
    # 復元位置(voxel)を [0,1] へ戻して真のクラスタ中心と比較
    pos01 = np.array(res[1:]) / 31.0
    assert np.linalg.norm(pos01 - c) < 0.12


def _has_scipy():
    try:
        import scipy  # noqa: F401
        return True
    except Exception:
        return False


need_scipy = pytest.mark.skipif(not _has_scipy(), reason="scipy 不在")


def _blob3(N, seed):
    rng = np.random.default_rng(seed)
    v = np.zeros((N, N, N), np.float32)
    zz, yy, xx = np.mgrid[0:N, 0:N, 0:N]
    for _ in range(5):
        c = rng.uniform(0.3, 0.7, 3) * N
        r = rng.uniform(3, 7, 3)
        v += np.exp(-(((zz - c[0]) / r[0]) ** 2 + ((yy - c[1]) / r[1]) ** 2
                      + ((xx - c[2]) / r[2]) ** 2))
    return v


@skip
@need_scipy
def test_logpolar_recovers_z_rotation():
    """Fourier-Mellin(log-polar × 位相相関)が z 軸回転を coarse 復元。回転+スケール列。"""
    from scipy import ndimage
    N = 48
    errs = []
    for ang in (10, 20, -15, -25):
        base = _blob3(N, 7)
        rot = ndimage.rotate(base, ang, axes=(1, 2), reshape=False, order=1)
        rec, _ = X.match_logpolar_z(base, rot, "cpu")
        errs.append(abs(rec - ang))
    assert max(errs) < 7.0                                # coarse 推定器(±45/90°別名は避ける)


@skip
@need_scipy
def test_logpolar_recovers_scale():
    """等方スケールを log-polar の rho シフトから復元(~10% 過小の中央ローブ偏りは許容)。"""
    from scipy import ndimage
    N = 48
    base = _blob3(N, 3)
    z = ndimage.zoom(base, 1.3, order=1)
    out = np.zeros((N, N, N), np.float32)
    o = (z.shape[0] - N) // 2
    out = z[o:o + N, o:o + N, o:o + N]
    _, s = X.match_logpolar_z(base, out, "cpu")
    assert abs(s - 1.3) / 1.3 < 0.15                      # coarse スケール


@skip
@need_scipy
def test_edt_jfa_exact_vs_scipy():
    """jump-flooding EDT が scipy EDT と厳密一致(chamfer 全 GPU 化の土台)。"""
    from scipy import ndimage
    for N, seed in ((32, 0), (40, 1), (72, 2)):        # 72>64: JFA+2 が大 N でも厳密
        rng = np.random.default_rng(seed)
        se = rng.random((N, N, N)) < 0.01
        se[0, 0, 0] = True
        dj = X.edt_jfa(se, "cpu").cpu().numpy()
        ds = ndimage.distance_transform_edt(~se)
        assert np.abs(dj - ds).max() < 1e-4


@skip
@need_scipy
def test_chamfer_jfa_matches_scipy_localization():
    """chamfer の edt='jfa'(全 GPU)が edt='scipy' と同一定位。"""
    z, y, x = np.ogrid[-6:7, -6:7, -6:7]
    rr = np.sqrt(x * x + y * y + z * z)
    T = (np.abs(rr - 4) < 1.2).astype(float)
    N = 56
    rng = np.random.default_rng(0)
    scene = rng.random((N, N, N)) * 0.15
    d, h, w = 34, 18, 26
    scene[d - 6:d + 7, h - 6:h + 7, w - 6:w + 7] += T
    scene = np.clip(scene, 0, 1)
    r1 = X.match_chamfer_3d(scene, T, "cpu", edt="scipy")
    r2 = X.match_chamfer_3d(scene, T, "cpu", edt="jfa")
    assert abs(r1[1] - r2[1]) + abs(r1[2] - r2[2]) + abs(r1[3] - r2[3]) == 0
    assert abs(r2[1] - d) + abs(r2[2] - h) + abs(r2[3] - w) <= 1


def _shell_template(rad=3.5, half=1.0, r=5):
    z, y, x = np.ogrid[-r:r + 1, -r:r + 1, -r:r + 1]
    rr = np.sqrt(x * x + y * y + z * z)
    return (np.abs(rr - rad) < half).astype(float)


@skip
def test_hough_multi_instance():
    """generalized Hough 3D: 投票 accumulator の NMS で **複数インスタンス**を検出。"""
    T = _shell_template()
    N = 64
    rng = np.random.default_rng(0)
    scene = rng.random((N, N, N)) * 0.1
    locs = [(20, 18, 22), (44, 40, 38)]
    for (d, h, w) in locs:
        scene[d - 5:d + 6, h - 5:h + 6, w - 5:w + 6] += T
    scene = np.clip(scene, 0, 1)
    ps = X.match_hough_3d(scene, T, "cpu", topk=2, nms=6)
    found = sum(any(abs(p[1] - d) + abs(p[2] - h) + abs(p[3] - w) <= 2 for p in ps)
                for (d, h, w) in locs)
    assert found == 2                                    # 両インスタンス検出


@skip
def test_hough_robust_to_occlusion():
    """Hough 投票は欠けたエッジがピークを下げるだけ = 半分遮蔽でも定位(頑健)。"""
    T = _shell_template()
    N = 64
    rng = np.random.default_rng(1)
    scene = rng.random((N, N, N)) * 0.1
    d, h, w = 30, 28, 34
    scene[d - 5:d + 6, h - 5:h + 6, w - 5:w + 6] += T
    scene = np.clip(scene, 0, 1)
    Tocc = T.copy(); Tocc[:, :, 6:] = 0                  # 半分遮蔽
    p = X.match_hough_3d(scene, Tocc, "cpu", topk=1)
    assert abs(p[0][1] - d) + abs(p[0][2] - h) + abs(p[0][3] - w) <= 2


@skip
def test_curvature_shape_index_sphere_vs_cylinder():
    """線→面リフト: shape index が球=cap(≈+1)・円柱=ridge(≈+0.5)を正しく分類。"""
    N = 48; c = N // 2
    zz, yy, xx = np.mgrid[0:N, 0:N, 0:N]
    r = np.sqrt((zz - c) ** 2 + (yy - c) ** 2 + (xx - c) ** 2)
    sphere = 1 / (1 + np.exp((r - 12) / 1.5))
    S, _, _, _ = X.curvature_maps(sphere, "cpu", mc=0.01)
    Ss = S.cpu().numpy()[np.abs(r - 12) < 1.5]
    assert abs(Ss.mean() - 1.0) < 0.1                    # 球殻 = cap
    rc = np.sqrt((yy - c) ** 2 + (xx - c) ** 2)
    cyl = 1 / (1 + np.exp((rc - 10) / 1.5))
    S2, _, _, _ = X.curvature_maps(cyl, "cpu", mc=0.01)
    Sc = S2.cpu().numpy()[(np.abs(rc - 10) < 1.5) & (np.abs(zz - c) < 12)]
    assert abs(Sc.mean() - 0.5) < 0.1                    # 円柱 = ridge


@skip
def test_curvature_matches_by_shape_not_intensity():
    """曲率マッチングは強度でなく形状で一致 = 同強度の球/円柱から球を選ぶ。"""
    ct = 8
    zt, yt, xt = np.mgrid[0:2 * ct + 1, 0:2 * ct + 1, 0:2 * ct + 1]
    rt = np.sqrt((zt - ct) ** 2 + (yt - ct) ** 2 + (xt - ct) ** 2)
    Tsph = 1 / (1 + np.exp((rt - 5) / 1.2))
    Ns = 56
    sc = np.zeros((Ns, Ns, Ns))
    Z, Y, Xx = np.mgrid[0:Ns, 0:Ns, 0:Ns]
    ra = np.sqrt((Z - 16) ** 2 + (Y - 16) ** 2 + (Xx - 16) ** 2)
    sc += 1 / (1 + np.exp((ra - 5) / 1.2))               # 球 A
    rcB = np.sqrt((Y - 40) ** 2 + (Xx - 40) ** 2)
    sc += 1 / (1 + np.exp((rcB - 5) / 1.2)) * (np.abs(Z - 40) < 6)   # 円柱 B(同強度)
    r = X.match_curvature_3d(np.clip(sc, 0, 1), Tsph, "cpu", mc=0.01)
    assert abs(r[1] - 16) + abs(r[2] - 16) + abs(r[3] - 16) <= 3     # 球を選ぶ


@skip
def test_hough_plane_detects_normal_and_offset():
    """パラメトリック Hough: テンプレなしで平面 (法線 n, 距離 d) を検出。"""
    N = 48
    Z, Y, Xx = np.mgrid[0:N, 0:N, 0:N]
    ntrue = np.array([0.3, 0.5, 0.8]); ntrue /= np.linalg.norm(ntrue)
    dtrue = 25.0
    vol = 1 / (1 + np.exp((ntrue[0] * Z + ntrue[1] * Y + ntrue[2] * Xx - dtrue) / 1.0))
    nrm, dval, inl, tot = X.hough_plane_3d(vol, "cpu")
    assert abs(abs(np.dot(nrm, ntrue)) - 1.0) < 0.02     # 法線方向を復元
    assert abs(dval - dtrue) < 1.5                        # 距離(isosurface 位置)
    assert inl > 0.7 * tot                                # 大半が inlier


@skip
def test_hough_sphere_detects_center_and_radius():
    """パラメトリック Hough: テンプレなしで球 (中心 c, 半径 r) を検出。"""
    N = 48
    Z, Y, Xx = np.mgrid[0:N, 0:N, 0:N]
    ctrue = (24, 22, 26); rtrue = 9
    r = np.sqrt((Z - ctrue[0]) ** 2 + (Y - ctrue[1]) ** 2 + (Xx - ctrue[2]) ** 2)
    ball = (r < rtrue).astype(float)
    res = X.hough_sphere_3d(ball, "cpu", radii=range(5, 14))
    votes, rad, center = res
    assert abs(center[0] - ctrue[0]) + abs(center[1] - ctrue[1]) + abs(center[2] - ctrue[2]) <= 1
    assert abs(rad - rtrue) < 1.5                         # 半径(isosurface 位置)


@skip
@need_scipy
def test_sh_descriptor_rotation_invariant():
    """線→面リフト: 球面調和記述子が 3D 回転で不変・別形状は識別(rod vs sphere)。"""
    from scipy import ndimage
    N = 48; c = N // 2
    Z, Y, Xx = np.mgrid[0:N, 0:N, 0:N]
    rod = np.exp(-(((Z - c) / 12.0) ** 2 + ((Y - c) / 3.0) ** 2 + ((Xx - c) / 3.0) ** 2))
    sph = np.exp(-(((Z - c) / 7.0) ** 2 + ((Y - c) / 7.0) ** 2 + ((Xx - c) / 7.0) ** 2))
    rod_r = ndimage.rotate(rod, 40, axes=(1, 2), reshape=False, order=1)
    rod_r = ndimage.rotate(rod_r, 25, axes=(0, 2), reshape=False, order=1)
    inv = X.match_sh_descriptor(rod, rod_r)
    diff = X.match_sh_descriptor(rod, sph)
    assert inv > 0.98                                     # 回転不変
    assert inv - diff > 0.1                               # 別形状を識別


# ── 反復精緻化(粗推定 → Newton/GN/LM/ICP で高精度収束)──────────────────
def _blob4(N, seed):
    rng = np.random.default_rng(seed)
    v = np.zeros((N, N, N), np.float32)
    zz, yy, xx = np.mgrid[0:N, 0:N, 0:N]
    for _ in range(4):
        c = rng.uniform(0.35, 0.65, 3) * N; r = rng.uniform(4, 8, 3)
        v += np.exp(-(((zz - c[0]) / r[0]) ** 2 + ((yy - c[1]) / r[1]) ** 2
                      + ((xx - c[2]) / r[2]) ** 2))
    return v


@skip
def test_refine_peak_newton_subvoxel():
    """3D Newton サブボクセルピーク: 相互曲率のある異方性山を <0.05 voxel で回復。"""
    N = 40; mu = np.array([15.3, 20.7, 9.4])
    zz, yy, xx = np.mgrid[0:N, 0:N, 0:N]
    dz, dy, dx = zz - mu[0], yy - mu[1], xx - mu[2]
    q = (1.0 * dz * dz + 1.2 * dy * dy + 0.8 * dx * dx
         + 2 * 0.3 * dz * dy + 2 * 0.15 * dz * dx + 2 * 0.2 * dy * dx)
    score = np.exp(-q / 12.0)
    idx = np.unravel_index(np.argmax(score), score.shape)
    r = X.refine_peak_newton(score, idx)
    assert np.linalg.norm(r[1:] - mu) < 0.05


@skip
@need_scipy
def test_refine_translation_lk_subvoxel():
    """逆合成 Lucas-Kanade 並進: 既知サブボクセルずれを <0.1 voxel で回復。"""
    from scipy import ndimage
    base = _blob4(48, 7); off = np.array([0.37, -0.62, 0.28])
    shifted = ndimage.shift(base, off, order=3, mode="nearest")
    T = base[16:32, 16:32, 16:32]
    r = X.refine_translation_lk(shifted, T, [16, 16, 16])
    assert np.linalg.norm(r - (np.array([16, 16, 16]) + off)) < 0.1


@skip
@need_scipy
def test_refine_lm_translation_and_scale():
    """Levenberg-Marquardt: 並進を <0.05 voxel、かつ等方スケールを回復(規約=中心(Td-1)/2)。"""
    from scipy import ndimage
    base = _blob4(48, 7); off = np.array([0.37, -0.62, 0.28])
    shifted = ndimage.shift(base, off, order=3, mode="nearest")
    T = base[16:32, 16:32, 16:32]
    cen = np.array([16, 16, 16]) + (16 - 1) / 2.0 + off
    r = X.refine_lm(shifted, T, [23, 23, 23], scale=True)
    assert np.linalg.norm(np.array(r["pos"]) - cen) < 0.05
    big = ndimage.zoom(base, 1.05, order=3)
    o = (big.shape[0] - 48) // 2; big = big[o:o + 48, o:o + 48, o:o + 48]
    r2 = X.refine_lm(big, base[16:32, 16:32, 16:32], [23, 23, 23], scale=True)
    assert abs(r2["scale"] - 1.05) < 0.03                # スケール回復(COM は原理的に不可)


@skip
@need_scipy
def test_refine_rotation_z_gauss_newton():
    """Gauss-Newton z 軸回転: Fourier-Mellin の粗い初期(15°)を真値 17.3° へ <0.3° 収束。"""
    from scipy import ndimage
    base = _blob4(48, 3); ang = 17.3
    rot = ndimage.rotate(base, ang, axes=(1, 2), reshape=False, order=3)
    ra, _ = X.refine_rotation_z(rot, base, init_angle_deg=15.0)
    assert abs(ra - ang) < 0.3


@skip
@need_scipy
def test_icp_point2point_recovers_pose():
    """ICP 点-点(Kabsch/SVD): 既知 R,t で変換した点群を RMSE<1e-2 に精緻化。"""
    rng = np.random.default_rng(1)
    src = rng.random((800, 3)) * 20
    th = 0.15
    Rz = np.array([[np.cos(th), -np.sin(th), 0], [np.sin(th), np.cos(th), 0], [0, 0, 1]])
    dst = (Rz @ src.T).T + np.array([1.5, -2.0, 0.8])
    _, _, info = X.icp_point2point_3d(src, dst, iters=50)
    assert info["rmse"] < 1e-2


@skip
def test_icp_point2plane_recovers_pose():
    """ICP 点-面(Gauss-Newton): 表面点群を法線利用で RMSE<1e-2 に高速収束。"""
    rng = np.random.default_rng(2)
    u = rng.random(1500) * 2 * np.pi; v = rng.random(1500) * np.pi
    ctr = np.array([10.0, 10.0, 10.0])
    sph = np.stack([np.sin(v) * np.cos(u), np.sin(v) * np.sin(u), np.cos(v)], 1) * 8 + ctr
    nrm = sph - ctr; nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    th = 0.1
    Rz = np.array([[np.cos(th), -np.sin(th), 0], [np.sin(th), np.cos(th), 0], [0, 0, 1]])
    src = (Rz.T @ (sph - ctr).T).T + ctr - np.array([0.3, 0.2, 0.0])
    _, _, _, rmse, _ = X.icp_point2plane(src, sph, nrm, iters=30)
    assert rmse < 1e-2


@skip
@need_scipy
def test_scene_flow_recovers_motion():
    """scene flow(3D optical flow): 一様並進を密運動場で回復、拡大場で発散を検出。"""
    from scipy import ndimage
    N = 48
    rng = np.random.default_rng(0)
    base = np.zeros((N, N, N), np.float32)
    zz, yy, xx = np.mgrid[0:N, 0:N, 0:N]
    for _ in range(5):
        c = rng.uniform(0.3, 0.7, 3) * N; r = rng.uniform(4, 7, 3)
        base += np.exp(-(((zz - c[0]) / r[0]) ** 2 + ((yy - c[1]) / r[1]) ** 2
                         + ((xx - c[2]) / r[2]) ** 2))
    true = np.array([1.5, -2.0, 1.0])
    moved = ndimage.shift(base, true, order=3, mode="nearest")
    flow = X.scene_flow_lk(base, moved, "cpu")
    ctr = flow[:, 12:36, 12:36, 12:36].reshape(3, -1).mean(1)
    assert np.linalg.norm(ctr - true) < 0.2                # 密運動場で並進回復
    big = ndimage.zoom(base, 1.08, order=3)
    o = (big.shape[0] - N) // 2; big = big[o:o + N, o:o + N, o:o + N]
    flow2 = X.scene_flow_lk(base, big, "cpu")
    c = N / 2
    radial = flow2[0] * (zz - c) + flow2[1] * (yy - c) + flow2[2] * (xx - c)
    m = np.abs(zz - c) + np.abs(yy - c) + np.abs(xx - c) > 6
    assert radial[m].mean() > 0                            # 拡大=外向き発散


# ── データ形式の変換 + 3D モルフォロジー ────────────────────────────────
@skip
def test_signed_distance_field():
    """occupancy → SDF: 中心が最も負・表面で 0 交差・外側が正。"""
    N = 48; c = N // 2
    zz, yy, xx = np.mgrid[0:N, 0:N, 0:N]
    ball = (np.sqrt((zz - c) ** 2 + (yy - c) ** 2 + (xx - c) ** 2) < 12).astype(float)
    sdf = X.signed_distance_field(ball, "cpu")
    assert sdf[c, c, c] < -8                              # 中心=深い内側
    assert abs(sdf[c, c, c + 12]) < 2                     # 表面 ~0
    assert sdf[0, 0, 0] > 5                               # 端=外側
    assert np.array_equal(X.sdf_to_occupancy(sdf, 0.0), ball)   # 往復


@skip
@need_scipy
def test_estimate_point_normals_sphere():
    """点群法線: 球面の法線が放射方向に一致(FPFH/ICP-p2plane の前段)。"""
    rng = np.random.default_rng(1)
    u = rng.random(2000) * 2 * np.pi; v = rng.random(2000) * np.pi
    sph = np.stack([np.sin(v) * np.cos(u), np.sin(v) * np.sin(u), np.cos(v)], 1) * 8
    nrm = X.estimate_point_normals(sph, k=20, viewpoint=np.array([0, 0, 100.0]))
    radial = sph / np.linalg.norm(sph, axis=1, keepdims=True)
    assert np.abs(np.einsum("ni,ni->n", nrm, radial)).mean() > 0.95


@skip
def test_morph_gradient_extracts_boundary():
    """3D モルフォロジー勾配 = dilation-erosion が境界のみ抽出(内部は零)。"""
    N = 40; c = N // 2
    zz, yy, xx = np.mgrid[0:N, 0:N, 0:N]
    r = np.sqrt((zz - c) ** 2 + (yy - c) ** 2 + (xx - c) ** 2)
    ball = (r < 12).astype(float)
    grad = X.morph_gradient3d(ball, 1, "cpu")
    assert (grad > 0.5).sum() > 100                       # 境界に応答
    assert np.allclose(grad[r < 10], 0)                   # 内部は零


@skip
def test_morph_tophat_isolates_small_feature():
    """3D white top-hat が SE より小さい明構造を抽出、大構造内部は零。"""
    N = 40; c = N // 2
    zz, yy, xx = np.mgrid[0:N, 0:N, 0:N]
    big = (np.sqrt((zz - c) ** 2 + (yy - c) ** 2 + (xx - c) ** 2) < 12).astype(np.float32)
    big[8:11, 8:11, 8:11] += 1.0
    th = X.morph_tophat3d(big, 3, "cpu")
    assert th[9, 9, 9] > 0.5                              # 小突起を抽出
    assert abs(th[c, c, c]) < 0.1                         # 大球内部は零


# ── 幾何プリミティブ / メトロロジー(2点→線・3点→面/角度)──────────────
def test_geometry_angles_and_distances():
    """角度(3点/面/線-面)と距離(点-面/ねじれ線間)が閉形式で厳密。"""
    assert abs(X.angle_3points([1, 0, 0], [0, 0, 0], [0, 1, 0]) - 90) < 1e-6
    assert abs(X.angle_between_planes([0, 0, 1], [0, 1, 0]) - 90) < 1e-6
    assert abs(X.angle_line_plane([0, 0, 1], [0, 0, 1]) - 90) < 1e-6
    assert abs(X.distance_point_plane([1, 2, 3], [0, 0, 0], [0, 0, 1]) - 3) < 1e-6
    assert abs(X.distance_line_line([0, 0, 0], [1, 0, 0], [0, 0, 5], [0, 1, 0]) - 5) < 1e-6


def test_geometry_intersections():
    """交差: 直線∩平面 → 点、平面∩平面 → 直線。"""
    p = X.intersect_line_plane([0, 0, -5], [0, 0, 1], [0, 0, 0], [0, 0, 1])
    assert np.allclose(p, [0, 0, 0])
    pt, d = X.intersect_planes([0, 0, 0], [0, 0, 1], [0, 0, 0], [0, 1, 0])
    assert abs(abs(d[0]) - 1) < 1e-6 and abs(d[1]) < 1e-6 and abs(d[2]) < 1e-6   # ±x 方向


def test_geometry_fitting():
    """フィッティング: 球(中心/半径)・平面(法線/残差)・円を最小二乗で厳密回復。"""
    rng = np.random.default_rng(0)
    u = rng.random(500) * 2 * np.pi; v = rng.random(500) * np.pi
    sp = np.stack([np.sin(v) * np.cos(u), np.sin(v) * np.sin(u), np.cos(v)], 1) * 7 + np.array([3, 4, 5])
    c, r = X.fit_sphere_3d(sp)
    assert np.linalg.norm(c - [3, 4, 5]) < 1e-6 and abs(r - 7) < 1e-6
    P = rng.random((300, 2))
    pts = np.stack([P[:, 0], P[:, 1], 0.3 * P[:, 0] + 0.2 * P[:, 1] + 1], 1)
    _, n, resid = X.fit_plane_3d(pts)
    assert resid < 1e-6 and abs(abs(n @ _unit([0.3, 0.2, -1])) - 1) < 1e-6


def _unit(v):
    v = np.asarray(v, float); return v / np.linalg.norm(v)
