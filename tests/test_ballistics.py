"""ballistics の門(跳ねる球・摩擦・ひも)。実行: ``PYTHONPATH=. py -3.11 -m pytest tests/test_ballistics.py -q``。

数値はすべて try17.py で測った値(閉形式との一致・定理の保存量・実測の周期と snap 時刻)。

門の一覧:
 1. ball_params の既定値(ITTF 球)と慣性 2/3・2/5、不正値の拒否
 2. impact_params の範囲(0 ≤ e ≤ 1、μ ≥ 0)
 3. flight_vacuum の形(スカラ t → (3,)、配列 t → (N, 3))と z = z₀ + v_z t − ½ g t²
 4. flight_ode(rho = 0)= flight_vacuum(1e-12)、時刻格子は 0..t_end を dt 刻みで両端含む
 5. 抗力だけ(g = 0、ω = 0)なら速さは単調減少、加速度は v と反平行
 6. マグヌス力は v にも ω にも直交、大きさ ½ρC_L A|v|²/m
 7. magnus_lift_coefficient: S = 0 で 0、S = 1 で 1/3、S → ∞ で 0.5、ベクトル化
 8. bounce の定理(乱数 500 本): 接触点まわりの角運動量保存(1e-12)、運動エネルギー非増加、v_z' = −e v_z、
    grip/slip の両領域が出る、grip 後の接触点の滑りは 0
 9. μ = 0 なら接線速度と回転は不変、法線だけ −e 倍
10. 離れていく球(v·n ≥ 0)は regime "none" で状態不変
11. 無回転の滑り球が grip する古典解: 中実球は水平速度 5/7 倍、薄殻は 3/5 倍
12. apex_sequence = e^{2k} h₀、bounce_total_time = √(2h₀/g)(1 + e)/(1 − e)、不正値の拒否
13. 落として跳ねる列(h₀ = 0.305、e = 0.88、真空): 頂点高さが閉形式と 1e-6、接触 ≥ 40 回、rest_t が閉形式と 0.01、
    卓の下に沈まない
14. restitution_from_apexes / restitution_from_intervals が e = 0.88 を戻す(1e-5 / 1e-6)、不正入力の拒否
15. fit_parabola が真空の標本から p₀, v₀, g を 1e-9 で戻す(rms < 1e-12)、3 点未満の拒否
16. table_xy: 卓の外に落ちる球は接触せず z = r を通り抜ける、table_xy = None なら跳ねる
17. トップスピンの打球: 0.6 s までに接触はちょうど 1 回、regime "grip"、跳ね返りの v_z > 0
18. 滑りの停止距離 v₀²/(2μg)、μ の逆算の往復、斜面の滑り出し角 atan μ、不正値の拒否
19. roll_slide_state: v_t = r ω × n なら転がり(滑り 0)、それ以外は滑り
20. pendulum_period = 2π√(L/g)、不正値の拒否
21. 固定手元の小振幅振り子: |p − h| ≤ L + 1e-9、張力 ≥ 0、snap 無し、エネルギーの peak-to-peak < 1e-4 J、
    x の零交差から測る周期が 2π√(L/g)(1 + θ²/16) と 0.5 %
22. 真上に投げた玉のひもが張る瞬間(snap): ちょうど 1 回(≈ 0.612 s)、失うエネルギー ½ m v_r² ≈ 0.045 J、
    その後は球面上に留まる
23. 動く手元 h(t) = (0, 0, 0.5 t) でも |p − h| ≤ L と張力 ≥ 0、初期状態が |p₀ − h| > L なら ValueError
24. cup_catch_check: 中心・低速・皿のすぐ上なら捕球、横ずれ / 速すぎ / 皿の下なら不捕球、不正な半径の拒否
 +. (xfail、既知の不具合)皿より大きい玉(cup_radius < ball_radius)が中心にあると caught=True になる
"""
from __future__ import annotations

import numpy as np
import pytest

import ballistics as B

NZ = np.array([0.0, 0.0, 1.0])


def _kinetic(bp: dict, v, w) -> float:
    """並進 + 回転の運動エネルギー ½mv² + ½Iω²。"""
    v = np.asarray(v, float)
    w = np.asarray(w, float)
    return 0.5 * bp["mass"] * float(v @ v) + 0.5 * bp["inertia"] * float(w @ w)


# ─────────────────────────────── 1-2 表 ───────────────────────────────

def test_ball_params_defaults_and_inertia():
    """既定 = 直径 40 mm・2.7 g の薄殻(I = 2/3 m r²)、shell=False で中実(2/5)、面積 πr²、不正値は ValueError。"""
    bp = B.ball_params()
    assert bp["radius"] == 0.02
    assert bp["mass"] == 0.0027
    assert bp["shell"] is True
    assert bp["inertia"] == pytest.approx(2.0 / 3.0 * 0.0027 * 0.02 ** 2, rel=1e-15)
    assert bp["area"] == pytest.approx(np.pi * 0.02 ** 2, rel=1e-15)
    assert bp["cl"] is None
    solid = B.ball_params(shell=False)
    assert solid["inertia"] == pytest.approx(2.0 / 5.0 * 0.0027 * 0.02 ** 2, rel=1e-15)
    assert B.ball_params(cl=0.3)["cl"] == 0.3
    for kw in ({"radius": 0.0}, {"radius": -0.01}, {"mass": 0.0}, {"mass": -1.0}, {"cd": -0.1}, {"cl": -0.1}):
        with pytest.raises(ValueError):
            B.ball_params(**kw)


def test_impact_params_range():
    """0 ≤ e ≤ 1 と μ ≥ 0 の外は ValueError、内側は float で返る。"""
    ip = B.impact_params(0.9, 0.25)
    assert ip == {"e": 0.9, "mu": 0.25}
    assert B.impact_params(0.0, 0.0) == {"e": 0.0, "mu": 0.0}
    assert B.impact_params(1.0, 2.0)["e"] == 1.0
    for e, mu in ((-0.01, 0.2), (1.01, 0.2), (0.5, -0.01), (0.5, float("nan"))):
        with pytest.raises(ValueError):
            B.impact_params(e, mu)


# ─────────────────────────────── 3-7 飛翔 ───────────────────────────────

def test_flight_vacuum_shapes_and_closed_form():
    """スカラ t は (3,)、配列 t は (N, 3)。z = z₀ + v_z t − ½ g t²、x, y は等速。"""
    p0 = np.array([0.1, -0.2, 1.0])
    v0 = np.array([2.0, 0.5, 3.0])
    one = B.flight_vacuum(p0, v0, 0.3)
    assert one.shape == (3,)
    assert one == pytest.approx(p0 + v0 * 0.3 - np.array([0, 0, 0.5 * B.G * 0.3 ** 2]), abs=1e-15)
    t = np.linspace(0.0, 0.6, 7)
    many = B.flight_vacuum(p0, v0, t)
    assert many.shape == (7, 3)
    np.testing.assert_allclose(many[:, 0], p0[0] + v0[0] * t, atol=1e-15)
    np.testing.assert_allclose(many[:, 1], p0[1] + v0[1] * t, atol=1e-15)
    np.testing.assert_allclose(many[:, 2], p0[2] + v0[2] * t - 0.5 * B.G * t ** 2, atol=1e-15)
    assert B.flight_vacuum(p0, v0, t, g=0.0)[:, 2] == pytest.approx(p0[2] + v0[2] * t, abs=1e-15)
    with pytest.raises(ValueError):
        B.flight_vacuum([0, 0], v0, 0.1)


def test_flight_ode_vacuum_matches_closed_form():
    """rho = 0 の RK4 は真空の閉形式と 1e-12 で一致(等加速度なら RK4 は厳密)。時刻格子は 0..t_end を dt 刻みで両端含む。"""
    bv = B.ball_params(rho=0.0)
    p0, v0 = [0.0, 0.0, 1.0], [2.0, 0.5, 3.0]
    f = B.flight_ode(p0, v0, [0, 0, 0], bv, 0.6, 1e-3)
    T = f["t"]
    assert T.shape == (601,) and f["p"].shape == (601, 3) and f["v"].shape == (601, 3)
    assert T[0] == 0.0
    assert T[-1] == pytest.approx(0.6, abs=1e-12)
    np.testing.assert_allclose(np.diff(T), 1e-3, atol=1e-15)
    ref = B.flight_vacuum(p0, v0, T)
    assert np.abs(f["p"] - ref).max() < 1e-12
    vref = np.asarray(v0) - np.outer(T, [0.0, 0.0, B.G])
    assert np.abs(f["v"] - vref).max() < 1e-12
    with pytest.raises(ValueError):
        B.flight_ode(p0, v0, [0, 0, 0], bv, -0.1)
    with pytest.raises(ValueError):
        B.flight_ode(p0, v0, [0, 0, 0], bv, 0.1, dt=0.0)


def test_flight_ode_drag_only_slows_monotonically():
    """g = 0・ω = 0・C_d > 0 の水平飛翔: 速さは単調減少、向きは不変、加速度は v と反平行。"""
    bp = B.ball_params()
    bp["g"] = 0.0
    v0 = np.array([10.0, 3.0, 0.0])
    f = B.flight_ode([0, 0, 1], v0, [0, 0, 0], bp, 0.6, 1e-3)
    speed = np.linalg.norm(f["v"], axis=1)
    assert np.all(np.diff(speed) < 0)
    assert speed[-1] < speed[0] * 0.9                   # 0.6 s で目に見えて減速する
    direction = f["v"] / speed[:, None]
    assert np.abs(direction - v0 / np.linalg.norm(v0)).max() < 1e-12
    assert np.abs(f["p"][:, 2] - 1.0).max() < 1e-12     # 無重力なので高さは不変
    a = B._accel(v0, np.zeros(3), bp)
    assert float(a @ v0) < 0
    assert np.abs(np.cross(a, v0)).max() < 1e-12
    k = 0.5 * bp["rho"] * bp["area"] / bp["mass"]
    assert np.linalg.norm(a) == pytest.approx(k * bp["cd"] * float(v0 @ v0), rel=1e-12)


def test_magnus_acceleration_perpendicular_and_magnitude():
    """C_d = 0・C_L = 0.3・g = 0: 加速度は v と ω の両方に直交、大きさは ½ρC_L A|v|²/m。"""
    bm = B.ball_params(cd=0.0, cl=0.3)
    bm["g"] = 0.0
    v = np.array([5.0, 0.0, 0.0])
    w = np.array([0.0, 0.0, 100.0])
    a = B._accel(v, w, bm)
    assert abs(float(a @ v)) < 1e-12
    assert abs(float(a @ w)) < 1e-12
    expect = 0.5 * bm["rho"] * 0.3 * bm["area"] * 25.0 / bm["mass"]
    assert np.linalg.norm(a) == pytest.approx(expect, rel=1e-12)
    # ẑ × x̂ = ŷ: 向きも閉形式どおり
    assert a == pytest.approx([0.0, expect, 0.0], abs=1e-12)
    # 一般の向きでも直交(ω が v と平行でない)
    v2 = np.array([3.0, -2.0, 1.5])
    w2 = np.array([50.0, 20.0, -80.0])
    a2 = B._accel(v2, w2, bm)
    assert abs(float(a2 @ v2)) < 1e-12 and abs(float(a2 @ w2)) < 1e-12
    sin_theta = np.linalg.norm(np.cross(w2 / np.linalg.norm(w2), v2 / np.linalg.norm(v2)))   # ω̂ × v̂ の大きさ = sin θ
    assert np.linalg.norm(a2) == pytest.approx(0.5 * bm["rho"] * 0.3 * bm["area"] * float(v2 @ v2) / bm["mass"] * sin_theta,
                                               rel=1e-12)
    # ω = 0 なら加速度ゼロ(抗力も重力も切ってある)
    assert np.abs(B._accel(v, np.zeros(3), bm)).max() == 0.0


def test_magnus_lift_coefficient_limits():
    """C_L(S) = 1/(2 + 1/S): S = 0 で 0、S = 1 で 1/3、S → ∞ で 0.5、単調増加、ベクトル化。"""
    assert float(B.magnus_lift_coefficient(0.0)) == 0.0
    assert float(B.magnus_lift_coefficient(1.0)) == pytest.approx(1.0 / 3.0, rel=1e-15)
    assert float(B.magnus_lift_coefficient(1e12)) == pytest.approx(0.5, abs=1e-11)
    S = np.array([0.0, 0.1, 0.5, 1.0, 5.0, 100.0])
    cl = B.magnus_lift_coefficient(S)
    assert cl.shape == S.shape
    np.testing.assert_allclose(cl[1:], 1.0 / (2.0 + 1.0 / S[1:]), rtol=1e-15)
    assert cl[0] == 0.0
    assert np.all(np.diff(cl) > 0) and np.all(cl < 0.5)
    assert float(B.magnus_lift_coefficient(-1.0)) == 0.0   # 負は 0 に落とす


# ─────────────────────────────── 8-11 跳ね ───────────────────────────────

def test_bounce_theorems_random():
    """乱数 500 本: 接触点まわりの角運動量は保存(相対 1e-12)、運動エネルギーは増えない、v_z' = −e v_z、
    grip と slip の両方が出る、grip 後は接触点の滑りが消えている。"""
    bp = B.ball_params()
    rng = np.random.default_rng(0)
    worst = 0.0
    regimes = {"grip": 0, "slip": 0, "none": 0}
    for _ in range(500):
        v = rng.normal(0, 5, 3)
        v[2] = -abs(v[2]) - 0.1
        w = rng.normal(0, 200, 3)
        ipk = B.impact_params(rng.uniform(0.3, 1.0), rng.uniform(0, 0.6))
        b = B.bounce(v, w, NZ, bp, ipk)
        L0 = B.contact_angular_momentum(v, w, NZ, bp)
        L1 = B.contact_angular_momentum(b["v"], b["omega"], NZ, bp)
        worst = max(worst, float(np.abs(L1 - L0).max() / max(1e-12, np.abs(L0).max())))
        assert _kinetic(bp, b["v"], b["omega"]) <= _kinetic(bp, v, w) + 1e-12
        assert abs(b["v"][2] + ipk["e"] * v[2]) < 1e-12
        assert b["J_n"] == pytest.approx(-(1.0 + ipk["e"]) * bp["mass"] * v[2], rel=1e-12)
        assert abs(float(b["J_t"] @ NZ)) < 1e-15                    # 接線力積は接線
        regimes[b["regime"]] += 1
        vt_out = b["v"] - b["v"][2] * NZ
        state = B.roll_slide_state(vt_out, b["omega"], NZ, bp)
        if b["regime"] == "grip":
            assert state["rolling"] and state["slip_speed"] < 1e-9
        else:
            assert np.linalg.norm(b["J_t"]) == pytest.approx(ipk["mu"] * b["J_n"], rel=1e-12)
            assert state["slip_speed"] < b["slip_speed"]              # 滑りは減るが消えない
    assert worst < 1e-12
    assert regimes["grip"] > 0 and regimes["slip"] > 0 and regimes["none"] == 0


def test_bounce_frictionless_keeps_tangential_and_spin():
    """μ = 0: 接線速度と回転は不変、法線速度だけ −e 倍、regime は slip(接線力積ゼロ)。"""
    bp = B.ball_params()
    b = B.bounce([3.0, 0.0, -4.0], [0.0, 50.0, 0.0], NZ, bp, B.impact_params(0.8, 0.0))
    assert b["v"] == pytest.approx([3.0, 0.0, 3.2], abs=1e-15)
    assert b["omega"] == pytest.approx([0.0, 50.0, 0.0], abs=1e-15)
    assert np.abs(b["J_t"]).max() == 0.0
    assert b["J_n"] == pytest.approx(1.8 * bp["mass"] * 4.0, rel=1e-15)
    assert b["regime"] == "slip"


def test_bounce_separating_ball_is_untouched():
    """v·n ≥ 0(離れていく / 平行)なら regime "none" で状態はそのまま、力積ゼロ。"""
    bp = B.ball_params()
    ip = B.impact_params(0.9, 0.3)
    for v in ([1.0, 2.0, 0.5], [1.0, 2.0, 0.0]):
        b = B.bounce(v, [10.0, -20.0, 30.0], NZ, bp, ip)
        assert b["regime"] == "none"
        assert b["v"] == pytest.approx(v, abs=0.0)
        assert b["omega"] == pytest.approx([10.0, -20.0, 30.0], abs=0.0)
        assert b["J_n"] == 0.0 and np.abs(b["J_t"]).max() == 0.0 and b["slip_speed"] == 0.0
    # 返り値は入力のコピー(呼び手の配列を共有しない)
    v_in = np.array([1.0, 2.0, 0.5])
    b = B.bounce(v_in, [0, 0, 0], NZ, bp, ip)
    b["v"][0] = 99.0
    assert v_in[0] == 1.0


def test_bounce_classic_sliding_to_rolling_factors():
    """無回転で滑って当たり grip する球の古典解: 中実球(I = 2/5 m r²)は水平速度 5/7 倍、薄殻(2/3)は 3/5 倍。
    J_stop = m|s|/(1 + m r²/I) → v_t' = v_t (1 − 1/(1 + m r²/I))。"""
    ip = B.impact_params(0.9, 0.8)                    # μ J_n = 0.8·1.9·4 m ≫ J_stop なので grip
    for shell, factor in ((False, 5.0 / 7.0), (True, 3.0 / 5.0)):
        bp = B.ball_params(shell=shell)
        b = B.bounce([3.0, 0.0, -4.0], [0.0, 0.0, 0.0], NZ, bp, ip)
        assert b["regime"] == "grip"
        assert b["v"][0] == pytest.approx(factor * 3.0, rel=1e-12)
        assert b["v"][1] == pytest.approx(0.0, abs=1e-15)
        assert b["v"][2] == pytest.approx(3.6, rel=1e-12)
        # 跳ね返りは転がり: v_t = r ω × n、回転軸は −y(前方回転)
        assert B.roll_slide_state([b["v"][0], 0.0, 0.0], b["omega"], NZ, bp)["rolling"]
        assert b["omega"][1] == pytest.approx(factor * 3.0 / bp["radius"], rel=1e-12)
        assert b["omega"][0] == 0.0 and b["omega"][2] == 0.0
        assert np.linalg.norm(b["J_t"]) == pytest.approx(bp["mass"] * 3.0 * (1.0 - factor), rel=1e-12)


# ─────────────────────────────── 12-14 落として跳ねる列 ───────────────────────────────

def test_apex_sequence_and_total_time_closed_forms():
    """h_k = e^{2k} h₀、総時間 √(2h₀/g)(1 + e)/(1 − e)、不正引数の拒否。"""
    h = B.apex_sequence(0.305, 0.88, 5)
    assert h.shape == (6,)
    np.testing.assert_allclose(h, 0.305 * 0.88 ** (2 * np.arange(6)), rtol=1e-15)
    assert B.apex_sequence(1.0, 1.0, 3) == pytest.approx([1.0] * 4)
    assert B.apex_sequence(1.0, 0.0, 2) == pytest.approx([1.0, 0.0, 0.0])
    T = B.bounce_total_time(0.305, 0.88)
    assert T == pytest.approx(np.sqrt(2 * 0.305 / B.G) * 1.88 / 0.12, rel=1e-15)
    assert B.bounce_total_time(0.305, 0.0) == pytest.approx(np.sqrt(2 * 0.305 / B.G), rel=1e-15)   # 跳ねなければ落下時間
    assert B.bounce_total_time(1.0, 0.5, g=2.0) == pytest.approx(3.0, rel=1e-15)
    for args in ((-0.1, 0.5, 3), (0.3, 1.1, 3), (0.3, -0.1, 3), (0.3, 0.5, -1)):
        with pytest.raises(ValueError):
            B.apex_sequence(*args)
    for args in ((-0.1, 0.5), (0.3, 1.0), (0.3, -0.1)):
        with pytest.raises(ValueError):
            B.bounce_total_time(*args)
    with pytest.raises(ValueError):
        B.bounce_total_time(0.3, 0.5, g=0.0)


@pytest.fixture(scope="module")
def drop_sim():
    """h₀ = 0.305 から真空で落とす(e = 0.88、μ = 0.2)。13 と 14 で共有。頂点は格子の最大なので dt = 5e-4
    (格子の取りこぼし ≤ ½g(dt/2)² ≈ 3e-7 < 1e-6)。"""
    h0 = 0.305
    bd = B.ball_params(rho=0.0)
    ipd = B.impact_params(0.88, 0.2)
    sim = B.flight_simulate([0, 0, h0 + bd["radius"]], [0, 0, 0], [0, 0, 0], bd, ipd, 4.0, 5e-4)
    ct = np.array([c["t"] for c in sim["contacts"]])
    apex = []
    for i in range(len(ct) - 1):
        m = (sim["t"] > ct[i]) & (sim["t"] < ct[i + 1])
        if m.any():
            apex.append(sim["p"][m, 2].max() - bd["radius"])
    return {"h0": h0, "bp": bd, "sim": sim, "ct": ct, "apex": np.array(apex)}


def test_flight_simulate_drop_sequence(drop_sim):
    """頂点高さは e^{2k}h₀ と 1e-6、接触は 40 回以上、rest_t は閉形式の総時間と 0.01、卓の下に沈まない、
    接触の regime は全部 grip(無回転・垂直落下なら滑りゼロ)。"""
    sim, ct, apex, h0 = drop_sim["sim"], drop_sim["ct"], drop_sim["apex"], drop_sim["h0"]
    r = drop_sim["bp"]["radius"]
    assert len(ct) >= 40
    assert np.all(np.diff(ct) > 0)
    assert len(apex) >= 5
    assert np.abs(apex[:5] - B.apex_sequence(h0, 0.88, 5)[1:]).max() < 1e-6
    assert sim["rest_t"] is not None
    assert abs(sim["rest_t"] - B.bounce_total_time(h0, 0.88)) < 0.01
    assert sim["p"][:, 2].min() - r >= -1e-9
    assert sim["t"][0] == 0.0 and sim["t"][-1] == pytest.approx(4.0, abs=1e-9)
    assert np.all(np.diff(sim["t"]) >= 0)
    assert sim["p"].shape == sim["v"].shape == sim["omega"].shape == (sim["t"].size, 3)
    # 置いた後は高さ固定・鉛直速度ゼロ
    after = sim["t"] > sim["rest_t"] + 1e-9
    assert np.abs(sim["p"][after, 2] - r).max() < 1e-12
    assert np.abs(sim["v"][after, 2]).max() == 0.0
    # 最初の接触は落下時間 √(2h₀/g)、入射速度 −√(2gh₀)、regime grip
    c0 = sim["contacts"][0]
    assert c0["t"] == pytest.approx(np.sqrt(2 * h0 / B.G), abs=1e-9)
    assert c0["v_in"][2] == pytest.approx(-np.sqrt(2 * B.G * h0), rel=1e-9)
    assert c0["v_out"][2] == pytest.approx(0.88 * np.sqrt(2 * B.G * h0), rel=1e-9)
    assert all(c["regime"] == "grip" for c in sim["contacts"])
    # 接触の間隔は e 倍ずつ縮む(T_{k+1} = e T_k)
    ratios = np.diff(ct)[1:8] / np.diff(ct)[:7]
    assert np.abs(ratios - 0.88).max() < 1e-6


def test_restitution_estimators_recover_e(drop_sim):
    """頂点列(h₀ を先頭に)から e = 0.88 を 1e-5、接触時刻 8 個から 1e-6 で戻す。不正入力は ValueError。"""
    apex, ct, h0 = drop_sim["apex"], drop_sim["ct"], drop_sim["h0"]
    ra = B.restitution_from_apexes(np.r_[h0, apex[:6]])
    assert abs(ra["e"] - 0.88) < 1e-5
    assert ra["h0"] == pytest.approx(h0, rel=1e-5)
    assert ra["residual"] < 1e-5
    ri = B.restitution_from_intervals(ct[:8])
    assert abs(ri["e"] - 0.88) < 1e-6
    assert ri["residual"] < 1e-6
    # 閉形式の列からは丸めの精度で戻る
    assert B.restitution_from_apexes(B.apex_sequence(1.0, 0.7, 6))["e"] == pytest.approx(0.7, abs=1e-12)
    for bad in ([0.3], [0.3, 0.0], [0.3, -0.1], [0.3, float("inf")]):
        with pytest.raises(ValueError):
            B.restitution_from_apexes(bad)
    for bad in ([0.0, 1.0], [0.0, 1.0, 0.5], [0.0, 1.0, 1.0]):
        with pytest.raises(ValueError):
            B.restitution_from_intervals(bad)


def test_fit_parabola_recovers_vacuum_flight():
    """真空の標本(閉形式)から p₀, v₀, g を 1e-9 で戻し rms < 1e-12。3 点未満・長さ不一致は ValueError。"""
    p0 = np.array([0.1, -0.3, 1.0])
    v0 = np.array([2.0, 0.5, 3.0])
    t = np.arange(0.0, 0.6 + 1e-12, 1e-3)
    P = B.flight_vacuum(p0, v0, t)
    fit = B.fit_parabola(t, P)
    assert np.abs(fit["p0"] - p0).max() < 1e-9
    assert np.abs(fit["v0"] - v0).max() < 1e-9
    assert abs(fit["g"] - B.G) < 1e-9
    assert fit["rms"] < 1e-12
    # RK4 の真空飛翔からも同じ
    f = B.flight_ode(p0, v0, [0, 0, 0], B.ball_params(rho=0.0), 0.6, 1e-3)
    fit2 = B.fit_parabola(f["t"], f["p"])
    assert abs(fit2["g"] - B.G) < 1e-9 and fit2["rms"] < 1e-12
    with pytest.raises(ValueError):
        B.fit_parabola(t[:2], P[:2])
    with pytest.raises(ValueError):
        B.fit_parabola(t[:5], P[:4])


# ─────────────────────────────── 16-17 卓上の飛翔 ───────────────────────────────

def test_flight_simulate_table_extent():
    """卓の範囲外に落ちる球は接触せず z = r を通り抜ける(contacts 空、z が r より下へ)。
    table_xy = None なら同じ球が跳ねる。"""
    bp = B.ball_params(rho=0.0)
    ip = B.impact_params(0.9, 0.25)
    table = (-1.37, 1.37, -0.76, 0.76)
    r = bp["radius"]
    p0 = [2.0, 0.0, 0.3]
    miss = B.flight_simulate(p0, [0, 0, 0], [0, 0, 0], bp, ip, 0.5, 1e-3, table_xy=table)
    assert miss["contacts"] == []
    assert miss["rest_t"] is None
    assert miss["p"][:, 2].min() < r - 0.1                 # 卓面を抜けて落ち続ける
    hit = B.flight_simulate(p0, [0, 0, 0], [0, 0, 0], bp, ip, 0.5, 1e-3, table_xy=None)
    assert len(hit["contacts"]) >= 1
    assert hit["p"][:, 2].min() - r >= -1e-9
    assert hit["contacts"][0]["t"] == pytest.approx(np.sqrt(2 * (0.3 - r) / B.G), abs=1e-9)
    # 範囲内に落ちる球は table_xy があっても跳ねる
    inside = B.flight_simulate([0.5, 0.2, 0.3], [0, 0, 0], [0, 0, 0], bp, ip, 0.5, 1e-3, table_xy=table)
    assert len(inside["contacts"]) >= 1


def test_flight_simulate_topspin_shot():
    """トップスピン(ω = +300 ŷ、v = +6 x̂)の打球: マグヌスで沈み 0.6 s までに接触はちょうど 1 回、
    接触点の滑りが小さいので grip、跳ね返りは上向き(v_z > 0)で前進を保つ。"""
    bp = B.ball_params()
    ip = B.impact_params()
    sp = B.flight_simulate([-1.2, 0, 0.3], [6, 0, 0.5], [0, 300, 0], bp, ip, 0.6, 1e-3,
                           table_xy=(-1.37, 1.37, -0.76, 0.76))
    assert len(sp["contacts"]) == 1
    c = sp["contacts"][0]
    assert 0.0 < c["t"] < 0.6
    assert c["regime"] == "grip"
    assert c["v_in"][2] < 0 < c["v_out"][2]
    assert c["v_out"][2] == pytest.approx(-ip["e"] * c["v_in"][2], rel=1e-12)
    assert c["v_out"][0] > 0
    assert c["p"][2] == pytest.approx(bp["radius"], abs=1e-12)
    assert -1.37 <= c["p"][0] <= 1.37
    # トップスピンは下向きの揚力: 真空の放物線より早く落ちる
    t_vac = (0.5 + np.sqrt(0.25 + 2 * B.G * (0.3 - bp["radius"]))) / B.G
    assert c["t"] < t_vac
    # 接触の前後で角速度の記録が繋がっている
    assert np.abs(c["omega_in"] - [0, 300, 0]).max() == 0.0
    idx = int(np.argmin(np.abs(sp["t"] - c["t"])))
    assert np.abs(sp["omega"][idx] - c["omega_out"]).max() < 1e-12
    assert sp["p"][:, 2].min() - bp["radius"] >= -1e-9


# ─────────────────────────────── 18-19 摩擦 ───────────────────────────────

def test_friction_closed_forms():
    """停止距離 v₀²/(2μg)、μ の逆算は往復で一致、斜面の滑り出し角 atan μ。不正値は ValueError。"""
    d = B.slide_stop_distance(2.0, 0.25)
    assert d == pytest.approx(4.0 / (2 * 0.25 * B.G), rel=1e-15)
    assert B.slide_stop_distance(0.0, 0.25) == 0.0
    assert B.slide_stop_distance(3.0, 0.5, g=2.0) == pytest.approx(4.5, rel=1e-15)
    assert B.mu_from_stop_distance(2.0, d) == pytest.approx(0.25, rel=1e-12)
    for v0, mu in ((1.0, 0.1), (5.0, 0.6), (0.3, 1.5)):
        assert B.mu_from_stop_distance(v0, B.slide_stop_distance(v0, mu)) == pytest.approx(mu, rel=1e-12)
    assert B.incline_slip_angle(0.0) == 0.0
    assert B.incline_slip_angle(1.0) == pytest.approx(np.pi / 4, rel=1e-15)
    assert B.incline_slip_angle(0.25) == pytest.approx(np.arctan(0.25), rel=1e-15)
    for args in ((-1.0, 0.25), (2.0, 0.0), (2.0, -0.1)):
        with pytest.raises(ValueError):
            B.slide_stop_distance(*args)
    with pytest.raises(ValueError):
        B.slide_stop_distance(2.0, 0.25, g=0.0)
    for args in ((-1.0, 1.0), (2.0, 0.0), (2.0, -1.0)):
        with pytest.raises(ValueError):
            B.mu_from_stop_distance(*args)
    with pytest.raises(ValueError):
        B.incline_slip_angle(-0.1)


def test_roll_slide_state():
    """接触点の滑り s = v_t − r ω × n: v_t = r ω × n なら転がり(slip 0)、そうでなければ滑り。法線は正規化される。"""
    bp = B.ball_params()
    r = bp["radius"]
    w = np.array([0.0, 40.0, 0.0])                        # ω × ẑ = 40 x̂ → 転がりは v_t = 0.8 x̂
    roll = B.roll_slide_state([r * 40.0, 0.0, 0.0], w, NZ, bp)
    assert roll["rolling"] and roll["slip_speed"] < 1e-9
    slide = B.roll_slide_state([1.0, 0.0, 0.0], w, NZ, bp)
    assert not slide["rolling"]
    assert slide["slip_speed"] == pytest.approx(1.0 - 0.8, rel=1e-12)
    back = B.roll_slide_state([-r * 40.0, 0.0, 0.0], w, NZ, bp)    # 逆向きに動けば滑り 2 倍
    assert back["slip_speed"] == pytest.approx(1.6, rel=1e-12)
    still = B.roll_slide_state([0.0, 0.0, 0.0], [0.0, 0.0, 0.0], NZ, bp)
    assert still["rolling"]
    spin_only = B.roll_slide_state([0.0, 0.0, 0.0], [0.0, 0.0, 100.0], NZ, bp)   # 法線まわりの回転は滑らない
    assert spin_only["rolling"]
    scaled = B.roll_slide_state([1.0, 0.0, 0.0], w, [0.0, 0.0, 5.0], bp)          # 法線は長さに依らない
    assert scaled["slip_speed"] == pytest.approx(slide["slip_speed"], rel=1e-15)


# ─────────────────────────────── 20-23 ひも ───────────────────────────────

def test_pendulum_period_closed_form():
    """2π√(L/g)。L ≤ 0、g ≤ 0 は ValueError。"""
    assert B.pendulum_period(0.4) == pytest.approx(2 * np.pi * np.sqrt(0.4 / B.G), rel=1e-15)
    assert B.pendulum_period(1.0, g=np.pi ** 2) == pytest.approx(2.0, rel=1e-15)
    assert B.pendulum_period(1.6) == pytest.approx(2 * B.pendulum_period(0.4), rel=1e-15)
    for args, kw in (((0.0,), {}), ((-0.1,), {}), ((0.4,), {"g": 0.0}), ((0.4,), {"g": -9.81})):
        with pytest.raises(ValueError):
            B.pendulum_period(*args, **kw)


def test_tether_small_amplitude_pendulum():
    """固定手元・小振幅(v₀ = 0.3 m/s、L = 0.4): |p − h| ≤ L + 1e-9、張力 ≥ 0、snap 無し、
    エネルギー peak-to-peak < 1e-4 J(実測 6.7e-6)、x の零交差から測る周期が 2π√(L/g)(1 + θ²/16) と 0.5 %
    (実測 1.2705 vs 1.2687·1.0014)。"""
    L = 0.4
    tp = B.tether_simulate([0.0, 0.0, -L], [0.3, 0.0, 0.0], [0.0, 0.0, 0.0], L, 6.0, 2e-4)
    dist = np.linalg.norm(tp["p"], axis=1)
    assert dist.max() <= L + 1e-9
    assert tp["tension"].min() >= 0.0
    assert tp["tension"][1:].min() > 0.0                  # 常に張っている(重力が外向き)
    assert tp["taut"][1:].all()
    assert tp["snap_times"].size == 0
    assert tp["snap_loss"] == 0.0
    assert np.ptp(tp["energy"]) < 1e-4
    assert tp["t"].shape == (30001,) and tp["p"].shape == (30001, 3)
    x = tp["p"][:, 0]
    zc = np.where(np.diff(np.sign(x)) != 0)[0]
    assert zc.size >= 8
    period = 2.0 * float(np.mean(np.diff(tp["t"][zc])))
    theta = np.abs(x).max() / L
    expect = B.pendulum_period(L) * (1.0 + theta ** 2 / 16.0)
    assert abs(period / expect - 1.0) < 0.005
    assert 0.1 < theta < 0.2                              # 小振幅(実測 ≈ 0.151 rad)
    # 面内運動(y は動かない)、最下点の張力 ≈ m(g + v²/L)
    assert np.abs(tp["p"][:, 1]).max() == 0.0
    assert tp["tension"][1] == pytest.approx(0.01 * (B.G + 0.09 / L), rel=0.02)


def test_tether_snap_from_slack():
    """真上に 3 m/s で投げた玉: ひもは緩んだまま手元の上まで昇り、落ちて |p − h| = L に戻る瞬間に張る(snap)。
    snap はちょうど 1 回(≈ 3/(g/2)·… = 0.6116 s)、失う運動エネルギー ½ m v_r² ≈ 0.045 J(実測 0.04502)、
    その後は球面上に留まり再び snap しない。"""
    L = 0.4
    ts = B.tether_simulate([0.0, 0.0, -L], [0.0, 0.0, 3.0], [0.0, 0.0, 0.0], L, 1.5, 1e-3)
    dist = np.linalg.norm(ts["p"], axis=1)
    assert dist.max() <= L + 1e-9
    assert ts["snap_times"].shape == (1,)
    t_snap = float(ts["snap_times"][0])
    assert t_snap == pytest.approx(2 * 3.0 / B.G, abs=2e-3)          # 上って戻るまで 2v₀/g
    assert abs(ts["snap_loss"] - 0.045) < 0.02 * 0.045
    idx = int(np.argmin(np.abs(ts["t"] - t_snap)))
    v_before = float(np.linalg.norm(ts["v"][idx - 1]))
    assert ts["snap_loss"] == pytest.approx(0.5 * 0.01 * v_before ** 2, rel=0.02)
    assert np.linalg.norm(ts["v"][idx]) < 1e-9                       # 径方向しか無い速度は全部消える
    assert ts["tension"][idx] > 0.0
    assert ts["tension"][idx] == pytest.approx(0.01 * v_before / 1e-3, rel=0.02)   # 撃力 m v_r/dt
    # 昇り(緩み)の間は張らず張力ゼロ、手元の高さより上まで達する
    rising = ts["t"] < t_snap - 2e-3
    assert not ts["taut"][rising].any()
    assert ts["tension"][rising].max() == 0.0
    assert ts["p"][:, 2].max() > 0.0
    # snap の後は張ったまま(最下点で静止、重力は外向き)
    after = ts["t"] > t_snap + 1e-9
    assert ts["taut"][after].all()
    assert np.abs(dist[after] - L).max() < 1e-9
    assert ts["energy"][idx] < ts["energy"][idx - 1] - 0.9 * ts["snap_loss"]   # エネルギーは snap で落ちる
    with pytest.raises(ValueError):
        B.tether_simulate([0, 0, -L], [0, 0, 0], [0, 0, 0], 0.0, 1.0)


def test_tether_moving_handle():
    """動く手元 h(t) = (0, 0, 0.5 t)(引き上げ): 各時刻で |p − h(t)| ≤ L + 1e-9、張力 ≥ 0、玉は持ち上がる。
    初期状態が |p₀ − h(0)| > L なら ValueError。"""
    L = 0.4

    def handle(t):
        return np.array([0.0, 0.0, 0.5 * t])

    p0 = [0.2, 0.0, -np.sqrt(L * L - 0.04)]              # 少し横にずらして揺れながら引き上げる
    tm = B.tether_simulate(p0, [0.0, 0.0, 0.0], handle, L, 2.0, 1e-3)
    H = np.array([handle(t) for t in tm["t"]])
    dist = np.linalg.norm(tm["p"] - H, axis=1)
    assert dist.max() <= L + 1e-9
    assert tm["tension"].min() >= 0.0
    assert tm["p"][-1, 2] > tm["p"][0, 2] + 0.5          # 2 s で 1 m 引き上げられる
    assert abs(tm["p"][-1, 2] - (H[-1, 2] - L)) < 0.4     # 手元の下 L 以内
    assert tm["snap_loss"] >= 0.0
    # 固定手元と違い手元の仕事でエネルギーは増える
    assert tm["energy"][-1] > tm["energy"][0]
    with pytest.raises(ValueError):
        B.tether_simulate([0.0, 0.0, -L - 0.05], [0, 0, 0], handle, L, 1.0, 1e-3)
    with pytest.raises(ValueError):
        B.tether_simulate([0.0, 0.0, -L - 0.05], [0, 0, 0], [0.0, 0.0, 0.0], L, 1.0, 1e-3)


# ─────────────────────────────── 24 皿 ───────────────────────────────

def test_cup_catch_check():
    """中心・低速・皿のすぐ上なら捕球。横ずれ > cup_radius − ball_radius、速さ > v_rel_max、皿の下(height < 0)は不捕球。
    不正な半径は ValueError。"""
    c, ax = [0.0, 0.0, 0.0], [0.0, 0.0, 1.0]
    ok = B.cup_catch_check([0.0, 0.0, 0.01], [0.0, 0.0, -0.2], c, ax, 0.02, 0.015)
    assert ok["caught"] is True
    assert ok["lateral"] == 0.0 and ok["height"] == pytest.approx(0.01) and ok["speed"] == pytest.approx(0.2)
    # 横ずれ: 許容は cup_radius − ball_radius = 0.005
    assert B.cup_catch_check([0.004, 0.0, 0.01], [0.0, 0.0, -0.2], c, ax, 0.02, 0.015)["caught"]
    off = B.cup_catch_check([0.006, 0.0, 0.01], [0.0, 0.0, -0.2], c, ax, 0.02, 0.015)
    assert off["caught"] is False and off["lateral"] == pytest.approx(0.006)
    # 速すぎ
    fast = B.cup_catch_check([0.0, 0.0, 0.01], [0.0, 0.0, -1.5], c, ax, 0.02, 0.015)
    assert fast["caught"] is False and fast["speed"] == pytest.approx(1.5)
    assert B.cup_catch_check([0.0, 0.0, 0.01], [0.0, 0.0, -1.5], c, ax, 0.02, 0.015, v_rel_max=2.0)["caught"]
    # 皿の下
    below = B.cup_catch_check([0.0, 0.0, -0.01], [0.0, 0.0, -0.2], c, ax, 0.02, 0.015)
    assert below["caught"] is False and below["height"] == pytest.approx(-0.01)
    # 皿より高すぎ(> 1.5 r)
    assert not B.cup_catch_check([0.0, 0.0, 0.05], [0.0, 0.0, -0.2], c, ax, 0.02, 0.015)["caught"]
    # 皿の軸が傾いていても軸まわりで測る(軸の長さは正規化)
    tilted = B.cup_catch_check([0.01, 0.0, 0.0], [0.0, 0.0, 0.0], c, [2.0, 0.0, 0.0], 0.02, 0.015)
    assert tilted["caught"] and tilted["height"] == pytest.approx(0.01) and tilted["lateral"] == pytest.approx(0.0, abs=1e-15)
    for cup_r, ball_r in ((0.0, 0.015), (-0.02, 0.015), (0.02, 0.0), (0.02, -0.01)):
        with pytest.raises(ValueError):
            B.cup_catch_check([0.0, 0.0, 0.01], [0.0, 0.0, 0.0], c, ax, cup_r, ball_r)
    with pytest.raises(ValueError):
        B.cup_catch_check([0.0, 0.0, 0.01], [0.0, 0.0, 0.0], c, ax, 0.02, 0.015, v_rel_max=-1.0)


def test_cup_catch_check_ball_larger_than_cup():
    """皿の半径 0.01 < 玉の半径 0.015 は幾何的に入らない設定 → fail-closed で ValueError。"""
    with pytest.raises(ValueError):
        B.cup_catch_check([0.0, 0.0, 0.01], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 1.0], 0.01, 0.015)
