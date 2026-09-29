"""rsssafety(RSS の安全距離)の門。

固定する性質:
- 公表値: ad-rss-lib ``RssFormulaTestsCalculateSafeLateralDistance.cpp`` の期待値(km/h → m/s、ρ 2 s、
  a_lat 0.2、b_lat 0.8、μ 0.1)、μ の加算(+0.5 片方で +0.25)、同方向で先行が速ければ 0、min_distance の加算、
  doc の 50 km/h(加速 0 で ≈ 40 m、加速 4 で 75〜90 m)
- 手計算: 同方向 26.28125、対向 58.073、横 1 km/h 両車 1.1965
- 定理(第 2 実装): 最悪ケース軌道の min_gap = d0 − d_min(同方向・対向)、d0 − (d_min − μ)(横、d_min > μ)。
  乱数 200 組。d0 = d_min で |min_gap| < 1e-6、d0 < d_min で collided、d0 > d_min で not collided
- 単調性: v_rear ↑、v_front ↓、ρ ↑、brake_min ↓
- 対称性: 対向は p1 = p2 かつ brake_min_correct = brake_min で (v1, v2) 入替に不変。横は左右入替 + 符号反転で不変
- 論文の式との一致: ρ 後の横速度が互いに向いている範囲で論文 Lemma lateral の式と一致
- fail-closed: 負の縦速度、負のパラメータ、brake_min > brake_max、brake_min_correct > brake_min、dt ≤ 0、
  負の間隔、壊れた params dict は ValueError
"""
import math

import numpy as np
import pytest

import rsssafety as R

KMH = 1.0 / 3.6
# ad-rss-lib のテスト dynamics(getObjectRssDynamics): ρ 2 s、lat accel 0.2、lat brake 0.8、μ 0.1、min_distance 0
P_LIB = R.rss_params(rho=2.0, accel_max=3.5, brake_min=4.0, brake_max=8.0, brake_min_correct=3.0,
                     lat_accel_max=0.2, lat_brake_min=0.8, lat_margin=0.1, min_distance=0.0)


# ---- 公表値(ad-rss-lib のテスト期待値) ----------------------------------------------------------------
@pytest.mark.parametrize("kmh, expected", [(0.0, 1.1), (1.0, 1.19), (-1.0, 1.19), (5.0, 2.9), (-5.0, 2.9)])
def test_lateral_same_speed_published(kmh, expected):
    v = kmh * KMH
    assert abs(R.rss_lateral(v, v, P_LIB) - expected) < 0.01
    assert abs(R.rss_lateral(v, v, P_LIB, P_LIB) - expected) < 0.01      # 左右を入れ替えても同じ


@pytest.mark.parametrize("kmh, exp_left, exp_right", [(1.0, 1.84, 0.45), (-1.0, 0.45, 1.84),
                                                       (5.0, 5.77, 0.0), (-5.0, 0.0, 5.77)])
def test_lateral_one_zero_speed_published(kmh, exp_left, exp_right):
    v = kmh * KMH
    assert abs(R.rss_lateral(v, 0.0, P_LIB) - exp_left) < 0.01
    assert abs(R.rss_lateral(0.0, v, P_LIB) - exp_right) < 0.01


@pytest.mark.parametrize("kmh, expected", [(0.0, 1.1), (1.0, 1.19), (-1.0, 1.19), (5.0, 2.9), (-5.0, 2.9)])
def test_lateral_fluctuation_margin_published(kmh, expected):
    v = kmh * KMH
    p_plus = R.rss_params(**{**P_LIB, "lat_margin": P_LIB["lat_margin"] + 0.5})
    assert abs(R.rss_lateral(v, v, P_LIB, p_plus) - (expected + 0.25)) < 0.01
    assert abs(R.rss_lateral(v, v, p_plus, p_plus) - (expected + 0.5)) < 0.01


def test_lateral_hand_calculation_1kmh():
    # 左 = 0.4 + 0.5556 + 0.6778²/1.6 = 1.2427、右 = −0.4 + 0.5556 − 0.1222²/1.6 = 0.1462 → 1.2427 − 0.1462 + 0.1
    v = 1.0 * KMH
    left = R.rss_stopping_distance(v, 2.0, +0.2, 0.8, None, +1.0)
    right = R.rss_stopping_distance(v, 2.0, -0.2, 0.8, None, -1.0)
    assert abs(left - 1.2427) < 5e-4
    assert abs(right - 0.1462) < 5e-4
    assert abs(R.rss_lateral(v, v, P_LIB) - 1.1965) < 5e-4


def test_same_direction_leading_much_faster_published():
    # lib: 先行 100 km/h、後続 10 km/h → 0。min_longitudinal_safety_distance = 2 なら 2
    assert R.rss_longitudinal_same(10 * KMH, 100 * KMH, P_LIB) == 0.0
    p2 = R.rss_params(**{**P_LIB, "min_distance": 2.0})
    assert R.rss_longitudinal_same(10 * KMH, 100 * KMH, p2) == 2.0
    # min_distance は [·]_+ の外で足す(先行が遅い普通の場合も同じ分だけ増える)
    assert abs(R.rss_longitudinal_same(20.0, 10.0, p2) - R.rss_longitudinal_same(20.0, 10.0, P_LIB) - 2.0) < 1e-12


def test_doc_50kmh_city_speed_published():
    # doc 行 99-107: 50 km/h、ρ = 2 s、brake_min 4 / brake_max 8。加速 0 → ≈ 40 m、加速 4 → 「about 80」
    v = 50 * KMH
    p0 = R.rss_params(rho=2.0, accel_max=0.0, brake_min=4.0, brake_max=8.0)
    p4 = R.rss_params(rho=2.0, accel_max=4.0, brake_min=4.0, brake_max=8.0)
    d0 = R.rss_longitudinal_same(v, v, p0)
    d4 = R.rss_longitudinal_same(v, v, p4)
    assert abs(d0 - 40.0) < 1.0
    assert 75.0 < d4 < 90.0


def test_hand_calculation_longitudinal_same():
    # v_r = 8, v_f = 0, ρ 1, accel 3.5, brake_min 4 → 8 + 1.75 + 11.5²/8 = 26.28125
    p = R.rss_params(rho=1.0, accel_max=3.5, brake_min=4.0)
    assert abs(R.rss_longitudinal_same(8.0, 0.0, p) - 26.28125) < 1e-12
    # 論文 Lemma 2 の式そのもの
    vr, vf = 12.0, 7.0
    paper = vr * 1.0 + 0.5 * 3.5 + (vr + 3.5) ** 2 / 8.0 - vf ** 2 / 16.0
    assert abs(R.rss_longitudinal_same(vr, vf, p) - paper) < 1e-12


def test_hand_calculation_longitudinal_opposite():
    # v1 = v2 = 8, ρ 1, correct 3, brake_min 4 → 9.75 + 22.0417 + 9.75 + 16.53125 = 58.073
    p = R.rss_params(rho=1.0, accel_max=3.5, brake_min=4.0, brake_min_correct=3.0)
    d = R.rss_longitudinal_opposite(8.0, 8.0, p)
    assert abs(d - 58.073) < 5e-4
    assert R.rss_longitudinal_opposite(8.0, -8.0, p) == d       # 逆走の速度は負でも大きさでも受ける
    # 論文 Lemma two_way の式そのもの
    v1r, v2r = 8.0 + 3.5, 8.0 + 3.5
    paper = (8 + v1r) / 2 * 1.0 + v1r ** 2 / 6.0 + (8 + v2r) / 2 * 1.0 + v2r ** 2 / 8.0
    assert abs(d - paper) < 1e-12


def test_default_params_are_the_published_table():
    p = R.rss_params()
    assert p == {"rho": 1.0, "accel_max": 3.5, "brake_min": 4.0, "brake_max": 8.0, "brake_min_correct": 3.0,
                 "lat_accel_max": 0.2, "lat_brake_min": 0.8, "lat_margin": 0.1, "min_distance": 0.0,
                 "v_max_accel": None}


# ---- 論文の式との一致(前提が成り立つ範囲) -----------------------------------------------------------
def test_lateral_matches_paper_formula_when_velocities_point_at_each_other():
    rng = np.random.default_rng(3)
    n_hit = 0
    for _ in range(300):
        rho, a, b, mu = rng.uniform(0.2, 2.5), rng.uniform(0.0, 1.0), rng.uniform(0.3, 2.0), rng.uniform(0.0, 0.5)
        v1, v2 = rng.uniform(-2.0, 2.0), rng.uniform(-2.0, 2.0)
        v1r, v2r = v1 + rho * a, v2 - rho * a
        if not (v1r >= 0 and v2r <= 0):
            continue
        inner = (v1 + v1r) / 2 * rho + v1r ** 2 / (2 * b) - ((v2 + v2r) / 2 * rho - v2r ** 2 / (2 * b))
        if inner < 0:
            continue                                  # [·]_+ の位置が違う領域(lib に従う)。docstring 参照
        paper = mu + inner
        p = R.rss_params(rho=rho, lat_accel_max=a, lat_brake_min=b, lat_margin=mu)
        assert abs(R.rss_lateral(v1, v2, p) - paper) < 1e-9
        n_hit += 1
    assert n_hit > 100


def test_lateral_paper_vs_lib_disagreement_is_documented():
    # 左 −5 km/h、右 0: lib は 0.0(公表テスト)、論文の式は μ + [·]_+ ≥ μ = 0.1。実装は lib。
    assert R.rss_lateral(-5 * KMH, 0.0, P_LIB) == 0.0


# ---- 定理(第 2 実装): 軌道の最小間隔 = d0 − d_min -------------------------------------------------------
def _random_params(rng, n=200):
    for _ in range(n):
        bmin, bmax = rng.uniform(2.0, 6.0), rng.uniform(6.0, 10.0)
        yield dict(rho=rng.uniform(0.2, 2.5), accel_max=rng.uniform(0.0, 5.0), brake_min=bmin, brake_max=bmax,
                   brake_min_correct=rng.uniform(1.0, bmin))


def test_theorem_same_direction_random_200():
    rng = np.random.default_rng(1)
    worst = 0.0
    n_coll = n_free = 0
    for kw in _random_params(rng):
        p = R.rss_params(**kw)
        pf = R.rss_params(**{**kw, "rho": rng.uniform(0.2, 2.5)})     # 先行は別 dict(brake_max だけ使う)
        vr, vf = rng.uniform(0.0, 30.0), rng.uniform(0.0, 30.0)
        dmin = R.rss_longitudinal_same(vr, vf, p, pf)
        d0 = dmin + rng.uniform(0.0, 20.0)
        r = R.rss_worst_case_gap(d0, vr, vf, p, pf, dt=1e-2)
        worst = max(worst, abs(r["min_gap"] - (d0 - dmin)))
        eq = R.rss_worst_case_gap(dmin, vr, vf, p, pf, dt=1e-2)
        assert abs(eq["min_gap"]) < 1e-6
        if dmin > 0.1:
            assert R.rss_worst_case_gap(dmin - 0.1, vr, vf, p, pf, dt=1e-2)["collided"]
            n_coll += 1
        assert not R.rss_worst_case_gap(dmin + 0.1, vr, vf, p, pf, dt=1e-2)["collided"]
        n_free += 1
    assert worst < 1e-6
    assert n_coll > 100 and n_free == 200


def test_theorem_opposite_random_200():
    rng = np.random.default_rng(2)
    worst = 0.0
    n_coll = 0
    for kw in _random_params(rng):
        p1 = R.rss_params(**kw)
        p2 = R.rss_params(**{**kw, "rho": rng.uniform(0.2, 2.5), "accel_max": rng.uniform(0.0, 5.0)})
        v1, v2 = rng.uniform(0.0, 30.0), rng.uniform(0.0, 30.0)
        dmin = R.rss_longitudinal_opposite(v1, v2, p1, p2)
        d0 = dmin + rng.uniform(0.0, 20.0)
        r = R.rss_worst_case_gap_opposite(d0, v1, -v2, p1, p2, dt=1e-2)
        worst = max(worst, abs(r["min_gap"] - (d0 - dmin)))
        assert abs(R.rss_worst_case_gap_opposite(dmin, v1, v2, p1, p2, dt=1e-2)["min_gap"]) < 1e-6
        assert R.rss_worst_case_gap_opposite(dmin - 0.1, v1, v2, p1, p2, dt=1e-2)["collided"]
        assert not R.rss_worst_case_gap_opposite(dmin + 0.1, v1, v2, p1, p2, dt=1e-2)["collided"]
        n_coll += 1
    assert worst < 1e-6
    assert n_coll == 200


def test_theorem_lateral_random_200():
    rng = np.random.default_rng(4)
    worst = 0.0
    n_approach = n_coll = n_assumed = 0
    shortfalls = []
    for _ in range(200):
        p1 = R.rss_params(rho=rng.uniform(0.2, 2.5), lat_accel_max=rng.uniform(0.0, 1.0),
                          lat_brake_min=rng.uniform(0.3, 2.0), lat_margin=rng.uniform(0.0, 0.5))
        p2 = R.rss_params(rho=rng.uniform(0.2, 2.5), lat_accel_max=rng.uniform(0.0, 1.0),
                          lat_brake_min=rng.uniform(0.3, 2.0), lat_margin=rng.uniform(0.0, 0.5))
        v1, v2 = rng.uniform(-3.0, 3.0), rng.uniform(-3.0, 3.0)
        dmin = R.rss_lateral(v1, v2, p1, p2)
        mu = 0.5 * (p1["lat_margin"] + p2["lat_margin"])
        core = max(dmin - mu, 0.0)                    # μ は最終間隔の下限なので比較は μ を除く
        d0 = core + rng.uniform(0.0, 5.0)
        r = R.rss_worst_case_gap_lateral(d0, v1, v2, p1, p2, dt=1e-2)
        assert r["margin"] == mu
        assert abs(r["min_gap_closed_form"] - (d0 - core)) < 1e-12
        # 閉形式は軌道の最小間隔を下回らない(下回るなら閉形式が安全側で min_gap は「もっと大きい」ことになり、
        # それは起きない): min_gap ≤ 閉形式
        assert r["min_gap"] <= d0 - core + 1e-9
        assert abs(r["shortfall"] - max(d0 - core - r["min_gap"], 0.0)) < 1e-12
        v1r, v2r = v1 + p1["rho"] * p1["lat_accel_max"], v2 - p2["rho"] * p2["lat_accel_max"]
        assert r["paper_assumption"] == (v1r >= 0 and v2r <= 0)
        if r["paper_assumption"]:
            # 論文の前提の下では定理: min_gap = d0 − max(d_min − μ, 0)、shortfall = 0
            worst = max(worst, abs(r["min_gap"] - (d0 - core)))
            assert r["shortfall"] < 1e-9
            n_assumed += 1
        else:
            shortfalls.append(r["shortfall"])
        if dmin > mu:                                 # 互いに近づく場合: 仕様の式 d0 − (d_min − μ) そのもの
            if r["paper_assumption"]:
                assert abs(r["min_gap"] - (d0 - (dmin - mu))) < 1e-6
                assert abs(R.rss_worst_case_gap_lateral(dmin - mu, v1, v2, p1, p2, dt=1e-2)["min_gap"]) < 1e-6
            n_approach += 1
            if core > 0.1:
                assert R.rss_worst_case_gap_lateral(core - 0.1, v1, v2, p1, p2, dt=1e-2)["collided"]
                n_coll += 1
        assert not R.rss_worst_case_gap_lateral(core + r["shortfall"] + 0.1, v1, v2, p1, p2, dt=1e-2)["collided"]
        # μ の門(論文の定義 = 最終間隔 ≥ μ): d0 > d_min なら final_gap > μ、d0 < d_min(d_min > 0)なら final_gap < μ
        hi = R.rss_worst_case_gap_lateral(dmin + 1e-6, v1, v2, p1, p2, dt=1e-2)
        assert not hi["margin_violated"] and hi["final_gap"] > mu
        assert hi["final_gap"] == hi["gap"][-1]
        if dmin > 1e-6:
            assert R.rss_worst_case_gap_lateral(dmin - 1e-6, v1, v2, p1, p2, dt=1e-2)["margin_violated"]
    assert worst < 1e-6
    assert n_approach > 50 and n_coll > 30 and n_assumed > 50
    # 前提の外(片方が ρ 後もまだ離れる向き)では lib の閉形式が min_gap を過大評価する例が実在する(honest disclosure)。
    # 大きさはこの乱数範囲(|v| ≤ 3 m/s、a ≤ 1、b ≥ 0.3)で 1 m 未満
    assert len(shortfalls) > 20 and max(shortfalls) > 0.0 and max(shortfalls) < 1.0


def test_lateral_shortfall_example_is_an_interior_minimum():
    # 左が左へ 1.95 m/s(離れる)、右が左へ 2.85 m/s(追う)。右が先に減速を終え t ≈ 1.42 s で速度が並び、そこが最小。
    # lib の閉形式は左を ρ_1 = 1.98 s の位置で凍結するので、その間に左が離れた分だけ間隔を大きく見積もる
    p1 = R.rss_params(rho=1.9827441881710968, lat_accel_max=0.301354105432984, lat_brake_min=1.1101928047176306)
    p2 = R.rss_params(rho=0.4177165045714264, lat_accel_max=0.37586094220218513, lat_brake_min=1.484432117656691)
    v1, v2 = -1.9504077453796753, -2.8494543381390836
    r = R.rss_worst_case_gap_lateral(5.0, v1, v2, p1, p2, dt=1e-3)
    assert not r["paper_assumption"]
    assert 0.03 < r["shortfall"] < 0.035
    assert 0.0 < r["t_min"] < p1["rho"]                                  # 内部の最小(端点でない)
    i = int(np.argmin(r["gap"]))
    assert abs(r["v1"][i] - r["v2"][i]) < 2e-3                           # 速度が並ぶ時刻
    # 論文の前提を満たすように左の加速を上げると shortfall は 0 に戻る
    q1 = R.rss_params(**{**p1, "lat_accel_max": 1.0})
    assert R.rss_worst_case_gap_lateral(5.0, v1, v2, q1, p2, dt=1e-3)["shortfall"] < 1e-9


def test_worst_case_breakpoints_are_in_the_time_grid_and_min_is_dt_independent():
    p = R.rss_params(rho=1.3, accel_max=2.0, brake_min=3.0, brake_max=7.0, v_max_accel=21.0)
    r = R.rss_worst_case_gap(60.0, 20.0, 15.0, p, dt=0.05)
    t = r["t"]
    t_cap = (21.0 - 20.0) / 2.0                        # 頭打ち時刻
    for b in (0.0, t_cap, 1.3, r["t_stop_rear"], r["t_stop_front"]):
        assert np.any(np.isclose(t, b, atol=0.0, rtol=0.0))
    assert abs(r["t_stop_rear"] - (1.3 + 21.0 / 3.0)) < 1e-12
    assert abs(r["t_stop_front"] - 15.0 / 7.0) < 1e-12
    assert np.all(np.diff(t) > 0)
    # 区分ごとの厳密式なので min_gap は dt に依らない
    r2 = R.rss_worst_case_gap(60.0, 20.0, 15.0, p, dt=1e-3)
    assert r["min_gap"] == r2["min_gap"]
    # 停止後の位置 = 閉形式の走行距離
    assert abs(r["x_rear"][-1] - R.rss_stopping_distance(20.0, 1.3, 2.0, 3.0, 21.0)) < 1e-9
    assert abs(r["x_front"][-1] - (60.0 + 15.0 ** 2 / 14.0)) < 1e-9
    assert r["v_rear"][-1] == 0.0 and r["v_front"][-1] == 0.0
    assert r["gap"].shape == t.shape and r["x_rear"].shape == t.shape


def test_worst_case_min_gap_with_min_distance():
    # min_distance は [·]_+ の外で足すので、軌道の識別式は d0 − (d_min − min_distance)
    p = R.rss_params(min_distance=2.5)
    dmin = R.rss_longitudinal_same(15.0, 10.0, p)
    r = R.rss_worst_case_gap(dmin, 15.0, 10.0, p, dt=1e-2)
    assert abs(r["min_gap"] - 2.5) < 1e-9
    assert not r["collided"]


def test_worst_case_t_max_truncates():
    p = R.rss_params()
    full = R.rss_worst_case_gap(30.0, 15.0, 10.0, p, dt=1e-2)
    cut = R.rss_worst_case_gap(30.0, 15.0, 10.0, p, dt=1e-2, t_max=0.5)
    assert cut["t"][-1] == 0.5 and cut["t"][-1] < full["t"][-1]
    assert cut["min_gap"] >= full["min_gap"]


def test_worst_case_both_stopped_is_trivial():
    # 両車静止・加速 0: 応答時間 ρ の区分だけが残り(位置は動かない)、その後は何もない
    p = R.rss_params(accel_max=0.0)
    r = R.rss_worst_case_gap(3.0, 0.0, 0.0, p)
    assert r["t"][-1] == p["rho"] and r["min_gap"] == 3.0 and not r["collided"]
    assert np.all(r["x_rear"] == 0.0) and np.all(r["x_front"] == 3.0)
    assert R.rss_longitudinal_same(0.0, 0.0, p) == 0.0
    # ρ = 0 なら時刻列は t = 0 の 1 点
    r0 = R.rss_worst_case_gap(3.0, 0.0, 0.0, R.rss_params(rho=0.0, accel_max=0.0))
    assert r0["t"].shape == (1,) and r0["min_gap"] == 3.0


# ---- stated braking pattern の個別性質 ----------------------------------------------------------------
def test_stopping_distance_speed_cap():
    # v_max で頭打ち: 到達速度 min(v + aρ, max(v_max, v))、その後定速
    s_free = R.rss_stopping_distance(10.0, 2.0, 3.0, 4.0)
    s_cap = R.rss_stopping_distance(10.0, 2.0, 3.0, 4.0, v_max=13.0)
    t_acc = 1.0
    expect = 10.0 * t_acc + 0.5 * 3.0 * t_acc ** 2 + 13.0 * (2.0 - t_acc) + 13.0 ** 2 / 8.0
    assert abs(s_cap - expect) < 1e-12 and s_cap < s_free
    # 既に v_max より速ければ加速しない(lib: max(max_speed_on_acceleration, currentSpeed))
    assert abs(R.rss_stopping_distance(20.0, 2.0, 3.0, 4.0, v_max=15.0) - (40.0 + 400.0 / 8.0)) < 1e-12
    # 十分大きい v_max は無効化と同じ
    assert R.rss_stopping_distance(10.0, 2.0, 3.0, 4.0, v_max=1e6) == s_free


def test_stopping_distance_moving_away_adds_no_stop_term():
    # 左の車が左へ(−)動いていて ρ 後も左向き: 停止距離を足さない(= ρ 時点で止まったと見なす)
    s = R.rss_stopping_distance(-2.0, 1.0, 0.2, 0.8, None, +1.0)
    assert abs(s - (-2.0 * 1.0 + 0.5 * 0.2)) < 1e-12
    # ρ 後に向きが変わる場合は変わってからの停止距離を足す
    s2 = R.rss_stopping_distance(-0.1, 1.0, 0.2, 0.8, None, +1.0)
    assert abs(s2 - (-0.1 + 0.1 + 0.1 ** 2 / 1.6)) < 1e-12


# ---- 単調性 ---------------------------------------------------------------------------------------------
def test_monotonic_in_velocities_rho_and_brake():
    rng = np.random.default_rng(5)
    for _ in range(200):
        kw = next(_random_params(rng, 1))
        p = R.rss_params(**kw)
        vr, vf = rng.uniform(0.0, 30.0), rng.uniform(0.0, 30.0)
        dv, drho, db = rng.uniform(0.0, 5.0), rng.uniform(0.0, 1.0), rng.uniform(0.0, 1.0)
        base = R.rss_longitudinal_same(vr, vf, p)
        assert R.rss_longitudinal_same(vr + dv, vf, p) >= base                        # v_rear で単調非減少
        assert R.rss_longitudinal_same(vr, vf + dv, p) <= base                        # v_front で単調非増加
        assert R.rss_longitudinal_same(vr, vf, R.rss_params(**{**kw, "rho": kw["rho"] + drho})) >= base
        bm = kw["brake_min"] + db
        p_b = R.rss_params(**{**kw, "brake_min": bm, "brake_max": max(kw["brake_max"], bm)})
        assert R.rss_longitudinal_same(vr, vf, p_b) <= base                           # brake_min で単調非増加


# ---- 対称性 ---------------------------------------------------------------------------------------------
def test_opposite_symmetric_when_correct_equals_brake_min():
    rng = np.random.default_rng(6)
    for _ in range(100):
        kw = next(_random_params(rng, 1))
        p = R.rss_params(**{**kw, "brake_min_correct": kw["brake_min"]})
        v1, v2 = rng.uniform(0.0, 30.0), rng.uniform(0.0, 30.0)
        assert abs(R.rss_longitudinal_opposite(v1, v2, p) - R.rss_longitudinal_opposite(v2, v1, p)) < 1e-9
        # correct ≠ brake_min なら役割の入れ替えは brake の入れ替え
        q = R.rss_params(**kw)
        a = R.rss_longitudinal_opposite(v1, v2, q)
        s1 = R.rss_stopping_distance(v2, q["rho"], q["accel_max"], q["brake_min_correct"])
        s2 = R.rss_stopping_distance(v1, q["rho"], q["accel_max"], q["brake_min"])
        assert abs(R.rss_longitudinal_opposite(v2, v1, q) - (s1 + s2)) < 1e-9
        if kw["brake_min_correct"] < kw["brake_min"]:
            assert a != R.rss_longitudinal_opposite(v2, v1, q) or v1 == v2


def test_lateral_mirror_symmetry():
    rng = np.random.default_rng(7)
    for _ in range(200):
        p1 = R.rss_params(rho=rng.uniform(0.2, 2.5), lat_accel_max=rng.uniform(0.0, 1.0),
                          lat_brake_min=rng.uniform(0.3, 2.0), lat_margin=rng.uniform(0.0, 0.5))
        p2 = R.rss_params(rho=rng.uniform(0.2, 2.5), lat_accel_max=rng.uniform(0.0, 1.0),
                          lat_brake_min=rng.uniform(0.3, 2.0), lat_margin=rng.uniform(0.0, 0.5))
        v1, v2 = rng.uniform(-3.0, 3.0), rng.uniform(-3.0, 3.0)
        # 左右入れ替え + 速度の符号反転(鏡映)で不変
        assert abs(R.rss_lateral(v1, v2, p1, p2) - R.rss_lateral(-v2, -v1, p2, p1)) < 1e-9
        r = R.rss_worst_case_gap_lateral(4.0, v1, v2, p1, p2, dt=1e-2)
        m = R.rss_worst_case_gap_lateral(4.0, -v2, -v1, p2, p1, dt=1e-2)
        assert abs(r["min_gap"] - m["min_gap"]) < 1e-9


# ---- 判定 -----------------------------------------------------------------------------------------------
def test_checks_flags():
    p = R.rss_params()
    d = R.rss_longitudinal_same(20.0, 10.0, p)
    c = R.rss_longitudinal_check(d + 1.0, 20.0, 10.0, p)
    assert c["safe_distance"] == d and not c["dangerous"] and abs(c["margin"] - 1.0) < 1e-12
    assert R.rss_longitudinal_check(d, 20.0, 10.0, p)["dangerous"]              # lib: d > safe でないと危険
    assert R.rss_longitudinal_check(d - 1.0, 20.0, 10.0, p)["dangerous"]
    dl = R.rss_lateral(0.5, -0.5, p)
    assert not R.rss_lateral_check(dl + 0.01, 0.5, -0.5, p)["dangerous"]
    assert R.rss_lateral_check(dl - 0.01, 0.5, -0.5, p)["dangerous"]
    assert R.rss_lateral_check(dl - 0.01, 0.5, -0.5, p)["margin"] < 0


# ---- fail-closed ----------------------------------------------------------------------------------------
@pytest.mark.parametrize("kw", [dict(rho=-0.1), dict(accel_max=-1.0), dict(brake_min=0.0), dict(brake_min=-4.0),
                                dict(brake_max=-8.0), dict(brake_min_correct=-3.0), dict(lat_accel_max=-0.2),
                                dict(lat_brake_min=0.0), dict(lat_margin=-0.1), dict(min_distance=-1.0),
                                dict(v_max_accel=-5.0), dict(brake_min=9.0, brake_max=8.0),
                                dict(brake_min_correct=5.0, brake_min=4.0), dict(rho=float("nan")),
                                dict(rho=float("inf")), dict(rho="a")])
def test_params_fail_closed(kw):
    with pytest.raises(ValueError):
        R.rss_params(**kw)


def test_functions_fail_closed():
    p = R.rss_params()
    with pytest.raises(ValueError):
        R.rss_longitudinal_same(-1.0, 5.0, p)
    with pytest.raises(ValueError):
        R.rss_longitudinal_same(5.0, -1.0, p)
    with pytest.raises(ValueError):
        R.rss_longitudinal_opposite(-1.0, 5.0, p)
    with pytest.raises(ValueError):
        R.rss_longitudinal_check(-0.5, 5.0, 5.0, p)
    with pytest.raises(ValueError):
        R.rss_lateral_check(-0.5, 0.0, 0.0, p)
    with pytest.raises(ValueError):
        R.rss_worst_case_gap(10.0, 5.0, 5.0, p, dt=0.0)
    with pytest.raises(ValueError):
        R.rss_worst_case_gap_opposite(10.0, 5.0, 5.0, p, dt=-1e-3)
    with pytest.raises(ValueError):
        R.rss_worst_case_gap_lateral(1.0, 0.0, 0.0, p, dt=0.0)
    with pytest.raises(ValueError):
        R.rss_worst_case_gap(-1.0, 5.0, 5.0, p)
    with pytest.raises(ValueError):
        R.rss_worst_case_gap(10.0, 5.0, 5.0, p, t_max=0.0)
    with pytest.raises(ValueError):
        R.rss_stopping_distance(5.0, 1.0, -1.0, 4.0)                    # accel が相手と逆向き
    with pytest.raises(ValueError):
        R.rss_stopping_distance(5.0, 1.0, 1.0, 0.0)                     # brake = 0
    with pytest.raises(ValueError):
        R.rss_stopping_distance(5.0, 1.0, 1.0, 4.0, direction=0.5)
    bad = dict(p)
    bad.pop("rho")
    with pytest.raises(ValueError):
        R.rss_longitudinal_same(5.0, 5.0, bad)
    with pytest.raises(ValueError):
        R.rss_longitudinal_same(5.0, 5.0, {**p, "extra": 1.0})
    with pytest.raises(ValueError):
        R.rss_longitudinal_same(5.0, 5.0, {**p, "brake_min": 9.0})      # 手で壊した dict も検査する
    with pytest.raises(ValueError):
        R.rss_lateral(0.0, 0.0, "not a dict")


def test_all_exports_exist():
    for name in R.__all__:
        assert callable(getattr(R, name))
    assert len(R.__all__) == 10
