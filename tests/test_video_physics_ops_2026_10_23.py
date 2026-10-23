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
 9. 公開面 fullseye.ledger 経由でも NaN 入力は(op 自身の検査で)ValueError になる(包み紙は素通し、2026-10-23 の契約)
10. 敵対的レビュー(2026-10-23)の所見: 雑音ゼロの軌跡(残差が離散化の床)は AIC の比較を拒否 / dt > 標本間隔・iters < 1・
    真空・bp の鍵欠落や非有限や質量 0・t_end や dt の非有限・文字列 は全部 ValueError(KeyError / ZeroDivisionError / NaN を出さない)/
    単位違い(ms の t)は歩数の上限で即座に止まる / rss_floor は雑音のある当てはめでは RSS の 1e-3 未満
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
    rng = np.random.default_rng(7)
    PT = sample(P0, V0, 0.3 * V0 / np.linalg.norm(V0), bp)[:, [0, 2]] + rng.normal(0.0, 0.01, (len(T), 2))
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


def test_noise_free_track_is_refused_because_residuals_are_discretisation_not_noise():
    """★ 雑音ゼロの真値に既定の dt = 1e-3 で ΔAIC = +144(推力の推定値は 3e-14 m/s²)が出ていた(2026-10-23 の敵対的レビュー)。
    残差が離散化の床 ``rss_floor`` の 10 倍を下回るときは比較を拒否する。雑音があれば床は RSS の 1e-3 未満で、結果は変わらない。"""
    bp = car()
    PB = sample(P0, V0, (0.0, 0.0, 0.0), bp)[:, [0, 2]]
    for dt in (1e-3, 1.0 / 120.0):
        with pytest.raises(ValueError, match="discretisation floor"):
            B.ballistic_vs_thrust(T, PB, bp, dt=dt)
    rng = np.random.default_rng(3)
    r = B.ballistic_vs_thrust(T, PB + rng.normal(0.0, 0.03, PB.shape), bp, dt=1.0 / 120.0)
    f = r["thrust"]
    assert 0.0 < f["rss_floor"] < 1e-3 * f["rss"], (f["rss_floor"], f["rss"])
    assert f["rss_floor"] == pytest.approx(f["n"] * ((bp["g"] + f["thrust_norm"]) * (1.0 / 120.0) ** 2 / 8.0) ** 2)
    assert -4.0 - 1e-6 <= r["delta_aic"] < 10.0


def test_review_findings_are_value_errors_not_silent_answers():
    """dt > 標本間隔(模型が区分線形になり C_d 0.33 → 3.1 に化けていた)、iters < 1(放物線の初期値をそのまま返していた)、
    真空(C_d が同定不能で初期値のまま cond = inf)、bp の欠落 / NaN / 質量 0(KeyError / NaN の軌跡 / ZeroDivisionError だった)、
    t_end や dt の非有限・文字列、ms で渡した t(2×10⁶ 歩 × 数百回の評価で止まらなかった)は、全部 ValueError で即座に止まる。"""
    import time
    bp = car()
    rng = np.random.default_rng(5)
    P = sample(P0, V0, (0.0, 0.0, 0.0), bp)[:, [0, 2]] + rng.normal(0.0, 0.03, (len(T), 2))
    for fn in (B.drag_fit, B.thrust_fit, B.ballistic_vs_thrust):
        with pytest.raises(ValueError, match="sample spacing"):
            fn(T, P, bp, dt=0.5)
        for it in (0, -5, True, 2.0):
            with pytest.raises(ValueError, match="iters"):
                fn(T, P, bp, iters=it)
        with pytest.raises(ValueError, match="vacuum"):
            fn(T, P, dict(bp, rho=0.0))
        with pytest.raises(ValueError, match="bp"):
            fn(T, P, {})
        with pytest.raises(ValueError, match="bp"):
            fn(T, P, None)
        with pytest.raises(ValueError, match="finite"):
            fn(T, P, dict(bp, g=float("nan")))
        with pytest.raises(ValueError, match="mass"):
            fn(T, P, dict(bp, mass=0.0))
        t0 = time.time()
        with pytest.raises(ValueError, match="units"):
            fn(T * 1000.0, P, bp)                       # ms で渡した t: 歩数の上限で止まる
        assert time.time() - t0 < 2.0
        with pytest.raises(ValueError, match="dt"):
            fn(T, P, bp, dt=float("inf"))
    for bad_t in (float("inf"), float("nan"), "1"):
        with pytest.raises(ValueError):
            B.thrust_ode(P0, V0, (0.0, 0.0, 0.0), bp, bad_t)
    with pytest.raises(ValueError):
        B.thrust_ode(P0, V0, (0.0, 0.0, 0.0), bp, 1.0, float("inf"))
    with pytest.raises(ValueError, match="steps"):
        B.thrust_ode(P0, V0, (0.0, 0.0, 0.0), bp, 1e4, 1e-3)
    for bad_bp in ({}, None, dict(bp, g=float("nan")), dict(bp, mass=0.0), dict(bp, cd=-1.0), dict(bp, cd="cube")):
        with pytest.raises(ValueError):
            B.thrust_ode(P0, V0, (0.0, 0.0, 0.0), bad_bp, 0.01)
    assert B.thrust_ode(P0, V0, (0.0, 0.0, 0.0), dict(bp, rho=0.0), 0.01)["p"].shape == (11, 3)   # 真空の積分は可
    for g in ("9", b"9", True):
        with pytest.raises(ValueError):
            B.time_stretch_from_gravity(g)


def test_public_tier_route_works_and_refuses_nan_at_the_entrance():
    """公開面 ``fullseye.ledger.<名前>`` と opsdrive の台帳から呼べること(登録を 1 つ落とすと静かに消える)、
    NaN は ValueError になること(包み紙は素通しなので、見ているのは op 自身の入口検査)。"""
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
