"""音響物性の単一表化と自由キャリア吸収配線の回帰門。"""
from __future__ import annotations

import numpy as np
import pytest

import materials as M
import ultrasound as U


EXPECTED = {
    "water": (998.0, 1481.0, 2.4983048258985403e-14, 2.0, True),
    "silicon": (2329.0, 8430.0, 0.0, 2.0, True),
    "sio2": (2203.0, 5914.614951608688, 0.0, 2.0, True),
    "copper": (8935.0, 4778.2383025422, 0.0, 1.0, True),
    "air": (1.2041, 343.0, 0.0, 2.0, True),
    "polyimide": (1420.0, 2300.0, 1.0e-6, 1.0, False),
    "epoxy_underfill": (1800.0, 2800.0, 2.0e-6, 1.0, False),
}


def test_ultrasound_builtin_values_are_bit_identical_to_pre_unification_table():
    table = U.acoustic_material_table()["materials"]
    for name, (rho, speed, alpha0, alpha_n, verified) in EXPECTED.items():
        row = table[name]
        assert row["rho"] == rho
        assert row["c"] == speed
        assert row["alpha0"] == alpha0
        assert row["alpha_n"] == alpha_n
        assert row["verified"] is verified
        assert row["Z"] == rho * speed


def test_each_acoustic_material_is_one_material_record_with_provenance():
    for alias in EXPECTED:
        acoustic = M.material_acoustic(alias)
        record = M.material_record(alias)
        assert acoustic["acoustic_source"]
        assert acoustic["acoustic_source"] == record["properties"]["acoustic_source"]
        assert acoustic["acoustic_impedance_mrayl"] == (
            acoustic["density_kg_m3"] * acoustic["sound_speed_longitudinal_m_s"] / 1e6)


def test_impedance_mismatch_is_closed_form_and_symmetric():
    a, b = M.material_acoustic("water"), M.material_acoustic("silicon")
    z1, z2 = a["acoustic_impedance_mrayl"], b["acoustic_impedance_mrayl"]
    exact = ((z2 - z1) / (z2 + z1)) ** 2
    ab = M.acoustic_impedance_mismatch("water", "silicon")
    ba = M.acoustic_impedance_mismatch("silicon", "water")
    assert ab["reflection"] == exact
    assert ba["reflection"] == exact
    assert ab["transmission"] == 1.0 - exact


def test_doped_si_transmittance_drops_monotonically_and_none_is_identical():
    args = ("SI", 0.775, 1200.0, 1201.0, 2)
    old_path = M.material_transmittance(*args, include_fresnel=False)
    none_path = M.material_transmittance(*args, include_fresnel=False, doping_cm3=None)
    assert np.array_equal(old_path, none_path)
    low = M.material_transmittance(*args, include_fresnel=False, doping_cm3=1e15)
    high = M.material_transmittance(*args, include_fresnel=False, doping_cm3=1e18)
    assert old_path[0, 1] > low[0, 1] > high[0, 1]
    # 期待値は既存の λ² 自由キャリア吸収を合成した閉形式から導く。
    fc = M.silicon_free_carrier_absorption(1e18, "n", 1200.0, 1201.0, 2)[0, 1]
    assert high[0, 1] == old_path[0, 1] * np.exp(-fc * 0.775 * 0.1)


def test_doping_unknown_or_unsupported_material_fails_closed():
    with pytest.raises(ValueError, match="unknown material"):
        M.material_transmittance("NOT_A_MATERIAL", doping_cm3=1e18)
    with pytest.raises(ValueError, match="free-carrier coefficients not available for GE"):
        M.material_transmittance("GE", 0.775, 1200.0, 1201.0, 2, doping_cm3=1e18)
    with pytest.raises(ValueError, match="acoustic properties not available"):
        M.material_acoustic("GE")
