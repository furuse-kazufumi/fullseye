"""畳まれた型(``TYPE_TO_SORT``)の台帳を門にする。

``backends_typed.TYPE_TO_SORT`` は宣言型を進化側の sort に畳む。畳むと繋げる
組合せは増えるが、**隣の型を渡しても例外が出ない**経路も同時に増える
(位置の点群を法線として、ラベルを SDF として、Hz を counts として)。

この門は 3 つを別々に測る:

1. ``TYPE_TO_SORT`` から導いた「2 語以上が同じ sort に畳まれている組」が、
   ``docs/TYPE_ALIAS_LEDGER.json`` の組と**厳密に一致**すること。
   —— 新しい alias を、実測も理由も書かずに足せなくする。
2. ``fail_closed: true`` と書いた行は、**実際に例外が出ること**。
   —— 「検査を書いた」と「検査が効いている」を分ける(検査が死んでいても
   台帳の行は残るので、行の存在では確かめたことにならない)。
3. ``documented_at`` に挙げた関数の docstring に、実測値が本当に載っていること。
   —— 台帳と docstring がずれると、読む人は docstring しか見ない。
"""
import json
import os

import numpy as np
import pytest

import backends_typed as bt
import fullseye as fs

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "..", "docs", "TYPE_ALIAS_LEDGER.json")


def _ledger():
    with open(LEDGER, encoding="utf-8") as fh:
        return json.load(fh)


def _collapsed_groups():
    """``TYPE_TO_SORT`` から「2 語以上が同じ sort に畳まれている組」を作る。"""
    by_sort = {}
    for typ, sort in bt.TYPE_TO_SORT.items():
        if sort is None:
            continue
        by_sort.setdefault(sort, set()).add(typ)
    return {sort: types for sort, types in by_sort.items() if len(types) > 1}


def test_ledger_covers_exactly_the_collapsed_groups():
    groups = _collapsed_groups()
    led = {e["sort"]: set(e["types"]) for e in _ledger()["aliases"]}
    assert set(led) == set(groups), (
        "TYPE_TO_SORT の畳み方が台帳とずれた。新しい alias を足したなら "
        "docs/TYPE_ALIAS_LEDGER.json に理由・実測・fail_closed を書くこと。\n"
        f"  台帳にあって実体に無い: {sorted(set(led) - set(groups))}\n"
        f"  実体にあって台帳に無い: {sorted(set(groups) - set(led))}")
    for sort in sorted(groups):
        assert led[sort] == groups[sort], (
            f"sort '{sort}' に畳まれる型が変わった: 実体 {sorted(groups[sort])} / "
            f"台帳 {sorted(led[sort])}")


def test_every_alias_row_is_filled_in():
    for e in _ledger()["aliases"]:
        tag = "/".join(e["types"])
        assert len(e.get("why", "")) > 20, f"{tag}: why が空"
        assert len(e.get("crossing_measured", "")) > 40, f"{tag}: 実測が書かれていない"
        assert isinstance(e.get("fail_closed"), bool), f"{tag}: fail_closed が bool でない"
        key = "fail_closed_how" if e["fail_closed"] else "fail_closed_why_not"
        assert len(e.get(key, "")) > 20, f"{tag}: {key} が空"
        assert e.get("documented_at"), f"{tag}: documented_at が空"


def test_normals_alias_is_really_fail_closed():
    """位置の点群を法線として渡すと、``extra_checks='on'`` が拒否する。"""
    t = np.linspace(0.0, 1.0, 200)
    pts = np.stack([t, 0.3 + 0.2 * np.sin(6.0 * t), 0.5 + 0.4 * t], axis=1)
    unit = np.tile(np.array([0.0, 0.0, 1.0]), (200, 1))

    # 既定は通る(進化器を壊さないため)—— 通ることも測っておく
    assert float(np.asarray(fs.ledger.normals_to_egi(pts)).sum()) == 200.0
    with fs.system(extra_checks="on"):
        assert float(np.asarray(fs.ledger.normals_to_egi(unit)).sum()) == 200.0
        with pytest.raises(ValueError, match="not unit length"):
            fs.ledger.normals_to_egi(pts)


def test_indices_alias_is_really_fail_closed():
    """連続な信号を添字として渡すと、既定で拒否する(extra_checks 不要)。"""
    sig = 0.5 + 0.4 * np.sin(np.linspace(0.0, 6.0, 64))
    idx = np.array([3, 11, 29, 47], dtype=float)
    assert int((np.asarray(fs.ledger.indices_to_labels(idx)) != 0).sum()) == 4
    with pytest.raises(ValueError, match="whole numbers"):
        fs.ledger.indices_to_labels(sig)


def test_labels_as_sdf_still_produces_the_recorded_number():
    """台帳に書いた「5.5 倍」が今も再現すること(直したら台帳を直す)。"""
    m = 24
    gz, gy, gx = np.mgrid[0:m, 0:m, 0:m].astype(float)
    sdf = np.maximum.reduce([np.abs(gx - 11.5) - 6.0,
                             np.abs(gy - 11.5) - 6.0,
                             np.abs(gz - 11.5) - 6.0])
    lab = (sdf < 0).astype(float)
    lab[np.abs(gx - 11.5) < 3] += 1.0
    right = int((np.asarray(fs.ledger.sdf_to_occupancy(sdf)) > 0.5).sum())
    wrong = int((np.asarray(fs.ledger.sdf_to_occupancy(lab)) > 0.5).sum())
    assert right == 1728, right
    assert wrong == 9504, wrong


def test_countrate_double_application_is_still_1000x():
    rate = np.full(64, 1200.0)
    once = np.asarray(fs.ledger.countrate_to_counts(rate, gate_s=1e-3), float)
    twice = np.asarray(fs.ledger.countrate_to_counts(once, gate_s=1e-3), float)
    assert abs(once.mean() - 1.2) < 1e-12
    assert abs(once.mean() / twice.mean() - 1000.0) < 1e-6


@pytest.mark.parametrize("fn,needle", [
    ("match3d.sdf_to_occupancy", "9,504"),
    ("reprconv.normals_to_egi", "総和はどちらも 200"),
    ("reprconv.countrate_to_counts", "1,000 倍"),
    ("reprconv.indices_to_labels", "可逆"),
    ("range_image.normals_from_depth", "spacing"),
])
def test_documented_at_really_documents_it(fn, needle):
    import importlib
    mod, name = fn.rsplit(".", 1)
    doc = getattr(importlib.import_module(mod), name).__doc__ or ""
    assert needle in doc, f"{fn} の docstring に「{needle}」が無い(台帳とずれた)"
