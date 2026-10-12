# -*- coding: utf-8 -*-
"""事例: 土・粒・群れ・触覚の膜(運転の台帳 op ギャラリー: roverslip / scoop / granular / swarmflow / tacdome / tacslip)

平たく言うと:
  ローバーの滑り、すくった粒の流れ、粒の山、群れの密度、指先の触覚センサの膜 —— 運転系の PoC が
  「足元と手先」を読むのに使う部品を、答えが外から分かる入力で 1 本ずつ呼ぶ。各行に
  「何を期待し、何が出て、合ったか」を印字し、外れたら exit 1。

確かめ方(op ごとの真値):
  * bekker_pressure          —— 公表の土の表(乾いた砂: k_c, k_φ, n)から手で計算した (k_c/b + k_φ) zⁿ、
                                log-log の傾き = n、細い車輪ほど圧が高い
  * slip_cvar                —— ガウス過程の予測分布 N(μ, σ) の上側 10 % の平均を 40 万標本のモンテカルロで(±1 %)、
                                α = 0 で平均
  * stream_areal_density     —— 面密度 n を知って円板をポアソンで撒いた画像の被覆率から逆に解き、n に戻る(±5 %)。
                                素朴な c/(πr²) が数え落とすことも並べる
  * cone_profile_px          —— 円錐 H − u tan φ、頂を丸めた高さ H − r/cos φ + r、両方の接点で傾きが連続
  * sph_density_pressure     —— 周期境界の正方格子(m = ρ₀Δ²、h = 1.3Δ)で全点が同じ ρ、ρ₀ の 0.3 % 以内、p = c²(ρ − ρ₀)
  * largedef_c1_coefficient  —— n = 1 で κ(d) が neo-Hookean の円柱の厳密解 [(1 − d)⁻² − (1 − d)]/(3d) に一致するのは
                                「導出」の読みだけ(原文の活字・以前のメモは外れる)、小さい d で 1 + 2d/(1 + n)
  * marker_match_grow        —— 核が 6.4 px 動く(ピッチ 8 px)場で、縁から伸ばす対応は全部正しい / 最近傍は隣に飛ぶ
  * mindlin_fit_vector       —— 向き φ・接線力 Q 既知の部分滑りの変位場(膜の合成)から φ と Q を読み戻す

    py -3.11 examples/gallery_drive_soil_tactile.py
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402
from scipy import ndimage  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

import granular as GR  # noqa: E402
import pegtactile as PT  # noqa: E402
import roverslip as RV  # noqa: E402
import scoop as SC  # noqa: E402
import swarmflow as SW  # noqa: E402
import tacdome as TD  # noqa: E402
import tacslip as TS  # noqa: E402

ROWS: list = []


def check(op: str, what: str, expected: str, got: str, ok: bool) -> None:
    """表の 1 行を貯める(何を期待し、何が出て、合ったか)。"""
    ROWS.append((op, what, expected, got, bool(ok)))


def demo_rover() -> None:
    kc, kphi, n = 10.3, 5309.4, 1.9                          # 乾いた砂(arXiv:2606.06790v2 表 2、roverslip.SOILS と同じ値)
    s = RV.SOILS["dry_sand"]
    check("bekker_pressure", "土の表の値(乾いた砂)", f"k_c = {kc}, k_φ = {kphi}, n = {n}", f"{s['kc']}, {s['kphi']}, {s['n']}",
          (s["kc"], s["kphi"], s["n"]) == (kc, kphi, n))
    z, b = np.array([0.0, 0.005, 0.02, 0.05]), 0.1
    p = RV.bekker_pressure(z, b, "dry_sand")
    want = (kc / b + kphi) * z ** n
    check("bekker_pressure", f"幅 b = {b} m、沈下 0〜5 cm", "(k_c/b + k_φ) zⁿ [kPa]", np.array2string(p, precision=4),
          np.allclose(p, want, rtol=1e-14) and p[0] == 0.0)
    slope = math.log(p[3] / p[2]) / math.log(z[3] / z[2])
    check("bekker_pressure", "log-log の傾き", f"n = {n}", f"{slope:.12f}", abs(slope - n) < 1e-12)
    narrow = float(RV.bekker_pressure(0.02, 0.05, "dry_sand"))
    check("bekker_pressure", "幅 5 cm と 10 cm(沈下 2 cm)", "細い車輪ほど圧が高い", f"{narrow:.4f} > {p[2]:.4f}", narrow > p[2])

    rng = np.random.default_rng(0)
    x = rng.uniform(-20, 24, 200)
    y = 0.02 + 0.012 * np.maximum(x, 0) + rng.normal(0, 0.03, x.size)   # 上りほど滑る(合成)
    gp = RV.slip_gp_fit(x, y)
    xx = np.array([0.0, 10.0, 20.0])
    pred = RV.slip_predict(gp, xx)
    c0 = RV.slip_cvar(gp, xx, 0.0)
    check("slip_cvar", "α = 0", "予測の平均", f"最大差 {np.abs(c0 - pred['mean']).max():.1e}", np.allclose(c0, pred["mean"], atol=1e-12))
    c9 = RV.slip_cvar(gp, xx, 0.9)
    zs = np.random.default_rng(1).standard_normal(400000)
    mc = []
    for m, sd in zip(pred["mean"], pred["std"]):
        smp = m + sd * zs
        mc.append(smp[smp >= np.quantile(smp, 0.9)].mean())
    mc = np.array(mc)
    check("slip_cvar", "α = 0.9(3 つの斜面角)", "N(μ, σ) の上側 10 % の平均(MC 40 万)± 1 %",
          f"{np.array2string(c9, precision=4)} vs MC {np.array2string(mc, precision=4)}", np.all(np.abs(c9 / mc - 1) < 0.01))


def demo_grains() -> None:
    rng = np.random.default_rng(5)
    Wd, r_px, n_true = 600, 6.0, 0.012                         # [個/px²]
    pad = int(r_px) + 2
    A = (Wd + 2 * pad) ** 2
    N = rng.poisson(n_true * A)
    cen = rng.uniform(-pad, Wd + pad, (N, 2))
    grid = np.ones((Wd + 2 * pad, Wd + 2 * pad), bool)
    ij = np.floor(cen + pad).astype(int)
    grid[ij[:, 0], ij[:, 1]] = False
    yy, xx = np.mgrid[-int(r_px) - 1:int(r_px) + 2, -int(r_px) - 1:int(r_px) + 2]
    a_eff = float(((yy ** 2 + xx ** 2) <= r_px ** 2).sum())          # 画素にした円板の面積(格子点の数)
    cover = ndimage.distance_transform_edt(grid) <= r_px
    c = float(cover[pad:-pad, pad:-pad].mean())
    r_eff = math.sqrt(a_eff / math.pi)
    n_hat = float(SC.stream_areal_density(np.array([c]), r_eff)[0])
    naive = c / a_eff
    check("stream_areal_density", f"ポアソンの円板(n = {n_true}/px²、r = {r_px} px)の被覆率 {c:.3f}",
          f"n = {n_true} ± 5 %", f"{n_hat:.5f}(素朴な c/(πr²) は {naive:.5f})", abs(n_hat / n_true - 1) < 0.05 and naive < 0.8 * n_true)
    try:
        SC.stream_areal_density(np.array([0.97]), r_eff)
        sat = False
    except ValueError:
        sat = True
    check("stream_areal_density", "被覆率 0.97(向こうが見えない)", "ValueError(mode='raise')", "ValueError" if sat else "通った", sat)

    H, phi = 80.0, 30.0
    t = math.tan(math.radians(phi))
    u = np.array([0.0, 20.0, 60.0, 200.0])
    cp = GR.cone_profile_px(u, H, phi)
    check("cone_profile_px", f"H = {H} px、φ = {phi}°", "max(0, H − u tan φ)", np.array2string(cp, precision=4),
          np.allclose(cp, np.maximum(0, H - u * t), atol=1e-12))
    rb, rt = 10.0, 12.0
    top = float(GR.cone_profile_px(np.array([0.0]), H, phi, apex_blunt_px=rb)[0])
    want_top = H - rb / math.cos(math.radians(phi)) + rb
    check("cone_profile_px", f"頂を半径 {rb} px で丸める", f"H − r/cos φ + r = {want_top:.6f}", f"{top:.6f}", abs(top - want_top) < 1e-9)
    s_phi = math.sin(math.radians(phi))
    x_t = H / t + rt * math.tan(math.radians(phi) / 2)          # 裾の円弧の中心(空気側)の u
    eps = 1e-6
    for name, ut in (("頂の接点 u = r sin φ", rb * s_phi), ("裾の接点 u = x_t − r sin φ", x_t - rt * s_phi)):
        cl, cm, cr = GR.cone_profile_px(np.array([ut - eps, ut, ut + eps]), H, phi, toe_round_px=rt, apex_blunt_px=rb)
        sl, sr = (cm - cl) / eps, (cr - cm) / eps
        check("cone_profile_px", f"両方丸めた断面の{name} = {ut:.4f} px", f"左右の傾きがどちらも −tan φ = {-t:.6f}(折れない)",
              f"左 {sl:.6f}、右 {sr:.6f}", abs(sl + t) < 1e-4 and abs(sr + t) < 1e-4)


def demo_sph() -> None:
    d, nx = 1.0, 20
    g = np.stack(np.meshgrid(np.arange(nx) * d, np.arange(nx) * d), -1).reshape(-1, 2) + 0.5 * d
    rho0, cs = 1000.0, 10.0
    res = SW.sph_density_pressure(g, 1.3 * d, mass=rho0 * d * d, rho0=rho0, c=cs, box=(nx * d, nx * d))
    rho = res["rho"]
    check("sph_density_pressure", "周期の正方格子 20 × 20、h = 1.3Δ", "全点同じ ρ、ρ₀ の 0.3 % 以内",
          f"ρ/ρ₀ − 1 = {rho.mean() / rho0 - 1:+.4%}、ばらつき {np.ptp(rho):.1e}",
          np.ptp(rho) < 1e-9 * rho0 and abs(rho.mean() / rho0 - 1) < 0.003)
    check("sph_density_pressure", "状態方程式", "p = c² (ρ − ρ₀)", f"最大差 {np.abs(res['p'] - cs ** 2 * (rho - rho0)).max():.1e}",
          np.allclose(res["p"], cs ** 2 * (rho - rho0), rtol=0, atol=1e-9))
    open_ = SW.sph_density_pressure(g, 1.3 * d, mass=rho0 * d * d, rho0=rho0, c=cs)
    corner = int(np.argmin(g.sum(1)))                                       # (0.5, 0.5)
    edge = int(np.argmin(np.abs(g[:, 0] - 0.5) + np.abs(g[:, 1] - (nx // 2 + 0.5))))
    inner = int(np.argmin(np.abs(g[:, 0] - (nx // 2 + 0.5)) + np.abs(g[:, 1] - (nx // 2 + 0.5))))
    rc, re, ri = (open_["rho"][k] for k in (corner, edge, inner))
    check("sph_density_pressure", "周期でない格子: 角 < 辺 < 内側", "近傍が欠けるほど ρ が低い、内側は周期と同じ",
          f"{rc / rho0:.3f} < {re / rho0:.3f} < {ri / rho0:.4f}", rc < re < ri and abs(ri - rho.mean()) < 1e-9 * rho0)


def demo_tactile() -> None:
    for n in (1.0, 2.0, 3.0):
        c1 = TD.largedef_c1_coefficient(n)
        check("largedef_c1_coefficient", f"n = {n:g}、d → 0 の 1 次", f"κ ≈ 1 + 2d/(1+n) ⇔ c₁ = 2 − 2/(1+n) = {2 - 2 / (1 + n):.6f}",
              f"{c1:.6f}", abs(c1 - (2 - 2 / (1 + n))) < 1e-15)
    dgrid = np.linspace(0.05, 0.6, 12)
    exact = ((1 - dgrid) ** -2 - (1 - dgrid)) / (3 * dgrid)
    for reading in ("derived", "printed"):
        c1 = TD.largedef_c1_coefficient(1.0, reading)
        kap = (1 - c1 * dgrid + (1 / 3) * dgrid ** 2) / (1 - dgrid) ** 2
        err = float(np.abs(kap / exact - 1).max())
        want_match = reading == "derived"
        check("largedef_c1_coefficient", f"n = 1、読み「{reading}」(c₁ = {c1:.3f})",
              "neo-Hookean の円柱の厳密解と一致" if want_match else "厳密解から外れる", f"最大の相対差 {err:.1e}",
              (err < 1e-12) if want_match else (err > 0.05))
    # 「memo」2/(1+n) は n = 1 でだけ導出と同じ値になる(偶然)。n = 2 で小さい d の 1 次を外す
    cm2 = TD.largedef_c1_coefficient(2.0, "memo")
    check("largedef_c1_coefficient", f"n = 2、読み「memo」(c₁ = {cm2:.4f})", f"1 次の極限が要る c₁ = {2 - 2 / 3:.4f} から外れる",
          f"差 {abs(cm2 - (2 - 2 / 3)):.4f}", abs(cm2 - (2 - 2 / 3)) > 0.5)

    p0 = TS.membrane_markers(160, 8.0, 0.0, 0.0)
    rc = np.hypot(p0[:, 0] - 79.5, p0[:, 1] - 79.5)
    u = 6.4 * np.exp(-(rc / 30.0) ** 2)
    p1 = p0 + np.column_stack([u, np.zeros_like(u)])
    mt = TS.marker_match_grow(p0, p1, 8.0)
    ok_pairs = int(np.sum(mt["i0"] == mt["i1"]))
    check("marker_match_grow", f"核が 6.4 px 動く場(ピッチ 8 px、{len(p0)} 個)", f"全 {len(p0)} 個が正しい相手",
          f"{mt['matched']} 個対応、うち正しい {ok_pairs}", mt["matched"] == len(p0) and ok_pairs == len(p0))
    wrong_nn = int((cKDTree(p1).query(p0)[1] != np.arange(len(p0))).sum())
    check("marker_match_grow", "比べ: 予測なしの最近傍", "核で隣のマーカーに飛ぶ(> 20 個)", f"{wrong_nn} 個が誤り", wrong_nn > 20)

    pad = PT.pad_params()
    ctx = PT.pad_context(pad)
    for ph in (0.4, 2.0):
        q = 0.8 * np.array([math.cos(ph), math.sin(ph)])
        d = PT.pad_marker_displacement(4.0, q, pad, ctx)
        hz = d["hz"]
        pts = ctx["pts_flat"]
        rr = np.hypot(*(pts - ctx["c0"]).T) * pad["pitch"]
        # 法線荷重(Hertz)の半径方向の変位を引いて、せん断の場だけを残す
        ur = TS.hertz_surface_ur(rr, hz["a"], hz["p0"], pad["G"], pad["nu"]) / np.maximum(rr, 1e-12)
        u_sh = d["u_m"] - ur[:, None] * (pts - ctx["c0"]) * pad["pitch"]
        model = TS.mindlin_model(hz, ctx["X"], ctx["Y"], ctx["kern"], pad["G"], pad["nu"])
        fit = TS.mindlin_fit_vector(model, pts, u_sh)
        dphi = math.degrees((fit["phi"] - ph + math.pi) % (2 * math.pi) - math.pi)
        check("mindlin_fit_vector", f"せん断 Q = 0.8 N、向き {math.degrees(ph):.1f}°", "向き ±0.1°、Q ± 5 mN、c/a は合成の値 ± 0.02",
              f"向き差 {dphi:+.4f}°、Q = {fit['Q']:.4f} N、c/a = {fit['c_over_a']:.3f}(真 {d['mp']['c_over_a']:.3f})",
              abs(dphi) < 0.1 and abs(fit["Q"] - 0.8) < 5e-3 and abs(fit["c_over_a"] - d["mp"]["c_over_a"]) < 0.02)


def main() -> int:
    t0 = time.time()
    demo_rover()
    demo_grains()
    demo_sph()
    demo_tactile()
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
