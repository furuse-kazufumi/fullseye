"""curvature3d の GT 検証: 球/円柱/平面の閉形式曲率と一致するか。"""
import numpy as np

import curvature3d


def _fib_sphere(n, R, seed=0):
    """Fibonacci 球で半径 R の球面を n 点サンプル。"""
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    gold = np.pi * (1 + 5 ** 0.5)
    theta = gold * i
    x = np.sin(phi) * np.cos(theta)
    y = np.sin(phi) * np.sin(theta)
    z = np.cos(phi)
    return R * np.stack([x, y, z], axis=1)


def _cylinder(n_theta, n_z, R, H, seed=0):
    """半径 R・高さ H の円柱側面。"""
    th = np.linspace(0, 2 * np.pi, n_theta, endpoint=False)
    zz = np.linspace(-H / 2, H / 2, n_z)
    T, Z = np.meshgrid(th, zz)
    x = R * np.cos(T).ravel()
    y = R * np.sin(T).ravel()
    z = Z.ravel()
    return np.stack([x, y, z], axis=1)


def _plane(n, L, seed=0):
    rng = np.random.default_rng(seed)
    xy = rng.uniform(-L, L, size=(n, 2))
    return np.stack([xy[:, 0], xy[:, 1], np.zeros(n)], axis=1)


def test_sphere_curvature():
    R = 2.0
    pts = _fib_sphere(700, R)
    k1, k2 = curvature3d.principal_curvatures(pts, k=25)
    K = curvature3d.gaussian_curvature(pts, k=25)
    # 球: k1=k2=1/R, K=1/R²(離散フィット + 境界なしの閉曲面 → 中央値で ~10%)
    assert abs(np.median(np.abs(k1)) - 1 / R) < 0.15 * (1 / R)
    assert abs(np.median(np.abs(k2)) - 1 / R) < 0.15 * (1 / R)
    assert abs(np.median(K) - 1 / R ** 2) < 0.20 * (1 / R ** 2)
    # 凸符号(外向き法線で正)
    assert np.median(k1) > 0 and np.median(k2) > 0


def test_sphere_shape_index():
    pts = _fib_sphere(700, 2.0)
    s = curvature3d.shape_index(pts, k=25)
    # 凸球 → +1 付近
    assert np.median(s) > 0.9, np.median(s)


def test_cylinder_curvature():
    R = 1.5
    pts = _cylinder(60, 40, R, H=6.0)
    k1, k2 = curvature3d.principal_curvatures(pts, k=25)
    K = curvature3d.gaussian_curvature(pts, k=25)
    # 円柱: k1=1/R, k2≈0, K≈0(端の境界点はフィットが歪む → 中央値でロバストに)
    assert abs(np.median(k1) - 1 / R) < 0.15 * (1 / R), np.median(k1)
    assert abs(np.median(k2)) < 0.15 * (1 / R), np.median(k2)
    assert abs(np.median(K)) < 0.10 * (1 / R ** 2), np.median(K)


def test_cylinder_shape_index():
    pts = _cylinder(60, 40, 1.5, H=6.0)
    s = curvature3d.shape_index(pts, k=25)
    # 円柱(凸)→ +0.5 付近
    assert 0.3 < np.median(s) < 0.7, np.median(s)


def test_plane_curvature():
    pts = _plane(500, 3.0)
    k1, k2 = curvature3d.principal_curvatures(pts, k=25)
    K = curvature3d.gaussian_curvature(pts, k=25)
    assert np.median(np.abs(k1)) < 0.05
    assert np.median(np.abs(k2)) < 0.05
    assert np.median(np.abs(K)) < 0.01


def test_gaussian_sign_invariant_to_normal_flip():
    # ガウス曲率は法線反転に不変であるべき(K=k1k2)
    pts = _fib_sphere(400, 2.0)
    K = curvature3d.gaussian_curvature(pts, k=25)
    assert np.median(K) > 0  # 球は常に正の K


def _saddle(n, a, L, seed=0):
    """双曲放物面 z=(x²-y²)/(2a): 原点で主曲率 ±1/a(鞍点、K<0)。"""
    rng = np.random.default_rng(seed)
    xy = rng.uniform(-L, L, size=(n, 2))
    x, y = xy[:, 0], xy[:, 1]
    z = (x ** 2 - y ** 2) / (2 * a)
    return np.stack([x, y, z], axis=1)


def test_saddle_negative_gaussian_and_zero_shape_index():
    # 鞍点(双曲放物面): K<0、shape index ≈ 0(k1≈-k2)。中央付近でロバスト評価。
    a = 2.0
    pts = _saddle(1200, a, L=1.5)
    # 原点近傍の点だけ評価(端は曲率が変化)
    r = np.linalg.norm(pts[:, :2], axis=1)
    core = r < 0.7
    K = curvature3d.gaussian_curvature(pts, k=30)
    s = curvature3d.shape_index(pts, k=30)
    assert np.median(K[core]) < 0, np.median(K[core])          # 鞍点は負のガウス曲率
    assert abs(np.median(s[core])) < 0.35, np.median(s[core])  # k1≈-k2 → shape index ~0


def _paraboloid(n, k, L, seed=0):
    """軸対称放物面 z=0.5*k*(x²+y²)。k>0 = 上に凹む bowl/cup、k<0 = 上に膨らむ dome/cap。

    原点で主曲率 = |k|(臍点、K=k²>0)。曲率 |k| を小さくすれば「緩やかな凸/凹」になる。
    """
    rng = np.random.default_rng(seed)
    xy = rng.uniform(-L, L, size=(n, 2))
    x, y = xy[:, 0], xy[:, 1]
    z = 0.5 * k * (x ** 2 + y ** 2)
    return np.stack([x, y, z], axis=1)


def test_gentle_curvature_not_misclassified_as_flat():
    # 回帰(Bug1): 曲率 ~1e-7 の緩やかな凸ドームは平面(s=0)ではなく凸(s~+1)。
    # 旧挙動: 絶対しきい値 |ssum|>1e-6 未満で臍点判定を捨て s=0 に誤分類 → median=0.0 で FAIL。
    # 新挙動: スケール相対の臍点判定で符号を保ち median~+1 で PASS。
    pts = _paraboloid(1500, k=-1e-7, L=1.0)          # k<0 = 凸ドーム(向き無し=凸マグニチュード)
    k1, k2 = curvature3d.principal_curvatures(pts, k=30)
    # 主曲率自体は正しく ~1e-7(平面 0 ではない)
    assert abs(np.median(np.abs(k1)) - 1e-7) < 0.3e-7, np.median(np.abs(k1))
    s = curvature3d.shape_index(pts, k=30)
    assert np.median(s) > 0.9, np.median(s)          # 緩くても凸 → +1(平面 0 ではない)


def test_oriented_normals_distinguish_bowl_from_dome():
    # 回帰(Bug2): 開いた面の凹(bowl/cup)と凸(dome/cap)は向き付き法線で符号が分かれる。
    # 旧挙動: normals 引数が無く(TypeError)、あってもヒューリスティクスで両方 +(区別不能)。
    # 新挙動: +z 向き法線を与えると cup(凹)→負、cap(凸)→正 で符号が逆転。
    bowl = _paraboloid(1500, k=+0.8, L=1.0)          # k>0 = 上に凹む cup
    dome = _paraboloid(1500, k=-0.8, L=1.0)          # k<0 = 上に膨らむ cap
    up = np.tile([0.0, 0.0, 1.0], (1500, 1))         # 視点由来の向き付き法線(+z)

    def _core(pts):
        return np.linalg.norm(pts[:, :2], axis=1) < 0.6   # 端は fit が歪むので中央部で評価

    s_bowl = curvature3d.shape_index(bowl, k=30, normals=up)
    s_dome = curvature3d.shape_index(dome, k=30, normals=up)
    assert np.median(s_bowl[_core(bowl)]) < -0.5, np.median(s_bowl[_core(bowl)])  # cup → -1
    assert np.median(s_dome[_core(dome)]) > 0.5, np.median(s_dome[_core(dome)])   # cap → +1
    # 対比: 向き付き法線なしでは両方 凸マグニチュード(+)= 原理的に区別不能(honest)
    hb = curvature3d.shape_index(bowl, k=30)
    hd = curvature3d.shape_index(dome, k=30)
    assert np.median(hb[_core(bowl)]) > 0.5 and np.median(hd[_core(dome)]) > 0.5


def test_principal_curvature_sign_follows_oriented_normal():
    # 向き付き法線で主曲率の符号が正しく出る(cup=負, cap=正)。K=k1k2 は不変で常に正。
    bowl = _paraboloid(1500, k=+0.8, L=1.0)
    dome = _paraboloid(1500, k=-0.8, L=1.0)
    up = np.tile([0.0, 0.0, 1.0], (1500, 1))

    def _core(pts):
        return np.linalg.norm(pts[:, :2], axis=1) < 0.6

    k1b, k2b = curvature3d.principal_curvatures(bowl, k=30, normals=up)
    k1d, k2d = curvature3d.principal_curvatures(dome, k=30, normals=up)
    assert np.median(k1b[_core(bowl)]) < 0 and np.median(k2b[_core(bowl)]) < 0   # cup: 両方負
    assert np.median(k1d[_core(dome)]) > 0 and np.median(k2d[_core(dome)]) > 0   # cap: 両方正
    # ガウス曲率は向きに不変(cup も cap も正の K)
    assert np.median(curvature3d.gaussian_curvature(bowl, k=30)[_core(bowl)]) > 0
    assert np.median(curvature3d.gaussian_curvature(dome, k=30)[_core(dome)]) > 0


def test_normals_validation_fail_closed():
    # fail-closed: 不正な向き付き法線は詐称せず ValueError。
    pts = _paraboloid(400, k=0.8, L=1.0)
    with pytest.raises(ValueError):
        curvature3d.shape_index(pts, k=25, normals=np.zeros((400, 3)))        # ゼロ長
    with pytest.raises(ValueError):
        curvature3d.shape_index(pts, k=25, normals=np.ones((399, 3)))         # 形状不一致
    with pytest.raises(ValueError):
        bad = np.ones((400, 3)); bad[0, 0] = np.nan
        curvature3d.shape_index(pts, k=25, normals=bad)                       # 非有限
