"""kendama の門(けん玉: 振り子の定理、弛み、振り上げ、段階を明示した捕球、画像の予測の部品)。

実行: ``py -3.11 -m pytest tests/test_kendama.py -q``。数値はすべて測った値(scratchpad の measure スクリプト)。

門の一覧:
 1. kendama_params: JKA 16-2 型(玉 60・横幅 70・全長 180 mm = 協会の公表値、けん 160 mm・皿 42 / 38 / 35 mm = ユーザー提供の説明)、
    推奨品(大皿 49 mm・穴 24 mm)、導いた値(ひもの有効長 = 糸 + r_b、穴の深さ 40 mm、皿の深さ = 玉の沈み + 1.5 mm)、技の姿勢
    (皿持ちでけん先が 15° 下、ろうそくの中皿は手元の 147 mm 上)、不正値の拒否
 2. elliptic_k_agm の公表値、pendulum_period_exact の小振幅極限
 4-5. 周期の定理 vs ひも(1e-3)・棒(1e-9)
 6-9. 張力の閉形式、弛む角の閉形式とシミュレーション、上半分に届かない振幅は弛まない
 10-11. エネルギー(1 次収束の散逸)と snap(ひもの有効長 0.42 m: 0.5867 s、0.237 J)、kendama_simulate = tether_simulate(点のけん)
 12-13. swing_up_plan の運動学、swing_up_apex の閉形式(lift 0.265 m: 頂点は手元の 8.4 cm 上)
 14. kendama_catch_check の幾何(r_c = 21 mm)と着地の窓(縁に最初に触れる高さ √(r_b² − (r_c − δ)²) + 3 mm)
 15. 段階を明示した制御で大皿を 4 件捕る(lift → wait → hold → carry → absorb → caught、けんに触れない、弛んだ後に昇って下降中に受ける)
 16. 同じ計画で大皿・小皿・中皿・ろうそく、着地で下げると相対速さが下がる
 17. けんは玉を押さない: 逃がさない振り上げは hit_ken(contact なしだと突き抜けて「捕れる」)
 18. 悪い計画は missed、時間切れは timeout
 19. catch_plan_ballistic の閉形式(面の計画)
 20. catch_success_rate(既定 = 段階の計画 + 逃がす + 自動の持ち上げ、接触は失敗): 真値 ≥ 0.9、1 ms ごとの独立な雑音は単調でない(正直に)
 21. catch_plan_staged の閉形式(hold の早い根、carry の遅い根と水平の目標、absorb の √(d/a)、新しい試行で取り直す)
 22. swing_up_lift は swing_up_apex の逆(1e-12)
 23. parabola_fit_g: 真空の標本から 1e-9、真上に投げた玉(水平速度 0)でも悪条件にならない
 24. hole_detect: 描いた玉の穴の角度・offset・楕円率、灰色の糸は穴にしない
 25. noisy_perceiver、fail-closed、抗力(60 mm・75 g の玉)、pendulum_launch_speed
"""
from __future__ import annotations

import math

import numpy as np
import pytest

import ballistics as B
import kendama as K

KP = K.kendama_params()
ZERO = (0.0, 0.0, 0.0)
UP = (0.0, 0.0, 1.0)
KV = K.kendama_params(rho=0.0, tie_offset=ZERO, cup_offset=ZERO, cup_axis=UP)          # 点のけん(支点 = 皿 = 手元): 定理の門
KV_NOCUP = K.kendama_params(rho=0.0, tie_offset=ZERO, cup_offset=(1.0, 0.0, 0.0), cup_axis=UP)   # 皿を 1 m 横に: 飛翔だけ見る
L = KP["pendulum_length"]
ORIGIN = np.zeros(3)
TIE = ORIGIN + KP["tie_offset"]                                           # 実物の形: 手元 = 皿胴の中心、支点 = 皿胴の糸穴


def _period_from_zero_crossings(t, x):
    """符号が変わる区間を線形補間して零交差時刻を取り、その間隔の平均 × 2 を周期に。"""
    idx = np.where(np.diff(np.sign(x)) != 0)[0]
    tc = np.array([t[i] - x[i] * (t[i + 1] - t[i]) / (x[i + 1] - x[i]) for i in idx])
    return 2.0 * float(np.mean(np.diff(tc))), int(tc.size)


def _angle_from_bottom(p, anchor=ORIGIN):
    d = np.asarray(p, float) - anchor
    return math.atan2(math.hypot(d[0], d[1]), -d[2])


def _hang(x=0.0, y=0.0, anchor=ORIGIN):
    """支点 anchor の真下 L に吊った玉(横に x, y ずらしても糸は張ったまま)。実物の形の kp では anchor = TIE。"""
    return np.asarray(anchor, float) + np.array([x, y, -math.sqrt(L * L - x * x - y * y)])


# ─────────────────────────────── 1-3 表と楕円積分 ───────────────────────────────

def test_kendama_params_published_dimensions_and_rejects():
    """既定 = JKA 16-2 型(玉 60・横幅 70・全長 180 mm は協会の公表値、けん 160 mm と皿 42 / 38 / 35 mm はユーザー提供の説明)、
    推奨品は大皿 49 mm・穴 24 mm。派生量(ひもの有効長 = 糸 + r_b、穴の深さ 40 mm、皿の深さ = 玉の沈み + 1.5 mm、姿勢の幾何)、fail-closed。"""
    assert KP["preset"] == "jka_16_2" and KP["ball_radius"] == 0.030 and KP["string"] == 0.39
    assert KP["pendulum_length"] == pytest.approx(0.42, abs=1e-15)
    assert KP["cup_radius_big"] == 0.021 and KP["cup_radius_base"] == 0.019 and KP["cup_radius_small"] == 0.0175
    assert KP["ken_length"] == 0.16 and KP["width"] == 0.070 and KP["mass"] == 0.075 and KP["ken_mass"] == 0.070
    assert KP["hole_depth"] == pytest.approx(0.040, abs=1e-15) and KP["total_length"] == pytest.approx(0.180, abs=1e-15)
    assert KP["hole_radius"] == 0.0085 and 0.140 <= KP["mass"] + KP["ken_mass"] <= 0.150
    assert KP["cup_depth"] == pytest.approx(0.03 - math.sqrt(0.03 ** 2 - 0.021 ** 2) + 0.0015, rel=1e-15)
    a15 = math.radians(15.0)                                                  # 大皿(皿持ち): けん先が 15° 下(仮定)
    assert np.allclose(KP["cup_offset"], [0.035 * math.sin(a15), 0.0, 0.035 * math.cos(a15)], atol=1e-15)
    assert np.allclose(KP["tie_offset"], [0.0, -0.013, 0.0], atol=1e-15)
    assert np.allclose(KP["cup_axis"], [math.sin(a15), 0.0, math.cos(a15)], atol=1e-15)
    assert KP["trick"] == "ozara" and KP["catch_cup"] == "big" and KP["cup_radius"] == KP["cup_radius_big"]
    ro = K.kendama_params(trick="rousoku")                                    # けん先をつまむ: 中皿は手元の 147 mm 上
    assert ro["catch_cup"] == "base" and ro["cup_offset"][2] == pytest.approx(0.1474, abs=1e-4) and ro["cup_radius"] == 0.019
    big = K.kendama_params("recommended_large_cup")
    assert big["cup_radius_big"] == 0.0245 and big["hole_radius"] == 0.012 and big["total_length"] == pytest.approx(0.18, abs=1e-15)
    assert KP["cup_rest_height"] == pytest.approx(math.sqrt(0.03 ** 2 - 0.021 ** 2), rel=1e-15)
    assert KP["bp"]["radius"] == 0.03 and KP["bp"]["mass"] == 0.075 and KP["bp"]["shell"] is False
    assert KP["bp"]["inertia"] == pytest.approx(0.4 * 0.075 * 0.03 ** 2, rel=1e-12)
    assert KV["bp"]["rho"] == 0.0 and KP["bp"]["rho"] == 1.2
    assert np.array_equal(K.kendama_params(cup_offset=(0.035, 0, 0))["cup_offset"], [0.035, 0, 0])
    bad = [dict(ball_radius=0.0), dict(mass=-1.0), dict(string=0.0), dict(cup_radius_big=0.03), dict(cup_radius_big=0.04),
           dict(width=0.04), dict(string=0.02), dict(cup_depth=-0.001), dict(ken_length=0.0), dict(g=0.0), dict(cup_offset=(1, 2)),
           dict(ball_radius=float("nan")), dict(ken_length=0.30), dict(tie_offset=(0, 0)), dict(cup_axis=(0, 0, 0))]
    assert len(bad) == 15
    for kw in bad:
        with pytest.raises(ValueError):
            K.kendama_params(**kw)
    with pytest.raises(ValueError):
        K.kendama_params("wooden_sword")
    with pytest.raises(ValueError):
        K.kendama_params(trick="moshikame")


def test_elliptic_k_published_values():
    """K(0) = π/2、K(0.5) = 1.685750354812596(m = 0.25 の公表値)、K(1/√2) = Γ(1/4)²/(4√π)、偶関数、単調増加、|k| ≥ 1 は拒否。"""
    assert K.elliptic_k_agm(0.0) == pytest.approx(math.pi / 2, rel=1e-15)
    assert K.elliptic_k_agm(0.5) == pytest.approx(1.685750354812596, rel=1e-14)
    assert K.elliptic_k_agm(1 / math.sqrt(2)) == pytest.approx(1.854074677301372, rel=1e-14)
    assert K.elliptic_k_agm(1 / math.sqrt(2)) == pytest.approx(math.gamma(0.25) ** 2 / (4 * math.sqrt(math.pi)), rel=1e-14)
    assert K.elliptic_k_agm(0.3) == K.elliptic_k_agm(-0.3)
    ks = np.linspace(0.0, 0.999, 50)
    vals = np.array([K.elliptic_k_agm(k) for k in ks])
    assert vals.shape == (50,)
    assert np.all(np.diff(vals) > 0)
    assert vals[-1] > 4.0                                        # k → 1 で対数発散
    for k in (1.0, -1.0, 1.5, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            K.elliptic_k_agm(k)


def test_pendulum_period_exact_small_amplitude_limit():
    """θ₀ → 0 で 2π√(L/g)(1 + θ₀²/16 + 11θ₀⁴/3072)、pendulum_period に収束、範囲外は拒否。"""
    T0 = B.pendulum_period(L)
    thetas = [1e-3, 1e-2, 0.05, 0.2]
    assert len(thetas) == 4
    for th in thetas:
        series = T0 * (1.0 + th ** 2 / 16.0 + 11.0 * th ** 4 / 3072.0)
        assert K.pendulum_period_exact(L, th) == pytest.approx(series, rel=th ** 6)
    assert K.pendulum_period_exact(L, 1e-8) == pytest.approx(T0, rel=1e-14)
    assert K.pendulum_period_exact(1.0, 1e-8, g=math.pi ** 2) == pytest.approx(2.0, rel=1e-14)
    assert K.pendulum_period_exact(L, 2.0) > K.pendulum_period_exact(L, 1.0) > T0
    for args in ((L, 0.0), (L, math.pi), (0.0, 1.0), (L, -0.1), (L, 1.0, 0.0)):
        with pytest.raises(ValueError):
            K.pendulum_period_exact(*args)


# ─────────────────────────────── 4-5 周期の定理 ───────────────────────────────

def test_period_theorem_vs_tether_simulate():
    """手元固定・真空のひも(10°・60°、dt = 1e-4)の周期が 4√(L/g)K(sin θ₀/2) と 1e-3 以内(実測 −6.9e-6 / −4.2e-4)。
    振幅は与えた通り(asin(x_max/L))、ずっと張っている。射影法は 1 次精度: dt = 1e-3 では 60° で −5.3e-3(門を落とす)。"""
    cases = [(10.0, 6.9e-6), (60.0, 4.2e-4)]
    assert len(cases) == 2
    for deg, measured in cases:
        th = math.radians(deg)
        v0 = K.pendulum_launch_speed(th, L)
        r = B.tether_simulate(_hang(), [v0, 0.0, 0.0], ORIGIN, L, 6.0, 1e-4)
        per, nc = _period_from_zero_crossings(r["t"], r["p"][:, 0])
        assert nc >= 8
        assert abs(per / K.pendulum_period_exact(L, th) - 1.0) < 1e-3
        assert abs(per / K.pendulum_period_exact(L, th) - 1.0) < 2.0 * measured + 1e-6
        assert math.degrees(math.asin(np.abs(r["p"][:, 0]).max() / L)) == pytest.approx(deg, abs=0.05)
        assert r["taut"][1:].all()
    # 1 次精度の証拠: dt を 10 倍にすると誤差も ≈ 10 倍(60°)
    th = math.radians(60.0)
    v0 = K.pendulum_launch_speed(th, L)
    coarse = B.tether_simulate(_hang(), [v0, 0.0, 0.0], ORIGIN, L, 6.0, 1e-3)
    err_coarse = abs(_period_from_zero_crossings(coarse["t"], coarse["p"][:, 0])[0] / K.pendulum_period_exact(L, th) - 1.0)
    assert 3e-3 < err_coarse < 8e-3


def test_period_theorem_vs_rod_pendulum():
    """棒の振り子(RK4、dt = 1e-3)の周期が定理と 1e-9 以内(10°・60°・120°・170°、実測 ≤ 6e-11)、エネルギー保存。
    ひもは 120° に届かない: 真下で同じ速さを与えると 109.47° で弛む(定理 3)。"""
    degs = [10.0, 60.0, 120.0, 170.0]
    assert len(degs) == 4
    for deg in degs:
        th = math.radians(deg)
        r = K.pendulum_rod_simulate(L, th, 12.0, 1e-3)
        per, nc = _period_from_zero_crossings(r["t"], r["theta"])
        assert nc >= 6
        assert abs(per / K.pendulum_period_exact(L, th) - 1.0) < 1e-9
        assert np.ptp(r["energy"]) < 1e-9
        assert np.abs(r["theta"]).max() == pytest.approx(th, rel=1e-9)
    r = B.tether_simulate(_hang(), [K.pendulum_launch_speed(math.radians(120.0), L), 0.0, 0.0], ORIGIN, L, 1.0, 2e-4)
    assert not r["taut"][1:].all()
    angles = np.array([_angle_from_bottom(p) for p in r["p"]])
    assert angles.max() < math.radians(120.0)
    assert K.tether_slack_angle(math.radians(120.0), L) == pytest.approx(math.acos(-1.0 / 3.0), rel=1e-15)


# ─────────────────────────────── 6-9 張力と弛み ───────────────────────────────

def test_tension_closed_form_structured_and_vs_simulation():
    """構造入力: 真下 m(v²/L + g)、水平 m v²/L、真上 m(v²/L − g)、静止の真上は負(押せない)。
    tether_simulate(60°、dt = 1e-3、m = 0.075)の推定張力 m·v_r/dt が閉形式 m(v²/L + g cos θ) と 2 % 以内
    (実測: 最大張力 1.47 N に対し最大誤差 0.18 %、張力が最大の 10 % 以上の所で相対 0.34 %)。"""
    m = KP["mass"]
    assert K.tether_tension_fixed(1.0, 0.0, L, m) == pytest.approx(m * (1.0 / L + B.G), rel=1e-15)
    assert K.tether_tension_fixed(1.0, math.pi / 2, L, m) == pytest.approx(m / L, abs=1e-15)
    assert K.tether_tension_fixed(1.0, math.pi, L, m) == pytest.approx(m * (1.0 / L - B.G), rel=1e-15)
    assert K.tether_tension_fixed(0.0, math.pi, L, m) < 0.0
    assert K.tether_tension_fixed(0.0, 0.0, L, m) == pytest.approx(m * B.G, rel=1e-15)
    for args in ((-1.0, 0.0, L, m), (1.0, 0.0, 0.0, m), (1.0, 0.0, L, 0.0), (float("nan"), 0.0, L, m), (1.0, 0.0, L, m, 0.0)):
        with pytest.raises(ValueError):
            K.tether_tension_fixed(*args)
    th0 = math.radians(60.0)
    r = B.tether_simulate(_hang(), [K.pendulum_launch_speed(th0, L), 0.0, 0.0], ORIGIN, L, 3.0, 1e-3, mass=m)
    speed = np.linalg.norm(r["v"], axis=1)
    theta = np.array([_angle_from_bottom(p) for p in r["p"]])
    closed = np.array([K.tether_tension_fixed(s, t, L, m) for s, t in zip(speed, theta)])
    sim = r["tension"]
    assert sim.shape == (3001,) and r["taut"][1:].all()
    err = np.abs(sim[1:] - closed[1:])
    assert closed.max() == pytest.approx(m * (2 * B.G * L * (1 - math.cos(th0)) / L + B.G), rel=1e-6)   # 真下: m(v₀²/L + g)
    assert closed.min() == pytest.approx(m * B.G * math.cos(th0), rel=0.01)                            # 折り返し: m g cos θ₀
    assert err.max() < 0.02 * closed.max()
    strong = closed[1:] > 0.1 * closed.max()
    assert strong.sum() > 2000
    assert (err[strong] / closed[1:][strong]).max() < 0.02


def test_slack_angle_closed_form():
    """cos θ_s = (2/3) cos θ₀: 120° → 109.47°、180° → 131.81°(頂点にちょうど届くエネルギー)、91° → 90.96°、
    θ₀ ≤ 90° は None(弛まない)、範囲外は拒否、θ₀ が増えると θ_s も増える(上限 131.81°)。"""
    assert math.degrees(K.tether_slack_angle(math.radians(120.0), L)) == pytest.approx(109.47122063449069, rel=1e-12)
    assert math.degrees(K.tether_slack_angle(math.pi, L)) == pytest.approx(131.81031489577862, rel=1e-12)
    assert K.tether_slack_angle(math.pi, L) == pytest.approx(math.acos(-2.0 / 3.0), rel=1e-15)
    assert math.degrees(K.tether_slack_angle(math.radians(91.0), L)) == pytest.approx(90.667, abs=0.001)
    nones = [K.tether_slack_angle(th, L) for th in (1e-6, math.radians(30), math.radians(60), math.pi / 2)]
    assert len(nones) == 4 and all(x is None for x in nones)
    ths = np.linspace(math.pi / 2 + 1e-6, math.pi, 30)
    ss = np.array([K.tether_slack_angle(t, L) for t in ths])
    assert ss.shape == (30,) and np.all(np.diff(ss) > 0) and ss.min() > math.pi / 2 and ss.max() <= math.acos(-2.0 / 3.0)
    assert K.tether_slack_angle(2.0, 0.39, 1.0) == K.tether_slack_angle(2.0, 5.0, 9.81)            # L・g に依らない
    for args in ((0.0, L), (-1.0, L), (math.pi + 1e-9, L), (2.0, 0.0), (2.0, L, -1.0)):
        with pytest.raises(ValueError):
            K.tether_slack_angle(*args)


def test_slack_angle_vs_simulation():
    """真下で v₀ = √(2gL(1 − cos θ₀)) を与えたひも(dt = 2e-4)が弛む角がシミュレーションで閉形式と 1° 以内
    (100°・120°・150°・180°、実測 −0.09° / −0.13° / −0.26° / −0.30°: 1 次精度の遅れ)。kendama_simulate の slack_t も同じ瞬間。"""
    degs = [100.0, 120.0, 150.0, 180.0]
    assert len(degs) == 4
    for deg in degs:
        th0 = math.radians(deg)
        v0 = K.pendulum_launch_speed(th0, L)
        r = B.tether_simulate(_hang(), [v0, 0.0, 0.0], ORIGIN, L, 1.0, 2e-4)
        idx = np.where(r["taut"][1:-1] & ~r["taut"][2:])[0]
        assert idx.size >= 1
        i0 = int(idx[0]) + 1
        ang = _angle_from_bottom(r["p"][i0])
        closed = K.tether_slack_angle(th0, L)
        assert abs(math.degrees(ang - closed)) < 1.0
        assert r["tension"][i0 + 1] == 0.0 and r["tension"][i0 - 1] > 0.0
        # 同じ運動を kendama_simulate で: 弛む時刻は同じ step
        k = K.kendama_simulate(KV, ORIGIN, p0=_hang(), v0=[v0, 0.0, 0.0], t_end=1.0, dt=2e-4, stop_on_miss=False)
        assert k["slack_t"] == pytest.approx(r["t"][i0 + 1], abs=1e-12)


def test_no_slack_below_horizontal():
    """上半分に届かない振幅(30°・60°・80°)では 3 s ずっと張ったまま、張力の最小 ≈ m g cos θ₀ > 0、snap 無し。"""
    degs = [30.0, 60.0, 80.0]
    assert len(degs) == 3
    for deg in degs:
        th0 = math.radians(deg)
        r = K.kendama_simulate(KV, ORIGIN, p0=_hang(), v0=[K.pendulum_launch_speed(th0, L), 0.0, 0.0], t_end=3.0, dt=1e-3)
        assert r["end_reason"] == "timeout" and r["slack_t"] is None and not r["caught"]
        assert r["taut"][1:].all()
        assert r["tension"][1:].min() > 0.0
        th_max = max(_angle_from_bottom(p) for p in r["p"])                # 実際の折り返し(1 次精度の減衰で θ₀ より僅かに小さい)
        assert th0 - math.radians(0.5) < th_max < th0
        assert r["tension"][1:].min() == pytest.approx(KV["mass"] * B.G * math.cos(th_max), rel=1e-4)   # 折り返しで v = 0 → m g cos θ
        assert r["snap_times"].size == 0 and r["snap_loss"] == 0.0


# ─────────────────────────────── 10-11 エネルギー・snap・一致 ───────────────────────────────

def test_energy_conservation_and_snap_loss():
    """手元固定・真空: 60° の振り子のエネルギーは射影法の散逸で単調に減り、損失は dt に比例(3 s で 5.7 % @ 1e-3、0.59 % @ 1e-4)。横に投げ上げた玉
    (v₀ = (0.4, 0, 3))は弛んだまま昇り、|p(t)| = L(0.42 m)に戻る 4 次多項式の正の根 0.5867 s で snap(実測 0.587)、
    損失 = ½ m v_r²(0.237 J)、その前はエネルギー保存(1e-12)、snap でエネルギーが落ちる。"""
    m = KV["mass"]
    swing = 0.5 * m * 2 * B.G * L * (1 - math.cos(math.radians(60.0)))       # 振りのエネルギー(真下の運動エネルギー)0.155 J
    loss = []
    for dt in (1e-3, 1e-4):
        r = K.kendama_simulate(KV, ORIGIN, p0=_hang(), v0=[K.pendulum_launch_speed(math.radians(60.0), L), 0.0, 0.0], t_end=3.0, dt=dt)
        assert r["energy"][0] == pytest.approx(swing - m * B.G * L, rel=1e-12)
        assert np.all(np.diff(r["energy"]) <= 1e-12)                        # 射影法は散逸的(作りはしない)
        loss.append(np.ptp(r["energy"]) / swing)
    assert len(loss) == 2
    assert loss[1] < 0.01 and 5.0 < loss[0] / loss[1] < 15.0                 # dt = 1e-4 で 0.56 %、1e-3 で 5.5 %(1 次収束)
    v0 = np.array([0.4, 0.0, 3.0])
    s = K.kendama_simulate(KV, ORIGIN, p0=_hang(), v0=v0, t_end=1.5, stop_on_miss=False)
    zc = np.array([-L, v0[2], -0.5 * B.G])                                   # z(t) の昇冪係数
    f = np.polynomial.polynomial.polymul(zc, zc)
    f[2] += v0[0] ** 2
    f[0] -= L * L
    roots = np.polynomial.polynomial.polyroots(f)
    real_pos = sorted(float(x.real) for x in roots if abs(x.imag) < 1e-12 and x.real > 1e-9)
    assert len(real_pos) == 1
    t_snap_closed = real_pos[0]
    assert t_snap_closed == pytest.approx(0.5867, abs=5e-4)
    assert s["snap_times"].shape == (1,)
    assert s["snap_times"][0] == pytest.approx(t_snap_closed, abs=1.5e-3)
    assert s["slack_t"] == pytest.approx(1e-3, abs=1e-12)                    # 最初の step で弛む
    i = int(np.argmin(np.abs(s["t"] - s["snap_times"][0])))
    p_before, v_before = s["p"][i - 1], s["v"][i - 1]
    rhat = p_before / np.linalg.norm(p_before)
    vr = float(v_before @ rhat)
    assert vr > 0.0
    assert s["snap_loss"] == pytest.approx(0.5 * m * vr * vr, rel=0.02)
    assert s["snap_loss"] == pytest.approx(0.237, abs=0.005)
    assert np.ptp(s["energy"][: i - 1]) < 1e-12
    assert s["energy"][i] < s["energy"][i - 1] - 0.9 * s["snap_loss"]
    assert not s["taut"][1:i - 1].any() and s["taut"][i:].all()
    assert s["end_reason"] == "timeout" and not s["caught"]
    assert np.linalg.norm(s["p"], axis=1).max() <= L + 1e-9


def test_kendama_simulate_matches_tether_simulate_fixed_handle():
    """手元固定・真空・計画なしの kendama_simulate は ballistics.tether_simulate と同じ軌跡・張力(1e-12)。
    動く手元(z = 0.5 t)でも同じ。"""
    v0 = [K.pendulum_launch_speed(math.radians(60.0), L), 0.0, 0.0]
    a = B.tether_simulate(_hang(), v0, ORIGIN, L, 3.0, 1e-3, mass=KV["mass"])
    b = K.kendama_simulate(KV, ORIGIN, p0=_hang(), v0=v0, t_end=3.0)
    assert a["p"].shape == b["p"].shape == (3001, 3)
    assert np.abs(a["p"] - b["p"]).max() < 1e-12 and np.abs(a["v"] - b["v"]).max() < 1e-12
    assert np.abs(a["tension"] - b["tension"]).max() < 1e-12 and np.array_equal(a["taut"][1:], b["taut"][1:])
    assert np.abs(a["energy"] - b["energy"]).max() < 1e-12

    def handle(t):
        return np.array([0.0, 0.0, 0.5 * t])

    p0 = _hang(0.2)
    a = B.tether_simulate(p0, [0.0, 0.0, 0.0], handle, L, 2.0, 1e-3, mass=KV["mass"])
    b = K.kendama_simulate(KV, handle, p0=p0, v0=[0.0, 0.0, 0.0], t_end=2.0, stop_on_miss=False)
    assert np.abs(a["p"] - b["p"]).max() < 1e-12
    H = np.array([handle(t) for t in b["t"]])
    assert np.abs(b["anchor"] - H).max() < 1e-12 and np.abs(b["cup"] - H).max() < 1e-12 and np.abs(b["hand"] - H).max() < 1e-12
    assert np.linalg.norm(b["p"] - H, axis=1).max() <= L + 1e-9


# ─────────────────────────────── 12-13 振り上げ ───────────────────────────────

def test_swing_up_plan_kinematics():
    """handle(0) = origin、handle(T_lift) = origin + lift·ẑ、t > T_lift で静止(5 s 後も同じ)、z は単調非減少、xy は不変、
    bang の加速度 4·lift/T²(有限差分)、trap は等速区間あり、kind/lift/T の不正は拒否。"""
    for kind in ("bang", "trap"):
        h = K.swing_up_plan(KP, lift=0.25, T_lift=0.15, kind=kind, origin=(0.1, -0.2, 0.3))
        assert np.array_equal(h(0.0), [0.1, -0.2, 0.3]) and np.array_equal(h(-1.0), [0.1, -0.2, 0.3])
        assert h(0.15)[2] == pytest.approx(0.55, abs=1e-15)
        assert np.array_equal(h(0.15), h(0.2)) and np.array_equal(h(0.15), h(5.0))
        ts = np.linspace(0.0, 0.2, 401)
        Z = np.array([h(t) for t in ts])
        assert Z.shape == (401, 3)
        assert np.all(np.diff(Z[:, 2]) >= -1e-15)
        assert np.abs(Z[:, 0] - 0.1).max() == 0.0 and np.abs(Z[:, 1] + 0.2).max() == 0.0
        assert h.T_lift == 0.15 and h.lift == 0.25 and h.kind == kind
    h = K.swing_up_plan(KP, lift=0.25, T_lift=0.15, kind="bang")
    a = 4.0 * 0.25 / 0.15 ** 2
    assert h.accel == pytest.approx(a, rel=1e-12)
    dd = 1e-4
    for t in (0.02, 0.05, 0.07):
        assert (h(t + dd)[2] - 2 * h(t)[2] + h(t - dd)[2]) / dd ** 2 == pytest.approx(a, rel=1e-6)
    for t in (0.08, 0.11, 0.14):
        assert (h(t + dd)[2] - 2 * h(t)[2] + h(t - dd)[2]) / dd ** 2 == pytest.approx(-a, rel=1e-6)
    assert h(0.075)[2] == pytest.approx(0.125, rel=1e-12)
    tr = K.swing_up_plan(KP, lift=0.25, T_lift=0.15, kind="trap")
    vc = 1.5 * 0.25 / 0.15
    assert (tr(0.08)[2] - tr(0.06)[2]) / 0.02 == pytest.approx(vc, rel=1e-12)          # 等速区間 T/3〜2T/3
    assert tr(0.1)[2] == pytest.approx(0.75 * 0.25, rel=1e-12)
    for kw in (dict(kind="sine"), dict(lift=0.0), dict(T_lift=-1.0), dict(origin=(0, 0)), dict(lift=float("nan"))):
        with pytest.raises(ValueError):
            K.swing_up_plan(KP, **kw)


def test_swing_up_apex_closed_form_vs_simulation():
    """既定(lift 0.265、T 0.15、bang: a = 47.1 m/s² > g)は T/2 で弛み頂点 0.3488(ひもの有効長 0.42 m、手元の 8.4 cm 上)。
    シミュレーション(真空、計画なし、捕らない)の頂点は 1 次で収束: dt = 1e-3 で −4.9 mm、1e-4 で −0.50 mm。遅い持ち上げ(T 0.35、a = 8.2 < g)は
    弛まず玉は手元の L 下に留まる(閉形式 flies False、sim の slack 無し・頂点 = lift − L)。trap の閉形式も sim と一致。"""
    ap = K.swing_up_apex(KV)
    assert ap["accel"] == pytest.approx(4 * 0.265 / 0.15 ** 2, rel=1e-12) and ap["flies"]
    assert ap["slack_t"] == 0.075 and ap["z_slack"] == pytest.approx(0.1325, rel=1e-15)
    assert ap["v_slack"] == pytest.approx(2 * 0.265 / 0.15, rel=1e-12)
    assert ap["apex"] == pytest.approx(0.1325 - L + (2 * 0.265 / 0.15) ** 2 / (2 * B.G), rel=1e-12)
    assert ap["apex_above_handle"] == pytest.approx(0.0838, abs=2e-4)
    assert K.swing_up_apex(KP)["apex_above_cup"] == pytest.approx(0.0838 - KP["cup_offset"][2], abs=2e-4)   # 大皿は手元の 33.8 mm 上
    h = K.swing_up_plan(KV)
    errs = []
    for dt in (1e-3, 1e-4):
        r = K.kendama_simulate(KV_NOCUP, h, p0=_hang(), v0=[0.0, 0.0, 0.0], t_end=0.45, dt=dt, stop_on_miss=False)
        assert r["slack_t"] == pytest.approx(0.075, abs=2.5 * dt)
        assert r["end_reason"] == "timeout"
        errs.append(r["p"][:, 2].max() - ap["apex"])
    assert len(errs) == 2
    assert abs(errs[0]) < 5e-3 and abs(errs[1]) < 5e-4
    assert 5.0 < errs[0] / errs[1] < 15.0                                    # 1 次収束
    slow = K.swing_up_apex(KV, lift=0.25, T_lift=0.35)
    assert not slow["flies"] and slow["accel"] < B.G and slow["slack_t"] is None
    assert slow["apex"] == pytest.approx(0.25 - L, rel=1e-12)
    r = K.kendama_simulate(KV, K.swing_up_plan(KV, lift=0.25, T_lift=0.35), p0=_hang(), v0=[0.0, 0.0, 0.0], t_end=1.0,
                           stop_on_miss=False)
    assert r["p"][:, 2].max() == pytest.approx(0.25 - L, abs=1e-4)
    assert r["p"][-1, 2] == pytest.approx(0.25 - L, abs=1e-6) and r["taut"][-1]
    tr = K.swing_up_apex(KV, kind="trap")
    r = K.kendama_simulate(KV_NOCUP, K.swing_up_plan(KV, kind="trap"), p0=_hang(), v0=[0.0, 0.0, 0.0], t_end=0.6, stop_on_miss=False)
    assert tr["flies"] and r["slack_t"] == pytest.approx(0.1, abs=2.5e-3)
    assert r["p"][:, 2].max() == pytest.approx(tr["apex"], abs=5e-4)
    with pytest.raises(ValueError):
        K.swing_up_apex(KV, kind="sine")


# ─────────────────────────────── 14-18 皿と閉ループ ───────────────────────────────

def test_kendama_catch_check_geometry():
    """縁の中心 c、軸 ẑ(大皿 r_c = 21 mm)。玉の中心が c + h_c ẑ で静止 → 捕球(高さ = h_c、横ずれ 0)。横ずれ 20.5 mm は可、21.5 mm は不可。
    窓の上端 h_c + 45 mm は可、その 1 mm 上は不可。縁より下(h_c − 1 mm)は不可。相対速さ 1.0 は可、1.01 は不可、皿が一緒に
    動けば相対で判定。昇る玉(相対 +0.1 m/s)は不可。軸を倒しても軸に沿って判定。window(着地)= 縁に最初に触れる高さ
    √(r_b² − (r_c − δ)²) + window 以下: 真ん中の玉は h_c + 3 mm まで、横ずれ 10 mm の玉はそれより高い所で触れる。不正な軸は拒否。"""
    c = np.array([0.1, 0.2, 0.3])
    hc = KP["cup_rest_height"]
    assert KP["cup_radius"] == KP["cup_radius_big"] == 0.021
    ok = K.kendama_catch_check(KP, c + [0, 0, hc], [0, 0, 0], c)
    assert ok["caught"] and ok["lateral"] == 0.0 and ok["height"] == pytest.approx(hc, abs=1e-15) and ok["descending"]
    assert K.kendama_catch_check(KP, c + [0.0205, 0, hc], [0, 0, -0.1], c)["caught"]
    assert not K.kendama_catch_check(KP, c + [0.0215, 0, hc], [0, 0, -0.1], c)["caught"]
    assert K.kendama_catch_check(KP, c + [0, 0, hc + 0.045], [0, 0, -0.1], c)["caught"]
    assert not K.kendama_catch_check(KP, c + [0, 0, hc + 0.046], [0, 0, -0.1], c)["caught"]
    assert not K.kendama_catch_check(KP, c + [0, 0, hc - 0.001], [0, 0, -0.1], c)["caught"]
    assert K.kendama_catch_check(KP, c + [0, 0, hc], [0, 0, -1.0], c)["caught"]
    assert not K.kendama_catch_check(KP, c + [0, 0, hc], [0, 0, -1.01], c)["caught"]
    moving = K.kendama_catch_check(KP, c + [0, 0, hc], [0, 0, -1.5], c, v_cup=[0, 0, -1.0])
    assert moving["caught"] and moving["speed"] == pytest.approx(0.5, abs=1e-15)
    rising = K.kendama_catch_check(KP, c + [0, 0, hc], [0, 0, 0.1], c)
    assert not rising["caught"] and not rising["descending"]
    assert K.kendama_catch_check(KP, c + [0, 0, hc], [0, 0, 0.1], c, v_cup=[0, 0, 0.1])["caught"]      # 一緒に昇れば相対 0
    tilted = K.kendama_catch_check(KP, c + [hc, 0, 0], [-0.1, 0, 0], c, cup_axis=[1, 0, 0])
    assert tilted["caught"] and tilted["height"] == pytest.approx(hc, abs=1e-15)
    w = KP["catch_window"]
    assert w == 0.003
    assert K.kendama_catch_check(KP, c + [0, 0, hc + 0.0029], [0, 0, -0.5], c, window=w)["caught"]
    assert not K.kendama_catch_check(KP, c + [0, 0, hc + 0.0031], [0, 0, -0.5], c, window=w)["caught"]
    h_touch = math.sqrt(0.03 ** 2 - (0.021 - 0.010) ** 2)                      # 横ずれ 10 mm の玉が縁に触れる高さ 27.9 mm
    assert K.kendama_catch_check(KP, c + [0.010, 0, h_touch + 0.0029], [0, 0, -0.5], c, window=w)["caught"]
    assert not K.kendama_catch_check(KP, c + [0.010, 0, h_touch + 0.0031], [0, 0, -0.5], c, window=w)["caught"]
    with pytest.raises(ValueError):
        K.kendama_catch_check(KP, c, [0, 0, 0], c, cup_axis=[0, 0, 0])


def _contact(kp):
    import kendamaworld as KW
    return lambda hand, p: KW.kendama_clearance(kp, hand, p)["gap"][0]


def _flight_shape_ok(r):
    """門 3(ユーザーの条件): 弛んだ瞬間の鉛直速度 > 0、頂点が弛んだ高さより上、捕球は頂点より低く下降中。"""
    i_s = int(round(r["slack_t"] / (r["t"][1] - r["t"][0])))
    i_a = int(np.argmax(r["p"][:, 2]))
    return bool(r["v"][i_s, 2] > 0 and r["p"][i_a, 2] > r["p"][i_s, 2] and i_a > i_s and r["p"][-1, 2] < r["p"][i_a, 2]
                and r["v"][-1, 2] < 0)


def test_staged_plan_catches_without_touching_the_ken():
    """段階を明示した制御(catch_plan_staged)+ 手元を −y へ 10 cm 逃がす振り上げ(swing_up_lift で頂点を決める)+ けんとの接触の監視:
    大皿の技で真下・横 1 cm・横 −2 cm・対角 3 cm の 4 件すべて捕球(実測 0.535〜0.550 s)。段階は lift → wait → hold → carry →
    absorb → caught の順、玉はけん玉に触れない(隙間の最小 0.4〜2.0 mm > 0)、弛んだ後に昇って頂点を越え下降中に受ける、
    着地の相対速さ ≤ 1(実測 0.53〜0.69)、横ずれ ≤ 5 mm(実測 0.9〜3.4 mm)。計画は毎 step 記録。"""
    plan = K.catch_plan_staged(KP)
    h = K.swing_up_plan(KP, lift=K.swing_up_lift(KP), dodge=(0.0, -0.10, 0.0))
    starts = [(0.0, 0.0), (0.01, 0.0), (0.0, -0.02), (0.03, 0.03)]
    assert len(starts) == 4
    for x, y in starts:
        r = K.kendama_simulate(KP, h, p0=_hang(x, y, TIE), v0=[0.0, 0.0, 0.0], t_end=1.5, catch_plan=plan, plan_from=h.T_lift,
                               contact=_contact(KP))
        assert r["caught"] and r["end_reason"] == "caught" and 0.52 < r["catch_t"] < 0.56
        order = [st for i, st in enumerate(r["stage"]) if i == 0 or st != r["stage"][i - 1]]
        assert order == ["lift", "wait", "hold", "carry", "absorb", "caught"], order
        assert r["min_gap"] > 0.0 and _flight_shape_ok(r)
        assert r["lateral"] < 0.005
        chk = K.kendama_catch_check(KP, r["p"][-1], r["v"][-1], r["cup"][-1], KP["cup_axis"], r["cup_v"][-1])
        assert chk["descending"] and 0.4 < chk["speed"] <= 1.0
        assert len(r["plan_log"]) > 300 and r["plan_log"][0][0] >= h.T_lift
        assert np.linalg.norm(r["p"] - r["anchor"], axis=1).max() <= L + 1e-9


def test_three_tricks_same_plan_and_absorb():
    """同じ計画と制御で大皿・小皿・中皿・ろうそく(姿勢は kp の技)を横 2 cm から: 4 技とも捕る、けんに触れない、門 3 の飛び方。
    着地で下げる(absorb 2 cm)と相対速さが下がる(実測 大皿 0.92 → 0.52、小皿 0.90 → 0.58、中皿 0.76 → 0.42 m/s)。
    ろうそくは持つ所が違うだけで(皿は手元の 147 mm 上)、手元の並進だけの剛体では中皿と同じ相対運動になる。"""
    rel = {}
    for trick in ("ozara", "kozara", "chuzara", "rousoku"):
        kp = K.kendama_params(trick=trick)
        assert kp["cup_axis"][2] > 0.96 and kp["catch_cup"] == K.KENDAMA_TRICKS[trick]["cup"]
        h = K.swing_up_plan(kp, lift=K.swing_up_lift(kp), dodge=(0.0, -0.10, 0.0))
        p0 = _hang(0.02, 0.0, kp["tie_offset"])
        for depth in (0.02, 0.0):
            r = K.kendama_simulate(kp, h, p0=p0, v0=[0.0, 0.0, 0.0], t_end=1.5, catch_plan=K.catch_plan_staged(kp, absorb_depth=depth),
                                   plan_from=h.T_lift, contact=_contact(kp))
            assert r["caught"] and r["min_gap"] > 0.0 and _flight_shape_ok(r), (trick, depth, r["end_reason"])
            rel[(trick, depth)] = float(np.linalg.norm(r["v"][-1] - r["cup_v"][-1]))
        assert rel[(trick, 0.02)] < rel[(trick, 0.0)] - 0.15
    assert rel[("chuzara", 0.02)] == pytest.approx(rel[("rousoku", 0.02)], abs=1e-9)


def test_ken_contact_ends_the_trial():
    """けんは玉を押さない: 逃がさず計画もない振り上げは、真下から昇る玉が皿胴に触れて "hit_ken" で終わる(実測 0.263 s、
    contact なしだと突き抜けて 0.482 s に「捕れて」しまう = 物理が衝突を解かない分を contact で失敗にする)。"""
    h = K.swing_up_plan(KP)
    r = K.kendama_simulate(KP, h, p0=_hang(anchor=TIE), v0=[0.0, 0.0, 0.0], t_end=1.5, contact=_contact(KP))
    assert r["end_reason"] == "hit_ken" and not r["caught"] and r["min_gap"] < -5e-4
    assert r["t"][-1] == pytest.approx(0.263, abs=3e-3)
    through = K.kendama_simulate(KP, h, p0=_hang(anchor=TIE), v0=[0.0, 0.0, 0.0], t_end=1.5)
    assert through["caught"] and through["catch_t"] == pytest.approx(0.482, abs=3e-3)


def test_kendama_simulate_bad_plan_misses_and_timeout():
    """皿を 30 cm 横へ運ぶ計画は missed(捕球なし、catch_t None、玉は皿の面より 2 r_b 下まで落ちて終わる)。t_end が飛翔より短ければ timeout。
    計画なし・横 3 cm からは missed。"""
    h = K.swing_up_plan(KP)

    def bad_plan(t, p, v, cup):
        return {"target": np.array([0.3, 0.0, 0.25])}

    r = K.kendama_simulate(KP, h, p0=_hang(anchor=TIE), v0=[0.0, 0.0, 0.0], t_end=1.5, catch_plan=bad_plan, plan_from=h.T_lift)
    assert not r["caught"] and r["end_reason"] == "missed" and r["catch_t"] is None
    assert r["p"][-1, 2] < r["cup"][-1, 2] - 2 * KP["ball_radius"] and r["v"][-1, 2] < 0
    assert r["lateral"] > KP["cup_radius_big"]
    assert r["cup"][-1, 0] > 0.1
    short = K.kendama_simulate(KP, h, p0=_hang(anchor=TIE), v0=[0.0, 0.0, 0.0], t_end=0.3, catch_plan=K.catch_plan_staged(KP),
                               plan_from=h.T_lift)
    assert short["end_reason"] == "timeout" and not short["caught"] and short["t"].shape == (301,)
    r = K.kendama_simulate(KP, h, p0=_hang(0.03, anchor=TIE), v0=[0.0, 0.0, 0.0], t_end=1.5)
    assert r["end_reason"] == "missed" and not r["caught"] and r["lateral"] > KP["cup_radius_big"]


def test_catch_plan_ballistic_closed_form():
    """状態 p = (0.01, −0.02, 0.28)、v = (0.1, 0.05, 1.0)、皿 (0, 0, 0.25): 頂点 z + v_z²/(2g)、面 = 頂点 − (h_c + 1.5 r_b) − v_t²/(2g)、
    t_hit で z(t) = 面 + h_c + 1.5 r_b(1e-12、遅い根)、xy = p + v τ、v_hit = (v_x, v_y, v_z − g τ)、|v_hit_z| = v_target、
    間に合う(feasible)。v_max・a_max を極端に小さくすると間に合わず feasible False(面は最上段のまま)。目標へ動いている皿の
    残り時間は静止からより短い。皿より下を落ちる玉には皿の下の面と feasible False。拒否。"""
    plan = K.catch_plan_ballistic(KP)
    p, v = np.array([0.01, -0.02, 0.28]), np.array([0.1, 0.05, 1.0])
    cup = {"p": np.array([0.0, 0.0, 0.25]), "v": np.zeros(3), "axis": np.array([0.0, 0.0, 1.0])}
    res = plan(0.3, p, v, cup)
    h_top = KP["cup_rest_height"] + 1.5 * KP["ball_radius"]
    apex = 0.28 + 1.0 / (2 * B.G)
    assert res["apex"] == pytest.approx(apex, rel=1e-12)
    assert res["z_plane"] == pytest.approx(apex - h_top - 0.25 / (2 * B.G), rel=1e-12)
    tau = res["t_hit"] - 0.3
    assert tau > 1.0 / B.G                                                    # 頂点より後(下降)
    assert 0.28 + 1.0 * tau - 0.5 * B.G * tau ** 2 == pytest.approx(res["z_plane"] + h_top, abs=1e-12)
    assert np.allclose(res["target"][:2], p[:2] + v[:2] * tau, atol=1e-12)
    assert np.allclose(res["v_ball_hit"], [0.1, 0.05, 1.0 - B.G * tau], atol=1e-12)
    assert res["v_ball_hit"][2] == pytest.approx(-0.5, abs=1e-12)
    assert res["feasible"] and res["travel"] < tau
    assert res["travel"] == pytest.approx(2 * math.sqrt(np.linalg.norm(res["target"] - cup["p"]) / 20.0), rel=1e-12)
    slow = K.catch_plan_ballistic(KP, v_max=0.01, a_max=0.01)(0.3, p, v, cup)
    assert not slow["feasible"] and slow["z_plane"] == pytest.approx(res["z_plane"], rel=1e-12)          # 最上段のまま
    assert slow["travel"] == pytest.approx(np.linalg.norm(slow["target"] - cup["p"]) / 0.01 + 1.0, rel=1e-12)   # d/v + v/a
    # 動いている皿: 目標へ向かう速さ込みの残り時間は静止からより短い
    moving = plan(0.3, p, v, {"p": cup["p"], "v": np.array([0.5, 0.0, 0.0]), "axis": cup["axis"]})
    assert moving["travel"] < res["travel"] and moving["feasible"]
    # 皿より 75 cm 下を落ちる玉: 面は皿の下、間に合わない
    gone = plan(1.0, [0.0, 0.0, -0.5], [0.0, 0.0, -3.0], cup)
    assert not gone["feasible"] and gone["z_plane"] < -0.5 and gone["t_hit"] - 1.0 < 0.01
    for kw in (dict(v_max=0.0), dict(a_max=-1.0), dict(v_target=1.5), dict(v_target=-0.1), dict(n_planes=0), dict(plane_step=0.0)):
        with pytest.raises(ValueError):
            K.catch_plan_ballistic(KP, **kw)


def test_catch_success_rate_truth_and_noise():
    """既定(段階の計画 + 逃がす振り上げ + 自動の持ち上げ)、けんとの接触を失敗に数える: 真値 20 回で ≥ 0.9(実測 1.0、seed 0・1)。
    着地で下げない(absorb=False)でも 0.95〜1.0。**正直に**: noisy_perceiver の雑音は 1 ms ごとに独立なので、hold の「玉が
    けんの上に出た」判定が雑音の 1 標本で早く立ち、昇ってくる玉へ皿を寄せてけんに当てる(20 mm で 0.35〜0.45、50 mm で
    0.6〜0.7 と単調でない —— 画像の知覚は放物線で均すのでこうならない)。100 mm で 0。返り値の形(n 件、rate = 平均、lift)。"""
    c = _contact(KP)
    truth = K.catch_success_rate(KP, n=20, seed=0, contact=c)
    assert truth["n"] == 20 and len(truth["caught_list"]) == 20 and len(truth["end_reasons"]) == 20 and len(truth["starts"]) == 20
    assert truth["rate"] == pytest.approx(np.mean(truth["caught_list"]), abs=1e-15)
    assert truth["rate"] >= 0.9 and truth["mean_lateral"] < 0.005
    assert truth["lift"] == pytest.approx(K.swing_up_lift(KP), rel=1e-15)
    assert K.catch_success_rate(KP, n=20, seed=0, contact=c, absorb=False)["rate"] >= 0.9
    noisy = K.catch_success_rate(KP, n=20, seed=0, noise_pos=0.02, contact=c)
    assert noisy["rate"] < truth["rate"] and "hit_ken" in noisy["end_reasons"]
    assert K.catch_success_rate(KP, n=20, seed=0, noise_pos=0.1, contact=c)["rate"] == 0.0
    for kw in (dict(n=0), dict(noise_pos=-0.01), dict(jitter_pos=-1.0), dict(planner="magic")):
        with pytest.raises(ValueError):
            K.catch_success_rate(KP, **kw)


def test_catch_plan_staged_closed_form_and_stages():
    """構造入力(大皿、皿の中心 (0, 0, 1.30)、手元 = 皿 − cup_offset): 玉が昇りながらけんの最高点 + r_b + 5 mm より下なら hold
    (目標 = 今の皿、wait = その高さに届く早い根)、越えていれば carry(目標の高さは受ける高さのまま = 水平、xy = 玉の中心が
    皿 + h_c·軸 の高さへ下りてくる遅い根 τ での xy − h_c·(a_x, a_y))、着地の √(depth/a_max) 前から absorb(目標を 2 cm 下げる)。
    頂点が着地の高さに届かない玉は hold・feasible False。新しい試行(t が戻る)で受ける高さを取り直す。拒否。"""
    g = B.G
    plan = K.catch_plan_staged(KP)
    cup = np.array([0.0, 0.0, 1.30])
    st = {"p": cup, "v": np.zeros(3)}
    ax, hc, off = KP["cup_axis"], KP["cup_rest_height"], KP["cup_offset"]
    h_clear = cup[2] - off[2] + KP["top_offset"] + 0.005 + 0.03
    p, v = np.array([0.05, -0.1, 1.2]), np.array([0.0, 0.0, 2.0])
    r = plan(0.2, p, v, st)
    assert r["stage"] == "hold" and np.allclose(r["target"], cup)
    assert r["wait"] == pytest.approx((2.0 - math.sqrt(4.0 - 2 * g * (h_clear - 1.2))) / g, rel=1e-12)
    p2 = np.array([0.05, -0.1, h_clear + 0.001])
    r = plan(0.3, p2, np.array([0.1, 0.0, 0.5]), st)
    z_land = cup[2] + hc * ax[2]
    tau = (0.5 + math.sqrt(0.25 - 2 * g * (z_land - p2[2]))) / g
    assert r["stage"] == "carry" and r["t_land"] == pytest.approx(0.3 + tau, rel=1e-12)
    assert np.allclose(r["target"], [0.05 + 0.1 * tau - hc * ax[0], -0.1 - hc * ax[1], 1.30], atol=1e-12)
    # 着地の直前: absorb(√(0.02/20) = 31.6 ms 以内)
    tau_a = 0.02
    p3 = np.array([0.0, 0.0, z_land + 0.5 * g * tau_a ** 2])                  # 頂点から tau_a で着地
    r = plan(0.31, p3, np.zeros(3), st)
    assert r["stage"] == "absorb" and r["target"][2] == pytest.approx(1.30 - 0.02, abs=1e-12)
    low = plan(0.32, np.array([0.0, 0.0, 1.0]), np.array([0.0, 0.0, 0.5]), st)      # 頂点が着地の高さに届かない
    assert low["stage"] == "hold" and not low["feasible"]
    again = plan(0.1, p, v, {"p": cup + [0, 0, 0.1], "v": np.zeros(3)})           # t が戻った = 新しい試行
    assert again["stage"] == "hold" and np.allclose(again["target"], cup + [0, 0, 0.1])
    for kw in (dict(v_max=0.0), dict(absorb_depth=-0.01), dict(margin=-1.0)):
        with pytest.raises(ValueError):
            K.catch_plan_staged(KP, **kw)


def test_swing_up_lift_inverts_the_apex():
    """swing_up_lift は swing_up_apex の逆: 既定の頂点(max(h_c + 0.9 r_b, けんの最高点 + r_b + 35 mm)− 皿)を 1e-12 で返す。
    大皿 0.271 m(頂点は皿の 75.9 mm 上)、中皿 0.284 m(66.7 mm)。T_lift ≤ 0 は ValueError。"""
    for trick, lift_m, above in (("ozara", 0.271, 0.07594), ("chuzara", 0.2839, 0.06666)):
        kp = K.kendama_params(trick=trick)
        lift = K.swing_up_lift(kp)
        assert lift == pytest.approx(lift_m, abs=5e-4)
        ap = K.swing_up_apex(kp, lift=lift)
        target = max(kp["cup_rest_height"] + 0.9 * kp["ball_radius"], kp["top_offset"] - kp["cup_offset"][2] + kp["ball_radius"] + 0.035)
        assert ap["apex_above_cup"] == pytest.approx(target, abs=1e-12) and ap["apex_above_cup"] == pytest.approx(above, abs=5e-5)
        assert K.swing_up_apex(kp, lift=K.swing_up_lift(kp, apex_above_cup=0.05))["apex_above_cup"] == pytest.approx(0.05, abs=1e-12)
    with pytest.raises(ValueError):
        K.swing_up_lift(KP, T_lift=0.0)


def test_parabola_fit_g_exact_and_upright():
    """真空の正確な標本(8 点)から (p, v) を 1e-9 で戻す。真上に投げた玉(水平速度 0)でも悪条件にならない(各軸は [1, τ] の
    2 未知: 水平の速度 0 を 1e-12 で返す)。NaN の行は飛ばす。t_ref を渡すとその時刻の状態。点 < 2・時刻が同じ・長さ違いは拒否。"""
    p0, v0 = np.array([0.1, -0.2, 1.1]), np.array([0.3, -0.1, 2.0])
    t = np.linspace(0.0, 0.07, 8)
    P = p0 + np.outer(t, v0) - np.outer(0.5 * B.G * t * t, [0, 0, 1.0])
    f = K.parabola_fit_g(t, P)
    assert f["n"] == 8 and f["rms"] < 1e-12 and f["t_ref"] == t[-1]
    assert np.allclose(f["p"], P[-1], atol=1e-9) and np.allclose(f["v"], v0 - B.G * t[-1] * np.array([0, 0, 1.0]), atol=1e-9)
    f0 = K.parabola_fit_g(t, P, t_ref=0.0)
    assert np.allclose(f0["p"], p0, atol=1e-9) and np.allclose(f0["v"], v0, atol=1e-9)
    up = np.array([0.0, 0.0, 2.5])
    Pu = p0 + np.outer(t, up) - np.outer(0.5 * B.G * t * t, [0, 0, 1.0])
    fu = K.parabola_fit_g(t, Pu, t_ref=0.0)
    assert np.abs(fu["v"][:2]).max() < 1e-12 and fu["v"][2] == pytest.approx(2.5, abs=1e-9)
    P2 = P.copy()
    P2[3] = np.nan
    assert K.parabola_fit_g(t, P2)["n"] == 7
    for args in ((t[:1], P[:1]), (np.zeros(3), P[:3]), (t, P[:5])):
        with pytest.raises(ValueError):
            K.parabola_fit_g(*args)


def test_hole_detect_on_a_drawn_ball():
    """橙の円(半径 30 px)に暗い茶の楕円(半軸 8 × 4 px、中心は玉の中心から角度 60°・18 px)を描く: 見つかり、角度 60°(1°)、
    offset 0.6(0.02)、楕円率 0.5(0.05)。灰色の糸(彩度 0)だけなら見つからない。玉の外の暗い画素は数えない。拒否。"""
    H = W = 100
    yy, xx = np.mgrid[0:H, 0:W]
    img = np.full((H, W, 3), 0.6)
    c = np.array([50.0, 50.0])
    ball = (xx - c[0]) ** 2 + (yy - c[1]) ** 2 <= 30 ** 2
    img[ball] = (1.0, 0.55, 0.05)
    a = math.radians(60.0)
    hc = c + 18 * np.array([math.cos(a), math.sin(a)])
    u = np.array([math.cos(a), math.sin(a)])
    dx, dy = xx - hc[0], yy - hc[1]
    along, across = dx * u[0] + dy * u[1], -dx * u[1] + dy * u[0]
    hole = (along / 4.0) ** 2 + (across / 8.0) ** 2 <= 1.0
    img[hole] = (0.10, 0.06, 0.03)
    img[5:10, 5:10] = (0.1, 0.06, 0.03)                                       # 玉の外の暗い茶: 数えない
    r = K.hole_detect(img, c, 30.0)
    assert r["found"] and math.degrees(r["angle"]) == pytest.approx(60.0, abs=1.0)
    assert r["offset"] == pytest.approx(0.6, abs=0.02) and r["ellipticity"] == pytest.approx(0.5, abs=0.05)
    assert r["area"] == int(hole.sum())
    grey = np.full((H, W, 3), 0.6)
    grey[ball] = (1.0, 0.55, 0.05)
    grey[48:52, 20:80] = 0.12                                                 # 灰色の糸
    assert not K.hole_detect(grey, c, 30.0)["found"]
    with pytest.raises(ValueError):
        K.hole_detect(img[..., 0], c, 30.0)
    with pytest.raises(ValueError):
        K.hole_detect(img, c, 0.0)


def test_noisy_perceiver():
    """σ = 0 で恒等(同じ配列値)、σ > 0 で散り 1000 標本の std が σ の 0.9〜1.1 倍、速度だけ・位置だけも可、負の σ は拒否。"""
    rng = np.random.default_rng(3)
    ident = K.noisy_perceiver(rng)
    p, v = ident(0.0, [1, 2, 3], [4, 5, 6])
    assert np.array_equal(p, [1, 2, 3]) and np.array_equal(v, [4, 5, 6])
    per = K.noisy_perceiver(rng, 0.02, 0.5)
    P = np.array([per(0.0, [0, 0, 0], [0, 0, 0])[0] for _ in range(1000)])
    V = np.array([per(0.0, [0, 0, 0], [0, 0, 0])[1] for _ in range(1000)])
    assert P.shape == (1000, 3) and V.shape == (1000, 3)
    assert 0.9 < P.std() / 0.02 < 1.1 and 0.9 < V.std() / 0.5 < 1.1
    only_p = K.noisy_perceiver(rng, 0.02, 0.0)(0.0, [0, 0, 0], [1, 1, 1])
    assert np.array_equal(only_p[1], [1, 1, 1]) and np.linalg.norm(only_p[0]) > 0
    for args in ((-0.1, 0.0), (0.0, -1.0), (float("nan"), 0.0)):
        with pytest.raises(ValueError):
            K.noisy_perceiver(rng, *args)


def test_fail_closed_inputs():
    """kendama_simulate: |p₀ − handle(0)| > L、t_end < 0、dt ≤ 0、v_max/a_max ≤ 0、plan_from < 0、p₀ の形。
    pendulum_rod_simulate / pendulum_launch_speed の不正。"""
    bad = [dict(p0=[0, 0, -L - 0.01], v0=[0, 0, 0], t_end=1.0), dict(p0=_hang(), v0=[0, 0, 0], t_end=-1.0),
           dict(p0=_hang(), v0=[0, 0, 0], t_end=1.0, dt=0.0), dict(p0=_hang(), v0=[0, 0, 0], t_end=1.0, v_max=0.0),
           dict(p0=_hang(), v0=[0, 0, 0], t_end=1.0, a_max=-1.0), dict(p0=_hang(), v0=[0, 0, 0], t_end=1.0, plan_from=-1.0),
           dict(p0=[0, 0], v0=[0, 0, 0], t_end=1.0), dict(p0=_hang(), v0=[0, 0, float("nan")], t_end=1.0),
           dict(p0=_hang(), v0=[0, 0, 0], t_end=1.0, g=0.0)]
    assert len(bad) == 9
    for kw in bad:
        with pytest.raises(ValueError):
            K.kendama_simulate(KP, ORIGIN, **kw)
    with pytest.raises(ValueError):
        K.kendama_simulate(KP, [0, 0], p0=_hang(), v0=[0, 0, 0], t_end=1.0)
    for args in ((0.0, 1.0, 1.0), (L, 1.0, -1.0), (L, 1.0, 1.0, 0.0)):
        with pytest.raises(ValueError):
            K.pendulum_rod_simulate(*args)
    for args in ((-0.1, L), (math.pi + 0.1, L), (1.0, 0.0), (1.0, L, 0.0)):
        with pytest.raises(ValueError):
            K.pendulum_launch_speed(*args)


# ─────────────────────────────── 21-22 抗力と発射速度 ───────────────────────────────

def test_drag_effect_on_60mm_ball():
    """kp の bp(C_d = 0.4、ρ = 1.2、k = ½ρC_dA/m = 0.00905 /m)の玉を 1 s 自由落下: 真空より 7.1 cm 手前(設計の見込み「1 cm 未満」は誤り。
    k g² t⁴/12 の見積 7.6 cm と同程度)。0.3 s で 0.59 mm、0.5 s で 4.5 mm。けん玉の飛翔(3.33 m/s で投げ上げ、0.68 s)は
    頂点で 2.9 mm、終点で 5.7 mm 低い。真空(KV)なら閉形式と 1e-12。"""
    k = 0.5 * 1.2 * KP["bp"]["area"] * 0.4 / KP["mass"]
    assert k == pytest.approx(0.009048, rel=1e-3)
    f = B.flight_ode([0, 0, 0], [0, 0, 0], [0, 0, 0], KP["bp"], 1.0, 1e-3)
    vac = B.flight_vacuum([0, 0, 0], [0, 0, 0], f["t"])
    dz = f["p"][:, 2] - vac[:, 2]
    assert dz.shape == (1001,)
    assert dz[-1] * 100 == pytest.approx(7.09, abs=0.05)
    assert 0.5 * k * B.G ** 2 / 12 < dz[-1] < 2.0 * k * B.G ** 2 / 12
    assert dz[300] * 1000 == pytest.approx(0.59, abs=0.05)
    assert dz[500] * 1000 == pytest.approx(4.5, abs=0.1)
    assert np.all(np.diff(dz) >= 0)                                          # 抗力は落下を遅らせる一方
    up = B.flight_ode([0, 0, 0], [0, 0, 10.0 / 3.0], [0, 0, 0], KP["bp"], 0.68, 1e-3)
    upv = B.flight_vacuum([0, 0, 0], [0, 0, 10.0 / 3.0], up["t"])
    assert (up["p"][:, 2].max() - upv[:, 2].max()) * 1000 == pytest.approx(-2.87, abs=0.1)
    assert (up["p"][-1, 2] - upv[-1, 2]) * 1000 == pytest.approx(-5.73, abs=0.1)
    fv = B.flight_ode([0, 0, 0], [0, 0, 0], [0, 0, 0], KV["bp"], 1.0, 1e-3)
    assert np.abs(fv["p"][:, 2] - vac[:, 2]).max() < 1e-12


def test_pendulum_launch_speed_closed_form():
    """v₀ = √(2gL(1 − cos θ₀)): 0 → 0、π/2 → √(2gL)、π → 2√(gL)、単調増加。"""
    assert K.pendulum_launch_speed(0.0, L) == 0.0
    assert K.pendulum_launch_speed(math.pi / 2, L) == pytest.approx(math.sqrt(2 * B.G * L), rel=1e-15)
    assert K.pendulum_launch_speed(math.pi, L) == pytest.approx(2 * math.sqrt(B.G * L), rel=1e-15)
    ths = np.linspace(0, math.pi, 20)
    vs = np.array([K.pendulum_launch_speed(t, L) for t in ths])
    assert vs.shape == (20,) and np.all(np.diff(vs) > 0)
