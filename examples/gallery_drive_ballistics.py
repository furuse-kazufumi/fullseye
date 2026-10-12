# -*- coding: utf-8 -*-
"""事例: 球の飛翔・跳ね・摩擦と、真上のカメラの画素→台の座標(運転の台帳 op ギャラリー: ballistics / puck)

平たく言うと:
  卓球の球・けん玉・エアホッケーの PoC が下請けに使う「物理の小さな部品」を、1 本ずつ
  **答えが外から分かる入力**で呼んで確かめる。数字を並べるだけでなく、各行に
  「何を期待したか / 何が出たか / 合ったか」を印字し、1 つでも外れたら exit 1。

確かめ方(op ごとの真値):
  * pendulum_period        —— 振り子の運動方程式 θ'' = −(g/L) sin θ を小振幅で numpy の RK4 で積分し、
                              零交差の間隔から測った周期(op の式を使わない独立な経路)
  * incline_slip_angle     —— 斜面の力のつり合い mg sin θ = μ mg cos θ(μ = 1 なら 45°)
  * mu_from_stop_distance  —— 等減速 μg で止まるまでを数値積分した距離から逆算した μ と往復
  * drag_coefficient_sphere —— Stokes の極限 C_d·Re/24 → 1、Newton 領域の教科書値 0.38〜0.50、抗力危機
  * magnus_lift_coefficient —— 閉形式 1/(2 + 1/S) の手計算(S = 1 で 1/3)と両端の極限
  * fit_bounce             —— :func:`ballistics.bounce` で (e, μ) 既知の跳ねを作り、前後の速度から戻す(往復)
  * roll_slide_state       —— 転がりの条件 v = r ω × n を手で満たした球 / 跳ねた後の grip 球
  * fit_aero               —— C_d・C_L 既知の RK4 軌跡から 8 パラメータを同定し直す(往復)
  * cup_catch_check        —— 皿の幾何の境目(横ずれ = 皿 − 玉 の半径、高さ 0〜1.5 r、速さ)の手計算
  * puck_pixel_to_world    —— 針穴カメラの閉形式 x = (col − W/2)·h/f と、world → pixel の往復

    py -3.11 examples/gallery_drive_ballistics.py
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402

import ballistics as B  # noqa: E402
import puck as PK  # noqa: E402

ROWS: list = []


def check(op: str, what: str, expected: str, got: str, ok: bool) -> None:
    """表の 1 行を貯める(何を期待し、何が出て、合ったか)。"""
    ROWS.append((op, what, expected, got, bool(ok)))


def _pendulum_rk4_period(L: float, g: float, theta0: float = 1e-3, dt: float = 1e-4) -> float:
    """θ'' = −(g/L) sin θ を RK4 で積分し、下向きの零交差の間隔(線形補間)から周期を測る。"""
    def f(th, om):
        return om, -(g / L) * math.sin(th)
    th, om, t = theta0, 0.0, 0.0
    crossings = []
    while len(crossings) < 3:
        k1 = f(th, om)
        k2 = f(th + 0.5 * dt * k1[0], om + 0.5 * dt * k1[1])
        k3 = f(th + 0.5 * dt * k2[0], om + 0.5 * dt * k2[1])
        k4 = f(th + dt * k3[0], om + dt * k3[1])
        th2 = th + dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        om2 = om + dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        if th > 0 >= th2:                                  # 正 → 負へ横切る瞬間
            crossings.append(t + dt * th / (th - th2))
        th, om, t = th2, om2, t + dt
    return float(np.mean(np.diff(crossings)))


def demo_pendulum_incline_stop() -> None:
    g = 9.81
    for L in (0.4, 1.0):
        T_op = B.pendulum_period(L)
        T_sim = _pendulum_rk4_period(L, g)
        check("pendulum_period", f"L = {L} m の周期 [s]", f"RK4 の積分 {T_sim:.6f}", f"{T_op:.6f}",
              abs(T_op / T_sim - 1) < 1e-5)
    for mu in (0.3, 1.0):
        th = B.incline_slip_angle(mu)
        resid = math.sin(th) - mu * math.cos(th)            # 斜面方向の重力 − 最大静止摩擦
        check("incline_slip_angle", f"μ = {mu} で滑り出す角", "sin θ − μ cos θ = 0" + (" (= 45°)" if mu == 1.0 else ""),
              f"{math.degrees(th):.4f}° (残差 {resid:.1e})",
              abs(resid) < 1e-12 and (mu != 1.0 or abs(math.degrees(th) - 45.0) < 1e-12))
    # 等減速 μg で止まるまでを数値積分して距離を測り、その距離から μ を戻す
    v0, mu_true, dt = 12.0, 0.7, 1e-5
    v, x = v0, 0.0
    while v > 0:
        v_new = max(v - mu_true * g * dt, 0.0)
        x += 0.5 * (v + v_new) * dt
        v = v_new
    mu_est = B.mu_from_stop_distance(v0, x)
    check("mu_from_stop_distance", f"{v0} m/s から {x:.3f} m で停止", f"μ = {mu_true}", f"{mu_est:.6f}",
          abs(mu_est - mu_true) < 1e-4)
    d_back = B.slide_stop_distance(v0, mu_est)
    check("mu_from_stop_distance", "往復: slide_stop_distance(μ̂) が元の距離", f"{x:.6f} m", f"{d_back:.6f} m",
          abs(d_back - x) < 1e-9)


def demo_aero_coefficients() -> None:
    cd_stokes = float(B.drag_coefficient_sphere(np.array([1e-3]))[0])
    check("drag_coefficient_sphere", "Stokes の極限 Re = 1e-3", "C_d·Re/24 = 1 (±0.1 %)", f"{cd_stokes * 1e-3 / 24:.5f}",
          abs(cd_stokes * 1e-3 / 24 - 1) < 1e-3)
    cd = B.drag_coefficient_sphere(np.array([1e4, 3e4, 1e5, 1e6]))
    check("drag_coefficient_sphere", "Newton 領域 Re = 1e4〜1e5(卓球の球)", "0.38〜0.50(教科書の球)",
          ", ".join(f"{c:.3f}" for c in cd[:3]), bool(np.all((cd[:3] > 0.38) & (cd[:3] < 0.50))))
    check("drag_coefficient_sphere", "抗力危機 Re = 1e6", "C_d(1e6) < ½ C_d(1e5)", f"{cd[3]:.3f} vs {cd[2]:.3f}",
          cd[3] < 0.5 * cd[2])
    S = np.array([1e-4, 1.0, 1e4])
    cl = B.magnus_lift_coefficient(S)
    check("magnus_lift_coefficient", "S = 1", "1/3 (= 1/(2 + 1))", f"{cl[1]:.12f}", abs(cl[1] - 1 / 3) < 1e-15)
    check("magnus_lift_coefficient", "S → 0 で C_L ≈ S、S → ∞ で 0.5", "1e-4 / 0.5",
          f"{cl[0]:.6e} / {cl[2]:.6f}", abs(cl[0] / 1e-4 - 1) < 3e-4 and abs(cl[2] - 0.5) < 1e-4)


def demo_bounce_roll() -> None:
    bp = B.ball_params()
    n = np.array([0.0, 0.0, 1.0])
    # 滑ったまま跳ねる(速い接線速度・小さい μ)
    e_true, mu_true = 0.85, 0.15
    ip = B.impact_params(e_true, mu_true)
    v_in, w_in = np.array([4.0, 0.5, -3.0]), np.array([0.0, -20.0, 0.0])
    out = B.bounce(v_in, w_in, n, bp, ip)
    fit = B.fit_bounce(v_in, w_in, out["v"], out["omega"], n, bp)
    check("fit_bounce", f"滑りの跳ね({out['regime']})から (e, μ)", f"e = {e_true}, μ = {mu_true}(等号)",
          f"e = {fit['e']:.12f}, μ = {fit['mu']:.12f}, 下界? {fit['mu_is_lower_bound']}",
          out["regime"] == "slip" and abs(fit["e"] - e_true) < 1e-12 and abs(fit["mu"] - mu_true) < 1e-12
          and not fit["mu_is_lower_bound"])
    # 途中で転がりに移る跳ね(μ が大きい): 戻る μ は下界
    ip2 = B.impact_params(0.9, 0.6)
    v2, w2 = np.array([1.0, 0.0, -3.0]), np.zeros(3)
    out2 = B.bounce(v2, w2, n, bp, ip2)
    fit2 = B.fit_bounce(v2, w2, out2["v"], out2["omega"], n, bp)
    check("fit_bounce", f"grip の跳ね({out2['regime']})から μ", "下界の印つき・μ̂ ≤ 0.6",
          f"μ̂ = {fit2['mu']:.4f}, 下界? {fit2['mu_is_lower_bound']}",
          out2["regime"] == "grip" and fit2["mu_is_lower_bound"] and fit2["mu"] <= 0.6 + 1e-12)
    # 転がり: v = r ω × n を手で満たす(n = ẑ なら ω_y = v_x / r)
    v_t = np.array([1.5, 0.0, 0.0])
    w_roll = np.array([0.0, 1.5 / bp["radius"], 0.0])
    rs = B.roll_slide_state(v_t, w_roll, n, bp)
    check("roll_slide_state", "ω_y = v_x / r の球", "転がり(滑り 0)", f"滑り {rs['slip_speed']:.2e} m/s, rolling={rs['rolling']}",
          rs["rolling"] and rs["slip_speed"] < 1e-12)
    rs0 = B.roll_slide_state(v_t, np.zeros(3), n, bp)
    check("roll_slide_state", "回っていない球", "滑り = |v| = 1.5 m/s", f"{rs0['slip_speed']:.12f}",
          (not rs0["rolling"]) and abs(rs0["slip_speed"] - 1.5) < 1e-15)
    rs2 = B.roll_slide_state(out2["v"] - (out2["v"] @ n) * n, out2["omega"], n, bp)
    check("roll_slide_state", "grip の跳ねの直後(bounce の出力)", "転がり", f"滑り {rs2['slip_speed']:.2e} m/s",
          rs2["rolling"])


def demo_fit_aero() -> None:
    cd_true, cl_true = 0.45, 0.20
    bp = B.ball_params(cd=cd_true, cl=cl_true)
    omega = np.array([0.0, -150.0, 0.0])                    # トップスピン
    tr = B.flight_ode([0.0, 0.0, 0.3], [6.0, 0.0, 1.5], omega, bp, 0.30, 1e-3)
    idx = np.arange(0, len(tr["t"]), 10)                    # 100 fps 相当で 31 点
    fit = B.fit_aero(tr["t"][idx], tr["p"][idx], omega, B.ball_params(cd=0.4, cl=0.1))
    check("fit_aero", "C_d・C_L 既知の軌跡(31 点)から同定", f"C_d = {cd_true}, C_L = {cl_true}",
          f"C_d = {fit['cd']:.6f}, C_L = {fit['cl']:.6f}, rms = {fit['rms']:.1e} m",
          abs(fit["cd"] - cd_true) < 1e-4 and abs(fit["cl"] - cl_true) < 1e-4)
    check("fit_aero", "初速度も戻る", "(6, 0, 1.5) m/s", np.array2string(fit["v0"], precision=5),
          np.allclose(fit["v0"], [6.0, 0.0, 1.5], atol=1e-4))


def demo_cup() -> None:
    c, a = np.array([0.1, 0.2, 0.3]), np.array([0.0, 0.0, 1.0])
    R, r = 0.05, 0.02                                        # 皿 5 cm、玉 2 cm → 横ずれの許容 3 cm、高さ 0〜3 cm
    cases = [("中心・静止", [0, 0, 0.01], [0, 0, 0], True),
             ("横ずれ 2.9 cm", [0.029, 0, 0.01], [0, 0, 0], True),
             ("横ずれ 3.1 cm", [0.031, 0, 0.01], [0, 0, 0], False),
             ("高さ 2.9 cm", [0, 0, 0.029], [0, 0, 0], True),
             ("高さ 3.1 cm", [0, 0, 0.031], [0, 0, 0], False),
             ("皿の面の下", [0, 0, -0.001], [0, 0, 0], False),
             ("速さ 1.2 m/s(上限 1)", [0, 0, 0.01], [0, 0, -1.2], False)]
    for name, d, v, want in cases:
        res = B.cup_catch_check(c + d, v, c, a, R, r)
        check("cup_catch_check", name, "入る" if want else "入らない",
              f"{'入る' if res['caught'] else '入らない'} (横 {res['lateral']:.3f}, 高 {res['height']:.3f})", res["caught"] == want)


def demo_puck_camera() -> None:
    tb = PK.puck_table()
    h, fovy, (Hh, W) = 1.5, 50.0, (480, 800)
    cam = PK.puck_pinhole_camera(tb, h, fovy, (Hh, W))
    f = (Hh / 2) / math.tan(math.radians(fovy) / 2)           # 焦点距離 [px](手計算)
    cr = np.array([[W / 2, Hh / 2], [W / 2 + f * 0.3 / h, Hh / 2 - f * 0.2 / h], [W / 2 - f * 0.9 / h, Hh / 2 + f * 0.4 / h]])
    want = np.array([[0.0, 0.0], [0.3, 0.2], [-0.9, -0.4]])
    got = PK.puck_pixel_to_world(cam, cr)
    err = float(np.abs(got - want).max())
    check("puck_pixel_to_world", "針穴 x = (col − W/2)·h/f(3 点)", "(0,0), (0.3,0.2), (−0.9,−0.4) m", f"最大誤差 {err:.1e} m",
          err < 1e-12)
    rng = np.random.default_rng(7)
    xy = np.column_stack([rng.uniform(-tb["x_half"], tb["x_half"], 50), rng.uniform(-tb["y_half"], tb["y_half"], 50)])
    back = PK.puck_pixel_to_world(cam, PK.puck_world_to_pixel(cam, xy))
    check("puck_pixel_to_world", "往復 world → pixel → world(50 点)", "誤差 ≤ 1e-12 m", f"{np.abs(back - xy).max():.1e}",
          np.abs(back - xy).max() < 1e-12)
    cam2 = PK.puck_camera(tb, px_per_m=200.0, margin=0.06)  # 正射の合成カメラ: col = (x + x_half + margin)·s
    corner = PK.puck_pixel_to_world(cam2, [[0.0, 0.0]])[0]
    check("puck_pixel_to_world", "正射カメラの画素 (0, 0)", f"(−{tb['x_half'] + 0.06:.3f}, +{tb['y_half'] + 0.06:.3f}) m",
          f"({corner[0]:.3f}, {corner[1]:+.3f})", np.allclose(corner, [-(tb["x_half"] + 0.06), tb["y_half"] + 0.06], atol=1e-12))


def main() -> int:
    t0 = time.time()
    demo_pendulum_incline_stop()
    demo_aero_coefficients()
    demo_bounce_roll()
    demo_fit_aero()
    demo_cup()
    demo_puck_camera()
    w_op = max(len(r[0]) for r in ROWS)
    print(f"{'op':<{w_op}} | 確かめたこと | 期待 | 出た値 | 判定")
    for op, what, exp, got, ok in ROWS:
        print(f"{op:<{w_op}} | {what} | {exp} | {got} | {'合格' if ok else '★不合格'}")
    bad = [r for r in ROWS if not r[4]]
    ops_called = sorted({r[0] for r in ROWS})
    if bad:
        print(f"FAIL: {len(bad)}/{len(ROWS)} 行が外れた({', '.join(sorted({r[0] for r in bad}))})")
        return 1
    print(f"PASS: {len(ops_called)} op を {len(ROWS)} 行の真値で確認({time.time() - t0:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
