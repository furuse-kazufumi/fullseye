# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""流体のように流れる群れが、見えない障害物を「速度場の乱れ」だけで察知する —— 俯瞰の映像から衝突点と障害物の輪郭を読む(2026-10-05)。

群れのロボットを SPH(平滑化粒子流体力学)の粒子として動かすと、群れ全体が流体のように流れ、障害物に当たった個体の減速が
押し合いの圧力として上流へ伝わる。上から撮った映像で個体を追い、速度場の「自由流からの欠け方」を読めば、障害物は
映っていなくても、**どこに・どれくらいの大きさで**あるかが分かる。題材の背景は群れロボットの流体模倣制御
(doi:10.1109/iros58592.2024.10801800 とその発展)。学習は使わず、外から来る閉形式と比べる。

外から来るもの(閉形式):
  * SPH の 3 次スプライン核の正規化 ∫ W dV = 1(恒等式、1・2・3 次元)。
  * 円柱まわりのポテンシャル流 u − i v = U (1 − R²/(z − z_c)²): よどみ点 (x_c − R, y_c)、表面の速さ 2U|sin θ|。
    群れ(自由流へ戻る抵抗が強い弱圧縮の流体)は Darcy の流れになり、円柱のまわりで近似的にポテンシャル流になる(導出は module)。
  * Ritter のダム崩壊解(先端 2√(g h₀)、ダムの位置で 4h₀/9)と、粒子法の最も前の粒子の居場所 x_f − (27 g t² m/2)^{1/3}(導出)。
被験者(既存の op): pivops.piv_cross_correlate(相互相関の PIV)、blob2d.blob_label(個体の検出)。

門(既定 12 本、numpy + scipy、数秒):
  1 核の正規化 / 2 ポテンシャル流の閉形式 / 3 二つの推定(中心線の直線化と 2 次元の当てはめ)が閉形式の場で一致 /
  4 粒子の映像 → PIV の速度場の誤差と障害物 / 5 粒子の映像 → 追跡の速度場の誤差と障害物 / 6 否定の門(両側)/
  7 密度の限界(個体の間隔と半径の比)/ 8 群れの模擬: 映像の速度 = 個体の本当の速度 / 9 群れ: 上流だけで障害物を当てる
  (当たる前に分かる)/ 10 群れ: 障害物なしで何も言わない / 11 罠 2 つ(格子のように並ぶ群れの PIV、上流の端の速さを U に
  そのまま使う)/ 12 Ritter と SPH の浅水(ゲートを開けた群れの広がり)。
図(FULLSEYE_FIGURE_DIR があるとき、等倍): 01 障害物を描かない群れの流れに、推定した衝突点と障害物の輪郭が浮かび上がる GIF /
  02 速さの変化の地図(閉形式・PIV・追跡・群れ)/ 03 中心線の 1/√d の直線(閉形式・PIV・群れ)/ 04 密度と誤差(追跡と PIV の限界)/ 05 ダム崩壊。
正直に: 群れの流れは厳密なポテンシャル流ではない —— 障害物の後ろに個体の入らない空洞ができ、表面の速さは 2U に届かない
(実測 1.3U 前後)。だから当てはめは**上流だけ**で行い、それでも半径は 1 割ほど小さく出る(門 9 の内訳)。
Run: py -3.11 examples/poc_swarm_obstacle_from_flow.py
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import swarmflow as S  # noqa: E402

_GATES: list[tuple[str, bool]] = []
CYL = (0.3, 0.123, 0.6)                 # 粒子の映像の障害物(中心は格子の節点に載せない)
RES, SHAPE = 0.015, (267, 400)
SW_CYL, SW_BOX, SW_RES, SW_SHAPE = (0.3, 0.1, 0.6), (8.0, 5.0), 0.02, (250, 400)


def gate(name, ok, detail=""):
    _GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail), flush=True)


def _cerr(ob, cyl):
    return math.hypot(ob["center"][0] - cyl[0], ob["center"][1] - cyl[1]) / cyl[2], ob["radius"] / cyl[2] - 1.0


def pf_frames(n_agents, n_frames, dt, seed=0, cyl=CYL):
    """一様に撒いた粒子をポテンシャル流で RK4 で運んだ俯瞰のコマ(真値の速度場は閉形式)。"""
    rng = np.random.default_rng(seed)
    p = np.column_stack([rng.uniform(-3.3, 3.3, n_agents), rng.uniform(-2.1, 2.1, n_agents)])
    p = p[np.hypot(p[:, 0] - cyl[0], p[:, 1] - cyl[1]) > cyl[2]]

    def vel(q):
        r = S.potential_flow_cylinder(q[:, 0], q[:, 1], cyl, 1.0)
        return np.column_stack([np.nan_to_num(r["u"]), np.nan_to_num(r["v"])])

    out = []
    for _ in range(n_frames):
        out.append(S.swarm_render_overhead(p, SHAPE, RES, diameter_px=2.5))
        h = dt / 4
        for _ in range(4):
            k1 = vel(p)
            k2 = vel(p + h / 2 * k1)
            k3 = vel(p + h / 2 * k2)
            k4 = vel(p + h * k3)
            p = p + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
    return out


def field_err(field, cyl=CYL, margin=1.3):
    t = S.potential_flow_cylinder(field["x"], field["y"], cyl, 1.0, grid=True)
    X, Y = np.meshgrid(field["x"], field["y"])
    m = field["valid"] & t["valid"] & (np.hypot(X - cyl[0], Y - cyl[1]) > margin * cyl[2])
    e = np.hypot(field["u"] - t["u"], field["v"] - t["v"])[m]
    return float(np.sqrt(np.mean(e ** 2))), int(m.sum())


def run() -> dict:
    out = {}
    from scipy.integrate import quad
    # 1. 核の正規化
    tot = []
    for d, area in ((1, 2.0), (2, 2 * math.pi), (3, 4 * math.pi)):
        f = lambda r, d=d, area=area: S.sph_kernel(np.array(r), 0.7, dim=d)[()] * area * r ** (d - 1)  # noqa: E731
        tot.append(quad(f, 0, 0.7)[0] + quad(f, 0.7, 1.4)[0])
    gate("1 SPH 核の正規化 ∫W dV = 1", max(abs(t - 1) for t in tot) < 1e-10, "1D/2D/3D = %s" % ", ".join("%.12f" % t for t in tot))
    # 2. ポテンシャル流の閉形式
    xc, yc, R = CYL
    th = np.linspace(0.05, math.pi - 0.05, 60)
    r = S.potential_flow_cylinder(xc + R * 1.0000001 * np.cos(th), yc + R * 1.0000001 * np.sin(th), CYL, 1.0)
    es = float(np.max(np.abs(np.hypot(r["u"], r["v"]) - 2 * np.sin(th))))
    st = S.potential_flow_cylinder(np.array([xc - R - 1e-9]), np.array([yc]), CYL, 1.0)
    gate("2 ポテンシャル流: 表面の速さ 2U|sin θ|・よどみ点で 0", es < 1e-5 and abs(st["u"][0]) < 1e-6,
         "表面の最大のずれ %.1e、よどみ点の u %.1e" % (es, st["u"][0]))
    # 3. 二つの推定が閉形式の場で一致
    x, y = np.linspace(-3, 3, 121), np.linspace(2, -2, 81)
    fpf = S.potential_flow_cylinder(x, y, CYL, 1.0, grid=True)
    c1 = S.stagnation_from_centerline(fpf)
    c2 = S.obstacle_fit_doublet(fpf)
    e1, e2 = _cerr(c1, CYL), _cerr(c2, CYL)
    out["centerline"], out["pf_field"] = c1, fpf
    gate("3 中心線の直線化 = 2 次元の当てはめ = 真値(閉形式の場)", max(map(abs, e1)) < 5e-3 and max(map(abs, e2)) < 1e-6,
         "中心線: 中心 %.4f R・半径 %+.4f(y_c は格子の間)/ 2 次元: %.1e・%+.1e / よどみ点 x %.4f(真 %.4f)、反復 %d 回"
         % (e1[0], e1[1], e2[0], e2[1], c1["stagnation"][0], xc - R, c1.get("n_iter", 0)))
    # 4. PIV
    t0 = time.process_time()
    fr = pf_frames(2400, 5, 0.03, seed=0)
    fp = S.swarm_field_from_piv(fr, RES, 0.03, window=32, min_peak_ratio=1.2)
    ep, npv = field_err(fp)
    op_ = S.obstacle_fit_doublet(fp)
    cp = _cerr(op_, CYL)
    out["piv"] = (fp, op_)
    gate("4 粒子の映像 → PIV(pivops)→ 速度場と障害物", ep < 0.03 and op_["detected"] and max(map(abs, cp)) < 0.02,
         "速度の rms 誤差 %.2f %% of U(%d 格子)、中心 %.3f R、半径 %+.3f、説明できる割合 %.3f(CPU %.2f s)"
         % (100 * ep, npv, cp[0], cp[1], op_["explained"], time.process_time() - t0))
    # 5. 追跡
    t0 = time.process_time()
    fr = pf_frames(1200, 5, 0.015, seed=1)
    ft = S.swarm_field_from_tracks(fr, RES, 0.015)
    et, nt = field_err(ft)
    ot = S.obstacle_fit_doublet(ft)
    ct = _cerr(ot, CYL)
    out["track"] = (ft, ot)
    gate("5 粒子の映像 → 追跡(blob2d)→ 速度場と障害物", et < 0.04 and ot["detected"] and max(map(abs, ct)) < 0.02,
         "速度の rms 誤差 %.2f %% of U(%d 格子)、つないだ組 %d・捨てた組 %d、中心 %.3f R、半径 %+.3f(CPU %.2f s)"
         % (100 * et, nt, ft["n_linked"], ft["n_outliers"], ct[0], ct[1], time.process_time() - t0))
    # 6. 否定の門(両側)
    rng = np.random.default_rng(2)
    xg, yg = np.linspace(-3, 3, 61), np.linspace(2, -2, 41)
    en, eo = [], []
    for k in range(4):
        nz = 0.05 * rng.normal(size=(2, 41, 61))
        on = S.obstacle_fit_doublet({"x": xg, "y": yg, "u": 1 + nz[0], "v": nz[1]})
        f = S.potential_flow_cylinder(xg, yg, (0.3 * k - 0.4, 0.2 * k - 0.3, 0.45), 1.0, grid=True)
        oo = S.obstacle_fit_doublet(dict(f, u=f["u"] + nz[0], v=f["v"] + nz[1]))
        en.append((on["explained"], on["detected"]))
        eo.append((oo["explained"], oo["detected"]))
    X, Y = np.meshgrid(xg, yg)
    r2 = np.maximum((X - 0.3) ** 2 + (Y - 0.1) ** 2, 0.09)
    other = []
    for u, v in ((1 - 0.4 * (Y - 0.1) / r2, 0.4 * (X - 0.3) / r2), (1 + 0.4 * (X - 0.3) / r2, 0.4 * (Y - 0.1) / r2)):
        o = S.obstacle_fit_doublet({"x": xg, "y": yg, "u": u + 0.02 * rng.normal(size=u.shape), "v": v + 0.02 * rng.normal(size=u.shape)})
        other.append(o)
    ok6 = (not any(d for _, d in en) and all(d for _, d in eo) and max(e for e, _ in en) < 0.1 and min(e for e, _ in eo) > 0.7
           and all((not o["detected"]) and o["radius"] >= o["min_radius"] for o in other))
    gate("6 否定の門: 障害物なし・渦・湧き出し → 言わない / あり → 言う(しきい値 0.5 から両側とも離れている)", ok6,
         "説明できる割合: なし 最大 %.3f / あり 最小 %.3f(雑音 5 %% of U、4 通り)/ 渦 %.3f(R %.2f m)・湧き出し %.3f(R %.2f m)は半径の下限 %.2f m を"
         "超えるのに割合で落ちる" % (max(e for e, _ in en), min(e for e, _ in eo), other[0]["explained"], other[0]["radius"],
                                    other[1]["explained"], other[1]["radius"], other[0]["min_radius"]))
    # 7. 密度の限界
    dens = []
    for n in (2400, 600, 140, 70, 35):
        row = {"n": n}
        f = S.swarm_field_from_tracks(pf_frames(n, 4, 0.015, seed=3), RES, 0.015)
        o = S.obstacle_fit_doublet(f)
        row.update(spacing=f["spacing"], track=_cerr(o, CYL), track_det=o["detected"], track_err=field_err(f)[0])
        f2 = S.swarm_field_from_piv(pf_frames(n, 3, 0.03, seed=3), RES, 0.03, window=32, min_peak_ratio=1.2)
        o2 = S.obstacle_fit_doublet(f2)
        row.update(piv=_cerr(o2, CYL), piv_det=o2["detected"], piv_err=field_err(f2)[0])
        dens.append(row)
    out["density"] = dens
    d600 = next(r_ for r_ in dens if r_["n"] == 600)
    d35 = next(r_ for r_ in dens if r_["n"] == 35)
    ok7 = d600["track_det"] and max(map(abs, d600["track"])) < 0.05 and not d35["track_det"] and abs(d35["track"][1]) > 0.25
    gate("7 密度の限界(追跡): R/間隔 ≈ 5 で当たり、≈ 1.2 では言わない(言わないのが正しい = 半径が大きく外れる)。PIV は窓の格子が固定なので疎でも読める", ok7,
         "; ".join("n=%d R/s=%.1f 追跡 %s(半径 %+.2f)PIV %s(%.1f %%)" % (r_["n"], CYL[2] / r_["spacing"], "○" if r_["track_det"] else "×",
                                                                    r_["track"][1], "○" if r_["piv_det"] else "×", 100 * r_["piv_err"])
                   for r_ in dens))
    # 8〜10. 群れの模擬
    t0 = time.process_time()
    sims = {}
    # 障害物ありは 2 s 流して定常に近づける(1.2 s では過渡で中心が 0.14R ずれた —— 種 3 つで実測、2 s で 0.03〜0.05R)。
    for name, obs, tw in (("obstacle", SW_CYL, 2.0), ("none", None, 1.0)):
        sim = S.swarm_simulate(obs, box=SW_BOX, spacing=0.15, t_warm=tw, n_frames=10, frame_dt=0.04, seed=4)
        frs = [S.swarm_render_overhead(p, SW_SHAPE, SW_RES, diameter_px=3.0) for p in sim["frames"]]
        f = S.swarm_field_from_tracks(frs, SW_RES, 0.04)
        g, _ = S._shepard(sim["frames"][:-1].reshape(-1, 2), sim["velocities"][:-1].reshape(-1, 2), f["x"], f["y"], f["spacing"], 3)
        m = f["valid"] & np.isfinite(g[..., 0])
        err = float(np.sqrt(np.mean((f["u"] - g[..., 0])[m] ** 2 + (f["v"] - g[..., 1])[m] ** 2)))
        sims[name] = {"sim": sim, "frames": frs, "field": f, "err": err}
    out["sims"] = sims
    so = sims["obstacle"]
    gate("8 群れ: 映像から測った速度 = 個体の本当の速度", so["err"] < 0.05 and sims["none"]["err"] < 0.05
         and so["sim"]["t_total"] < so["sim"]["t_wake_reenters"],
         "rms %.2f %% / %.2f %% of U(個体 %d、密度の揺れ ρ/ρ₀ %.3f〜%.3f、流した %.2f s < 空洞が回り込む %.2f s、CPU %.1f s)"
         % (100 * so["err"], 100 * sims["none"]["err"], so["sim"]["n_agents"], *so["sim"]["density_range"], so["sim"]["t_total"],
            so["sim"]["t_wake_reenters"], time.process_time() - t0))
    ofull = S.obstacle_fit_doublet(so["field"])
    oup = S.obstacle_fit_doublet(so["field"], upstream_only=True)
    cu, cf = _cerr(oup, SW_CYL), _cerr(ofull, SW_CYL)
    out["sw_fit"] = (oup, ofull)
    gate("9 群れ: 上流だけの当てはめで障害物の位置と大きさ(当たる前に分かる)", oup["detected"] and cu[0] < 0.15 and -0.25 < cu[1] < 0.05,
         "上流: 中心 %.3f R・半径 %+.3f・衝突点 x %.3f(壁 %.3f)/ 全面: 中心 %.3f R・半径 %+.3f・説明 %.2f(後ろの空洞で模型が外れる)"
         % (cu[0], cu[1], oup["stagnation"][0], SW_CYL[0] - SW_CYL[2], cf[0], cf[1], ofull["explained"]))
    f0 = sims["none"]["field"]
    n0, n0u = S.obstacle_fit_doublet(f0), S.obstacle_fit_doublet(f0, upstream_only=True)
    gate("10 群れ: 障害物なしでは何も言わない", not n0["detected"] and not n0u["detected"],
         "説明できる割合 %.3f / 上流だけ %.3f" % (n0["explained"], n0u["explained"]))
    # 11. 罠
    fp0 = S.swarm_field_from_piv(so["frames"][:4], SW_RES, 0.04, min_peak_ratio=0.0, outlier_threshold=None)
    fp1 = S.swarm_field_from_piv(so["frames"][:4], SW_RES, 0.04)
    sim = so["sim"]
    errs = []
    for fpx in (fp0, fp1):
        g, _ = S._shepard(sim["frames"][:3].reshape(-1, 2), sim["velocities"][:3].reshape(-1, 2), fpx["x"], fpx["y"], 0.2, 3)
        m = fpx["valid"] & np.isfinite(g[..., 0])
        errs.append(float(np.sqrt(np.mean((fpx["u"] - g[..., 0])[m] ** 2 + (fpx["v"] - g[..., 1])[m] ** 2))))
    c_naive = S.stagnation_from_centerline(fpf, n_iter=1)
    out["traps"] = errs
    gate("11 罠: 格子のように並ぶ群れの PIV(峰の比と中央値の検査なし)/ 上流の端の速さをそのまま U に",
         errs[0] > 3 * errs[1] and abs(_cerr(c_naive, CYL)[1]) > 0.1,
         "PIV の rms: 検査なし %.1f %% → 峰の比 1.1 + 中央値の検査で %.1f %%(測れた窓 %.0f %%)/ U を端の中央値のまま: 半径 %+.1f %%(U = %.4f)"
         % (100 * errs[0], 100 * errs[1], 100 * fp1["valid_fraction"], 100 * _cerr(c_naive, CYL)[1], c_naive["speed"]))
    # 12. Ritter と SPH の浅水
    t0 = time.process_time()
    db = S.sph_dam_break_1d(h0=0.1, length=1.0, n_particles=400, t_end=0.2, n_out=4)
    rows, ok12 = [], True
    for k, t in enumerate(db["t"]):
        rr = S.ritter_dam_break(db["x"][k], t, 0.1, particle_mass=0.1 / 400)
        fan = (db["x"][k] > rr["rarefaction_head"]) & (db["x"][k] < 0.7 * rr["front"])
        l1 = float(np.mean(np.abs(db["h"][k] - rr["h"])[fan])) / 0.1
        lead = db["front"][k] / rr["lead_particle"] - 1
        ok12 &= l1 < 0.015 and abs(lead) < 0.07
        rows.append((t, l1, lead, db["front"][k] / rr["front"]))
    out["dam"] = db
    gate("12 Ritter: SPH の浅水の扇の形と最も前の粒子(先端から m/2 の所)", ok12,
         "; ".join("t=%.2f s 扇 L1 %.2f %%・前の粒子 %+.1f %%・Ritter の先端との比 %.2f" % (r_[0], 100 * r_[1], 100 * r_[2], r_[3]) for r_ in rows)
         + "(CPU %.1f s)" % (time.process_time() - t0))
    return out


# ======================================================================================================================
# 図
def _ring(shape, cx, cy, r, width=1.6):
    yy, xx = np.indices(shape)
    return np.clip(1.0 - np.abs(np.hypot(xx - cx, yy - cy) - r) / width, 0.0, 1.0)


def _dashed(shape, cx, cy, r, width=1.3, n=36):
    yy, xx = np.indices(shape)
    ang = np.arctan2(yy - cy, xx - cx)
    on = (np.floor((ang + math.pi) / (2 * math.pi) * n) % 2) == 0
    return _ring(shape, cx, cy, r, width) * on


def _cross(shape, cx, cy, size=7, width=1.4):
    yy, xx = np.indices(shape)
    d1 = np.abs((xx - cx) - (yy - cy)) / math.sqrt(2)
    d2 = np.abs((xx - cx) + (yy - cy)) / math.sqrt(2)
    inside = (np.abs(xx - cx) <= size) & (np.abs(yy - cy) <= size)
    return np.clip(1.0 - np.minimum(d1, d2) / width, 0, 1) * inside


def _blend(img, alpha, color):
    a = alpha[..., None]
    return img * (1 - a) + np.asarray(color)[None, None, :] * a


def _gif(out):
    import fullseye as fs
    so = out["sims"]["obstacle"]
    sim = S.swarm_simulate(SW_CYL, box=SW_BOX, spacing=0.15, t_warm=1.8, n_frames=30, frame_dt=0.04, seed=4)
    frs = [S.swarm_render_overhead(p, SW_SHAPE, SW_RES, diameter_px=3.0) for p in sim["frames"]]
    dres = SW_RES / 2
    dshape = (SW_SHAPE[0] * 2, SW_SHAPE[1] * 2)
    to_px = lambda x, y: ((x - 0.0) / dres + (dshape[1] - 1) / 2.0, (dshape[0] - 1) / 2.0 - (y - 0.0) / dres)  # noqa: E731
    frames = []
    hist = []
    for k in range(len(frs)):
        lum = S.swarm_render_overhead(sim["frames"][k], dshape, dres, diameter_px=5.0)
        base = np.zeros(dshape + (3,)) + np.array([0.04, 0.05, 0.09])
        base = _blend(base, np.round(np.clip(1.4 * lum, 0, 1) * 3) / 3 * 0.92, (0.92, 0.94, 1.0))   # 4 段の点(GIF の色数を抑える)
        lo = max(0, k - 9)
        label = "watching the flow ..."
        if k - lo >= 2:
            f = S.swarm_field_from_tracks(frs[lo:k + 1], SW_RES, 0.04)
            dm = S.velocity_deficit_map(f)["deficit"]
            # 欠損の地図を表示の格子へ(最近傍)
            yy, xx = np.indices(dshape)
            wx = (xx - (dshape[1] - 1) / 2.0) * dres
            wy = ((dshape[0] - 1) / 2.0 - yy) * dres
            jx = np.clip(np.round((wx - f["x"][0]) / (f["x"][1] - f["x"][0])).astype(int), 0, len(f["x"]) - 1)
            iy = np.clip(np.round((wy - f["y"][0]) / (f["y"][1] - f["y"][0])).astype(int), 0, len(f["y"]) - 1)
            dd = np.round(np.nan_to_num(dm[iy, jx]) / 0.1) * 0.1        # 0.1 刻みの帯(等高線の段)—— 読みやすく、GIF も軽い
            base = _blend(base, np.clip(dd, 0, 0.8) * 0.75, (1.0, 0.55, 0.1))      # 遅くなった所 = 橙
            base = _blend(base, np.clip(-dd, 0, 0.4) * 0.9, (0.2, 0.55, 1.0))      # 速くなった所 = 青
            ob = S.obstacle_fit_doublet(f, upstream_only=True)
            if ob["detected"]:
                hist.append(ob)
                cx, cy = to_px(*ob["center"])
                base = _blend(base, _ring(dshape, cx, cy, ob["radius"] / dres, 2.2), (0.3, 1.0, 0.95))
                sx, sy = to_px(*ob["stagnation"])
                base = _blend(base, _cross(dshape, sx, sy, 9, 2.0), (1.0, 0.25, 0.8))
                label = "estimated obstacle R = %.2f m, impact point x = %.2f m (from the upstream flow only)" % (ob["radius"], ob["stagnation"][0])
        if k >= len(frs) - 8:
            cx, cy = to_px(*SW_CYL[:2])
            base = _blend(base, _dashed(dshape, cx, cy, SW_CYL[2] / dres, 1.6), (1.0, 1.0, 1.0))
            label = "dashed = true obstacle (never drawn to the swarm or the estimator)"
        img = np.clip(base, 0, 1)
        img = np.asarray(fs.text_box(img, "t = %.2f s   %s" % (k * 0.04, label), (10, 10), anchor="lt", font_size=14))
        frames.append((np.clip(img, 0, 1) * 255).astype(np.uint8))
    figs.save_gif("swarmflow_hidden_obstacle_emerges", frames, fps=8.0,
                  caption="群れ(白い点、%d 個体)が左から右へ流れる。障害物は描いていない —— 群れには当たる壁として効くだけ。直近 10 コマの"
                          "個体の追跡から速度場を作り、自由流より遅い所を橙、速い所を青で塗る。上流だけの当てはめで推定した障害物の輪郭"
                          "(水色の輪)と衝突点(桃色の×)が浮かび上がる。最後の 8 コマで真の障害物を白の破線で重ねる(半径は 1 割ほど小さめに"
                          "出る —— 群れの流れは厳密なポテンシャル流ではないため)。" % sim["n_agents"])
    return hist


def figures(out):
    t0 = time.time()
    _gif(out)
    # 2. 速さの変化の地図 4 枚(同じ縮尺 80 px/m、最近傍で表示の格子へ —— 縮尺が違うと円が別の大きさに見える)
    panels, caps = [], []
    for name, f in (("closed form", out["pf_field"]), ("PIV (particle video)", out["piv"][0]), ("tracking (particle video)", out["track"][0]),
                    ("swarm, tracking (hole = no agents)", out["sims"]["obstacle"]["field"])):
        U = 1.0 if name == "closed form" else S.velocity_deficit_map(f)["speed"]
        x, y = f["x"], f["y"]
        dx, dy = abs(x[1] - x[0]), abs(y[1] - y[0])
        W, H = int(round((x[-1] - x[0] + dx) * 80)), int(round((y[0] - y[-1] + dy) * 80))
        wx = x[0] - dx / 2 + (np.arange(W) + 0.5) / 80
        wy = y[0] + dy / 2 - (np.arange(H) + 0.5) / 80
        jx = np.clip(np.round((wx - x[0]) / dx).astype(int), 0, len(x) - 1)
        iy = np.clip(np.round((y[0] - wy) / dy).astype(int), 0, len(y) - 1)
        rel = f["u"][np.ix_(iy, jx)] / U - 1.0
        panels.append(np.clip(np.nan_to_num(rel), -0.8, 0.8))
        caps.append(name)
    figs.save_grid("swarmflow_speed_change_maps", panels, captions=caps, ncols=2, signed=True,
                   caption="自由流からの速さの変化 u/U − 1(橙 = 遅くなった、青 = 速くなった、黒 = 0 か欠測)。同じ縮尺 80 px/m。閉形式、粒子の映像の PIV と"
                           "追跡、群れの模擬の追跡。群れは障害物の所に個体が入れない穴が開き、その後ろに長い空洞が伸びる(欠測)。上流の橙の扇だけがポテンシャル流"
                           "に近く、推定はそこを使う。穴そのものも障害物の手がかりだが、推定は穴を使わない(速度だけ)。")
    # 3. 中心線の直線化(閉形式・PIV・群れ)
    f = out["pf_field"]
    c = out["centerline"]
    xl = np.linspace(-3.0, CYL[0] - CYL[2], 50)
    series = [("closed form (x_c - x)/R", xl, (CYL[0] - xl) / CYL[2])]
    kinds, styles, colors = ["line"], ["dashed"], ["reference"]
    for name, ff, cyl, col in (("potential flow field", f, CYL, "emphasis"), ("PIV of the particle video", out["piv"][0], CYL, "neutral"),
                               ("swarm (tracking), x shifted to the same wall", out["sims"]["obstacle"]["field"], SW_CYL, "wrong")):
        U = 1.0 if ff is f else S.obstacle_fit_doublet(ff, upstream_only=True)["speed"]
        fi = (cyl[1] - ff["y"][0]) / (ff["y"][1] - ff["y"][0])
        i0 = int(np.clip(np.floor(fi), 0, len(ff["y"]) - 2))
        t_ = fi - i0
        d = 1.0 - ((1 - t_) * ff["u"][i0] + t_ * ff["u"][i0 + 1]) / U
        xs = ff["x"] - cyl[0] + CYL[0]
        sel = np.isfinite(d) & (xs < CYL[0] - CYL[2]) & (d > 0.02)
        series.append((name, xs[sel], 1 / np.sqrt(d[sel])))
        kinds.append("scatter")
        styles.append(None)
        colors.append(col)
    figs.save_plot("swarmflow_centerline_linearised", series, xlabel="x [m] (flow from left, wall at -0.30)", ylabel="1 / sqrt(1 - u/U)",
                   title="The deficit straightens into a line; where it reaches 1 is the impact point",
                   kinds=kinds, styles=styles, colors=colors, size=(640, 400),
                   caption="中心線の上の欠損 d = R²/(x − x_c)² は 1/√d にすると直線になり(傾き −1/R)、1/√d = 1 の所がよどみ点(衝突点)。閉形式の場から読んだ値: "
                           "中心 x %.4f m・半径 %.4f m(真 %.3f・%.3f)。PIV の点は壁の近くで直線に乗り、遠くでは欠損が速さの雑音に埋もれて上へ散る(1/√d は小さな d の"
                           "雑音を増やす —— 推定が重み d^{3/2} を掛ける理由)。群れ(赤)は壁の近くで直線に乗るが、遠くでは直線より上(欠損が速く消える)で、"
                           "x < −3 では平らになる(周期の箱の端)。2 次元の当てはめがこの遠くの小さな欠損に引かれて、半径が 1 割ほど小さく出る。" % (c["center"][0], c["radius"], CYL[0], CYL[2]))
    # 4. 密度と誤差
    dens = out["density"]
    rs = np.array([CYL[2] / r_["spacing"] for r_ in dens])
    figs.save_plot("swarmflow_density_limit",
                   [("tracking: radius error", rs, np.array([abs(r_["track"][1]) for r_ in dens])),
                    ("PIV: radius error", rs, np.array([abs(r_["piv"][1]) for r_ in dens])),
                    ("tracking: velocity rms / U", rs, np.array([r_["track_err"] for r_ in dens])),
                    ("PIV: velocity rms / U", rs, np.array([r_["piv_err"] for r_ in dens]))],
                   xlabel="obstacle radius / agent spacing", ylabel="error (fraction)", title="How sparse can the swarm be?",
                   kinds=["scatter", "scatter", "line", "line"], styles=[None, None, "dashed", "dotted"],
                   colors=["emphasis", "neutral", "emphasis", "neutral"],
                   caption="個体を減らすと間隔 s が広がる。追跡は R/s ≈ 2 まで半径を数 %% で当て、それより疎になると外れる(op は R < 2s で「ある」と言わない)。"
                           "PIV は窓の中の個体が減ると速度の誤差が増える。密な側では追跡が取り違え(1 コマの移動が間隔に近づく)で悪くなる。")
    # 5. ダム崩壊
    db = out["dam"]
    series, kinds, styles, colors = [], [], [], []
    for k in (1, 3):
        t = db["t"][k]
        xx = np.linspace(-1.0, 0.5, 600)
        rr = S.ritter_dam_break(xx, t, 0.1)
        series += [("SPH t = %.2f s" % t, db["x"][k][::3], db["h"][k][::3] * 100), ("Ritter t = %.2f s" % t, xx, rr["h"] * 100)]
        kinds += ["scatter", "line"]
        styles += [None, "dashed"]
        colors += ["emphasis" if k == 3 else "neutral", "reference"]
    figs.save_plot("swarmflow_dam_break_ritter", series, xlabel="x [m] (gate at 0)", ylabel="depth h [cm]",
                   title="Releasing the swarm: SPH shallow water vs Ritter", kinds=kinds, styles=styles, colors=colors, size=(640, 380),
                   caption="ゲートを開けた群れの広がりの模型(1 次元 SPH の浅水、400 粒子)。扇の形は Ritter の解に重なる。先端は Ritter の 2√(g h₀) t に"
                           "届かず手前で止まって見えるが、それは粒子 1 個の量 m の所(先端から (27 g t² m/2)^{1/3})で、式どおりの遅れ。")
    print("  図: %s(%.1f s)" % (figs.errors() or "ok", time.time() - t0))


def main() -> int:
    t_all, c_all = time.time(), time.process_time()
    out = run()
    if figs.enabled():
        figures(out)
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    n_ng = sum(1 for _, ok in _GATES if not ok)
    print("gates: %d / %d ok  (%.1f s、この過程の CPU %.1f s)" % (len(_GATES) - n_ng, len(_GATES), time.time() - t_all, time.process_time() - c_all))
    if n_ng or figs.errors():
        print("FAIL")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
