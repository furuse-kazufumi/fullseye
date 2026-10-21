import numpy as np

import matching


def test_prepared_ncc_model_owns_template_and_records_prepared_values():
    template = np.arange(20, dtype=np.float32).reshape(4, 5)
    original = template.copy()
    model = matching.create_ncc_model(template)

    template[:] = -99
    np.testing.assert_array_equal(model["template"], original.astype(np.float64))
    assert model["template"].dtype == np.float64
    assert model["dtype"] == np.dtype(np.float32)
    assert model["shape"] == (4, 5)
    assert model["origin"] == (2, 2)
    assert model["norm"] == np.linalg.norm(original - original.mean())
    np.testing.assert_allclose(np.linalg.norm(model["t0n"]), 1.0)
    assert isinstance(model["version"], str)


def test_prepared_and_raw_ncc_maps_are_bit_identical_after_caller_mutation():
    rng = np.random.default_rng(101022)
    template = rng.normal(size=(8, 7))
    original = template.copy()
    image = rng.normal(size=(35, 37))
    model = matching.create_ncc_model(template)

    raw = matching._ncc_map(original, image)
    template[:] = 1e9
    prepared = matching._ncc_map(model, image)
    np.testing.assert_array_equal(prepared, raw)
