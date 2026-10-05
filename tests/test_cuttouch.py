# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""cuttouch の門(包丁を指先の視触覚だけで持ち、靱性 R・刃の当たり位置・ねじりの余裕を読む)。

numpy だけ(常に走る):
 1. 部分滑りのねじりの数値解の両端 = 閉形式(Reissner–Sagoci の β、全滑りのトルク (3π/16)μPa)、単調
 2. パッドの格子で畳んだ場は固着円の中で剛体回転(ω = β)、小さい M で無滑りの場(tactorque)に一致
 3. 既存の読み手(pegtactile)は部分滑りの像でねじりを過大に読む(比 0.5 で ×1.33)、補正で戻る
 4. 静力学の往復(食材 + 包丁の重さ → 2 パッド → 風袋を引いて V・H・Ly・ξ、刃の傾き込み)
 5. 靱性: 閉形式の切断 1 回分のレンチ → R と ξ̂(触覚だけ)
 6. 持てる柄の長さの限界 = 閉形式、全滑り・読めない印
 7. 綴り壊し・測れない入力は ValueError
 8. 入口: __all__ が実在、docstring に Markdown のリンク記法なし
mujoco があれば:
 9. MuJoCo の切断の数コマ → R̂(設定値との差 2 % 以内)
"""
from __future__ import annotations

import math

import numpy as np
import pytest

import cutting as C
import cuttouch as CT
import pegtactile as PT
import tacsim as T
import tacslip as S
import tactorque as TQ


@pytest.fixture(scope="module")
def pad_ctx():
    pad = PT.pad_params()
    return pad, PT.pad_context(pad)


def _mf(pad, P=None):
    P = pad["grip"] if P is None else P
    return 3 * math.pi / 16 * pad["mu"] * P * T.hertz_sphere(P, pad["R"], pad["Es"])["a"]


def _raises(fn, *a, **k):
    try:
        fn(*a, **k)
    except ValueError:
        return True
    return False


def _frame(P, q, tau, pad, ctx, seed=0, noise=0.003):
    disp = PT.pad_marker_displacement(P, q, pad, ctx, torsion=0.0)
    u = disp["u_m"] + (CT.torsion_partial_slip(tau, P, pad, ctx=ctx, field=True)["u_markers"] if tau else 0.0)
    ind = T.membrane_indent_sphere(disp["hz"], pad["n"], pad["fov"])
    sh = T.membrane_render_rgb(ind["normals"], ctx["lights"], ambient=PT._AMB)
    rgb = S.membrane_render_markers(sh, ctx["pts_flat"] + u / pad["pitch"], pad["marker_r_px"], pad["dark"])
    rng = np.random.default_rng(seed)
    return {"rgb": rgb + rng.normal(0, noise, rgb.shape), "shading": sh + rng.normal(0, noise, sh.shape)}


def _exact_reads(F_pad, M_pad, pad):
    L = PT.peg_wrench_to_pad_loads(F_pad, M_pad, pad)
    return ({"P": L["R"]["P"], "q": L["R"]["q"], "torsion": L["R"]["torsion"]},
            {"P": L["L"]["P"], "q": L["L"]["q"], "torsion": L["L"]["torsion"]})


def _pad_wrench(V, H, Ly, Lz, com_y=0.0, mass=0.0, Lz0=18e-3):
    F = np.array([0.0, -H, V])
    M = np.cross([0.0, Ly, -Lz], F)
    Fg = np.array([0.0, 0.0, -9.81 * mass])
    Mg = np.cross([0.0, com_y, -Lz0 / 2], Fg)
    return -(F + Fg), -(M + Mg)


# ── 1. 数値解の両端 ───────────────────────────────────────────────────────
def test_partial_slip_solution_meets_both_closed_forms():
    tab = CT._torsion_table(64)
    assert tab["beta"][0] / (3 * tab["M"][0] / 16) == pytest.approx(1.0, abs=0.005)      # c → a: Reissner–Sagoci
    assert tab["M_full"] == pytest.approx(math.pi ** 2 / 8, rel=0.003)                   # c → 0: (3π/16)μPa の無次元形
    assert np.all(np.diff(tab["c"]) < 0) and np.all(np.diff(tab["ratio"]) > 0) and np.all(np.diff(tab["beta"]) > 0)
    c5, b5, _ = CT._interp_ratio(tab, 0.5)
    assert 0.80 < c5 < 0.84 and 1.30 < b5 < 1.36


# ── 2. 場 ─────────────────────────────────────────────────────────────────
def test_partial_slip_field_is_rigid_in_the_stick_zone(pad_ctx):
    pad, ctx = pad_ctx
    Mf = _mf(pad)
    X, Y = ctx["X"], ctx["Y"]
    for m in (0.3, 0.8):
        r = CT.torsion_partial_slip(m * Mf, pad["grip"], pad, ctx=ctx, field=True)
        msk = np.hypot(X, Y) < 0.9 * r["c_over_a"] * r["a"]
        fit = TQ.rigid_rotation_fit(np.column_stack([X[msk], Y[msk]]), np.column_stack([r["ux"][msk], r["uy"][msk]]))
        assert fit["omega"] / r["beta"] == pytest.approx(1.0, abs=0.005)
        assert r["u_markers"].shape == (len(ctx["pts_flat"]), 2) and np.all(np.isfinite(r["u_markers"]))
    small = CT.torsion_partial_slip(0.05 * Mf, pad["grip"], pad, ctx=ctx, field=True)
    a = small["a"]
    ref = TQ.torsion_stick_field(X, Y, a, 0.05 * Mf, ctx["kern"], pad["G"])
    core = np.hypot(X, Y) < 0.5 * a
    assert np.median(small["ux"][core & (np.abs(ref["ux"]) > 0)] / ref["ux"][core & (np.abs(ref["ux"]) > 0)]) == pytest.approx(1.0, abs=0.03)


# ── 3. 既存の読み手の偏りと補正 ──────────────────────────────────────────
def test_existing_reader_overestimates_twist_and_correction_restores_it(pad_ctx):
    pad, ctx = pad_ctx
    tau = 0.5 * _mf(pad)
    fr = _frame(pad["grip"], [0.3, 0.2], tau, pad, ctx, seed=3)
    old = PT.pad_tactile_read(fr, pad, ctx, torsion_model="no_slip")         # 0.4.0 の読み(無滑りの関係)
    assert old["torsion"] / tau == pytest.approx(1.332, abs=0.025)
    tc, c_a, ok, sat = CT._true_torsion_from_stick_read(old["torsion"], old["P"], pad, 64)
    assert tc / tau == pytest.approx(1.0, abs=0.02) and ok and not sat and 0.78 < c_a < 0.86
    # 2026-10-06 から pegtactile の既定の読みはこの補正そのもの(公開の入口 from_no_slip_read 経由)、二重に直さない
    rd = PT.pad_tactile_read(fr, pad, ctx)
    assert rd["torsion_model"] == "partial_slip" and rd["torsion"] == pytest.approx(tc, rel=1e-9)
    assert rd["torsion_no_slip"] == pytest.approx(old["torsion"], rel=1e-12) and rd["torsion_readable"]
    assert CT.torsion_partial_slip(old["torsion"], old["P"], pad, from_no_slip_read=True)["M"] == pytest.approx(tc, rel=1e-12)
    rR = {"P": rd["P"], "q": rd["q"], "torsion": rd["torsion"], "torsion_no_slip": rd["torsion_no_slip"], "torsion_model": "partial_slip"}
    rO = {"P": old["P"], "q": old["q"], "torsion": old["torsion"]}
    k_new = CT.knife_load_from_pads(rR, rR, pad, 18e-3)
    k_old = CT.knife_load_from_pads(rO, rO, pad, 18e-3)
    assert k_new["pads"]["R"]["torsion"] == pytest.approx(k_old["pads"]["R"]["torsion"], rel=1e-12)
    assert _raises(lambda: CT.knife_load_from_pads({**rR, "torsion_model": "slip"}, rR, pad, 18e-3))


# ── 4. 静力学の往復 ─────────────────────────────────────────────────────
def test_statics_round_trip_with_tare_and_tilted_edge(pad_ctx):
    pad, _ = pad_ctx
    s, Lz0 = math.tan(math.radians(4.0)), 18e-3
    tare = _exact_reads(*_pad_wrench(0.0, 0.0, 0.0, Lz0, com_y=1.5e-3, mass=0.15), pad)
    for V, H, Ly in ((1.0, 0.07, 3e-3), (2.0, 0.14, -2e-3), (0.6, 0.2, 5e-3)):
        rR, rL = _exact_reads(*_pad_wrench(V, H, Ly, Lz0 - Ly * s, com_y=1.5e-3, mass=0.15), pad)
        r = CT.knife_load_from_pads(rR, rL, pad, Lz0, edge_slope=s, torsion_model="no_slip", tare=tare)
        assert abs(r["V"] - V) < 1e-12 and abs(r["H"] - H) < 1e-12 and abs(r["Ly"] - Ly) < 1e-12 and abs(r["xi"] - H / V) < 1e-12
        assert -1.0 < r["combined_margin"] < 1.0 and r["torsion_model"] == "no_slip"


# ── 5. 靱性 ─────────────────────────────────────────────────────────────
def test_toughness_from_pads_on_a_closed_form_cut(pad_ctx):
    pad, _ = pad_ctx
    ep = C.cutting_episode_synth(R=60.0, theta_deg=4.0, vx=0.0, vz=6.0, dt=0.1, n_frames=40)
    xi = ep["xi"]
    loads, w = [], []
    for V, we in zip(ep["F"], ep["w_eff"]):
        if we < 2.0:
            continue
        rR, rL = _exact_reads(*_pad_wrench(float(V), float(V) * xi, 1e-3, 18e-3), pad)
        loads.append(CT.knife_load_from_pads(rR, rL, pad, 18e-3, torsion_model="no_slip"))
        w.append(we)
    tf = CT.toughness_from_pads(loads, w)
    assert tf["R"] == pytest.approx(60.0, rel=1e-9) and tf["xi_tactile"] == pytest.approx(xi, rel=1e-9)
    assert tf["Ly_median"] == pytest.approx(1e-3, rel=1e-9) and tf["n_unreadable"] == 0
    assert CT.toughness_from_pads(loads, w, xi=0.0)["R"] < tf["R"]          # ξ を無視すると g = 1 で R を小さく出す


# ── 6. 柄の長さの限界と印 ───────────────────────────────────────────────
def test_handle_length_limits_and_flags(pad_ctx):
    pad, ctx = pad_ctx
    V, s, Lz0 = 2.0, 0.07, 18e-3
    H = V * s
    rR, rL = _exact_reads(*_pad_wrench(V, H, 0.0, Lz0), pad)
    r = CT.knife_load_from_pads(rR, rL, pad, Lz0, edge_slope=s)
    Mf = _mf(pad)
    lo, hi = r["Ly_range_full_slip"]
    assert lo == pytest.approx((-2 * Mf + Lz0 * H) / (V + s * H), rel=1e-12) and hi == pytest.approx((2 * Mf + Lz0 * H) / (V + s * H), rel=1e-12)
    rl, rh = r["Ly_range_readable"]
    assert lo < rl < 0 < rh < hi and 0.80 < r["ratio_at_read_limit"] < 0.85
    full = CT.torsion_partial_slip(1.2 * Mf, pad["grip"], pad)
    assert full["slipping"] and not full["readable"] and math.isnan(full["beta"])
    edge = CT.torsion_partial_slip(0.9 * Mf, pad["grip"], pad)
    assert not edge["slipping"] and not edge["readable"] and edge["c_over_a"] < 0.6


# ── 7. fail-closed ──────────────────────────────────────────────────────
def test_spelling_breaks_fail_closed(pad_ctx):
    pad, ctx = pad_ctx
    g = {"P": 4.0, "q": [0.1, 0.0], "torsion": 0.0}
    rR, rL = _exact_reads(*_pad_wrench(1.0, 0.07, 0.0, 18e-3), pad)
    ok = CT.knife_load_from_pads(rR, rL, pad, 18e-3)
    assert all([
        _raises(CT.torsion_partial_slip, 1e-3, 0.0, pad),
        _raises(CT.torsion_partial_slip, float("nan"), 4.0, pad),
        _raises(CT.torsion_partial_slip, 1e-3, True, pad),
        _raises(CT.torsion_partial_slip, 1e-3, 4.0, pad, na=10),
        _raises(CT.torsion_partial_slip, 1.0, 4.0, pad, ctx=ctx, field=True),
        _raises(CT.knife_load_from_pads, g, {"P": 4.0}, pad, 18e-3),
        _raises(CT.knife_load_from_pads, g, g, pad, 18e-3, torsion_model="partial-slip"),
        _raises(CT.knife_load_from_pads, g, g, pad, float("nan")),
        _raises(CT.knife_load_from_pads, g, g, pad, 18e-3),                              # V = 0: 当たり位置が定まらない
        _raises(CT.knife_load_from_pads, rR, rL, pad, 18e-3, tare={"F": [0, 0]}),
        _raises(CT.toughness_from_pads, [], []),
        _raises(CT.toughness_from_pads, [ok] * 3, [10.0, 10.0]),
        _raises(CT.toughness_from_pads, [ok] * 2, [10.0, 10.0]),
        _raises(CT.toughness_from_pads, [{"V": 1.0}] * 3, [10.0] * 3),
    ])


# ── 8. 入口 ─────────────────────────────────────────────────────────────
def test_entry_points_exist_and_docstrings_have_no_markdown_links():
    assert CT.__all__ == ["torsion_partial_slip", "knife_load_from_pads", "toughness_from_pads"]
    for name in CT.__all__:
        doc = getattr(CT, name).__doc__ or ""
        assert doc.strip() and "](" not in doc, name
    assert "](" not in CT.__doc__


# ── 9. MuJoCo(任意) ────────────────────────────────────────────────────
def test_mujoco_cut_frames_give_the_set_toughness(pad_ctx):
    pytest.importorskip("mujoco")
    pad, ctx = pad_ctx
    run = C.cutting_mujoco_wrist(theta_deg=4.0, R=60.0, render=False, dt_frame=0.1, n_frames=14)
    sc = C.cutting_scene("face")
    s = math.tan(math.radians(4.0))
    loads, w = [], []
    for ez, F in zip(run["edge_z_true"], run["F_constraint"]):
        we = C.food_cut_width(4.0, float(ez), sc["food_w"], sc["food_h"])
        if we < 2.0:
            continue
        Ly = (sc["food_w"] / 2 * -1 + we / 2 + 3.0) * 1e-3
        L = PT.peg_wrench_to_pad_loads(*_pad_wrench(float(F), float(F) * s, Ly, 18e-3 - Ly * s), pad)
        rd = {k: PT.pad_tactile_read(_frame(L[k]["P"], L[k]["q"], L[k]["torsion"], pad, ctx, seed=len(w) * 2 + i), pad, ctx)
              for i, k in enumerate(("R", "L"))}
        loads.append(CT.knife_load_from_pads(rd["R"], rd["L"], pad, 18e-3, edge_slope=s))
        w.append(we)
        if len(w) >= 4:
            break
    tf = CT.toughness_from_pads(loads, w)
    assert tf["R"] == pytest.approx(60.0, rel=0.02) and tf["xi_tactile"] == pytest.approx(s, rel=0.10)   # 入り始めの 4 コマ(H ≈ 0.03 N)、PoC の 14 コマで −0.7 %


# ── 10. docstring の呼び出し例が走る ─────────────────────────────────────────
def test_usage_example_in_the_module_docstring_runs(capsys):
    import textwrap

    import cuttouch as _M
    doc = _M.__doc__
    i = doc.index("呼び出し例")
    block = doc[doc.index("::", i) + 2:]
    lines = []
    for ln in block.splitlines()[1:]:
        if ln.strip() and not ln.startswith("    "):
            break
        lines.append(ln)
    code = textwrap.dedent("\n".join(lines))
    assert code.count("\n") >= 8 and "print(" in code
    exec(compile(code, "<cuttouch usage>", "exec"), {})
    out = capsys.readouterr().out.strip()
    assert out and "nan" not in out.lower() and "inf" not in out.lower()
