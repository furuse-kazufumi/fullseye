# -*- coding: utf-8 -*-
"""fit_spin_aero(ballistics: 抗力 C_d と回転 ω の同時推定)の門。実行: ``py -3.11 -m pytest tests/test_fit_spin_aero.py``

門の一覧(数字は全部この場で計算した真値との比較):
 1. 同じ模型で作った軌跡(雑音なし)から ω が 1e-3 rad/s、C_d が 1e-5(相対)で戻る(初期の C_d が真値と違っても)。符号つき: C_d が真値より大きい世界でも大きく戻る
 2. 定数 C_L の bp は ValueError(定数 C_L のマグヌスの力は大きさが ω によらず、|ω| が読めない)。bp["cl_scale"] の既定は従来と bit 一致、0.5 で横の曲がりが半分
 3. fit_cl=True: ω と κ の相関が ±0.99 超、cond が κ 固定の 10 倍以上、初期値を変えると rms が同じで ω が違う(縮退を返り値が申告する)
 4. 線形化した共分散は実測のばらつきと合う: 雑音 σ のモンテカルロで C_d の標準偏差が cov_unit·σ と 2 倍以内、ω⊥ は頑健な尺度で桁が合う
 5. ω の平行成分の標準偏差は垂直成分の 3 倍以上(読めない成分を返り値が申告する)
 6. C_d と ω⊥ の相関は 0.1 未満(直交)、C_d と初速は 0.9 超(短い区間の縮退)
 7. 入力の拒否(fail-closed): 12 点未満・NaN・時刻が増えない・omega_max が 0 以下や非有限は ValueError
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ballistics as B  # noqa: E402

P0 = np.array([-1.30, 0.0, 1.01])
V0 = np.array([6.0, 0.0, 1.3])
W0 = np.array([0.0, 150.0, 0.0])
T = np.arange(0.0, 0.3, 1.0 / 240.0)


def traj(cd=0.42, w=W0, t=T, cl_scale=None):
    bp = B.ball_params(cd=cd, cl=None)
    if cl_scale is not None:
        bp["cl_scale"] = cl_scale
    f = B.flight_ode(P0, V0, w, bp, float(t[-1]) + 1e-3, 1e-4)
    return np.column_stack([np.interp(t, f["t"], f["p"][:, k]) for k in range(3)])


def test_identity_recovers_omega_and_cd_even_from_a_wrong_start():
    P = traj(cd=0.42)
    r = B.fit_spin_aero(T, P, B.ball_params(cd=0.30, cl=None))
    assert np.linalg.norm(r["omega"] - W0) < 1e-3
    assert abs(r["cd"] - 0.42) / 0.42 < 1e-5
    assert r["rms"] < 1e-6 and not r["at_bound"]
    assert r["omega_perp"][1] > 149.0                         # 符号つき: +y の回転は +y で戻る(abs で隠さない)
    r2 = B.fit_spin_aero(T, traj(cd=0.55), B.ball_params(cd=0.30, cl=None))
    assert abs(r2["cd"] - 0.55) / 0.55 < 1e-5 and r2["cd"] > r["cd"]
    r3 = B.fit_spin_aero(T, traj(w=-W0), B.ball_params(cd=0.42, cl=None))
    assert r3["omega"][1] < -149.0                            # バックスピンは負で戻る


def test_constant_cl_is_rejected_and_cl_scale_is_bit_identical_by_default():
    with pytest.raises(ValueError, match="constant C_L"):
        B.fit_spin_aero(T, traj(), B.ball_params(cd=0.42, cl=0.2))
    bp = B.ball_params(cd=0.42, cl=None)
    a = B.flight_ode(P0, V0, W0, bp, 0.2, 1e-3)["p"]
    b = B.flight_ode(P0, V0, W0, dict(bp, cl_scale=1.0), 0.2, 1e-3)["p"]
    assert np.array_equal(a, b)                               # 係数 1 は従来と bit 一致
    base = B.flight_ode(P0, V0, [0, 0, 0], bp, 0.2, 1e-3)["p"]
    half = B.flight_ode(P0, V0, W0, dict(bp, cl_scale=0.5), 0.2, 1e-3)["p"]
    full = a
    d_half, d_full = (half - base)[-1, 2], (full - base)[-1, 2]
    assert d_full < 0 and d_half < 0                          # トップスピンは沈む(符号)
    assert 0.4 < d_half / d_full < 0.6                        # 係数 0.5 で曲がりはほぼ半分


def test_free_cl_scale_makes_omega_and_kappa_degenerate_and_says_so():
    P = traj(cd=0.42)
    bp = B.ball_params(cd=0.42, cl=None)
    fixed = B.fit_spin_aero(T, P, bp)
    rms, ws = [], []
    for w_init in (40.0, 220.0):
        r = B.fit_spin_aero(T, P, bp, fit_cl=True, omega0=[0.0, w_init, 0.0], iters=40)
        assert r["param_names"][-1] == "cl_scale" and r["corr"].shape == (11, 11)
        assert abs(r["corr"][7, 10]) > 0.99                   # ω_y と κ はほぼ完全に相関
        assert r["cond"] > 10 * fixed["cond"]
        rms.append(r["rms"])
        ws.append(float(r["omega_perp"][1]))
    assert max(rms) < 1e-3                                    # どちらの初期値でも軌跡は合う(rms < 1 mm)
    assert abs(ws[0] - ws[1]) > 20.0                          # のに ω は違う(縮退)


def test_covariance_matches_monte_carlo_scatter_and_reports_unreadable_axes():
    P = traj(cd=0.42)
    bp = B.ball_params(cd=0.42, cl=None)
    clean = B.fit_spin_aero(T, P, bp)
    sigma = 1.0e-3
    rng = np.random.default_rng(7)
    cds, wy = [], []
    for _ in range(10):
        r = B.fit_spin_aero(T, P + rng.normal(0.0, sigma, P.shape), bp)
        cds.append(r["cd"])
        wy.append(r["omega_perp"][1])
    sd_cd, sd_w = clean["cov_unit"][9, 9] ** 0.5 * sigma, clean["omega_perp_std_unit"] * sigma
    assert 0.5 < np.std(cds, ddof=1) / sd_cd < 2.0            # C_d: 線形化の標準偏差と実測が 2 倍以内
    # ω⊥: 平らな谷で 25 反復に届かない標本が混ざる(実測 10 本中 1 本、ω_x が 240 rad/s へ寄る)ので、ばらつきは頑健な尺度(MAD)で、桁が合えばよい
    mad = 1.4826 * float(np.median(np.abs(np.array(wy) - np.median(wy))))
    assert 0.3 < mad / sd_w < 4.0
    assert abs(clean["corr_cd_omega"]) < 0.1                  # 抗力と回転は直交して分かれる
    assert clean["corr_cd_v0"] > 0.9                          # C_d は初速と分けにくい
    assert clean["omega_axial_std_unit"] > 3.0 * clean["omega_perp_std_unit"]   # 平行成分は垂直成分より読めない
    assert np.allclose(clean["corr"], clean["corr"].T) and np.allclose(np.diag(clean["corr"]), 1.0)


def test_shorter_flights_are_worse():
    P = traj(cd=0.42)
    bp = B.ball_params(cd=0.42, cl=None)
    short = B.fit_spin_aero(T[:30], P[:30], bp)
    long_ = B.fit_spin_aero(T, P, bp)
    assert short["cond"] > long_["cond"]
    assert short["cov_unit"][9, 9] > 10 * long_["cov_unit"][9, 9]


def test_bad_inputs_raise_value_error():
    bp = B.ball_params(cd=0.42, cl=None)
    P = traj()
    with pytest.raises(ValueError):
        B.fit_spin_aero(T[:11], P[:11], bp)
    bad = P.copy()
    bad[3, 1] = np.nan
    with pytest.raises(ValueError):
        B.fit_spin_aero(T, bad, bp)
    t2 = T.copy()
    t2[5] = t2[4]
    with pytest.raises(ValueError):
        B.fit_spin_aero(t2, P, bp)
    for om in (0.0, -1.0, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            B.fit_spin_aero(T, P, bp, omega_max=om)
    with pytest.raises(ValueError):
        B.fit_spin_aero(T, P, bp, omega0=[1.0, 2.0])
