"""plane_sweep の GT 検証: 既知深度の合成テクスチャ平面を 2 視点でレンダ→深度を復元。

レンダラは実装とは独立の前方モデル(各画素の ray を平面と交差→テクスチャをサンプル)。
plane_sweep は逆に homography ワープ+winner-take-all で解くので、GT は実装の再導出ではない。
"""
import numpy as np
import pytest

import plane_sweep


# ---- 独立 GT レンダラ -------------------------------------------------------

def _rot(axis, deg):
    """軸まわり deg 度の回転(Rodrigues)。"""
    axis = np.asarray(axis, float)
    axis = axis / np.linalg.norm(axis)
    th = np.deg2rad(deg)
    Kx = np.array([[0, -axis[2], axis[1]],
                   [axis[2], 0, -axis[0]],
                   [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(th) * Kx + (1 - np.cos(th)) * (Kx @ Kx)


def _texture(x, y):
    """平面上 (x,y) の輝度。勾配が概ね全域で非零・低周期(深度の一意性を担保)。"""
    return (np.sin(1.7 * x + 0.3) * np.cos(2.3 * y - 0.5)
            + 0.6 * np.sin(0.9 * x + 1.1 * y + 0.7)
            + 0.4 * np.cos(2.9 * x - 1.3 * y + 0.2)
            + 0.25 * np.sin(0.5 * x - 0.4 * y))


def _render(K, R, t, normal, d0, shape):
    """カメラ P=K[R|t] で平面 n^T X = d0(基準系)を撮像。→ (画像, 深度 Z, 3D 点 X)。

    画素 p の ray を平面と交差→3D 点 X→_texture(X_x,X_y) をサンプル。X の基準系深度と
    3D 点(H,W,3)も返す。R,t は基準カメラ([I|0])に対する姿勢。基準系で ray を組み立て交差を解く。
    """
    h, w = shape
    Kinv = np.linalg.inv(K)
    Rinv = R.T
    C = -Rinv @ t                       # カメラ中心(基準系)
    yy, xx = np.mgrid[0:h, 0:w]
    p = np.stack([xx.ravel(), yy.ravel(), np.ones(xx.size)], axis=0)  # (3,N)
    dir_cam = Kinv @ p                  # カメラ系 ray 方向
    dir_ref = Rinv @ dir_cam            # 基準系方向
    n = np.asarray(normal, float).reshape(3)
    # n^T (C + s dir_ref) = d0  →  s = (d0 - n·C) / (n·dir_ref)
    denom = n @ dir_ref
    s = (d0 - n @ C) / denom
    X = C[:, None] + s[None, :] * dir_ref            # (3,N) 基準系 3D 点
    img = _texture(X[0], X[1]).reshape(h, w)
    depth = X[2].reshape(h, w)          # 基準系での深度 Z
    return img, depth, X.T.reshape(h, w, 3)


def _visible_mask(K, R, t, X_ref, shape, margin=2.0):
    """ref の各 3D 点を source に投影し、画像内(margin 付)に落ちる画素の可視マスク。→ (H,W) bool。

    真の 3D 点の src 投影が FOV 外/背面の画素は(オクルージョン相当で)照合不能。評価から除外する。
    """
    h, w = shape
    Xf = X_ref.reshape(-1, 3).T
    proj = K @ (R @ Xf + t.reshape(3, 1))
    z = proj[2]
    with np.errstate(invalid="ignore", divide="ignore"):
        u = proj[0] / z
        v = proj[1] / z
    ok = (z > 1e-6) & (u >= margin) & (u <= w - 1 - margin) \
        & (v >= margin) & (v <= h - 1 - margin)
    return ok.reshape(h, w)


def _scene(d_scale=1.0, tilt_deg=0.0):
    """合成 2 視点シーン。→ (img_ref, img_src, K, R, t, normal, d0, ref 真深度, ref 3D 点)。"""
    shape = (140, 180)
    K = np.array([[500.0, 0, 90.0], [0, 500.0, 70.0], [0, 0, 1.0]])
    R = _rot([0.15, 1.0, 0.1], 5.0)                  # source の相対回転
    t = np.array([0.14, 0.03, 0.02]) * d_scale       # baseline(深度スケールに比例)
    d0 = 5.0 * d_scale                               # 平面パラメータ(距離)
    if tilt_deg == 0.0:
        normal = np.array([0.0, 0.0, 1.0])
    else:
        th = np.deg2rad(tilt_deg)                     # 法線を傾け per-pixel 深度を変化させる
        normal = np.array([np.sin(th) * 0.4, np.sin(th), np.cos(th)])
        normal = normal / np.linalg.norm(normal)
    img_ref, depth_ref, X_ref = _render(K, np.eye(3), np.zeros(3), normal, d0, shape)
    img_src, _, _ = _render(K, R, t, normal, d0, shape)
    return img_ref, img_src, K, R, t, normal, d0, depth_ref, X_ref


def _candidates(zmin, zmax, num):
    """逆深度等間隔の候補深度(近距離を密に)。"""
    inv = np.linspace(1.0 / zmax, 1.0 / zmin, num)
    return (1.0 / inv)[::-1].copy()


def _crop(a):
    """視野外/端の影響を避ける中央領域。"""
    return a[25:-25, 30:-30]


# ---- homography / warp の GT -----------------------------------------------

def test_plane_homography_matches_geometry():
    """H が ref 画素→src 画素の射影に一致(既知 3D 点の投影と突合)。"""
    K = np.array([[500.0, 0, 128], [0, 500.0, 96], [0, 0, 1.0]])
    R = _rot([0.1, 1, 0.05], 8.0)
    t = np.array([0.4, 0.05, 0.05])
    d0 = 5.0
    H = plane_sweep.plane_homography(K, R, t, d0)
    Kinv = np.linalg.inv(K)
    for p in ([150.0, 110.0, 1.0], [60.0, 40.0, 1.0]):
        p = np.array(p)
        X = (Kinv @ p) * d0              # 平面 Z=d0 上の点
        ps = K @ (R @ X + t)
        ps = ps[:2] / ps[2]
        ph = H @ p
        ph = ph[:2] / ph[2]
        assert np.allclose(ps, ph, atol=1e-9)


def test_warp_identity():
    """H=I なら恒等ワープ(入力を復元)。"""
    rng = np.random.default_rng(1)
    img = rng.random((30, 40))
    out = plane_sweep.warp_by_plane(img, np.eye(3))
    assert np.allclose(out, img, atol=1e-9)


def test_warp_roundtrip_inverse():
    """H で前進→H^{-1} で戻すと内部領域が一致(homography ワープの整合)。"""
    K = np.array([[300.0, 0, 60], [0, 300.0, 45], [0, 0, 1.0]])
    R = _rot([0, 1, 0], 5.0)
    t = np.array([0.2, 0.0, 0.02])
    H = plane_sweep.plane_homography(K, R, t, 6.0)
    rng = np.random.default_rng(2)
    img = ndi_smooth(rng.random((90, 120)))
    fwd = plane_sweep.warp_by_plane(img, H)
    back = plane_sweep.warp_by_plane(fwd, np.linalg.inv(H))
    m = np.isfinite(back)
    c = np.zeros_like(m)
    c[20:-20, 25:-25] = True
    sel = m & c
    assert np.nanmax(np.abs(back[sel] - img[sel])) < 1e-2


def ndi_smooth(a):
    """テスト補助: 軽い平滑化(補間往復の誤差を抑える)。"""
    from scipy import ndimage
    return ndimage.gaussian_filter(a, 1.0)


# ---- 深度復元 GT(フロント平行, 2 スケール) --------------------------------

@pytest.mark.parametrize("d_scale", [1.0, 8.0])
def test_recover_frontoparallel_depth_two_scales(d_scale):
    """既知深度のフロント平行平面を復元(相対誤差 < 数%)。スケール相対で 2 値検証。"""
    img_ref, img_src, K, R, t, normal, d0, depth_ref = _scene(d_scale=d_scale)
    cands = _candidates(0.5 * d0, 1.8 * d0, 80)
    est = plane_sweep.plane_sweep_depth(img_ref, img_src, K, R, t, cands, window=5)
    est_c = _crop(est)
    gt_c = _crop(depth_ref)
    assert np.all(np.isfinite(est_c))
    rel = np.abs(est_c - gt_c) / gt_c
    # 系統誤差の上限は候補間隔(離散化)。中央値/90%tile で honest に評価。
    assert np.median(rel) < 0.03, f"median rel={np.median(rel):.4f}"
    assert np.percentile(rel, 90) < 0.06, f"p90 rel={np.percentile(rel, 90):.4f}"


def test_recover_depth_value_is_uniform_frontoparallel():
    """フロント平行なら真深度は全域一定 → 推定も概ね一定(平面の性質を確認)。"""
    img_ref, img_src, K, R, t, normal, d0, depth_ref = _scene(d_scale=1.0)
    assert np.allclose(depth_ref, d0, atol=1e-9)     # GT 自体の健全性
    cands = _candidates(0.5 * d0, 1.8 * d0, 80)
    est = _crop(plane_sweep.plane_sweep_depth(img_ref, img_src, K, R, t, cands, window=5))
    assert np.median(np.abs(est - d0) / d0) < 0.03


# ---- 深度復元 GT(傾いた平面, per-pixel 深度が変化) ------------------------

def test_recover_tilted_plane_varying_depth():
    """傾いた平面の per-pixel 深度(画像内で変化)をフロント平行掃引で復元。"""
    img_ref, img_src, K, R, t, normal, d0, depth_ref = _scene(tilt_deg=20.0)
    gt_c = _crop(depth_ref)
    # 深度が実際に変化していること(自明な一定深度でない判別ケース)
    assert (gt_c.max() - gt_c.min()) / gt_c.mean() > 0.15
    cands = _candidates(0.7 * gt_c.min(), 1.3 * gt_c.max(), 120)
    est = _crop(plane_sweep.plane_sweep_depth(img_ref, img_src, K, R, t, cands, window=5))
    rel = np.abs(est - gt_c) / gt_c
    assert np.median(rel) < 0.04, f"median rel={np.median(rel):.4f}"
    assert np.percentile(rel, 85) < 0.08, f"p85 rel={np.percentile(rel, 85):.4f}"


# ---- fail-closed ------------------------------------------------------------

def _K():
    return np.array([[500.0, 0, 90.0], [0, 500.0, 70.0], [0, 0, 1.0]])


def test_fail_empty_image():
    with pytest.raises(ValueError):
        plane_sweep.plane_sweep_depth(np.zeros((0, 0)), np.zeros((0, 0)),
                                      _K(), np.eye(3), np.zeros(3), [5.0])


def test_fail_non_2d():
    with pytest.raises(ValueError):
        plane_sweep.warp_by_plane(np.zeros((4, 4, 3)), np.eye(3))


def test_fail_shape_mismatch():
    with pytest.raises(ValueError):
        plane_sweep.cost_volume(np.zeros((10, 10)), np.zeros((10, 12)),
                                _K(), np.eye(3), np.zeros(3), [5.0])


def test_fail_empty_candidates():
    with pytest.raises(ValueError):
        plane_sweep.plane_sweep_depth(np.zeros((8, 8)), np.zeros((8, 8)),
                                      _K(), np.eye(3), np.zeros(3), [])


def test_fail_nonpositive_depth():
    with pytest.raises(ValueError):
        plane_sweep.plane_homography(_K(), np.eye(3), np.zeros(3), -1.0)
    with pytest.raises(ValueError):
        plane_sweep.cost_volume(np.zeros((8, 8)), np.zeros((8, 8)),
                                _K(), np.eye(3), np.zeros(3), [5.0, 0.0])


def test_fail_singular_K():
    Ksing = np.array([[500.0, 0, 90.0], [0, 0.0, 70.0], [0, 0, 1.0]])  # fy=0
    with pytest.raises(ValueError):
        plane_sweep.plane_homography(Ksing, np.eye(3), np.zeros(3), 5.0)
