# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsearch の門: 名前順の一覧を真値にして、二分探索の答え = 全件を愚直に調べた答え。"""
import random
import time

import pytest

import opsearch as OS


def _all_op_names():
    import api
    return [r["name"] for r in api.list_ops(include_algo=True, include_ledger=True)]


@pytest.fixture(scope="module")
def names():
    ns = _all_op_names()
    assert len(ns) > 2000, len(ns)                        # 空を数えて通らない
    return ns


@pytest.fixture(scope="module")
def index(names):
    return OS.OpNameIndex(names)


def _queries(names, rng):
    qs = ["warp", "_warp", "affine", "vx_", "x", "e", "mirror", "zzzz_not_an_op", "WARP", " Affine ", "a_b", "__"]
    lows = sorted({n.lower() for n in names})
    for _ in range(300):                                  # 名前の一部を切り出した問い合わせ(当たる)
        n = rng.choice(lows)
        i = rng.randrange(len(n))
        j = rng.randrange(i + 1, len(n) + 1)
        qs.append(n[i:j])
    for _ in range(100):                                  # 区切りの直後から(word 順位を通る)
        n = rng.choice([x for x in lows if "_" in x])
        k = n.index("_") + 1
        qs.append(n[k:k + rng.randint(1, 4)])
    for _ in range(100):                                  # 乱数の文字列(ほぼ当たらない)
        qs.append("".join(rng.choice("abcdefghijklmnopqrstuvwxyz_0123456789") for _ in range(rng.randint(1, 5))))
    return qs


def test_index_equals_brute_force_on_real_op_names(names, index):
    rng = random.Random(7)
    qs = _queries(names, rng)
    assert len(qs) > 500, len(qs)                      # 空の一覧で素通りしない
    for q in qs:
        assert index.search(q, limit=None) == OS.brute_force_search(names, q), q
        assert index.search(q, limit=50) == OS.brute_force_search(names, q, limit=50), q   # 打ち切りの近道も同じ答え


def test_prefix_is_a_contiguous_slice_of_the_sorted_list(names, index):
    lows = sorted({n.lower() for n in names})
    for q in ["vx_", "mirror", "a", "zz", "drive"]:
        assert [n.lower() for n in index.prefix(q)] == [n for n in lows if n.startswith(q)]


def test_ranking_order():
    ix = OS.OpNameIndex(["warp", "warp_affine", "vx_warp_affine", "dewarp", "affine_warp", "Warped"])
    got = ix.search("warp", limit=None, with_rank=True)
    assert got == [("warp", "exact"), ("warp_affine", "prefix"), ("Warped", "prefix"),
                   ("affine_warp", "word"), ("vx_warp_affine", "word"), ("dewarp", "contains")]
    assert ix.search("WARP", limit=2) == ["warp", "warp_affine"]           # 大文字小文字を区別しない・打ち切り
    assert ix.search("   ") == [] and ix.search("nothing") == []


def test_bad_inputs_raise():
    with pytest.raises(TypeError):
        OS.OpNameIndex(["ok", 3])
    ix = OS.OpNameIndex(["a_b"])
    with pytest.raises(TypeError):
        ix.search(None)
    with pytest.raises(ValueError):
        ix.search("a", limit=-1)


def test_a_keystroke_does_not_scan_everything(names, index):
    """打鍵 1 回の手間: 全件を舐める愚直な版より桁で速い(壁時計なので緩い比で見る)。"""
    rng = random.Random(3)
    qs = [q for q in _queries(names, rng) if len(q.strip()) >= 2][:300]   # Studio は 2 文字目から一覧を出す
    t0 = time.perf_counter()
    for q in qs:
        index.search(q, limit=50)
    t_idx = time.perf_counter() - t0
    t0 = time.perf_counter()
    for q in qs:
        OS.brute_force_search(names, q, limit=50)
    t_bf = time.perf_counter() - t0
    assert t_idx * 5 < t_bf, (t_idx, t_bf)
    assert t_idx / len(qs) < 0.005, t_idx / len(qs)      # 1 打鍵 5 ms 未満
