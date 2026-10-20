"""Regression gates for the 2026-10-20 repeated-transform performance slice."""
from __future__ import annotations

import tracemalloc

import numpy as np
import pytest

import dsp
import mesh_props
import pivops
import rangedoppler
import volops


def _old_abs_sorted_eigs(e1, e2, e3):
    values = np.stack([e1, e2, e3], axis=-1)
    order = np.argsort(np.abs(values), axis=-1)
    sorted_values = np.take_along_axis(values, order, axis=-1)
    return tuple(sorted_values[..., i] for i in range(3))


def _old_spectrogram(x, rate=1.0, win=256, hop=None):
    x = dsp._require_finite(x)
    win = int(win)
    hop = win // 2 if hop is None else int(hop)
    if len(x) < win:
        x = np.pad(x, (0, win - len(x)))
    window = np.hanning(win)
    starts = range(0, len(x) - win + 1, hop)
    cols = [np.abs(np.fft.rfft(x[s:s + win] * window)) for s in starts]
    spectrum = np.stack(cols, axis=1) if cols else np.zeros((win // 2 + 1, 0))
    return (np.fft.rfftfreq(win, d=1.0 / float(rate)),
            np.array([s / float(rate) for s in starts]), spectrum)


def _old_vertex_normals(mesh):
    vertices, faces = mesh_props._as_mesh(mesh)
    cross = mesh_props._face_cross(vertices, faces)
    normals = np.zeros_like(vertices)
    for corner in range(3):
        np.add.at(normals, faces[:, corner], cross)
    magnitude = np.linalg.norm(normals, axis=1)
    scale = float(np.median(magnitude[magnitude > 0])) if np.any(magnitude > 0) else 0.0
    bad = magnitude <= mesh_props._DEGEN_REL * scale if scale > 0 else magnitude <= 0
    if np.any(bad):
        raise ValueError(f"{int(bad.sum())} vertex(es) have no defined normal"
                         " (no incident triangles, or face normals cancel out)")
    return normals / magnitude[:, None]


def _old_range_doppler_map(cube, combine="incoherent", antenna=None, normalize=False):
    arr = rangedoppler._as_beat_cube(cube, "cube", "range_doppler_map")
    na, nc, ns = arr.shape
    if antenna is not None:
        arr = arr[int(antenna):int(antenna) + 1]
    spec = rangedoppler._fft_checked(arr, 2, "range_doppler_map", "range")
    spec = rangedoppler._fft_checked(spec, 1, "range_doppler_map", "Doppler")
    spec = np.fft.fftshift(spec, axes=1)
    out = np.abs(spec.mean(axis=0)) if combine == "coherent" else np.abs(spec).mean(axis=0)
    return np.ascontiguousarray(out / float(nc * ns) if normalize else out)


def _old_cross_correlate(a, b, window=16, overlap=0.5):
    win = int(window)
    step = max(1, int(round(win * (1.0 - overlap))))
    rows = np.arange(0, a.shape[0] - win + 1, step)
    cols = np.arange(0, a.shape[1] - win + 1, step)
    taper = pivops._taper(win, "hann")
    weight = pivops._overlap_weight(win, taper)
    keep = pivops._search_mask(win, 0.25)
    flow = np.zeros((2, rows.size, cols.size))
    ratio = np.zeros((rows.size, cols.size))
    for i, r in enumerate(rows):
        for j, c in enumerate(cols):
            dy, dx, pr = pivops._correlate_window(
                a[r:r + win, c:c + win], b[r:r + win, c:c + win],
                taper, True, "gauss3", weight, keep)
            flow[:, i, j] = dy, dx
            ratio[i, j] = pr
    return flow, ratio


def _old_ensemble(images, window=16):
    win = int(window)
    rows = np.arange(0, images[0].shape[0] - win + 1, win // 2)
    cols = np.arange(0, images[0].shape[1] - win + 1, win // 2)
    taper = pivops._taper(win, "hann")
    weight = pivops._overlap_weight(win, taper)
    keep = pivops._search_mask(win, 0.25)
    flow = np.zeros((2, rows.size, cols.size))
    for i, r in enumerate(rows):
        for j, c in enumerate(cols):
            acc = np.zeros((win, win))
            for k in range(len(images) - 1):
                acc += pivops._corr_map(images[k][r:r + win, c:c + win],
                                         images[k + 1][r:r + win, c:c + win],
                                         taper, True, weight)
            search = np.where(keep, acc, -np.inf)
            pi, pj = divmod(int(np.argmax(search)), win)
            flow[0, i, j] = pi - win // 2 + pivops._subpixel(acc, pi, pj, 0, "gauss3")
            flow[1, i, j] = pj - win // 2 + pivops._subpixel(acc, pi, pj, 1, "gauss3")
    return flow


def test_abs_sorted_eigs_matches_old_for_non_ties_and_defines_ties():
    rng = np.random.default_rng(20261020)
    values = rng.normal(size=(3, 19, 23))
    got = volops._abs_sorted_eigs(*values)
    expected = _old_abs_sorted_eigs(*values)
    for actual, reference in zip(got, expected):
        np.testing.assert_array_equal(actual, reference)
    for perm in __import__("itertools").permutations((-2.0, 1.0, 3.0)):
        assert tuple(float(x) for x in volops._abs_sorted_eigs(*perm)) == tuple(
            float(x) for x in _old_abs_sorted_eigs(*perm))
    tie_patterns = [(-1.0, 1.0, -1.0), (1.0, -1.0, -1.0),
                    (-0.0, 0.0, -0.0), (-np.inf, np.inf, np.nan)]
    for pattern in tie_patterns:
        got = volops._abs_sorted_eigs(*pattern)
        if np.isnan(pattern[-1]):
            assert np.isnan(got[-1])
            np.testing.assert_array_equal(got[:2], pattern[:2])
        else:
            np.testing.assert_array_equal(got, pattern)


@pytest.mark.parametrize("length,win,hop", [(8193, 128, 37), (31, 64, 16), (64, 64, 16)])
def test_spectrogram_batched_matches_old(length, win, hop):
    x = np.sin(np.arange(length, dtype=np.float64) * 0.173) + np.arange(length) / 1e5
    expected = _old_spectrogram(x, 48000.0, win, hop)
    got = dsp.spectrogram(x, 48000.0, win, hop)
    for actual, reference in zip(got, expected):
        np.testing.assert_allclose(actual, reference, rtol=1e-12, atol=0.0)


def test_region_centroids_structured_and_dense_match_coordinate_reference():
    labels = np.zeros((48, 64, 64), dtype=np.int32)
    labels[0, 0, 0] = 1
    labels[0:4, 8:13, 60:64] = 2
    labels[8:33, 4:54, 2:62] = 3  # 75,000 dense voxels
    props = volops.vol_region_props(labels, spacing=(2.0, 3.0, 4.0), surface="faces")
    assert len(props) == 3
    for item in props:
        coords = np.argwhere(labels == item["label"])
        np.testing.assert_allclose(item["centroid"], coords.mean(axis=0), rtol=1e-12, atol=0.0)


def test_region_centroid_peak_memory_is_below_coordinate_enumeration():
    mask = np.ones((47, 47, 47), dtype=bool)
    tracemalloc.start()
    np.argwhere(mask).mean(axis=0)
    old_peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    tracemalloc.start()
    labels = mask.astype(np.int8)
    volops.vol_region_props(labels, surface="faces")
    new_peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    assert new_peak < 0.6 * old_peak


def test_vertex_normals_match_old_and_cancellation_error_count():
    vertices = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.],
                         [0., -1., 0.], [2., 0., 0.], [1., 0., 1.]])
    faces = np.array([[0, 1, 2], [0, 1, 3], [1, 4, 2], [1, 3, 4],
                      [3, 4, 5], [4, 2, 5], [2, 3, 5]])
    mesh = vertices, faces
    with pytest.raises(ValueError, match="1 vertex") as old_error:
        _old_vertex_normals(mesh)
    with pytest.raises(ValueError, match="1 vertex") as new_error:
        mesh_props.vertex_normals(mesh)
    assert str(new_error.value) == str(old_error.value)
    tetra = (np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]]),
             np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]]))
    np.testing.assert_allclose(mesh_props.vertex_normals(tetra), _old_vertex_normals(tetra),
                               rtol=1e-12, atol=1e-15)


def test_ensemble_fft_count_and_known_shift(monkeypatch):
    rng = np.random.default_rng(8)
    base = rng.normal(size=(32, 32))
    frames = [np.roll(base, k, axis=1) for k in range(30)]
    counts = {"forward": 0, "inverse": 0}
    real_forward, real_inverse = np.fft.rfft2, np.fft.irfft2
    def forward(*args, **kwargs):
        counts["forward"] += 1
        return real_forward(*args, **kwargs)
    def inverse(*args, **kwargs):
        counts["inverse"] += 1
        return real_inverse(*args, **kwargs)
    monkeypatch.setattr(np.fft, "rfft2", forward)
    monkeypatch.setattr(np.fft, "irfft2", inverse)
    flow, _ = pivops.piv_ensemble_correlate(frames, window=32, overlap=0,
                                             peak="gauss3", window_func="none",
                                             normalize="none", search_limit=None)
    assert counts == {"forward": 30, "inverse": 1}
    np.testing.assert_allclose(flow[:, 0, 0], (0.0, 1.0), atol=0.05)


def test_ensemble_matches_old_subpixel_results():
    rng = np.random.default_rng(81)
    base = rng.normal(size=(35, 39))
    frames = [np.roll(base, k, axis=0) for k in range(5)]
    expected = _old_ensemble(frames)
    got, _ = pivops.piv_ensemble_correlate(frames, window=16)
    np.testing.assert_allclose(got, expected, rtol=1e-9, atol=1e-12)


def test_cross_correlate_batches_non_multiple_image_and_matches_old(monkeypatch):
    rng = np.random.default_rng(82)
    a = rng.normal(size=(53, 61))
    b = np.roll(a, (1, -2), axis=(0, 1))
    expected_flow, expected_ratio = _old_cross_correlate(a, b)
    counts = {"forward": 0, "inverse": 0}
    real_forward, real_inverse = np.fft.rfft2, np.fft.irfft2
    def forward(*args, **kwargs):
        counts["forward"] += 1
        return real_forward(*args, **kwargs)
    def inverse(*args, **kwargs):
        counts["inverse"] += 1
        return real_inverse(*args, **kwargs)
    monkeypatch.setattr(np.fft, "rfft2", forward)
    monkeypatch.setattr(np.fft, "irfft2", inverse)
    got, info = pivops.piv_cross_correlate(a, b, window=16)
    np.testing.assert_allclose(got, expected_flow, rtol=1e-12, atol=1e-12, equal_nan=True)
    np.testing.assert_allclose(info["peak_ratio"], expected_ratio, rtol=1e-12,
                               atol=1e-12, equal_nan=True)
    assert counts["forward"] == 3  # overlap weight plus two batched image FFTs
    assert counts["inverse"] == 2  # overlap weight plus one batched inverse FFT


@pytest.mark.parametrize("combine", rangedoppler.COMBINE_MODES)
@pytest.mark.parametrize("normalize", [False, True])
def test_range_doppler_shift_after_combine_matches_old(combine, normalize):
    rng = np.random.default_rng(19)
    cube = rng.normal(size=(3, 9, 13)) + 1j * rng.normal(size=(3, 9, 13))
    got = rangedoppler.range_doppler_map(cube, combine=combine, normalize=normalize)
    expected = _old_range_doppler_map(cube, combine=combine, normalize=normalize)
    np.testing.assert_allclose(got, expected, rtol=1e-12, atol=0.0)


def test_butter_coefficient_cache_hit_and_output_identity():
    from scipy.signal import butter, filtfilt
    x = np.sin(np.arange(500, dtype=np.float64) * 0.1)
    b, a = butter(4, 20.0 / 50.0, btype="low")
    expected = filtfilt(b, a, x)
    dsp._butter_coefficients.cache_clear()
    np.testing.assert_array_equal(dsp.lowpass(x, 100.0, 20.0), expected)
    np.testing.assert_array_equal(dsp.lowpass(x, 100.0, 20.0), expected)
    assert dsp._butter_coefficients.cache_info().hits == 1
