"""Type-model layer — the general-tier control types (`Seq`, `Scalar`) and the
unified sort vocabulary in ``fslib``.

These complete the "the sort is carried by the type, never guessed" foundation:
every Fullseye value (iconic FImage/Region/ObjectSet and control Seq/Scalar)
reports its own sort, none is implicitly truthy, and storage stays private.
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pytest

import algo
import fslib
from fslib import FsTypeError, Scalar, Seq


# --------------------------------------------------------------------------- #
# Seq
# --------------------------------------------------------------------------- #
def test_seq_basic_accessors():
    s = Seq.of([3, 1, 2])
    assert s.sort == "seq"
    assert s.length() == len(s) == 3
    assert s.tolist() == [3.0, 1.0, 2.0]
    assert s.real(1) == 1.0
    assert list(s) == [3.0, 1.0, 2.0]
    assert s[0] == 3.0


def test_seq_from_ndarray_generator_and_empty():
    assert Seq.of(np.array([1.5, 2.5])).tolist() == [1.5, 2.5]
    assert Seq.of(x for x in [4, 5]).tolist() == [4.0, 5.0]
    assert Seq.of([]).length() == 0


def test_seq_rejects_2d_from_list_and_ndarray():
    with pytest.raises(FsTypeError):
        Seq.of([[1, 2], [3, 4]])
    with pytest.raises(FsTypeError):
        Seq.of(np.zeros((2, 2)))


def test_seq_has_no_truth_value():
    with pytest.raises(FsTypeError):
        bool(Seq.of([1, 2]))
    with pytest.raises(FsTypeError):
        bool(Seq.of([]))                       # empty must ALSO raise, not be falsy


def test_seq_values_is_a_defensive_copy():
    s = Seq.of([1.0, 2.0, 3.0])
    v = s.values()
    v[0] = 99.0
    assert s.tolist() == [1.0, 2.0, 3.0]       # mutating the copy must not touch storage


def test_seq_construction_copies_the_input_array():
    # a "frozen" Seq must NOT alias the caller's ndarray (the write path, not just
    # the read path) — mutating the original must not change the Seq.
    a = np.array([1.0, 2.0, 3.0])
    s = Seq.of(a)
    a[0] = 99.0
    assert s.tolist() == [1.0, 2.0, 3.0]
    s2 = Seq(a)                                 # direct constructor too
    a[1] = 77.0
    assert s2.tolist() == [1.0, 99.0, 3.0]      # sees a[0]=99 (set above) but not a[1]=77


def test_seq_is_immutable():
    s = Seq.of([1.0])
    with pytest.raises(dataclasses.FrozenInstanceError):
        s._values = np.array([2.0])


def test_seq_rejects_non_numeric():
    with pytest.raises(FsTypeError):
        Seq.of(["1", "2.5"])                    # numeric strings are NOT numbers (no inference)
    with pytest.raises(FsTypeError):
        Seq.of(["abc"])                         # FsTypeError, not a bare ValueError


def test_seq_allows_non_finite_at_the_container_level():
    # a Seq is a general numeric container; NaN/inf are stored (algo.py enforces
    # finiteness at its own boundary). Pins the documented decision.
    s = Seq.of([np.nan, np.inf, -np.inf, 1.0])
    assert s.length() == 4 and not np.isfinite(s.values()[:3]).any()


def test_seq_and_scalar_value_equality_and_hash():
    assert Seq.of([1, 2, 3]) == Seq.of([1, 2, 3])
    assert Seq.of([1, 2, 3]) != Seq.of([1, 2, 4])
    assert Scalar.of(5.0) == Scalar.of(5.0)
    assert Scalar.of(5.0) != Scalar.of(6.0)
    # hashable by value (storage is write-protected)
    assert len({Seq.of([1, 2]), Seq.of([1, 2]), Seq.of([3])}) == 2
    assert len({Scalar.of(1.0), Scalar.of(1.0)}) == 1


# --------------------------------------------------------------------------- #
# Scalar
# --------------------------------------------------------------------------- #
def test_scalar_basic():
    x = Scalar.of(5.0)
    assert x.sort == "scalar"
    assert x.value() == 5.0
    assert float(x) == 5.0


def test_scalar_has_no_truth_value_even_for_zero():
    with pytest.raises(FsTypeError):
        bool(Scalar.of(0.0))                   # 0.0 must not read as False
    with pytest.raises(FsTypeError):
        bool(Scalar.of(5.0))


def test_scalar_is_immutable():
    x = Scalar.of(1.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        x._value = 2.0


# --------------------------------------------------------------------------- #
# unified sort vocabulary
# --------------------------------------------------------------------------- #
def test_sorts_vocabulary():
    assert fslib.SORTS == ("image", "region", "objectset", "seq", "scalar")


def test_every_value_reports_its_own_sort():
    img = fslib.FImage.from_u8(np.zeros((8, 8), np.uint8))
    reg = fslib.threshold(img, 0.5, 1.0)
    objs = fslib.connection(reg)
    assert img.sort == "image"
    assert reg.sort == "region"
    assert objs.sort == "objectset"
    assert Seq.of([1]).sort == "seq"
    assert Scalar.of(1).sort == "scalar"


def test_sort_of_matches_the_type():
    img = fslib.FImage.from_u8(np.zeros((8, 8), np.uint8))
    reg = fslib.threshold(img, 0.5, 1.0)
    objs = fslib.connection(reg)
    assert fslib.sort_of(img) == "image"
    assert fslib.sort_of(reg) == "region"
    assert fslib.sort_of(objs) == "objectset"
    assert fslib.sort_of(Seq.of([1, 2])) == "seq"
    assert fslib.sort_of(Scalar.of(3)) == "scalar"
    # every reported sort is in the vocabulary
    for v in (img, reg, objs, Seq.of([1]), Scalar.of(1)):
        assert fslib.sort_of(v) in fslib.SORTS


def test_sort_of_is_fail_closed_on_a_bare_array():
    # the whole point: a bare numpy array has NO carried sort (do not infer one)
    with pytest.raises(FsTypeError):
        fslib.sort_of(np.zeros((4, 4)))
    with pytest.raises(FsTypeError):
        fslib.sort_of([1, 2, 3])
    with pytest.raises(FsTypeError):
        fslib.sort_of(3.0)


# --------------------------------------------------------------------------- #
# bridge to the general-algorithm tier
# --------------------------------------------------------------------------- #
def test_algo_operates_on_a_typed_seq():
    s = Seq.of([5, 3, 1, 4, 2])
    assert algo.run_algo("quicksort", s) == [1.0, 2.0, 3.0, 4.0, 5.0]
    assert algo.run_algo("seq_max", s) == 5.0
    # round-trip through the typed value
    result = Seq.of(algo.run_algo("mergesort", s))
    assert result.sort == "seq" and result.tolist() == [1.0, 2.0, 3.0, 4.0, 5.0]


def test_general_tier_sort_names_match_the_type_model():
    # algo's SEQ/SCALAR constants are the SAME vocabulary fslib carries (unified).
    assert algo.SEQ == "seq" == fslib.sort_of(Seq.of([1]))
    assert algo.SCALAR == "scalar" == fslib.sort_of(Scalar.of(1))
    assert {algo.SEQ, algo.SCALAR} <= set(fslib.SORTS)
