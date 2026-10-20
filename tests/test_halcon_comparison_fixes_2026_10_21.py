import numpy as np
import pytest

import geometry2d
import image_gen


def test_reproduced_h02_domain_results_can_be_chained_and_cropped():
    image = np.arange(36, dtype=np.float64).reshape(6, 6)
    r1 = np.zeros_like(image, dtype=bool)
    r1[1:5, 1:5] = True
    r2 = np.zeros_like(image, dtype=bool)
    r2[2:, :4] = True

    first = image_gen.reduce_domain(image, r1)
    np.testing.assert_array_equal(image_gen.get_domain(first), r1)
    second = image_gen.reduce_domain(first, r2)
    np.testing.assert_array_equal(second["domain"], r1 & r2)
    np.testing.assert_array_equal(second["image"], np.where(r1 & r2, image, 0.0))

    changed = image_gen.change_domain(first, r2)
    np.testing.assert_array_equal(changed["domain"], r2)
    cropped = image_gen.crop_domain(first, r2)
    np.testing.assert_array_equal(cropped["image"], first["image"][2:6, 0:4])
    np.testing.assert_array_equal(cropped["domain"], r1[2:6, 0:4])
    cropped_rel = image_gen.crop_domain_rel(first, r2, top=1, left=1, bottom=1, right=1)
    np.testing.assert_array_equal(cropped_rel["image"], first["image"][3:5, 1:3])
    np.testing.assert_array_equal(cropped_rel["domain"], r1[3:5, 1:3])


def test_reproduced_h03_rectangle_intersection_defaults_to_exact_and_grid_converges():
    cases = [
        (0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 1.0, 1.0),
        (0.0, 0.0, np.pi / 4, 1.0, 1.0, 0.0, 0.0, np.pi / 4, 1.0, 1.0),
        (1e5, -1e5, np.pi / 3, 3.0, 0.02, 1e5, -1e5, np.pi / 3, 3.0, 0.02),
    ]
    for args in cases:
        expected = 4.0 * args[3] * args[4]
        assert geometry2d.area_intersection_rectangle2(*args) == pytest.approx(expected, abs=2e-10)

    square = cases[1]
    exact = geometry2d.area_intersection_rectangle2(*square)
    error_60 = abs(geometry2d.area_intersection_rectangle2(*square, n=60, method="grid") - exact)
    error_600 = abs(geometry2d.area_intersection_rectangle2(*square, n=600, method="grid") - exact)
    assert error_600 < error_60 < 0.2

    containment = (0, 0, 0.2, 3, 2, 0, 0, 0.2, 1, 0.5)
    assert geometry2d.area_intersection_rectangle2(*containment) == pytest.approx(2.0)
    assert geometry2d.area_intersection_rectangle2(0, 0, 0, 1, 1, 0, 5, 0, 1, 1) == 0.0
    assert geometry2d.area_intersection_rectangle2(0, 0, 0, 1, 1, 0, 2, 0, 1, 1) == 0.0
    shifted = tuple(v + 1e5 if i in {0, 1, 5, 6} else v for i, v in enumerate(containment))
    assert geometry2d.area_intersection_rectangle2(*shifted) == pytest.approx(2.0, abs=1e-8)
