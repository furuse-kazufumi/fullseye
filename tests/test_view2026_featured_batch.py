# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""目玉の一括の道具を回しても、目玉の集合(featured_ids)が変わらないこと(2026-11-08)。

以前の道具は台帳の PoC を全部目玉へ足していたので、約 40 件に絞った目玉が回すたびに 285 件へ戻った。
ファイルには書かず、関数 ``rebuild`` を committed の exhibits.json と台帳に当てて確かめる。
"""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "build_view2026_featured_batch", ROOT / "tools" / "build_view2026_featured_batch.py")
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)


def _inputs():
    d = json.loads(B.DATA.read_text(encoding="utf-8"))
    ledger = json.loads(B.LEDGER.read_text(encoding="utf-8"))["exhibits"]
    return d, ledger


def test_rerunning_the_tool_keeps_the_featured_set_and_every_card():
    d, ledger = _inputs()
    assert 30 <= len(d["featured_ids"]) < len(ledger)       # 台帳の全部ではない(絞った状態)
    new = B.rebuild(d, ledger)
    assert [e["id"] for e in new["exhibits"]] == d["featured_ids"]
    assert new["exhibits"] == d["exhibits"]                # 見出し・分類・図・see/num の切り方も残る
    assert new == d                                        # 他の欄にも触らない
    assert B.rebuild(new, ledger) == new                   # 2 回目も同じ


def test_the_tool_adds_only_listed_ids():
    d, ledger = _inputs()
    pid = next(e["id"] for e in ledger if e["id"] not in d["featured_ids"]
               and e["id"] in {a["id"] for a in d["all"]} and B.media_for(e["id"]))
    widened = copy.deepcopy(d)
    widened["featured_ids"].append(pid)
    new = B.rebuild(widened, ledger)
    assert [e["id"] for e in new["exhibits"]] == widened["featured_ids"]
    card = new["exhibits"][-1]
    assert card["see"]["ja"] + card["num"]["ja"] == next(e for e in ledger if e["id"] == pid)["caption_ja"]


def test_a_ledger_poc_missing_from_all_stops_the_tool():
    d, ledger = _inputs()
    victim = next(e["id"] for e in ledger if e["id"] not in d["featured_ids"])
    broken = copy.deepcopy(d)
    broken["all"] = [a for a in broken["all"] if a["id"] != victim]
    with pytest.raises(SystemExit) as exc:
        B.rebuild(broken, ledger)
    assert victim in str(exc.value)


def test_missing_or_duplicated_featured_ids_stop_the_tool():
    d, ledger = _inputs()
    for bad in (None, d["featured_ids"] + d["featured_ids"][:1]):
        broken = copy.deepcopy(d)
        broken["featured_ids"] = bad
        with pytest.raises(SystemExit):
            B.rebuild(broken, ledger)


def test_a_changed_caption_resets_the_split_to_the_full_caption():
    d, ledger = _inputs()
    pid = next(e["id"] for e in d["exhibits"] if "numbers_source" in e and e["num"]["ja"])
    changed = copy.deepcopy(ledger)
    row = next(e for e in changed if e["id"] == pid)
    row["caption_ja"] += "改"
    card = next(e for e in B.rebuild(d, changed)["exhibits"] if e["id"] == pid)
    assert (card["see"]["ja"], card["num"]["ja"]) == (row["caption_ja"], "")
