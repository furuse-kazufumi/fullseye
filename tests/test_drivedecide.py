"""drivedecide(判断の場面)の門。

固定する性質(閉形式と独立な経路で比べる):
- 平面鏡: 折り返し S は対合・行列式 −1。鏡像の位置 S(Q) = 「入射角 = 反射角」を Fermat の最短経路で数値に解いた
  光線追跡の見かけの点(1e-9)。P·S で写した画素 = 実カメラが鏡越しに見る画素。仮想カメラ F·P·S は行列式 +1 で
  画像は u' = 2c_x − u(左右反転)。
- 鏡の向き: 法線で反射した光線が狙った向きになる(2D・3D)。
- 凸面鏡の視野角: 厳密式 = 光線と球の交点を二分法で縁に合わせて反射させた角(1e-9)、R → ∞ で平面鏡、
  近軸の誤差は開口を半分にすると約 1/8(3 次)。
- 死角: 多角形 = 細かい格子の点ごとの光線追跡(鏡の円弧上 601 点の反射光線の符号の切り替わり + 方位)。境界から
  格子 1.5 目より離れた点は全一致、面積は格子の数え上げと一致。
- 確認の順序: 正しい順序で満点、順序の 6 通りの真理表、約 3 秒・30 m の境目、合図の継続・終了(法 53 条)、減点 =
  丁運発第44号の 10 / 5 点。
- 信号: 時間割の衝突なし・F = L/v、予測の区間が真値を必ず含み誤差 ≤ 半幅 ≤ 1/(2 fps)(400 試行)。
- ジレンマゾーン: 刻みを進めるシミュレーションの「止まれず抜けられない」初期位置の集合 = (x_0, x_c)、
  x_c = rsssafety.rss_stopping_distance(v, δ, 0, a)、v_critical で長さ 0。
- 光: 点滅の推定 = 真の周波数(fps/2 未満)/ aliased_frequency の値(fps/2 超)。
- 音: 合成音(発音時刻の 2 次方程式だけで作る)の真の周波数 = 数値微分 f_e dτ/dt = doppler_shift の式、
  doppler_track の視線速度 = 幾何の真値、近づく → 遠ざかるの判定、取り違えの境目の速さ。TDOA の方位 = 幾何。
- 40 条・31 条の 2 の採点の真理表、バスの a_req = rsssafety と刻みのブレーキ(二分法)。
- fail-closed: 形・範囲・矛盾は ValueError。
"""
import itertools
import math

import numpy as np
import pytest

import drivedecide as D
import rsssafety as R


def _look_at(eye, target, up=(0.0, 0.0, 1.0)):
    """render3d.look_at と同じ規約(world→camera、−Z 前方)。ここでは import を避けて同じ式を書く。"""
    e, t, u = (np.asarray(a, float) for a in (eye, target, up))
    f = (t - e) / np.linalg.norm(t - e)
    s = np.cross(f, u)
    s /= np.linalg.norm(s)
    u2 = np.cross(s, f)
    Rm = np.stack([s, u2, -f])
    P = np.eye(4)
    P[:3, :3] = Rm
    P[:3, 3] = -Rm @ e
    return P


def _fermat_point(C, Q, n, d):
    """鏡面 n·X = d 上で |C − M| + |M − Q| を最小にする M(Newton、数値の勾配・ヘッセ)。"""
    e1 = np.cross(n, [1.0, 0.0, 0.0] if abs(n[0]) < 0.9 else [0.0, 1.0, 0.0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(n, e1)
    M0 = d * n

    def f(ab):
        M = M0 + ab[0] * e1 + ab[1] * e2
        return np.linalg.norm(C - M) + np.linalg.norm(M - Q)

    ab = np.array([(C @ e1 + Q @ e1) / 2, (C @ e2 + Q @ e2) / 2])
    h = 1e-5
    for _ in range(60):
        g = np.array([(f(ab + h * np.eye(2)[i]) - f(ab - h * np.eye(2)[i])) / (2 * h) for i in range(2)])
        H = np.array([[(f(ab + h * (np.eye(2)[i] + np.eye(2)[j])) - f(ab + h * (np.eye(2)[i] - np.eye(2)[j]))
                        - f(ab - h * (np.eye(2)[i] - np.eye(2)[j])) + f(ab - h * (np.eye(2)[i] + np.eye(2)[j])))
                       / (4 * h * h) for j in range(2)] for i in range(2)])
        step = np.linalg.solve(H, g)
        ab = ab - step
        if np.linalg.norm(step) < 1e-13:
            break
    return M0 + ab[0] * e1 + ab[1] * e2


# ---- 1. ミラー ---------------------------------------------------------------------------------------
def test_reflection_matrix_is_involution_with_det_minus_one():
    S = D.mirror_reflection_matrix([0.3, -1.0, 0.5, 2.0])
    np.testing.assert_allclose(S @ S, np.eye(4), atol=1e-14)
    assert np.linalg.det(S[:3, :3]) == pytest.approx(-1.0, abs=1e-14)
    n = np.array([0.3, -1.0, 0.5]) / np.linalg.norm([0.3, -1.0, 0.5])
    X = np.array([1.0, 2.0, 3.0])
    on_plane = X - (n @ X - 2.0 / np.linalg.norm([0.3, -1.0, 0.5])) * n
    np.testing.assert_allclose((S @ np.r_[on_plane, 1])[:3], on_plane, atol=1e-13)


@pytest.mark.parametrize("seed", range(5))
def test_mirror_image_equals_ray_traced_reflection(seed):
    rng = np.random.default_rng(seed)
    n = rng.normal(size=3)
    n /= np.linalg.norm(n)
    d = rng.uniform(-1, 1)
    # カメラと物体は鏡の前(n·X > d)
    C = d * n + rng.normal(size=3) * 2 + 3 * n
    C += max(0.0, d + 0.5 - n @ C) * n
    Q = d * n + rng.normal(size=3) * 2 + 2 * n
    Q += max(0.0, d + 0.5 - n @ Q) * n
    P = _look_at(C, d * n)
    out = D.mirror_virtual_camera(P, np.r_[n, d])
    np.testing.assert_allclose(out["eye_real"], C, atol=1e-12)
    M = _fermat_point(C, Q, n, d)
    assert abs(n @ M - d) < 1e-12
    # 入射角 = 反射角、同一平面
    a_in = np.dot(C - M, n) / np.linalg.norm(C - M)
    a_out = np.dot(Q - M, n) / np.linalg.norm(Q - M)
    assert a_in == pytest.approx(a_out, abs=1e-8)
    assert abs(np.linalg.det(np.stack([n, C - M, Q - M]))) < 1e-7 * np.linalg.norm(C - M) * np.linalg.norm(Q - M)
    L = np.linalg.norm(C - M) + np.linalg.norm(M - Q)
    apparent = C + L * (M - C) / np.linalg.norm(M - C)
    SQ = (out["reflection"] @ np.r_[Q, 1])[:3]
    np.testing.assert_allclose(SQ, apparent, atol=1e-7)
    # P·S で写した Q = 実カメラで写した見かけの点
    np.testing.assert_allclose(out["pose_mirrored"] @ np.r_[Q, 1], P @ np.r_[apparent, 1], atol=1e-7)
    # 仮想カメラ: 行列式 +1、x だけ反転、位置 = S(C)
    Pv = out["pose"]
    assert np.linalg.det(Pv[:3, :3]) == pytest.approx(1.0, abs=1e-12)
    cm, cv = out["pose_mirrored"] @ np.r_[Q, 1], Pv @ np.r_[Q, 1]
    np.testing.assert_allclose(cv, cm * np.array([-1, 1, 1, 1]), atol=1e-12)
    np.testing.assert_allclose(Pv[:3, :3] @ out["eye"] + Pv[:3, 3], 0.0, atol=1e-11)
    # 画素: u' = 2 c_x − u
    K = np.array([[500.0, 0, 320.0], [0, 500.0, 240.0], [0, 0, 1]])
    um = K @ (cm[:3] * np.array([1, -1, -1]))
    uv = K @ (cv[:3] * np.array([1, -1, -1]))
    assert uv[0] / uv[2] == pytest.approx(2 * 320.0 - um[0] / um[2], abs=1e-9)
    assert uv[1] / uv[2] == pytest.approx(um[1] / um[2], abs=1e-9)


@pytest.mark.parametrize("dim", [2, 3])
def test_mirror_aim_normal_reflects_to_look_dir(dim):
    rng = np.random.default_rng(dim)
    for _ in range(20):
        E, M, L = rng.normal(size=dim), rng.normal(size=dim), rng.normal(size=dim)
        n = D.mirror_aim_normal(E, M, L)
        d = (M - E) / np.linalg.norm(M - E)
        r = d - 2 * (d @ n) * n
        np.testing.assert_allclose(r, L / np.linalg.norm(L), atol=1e-12)
        assert n @ (E - M) > 0


def _trace_convex_edge(R_, h, Dd):
    """眼 (0, D)(頂点 (0,0)、球の中心 (0, −R))から出て球の y 座標が h になる所に当たる光線を二分法で探し、
    反射した光線の軸(+y 向き)からの角を返す。"""
    O = np.array([0.0, -R_])
    E = np.array([0.0, Dd])

    def hit(phi):                                     # 光線 E + s(sin φ, −cos φ)
        dvec = np.array([math.sin(phi), -math.cos(phi)])
        m = E - O
        b = m @ dvec
        c = m @ m - R_ * R_
        disc = b * b - c
        if disc < 0:
            return None, dvec
        s = -b - math.sqrt(disc)
        return E + s * dvec, dvec

    lo, hi = 0.0, math.pi / 2
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        P, _ = hit(mid)
        if P is not None and P[0] < h:
            lo = mid
        else:
            hi = mid
    P, dvec = hit(lo)
    nrm = (P - O) / R_
    r = dvec - 2 * (dvec @ nrm) * nrm
    return math.atan2(r[0], r[1]), P


@pytest.mark.parametrize("R_,a,Dd", [(1.4, 0.18, 0.9), (0.5, 0.3, 1.2), (3.0, 0.4, 0.6), (0.25, 0.4, 2.0)])
def test_convex_fov_equals_ray_tracing(R_, a, Dd):
    out = D.convex_mirror_fov(R_, a, Dd)
    ang, P = _trace_convex_edge(R_, a / 2, Dd)
    assert P[0] == pytest.approx(a / 2, abs=1e-10)
    assert out["fov_rad"] == pytest.approx(2 * ang, rel=1e-9)
    assert out["widening"] > 1.0


def test_convex_fov_flat_limit_and_paraxial_order():
    flat = D.convex_mirror_fov(math.inf, 0.2, 1.0)
    assert flat["fov_rad"] == pytest.approx(2 * math.atan(0.1), rel=1e-15)
    assert D.convex_mirror_fov(1e9, 0.2, 1.0)["fov_rad"] == pytest.approx(flat["fov_rad"], rel=1e-8)
    e = []
    for a in (0.2, 0.1, 0.05):
        o = D.convex_mirror_fov(1.4, a, 1.0)
        e.append(abs(o["fov_rad"] - o["fov_paraxial_rad"]))
    r1, r2 = e[0] / e[1], e[1] / e[2]
    assert 7.0 < r1 < 9.0 and 7.0 < r2 < 9.0, (r1, r2)   # 3 次(2 次なら 4)


# 日本の右ハンドル車(x 前、y 左)。値は例(仮定)。
EYE = np.array([-2.3, -0.4])
MIR = np.array([-1.9, 1.05])


def _mirror_visible(T, E, Mc, n0, w, R_, n_arc=601):
    """格子の点ごとの光線追跡: 円弧上の n_arc 点で反射した光線と (T − P) の外積の符号が変われば見える。"""
    t = np.array([-n0[1], n0[0]])
    if math.isinf(R_):
        u = np.linspace(-w, w, n_arc)
        P = Mc + u[:, None] * t
        N = np.repeat(n0[None], n_arc, 0)
    else:
        phi = np.linspace(-math.asin(w / R_), math.asin(w / R_), n_arc)
        N = np.cos(phi)[:, None] * n0 + np.sin(phi)[:, None] * t
        P = (Mc - R_ * n0) + R_ * N
    d = P - E
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    r = d - 2 * np.sum(d * N, 1, keepdims=True) * N
    V = T[:, None, :] - P[None, :, :]
    cr = r[None, :, 0] * V[:, :, 1] - r[None, :, 1] * V[:, :, 0]
    dot = np.sum(r[None] * V, axis=2)
    sgn = np.sign(cr)
    change = np.any(sgn[:, :-1] * sgn[:, 1:] <= 0, axis=1)
    ahead = np.max(dot, axis=1) > 0
    return change & ahead


def _in_convex(T, poly):
    e = np.roll(poly, -1, 0) - poly
    cr = e[None, :, 0] * (T[:, None, 1] - poly[None, :, 1]) - e[None, :, 1] * (T[:, None, 0] - poly[None, :, 0])
    return np.all(cr >= 0, axis=1) | np.all(cr <= 0, axis=1)


def _seg_dist(T, A, B):
    AB = B - A
    s = np.clip(((T - A) @ AB) / (AB @ AB), 0, 1)
    return np.linalg.norm(T - (A + s[:, None] * AB), axis=1)


@pytest.mark.parametrize("R_", [1.4, math.inf])
def test_blind_zone_matches_grid_ray_tracing(R_):
    n0 = D.mirror_aim_normal(EYE, MIR, [-1.0, 0.10])
    roi = (-15.0, -2.0, 0.9, 4.4)
    out = D.mirror_blind_zone(EYE, MIR, n0, 0.18, mirror_radius=R_, direct_limit_deg=100.0, roi=roi)
    h = 0.07
    xs = np.arange(roi[0] + h / 2, roi[1], h)
    ys = np.arange(roi[2] + h / 2, roi[3], h)
    T = np.stack(np.meshgrid(xs, ys), -1).reshape(-1, 2)
    brg = np.degrees(np.arctan2(T[:, 1] - EYE[1], T[:, 0] - EYE[0]))
    blind_true = ~(_mirror_visible(T, EYE, MIR, n0, 0.09, R_) | (brg <= 100.0))
    inpoly = np.zeros(len(T), bool)
    for p in out["pieces"]:
        inpoly |= _in_convex(T, p)
    edges = [(p[i], p[(i + 1) % len(p)]) for p in out["pieces"] for i in range(len(p))]
    dist = np.min([_seg_dist(T, a, b) for a, b in edges], axis=0)
    far = dist > 1.5 * h
    assert np.array_equal(inpoly[far], blind_true[far])
    assert out["area"] == pytest.approx(blind_true.sum() * h * h, rel=0.02)
    assert out["area"] > 1.0                                   # 死角が実際にある
    assert out["area"] + out["mirror_area"] + out["direct_area"] >= out["roi_area"] - 1e-9


def test_convex_mirror_shrinks_blind_zone():
    n0 = D.mirror_aim_normal(EYE, MIR, [-1.0, 0.10])
    flat = D.mirror_blind_zone(EYE, MIR, n0, 0.18, mirror_radius=math.inf)
    cvx = D.mirror_blind_zone(EYE, MIR, n0, 0.18, mirror_radius=1.4)
    assert cvx["area"] < flat["area"]
    assert cvx["mirror_area"] > flat["mirror_area"]


# ---- 2. 確認の順序 -----------------------------------------------------------------------------------
def _lc(mirror=0.0, sig=1.0, start=4.0, end=7.0, off=7.5):
    ev = [{"t": sig, "kind": "signal_on"}, {"t": start, "kind": "start"}]
    if mirror is not None:
        ev.append({"t": mirror, "kind": "mirror"})
    if end is not None:
        ev.append({"t": end, "kind": "end"})
    if off is not None:
        ev.append({"t": off, "kind": "signal_off"})
    return ev


def test_sequence_perfect_lane_change_scores_100():
    r = D.check_sequence_score(_lc())
    assert r["ok"] and r["score"] == 100 and r["lead"] == pytest.approx(3.0) and r["passes_exam"]


def test_sequence_order_truth_table():
    """ミラー・合図・進路変更の 6 通りの並び。満点は「ミラー → 合図 → 進路変更」だけ。"""
    base = {"mirror": 0.0, "signal_on": 1.0, "start": 4.5}
    expect = {("mirror", "signal_on", "start"): set()}
    for order in itertools.permutations(base):
        times = dict(zip(order, (0.0, 1.0, 4.5)))
        ev = [{"t": times[k], "kind": k} for k in order] + [{"t": 8.0, "kind": "end"}, {"t": 8.2, "kind": "signal_off"}]
        r = D.check_sequence_score(ev)
        rules = {v["rule"] for v in r["violations"]}
        if order in expect:
            assert rules == set()
        else:
            assert rules, order                        # どの並びも何か減点される
            if times["signal_on"] > times["start"]:
                assert "signal_missing" in rules
            elif times["mirror"] > times["signal_on"]:
                assert "safety_check_missing" in rules


def test_sequence_lead_time_boundary_and_deductions():
    ok = D.check_sequence_score(_lc(sig=1.5, start=4.0))      # 2.5 s = 3 − 0.5 ちょうど
    assert ok["ok"]
    bad = D.check_sequence_score(_lc(sig=1.6, start=4.0))
    assert [v["rule"] for v in bad["violations"]] == ["signal_timing"] and bad["deduction"] == 5
    early = D.check_sequence_score(_lc(sig=-10.0, mirror=-11.0), max_lead=8.0)
    assert [v["rule"] for v in early["violations"]] == ["signal_timing"]
    nomirror = D.check_sequence_score(_lc(mirror=None))
    assert nomirror["deduction"] == 10 and nomirror["violations"][0]["rule"] == "safety_check_missing"
    # 合図を途中でやめる / やめない(法 53 条 1 項・4 項)
    assert [v["rule"] for v in D.check_sequence_score(_lc(off=5.0))["violations"]] == ["signal_not_continued"]
    assert [v["rule"] for v in D.check_sequence_score(_lc(off=None))["violations"]] == ["signal_not_cancelled"]
    assert [v["rule"] for v in D.check_sequence_score(_lc(off=12.0))["violations"]] == ["signal_not_cancelled"]
    assert D.CHECK_DEDUCTIONS["safety_check_missing"] == 10 and D.CHECK_DEDUCTIONS["signal_timing"] == 5
    assert D.SOURCES["check_deductions"]["status"] == "primary"


def test_sequence_turn_30m():
    def ev(s_sig):
        return [{"t": 0.0, "kind": "mirror"}, {"t": 1.0, "kind": "signal_on", "s": s_sig},
                {"t": 5.0, "kind": "start", "s": 100.0}, {"t": 8.0, "kind": "end"}, {"t": 8.5, "kind": "signal_off"}]
    assert D.check_sequence_score(ev(70.0), maneuver="left_turn")["ok"]
    assert D.check_sequence_score(ev(73.0), maneuver="left_turn")["ok"]          # 27 m = 30 − 3
    r = D.check_sequence_score(ev(75.0), maneuver="right_turn")
    assert r["distance"] == pytest.approx(25.0) and [v["rule"] for v in r["violations"]] == ["signal_timing"]


def test_sequence_signal_cancelled_before_start_counts_as_missing():
    ev = _lc() + [{"t": 2.0, "kind": "signal_off"}]
    rules = [v["rule"] for v in D.check_sequence_score(ev)["violations"]]
    assert rules[0] == "signal_missing"


# ---- 3. 信号 ---------------------------------------------------------------------------------------
def _plan(**kw):
    p = dict(crossing_length=15.0, ped_green=12.0, walk_speed=1.0, ped_red_to_amber=2.0, amber=3.0, all_red=2.0,
             cross_green=20.0)
    p.update(kw)
    return D.signal_phase_plan(**p)


def test_signal_plan_structure_and_no_conflict():
    pl = _plan()
    assert pl["ped_flash_duration"] == pytest.approx(15.0)
    assert pl["amber_onset"] == pytest.approx(12 + 15 + 2)
    assert _plan(flash_fraction=0.5)["ped_flash_duration"] == pytest.approx(7.5)
    t = np.linspace(0, pl["cycle"], 20001, endpoint=False)
    a = D.signal_state(pl, "veh_A", t)
    b = D.signal_state(pl, "veh_B", t)
    p = D.signal_state(pl, "ped_A", t)
    go = lambda s: (s == "green") | (s == "amber")                   # noqa: E731
    assert not np.any(go(a) & go(b))                                 # 交差する流れが同時に動かない
    assert not np.any(((p == "green") | (p == "flash")) & (a != "green"))
    assert np.all(a[t < pl["amber_onset"]] == "green")
    # 全赤
    ar = (t >= pl["red_onset"]) & (t < pl["red_onset"] + pl["all_red"])
    assert np.all((a[ar] == "red") & (b[ar] == "red"))


@pytest.mark.parametrize("fps", [10.0, 2.0])
def test_predict_amber_onset_interval_contains_truth(fps):
    rng = np.random.default_rng(int(fps))
    pl = _plan()
    worst = 0.0
    for _ in range(200):
        off = rng.uniform(0, pl["cycle"])
        t0 = off + rng.uniform(0, 1 / fps)
        ts = t0 + np.arange(0, 60, 1 / fps)
        ts = ts[ts < off + pl["amber_onset"]]                       # 黄の前までしか見ていない
        st = D.signal_state(pl, "ped_A", ts - off)
        obs = list(zip(ts, st))
        if not any(s == "flash" for s in st):
            continue
        r = D.predict_amber_onset(obs, crossing_length=15.0, walk_speed=1.0, ped_red_to_amber=2.0)
        truth = off + pl["amber_onset"]
        assert r["lo"] - 1e-9 <= truth <= r["hi"] + 1e-9
        err = abs(r["amber_onset"] - truth)
        assert err <= r["half_width"] + 1e-9 and r["half_width"] <= 0.5 / fps + 1e-9
        worst = max(worst, err)
    assert worst > 0.3 * 0.5 / fps                                  # 区間の幅は本当に効いている(0 ではない)


def test_predict_amber_with_red_only_and_inconsistent():
    r = D.predict_amber_onset([(10.0, "flash"), (10.5, "red")], ped_red_to_amber=2.0)
    assert (r["lo"], r["hi"]) == (12.0, 12.5) and r["basis"] == ["flash->red"]
    with pytest.raises(ValueError):
        D.predict_amber_onset([(0.0, "green"), (0.5, "flash"), (2.0, "flash"), (2.5, "red")],
                              flash_duration=15.0, ped_red_to_amber=2.0)
    with pytest.raises(ValueError):
        D.predict_amber_onset([(0.0, "green"), (1.0, "green")], flash_duration=5.0)


def _simulate_dilemma(x, v, rho, a, tau, w, L, dt=1e-3):
    """刻みを進める: (1) 反応の後に減速して止まる位置 ≤ x か (2) 一定速度で τ の間に x + w + L を越えるか。"""
    s, vv, t = 0.0, v, 0.0
    while vv > 0:
        acc = 0.0 if t < rho else -a
        v_new = max(0.0, vv + acc * dt)
        s += 0.5 * (vv + v_new) * dt
        vv, t = v_new, t + dt
    can_stop = s <= x + 1e-9
    n = int(round(tau / dt))
    s2 = 0.0
    for _ in range(n):
        s2 += v * dt
    can_clear = s2 >= x + w + L - 1e-9
    return can_stop, can_clear


@pytest.mark.parametrize("v", [8.0, 13.9, 16.7])
def test_dilemma_zone_equals_simulation(v):
    rho, a, tau, w, L = 1.0, 3.0, 3.0, 20.0, 4.5
    dz = D.dilemma_zone(v, reaction=rho, decel=a, amber=tau, intersection_width=w, car_length=L)
    assert dz["x_stop_min"] == pytest.approx(R.rss_stopping_distance(v, rho, 0.0, a), rel=1e-12)
    xs = np.arange(0.0, 80.0, 0.25)
    neither = []
    for x in xs:
        cs, cc = _simulate_dilemma(x, v, rho, a, tau, w, L, dt=2e-3)
        if not cs and not cc:
            neither.append(x)
    if dz["dilemma"] is None:
        assert not neither
    else:
        lo, hi = dz["dilemma"]
        res = 0.25 + v * 2e-3 * 2
        assert neither, "simulation found no dilemma"
        assert min(neither) == pytest.approx(max(lo, 0.0), abs=res)
        assert max(neither) == pytest.approx(hi, abs=res)
        assert all(lo - res < x < hi + res for x in neither)


def test_dilemma_critical_speeds_and_option_zone():
    kw = dict(reaction=1.0, decel=3.0, amber=4.0, intersection_width=5.0, car_length=4.5)
    dz = D.dilemma_zone(12.0, **kw)
    vc = dz["v_critical"]
    assert len(vc) == 2
    for v in vc:
        assert D.dilemma_zone(v, **kw)["length"] == pytest.approx(0.0, abs=1e-9)
    mid = 0.5 * (vc[0] + vc[1])
    assert D.dilemma_zone(mid, **kw)["option"] is not None and D.dilemma_zone(mid, **kw)["dilemma"] is None
    assert D.dilemma_zone(vc[1] + 2.0, **kw)["dilemma"] is not None
    # 黄の間に加速すると抜けられる距離が延びる
    assert D.dilemma_zone(15.0, accel=1.0, **kw)["x_clear_max"] > D.dilemma_zone(15.0, **kw)["x_clear_max"]


# ---- 4. 光 ------------------------------------------------------------------------------------------
def _square_flash(f, fps, dur, rng):
    t = np.arange(int(dur * fps)) / fps
    ph = rng.uniform(0, 1)
    return 50.0 + 150.0 * (np.mod(f * t + ph, 1.0) < 0.5) + rng.normal(0, 3.0, t.size)


def test_aliased_frequency_closed_form():
    assert D.aliased_frequency(3.0, 30.0) == 3.0
    assert D.aliased_frequency(27.0, 30.0) == pytest.approx(3.0)
    assert D.aliased_frequency(31.0, 30.0) == pytest.approx(1.0)
    assert D.aliased_frequency(60.0, 30.0) == pytest.approx(0.0)
    np.testing.assert_allclose(D.aliased_frequency(np.array([40.0, 58.5]), 30.0), [10.0, 1.5])
    assert np.all(D.aliased_frequency(np.linspace(0, 200, 999), 30.0) <= 15.0 + 1e-12)


@pytest.mark.parametrize("f", [1.5, 2.2, 27.0, 31.0, 40.0, 58.5])
def test_flash_frequency_matches_true_or_aliased(f):
    rng = np.random.default_rng(int(f * 10))
    fps = 30.0
    x = _square_flash(f, fps, 12.0, rng)
    for pad in (8, 1):                       # 0 詰めなし(格子 fps/512 ≈ 0.06 Hz)でも放物線補間で 1e-3 Hz
        r = D.flash_frequency(x, fps, pad=pad)
        assert r["frequency"] == pytest.approx(D.aliased_frequency(f, fps), abs=1e-3)
        assert r["peak_ratio"] > 10


# ---- 4. 音 ------------------------------------------------------------------------------------------
FS = 16000.0


def test_doppler_shift_closed_form():
    assert D.doppler_shift(960.0, 0.0) == 960.0
    assert D.doppler_shift(960.0, 20.0) == pytest.approx(960 * 343 / 323)
    assert D.doppler_shift(960.0, -20.0) < 960.0
    with pytest.raises(ValueError):
        D.doppler_shift(960.0, 343.0)


def test_siren_true_frequency_is_geometric_doppler():
    s = D.siren_signal(4.0, FS, source_start=(-30.0, 8.0), source_velocity=(15.0, 0.0))
    tau, t, fe = s["tau"][0], s["t"], s["f_emit"][0]
    dtau = np.gradient(tau, t)                               # 発音時刻の数値微分(式を使わない)
    np.testing.assert_allclose(s["f_true"][0], fe * dtau, rtol=1e-6)
    np.testing.assert_allclose(s["f_true"][0], D.doppler_shift(fe, s["v_radial"][0]), rtol=1e-12)


def test_siren_moving_mic_true_frequency_and_range_rate():
    """マイクが動く(自車に載る)版: f_true = f_e · dτ/dt(数値微分)、range_rate = 受信時の距離の数値微分、
    止まったマイクでは従来の値と一致(v_radial = 発音時の −ṙ)。"""
    uL = (8.0, 0.0)
    s = D.siren_signal(4.0, FS, source_start=(-40.0, -2.0), source_velocity=(17.0, 0.0), mics=((0.0, 0.5),), mic_velocity=uL)
    tau, t, fe = s["tau"][0], s["t"], s["f_emit"][0]
    np.testing.assert_allclose(s["f_true"][0], fe * np.gradient(tau, t), rtol=1e-6)
    p = np.array([-40.0, -2.0])[None, :] + tau[:, None] * np.array([17.0, 0.0])[None, :]
    m = np.array([0.0, 0.5])[None, :] + t[:, None] * np.array(uL)[None, :]
    r = np.linalg.norm(p - m, axis=1)
    np.testing.assert_allclose(s["range_rate"][0][1:-1], np.gradient(r, t)[1:-1], atol=2e-5)
    np.testing.assert_allclose(s["f_true"][0], D.doppler_shift(fe, s["v_radial"][0]), rtol=1e-12)
    # 近づく(range_rate < 0)⇔ 高く聞こえる
    assert np.all((s["range_rate"][0] < 0) == (s["f_true"][0] > fe))
    s0 = D.siren_signal(2.0, FS, source_start=(-30.0, 8.0), source_velocity=(15.0, 0.0))
    s1 = D.siren_signal(2.0, FS, source_start=(-30.0, 8.0), source_velocity=(15.0, 0.0), mic_velocity=(0.0, 0.0))
    np.testing.assert_array_equal(s0["signals"], s1["signals"])
    rd = (np.stack([-30.0 + 15.0 * s0["tau"][0], np.full_like(s0["tau"][0], 8.0)], 1) @ np.array([15.0, 0.0])) / np.hypot(
        -30.0 + 15.0 * s0["tau"][0], 8.0)
    np.testing.assert_allclose(s0["v_radial"][0], -rd, rtol=1e-12, atol=1e-12)
    with pytest.raises(ValueError, match="mic speed"):
        D.siren_signal(1.0, FS, mic_velocity=(400.0, 0.0))


def test_siren_mic_track_matches_velocity_form_and_braking_geometry():
    """mic_track(標本ごとのマイクの位置・速度): 等速の道なら mic_velocity 版と一致。減速する道でも f_true = f_e dτ/dt
    (数値微分)、range_rate = 受信時の距離の数値微分。"""
    T, n = 3.0, int(3.0 * FS)
    t = np.arange(n) / FS
    pos = np.stack([np.stack([8.0 * t, np.full(n, 0.5)], 1)])
    vel = np.broadcast_to(np.array([8.0, 0.0]), (1, n, 2))
    a = D.siren_signal(T, FS, source_start=(-40.0, -2.0), source_velocity=(17.0, 0.0), mics=((0.0, 0.5),), mic_velocity=(8.0, 0.0))
    b = D.siren_signal(T, FS, source_start=(-40.0, -2.0), source_velocity=(17.0, 0.0), mic_track=(pos, vel))
    np.testing.assert_allclose(b["signals"], a["signals"], atol=1e-12)
    np.testing.assert_allclose(b["f_true"], a["f_true"], rtol=1e-12)
    # 減速(8 → 0 m/s を 2 m/s² で)して左へ寄る道
    vx = np.maximum(0.0, 8.0 - 2.0 * t)
    x = np.where(t < 4.0, 8.0 * t - t * t, 16.0)
    y = 0.5 + 0.3 * (1 - np.cos(np.pi * np.minimum(t, 2.0) / 2.0))
    vy = np.where(t < 2.0, 0.3 * np.pi / 2.0 * np.sin(np.pi * t / 2.0), 0.0)
    pos = np.stack([np.stack([x, y], 1)])
    vel = np.stack([np.stack([vx, vy], 1)])
    c = D.siren_signal(T, FS, source_start=(-40.0, -2.0), source_velocity=(17.0, 0.0), mic_track=(pos, vel))
    np.testing.assert_allclose(c["f_true"][0], c["f_emit"][0] * np.gradient(c["tau"][0], t), rtol=5e-6)   # 加速度の折れ目で中心差分が 1e-6 を少し越える
    p = np.array([-40.0, -2.0])[None, :] + c["tau"][0][:, None] * np.array([17.0, 0.0])[None, :]
    r = np.linalg.norm(p - pos[0], axis=1)
    np.testing.assert_allclose(c["range_rate"][0][1:-1], np.gradient(r, t)[1:-1], atol=5e-5)
    with pytest.raises(ValueError, match="mic_track"):
        D.siren_signal(T, FS, mic_track=(pos[:, :10], vel[:, :10]))


def test_doppler_track_recovers_radial_speed_and_verdict():
    s = D.siren_signal(4.0, FS, source_start=(-30.0, 8.0), source_velocity=(15.0, 0.0))
    x = s["signals"][0]
    r = D.doppler_track(x, FS)
    vt = np.interp(r["t"], s["t"], s["v_radial"][0])
    ok = r["valid"]
    assert ok.mean() > 0.8
    err = np.abs(r["v_radial"][ok] - vt[ok])
    assert np.percentile(err, 99) < 0.3 and np.max(err) < 1.0, (np.percentile(err, 99), err.max())
    # 前半は近づく、後半は遠ざかる
    first = ok & (r["t"] < 1.0)
    last = ok & (r["t"] > 3.0)
    assert np.all(r["state"][first] == "approaching") and np.all(r["state"][last] == "receding")
    assert r["verdict"] == "receding"
    r2 = D.doppler_track(x[: int(1.5 * FS)], FS)
    assert r2["verdict"] == "approaching"


def test_doppler_track_misassigns_above_closed_form_speed():
    """近づく視線速度が c(1 − √(f_l/f_h)) を超えると低い音を高い音と取り違える(限界を門で固定)。"""
    vlim = 343.0 * (1 - math.sqrt(770.0 / 960.0))
    assert vlim == pytest.approx(35.8, abs=0.05)
    for v, fooled in ((vlim - 2.0, False), (vlim + 2.0, True)):
        s = D.siren_signal(1.0, FS, source_start=(-500.0, 0.5), source_velocity=(v, 0.0))
        r = D.doppler_track(s["signals"][0], FS)
        low = r["valid"] & (np.interp(r["t"], s["t"], s["f_emit"][0]) == 770.0)
        wrong = np.mean(r["f_nominal"][low] == 960.0)
        assert (wrong > 0.9) if fooled else (wrong < 0.01), (v, wrong)


@pytest.mark.parametrize("deg", [-60.0, -20.0, 0.0, 35.0, 70.0])
def test_tdoa_bearing_matches_geometry(deg):
    d = 0.15
    mics = ((0.0, d / 2), (0.0, -d / 2))                     # 左 = +y、右 = −y
    th = math.radians(deg)
    src = 80.0 * np.array([math.cos(th), math.sin(th)])
    s = D.siren_signal(1.0, 48000.0, source_start=tuple(src), source_velocity=(0.0, 0.0), mics=mics)
    r = D.tdoa_bearing(s["signals"][0], s["signals"][1], 48000.0, d)
    rl = np.linalg.norm(src - mics[0])
    rr = np.linalg.norm(src - mics[1])
    true_dt = (rr - rl) / 343.0
    assert r["delay"] == pytest.approx(true_dt, abs=2e-6)
    assert r["bearing_deg"] == pytest.approx(deg, abs=1.0)
    assert not r["ambiguous"]
    wide = D.tdoa_bearing(s["signals"][0], s["signals"][1], 48000.0, 0.5)
    assert wide["ambiguous"]


# ---- 4. 40 条の採点 -----------------------------------------------------------------------------------
def _traj(x, y, v, dt=0.1):
    n = len(x)
    return {"t": np.arange(n) * dt, "x": np.asarray(x, float), "y": np.asarray(y, float), "v": np.asarray(v, float)}


def _drive(x0, v0, stop_at, y_end, n=200, dt=0.1):
    """x0 から v0 で走り、stop_at(None なら止まらない)の手前で止まる。横は y_end へ寄る。"""
    x, v, y = [x0], [v0], [1.5]
    for k in range(1, n):
        vv = v[-1]
        if stop_at is not None:
            rem = stop_at - x[-1]
            need = vv * vv / (2 * max(rem, 1e-6))
            vv = max(0.0, vv - min(need, 4.0) * dt) if rem > 0 else 0.0
        x.append(x[-1] + vv * dt)
        v.append(vv)
        y.append(max(y_end, y[-1] - 0.1))
    return _traj(x, y, v, dt)


def test_yield_check_truth_table():
    box = [(100.0, 115.0)]
    # 40-1: 交差点の手前で左に寄って停止 → 適合
    r = D.yield_maneuver_check(_drive(80.0, 10.0, 95.0, 0.3), t_approach=0.0, t_passed=15.0, intersections=box)
    assert r["case"] == "40-1" and r["ok"], r["violations"]
    # 40-1: 交差点の中で止まる → 違反
    r = D.yield_maneuver_check(_drive(80.0, 10.0, 108.0, 0.3), t_approach=0.0, t_passed=15.0, intersections=box)
    assert {v["rule"] for v in r["violations"]} >= {"stopped_in_intersection"}
    # 40-1: 寄ったが止まらない → 違反
    r = D.yield_maneuver_check(_drive(80.0, 10.0, None, 0.3), t_approach=0.0, t_passed=5.0, intersections=box)
    assert [v["rule"] for v in r["violations"]] == ["no_stop"]
    # 40-2: 交差点から遠い。寄って走り続ける → 適合、寄らない → 違反
    r = D.yield_maneuver_check(_drive(0.0, 10.0, None, 0.3), t_approach=0.0, t_passed=5.0, intersections=box)
    assert r["case"] == "40-2" and r["ok"]
    r = D.yield_maneuver_check(_drive(0.0, 10.0, None, 1.5), t_approach=0.0, t_passed=5.0, intersections=box)
    assert [v["rule"] for v in r["violations"]] == ["not_left"]
    assert "40 条 2 項" in r["violations"][0]["article"]


# ---- 5. バス --------------------------------------------------------------------------------------
def _brake_sim_stops_within(v, rho, a, D_, dt=1e-4):
    s, vv, t = 0.0, v, 0.0
    while vv > 0:
        acc = 0.0 if t < rho else -a
        nv = max(0.0, vv + acc * dt)
        s += 0.5 * (vv + nv) * dt
        vv, t = nv, t + dt
    return s <= D_


@pytest.mark.parametrize("v,dist", [(10.0, 40.0), (14.0, 35.0), (8.0, 15.0)])
def test_bus_required_decel_matches_rss_and_simulation(v, dist):
    tr = {"t": [0.0, 1.0], "x": [0.0, v], "v": [v, v]}
    r = D.bus_departure_yield_check(tr, t_signal=0.0, bus_rear_x=dist, standoff=2.0, reaction=1.0)
    a = r["a_required"]
    assert R.rss_stopping_distance(v, 1.0, 0.0, a) == pytest.approx(dist - 2.0, rel=1e-12)
    lo, hi = 0.01, 50.0
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if _brake_sim_stops_within(v, 1.0, mid, dist - 2.0, dt=2e-4):
            hi = mid
        else:
            lo = mid
    assert hi == pytest.approx(a, rel=2e-3)


def test_bus_yield_truth_table():
    def tr(v, stop):
        t = np.arange(0, 8.0, 0.05)
        if stop:
            # 反応 1 s の後 2.5 m/s² で止まる(10 + 20 = 30 m、後端 35 m の手前)
            vv = np.where(t < 1.0, v, np.maximum(0.0, v - 2.5 * (t - 1.0)))
        else:
            vv = np.full_like(t, v)
        x = np.concatenate([[0.0], np.cumsum(0.5 * (vv[1:] + vv[:-1]) * 0.05)])
        return {"t": t, "x": x, "v": vv}
    # 10 m/s・後端 35 m: a_req = 100/(2·23) = 2.17 ≤ 3 → 譲る義務。走り抜ければ違反、止まれば適合
    r = D.bus_departure_yield_check(tr(10.0, False), t_signal=0.0, bus_rear_x=35.0)
    assert r["a_required"] == pytest.approx(100 / 46)
    assert r["must_yield"] and r["obstructed"] and r["violation"]
    r = D.bus_departure_yield_check(tr(10.0, True), t_signal=0.0, bus_rear_x=35.0)
    assert r["must_yield"] and not r["obstructed"] and not r["violation"]
    # 14 m/s・後端 25 m: a_req = 196/(2·9) = 10.9 > 3 → 義務なし(急ブレーキになる)
    r = D.bus_departure_yield_check(tr(14.0, False), t_signal=0.0, bus_rear_x=25.0)
    assert not r["must_yield"] and r["obstructed"] and not r["violation"]
    assert r["article"] == "道路交通法 31 条の 2"


# ---- fail-closed --------------------------------------------------------------------------------------
def test_fail_closed():
    with pytest.raises(ValueError, match="mirror_reflection_matrix"):
        D.mirror_reflection_matrix([0, 0, 0, 1])
    with pytest.raises(ValueError, match="mirror_virtual_camera"):
        D.mirror_virtual_camera(np.eye(3), [0, 0, 1, 0])
    with pytest.raises(ValueError, match="convex_mirror_fov"):
        D.convex_mirror_fov(0.1, 0.3, 1.0)
    with pytest.raises(ValueError, match="mirror_blind_zone"):
        D.mirror_blind_zone(EYE, MIR, [0.0, 1.0], 0.18)            # 法線が眼の側を向いていない
    with pytest.raises(ValueError, match="check_sequence_score"):
        D.check_sequence_score([{"t": 0, "kind": "mirror"}])        # start が無い
    with pytest.raises(ValueError, match="check_sequence_score"):
        D.check_sequence_score([{"t": 0, "kind": "wave"}, {"t": 1, "kind": "start"}])
    with pytest.raises(ValueError, match="signal_phase_plan"):
        _plan(flash_fraction=1.5)
    with pytest.raises(ValueError, match="dilemma_zone"):
        D.dilemma_zone(-1.0, reaction=1, decel=3, amber=3, intersection_width=10, car_length=4)
    with pytest.raises(ValueError, match="flash_frequency"):
        D.flash_frequency(np.ones(100), 30.0)
    with pytest.raises(ValueError, match="siren_signal"):
        D.siren_signal(1.0, 1000.0)                                 # 960 Hz ≥ fs/2
    with pytest.raises(ValueError, match="tdoa_bearing"):
        D.tdoa_bearing(np.zeros(100), np.zeros(99), 48000.0, 0.15)
    with pytest.raises(ValueError, match="yield_maneuver_check"):
        D.yield_maneuver_check({"t": [0, 1], "x": [0, 1], "y": [0, 0]}, t_approach=0, t_passed=1)
    with pytest.raises(ValueError, match="bus_departure_yield_check"):
        D.bus_departure_yield_check({"t": [0, 1], "x": [0, 1], "v": [-1, 1]}, t_signal=0, bus_rear_x=10)


def test_dilemma_stop_line_reading_critical_speed():
    """停止線を越えればよい読み(w = L = 0): v²/(2a) + v(δ − τ) = 0 → v_c = 2a(τ − δ)。それ以下はジレンマなし。"""
    kw = dict(reaction=1.0, decel=3.0, amber=3.0, intersection_width=0.0, car_length=0.0)
    assert D.dilemma_zone(10.0, **kw)["v_critical"] == pytest.approx((0.0, 12.0))
    assert D.dilemma_zone(11.9, **kw)["dilemma"] is None
    assert D.dilemma_zone(12.1, **kw)["dilemma"] is not None
    # x < 0(停止線の先)は区間に入れない
    dz = D.dilemma_zone(8.0, reaction=1.0, decel=3.0, amber=3.0, intersection_width=20.0, car_length=4.5)
    assert dz["dilemma"][0] == 0.0 and dz["length"] == pytest.approx(dz["x_stop_min"])
