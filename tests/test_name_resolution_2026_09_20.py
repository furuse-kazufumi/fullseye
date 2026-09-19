# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""名前解決層(GenSpark 第 20・21 報、2026-09-20): HALCON 別名の衝突は規則で決まり行から見える(N84)、
list_ops の sort / search は大小とアクセントを畳む(N85)、op_run は種を作れない型に None を渡さない(N87)。
"""
from __future__ import annotations

import collections
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import api  # noqa: E402
import fullseye as fs  # noqa: E402
import opassist as A  # noqa: E402
import ops  # noqa: E402


def _claims() -> dict:
    claims = collections.defaultdict(list)
    for o in ops.REGISTRY:
        if o.halcon:
            claims[o.halcon].append(o.name)
    return claims


def test_every_shared_alias_resolves_by_rule_not_by_registration_order():
    names = {o.name for o in ops.REGISTRY}
    shared = {a: v for a, v in _claims().items() if len(v) > 1}
    assert shared                                                   # 衝突は存在する(cv_ / sk_ の移植)
    for alias, claimants in shared.items():
        chosen = fs.find_op(alias).name
        if alias in names:
            assert chosen == alias, (alias, chosen)                 # 完全一致が勝つ
        else:
            assert alias in api._ALIAS_CANONICAL, "shared alias %r has no canonical op and no explicit row: %s" % (alias, claimants)
            assert chosen == api._ALIAS_CANONICAL[alias] and chosen in claimants


def test_list_ops_rows_name_their_alias_peers():
    by = {r["name"]: r for r in fs.list_ops() if r["tier"] == "registry"}
    assert all("halcon_peers" in r for r in by.values())
    claims = _claims()
    for alias, claimants in claims.items():
        for n in claimants:
            assert by[n]["halcon_peers"] == sorted(c for c in claimants if c != n)
    assert by["gaussian"]["halcon_peers"] == [] or "gaussian" not in by["gaussian"]["halcon_peers"]
    assert by["unsharp"]["halcon_peers"] == ["cv_sharpen"] and by["cv_sharpen"]["halcon_peers"] == ["unsharp"]


def test_list_ops_sort_and_search_fold_case_and_accents():
    assert len(fs.list_ops(sort="IMAGE")) == len(fs.list_ops(sort="image")) > 0
    assert len(fs.list_ops(search="GAUSS")) == len(fs.list_ops(search="gauss")) > 0
    assert {r["name"] for r in fs.list_ops(search="ötsu")} == {r["name"] for r in fs.list_ops(search="otsu")}
    assert fs.list_ops(search="ötsu")


@pytest.mark.parametrize("name", ["delta_e_2000", "geodesic_mesh", "lab_to_rgb", "mesh_to_points", "sinkhorn_divergence", "xyz_to_lab"])
def test_op_run_refuses_to_call_with_a_none_sample_and_names_the_sort(name):
    if A._ledger_entry(name)[1] is None:
        pytest.skip("%s not in a ledger here" % name)
    args, _kw = A.sample_input(name)
    if all(a is not None for a in args):
        pytest.skip("%s now has a sample" % name)
    with pytest.raises(ValueError, match="no built-in sample for input sort"):
        fs.op_run(name)


def test_op_run_with_a_sample_still_runs():
    out, notes = fs.op_run("a3_distribution")
    assert out is not None
