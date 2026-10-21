import numpy as np

import image_gen
import ops
import fslib
import pytest
import motionmag


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


def test_reproduced_h05_absolute_distance_is_not_normalized():
    fn = ops._BY_NAME["dist_transform_abs"].fn
    for size, peak in ((3, 2.0), (9, 5.0)):
        square = np.zeros((size + 2, size + 2), dtype=np.float64)
        square[1:-1, 1:-1] = 1
        assert fn(square, 0.0, 0.0).dtype == np.float64
        assert fn(square, 0.0, 0.0).max() == peak
    mask = np.zeros((5, 5), dtype=np.float64)
    mask[2, 2] = 1
    assert fn(mask, 0.4, 0.6)[0, 0] == 4.0
    assert fn(mask, 0.8, 0.6)[0, 0] == 2.0
    assert ops._BY_NAME["dist_transform"].fn(np.ones((9, 9)), 0, 0).max() == 1.0


def test_reproduced_h06_mean_width_height_are_independent_and_odd():
    image = np.arange(63, dtype=np.float64).reshape(7, 9)
    fn = ops._BY_NAME["mean_box_wh"].fn
    expected = ops._BY_NAME["mean_box"].fn(image, 0.0, 0.0)
    actual = fn(image, 0.125, 0.125)  # both map to 3
    np.testing.assert_array_equal(actual, expected)
    horizontal = fn(image, 0.26, 0.01)  # width 5, height 1
    vertical = fn(image, 0.01, 0.26)  # width 1, height 5
    assert not np.array_equal(horizontal, vertical)


def test_reproduced_h08_connection_neighborhood_and_limit():
    mask = np.eye(2, dtype=bool)
    reg = fslib.Region(mask)
    for backend in fslib.backends_for("connection"):
        profile_name = "reference" if backend == "numpy" else "industrial"
        with fslib.profile(profile_name):
            assert len(fslib.connection(reg).ids) == 1
            assert len(fslib.connection(reg, neighborhood=4).ids) == 2
            with pytest.raises(fslib.FsValueError, match="count 2.*limit 1"):
                fslib.connection(reg, neighborhood=4, max_connection=1)
    with pytest.raises(fslib.FsValueError):
        fslib.connection(reg, neighborhood=6)


def test_reproduced_h14_limit_precedes_stack_and_describes_allocation(monkeypatch):
    frames = [np.zeros((4, 5), dtype=np.uint16) for _ in range(3)]

    def forbidden_stack(*args, **kwargs):
        raise AssertionError("np.stack must not run before the size gate")

    monkeypatch.setattr(motionmag.np, "stack", forbidden_stack)
    with pytest.raises(ValueError) as exc:
        motionmag._require_video(frames, "video", "probe", max_elements=59)
    message = str(exc.value)
    assert "(3, 4, 5)" in message
    assert "uint16" in message
    assert "60 elements" in message
    assert "480 bytes" in message
