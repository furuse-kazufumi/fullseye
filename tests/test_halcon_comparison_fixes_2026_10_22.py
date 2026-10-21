import numpy as np

import image_gen


def test_reproduced_h01_keep_pixels_preserves_matrix_and_tracks_domain():
    image = np.arange(49, dtype=np.float64).reshape(7, 7)
    region = np.zeros((7, 7), dtype=bool)
    region[2:5, 2:5] = True
    kept = image_gen.reduce_domain(image, region, keep_pixels=True)
    default = image_gen.reduce_domain(image, region)
    assert kept["image"][~region].sum() == 960
    assert default["image"][~region].sum() == 0
    np.testing.assert_array_equal(kept["image"], image)
    np.testing.assert_array_equal(image_gen.get_domain(kept), region)
    r2 = np.zeros((7, 7), dtype=bool)
    r2[3:, 1:6] = True
    chained = image_gen.reduce_domain(kept, r2, keep_pixels=True)
    np.testing.assert_array_equal(chained["domain"], region & r2)
    np.testing.assert_array_equal(chained["image"], image)
    changed = image_gen.change_domain(kept, r2, keep_pixels=True)
    np.testing.assert_array_equal(changed["domain"], r2)
    np.testing.assert_array_equal(changed["image"], image)
    cropped = image_gen.crop_domain(chained, r2, keep_pixels=True)
    np.testing.assert_array_equal(cropped["image"], image[3:7, 1:6])


def test_reproduced_h01_default_plain_array_is_bit_identical():
    image = np.arange(49, dtype=np.float64).reshape(7, 7)
    region = np.zeros((7, 7), dtype=bool)
    region[1:6, 2:5] = True
    expected = np.where(region, image, 0.0)
    actual = image_gen.reduce_domain(image, region)["image"]
    assert np.max(np.abs(actual - expected)) == 0.0
