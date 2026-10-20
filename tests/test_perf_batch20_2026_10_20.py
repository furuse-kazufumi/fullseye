"""Performance batch 20: exact-result gates against the pre-change paths."""
from __future__ import annotations

import numpy as np
from scipy import ndimage

import motion


def _dominant_motion_old(u, v, robust=True, trim=0.25, iters=3):
    u = np.asarray(u, np.float64)
    v = np.asarray(v, np.float64)
    h, w = u.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    a = np.stack([np.ones(h * w), xx.ravel(), yy.ravel()], axis=1)
    bu, bv = u.ravel(), v.ravel()
    finite = np.isfinite(bu) & np.isfinite(bv)
    if int(finite.sum()) < 3:
        return np.full((2, 3), np.nan)
    af, buf, bvf = a[finite], bu[finite], bv[finite]
    cu, *_ = np.linalg.lstsq(af, buf, rcond=None)
    cv, *_ = np.linalg.lstsq(af, bvf, rcond=None)
    if robust:
        for _ in range(max(1, int(iters))):
            resid = np.hypot(buf - af @ cu, bvf - af @ cv)
            threshold = np.quantile(resid, 1.0 - float(trim))
            keep = resid <= threshold
            if int(keep.sum()) < 3:
                break
            cu, *_ = np.linalg.lstsq(af[keep], buf[keep], rcond=None)
            cv, *_ = np.linalg.lstsq(af[keep], bvf[keep], rcond=None)
    return np.stack([cu, cv], axis=0)


def _motion_segments_old(u, v, threshold, min_area=25, smooth=1.0):
    ru, rv = np.asarray(u, np.float64), np.asarray(v, np.float64)
    mag = np.hypot(ru, rv)
    mask = mag > float(threshold)
    if smooth and smooth > 0:
        it = int(round(smooth))
        padded = ndimage.binary_closing(np.pad(mask, it, mode="edge"), iterations=it)
        mask = padded[it:-it, it:-it]
    labels, count = ndimage.label(mask)
    segments = []
    for label in range(1, count + 1):
        ys, xs = np.where(labels == label)
        if xs.size < int(min_area):
            mask[ys, xs] = False
            continue
        segments.append({
            "area": int(xs.size),
            "centroid": (float(ys.mean()), float(xs.mean())),
            "bbox": (int(ys.min()), int(xs.min()), int(ys.max()), int(xs.max())),
            "mean_speed": float(mag[ys, xs].mean()),
        })
    segments.sort(key=lambda row: row["area"], reverse=True)
    return mask, segments


def _detect_events_old(energy, threshold=None, k=2.0):
    e = np.asarray(energy, np.float64)
    if e.size == 0:
        return np.zeros(0, dtype=int)
    threshold = float(e.mean() + float(k) * e.std()) if threshold is None else float(threshold)
    events = []
    for i in range(e.size):
        if e[i] <= threshold:
            continue
        left = e[i - 1] if i > 0 else -np.inf
        right = e[i + 1] if i < e.size - 1 else -np.inf
        if e[i] >= left and e[i] >= right:
            events.append(i)
    return np.array(events, dtype=int)


def test_131_dominant_motion_matches_two_rhs_reference():
    rng = np.random.default_rng(131)
    y, x = np.mgrid[:70, :90]
    u = 1e6 + 0.002 * x - 0.003 * y + rng.normal(0, 1e-8, x.shape)
    v = -1e6 + 0.004 * x + 0.001 * y + rng.normal(0, 1e-8, x.shape)
    u[10:25, 30:60] += 2.0
    v[10:25, 30:60] -= 3.0
    u[0, 0] = np.nan
    expected = _dominant_motion_old(u, v)
    np.testing.assert_array_equal(motion.dominant_motion(u, v), expected)
    np.testing.assert_allclose(motion.dominant_motion(u, v, method="fast"),
                               expected, atol=1e-8, rtol=0)


def test_132_motion_segments_matches_reference_stats_and_boxes():
    u = np.zeros((80, 100)); v = np.zeros_like(u)
    u[0:12, 3:20] = 2.5
    v[35:60, 50:85] = 4.0
    expected = _motion_segments_old(u, v, 1.0, min_area=10, smooth=1)
    actual = motion.motion_segments(u, v, 1.0, subtract_dominant=False, min_area=10, smooth=1)
    np.testing.assert_array_equal(actual[0], expected[0])
    assert actual[1] == expected[1]


def test_133_motion_energy_series_matches_materialized_reference(monkeypatch):
    import flow

    def fake_flow(a, b, **kwargs):
        return b - a, (b - a) * kwargs.get("scale", 2.0)

    monkeypatch.setattr(flow, "optical_flow_lk", fake_flow)
    frames = [np.full((19, 23), value) for value in (1, 2, 4, 9)]
    seq = [np.asarray(frame, np.float64) for frame in frames]
    expected = np.array([
        motion.frame_motion_energy(*fake_flow(a, b, scale=3.0))
        for a, b in zip(seq[:-1], seq[1:])
    ])
    np.testing.assert_array_equal(
        motion.motion_energy_series((frame for frame in frames), scale=3.0), expected)


def test_134_flow_from_model_is_bit_identical_to_full_grids():
    model = np.array([[1e6, 1e-9, -2e-9], [-1e6, 3e-9, 4e-9]])
    h, w = 137, 211
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    expected = (model[0, 0] + model[0, 1] * xx + model[0, 2] * yy,
                model[1, 0] + model[1, 1] * xx + model[1, 2] * yy)
    for actual, old in zip(motion.flow_from_model(model, (h, w)), expected):
        np.testing.assert_array_equal(actual, old)


def test_135_detect_events_matches_loops_for_flat_peaks_and_nan():
    for energy in (np.array([]), np.array([0., 2., 2., 0., np.nan, 3., 0.]),
                   np.random.default_rng(135).normal(size=10001)):
        np.testing.assert_array_equal(motion.detect_events(energy, threshold=1.0),
                                      _detect_events_old(energy, threshold=1.0))
