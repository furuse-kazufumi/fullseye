# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""polygrav(一様密度の多面体の重力・平面で切った閉じた立体)の門。

真値は op の外から取る: 直方体の重力は Gauss–Legendre の 3 重求積(別の経路)、遠方は点質量、発散と勾配は
差分(立体角の和を使わない経路)、切った 2 つの和は全体、体積は格子で数えた値。
"""
from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import pytest

import polygrav as pg

ROOT = Path(__file__).resolve().parents[1]


def _box(a, b, c, origin=(0.0, 0.0, 0.0)):
    V = np.array([[x, y, z] for x in (0, a) for y in (0, b) for z in (0, c)], float) + np.asarray(origin)
    quads = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    F = []
    for q in quads:
        F += [[q[0], q[1], q[2]], [q[0], q[2], q[3]]]
    return V, np.array(F)


def _quad(P, a, b, c, n=40):
    x, w = np.polynomial.legendre.leggauss(n)
    X, Y, Z = (x + 1) / 2 * a, (x + 1) / 2 * b, (x + 1) / 2 * c
    W = np.einsum("i,j,k->ijk", w, w, w) * a * b * c / 8.0
    XX, YY, ZZ = np.meshgrid(X, Y, Z, indexing="ij")
    d = np.stack([XX - P[0], YY - P[1], ZZ - P[2]], -1)
    r = np.linalg.norm(d, axis=-1)
    return -(W / r).sum(), (W[..., None] * d / r[..., None] ** 3).sum(axis=(0, 1, 2))


def _icosphere(freq, r):
    import fullseye as fs
    V, F = fs.ledger.geodesic_dome(freq, radius=r)
    return np.asarray(V, float), np.asarray(F)


def test_call_example():
    """module の docstring の呼び出し例をそのまま実行する。"""
    doc = pg.__doc__
    code = doc[doc.index("    import numpy as np\n    import polygrav"):]
    code = "\n".join(ln[4:] for ln in code.splitlines() if ln.startswith("    ") or not ln.strip())
    ns: dict = {}
    exec(compile(code, "polygrav_doc_example", "exec"), ns)
    g, h = ns["g"], ns["h"]
    assert g["mass"] == pytest.approx(2000.0 * 1e6 / 6.0, rel=1e-12)
    assert g["acceleration"][0, 0] == pytest.approx(-pg.G_NEWTON * g["mass"] / 1e8, rel=2e-2)
    assert h["volume"] == pytest.approx(g["volume"] / 8.0, rel=1e-12)


def test_box_matches_gauss_legendre_quadrature():
    V, F = _box(2.0, 1.0, 0.5)
    for P in (np.array([5.0, 3.0, 2.0]), np.array([-1.5, 0.4, 0.9]), np.array([1.0, -2.0, -0.3])):
        r = pg.polyhedron_gravity((V, F), P[None, :], density=1.0, G=1.0)
        U, g = _quad(P, 2.0, 1.0, 0.5)
        assert abs(r["potential"][0] - U) / abs(U) < 1e-11
        assert np.max(np.abs(r["acceleration"][0] - g)) / np.linalg.norm(g) < 1e-11


def test_sphere_far_field_is_a_point_mass_and_inside_is_linear():
    V, F = _icosphere(16, 100.0)
    far = np.array([[0.0, 0.0, 2000.0], [1000.0, 700.0, -400.0]])
    r = pg.polyhedron_gravity((V, F), far, density=1.0, G=1.0)
    rr = np.linalg.norm(far, axis=1)
    assert np.max(np.abs(np.linalg.norm(r["acceleration"], axis=1) * rr ** 2 / r["mass"] - 1.0)) < 1e-6
    assert np.max(np.abs(-r["potential"] * rr / r["mass"] - 1.0)) < 1e-6
    # 向きは中心へ
    cosang = -np.einsum("ij,ij->i", r["acceleration"], far) / (np.linalg.norm(r["acceleration"], axis=1) * rr)
    assert np.all(cosang > 1 - 1e-9)
    inside = np.array([[10.0, 20.0, 5.0]])
    ri = pg.polyhedron_gravity((V, F), inside, density=1.0, G=1.0)
    assert np.linalg.norm(ri["acceleration"][0]) == pytest.approx(4.0 / 3.0 * math.pi * np.linalg.norm(inside), rel=2e-3)


def test_gauss_law_by_solid_angles_and_by_finite_differences():
    V, F = _icosphere(4, 50.0)
    V = V * np.array([2.0, 1.0, 0.7])                       # 球でない(楕円体の多面体)
    rho, G = 1800.0, pg.G_NEWTON
    lim = 4.0 * math.pi * G * rho
    h = 1e-3
    for base, expect in ((np.array([3.0, -4.0, 2.0]), -lim), (np.array([0.0, 0.0, 120.0]), 0.0)):
        pts = [base]
        for k in range(3):
            e = np.zeros(3)
            e[k] = h
            pts += [base + e, base - e]
        r = pg.polyhedron_gravity((V, F), np.array(pts), density=rho)
        assert abs(r["div_g"][0] - expect) <= 1e-12 * lim
        fd = sum((r["acceleration"][1 + 2 * k][k] - r["acceleration"][2 + 2 * k][k]) / (2 * h) for k in range(3))
        assert abs(fd - expect) <= 1e-6 * lim
        grad = np.array([-(r["potential"][1 + 2 * k] - r["potential"][2 + 2 * k]) / (2 * h) for k in range(3)])
        assert np.linalg.norm(grad - r["acceleration"][0]) <= 1e-7 * np.linalg.norm(r["acceleration"][0])
    on = pg.polyhedron_gravity((V, F), V[:3], density=rho)    # 頂点の上でも有限
    assert np.all(np.isfinite(on["potential"])) and np.all(np.isfinite(on["acceleration"]))


def test_rigid_motion_moves_the_field_with_the_body():
    V, F = _icosphere(3, 40.0)
    V = V * np.array([1.8, 1.0, 0.6])
    P = np.array([[90.0, 10.0, -20.0], [5.0, 3.0, 1.0]])
    r0 = pg.polyhedron_gravity((V, F), P, density=1.0, G=1.0)
    for ang in (0.3, 1.1, 2.6):
        c, s = math.cos(ang), math.sin(ang)
        R = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]) @ np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])
        t = np.array([7.0, -3.0, 11.0])
        r1 = pg.polyhedron_gravity((V @ R.T + t, F), P @ R.T + t, density=1.0, G=1.0)
        assert np.max(np.abs(r1["potential"] - r0["potential"])) < 1e-12 * np.max(np.abs(r0["potential"]))
        assert np.max(np.abs(r1["acceleration"] - r0["acceleration"] @ R.T)) < 1e-12 * np.max(np.abs(r0["acceleration"]))
        assert np.allclose(r1["center_of_mass"], r0["center_of_mass"] @ R.T + t, atol=1e-9)


def test_spin_and_slope_outputs():
    V, F = _icosphere(8, 100.0)
    P = V[:5] * 1.0
    n = P / np.linalg.norm(P, axis=1)[:, None]
    w = 1e-4
    r = pg.polyhedron_gravity((V, F), P, density=2000.0, omega=w, normals=n)
    perp = P.copy()
    perp[:, 2] = 0.0
    assert np.allclose(r["effective_acceleration"], r["acceleration"] + w * w * (perp - np.r_[r["center_of_mass"][:2], 0.0]), atol=1e-18)
    assert np.allclose(r["effective_potential"],
                       r["potential"] - 0.5 * w * w * np.sum((perp - np.r_[r["center_of_mass"][:2], 0.0]) ** 2, axis=1))
    assert np.all(r["slope_deg"] >= 0) and np.all(r["slope_deg"] < 5.0)     # 球の上はほぼ平ら(遠心力の分だけ傾く)
    r0 = pg.polyhedron_gravity((V, F), P, density=2000.0, normals=n)
    assert "effective_acceleration" not in r0 and np.all(r0["slope_deg"] < 2.0)


def test_clip_pieces_add_up_to_the_whole():
    V, F = _icosphere(6, 80.0)
    V = V * np.array([2.0, 1.0, 0.8])
    probe = np.array([[0.0, 0.0, 300.0], [40.0, 5.0, 0.0], [500.0, 50.0, -30.0], [0.0, 0.0, 0.0]])
    for p, n in (([30.0, 0.0, 0.0], [1.0, 0.0, 0.0]), ([10.0, -5.0, 3.0], [0.6, 0.5, -0.3])):
        a = pg.polyhedron_clip_halfspace((V, F), p, n)
        b = pg.polyhedron_clip_halfspace((V, F), p, -np.asarray(n))
        w = pg.polyhedron_gravity((V, F), probe, density=1.0, G=1.0)
        ga = pg.polyhedron_gravity(a, probe, density=1.0, G=1.0)
        gb = pg.polyhedron_gravity(b, probe, density=1.0, G=1.0)
        assert abs(ga["volume"] + gb["volume"] - w["volume"]) < 1e-12 * w["volume"]
        assert np.max(np.abs(ga["acceleration"] + gb["acceleration"] - w["acceleration"])) < 1e-12 * np.max(np.abs(w["acceleration"]))
        assert np.max(np.abs(ga["potential"] + gb["potential"] - w["potential"])) < 1e-12 * np.max(np.abs(w["potential"]))


def test_clip_box_matches_direct_box_and_grid_volume():
    V, F = _box(2.0, 1.0, 0.5)
    h = pg.polyhedron_clip_halfspace((V, F), [1.5, 0.0, 0.0], [1.0, 0.0, 0.0])
    V2, F2 = _box(0.5, 1.0, 0.5, origin=(1.5, 0.0, 0.0))
    P = np.array([[10.0, 0.0, 0.0], [1.7, 0.5, 0.25]])
    a = pg.polyhedron_gravity(h, P, G=1.0)
    b = pg.polyhedron_gravity((V2, F2), P, G=1.0)
    assert np.max(np.abs(a["potential"] - b["potential"])) < 1e-13
    assert np.max(np.abs(a["acceleration"] - b["acceleration"])) < 1e-13
    # 斜めの平面(扇の中心が切り口の外 = 非凸の扇)の体積を格子で数えた値と
    p0, n0 = np.array([3.0, -5.0, 0.1]), np.array([1.0, 0.3, 0.2])
    hv = pg.polyhedron_clip_halfspace((V, F), p0, n0)
    vol = pg.polyhedron_gravity(hv, [[10.0, 10.0, 10.0]], G=1.0)["volume"]
    g1 = np.linspace(0, 2, 401)[:-1] + 0.0025
    g2 = np.linspace(0, 1, 201)[:-1] + 0.0025
    g3 = np.linspace(0, 0.5, 101)[:-1] + 0.0025
    XX, YY, ZZ = np.meshgrid(g1, g2, g3, indexing="ij")
    inside = ((XX - p0[0]) * n0[0] + (YY - p0[1]) * n0[1] + (ZZ - p0[2]) * n0[2]) >= 0
    assert vol == pytest.approx(inside.sum() * 0.005 ** 3, abs=2e-3)


def test_fail_closed():
    V, F = _box(1.0, 1.0, 1.0)
    with pytest.raises(ValueError, match="閉じていない"):
        pg.polyhedron_gravity((V, F[:-1]), [[5.0, 0.0, 0.0]])
    with pytest.raises(ValueError, match="体積が正でない"):
        pg.polyhedron_gravity((V, F[:, ::-1]), [[5.0, 0.0, 0.0]])
    with pytest.raises(ValueError, match="空"):
        pg.polyhedron_gravity((V, F), np.zeros((0, 3)))
    with pytest.raises(ValueError):
        pg.polyhedron_gravity((V, F), [[np.nan, 0.0, 0.0]])
    with pytest.raises(ValueError):
        pg.polyhedron_gravity((V, F), [[5.0, 0.0, 0.0]], density=0.0)
    with pytest.raises(ValueError):
        pg.polyhedron_gravity((V, F), [[5.0, 0.0, 0.0]], omega=-1.0)
    with pytest.raises(ValueError):
        pg.polyhedron_gravity((V, F + 100), [[5.0, 0.0, 0.0]])
    with pytest.raises(ValueError, match="反対側"):
        pg.polyhedron_clip_halfspace((V, F), [5.0, 0.0, 0.0], [1.0, 0.0, 0.0])
    with pytest.raises(ValueError):
        pg.polyhedron_clip_halfspace((V, F), [0.5, 0.0, 0.0], [0.0, 0.0, 0.0])


def test_whole_mesh_on_the_kept_side_is_returned_closed():
    V, F = _box(1.0, 1.0, 1.0)
    Vo, Fo = pg.polyhedron_clip_halfspace((V, F), [-1.0, 0.0, 0.0], [1.0, 0.0, 0.0])
    assert len(Fo) == len(F)
    assert pg.polyhedron_gravity((Vo, Fo), [[5.0, 0.0, 0.0]])["volume"] == pytest.approx(1.0, rel=1e-12)


def test_docstrings_name_the_empty_input_contract():
    for f in (pg.polyhedron_gravity, pg.polyhedron_clip_halfspace):
        assert re.search(r"空の入力(.+)は ValueError で拒否する", f.__doc__), f.__name__
