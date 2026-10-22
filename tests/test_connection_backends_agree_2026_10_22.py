import numpy as np
import pytest

import fslib


def _fixtures():
    diagonal = np.eye(2, dtype=bool)
    border = np.zeros((12, 13), bool); border[0:3, 0:4] = True; border[-3:, -4:] = True
    holes = np.zeros((15, 15), bool); holes[1:14, 1:14] = True; holes[4:11, 4:11] = False
    holes[6:9, 6:9] = True
    line = np.zeros((9, 12), bool); line[4, 1:11] = True
    empty = np.zeros((7, 8), bool)
    full = np.ones((7, 8), bool)
    random = np.random.default_rng(20261022).random((300, 300)) > 0.82
    return [diagonal, border, holes, line, empty, full, random]


def _result(mask, neighborhood, profile_name):
    with fslib.profile(profile_name):
        reg = fslib.Region(mask)
        objs = (fslib.connection_opts(reg, neighborhood=4)
                if neighborhood == 4 else fslib.connection(reg))
        components = {
            frozenset(map(tuple, np.argwhere(objs.labels == label)))
            for label in objs.ids
        }
        area, row, column = fslib.region_features(objs)
        features = sorted(zip(area.tolist(), row.tolist(), column.tolist()))
        return components, np.asarray(features, dtype=np.float64).reshape(-1, 3)


@pytest.mark.parametrize("mask", _fixtures())
def test_connection_and_default_facade_are_identical(mask):
    reg = fslib.Region(mask)
    for profile_name in ("reference", "industrial"):
        if profile_name == "industrial" and "cv2" not in fslib.backends_for("connection"):
            continue
        with fslib.profile(profile_name):
            plain = fslib.connection(reg)
            facade = fslib.connection_opts(reg)
        np.testing.assert_array_equal(plain.labels, facade.labels)
        np.testing.assert_array_equal(plain.ids, facade.ids)


@pytest.mark.parametrize("neighborhood", [4, 8])
@pytest.mark.parametrize("mask", _fixtures())
def test_connection_available_backends_agree(mask, neighborhood):
    available = fslib.backends_for("connection")
    if "numpy" not in available:
        pytest.skip("numpy connection backend is not importable")
    reference = _result(mask, neighborhood, "reference")
    if "cv2" not in available:
        pytest.skip("cv2 connection backend is not importable")
    candidate = _result(mask, neighborhood, "industrial")
    assert candidate[0] == reference[0]
    np.testing.assert_allclose(candidate[1], reference[1], rtol=0, atol=1e-9)
