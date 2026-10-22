"""Executable witnesses for the completed wave-2 contract corrections."""
import inspect

import numpy as np
import pytest

import flyvision
import lightfield
import materials
import mathops
import photoncount
import raytrace
import render3d
import ultrasound


@pytest.mark.parametrize(
    ("op", "statement"),
    [
        (flyvision.traj_tau_dot, '"mode"'),
        (lightfield.lf_disparity_to_depth, "one-element ``(1,)``"),
        (materials.material_optical_constants, "``epsilon_re`` / ``epsilon_im``"),
        (materials.material_transmittance, "``T=(1-R)/(1+R)``"),
        (mathops.cplx_rational_field, "sampled zero is returned as zero"),
        (mathops.curve_locality, "otherwise the minimum mean distance"),
        (photoncount.photon_sample, "optional non-negative integer (default 0)"),
        (photoncount.anscombe_inverse, "values below"),
        (raytrace.lens_system, "smallest non-null"),
        (render3d.gyroid_isosurface, "or a level outside"),
        (ultrasound.echo_phase_polarity, "tol_deg が (0, 90)"),
    ],
)
def test_corrected_contract_is_public(op, statement):
    assert statement in inspect.getdoc(op)


def test_corrected_contracts_match_behavior():
    trajectory = flyvision.traj_tau_dot(
        [[3, 0, 0], [2, 0, 0], [1, 0, 0]], [0, 1, 2]
    )
    assert trajectory["mode"] == "point"

    assert lightfield.lf_disparity_to_depth(2.0).shape == (1,)
    assert lightfield.lf_disparity_to_depth([2.0], far_depth=-1).shape == (1,)
    with pytest.raises(ValueError, match="far_depth must be >= 0"):
        lightfield.lf_disparity_to_depth([0.0], far_depth=-1)

    optical = materials.material_optical_constants("SI", 1000)
    assert "epsilon" not in optical and {"epsilon_re", "epsilon_im"} <= optical.keys()
    t0 = materials.material_transmittance("SI", 0, wl_min_nm=1000, wl_max_nm=1001, n_points=2)
    assert t0[0, 1] < 1

    field = mathops.cplx_rational_field([0j], [], shape=(5, 5))
    assert field[2, 2] == 0j
    locality = mathops.curve_locality([[0, 0], [1, 0], [2, 0], [3, 0], [4, 0]], gaps=(2, 1))
    assert locality["ratio"][0] == 2 and locality["ratio"][1] == 1

    image = np.ones((2, 2))
    np.testing.assert_array_equal(photoncount.photon_sample(image), photoncount.photon_sample(image))
    assert photoncount.anscombe_inverse([[1.2]], mode="unbiased")[0, 0] == 0

    system = raytrace.lens_system(
        [{"R": 10, "t": 1, "n": 1.5, "ap": 4}, {"R": -10, "t": 0, "n": 1, "ap": None}],
        stop=1,
    )
    assert system["surfaces"][1]["ap"] == 4
    assert "thickness" not in inspect.signature(render3d.gyroid_isosurface).parameters
    with pytest.raises(ValueError, match="tol_deg"):
        ultrasound.echo_phase_polarity(np.ones(9), tol_deg=0)
