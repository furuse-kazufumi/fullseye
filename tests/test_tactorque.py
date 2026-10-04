# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""tactorque の門(マーカー場の双極子 → 把持内トルク: Johnson 1985 の閉形式を真値に、論文 arXiv 2404.15626 の式を再実装)。

 1. 閉形式の自己検算: 平頭圧の格子積分(Σp h² = P、Σx p h² = M)、離れの fail-closed、楕円 Hertz 圧の P、ずらした Hertz 圧の 1 次モーメント = P·d
 2. Boussinesq 核 vs Johnson 3.41b / 3.42a / 平頭の u_z、Gauss の恒等式 ∇·ū = −(1−2ν)p/2G(ν 2 点)
 3. 双極子: 純法線で 0(3 形式)、D ∝ M(R²・係数・原点不変)、基線形式は符号を知らない、3 形状で係数が同じ
 4. ねじり: Reissner–Sagoci の β を Cerruti 畳み込みで、剛体回転の当てはめ、curl = 2β、piv_vorticity = −curl(符号規約)
 5. 分解: 重ね合わせ、純せん断の漏れと窓、雑音 ∝ σ、散在最小二乗 = 中心差分、nan ≠ 0、綴り壊し
 6. 像から: 描画 → marker_track → torque_decompose
 7. 有限要素(FULLSEYE_TAXIM_DATA があるときだけ): 有限厚は膨らむ(符号が逆)、斜め荷重の双極子はせん断漏れの符号
"""
from __future__ import annotations

import math
import os

import numpy as np
import pytest
from scipy import ndimage

import pivops
import sceneflow as SF
import tacsim as T
import tacslip as S
import tactorque as TQ

E, NU, R_BALL, P, MU = 0.2e6, 0.48, 6.0e-3, 2.0, 0.5
G = E / (2 * (1 + NU))
A = 3.0e-3
N, FOV = 128, 16.0e-3
PITCH = FOV / N
COEF = -(1.0 - 2.0 * NU) / (2.0 * G)
MK_PX = 4.0
MK_AREA = (MK_PX * PITCH) ** 2
FIT_R = 1.5 * MK_PX * PITCH
M_TEST = 1.0e-3


def _sample(fields, pts_px):
    p = np.asarray(pts_px, np.float64)
    return np.column_stack([ndimage.map_coordinates(np.asarray(f, np.float64), [p[:, 1], p[:, 0]], order=1, mode="nearest") for f in fields])


@pytest.fixture(scope="module")
def grid():
    X, Y, r, _ = T._grid(N, FOV)
    hz = T.hertz_sphere(P, R_BALL, T.combined_modulus(E, NU))
    kb = TQ.boussinesq_kernel(N, PITCH, G, NU)
    kc = S.cerruti_kernel(N, PITCH, G, NU)
    mk = S.membrane_markers(N, MK_PX)
    mk = mk[(mk[:, 0] >= 0) & (mk[:, 0] < N) & (mk[:, 1] >= 0) & (mk[:, 1] < N)]
    p0 = TQ.punch_pressure(X, Y, A, P, (0.0, 0.0), pitch=PITCH)
    pM = TQ.punch_pressure(X, Y, A, P, (M_TEST, 0.0), pitch=PITCH)
    M1g = TQ.pressure_first_moment(pM, X, Y, PITCH)["M1"][0]
    return {"X": X, "Y": Y, "r": r, "hz": hz, "kb": kb, "kc": kc, "mk_px": mk, "mk_m": (mk - (N - 1) / 2.0) * PITCH, "p0": p0, "pM": pM, "M1g": M1g}


@pytest.fixture(scope="module")
def tilt(grid):
    """傾き M_TEST の零点後の場(格子とマーカー)。"""
    dp = TQ.tilt_shear_field(grid["p0"], grid["pM"], grid["kb"])
    return {"dp": dp, "um": _sample((dp["ux"], dp["uy"]), grid["mk_px"])}


# ── 1. 閉形式 ───────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("M", [0.0, 0.5e-3, 1.0e-3])
def test_punch_pressure_grid_moments(grid, M):
    p = TQ.punch_pressure(grid["X"], grid["Y"], A, P, (M, 0.0), pitch=PITCH)
    m = TQ.pressure_first_moment(p, grid["X"], grid["Y"], PITCH)
    assert abs(m["P"] / P - 1.0) < 0.015                                  # 縁 1/√ の格子誤差(実測 0.57 %)
    if M > 0:
        assert abs(m["M1"][0] / M - 1.0) < 0.015                          # 実測 0.86 %
        assert m["tau"][1] == pytest.approx(m["M1"][0])
    assert abs(m["M1"][1]) < 1e-12 * max(M, P * A)
    assert (p >= 0).all()


def test_punch_pressure_fail_closed(grid):
    with pytest.raises(ValueError):
        TQ.punch_pressure(grid["X"], grid["Y"], A, P, (0.4 * P * A, 0.0))   # |M| > Pa/3 で離れる
    with pytest.raises(ValueError):
        TQ.punch_pressure(grid["X"], grid["Y"][:10], A, P)
    with pytest.raises(ValueError):
        TQ.punch_surface_uz(grid["r"], A, 0.0, G, NU)
    with pytest.raises(ValueError):
        TQ.ellipse_pressure_shifted(grid["X"], grid["Y"], 2e-3, 0.0, P)
    with pytest.raises(ValueError):
        TQ.hertz_pressure_shifted(grid["X"], grid["Y"], {"a": 1e-3})


def test_shifted_pressures_carry_first_moment_P_times_d(grid):
    d = 0.3e-3
    hs = TQ.hertz_pressure_shifted(grid["X"], grid["Y"], grid["hz"], (d, 0.0))
    m = TQ.pressure_first_moment(hs, grid["X"], grid["Y"], PITCH)
    assert abs(m["P"] / P - 1.0) < 2e-3
    assert m["M1"][0] == pytest.approx(P * d, rel=3e-3)
    el = TQ.ellipse_pressure_shifted(grid["X"], grid["Y"], 2e-3, 6e-3, P, (d, 0.0))
    me = TQ.pressure_first_moment(el, grid["X"], grid["Y"], PITCH)
    assert abs(me["P"] / P - 1.0) < 3e-3                                   # 式 4.24: P = 2πab p0/3
    assert me["M1"][0] == pytest.approx(P * d, rel=4e-3)


# ── 2. 核と Gauss の恒等式 ───────────────────────────────────────────────────
def test_boussinesq_kernel_matches_johnson_341b_342a_and_punch_uz(grid):
    X, Y, r, hz, kb = grid["X"], grid["Y"], grid["r"], grid["hz"], grid["kb"]
    ph = T.hertz_pressure(r, hz["a"], hz["p0"])
    u = TQ.boussinesq_surface_displacement(ph, kb)
    rr = np.maximum(r, 1e-12)
    ur = (u["ux"] * X + u["uy"] * Y) / rr
    ur_cf = S.hertz_surface_ur(r, hz["a"], hz["p0"], G, NU)
    assert np.sqrt(np.mean((ur - ur_cf) ** 2)) / np.abs(ur_cf).max() < 1e-3
    assert np.sqrt(np.mean((u["uz"] - T.hertz_surface_uz(r, hz["a"], hz["delta"], R_BALL)) ** 2)) / hz["delta"] < 1e-3
    uzp = TQ.boussinesq_surface_displacement(grid["p0"], kb)["uz"]
    uz_cf = TQ.punch_surface_uz(r, A, P, G, NU)
    assert np.sqrt(np.mean((uzp - uz_cf) ** 2)) / uz_cf.max() < 0.01      # 平頭の円内一様 δ(独立実装で検証、実測 0.35 %)
    assert np.ptp(uz_cf[r <= A]) == 0.0
    with pytest.raises(ValueError):
        TQ.boussinesq_surface_displacement(grid["p0"][:64], kb)
    with pytest.raises(ValueError):
        TQ.boussinesq_kernel(4, PITCH, G, NU)


@pytest.mark.parametrize("nu", [NU, 0.3])
def test_gauss_law_is_exact_in_the_half_space(grid, nu):
    G_ = E / (2 * (1 + nu))
    kb = grid["kb"] if nu == NU else TQ.boussinesq_kernel(N, PITCH, G_, nu)
    r = grid["r"]
    for p, a in ((T.hertz_pressure(r, grid["hz"]["a"], grid["hz"]["p0"]), grid["hz"]["a"]), (grid["pM"], A)):
        u = TQ.boussinesq_surface_displacement(p, kb)
        div = SF.flow_divergence(u["ux"], u["uy"]) / PITCH
        cf = TQ.surface_divergence_closed_form(p, G_, nu)
        m = r < 0.8 * a
        assert np.sqrt(np.mean((div[m] - cf[m]) ** 2)) / np.abs(cf[m]).max() < 5e-3
    with pytest.raises(ValueError):
        TQ.surface_divergence_closed_form(grid["p0"], 0.0, nu)


# ── 3. 双極子 ───────────────────────────────────────────────────────────────────
def test_pure_normal_load_gives_zero_dipole_in_all_forms(grid):
    X, Y, r, hz = grid["X"], grid["Y"], grid["r"], grid["hz"]
    u = TQ.boussinesq_surface_displacement(T.hertz_pressure(r, hz["a"], hz["p0"]), grid["kb"])
    pts = np.column_stack([X.ravel(), Y.ravel()]); uu = np.column_stack([u["ux"].ravel(), u["uy"].ravel()])
    div = (SF.flow_divergence(u["ux"], u["uy"]) / PITCH).ravel()
    ref = abs(COEF * M_TEST)
    assert len(TQ.DIPOLE_FORMS) == 3
    for form in TQ.DIPOLE_FORMS:
        d = TQ.tactile_dipole_moment(pts, uu, form, origin="centre", area=PITCH ** 2, rho=div if form == "divergence" else None)
        assert np.abs(d["D"]).max() / ref < 1e-9
        assert d["n"] == N * N


def test_dipole_is_linear_in_M_with_the_closed_form_coefficient(grid):
    Ms = np.linspace(0.0, 1.5e-3, 7)
    Ds, Dy = [], []
    assert len(Ms) == 7
    for M in Ms:
        pm = TQ.punch_pressure(grid["X"], grid["Y"], A, P, (M, 0.0), pitch=PITCH)
        dp = TQ.tilt_shear_field(grid["p0"], pm, grid["kb"])
        um = _sample((dp["ux"], dp["uy"]), grid["mk_px"])
        d = TQ.tactile_dipole_moment(grid["mk_m"], um, "divergence", area=MK_AREA, radius=FIT_R)
        Ds.append(d["D"][0]); Dy.append(d["D"][1])
    fit = TQ.dipole_to_torque_fit(Ds, Ms)
    assert fit["R2"] > 0.999
    assert fit["k"] / (COEF * grid["M1g"] / M_TEST) == pytest.approx(1.0, abs=5e-3)
    assert abs(fit["b"]) < 1e-3 * abs(fit["k"]) * Ms[-1]
    assert max(abs(y / x) for x, y in zip(Ds[1:], Dy[1:])) < 1e-3
    # 原点: 正負の重心の中点 vs 中心(格子の正味電荷 ~1e-3 の分だけ違う)
    pm = TQ.punch_pressure(grid["X"], grid["Y"], A, P, (Ms[-1], 0.0), pitch=PITCH)
    um = _sample((lambda dp: (dp["ux"], dp["uy"]))(TQ.tilt_shear_field(grid["p0"], pm, grid["kb"])), grid["mk_px"])
    d1 = TQ.tactile_dipole_moment(grid["mk_m"], um, "divergence", origin="midpoint", area=MK_AREA, radius=FIT_R)
    d2 = TQ.tactile_dipole_moment(grid["mk_m"], um, "divergence", origin="centre", area=MK_AREA, radius=FIT_R)
    assert np.abs(d1["D"] - d2["D"]).max() / np.abs(d1["D"]).max() < 1e-3
    assert d1["tau_dir"][1] == pytest.approx(d1["D"][0])


def test_baseline_norm_form_is_sign_blind_for_a_zeroed_symmetric_tilt(grid, tilt):
    um = tilt["um"]
    ddiv = TQ.tactile_dipole_moment(grid["mk_m"], um, "divergence", area=MK_AREA, radius=FIT_R)["D"][0]
    dnc = TQ.tactile_dipole_moment(grid["mk_m"], um, "norm_cross", origin="centre", area=MK_AREA)["D"][0]
    drad = TQ.tactile_dipole_moment(grid["mk_m"], um, "radial", origin="centre", area=MK_AREA)["D"][0]
    assert abs(dnc / ddiv) < 1e-3
    assert abs(drad / ddiv) < 1e-2
    # 符号を反転した M で基線は変わらない(|u| は偶関数)、発散形式は符号が変わる
    pm = TQ.punch_pressure(grid["X"], grid["Y"], A, P, (-M_TEST, 0.0), pitch=PITCH)
    dp = TQ.tilt_shear_field(grid["p0"], pm, grid["kb"])
    um2 = _sample((dp["ux"], dp["uy"]), grid["mk_px"])
    assert TQ.tactile_dipole_moment(grid["mk_m"], um2, "divergence", area=MK_AREA, radius=FIT_R)["D"][0] == pytest.approx(-ddiv, rel=1e-9)
    assert TQ.tactile_dipole_moment(grid["mk_m"], um2, "norm_cross", origin="centre", area=MK_AREA)["D"][0] == pytest.approx(dnc, abs=1e-6 * abs(ddiv))


def test_coefficient_is_shape_free_in_the_half_space(grid):
    X, Y, hz = grid["X"], grid["Y"], grid["hz"]
    d = M_TEST / P
    shapes = [(grid["p0"], grid["pM"]),
              (TQ.hertz_pressure_shifted(X, Y, hz), TQ.hertz_pressure_shifted(X, Y, hz, (d, 0.0))),
              (TQ.ellipse_pressure_shifted(X, Y, 2e-3, 6e-3, P), TQ.ellipse_pressure_shifted(X, Y, 2e-3, 6e-3, P, (d, 0.0)))]
    ks = []
    assert len(shapes) == 3
    for pa, pb in shapes:
        dp = TQ.tilt_shear_field(pa, pb, grid["kb"])
        M1g = TQ.pressure_first_moment(pb - pa, X, Y, PITCH)["M1"][0]
        pts = np.column_stack([X.ravel(), Y.ravel()]); u = np.column_stack([dp["ux"].ravel(), dp["uy"].ravel()])
        div = (SF.flow_divergence(dp["ux"], dp["uy"]) / PITCH).ravel()
        ks.append(TQ.tactile_dipole_moment(pts, u, "divergence", area=PITCH ** 2, rho=div)["D"][0] / COEF / M1g)
    ks = np.array(ks)
    assert np.ptp(ks) / ks.mean() < 2e-3
    assert np.allclose(ks, 1.0, atol=2e-3)


# ── 4. ねじり ───────────────────────────────────────────────────────────────────
def test_torsion_reissner_sagoci_beta_by_independent_convolution(grid):
    X, Y, r = grid["X"], grid["Y"], grid["r"]
    MZ = 0.5e-3
    tf = TQ.torsion_stick_field(X, Y, A, MZ, grid["kc"], G)
    assert (np.hypot(tf["qx"], tf["qy"]) * r).sum() * PITCH ** 2 / MZ == pytest.approx(1.0, abs=0.015)   # ∫ r q_θ dA = M_z
    rr = np.maximum(r, 1e-12)
    uth = (-tf["ux"] * Y + tf["uy"] * X) / rr
    m = (r < 0.9 * A) & (r > 0.1 * A)
    ratio = uth[m] / r[m]
    assert ratio.mean() / tf["beta"] == pytest.approx(1.0, abs=0.01)
    assert ratio.std() / ratio.mean() < 3e-3                                # 円内は剛体回転
    assert tf["beta"] == pytest.approx(3 * MZ / (16 * G * A ** 3))
    assert np.abs(tf["ux_cf"][m] - (-tf["beta"] * Y[m])).max() < 1e-18
    with pytest.raises(ValueError):
        TQ.torsion_stick_field(X, Y, A, MZ, grid["kc"], 0.0)
    with pytest.raises(ValueError):
        TQ.torsion_stick_field(X, Y, A, MZ, {"n": N}, G)


def test_rigid_rotation_fit_curl_and_piv_vorticity_convention(grid):
    X, Y, r = grid["X"], grid["Y"], grid["r"]
    MZ = 0.5e-3
    tf = TQ.torsion_stick_field(X, Y, A, MZ, grid["kc"], G)
    um = _sample((tf["ux"], tf["uy"]), grid["mk_px"])
    rf = TQ.rigid_rotation_fit(grid["mk_m"], um, (0.0, 0.0, 0.9 * A))
    assert rf["omega"] / tf["beta"] == pytest.approx(1.0, abs=0.01)
    assert rf["resid_rms"] < 0.02 * np.abs(um).max()
    curl = SF.flow_curl(tf["ux"], tf["uy"]) / PITCH
    m8 = r < 0.8 * A
    assert curl[m8].mean() / (2 * tf["beta"]) == pytest.approx(1.0, abs=0.02)
    vort = pivops.piv_vorticity(np.stack([tf["uy"], tf["ux"]]), spacing=PITCH)          # 規約 (dy, dx): −curl
    assert np.abs(vort[m8] + curl[m8]).max() / np.abs(curl[m8]).max() < 1e-9
    dec = TQ.torque_decompose(grid["mk_m"], um, MK_AREA, G, NU, a=A, window=(0.0, 0.0, 0.9 * A), radius=FIT_R)
    assert dec["Mz"] / MZ == pytest.approx(1.0, abs=0.01)
    assert np.abs(dec["M1"]).max() < 0.01e-3                                 # ねじりは傾きへ 0.01 N·mm 未満しか漏れない
    assert dec["omega_curl"] / tf["beta"] < 0.95                               # 平均 curl/2 は縁で低い(剛体回転の当てはめを使う理由)
    with pytest.raises(ValueError):
        TQ.rigid_rotation_fit(grid["mk_m"][:2], um[:2])


# ── 5. 分解 ─────────────────────────────────────────────────────────────────────
def test_superposition_decomposes_into_tilt_torsion_translation(grid, tilt):
    X, Y = grid["X"], grid["Y"]
    MZ = 0.5e-3
    tf = TQ.torsion_stick_field(X, Y, A, MZ, grid["kc"], G)
    ux = tilt["dp"]["ux"] + tf["ux"] + 1.0 * PITCH; uy = tilt["dp"]["uy"] + tf["uy"]
    um = _sample((ux, uy), grid["mk_px"])
    out = TQ.torque_decompose(grid["mk_m"], um, MK_AREA, G, NU, a=A, window=(0.0, 0.0, A + FIT_R), radius=FIT_R)
    inn = TQ.torque_decompose(grid["mk_m"], um, MK_AREA, G, NU, a=A, window=(0.0, 0.0, 0.9 * A), radius=FIT_R)
    assert out["M1"][0] / grid["M1g"] == pytest.approx(1.0, abs=0.04)        # ねじり → 傾きの漏れ込み(実測 2.4 %)
    assert inn["Mz"] / MZ == pytest.approx(1.0, abs=0.01)
    assert np.abs(inn["translation"] / PITCH - [1.0, 0.0]).max() < 0.05
    assert out["tau"][1] == pytest.approx(out["M1"][0])
    assert 0.4 < inn["M1"][0] / grid["M1g"] < 0.55                           # 小さい窓は固定比(較正で吸収)
    tilt_only = TQ.torque_decompose(grid["mk_m"], tilt["um"], MK_AREA, G, NU, a=A, window=(0.0, 0.0, A + FIT_R), radius=FIT_R)
    assert tilt_only["M1"][0] / grid["M1g"] == pytest.approx(1.0, abs=5e-3)
    assert "Mz" not in TQ.torque_decompose(grid["mk_m"], um, MK_AREA, G, NU, radius=FIT_R)


@pytest.mark.parametrize("qr", [0.05, 0.3, 0.6])
def test_pure_shear_leaks_only_outside_the_stick_window(grid, qr):
    hz = grid["hz"]
    mp = S.mindlin_partial_slip(qr * MU * P, hz, MU, G, NU)
    fld = S.membrane_shear_field(hz, mp, grid["X"], grid["Y"], grid["kc"])
    um = _sample((fld["ux"], fld["uy"]), grid["mk_px"])
    inn = TQ.torque_decompose(grid["mk_m"], um, MK_AREA, G, NU, a=hz["a"], window=(0.0, 0.0, mp["c"] - FIT_R), radius=FIT_R)
    assert np.abs(inn["M1"]).max() * 1e3 < 0.005                              # 固着円内は変位一様 → 発散 0
    assert inn["translation"][0] / mp["delta_x"] == pytest.approx(1.0, abs=0.01)
    full = TQ.torque_decompose(grid["mk_m"], um, MK_AREA, G, NU, a=hz["a"], window=None, radius=FIT_R)
    pred = (1 - NU) / (1 - 2 * NU) * qr * MU * P * (FOV / 2)                 # 導出(円窓)、正方窓なので 15 %
    assert abs(full["M1"][0]) / pred == pytest.approx(1.0, abs=0.15)
    assert abs(full["M1"][0]) > 100 * np.abs(inn["M1"]).max()


def test_noise_resolution_scales_with_sigma_and_window(grid, tilt):
    um = tilt["um"]
    r3 = TQ.dipole_torque_resolution(grid["mk_m"], um, 0.03, PITCH, COEF, MK_AREA, FIT_R, trials=60, window=(0.0, 0.0, 1.5 * A))
    r1 = TQ.dipole_torque_resolution(grid["mk_m"], um, 0.01, PITCH, COEF, MK_AREA, FIT_R, trials=60, window=(0.0, 0.0, 1.5 * A))
    rf = TQ.dipole_torque_resolution(grid["mk_m"], um, 0.03, PITCH, COEF, MK_AREA, FIT_R, trials=60, window=None)
    assert r3["sigma_M"][0] * 1e3 < 0.2
    assert r1["sigma_M"][0] / r3["sigma_M"][0] == pytest.approx(1 / 3, abs=0.05)
    assert rf["sigma_M"][0] > 3 * r3["sigma_M"][0]                            # マーカーを増やしても雑音が増えるだけ
    assert r3["snr"][0] > 5
    assert np.allclose(r3["D0"], TQ.tactile_dipole_moment(grid["mk_m"], um, "divergence", origin="centre", area=MK_AREA, radius=FIT_R, window=(0.0, 0.0, 1.5 * A))["D"])
    with pytest.raises(ValueError):
        TQ.dipole_torque_resolution(grid["mk_m"], um, -0.1, PITCH, COEF, MK_AREA, FIT_R)


def test_marker_divergence_equals_sceneflow_central_difference_on_a_grid(grid, tilt):
    X, Y = grid["X"], grid["Y"]
    ux, uy = tilt["dp"]["ux"], tilt["dp"]["uy"]
    pts = np.column_stack([X.ravel(), Y.ravel()]); u = np.column_stack([ux.ravel(), uy.ravel()])
    dc = TQ.marker_divergence(pts, u, 1.01 * PITCH)                           # 5 点(十字)= 中心差分
    div_sf = SF.flow_divergence(ux, uy) / PITCH; curl_sf = SF.flow_curl(ux, uy) / PITCH
    inner = np.ones((N, N), bool); inner[0, :] = inner[-1, :] = inner[:, 0] = inner[:, -1] = False
    assert np.abs(dc["div"].reshape(N, N)[inner] - div_sf[inner]).max() / np.abs(div_sf).max() < 1e-9
    assert np.abs(dc["curl"].reshape(N, N)[inner] - curl_sf[inner]).max() / np.abs(curl_sf).max() < 1e-9
    assert dc["n_valid"] == N * N - 4                                           # 四隅は十字の近傍が 3 点で特異 → nan(fail-closed)


def test_marker_divergence_is_nan_not_zero_when_underdetermined(grid, tilt):
    dc = TQ.marker_divergence(grid["mk_m"], tilt["um"], 0.3 * MK_PX * PITCH)
    assert np.isnan(dc["div"]).all() and dc["n_valid"] == 0
    col = np.column_stack([np.linspace(0, 1, 12), np.zeros(12)])                 # 共線 → 特異
    dcl = TQ.marker_divergence(col, np.zeros_like(col), 0.5)
    assert np.isnan(dcl["div"]).all()
    with pytest.raises(ValueError):
        TQ.marker_divergence(grid["mk_m"], tilt["um"], 0.0)
    with pytest.raises(ValueError):
        TQ.marker_divergence(grid["mk_m"][:3], tilt["um"][:3], FIT_R)


def test_spelling_break_and_fail_closed(grid, tilt):
    mk, um = grid["mk_m"], tilt["um"]
    bad = [
        lambda: TQ.tactile_dipole_moment(mk, um, "divergance", area=MK_AREA, radius=FIT_R),
        lambda: TQ.tactile_dipole_moment(mk, um, "divergence", weight="mean ", area=MK_AREA, radius=FIT_R),
        lambda: TQ.tactile_dipole_moment(mk, um, "divergence", origin="middle", area=MK_AREA, radius=FIT_R),
        lambda: TQ.tactile_dipole_moment(mk, um, "divergence", weight="area", radius=FIT_R),
        lambda: TQ.tactile_dipole_moment(mk, um, "divergence", area=MK_AREA),
        lambda: TQ.tactile_dipole_moment(mk, um, "divergence", area=MK_AREA, rho=np.zeros(3)),
        lambda: TQ.tactile_dipole_moment(mk[:2], um[:2], "norm_cross", origin="centre", area=MK_AREA),
        lambda: TQ.dipole_to_torque_fit([1.0], [1.0]),
        lambda: TQ.dipole_to_torque_fit([1.0, 2.0], [1.0, 1.0]),
        lambda: TQ.torque_decompose(mk, um, MK_AREA, G, NU),
        lambda: TQ.torque_decompose(mk, um, MK_AREA, G, 0.7, radius=FIT_R),
        lambda: TQ.torque_decompose(mk, um, MK_AREA, G, NU, radius=FIT_R, window=(0.0, 0.0, 1e-9)),
        lambda: TQ.pressure_first_moment(grid["p0"], grid["X"], grid["Y"], 0.0),
    ]
    assert len(bad) == 13
    for fn in bad:
        with pytest.raises(ValueError):
            fn()
    d = TQ.tactile_dipole_moment(mk, um, "divergence", weight="mean", radius=FIT_R)
    assert d["D"][0] == pytest.approx(TQ.tactile_dipole_moment(mk, um, "divergence", area=MK_AREA, radius=FIT_R)["D"][0] / MK_AREA / d["n"], rel=1e-9)


def test_dipole_to_torque_fit_recovers_an_exact_line():
    M = np.linspace(0, 2e-3, 9)
    k = -3.7e-6
    f = TQ.dipole_to_torque_fit(k * M, M)
    assert f["k"] == pytest.approx(k) and f["R2"] == pytest.approx(1.0) and abs(f["b"]) < 1e-15 and f["rmse_M"] < 1e-12
    g = TQ.dipole_to_torque_fit(k * M + 2e-9, M)
    assert g["b"] == pytest.approx(2e-9) and g["R2_affine"] == pytest.approx(1.0) and g["R2"] < g["R2_affine"]


# ── 6. 像から ───────────────────────────────────────────────────────────────────
def test_image_pipeline_render_track_decompose():
    N2 = 256; P2 = FOV / N2
    X2, Y2, r2, _ = T._grid(N2, FOV)
    kb2 = TQ.boussinesq_kernel(N2, P2, G, NU)
    h = -TQ.punch_surface_uz(r2, A, P, G, NU)
    gy, gx = np.gradient(h, P2)
    nrm = np.dstack([-gx, -gy, np.ones_like(h)]); nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    bg = T.membrane_render_rgb(nrm, T.membrane_lights(55.0), ambient=0.03)
    pts = S.membrane_markers(N2, 8.0)
    M = 1.5e-3
    pa = TQ.punch_pressure(X2, Y2, A, P, (0.0, 0.0), pitch=P2); pb = TQ.punch_pressure(X2, Y2, A, P, (M, 0.0), pitch=P2)
    dp = TQ.tilt_shear_field(pa, pb, kb2)
    p_cur = S.displace_markers(pts, dp["ux"], dp["uy"], P2)
    m_ref = S.marker_image(S.membrane_render_markers(bg, pts, 2.5, 0.85), bg)
    m_cur = S.marker_image(S.membrane_render_markers(bg, p_cur, 2.5, 0.85), bg)
    c2 = (N2 - 1) / 2.0
    fr = TQ.grasp_torque_frame(m_ref, m_cur, 0.85, 8.0, 2.5, P2, G, NU, a=A, window=(c2, c2, (A + 1.5 * 8.0 * P2) / P2))
    M1g = TQ.pressure_first_moment(pb - pa, X2, Y2, P2)["M1"][0]
    assert fr["M1"][0] / M1g == pytest.approx(1.0, abs=0.10)
    assert fr["track"]["matched"] >= 600
    u_true = _sample((dp["ux"], dp["uy"]), fr["track"]["p0"])
    assert np.sqrt(((fr["track"]["u"] * P2 - u_true) ** 2).mean()) / P2 < 0.03
    assert abs(fr["M1"][1]) < 0.05 * abs(fr["M1"][0])
    with pytest.raises(ValueError):
        TQ.grasp_torque_frame(m_ref, m_cur, 0.85, 8.0, 2.5, 0.0, G, NU)


# ── 7. 有限要素 ─────────────────────────────────────────────────────────────────
@pytest.mark.skipif(not os.environ.get("FULLSEYE_TAXIM_DATA"), reason="FULLSEYE_TAXIM_DATA が未設定(有限要素の節点テキストは repo の外)")
def test_fem_finite_thickness_bulges_and_oblique_dipole_has_the_shear_leak_sign():
    root = os.environ["FULLSEYE_TAXIM_DATA"]
    names = ("0705_dome_node_dz_0.3", "0705_dome_node_dxdz_0.3")
    fz = S.fem_nodes_load(os.path.join(root, "calibs", names[0]), names[0])
    fx = S.fem_nodes_load(os.path.join(root, "calibs", names[1]), names[1])
    SP = 0.155e-3
    out = {}
    for f in (fz, fx):
        Pn = np.column_stack([f["X"], f["Y"]]); U = np.column_stack([f["dx"], f["dy"]])
        out[f["name"]] = {"P": Pn, "U": U, "dz": f["dz"], "dc": TQ.marker_divergence(Pn, U, 2.5 * SP)}
    c0 = out[names[0]]["P"][np.argmax(out[names[0]]["dz"])]
    o = out[names[0]]; rr = np.hypot(o["P"][:, 0] - c0[0], o["P"][:, 1] - c0[1])
    core = o["dc"]["valid"] & (rr < 0.4e-3); ring = o["dc"]["valid"] & (rr >= 0.4e-3) & (rr < 1.2e-3)
    assert core.sum() >= 10 and ring.sum() >= 50
    assert np.nanmean(o["dc"]["div"][core]) > 0.01 and np.nanmean(o["dc"]["div"][ring]) < 0.0       # 膨らみ: 半空間と符号が逆
    area = SP ** 2; win = (c0[0], c0[1], 2.0e-3)
    Dz = TQ.tactile_dipole_moment(o["P"], o["U"], "divergence", origin=(c0[0], c0[1]), area=area, rho=o["dc"]["div"], window=win)
    ox = out[names[1]]
    Dx = TQ.tactile_dipole_moment(ox["P"], ox["U"], "divergence", origin=(c0[0], c0[1]), area=area, rho=ox["dc"]["div"], window=win)
    dDx = Dx["D"][0] - Dz["D"][0]
    dtx = ox["U"][Dx["keep"]].mean(0)[0] - o["U"][Dz["keep"]].mean(0)[0]
    assert np.sign(dDx) == -np.sign(dtx)                                     # せん断 +x → 双極子 −x(Cerruti の漏れの符号)
    assert abs(Dz["D"][0] / dDx) < 0.05
