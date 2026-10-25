# -*- coding: utf-8 -*-
"""レンズの収差の動く 3-D(examples/anim3d_lens_aberrations.py)の門。

例の中の検査(3 次の式と実光線の照合・アクロマート・PNG の往復)は ``--quick`` で走らせる。
ここでは、例が頼っている部品を **例の外の真値** で確かめる:

* 光線の棒の組(``Rays``)が、op の点を結ぶ線分にちょうど重なる(はみ出さない・隙間が無い)。
* 四元数 ``quat_x_to`` が x 軸を光線の向きへ回す。系 → 世界の置換 ``s2w`` が鏡映でなく回転。
* 2 本の直線の最接近点(``crossing``)が、交わる 2 直線の交点を厳密に返す。
* 帯の④の種類別の地図(``zmap``)が、``wavefront_from_opd`` の係数の規約(match3d の基底)と同じ。
* アクロマートの R3 で F 線と C 線の近軸の焦点がそろい、単レンズの焦点が厚肉レンズの閉形式と一致する。
* 収差が大きすぎる瞳では回折の PSF を作らず(``psf_safe`` が None)、幾何の PSF(光線の密度 ⊗ Airy)に切り替える。
  幾何の PSF は、回折の PSF も作れる重なりの領域で集中半径が 12 % 以内。
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "examples"))
sys.path.insert(0, ROOT)

import anim3d_lens_aberrations as A  # noqa: E402
import fullseye as fs  # noqa: E402


def _rot(q):
    return fs.pocviewer._quat_matrix(np.asarray(q, float))


def test_ray_pieces_tile_each_segment_exactly():
    """長さの変わる線分(コマごとに 30〜75)を、長さ L0 の棒の組でちょうど覆う。"""
    T = 7
    P = np.zeros((T, 1, 2, 3))
    L = np.linspace(30.0, 75.0, T)
    d = np.array([0.8, 0.0, 0.6])
    P[:, 0, 1] = L[:, None] * d + [1.0, 2.0, 3.0]
    P[:, 0, 0] = [1.0, 2.0, 3.0]
    R = A.Rays(P, np.ones((1, 3)), "t")
    xyz, quat = R.poses()
    L0 = R.meta[0][4]
    assert abs(L0 - 30.0) < 1e-12 and len(R.meta) == 3            # ceil(75 / 30) = 3 本
    for k in range(T):
        starts, ends = [], []
        for b, (_i, _j, _m, _k, l0) in enumerate(R.meta):
            u = _rot(quat[k, b]) @ [1.0, 0.0, 0.0]
            assert np.allclose(u, d, atol=1e-12)                    # 棒の向き = 線分の向き
            s0 = float((xyz[k, b] - P[k, 0, 0]) @ d)
            assert np.allclose(xyz[k, b], P[k, 0, 0] + s0 * d, atol=1e-9)   # 線分の上
            starts.append(s0)
            ends.append(s0 + l0)
        starts, ends = np.array(starts), np.array(ends)
        assert abs(starts.min()) < 1e-9 and abs(ends.max() - L[k]) < 1e-9   # 端から端まで、はみ出さない
        order = np.argsort(starts)
        assert np.all(starts[order][1:] <= ends[order][:-1] + 1e-9)        # 隙間が無い


def test_quaternion_turns_x_onto_the_ray_and_s2w_is_a_rotation():
    rng = np.random.default_rng(3)
    u = rng.normal(size=(50, 3))
    u[:, 0] = np.abs(u[:, 0]) + 0.05                              # 光は +X へ進む
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    q = A.quat_x_to(u)
    got = np.einsum("nij,j->ni", _rot(q), [1.0, 0.0, 0.0])
    assert np.max(np.abs(got - u)) < 1e-12
    M = np.stack([A.s2w(e) for e in np.eye(3)], 1)
    assert abs(np.linalg.det(M) - 1.0) < 1e-12 and np.allclose(M @ M.T, np.eye(3))


def test_crossing_returns_the_intersection_of_two_meeting_lines():
    X = np.array([0.3, -1.2, 47.0])
    D1, D2 = np.array([0.0, 0.1, 1.0]), np.array([0.02, -0.07, 1.0])
    got = A.crossing(X - 30 * D1, D1, X - 12 * D2, D2)
    assert np.max(np.abs(got - X)) < 1e-9


def test_zmap_uses_the_same_zernike_convention_as_wavefront_from_opd():
    import match3d
    z = {(2, 0): 0.3, (2, 2): -0.2, (2, -2): 0.1, (3, 1): 0.25, (3, -1): -0.4, (4, 0): 0.15}
    D = 24
    g = (np.arange(D) + 0.5) / D * 2 - 1
    X, Y = np.meshgrid(g, -g)
    r, th = np.hypot(X, Y), np.arctan2(Y, X)
    B, idx = match3d._zernike_eval(np.minimum(r, 1.0), th, 4)
    ref = sum(c * B[idx.index(k)] for k, c in z.items()).reshape(D, D)
    got = sum(np.nan_to_num(A.zmap(z, (key,), D)) for _k, key in A.ZKEYS)
    inside = r <= 1
    assert np.max(np.abs(got[inside] - ref[inside])) < 1e-12
    # 往復: その波面を wavefront_from_opd と同じ当てはめに通すと係数が戻る
    back = match3d._fit_zernike_points(X[inside], Y[inside], ref[inside], 4)
    for k, c in z.items():
        assert abs(back[k] - c) < 1e-9


def test_achromat_and_singlet_focus_against_closed_forms():
    R3 = A.achromat_r3()
    s2 = A.achromat(R3)
    assert abs(A.bfl_at(s2, A.WL_F) - A.bfl_at(s2, A.WL_C)) < 1e-6
    s1 = A.singlet()
    for wl in (0.45, A.WL_D, 0.68):
        n = fs.refractive_index("N-BK7", wl)
        assert abs(A.bfl_at(s1, wl) - (51.68 / (n - 1) - 9.0 / n)) < 1e-9
    # 薄肉の解からの出発点が正しい: 2 枚の屈折力の比は −V2/V1 に近い(アクロマートの条件 φ1/V1 + φ2/V2 = 0)
    n1, n2 = fs.refractive_index("N-BK7", A.WL_D), fs.refractive_index("N-SF2", A.WL_D)
    phi1 = (n1 - 1) * 2 / A.ACH_R1
    phi2 = (n2 - 1) * (-1 / A.ACH_R1 - 1 / R3)
    assert -0.62 < phi2 / phi1 < -0.42


def test_a_wavefront_too_steep_to_sample_gives_null_not_a_psf():
    assert A.psf_safe(A.singlet(20.0), 0.0) is None              # f/2.5: W040 ≈ 73 波長
    ok = A.psf_safe(A.singlet(3.0), 0.0)
    assert ok is not None and 0.9 < ok["strehl"] <= 1.0 + 1e-9


def test_geometric_psf_matches_the_diffraction_psf_where_both_exist():
    """幾何の PSF(光線の密度 ⊗ Airy)は、回折の PSF も作れる重なりの領域で集中半径が 12 % 以内。"""
    for system, field in ((A.singlet(14.0), 0.0), (A.descartes(), 4.0)):
        assert A.psf_safe(system, field) is not None              # 重なりの領域(回折の PSF がまだ作れる)
        r50, r80 = A.geo_vs_diffraction(system, field)
        assert abs(r50 - 1) < 0.12 and abs(r80 - 1) < 0.12, (field, r50, r80)


def test_geometric_psf_conserves_energy_and_tracks_the_spot():
    """和 = 1、重心が光線の重みつき重心に一致(画素の半分以内)、輪の重みの和 = 瞳の面積(1)。"""
    g = A.geo_rays(A.descartes(), 10.0)
    assert abs(g["w"].sum() - 1.0) < 1e-12
    pitch = 2.6 * float(np.abs(g["xy"]).max()) / 120
    G = A.geo_psf(g, 120, 120, pitch)
    assert abs(G.sum() - 1.0) < 1e-12 and np.all(G >= 0)
    y = -(np.arange(120) - 59.5) * pitch                           # 行 = −y
    cy = float((G.sum(1) * y).sum())
    ty = float((g["w"] * g["xy"][:, 1]).sum() / g["w"].sum())
    assert abs(cy - ty) < 0.5 * pitch, (cy, ty, pitch)


def test_the_regime_switch_is_a_real_op_refusal_not_a_bug():
    """コマ 10° で回折の PSF が無いのは、op が 512 点の瞳の格子で折り返しを断るから(理由の文に格子の数が出る)。"""
    with pytest.raises(ValueError, match="aliased"):
        fs.psf_field_grid(A.descartes(), fields=(10.0,), oversample=3)
    assert A.fmt_fc(0.0).startswith("< 1e-13 mm") and A.fmt_fc(2e-6) == "2.0e-06 mm"


@pytest.mark.timeout(600)
def test_the_example_passes_its_own_gates_quick(capsys):
    assert A.main(["--quick"]) == 0
    out = capsys.readouterr().out
    assert "PASS" in out and "限界" in out
