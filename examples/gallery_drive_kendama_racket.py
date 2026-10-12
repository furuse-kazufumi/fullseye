# -*- coding: utf-8 -*-
"""事例: けん玉の捕球の計画と、卓球ラケットの当たり・動き・打ち方(運転の台帳 op ギャラリー: kendama / racket)

平たく言うと:
  けん玉ロボと卓球ラリーの PoC が使う「玉を受ける・打ち返す」部品を、答えが外から分かる入力で
  1 本ずつ呼ぶ。各行に「何を期待し、何が出て、合ったか」を印字し、外れたら exit 1。

確かめ方(op ごとの真値):
  * parabola_fit_g        —— 真空の放物線の正確な標本から (p, v) を戻す / 雑音 1 mm では誤差が雑音の桁に収まる
  * noisy_perceiver       —— 2 万回知覚させた雑音の標本標準偏差が指定の σ(±3 %)、平均が真値
  * catch_plan_ballistic  —— 頂点 z + v_z²/(2g)・到達の遅い根・目標の xy = p + v τ の手計算、
                             さらに計画どおりの時刻まで真空の放物線で玉を進めると kendama_catch_check が「捕れた」
  * kendama_catch_check   —— 縁に乗る高さ h_c = √(r_b² − r_c²)、横ずれ r_c の境目、昇る玉は受けない
  * racket_hit_check      —— 板の面からの距離と枠(幅/2 + 半径)の境目の手計算
  * racket_move           —— 静止から bang-bang で d を動く時間 d/v_max + v_max/a_max(閉形式)、速さの上限
  * shot_is_legal         —— ロブは合法・ネットへ突っ込む球は "net"・後ろへの球は "no_net_cross"、
                             合法のロブはネットの上を通ることを独立の RK4(flight_ode)で確かめる
  * strategy_attacker     —— 「相手から遠い隅」: 狙いの y が相手の y と逆側、相手コートの中、そして
                             前後は交互(深い = 相手のエンドラインから 12 cm、浅い = ネット寄り)、滞空はフィーダーの 0.42 s より短い。
                             (浅い球は遠い位置から打つとネットに掛かることがある —— ラリーは shot_is_legal で先読みして巻き戻す前提)
  * strategy_feeder       —— 前回の狙いから ±step 以内、コートの端から 12 cm の内側、滞空 0.42 s

    py -3.11 examples/gallery_drive_kendama_racket.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402

import ballistics as B  # noqa: E402
import ballworld as BW  # noqa: E402
import kendama as K  # noqa: E402
import racket as RK  # noqa: E402

ROWS: list = []
G = B.G


def check(op: str, what: str, expected: str, got: str, ok: bool) -> None:
    """表の 1 行を貯める(何を期待し、何が出て、合ったか)。"""
    ROWS.append((op, what, expected, got, bool(ok)))


def demo_parabola_and_perceiver() -> None:
    p0, v0 = np.array([0.1, -0.2, 1.1]), np.array([0.3, -0.1, 2.0])
    t = np.linspace(0.0, 0.10, 11)
    P = p0 + np.outer(t, v0) - np.outer(0.5 * G * t * t, [0.0, 0.0, 1.0])
    f0 = K.parabola_fit_g(t, P, t_ref=0.0)
    check("parabola_fit_g", "真空の正確な標本 11 点(t_ref = 0)", "p = (0.1, −0.2, 1.1)、v = (0.3, −0.1, 2.0)",
          f"|Δp| = {np.abs(f0['p'] - p0).max():.1e}, |Δv| = {np.abs(f0['v'] - v0).max():.1e}",
          np.allclose(f0["p"], p0, atol=1e-9) and np.allclose(f0["v"], v0, atol=1e-9))
    rng = np.random.default_rng(3)
    Pn = P + rng.normal(0.0, 1e-3, P.shape)
    fn = K.parabola_fit_g(t, Pn)
    v_end = v0 - G * t[-1] * np.array([0, 0, 1.0])
    # rms は 3 軸の残差ベクトルの大きさ: 期待値 ≈ σ √(3 (N − 2)/N)(各軸 2 未知を当てた自由度)
    rms_cf = 1e-3 * np.sqrt(3 * (len(t) - 2) / len(t))
    rms_lo, rms_hi = 0.6 * rms_cf, 1.4 * rms_cf
    check("parabola_fit_g", "雑音 σ = 1 mm(最後の時刻の状態)", f"rms ≈ σ√(3(N−2)/N) = {rms_cf * 1e3:.2f} mm ± 40 %、|Δp| < 3 mm",
          f"rms = {fn['rms'] * 1e3:.2f} mm, |Δp| = {np.abs(fn['p'] - P[-1]).max() * 1e3:.2f} mm, |Δv| = {np.abs(fn['v'] - v_end).max():.3f} m/s",
          rms_lo < fn["rms"] < rms_hi and np.abs(fn["p"] - P[-1]).max() < 3e-3)
    perceive = K.noisy_perceiver(np.random.default_rng(11), noise_pos=0.002, noise_vel=0.05)
    p_true, v_true = np.array([0.0, 0.1, 0.5]), np.array([1.0, 0.0, -2.0])
    samp = [perceive(0.0, p_true, v_true) for _ in range(20000)]
    ph = np.array([s[0] for s in samp])
    vh = np.array([s[1] for s in samp])
    sp, sv = ph.std(axis=0), vh.std(axis=0)
    check("noisy_perceiver", "位置の雑音 σ = 2 mm(2 万回、3 軸)", "標本 σ = 2 mm ± 3 %", np.array2string(sp * 1e3, precision=3),
          bool(np.all(np.abs(sp / 0.002 - 1) < 0.03)))
    check("noisy_perceiver", "速度の雑音 σ = 0.05 m/s・平均は真値", "σ ± 3 %、|平均 − 真値| < 4 σ/√n",
          f"σ = {np.array2string(sv, precision=4)}, 平均の偏り {np.abs(vh.mean(0) - v_true).max():.1e}",
          bool(np.all(np.abs(sv / 0.05 - 1) < 0.03)) and np.abs(vh.mean(0) - v_true).max() < 4 * 0.05 / np.sqrt(20000))
    try:
        K.noisy_perceiver(np.random.default_rng(0), noise_pos=-1.0)
        neg = False
    except ValueError:
        neg = True
    check("noisy_perceiver", "負の σ", "ValueError", "ValueError" if neg else "通った", neg)


def demo_kendama() -> None:
    kp = K.kendama_params()
    r_b, r_c = kp["ball_radius"], kp["cup_radius"]
    h_c = np.sqrt(r_b ** 2 - r_c ** 2)                       # 縁に乗った玉の中心の高さ(手計算)
    c = np.array([0.1, 0.2, 0.3])
    cases = [("縁に乗って静止", [0, 0, h_c], [0, 0, 0], True),
             (f"横ずれ {1e3 * (r_c - 5e-4):.1f} mm(< r_c)", [r_c - 5e-4, 0, h_c], [0, 0, -0.1], True),
             (f"横ずれ {1e3 * (r_c + 5e-4):.1f} mm(> r_c)", [r_c + 5e-4, 0, h_c], [0, 0, -0.1], False),
             ("縁より 1 mm 下", [0, 0, h_c - 1e-3], [0, 0, -0.1], False),
             ("昇ってくる玉 +0.1 m/s", [0, 0, h_c], [0, 0, 0.1], False)]
    for name, d, v, want in cases:
        res = K.kendama_catch_check(kp, c + d, v, c)
        check("kendama_catch_check", name, "捕れる" if want else "捕れない",
              f"{'捕れる' if res['caught'] else '捕れない'} (高さ {res['height'] * 1e3:.2f} mm)", res["caught"] == want)
    check("kendama_catch_check", "縁に乗る高さ h_c = √(r_b² − r_c²)", f"{h_c * 1e3:.4f} mm(手計算)",
          f"{kp['cup_rest_height'] * 1e3:.4f} mm", abs(kp["cup_rest_height"] - h_c) < 1e-15)

    plan = K.catch_plan_ballistic(kp)
    p, v = np.array([0.01, -0.02, 0.28]), np.array([0.1, 0.05, 1.0])
    cup = {"p": np.array([0.0, 0.0, 0.25]), "v": np.zeros(3), "axis": np.array([0.0, 0.0, 1.0])}
    t_now = 0.3
    res = plan(t_now, p, v, cup)
    apex = p[2] + v[2] ** 2 / (2 * G)
    check("catch_plan_ballistic", "頂点 z + v_z²/(2g)", f"{apex:.9f} m", f"{res['apex']:.9f} m", abs(res["apex"] - apex) < 1e-12)
    tau = res["t_hit"] - t_now
    h_top = h_c + 1.5 * r_b
    z_tau = p[2] + v[2] * tau - 0.5 * G * tau ** 2
    check("catch_plan_ballistic", "到達時刻 τ は下降側の根(τ > v_z/g)で z(τ) = 面 + h_c + 1.5 r_b",
          f"{res['z_plane'] + h_top:.9f} m", f"{z_tau:.9f} m (τ = {tau:.4f} s)",
          tau > v[2] / G and abs(z_tau - (res["z_plane"] + h_top)) < 1e-12)
    check("catch_plan_ballistic", "目標の xy = p + v τ", np.array2string(p[:2] + v[:2] * tau, precision=6),
          np.array2string(res["target"][:2], precision=6), np.allclose(res["target"][:2], p[:2] + v[:2] * tau, atol=1e-12))
    # 独立の検算: 計画の時刻のすこし後まで真空の放物線で玉を進め、皿を計画の目標に置くと捕れる
    t_chk = tau + 0.002
    p_hit = B.flight_vacuum(p, v, t_chk)
    v_hit = v - np.array([0, 0, G * t_chk])
    chk = K.kendama_catch_check(kp, p_hit, v_hit, res["target"])
    check("catch_plan_ballistic", "計画の目標に皿を置き、玉を τ + 2 ms まで放物線で進める", "kendama_catch_check が捕れる",
          f"caught={chk['caught']} (横 {chk['lateral'] * 1e3:.3f} mm, 相対 {chk['speed']:.3f} m/s)", chk["caught"] and res["feasible"])


def demo_racket() -> None:
    rp, bp = RK.racket_params(), B.ball_params()
    r = bp["radius"]
    c, n = np.array([1.55, 0.0, 1.0]), [-1.0, 0.0, 0.0]
    cases = [("面の前 1 cm・枠の中", [-0.01, 0.03, -0.04], True, 0.01),
             ("面の前 5 cm(半径 2 cm より遠い)", [-0.05, 0.0, 0.0], False, 0.05),
             ("幅の縁 + 半径 − 1 µm", [0.0, rp["width"] / 2 + r - 1e-6, 0.0], True, 0.0),
             ("幅の縁 + 半径 + 1 µm", [0.0, rp["width"] / 2 + r + 1e-6, 0.0], False, 0.0),
             ("高さの縁 + 半径 + 1 µm", [0.0, 0.0, rp["height"] / 2 + r + 1e-6], False, 0.0)]
    for name, d, want, dist in cases:
        res = RK.racket_hit_check(c + d, c, n, rp, r)
        check("racket_hit_check", name, f"{'当たる' if want else '当たらない'}、面からの距離 {dist:.3f} m",
              f"{'当たる' if res['hit'] else '当たらない'}、{res['dist']:.3f} m", res["hit"] == want and abs(res["dist"] - dist) < 1e-12)

    rpm = RK.racket_params(v_max=1.0, a_max=60.0)
    tgt = np.array([0.5, 0.0, 0.0])
    pos, vel, dt = np.zeros(3), np.zeros(3), 1e-3
    vmax_seen, t_arr = 0.0, None
    for i in range(2000):
        pos, vel = RK.racket_move(pos, vel, tgt, dt, rpm)
        vmax_seen = max(vmax_seen, float(np.linalg.norm(vel)))
        if np.linalg.norm(tgt - pos) < 1e-4:
            t_arr = (i + 1) * dt
            break
    t_cf = 0.5 / rpm["v_max"] + rpm["v_max"] / rpm["a_max"]
    check("racket_move", "静止から 0.5 m(v_max 1 m/s、a_max 60 m/s²)の到着時刻", f"d/v + v/a = {t_cf:.4f} s(±5 歩)",
          f"{t_arr} s" if t_arr is None else f"{t_arr:.4f} s", t_arr is not None and abs(t_arr - t_cf) <= 5 * dt)
    check("racket_move", "速さの上限", "|v| ≤ 1.0 m/s", f"最大 {vmax_seen:.6f} m/s", vmax_seen <= 1.0 + 1e-12)


def demo_shots() -> None:
    bp, tp = B.ball_params(), BW.table_params()
    ip = B.impact_params(0.9, 0.25)
    H = tp["height"]
    p0 = np.array([-1.55, 0.0, H + 0.25])
    aim = RK.aim_velocity(p0, [0.75, 0.0, H + bp["radius"]], 0.42, bp)
    ok = RK.shot_is_legal(p0, aim["v"], [0.0, 0.0, 0.0], bp, ip, tp, 1.55, 0)
    check("shot_is_legal", "相手コート中央へのロブ(滞空 0.42 s)", "legal、相手の面 x ≈ +1.55 m に届く",
          f"{ok['reason']}、x = {ok['p_arrive'][0]:.3f} m", ok["legal"] and abs(ok["p_arrive"][0] - 1.55) < 0.02)
    tr = B.flight_ode(p0, aim["v"], np.zeros(3), bp, 0.6, 1e-3)
    k = int(np.argmax(tr["p"][:, 0] >= 0.0))
    z_net = float(np.interp(0.0, tr["p"][k - 1:k + 1, 0], tr["p"][k - 1:k + 1, 2]))
    net_top = H + tp["net_height"] + bp["radius"]
    check("shot_is_legal", "独立の RK4 でネット上(x = 0)の高さ", f"> 台 + ネット + 半径 = {net_top:.4f} m", f"{z_net:.4f} m",
          z_net > net_top)
    net = RK.shot_is_legal(p0, [3.0, 0.0, -0.5], [0.0, 0.0, 0.0], bp, ip, tp, 1.55, 0)
    check("shot_is_legal", "下向きに強く打った球", "reason = net", net["reason"], (not net["legal"]) and net["reason"] == "net")
    back = RK.shot_is_legal(p0, [-1.0, 0.0, 0.5], [0.0, 0.0, 0.0], bp, ip, tp, 1.55, 0)
    check("shot_is_legal", "自分の後ろへ打った球", "reason = no_net_cross", back["reason"],
          (not back["legal"]) and back["reason"] == "no_net_cross")

    rng = np.random.default_rng(1)
    L, W = tp["length"], tp["width"]
    for k_shot, y_opp in ((0, 0.3), (1, -0.25)):
        ctx = {"opp_pos": np.array([1.55, y_opp, 1.0]), "shot_index": k_shot, "tp": tp}
        c = RK.strategy_attacker(0, ctx, rng)
        x, y = c["target"]
        far = np.sign(y) == -np.sign(y_opp) and abs(y) >= W / 2 - 0.15        # 相手と逆の端(端から 15 cm 以内)
        inside = 0 < x <= L / 2 and abs(y) <= W / 2
        depth_ok = abs(x - (L / 2 - 0.12)) < 1e-12 if k_shot % 2 == 0 else x < L / 4      # 深い / 浅い(ネット寄り)を交互
        check("strategy_attacker", f"相手 y = {y_opp:+.2f} m(shot {k_shot}: {'深い' if k_shot % 2 == 0 else '浅い'})",
              "逆側の端・相手コートの中・前後の交互・滞空 < 0.42 s",
              f"狙い ({x:+.3f}, {y:+.3f})、T = {c['T']} s", far and inside and depth_ok and c["T"] < 0.42)
    prev = (0.9, 0.2)
    for _ in range(3):
        f = RK.strategy_feeder(0, {"tp": tp, "prev_target": prev}, rng, step=0.06)
        x, y = f["target"]
        near = abs(x - prev[0]) <= 0.06 + 1e-12 and abs(y - prev[1]) <= 0.06 + 1e-12
        inside = 0.25 - 1e-12 <= x <= L / 2 - 0.12 + 1e-12 and abs(y) <= W / 2 - 0.12 + 1e-12
        check("strategy_feeder", f"前回 ({prev[0]:+.3f}, {prev[1]:+.3f})", "±6 cm 以内・端から 12 cm 内・T = 0.42 s",
              f"({x:+.3f}, {y:+.3f})、T = {f['T']} s", near and inside and f["T"] == 0.42)
        prev = (x, y)
    edge = RK.strategy_feeder(0, {"tp": tp, "prev_target": (5.0, 5.0)}, rng)
    check("strategy_feeder", "前回が台の外 (5, 5)", f"x ≤ {L / 2 - 0.12:.3f}、y ≤ {W / 2 - 0.12:.4f} に収める",
          f"({edge['target'][0]:.3f}, {edge['target'][1]:.4f})",
          edge["target"][0] <= L / 2 - 0.12 + 1e-12 and edge["target"][1] <= W / 2 - 0.12 + 1e-12)


def main() -> int:
    t0 = time.time()
    demo_parabola_and_perceiver()
    demo_kendama()
    demo_racket()
    demo_shots()
    w_op = max(len(r[0]) for r in ROWS)
    print(f"{'op':<{w_op}} | 確かめたこと | 期待 | 出た値 | 判定")
    for op, what, exp, got, ok in ROWS:
        print(f"{op:<{w_op}} | {what} | {exp} | {got} | {'合格' if ok else '★不合格'}")
    bad = [r for r in ROWS if not r[4]]
    if bad:
        print(f"FAIL: {len(bad)}/{len(ROWS)} 行が外れた({', '.join(sorted({r[0] for r in bad}))})")
        return 1
    print(f"PASS: {len({r[0] for r in ROWS})} op を {len(ROWS)} 行の真値で確認({time.time() - t0:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
