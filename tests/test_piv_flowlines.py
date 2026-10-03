# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""矢印図と流線(``piv_quiver`` / ``piv_streamlines`` / ``piv_streamline_image``)の門。

門は定理で立てる(絵の好みではなく):

* 剛体回転の流線は円 —— 半径が流線の上で変わらない。双一次補間は線形な場を
  厳密に再現するので、残るのは RK4 の打ち切り誤差だけ(実測 1.2e-6)。
* 発散の無い場の流線は流れ関数 ψ の等高線 —— ψ が流線の上で一定。
* 等間隔配置(Jobard–Lefer 1997)の 2 つの約束: 別の流線どうしは ``d_test``
  より近づかない/動いている格子点はどれも ``(1 + √2/4) * separation`` 以内に
  流線を持つ(予備の種は間隔 ``separation/2`` の格子なので、どの点にも
  ``√2/4 * separation`` 以内に種がある。その種は線を始めたか、``separation``
  以内に既存の線があって捨てられたかのどちらか)。
* 矢印図: 矢印 = ``scale * v``、自動倍率では最長の矢印が間隔の 0.9 倍。
  描いた画素の主軸が場の向きと一致し、矢じりの側が先端にある。
"""
import numpy as np
import pytest

import pivops as P

H = W = 64
_R, _C = np.mgrid[0:H, 0:W].astype(np.float64)
R0 = C0 = 31.5


def _rotation():
    """画面上で時計回りの剛体回転(右側で下向き、上側で右向き)。"""
    return np.stack([_C - C0, -(_R - R0)])


def _cellular(L=16.0):
    """流れ関数 ψ = sin(πc/L) sin(πr/L) の格子状の渦列(発散 0)。"""
    k = np.pi / L
    dy = -k * np.cos(k * _C) * np.sin(k * _R)        # -∂ψ/∂c
    dx = k * np.sin(k * _C) * np.cos(k * _R)         # +∂ψ/∂r
    return np.stack([dy, dx]), (lambda p: np.sin(k * p[:, 1]) * np.sin(k * p[:, 0]))


def _pairs_closer_than(paths, d):
    """別々の流線に属する標本点の対で、距離が ``d`` 未満のものの数(格子で総当たり)。"""
    pts = np.concatenate(paths)
    lid = np.concatenate([np.full(len(p), i) for i, p in enumerate(paths)])
    cell = {}
    for i, (r, c) in enumerate(pts):
        cell.setdefault((int(r // d), int(c // d)), []).append(i)
    bad = 0
    for (kr, kc), idx in cell.items():
        cand = [j for dr in (-1, 0, 1) for dc in (-1, 0, 1) for j in cell.get((kr + dr, kc + dc), ())]
        cand = np.array(cand)
        for i in idx:
            dd = np.hypot(*(pts[cand] - pts[i]).T)
            bad += int(np.count_nonzero((dd < d) & (lid[cand] != lid[i])))
    return bad // 2


# =========================================================================
# 1. 流線 —— 定理の門
# =========================================================================

def test_rigid_rotation_streamlines_are_circles_and_close():
    st = P.piv_streamlines(_rotation())
    assert st["n"] >= 20
    worst = 0.0
    for p in st["paths"]:
        rad = np.hypot(p[:, 0] - R0, p[:, 1] - C0)
        worst = max(worst, float(np.ptp(rad) / rad.mean()))
    assert worst < 1e-4, worst
    # 枠に当たらない内側の円は、どれも閉じた軌道として止まる
    assert st["stop_counts"]["closed"] >= 2 * 10
    assert st["stop_counts"]["max_steps"] == 0


def test_the_stream_function_is_constant_along_every_streamline():
    flow, psi = _cellular()
    st = P.piv_streamlines(flow)
    assert st["n"] >= 40
    worst = max(float(np.ptp(psi(p))) for p in st["paths"] if len(p) > 1)
    # ψ の振れ幅は 2。双一次補間の誤差だけが残る(実測 8e-5)
    assert worst < 1e-3, worst


def test_user_seeds_trace_through_the_seed_in_flow_order():
    """種を渡すと、その点を通る線を上流 → 下流の順で返す。"""
    flow = np.stack([np.zeros((H, W)), np.ones((H, W))])     # 右向き一様
    st = P.piv_streamlines(flow, seeds=[[10.0, 30.0], [40.5, 5.0]])
    assert st["n"] == 2 and len(st["paths"]) == 2 and len(st["seeds"]) == 2
    paths = st["paths"]
    assert paths
    for p, (sr, sc) in zip(paths, st["seeds"]):
        assert np.allclose(p[:, 0], sr, atol=1e-12)          # 水平な直線
        assert np.all(np.diff(p[:, 1]) > 0)                  # 左から右へ
        assert p[0, 1] == pytest.approx(0.0, abs=st["step"]) and p[-1, 1] > W - 1 - st["step"]
    assert st["stop"][0] == ("boundary", "boundary")


# =========================================================================
# 2. 等間隔配置の 2 つの約束
# =========================================================================

@pytest.mark.parametrize("field", ["rotation", "cellular", "saddle"])
def test_evenly_spaced_lines_never_come_closer_than_d_test(field):
    flow = {"rotation": _rotation(), "cellular": _cellular()[0],
            "saddle": np.stack([-(_R - R0), _C - C0])}[field]
    st = P.piv_streamlines(flow)
    assert _pairs_closer_than(st["paths"], st["d_test"] * (1 - 1e-9)) == 0


@pytest.mark.parametrize("field", ["rotation", "cellular", "saddle"])
def test_evenly_spaced_lines_leave_no_gap_wider_than_the_proven_bound(field):
    flow = {"rotation": _rotation(), "cellular": _cellular()[0],
            "saddle": np.stack([-(_R - R0), _C - C0])}[field]
    st = P.piv_streamlines(flow)
    pts = np.concatenate(st["paths"])
    mag = np.hypot(*flow)
    moving = np.argwhere(mag >= 1e-3 * mag.max()).astype(np.float64)
    far = 0.0
    for chunk in np.array_split(moving, 16):
        d = np.sqrt(((chunk[:, None, :] - pts[None, :, :]) ** 2).sum(-1)).min(1)
        far = max(far, float(d.max()))
    bound = st["separation"] * (1.0 + np.sqrt(2.0) / 4.0)
    assert far <= bound * (1 + 1e-9), (far, bound)


def test_a_coarser_separation_draws_fewer_lines():
    flow = _cellular()[0]
    assert P.piv_streamlines(flow, separation=5.0)["n"] < P.piv_streamlines(flow)["n"]


# =========================================================================
# 3. 矢印図
# =========================================================================

def test_auto_scale_makes_the_longest_arrow_nine_tenths_of_the_spacing():
    p0, p1, k = P._quiver_segments(_rotation(), 4, None)
    v = (p1 - p0) / k
    lengths = np.hypot(*(p1 - p0).T)
    assert lengths.max() == pytest.approx(0.9 * 4)
    # 矢印は場そのもの(倍率 k を掛けただけ)
    r, c = p0[:, 0].astype(int), p0[:, 1].astype(int)
    assert np.allclose(v[:, 0], _rotation()[0][r, c]) and np.allclose(v[:, 1], _rotation()[1][r, c])
    # 倍率を固定すると、速い場は長い矢印になる
    _, q1, _ = P._quiver_segments(2.0 * _rotation(), 4, k)
    assert np.allclose(q1 - p0, 2.0 * (p1 - p0))


@pytest.mark.parametrize("deg", [0.0, 37.0, 90.0, 200.0, 311.0])
def test_drawn_arrows_point_the_way_the_field_points(deg):
    """一様な場を描き、描いた画素の主軸と矢じりの側から向きを読み戻す。"""
    t = np.radians(deg)
    # 画面上の角度(x 右・y 上)。行は下向きなので dy = -sin
    flow = np.stack([np.full((16, 16), -np.sin(t)), np.full((16, 16), np.cos(t))])
    # 間隔 16 で 16x16 の格子 → 矢印は格子点 (7, 7) の 1 本だけ。長さ 5 格子 = 40 px
    img = P.piv_quiver(flow, spacing=16, scale=5.0, upsample=8, width=2.0)
    ink = 1.0 - img.mean(axis=2)
    cy = cx = (7 + 0.5) * 8 - 0.5
    y, x = np.mgrid[0:ink.shape[0], 0:ink.shape[1]]
    near = ink > 0.0
    assert near.sum() > 80, "矢印が描かれていない"
    w = ink
    m = w.sum()
    my, mx = (w * y).sum() / m, (w * x).sum() / m
    cov = np.cov(np.stack([(x - mx)[near], -(y - my)[near]]), aweights=w[near])
    ev, evec = np.linalg.eigh(cov)
    ax = evec[:, 1]
    ang = np.degrees(np.arctan2(ax[1], ax[0])) % 180.0
    assert min(abs(ang - deg % 180.0), 180.0 - abs(ang - deg % 180.0)) < 2.0
    # 矢じりの分だけ墨の重心は先端側へ寄る
    shift = np.array([mx - cx, -(my - cy)])
    assert shift @ np.array([np.cos(t), np.sin(t)]) > 0.0


def test_quiver_draws_on_a_background_and_keeps_the_range():
    flow = _rotation()
    bg = P.piv_flow_to_rgbimage(flow).repeat(8, 0).repeat(8, 1)
    img = P.piv_quiver(flow, background=bg)
    assert img.shape == (H * 8, W * 8, 3)
    assert 0.0 <= img.min() and img.max() <= 1.0
    # 矢印の無い所は背景のまま
    assert np.mean(np.isclose(img, bg).all(axis=2)) > 0.6


def test_streamline_image_marks_the_direction_with_arrowheads():
    flow = _rotation()
    a = P.piv_streamline_image(flow, arrows=True)
    b = P.piv_streamline_image(flow, arrows=False)
    assert a.shape == (H * 8, W * 8, 3) and 0.0 <= a.min() and a.max() <= 1.0
    # 矢じりの分だけ濃くなった画素(実測 403 px・33 本)
    assert np.count_nonzero(a.mean(axis=2) < b.mean(axis=2) - 0.3) > 150, "矢じりが描かれていない"


# =========================================================================
# 4. 入力の検査(fail-closed)
# =========================================================================

def test_the_flowline_ops_refuse_bad_input():
    with pytest.raises(ValueError, match="non-finite"):
        bad = _rotation()
        bad[0, 3, 3] = np.nan
        P.piv_streamlines(bad)
    with pytest.raises(ValueError, match="zero everywhere"):
        P.piv_streamlines(np.zeros((2, 8, 8)))
    with pytest.raises(ValueError, match="outside"):
        P.piv_streamlines(_rotation(), seeds=[[-1.0, 3.0]])
    with pytest.raises(ValueError, match="too coarse"):
        P.piv_streamlines(_rotation(), separation=1.0, step=0.5)
    with pytest.raises(ValueError, match="at least 2x2 vectors"):
        P.piv_quiver(np.zeros((2, 1, 1)))
    with pytest.raises(ValueError, match="background"):
        P.piv_quiver(_rotation(), background=np.ones((10, 10)))
    with pytest.raises(ValueError, match="upsample"):
        P.piv_streamline_image(_rotation(), upsample=1)
