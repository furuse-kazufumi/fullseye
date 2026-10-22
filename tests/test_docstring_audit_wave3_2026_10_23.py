"""Executable witnesses for the completed wave-3 contract corrections."""
import inspect

import numpy as np
import pytest

import colortransport
import demops
import interferometry
import optics
import optscene
import pcl_augment
import pegsim
import profileops
import pxrd
import roadjp
import segcontour


@pytest.mark.parametrize(
    ("op", "statement"),
    [
        (optics.abcd_trace, "1 + |A| + |B| + |C| + |D|"),
        (roadjp.add_sign, "pole_radius + 1.2 cm"),
        (interferometry.csi_height_map, "centroid lose about three decades"),
        (demops.dem_cell_size_webmercator, "約 19 % 過小"),
        (segcontour.gvf_field, "2/(8μ + max b)"),
        (optscene.interface_budget, "42.5 Gbit/s = 5.3125 GB/s"),
        (optics.mueller_element, 'kind="retarder"'),
        (pegsim.peg_params, "カメラ像は px、画角は deg"),
        (profileops.profile_perturb, "contour の座標と同じ単位"),
    ],
)
def test_corrected_contract_is_public(op, statement):
    assert statement in inspect.getdoc(op)


def test_corrected_contracts_match_behavior():
    geometry = {"cx": 0, "cy": 0, "distance": 100, "pixel": 0.1, "wavelength": 0.5}
    with pytest.raises(ValueError, match="positive integers"):
        pxrd.detector_two_theta((2.5, 3), geometry)
    source = np.array([[0, 0], [1, 0], [0, 1.0]])
    reference = np.array([[0, 0], [1, 0], [2, 0.0]])
    with pytest.raises(ValueError, match="reference covariance is singular"):
        colortransport.gaussian_transport_map(source, reference)
    with pytest.raises(ValueError, match="clip must be > 0"):
        pcl_augment.jitter(np.empty((0, 3)), 1, clip=0)
    with pytest.raises(ValueError, match="real and unmasked"):
        optics.mueller_checks(np.eye(4, dtype=complex))
