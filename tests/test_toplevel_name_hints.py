"""Regression: guessed short names get a helpful AttributeError, never an alias (N223)."""
from __future__ import annotations

import pytest

import fullseye


@pytest.mark.parametrize("name,real", [
    ("Engine", "FullseyeEngine"),
    ("Graph", "FullseyeGraph"),
    ("op_info", "op_assist"),
    ("op_info", "op_find"),
    ("get_op", "find_op"),
])
def test_guessed_name_points_at_the_real_one(name, real):
    with pytest.raises(AttributeError) as ei:
        getattr(fullseye, name)
    msg = str(ei.value)
    assert "module 'fullseye' has no attribute '%s'" % name in msg
    assert "did you mean" in msg and real in msg


@pytest.mark.parametrize("name", ["Engine", "Graph", "op_info", "DAG"])
def test_no_alias_hasattr_stays_false(name):
    assert not hasattr(fullseye, name)
    assert name not in fullseye.__all__


def test_real_names_exist():
    for n in ("FullseyeEngine", "FullseyeGraph", "op_assist", "op_find", "find_op", "list_ops"):
        assert hasattr(fullseye, n), n


def test_unrelated_typo_is_plain_attribute_error():
    with pytest.raises(AttributeError) as ei:
        fullseye.gauss_filtr  # noqa: B018
    assert str(ei.value) == "module 'fullseye' has no attribute 'gauss_filtr'"


def test_star_import_unaffected():
    ns: dict = {}
    exec("from fullseye import *", ns)
    assert "FullseyeEngine" in ns and "Engine" not in ns
