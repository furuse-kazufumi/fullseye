"""drivetraffic(動く交通参加者と死角)の門。

固定する性質(閉形式と独立な経路で比べる):
- IDM: 自由走行 a(1 − (v/v0)^δ)、平衡車間で加速度 0、車列の積分が平衡車間 s_e(v) に収束(rtol 1e-6、3 種の癖)、
  止まった車列の車間は 0 < s ≤ s0(静止できる条件。s0 を僅かに下回る)で dt に 1 次収束、
  反応遅れ m 刻みの間は追従車の加速度が平衡の 0 のまま
- OU: 定常分散 σ²/(2θ)、自己相関 e^{−θτ}(許容幅 = AR(1) の標本誤差の 5 倍)、dt を変えても同じ(Euler なら落ちる幅)
- social force: 1 人は v0(1 − e^{−t/τ})・x(t) に dt に依らず一致、Euler(細かい dt)とも一致、
  正面衝突の点対称・並走の鏡映対称が保たれる、相互作用ありで 1 次収束
- 横断: 横断時間 = (W + 2·co)/speed、待つ人は縁で +π/2 を向いて停止、沿って歩く人は車道に入らない、向き = 差分の向き
- 死角: 軸平行の手計算 d = (e_x − c_x) e_y / (e_y − c_y)、場面全体の回転に不変(角度 6 つ)、総当たり(視線の点検査)と一致
- 止まれる速度: rsssafety.rss_stopping_distance(v, ρ, 0, b) == d(rtol 1e-12)、drivelong.stopping_distance_grade とも一致
- はみ出し: D* ± ε で go/wait が切り替わる、時間を進めるシミュレーションの PET = 0 の境目(二分法)が D* と一致
- ポアソン: 平均 = 分散 = ∫λ(標本誤差の 5 倍)、位置の分布 = λ/Λ(KS)、rate_max 違反は ValueError
- 重要度サンプリング: 閉形式の事故確率 1 − exp(−∫_win λ) と素朴 MC・IS の両方が一致、IS の 1 試行あたり分散が小さい
- fail-closed: 負の速度・未知の kind/intent・形の不一致・絶対連続でない率は ValueError
"""
import math

import numpy as np
import pytest

import drivetraffic as D
import rsssafety as R
import drivelong as DL

IDM = dict(v0=15.0, T=1.5, a=1.2, b=2.0, s0=2.0, delta=4.0)


def _idm_only(p):
    return {k: p[k] for k in ("v0", "T", "a", "b", "s0", "delta", "length")}


# ---- 1-3. IDM ------------------------------------------------------------------------------------
def test_idm_free_road_and_equilibrium_zero():
    v = np.array([0.0, 5.0, 10.0, 14.0])
    a = D.idm_accel(v, np.inf, 0.0, **IDM)
    np.testing.assert_allclose(a, 1.2 * (1 - (v / 15.0) ** 4), rtol=1e-15)
    se = D.idm_equilibrium_gap(v, v0=15.0, T=1.5, s0=2.0)
    np.testing.assert_allclose(D.idm_accel(v, se, 0.0, **IDM), 0.0, atol=1e-13)
    assert isinstance(D.idm_accel(5.0, 20.0, 1.0, **IDM), float)
    # 近づいていれば(dv > 0)減速が強い
    assert D.idm_accel(10.0, 30.0, 3.0, **IDM) < D.idm_accel(10.0, 30.0, 0.0, **IDM)


@pytest.mark.parametrize("kind", D.DRIVER_KINDS)
def test_platoon_converges_to_equilibrium_gap(kind):
    p = _idm_only(D.driver_style(kind))
    v_end = 8.0
    lead = lambda t: 11.0 if t < 10 else (5.0 if t < 25 else v_end)   # noqa: E731
    r = D.idm_platoon_simulate(lead, 4, params_per_vehicle=p, dt=0.05, t_end=400.0)
    assert not r["collision"]
    se = D.idm_equilibrium_gap(v_end, v0=p["v0"], T=p["T"], s0=p["s0"], delta=p["delta"])
    np.testing.assert_allclose(r["gap"][-1, 1:], se, rtol=1e-6)
    np.testing.assert_allclose(r["v"][-1, 1:], v_end, rtol=1e-6)


def test_platoon_mixed_styles_stop_gap_at_most_s0():
    """止まった車列: v = 0 で静止し続けられるのは IDM の加速度 a(1 − (s0/s)²) ≤ 0、つまり 0 < s ≤ s0 のとき。
    実測では s0 を僅かに **下回って** 止まる(careful で s0 = 3 に対し 2.973、dt → 0 でも残る = 離散化でなく
    モデルの性質)。止まった車間は dt について 1 次で収束する。"""
    ps = [_idm_only(D.driver_style(k)) for k in D.DRIVER_KINDS]
    lead = lambda t: 10.0 if t < 5 else max(0.0, 10.0 - 1.0 * (t - 5))     # noqa: E731
    gaps = []
    for dt in (0.02, 0.01, 0.005):
        r = D.idm_platoon_simulate(lead, 3, params_per_vehicle=ps, dt=dt, t_end=80.0)
        assert not r["collision"]
        g = r["gap"][-1, 1:]
        s0 = np.array([p["s0"] for p in ps])
        assert np.all(r["v"][-1] == 0.0) and np.all(r["v"] >= 0.0)
        assert np.all(g > 0) and np.all(g <= s0)
        for p, gi in zip(ps, g):
            assert D.idm_accel(0.0, gi, 0.0, **{k: p[k] for k in IDM}) <= 0.0
        gaps.append(g)
    e1 = np.abs(gaps[0] - gaps[1])
    e2 = np.abs(gaps[1] - gaps[2])
    assert np.all((e1 / e2 > 1.6) & (e1 / e2 < 2.5)), e1 / e2


def test_reaction_delay_holds_acceleration():
    dt, delay, t_change = 0.05, 1.0, 10.0
    lead = lambda t: 10.0 if t <= t_change else 6.0                        # noqa: E731
    r = D.idm_platoon_simulate(lead, 1, params_per_vehicle=dict(IDM), dt=dt, t_end=20.0, reaction_delay=delay)
    m = int(r["delay_steps"][0])
    assert m == 20
    k_change = int(round(t_change / dt))          # 先頭の位置が変わり始めるのは k_change + 1 から
    a1 = r["a"][:, 1]
    # 平衡から始めるので先頭の変化を見るまでは加速度 ≈ 0(位置の差の丸めで 1e-15 の桁だけ揺れる)
    assert np.all(np.abs(a1[: k_change + m + 1]) < 1e-12)
    assert abs(a1[k_change + m + 1]) > 1e-3
    # 遅れ 0 なら 1 刻みで反応する
    r0 = D.idm_platoon_simulate(lead, 1, params_per_vehicle=dict(IDM), dt=dt, t_end=20.0)
    assert np.all(np.abs(r0["a"][: k_change + 1, 1]) < 1e-12) and abs(r0["a"][k_change + 1, 1]) > 1e-3


def test_platoon_speed_noise_needs_seed_and_is_deterministic():
    p = dict(IDM, speed_noise=0.05)
    lead = lambda t: 8.0                                                    # noqa: E731
    with pytest.raises(ValueError, match="seed"):
        D.idm_platoon_simulate(lead, 2, params_per_vehicle=p, dt=0.1, t_end=5.0)
    r1 = D.idm_platoon_simulate(lead, 2, params_per_vehicle=p, dt=0.1, t_end=5.0, seed=7)
    r2 = D.idm_platoon_simulate(lead, 2, params_per_vehicle=p, dt=0.1, t_end=5.0, seed=7)
    assert np.array_equal(r1["x"], r2["x"])
    assert r1["params"][0]["v0"] != r1["params"][1]["v0"]


def test_idm_fail_closed():
    with pytest.raises(ValueError, match="idm_accel"):
        D.idm_accel(-1.0, 10.0, 0.0, **IDM)
    with pytest.raises(ValueError, match="idm_accel"):
        D.idm_accel(1.0, 0.0, 0.0, **IDM)
    with pytest.raises(ValueError, match="idm_equilibrium_gap"):
        D.idm_equilibrium_gap(15.0, v0=15.0, T=1.5, s0=2.0)
    with pytest.raises(ValueError, match="idm_platoon_simulate"):
        D.idm_platoon_simulate(lambda t: 5.0, 2, params_per_vehicle=[IDM], dt=0.1, t_end=1.0)
    with pytest.raises(ValueError, match="idm_platoon_simulate"):
        D.idm_platoon_simulate(lambda t: 5.0, 1, params_per_vehicle={"v0": 10.0}, dt=0.1, t_end=1.0)


# ---- 4. 運転の癖 -------------------------------------------------------------------------------------
def test_driver_style_ordering_and_determinism():
    c, n, s = (D.driver_style(k) for k in D.DRIVER_KINDS)
    assert c["T"] > n["T"] > s["T"] and c["s0"] > n["s0"] > s["s0"]
    assert c["reaction_delay"] < n["reaction_delay"] < s["reaction_delay"]
    sd = [x["wobble_sigma"] / math.sqrt(2 * x["wobble_theta"]) for x in (c, n, s)]
    assert sd[0] < sd[1] < sd[2]
    assert D.driver_style("normal", seed=3) == D.driver_style("normal", seed=3)
    assert D.driver_style("normal", seed=3) != D.driver_style("normal", seed=4)
    j = D.driver_style("normal", seed=3)
    assert 0.9 * n["T"] <= j["T"] <= 1.1 * n["T"]
    with pytest.raises(ValueError, match="driver_style"):
        D.driver_style("reckless")


# ---- 5. OU ------------------------------------------------------------------------------------------
def _acf(x, j):
    x = x - x.mean()
    return float(np.dot(x[:-j], x[j:]) / np.dot(x, x))


@pytest.mark.parametrize("dt", [0.1, 0.5])
def test_ou_stationary_variance_and_autocorrelation(dt):
    theta, sigma, n = 0.5, 0.2, 200_000
    x = D.lateral_wobble(n, dt, theta=theta, sigma=sigma, seed=11)
    var_true = sigma ** 2 / (2 * theta)
    phi = math.exp(-theta * dt)
    # 標本分散の標準誤差(AR(1)、ガウス): sqrt(2/n · (1 + φ²)/(1 − φ²)) · var
    se_var = var_true * math.sqrt(2.0 / n * (1 + phi ** 2) / (1 - phi ** 2))
    assert abs(np.var(x) - var_true) < 5 * se_var
    # Euler–Maruyama の定常分散 σ²/(2θ − θ²dt) はこの幅で落ちる(dt = 0.5 のとき)= 門が離散化の違いを見分ける
    if dt == 0.5:
        assert abs(sigma ** 2 / (2 * theta - theta ** 2 * dt) - var_true) > 5 * se_var
    for tau in (1.0, 2.0, 4.0):
        j = int(round(tau / dt))
        rho = math.exp(-theta * tau)
        # Bartlett: Var(r_j) ≈ (1/n)[(1 + φ²)(1 − φ^{2j})/(1 − φ²) − 2 j φ^{2j}]
        se = math.sqrt(((1 + phi ** 2) * (1 - phi ** (2 * j)) / (1 - phi ** 2) - 2 * j * phi ** (2 * j)) / n)
        assert abs(_acf(x, j) - rho) < 5 * se, (tau, _acf(x, j), rho, se)


def test_ou_determinism_and_fail_closed():
    a = D.lateral_wobble(100, 0.1, theta=1.0, sigma=0.1, seed=5)
    b = D.lateral_wobble(100, 0.1, theta=1.0, sigma=0.1, seed=5)
    assert np.array_equal(a, b)
    z = D.lateral_wobble(50, 0.1, theta=1.0, sigma=0.0, seed=1, x0=1.0)
    np.testing.assert_allclose(z, np.exp(-1.0 * 0.1 * np.arange(50)), rtol=1e-12)
    with pytest.raises(ValueError, match="lateral_wobble"):
        D.lateral_wobble(10, 0.1, theta=0.0, sigma=0.1, seed=1)


# ---- 6. social force -------------------------------------------------------------------------------
@pytest.mark.parametrize("dt", [0.1, 0.37])
def test_social_force_single_pedestrian_closed_form(dt):
    v0, tau = 1.3, 0.5
    P = np.array([[0.0, 0.0]])
    V = np.zeros((1, 2))
    G = np.array([[1000.0, 0.0]])
    for k in range(1, 30):
        P, V = D.social_force_step(P, V, G, dt=dt, v0=v0, tau=tau, A=25.0, B=0.08, radius=0.3)
        t = k * dt
        assert V[0, 0] == pytest.approx(v0 * (1 - math.exp(-t / tau)), rel=1e-12)
        assert P[0, 0] == pytest.approx(v0 * (t - tau * (1 - math.exp(-t / tau))), rel=1e-12)
        assert P[0, 1] == 0.0 and V[0, 1] == 0.0


def test_social_force_matches_fine_euler():
    """独立な積分器(前進 Euler、dt = 1e-4)で同じ 1 人を走らせ、閉形式・指数積分と 1e-4 の桁で一致。"""
    v0, tau, dt, T = 1.3, 0.5, 1e-4, 1.0
    v = x = 0.0
    for _ in range(int(round(T / dt))):
        a = (v0 - v) / tau
        x += v * dt
        v += a * dt
    P, V = np.array([[0.0, 0.0]]), np.zeros((1, 2))
    for _ in range(10):
        P, V = D.social_force_step(P, V, np.array([[50.0, 0.0]]), dt=0.1, v0=v0, tau=tau, A=0.0, B=0.1, radius=0.3)
    assert abs(V[0, 0] - v) < 1e-3 and abs(P[0, 0] - x) < 1e-3


def test_social_force_head_on_point_symmetry():
    P = np.array([[-5.0, 0.1], [5.0, -0.1]])
    V = np.zeros((2, 2))
    G = np.array([[5.0, 0.1], [-5.0, -0.1]])
    for _ in range(300):
        P, V = D.social_force_step(P, V, G, dt=0.05, v0=1.3, tau=0.5, A=25.0, B=0.08, radius=0.3)
        np.testing.assert_allclose(P[1], -P[0], atol=1e-12, rtol=0)
        np.testing.assert_allclose(V[1], -V[0], atol=1e-12, rtol=0)
    assert P[0, 0] > 4.5 and P[1, 0] < -4.5          # すれ違えた


def test_social_force_corridor_mirror_symmetry():
    walls = np.array([[[-10, 2.0], [30, 2.0]], [[-10, -2.0], [30, -2.0]]])
    P = np.array([[0.0, 0.4], [0.0, -0.4]])
    V = np.zeros((2, 2))
    G = np.array([[20.0, 0.4], [20.0, -0.4]])
    for _ in range(200):
        P, V = D.social_force_step(P, V, G, dt=0.05, v0=[1.2, 1.2], tau=0.5, A=25.0, B=0.08,
                                   radius=[0.3, 0.3], walls=walls)
        np.testing.assert_allclose(P[1] * [1, -1], P[0], atol=1e-12, rtol=0)
    assert np.all(np.abs(P[:, 1]) < 2.0)


def test_social_force_first_order_convergence():
    def run(dt):
        P = np.array([[-3.0, 0.05], [3.0, -0.05]])
        V = np.zeros((2, 2))
        G = np.array([[3.0, 0.05], [-3.0, -0.05]])
        for _ in range(int(round(4.0 / dt))):
            P, V = D.social_force_step(P, V, G, dt=dt, v0=1.3, tau=0.5, A=5.0, B=0.3, radius=0.3)
        return P
    p1, p2, p3 = run(0.02), run(0.01), run(0.005)
    e1, e2 = np.linalg.norm(p1 - p2), np.linalg.norm(p2 - p3)
    assert 1.6 < e1 / e2 < 2.5, (e1, e2)


def test_social_force_fail_closed():
    with pytest.raises(ValueError, match="social_force_step"):
        D.social_force_step(np.zeros((2, 2)), np.zeros((2, 2)), np.ones((2, 2)), dt=0.1, v0=1.0, tau=0.5,
                            A=1.0, B=0.1, radius=0.3)
    with pytest.raises(ValueError, match="social_force_step"):
        D.social_force_step(np.zeros((1, 3)), np.zeros((1, 3)), np.ones((1, 3)), dt=0.1, v0=1.0, tau=0.5,
                            A=1.0, B=0.1, radius=0.3)


# ---- 7. 横断の意図 -----------------------------------------------------------------------------------
def test_crossing_intents_ground_truth():
    W, co, sp = 7.0, 0.3, 1.2
    c = D.pedestrian_crossing("cross", start_xy=(2.0, -3.0), road_width=W, curb_offset=co, speed=sp, dt=0.01)
    w = D.pedestrian_crossing("wait_then_cross", start_xy=(2.0, -3.0), road_width=W, curb_offset=co, speed=sp,
                              wait_time=3.0, dt=0.01)
    a = D.pedestrian_crossing("walk_along", start_xy=(2.0, -3.0), speed=sp, dt=0.01, along_heading=math.pi)
    for r in (c, w):
        assert r["t_cross_end"] - r["t_cross_start"] == pytest.approx((W + 2 * co) / sp, rel=1e-12)
        # 横断の段の速さ(差分)= sp、終わりは向こうの縁
        cr = r["phase"] == "cross"
        vy = np.diff(r["xy"][:, 1])[cr[:-1] & cr[1:]] / 0.01
        np.testing.assert_allclose(vy, sp, rtol=1e-9)
        assert r["xy"][-1, 1] == pytest.approx(W + co)
    assert c["intent"] == "cross" and not np.any(c["phase"] == "wait")
    wait = w["phase"] == "wait"
    assert abs(wait.sum() * 0.01 - 3.0) <= 0.011
    assert np.all(w["xy"][wait, 1] == -co) and np.all(w["heading"][wait] == math.pi / 2)
    assert w["t_cross_start"] - c["t_cross_start"] == pytest.approx(3.0)
    assert np.all(a["xy"][:, 1] < 0) and np.all(a["phase"] == "along")
    d = np.diff(a["xy"], axis=0)
    np.testing.assert_allclose(np.arctan2(d[:, 1], d[:, 0]), a["heading"][1:], atol=1e-12)
    with pytest.raises(ValueError, match="pedestrian_crossing"):
        D.pedestrian_crossing("jaywalk")
    with pytest.raises(ValueError, match="pedestrian_crossing"):
        D.pedestrian_crossing("cross", start_xy=(0.0, 1.0))


# ---- 8. 死角 ------------------------------------------------------------------------------------------
BOX = (12.5, 2.5, 5.0, 2.0, 0.0)            # x ∈ [10, 15], y ∈ [1.5, 3.5]


def test_occlusion_axis_aligned_hand_formula():
    for e in [(16.0, 3.0), (15.5, 2.0), (17.0, 3.4)]:
        c = (15.0, 1.5)
        expect = (e[0] - c[0]) * e[1] / (e[1] - c[1])
        assert D.occlusion_reveal_distance((0.0, 0.0), 0.0, BOX, e) == pytest.approx(expect, rel=1e-9)
    # 見えている点(箱より手前の高さ 1.0)は s = 0 の縦距離
    assert D.occlusion_reveal_distance((0.0, 0.0), 0.0, BOX, (16.0, 1.0)) == pytest.approx(16.0)
    assert D.occlusion_reveal_distance((0.0, 0.0), 0.0, BOX, (12.0, 2.5)) == math.inf


@pytest.mark.parametrize("ang", [0.3, 1.0, 2.0, 3.0, -1.2, 4.5])
def test_occlusion_rotation_invariance(ang):
    c, s = math.cos(ang), math.sin(ang)
    Rm = np.array([[c, -s], [s, c]])
    off = np.array([3.0, -7.0])
    tr = lambda p: Rm @ np.asarray(p) + off                               # noqa: E731
    box = (*tr(BOX[:2]), BOX[2], BOX[3], BOX[4] + ang)
    d = D.occlusion_reveal_distance(tr((0.0, 0.0)), ang, box, tr((16.0, 3.0)))
    assert d == pytest.approx(2.0, rel=1e-9)


def _brute_reveal(ego, psi, box, e, ds=0.005, s_max=30.0, n_samp=4000):
    cx, cy, L, Wd, yaw = box
    h = np.array([math.cos(psi), math.sin(psi)])
    c, s_ = math.cos(yaw), math.sin(yaw)
    u = np.linspace(0, 1, n_samp)
    for s in np.arange(0, s_max, ds):
        p = np.asarray(ego) + s * h
        q = p[None, :] + u[:, None] * (np.asarray(e) - p)[None, :]
        lx = c * (q[:, 0] - cx) + s_ * (q[:, 1] - cy)
        ly = -s_ * (q[:, 0] - cx) + c * (q[:, 1] - cy)
        if not np.any((np.abs(lx) < L / 2) & (np.abs(ly) < Wd / 2)):
            return float(h @ (np.asarray(e) - p))
    return math.inf


def test_occlusion_matches_brute_force():
    rng = np.random.default_rng(23)
    checked = 0
    for _ in range(6):
        yaw = rng.uniform(-0.3, 0.3)
        box = (rng.uniform(10, 14), rng.uniform(2.2, 3.0), rng.uniform(4, 5.5), rng.uniform(1.7, 2.0), yaw)
        corners_front = box[0] + box[2] / 2 * math.cos(yaw)
        e = (corners_front + rng.uniform(0.3, 1.5), box[1] + rng.uniform(-0.3, 0.6))
        d = D.occlusion_reveal_distance((0.0, 0.0), 0.05, box, e)
        db = _brute_reveal((0.0, 0.0), 0.05, box, e)
        assert abs(d - db) < 0.05, (box, e, d, db)
        checked += math.isfinite(d)
    assert checked == 6


def test_occlusion_safe_speed_against_rss_and_drivelong():
    for d in [0.01, 0.5, 2.0, 7.3, 25.0, 120.0]:
        for rho in [0.0, 0.5, 1.0, 1.5]:
            for b in [3.0, 6.0, 8.0]:
                v = D.occlusion_safe_speed(d, reaction=rho, brake=b)
                assert R.rss_stopping_distance(v, rho, 0.0, b) == pytest.approx(d, rel=1e-12)
                assert DL.stopping_distance_grade(v, rho, b) == pytest.approx(d, rel=1e-12)
    assert D.occlusion_safe_speed(0.0, reaction=1.0, brake=6.0) == 0.0
    assert D.occlusion_safe_speed(-1.0, reaction=1.0, brake=6.0) == 0.0
    v = D.occlusion_safe_speed(np.array([1e-12, 1.0]), reaction=1.0, brake=6.0)
    assert v[0] == pytest.approx(1e-12, rel=1e-9)        # 桁落ちしない(v ≈ d/ρ)
    # 死角から 2 m で見えた人の前に止まれる速度(ρ = 0.75 s、b = 6)— 約 2.4 m/s ≈ 8.6 km/h
    d = D.occlusion_reveal_distance((0.0, 0.0), 0.0, BOX, (16.0, 3.0))
    assert 2.0 < D.occlusion_safe_speed(d, reaction=0.75, brake=6.0) < 2.6
    with pytest.raises(ValueError, match="occlusion_safe_speed"):
        D.occlusion_safe_speed(1.0, reaction=1.0, brake=0.0)


# ---- 10. はみ出し ------------------------------------------------------------------------------------
PASS = dict(parked_len=5.0, margin_front=3.0, margin_back=5.0, v_ego=8.0, v_oncoming=10.0)


def test_passing_closed_form_and_switch():
    r = D.passing_gap_required(**PASS, lane_change_time=2.0)
    assert r["t_occupy"] == pytest.approx(13.0 / 8.0 + 2.0)
    assert r["d_required"] == pytest.approx((13.0 / 8.0 + 2.0) * 18.0)
    Ds = r["d_required"]
    args = (PASS["parked_len"], PASS["margin_front"], PASS["margin_back"], PASS["v_ego"], PASS["v_oncoming"])
    assert D.passing_decision(Ds, *args, lane_change_time=2.0) == "go"
    assert D.passing_decision(Ds * (1 + 1e-9), *args, lane_change_time=2.0) == "go"
    assert D.passing_decision(Ds * (1 - 1e-9), *args, lane_change_time=2.0) == "wait"


@pytest.mark.parametrize("ve, vo, tlc, el", [(8.0, 10.0, 2.0, 0.0), (5.0, 14.0, 1.5, 4.5), (12.0, 3.0, 0.0, 4.0)])
def test_passing_simulation_boundary_matches_closed_form(ve, vo, tlc, el):
    kw = dict(lane_change_time=tlc, ego_length=el)
    args = (5.0, 3.0, 5.0, ve, vo)
    Ds = D.passing_gap_required(*args, **kw)["d_required"]
    pet = lambda Dd: D.passing_simulate(Dd, *args, dt=0.013, **kw)["pet"]   # noqa: E731
    lo, hi = 1.0, 500.0
    assert pet(lo) < 0 < pet(hi)
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if pet(mid) < 0 else (lo, mid)
    assert 0.5 * (lo + hi) == pytest.approx(Ds, rel=1e-6)
    # go の判断なら PET ≥ 0、wait 側(D* の 1% 手前)で go にすると PET < 0
    assert pet(Ds * 1.01) > 0 and pet(Ds * 0.99) < 0


def test_passing_pet_min_shifts_boundary():
    r0 = D.passing_gap_required(**PASS, lane_change_time=2.0)
    r1 = D.passing_gap_required(**PASS, lane_change_time=2.0, pet_min=1.5)
    assert r1["d_required"] - r0["d_required"] == pytest.approx(1.5 * PASS["v_oncoming"])
    with pytest.raises(ValueError, match="passing_gap_required"):
        D.passing_gap_required(5.0, 3.0, 5.0, 0.0, 10.0, lane_change_time=2.0)


# ---- 11. ポアソン ------------------------------------------------------------------------------------
BUS = dict(bus_rear=40.0, bus_front=52.0, base=0.002, peak=0.05, spread=3.0)
X_MAX = 100.0


def _lam(x):
    return D.bus_stop_rate(x, **BUS)


def _Lambda(fn, a=0.0, b=X_MAX, n=200_001):
    xg = np.linspace(a, b, n)
    y = fn(xg)
    return float(np.sum(0.5 * (y[1:] + y[:-1]) * np.diff(xg)))


def test_poisson_mean_equals_variance_equals_integral():
    rmax = BUS["base"] + 2 * BUS["peak"]
    Lam = _Lambda(_lam)
    rng = np.random.default_rng(101)
    n = 40_000
    counts = np.empty(n)
    pos = []
    for i in range(n):
        ev = D.poisson_events(_lam, X_MAX, rate_max=rmax, seed=rng)
        counts[i] = ev.size
        pos.append(ev)
    se_mean = math.sqrt(Lam / n)
    se_var = math.sqrt((Lam + 2 * Lam ** 2) / n)        # Poisson: μ4 = Λ + 3Λ²
    assert abs(counts.mean() - Lam) < 5 * se_mean
    assert abs(counts.var(ddof=1) - Lam) < 5 * se_var
    # 位置の分布 = λ/Λ(KS 統計、臨界値 1.95/sqrt(N) ≈ α 0.001)
    allx = np.sort(np.concatenate(pos))
    xg = np.linspace(0, X_MAX, 200_001)
    yg = _lam(xg)
    cdf = np.concatenate([[0.0], np.cumsum(0.5 * (yg[1:] + yg[:-1]) * np.diff(xg))]) / Lam
    F = np.interp(allx, xg, cdf)
    N = allx.size
    ks = max(np.max(np.arange(1, N + 1) / N - F), np.max(F - np.arange(N) / N))
    assert ks < 1.95 / math.sqrt(N)


def test_poisson_fail_closed_and_deterministic():
    with pytest.raises(ValueError, match="rate_max"):        # 一定率 1 > 上限 0.5(候補 ≈ 50 個のどれでも違反)
        D.poisson_events(lambda x: np.ones_like(x), X_MAX, rate_max=0.5, seed=1)
    a = D.poisson_events(_lam, X_MAX, rate_max=0.2, seed=9)
    b = D.poisson_events(_lam, X_MAX, rate_max=0.2, seed=9)
    assert np.array_equal(a, b) and np.all(np.diff(a) >= 0)


# ---- 12. 重要度サンプリング -------------------------------------------------------------------------------
LOW = dict(bus_rear=40.0, bus_front=52.0, base=0.0005, peak=0.002, spread=3.0)
WIN = (50.0, 56.0)                       # バスの前端のすぐ先 = 自車が止まれない区間(例)


def _low(x):
    return D.bus_stop_rate(x, **LOW)


def _boost(x):
    x = np.asarray(x, dtype=float)
    return _low(x) * np.where((x >= WIN[0] - 2) & (x <= WIN[1] + 2), 20.0, 1.0)


def _accident(ev, rng):
    return float(np.any((ev >= WIN[0]) & (ev <= WIN[1])))


def test_importance_sampling_matches_closed_form_and_naive():
    p_true = 1.0 - math.exp(-_Lambda(_low, *WIN))
    rmax_low = LOW["base"] + 2 * LOW["peak"]
    naive = D.importance_risk_estimate(_accident, _low, _low, 40_000, 5, x_max=X_MAX, boosted_rate_max=rmax_low)
    imp = D.importance_risk_estimate(_accident, _low, _boost, 4_000, 6, x_max=X_MAX,
                                     boosted_rate_max=20 * rmax_low)
    assert naive["mean_weight"] == 1.0
    assert abs(naive["estimate"] - p_true) < 4.5 * naive["std_error"]
    assert abs(imp["estimate"] - p_true) < 4.5 * imp["std_error"]
    assert abs(imp["estimate"] - naive["estimate"]) < 4.5 * math.hypot(imp["std_error"], naive["std_error"])
    # 1 試行あたりの分散は IS の方が小さく、試行 1/10 で標準誤差も小さい
    assert imp["per_run_var"] < naive["per_run_var"] / 5
    assert imp["std_error"] < naive["std_error"]
    # 重みの平均 ≈ 1(E_λ'[w] = 1)。重みの分布が広い分 ESS < n
    assert abs(imp["mean_weight"] - 1.0) < 0.1
    assert imp["ess"] < 4_000


def test_importance_fail_closed():
    zero_win = lambda x: np.where(np.asarray(x) < 50, _low(x), 0.0)        # noqa: E731
    with pytest.raises(ValueError, match="absolutely continuous"):
        D.importance_risk_estimate(_accident, _low, zero_win, 10, 1, x_max=X_MAX, boosted_rate_max=1.0)
    with pytest.raises(ValueError, match="importance_risk_estimate"):
        D.importance_risk_estimate(lambda ev, rng: 2.0, _low, _low, 10, 1, x_max=X_MAX, boosted_rate_max=1.0)


def test_delay_longer_than_headway_destabilises_platoon():
    """観察(門として固定): 反応遅れが車間時間 T を超える sloppy(T 1.0 s、遅れ 1.3 s)は、先頭が 10 → 8 m/s に
    落としただけで振動が後ろへ育って衝突する。careful・normal(遅れ < T)は同じ入力で平衡に収束する。"""
    lead = lambda t: 10.0 if t < 20 else 8.0                                # noqa: E731
    out = {}
    for k in D.DRIVER_KINDS:
        p = dict(D.driver_style(k), speed_noise=0.0)
        r = D.idm_platoon_simulate(lead, 3, params_per_vehicle=p, dt=0.05, t_end=300.0)
        before = (r["t"] >= 20.0) & (r["t"] < (r["collision_time"] if r["collision"] else np.inf))
        out[k] = (r["collision"], np.ptp(r["v"][-1000:, 1:], axis=0), np.ptp(r["v"][before, 1:], axis=0))
    for k in ("careful", "normal"):
        assert not out[k][0] and np.all(out[k][1] < 1e-6)
    assert out["sloppy"][0]
    # 追突の前の速度の振れ: 2 台目 > 1 台目 > 1 m/s(後ろへ育つ。3 台目は育ち切る前に追突して止まる)
    assert out["sloppy"][2][1] > out["sloppy"][2][0] > 1.0


# ==== r23 第 2 段: 足した op(PoC の補いを op に移したもの) ===================================================
def _vis_point_sampling(p, e, box, n_samp=4000):
    """線分 p → e 上の点を細かく撒いて箱の内部に入るかを見る(閉形式・スラブ法と独立な総当たり)。"""
    cx, cy, L, Wd, yaw = box
    c, s_ = math.cos(yaw), math.sin(yaw)
    u = np.linspace(0, 1, n_samp)
    q = np.asarray(p)[None, :] + u[:, None] * (np.asarray(e) - np.asarray(p))[None, :]
    lx = c * (q[:, 0] - cx) + s_ * (q[:, 1] - cy)
    ly = -s_ * (q[:, 0] - cx) + c * (q[:, 1] - cy)
    return not np.any((np.abs(lx) < L / 2) & (np.abs(ly) < Wd / 2))


def test_poisson_grid_check_catches_narrow_peak_that_candidates_miss():
    """候補点だけの検査は狭い山(高さ 10、幅 0.1、上限 0.5)を外すことがある → 引く前の格子の検査で必ず止める。"""
    spike = lambda x: 0.01 + 10.0 * np.exp(-0.5 * ((np.asarray(x) - 50.0) / 0.1) ** 2)   # noqa: E731
    missed = 0
    for seed in range(20):
        with pytest.raises(ValueError, match="check grid"):
            D.poisson_events(spike, X_MAX, rate_max=0.5, seed=seed)
        try:                                                   # 候補だけの検査(内部)は見逃す seed がある = 門が自明でない
            D._thinning(spike, X_MAX, 0.5, np.random.default_rng(seed), "probe")
            missed += 1
        except ValueError:
            pass
    assert missed > 0
    with pytest.raises(ValueError, match="n_grid"):
        D.poisson_events(_lam, X_MAX, rate_max=1.0, seed=1, n_grid=1)
    with pytest.raises(ValueError, match="boosted_rate_max"):
        D.importance_risk_estimate(_accident, _low, spike, 10, 1, x_max=X_MAX, boosted_rate_max=0.5)


XT = dict(rear=40.0, front=52.0, base=2e-3, peak=0.02, spread=2.0, t_dep=6.0, X=100.0, T=10.0)


def _lam_xt(x, t):
    b = XT
    g = D.bus_stop_rate(x, bus_rear=b["rear"], bus_front=b["front"], base=0.0, peak=b["peak"], spread=b["spread"])
    return b["base"] + g * (np.asarray(t) < b["t_dep"])


def test_poisson_xt_count_and_marginals():
    b = XT
    lam_bus = b["peak"] * b["spread"] * math.sqrt(2 * math.pi) * 2 * b["t_dep"]     # 山は [0, X] の十分内側
    Lam = b["base"] * b["X"] * b["T"] + lam_bus
    rng = np.random.default_rng(31)
    rmax = b["base"] + 2 * b["peak"]
    N = 4000
    n = np.empty(N)
    early = 0
    for i in range(N):
        ev = D.poisson_events_xt(_lam_xt, b["X"], b["T"], rate_max=rmax, seed=rng, n_grid=(101, 21))
        assert ev.shape[1] == 2 and np.all(np.diff(ev[:, 1]) >= 0)
        assert np.all((ev[:, 0] >= 0) & (ev[:, 0] <= b["X"]) & (ev[:, 1] >= 0) & (ev[:, 1] <= b["T"]))
        n[i] = len(ev)
        early += int(np.sum(ev[:, 1] < b["t_dep"]))
    assert abs(n.mean() - Lam) < 5 * math.sqrt(Lam / N)
    assert abs(n.var(ddof=1) - Lam) < 5 * math.sqrt((Lam + 2 * Lam ** 2) / N)
    # 時刻の周辺: 発車前に出る割合 = (base X t_dep + 山の分) / Λ
    p_early = (b["base"] * b["X"] * b["t_dep"] + lam_bus) / Lam
    tot = n.sum()
    assert abs(early / tot - p_early) < 5 * math.sqrt(p_early * (1 - p_early) / tot)
    with pytest.raises(ValueError, match="check grid"):
        D.poisson_events_xt(_lam_xt, b["X"], b["T"], rate_max=0.5 * rmax, seed=1)
    with pytest.raises(ValueError, match="poisson_events_xt"):
        D.poisson_events_xt(_lam_xt, b["X"], 0.0, rate_max=rmax, seed=1)


@pytest.mark.parametrize("vb", [0.0, 2.0, 4.0])
def test_passing_moving_obstacle_matches_simulation(vb):
    kw = dict(lane_change_time=2.0, ego_length=4.5, v_obstacle=vb)
    args = (1.8, 2.0, 2.0, 8.33, 11.1)
    Ds = D.passing_gap_required(*args, **kw)["d_required"]
    L_occ = 1.8 + 2.0 + 2.0 + 4.5
    assert Ds == pytest.approx((L_occ / (8.33 - vb) + 2.0) * (8.33 + 11.1), rel=1e-14)
    pet = lambda Dd: D.passing_simulate(Dd, *args, dt=0.011, **kw)["pet"]           # noqa: E731
    lo, hi = 1.0, 800.0
    assert pet(lo) < 0 < pet(hi)
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if pet(mid) < 0 else (lo, mid)
    assert 0.5 * (lo + hi) == pytest.approx(Ds, rel=1e-6)
    assert D.passing_decision(Ds * (1 + 1e-9), *args, **kw) == "go"
    assert D.passing_decision(Ds * (1 - 1e-9), *args, **kw) == "wait"
    with pytest.raises(ValueError, match="v_obstacle"):
        D.passing_gap_required(*args, lane_change_time=2.0, v_obstacle=8.33)


def test_passing_decision_accepts_no_oncoming():
    assert D.passing_decision(math.inf, **PASS, lane_change_time=2.0) == "go"
    for bad in (-math.inf, math.nan):
        with pytest.raises(ValueError, match="passing_decision"):
            D.passing_decision(bad, **PASS, lane_change_time=2.0)
    with pytest.raises(ValueError, match="passing_gap_required"):            # inf でも他の引数は検査する
        D.passing_decision(math.inf, 5.0, 3.0, 5.0, 0.0, 10.0, lane_change_time=2.0)


def test_occlusion_visible_intervals_visible_hidden_visible():
    """歩道の点 (17, 4.0) は遠く(x = −100)からは箱の外(y > 3.5)を通る視線で見え、近づくと隠れ、また見える。"""
    e = (17.0, 4.0)
    ego, s_max = (-100.0, 0.0), 117.0
    iv = D.occlusion_visible_intervals(ego, 0.0, BOX, e, s_max)
    assert len(iv) == 2 and iv[0][0] == 0.0 and iv[0][1] < iv[1][0] and iv[1][1] == s_max
    # 総当たり(点の撒き)と区間の内外が一致(端から 1e-3 以上離れた s で)
    for s in np.linspace(0.0, s_max, 600):
        if min(abs(s - x) for ab in iv for x in ab) < 1e-3:
            continue
        inside = any(a <= s <= b for a, b in iv)
        assert inside == _vis_point_sampling((ego[0] + s, 0.0), e, BOX), s
    # 2 つ目の区間の始まり = 隠れた所から出発した occlusion_reveal_distance
    s_h = 0.5 * (iv[0][1] + iv[1][0])
    d = D.occlusion_reveal_distance((ego[0] + s_h, 0.0), 0.0, BOX, e)
    assert d == pytest.approx(e[0] - (ego[0] + iv[1][0]), rel=1e-9)
    # 箱の帯の中の点は 1 区間、箱の内部は []
    assert len(D.occlusion_visible_intervals((0.0, 0.0), 0.0, BOX, (16.0, 3.0), 16.0)) == 1
    assert D.occlusion_visible_intervals((0.0, 0.0), 0.0, BOX, (12.0, 2.5), 30.0) == []
    with pytest.raises(ValueError, match="occlusion_visible_intervals"):
        D.occlusion_visible_intervals((0.0, 0.0), 0.0, BOX, e, 0.0)


@pytest.mark.parametrize("dt", [0.1, 0.5])
def test_ou_estimate_recovers_parameters(dt):
    th, sg = 0.4, 0.12
    x = D.lateral_wobble(50_000, dt, theta=th, sigma=sg, seed=77)
    est = D.ou_estimate(x, dt)
    assert abs(est["theta"] - th) < 5 * est["se_theta"]
    assert abs(est["sigma"] - sg) < 5 * est["se_sigma"]
    assert est["sd"] == pytest.approx(est["sigma"] / math.sqrt(2 * est["theta"]))
    # 増分の粗い推定は E[Δx²] = σ²(1 − φ)/θ に従う(dt = 0.5 で 10% 小さい)
    assert est["sigma_increment"] == pytest.approx(sg * math.sqrt((1 - math.exp(-th * dt)) / (th * dt)), rel=0.02)


def test_ou_estimate_standard_errors_match_spread():
    th, sg, dt = 0.25, 0.2, 0.1
    ests = [D.ou_estimate(D.lateral_wobble(3000, dt, theta=th, sigma=sg, seed=500 + i), dt) for i in range(300)]
    for key in ("theta", "sigma"):
        v = np.array([e[key] for e in ests])
        se = np.mean([e["se_" + key] for e in ests])
        assert 0.75 < v.std(ddof=1) / se < 1.33, key
    with pytest.raises(ValueError, match="ou_estimate"):
        D.ou_estimate(np.array([1.0, -1.0] * 50), 0.1)             # φ̂ < 0
    with pytest.raises(ValueError, match="ou_estimate"):
        D.ou_estimate(np.zeros(10), 0.1)
    with pytest.raises(ValueError, match="ou_estimate"):
        D.ou_estimate(np.ones((3, 3)), 0.1)


def test_crossing_stand_no_cross():
    co, sp = 0.3, 1.2
    r = D.pedestrian_crossing("stand_no_cross", start_xy=(1.0, -3.0), curb_offset=co, speed=sp, dt=0.01)
    t_app = (3.0 - co) / sp
    assert r["intent"] == "stand_no_cross" and r["t_cross_start"] is None and r["t_cross_end"] is None
    assert r["t"][-1] == pytest.approx(t_app + 10.0, abs=0.011)
    assert not np.any(r["phase"] == "cross") and not np.any(r["phase"] == "done")
    st = r["phase"] == "wait"
    assert abs(st.sum() * 0.01 - 10.0) <= 0.011
    assert np.all(r["xy"][st, 1] == -co) and np.all(r["heading"][st] == math.pi / 2)
    w = D.pedestrian_crossing("wait_then_cross", start_xy=(1.0, -3.0), curb_offset=co, speed=sp, wait_time=5.0, dt=0.01)
    k = int(round((t_app + 2.0) / 0.01))                        # 待ちの途中は wait_then_cross と見分けがつかない
    np.testing.assert_array_equal(r["xy"][:k], w["xy"][:k])
    np.testing.assert_array_equal(r["heading"][:k], w["heading"][:k])


def test_platoon_crash_stops_vehicle_without_overlap():
    lead = lambda t: 10.0 if t < 5.0 else 8.0                                   # noqa: E731
    r = D.idm_platoon_simulate(lead, 5, params_per_vehicle=dict(D.driver_style("sloppy"), speed_noise=0.0),
                               dt=0.05, t_end=120.0)
    assert r["collision"] and len(r["collisions"]) >= 2
    assert r["collision_time"] == r["collisions"][0][0]
    assert [c[0] for c in r["collisions"]] == sorted(c[0] for c in r["collisions"])
    assert np.all(r["gap"][:, 1:] >= -1e-9)                                     # 重ならない
    for tc, i in r["collisions"]:
        assert r["crashed"][i]
        after = r["t"] >= tc
        assert np.all(r["v"][after, i] == 0.0) and np.ptp(r["x"][after, i]) == 0.0
        k = int(np.argmax(after))
        assert r["gap"][k, i] == pytest.approx(0.0, abs=1e-9)                   # 接触の位置で止まる
    assert r["crashed"].sum() == len(r["collisions"])
