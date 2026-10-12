# -*- coding: utf-8 -*-
"""事例: カーブの限界・横の制御・視界の環境・横の安全距離・技能試験の数字(運転の台帳 op ギャラリー)

平たく言うと:
  運転の PoC が使う「横の運動」(drivelateral)、「天気と光」(driveenv)、「横の安全距離」(rsssafety)、
  「技能試験の採点の数字」(drivelong)の部品を、答えが外から分かる入力で 1 本ずつ呼ぶ。
  各行に「何を期待し、何が出て、合ったか」を印字し、外れたら exit 1。

確かめ方(op ごとの真値):
  * curve_speed_limit      —— 道路構造令の解説 (2) 式の力のつり合いを、出た速さで計算し直すと等号(残差 0)
  * design_min_radius      —— (3) 式 V²/(127(i + f)) の手計算と、その半径で curve_speed_limit が V に戻る(i·f の分だけ)
  * fresnel_integrals      —— scipy.special.fresnel(独立の実装)と既知値 C(∞) = S(∞) = ½
  * stanley_steer          —— 直線の経路で前車軸の運動学を Stanley の舵で積分した横ずれ e(t) が
  * stanley_straight_decay —— 閉形式(F(e) の二分法)と一致 / 小さい e は指数 e₀ e^{−vkt/(k_s+v)}
  * steady_cornering       —— δ = L/R + K u²/R、K = (m/L)(l_r/C_f − l_f/C_r) の手計算、r = u/R、a_y = u²/R
  * julian_day             —— J2000.0 = 2451545.0(2000-01-01 12:00 UTC)、Unix 元期 2440587.5、JST の換算、素朴な datetime は拒否
  * koschmieder / mor_from_beta —— 視程 MOR の距離で、見かけのコントラストがちょうど 5 %(2 つの op の整合)
  * tone_map               —— 暗い所は線形(露出倍)、色の比(色度)は保つ、最大チャンネルは 1 を超えない
  * veiling_luminance      —— Stiles–Holladay 10 E/θ² と CIE 146:2002 の一般式の手計算
  * rss_worst_case_gap_lateral —— 論文の横の安全距離を手で計算した最小間隔 d₀ − (d_min − μ) と、衝突の境目
  * skill_test_thresholds  —— 採点(skill_test_score)がその数字の境目で減点を切り替える、合格点 70(第一種)

    py -3.11 examples/gallery_drive_lateral_env.py
"""
from __future__ import annotations

import datetime as dt
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402

import driveenv as DE  # noqa: E402
import drivelateral as DL  # noqa: E402
import drivelong as DLG  # noqa: E402
import rsssafety as RS  # noqa: E402

ROWS: list = []
G = 9.81


def check(op: str, what: str, expected: str, got: str, ok: bool) -> None:
    """表の 1 行を貯める(何を期待し、何が出て、合ったか)。"""
    ROWS.append((op, what, expected, got, bool(ok)))


def demo_curves() -> None:
    R, f, i = 100.0, 0.15, 0.06
    v = float(DL.curve_speed_limit(R, side_friction=f, superelevation=i))
    a = math.atan(i)
    Z, Gw = v * v / (G * R), 1.0                       # 遠心力 / 重力(重さで割った)
    resid = (Z * math.cos(a) - Gw * math.sin(a)) - f * (Z * math.sin(a) + Gw * math.cos(a))
    check("curve_speed_limit", f"R = {R} m、f = {f}、i = {i}", "Z cos α − G sin α = f(Z sin α + G cos α)",
          f"v = {v:.4f} m/s ({v * 3.6:.2f} km/h)、残差 {resid:.1e}", abs(resid) < 1e-12)
    v0 = float(DL.curve_speed_limit(R, side_friction=f))
    check("curve_speed_limit", "片勾配 0", f"√(g R f) = {math.sqrt(G * R * f):.6f} m/s", f"{v0:.6f}",
          abs(v0 - math.sqrt(G * R * f)) < 1e-12)
    V = 60.0
    Rmin = float(DL.design_min_radius(V, side_friction=f, superelevation=i))
    check("design_min_radius", f"V = {V} km/h、f = {f}、i = {i}", f"V²/(127(i + f)) = {V * V / (127 * (i + f)):.4f} m",
          f"{Rmin:.4f} m", abs(Rmin - V * V / (127 * (i + f))) < 1e-9)
    vb = float(DL.curve_speed_limit(Rmin, side_friction=f, superelevation=i)) * 3.6
    check("design_min_radius", "その半径の厳密な上限速度(curve_speed_limit)", f"≈ {V} km/h(i·f と 127 ≈ 3.6² g の差だけ)",
          f"{vb:.3f} km/h", abs(vb / V - 1) < 0.01)


def demo_fresnel() -> None:
    from scipy.special import fresnel as sp_fresnel        # 独立の実装(scipy は (S, C) の順で返す)
    x = np.array([0.3, 1.0, 2.5, 3.4, 3.6, 6.0, 20.0])
    C, S = DL.fresnel_integrals(x)
    Ss, Cs = sp_fresnel(x)
    err = float(max(np.abs(C - Cs).max(), np.abs(S - Ss).max()))
    check("fresnel_integrals", "7 点(級数と漸近の境 3.5 を跨ぐ)", "scipy と 1e-8 以内", f"最大差 {err:.1e}", err < 1e-8)
    Cb, Sb = DL.fresnel_integrals(np.array([1e4]))
    check("fresnel_integrals", "x → ∞", "C = S = 0.5", f"C = {Cb[0]:.6f}, S = {Sb[0]:.6f}",
          abs(Cb[0] - 0.5) < 1e-4 and abs(Sb[0] - 0.5) < 1e-4)
    Cn, Sn = DL.fresnel_integrals(-x)
    check("fresnel_integrals", "奇関数", "C(−x) = −C(x)", f"{np.abs(Cn + C).max():.1e}",
          np.abs(Cn + C).max() < 1e-15 and np.abs(Sn + S).max() < 1e-15)


def demo_stanley() -> None:
    e0, k, v, ks, L, T, h = 2.0, 1.0, 5.0, 0.0, 2.7, 3.0, 2e-3
    path = np.stack([np.linspace(-50, 500, 5501), np.zeros(5501)], 1)
    f, psi, es = np.array([0.0, e0]), -0.2, [e0]
    for _ in range(int(round(T / h))):
        o = DL.stanley_steer(np.r_[f, psi], path, gain=k, speed=v, softening=ks)
        d = float(o["steer"][0]) if np.ndim(o["steer"]) else float(o["steer"])
        f = f + h * v * np.array([math.cos(psi + d), math.sin(psi + d)])
        psi = psi + h * v * math.sin(d) / L
        es.append(f[1])
    es = np.array(es)
    t = np.linspace(0, T, len(es))
    cf = DL.stanley_straight_decay(e0, t, gain=k, speed=v, softening=ks)
    err = float(np.abs(cf - es).max())
    check("stanley_steer", "直線の経路で e₀ = 2 m から積分(k = 1、v = 5 m/s)", "閉形式と 2e-3·e₀ 以内",
          f"最大差 {err * 1e3:.2f} mm(t = 3 s で e = {es[-1]:.4f} m)", err < 2e-3 * e0)
    o = DL.stanley_steer(np.array([0.0, 0.5, 0.0]), path, gain=k, speed=v)
    st = float(np.ravel(o["steer"])[0])
    check("stanley_steer", "経路の左 0.5 m・向きは平行", "δ = atan2(−k e, v) = atan2(−0.5, 5)", f"{st:.9f} rad",
          abs(st - math.atan2(-0.5, 5.0)) < 1e-12)
    e_small = float(DL.stanley_straight_decay(1e-4, 0.5, gain=2.0, speed=8.0, softening=1.0))
    want = 1e-4 * math.exp(-8.0 * 2.0 * 0.5 / (1.0 + 8.0))
    check("stanley_straight_decay", "小さい e(1e-4 m、k = 2、v = 8、k_s = 1)", f"e₀ e^(−vkt/(k_s+v)) = {want:.6e}",
          f"{e_small:.6e}", abs(e_small - want) < 1e-9)
    check("stanley_straight_decay", "直線を積分した軌跡(上の stanley_steer と同じ)", "閉形式と一致", f"最大差 {err * 1e3:.2f} mm",
          err < 2e-3 * e0)


def demo_cornering() -> None:
    car = {"mass": 1500.0, "l_f": 1.2, "l_r": 1.5, "c_f": 80000.0, "c_r": 90000.0, "inertia": 2500.0}
    u, R = 15.0, 80.0
    ss = DL.steady_cornering(u, R, car)
    Lw = car["l_f"] + car["l_r"]
    K = car["mass"] / Lw * (car["l_r"] / car["c_f"] - car["l_f"] / car["c_r"])
    want = Lw / R + K * u * u / R
    check("steady_cornering", f"u = {u} m/s、R = {R} m の舵角", f"L/R + K u²/R = {want:.9f} rad", f"{ss['steer']:.9f}",
          abs(ss["steer"] - want) < 1e-12)
    check("steady_cornering", "ヨーレート・横加速度", f"u/R = {u / R}, u²/R = {u * u / R}",
          f"{ss['yaw_rate']}, {ss['lateral_accel']}", abs(ss["yaw_rate"] - u / R) < 1e-15 and abs(ss["lateral_accel"] - u * u / R) < 1e-12)
    right = DL.steady_cornering(u, -R, car)
    check("steady_cornering", "右旋回(R < 0)", "舵角の符号だけ反転", f"{right['steer']:.9f}", abs(right["steer"] + ss["steer"]) < 1e-15)


def demo_environment() -> None:
    j2000 = DE.julian_day(dt.datetime(2000, 1, 1, 12, 0, tzinfo=dt.timezone.utc))
    check("julian_day", "2000-01-01 12:00 UTC", "2451545.0(J2000.0)", f"{j2000}", abs(j2000 - 2451545.0) < 1e-9)
    unix = DE.julian_day(dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc))
    check("julian_day", "1970-01-01 00:00 UTC", "2440587.5(Unix 元期)", f"{unix}", abs(unix - 2440587.5) < 1e-9)
    jst = DE.julian_day(dt.datetime(2000, 1, 1, 21, 0, tzinfo=dt.timezone(dt.timedelta(hours=9))))
    check("julian_day", "2000-01-01 21:00 JST", "UTC に直して J2000.0", f"{jst}", abs(jst - 2451545.0) < 1e-9)
    try:
        DE.julian_day(dt.datetime(2000, 1, 1, 12, 0))
        naive = False
    except ValueError:
        naive = True
    check("julian_day", "タイムゾーンの無い datetime", "拒否(ValueError)", "ValueError" if naive else "通った", naive)

    beta = 3.0e-3                                            # 1/m(霧)
    mor = DE.mor_from_beta(beta)
    check("mor_from_beta", f"β = {beta} /m", f"−ln 0.05 / β = {-math.log(0.05) / beta:.3f} m", f"{mor:.3f} m",
          abs(mor + math.log(0.05) / beta) < 1e-9)
    L0, Lh = 20.0, 200.0                                     # 暗い物体と明るい空
    Ld = float(DE.koschmieder(L0, Lh, beta, mor))
    contrast = (Ld - Lh) / (L0 - Lh)
    check("koschmieder", "視程 MOR の距離での見かけのコントラスト", "ちょうど 5 %", f"{contrast * 100:.9f} %", abs(contrast - 0.05) < 1e-12)
    far = float(DE.koschmieder(L0, Lh, beta, 1e5))
    check("koschmieder", "十分遠い物体", f"空の輝度 {Lh} に溶ける", f"{far:.6f}", abs(far - Lh) < 1e-6)

    rad = np.array([[1e-4, 2e-4, 0.5e-4], [3.0, 1.5, 0.3], [100.0, 40.0, 10.0]])
    out = DE.tone_map(rad, 2.0)
    check("tone_map", "暗い画素(m ≪ 1)", "露出倍 2 の線形(相対差 < 1e-3)", f"{np.abs(out[0] / (2 * rad[0]) - 1).max():.1e}",
          np.abs(out[0] / (2 * rad[0]) - 1).max() < 1e-3)
    ratio_err = float(np.abs(out[1:] / out[1:, :1] - rad[1:] / rad[1:, :1]).max())
    check("tone_map", "明るい画素の色の比(色度)", "入力の比と同じ", f"最大差 {ratio_err:.1e}", ratio_err < 1e-12)
    check("tone_map", "明るい画素の最大チャンネル", "≤ 1(白飛びで色が抜けない)", np.array2string(out[1:].max(1), precision=6),
          bool(np.all(out.max(1) <= 1.0 + 1e-15)))

    E, th = 5.0, np.array([2.0, 5.0, 10.0])
    sh = DE.veiling_luminance(E, th)
    check("veiling_luminance", "Stiles–Holladay、E = 5 lx", "10 E/θ²", np.array2string(sh, precision=6),
          np.allclose(sh, 10 * E / th ** 2, rtol=1e-14))
    age, p = 60.0, 0.5
    cie = DE.veiling_luminance(E, th, model="cie", age=age, p=p)
    want = E * (10 / th ** 3 + (5 / th ** 2 + 0.1 * p / th) * (1 + (age / 62.5) ** 4) + 0.0025 * p)
    check("veiling_luminance", f"CIE 146 一般式(60 歳、p = {p})", np.array2string(want, precision=6), np.array2string(cie, precision=6),
          np.allclose(cie, want, rtol=1e-14))


def demo_rss_lateral() -> None:
    p = RS.rss_params()                                      # ρ = 1 s、a_lat = 0.2、b_lat = 0.8、μ = 0.1
    v1, v2, d0 = 0.5, -0.5, 3.0                              # 左右から互いに 0.5 m/s で寄る
    rho, a, b = p["rho"], p["lat_accel_max"], p["lat_brake_min"]
    v1r = v1 + rho * a
    reach = (v1 + v1r) / 2 * rho + v1r ** 2 / (2 * b)        # 片側の車が止まるまでに寄る距離(論文 Lemma の形)
    want = d0 - 2 * reach
    r = RS.rss_worst_case_gap_lateral(d0, v1, v2, p)
    check("rss_worst_case_gap_lateral", f"d₀ = {d0} m、互いに 0.5 m/s で寄る", f"最小間隔 d₀ − 2·{reach:.5f} = {want:.5f} m",
          f"{r['min_gap']:.5f} m(衝突 {r['collided']})", abs(r["min_gap"] - want) < 1e-6 and not r["collided"])
    r2 = RS.rss_worst_case_gap_lateral(2 * reach - 0.1, v1, v2, p)
    check("rss_worst_case_gap_lateral", "寄る距離の和より 10 cm 近い", "衝突(min_gap < 0)", f"min_gap = {r2['min_gap']:.4f} m",
          r2["collided"] and abs(r2["min_gap"] + 0.1) < 1e-6)
    dmin = RS.rss_lateral(v1, v2, p, p)
    check("rss_worst_case_gap_lateral", "rss_lateral の d_min から μ を除いた閉形式", f"{d0 - (dmin - p['lat_margin']):.5f} m",
          f"{r['min_gap_closed_form']:.5f} m", abs(r["min_gap_closed_form"] - (d0 - (dmin - p["lat_margin"]))) < 1e-12)


def demo_skill_test() -> None:
    th = DLG.skill_test_thresholds()
    check("skill_test_thresholds", "逆行の段の順", "小 < 中 < 大", f"{th['rollback_small']} < {th['rollback_medium']} < {th['rollback_large']}",
          th["rollback_small"] < th["rollback_medium"] < th["rollback_large"])
    labels = {"逆行小": th["rollback_small"], "逆行中": th["rollback_medium"], "逆行大": th["rollback_large"]}
    for name, x in labels.items():
        below = DLG.skill_test_score([{"kind": "start", "rollback": x - 1e-6}])
        at = DLG.skill_test_score([{"kind": "start", "rollback": x}])
        got_at = [d[0] for d in at["deductions"]]
        got_below = [d[0] for d in below["deductions"]]
        check("skill_test_thresholds", f"逆行 {x} m の境目", f"{x} m で「{name}」、その直前は別の段",
              f"直前 {got_below or '減点なし'} / 境目 {got_at}", name in got_at and name not in got_below)
    g = th["stop_gap_max"]
    near = DLG.skill_test_score([{"kind": "stop", "gap": g}])
    far = DLG.skill_test_score([{"kind": "stop", "gap": g + 1e-6}])
    check("skill_test_thresholds", f"停止線の手前 {g} m の境目", "以内は減点なし、越えたら停止位置不適",
          f"{len(near['deductions'])} 件 / {[d[0] for d in far['deductions']]}",
          not near["deductions"] and [d[0] for d in far["deductions"]] == ["停止位置不適"])
    pm = th["pass_mark"]
    s70 = DLG.skill_test_score([{"kind": "start", "rollback": th["rollback_medium"]}] + [{"kind": "brake", "stages": 1}] * 2)
    check("skill_test_thresholds", f"合格点 {pm}(丙運発第 12 号、第一種)", "100 − 30 = 70 点で合格",
          f"{s70['score']} 点、合格 {s70['passed']}", pm == 70 and s70["score"] == 70 and s70["passed"])


def main() -> int:
    t0 = time.time()
    demo_curves()
    demo_fresnel()
    demo_stanley()
    demo_cornering()
    demo_environment()
    demo_rss_lateral()
    demo_skill_test()
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
