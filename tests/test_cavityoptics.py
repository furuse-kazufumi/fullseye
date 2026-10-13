# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""cavityoptics(Fabry-Perot・Michelson・PDH・量子雑音)の門。

採点は「それらしい数か」ではなく**閉形式に合うか**: Airy 透過の半値を独立に探して線幅と一致、
伝達関数は極で 1/√2・FSR で零、Michelson の傾きは有限差分と一致し散射雑音限界は φ₀ → 0 の極限へ、
PDH は反対称・共振で零・傾きが Black 2001 の式 15、量子雑音は散射 × 輻射圧 = SQL⁴/4 の恒等式と
「総和 ≥ SQL、等号は K = 1」(Kimble ら 2001)。aLIGO の公表設計値(腕 3994.5 m、T_ITM 1.4 %)で
フィネス ≈ 445・極 ≈ 42 Hz になることも見る。
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cavityoptics as C                                           # noqa: E402
import opsoptics                                                   # noqa: E402


# --------------------------------------------------------------------------- #
# 1. Fabry-Perot                                                               #
# --------------------------------------------------------------------------- #
def test_aligo_arm_cavity_has_the_published_finesse_and_pole():
    """L 3994.5 m、T_ITM 0.014、T_ETM 5 ppm(aLIGO の設計値)→ F ≈ 445、極 ≈ 42 Hz、FSR 37.53 kHz。"""
    r = C.fabry_perot_response()
    assert r["fsr_hz"] == pytest.approx(299792458.0 / (2 * 3994.5), rel=1e-12)
    assert 440.0 < r["finesse"] < 450.0
    assert 41.0 < r["pole_hz"] < 43.0
    assert r["linewidth_hz"] == pytest.approx(2 * r["pole_hz"], rel=1e-12)
    assert r["linewidth_hz"] == pytest.approx(r["linewidth_approx_hz"], rel=1e-4)
    assert r["power_gain"] == pytest.approx(0.014 / (1 - r["r1"] * r["r2"]) ** 2, rel=1e-12)
    assert r["storage_time_s"] == pytest.approx(1.0 / (2 * np.pi * r["pole_hz"]), rel=1e-12)


def test_the_airy_half_maximum_found_numerically_equals_the_closed_form_linewidth():
    """透過 T(φ) を細かく標本化して半値の交点を brentq で探し、linewidth_hz(asin 形)と 1e-9 で一致。"""
    from scipy import optimize

    for T1, T2 in ((0.014, 5e-6), (0.05, 0.05), (0.3, 0.1)):
        r = C.fabry_perot_response(1.0, itm_transmittance=T1, etm_transmittance=T2)
        F, tmax = r["finesse"], r["transmission_max"]

        def half(f_hz):
            phi = 2 * np.pi * f_hz / r["fsr_hz"]
            return C._airy_transmission(np.array([phi]), F, tmax)[0] - 0.5 * tmax

        f_half = optimize.brentq(half, 1e-9, 0.5 * r["fsr_hz"], xtol=1e-12)
        assert 2 * f_half == pytest.approx(r["linewidth_hz"], rel=1e-9), (T1, T2)


def test_a_symmetric_lossless_cavity_transmits_everything_on_resonance():
    r = C.fabry_perot_response(0.1, itm_transmittance=0.02, etm_transmittance=0.02)
    assert r["transmission_max"] == pytest.approx(1.0, abs=1e-12)
    assert r["reflection_min"] == pytest.approx(0.0, abs=1e-12)


@pytest.mark.parametrize("kw", [dict(length_m=0.0), dict(length_m=-1.0), dict(itm_transmittance=1.0),
                                dict(itm_transmittance=0.5, itm_loss=0.5), dict(etm_transmittance=-0.1),
                                dict(itm_transmittance=0.0, etm_transmittance=0.0),
                                dict(wavelength_nm=float("nan"))])
def test_fabry_perot_rejects_impossible_mirrors(kw):
    with pytest.raises(ValueError):
        C.fabry_perot_response(**kw)


# --------------------------------------------------------------------------- #
# 2. 伝達関数                                                                  #
# --------------------------------------------------------------------------- #
def test_the_transfer_function_is_one_over_root_two_at_the_pole_and_zero_at_the_fsr():
    r = C.fabry_perot_response()
    fp, fsr, F = r["pole_hz"], r["fsr_hz"], r["finesse"]
    tf = C.cavity_strain_transfer(3994.5, F, f_min_hz=fp, f_max_hz=fsr, n_points=64)
    assert tf.shape == (64, 2) and np.isfinite(tf).all()
    assert tf[0, 0] == pytest.approx(fp, rel=1e-12)
    dc = 2 * F / np.pi
    # 極の定義(γ = Tc/4L)と asin 形の極は 1e-5、sinc(2πf_pL/c) は 1 − 2e-6: 合わせて 1e-4 で見る
    assert tf[0, 1] == pytest.approx(dc / np.sqrt(2.0), rel=1e-4)
    assert tf[-1, 1] == pytest.approx(0.0, abs=dc * 1e-12)
    assert (np.diff(tf[:, 1]) < 0).all()            # 極から FSR までは単調減少
    lo = C.cavity_strain_transfer(3994.5, F, f_min_hz=1e-3, f_max_hz=1e-2, n_points=2)
    assert lo[0, 1] == pytest.approx(dc, rel=1e-8)


def test_the_transfer_function_rejects_a_reversed_band():
    with pytest.raises(ValueError):
        C.cavity_strain_transfer(f_min_hz=100.0, f_max_hz=10.0)
    with pytest.raises(ValueError):
        C.cavity_strain_transfer(n_points=1)


# --------------------------------------------------------------------------- #
# 3. Michelson の DC 読み出し                                                  #
# --------------------------------------------------------------------------- #
def test_the_strain_slope_matches_a_central_finite_difference():
    for phi0 in (0.01, 0.3, 1.5):
        m = C.michelson_dc_readout(5200.0, 3994.5, dc_offset_rad=phi0)
        eps = 1e-20                                     # 4πεL/λ ≈ 5e-10 rad: 丸め 2e-7、打ち切り 1e-20
        pa = C.michelson_dc_readout(5200.0, 3994.5, dc_offset_rad=phi0, strain=+eps)["p_out_w"]
        pb = C.michelson_dc_readout(5200.0, 3994.5, dc_offset_rad=phi0, strain=-eps)["p_out_w"]
        assert (pa - pb) / (2 * eps) == pytest.approx(m["slope_w_per_strain"], rel=1e-6), phi0


def test_the_shot_noise_limit_is_the_small_offset_limit_and_does_not_depend_on_the_offset():
    """h_shot(φ₀) = h_limit / cos(φ₀/2) → φ₀ → 0 で h_limit。φ₀ = 1e-3 で 1e-6 以内、π/2 で √2 倍。"""
    m0 = C.michelson_dc_readout(1.0, 1.0, dc_offset_rad=1e-3)
    assert m0["h_shot_per_rthz"] == pytest.approx(m0["h_shot_limit_per_rthz"], rel=1e-6)
    m1 = C.michelson_dc_readout(1.0, 1.0, dc_offset_rad=np.pi / 2)
    assert m1["h_shot_per_rthz"] == pytest.approx(np.sqrt(2.0) * m1["h_shot_limit_per_rthz"], rel=1e-12)
    # 閉形式そのもの: (1/2L)√(ħcλ/πP)
    lam = 1064e-9
    assert m0["h_shot_limit_per_rthz"] == pytest.approx(
        0.5 * np.sqrt(C.HBAR * C.C_LIGHT * lam / np.pi), rel=1e-12)
    # 光量 4 倍で限界は半分
    m4 = C.michelson_dc_readout(4.0, 1.0, dc_offset_rad=1e-3)
    assert m4["h_shot_limit_per_rthz"] == pytest.approx(0.5 * m0["h_shot_limit_per_rthz"], rel=1e-12)


@pytest.mark.parametrize("phi", [0.0, np.pi, -0.1, float("inf")])
def test_michelson_rejects_offsets_outside_the_open_interval(phi):
    with pytest.raises(ValueError):
        C.michelson_dc_readout(dc_offset_rad=phi)


# --------------------------------------------------------------------------- #
# 4. PDH                                                                       #
# --------------------------------------------------------------------------- #
def test_pdh_is_antisymmetric_zero_on_resonance_and_has_blacks_slope():
    from scipy.special import j0, j1

    e = C.pdh_error_signal(1.0, itm_transmittance=0.01, etm_transmittance=0.01,
                           mod_freq_hz=2.0e7, mod_depth=1.08, n_points=2001)
    d, eps = e[:, 0], e[:, 1]
    assert e.shape == (2001, 2) and np.isfinite(e).all()
    assert np.max(np.abs(eps + eps[::-1])) < 1e-12 * np.max(np.abs(eps))
    i0 = 1000
    assert d[i0] == 0.0 and abs(eps[i0]) < 1e-15 * np.max(np.abs(eps))
    slope = (eps[i0 + 1] - eps[i0 - 1]) / (d[i0 + 1] - d[i0 - 1])
    r = C.fabry_perot_response(1.0, itm_transmittance=0.01, etm_transmittance=0.01)
    black = -8.0 * np.sqrt(j0(1.08) ** 2 * j1(1.08) ** 2) / r["linewidth_hz"]
    assert slope == pytest.approx(black, rel=0.01)


def test_pdh_slope_is_steeper_for_a_narrower_cavity():
    s = []
    for T in (0.05, 0.01):
        e = C.pdh_error_signal(1.0, itm_transmittance=T, etm_transmittance=T, n_points=2001)
        s.append((e[1001, 1] - e[999, 1]) / (e[1001, 0] - e[999, 0]))
    assert abs(s[1]) > 3.0 * abs(s[0])


def test_pdh_rejects_a_zero_modulation():
    with pytest.raises(ValueError):
        C.pdh_error_signal(mod_freq_hz=0.0)
    with pytest.raises(ValueError):
        C.pdh_error_signal(n_points=2)


# --------------------------------------------------------------------------- #
# 5. 量子雑音                                                                  #
# --------------------------------------------------------------------------- #
def test_shot_times_radiation_pressure_is_the_sql_squared_over_two_for_any_power():
    """S_shot·S_rp = h_SQL⁴/4(振幅で shot·rp = sql²/2)—— 入射光量に依らない恒等式。"""
    for P in (10.0, 5200.0, 1e6):
        q = C.quantum_noise_budget(power_w=P)
        prod = q["shot"] ** 2 * q["radiation_pressure"] ** 2
        assert np.allclose(prod, q["sql"] ** 4 / 4.0, rtol=1e-10)
        assert (q["total"] >= q["sql"] * (1 - 1e-12)).all()
        assert np.isfinite(q["total"]).all() and (q["total"] > 0).all()


def test_the_total_touches_the_sql_exactly_at_the_cavity_pole_when_the_power_is_i_sql():
    q0 = C.quantum_noise_budget(power_w=1.0)
    fp = q0["pole_hz"]
    q = C.quantum_noise_budget(power_w=q0["i_sql_w"], f_min_hz=fp, f_max_hz=2 * fp, n_points=2)
    assert q["power_ratio"] == pytest.approx(1.0, rel=1e-12)
    assert q["kappa"][0] == pytest.approx(1.0, rel=1e-9)
    assert q["total"][0] == pytest.approx(q["sql"][0], rel=1e-9)
    assert q["f_sql_touch_hz"] == pytest.approx(fp, rel=1e-6)
    # γ = Tc/4L の極は Fabry-Perot の極(asin 形)と 1 % 以内で一致
    assert fp == pytest.approx(C.fabry_perot_response()["pole_hz"], rel=0.01)


def test_more_power_lowers_shot_noise_and_raises_radiation_pressure():
    a = C.quantum_noise_budget(power_w=1000.0)
    b = C.quantum_noise_budget(power_w=4000.0)
    assert np.allclose(b["shot"], a["shot"] / 2.0, rtol=1e-12)
    assert np.allclose(b["radiation_pressure"], a["radiation_pressure"] * 2.0, rtol=1e-12)
    assert np.allclose(a["sql"], b["sql"], rtol=1e-12)


def test_quantum_noise_rejects_a_closed_arm_and_a_reversed_band():
    with pytest.raises(ValueError):
        C.quantum_noise_budget(itm_transmittance=0.0)
    with pytest.raises(ValueError):
        C.quantum_noise_budget(f_min_hz=1000.0, f_max_hz=10.0)
    with pytest.raises(ValueError):
        C.quantum_noise_budget(mirror_mass_kg=-1.0)


# --------------------------------------------------------------------------- #
# 6. 台帳                                                                      #
# --------------------------------------------------------------------------- #
class TestLedger:
    def test_every_op_is_registered_and_implemented(self):
        assert opsoptics.missing() == []
        assert set(C.__all__) == set(opsoptics.list_ops("cavity"))
        assert len(C.__all__) == 5

    def test_declared_out_types_are_what_the_ops_return(self):
        assert isinstance(opsoptics.call("fabry_perot_response"), dict)
        tf = opsoptics.call("cavity_strain_transfer")
        assert isinstance(tf, np.ndarray) and tf.ndim == 2 and tf.shape[1] == 2
        assert isinstance(opsoptics.call("michelson_dc_readout"), dict)
        e = opsoptics.call("pdh_error_signal")
        assert isinstance(e, np.ndarray) and e.shape[1] == 2
        assert isinstance(opsoptics.call("quantum_noise_budget"), dict)

    def test_reachable_from_the_facade(self):
        import fullseye as fs

        L = fs.ledger
        r = L.fabry_perot_response(length_m=1.0, itm_transmittance=0.02, etm_transmittance=0.02)
        assert r["transmission_max"] == pytest.approx(1.0, abs=1e-12)

    def test_no_op_name_collides_with_a_two_d_registry_op(self):
        import ops

        reg = {o.name for o in ops.REGISTRY}
        assert not (set(C.__all__) & reg)
