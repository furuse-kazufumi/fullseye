# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""教則の場面の再現台帳(docs/drive/kyosoku_scenarios.json)の門。

台帳は「交通の方法に関する教則」の運転者の場面 159 件に、Fullseye の PoC で再現しているかを付けたもの。門は両向き:
台帳が「PoC X が場面 S を再現」と言うなら X のソースが S を名指しし、PoC のソースが名指しする場面は台帳がその PoC を挙げる。
片方だけ直すと黙って食い違う(台帳を盛る / PoC を足したのに台帳が古い)ので、どちらの向きでも落ちる。
"""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs" / "drive" / "kyosoku_scenarios.json"
STATUSES = {"reproduced", "partial", "pending", "not_reproducible"}
SID = re.compile(r"\b(S\d{3})\b")
MARK = "教則の場面:"


def _ledger():
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def _named_in_poc(poc_id):
    """PoC のソースの「教則の場面: S…」行が名指しする場面の集合。"""
    src = (ROOT / "examples" / (poc_id + ".py")).read_text(encoding="utf-8")
    lines = [ln for ln in src.splitlines() if MARK in ln]
    return {m for ln in lines for m in SID.findall(ln)}


def test_every_scenario_has_a_status_and_the_ids_are_unique():
    rows = _ledger()["scenarios"]
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)) == 159
    assert {r["status"] for r in rows} <= STATUSES
    for r in rows:
        assert r["scene"] and r["action"], r["id"]
        if r["status"] in ("reproduced", "partial"):
            assert r["reproduced_by"] and r["note"], r["id"]
        elif r["status"] == "not_reproducible":
            assert not r["reproduced_by"] and r["note"], "%s: a reason is required" % r["id"]
        else:
            assert not r["reproduced_by"], r["id"]


def test_the_ledger_and_the_pocs_name_each_other():
    rows = _ledger()["scenarios"]
    claimed = {}
    for r in rows:
        for poc in r["reproduced_by"]:
            assert (ROOT / "examples" / (poc + ".py")).is_file(), (r["id"], poc)
            claimed.setdefault(poc, set()).add(r["id"])
    for poc, ids in claimed.items():
        named = _named_in_poc(poc)
        assert named == ids, "%s: ledger says %s, the PoC names %s" % (poc, sorted(ids - named), sorted(named - ids))
    for path in sorted((ROOT / "examples").glob("poc_*.py")):
        named = _named_in_poc(path.stem)
        assert not named or path.stem in claimed, "%s names scenarios %s the ledger does not credit" % (path.stem, sorted(named))


def test_the_counts_are_reported_with_reasons():
    c = Counter(r["status"] for r in _ledger()["scenarios"])
    assert sum(c.values()) == 159
    assert c["reproduced"] >= 22                  # 第 10 回の時点(下がったら PoC が場面を落とした)
    assert c["not_reproducible"] <= 10            # 「再現不能」に逃がしすぎない
