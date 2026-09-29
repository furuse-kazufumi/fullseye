"""racket の門: ラケットの表 / 動く板の衝突(静止なら台の跳ねと同じ・ラケット系でエネルギー不増・接触点の角運動量保存)/
板の当たり判定 / 狙い(真空の閉形式・抗力+マグヌスの Gauss–Newton)/ 打ち方の計画 / 上限つきの動き / 戦略 / 先読みの合法判定 /
ラリー(本数・終わり方・巻き戻し・知覚雑音・決定性・再計画間隔)。

ラリーは 1 本 ≈ 1 s と遅いので、module スコープで 1 度だけ回して複数の門で共有し、本数は小さく取る。"""
from __future__ import annotations

import time

import numpy as np
import pytest

import ballistics as B
import ballworld as BW
import racket as RK

BP = B.ball_params()
RP = RK.racket_params()
TP = BW.table_params()
H = TP["height"]
IP = B.impact_params(0.9, 0.25)


# ─────────────────────────────── 共有のラリー(module スコープ) ───────────────────────────────

@pytest.fixture(scope="module")
def rally_ff6():
    """feeder 対 feeder、max_hits=6、retries=0、seed=1(門 9・12・13 で共有)。"""
    return RK.rally_simulate(BP, RP, TP, max_hits=6, retries=0, seed=1)


@pytest.fixture(scope="module")
def rally_ff3_replan5():
    """feeder 対 feeder、max_hits=3、retries=0、seed=1、replan_every=5(門 13・14 で共有)。"""
    return RK.rally_simulate(BP, RP, TP, max_hits=3, retries=0, seed=1, replan_every=5)


# ─────────────────────────────── 1. 表 ───────────────────────────────

def test_racket_params_defaults_and_validation():
    """既定値(幅 0.15・高さ 0.16・e 0.8・μ 0.6・v_max 6・a_max 60)と、幅 ≤ 0・e ∉ [0,1]・μ < 0 の拒否。"""
    rp = RK.racket_params()
    assert rp == {"width": 0.15, "height": 0.16, "e": 0.8, "mu": 0.6, "v_max": 6.0, "a_max": 60.0}
    assert all(isinstance(v, float) for v in rp.values())
    assert RK.racket_params(e=0.0)["e"] == 0.0 and RK.racket_params(e=1.0)["e"] == 1.0 and RK.racket_params(mu=0.0)["mu"] == 0.0
    with pytest.raises(ValueError):
        RK.racket_params(width=0.0)
    with pytest.raises(ValueError):
        RK.racket_params(height=-0.1)
    with pytest.raises(ValueError):
        RK.racket_params(e=1.2)
    with pytest.raises(ValueError):
        RK.racket_params(e=-0.1)
    with pytest.raises(ValueError):
        RK.racket_params(mu=-0.01)
    with pytest.raises(ValueError):
        RK.racket_params(v_max=0.0)
    with pytest.raises(ValueError):
        RK.racket_params(a_max=-1.0)


# ─────────────────────────────── 2. 動く板の衝突 ───────────────────────────────

def test_racket_impact_theorems():
    """静止ラケット = ballistics.bounce と完全一致 / 動くラケットはラケット系で bounce(v − v_r) と一致 /
    ラケット系の運動エネルギー(並進 + 回転)は 200 例で増えない / 接触点まわりの角運動量は 1e-12 で保存。"""
    v, w, n = [-5.0, 0.2, -1.0], [0.0, 200.0, 0.0], [1.0, 0.0, 0.0]
    b0 = RK.racket_impact(v, w, n, [0.0, 0.0, 0.0], BP, RP)
    b1 = B.bounce(v, w, n, BP, B.impact_params(RP["e"], RP["mu"]))
    assert np.array_equal(b0["v"], b1["v"]) and np.array_equal(b0["omega"], b1["omega"])
    assert b0["regime"] == b1["regime"] and b0["J_n"] == b1["J_n"]
    assert np.array_equal(b0["v_rel_in"], np.asarray(v, float))
    # 動くラケット: 相対速度で跳ねて戻す
    vr = np.array([2.0, -0.5, 0.3])
    bm = RK.racket_impact(v, w, n, vr, BP, RP)
    br = B.bounce(np.asarray(v) - vr, w, n, BP, B.impact_params(RP["e"], RP["mu"]))
    assert np.allclose(bm["v"] - vr, br["v"], atol=1e-14) and np.array_equal(bm["omega"], br["omega"])
    assert np.allclose(bm["v_rel_in"], np.asarray(v) - vr)
    # 定理: エネルギー不増・角運動量保存(向き・速度・回転を乱数で 200 例)
    rng = np.random.default_rng(0)
    for _ in range(200):
        nn = rng.normal(size=3)
        nn /= np.linalg.norm(nn)
        vr = rng.normal(size=3) * 3.0
        vv = vr - rng.uniform(1.0, 8.0) * nn + rng.normal(size=3) * 0.5      # 板に向かって近づく
        ww = rng.normal(size=3) * 100.0
        b = RK.racket_impact(vv, ww, nn, vr, BP, RP)
        rel_in, rel_out = vv - vr, b["v"] - vr
        e_in = 0.5 * BP["mass"] * rel_in @ rel_in + 0.5 * BP["inertia"] * ww @ ww
        e_out = 0.5 * BP["mass"] * rel_out @ rel_out + 0.5 * BP["inertia"] * b["omega"] @ b["omega"]
        assert e_out <= e_in + 1e-12
        L0 = B.contact_angular_momentum(rel_in, ww, nn, BP)
        L1 = B.contact_angular_momentum(rel_out, b["omega"], nn, BP)
        assert np.abs(L1 - L0).max() < 1e-12
    with pytest.raises(ValueError):
        RK.racket_impact([1.0, 2.0], w, n, [0, 0, 0], BP, RP)


# ─────────────────────────────── 3. 当たり判定 ───────────────────────────────

def test_racket_hit_check_geometry():
    """板の枠(幅 × 高さ + 半径)の内外、面からの距離の符号(法線側が正)、u = 幅方向・v = 高さ方向。
    法線がゼロのときは **ValueError にならず** NaN の dist と hit=False を返す(観測した挙動を記録: 本来は拒否すべき)。"""
    c = np.array([1.55, 0.0, 1.0])
    n = [-1.0, 0.0, 0.0]                                   # 板は −x(相手)を向く; up = z → v = Δz、u = (z × n) = −y 方向
    r = BP["radius"]
    inside = RK.racket_hit_check(c + [-0.01, 0.03, -0.04], c, n, RP, r)
    assert inside["hit"] and inside["dist"] == pytest.approx(0.01) and inside["v"] == pytest.approx(-0.04)
    assert abs(inside["u"]) == pytest.approx(0.03)
    behind = RK.racket_hit_check(c + [0.01, 0.0, 0.0], c, n, RP, r)
    assert behind["hit"] and behind["dist"] == pytest.approx(-0.01)              # 面の裏側 = 負の距離
    far = RK.racket_hit_check(c + [-0.05, 0.0, 0.0], c, n, RP, r)
    assert not far["hit"] and far["dist"] == pytest.approx(0.05)
    # 幅の縁: 半径ぶんの余裕まで当たり、それを越えると外
    edge_in = RK.racket_hit_check(c + [0.0, RP["width"] / 2 + r - 1e-6, 0.0], c, n, RP, r)
    edge_out = RK.racket_hit_check(c + [0.0, RP["width"] / 2 + r + 1e-6, 0.0], c, n, RP, r)
    assert edge_in["hit"] and not edge_out["hit"]
    top_in = RK.racket_hit_check(c + [0.0, 0.0, RP["height"] / 2 + r - 1e-6], c, n, RP, r)
    top_out = RK.racket_hit_check(c + [0.0, 0.0, RP["height"] / 2 + r + 1e-6], c, n, RP, r)
    assert top_in["hit"] and not top_out["hit"]
    # 法線が up と平行なら up の代わりに z が使われ、NaN にならない
    flat = RK.racket_hit_check(c + [0.02, 0.01, 0.01], c, [0.0, 0.0, 1.0], RP, r)
    assert flat["hit"] and np.isfinite([flat["dist"], flat["u"], flat["v"]]).all()
    # ゼロ法線は fail-closed(ValueError)
    with pytest.raises(ValueError):
        RK.racket_hit_check(c, c, [0.0, 0.0, 0.0], RP, r)
    with pytest.raises(ValueError):
        RK.racket_impact([1.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], BP, RP)
    with pytest.raises(ValueError):
        RK.racket_hit_check([0.0, 0.0], c, n, RP, r)


# ─────────────────────────────── 4. 狙い ───────────────────────────────

def test_aim_velocity_vacuum_and_air():
    """真空(rho = 0)は閉形式で目標に厳密到達(residual 0、放物線で検算)/ 抗力 + マグヌスは refine で 1e-6 m 以内
    (残差の欄 = 実際に飛ばした到達点のずれ)/ T ≤ 0 は拒否。"""
    p, q, T = np.array([-1.5, 0.0, 1.0]), np.array([0.8, 0.1, 0.78]), 0.4
    bp_vac = B.ball_params(rho=0.0)
    a0 = RK.aim_velocity(p, q, T, bp_vac)
    assert a0["residual"] == 0.0
    assert np.allclose(B.flight_vacuum(p, a0["v"], T, bp_vac["g"]), q, atol=1e-12)
    assert np.allclose(a0["v"], [(q[0] - p[0]) / T, (q[1] - p[1]) / T, (q[2] - p[2] + 0.5 * bp_vac["g"] * T * T) / T])
    w = [0.0, 100.0, 0.0]
    a1 = RK.aim_velocity(p, q, T, BP, w)
    assert a1["residual"] < 1e-6
    f = B.flight_ode(p, a1["v"], w, BP, T + 1e-3, 1e-3)
    landed = np.array([np.interp(T, f["t"], f["p"][:, k]) for k in range(3)])
    assert np.linalg.norm(landed - q) < 1e-6
    assert np.linalg.norm(landed - q) == pytest.approx(a1["residual"], abs=1e-12)
    # 空気ありなら真空の閉形式からは動いている(抗力ぶん速く打つ)
    assert not np.allclose(a1["v"], a0["v"], atol=1e-3)
    with pytest.raises(ValueError):
        RK.aim_velocity(p, q, 0.0, BP)
    with pytest.raises(ValueError):
        RK.aim_velocity(p, q, -0.1, BP)


# ─────────────────────────────── 5. 打ち方の計画 ───────────────────────────────

def test_racket_plan_closed_form_and_friction():
    """μ = 0・ω = 0 なら閉形式が厳密(残差 < 1e-12、v_out_actual == v_out)/ 摩擦 + スピンでも反復で残差 < 1e-3
    (実測 ≈ 1e-5)/ v_out == v_in は ValueError。返り値の法線は単位ベクトル、v_racket は法線方向。"""
    v_in = [-5.0, 0.2, -1.0]
    v_out = RK.aim_velocity([-1.5, 0.0, 1.0], [0.8, 0.1, 0.78], 0.4, BP, [0.0, 100.0, 0.0])["v"]
    rp0 = RK.racket_params(mu=0.0)
    pl0 = RK.racket_plan(v_in, [0.0, 0.0, 0.0], v_out, BP, rp0)
    assert pl0["residual"] < 1e-12
    assert np.allclose(pl0["v_out_actual"], v_out, atol=1e-12)
    assert np.linalg.norm(pl0["normal"]) == pytest.approx(1.0)
    assert np.allclose(np.cross(pl0["v_racket"], pl0["normal"]), 0.0, atol=1e-12)       # v_r ∥ n
    dv = v_out - np.asarray(v_in)
    assert np.allclose(pl0["normal"], dv / np.linalg.norm(dv))                            # n ∝ v_out − v_in
    # 閉形式の速さ v_r·n = |Δv|/(1+e) + v_in·n
    assert pl0["v_racket"] @ pl0["normal"] == pytest.approx(np.linalg.norm(dv) / (1 + rp0["e"]) + np.asarray(v_in) @ pl0["normal"])
    pl = RK.racket_plan(v_in, [0.0, 200.0, 0.0], v_out, BP, RP)
    assert pl["residual"] < 1e-3
    assert np.linalg.norm(pl["v_out_actual"] - v_out) == pytest.approx(pl["residual"])
    assert pl["omega_out"].shape == (3,)
    with pytest.raises(ValueError):
        RK.racket_plan(v_in, [0.0, 0.0, 0.0], v_in, BP, RP)


# ─────────────────────────────── 6. 動き ───────────────────────────────

def test_racket_move_limits_and_arrival():
    """目標へ近づき、|v| ≤ v_max、1 歩の速度変化 ≤ a_max·dt(**最後の 1 歩を除く**)、行き過ぎない(目標方向の残りが負に
    ならない)、目標に達したら (target, 0) を返す。

    観測(記録): 減速の目安 v_stop = √(2 a d) を離散時間で追うと必要な減速が a·dt を毎歩わずかに超える(√ の曲率)ので、
    ラケットは 0 でない速さで目標を跨ぎ、最後の 1 歩は「目標に置いて速度 0」で吸収される —— その歩だけ |Δv| が a_max·dt を
    超える(dt = 5 ms で ≈ 5 倍、ラリーの dt = 0.2 ms で ≈ 23 倍)。位置の跳びは v·dt 以下で小さいが、速度の連続性は破れる。"""
    rp = RK.racket_params(v_max=1.0, a_max=60.0)
    tgt = np.array([0.5, 0.3, -0.2])
    u0 = tgt / np.linalg.norm(tgt)
    pos, vel, dt = np.zeros(3), np.zeros(3), 5e-3
    dist_prev = np.linalg.norm(tgt)
    reached = None
    dv_hist = []
    for i in range(200):
        pos2, vel2 = RK.racket_move(pos, vel, tgt, dt, rp)
        assert np.linalg.norm(vel2) <= rp["v_max"] + 1e-9
        dv_hist.append(float(np.linalg.norm(vel2 - vel)))
        assert float((tgt - pos2) @ u0) >= -1e-12                                           # 行き過ぎない
        dist = np.linalg.norm(tgt - pos2)
        assert dist <= dist_prev + 1e-12                                                    # 近づく
        pos, vel, dist_prev = pos2, vel2, dist
        if dist < 1e-3:
            reached = i
            break
    assert reached is not None and reached > 10                                             # 上限のせいで即着はしない
    assert all(dv <= rp["a_max"] * dt + 1e-9 for dv in dv_hist)                            # 全部の歩が加速度上限内(離散の 1 歩ぶんの余裕)
    print("racket_move reached in %d steps, max |dv| = %.4f (a_max*dt = %.3f)" % (reached, max(dv_hist), rp["a_max"] * dt))
    # 目標の上にいれば (target, 0)
    at, v_at = RK.racket_move(tgt, [1.0, 0.0, 0.0], tgt, dt, rp)
    assert np.array_equal(at, tgt) and np.array_equal(v_at, np.zeros(3))
    # v_max に張り付く(遠い目標を速さ上限で追う)
    pos, vel = np.zeros(3), np.zeros(3)
    for _ in range(100):
        pos, vel = RK.racket_move(pos, vel, [10.0, 0.0, 0.0], dt, rp)
    assert np.linalg.norm(vel) == pytest.approx(rp["v_max"])


# ─────────────────────────────── 7. 戦略 ───────────────────────────────

def test_strategies():
    """attacker: 相手側(符号)の隅、|y| = W/2 − 0.10 で相手と逆側、shot_index で深い/浅いを交互、T も交互。
    feeder: 前回の狙いから ±step、コートの内側(端から 12 cm)、自分から見て相手側。"""
    rng = np.random.default_rng(1)
    W, L = TP["width"], TP["length"]
    for side, sign in ((0, 1.0), (1, -1.0)):
        for k in range(4):
            ctx = {"opp_pos": np.array([-sign * 1.55, 0.3, 1.0]), "shot_index": k, "tp": TP}
            c = RK.strategy_attacker(side, ctx, rng)
            x, y = c["target"]
            assert np.sign(x) == sign
            assert y == pytest.approx(-(W / 2 - 0.10))                                   # 相手 y = +0.3 の逆側
            assert abs(x) == pytest.approx((L / 2 - 0.12) if k % 2 == 0 else 0.30)
            assert c["T"] == (0.30 if k % 2 == 0 else 0.26)
            assert c["spin"] in ("topspin", "flat")
        # 相手が中央なら乱数で左右どちらかの端
        c = RK.strategy_attacker(side, {"opp_pos": np.array([-sign * 1.55, 0.0, 1.0]), "shot_index": 0, "tp": TP}, rng)
        assert abs(c["target"][1]) == pytest.approx(W / 2 - 0.10)
        # feeder
        first = RK.strategy_feeder(side, {"tp": TP, "prev_target": None}, rng)
        assert abs(first["target"][0] - sign * 0.75) <= 0.06 + 1e-12 and abs(first["target"][1]) <= 0.06 + 1e-12
        assert first["T"] == 0.42 and first["spin"] == "flat"
        for _ in range(50):
            prev = (sign * rng.uniform(0.25, L / 2 - 0.12), rng.uniform(-W / 2 + 0.12, W / 2 - 0.12))
            f = RK.strategy_feeder(side, {"tp": TP, "prev_target": prev}, rng, step=0.06)
            x, y = f["target"]
            assert abs(x - prev[0]) <= 0.06 + 1e-12 and abs(y - prev[1]) <= 0.06 + 1e-12
            assert 0.25 - 1e-12 <= sign * x <= L / 2 - 0.12 + 1e-12 and abs(y) <= W / 2 - 0.12 + 1e-12
        # 端に張り付いた前回でもコートの内側に収める
        f = RK.strategy_feeder(side, {"tp": TP, "prev_target": (sign * 5.0, 5.0)}, rng)
        assert sign * f["target"][0] <= L / 2 - 0.12 + 1e-12 and f["target"][1] <= W / 2 - 0.12 + 1e-12


# ─────────────────────────────── 8. 先読みの合法判定 ───────────────────────────────

def test_shot_is_legal_reasons():
    """良いロブ(0 側から相手コートへ T = 0.42)は legal、到達点は相手の面 x ≈ +x_r で打てる高さ / ネットに突っ込む球は "net" /
    後ろ・上に打つ球は "no_net_cross"。"""
    p0 = np.array([-1.55, 0.0, H + 0.25])
    aim = RK.aim_velocity(p0, [0.75, 0.0, H + BP["radius"]], 0.42, BP)
    ok = RK.shot_is_legal(p0, aim["v"], [0.0, 0.0, 0.0], BP, IP, TP, 1.55, 0)
    assert ok["legal"] and ok["reason"] == "ok"
    assert ok["p_arrive"][0] == pytest.approx(1.55, abs=0.02)
    assert H + 0.05 <= ok["p_arrive"][2] <= H + 0.45
    assert 0.42 < ok["t_arrive"] < 1.0
    net = RK.shot_is_legal(p0, [3.0, 0.0, -0.5], [0.0, 0.0, 0.0], BP, IP, TP, 1.55, 0)
    assert not net["legal"] and net["reason"] == "net" and net["p_arrive"] is None
    back = RK.shot_is_legal(p0, [-1.0, 0.0, 0.5], [0.0, 0.0, 0.0], BP, IP, TP, 1.55, 0)
    assert not back["legal"] and back["reason"] == "no_net_cross"
    # 1 側から打つ場合は相手の面が −x_r
    p1 = np.array([1.55, 0.0, H + 0.25])
    aim1 = RK.aim_velocity(p1, [-0.75, 0.0, H + BP["radius"]], 0.42, BP)
    ok1 = RK.shot_is_legal(p1, aim1["v"], [0.0, 0.0, 0.0], BP, IP, TP, 1.55, 1)
    assert ok1["legal"] and ok1["p_arrive"][0] == pytest.approx(-1.55, abs=0.02)


# ─────────────────────────────── 9〜14. ラリー ───────────────────────────────

def test_rally_feeder_vs_feeder_structure(rally_ff6):
    """feeder 対 feeder(max_hits 6、retries 0): 6 本で "max_hits"、側は 0,1,0,1,…、打球時刻は増加、
    racket_pos は (N, 2, 3)、巻き戻し 0、各 shot の残差は小さい、返り値の配列は同じ長さ。"""
    r = rally_ff6
    assert r["hits"] == 6 and r["end_reason"] == "max_hits" and r["rewinds"] == 0
    assert [s["side"] for s in r["shots"]] == [0, 1, 0, 1, 0, 1]
    assert len(r["hit_times"]) == 6 and np.all(np.diff(r["hit_times"]) > 0.3)
    N = len(r["t"])
    assert r["p"].shape == (N, 3) and r["racket_pos"].shape == (N, 2, 3) and N > 1000
    assert np.all(np.diff(r["t"]) > 0)
    assert len(r["shots"]) == 6                              # 空なら下の 2 行は無条件に通る
    assert all(s["residual"] < 1e-3 for s in r["shots"])
    assert all(s["rewinds"] == 0 for s in r["shots"])
    # ラケットは自分の面 x = ±x_r 付近から離れない
    assert np.all(np.abs(r["racket_pos"][:, 0, 0] + 1.55) < 0.5) and np.all(np.abs(r["racket_pos"][:, 1, 0] - 1.55) < 0.5)
    # 狙いは相手コート(側 0 は +x、側 1 は −x)
    for s in r["shots"]:
        assert (s["target"][0] > 0) == (s["side"] == 0)


def test_rally_with_retries_records_rewinds():
    """retries=3(feeder 対 feeder、max_hits 4): 各 shot に "rewinds" ≥ 0 と "choice"(target/T/spin)が残り、
    合計の rewinds は shot ごとの和に等しい。"""
    r = RK.rally_simulate(BP, RP, TP, max_hits=4, retries=3, seed=1)
    assert r["hits"] == 4 and r["end_reason"] == "max_hits"
    assert len(r["shots"]) == 4                              # 空なら下の表明は無条件に通る
    for s in r["shots"]:
        assert isinstance(s["rewinds"], int) and s["rewinds"] >= 0
        assert {"target", "T", "spin"} <= set(s["choice"].keys())
        assert s["choice"]["T"] == 0.42 and s["choice"]["spin"] == "flat"
        assert np.allclose(s["target"][:2], s["choice"]["target"]) and s["target"][2] == pytest.approx(H + BP["radius"])
    assert r["rewinds"] == sum(s["rewinds"] for s in r["shots"])


def test_rally_attacker_vs_feeder_ends_early():
    """attacker 対 feeder(max_hits 12、retries 0): 攻める球は上限より前に終わる(実測 9 本・"out")。"""
    r = RK.rally_simulate(BP, RP, TP, strategies=(RK.strategy_attacker, RK.strategy_feeder), max_hits=12, retries=0, seed=1)
    print("attacker vs feeder: hits %d end %s" % (r["hits"], r["end_reason"]))
    assert 3 <= r["hits"] < 12
    assert r["end_reason"] in {"out", "net", "double_bounce", "unreachable", "wrong_side_bounce", "volley"}
    assert r["hits"] == 9 and r["end_reason"] == "out"                                   # 実測(決定的)
    attacker_shots = [s for s in r["shots"] if s["side"] == 0]
    assert len(attacker_shots) == 5                          # 9 本のうち攻める側は 0, 2, 4, 6, 8 本目
    assert all(abs(s["choice"]["target"][1]) == pytest.approx(TP["width"] / 2 - 0.10) for s in attacker_shots[1:])


def test_rally_noisy_perception_is_not_longer(rally_ff6):
    """知覚に 5 cm のガウス雑音(位置のみ)を足すと、真値の知覚より本数が伸びない(max_hits 6: 真値 6 本、実測 雑音 5 本 "out")。"""
    noise = np.random.default_rng(5)
    r = RK.rally_simulate(BP, RP, TP, max_hits=6, retries=0, seed=1,
                          perceive=lambda t, p, v, w: (p + noise.normal(0.0, 0.05, 3), v, w))
    print("noisy: hits %d end %s / truth: hits %d end %s" % (r["hits"], r["end_reason"], rally_ff6["hits"], rally_ff6["end_reason"]))
    assert isinstance(r, dict) and {"hits", "end_reason", "shots", "t", "p", "racket_pos", "hit_times", "rewinds"} <= set(r)
    assert r["hits"] <= rally_ff6["hits"]
    assert r["hits"] == len(r["shots"]) == len(r["hit_times"])


def test_rally_determinism(rally_ff6, rally_ff3_replan5):
    """同じ seed なら同じ結果: max_hits 3 の走りは max_hits 6 の走りの前半 3 本(狙い・時刻・打球速度)と一致し、
    3 本で "max_hits" になる。"""
    a, b = rally_ff3_replan5, rally_ff6
    assert a["hits"] == 3 and a["end_reason"] == "max_hits"
    for sa, sb in zip(a["shots"], b["shots"][:3]):
        assert np.array_equal(sa["target"], sb["target"]) and sa["t"] == sb["t"]
        assert np.array_equal(sa["v_out"], sb["v_out"]) and np.array_equal(sa["omega_out"], sb["omega_out"])
    assert np.array_equal(a["hit_times"], b["hit_times"][:3])
    n = len(a["t"])
    assert np.array_equal(a["p"], b["p"][:n]) and np.array_equal(a["racket_pos"], b["racket_pos"][:n])


def test_rally_replan_every(rally_ff3_replan5):
    """replan_every = 1 と 5 の両方が走り(max_hits 3)、本数が同じ。サーブと 1 本目の返球時刻は一致し(サーブの計画は
    間隔によらない)、2 本目以降は計画したコマが違うので狙いが変わり打球時刻がずれる(実測 1.370 vs 1.267 s)。"""
    r1 = RK.rally_simulate(BP, RP, TP, max_hits=3, retries=0, seed=1, replan_every=1)
    r5 = rally_ff3_replan5
    print("replan_every 1: hits %d %s %s / 5: hits %d %s %s" % (r1["hits"], r1["end_reason"], r1["hit_times"],
                                                              r5["hits"], r5["end_reason"], r5["hit_times"]))
    assert r1["hits"] >= 2 and r5["hits"] >= 2
    assert r1["hits"] == r5["hits"] == 3
    assert r1["end_reason"] == r5["end_reason"] == "max_hits"
    assert np.allclose(r1["hit_times"][:2], r5["hit_times"][:2])
    assert abs(r1["hit_times"][2] - r5["hit_times"][2]) < 0.3
