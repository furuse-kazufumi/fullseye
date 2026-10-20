"""Performance slice 29 equivalence gates.

The small reference functions intentionally preserve the implementations that were
present at c52e55d416; optimized paths are always compared with them here.
"""

import numpy as np
import pytest

import acquire
import doe
import graphinv
import pivops


def _cycle3_reference(adj):
    b = graphinv._as_binary_adjacency(adj, "adj", "graph_cycle3")
    np.fill_diagonal(b, 0)
    m = b.astype(np.int64)
    return int(np.trace(m @ m @ m)) // 3


def _min_dist_reference(u):
    d = np.sqrt(((u[:, None, :] - u[None, :, :]) ** 2).sum(-1))
    d[np.diag_indices_from(d)] = np.inf
    return float(d.min())


def _lhs_reference(n, factors, seed, maximin, centered=False):
    rng = np.random.default_rng(seed)
    def one():
        perm = np.stack([rng.permutation(n) for _ in range(factors)], axis=1).astype(np.float64)
        jitter = np.full((n, factors), 0.5) if centered else rng.random((n, factors))
        return (perm + jitter) / n
    best, md = None, -1.0
    for _ in range(maximin):
        cand = one()
        d = _min_dist_reference(cand)
        if d > md:
            best, md = cand, d
    return best, md, rng.bit_generator.state


def _unpack_lsb_reference(buf, bits, count):
    b = np.unpackbits(np.asarray(buf, dtype=np.uint8).ravel(), bitorder="little")
    need = int(bits) * int(count)
    if b.size < need:
        raise ValueError
    w = b[:need].reshape(int(count), int(bits))
    return (w * (1 << np.arange(int(bits), dtype=np.uint32))).sum(axis=1).astype(np.uint16)


def _peak_ratio_reference(corr, pi, pj, top):
    n = corr.shape[0]
    y0, y1 = max(0, pi - 1), min(n, pi + 2)
    x0, x1 = max(0, pj - 1), min(n, pj + 2)
    masked = np.array(corr, dtype=np.float64, copy=True)
    masked[y0:y1, x0:x1] = -np.inf
    second = float(np.max(masked))
    return np.inf if not np.isfinite(second) or second <= 0 else float(top / second)


def test_396_cycle3_matches_reference_random_and_overflow_guard():
    rng = np.random.default_rng(396)
    for n in (1, 3, 17, 80):
        for density in (0.0, 0.08, 0.7, 1.0):
            a = (rng.random((n, n)) < density).astype(np.uint8)
            assert graphinv.graph_cycle3(a)["cycles3"] == _cycle3_reference(a)
    # int64 multiplication is required: uint8 overflows on a dense graph.
    a = np.ones((300, 300), dtype=np.uint8)
    np.fill_diagonal(a, 0)
    assert graphinv.graph_cycle3(a)["cycles3"] == _cycle3_reference(a)


def test_408_min_dist_matches_reference_including_duplicates():
    rng = np.random.default_rng(408)
    for shape in ((2, 1), (20, 7), (101, 3)):
        u = rng.random(shape)
        assert doe._min_dist(u) == pytest.approx(_min_dist_reference(u), rel=0, abs=1e-15)
    u = np.array([[0.0, 0.0], [1.0, 1.0], [0.0, 0.0]])
    assert doe._min_dist(u) == 0.0


def test_410_lhs_early_rejection_preserves_design_and_rng_state(monkeypatch):
    expect, md, state = _lhs_reference(90, 4, 410, 20)
    calls = {"pairs": 0}
    original = doe._min_dist_bounded
    observed_rng = np.random.default_rng(410)
    monkeypatch.setattr(doe.np.random, "default_rng", lambda seed: observed_rng)
    def counted(u, upper):
        value, pairs = original(u, upper, return_pairs=True)
        calls["pairs"] += pairs
        return value
    monkeypatch.setattr(doe, "_min_dist_bounded", counted)
    got = doe.doe_lhs(n=90, factors=4, seed=410, maximin=20)
    np.testing.assert_array_equal(got["coded"], 2.0 * expect - 1.0)
    assert got["meta"]["min_distance"] == md
    assert observed_rng.bit_generator.state == state
    assert calls["pairs"] < 20 * 90 * 89 // 2


@pytest.mark.parametrize("bits", [10, 12])
def test_420_unpack_lsb_matches_reference_every_short_count(bits):
    rng = np.random.default_rng(420 + bits)
    for count in range(1, 65):
        raw = rng.integers(0, 256, (bits * count + 7) // 8, dtype=np.uint8)
        np.testing.assert_array_equal(acquire.unpack_lsb(raw, bits, count),
                                      _unpack_lsb_reference(raw, bits, count))
    raw = rng.integers(0, 256, 2_000_000, dtype=np.uint8)
    count = raw.size * 8 // bits
    np.testing.assert_array_equal(acquire.unpack_lsb(raw, bits, count),
                                  _unpack_lsb_reference(raw, bits, count))


def test_425_unpack_lsb_rejects_shortfall_before_unpackbits(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("large temporary was attempted")
    monkeypatch.setattr(np, "unpackbits", forbidden)
    with pytest.raises(ValueError, match="need"):
        acquire.unpack_lsb(np.array([0], dtype=np.uint8), 12, 10**12)


def test_430_peak_ratio_matches_copying_reference():
    rng = np.random.default_rng(430)
    cases = [np.empty((0, 0)), np.full((5, 5), np.nan), np.zeros((5, 5))]
    for corr in cases[1:]:
        assert pivops._peak_ratio(corr, 2, 2, 1.0) == _peak_ratio_reference(corr, 2, 2, 1.0)
    for n in (3, 8, 31):
        corr = rng.normal(size=(n, n))
        pi, pj = np.unravel_index(np.nanargmax(corr), corr.shape)
        got = pivops._peak_ratio(corr, pi, pj, corr[pi, pj])
        expect = _peak_ratio_reference(corr, pi, pj, corr[pi, pj])
        assert got == expect
