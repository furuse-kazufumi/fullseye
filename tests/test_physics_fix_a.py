import math
import pathlib
import sys

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "examples"))

import chromconf as cc
import poc_multibeam_bathymetry as mb


def test_const_layers_preserves_surface_ray_parameter_in_first_layer():
    prof = (np.array([0.0, 50.0]), np.array([1520.0, 1480.0]))
    theta = 65.0
    x, t = mb.trace_const_layers(prof, theta, 50.0, 1)
    c0 = float(prof[1][0])
    cm = float(np.interp(25.0, prof[0], prof[1]))
    th1 = math.asin(math.sin(math.radians(theta)) * cm / c0)
    assert x == pytest.approx(50.0 * math.tan(th1), rel=1e-12)
    assert t == pytest.approx(50.0 / (cm * math.cos(th1)), rel=1e-12)


def test_plate_lsa_matches_independent_snell_ray_trace_without_dividing_by_n():
    n, na, thickness = 1.52, 0.30, 500.0
    marginal = cc._plate_marginal_focus_um(n, na, thickness)
    paraxial = thickness / n
    exact_lsa = paraxial - marginal
    assert thickness * cc._plate_g(n, na) == pytest.approx(exact_lsa, rel=1e-12)
    assert thickness * cc._plate_g(n, na) / n != pytest.approx(exact_lsa, rel=1e-3)
