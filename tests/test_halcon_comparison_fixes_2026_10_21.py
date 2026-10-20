import numpy as np

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
