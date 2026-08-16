"""Public programmatic API (api.py / the `fullseye` facade) — the surface other
projects consume. Ground-truth checks that numpy-in/numpy-out works and that op
resolution matches the CLI."""
import numpy as np
import pytest

import api
import ops


def _img(n=48):
    y, x = np.mgrid[0:n, 0:n]
    return np.clip(0.5 + 0.3 * np.sin(x / 7.0) * np.cos(y / 9.0), 0, 1)


def test_apply_resolves_opname_and_halcon_alias_identically():
    f = _img()
    # gaussian is the op name; gauss_filter is its HALCON alias — both must work
    # and give the same result (same underlying RT entry).
    assert np.allclose(api.apply(f, "gaussian"), api.apply(f, "gauss_filter"))


def test_apply_returns_declared_sort():
    f = _img()
    seg = api.apply(f, "otsu")                      # image -> region
    assert set(np.unique(seg)).issubset({0.0, 1.0})
    n = api.apply(seg, "count_obj")                 # region -> feature
    assert isinstance(n, float)                     # scalar, not an array


def test_apply_output_is_finite_and_in_range_for_image_ops():
    f = _img()
    for name in ("sobel_amp", "gaussian", "clahe", "bilateral", "frei_dir"):
        out = api.apply(f, name)
        assert np.all(np.isfinite(out))
        assert out.min() >= -1e-9 and out.max() <= 1 + 1e-9, name


def test_run_pipeline_shared_and_per_stage():
    f = _img()
    shared = api.run_pipeline(f, ["gaussian", "sobel_amp", "otsu"], a=0.4, b=0.5)
    assert shared.shape == f.shape
    # per-stage knobs (the CLI cannot express this in one call)
    staged = api.run_pipeline(f, [("gaussian", 0.3, 0.5), ("sobel_amp", 0.5, 0.5),
                                  ("otsu", 0.4, 0.5)])
    assert set(np.unique(staged)).issubset({0.0, 1.0})


def test_coerce_binarizes_input_for_region_op():
    # A grayscale array handed to a region-input op is binarised at 0.5 (coerce=True).
    f = _img()
    region_in = [o for o in ops.REGISTRY if o.in_sort == "region"]
    assert region_in, "expected some region-input ops"
    op = next(o for o in region_in if o.out_sort in ("region", "feature"))
    out = api.apply(f, op.name)                     # should not raise on fractional input
    assert out is not None


def test_coerce_bool_region_input_becomes_float_mask():
    # Regression: a bool mask used to bypass coercion entirely (dtype kind "b" was
    # not in "fiu"), so ops received a bool array even though apply() promises a
    # float64 mask — and `-`/`sum` on bool raises or changes meaning.
    mask = np.zeros((24, 24), bool)
    mask[4:12, 5:15] = True
    op = next(o for o in ops.REGISTRY if o.name == "reg_erode")
    got = api._coerce_input(mask, op)
    assert isinstance(got, np.ndarray) and got.dtype == np.float64
    assert set(np.unique(got)).issubset({0.0, 1.0})
    assert np.array_equal(got > 0.5, mask)                 # re-typed, never re-valued
    # and the op result is unchanged by the coercion
    assert np.allclose(api.apply(mask, "reg_erode"),
                       api.apply(mask.astype(np.float64), "reg_erode"))


def test_coerce_two_level_grayscale_region_input_is_left_to_internal_bin():
    # Contract pin: an in-range two-level array ({0.3,0.7}) is NOT rewritten here —
    # every region op binarises at 0.5 itself, so the mask is identical, while the
    # label-reading region ops still see their gray levels.
    mask = np.zeros((24, 24), bool)
    mask[4:12, 5:15] = True
    two = np.where(mask, 0.7, 0.3)
    op = next(o for o in ops.REGISTRY if o.name == "reg_erode")
    assert api._coerce_input(two, op) is two               # passed through untouched
    assert np.allclose(api.apply(two, "reg_erode"),
                       api.apply(mask.astype(np.float64), "reg_erode"))
    labels = api.apply(two, "r3_label_to_region", a=0.0)   # levels survive coercion
    assert np.array_equal(labels > 0.5, ~mask)             # 0.3 is the lowest label
    # 3+ levels or out-of-range values are binarised, as before
    three = np.where(mask, 0.7, 0.3); three[0, 0] = 0.9
    assert set(np.unique(api._coerce_input(three, op))).issubset({0.0, 1.0})


def test_unknown_op_raises_keyerror():
    with pytest.raises(KeyError):
        api.apply(_img(), "no_such_operator_xyz")


def test_find_op_and_discovery():
    assert api.find_op("gaussian") is not None
    assert api.find_op("gauss_filter") is not None      # halcon alias
    assert api.find_op("definitely_not_an_op") is None
    names = api.op_names()
    assert "gaussian" in names and len(names) == len(ops.REGISTRY)
    assert all(r["in_sort"] == "region" for r in api.list_ops(sort="region"))


def test_fullseye_facade_reexports_api():
    import fullseye
    f = _img()
    assert fullseye.__version__ == api.__version__
    assert np.allclose(fullseye.apply(f, "gaussian"), api.apply(f, "gaussian"))
    assert fullseye.op_names() == api.op_names()
