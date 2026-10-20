"""性能レビュー batch 17-A の同値性ゲート。"""

import numpy as np
from scipy import ndimage

import astrostack as astro
import events
import mcphoton
import tacslip


def _circle_weights_old(h, w, r0, c0, radius, supersample):
    s = int(supersample)
    off = (np.arange(s, dtype=np.float64) + 0.5) / s - 0.5
    i0 = max(0, int(np.floor(r0 - radius - 1)))
    i1 = min(h, int(np.ceil(r0 + radius + 2)))
    j0 = max(0, int(np.floor(c0 - radius - 1)))
    j1 = min(w, int(np.ceil(c0 + radius + 2)))
    if i1 <= i0 or j1 <= j0:
        return np.zeros((h, w)), (0, 0, 0, 0)
    rows = (np.arange(i0, i1)[:, None] + off[None, :]).ravel()
    cols = (np.arange(j0, j1)[:, None] + off[None, :]).ravel()
    inside = ((rows - r0)[:, None] ** 2 + (cols - c0)[None, :] ** 2) <= radius**2
    sub = inside.reshape(i1 - i0, s, j1 - j0, s).mean(axis=(1, 3))
    out = np.zeros((h, w))
    out[i0:i1, j0:j1] = sub
    return out, (i0, i1, j0, j1)


def test_01_circle_weights_patch_and_photometry_are_exact():
    shape = (1024, 1536)
    old, bounds = _circle_weights_old(*shape, 0.2, 1534.4, 7.3, 8)
    patch, got_bounds = astro._circle_weights_patch(*shape, 0.2, 1534.4, 7.3, 8)
    assert got_bounds == bounds
    i0, i1, j0, j1 = bounds
    assert np.array_equal(patch, old[i0:i1, j0:j1])
    rng = np.random.default_rng(1701)
    image = rng.normal(100.0, 3.0, (64, 80))
    centers = np.array([[12.25, 17.75], [0.1, 78.8], [55.5, 40.2]])
    got = astro.aperture_photometry(image, centers, 4.2, 6.0, 9.0, supersample=8)
    fast = astro.aperture_photometry(image, centers, 4.2, 6.0, 9.0, supersample=8, method="patch")
    for rec, (r0, c0) in zip(got, centers):
        weight, _ = _circle_weights_old(64, 80, r0, c0, 4.2, 8)
        rows, cols = np.ogrid[:64, :80]
        ann = ((rows-r0)**2 + (cols-c0)**2 >= 36) & ((rows-r0)**2 + (cols-c0)**2 <= 81)
        bkg = float(np.median(image[ann]))
        assert rec["flux"] == float((weight * (image - bkg)).sum())
    assert max(abs(a["flux"] - b["flux"]) for a, b in zip(got, fast)) <= 2e-13


def _integer_shift_old(a, dy, dx):
    return ndimage.shift(a, (dy, dx), order=1, mode="constant", cval=0.0)


def test_06_integer_slice_shift_is_bit_identical_and_argmax_matches():
    rng = np.random.default_rng(1706)
    a = rng.integers(-2, 3, (19, 23)).astype(np.float64)
    for dy in range(-8, 9):
        for dx in range(-8, 9):
            assert np.array_equal(events._integer_shift_zero(a, dy, dx), _integer_shift_old(a, dy, dx))
    frames = np.zeros((4, 25, 27))
    frames[:, 5:18, 7:19] = np.array([0.1, 0.4, 0.8, 1.0])[:, None, None]
    got = events.contrast_maximization(frames, max_v=3, thr=0.2)
    ev = [(t, events.event_count(frames[t-1], frames[t], 0.2, events._EPS)) for t in range(1, 4)]
    scores = {(vy, vx): np.var(sum((_integer_shift_old(e, -t*vy, -t*vx) for t, e in ev), np.zeros((25, 27))))
              for vy in range(-3, 4) for vx in range(-3, 4)}
    assert (got["vy"], got["vx"]) == tuple(map(float, max(scores, key=scores.get)))


def _scalar_lstsq_old(f, obs):
    return np.linalg.lstsq(f[:, None], obs, rcond=None)[0][0]


def test_16_scalar_least_squares_matches_old_including_zero_denominator():
    rng = np.random.default_rng(1716)
    obs = rng.normal(size=40)
    for f in (rng.normal(size=40), np.zeros(40), np.full(40, 1e-300)):
        assert np.isclose(tacslip._scalar_lstsq(f, obs), _scalar_lstsq_old(f, obs), rtol=0, atol=1e-12)


def test_21_trace_fixture_indices_are_unique_and_absorption_is_finite():
    packet = np.arange(128)
    layer = np.random.default_rng(1721).integers(0, 2, 128)
    pairs = np.column_stack((packet, layer))
    assert len(np.unique(pairs, axis=0)) == len(pairs)
    layers = [(1.4, 0.2, 2.0, 0.8, 0.5), (1.5, 0.3, 1.5, 0.7, 0.7)]
    args = (layers, 1.0, 1.0, 128)
    got = mcphoton._trace(*args, np.random.default_rng(1721), 1e-4, 10.0, 10000)
    assert np.isfinite(got[2]).all()


def test_03_sparse_drizzle_matches_dense_reference_and_flux():
    rng = np.random.default_rng(1703)
    cube = rng.normal(size=(3, 17, 19))
    shifts = np.array([[0.0, 0.0], [0.3, -0.4], [-0.25, 0.6]])
    got_num, got_den = astro.drizzle_resample(list(cube), shifts, scale=2.0, pixfrac=0.7)
    ho, wo = 34, 38
    num = np.zeros((ho, wo)); den = np.zeros((ho, wo))
    for i in range(3):
        wr = astro._drop_overlap(17, ho, -shifts[i, 0], 2.0, 0.7)
        wc = astro._drop_overlap(19, wo, -shifts[i, 1], 2.0, 0.7)
        num += wr.T @ cube[i] @ wc / 0.49
        den += wr.sum(0)[:, None] * wc.sum(0)[None, :] / 0.25
    assert np.allclose(got_num, num / 3, rtol=0, atol=1e-12)
    assert np.allclose(got_den, den / 3, rtol=0, atol=1e-12)
    conserved, _ = astro.drizzle_resample(list(cube), np.zeros((3, 2)), scale=2.0, pixfrac=0.7)
    assert np.isclose(conserved.sum(), cube.sum() / 3, rtol=0, atol=1e-12)
