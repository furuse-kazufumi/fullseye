import copy

import numpy as np

import sensitivity as se
import sfpolar as sf
import superquadric as sq
import volregion as vr


def _old_morris(k, p, delta, rng):
    B = np.tril(np.ones((k + 1, k)), -1)
    J = np.ones((k + 1, k))
    grid_max = int(round((1.0 - delta) * (p - 1)))
    xstar = rng.integers(0, grid_max + 1, size=k) / (p - 1)
    D = np.diag(rng.choice([-1.0, 1.0], size=k))
    perm = rng.permutation(k)
    P = np.eye(k)[:, perm]
    Bstar = (J * xstar[None, :] + 0.5 * delta * ((2 * B - J) @ D + J)) @ P
    diff = np.diff(Bstar, axis=0)
    changed = np.argmax(np.abs(diff), axis=1)
    sign = np.sign(diff[np.arange(k), changed])
    return Bstar, changed, sign


def test_369_morris_trajectory_and_rng_state_are_bit_identical():
    for seed in range(20):
        a = np.random.default_rng(seed)
        b = np.random.default_rng(seed)
        got = se._morris_trajectory(17, 6, 0.6, a)
        ref = _old_morris(17, 6, 0.6, b)
        assert len(got) == len(ref) == 3
        for x, y in zip(got, ref):
            assert np.array_equal(x, y)
        assert a.bit_generator.state == b.bit_generator.state


def test_371_morris_selection_stays_exact_for_twenty_seeds():
    for seed in range(20):
        rng = np.random.default_rng(seed)
        trajs = [_old_morris(7, 4, 2 / 3, rng) for _ in range(24)]
        pts = np.stack([t[0] for t in trajs])
        dist = np.zeros((24, 24))
        for a in range(24):
            dist[a] = np.sqrt(((pts[a][None, :, None, :] - pts[:, None, :, :]) ** 2).sum(-1)).sum((1, 2))
        np.fill_diagonal(dist, 0)
        chosen = list(np.unravel_index(int(np.argmax(dist)), dist.shape))
        while len(chosen) < 8:
            gain = dist[:, chosen].sum(axis=1)
            gain[chosen] = -np.inf
            chosen.append(int(np.argmax(gain)))
        ref = 2 * np.concatenate([trajs[i][0] for i in chosen]) - 1
        assert np.array_equal(se.doe_morris(8, 7, seed=seed, n_candidates=24)["coded"], ref)


def test_374_rle_boolean_adversarial_and_noncanonical():
    shape = (1, 2, 10)
    a = vr.VolRLE(np.array([0, 0, 1], np.int32), np.array([0, 3, 2], np.int32),
                  np.array([3, 7, 9], np.int32), shape)
    b = vr.VolRLE(np.array([0, 0], np.int32), np.array([2, 5], np.int32),
                  np.array([5, 8], np.int32), shape)
    da, db = vr.vol_rle_decode(a) > .5, vr.vol_rle_decode(b) > .5
    assert np.array_equal(vr.vol_rle_decode(vr.vol_rle_union(a, b)) > .5, da | db)
    assert np.array_equal(vr.vol_rle_decode(vr.vol_rle_intersect(a, b)) > .5, da & db)
    assert np.array_equal(vr.vol_rle_decode(vr.vol_rle_difference(a, b)) > .5, da & ~db)
    bad = vr.VolRLE(a.rows[::-1], a.starts[::-1], a.ends[::-1], shape)
    assert np.array_equal(vr.vol_rle_decode(vr.vol_rle_union(bad, b)) > .5, da | db)


def test_377_encode_edges_and_odd_block_height():
    for shape in ((2, 5, 9), (1, 3, 1)):
        v = np.zeros(shape, bool)
        v.reshape(-1, shape[-1])[::2, 0] = True
        v.reshape(-1, shape[-1])[1::2, -1] = True
        assert np.array_equal(vr.vol_rle_decode(vr.vol_rle_encode(v)).astype(bool), v)


def test_379_380_disambiguation_matches_old_selection_formula():
    rng = np.random.default_rng(4)
    cand = rng.normal(size=(4, 13, 17, 3))
    cand /= np.linalg.norm(cand, axis=-1, keepdims=True)
    prior = rng.normal(size=(13, 17, 3))
    prior /= np.linalg.norm(prior, axis=-1, keepdims=True)
    table = {"kind": "sfp_candidates", "model": "specular", "candidates": cand,
             "valid": np.ones((13, 17), bool), "zenith_deg": np.zeros((2, 13, 17)),
             "azimuth_deg": np.zeros((2, 13, 17)), "dolp": np.zeros((13, 17))}
    k = np.argmax(np.einsum("khwc,hwc->khw", cand, prior), axis=0)
    ref = np.take_along_axis(cand, k[None, ..., None].repeat(3, axis=-1), axis=0)[0]
    assert np.array_equal(sf.sfp_disambiguate(table, "normals", prior_normals=prior), ref)


def test_382_residual_matches_solver_vector_when_clip_does_not_bite():
    P = sq.sample_surface((2., 1.5, .8), (1., 1.), 12, 10)
    fit = sq.fit_superquadric(P)
    ref = sq.superquadric_residual(P, fit["a"], fit["eps"], fit["R"], fit["t"])
    assert fit["residual"] == ref
