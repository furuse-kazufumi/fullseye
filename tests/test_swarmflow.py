# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""swarmflow の門(流体のように流れる群れが、見えない障害物を速度場の乱れだけで察知する)。

numpy + scipy だけ(物理エンジンは使わない)。全部で数秒:
 1. SPH の核: ∫ W dV = 1(1・2・3 次元、数値の求積)、勾配 = 差分、台の外は 0
 2. 格子の密度 = ρ₀(内側)、圧力 = c²(ρ − ρ₀)
 3. 円柱まわりのポテンシャル流の閉形式: よどみ点 (x_c − R, y_c) で速さ 0、表面の速さ 2U|sin θ|、遠方で U
 4. 中心線の直線化(実装 1)がポテンシャル流の場で中心・半径を当てる(副格子の y_c も)
 5. 二重湧き出しの当てはめ(実装 2)が雑音つきの場で当てる、上流だけでも当てる
 6. 否定の門(両側): 障害物なし・渦・湧き出し → 検出しない、障害物あり → 検出する(説明できる割合が両側でしきい値から離れている)
 7. 粒子の映像 → PIV(pivops)の速度場の誤差、そこから障害物
 8. 粒子の映像 → 追跡(blob2d)の速度場の誤差、そこから障害物
 9. 密度を下げた限界: 個体の間隔が障害物の半径に近づくと検出が外れる(上と下の両方で確かめる)
10. 群れの模擬: 障害物ありで上流だけの当てはめが位置・半径を当て、障害物なしで検出しない
11. Ritter の解: 質量の保存、ダムの位置で 4h₀/9、SPH の浅水の扇の形と最も前の粒子の居場所
12. 綴り壊しは ValueError、出力が空・定数・inf でない
"""
from __future__ import annotations

import math

import numpy as np
import pytest

import swarmflow as S

CYL = (0.3, 0.123, 0.6)
RES, SHAPE = 0.015, (267, 400)


def _raises(fn, exc=ValueError):
    try:
        fn()
    except exc:
        return True
    return False


def _pf_frames(n_agents, n_frames, dt, seed=0, cyl=CYL):
    """一様に撒いた粒子をポテンシャル流で RK4 で運び、俯瞰のコマを作る(真値の速度は閉形式)。"""
    rng = np.random.default_rng(seed)
    p = np.column_stack([rng.uniform(-3.3, 3.3, n_agents), rng.uniform(-2.1, 2.1, n_agents)])
    if cyl is not None:
        p = p[np.hypot(p[:, 0] - cyl[0], p[:, 1] - cyl[1]) > cyl[2]]

    def vel(q):
        if cyl is None:
            return np.column_stack([np.ones(len(q)), np.zeros(len(q))])
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


def _field_err(field, cyl=CYL, margin=1.3):
    t = S.potential_flow_cylinder(field["x"], field["y"], cyl, 1.0, grid=True)
    X, Y = np.meshgrid(field["x"], field["y"])
    m = field["valid"] & t["valid"] & (np.hypot(X - cyl[0], Y - cyl[1]) > margin * cyl[2])
    e = np.hypot(field["u"] - t["u"], field["v"] - t["v"])[m]
    return float(np.sqrt(np.mean(e ** 2))), int(m.sum())


def _cerr(ob, cyl=CYL):
    return math.hypot(ob["center"][0] - cyl[0], ob["center"][1] - cyl[1]) / cyl[2], ob["radius"] / cyl[2] - 1.0


# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("dim", [1, 2, 3])
def test_kernel_normalisation_and_gradient(dim):
    from scipy.integrate import quad
    h = 0.7
    area = {1: 2.0, 2: 2.0 * math.pi, 3: 4.0 * math.pi}[dim]

    def f(r):
        return S.sph_kernel(np.array(r), h, dim=dim)[()] * area * r ** (dim - 1)

    total = quad(f, 0, h)[0] + quad(f, h, 2 * h)[0]
    assert abs(total - 1.0) < 1e-10                           # ∫ W dV = 1(恒等式)
    r = np.linspace(0.01, 2.2 * h, 300)
    fd = (S.sph_kernel(r + 1e-6, h, dim) - S.sph_kernel(r - 1e-6, h, dim)) / 2e-6
    assert np.max(np.abs(fd - S.sph_kernel(r, h, dim, derivative=True))) < 1e-5 * S.sph_kernel(0.0, h, dim)[()]
    assert np.all(S.sph_kernel(np.array([2 * h, 3 * h]), h, dim) == 0.0)
    assert np.all(S.sph_kernel(r, h, dim, derivative=True) <= 0.0)


def test_lattice_density_and_pressure():
    dx = 0.1
    g = np.mgrid[0:30, 0:30].reshape(2, -1).T * dx
    r = S.sph_density_pressure(g, 1.3 * dx, mass=dx * dx, rho0=1.0, c=10.0)
    inner = np.abs(g - 1.45).max(axis=1) < 0.8
    assert np.max(np.abs(r["rho"][inner] - 1.0)) < 3e-3
    assert np.allclose(r["p"], 100.0 * (r["rho"] - 1.0))
    edge = r["rho"][np.abs(g - 1.45).max(axis=1) > 1.4]
    assert edge.max() < 0.9                                   # 縁は核が欠けて薄い(群れの境界で圧力が下がる理由)
    per = S.sph_density_pressure(g, 1.3 * dx, mass=dx * dx, box=(3.0, 3.0))
    assert np.max(np.abs(per["rho"] - 1.0)) < 3e-3            # 周期境界なら縁も同じ


def test_potential_flow_closed_forms():
    xc, yc, R = CYL
    th = np.linspace(0.05, math.pi - 0.05, 50)
    xs, ys = xc + R * 1.0000001 * np.cos(th), yc + R * 1.0000001 * np.sin(th)
    r = S.potential_flow_cylinder(xs, ys, CYL, 1.5)
    assert np.max(np.abs(np.hypot(r["u"], r["v"]) - 2 * 1.5 * np.sin(th))) < 1e-5
    st = S.potential_flow_cylinder(np.array([xc - R - 1e-9]), np.array([yc]), CYL, 1.5)
    assert abs(st["u"][0]) < 1e-6 and st["stagnation"] == (xc - R, yc)
    far = S.potential_flow_cylinder(np.array([xc - 300.0]), np.array([yc]), CYL, 1.5)
    assert abs(far["u"][0] - 1.5) < 1e-5
    g = S.potential_flow_cylinder(np.linspace(-3, 3, 61), np.linspace(2, -2, 41), CYL, 1.0, grid=True)
    assert g["u"].shape == (41, 61) and g["valid"].sum() < g["valid"].size and np.isnan(g["u"][~g["valid"]]).all()
    # 点の列(同じ長さの 1 次元の x と y)を黙って格子にしない
    pts = S.potential_flow_cylinder(np.linspace(-3, 3, 41), np.linspace(2, -2, 41), CYL, 1.0)
    assert pts["u"].shape == (41,)


def test_centerline_linearisation_on_potential_flow():
    x, y = np.linspace(-3, 3, 121), np.linspace(2, -2, 81)
    f = S.potential_flow_cylinder(x, y, CYL, 1.0, grid=True)
    st = S.stagnation_from_centerline(f)
    assert st["ok"] and st["n_used"] >= 10
    ce, re_ = _cerr(st)
    assert ce < 5e-3 and abs(re_) < 5e-3                     # y_c = 0.123 は格子の間(行の間の 1 次補間、実測 3.0e-3)
    on = S.stagnation_from_centerline(S.potential_flow_cylinder(x, y, (0.3, 0.1, 0.6), 1.0, grid=True))
    assert max(abs(on["center"][0] - 0.3), abs(on["center"][1] - 0.1), abs(on["radius"] - 0.6)) < 1e-6   # 節点の上なら厳密
    assert abs(st["stagnation"][0] - (CYL[0] - CYL[2])) < 2e-3 and abs(st["speed"] - 1.0) < 1e-4
    st1 = S.stagnation_from_centerline(f, n_iter=1)           # U を上流の端の中央値のまま使う罠
    assert abs(_cerr(st1)[1]) > 0.1


def test_doublet_fit_noise_and_upstream_only():
    rng = np.random.default_rng(1)
    x, y = np.linspace(-3, 3, 61), np.linspace(2, -2, 41)
    f = S.potential_flow_cylinder(x, y, CYL, 1.0, grid=True)
    exact = S.obstacle_fit_doublet(f)
    assert max(map(abs, _cerr(exact))) < 1e-6 and exact["explained"] > 0.999999
    fn = dict(f, u=f["u"] + 0.05 * rng.normal(size=f["u"].shape), v=f["v"] + 0.05 * rng.normal(size=f["u"].shape))
    ob = S.obstacle_fit_doublet(fn)
    ce, re_ = _cerr(ob)
    assert ce < 0.02 and abs(re_) < 0.02 and ob["detected"]
    up = S.obstacle_fit_doublet(fn, upstream_only=True)
    ce, re_ = _cerr(up)
    assert ce < 0.06 and abs(re_) < 0.05 and up["detected"]
    assert np.all(np.isfinite([ob["rms_residual"], ob["rms_null"], up["speed"]]))


def test_negative_gate_both_sides():
    rng = np.random.default_rng(2)
    x, y = np.linspace(-3, 3, 61), np.linspace(2, -2, 41)
    expl_null, expl_obs = [], []
    for k in range(3):
        nz = 0.05 * rng.normal(size=(2, 41, 61))
        null = {"x": x, "y": y, "u": 1.0 + nz[0], "v": nz[1]}
        on = S.obstacle_fit_doublet(null)
        assert not on["detected"]
        expl_null.append(on["explained"])
        f = S.potential_flow_cylinder(x, y, (0.3 * k - 0.4, 0.2 * k - 0.3, 0.45), 1.0, grid=True)
        f["u"] = f["u"] + nz[0]
        f["v"] = f["v"] + nz[1]
        oo = S.obstacle_fit_doublet(f)
        assert oo["detected"]
        expl_obs.append(oo["explained"])
    th = 0.5
    assert max(expl_null) < 0.2 * th and min(expl_obs) > 1.4 * th    # しきい値が端で偶然に合っていない
    # 円柱でない形の乱れ(渦・湧き出し): 当てはめは半径の下限を超える R を返すが、説明できる割合が小さいので言わない
    # (この 2 つが無いと「説明できる割合」の条件は門で一度も効かない —— 雑音だけの場は R が小さくて先に落ちる)
    X, Y = np.meshgrid(x, y)
    r2 = np.maximum((X - 0.3) ** 2 + (Y - 0.1) ** 2, 0.09)
    for u, v in ((1 - 0.4 * (Y - 0.1) / r2, 0.4 * (X - 0.3) / r2), (1 + 0.4 * (X - 0.3) / r2, 0.4 * (Y - 0.1) / r2)):
        o = S.obstacle_fit_doublet({"x": x, "y": y, "u": u + 0.02 * rng.normal(size=u.shape), "v": v + 0.02 * rng.normal(size=u.shape)})
        assert o["radius"] >= o["min_radius"] and o["explained"] < 0.2 * th and not o["detected"]


def test_piv_field_from_particle_video():
    fr = _pf_frames(2400, 5, 0.03, seed=0)
    f = S.swarm_field_from_piv(fr, RES, 0.03, window=32, min_peak_ratio=1.2)
    e, n = _field_err(f)
    assert n > 250 and e < 0.03 and f["valid_fraction"] > 0.9
    ob = S.obstacle_fit_doublet(f)
    ce, re_ = _cerr(ob)
    assert ob["detected"] and ce < 0.02 and abs(re_) < 0.02


def test_track_field_from_particle_video():
    fr = _pf_frames(1200, 5, 0.015, seed=1)
    f = S.swarm_field_from_tracks(fr, RES, 0.015)
    e, n = _field_err(f)
    assert n > 1000 and e < 0.04 and f["n_linked"] > 2000
    ob = S.obstacle_fit_doublet(f)
    ce, re_ = _cerr(ob)
    assert ob["detected"] and ce < 0.02 and abs(re_) < 0.02
    assert f["n_outliers"] > 0                                # 取り違えは起きていて、検査で捨てている


def test_density_limit_both_sides():
    """個体の間隔 s と半径 R の比で限界が来る。追跡の格子は間隔 s ごとなので、R < 2s では op が「障害物あり」と言わない。
    その拒否が正当か(推定が本当に悪いか)を限界の向こう側で確かめ、こちら側では当たることを確かめる。"""
    res = {}
    for n in (600, 140, 35):
        f = S.swarm_field_from_tracks(_pf_frames(n, 4, 0.015, seed=3), RES, 0.015)
        res[n] = (f["spacing"], S.obstacle_fit_doublet(f))
    s600, o600 = res[600]
    s140, o140 = res[140]
    s35, o35 = res[35]
    assert CYL[2] / s600 > 4 and o600["detected"] and max(map(abs, _cerr(o600))) < 0.05
    assert 2 < CYL[2] / s140 < 3 and o140["detected"] and max(map(abs, _cerr(o140))) < 0.08
    assert CYL[2] / s35 < 1.5 and not o35["detected"]
    assert abs(_cerr(o35)[1]) > 0.25                         # 拒否は正当: 半径が 25 % 以上外れている


def test_swarm_simulation_upstream_detection():
    cyl = (0.2, 0.05, 0.5)
    res, shape = 0.02, (175, 300)
    out = {}
    # 障害物ありは 2 s 流して定常に近づける(1.0〜1.5 s では過渡で中心が 0.07〜0.32R ずれた。2 s で 0.03〜0.04R、種 2 つ)
    for name, obs, tw in (("obstacle", cyl, 2.0), ("none", None, 0.6)):
        sim = S.swarm_simulate(obs, box=(6.0, 3.5), spacing=0.15, t_warm=tw, n_frames=6, frame_dt=0.04, seed=4)
        fr = [S.swarm_render_overhead(p, shape, res, diameter_px=3.0) for p in sim["frames"]]
        f = S.swarm_field_from_tracks(fr, res, 0.04)
        g, _ = S._shepard(sim["frames"][:-1].reshape(-1, 2), sim["velocities"][:-1].reshape(-1, 2), f["x"], f["y"], f["spacing"], 3)
        m = f["valid"] & np.isfinite(g[..., 0])
        out[name] = (sim, f, float(np.sqrt(np.mean((f["u"] - g[..., 0])[m] ** 2 + (f["v"] - g[..., 1])[m] ** 2))))
    sim, f, e = out["obstacle"]
    assert e < 0.05                                          # 映像から測った速度 ≈ 個体の本当の速度
    assert 0.98 < sim["density_range"][0] and sim["density_range"][1] < 1.12   # 弱圧縮(密度の揺れ 12 % 以内)
    assert sim["t_total"] < sim["t_wake_reenters"]           # 後ろの空洞がまだ上流へ回り込んでいない
    ob = S.obstacle_fit_doublet(f, upstream_only=True)
    ce, re_ = _cerr(ob, cyl)
    assert ob["detected"] and ce < 0.1 and -0.25 < re_ < 0.0     # 群れの流れは厳密なポテンシャル流ではない(半径は 15 % 小さく出る)
    _, f0, e0 = out["none"]
    assert e0 < 0.05
    assert not S.obstacle_fit_doublet(f0)["detected"] and not S.obstacle_fit_doublet(f0, upstream_only=True)["detected"]


def test_ritter_and_sph_dam_break():
    x = np.linspace(-1.0, 1.0, 20001)
    r = S.ritter_dam_break(x, 0.2, 0.1)
    assert abs(np.trapezoid(r["h"], x) - 0.1 * 1.0) < 1e-6   # 質量の保存(x < 0 にあった h₀ × 1)
    assert abs(np.interp(0.0, x, r["h"]) - 4 * 0.1 / 9) < 1e-9
    assert r["front"] == pytest.approx(2 * math.sqrt(9.81 * 0.1) * 0.2)
    sph = S.sph_dam_break_1d(h0=0.1, length=1.0, n_particles=300, t_end=0.2, n_out=2)
    for k, t in enumerate(sph["t"]):
        xs, hs = sph["x"][k], sph["h"][k]
        rr = S.ritter_dam_break(xs, t, 0.1, particle_mass=0.1 / 300)
        fan = (xs > rr["rarefaction_head"]) & (xs < 0.7 * rr["front"])
        assert np.mean(np.abs(hs - rr["h"])[fan]) < 0.012 * 0.1
        assert abs(sph["front"][k] / rr["lead_particle"] - 1) < 0.06   # 最も前の粒子 = 先端から m/2 の所
        assert sph["front"][k] < 0.8 * rr["front"]                       # Ritter の先端そのものには届かない(罠)
    assert np.all(np.isfinite(sph["h"])) and np.ptp(sph["h"][-1]) > 0.05
    few = S.sph_dam_break_1d(n_particles=40, t_end=0.03, n_out=1)     # 回帰: 粒子が少なく鏡像の幅が全体を超えても落ちない
    assert np.all(np.isfinite(few["h"])) and abs(few["h"][0].max() - 0.1) < 0.01


def test_misuse_raises_and_outputs_are_meaningful():
    assert _raises(lambda: S.sph_kernel(1.0, 0.0))
    assert _raises(lambda: S.sph_kernel(-1.0, 1.0))
    assert _raises(lambda: S.sph_kernel(1.0, 1.0, dim=4))
    assert _raises(lambda: S.potential_flow_cylinder(0.0, 0.0, (0, 0, -1)))
    assert _raises(lambda: S.potential_flow_cylinder(np.zeros((2, 2)), np.zeros((2, 2)), (0, 0, 1), grid=True))
    assert _raises(lambda: S.swarm_render_overhead([[0, 0]], (4, 4), 0.1))
    assert _raises(lambda: S.swarm_field_from_tracks([np.zeros((20, 20))], 0.1, 0.1))
    assert _raises(lambda: S.velocity_deficit_map({"x": [0, 1, 2], "y": [0, 1, 2], "u": np.ones((3, 3))}))
    assert _raises(lambda: S.stagnation_from_centerline(S.potential_flow_cylinder(np.linspace(-3, 3, 9), np.linspace(2, -2, 7),
                                                                                  CYL, grid=True), d_range=(0.5, 0.2)))
    assert _raises(lambda: S.ritter_dam_break(0.0, 0.0, 0.1))
    assert _raises(lambda: S.sph_dam_break_1d(t_end=5.0))
    assert _raises(lambda: S.swarm_simulate((0, 0, 0.5), box=(0.5, 0.5)))
    img = S.swarm_render_overhead([[0.0, 0.0], [0.3, 0.1]], (40, 60), 0.02)
    assert np.isfinite(img).all() and np.ptp(img) > 0.5 and img.sum() > 0
    assert np.ptp(S.swarm_render_overhead(np.zeros((0, 2)), (40, 60), 0.02)) == 0.0
    d = S.velocity_deficit_map(S.potential_flow_cylinder(np.linspace(-3, 3, 31), np.linspace(2, -2, 21), CYL, grid=True), 1.0)
    fin = d["deficit"][np.isfinite(d["deficit"])]
    assert fin.size > 400 and np.ptp(fin) > 0.5 and np.isfinite(fin).all()
