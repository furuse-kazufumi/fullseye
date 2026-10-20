"""Performance slice 29 equivalence gates.

The small reference functions intentionally preserve the implementations that were
present at c52e55d416; optimized paths are always compared with them here.
"""

import numpy as np
import pytest

import acquire
import dsp
import funct1d
import doe
import graphinv
import meshio_opt
import pivops


def _rms_reference(x, frame=None, hop=None):
    x = dsp._require_finite(x)
    if frame is None:
        return float(np.sqrt(np.mean(x * x)))
    frame = int(frame)
    hop = frame // 2 if hop is None else int(hop)
    return np.array([np.sqrt(np.mean(x[s:s + frame] ** 2))
                     for s in range(0, max(1, len(x) - frame + 1), hop)])


def _zcr_reference(x):
    x = dsp._require_finite(x)
    if x.size < 2:
        return 0.0
    s = np.sign(x)
    nz = s[s != 0.0]
    if nz.size < 2:
        return 0.0
    return float(np.count_nonzero(np.diff(nz) != 0.0)) / float(x.size - 1)


def test_384_385_rms_matches_original():
    rng = np.random.default_rng(384)
    x = rng.normal(1e6, 3.0, 24000)
    for frame, hop in ((None, None), (64, 64), (63, 63), (64, 17)):
        np.testing.assert_allclose(dsp.rms(x, frame, hop),
                                   _rms_reference(x, frame, hop), rtol=0, atol=1e-12)


def test_389_zcr_matches_original_with_zeros():
    rng = np.random.default_rng(389)
    for x in ([1, 0, -1], [0, 0], rng.choice([-1.0, 0.0, 1.0], 10000)):
        assert dsp.zero_crossing_rate(x) == _zcr_reference(x)


def test_392_395_funct1d_identity_and_batch_lookup():
    rng = np.random.default_rng(392)
    y = rng.normal(size=10000)
    order = np.argsort(y, kind="stable")
    inv = funct1d.invert_funct_1d(y)
    np.testing.assert_array_equal(inv["x"], y[order])
    np.testing.assert_array_equal(inv["y"], np.arange(y.size, dtype=float)[order])
    expect = np.column_stack([2.5 * np.arange(y.size) - 3, -2 * y + 4])
    np.testing.assert_array_equal(funct1d.transform_funct_1d(y, 2.5, -3, -2, 4), expect)
    xs = np.array([-2.0, 0.5, 18.25, 1e6])
    np.testing.assert_array_equal(funct1d.get_y_value_funct_1d(y, xs),
                                  np.array([np.interp(x, np.arange(y.size), y) for x in xs]))


def test_394_zero_crossings_matches_product_reference():
    rng = np.random.default_rng(394)
    y = rng.choice([-2.0, 0.0, 3.0], 50000)
    expect = np.nonzero((np.sign(y[:-1]) * np.sign(y[1:])) < 0)[0]
    np.testing.assert_array_equal(funct1d.zero_crossings_funct_1d(y), expect)


def test_390_391_match_fft_within_gate():
    rng = np.random.default_rng(390)
    a = rng.normal(size=5000); b = rng.normal(size=4200)
    ac, bc = a - a.mean(), b - b.mean()
    got_lags, got = funct1d._match_scores(ac, bc)
    # Force the original direct correlation for the reference formula.
    old = np.correlate(ac, bc, mode="full")
    n1, n2 = ac.size, bc.size; lags = np.arange(-(n2 - 1), n1)
    head = np.clip(lags, 0, n1); tail = np.clip(lags + n2, 0, n1)
    j0 = np.clip(head-lags, 0, n2); j1 = np.clip(tail-lags, 0, n2)
    sa=np.r_[0.,np.cumsum(ac)]; sa2=np.r_[0.,np.cumsum(ac*ac)]
    sb=np.r_[0.,np.cumsum(bc)]; sb2=np.r_[0.,np.cumsum(bc*bc)]
    sv=head*bc[0]+sb[j1]-sb[j0]+(n1-tail)*bc[-1]
    svv=head*bc[0]**2+sb2[j1]-sb2[j0]+(n1-tail)*bc[-1]**2
    num=bc[0]*sa[head]+old+bc[-1]*(sa[n1]-sa[tail])-sa[n1]*sv/n1
    va=sa2[n1]-sa[n1]**2/n1; vv=svv-sv**2/n1
    ref=np.zeros(lags.size); live=(va>0)&(vv>1e-12*np.abs(svv)); ref[live]=num[live]/np.sqrt(va*vv[live])
    np.testing.assert_array_equal(got_lags, lags)
    np.testing.assert_allclose(got, np.clip(ref,-1,1), rtol=0, atol=1e-12)


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


def _swap_reference(adj, pairs):
    b = graphinv._as_binary_adjacency(adj, "adj", "graph_swap_symmetry")
    np.fill_diagonal(b, 0)
    perm = np.arange(len(b))
    for i, j in pairs:
        perm[i], perm[j] = j, i
    bm = b[np.ix_(perm, perm)]
    return int(((b == 1) & (bm == 1)).sum()), int(((b == 1) | (bm == 1)).sum())


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


def test_400_swap_symmetry_shared_and_union_match_reference():
    rng = np.random.default_rng(400)
    pairs = [(i, i + 1) for i in range(0, 40, 2)]
    for density in (0.01, 0.24, 0.25, 0.8):
        a = (rng.random((80, 80)) < density).astype(np.uint8)
        shared, union = _swap_reference(a, pairs)
        got = graphinv.graph_swap_symmetry(a, pairs)
        assert (got["shared"], got["union"]) == (shared, union)


def _rich_club_reference(b, deg, ks):
    phi=np.zeros(len(ks)); cnt=np.zeros(len(ks), dtype=np.int64)
    order=np.argsort(-deg); ds=deg[order]
    for i,k in enumerate(ks):
        r=int((ds>k).sum()); cnt[i]=r
        if r >= 2:
            idx=order[:r]; phi[i]=float(b[np.ix_(idx,idx)].sum())/(r*(r-1))
    return phi,cnt


def test_397_sparse_cycle_and_399_rich_club_match_original():
    rng=np.random.default_rng(399)
    a=(rng.random((300,300)) < .01).astype(np.int64); np.fill_diagonal(a,0)
    assert graphinv.graph_cycle3(a)["cycles3"] == _cycle3_reference(a)
    deg=a.sum(0)+a.sum(1); ks=np.arange(int(deg.max()))
    got=graphinv._rich_club_phi(a,deg,ks)
    ref=_rich_club_reference(a,deg,ks)
    np.testing.assert_array_equal(got[0],ref[0]); np.testing.assert_array_equal(got[1],ref[1])


def test_403_404_consensus_aggregation_identity():
    rng=np.random.default_rng(403)
    mats=[rng.integers(0,4,(40,40)) for _ in range(5)]
    for m in mats: np.fill_diagonal(m,0)
    got=graphinv.graph_edge_consensus(mats)
    p=np.stack([m>0 for m in mats]); occ=p.sum(0); s=np.stack(mats).sum(0)
    ref=[float(s[occ==c].sum()/s.sum()) if c else 0.0 for c in range(6)]
    np.testing.assert_allclose(got["synapse_share"], ref, rtol=0, atol=1e-15)


def test_408_min_dist_matches_reference_including_duplicates():
    rng = np.random.default_rng(408)
    for shape in ((2, 1), (20, 7), (101, 3)):
        u = rng.random(shape)
        assert doe._min_dist(u) == pytest.approx(_min_dist_reference(u), rel=0, abs=1e-15)
    u = np.array([[0.0, 0.0], [1.0, 1.0], [0.0, 0.0]])
    assert doe._min_dist(u) == 0.0
    u = rng.random((700, 5))
    assert doe._min_dist(u) == pytest.approx(_min_dist_reference(u), rel=0, abs=1e-15)


def test_412_oa_strength_matches_original_counts():
    rng=np.random.default_rng(412)
    for shape in ((40,8),(81,12)):
        table=rng.integers(1,4,shape)
        def ref(t):
            n=t.shape[0]
            for a in range(t.shape[1]):
                for b in range(a+1,t.shape[1]):
                    sa,sb=np.unique(t[:,a]),np.unique(t[:,b])
                    if n%(sa.size*sb.size): return False
                    want=n//(sa.size*sb.size)
                    for x in sa:
                        for y in sb:
                            if int(np.sum((t[:,a]==x)&(t[:,b]==y))) != want: return False
            return True
        assert doe._oa_strength2_ok(table) is ref(table)


def test_414_strided_accessor_owned_and_identical():
    from types import SimpleNamespace as NS
    raw=bytearray(5*16)
    vals=np.arange(15,dtype="<f4").reshape(5,3)
    for i,row in enumerate(vals): raw[i*16:i*16+12]=row.tobytes()
    gltf=NS(accessors=[NS(sparse=None,bufferView=0,componentType=5126,type="VEC3",count=5,byteOffset=0)],
            bufferViews=[NS(buffer=0,byteStride=16,byteOffset=0)])
    got=meshio_opt._read_accessor(gltf,[raw],0,"memory")
    np.testing.assert_array_equal(got,vals)
    assert got.flags.owndata and got.flags.c_contiguous


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


@pytest.mark.parametrize("bits", [1, 3, 7, 8, 9, 10, 12, 15, 16])
def test_421_lsb_general_width_and_raw_buffer_contract(bits):
    rng=np.random.default_rng(421+bits); count=257
    raw=rng.integers(0,256,(bits*count+7)//8,dtype=np.uint8)
    ref=_unpack_lsb_reference(raw,bits,count)
    for source in (raw, raw.tobytes(), bytearray(raw), memoryview(raw)):
        np.testing.assert_array_equal(acquire.unpack_lsb(source,bits,count),ref)


def test_422_grouped_raw_buffer_contract():
    rng=np.random.default_rng(422); raw=rng.integers(0,256,300,dtype=np.uint8)
    for bits in (10,12):
        ref=acquire.unpack_grouped(raw,bits,199)
        np.testing.assert_array_equal(acquire.unpack_grouped(raw.tobytes(),bits,199),ref)


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
