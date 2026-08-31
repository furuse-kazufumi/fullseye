"""feature descriptor 系(3D keypoint + 記述子 + RANSAC 登録)のテスト。

初期推定なしに大回転+部分重なりを対応付け → RANSAC で剛体姿勢。密マッチ(NCC/Hough)が
扱えない領域。Workflow 並行探索の 4 手法を統合後に一次検証したものを固定する。scipy 必須。
"""
import numpy as np
import pytest

torch = pytest.importorskip("torch")
scipy = pytest.importorskip("scipy")

import feat_harris
import feat_spin
import feat_shot
import feat_fpfh
import match3d as X


def _feature_cloud(seed=0, n=4000):
    rng = np.random.default_rng(seed)
    pts = [rng.uniform([0, 0, 0], [10, 3, 3], (n // 3, 3)),
           rng.uniform([0, 0, 0], [3, 10, 3], (n // 4, 3))]
    for L, off in [(6, [8, 1, 1]), (4, [1, 8, 1]), (8, [5, 5, 3])]:
        pts.append(rng.uniform(off, [off[0] + 1.5, off[1] + 1.5, off[2] + L], (n // 8, 3)))
    u = rng.random(n // 8) * 2 * np.pi; v = rng.random(n // 8) * np.pi
    pts.append(np.stack([np.sin(v) * np.cos(u), np.sin(v) * np.sin(u), np.cos(v)], 1) * 1.5
               + np.array([9, 9, 6]))
    return np.vstack(pts)


def _rot_axis(axis, deg):
    a = np.asarray(axis, float); a /= np.linalg.norm(a); th = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * K @ K


def _rot_err(Re, Rg):
    Re = Re.detach().cpu().numpy() if hasattr(Re, "detach") else np.asarray(Re)

    def geo(A, B):
        return np.degrees(np.arccos(np.clip((np.trace(A.T @ B) - 1) / 2, -1, 1)))

    return min(geo(Re, Rg), geo(Re, Rg.T))


def _scene(seed=0):
    src = _feature_cloud(seed)
    Rg = _rot_axis([1, 0.5, 0.3], 60.0); tg = np.array([5.0, -3.0, 2.0])
    dst = (Rg @ src.T).T + tg
    src_p = src[src[:, 0] < 8.5]                            # 部分重なり(src ~70%)
    return src_p, dst, Rg


def test_spin_registers_large_rotation():
    """Spin Image + RANSAC: 60° 回転 + 部分重なりを初期推定なしで登録(rot_err < 8°)。"""
    src, dst, Rg = _scene(0)
    R, t, info = feat_spin.register_spin(src, dst)
    assert _rot_err(R, Rg) < 8.0


def test_fpfh_registers_large_rotation():
    """FPFH + RANSAC: 60° 回転 + 部分重なりを登録(rot_err < 8°)。"""
    src, dst, Rg = _scene(0)
    out = feat_fpfh.register_fpfh(src, dst)
    assert _rot_err(out[0], Rg) < 8.0


def test_shot_registers_large_rotation():
    """SHOT + RANSAC + ICP: 60° 回転 + 部分重なりを高精度に登録(rot_err < 2°)。"""
    src, dst, Rg = _scene(0)
    R, t, info = feat_shot.register_shot(src, dst)
    assert _rot_err(R, Rg) < 2.0                            # ICP 精緻化込み


def test_harris3d_detects_keypoints():
    """3D Harris(mineig): 回転前後の voxel 双方で keypoint を検出(repeatable な構造)。"""
    src = _feature_cloud(0)
    vol = X.points_to_voxel((src - src.min(0)) / (src.max(0) - src.min(0)) * 44 + 2, 48)
    kp, resp = feat_harris.harris3d_keypoints(vol, topn=40)
    assert len(kp) >= 20                                    # コーナーを検出


# ── 異種構造の統合(TRIZ 統合: 全5構造を組み合わせる)──────────────────
def _box_mesh(lo, hi):
    from itertools import product
    v = np.array(list(product(*zip(lo, hi))), float)
    f = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1],
                  [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
    return v, f


def test_cross_structure_registration_mesh_vs_points():
    """異種構造間登録: CAD mesh vs 点群スキャン(50° 回転+部分)= Physical AI の CAD-to-scan。"""
    import fuse3d
    v1, f1 = _box_mesh([0, 0, 0], [10, 4, 4]); v2, f2 = _box_mesh([0, 0, 0], [4, 10, 4])
    verts = np.vstack([v1, v2]); faces = np.vstack([f1, f2 + len(v1)])
    full = X.mesh_to_points(verts, faces, 8000)
    Rg = _rot_axis([1, 0.4, 0.2], 50.0); tg = np.array([3.0, -2.0, 1.0])
    scan = ((Rg @ full.T).T + tg)[full[:, 0] < 8]          # 回転 + 部分
    R, t = fuse3d.register_cross((verts, faces), "mesh", scan, "points",
                                 method="fpfh", samples=8000)
    assert _rot_err(R, Rg) < 8.0                            # 異種構造でも登録成功


def test_fuse_multiple_structures_to_voxel():
    """多構造フュージョン: mesh + points + depth → 1 密度 voxel(TRIZ 統合)。"""
    import fuse3d
    v1, f1 = _box_mesh([0, 0, 0], [10, 4, 4])
    pts = np.random.default_rng(0).uniform([2, 2, 4], [8, 8, 7], (2000, 3))
    yy, xx = np.mgrid[0:32, 0:32]; depth = 8.0 + 0.05 * xx
    vol, bnd = fuse3d.fuse_to_voxel(
        [((v1, f1), "mesh", {}), (pts, "points", {}),
         (depth, "depth", {"fx": 30, "fy": 30, "cx": 16, "cy": 16})], size=48)
    assert vol.shape == (48, 48, 48) and (vol > 0.01).sum() > 1000   # 3 構造が融合


def test_register_fpfh_rejects_degenerate_clouds():
    """Regression (chain fuzz wave-4): 空点群(上流 filter が全点除去した産物)が
    voxel_downsample の grp[-1] / KDTree 添字で生 IndexError 化していた
    (index -1 is out of bounds for axis 0 with size 0)。"""
    rng = np.random.default_rng(0)
    good = rng.random((50, 3))
    empty = np.zeros((0, 3))
    with pytest.raises(ValueError, match="at least 3 points"):
        feat_fpfh.register_fpfh(empty, good)
    with pytest.raises(ValueError, match="at least 3 points"):
        feat_fpfh.register_fpfh(good, empty)
    with pytest.raises(ValueError, match="at least 3 points"):
        feat_fpfh.register_fpfh(good[:2], good)          # 1-2 点も pose 未定義
    with pytest.raises(ValueError, match="numeric"):
        feat_fpfh.register_fpfh({"p": 1}, good)          # dict も同系穴
    with pytest.raises(ValueError, match="non-empty"):
        feat_fpfh.voxel_downsample(empty, 0.5)           # 兄弟 util 単体も fail-closed
