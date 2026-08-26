"""ransac_fit.py の ground-truth テスト(既知プリミティブ + 外れ値注入で頑健性を数値検証)。

match3d.py の最小二乗 ``fit_*`` は外れ値に弱い。ここでは既知の平面/球/直線/円筒を生成し、
30% 前後のランダム外れ値を混ぜても RANSAC が真値を復元し(角度/中心/半径誤差)、
inlier_mask が注入外れ値を排除することを確認する。決定論(同一 seed で二度呼んで一致)も検証。
"""
import numpy as np
import pytest

pytest.importorskip("scipy")

import ransac_fit as R


def _cos(a, b):
    """2 方向ベクトルの |cos|(符号の任意性を吸収)。"""
    a = np.asarray(a, float); b = np.asarray(b, float)
    return abs(float(a @ b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def _angle_deg(a, b):
    """2 方向ベクトルのなす角(度、符号非依存で 0〜90)。"""
    return np.degrees(np.arccos(np.clip(_cos(a, b), 0.0, 1.0)))


# ═══════════════════════════════════════════════════════════════════════════
# 平面
# ═══════════════════════════════════════════════════════════════════════════
def _plane_cloud(seed=0, n=600, outlier_frac=0.30, noise=0.01):
    """既知平面 normal·x = offset 上の点 + ランダム外れ値。返り (P, normal, is_outlier)。"""
    rng = np.random.default_rng(seed)
    normal = _u([0.3, -0.5, 1.0]); offset = 0.7
    e1 = _u(np.cross(normal, [1, 0, 0])); e2 = np.cross(normal, e1)
    n_out = int(n * outlier_frac); n_in = n - n_out
    uv = rng.uniform(-5, 5, (n_in, 2))
    base = normal * offset
    inl = base + uv[:, :1] * e1 + uv[:, 1:] * e2 + rng.normal(0, noise, (n_in, 3))
    out = rng.uniform(-5, 5, (n_out, 3))            # 空間全体に散る外れ値
    P = np.vstack([inl, out])
    is_out = np.zeros(n, bool); is_out[n_in:] = True
    perm = rng.permutation(n)
    return P[perm], normal, is_out[perm]


def _u(v):
    v = np.asarray(v, float); return v / np.linalg.norm(v)


def test_plane_recovers_normal_under_outliers():
    """平面: 30% 外れ値下で復元法線が真値と一致(角度<2°)+ inlier_ratio が inlier 割合付近。"""
    P, normal, is_out = _plane_cloud(0)
    params, mask, info = R.ransac_plane(P, thresh=0.05)
    assert _angle_deg(params["normal"], normal) < 2.0
    # 平面方程式 normal·x + d = 0 が inlier で満たされる
    d = params["d"]
    resid = np.abs(P[mask] @ params["normal"] + d)
    assert resid.max() < 0.06
    assert info["n_inliers"] > 0.6 * len(P)


def test_plane_mask_excludes_outliers():
    """平面: inlier_mask が注入外れ値の大半(>80%)を False にする。"""
    P, normal, is_out = _plane_cloud(1)
    _, mask, _ = R.ransac_plane(P, thresh=0.05)
    # 注入外れ値のうち mask=False の割合
    excluded = (~mask[is_out]).mean()
    assert excluded > 0.8
    # 真の inlier の大半は拾えている
    assert mask[~is_out].mean() > 0.9


# ═══════════════════════════════════════════════════════════════════════════
# 球
# ═══════════════════════════════════════════════════════════════════════════
def _sphere_cloud(seed=0, n=600, outlier_frac=0.30, noise=0.01):
    """既知 center/radius の球面上の点 + 外れ値。返り (P, center, radius, is_outlier)。"""
    rng = np.random.default_rng(seed)
    center = np.array([1.2, -0.7, 2.0]); radius = 1.5
    n_out = int(n * outlier_frac); n_in = n - n_out
    v = rng.normal(0, 1, (n_in, 3)); v /= np.linalg.norm(v, axis=1, keepdims=True)
    inl = center + radius * v + rng.normal(0, noise, (n_in, 3))
    out = center + rng.uniform(-4, 4, (n_out, 3))   # 球から外れる点
    P = np.vstack([inl, out])
    is_out = np.zeros(n, bool); is_out[n_in:] = True
    perm = rng.permutation(n)
    return P[perm], center, radius, is_out[perm]


def test_sphere_recovers_center_radius_under_outliers():
    """球: 30% 外れ値下で center 誤差<thresh 相当・radius 誤差小・外れ値を排除。"""
    P, center, radius, is_out = _sphere_cloud(0)
    thresh = 0.05
    params, mask, info = R.ransac_sphere(P, thresh=thresh)
    assert np.linalg.norm(params["center"] - center) < thresh
    assert abs(params["radius"] - radius) < thresh
    assert (~mask[is_out]).mean() > 0.8
    assert mask[~is_out].mean() > 0.9


# ═══════════════════════════════════════════════════════════════════════════
# 直線
# ═══════════════════════════════════════════════════════════════════════════
def _line_cloud(seed=0, n=500, outlier_frac=0.30, noise=0.01):
    """既知直線 point + t*direction 上の点 + 外れ値。返り (P, point, direction, is_outlier)。"""
    rng = np.random.default_rng(seed)
    point = np.array([0.5, -1.0, 0.3]); direction = _u([1.0, 0.4, -0.2])
    n_out = int(n * outlier_frac); n_in = n - n_out
    t = rng.uniform(-5, 5, (n_in, 1))
    inl = point + t * direction + rng.normal(0, noise, (n_in, 3))
    out = point + rng.uniform(-6, 6, (n_out, 3))
    P = np.vstack([inl, out])
    is_out = np.zeros(n, bool); is_out[n_in:] = True
    perm = rng.permutation(n)
    return P[perm], point, direction, is_out[perm]


def test_line_recovers_direction_under_outliers():
    """直線: 30% 外れ値下で direction が一致(|cos|>0.99)+ 外れ値を排除。"""
    P, point, direction, is_out = _line_cloud(0)
    params, mask, info = R.ransac_line(P, thresh=0.05)
    assert _cos(params["direction"], direction) > 0.99
    assert (~mask[is_out]).mean() > 0.8
    assert mask[~is_out].mean() > 0.9


# ═══════════════════════════════════════════════════════════════════════════
# 円筒
# ═══════════════════════════════════════════════════════════════════════════
def _cylinder_cloud(seed=0, n=800, outlier_frac=0.25, noise=0.01):
    """既知 軸/半径 の円筒面上の点 + 各点法線 + 外れ値。返り (P, Nrm, axis, radius, is_outlier)。"""
    rng = np.random.default_rng(seed)
    axis = _u([0.2, 0.3, 1.0]); radius = 1.2
    axis_pt = np.array([0.5, -0.4, 0.0])
    e1 = _u(np.cross(axis, [1, 0, 0])); e2 = np.cross(axis, e1)
    n_out = int(n * outlier_frac); n_in = n - n_out
    th = rng.uniform(0, 2 * np.pi, n_in); h = rng.uniform(-4, 4, n_in)
    radial = np.cos(th)[:, None] * e1 + np.sin(th)[:, None] * e2
    inl = axis_pt + radius * radial + h[:, None] * axis + rng.normal(0, noise, (n_in, 3))
    n_inl = radial + rng.normal(0, noise, (n_in, 3))            # 外向き法線(+ノイズ)
    n_inl /= np.linalg.norm(n_inl, axis=1, keepdims=True)
    out = axis_pt + rng.uniform(-4, 4, (n_out, 3))
    n_out_v = rng.normal(0, 1, (n_out, 3)); n_out_v /= np.linalg.norm(n_out_v, axis=1, keepdims=True)
    P = np.vstack([inl, out]); Nrm = np.vstack([n_inl, n_out_v])
    is_out = np.zeros(n, bool); is_out[n_in:] = True
    perm = rng.permutation(n)
    return P[perm], Nrm[perm], axis, radius, is_out[perm]


def test_cylinder_recovers_axis_radius_under_outliers():
    """円筒: 25% 外れ値下で軸方向が一致(|cos|>0.98)・radius 誤差小・inlier 情報が整合。"""
    P, Nrm, axis, radius, is_out = _cylinder_cloud(0)
    params, mask, info = R.ransac_cylinder(P, Nrm, thresh=0.05)
    assert _cos(params["axis"], axis) > 0.98
    assert abs(params["radius"] - radius) < 0.05
    assert info["n_inliers"] == int(mask.sum())
    assert 0.0 <= info["inlier_ratio"] <= 1.0
    assert (~mask[is_out]).mean() > 0.7


# ═══════════════════════════════════════════════════════════════════════════
# 決定論
# ═══════════════════════════════════════════════════════════════════════════
def test_determinism_same_seed():
    """同じ seed で 2 回呼ぶと 4 プリミティブ全てで結果がビット一致する。"""
    Pp, *_ = _plane_cloud(3)
    Ps, *_ = _sphere_cloud(3)
    Pl, *_ = _line_cloud(3)
    Pc, Nc, *_ = _cylinder_cloud(3)

    for a, b in [
        (R.ransac_plane(Pp, 0.05, seed=7), R.ransac_plane(Pp, 0.05, seed=7)),
        (R.ransac_sphere(Ps, 0.05, seed=7), R.ransac_sphere(Ps, 0.05, seed=7)),
        (R.ransac_line(Pl, 0.05, seed=7), R.ransac_line(Pl, 0.05, seed=7)),
        (R.ransac_cylinder(Pc, Nc, 0.05, seed=7), R.ransac_cylinder(Pc, Nc, 0.05, seed=7)),
    ]:
        pa, ma, ia = a; pb, mb, ib = b
        for k in pa:
            assert np.allclose(pa[k], pb[k])
        assert np.array_equal(ma, mb)
        assert ia == ib


def test_insufficient_points_raises():
    """点数不足は graceful に ValueError(深部の IndexError にしない)。"""
    with pytest.raises(ValueError):
        R.ransac_plane(np.zeros((2, 3)), 0.05)
    with pytest.raises(ValueError):
        R.ransac_sphere(np.zeros((3, 3)), 0.05)
    with pytest.raises(ValueError):
        R.ransac_cylinder(np.zeros((1, 3)), np.zeros((1, 3)), 0.05)
    with pytest.raises(ValueError):                     # 形状不一致
        R.ransac_cylinder(np.zeros((5, 3)), np.zeros((4, 3)), 0.05)
