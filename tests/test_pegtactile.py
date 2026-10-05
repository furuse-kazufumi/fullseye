# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""pegtactile の門(ペグ挿入を 2 本指の膜で読む: Whitney の閉形式・接触力学の閉形式・群の作用を真値に)。

numpy だけの門(常に走る。膜の合成と読みは 1 枚 0.2 s なので CI 用に組を絞り、母集団全部は PoC の --full):
 1. 静力学の写像の往復が恒等(1e-12)、パッドが離れる荷重は ValueError、滑りとねじりの全滑りは例外でなく印
 2. 共通成分と偶力の分解(同じ向き = 0、純粋な偶力 = 1)
 3. 膜 1 枚の往復(中くらいのせん断 + ねじり / ゼロのせん断): P・q・ねじり・第 2 実装 Q_stick
 4. 罠: 規則格子のマーカーはゼロ荷重で偽のせん断(ジッタの 3 倍超)
 5. 膜の SO(2) 同変性(向きを 45° 回すと推定も 45° 回り、大きさは不変)
 6. 罠: 半径ビンの接触半径は P̂ の傾きを狂わせ、tacsim.contact_radius_fit_pixelwise は直す(+ fail-closed)
 7. tacslip.mindlin_fit_vector は真の変位場から向きと Q を読む(画像を通さない)、点が 3 未満は ValueError
 8. Whitney の閉形式レンチ 36 組 → 状態: 幾何つき 36/36、レンチだけはくさびの境目の帯でだけ外れる
 9. くさびの境目の二点を膜経由で読んでも二点、壁の μ < 0.005
10. 二点の分解(μ と 2 つの法線力)、一点の μ(先端の壁 / 胴 / 面取り)、止まった時の判定の境目
11. 候補点の幾何(壁に触れた先端の縁だけが有効、口の縁は胴が通る所だけ)
12. 輪郭の複素フーリエから n 回対称(5 形状)、フーリエ位相の同変性、2 次モーメントの罠
13. 手首剛性の当てはめと悪条件、合成 RGB-D(mujoco 不要)から手首のたわみ
14. 綴り壊し・fail-closed、断面の MJCF 文字列(mujoco 不要)
mujoco が要る門(無ければ skip):
15. 短い挿入 1 走行: 触覚のレンチ vs MuJoCo の接触、接触状態の一致、手首剛性の画像同定
"""
from __future__ import annotations

import math

import numpy as np
import pytest

import pegsim as PS
import pegtactile as PT
import tacsim as T
import tacslip as S

KP = PS.peg_params()
DEG = math.pi / 180.0


def _raises(fn, exc=ValueError):
    try:
        fn()
    except exc:
        return True
    return False


@pytest.fixture(scope="module")
def pc():
    pad = PT.pad_params()
    return pad, PT.pad_context(pad)


def _through(F_c, M_c, axis, pad, ctx):
    a = np.asarray(axis, np.float64) / np.linalg.norm(axis)
    Rw = PT._rot_z_to(a)
    Fg = np.array([0.0, 0.0, -pad["peg_mass"] * 9.81])
    cmg = -(pad["com_below_top"] - pad["grasp_below_top"]) * a
    loads = PT.peg_wrench_to_pad_loads(Rw.T @ -(np.asarray(F_c) + Fg), Rw.T @ -(np.asarray(M_c) + np.cross(cmg, Fg)), pad)
    tq = loads["R"]["torsion"]
    rd = {s: PT.pad_tactile_read(PT.pad_tactile_frame(loads[s]["P"], loads[s]["q"], pad, ctx, torsion=tq), pad, ctx) for s in ("R", "L")}
    est = PT.pad_loads_to_peg_wrench(rd["R"]["P"], rd["R"]["q"], rd["L"]["P"], rd["L"]["q"], pad, torsion=0.5 * (rd["R"]["torsion"] + rd["L"]["torsion"]))
    return -(Rw @ est["F"]) - Fg, -(Rw @ est["M"]) - np.cross(cmg, Fg)


# ── 1〜2. 静力学 ───────────────────────────────────────────────────────────────
def test_statics_roundtrip_is_identity_and_lost_contact_fails_closed(pc):
    pad, _ = pc
    rng = np.random.default_rng(1)
    err = 0.0
    for _ in range(100):
        F, M = rng.normal(0, 0.5, 3), rng.normal(0, 4e-3, 3)
        L = PT.peg_wrench_to_pad_loads(F, M, pad)
        W = PT.pad_loads_to_peg_wrench(L["R"]["P"], L["R"]["q"], L["L"]["P"], L["L"]["q"], pad, torsion=L["R"]["torsion"])
        err = max(err, float(np.abs(W["F"] - F).max()), float(np.abs(W["M"] - M).max()), abs(W["grip"] - pad["grip"]))
    assert err < 1e-12
    assert _raises(lambda: PT.peg_wrench_to_pad_loads([2 * pad["grip"] + 0.1, 0, 0], [0, 0, 0], pad))
    slip = PT.peg_wrench_to_pad_loads([0, 0, 2.2 * pad["mu"] * pad["grip"]], [0, 0, 0], pad)
    assert not slip["ok"] and slip["R"]["slip_ratio"] > 1.0 and slip["min_margin"] < 0
    tw = PT.peg_wrench_to_pad_loads([0, 0, 0], [0.05, 0, 0], pad)            # 50 mN·m のねじりは全滑りを超える = 印
    assert not tw["torsion_ok"] and tw["R"]["torsion_ratio"] > 1.0


def test_shear_asymmetry_splits_common_force_and_couple():
    same = PT.pad_shear_asymmetry([0.0, 0.3], [0.0, 0.3])
    couple = PT.pad_shear_asymmetry([0.0, 0.3], [0.0, -0.3])
    assert same["ratio_v"] == 0.0 and not same["opposite_v"]
    assert couple["ratio_v"] == 1.0 and couple["opposite_v"] and np.allclose(couple["common"], 0.0)


# ── 3〜7. 膜の合成と読み ───────────────────────────────────────────────────────
def test_membrane_roundtrip_reads_load_shear_and_torsion(pc):
    pad, ctx = pc
    q = 0.5 * np.array([math.cos(3.5), math.sin(3.5)])
    fr = PT.pad_tactile_frame(4.5, q, pad, ctx, torsion=2.0e-3)
    rd = PT.pad_tactile_read(fr, pad, ctx)
    assert abs(rd["P"] / 4.5 - 1) < 3e-4 and np.linalg.norm(rd["q"] - q) < 6e-3
    assert abs(rd["torsion"] - 2.0e-3) < 3e-5 and abs(rd["Q_stick"] - 0.5) < 8e-3
    assert not fr["truth"]["slipping"] and fr["rgb"].shape == (pad["n"], pad["n"], 3)
    z = PT.pad_tactile_read(PT.pad_tactile_frame(3.5, (0.0, 0.0), pad, ctx), pad, ctx)
    assert abs(z["P"] / 3.5 - 1) < 3e-4 and np.linalg.norm(z["q"]) < 2e-3


def test_regular_marker_grid_gives_false_shear_at_zero_load(pc):
    pad, ctx = pc
    ctx_reg = PT.pad_context(pad, jitter_px=0.0)
    reg = PT.pad_tactile_read(PT.pad_tactile_frame(3.5, (0.0, 0.0), pad, ctx_reg), pad, ctx_reg)
    jit = PT.pad_tactile_read(PT.pad_tactile_frame(3.5, (0.0, 0.0), pad, ctx), pad, ctx)
    assert np.linalg.norm(reg["q"]) > 3.0 * np.linalg.norm(jit["q"]) and np.linalg.norm(reg["q"]) > 5e-3


def test_membrane_reading_rotates_with_the_shear(pc):
    pad, ctx = pc
    out = []
    for ph in (0.05, 0.05 + math.pi / 4):
        q = np.array([math.cos(ph), math.sin(ph)])
        rd = PT.pad_tactile_read(PT.pad_tactile_frame(4.0, q, pad, ctx), pad, ctx)
        out.append((math.degrees((rd["phi"] - ph + math.pi) % (2 * math.pi) - math.pi), rd["Q"]))
    assert len(out) == 2
    assert max(abs(o[0]) for o in out) < 0.25 and abs(out[0][1] - out[1][1]) < 1.2e-2


def test_pixelwise_contact_radius_fixes_the_slope_trap(pc):
    pad, ctx = pc
    Ps = np.array([3.8, 4.0, 4.2])
    eb, ep = [], []
    for P in Ps:
        fr = PT.pad_tactile_frame(float(P), (0.0, 0.3), pad, ctx)
        rec = T.membrane_recover(fr["shading"], ctx["lights"], pad["pitch"], ambient=0.03)
        ab = T.contact_radius_fit(rec["normals"], ctx["X"], ctx["Y"], pad["R"], pad["pitch"], centre_xy=(0.0, 0.0))["a"]
        fp = T.contact_radius_fit_pixelwise(rec["normals"], ctx["X"], ctx["Y"], pad["R"], ab)
        eb.append(T.hertz_force(pad["R"], pad["Es"], a=ab) - P)
        ep.append(T.hertz_force(pad["R"], pad["Es"], a=fp["a"]) - P)
        assert fp["n"] > 1000 and abs(fp["delta"] - fp["a"] ** 2 / pad["R"]) < 1e-15
    sb = np.abs(np.diff(eb) / np.diff(Ps)).max()
    sp = np.abs(np.diff(ep) / np.diff(Ps)).max()
    assert sp < 1e-3 and sb > 10 * sp and np.abs(ep).max() < 1e-3
    assert _raises(lambda: T.contact_radius_fit_pixelwise(rec["normals"], ctx["X"], ctx["Y"], pad["R"], 0.0))
    assert _raises(lambda: T.contact_radius_fit_pixelwise(rec["normals"][:10], ctx["X"], ctx["Y"], pad["R"], ab))
    assert _raises(lambda: T.contact_radius_fit_pixelwise(rec["normals"], ctx["X"], ctx["Y"], pad["R"], 1e-6))   # 使える画素が無い


def test_mindlin_fit_vector_reads_direction_from_the_true_field(pc):
    pad, ctx = pc
    for ph in (0.4, 2.0):
        q = 0.8 * np.array([math.cos(ph), math.sin(ph)])
        d = PT.pad_marker_displacement(4.0, q, pad, ctx)
        hz = d["hz"]
        pts = ctx["pts_flat"]
        rr = np.hypot(*(pts - ctx["c0"]).T) * pad["pitch"]
        u = d["u_m"] - (S.hertz_surface_ur(rr, hz["a"], hz["p0"], pad["G"], pad["nu"]) / np.maximum(rr, 1e-12))[:, None] * (pts - ctx["c0"]) * pad["pitch"]
        model = S.mindlin_model(hz, ctx["X"], ctx["Y"], ctx["kern"], pad["G"], pad["nu"])
        fit = S.mindlin_fit_vector(model, pts, u)
        assert abs((fit["phi"] - ph + math.pi) % (2 * math.pi) - math.pi) < 0.1 * DEG
        assert abs(fit["Q"] - 0.8) < 5e-3 and abs(fit["c_over_a"] - d["mp"]["c_over_a"]) < 0.02
    assert _raises(lambda: S.mindlin_fit_vector(model, pts[:2], u[:2]))
    assert _raises(lambda: S.mindlin_fit_vector(model, pts, u[:, :1]))


# ── 8〜11. Whitney の状態 ─────────────────────────────────────────────────────
def _cases():
    out = []
    for th_deg in (1.5, 3.0, 4.5):
        th = th_deg * DEG
        l2 = PS.two_point_depth(KP, th)
        for mu in (0.3, 0.8):
            for fn in (0.15, 0.6):
                out += [("one_point", th, KP["chamfer"] + 0.4 * l2, mu, fn, 0.0), ("mouth", th, KP["chamfer"] + 0.6 * l2, mu, 0.0, fn),
                        ("two_point", th, KP["chamfer"] + l2, mu, fn, 1.3 * fn)]
    return out


def test_whitney_wrench_states_and_the_blind_band():
    c_ = (KP["R"] - KP["r"]) / KP["R"]
    cases = _cases()
    assert len(cases) == 36
    ok_geo, ok_wrench, blind = 0, 0, []
    for st, th, depth, mu, f1, f2 in cases:
        ww = PT.whitney_wrench(KP, st, th, depth, mu, f1, f2)
        truth = "one_point" if st in ("one_point", "mouth") else "two_point"
        ok_geo += PT.contact_state_from_wrench(KP, ww["F"], ww["M_g"], ww["g"], ww["tip"], ww["axis"])["state"] == truth
        s0 = PT.contact_state_from_wrench(KP, ww["F"], ww["M_g"], ww["g"], ww["tip"], ww["axis"], geometry=False)["state"]
        ok_wrench += s0 == truth
        if s0 != truth:
            blind.append(abs(c_ / th - mu))
    assert ok_geo == 36 and 30 <= ok_wrench < 36 and len(blind) >= 1 and max(blind) < 0.1


def test_wedge_boundary_two_point_read_through_membranes(pc):
    pad, ctx = pc
    th = 3.0 * DEG
    ww = PT.whitney_wrench(KP, "two_point", th, KP["chamfer"] + PS.two_point_depth(KP, th), 0.8, 0.6, 0.78)
    F, M = _through(ww["F"], ww["M_g"], ww["axis"], pad, ctx)
    assert np.linalg.norm(F - ww["F"]) < 6e-3
    st = PT.contact_state_from_wrench(KP, F, M, ww["g"], ww["tip"], ww["axis"])
    assert st["state"] == "two_point" and st["forced"]
    assert abs(PT.two_point_forces(KP, F, M, ww["g"], ww["tip"], ww["axis"])["mu"] - 0.8) < 5e-3


def test_two_point_split_single_contact_mu_and_stall_verdict():
    th = 3.0 * DEG
    ww = PT.whitney_wrench(KP, "two_point", th, KP["chamfer"] + PS.two_point_depth(KP, th), 0.3, 0.6, 0.78)
    tp = PT.two_point_forces(KP, ww["F"], ww["M_g"], ww["g"], ww["tip"], ww["axis"])
    assert abs(tp["mu"] - 0.3) < 1e-3 and abs(tp["fn_tip"] - 0.6) < 2e-3 and abs(tp["fn_mouth"] - 0.78) < 2e-3
    for st, f1, f2 in (("one_point", 0.5, 0.0), ("mouth", 0.0, 0.5)):
        w1 = PT.whitney_wrench(KP, st, th, KP["chamfer"] + 0.5 * PS.two_point_depth(KP, th), 0.3, f1, f2)
        s = PT.contact_state_from_wrench(KP, w1["F"], w1["M_g"], w1["g"], w1["tip"], w1["axis"])
        assert s["state"] == "one_point" and s["where"] == ("tip" if st == "one_point" else "mouth")
        assert abs(PT.friction_from_single_contact(w1["F"], s["where"], s["c"], w1["axis"])["mu"] - 0.3) < 1e-9
    # 面取り 45° の上: 法線 (−r̂, 1)/√2、下へ滑る摩擦 μ = 0.3
    c = np.array([-KP["R"] - 0.5e-3, 0.0, -0.5e-3])
    nv = np.array([1.0, 0.0, 1.0]) / math.sqrt(2.0)
    tv = np.array([-1.0, 0.0, 1.0]) / math.sqrt(2.0)                    # 斜面に沿って上向き(下へ滑る物体に働く摩擦)
    assert abs(PT.friction_from_single_contact(0.7 * (nv + 0.3 * tv), "tip", c, [0, 0, 1], chamfer=True)["mu"] - 0.3) < 1e-12
    assert PT.friction_from_single_contact([0, 0, 1.0], "none", None, [0, 0, 1])["mu"] is None
    c_ = (KP["R"] - KP["r"]) / KP["R"]
    assert [PT.stall_verdict(KP, (c_ / mu) * f, mu)["verdict"] for mu in (0.3, 0.8) for f in (0.98, 1.02)] == ["jamming", "wedging"] * 2
    assert PT.stall_verdict(KP, 0.05, None)["verdict"] == "unknown" and PT.stall_verdict(KP, 0.05, 0.0)["verdict"] == "unknown"


def test_contact_candidates_are_geometric():
    a = np.array([0.0, 0.0, 1.0])
    centred = PT.contact_candidates(KP, [0.0, 0.0, -5e-3], a)                # 中心で鉛直: 隙間 0.2 mm、壁にも口にも触れない
    assert not centred["rim_ok"].any() and not centred["mouth_ok"].any()
    touching = PT.contact_candidates(KP, [-(KP["R"] - KP["r"]), 0.0, -5e-3], a)   # −x の壁に先端の縁が触れる
    ok = touching["tip_rim"][touching["rim_ok"]]
    assert len(ok) >= 1 and ok[:, 0].max() < 0 and np.hypot(ok[:, 0], ok[:, 1]).max() >= KP["R"] - 1e-9
    th = 3.0 * DEG
    ww = PT.whitney_wrench(KP, "two_point", th, KP["chamfer"] + PS.two_point_depth(KP, th), 0.3, 0.6, 0.78)
    both = PT.contact_candidates(KP, ww["tip"], ww["axis"])
    assert both["rim_ok"].any() and both["mouth_ok"].any() and both["mouth"][both["mouth_ok"]][:, 0].min() > 0


# ── 12. 対称性 ────────────────────────────────────────────────────────────────
def test_symmetry_order_equivariance_and_the_moment_trap():
    import blob2d
    want = {"circle": 0, "triangle": 3, "square": 4, "hexagon": 6, "keyed": 1}
    cen = (79.87, 79.29)
    got = {nm: PT.symmetry_order_contour(PT._level_contour(PT.symmetric_peg_shape(nm, 160, 50.0, 0.3, centre=cen)))["n"] for nm in PT.SHAPES}
    assert got == want

    def fourier(img):
        so = PT.symmetry_order_contour(PT._level_contour(img))
        return so["centroid"][0], so["centroid"][1], so["angle"]

    def moment(img):
        f = blob2d.blob_features(blob2d.blob_label(img > 0.5, 8))
        return float(f["row"][0]), float(f["col"][0]), float(f["angle"][0])
    for nm, n in (("hexagon", 6), ("keyed", 1)):
        e = PT.equivariance_check(lambda t, nm=nm: PT.symmetric_peg_shape(nm, 160, 50.0, 0.3 + t, centre=cen), fourier, [0.9], n, (cen[1], cen[0]))
        assert e["pos_err_px"] < 0.25 and e["ang_err_deg"] < (0.05 if n >= 3 else 1.0)
    em = PT.equivariance_check(lambda t: PT.symmetric_peg_shape("triangle", 160, 50.0, 0.3 + t, centre=cen), moment, [0.9], 3, (cen[1], cen[0]))
    assert em["ang_err_deg"] > 5.0                                           # n ≥ 3 で慣性が等方 = 2 次モーメントの向きは形と無関係


# ── 13. 手首 ──────────────────────────────────────────────────────────────────
def test_wrist_stiffness_fit_and_deflection_from_synthetic_rgbd():
    x = np.linspace(-0.6e-3, 0.6e-3, 41)
    fit = PT.wrist_stiffness_fit(x, 600.0 * x + np.random.default_rng(3).normal(0, 0.003, x.size))
    assert abs(fit["k"] / 600 - 1) < 5e-3 and fit["r2"] > 0.99
    assert _raises(lambda: PT.wrist_stiffness_fit(np.full(10, 1e-4) + np.arange(10) * 1e-9, np.ones(10)))
    assert _raises(lambda: PT.wrist_stiffness_fit([1e-3, 2e-3], [1.0, 2.0]))
    tip = np.array([1.0e-3, 0.5e-3, 0.004])
    ax = np.array([math.sin(2 * DEG), 0.0, math.cos(2 * DEG)])
    sy = PS.peg_synthetic_rgbd(KP, tip_xyz=tip, axis=ax, width=160, height=120, supersample=2)
    hz = 0.02
    r = PT.wrist_deflection_from_rgbd(sy["rgb"], sy["depth"], sy["K"], sy["R_cam_to_world"], -sy["R"].T @ sy["t"], np.zeros(3), KP["r"], hinge_z=hz)
    want = tip + (hz - tip[2]) / ax[2] * ax
    assert math.hypot(r["dx"] - want[0], r["dy"] - want[1]) < 30e-6 and abs(r["tilt_y"] - 2 * DEG) < 0.1 * DEG
    blank = np.zeros_like(sy["rgb"])
    assert _raises(lambda: PT.wrist_deflection_from_rgbd(blank, sy["depth"], sy["K"], sy["R_cam_to_world"], np.zeros(3), np.zeros(3), KP["r"]))


# ── 14. 綴り壊しと MJCF ───────────────────────────────────────────────────────
def test_spelling_breaks_and_bad_inputs_fail_closed(pc):
    pad, ctx = pc
    bad = [lambda: PT.whitney_wrench(KP, "tow_point", 0.05, 0.005, 0.3, 0.1),
           lambda: PT.whitney_wrench(KP, "two_point", -0.05, 0.005, 0.3, 0.1),
           lambda: PT.symmetric_peg_shape("hexagn"),
           lambda: PT.pad_tactile_frame(0.0, (0, 0), pad, ctx),
           lambda: PT.pad_tactile_frame(4.0, (0, float("nan")), pad, ctx),
           lambda: PT.pad_tactile_read({"rgb": 1}, pad, ctx),
           lambda: PT.pad_params(nu=0.6),
           lambda: PT.pad_params(grip=40.0),
           lambda: PT.pad_params(n=32),
           lambda: PT.pad_context(pad, jitter_px=-1.0),
           lambda: PT.peg_wrench_to_pad_loads([0, 0], [0, 0, 0], pad),
           lambda: PT.peg_wrench_to_pad_loads([0, 0, 0], [0, 0, 0], {"R": 1}),
           lambda: PT.friction_from_single_contact([0, 0, 1], "tipp", None, [0, 0, 1]),
           lambda: PT.friction_from_single_contact([0, 0, 1], "tip", None, [0, 0, 1], chamfer=True),
           lambda: PT.contact_state_from_wrench(KP, [0, 0, float("nan")], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 1]),
           lambda: PT.contact_state_from_wrench(KP, [0, 0, 1], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]),
           lambda: PT.two_point_forces(KP, [1, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 1]),
           lambda: PT.stall_verdict(KP, float("nan"), 0.3),
           lambda: PT.symmetry_order_contour(np.zeros((5, 2))),
           lambda: PT.equivariance_check(1, 2, [0.1], 3, (0, 0)),
           lambda: PT.equivariance_check(lambda t: 0, lambda i: (0, 0, 0), [], 3, (0, 0)),
           lambda: PT._level_contour(np.zeros((32, 32))),
           lambda: PT.pegtactile_cutaway_xml("<not xml"),
           lambda: PT.pegtactile_cutaway_xml("<mujoco/>"),
           lambda: PT.pegtactile_prefetch([], pad, None),
           lambda: PT.pegtactile_process_episode({"frames": []}, pad, ctx)]
    assert len(bad) == 26
    assert [i for i, f in enumerate(bad) if not _raises(f)] == []


def test_cutaway_xml_is_numpy_only():
    import xml.etree.ElementTree as ET
    import pegfail as PF
    xml = PT.pegtactile_cutaway_xml(PF.pegfail_scene_mjcf(KP), alpha=0.3)
    root = ET.fromstring(xml)
    cams = list(root.iter("camera"))
    assert len(cams) >= 1
    assert any(c.get("name") == "cut" for c in cams)
    plate = next(b for b in root.iter("body") if b.get("name") == "plate")
    alphas = {float(g.get("rgba").split()[3]) for g in plate.iter("geom") if g.get("rgba") and g.get("name")}
    assert alphas == {0.3}
    assert int(root.find("visual/global").get("offwidth")) >= 480


# ── 15. mujoco ────────────────────────────────────────────────────────────────
def test_mujoco_short_insertion_read_through_membranes(pc):
    pytest.importorskip("mujoco")
    pad, ctx = pc
    ep = PT.pegtactile_episode_run(pad=pad, eps_mm=(0.6, 0.0), tilt_deg=3.0, t_max=5.0, frame_every=0.12, render_wrist=True)
    assert ep["status"] in ("inserted", "timeout") and len(ep["frames"]) >= 15 and max(fr["depth"] for fr in ep["frames"]) > 7e-3
    res = PT.pegtactile_process_episode(ep, pad, ctx)
    eF = [float(np.linalg.norm(row["tw"]["F"] - fr["Fc"])) for fr, row in zip(ep["frames"], res["rows"]) if np.linalg.norm(fr["Fc"]) > 0.05]
    assert len(eF) >= 5 and np.median(eF) < 5e-3 and max(eF) < 15e-3
    acc = sum(row["st_tactile"]["state"] == row["state_true"] for row in res["rows"]) / len(res["rows"])
    assert acc >= 0.9
    assert res["k_fit"] is not None and abs(res["k_fit"]["k"] / KP["k_trans"] - 1) < 0.02
