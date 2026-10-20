"""Regression gates for the 0.7.2 allocation reductions."""
import time
import tracemalloc

import numpy as np

import anomaly_patch as ap
import lockin
import spc
import stereo
import studio
import volops


def _old_pool(chans, patch, stride):
    c = np.stack(chans, axis=-1)
    h, w, _ = c.shape
    gh, gw = (h - patch) // stride + 1, (w - patch) // stride + 1
    ii = np.zeros((h + 1, w + 1, c.shape[-1]))
    ii[1:, 1:] = c.cumsum(axis=0).cumsum(axis=1)
    r0, c0 = np.arange(gh) * stride, np.arange(gw) * stride
    return (ii[r0[:, None] + patch, c0[None, :] + patch]
            - ii[r0[:, None], c0[None, :] + patch]
            - ii[r0[:, None] + patch, c0[None, :]]
            + ii[r0[:, None], c0[None, :]]) / float(patch * patch)


def _peak(fn):
    tracemalloc.start()
    result = fn()
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return result, peak


def test_pool_matches_old_and_uses_less_peak_memory():
    rng = np.random.default_rng(1)
    chans = [rng.normal(size=(256, 384)) for _ in range(51)]
    old, old_peak = _peak(lambda: _old_pool(chans, 8, 4))
    new, new_peak = _peak(lambda: ap._pool(chans, 8, 4))
    np.testing.assert_allclose(new, old, rtol=1e-12, atol=1e-12)
    assert new_peak < 0.6 * old_peak
    np.testing.assert_allclose(ap._pool(chans[:1], 7, 3), _old_pool(chans[:1], 7, 3), rtol=1e-12)


def test_census_streaming_matches_volume_including_ties_and_random():
    cases = [
        (np.zeros((9, 11)), np.zeros((9, 11))),
        (np.tile(np.arange(13), (8, 1)), np.tile(np.arange(13), (8, 1))),
        tuple(np.random.default_rng(2).normal(size=(2, 17, 19))),
    ]
    for left, right in cases:
        lc, rc = stereo.census_transform(left, 5), stereo.census_transform(right, 5)
        expected = stereo._census_cost_volume(lc, rc, 6).argmin(0).astype(float)
        np.testing.assert_array_equal(stereo.disparity_census(left, right, 6, 5), expected)
    assert np.all(stereo.disparity_census(*cases[0], max_disp=4) == 0)


def test_gauss_auto_matches_scalar_reference():
    rng = np.random.default_rng(3)
    feats = rng.normal(size=(9, 13, 11, 5))
    mean = feats.mean(0)
    xc = feats - mean
    cov = np.einsum("nijd,nije->ijde", xc, xc) / len(feats)
    expected = np.array([[ap._lw_intensity(xc[:, i, j], cov[i, j])
                          for j in range(11)] for i in range(13)])
    got = ap._gauss_fit(feats, "auto", 1e-6, "test")[2]
    np.testing.assert_allclose(got, expected, rtol=1e-12, atol=1e-12)


def _old_knn(q, bank, k):
    d2 = np.maximum((q * q).sum(1)[:, None] + (bank * bank).sum(1)[None]
                    - 2.0 * (q @ bank.T), 0.0)
    return np.sqrt(np.partition(d2, k - 1, axis=1)[:, :k]).mean(1)


def test_knn_inplace_and_bank_blocking_match_reference(monkeypatch):
    rng = np.random.default_rng(4)
    q, bank = rng.normal(size=(31, 7)), rng.normal(size=(173, 7))
    expected = _old_knn(q, bank, 5)
    np.testing.assert_allclose(ap._knn_dist(q, bank, 5), expected, rtol=1e-12, atol=1e-12)
    monkeypatch.setattr(ap, "_KNN_BANK_BLOCK", 40)
    np.testing.assert_allclose(ap._knn_dist(q, bank, 5), expected, rtol=1e-12, atol=1e-12)


def test_monte_carlo_default_seed_unchanged_and_stream_rules(monkeypatch):
    table = {"u": [1.0, 2.0, 0.5], "sensitivity": [2.0, -1.0, 3.0]}
    z = spc._mc_standardised(["normal"] * 3, None, 5000, 7, "gum_monte_carlo")
    y = z @ np.array([2.0, -2.0, 1.5])
    expected = (y.std(ddof=1), y.mean())
    got = spc.gum_monte_carlo(table, n=5000, seed=7)
    np.testing.assert_allclose([got["u_monte_carlo"][0], got["mean"][0]], expected, rtol=1e-12)
    streamed = spc.gum_monte_carlo(table, n=5000, seed=7, stream=True)
    np.testing.assert_allclose(streamed["u_monte_carlo"], got["u_monte_carlo"], rtol=1e-12)
    called = []
    original = spc._mc_standardised
    monkeypatch.setattr(spc, "_mc_standardised", lambda *a, **k: (called.append(True), original(*a, **k))[1])
    spc.gum_monte_carlo(table, n=1000, stream=True, correlation=np.eye(3))
    assert called == [True]


def test_sgm_streaming_aggregate_matches_old():
    rng = np.random.default_rng(5)
    c = rng.integers(0, 20, size=(9, 12, 7)).astype(float)
    for direction in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        expected = stereo._aggregate_dir(c, *direction, 3.0, 20.0)
        got = np.zeros_like(c)
        stereo._aggregate_dir_into(c, got, *direction, 3.0, 20.0)
        np.testing.assert_array_equal(got, expected)


def test_nearest_seed_vector_matches_grid_reference_and_peak():
    v = np.zeros((64, 65, 63), bool)
    v[3, 7, 11] = v[50, 40, 30] = True
    from scipy import ndimage
    idx = ndimage.distance_transform_edt(~v, return_distances=False, return_indices=True)
    old, old_peak = _peak(lambda: np.ascontiguousarray(idx.astype(np.int64)
                                                       - np.indices(v.shape, dtype=np.int64), dtype=float))
    new, new_peak = _peak(lambda: volops.vol_nearest_seed_vector(v))
    np.testing.assert_array_equal(new, old)
    assert new_peak < 0.7 * old_peak


def test_lockin_fused_product_matches_three_products():
    rng = np.random.default_rng(6)
    video = rng.normal(size=(40, 7, 9))
    got = lockin.lockin_demodulate(video, 5, 40)
    ph = 2 * np.pi * 5 * np.arange(40) / 40
    flat = video.reshape(40, -1)
    expected = [(2 / 40 * (np.cos(ph) @ flat)).reshape(7, 9),
                (-2 / 40 * (np.sin(ph) @ flat)).reshape(7, 9), flat.mean(0).reshape(7, 9)]
    for key, value in zip(("in_phase", "quadrature", "dc"), expected):
        np.testing.assert_allclose(got[key], value, rtol=1e-12, atol=1e-12)


def _old_is_binary(a):
    if a.dtype == bool:
        return True
    a = np.asarray(a, dtype=float) if a.dtype.kind in "iu" else a
    u = np.unique(a[np.isfinite(a)]) if a.size else a
    return u.size <= 2 and set(np.round(u, 6).tolist()).issubset({0.0, 1.0})


def test_is_binary_matches_edge_cases_and_exits_early():
    arrays = [np.array([0., 1.]), np.array([0, 1]), np.array([True, False]),
              np.array([0., 1., np.nan]), np.linspace(0, 1, 100),
              np.r_[np.tile([0., 1.], 3000), 0.5], np.array([0, 1, 2]),
              np.array([]), np.array([1.]), np.array([np.nan]), np.array([-0., 1.])]
    assert len(arrays) == 11
    assert [studio._is_binary(a) for a in arrays] == [_old_is_binary(a) for a in arrays]
    big = np.linspace(0, 1, 2048 * 2048).reshape(2048, 2048)
    def elapsed(fn):
        return min((lambda s=time.process_time(): (fn(big), time.process_time() - s)[1])() for _ in range(3))
    assert elapsed(studio._is_binary) * 20 < elapsed(_old_is_binary)


def test_too_large_patch_input_rejected_before_float_conversion(monkeypatch):
    monkeypatch.setattr(ap, "_MAX_VALUES", 1000)
    data = np.zeros((2, 30, 30), dtype=np.uint8)
    _, peak = _peak(lambda: _raises_large(data))
    assert peak < 100_000


def _raises_large(data):
    try:
        ap.patchbank_fit(data, groups=("intensity",), scales=(1.0,))
    except ValueError as exc:
        assert "values" in str(exc)
        return
    raise AssertionError("size guard did not raise")
