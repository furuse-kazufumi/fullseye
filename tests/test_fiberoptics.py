# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""fiberoptics の門: 遮断は Bessel の零点、モード数は V²/2、b(V) と MFD は公表の近似式、溶融石英の分散は公表値。"""
from __future__ import annotations

import numpy as np
import pytest
from scipy import special

import fiberoptics as F


def test_cutoffs_are_bessel_zeros():
    j01 = float(special.jn_zeros(0, 1)[0])
    j11 = float(special.jn_zeros(1, 1)[0])
    assert F.fiber_lp_modes(j01 - 1e-3)["n_modes"] == 2
    assert F.fiber_lp_modes(j01 + 1e-3)["n_modes"] == 6
    assert F.fiber_lp_modes(j11 + 1e-3)["n_modes"] == 10        # LP21 (algebraic approach)
    assert F.fiber_lp_modes(j11 + 5e-2)["n_modes"] == 12        # LP02 (exponentially weak near cutoff)
    v = F.fiber_v_number(4.1, 0.12, 1550.0)
    assert v["single_mode"] and abs(2 * np.pi * 4.1 * 0.12 / (v["cutoff_wavelength_nm"] / 1000.0) - j01) < 1e-9


def test_mode_count_and_b_follow_published_approximations():
    big = F.fiber_lp_modes(30.0)
    assert abs(big["n_modes"] / big["count_approx"] - 1) < 0.02
    Vs = np.linspace(1.6, 2.4, 9)
    assert len(Vs) == 9
    worst = max(abs(F.fiber_lp_modes(float(V))["modes"][0]["b"] / (1.1428 - 0.996 / V) ** 2 - 1) for V in Vs)
    assert worst < 0.005
    for m in F.fiber_lp_modes(6.0)["modes"]:
        assert 0.0 < m["b"] < 1.0 and abs(m["u"] ** 2 + m["w"] ** 2 - 36.0) < 1e-9


def test_mode_field_diameter_matches_marcuse_and_definitions_differ():
    rows = [F.fiber_mode_field_diameter(4.1, V) for V in (1.2, 1.6, 2.0, 2.4)]
    assert len(rows) == 4
    assert max(abs(r["relative_difference"]) for r in rows) < 0.01
    assert rows[0]["mfd_petermann1_um"] / rows[0]["mfd_um"] - 1 > 0.05
    assert rows[-1]["overlap"] > 0.99


def test_silica_dispersion_published_values():
    ng = float(F.material_group_index("SILICA", 1549.0, 1551.0, 3)[1, 1])
    assert 1.4615 < ng < 1.4635
    D = F.material_gvd("SILICA", 1200.0, 1350.0, 151)
    i = int(np.argmin(np.abs(D[:, 1])))
    assert 1265.0 < D[i, 0] < 1280.0
    assert 21.0 < float(F.material_gvd("SILICA", 1549.0, 1551.0, 3)[1, 1]) < 23.0


def test_bundle_coupling_closed_form_and_fail_closed():
    b = F.fiber_bundle_coupling(0.5, 0.25, 1.0, 1.0, 0.0, 0.0)
    assert abs(b["acceptance"] - 0.25) < 1e-15 and abs(b["transmission"] - 0.25) < 1e-15
    with pytest.raises(ValueError, match="core index"):
        F.fiber_numerical_aperture(1.45, 1.46)
    with pytest.raises(ValueError):
        F.fiber_bundle_coupling(packing_fraction=1.5)
    with pytest.raises(ValueError):
        F.fiber_lp_modes(500.0)
    with pytest.raises(ValueError):
        F.material_gvd("SILICA", 1000.0, 9000.0, 11)              # outside the Malitson range
    na = F.fiber_numerical_aperture("SILICA", 1.40, 1550.0)       # material names resolve
    assert 0.3 < na["na"] < 0.5
