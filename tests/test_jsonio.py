# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""fullseye.jsonio — sort ごとの JSON 橋。★往復が bit 一致することを、op の門と同じ探針で確かめる。"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fullseye import jsonio as J  # noqa: E402


def _same(a, b):
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        a, b = np.asarray(a), np.asarray(b)
        return a.shape == b.shape and np.array_equal(a.view(np.uint8) if a.dtype == b.dtype else a, b.view(np.uint8) if a.dtype == b.dtype else b, equal_nan=True)
    return a == b


@pytest.mark.parametrize("sort", sorted(J._ARRAY_SORTS))
@pytest.mark.parametrize("readable", [False, True])
def test_every_array_sort_round_trips_bit_for_bit(sort, readable):
    rng = np.random.default_rng(hash(sort) % 1000)
    _, ndim, last = J._ARRAY_SORTS[sort]
    shape = [5, 7, 3, 2][:ndim]
    if last is not None:
        shape[-1] = last
    if sort == "polsweep":
        shape = [4, 6, 8]
    a = rng.standard_normal(shape) * 1e-3 + 0.5
    a.flat[0] = np.pi                      # 短い 10 進では戻らない値
    a.flat[-1] = 1.0 / 3.0
    text = J.to_json(a, sort, readable=readable)
    b, s = J.from_json(text)
    assert s == sort and b.shape == a.shape and b.dtype == np.float64
    assert np.array_equal(a.view(np.uint8), b.view(np.uint8)), "bit が違う"
    env = json.loads(text)
    assert env["fullseye_sort"] == sort and env["version"] == 1


def test_the_probes_of_the_op_gates_round_trip_too():
    """op の門が使うのと同じ探針(構造入力)を橋に通す —— 橋が探針より狭ければここで割れる。"""
    import op_probe as P
    rng = np.random.default_rng(0)
    for sort in ("image", "region", "color", "points", "signal", "volume", "feature", "contour"):
        v = P.sample_input(sort, rng, structured=True)
        if v is None:
            pytest.skip("%s の探針が無い(optional backend)" % sort)
        back, s = J.from_json(J.to_json(v, sort))
        assert s == sort
        if sort == "region":
            assert np.array_equal(back, (np.asarray(v) > 0.5).astype(np.float64))
        elif sort == "feature":
            assert back == float(v)
        elif sort == "contour":
            assert tuple(back["shape"]) == tuple(v["shape"]) and len(back["cs"]) == len(v["cs"])
            for x, y in zip(back["cs"], v["cs"]):
                assert np.array_equal(np.asarray(x), np.asarray(y, dtype=np.float64))
        else:
            assert np.array_equal(np.asarray(back), np.asarray(v, dtype=np.float64))


def test_region_travels_as_run_lengths_and_comes_back_exactly():
    rng = np.random.default_rng(1)
    m = (rng.random((17, 23)) > 0.7).astype(np.float64)
    env = J.to_jsonable(m, "region")
    assert env["payload"]["encoding"] == "rle" and sum(env["payload"]["runs"]) == 17 * 23
    back, _ = J.from_jsonable(env)
    assert np.array_equal(back, m)
    # 全 0 / 全 1 / 空
    for x in (np.zeros((3, 4)), np.ones((3, 4)), np.zeros((0, 4))):
        assert np.array_equal(J.from_jsonable(J.to_jsonable(x, "mask"))[0], x)
    with pytest.raises(ValueError, match="fit"):
        J.from_jsonable({"fullseye_sort": "region", "version": 1,
                         "payload": {"encoding": "rle", "shape": [2, 2], "runs": [1, 9]}})


def test_non_finite_values_are_flagged_and_still_exact():
    a = np.array([[1.0, np.nan], [np.inf, -np.inf]])
    text = J.to_json(a, "image")
    assert json.loads(text)["nonfinite"] is True
    b, _ = J.from_json(text)
    assert np.array_equal(a.view(np.uint8), b.view(np.uint8))
    assert "NaN" not in text and "Infinity" not in text           # 裸の NaN トークンは出さない
    v, _ = J.from_json(J.to_json(float("nan"), "feature"))
    assert np.isnan(v)


def test_the_bridge_is_fail_closed():
    with pytest.raises(ValueError, match="no JSON bridge"):
        J.to_json(np.zeros(3), "match")
    with pytest.raises(ValueError, match="2-D"):
        J.to_json(np.zeros((2, 2, 2)), "image")
    with pytest.raises(ValueError, match="last axis of 3"):
        J.to_json(np.zeros((2, 2, 4)), "rgb")
    with pytest.raises(ValueError, match="last axis of 4"):
        J.to_json(np.zeros(3), "stokes")
    with pytest.raises(ValueError, match="envelope"):
        J.from_json('{"shape": [2, 2]}')
    with pytest.raises(ValueError, match="version"):
        J.from_json('{"fullseye_sort": "image", "version": 99, "payload": {}}')
    with pytest.raises(ValueError, match="unknown sort"):
        J.from_json('{"fullseye_sort": "bbox", "version": 1, "payload": {}}')
    with pytest.raises(ValueError, match="not JSON"):
        J.from_json("{")
    bad = J.to_jsonable(np.zeros((2, 3)), "image")
    bad["payload"]["shape"] = [3, 3]
    with pytest.raises(ValueError, match="values in data"):
        J.from_jsonable(bad)


def test_tables_and_contours_keep_their_structure():
    t = {"n": np.int64(3), "ok": np.bool_(True), "xs": np.arange(3.0), "name": "a", "nested": [{"v": np.float32(1.5)}]}
    back, _ = J.from_json(J.to_json(t, "table"))
    assert back == {"n": 3, "ok": True, "xs": [0.0, 1.0, 2.0], "name": "a", "nested": [{"v": 1.5}]}
    c = {"shape": (10, 12), "cs": [np.array([[0.5, 1.5], [2.5, 3.5]]), np.zeros((0, 2))]}
    back, _ = J.from_json(J.to_json(c, "contour", readable=True))
    assert back["shape"] == (10, 12) and np.array_equal(back["cs"][0], c["cs"][0]) and back["cs"][1].shape == (0, 2)
    with pytest.raises(ValueError, match="cannot serialise"):
        J.to_json({"f": object()}, "table")


def test_save_and_load_round_trip_through_a_file(tmp_path):
    img = np.random.default_rng(3).random((6, 8))
    img[0, 0] = np.pi
    p = str(tmp_path / "img.json")
    assert J.save_json(img, "image", p) == p
    back, sort = J.load_json(p)
    assert sort == "image" and np.array_equal(img.view(np.uint8), back.view(np.uint8))
    # readable=True is exact too
    q = str(tmp_path / "img2.json")
    J.save_json(img, "image", q, readable=True)
    back2, _ = J.load_json(q)
    assert np.array_equal(img.view(np.uint8), back2.view(np.uint8))


def test_json_lines_carry_a_list_of_mixed_sorts_one_per_line():
    items = [(np.array([[1.5, 2.0], [1.0 / 3.0, 4.0]]), "points"),
             (float(np.pi), "feature"),
             ((np.eye(3) > 0).astype(np.float64), "region"),
             ({"n": 3, "labels": ["a", "b"]}, "table")]
    jl = J.to_json_lines(items)
    assert jl.count("\n") == len(items) - 1                 # one line per item, no trailing newline
    back = J.from_json_lines(jl)
    assert [s for _, s in back] == ["points", "feature", "region", "table"]
    assert np.array_equal(back[0][0].view(np.uint8), items[0][0].view(np.uint8))
    assert back[1][0] == items[1][0]
    assert np.array_equal(back[2][0], items[2][0])
    assert back[3][0] == {"n": 3, "labels": ["a", "b"]}


def test_json_lines_skip_blanks_and_fail_closed():
    jl = J.to_json_lines([(np.zeros((2, 2)), "image")])
    assert J.from_json_lines("\n" + jl + "\n\n")            # surrounding blank lines are ignored
    with pytest.raises(ValueError, match="line 1"):
        J.from_json_lines('{"not": "an envelope"}')
    with pytest.raises(ValueError, match="pair"):
        J.to_json_lines([np.zeros(3)])                      # not a (value, sort) pair
