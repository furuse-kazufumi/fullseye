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
    for N, seed in ((32, 0), (40, 1)):
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
