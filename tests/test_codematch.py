# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""codematch(符号系の頑健照合 6 op)の門。

真値は外から取る:

* **第 2 実装** —— 論文の式をそのまま画素ごとに回す総当たり(FFT も相関の分解も使わない)と、
  OCM / ISC は**整数で 1 ビットも違わない**こと、SCC は 1e-12 以内。
* **既存の NCC** —— マスクが全部立つとき(狭義単調な明るさ変換を掛けた場面の正解位置)、
  SCC は ``matching.find_ncc_model`` の核(``matching._ncc_map``、画素ごとの別実装)と一致する。
* **定理** —— 狭義単調増加の変換で ISC の点数地図と RRF の出力は不変。方向符号は
  オフセットで不変、2 の冪のゲイン(閾値も同じ倍率)で不変、``np.rot90`` で N/4 だけ巡回。
  OCM の点数地図は rot90 と可換(巡回差だから)。
* **閉形式** —— 一様に乱れた符号の巡回差の平均は N/4。拡張マスクが外す確率は
  ``1 - (1-p)^4 - 4p(1-p)^3``(p = 0.5 で 0.6875)。正解位置の SCC のマスク率と ISC の値は、
  雑音の無い場面の増分と雑音 σ から正規分布の累積で期待値が決まる(論文の統計モデルを
  組ごとに評価したもの)。分散も閉形式(SCC の組は画素を共有しないので独立、ISC は隣り合う
  増分だけが画素を共有するので分散は独立の場合の 3 倍以下)→ z の門。
* **壊して確かめる探針** —— 巡回差を絶対差にすり替えると rot90 の可換性が壊れる。
"""
from __future__ import annotations

import itertools
import math

import numpy as np
import pytest
from scipy import ndimage

import codematch as C


def _scene(seed, shape=(40, 46), sigma=1.3):
    rr = np.random.default_rng(seed)
    a = ndimage.gaussian_filter(rr.random(shape), sigma)
    return (a - a.min()) / (a.max() - a.min())


def _bars(shape=(40, 46)):
    """構造の違う 2 枚目: 縞と円(勾配の向きが偏る、平坦な所がある)。"""
    yy, xx = np.mgrid[:shape[0], :shape[1]].astype(float)
    a = 0.5 + 0.3 * np.sign(np.sin(xx / 3.1)) * (yy > 12)
    a += 0.2 * (np.hypot(yy - 25, xx - 30) < 7)
    return ndimage.gaussian_filter(a, 0.8)


_INPUTS = [(_scene(1), (9, 7), (13, 14)), (_bars(), (10, 12), (14, 15))]


# ---- 第 2 実装(総当たり) ------------------------------------------------------
def _brute_ocm(img, tpl, n, g):
    ci = C._codes(img, n, g)
    ct = C._codes(tpl, n, g)
    th, tw = tpl.shape
    out = np.zeros((img.shape[0] - th + 1, img.shape[1] - tw + 1))
    for y in range(out.shape[0]):
        for x in range(out.shape[1]):
            s = 0.0
            for i in range(th):
                for j in range(tw):
                    m, q = int(ct[i, j]), int(ci[y + i, x + j])
                    if m == n:
                        d = 0.0
                    elif q == n:
                        d = n / 4.0
                    else:
                        d = min(abs(m - q), n - abs(m - q))
                    s += d
            out[y, x] = 1.0 - s / tpl.size / (n / 2.0)
    return out


def _brute_isc(img, tpl, axes):
    th, tw = tpl.shape
    out = np.zeros((img.shape[0] - th + 1, img.shape[1] - tw + 1))
    for y in range(out.shape[0]):
        for x in range(out.shape[1]):
            w = img[y:y + th, x:x + tw]
            a = n = 0
            for ax in axes:
                bw = np.diff(w, axis=ax) >= 0
                bt = np.diff(tpl, axis=ax) >= 0
                a += int((bw == bt).sum())
                n += bt.size
            out[y, x] = a / n
    return out


def _brute_scc(img, tpl, ext):
    th, tw = tpl.shape
    K = tw // 2
    out = np.full((img.shape[0] - th + 1, img.shape[1] - tw + 1), np.nan)
    for y in range(out.shape[0]):
        for x in range(out.shape[1]):
            w = img[y:y + th, x:x + tw]
            e = (w[:, 1:2 * K:2] >= w[:, 0:2 * K:2]) == (tpl[:, 1:2 * K:2] >= tpl[:, 0:2 * K:2])
            if ext:
                e2 = e.copy()
                for a in range(0, th - th % 2, 2):
                    for b in range(0, K - K % 2, 2):
                        e2[a:a + 2, b:b + 2] = e[a:a + 2, b:b + 2].sum() >= 3
                e = e2
            c = np.zeros(tpl.shape)
            c[:, 0:2 * K:2] = e
            c[:, 1:2 * K:2] = e
            f = w - w.mean()
            g = tpl - tpl.mean()
            den = math.sqrt((c * f * f).sum() * (c * g * g).sum())
            if den > 0:
                out[y, x] = (c * f * g).sum() / den
    return out


@pytest.mark.parametrize("k", [0, 1])
@pytest.mark.parametrize("n,g", [(16, 0.01), (8, 0.05)])
def test_ocm_equals_brute_force_exactly(k, n, g):
    img, tl, sz = _INPUTS[k]
    tpl = img[tl[0]:tl[0] + sz[0], tl[1]:tl[1] + sz[1]]
    r = C.ocm_match(img + 0.0, tpl, n_codes=n, grad_thresh=g, min_valid=1, min_valid_fraction=0)
    ref = _brute_ocm(img, tpl, n, g)
    assert np.array_equal(r["score_map"], ref)          # 整数で数えているので完全一致
    assert (r["row_tl"], r["col_tl"]) == tl


@pytest.mark.parametrize("k", [0, 1])
@pytest.mark.parametrize("direction,axes", [("h", (1,)), ("v", (0,)), ("hv", (1, 0))])
def test_isc_equals_brute_force_exactly(k, direction, axes):
    img, tl, sz = _INPUTS[k]
    tpl = img[tl[0]:tl[0] + sz[0], tl[1]:tl[1] + sz[1]]
    noisy = img + 0.02 * np.random.default_rng(7).standard_normal(img.shape)
    r = C.isc_match(noisy, tpl, direction=direction, min_valid=1)
    assert np.array_equal(r["score_map"], _brute_isc(noisy, tpl, axes))


@pytest.mark.parametrize("k", [0, 1])
@pytest.mark.parametrize("ext", [False, True])
def test_scc_equals_brute_force(k, ext):
    img, tl, sz = _INPUTS[k]
    tpl = img[tl[0]:tl[0] + sz[0], tl[1]:tl[1] + sz[1]]
    noisy = img + 0.03 * np.random.default_rng(11).standard_normal(img.shape)
    r = C.scc_match(noisy, tpl, min_valid=1, min_mask_fraction=0.0, mask_extension=ext)
    ref = _brute_scc(noisy, tpl, ext)
    v = r["valid_map"]
    assert v.mean() > 0.95
    assert np.nanmax(np.abs(r["score_map"][v] - ref[v])) < 1e-12


def test_scc_equals_existing_ncc_when_the_mask_is_full():
    """狭義単調な変換は増分符号を保つ → 正解位置でマスクが全部立ち、SCC = NCC(既存の別実装)。"""
    import matching
    import ops
    img = _scene(5, (48, 52))
    tpl = img[12:30, 16:36]                            # 列数 20 = 偶数(組が全列を覆う)
    for gmap in (lambda a: a ** 2.2, lambda a: 0.3 + 0.5 * np.sqrt(a), lambda a: np.tanh(3 * a)):
        sc = gmap(img)
        r = C.scc_match(sc, tpl)
        assert r["mask"].all() and (r["row_tl"], r["col_tl"]) == (12, 16)
        ncc_loop = matching._ncc_map(tpl, sc)[12, 16]
        ncc_box = ops._ncc_map(sc, tpl)[12 + tpl.shape[0] // 2, 16 + tpl.shape[1] // 2]
        assert abs(r["score"] - ncc_loop) < 1e-9
        assert abs(r["score"] - ncc_box) < 1e-9


# ---- 定理 ------------------------------------------------------------------------
_MONOTONE = [lambda a: a ** 0.3, lambda a: a ** 3.0, lambda a: 2.5 * a - 0.7,
             lambda a: np.log1p(40 * a), lambda a: 1.0 / (1.0 + np.exp(-12 * (a - 0.4)))]


@pytest.mark.parametrize("k", [0, 1])
def test_isc_is_invariant_under_strictly_monotone_maps(k):
    img, tl, sz = _INPUTS[k]
    tpl = img[tl[0]:tl[0] + sz[0], tl[1]:tl[1] + sz[1]]
    noisy = np.clip(img + 0.02 * np.random.default_rng(3).standard_normal(img.shape), 1e-6, 1)
    base = C.isc_match(noisy, tpl, direction="hv", min_valid=1)["score_map"]
    for gmap in _MONOTONE:
        assert np.array_equal(C.isc_match(gmap(noisy), tpl, direction="hv", min_valid=1)["score_map"], base)


def test_rrf_is_invariant_under_strictly_monotone_maps_of_the_image():
    bg = _scene(21, (48, 56))
    cur = np.clip(bg + 0.01 * np.random.default_rng(4).standard_normal(bg.shape), 1e-6, 1)
    cur[14:30, 20:36] = 1.0 - bg[0:16, 0:16]
    base = C.radial_reach_filter(bg, cur, t_p=0.05)
    assert 0.02 < base["foreground_fraction"] < 0.4
    for gmap in _MONOTONE:
        r = C.radial_reach_filter(bg, gmap(cur), t_p=0.05)
        assert np.array_equal(r["foreground"], base["foreground"])
        assert np.array_equal(r["rrc"], base["rrc"])


def test_orientation_code_offset_and_power_of_two_gain():
    img = _scene(8)
    c = C.orientation_code(img, grad_thresh=0.02)
    assert np.array_equal(C.orientation_code(img + 0.375, grad_thresh=0.02), c)
    for gain in (2.0, 4.0, 0.5):
        assert np.array_equal(C.orientation_code(gain * img, grad_thresh=0.02 * gain), c)


@pytest.mark.parametrize("k", [0, 1])
def test_orientation_code_rotates_by_a_quarter_turn_under_rot90(k):
    img = _INPUTS[k][0]
    n = 16
    c0 = C.orientation_code(img, n_codes=n, grad_thresh=0.01)
    c1 = C.orientation_code(np.rot90(img), n_codes=n, grad_thresh=0.01)
    pred = np.rot90(np.where(c0 < n, (c0 - n // 4) % n, n))
    assert np.array_equal(c1, pred)


def _ocm_rot90_mismatch(img, tpl):
    a = C.ocm_match(img, tpl, grad_thresh=0.01, min_valid=1)["score_map"]
    b = C.ocm_match(np.rot90(img), np.rot90(tpl), grad_thresh=0.01, min_valid=1)["score_map"]
    return int((np.rot90(a) != b).sum()), a.size


@pytest.mark.parametrize("k", [0, 1])
def test_ocm_commutes_with_rot90(k):
    img, tl, sz = _INPUTS[k]
    tpl = img[tl[0]:tl[0] + sz[0], tl[1]:tl[1] + sz[1]]
    bad, _ = _ocm_rot90_mismatch(img, tpl)
    assert bad == 0


@pytest.mark.parametrize("k", [0, 1])
def test_probe_absolute_difference_breaks_rot90(monkeypatch, k):
    """探針: 巡回差を絶対差にすり替えると、0 と N-1 が隣どうしでなくなり rot90 の門が落ちる。"""
    img, tl, sz = _INPUTS[k]
    tpl = img[tl[0]:tl[0] + sz[0], tl[1]:tl[1] + sz[1]]
    monkeypatch.setattr(C, "_code_distance",
                        lambda a, b, n: np.abs(np.asarray(a, np.int64) - np.asarray(b, np.int64)))
    bad, total = _ocm_rot90_mismatch(img, tpl)
    assert bad > total // 2


# ---- 閉形式 ------------------------------------------------------------------------
@pytest.mark.parametrize("n", [4, 8, 16, 32, 64])
def test_mean_cyclic_distance_of_random_codes_is_n_over_4(n):
    a, b = np.meshgrid(np.arange(n), np.arange(n))
    assert C._code_distance(a, b, n).mean() == n / 4.0     # 画像側だけ無効のときの罰と同じ値


@pytest.mark.parametrize("p", [0.0, 0.1, 0.223, 0.5, 0.8, 1.0])
def test_extended_mask_rate_closed_form(p):
    exact = sum(math.prod(p if m else 1 - p for m in c)
                for c in itertools.product([0, 1], repeat=4) if sum(c) >= 2)
    assert abs(exact - (1 - (1 - p) ** 4 - 4 * p * (1 - p) ** 3)) < 1e-15
    if p == 0.5:
        assert exact == 0.6875


def _phi(z):
    return 0.5 * (1.0 + np.vectorize(math.erf)(np.asarray(z) / math.sqrt(2.0)))


def _occluded(seed, frac, sigma):
    rr = np.random.default_rng(seed)
    base = _scene(100 + seed, (60, 64), 1.2)
    tpl = base[14:46, 16:48].copy()                     # 32 x 32
    clean = base.copy()
    occ = _scene(500 + seed, (32, 32), 1.0) * rr.uniform(0.2, 0.6) + rr.uniform(0.1, 0.5)
    w = int(round(frac * 32))
    clean[14:46, 16:16 + w] = occ[:, :w]
    noisy = clean + sigma * rr.standard_normal(clean.shape)
    return clean, noisy, tpl


def test_scc_mask_rate_at_the_true_position_matches_the_closed_form():
    """組ごとの一致確率 Φ(±Δ/(√2σ)) から、マスク率の期待値と分散が厳密に決まる(組は独立)。"""
    sigma = 0.02
    zs = {False: [], True: []}
    for seed in range(24):
        clean, noisy, tpl = _occluded(seed, 0.15 * (seed % 5), sigma)
        win = clean[14:46, 16:48]
        dS = win[:, 1::2] - win[:, 0::2]
        bt = tpl[:, 1::2] >= tpl[:, 0::2]
        p1 = _phi(dS / (math.sqrt(2) * sigma))
        pa = np.where(bt, p1, 1 - p1)                   # 組ごとの一致確率
        for ext in (False, True):
            r = C.scc_match(noisy, tpl, mask_extension=ext, min_mask_fraction=0.0)
            meas = r["mask_fraction_map"][14, 16]
            if not ext:
                mean = 2 * pa.sum() / tpl.size
                var = 4 * (pa * (1 - pa)).sum() / tpl.size ** 2
            else:
                keep = []
                for a in range(0, 32, 2):
                    for b in range(0, 16, 2):
                        q = [pa[a, b], pa[a, b + 1], pa[a + 1, b], pa[a + 1, b + 1]]
                        pk = sum(math.prod(q[i] if c[i] else 1 - q[i] for i in range(4))
                                 for c in itertools.product([0, 1], repeat=4) if sum(c) >= 3)
                        keep.append(pk)
                keep = np.array(keep)
                mean = 8 * keep.sum() / tpl.size
                var = 64 * (keep * (1 - keep)).sum() / tpl.size ** 2
            zs[ext].append((meas - mean) / math.sqrt(var))
    for ext, z in zs.items():
        z = np.array(z)
        assert np.abs(z).max() < 4.5, (ext, z)
        assert abs(z.mean()) < 4.5 / math.sqrt(len(z)), (ext, z.mean())


def test_isc_at_the_true_position_matches_the_closed_form():
    """ISC の期待値は増分ごとの Φ の和。隣の増分は画素を 1 つ共有する → 分散は独立の 3 倍以下。"""
    sigma = 0.02
    z = []
    for seed in range(24):
        clean, noisy, tpl = _occluded(seed, 0.15 * (seed % 5), sigma)
        win = clean[14:46, 16:48]
        p1 = _phi(np.diff(win, axis=1) / (math.sqrt(2) * sigma))
        pa = np.where(np.diff(tpl, axis=1) >= 0, p1, 1 - p1)
        r = C.isc_match(noisy, tpl)
        meas = r["score_map"][14, 16]
        z.append((meas - pa.mean()) / math.sqrt(3 * (pa * (1 - pa)).sum() / pa.size ** 2))
    z = np.array(z)
    assert np.abs(z).max() < 4.5, z
    assert abs(z.mean()) < 4.5 / math.sqrt(len(z))


# ---- 黙って間違わない ----------------------------------------------------------------
def test_flat_template_is_refused_while_ncc_answers():
    import matching
    img = _scene(9, (48, 52)) * 0.02 + 0.5            # 低コントラスト
    tpl = np.full((16, 16), 0.5) + 0.0005 * np.random.default_rng(1).standard_normal((16, 16))
    for f in (C.ocm_match, C.isc_match, C.scc_match):
        with pytest.raises(ValueError, match="undetermined"):
            f(img, tpl, **({"flat_thresh": 0.004} if f is not C.ocm_match else {}))
    r = matching.find_ncc_model(matching.create_ncc_model(tpl), img, min_score=-1)
    assert r["row"] >= 0                                 # NCC は何かを返してしまう


def test_flat_background_is_refused_by_rrf():
    bg = np.full((32, 32), 0.4)
    with pytest.raises(ValueError, match="too flat"):
        C.radial_reach_filter(bg, bg + 0.1)


def test_rrf_leaves_flat_pixels_undecided():
    bg = _scene(30, (48, 48))
    bg[:, :16] = 0.3                                   # 平坦な帯
    r = C.radial_reach_filter(bg, bg, t_p=0.05, max_reach=6)
    assert not r["decided"][:, :8].any() or r["decided"][:, :8].mean() < 0.2
    assert not r["foreground"].any()                   # 同じ画像なら前景は 0


@pytest.mark.parametrize("bad", [np.full((8, 8), np.nan), np.zeros((8, 8, 3)), np.zeros(5), []])
def test_bad_inputs_are_refused(bad):
    tpl = _scene(2, (6, 6))
    for f in (C.ocm_match, C.isc_match, C.scc_match):
        with pytest.raises(ValueError):
            f(bad, tpl)
    with pytest.raises(ValueError):
        C.radial_reach_filter(bad, bad)
    with pytest.raises(ValueError):
        C.orientation_code(bad)


def test_template_larger_than_image_and_bad_knobs_are_refused():
    img = _scene(2, (20, 20))
    with pytest.raises(ValueError, match="larger"):
        C.isc_match(img[:8, :8], img)
    with pytest.raises(ValueError):
        C.orientation_code(img, n_codes=6)
    with pytest.raises(ValueError):
        C.isc_match(img, img[:8, :8], direction="d")
    with pytest.raises(ValueError):
        C.radial_reach_filter(img, img, t_p=0)
    with pytest.raises(ValueError):
        C.scc_match(img, img[:8, :8], mask_extension="yes")


def test_results_are_deterministic_and_centre_convention_matches_ncc():
    import matching
    img = _scene(12, (50, 50))
    tpl = img[10:30, 14:34]
    m = matching.find_ncc_model(matching.create_ncc_model(tpl), img)
    for f in (C.ocm_match, C.isc_match, C.scc_match):
        a, b = f(img, tpl), f(img, tpl)
        assert (a["row"], a["col"]) == (m["row"], m["col"]) == (20, 24)
        assert np.array_equal(a["score_map"], b["score_map"])


# ---- 台帳 --------------------------------------------------------------------------
def test_ledger_matches_module_and_is_reachable():
    import opscodematch
    assert opscodematch.missing() == []
    assert sorted(opscodematch.list_ops()) == sorted(C.__all__)
    assert set(opscodematch.categories()) == {"code", "match", "change"}
    import fullseye as fs
    for name in C.__all__:
        assert callable(getattr(fs.ledger, name))


def test_typed_catalog_declares_the_family():
    import typed_catalog
    names = {e[0]: e for e in typed_catalog.catalog() if e[1] == "codematch"}
    assert set(names) == set(C.__all__)
    assert names["isc_match"][2] == ["image2d", "image2d"] and names["isc_match"][3] == "table"
