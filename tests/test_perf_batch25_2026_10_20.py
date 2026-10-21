"""Agreement gates for performance review batch 25.

Reference helpers intentionally preserve the pre-optimisation arithmetic.
"""

import numpy as np
from scipy import ndimage
from scipy import fft

import occupancy
import varmodel
import mathnumerics
import mathspectral
import deconvstop
import tacscalib
import specularity


def _inflate_reference(occ, radius, voxel_size=1.0):
    occ = np.asarray(occ, bool)
    if radius == 0.0 or not occ.any():
        return occ.copy()
    if occ.all():
        field = np.full(occ.shape, -np.inf, np.float64)
    else:
        field = (ndimage.distance_transform_edt(~occ, sampling=voxel_size)
                 - ndimage.distance_transform_edt(occ, sampling=voxel_size))
    return field <= radius


def _esdf_reference(occ, voxel_size=1.0):
    occ = np.asarray(occ, bool)
    if not occ.any():
        return np.full(occ.shape, np.inf)
    if occ.all():
        return np.full(occ.shape, -np.inf)
    return (ndimage.distance_transform_edt(~occ, sampling=voxel_size)
            - ndimage.distance_transform_edt(occ, sampling=voxel_size))


def _occupancy_grid_reference(points, bounds, res):
    points = np.asarray(points, np.float64)
    bounds = np.asarray(bounds, np.float64)
    res = np.broadcast_to(np.asarray(res, np.int64), (3,))
    frac = (points - bounds[:, 0]) / (bounds[:, 1] - bounds[:, 0])
    frac = frac[np.all((frac >= 0.0) & (frac <= 1.0), axis=1)]
    idx = np.minimum((frac * res).astype(np.int64), res - 1)
    grid = np.zeros(tuple(res), bool)
    grid[idx[:, 0], idx[:, 1], idx[:, 2]] = True
    return grid


def _query_distance_reference(esdf_grid, bounds, res, query_points):
    bounds = np.asarray(bounds, np.float64)
    res = np.broadcast_to(np.asarray(res, np.int64), (3,))
    c = ((query_points - bounds[:, 0]) / (bounds[:, 1] - bounds[:, 0])
         * res - 0.5)
    c0 = np.floor(c).astype(np.int64)
    t = c - c0
    out = np.zeros(len(query_points), np.float64)
    for dx in (0, 1):
        wx = t[:, 0] if dx else 1.0 - t[:, 0]
        i = np.clip(c0[:, 0] + dx, 0, res[0] - 1)
        for dy in (0, 1):
            wy = t[:, 1] if dy else 1.0 - t[:, 1]
            j = np.clip(c0[:, 1] + dy, 0, res[1] - 1)
            for dz in (0, 1):
                wz = t[:, 2] if dz else 1.0 - t[:, 2]
                k = np.clip(c0[:, 2] + dz, 0, res[2] - 1)
                out += wx * wy * wz * esdf_grid[i, j, k]
    return out


def _lomb_scargle_reference(t, y, freqs):
    f = np.asarray(freqs, np.float64)
    yc = y - np.mean(y)
    w = 2.0 * np.pi * f[:, None]
    tau = (np.arctan2(np.sum(np.sin(2 * w * t), axis=1),
                      np.sum(np.cos(2 * w * t), axis=1))[:, None] / (2 * w))
    arg = w * (t[None, :] - tau)
    c, s = np.cos(arg), np.sin(arg)
    cc, ss = np.sum(c * c, axis=1), np.sum(s * s, axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        return 0.5 * (np.where(cc > 0, (c @ yc) ** 2 / cc, 0.0)
                      + np.where(ss > 0, (s @ yc) ** 2 / ss, 0.0))


def _chebyshev_coeffs_reference(values):
    coeffs = values[tuple(slice(None, None, -1) for _ in values.shape)]
    for axis, n in enumerate(values.shape):
        coeffs = fft.dct(coeffs, type=1, axis=axis) / (n - 1)
        for end in (0, n - 1):
            index = [slice(None)] * values.ndim
            index[axis] = end
            coeffs[tuple(index)] *= 0.5
    return coeffs


def _chebyshev_eval_reference(coeffs, points):
    bases = [np.cos(np.arange(coeffs.shape[axis])[None, :]
                    * np.arccos(points[:, axis])[:, None])
             for axis in range(coeffs.ndim)]
    letters = "abcdefgh"[:coeffs.ndim]
    spec = letters + "," + ",".join("m" + x for x in letters) + "->m"
    return np.einsum(spec, coeffs, *bases, optimize=True)


def test_269_inflate_matches_two_edt_reference(monkeypatch):
    rng = np.random.default_rng(269)
    fixtures = [np.zeros((9, 8, 7), bool), np.ones((9, 8, 7), bool),
                rng.random((9, 8, 7)) < 0.2]
    for occ in fixtures:
        original = occ.copy()
        for radius in (0.0, 1.3, 20.0):
            for spacing in (1.0, (0.5, 1.5, 2.0)):
                assert np.array_equal(occupancy.inflate(occ, radius, spacing),
                                      _inflate_reference(occ, radius, spacing))
        assert np.array_equal(occ, original)

    calls = 0
    real = occupancy.ndimage.distance_transform_edt

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return real(*args, **kwargs)

    monkeypatch.setattr(occupancy.ndimage, "distance_transform_edt", counted)
    occupancy.inflate(fixtures[-1], 2.0)
    assert calls == 1


def test_270_esdf_matches_reference_and_preserves_input():
    rng = np.random.default_rng(270)
    occ = rng.random((17, 15, 13)) < 0.3
    before = occ.copy()
    got = occupancy.esdf(occ, (0.5, 1.0, 2.0))
    assert np.array_equal(got, _esdf_reference(occ, (0.5, 1.0, 2.0)))
    assert np.array_equal(occ, before)


def test_271_272_query_distance_chunked_matches_reference():
    rng = np.random.default_rng(271)
    grid = rng.normal(size=(19, 17, 13))
    points = rng.uniform(-2.0, 3.0, size=(10003, 3))
    bounds = ((-1.0, 2.0), (-0.5, 1.5), (0.0, 1.0))
    expected = _query_distance_reference(grid, bounds, grid.shape, points)
    got = occupancy.query_distance(grid, bounds, grid.shape, points, chunk=127)
    assert np.array_equal(got, expected)


def test_273_occupancy_grid_chunked_matches_reference():
    rng = np.random.default_rng(273)
    points = rng.uniform(-0.2, 1.2, size=(10003, 3))
    points[:2] = (0.0, 1.0, 0.5), (1.0, 0.0, 1.0)
    bounds = ((0.0, 1.0),) * 3
    expected = _occupancy_grid_reference(points, bounds, (23, 19, 17))
    got = occupancy.occupancy_grid(points, bounds, (23, 19, 17), chunk=127)
    assert np.array_equal(got, expected)


def test_281_chebyshev_decay_matches_original_reductions():
    rng = np.random.default_rng(281)
    values = rng.normal(size=(9, 8, 7))
    got = mathnumerics.chebyshev_coeffs_nd(values)
    coeffs = got["coeffs"]
    expected = [np.abs(np.moveaxis(coeffs, axis, 0))
                .reshape(coeffs.shape[axis], -1).max(axis=1)
                for axis in range(coeffs.ndim)]
    assert expected
    for actual, reference in zip(got["decay"], expected):
        assert np.array_equal(actual, reference)


def test_279_280_chebyshev_fast_variants_match_references():
    rng = np.random.default_rng(280)
    values = rng.normal(size=(11, 10, 9, 8))
    exact_coeffs = _chebyshev_coeffs_reference(values)
    fast = mathnumerics.chebyshev_coeffs_nd(values, method="fast")["coeffs"]
    np.testing.assert_allclose(fast, exact_coeffs, rtol=0.0, atol=1e-12)
    points = rng.uniform(-1.0, 1.0, size=(1003, values.ndim))
    expected = _chebyshev_eval_reference(exact_coeffs, points)
    got = mathnumerics.chebyshev_eval_nd(exact_coeffs, points, method="fast")
    np.testing.assert_allclose(got, expected, rtol=0.0, atol=1e-12)


def test_282_lomb_scargle_chunked_matches_reference():
    rng = np.random.default_rng(282)
    t = np.sort(rng.uniform(1e8, 1e8 + 100.0, 301))
    y = rng.normal(size=len(t))
    freq = np.linspace(0.001, 2.0, 1003)
    expected = _lomb_scargle_reference(t, y, freq)
    got = mathspectral.lomb_scargle(t, y, freq, chunk=37)["power"]
    np.testing.assert_allclose(got, expected, rtol=0.0, atol=1e-12)


def test_274_276_rl_compact_path_matches_history_reference(monkeypatch):
    rng = np.random.default_rng(274)
    image = rng.poisson(20.0, size=(32, 33)).astype(np.float64)
    kwargs = {"tau": 1e-12, "max_iter": 12, "plateau_window": 20,
              "plateau_rtol": 1e-300}
    reference = deconvstop.iv_richardson_lucy_until(
        image, keep_history=True, **kwargs)
    calls = 0
    original_conj = deconvstop.np.conj

    def counted_conj(value):
        nonlocal calls
        calls += 1
        return original_conj(value)

    monkeypatch.setattr(deconvstop.np, "conj", counted_conj)
    got = deconvstop.iv_richardson_lucy_until(
        image, keep_history=False, **kwargs)
    assert calls == 1
    assert "discrepancy_history" not in got
    assert got["status"] == reference["status"]
    assert got["n_iter"] == reference["n_iter"]
    assert got["discrepancy"] == reference["discrepancy"]
    assert np.array_equal(got["last_iterate"], reference["last_iterate"])


def test_259_lights_fit_reuses_lstsq_singular_values(monkeypatch):
    rng = np.random.default_rng(259)
    normals = rng.normal(size=(40, 41, 3))
    normals /= np.linalg.norm(normals, axis=2, keepdims=True)
    mask = np.ones(normals.shape[:2], bool)
    ambient = np.array([0.1, 0.2, 0.3])
    lights = rng.normal(size=(3, 3))
    image = ambient + np.einsum("hwk,ck->hwc", normals, lights)

    def forbidden(*args, **kwargs):
        raise AssertionError("separate condition-number SVD was executed")

    monkeypatch.setattr(tacscalib.np.linalg, "svd", forbidden)
    got = tacscalib.lights_fit_from_sphere(image, normals, mask)
    np.testing.assert_allclose(got["L"], lights, rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(got["ambient"], ambient, rtol=0.0, atol=1e-12)


def test_261_membrane_prediction_chunked_matches_original():
    rng = np.random.default_rng(261)
    normals = rng.normal(size=(73, 67, 3))
    coef = rng.normal(size=(4, 6, 3))
    ys, xs = np.mgrid[:normals.shape[0], :normals.shape[1]]
    basis = tacscalib._pos_basis(ys.ravel(), xs.ravel(), "unit", normals.shape[:2])
    field = np.einsum("pk,fkc->pfc", basis, coef)
    flat = normals.reshape(-1, 3)
    expected = (field[:, 0] + np.einsum("pk,pkc->pc", flat, field[:, 1:]))
    fit = {"L": np.zeros((3, 3)), "order": 2, "coef": coef,
           "image_shape": normals.shape[:2]}
    got = tacscalib.membrane_predict_rgb(normals, fit, chunk=113)
    assert np.array_equal(got, expected.reshape(got.shape))


def test_262_265_lut_chunks_match_original_results():
    rng = np.random.default_rng(262)
    count = 20000
    normals = rng.normal(size=(count, 3))
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    rgb = rng.normal(size=(count, 3))
    pos = rng.uniform((0, 0), (79, 80), size=(count, 2))
    one = tacscalib.gradient_lut_build(
        rgb, normals, 24, positions=pos, image_shape=(80, 81), chunk=count)
    split = tacscalib.gradient_lut_build(
        rgb, normals, 24, positions=pos, image_shape=(80, 81), chunk=127)
    for key in ("mean_rgb", "count", "coef"):
        assert np.array_equal(one[key], split[key], equal_nan=True)
    image = rng.normal(size=(80, 81, 3))
    a = tacscalib.gradient_lut_invert(image, one, method="coarse", chunk=100000)
    b = tacscalib.gradient_lut_invert(image, one, method="coarse", chunk=37)
    assert np.array_equal(a, b)
    tree = tacscalib.gradient_lut_build(
        rgb, normals, 24, positions=pos, image_shape=(80, 81), chunk=127,
        pool_method="tree")
    tree_again = tacscalib.gradient_lut_build(
        rgb, normals, 24, positions=pos, image_shape=(80, 81), chunk=127,
        pool_method="tree")
    assert np.array_equal(tree["coef"], tree_again["coef"], equal_nan=True)
    assert np.all(np.isfinite(tree["coef"]))


def test_256_calibration_map_matches_full_score_without_explanations(monkeypatch):
    rng = np.random.default_rng(256)
    center = rng.normal(size=(48, 52))
    model = {
        "center": center, "spread": np.full(center.shape, 0.7),
        "valid": np.ones(center.shape, bool), "k": 2.5, "far": 0.01,
        "spread_kind": "std", "n": 20,
        "alignment": {"observable": False, "max_misalign_px": 0.5},
    }
    image = center + rng.normal(scale=0.3, size=center.shape)
    full = varmodel.varmodel_score(image, model, align="translate")
    z, valid = varmodel._calibration_z_valid(image, model)
    assert np.array_equal(z, full["z"])
    assert np.array_equal(valid, full["valid"])

    def forbidden(*args, **kwargs):
        raise AssertionError("calibration executed explanation work")

    monkeypatch.setattr(varmodel._stats(), "binom", forbidden)
    monkeypatch.setattr(varmodel.ndimage if hasattr(varmodel, "ndimage") else ndimage,
                        "label", forbidden)
    # Enough pixels for the far-tail gate; a zero offset avoids unrelated FFT work.
    out = varmodel.varmodel_calibrate(model, np.stack([image] * 5), far=0.01)
    assert out["calibration_n_pixels"] == image.size * 5


def test_249_mad_chunks_match_original_full_stack(monkeypatch):
    rng = np.random.default_rng(249)
    stack = rng.normal(size=(9, 48, 51))
    center = np.median(stack, axis=0)
    spread = np.median(np.abs(stack - center), axis=0) * varmodel._MAD_TO_SIGMA
    monkeypatch.setattr(varmodel, "_alignment", lambda a, tol: (
        np.zeros((len(a), 2)), np.zeros(len(a)), np.ones(len(a)), 0.0, False))
    got = varmodel.varmodel_fit(
        stack, spread="mad", spread_floor=1e-9, chunk=113)
    assert np.array_equal(got["center"], center)
    assert np.array_equal(got["spread"], spread)


def test_253_separable_fourier_phase_matches_original():
    rng = np.random.default_rng(253)
    image = rng.normal(size=(71, 67))
    dr, dc = 2.35, -1.7
    p = int(np.ceil(max(abs(dr), abs(dc)))) + 16
    big = np.pad(image, p, mode="symmetric")
    fr = np.fft.fftfreq(big.shape[0])[:, None]
    fc = np.fft.fftfreq(big.shape[1])[None, :]
    phase = np.exp(-2j * np.pi * (fr * dr + fc * dc))
    expected = np.fft.ifft2(np.fft.fft2(big) * phase).real[
        p:p + image.shape[0], p:p + image.shape[1]]
    got = varmodel._fourier_shift(image, dr, dc)
    np.testing.assert_allclose(got, expected, rtol=0.0, atol=1e-12)


def test_255_translate_maps_matches_roll_then_clear():
    rng = np.random.default_rng(255)
    z = rng.normal(size=(31, 29))
    valid = rng.random(z.shape) > 0.2
    for ir, ic in ((3, -2), (-4, 5), (0, 7)):
        expected_z = np.roll(z, (ir, ic), axis=(0, 1))
        expected_valid = np.roll(valid, (ir, ic), axis=(0, 1))
        if ir > 0:
            expected_valid[:ir] = False
        elif ir < 0:
            expected_valid[ir:] = False
        if ic > 0:
            expected_valid[:, :ic] = False
        elif ic < 0:
            expected_valid[:, ic:] = False
        expected_z = np.where(expected_valid, expected_z, 0.0)
        got_z, got_valid = varmodel._translate_maps(z, valid, ir, ic)
        assert np.array_equal(got_z, expected_z)
        assert np.array_equal(got_valid, expected_valid)


def test_257_calibration_preallocation_matches_concatenated_reference():
    rng = np.random.default_rng(257)
    center = rng.normal(size=(48, 52))
    model = {"center": center, "spread": np.ones(center.shape),
             "valid": np.ones(center.shape, bool), "k": 3.0, "far": 0.01,
             "spread_kind": "std", "n": 20,
             "alignment": {"observable": False}}
    images = rng.normal(size=(5,) + center.shape)
    reference = np.concatenate([
        np.abs(varmodel._calibration_z_valid(image, model)[0]).ravel()
        for image in images])
    out = varmodel.varmodel_calibrate(
        model, images, far=0.01)
    assert out["calibration_n_pixels"] == 5 * center.size
    assert out["k"] == np.quantile(reference, 0.99)


def test_258_only_first_offset_iteration_requests_psr(monkeypatch):
    calls = []

    def fake(win, spectrum, image, need_psr=True):
        calls.append(need_psr)
        return (0.2, -0.1, 7.0) if len(calls) < 3 else (0.0, 0.0, 0.0)

    monkeypatch.setattr(varmodel, "_offset_once", fake)
    monkeypatch.setattr(varmodel, "_fourier_shift", lambda image, dr, dc: image)
    got = varmodel._offset(np.ones((8, 8)), np.ones((8, 8)))
    assert calls == [True, False, False]
    assert got == (0.4, -0.2, 7.0)


def test_254_model_reference_cache_reuses_and_invalidates(monkeypatch):
    center = np.arange(256, dtype=np.float64).reshape(16, 16)
    model = {"center": center, "spread": np.ones(center.shape),
             "valid": np.ones(center.shape, bool), "k": 3.0, "far": 0.01,
             "spread_kind": "std", "n": 20,
             "alignment": {"observable": True, "max_misalign_px": 1.0}}
    calls = 0
    original = varmodel._ref_spec

    def counted(image):
        nonlocal calls
        calls += 1
        return original(image)

    monkeypatch.setattr(varmodel, "_ref_spec", counted)
    varmodel.varmodel_score(center, model)
    varmodel.varmodel_score(center, model)
    assert calls == 1
    model["center"] = center + 1.0
    varmodel.varmodel_score(center + 1.0, model)
    assert calls == 2


def test_284_combined_polarization_matches_three_original_entries(monkeypatch):
    rng = np.random.default_rng(284)
    diffuse = rng.uniform(0.2, 1.0, size=(81, 79))
    polarized = rng.uniform(0.0, 0.2, size=diffuse.shape)
    frames = specularity.polarization_render(diffuse, polarized)
    expected_d, expected_s = specularity.polarization_separate(frames)
    expected_p = specularity.polarization_dolp_map(frames)
    expected_stokes = specularity.polarization_stokes(frames)
    calls = 0
    original = specularity._polar_fit

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(specularity, "_polar_fit", counted)
    got = specularity.polarization_analyze(frames)
    assert calls == 1
    assert np.array_equal(got["diffuse"], expected_d)
    assert np.array_equal(got["specular"], expected_s)
    assert np.array_equal(got["dolp"], expected_p)
    assert np.array_equal(got["stokes"], expected_stokes)


def test_288_grouped_material_pixels_match_boolean_reference(monkeypatch):
    rng = np.random.default_rng(288)
    labels = np.repeat(np.arange(4), 200).reshape(20, 40)
    illuminant = np.array([0.4, 0.5, 0.7])
    illuminant /= np.linalg.norm(illuminant)
    bodies = rng.uniform(0.1, 1.0, size=(4, 3))
    image = np.empty(labels.shape + (3,))
    for label in range(4):
        count = np.sum(labels == label)
        image[labels == label] = (
            rng.uniform(0.2, 1.0, count)[:, None] * bodies[label]
            + rng.uniform(0.0, 0.8, count)[:, None] * illuminant)
    expected = specularity.illuminant_from_dichromatic_planes(image, labels)
    perm = rng.permutation(labels.size)
    got = specularity.illuminant_from_dichromatic_planes(
        image.reshape(-1, 3)[perm].reshape(image.shape),
        labels.ravel()[perm].reshape(labels.shape))
    np.testing.assert_allclose(got, expected, rtol=0.0, atol=1e-12)


def test_286_robust_stereo_chunk_variant_matches_exact():
    rng = np.random.default_rng(286)
    lights = rng.normal(size=(7, 3))
    lights /= np.linalg.norm(lights, axis=1, keepdims=True)
    normals = rng.normal(size=(31, 29, 3))
    normals /= np.linalg.norm(normals, axis=2, keepdims=True)
    images = np.einsum("nk,hwk->nhw", lights, normals)
    images[0, 3:20, 4:22] += 2.0
    exact = specularity.photometric_stereo_robust(images, lights)
    split = specularity.photometric_stereo_robust(images, lights, chunk=37)
    np.testing.assert_allclose(split[0], exact[0], rtol=0.0, atol=1e-6,
                               equal_nan=True)
    np.testing.assert_allclose(split[1], exact[1], rtol=0.0, atol=1e-6,
                               equal_nan=True)
    assert np.array_equal(split[2], exact[2])
