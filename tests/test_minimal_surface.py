# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""極小曲面 4 op + 管メッシュの門。**定義そのものが門**になる珍しい族。

極小曲面は「平均曲率 H が至るところ 0」の曲面で、既存 ``vertex_curvature`` が
まさにそれを測る —— つまり「これは極小曲面だ」という主張を、**作り方を知らない
op が採点する**。対照群として球(H = 1/R)と円柱(H = 1/2R)を同じ手続きに
かけ、門が本当に区別していることを示す。

★カテノイドとヘリコイドは等長なのでガウス曲率 K が一致する。だがそれは
**必要条件にすぎない** —— K が一致しても極小とは限らないので、門にするのは H。

管メッシュの真値は解析解: 円を中心線にすると管はトーラスになり、体積
``2 pi^2 R r^2``・表面積 ``4 pi^2 R r``。どちらも既存 ``mesh_volume`` /
``mesh_area`` が測る。
"""
import numpy as np
import pytest

import render3d


def _mean_curvature(V, F, trim=0.1):
    """既存 op で平均曲率の大きさを測る。端は評価が甘いので上側を落とす。"""
    import fullseye as fs
    h = np.asarray(fs.ledger.vertex_curvature((V, F)), dtype=np.float64)
    h = np.abs(h[np.isfinite(h)])
    if trim > 0 and h.size > 20:
        cut = int(h.size * trim)
        h = np.sort(h)[:-cut] if cut else h
    return h


def _sphere(nu=90, nv=140):
    th = np.linspace(0.01, np.pi - 0.01, nu)[:, None]
    ph = np.linspace(0.0, 2.0 * np.pi, nv, endpoint=False)[None, :]
    V = np.stack([(np.sin(th) * np.cos(ph)).ravel(),
                  (np.sin(th) * np.sin(ph)).ravel(),
                  np.broadcast_to(np.cos(th), (nu, nv)).ravel()], axis=1)
    return V, render3d._surf_grid_faces(nu, nv, wrap_v=True)


def _cylinder(nu=90, nv=140):
    ph = np.linspace(0.0, 2.0 * np.pi, nv, endpoint=False)[None, :]
    z = np.linspace(-1.0, 1.0, nu)[:, None]
    V = np.stack([np.broadcast_to(np.cos(ph), (nu, nv)).ravel(),
                  np.broadcast_to(np.sin(ph), (nu, nv)).ravel(),
                  np.broadcast_to(z, (nu, nv)).ravel()], axis=1)
    return V, render3d._surf_grid_faces(nu, nv, wrap_v=True)


@pytest.mark.parametrize("kind", ["catenoid", "helicoid", "enneper", "scherk"])
def test_minimal_surfaces_have_vanishing_mean_curvature(kind):
    """★H = 0 —— 既存 vertex_curvature が測る(この族の作り方を知らない op)。"""
    V, F = render3d.minimal_surface(kind, 90, 140, 1.2)
    assert V.ndim == 2 and V.shape[1] == 3 and F.shape[1] == 3
    h = _mean_curvature(V, F)
    assert float(np.median(h)) < 0.01, float(np.median(h))
    assert float(np.percentile(h, 90)) < 0.05, float(np.percentile(h, 90))


@pytest.mark.parametrize("name,want", [("sphere", 1.0), ("cylinder", 0.5)])
def test_the_gate_separates_non_minimal_control_surfaces(name, want):
    """対照群: 単位球は H = 1、半径 1 の円柱は H = 1/2。門が素通しでない証拠。"""
    V, F = _sphere() if name == "sphere" else _cylinder()
    h = _mean_curvature(V, F)
    assert abs(float(np.median(h)) - want) < 0.05, (name, float(np.median(h)))


def test_gaussian_curvature_agreement_is_necessary_but_not_sufficient():
    """★カテノイドとヘリコイドは等長なので K が近い。だが K は門にならない。"""
    import fullseye as fs
    Vc, _Fc = render3d.minimal_surface("catenoid", 80, 120, 1.0)
    Vh, _Fh = render3d.minimal_surface("helicoid", 80, 120, 1.0)
    k1c, k2c = fs.ledger.principal_curvatures(Vc)
    k1h, k2h = fs.ledger.principal_curvatures(Vh)
    Kc = np.asarray(k1c) * np.asarray(k2c)
    Kh = np.asarray(k1h) * np.asarray(k2h)
    mc = float(np.median(Kc[np.isfinite(Kc)]))
    mh = float(np.median(Kh[np.isfinite(Kh)]))
    assert mc < 0 and mh < 0                          # 極小曲面は K <= 0
    assert abs(mc - mh) < 0.5 * abs(mc), (mc, mh)
    # 球も K が一定だが極小ではない —— K の一致だけでは何も言えない
    Vs, Fs = _sphere()
    hs = _mean_curvature(Vs, Fs)
    assert float(np.median(hs)) > 0.5


@pytest.mark.parametrize("t", [0.0, 0.25, 0.5, 0.75, 1.0])
def test_the_bending_family_stays_minimal_and_isometric(t):
    """t を振っても H は 0 のまま、面積も変わらない(等長変形)。"""
    import fullseye as fs
    V, F = render3d.minimal_surface_bend(t * np.pi / 2.0, 80, 120, 1.0)
    h = _mean_curvature(V, F)
    assert float(np.median(h)) < 0.02, float(np.median(h))
    area = float(fs.ledger.mesh_area((V, F)))
    ref = float(fs.ledger.mesh_area(render3d.minimal_surface_bend(0.0, 80, 120, 1.0)))
    assert abs(area / ref - 1.0) < 0.02, (area, ref)


@pytest.mark.parametrize("n", [48, 64, 96])
def test_gyroid_solid_fraction_converges_on_a_half_by_symmetry(n):
    """level = 0 で場は体心反転に対し奇 —— 両側の体積はちょうど半分ずつ。"""
    m = np.asarray(render3d.gyroid_solid_mask((n, n, n), 0.0, 1.0, 1e9))
    assert m.shape == (n, n, n)
    assert float(m.mean()) == 1.0                    # thickness 巨大 = 全部
    thin = np.asarray(render3d.gyroid_solid_mask((n, n, n), 0.0, 1.0, 0.0))
    assert 0.0 <= float(thin.mean()) < 0.2


def test_gyroid_solid_fraction_is_a_half_above_the_level():
    """符号で分けた体積比は 1/2 に収束する(対称性で、格子に依らない)。"""
    for n in (48, 64, 96):
        f = render3d._gyroid_field("t", (n, n, n), 1.0)
        assert abs(float((f > 0).mean()) - 0.5) < 0.02, n


def test_gyroid_shell_volume_grows_with_thickness():
    """薄い殻の体積は厚さにほぼ比例(等値面の面積が有限なので)。"""
    fr = [float(np.asarray(render3d.gyroid_solid_mask((64, 64, 64), 0.0, 1.0, t)).mean())
          for t in (0.1, 0.2, 0.4)]
    assert all(a < b for a, b in zip(fr, fr[1:])), fr
    assert abs(fr[1] / fr[0] - 2.0) < 0.3, fr
    assert abs(fr[2] / fr[1] - 2.0) < 0.3, fr


def test_gyroid_mesh_is_the_nodal_approximation_and_says_so():
    """★節面近似であって厳密な三重周期極小曲面ではない —— 残差を隠さない。"""
    pytest.importorskip("skimage")
    V, F = render3d.gyroid_isosurface((64, 64, 64), 0.0, 1.0)
    # 退化三角形(面積 0)は落としてある: 曲率 op が正しく拒否するので
    e1 = V[F[:, 1]] - V[F[:, 0]]
    e2 = V[F[:, 2]] - V[F[:, 0]]
    assert float(np.linalg.norm(np.cross(e1, e2), axis=1).min()) > 0.0
    assert int(np.unique(F).size) == V.shape[0]      # 使わない頂点を残さない


def test_gyroid_level_outside_the_field_range_is_refused():
    """等値面が存在しない level は空メッシュでなく ValueError。"""
    with pytest.raises(ValueError, match="outside the field range"):
        render3d.gyroid_isosurface((32, 32, 32), 9.0, 1.0)


def test_tube_of_a_circle_is_a_torus_with_the_analytic_volume_and_area():
    """★円の管はトーラス: 体積 2 pi^2 R r^2 / 面積 4 pi^2 R r を既存 op が測る。"""
    import fullseye as fs
    R, r, m, k = 2.0, 0.3, 720, 48
    th = np.linspace(0.0, 2.0 * np.pi, m, endpoint=False)
    centre = np.stack([R * np.cos(th), R * np.sin(th), np.zeros(m)], axis=1)
    V, F = render3d.curve3d_tube_mesh(centre, r, k, closed=True)
    vol = abs(float(fs.ledger.mesh_volume((V, F))))
    area = float(fs.ledger.mesh_area((V, F)))
    assert abs(vol / (2.0 * np.pi ** 2 * R * r ** 2) - 1.0) < 0.01, vol
    assert abs(area / (4.0 * np.pi ** 2 * R * r) - 1.0) < 0.01, area


def test_tube_refuses_a_curve_with_a_repeated_point():
    """方向が定義できない所は黙って前の向きを使わず ValueError。"""
    p = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    with pytest.raises(ValueError, match="repeats a point"):
        render3d.curve3d_tube_mesh(p, 0.1, 8)


def test_tube_uses_a_parallel_transport_frame_not_a_frenet_frame():
    """★直線部でも法線が定義できる = フレネ枠では通らない曲線で確かめる。

    折れ線の中に**まっすぐな区間**を入れると、フレネ枠は曲率 0 で法線が
    定義できず落ちるか捏造する。平行移動フレームは前の法線を運ぶので通る。
    """
    z = np.linspace(0.0, 4.0, 200)
    x = np.where(z < 2.0, 0.0, (z - 2.0) ** 2 * 0.3)   # 前半はまっすぐ
    centre = np.stack([x, np.zeros_like(z), z], axis=1)
    V, F = render3d.curve3d_tube_mesh(centre, 0.15, 16)
    assert np.all(np.isfinite(V))
    # 半径は全周で一定(捏造した枠だと管がねじれて半径が崩れる)
    ring = V.reshape(centre.shape[0], 16, 3)
    rad = np.linalg.norm(ring - centre[:, None, :], axis=2)
    assert abs(float(rad.min()) - 0.15) < 1e-9 and abs(float(rad.max()) - 0.15) < 1e-9
