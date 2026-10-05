# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""roverslip の門(Bekker / Wong–Reece → 斜面の滑り → 実滑り率 → 不確かさ → CVaR のコスト地図 → 経路)。

numpy だけの門(常に走る):
 1. Bekker の圧力: z = 0 で 0、単調、手計算の値
 2. 閉形式の恒等式(後側の接地なし): τ = 0 で DP = −b k z^(n+1)/(n+1)(n = 0.6・1・1.9)、n = 1 で F_z の閉形式、
    せん断が完全に動員されたとき T = r² b [c θ_f + tan φ · k r (sin θ_f − θ_f cos θ_f)](n = 1)
 3. Bekker の近似式: 放物線 + 厳密な I(n) は数値積分に収束(z/D → 0 で誤差 → 0)、教科書の (3 − n)/3 は n = 1 で一致し、
    n = 1.9 では沈下を 17 % 深く出す(罠)
 4. 沈下: 荷重について単調、F_z(wheel_sinkage(W)) = W
 5. 牽引–滑り曲線: 牽引は滑りとともに増え、上限 c·A + W tan φ の範囲、効率は [0, 1]
 6. 斜面 → 滑り: 登れる範囲で滑りは単調増加、剛な地面の極限で登れる最大の角 → atan(tan φ)
 7. 実滑り率: 解析的な模様(副画素の並進が厳密)のコマから並進を 0.05 px、滑り率を 0.01 以内
 8. 不確かさの被覆率(名目 90 %): 分位点回帰 + 共形の補正は 6 通りの種の平均で 86〜94 %、ガウス過程は全体では
    近くても急斜面で足りず緩斜面で広すぎる(異分散の罠)
 9. CVaR: ガウス過程の α = 0 は平均、α について単調、閉形式 = モンテカルロ、分位点回帰の CVaR は二峰の真値の CVaR に近い
10. ガウス過程の外挿の罠: データの外で事前の平均に戻り急斜面ほど滑らないと答える → 既定(extrapolate=False)で通さない
11. 経路: α = 0 の CVaR 経路 = 平均の経路、Dijkstra の合計 = 辺の和、対称な格子で既存の algo.graph_dijkstra と一致
12. 差が出る場面と出ない場面(否定の門は両側): 12° の斜面に崩れる殻の土 → 平均は殻を突っ切り CVaR は避ける /
    平らなら同じ経路
13. 「走った」でなく中身: 曲線・地図が有限・非定数・空でない
14. 既存 op を被験者に: filters_freq.phase_correlation_fft(整数の並進)、flow.optical_flow_lk(平均の流れ)、
    terrain.slope_map(傾き)(worktree が import できなければ skip)
15. 綴り壊しと壊れた入力は ValueError
16. 入口: __all__ が実在、docstring に Markdown のリンク記法なし、ソースに acos / asin の呼び出しなし
物理シミュレータの門(mujoco が無ければ skip):
17. 剛な地面では Wong–Reece の極限と MuJoCo の剛体の車輪が一致(滑り < 0.05、限界の角の差 < 0.75°)、
    乾いた砂では一致しない(20° の滑りの差 > 0.15、限界の角の差 > 5°)
実データの門(環境変数 FULLSEYE_ROVERSLIP_DATA が無ければ skip):
18. HiRISE の DTM の切り出し: SHA-256、標高がラベルの有効範囲、傾きの分布、その上で CVaR 経路の CVaR 時間 ≤ 平均の経路
"""
from __future__ import annotations

import hashlib
import inspect
import math
import os
import re
from pathlib import Path

import numpy as np
import pytest

import roverslip as R

WHEEL = {"r": 0.15, "b": 0.12}
MASS, NW = 50.0, 4
FRONT = dict(R.SOILS["dry_sand"], a0=0.0, a1=0.0, b0=0.0, b1=0.0)


def _raises(fn, *a, **k):
    try:
        fn(*a, **k)
    except ValueError:
        return True
    return False


_SAND = {}


def _sand_truth():
    """乾いた砂の定常の滑りの曲線(Wong–Reece)を 1 回だけ作り、内挿の関数を返す(登れない角は 1)。"""
    if "f" not in _SAND:
        grid = np.linspace(-30, 30, 61)
        sc = R.slope_slip_curve(grid, WHEEL, "dry_sand", mass=MASS, n_wheels=NW)
        ok = sc["feasible"]
        g, s = grid[ok], sc["slip"][ok]
        _SAND["f"] = lambda x: np.interp(x, g, s, right=1.0)
        _SAND["max"] = sc["max_slope"]
    return _SAND["f"]


def _sample(rng, n):
    u = rng.random(n) < 0.5
    return np.where(u, rng.uniform(-20, 24, n), np.clip(rng.normal(2, 9, n), -20, 24))


def _obs_sand(x, rng):
    return _sand_truth()(x) + rng.normal(0, 1, x.size) * (0.015 + 0.004 * np.abs(x))


def _obs_crust(x, rng):
    """崩れる殻(仮想の土): 85 % は砂の 0.3 倍しか滑らず、15 % は踏み抜いて砂より 0.03|θ| 多く滑る(二峰)。"""
    br = rng.random(x.size) < 0.15
    s = _sand_truth()(x)
    return np.where(br, s + 0.03 * np.abs(x), 0.3 * s) + rng.normal(0, 0.015, x.size)


def _worktree():
    """被験者の既存モジュール。repo の中では必ず import できる —— 失敗を skip に変えない(黙って門を外さない)。"""
    import importlib
    return {m: importlib.import_module(m) for m in ("filters_freq", "flow", "terrain", "algo")}


# ======================================================================================================================
def test_01_bekker_pressure():
    S = R.SOILS["dry_sand"]
    z = np.linspace(0, 0.05, 11)
    p = R.bekker_pressure(z, 0.12, "dry_sand")
    assert p[0] == 0 and np.all(np.diff(p) > 0)
    k = S["kc"] / 0.12 + S["kphi"]
    assert math.isclose(float(R.bekker_pressure(0.02, 0.12, "dry_sand")), k * 0.02 ** S["n"], rel_tol=1e-12)


def test_02_closed_form_identities():
    r, b = WHEEL["r"], WHEEL["b"]
    for n in (0.6, 1.0, 1.9):
        S = dict(FRONT, n=n, c=0.0, phi=0.0)
        z = 0.012
        f = R.wheel_forces(z, 0.3, WHEEL, S)
        k = (S["kc"] / b + S["kphi"]) * 1e3
        Rc = b * k * z ** (n + 1) / (n + 1)
        assert abs(f["DP"] / -Rc - 1) < 1e-6, (n, f["DP"], -Rc)
    S = dict(FRONT, n=1.0, c=0.0, phi=0.0)
    f = R.wheel_forces(0.02, 0.0, WHEEL, S)
    tf = f["theta_f"]
    k = (S["kc"] / b + S["kphi"]) * 1e3
    assert math.isclose(f["Fz"], b * k * r * r * (tf - math.sin(tf) * math.cos(tf)) / 2, rel_tol=1e-9)
    assert math.isclose(math.cos(tf), 1 - 0.02 / r, rel_tol=1e-12)        # 進入角の atan2 = cos θ_f = 1 − z/r
    S = dict(FRONT, n=1.0, K=1e-9)                                       # せん断を完全に動員
    f = R.wheel_forces(0.02, 0.5, WHEEL, S)
    tf = f["theta_f"]
    k = (S["kc"] / b + S["kphi"]) * 1e3
    T = r * r * b * (S["c"] * 1e3 * tf + math.tan(math.radians(S["phi"])) * k * r * (math.sin(tf) - tf * math.cos(tf)))
    assert abs(f["T"] / T - 1) < 1e-6, (f["T"], T)


def test_03_bekker_approximation_and_its_trap():
    for n in (0.6, 1.0, 1.9):
        S = dict(FRONT, n=n, c=0.0, phi=0.0)
        errs = []
        for W in (0.5, 5.0, 50.0):
            zn = float(R.wheel_sinkage(W, WHEEL, S))
            errs.append(abs(R.bekker_wheel_sinkage(W, WHEEL, S, "parabolic") / zn - 1))
        assert errs[0] < 0.002 and errs[0] < errs[1] < errs[2], (n, errs)
    S1 = dict(FRONT, n=1.0)
    assert math.isclose(R.bekker_wheel_sinkage(20, WHEEL, S1), R.bekker_wheel_sinkage(20, WHEEL, S1, "parabolic"), rel_tol=1e-12)
    S19 = dict(FRONT, n=1.9)
    ratio = R.bekker_wheel_sinkage(5, WHEEL, S19) / R.bekker_wheel_sinkage(5, WHEEL, S19, "parabolic")
    I = math.sqrt(math.pi) * math.gamma(2.9) / (2 * math.gamma(3.4))
    assert math.isclose(ratio, (I / ((3 - 1.9) / 3)) ** (2 / 4.8), rel_tol=1e-12) and ratio > 1.15


def test_04_sinkage():
    W = np.array([10.0, 30.0, 60.0, 120.0])
    z = R.wheel_sinkage(W, WHEEL, "dry_sand")
    assert np.all(np.diff(z) > 0)
    f = R.wheel_forces(z, 0.0, WHEEL, "dry_sand")
    assert np.allclose(f["Fz"], W, rtol=1e-6)
    assert _raises(R.wheel_sinkage, 1e6, WHEEL, "dry_sand")             # 半径まで沈んでも支えられない


def test_05_traction_curve():
    W = MASS * 3.72 / NW
    c = R.wheel_traction_curve(W, WHEEL, "dry_sand", np.linspace(0, 0.6, 25))
    assert np.all(np.diff(c["DP"]) > 0)
    S = R.SOILS["dry_sand"]
    tf = np.arctan2(np.sqrt(c["sinkage"] * (2 * 0.15 - c["sinkage"])), 0.15 - c["sinkage"])
    A = 0.12 * 0.15 * (tf - S["b0"] * tf)                                 # 接地の弧の面積(上限の見積もり)
    assert np.all(c["DP"] < S["c"] * 1e3 * A + W * math.tan(math.radians(S["phi"])) * 1.2)
    assert np.all((c["efficiency"] >= 0) & (c["efficiency"] <= 1))


def test_06_slope_slip_curve():
    f = _sand_truth()
    sc = R.slope_slip_curve(np.arange(-20, 26, 2.0), WHEEL, "dry_sand", mass=MASS, n_wheels=NW)
    s = sc["slip"][sc["feasible"]]
    assert np.all(np.diff(s) > 0) and 18 < _SAND["max"] < 30
    assert abs(f(10.0) - sc["slip"][15]) < 1e-3
    rg = R.slope_slip_curve(np.arange(20, 30, 0.25), WHEEL, "rigid_ground", mass=MASS, n_wheels=NW)
    assert abs(rg["max_slope"] - math.degrees(math.atan(0.5))) < 0.5, rg["max_slope"]


def _texture(shape, off_r, off_c, seed=3):
    """解析的な模様(帯域制限した正弦波 120 本の和)を (off_r, off_c) だけずらして標本化する(補間の誤差なし)。"""
    rng = np.random.default_rng(seed)
    f = rng.uniform(-0.2, 0.2, (120, 2))
    ph = rng.uniform(0, 2 * np.pi, 120)
    a = rng.uniform(0.3, 1.0, 120) / (1 + 20 * np.hypot(f[:, 0], f[:, 1]))
    i, j = np.mgrid[0:shape[0], 0:shape[1]].astype(float)
    img = np.zeros(shape)
    for k in range(120):
        img += a[k] * np.cos(2 * np.pi * (f[k, 0] * (i + off_r) + f[k, 1] * (j + off_c)) + ph[k])
    return img


def test_07_visual_odometry_slip():
    px, r, dphi = 0.002, 0.15, 0.05
    for s_true in (0.0, 0.2, 0.5):
        step = (1 - s_true) * r * dphi / px                               # 1 コマの移動 [px]
        frames = [_texture((64, 64), 0.3 * t, step * t) for t in range(8)]
        tr = R.ground_shift_track(frames, px)
        # 模様を +off で標本化 = 像の中では模様が −off へ動く(カメラが +off へ進む)
        assert np.max(np.abs(-tr["step"][:, 1] / px - step)) < 0.05, (s_true, tr["step"][:, 1] / px, step)
        assert np.max(np.abs(-tr["step"][:, 0] / px - 0.3)) < 0.05
        ang = dphi * np.arange(8)
        od = R.odometry_slip(-tr["position"][:, 1], ang, r, window=2)
        assert abs(od["slip_total"] - s_true) < 0.01 and np.nanmax(np.abs(od["slip"] - s_true)) < 0.02


def test_08_coverage_quantile_vs_gp():
    cov_q, cov_g, steep_g, gentle_g, steep_q = [], [], [], [], []
    for seed in range(6):
        rng = np.random.default_rng(seed)
        x = _sample(rng, 200)
        y = _obs_sand(x, rng)
        xt = _sample(rng, 3000)
        yt = _obs_sand(xt, rng)
        for kind, m in (("q", R.slip_quantile_fit(x, y)), ("g", R.slip_gp_fit(x, y))):
            p = R.slip_predict(m, xt, 0.9)
            inb = (yt >= p["lower"]) & (yt <= p["upper"])
            st, ge = inb[xt >= 8].mean(), inb[(xt > -5) & (xt < 8)].mean()
            if kind == "q":
                cov_q.append(inb.mean())
                steep_q.append(st)
            else:
                cov_g.append(inb.mean())
                steep_g.append(st)
                gentle_g.append(ge)
    # 閾値は種を 144 通り振って決めた(2026-10-06): 1 種あたりの被覆は平均 0.898・標準偏差 0.045・最小 0.753。元の門(平均 0.87〜0.95・
    # 最小 0.80)は 6 種の組 12 通りのうち 3 通りで落ちた(どれも最小の側)。6 種の平均の標準偏差は約 0.018 なので平均は ±3σ の
    # [0.86, 0.94]、1 種の最小は 0.72(約 −4σ)。24 組とも通る(平均 0.874〜0.923、最小 0.746)
    assert 0.86 <= np.mean(cov_q) <= 0.94 and min(cov_q) >= 0.72, cov_q
    assert 0.83 <= np.mean(steep_q) <= 0.97, steep_q
    assert np.mean(steep_g) < 0.85 and np.mean(gentle_g) > 0.97, (steep_g, gentle_g)


def test_09_cvar():
    rng = np.random.default_rng(0)
    x = _sample(rng, 200)
    gp = R.slip_gp_fit(x, _obs_sand(x, rng))
    xx = np.array([0.0, 10.0, 20.0])
    pred = R.slip_predict(gp, xx)
    assert np.allclose(R.slip_cvar(gp, xx, 0.0), pred["mean"])
    c = np.array([R.slip_cvar(gp, xx, a) for a in (0.0, 0.5, 0.8, 0.9, 0.95)])
    assert np.all(np.diff(c, axis=0) > 0)
    z = pred["mean"][2] + pred["std"][2] * np.random.default_rng(1).standard_normal(400000)
    q = np.quantile(z, 0.9)
    assert abs(z[z >= q].mean() / R.slip_cvar(gp, xx, 0.9)[2] - 1) < 0.01
    xc = rng.uniform(-20, 24, 400)
    qr = R.slip_quantile_fit(xc, _obs_crust(xc, rng))
    zt = _obs_crust(np.full(400000, 12.0), np.random.default_rng(2))
    qt = np.quantile(zt, 0.9)
    true_cvar = zt[zt >= qt].mean()
    assert abs(R.slip_cvar(qr, np.array([12.0]), 0.9)[0] - true_cvar) < 0.06, (R.slip_cvar(qr, np.array([12.0]), 0.9), true_cvar)
    assert np.allclose(R.slip_cvar(gp, xx, 0.9, sign=-1.0), -pred["mean"] + (R.slip_cvar(gp, xx, 0.9) - pred["mean"]))


def test_10_gp_extrapolation_trap():
    rng = np.random.default_rng(1)
    x = _sample(rng, 200)
    gp = R.slip_gp_fit(x, _obs_sand(x, rng))
    hi = gp["x_range"][1]
    m = R.slip_predict(gp, np.array([hi - 2, hi + 10.0]))["mean"]
    assert _sand_truth()(hi + 10) == 1.0 and m[1] < 0.6, m              # 真は立ち往生、GP は「滑らない」寄り
    Z = np.add.outer(np.zeros(12), np.arange(12) * math.tan(math.radians(30.0)))
    cm = R.cvar_cost_map(Z, 1.0, gp, alpha=0.9)
    assert np.all(~np.isfinite(cm["cost"][2][:, :-1]))                   # 30° の登り(東向き)は通さない
    cm2 = R.cvar_cost_map(Z, 1.0, gp, alpha=0.9, extrapolate=True)
    assert np.all(np.isfinite(cm2["cost"][2][:, :-1]))                   # 外挿させると通ってしまう(罠)


def _two_soil_models(kind="q", seed=1):
    rng = np.random.default_rng(seed)
    xs, xc = rng.uniform(-20, 24, 300), rng.uniform(-20, 24, 300)
    fit = R.slip_quantile_fit if kind == "q" else R.slip_gp_fit
    return [fit(xs, _obs_sand(xs, rng)), fit(xc, _obs_crust(xc, rng))]


def test_11_paths_identities_and_existing_dijkstra():
    rng = np.random.default_rng(4)
    x = _sample(rng, 200)
    qr = R.slip_quantile_fit(x, _obs_sand(x, rng))
    i, j = np.mgrid[0:40, 0:40]
    Z = 3.0 * np.exp(-((i - 20) ** 2 + (j - 18) ** 2) / 60.0)
    c0 = R.cvar_cost_map(Z, 1.0, qr, alpha=0.0)
    p0 = R.risk_aware_path(c0, (2, 2), (37, 37))
    # 辺の和 = 合計
    tot = sum(c0["cost"][int(np.where((R._OFFS == b - a).all(1))[0][0]), a[0], a[1]] for a, b in zip(p0["path"][:-1], p0["path"][1:]))
    assert math.isclose(tot, p0["cost"], rel_tol=1e-12)
    wt = _worktree()
    # 対称な格子(平ら・一様な辺の重み = 長さ)で既存の algo.graph_dijkstra と距離が一致
    n = 9
    Zf = np.zeros((n, n))
    cm = R.cvar_cost_map(Zf, 1.0, qr, alpha=0.0, speed=1.0)
    w = cm["cost"]
    edges = []
    for a in range(n):
        for b in range(n):
            for k in (1, 2, 3, 4):                                         # 半分の向きだけ(無向)
                da, db = R._OFFS[k]
                if 0 <= a + da < n and 0 <= b + db < n:
                    edges += [a * n + b, (a + da) * n + (b + db), w[k, a, b]]
    dist = wt["algo"].py_fn("graph_dijkstra")([float(n * n), float(len(edges) // 3), 0.0] + [float(e) for e in edges])
    ours = R.risk_aware_path(cm, (0, 0), (n - 1, n - 1))["cost_to_come"].ravel()
    assert np.allclose(ours, dist, rtol=1e-12)


def test_12_paths_differ_only_where_risk_differs():
    H = W = 48
    i, j = np.mgrid[0:H, 0:W]
    soil = np.zeros((H, W), dtype=np.int64)
    soil[(i >= 10) & (i <= 38) & (j >= 16) & (j <= 32)] = 1
    for kind in ("q", "g"):
        models = _two_soil_models(kind)
        for incl, should_differ in ((12.0, True), (0.0, False)):
            Z = ((H - 1 - i) * math.tan(math.radians(incl))).astype(float)
            paths = {}
            for a in (0.0, 0.9):
                cm = R.cvar_cost_map(Z, 1.0, models, alpha=a, s_max=0.6, soil_map=soil)
                paths[a] = R.risk_aware_path(cm, (45, 24), (2, 24))["path"]
            crust = [int(sum(soil[tuple(q)] for q in paths[a])) for a in (0.0, 0.9)]
            if should_differ and kind == "q":
                assert crust[0] >= 20 and crust[1] <= 3, (kind, incl, crust)
            elif not should_differ:
                assert np.array_equal(paths[0.0], paths[0.9]), (kind, incl, crust)
    # ガウス過程(一様な雑音)は二峰の殻の尾を薄く見積もる: 12° の CVaR が真値より 0.05 以上低く、0° では高すぎる
    gp_crust = _two_soil_models("g")[1]
    zt = _obs_crust(np.full(400000, 12.0), np.random.default_rng(5))
    z0 = _obs_crust(np.full(400000, 0.0), np.random.default_rng(6))
    tv = [z[z >= np.quantile(z, 0.9)].mean() for z in (z0, zt)]
    gv = R.slip_cvar(gp_crust, np.array([0.0, 12.0]), 0.9)
    assert gv[1] < tv[1] - 0.05 and gv[0] > tv[0] + 0.05, (gv, tv)


def test_13_content_not_just_ran():
    c = R.wheel_traction_curve(40.0, WHEEL, "mars_simulant_m90")
    for k in ("DP", "T", "sinkage"):
        assert np.all(np.isfinite(c[k])) and np.ptp(c[k]) > 0
    rng = np.random.default_rng(0)
    x = _sample(rng, 120)
    qr = R.slip_quantile_fit(x, _obs_sand(x, rng))
    i, j = np.mgrid[0:30, 0:30]
    cm = R.cvar_cost_map(np.sin(i / 5.0) * np.cos(j / 7.0) * 2.0, 1.0, qr)
    inner = cm["cost"][:, 1:-1, 1:-1]
    assert np.isfinite(inner).mean() > 0.9 and np.ptp(inner[np.isfinite(inner)]) > 0
    assert np.isfinite(cm["worst_slip"]).all() and np.ptp(cm["worst_slip"]) > 0


def test_14_existing_ops_as_subjects():
    wt = _worktree()
    a = _texture((64, 64), 0.0, 0.0)
    # 周期的なずれ(np.roll)では既存の位相相関は厳密(符号の約束が逆: image1 の image2 に対するずれ)
    b = np.roll(a, (2, 5), axis=(0, 1))
    pc = wt["filters_freq"].phase_correlation_fft(a, b)
    ours = R.ground_shift_track([a, b])["step"][0]
    assert (pc["row_shift"], pc["col_shift"]) == (-2.0, -5.0) and np.allclose(ours, [2.0, 5.0], atol=0.05)
    # 窓のない全白色化の位相相関は、地面のカメラのような周期的でない切り出しでは縁の不連続に負けて 0 付近を返す(罠、
    # 試作の測りで (1, 0)。真は (−2, −5))
    b2 = _texture((64, 64), -2.0, -5.0)
    pc2 = wt["filters_freq"].phase_correlation_fft(a, b2)
    ours2 = R.ground_shift_track([a, b2])["step"][0]
    assert max(abs(pc2["row_shift"] + 2), abs(pc2["col_shift"] + 5)) >= 2 and np.allclose(ours2, [2.0, 5.0], atol=0.05)
    an = (a - a.min()) / np.ptp(a)
    bn = (b2 - a.min()) / np.ptp(a)
    u, v = wt["flow"].optical_flow_lk(an, bn)
    c = (slice(16, 48), slice(16, 48))
    assert abs(np.median(u[c]) - ours2[1]) < 0.1 and abs(np.median(v[c]) - ours2[0]) < 0.1
    i, j = np.mgrid[0:20, 0:20]
    Z = j * math.tan(math.radians(15.0)) * 0.5
    sl = wt["terrain"].slope_map(Z, cell=0.5)
    cm = R.cvar_cost_map(Z, 0.5, R.slip_quantile_fit(*_xy_small()), alpha=0.0, extrapolate=True)
    assert np.allclose(sl[5:15, 5:15], 15.0, atol=1e-9) and np.allclose(cm["pitch"][2][5:15, 5:15], 15.0, atol=1e-9)


def _xy_small():
    rng = np.random.default_rng(7)
    x = _sample(rng, 80)
    return x, _obs_sand(x, rng)


def test_15_bad_inputs():
    assert _raises(R.bekker_pressure, 0.01, 0.12, "dry-sand")
    assert _raises(R.bekker_pressure, -0.01, 0.12, "dry_sand")
    assert _raises(R.wheel_forces, 0.2, 0.1, WHEEL, "dry_sand")           # z ≥ r
    assert _raises(R.wheel_forces, 0.01, 1.0, WHEEL, "dry_sand")
    assert _raises(R.wheel_forces, 0.01, 0.1, {"r": 0.1}, "dry_sand")
    assert _raises(R.bekker_wheel_sinkage, 10, WHEEL, "dry_sand", "clasic")
    assert _raises(R.slope_slip_curve, [10.0, np.nan], WHEEL, "dry_sand", 50.0)
    assert _raises(R.ground_shift_track, np.ones((3, 16, 16)))
    assert _raises(R.odometry_slip, np.zeros(5), np.zeros(5), 0.1)
    assert _raises(R.slip_gp_fit, [1.0, 1.0, 1.0], [0.1, 0.2, 0.3])
    assert _raises(R.slip_quantile_fit, np.arange(10.0), np.arange(9.0))
    assert _raises(R.slip_predict, {"kind": "gq"}, [1.0])
    assert _raises(R.slip_cvar, R.slip_quantile_fit(*_xy_small()), [1.0], 1.0)
    assert _raises(R.cvar_cost_map, np.zeros((5, 5)), 1.0, [R.slip_quantile_fit(*_xy_small())] * 2)
    assert _raises(R.risk_aware_path, {"cost": np.zeros((8, 4, 4))}, (0, 0), (9, 9))
    assert _raises(R.path_slip_risk, [[0, 0], [2, 2]], np.zeros((4, 4)), 1.0, R.slip_quantile_fit(*_xy_small()))


def test_16_entry_points():
    for name in R.__all__:
        assert hasattr(R, name), name
    src = inspect.getsource(R)
    assert "](" not in src.replace("]((", "")                            # docstring に Markdown のリンク記法なし
    assert not re.search(r"\b(np\.|math\.)?(arccos|arcsin|acos|asin)\(", src)


def test_17_mujoco_agreement_and_disagreement():
    pytest.importorskip("mujoco")
    sl = np.arange(0, 22, 4.0)
    mj = R._mujoco_slope_slip(sl, 0.5, WHEEL["r"], WHEEL["b"], MASS / NW)
    rg = R.slope_slip_curve(sl, WHEEL, "rigid_ground", mass=MASS, n_wheels=NW)
    assert np.all(np.abs(mj) < 0.05) and np.all(np.abs(rg["slip"]) < 0.05), (mj, rg["slip"])
    fine = np.arange(24.0, 28.01, 0.25)
    mjf = R._mujoco_slope_slip(fine, 0.5, WHEEL["r"], WHEEL["b"], MASS / NW)
    rgf = R.slope_slip_curve(fine, WHEEL, "rigid_ground", mass=MASS, n_wheels=NW)

    def cross(x, s, lvl=0.5):
        s = np.where(np.isfinite(s), s, 9.0)
        k = int(np.argmax(s >= lvl))
        return x[k - 1] + (x[k] - x[k - 1]) * (lvl - s[k - 1]) / (s[k] - s[k - 1])

    assert abs(cross(fine, mjf) - rgf["max_slope"]) < 0.75, (cross(fine, mjf), rgf["max_slope"])
    mu = math.tan(math.radians(R.SOILS["dry_sand"]["phi"]))
    mjs = R._mujoco_slope_slip(np.array([20.0]), mu, WHEEL["r"], WHEEL["b"], MASS / NW)
    assert _sand_truth()(20.0) - mjs[0] > 0.15
    assert math.degrees(math.atan(mu)) - _SAND["max"] > 5


def _data_dir():
    d = os.environ.get("FULLSEYE_ROVERSLIP_DATA", "").strip()
    return Path(d) if d and (Path(d) / "PROVENANCE.md").is_file() else None


DTM_NAME = "balvicar_dtm_L10800_S3860_1024.npy"
DTM_SHA = "1f2c6b559f69ce016d3f81ae6162df1af1a03f52a689855632c734a44a3252b6"


def test_18_hirise_dtm():
    d = _data_dir()
    if d is None:
        pytest.skip("FULLSEYE_ROVERSLIP_DATA が無い")
    p = d / DTM_NAME
    assert hashlib.sha256(p.read_bytes()).hexdigest() == DTM_SHA
    Z = np.load(p).astype(np.float64)
    assert Z.shape == (1024, 1024) and np.all(np.isfinite(Z)) and Z.min() > -2690.91 and Z.max() < -1049.92
    D = Z.reshape(128, 8, 128, 8).mean((1, 3))
    cell = 0.88208367396075 * 8
    rng = np.random.default_rng(0)
    x = _sample(rng, 200)
    qr = R.slip_quantile_fit(x, _obs_sand(x, rng))
    ev = {}
    for a in (0.0, 0.9):
        cm = R.cvar_cost_map(D, cell, qr, alpha=a, s_max=0.6)
        pth = R.risk_aware_path(cm, (8, 8), (120, 20))
        assert pth["reached"]
        ev[a] = R.path_slip_risk(pth["path"], D, cell, qr, alpha=0.9, s_max=0.6)
    assert ev[0.9]["time_cvar"] <= ev[0.0]["time_cvar"] * (1 + 2e-3)
    assert ev[0.0]["time_mean"] <= ev[0.9]["time_mean"] * (1 + 2e-3)


# ======================================================================================================================
def test_19_usage_example_in_the_module_docstring_runs(capsys):
    """モジュール docstring の呼び出し例をそのまま実行する(説明のコード例は走らせる門が無いと静かに壊れる)。"""
    import textwrap
    doc = R.__doc__
    i = doc.index("呼び出し例")
    block = doc[doc.index("::", i) + 2:]
    lines = []
    for ln in block.splitlines()[1:]:
        if ln.strip() and not ln.startswith("    "):
            break
        lines.append(ln)
    code = textwrap.dedent("\n".join(lines))
    assert code.count("\n") >= 8 and "print(" in code
    exec(compile(code, "<roverslip usage>", "exec"), {})
    out = capsys.readouterr().out.strip()
    assert out and "nan" not in out.lower() and "inf" not in out.lower() and "True" in out
