"""形状マッチング性能改善 第15便の一致・計数ゲート。"""
from __future__ import annotations

import numpy as np
import pytest

import shapematch as S


def _old_score(model, gy, gx, mag, r0, c0, normalised=False):
    assert not normalised
    pts = model["pts"]
    ys = pts[:, 0] - model["shape"][0] // 2 + r0
    xs = pts[:, 1] - model["shape"][1] // 2 + c0
    ok = (ys >= 0) & (ys < mag.shape[0]) & (xs >= 0) & (xs < mag.shape[1])
    if ok.sum() < 3:
        return 0.0
    ys, xs = ys[ok], xs[ok]
    m = mag[ys, xs]
    dots = (np.column_stack([gy[ys, xs] / (m + 1e-9),
                             gx[ys, xs] / (m + 1e-9)]) * model["grad"][ok]).sum(1)
    if model.get("min_contrast", 0.0) > 0:
        dots = np.where(m >= model["min_contrast"], dots, 0.0)
    n = len(pts)
    if model.get("metric") == "ignore_local_polarity":
        return float(np.abs(dots).sum() / n)
    if model.get("metric") == "ignore_global_polarity":
        return float(abs(dots.sum()) / n)
    return float(max(0.0, dots.sum() / n))


def _old_nms(score_map, min_score, max_matches, min_distance):
    sm = score_map.copy()
    out = []
    for _ in range(int(max_matches)):
        idx = np.unravel_index(np.argmax(sm), sm.shape)
        s = float(sm[idx])
        if s < min_score:
            break
        out.append((s, int(idx[0]), int(idx[1])))
        r, c = idx
        sm[max(0, r-min_distance):r+min_distance+1,
           max(0, c-min_distance):c+min_distance+1] = -1.0
    return out


def _old_search(models, pyr, fields, n_cand=12, score_fn=_old_score, _trace=None):
    top = len(models) - 1
    mh, mw = models[top]["shape"]
    gx, gy, mag = fields[top][:3]
    cand = [(score_fn(models[top], gy, gx, mag, r, c), r, c)
            for r in range(mh // 2, max(mh // 2 + 1, pyr[top].shape[0] - mh // 2))
            for c in range(mw // 2, max(mw // 2 + 1, pyr[top].shape[1] - mw // 2))]
    if not cand:
        return None
    cand.sort(key=lambda z: -z[0])
    cand = cand[:n_cand]
    if _trace is not None:
        _trace.append(list(cand))
    for level in range(top - 1, -1, -1):
        gx, gy, mag = fields[level][:3]
        mh, mw = models[level]["shape"]
        nxt = []
        for _, r0, c0 in cand:
            for dr in (-2, -1, 0, 1, 2):
                for dc in (-2, -1, 0, 1, 2):
                    r, c = r0 * 2 + dr, c0 * 2 + dc
                    if (mh // 2 <= r < pyr[level].shape[0] - mh // 2
                            and mw // 2 <= c < pyr[level].shape[1] - mw // 2):
                        nxt.append((score_fn(models[level], gy, gx, mag, r, c), r, c))
        if not nxt:
            return None
        nxt.sort(key=lambda z: -z[0])
        cand = nxt[:n_cand]
        if _trace is not None:
            _trace.append(list(cand))
    return cand[0]


def _fixture(size=192):
    rng = np.random.default_rng(1515)
    template = np.zeros((32, 32))
    template[7:26, 13:18] = 1
    template[19:24, 5:27] = 0.7
    image = rng.normal(0, 0.025, (size, size))
    image[65:97, 83:115] += template
    return S.create_shape_model(template), image


def test_pyramid_coordinate_cache_preserves_candidates_and_reduces_calls(monkeypatch):
    model, image = _fixture()
    models = S.build_model_pyramid(model)
    pyr = S.image_pyramid(image, len(models))
    fields = [S._grad_field(a) for a in pyr]
    original = S._score_at
    calls = 0

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(S, "_score_at", counted)
    got_trace = []
    got = S._search_with_pyramid(models, pyr, fields, n_cand=12,
                                 _trace=got_trace)
    cached_calls = calls
    calls = 0
    def old_counted(*args):
        nonlocal calls
        calls += 1
        return _old_score(*args)

    want_trace = []
    want = _old_search(models, pyr, fields, n_cand=12, score_fn=old_counted,
                       _trace=want_trace)
    old_calls = calls
    assert got == want
    assert got_trace == want_trace
    assert cached_calls < old_calls


@pytest.mark.parametrize("metric", ["use_polarity", "ignore_global_polarity",
                                     "ignore_local_polarity"])
def test_pre_normalised_pyramid_scores_match_old(metric):
    model, image = _fixture()
    model["metric"] = metric
    gx, gy, mag = S._grad_field(image)
    ngy, ngx = S._normalise_gradients(gy, gx, mag)
    for r, c in [(16, 16), (65, 83), (81, 99), (176, 176)]:
        want = _old_score(model, gy, gx, mag, r, c)
        got = S._score_at(model, ngy, ngx, mag, r, c, normalised=True)
        assert got == pytest.approx(want, abs=1e-12)


@pytest.mark.parametrize("distance", [7, 91])
def test_tiled_nms_matches_old_across_tile_boundaries(distance):
    sm = np.full((260, 270), -1.0)
    sm[60:70, 60:70] = 0.9
    sm[63:67, 63:67] = 0.95
    sm[63:67, 64:68] = 0.95  # plateau crosses the 64-column tile boundary
    sm[130, 129] = sm[129, 130] = 0.95
    sm[220, 240] = 0.8
    for threshold in (0.0, 0.85, 0.96):
        assert S._nms_from_map(sm, threshold, 20, distance) == \
            _old_nms(sm, threshold, 20, distance)


def test_tiled_nms_reads_fewer_pixels_on_large_map():
    rng = np.random.default_rng(15)
    sm = rng.random((2048, 2048))
    stats = {}
    got = S._nms_from_map(sm, 0.0, 200, 9, _stats=stats)
    assert got == _old_nms(sm, 0.0, 200, 9)
    assert stats["pixel_reads"] < sm.size * 10
    assert stats["strategy"] == "tiles"


def test_find_results_unchanged_on_neighbouring_candidates(monkeypatch):
    model, image = _fixture(224)
    for dc in range(12):
        image[130:162, 35+dc:67+dc] += model["template"] * (1 - dc * 0.01)
    got = S.find_shape_models(model, image, min_score=0.2, max_matches=12,
                              min_distance=1)
    monkeypatch.setattr(S, "_score_at", _old_score)
    monkeypatch.setattr(S, "_search_with_pyramid", _old_search)
    monkeypatch.setattr(S, "_pyramid_grad_field", S._grad_field)
    want = S.find_shape_models(model, image, min_score=0.2, max_matches=12,
                               min_distance=1)
    assert got == want
