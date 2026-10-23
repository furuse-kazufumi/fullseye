# -*- coding: utf-8 -*-
"""映像の物理整合性の op(ballistics: thrust_ode / thrust_fit / drag_fit / aic_from_rss / ballistic_vs_thrust /
time_stretch_from_gravity)の門。実行: ``py -3.11 -m pytest tests/test_video_physics_ops_2026_10_23.py``

門の一覧(数字は全部この場で計算した真値との比較):
 1. thrust_ode は真空で閉形式 p₀ + v₀ t + ½ (a_T − g ẑ) t² と 1e-9、推力 0 なら flight_ode(ω = 0)と 1e-12
 2. 推力つきの真値の軌跡から thrust_fit は a_T を 1e-5、C_d を 1e-3 で戻す(3-D と平面の両方)
 3. 推力 0 の真値では thrust_norm ≤ 1e-5、drag_fit の C_d は 1e-4
 4. 入れ子の保証: ballistic_vs_thrust の ΔAIC は雑音があっても −2Δk 以上(推力側が弾道側より悪くならない)
 5. 雑音だけ(弾道)では ΔAIC < 10、推力 2 m/s² なら ΔAIC ≥ 10(op は判定を返さず、閾値は呼び手)
 6. aic_from_rss の式と拒否(RSS ≤ 0・n ≤ k・非有限)
 7. time_stretch_from_gravity の閉形式(k 倍に引き延ばした時刻で放物線を当てると k が戻る)と拒否
 8. 空の入力・NaN・時刻が増えない・平面でも 3-D でもない形は ValueError(fail-closed)
 9. 包み紙(fullseye.apply)経由でも NaN 入力は入口で拒否される(2026-10-23 の契約)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ballistics as B  # noqa: E402

G = B.G
T = np.arange(0.0, 2.0, 1.0 / 30.0)


def car():
    return B.ball_params(radius=math.sqrt(2.2 / math.pi), mass=1900.0, cd=0.30, cl=0.0, rho=1.2)


def sample(p0, v0, thrust, bp, t=T):
    f = B.thrust_ode(p0, v0, thrust, bp, float(t[-1]) + 1e-3, 1e-3)
    return np.column_stack([np.interp(t, f["t"], f["p"][:, k]) for k in range(3)])


P0, V0 = np.array([0.0, 0.0, 0.8]), np.array([16.0, 0.0, 12.0])
A_T = np.array([3.0, 0.0, 2.0])


def test_thrust_ode_matches_closed_form_in_vacuum_and_flight_ode_without_thrust():
    bp = car()
    vac = dict(bp, rho=0.0)
    f = B.thrust_ode(P0, V0, A_T, vac, 2.0, 1e-3)
    closed = P0 + f["t"][:, None] * V0 + 0.5 * f["t"][:, None] ** 2 * (A_T - np.array([0.0, 0.0, bp["g"]]))
    assert np.abs(f["p"] - closed).max() < 1e-9
    a = B.thrust_ode(P0, V0, (0.0, 0.0, 0.0), bp, 2.0, 1e-3)["p"]
    b = B.flight_ode(P0, V0, (0.0, 0.0, 0.0), bp, 2.0, 1e-3)["p"]
    assert np.abs(a - b).max() < 1e-12
    assert f["t"].shape == (2001,) and f["p"].shape == (2001, 3) and f["v"].shape == (2001, 3)


@pytest.mark.parametrize("planar", [False, True])
def test_thrust_fit_recovers_the_truth(planar):
    bp = car()
    P = sample(P0, V0, A_T, bp)
    obs = P[:, [0, 2]] if planar else P
    f = B.thrust_fit(T, obs, bp, dt=1.0 / 120.0)
    assert np.linalg.norm(f["thrust"] - A_T) < 1e-5, f["thrust"]
    assert abs(f["cd"] - 0.30) < 1e-3, f["cd"]
    assert f["k"] == (7 if planar else 10) and f["n"] == (2 if planar else 3) * len(T) and f["dims"] == (2 if planar else 3)
    assert f["thrust"][1] == 0.0 if planar else True


def test_no_thrust_truth_gives_zero_thrust_and_drag_fit_recovers_cd():
    bp = car()
    P = sample(P0, V0, (0.0, 0.0, 0.0), bp)
    f = B.thrust_fit(T, P[:, [0, 2]], bp, dt=1.0 / 120.0)
    assert f["thrust_norm"] <= 1e-5, f["thrust_norm"]
    d = B.drag_fit(T, P[:, [0, 2]], bp, dt=1.0 / 120.0)
    assert abs(d["cd"] - 0.30) < 1e-4 and d["k"] == 5 and float(np.linalg.norm(d["thrust"])) == 0.0


def test_nested_models_delta_aic_is_bounded_below_and_follows_the_truth():
    bp = car()
    rng = np.random.default_rng(2026_10_23)
    PB = sample(P0, V0, (0.0, 0.0, 0.0), bp)[:, [0, 2]]
    PT = sample(P0, V0, 2.0 * V0 / np.linalg.norm(V0), bp)[:, [0, 2]]
    deltas = []
    for _ in range(5):
        r = B.ballistic_vs_thrust(T, PB + rng.normal(0.0, 0.04, PB.shape), bp, dt=1.0 / 120.0)
        deltas.append(r["delta_aic"])
        assert r["delta_aic"] < 10.0, r["delta_aic"]
        assert r["ballistic"]["k"] == 5 and r["thrust"]["k"] == 7
    # 入れ子: 推力側は弾道側の解から出発するので RSS_推力 ≤ RSS_弾道、よって ΔAIC ≥ −2Δk = −4(丸めの分だけ緩める)
    assert min(deltas) >= -4.0 - 1e-6, deltas
    assert max(deltas) < 10.0, deltas
    r = B.ballistic_vs_thrust(T, PT + rng.normal(0.0, 0.04, PT.shape), bp, dt=1.0 / 120.0)
    assert r["delta_aic"] >= 10.0, r["delta_aic"]
    assert abs(r["thrust_norm"] - 2.0) < 0.3, r["thrust_norm"]
    assert r["aic_ballistic"] - r["aic_thrust"] == pytest.approx(r["delta_aic"])


def test_no_verdict_is_bundled_only_the_aic_difference():
    """op は判定を返さない(閾値は呼び手)。返るのは 2 つの当てはめと AIC の差だけ。"""
    bp = car()
    PT = sample(P0, V0, 0.3 * V0 / np.linalg.norm(V0), bp)[:, [0, 2]]
    r = B.ballistic_vs_thrust(T, PT, bp, dt=1.0 / 120.0)
    assert set(r) == {"ballistic", "thrust", "aic_ballistic", "aic_thrust", "delta_aic", "thrust_norm"}
    assert r["delta_aic"] > 0 and r["thrust"]["k"] == r["ballistic"]["k"] + 2


def test_aic_from_rss_formula_and_refusals():
    assert B.aic_from_rss(2.0, 10, 3) == pytest.approx(10 * math.log(0.2) + 6.0)
    for bad in [(0.0, 10, 3), (-1.0, 10, 3), (float("nan"), 10, 3), (1.0, 3, 3), (1.0, 2, 3), (1.0, 10, 0)]:
        with pytest.raises(ValueError):
            B.aic_from_rss(*bad)


@pytest.mark.parametrize("k", [0.5, 1.0, 1.25, 2.0, 4.0])
def test_time_stretch_is_recovered_from_the_fitted_gravity(k):
    bp = car()
    P = sample(P0, V0, (0.0, 0.0, 0.0), dict(bp, rho=0.0))
    par = B.fit_parabola(T * k, P)                 # 時刻を k 倍に引き延ばした映像
    r = B.time_stretch_from_gravity(par["g"])
    assert r["k"] == pytest.approx(k, rel=1e-9) and r["log_k"] == pytest.approx(math.log(k), abs=1e-9)
    assert r["g_ref"] == G and r["g_fit"] == pytest.approx(G / k ** 2, rel=1e-9)


def test_time_stretch_refuses_non_positive_or_non_finite_gravity():
    for g in (0.0, -9.8, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            B.time_stretch_from_gravity(g)
    with pytest.raises(ValueError):
        B.time_stretch_from_gravity(9.8, g_ref=0.0)


def test_degenerate_inputs_are_refused():
    bp = car()
    P = sample(P0, V0, A_T, bp)
    with pytest.raises(ValueError):
        B.thrust_ode(P0, V0, [], bp, 1.0)
    with pytest.raises(ValueError):
        B.thrust_ode(P0, V0, A_T, bp, -1.0)
    for fn in (B.thrust_fit, B.drag_fit, B.ballistic_vs_thrust):
        with pytest.raises(ValueError):
            fn(np.array([]), np.zeros((0, 3)), bp)
        with pytest.raises(ValueError):
            fn(T[:5], P[:5], bp)                          # 8 点未満
        with pytest.raises(ValueError):
            fn(T[::-1], P, bp)                             # 時刻が増えない
        bad = P.copy()
        bad[3, 1] = float("nan")
        with pytest.raises(ValueError):
            fn(T, bad, bp)
        with pytest.raises(ValueError):
            fn(T, P[:, :1], bp)                            # (N, 1) は平面でも 3-D でもない


def test_public_tier_route_works_and_refuses_nan_at_the_entrance():
    """公開面 ``fullseye.ledger.<名前>`` と opsdrive の台帳から呼べること(登録を 1 つ落とすと静かに消える)、
    NaN は入口で ValueError になること。"""
    import fullseye as fs
    import opsdrive
    bp = car()
    P = sample(P0, V0, A_T, bp)
    for name in ("thrust_ode", "thrust_fit", "drag_fit", "aic_from_rss", "ballistic_vs_thrust", "time_stretch_from_gravity"):
        assert hasattr(fs.ledger, name), name
        assert name in opsdrive.OPSDRIVE and opsdrive.OPSDRIVE[name]["func"] is getattr(B, name), name
    out = fs.ledger.thrust_fit(T, P, bp, dt=1.0 / 120.0)
    assert np.linalg.norm(np.asarray(out["thrust"]) - A_T) < 1e-5
    assert fs.ledger.time_stretch_from_gravity(G / 4.0)["k"] == pytest.approx(2.0)
    bad = P.copy()
    bad[0, 0] = float("nan")
    with pytest.raises(ValueError):
        fs.ledger.thrust_fit(T, bad, bp)
