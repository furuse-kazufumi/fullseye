"""pipeline3d — Physical AI 合成パイプライン(高優先 op×op)の検証。"""
import numpy as np
import pytest
pytest.importorskip("torch")
pytest.importorskip("scipy")
import pipeline3d as P
import match3d as X


def _rot(ax, deg):
    a = np.asarray(ax, float); a /= np.linalg.norm(a); th = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * K @ K


def _rerr(Re, Rg):
    Re = np.asarray(Re)

    def g(A, B):
        return np.degrees(np.arccos(np.clip((np.trace(A.T @ B) - 1) / 2, -1, 1)))

    return min(g(Re, Rg), g(Re, Rg.T))


def _cloud(seed=0):
    rng = np.random.default_rng(seed)
    return np.vstack([rng.uniform([0, 0, 0], [10, 3, 3], (1500, 3)),
                      rng.uniform([0, 0, 0], [3, 10, 3], (1000, 3)),
                      rng.uniform([8, 1, 1], [9.5, 2.5, 7], (500, 3))])


def test_register_pointclouds_global_no_init():
    """点群大域登録(FPFH+ICP): 55° 回転+部分を init なしで機械精度に。"""
    pts = _cloud(0); Rg = _rot([1, 0.4, 0.2], 55.0)
    dst = (Rg @ pts.T).T + np.array([4, -2, 1.0])
    R, t, rmse = P.register_pointclouds(pts[pts[:, 0] < 8], dst)
    assert _rerr(R, Rg) < 3.0


def test_register_auto_selects_method():
    """register_auto: 遠/大回転→fpfh+icp、近接→icp を自動選択。"""
    pts = _cloud(0); Rg = _rot([1, 0.4, 0.2], 55.0)
    dst_far = (Rg @ pts.T).T + np.array([4, -2, 1.0])
    m1, R1, _ = P.register_auto(pts[pts[:, 0] < 8], dst_far)
    assert m1 == "fpfh+icp" and _rerr(R1, Rg) < 3.0
    dst_near = (_rot([0, 0, 1], 2.0) @ pts.T).T + 0.1
    m2, _, _ = P.register_auto(pts, dst_near)
    assert m2 == "icp"


def test_measure_plane_and_roundness():
    """メトロロジー合成: 平面度・真球度が欠陥を検出。"""
    rng = np.random.default_rng(0)
    Pp = rng.random((300, 2))
    pl = np.stack([Pp[:, 0] * 10, Pp[:, 1] * 10, 0.02 * Pp[:, 0] + 1], 1); pl[50] += [0, 0, 0.3]
    mp = P.measure_plane(pl)
    assert mp["pv"] > 0.25 and mp["flatness_rms"] < 0.1
    ctr = np.array([2.0, 3.0, 4.0])
    u = rng.random(400) * 2 * np.pi; v = rng.random(400) * np.pi
    sp = np.stack([np.sin(v) * np.cos(u), np.sin(v) * np.sin(u), np.cos(v)], 1) * 5 + ctr
    sp[:5] += 0.3 * (sp[:5] - ctr) / np.linalg.norm(sp[:5] - ctr, axis=1, keepdims=True)
    ir = P.inspect_roundness(sp)
    assert abs(ir["radius"] - 5.0) < 0.1 and ir["roundness_pv"] > 0.15


def test_match_sdf_localizes():
    """SDF ベース照合が定位(滑らか表現で robust)。"""
    N = 48
    zz, yy, xx = np.mgrid[0:N, 0:N, 0:N]
    scene = np.zeros((N, N, N)); d0, h0, w0 = 30, 20, 26
    tz, ty, tx = np.mgrid[0:15, 0:15, 0:15]
    tmpl = (np.sqrt((tz - 7) ** 2 + (ty - 7) ** 2 + (tx - 7) ** 2) < 6).astype(float)
    scene[d0 - 7:d0 + 8, h0 - 7:h0 + 8, w0 - 7:w0 + 8] = tmpl
    r = P.match_sdf(scene, tmpl)
    assert abs(r[1] - d0) + abs(r[2] - h0) + abs(r[3] - w0) <= 3
