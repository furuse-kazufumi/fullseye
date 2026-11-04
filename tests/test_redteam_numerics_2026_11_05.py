"""敵対的検証 2026-11-05(numerics): 長さ・長さ² の絶対の床と、中心化しない当てはめ。

どの門も「真値(閉形式)」か「入力を並進・拡大しても答えが同じ動きをする」不変量で比べる。
尺度は 1e6〜1e-7 を渡り、修正前は少なくとも 1 つの尺度で落ちていた(報告に記載)。
"""
from __future__ import annotations

import numpy as np
import pytest

import measure

# ── N8 / N6: measure.fit_ellipse / fit_circle / fit_line ─────────────────────


def _ellipse_points(ra, rb, ang_deg, cy, cx, n=48):
    t = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    ph = np.radians(ang_deg)
    x = ra * np.cos(t) * np.cos(ph) - rb * np.sin(t) * np.sin(ph)
    y = ra * np.cos(t) * np.sin(ph) + rb * np.sin(t) * np.cos(ph)
    return np.column_stack([cy + y, cx + x])


CENTRES = [(0.0, 0.0), (700.0, 500.0), (8000.0, 6000.0), (16000.0, 12000.0)]


@pytest.mark.parametrize("cy,cx", CENTRES)
def test_n8_fit_ellipse_is_translation_invariant(cy, cx):
    # 真値: ra=5, rb=4, 20°(雑音なし)。修正前は (8000, 6000) で 5.119 / 3.912 / 21.94°。
    r = measure.fit_ellipse(_ellipse_points(5.0, 4.0, 20.0, cy, cx))
    assert r["ra"] == pytest.approx(5.0, abs=1e-8)
    assert r["rb"] == pytest.approx(4.0, abs=1e-8)
    assert r["angle_deg"] == pytest.approx(20.0, abs=1e-6)
    assert r["cy"] == pytest.approx(cy, abs=1e-8)
    assert r["cx"] == pytest.approx(cx, abs=1e-8)


@pytest.mark.parametrize("s", [1e3, 1.0, 1e-4, 1e-7])
def test_n8_fit_ellipse_scales_with_input(s):
    r = measure.fit_ellipse(_ellipse_points(3.0 * s, 1.0 * s, -35.0, 2.0 * s, -1.0 * s))
    assert r["ra"] / s == pytest.approx(3.0, rel=1e-9)
    assert r["rb"] / s == pytest.approx(1.0, rel=1e-9)
    assert r["angle_deg"] == pytest.approx(-35.0, abs=1e-6)


@pytest.mark.parametrize("off", [0.0, 1e3, 1e5, 1e6])
def test_n6_fit_circle_is_translation_invariant(off):
    # 修正前: off=1e6 で r = 2.00003。
    t = np.linspace(0.0, 2.0 * np.pi, 64, endpoint=False)
    pts = np.column_stack([off + 2.0 * np.sin(t), off + 2.0 * np.cos(t)])
    r = measure.fit_circle(pts)
    assert r["r"] == pytest.approx(2.0, abs=1e-9)
    assert r["cy"] == pytest.approx(off, abs=1e-9)
    assert r["cx"] == pytest.approx(off, abs=1e-9)


@pytest.mark.parametrize("s", [1e-6, 4e-7, 1e-7, 1e-10])
def test_n6_fit_circle_small_radius_is_not_degenerate(s):
    # 修正前: 半径 2·4e-7 = 8e-7 から下は r² <= 1e-12 の絶対の床で ValueError。
    t = np.linspace(0.0, 2.0 * np.pi, 64, endpoint=False)
    pts = np.column_stack([2.0 * s * np.sin(t), 2.0 * s * np.cos(t)])
    assert measure.fit_circle(pts)["r"] / s == pytest.approx(2.0, rel=1e-9)


def test_n6_fit_line_short_segment_is_not_coincident():
    # 兄弟: fit_line の s[0] <= 1e-12 の絶対の床(長さ 1e-13 の線分を「一致点」と捨てていた)。
    s = 1e-13
    pts = np.column_stack([np.linspace(0, 1, 5) * s, np.linspace(0, 1, 5) * s])
    assert measure.fit_line(pts)["angle_deg"] == pytest.approx(45.0, abs=1e-9)


def test_n6_coincident_points_still_rejected():
    pts = np.full((6, 2), 1234.5)
    for fit in (measure.fit_line, measure.fit_circle, measure.fit_ellipse):
        with pytest.raises(ValueError):
            fit(pts)


# ── N5: superquadric.fit_superquadric ─────────────────────────────────────────


def _ellipsoid_cloud(noise=0.0):
    rng = np.random.default_rng(0)
    d = rng.standard_normal((400, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    P = np.array([1.0, -1.0, 2.0]) + d * np.array([2.0, 1.5, 1.0])
    return P + noise * rng.standard_normal(P.shape)


@pytest.mark.parametrize("s", [1e3, 1.0, 1e-4, 1e-6])
def test_n5_fit_superquadric_recovers_truth_at_any_scale(s):
    # 真値: 楕円体 a=(2,1.5,1)、eps=(1,1)、中心 (1,-1,2)(表面上の厳密点)。
    # 修正前は s <= 1e-4 で gtol が初回評価で満たされ、PCA 初期値 1.979/1.495/1.001 を返した。
    import superquadric as sq
    r = sq.fit_superquadric(_ellipsoid_cloud() * s)
    assert np.sort(r["a"])[::-1] / s == pytest.approx([2.0, 1.5, 1.0], abs=1e-6)
    assert r["t"] / s == pytest.approx([1.0, -1.0, 2.0], abs=1e-6)
    assert r["eps"] == pytest.approx([1.0, 1.0], abs=1e-6)


def test_n5_fit_superquadric_same_solution_for_s1_and_s1e6():
    # 雑音ありの点群(解は真値と少しずれる)でも、s=1 と s=1e-6 で同じ解・残差は s³ 倍。
    import superquadric as sq
    P = _ellipsoid_cloud(noise=0.02)
    r1 = sq.fit_superquadric(P)
    r6 = sq.fit_superquadric(P * 1e-6)
    assert r6["a"] / 1e-6 == pytest.approx(r1["a"], rel=1e-6)
    assert r6["t"] / 1e-6 == pytest.approx(r1["t"], abs=1e-6)
    assert r6["eps"] == pytest.approx(r1["eps"], abs=1e-6)
    assert r6["residual"] / 1e-18 == pytest.approx(r1["residual"], rel=1e-5, abs=0)
    # 返り値の residual は superquadric_residual と同じ量(元の単位)。approx の既定 abs=1e-12 は
    # 1e-21 の量を何とでも一致させるので abs=0 を明示する。
    assert r6["residual"] == pytest.approx(
        sq.superquadric_residual(P * 1e-6, r6["a"], r6["eps"], r6["R"], r6["t"]), rel=1e-9, abs=0)


def test_n5_superquadric_residual_scales_as_length_cubed():
    # 兄弟: superquadric_residual の体積補正 sqrt(max(a1a2a3, 1e-12)) の絶対の床。
    import superquadric as sq
    P = _ellipsoid_cloud(noise=0.02)
    a, eps, R, t = np.array([2.0, 1.5, 1.0]), (1.0, 1.0), np.eye(3), np.array([1.0, -1.0, 2.0])
    r1 = sq.superquadric_residual(P, a, eps, R, t)
    for s in (1e-3, 1e-6):
        rs = sq.superquadric_residual(P * s, a * s, eps, R, t * s)
        assert rs / s ** 3 == pytest.approx(r1, rel=1e-9, abs=0)


def test_n5_fit_superquadric_coincident_points_rejected():
    import superquadric as sq
    with pytest.raises(ValueError):
        sq.fit_superquadric(np.ones((10, 3)))
