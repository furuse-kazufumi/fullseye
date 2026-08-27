"""segment3d(点群セグメンテーション)テスト — 全て ground-truth 数値検証。

GT 方針(note_15 の3失敗モードを踏まない):
- (A) スケール相対: euclidean_cluster を scale 1x と 100x で走らせラベル一致を確認。
- (B) 縮退/不正入力は fail-closed(ValueError)。空入力は shape (0,)。
- (C) GT は独立生成(Fibonacci 球の既知点数・格子面の既知点数)+ 判別ケース
      (閾値を変えると結果が変わる=実装の再導出でない)。

各セグメントの「点数・個数」を既知値と厳密照合する(見た目でない)。
"""
import numpy as np
import pytest

import segment3d as S


# ── 決定論的ジオメトリ生成器(GT は独立に既知)──────────────────────────────
def fib_sphere(n: int, R: float, center) -> np.ndarray:
    """Fibonacci 球面: ちょうど n 点、半径 R、中心 center。ほぼ一様間隔で決定論的。"""
    i = np.arange(n, dtype=np.float64)
    phi = np.arccos(1.0 - 2.0 * (i + 0.5) / n)          # 極角(Archimedes 一様)
    theta = np.pi * (1.0 + np.sqrt(5.0)) * i            # 黄金角
    xyz = np.stack([np.sin(phi) * np.cos(theta),
                    np.sin(phi) * np.sin(theta),
                    np.cos(phi)], axis=1)
    return np.asarray(center, float) + R * xyz


def grid_plane(u_vals, v_vals, fixed_axis: int, fixed_val: float) -> np.ndarray:
    """軸平行な平面格子を生成。fixed_axis を fixed_val に固定し他2軸を格子化。"""
    U, V = np.meshgrid(u_vals, v_vals, indexing="ij")
    pts = np.zeros((U.size, 3))
    free = [a for a in range(3) if a != fixed_axis]
    pts[:, free[0]] = U.ravel()
    pts[:, free[1]] = V.ravel()
    pts[:, fixed_axis] = fixed_val
    return pts


# ═══════════════════════════════════════════════════════════════════════════
# 1. euclidean_cluster: 離れた2球 → 2クラスタ、各点数 = 球の点数
# ═══════════════════════════════════════════════════════════════════════════
def test_euclidean_two_spheres_counts():
    n1, n2 = 400, 250
    A = fib_sphere(n1, 0.5, (0, 0, 0))
    B = fib_sphere(n2, 0.5, (5, 0, 0))          # 表面間 gap = 5 - 1 = 4 >> tol
    P = np.vstack([A, B])

    labels = S.euclidean_cluster(P, tol=0.2, min_size=10)

    assert labels.shape == (n1 + n2,)
    uniq = np.unique(labels)
    assert set(uniq.tolist()) == {0, 1}          # ちょうど2クラスタ、ノイズ無し
    sizes = np.bincount(labels[labels >= 0])
    # サイズ降順ラベリング: label0 = 大きい球(400)、label1 = 小さい球(250)
    assert sizes.tolist() == [n1, n2]
    # 幾何的正当性: label0 の点は全て球A(x<2.5)側
    assert np.all(P[labels == 0][:, 0] < 2.5)
    assert np.all(P[labels == 1][:, 0] > 2.5)


def test_euclidean_large_tol_merges_to_one():
    """判別ケース: tol を gap より大きくすると2球は1クラスタに融合(実装が距離で判別)。"""
    A = fib_sphere(300, 0.5, (0, 0, 0))
    B = fib_sphere(300, 0.5, (5, 0, 0))
    P = np.vstack([A, B])
    labels = S.euclidean_cluster(P, tol=6.0, min_size=10)   # 6.0 > gap 4
    assert set(np.unique(labels).tolist()) == {0}
    assert int((labels == 0).sum()) == 600


def test_euclidean_min_size_marks_noise():
    """判別ケース: min_size 未満の孤立塊は -1(ノイズ)。"""
    A = fib_sphere(300, 0.5, (0, 0, 0))
    B = fib_sphere(200, 0.5, (5, 0, 0))
    strays = np.array([[20.0, 0, 0], [22.0, 0, 0], [24.0, 0, 0]])  # 相互 2 > tol, 孤立
    P = np.vstack([A, B, strays])
    labels = S.euclidean_cluster(P, tol=0.2, min_size=10)
    assert int((labels == -1).sum()) == 3        # 3 孤立点は全てノイズ
    assert set(np.unique(labels[labels >= 0]).tolist()) == {0, 1}
    assert np.bincount(labels[labels >= 0]).tolist() == [300, 200]


def test_euclidean_scale_invariance():
    """note_15(A): 距離閾値はスケール相対。1x と 100x でラベルは完全一致。"""
    A = fib_sphere(300, 0.5, (0, 0, 0))
    B = fib_sphere(250, 0.5, (5, 0, 0))
    P = np.vstack([A, B])
    lab1 = S.euclidean_cluster(P, tol=0.2, min_size=10)
    lab100 = S.euclidean_cluster(P * 100.0, tol=0.2 * 100.0, min_size=10)
    assert np.array_equal(lab1, lab100)


# ═══════════════════════════════════════════════════════════════════════════
# 2. region_growing: 向きの違う2平面(直交ディヘドラル)→ 2領域
# ═══════════════════════════════════════════════════════════════════════════
def _dihedral():
    """直交する2面 A(法線+z) / B(法線+x) を共有エッジ付きで生成。返り (P, normals, |A|, |B|)。"""
    # Face A: z=0 平面, x,y in [0,1] 11x11 = 121
    faceA = grid_plane(np.linspace(0, 1, 11), np.linspace(0, 1, 11),
                       fixed_axis=2, fixed_val=0.0)
    # Face B: x=1 平面, y in [0,1](11), z in [0.1,1.0](10) = 110(z=0 は A の縁と重複回避)
    yb = np.linspace(0, 1, 11)
    zb = np.linspace(0.1, 1.0, 10)
    Y, Z = np.meshgrid(yb, zb, indexing="ij")
    faceB = np.stack([np.ones(Y.size), Y.ravel(), Z.ravel()], axis=1)
    P = np.vstack([faceA, faceB])
    normals = np.vstack([np.tile([0.0, 0.0, 1.0], (len(faceA), 1)),   # +z
                         np.tile([1.0, 0.0, 0.0], (len(faceB), 1))])  # +x
    return P, normals, len(faceA), len(faceB)


def test_region_growing_two_planes():
    P, normals, na, nb = _dihedral()
    labels = S.region_growing(P, normals=normals, angle_thresh_deg=15.0, k=20)

    assert labels.shape == (na + nb,)
    assert int((labels == -1).sum()) == 0        # 全点いずれかの領域へ
    uniq = np.unique(labels)
    assert len(uniq) == 2                         # ちょうど2領域
    sizes = sorted(np.bincount(labels).tolist(), reverse=True)
    assert sizes == sorted([na, nb], reverse=True)   # {121, 110}
    # 幾何的正当性: 各領域が単一の面に一致(A は z≈0、B は x≈1)
    la = labels[0]                                # face A の先頭点のラベル
    assert np.allclose(P[labels == la][:, 2], 0.0)          # A 領域は z=0
    lb = labels[na]                              # face B の先頭点のラベル
    assert np.allclose(P[labels == lb][:, 0], 1.0)          # B 領域は x=1


def test_region_growing_wide_angle_merges():
    """判別ケース: 閾値 100°(>90° の二面角)にすると2面は1領域に融合。"""
    P, normals, na, nb = _dihedral()
    labels = S.region_growing(P, normals=normals, angle_thresh_deg=100.0, k=20)
    assert len(np.unique(labels)) == 1
    assert int((labels == 0).sum()) == na + nb


def test_region_growing_flat_plane_estimated_normals():
    """GT: 単一平坦面は PCA 推定法線でも1領域(normals=None パス)。"""
    P = grid_plane(np.linspace(0, 1, 12), np.linspace(0, 1, 12),
                   fixed_axis=2, fixed_val=0.0)          # 144 点, z=0
    labels = S.region_growing(P, normals=None, angle_thresh_deg=15.0, k=16)
    assert len(np.unique(labels)) == 1
    assert int((labels == 0).sum()) == 144


# ═══════════════════════════════════════════════════════════════════════════
# 3. plane_segmentation: 地面+球 → 地面を1平面分離、球は残差(-1)
# ═══════════════════════════════════════════════════════════════════════════
def test_plane_segmentation_ground_and_sphere():
    ground = grid_plane(np.linspace(-1, 1, 15), np.linspace(-1, 1, 15),
                        fixed_axis=2, fixed_val=0.0)       # 225 点, z=0
    ng = len(ground)
    sphere = fib_sphere(200, 0.4, (0, 0, 0.8))             # z in [0.4,1.2], 地面から離れる
    ns = len(sphere)
    P = np.vstack([ground, sphere])                        # index [:225]=地面, [225:]=球

    labels = S.plane_segmentation(P, thresh=0.02, min_inliers=100,
                                  max_planes=5, iters=300, seed=0)

    assert labels.shape == (ng + ns,)
    # 地面が唯一の平面(label 0)= 全 225 点、球は全て残差 -1
    assert set(np.unique(labels).tolist()) == {-1, 0}
    assert np.all(labels[:ng] == 0)                        # 地面 = label 0
    assert np.all(labels[ng:] == -1)                       # 球 = 残差
    assert int((labels == 0).sum()) == ng
    assert int((labels == -1).sum()) == ns


def test_plane_segmentation_two_planes_iterative():
    """判別ケース: 非共面な2平面 → 反復抽出で2枚検出(単一平面適合との差)。"""
    floor = grid_plane(np.linspace(-1, 1, 15), np.linspace(-1, 1, 15),
                       fixed_axis=2, fixed_val=0.0)         # z=0, 225
    # 壁: y=3 平面, x in [-1,1](15), z in [1,3](15) = 225。床と非共面かつ非接触。
    wall = grid_plane(np.linspace(-1, 1, 15), np.linspace(1, 3, 15),
                      fixed_axis=1, fixed_val=3.0)
    P = np.vstack([floor, wall])

    labels = S.plane_segmentation(P, thresh=0.02, min_inliers=100,
                                  max_planes=5, iters=400, seed=0)

    assert set(np.unique(labels).tolist()) == {0, 1}       # ちょうど2平面、残差無し
    sizes = sorted(np.bincount(labels).tolist(), reverse=True)
    assert sizes == [225, 225]


def test_plane_segmentation_max_planes_cap():
    """max_planes で抽出枚数を上限クリップ(残りは -1)。"""
    floor = grid_plane(np.linspace(-1, 1, 15), np.linspace(-1, 1, 15),
                       fixed_axis=2, fixed_val=0.0)
    wall = grid_plane(np.linspace(-1, 1, 15), np.linspace(1, 3, 15),
                      fixed_axis=1, fixed_val=3.0)
    P = np.vstack([floor, wall])
    labels = S.plane_segmentation(P, thresh=0.02, min_inliers=100,
                                  max_planes=1, iters=400, seed=0)
    assert set(np.unique(labels).tolist()) == {-1, 0}      # 1枚だけ、残りは残差
    assert int((labels == 0).sum()) == 225
    assert int((labels == -1).sum()) == 225


# ═══════════════════════════════════════════════════════════════════════════
# 4. fail-closed / 縮退(note_15 B)
# ═══════════════════════════════════════════════════════════════════════════
def test_bad_shape_raises():
    bad = np.zeros((10, 2))
    with pytest.raises(ValueError):
        S.region_growing(bad)
    with pytest.raises(ValueError):
        S.euclidean_cluster(bad, tol=0.1)
    with pytest.raises(ValueError):
        S.plane_segmentation(bad, thresh=0.1, min_inliers=3)


def test_nonfinite_raises():
    P = np.zeros((10, 3))
    P[0, 0] = np.nan
    with pytest.raises(ValueError):
        S.euclidean_cluster(P, tol=0.1)


def test_invalid_params_raise():
    P = fib_sphere(50, 0.5, (0, 0, 0))
    with pytest.raises(ValueError):
        S.euclidean_cluster(P, tol=0.0)                    # tol<=0
    with pytest.raises(ValueError):
        S.euclidean_cluster(P, tol=-1.0)
    with pytest.raises(ValueError):
        S.region_growing(P, angle_thresh_deg=0.0)          # 角度域外
    with pytest.raises(ValueError):
        S.region_growing(P, angle_thresh_deg=180.0)
    with pytest.raises(ValueError):
        S.plane_segmentation(P, thresh=0.0, min_inliers=3)  # thresh<=0
    with pytest.raises(ValueError):
        S.plane_segmentation(P, thresh=0.1, min_inliers=2)  # min_inliers<3
    with pytest.raises(ValueError):
        S.plane_segmentation(P, thresh=0.1, min_inliers=3, max_planes=0)


def test_empty_input_returns_empty():
    empty = np.zeros((0, 3))
    assert S.region_growing(empty).shape == (0,)
    assert S.euclidean_cluster(empty, tol=0.1).shape == (0,)
    assert S.plane_segmentation(empty, thresh=0.1, min_inliers=3).shape == (0,)


def test_normals_shape_mismatch_raises():
    P = fib_sphere(30, 0.5, (0, 0, 0))
    with pytest.raises(ValueError):
        S.region_growing(P, normals=np.zeros((30, 2)))


def test_region_growing_marks_isolated_points_as_noise():
    """統一契約: 孤立ゴミ点は -1(ノイズ)。旧実装は非負ラベル化し -1 を返さなかった。"""
    import numpy as np, segment3d
    pl = np.column_stack([np.stack(np.meshgrid(np.linspace(0, 1, 10), np.linspace(0, 1, 10)), -1).reshape(-1, 2), np.zeros(100)])
    junk = np.vstack([pl, [[50., 0, 0], [52, 0, 0], [0, 50, 0]]])
    lab = segment3d.region_growing(junk, min_region_size=3)
    assert (lab == -1).any()          # 孤立点がノイズに
    assert (lab[:100] >= 0).all()     # 平面本体は有効ラベル
