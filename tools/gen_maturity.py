# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""能力ごとの成熟度を、宣言ではなく**事実から数えて**出す。

生成物: ``docs/MATURITY.md``(読む用)と ``docs/maturity.json``(機械可読)。

## なぜ要るか(2026-09-09)

v0.1.10 のリリースノートに「実データで検証済み」という成熟度の段を書いた。
書いた時点で**実写 PoC は 1 本も入っていなかった**(タグの中身を
``git show v0.1.10:examples2d.py`` で数えたら real は 0 件)。公開したあとに
自分で気づいて削除した。

**人が散文で書く成熟度は、この種の嘘を止められない。** だからここでは、4 段の
はしごを次の事実**だけ**から決める:

* 能力ノート(``docs/capabilities/*.md``)が名指す op と例
* 例の台帳(``examples2d`` / ``examples3d``)が持つ ``data: synthetic | real``
* その例を**実際に走らせる門があるか**
* op の名前が ``tests/`` のどこかに現れるか

## 数え方の規律

★**1 つの数字に畳まない。** 「例が実データか」「例が走るか」「op に試験があるか」は
別々に数え、JSON には生の事実を全部残す —— 畳むと未実行が「検証済み」に化ける
(``feedback_coverage_counts_ran_not_succeeded`` と同じ型)。

★``validated-hardware`` は**構造的に到達不能**にしてある。CI に実機センサが無い
以上、この生成器はその段を決して出さない。出したくなったら、まず実機を回す門を
作ること —— 段を先に書くのは順序が逆。

★「走る」の判定は**門の実体**に基づく。``examples/poc_*.py`` は
``tests/test_poc_scripts_run.py`` が全数を副プロセスで走らせる。3-D 例は
``examples3d.py`` の全数実行があり、スイートはその代表部分集合だけを走らせる。
**それ以外の 2-D 例を走らせる門は無い**(2026-09-09 実測: 199 件中 83 件)。
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

import examples2d as EX2  # noqa: E402
import examples3d as EX3  # noqa: E402

SRC_DIR = os.path.join(_ROOT, "docs", "capabilities")
OUT_MD = os.path.join(_ROOT, "docs", "MATURITY.md")
OUT_JSON = os.path.join(_ROOT, "docs", "maturity.json")

#: はしごの 4 段。順に強くなる。定義は生成物にも書き出す(読み手が判定を再現できるように)。
LADDER = [
    ("research-prototype",
     "実装はあるが、名指しの op に試験が揃っておらず、走る例も無い",
     "Implemented, but not every named operator is exercised by a test and no linked "
     "example is executed by a gate."),
    ("verified-synthetic",
     "真値を持つ合成データで自動検証済み(名指しの op 全部に試験があるか、走る例がある)",
     "Automatically verified against ground truth that is synthesised or computed in "
     "closed form."),
    ("validated-public-real-data",
     "公開された実写・実測データを使う例が、門で実際に走っている",
     "At least one linked example that runs in CI is driven by real, publicly "
     "available measured data."),
    ("validated-hardware",
     "実機センサ・装置につないで検証済み(★CI に実機が無いのでこの段は決して出ない)",
     "Validated against physical sensors or instruments. Never emitted: there is no "
     "hardware in CI."),
]

REQUIRED_KEYS = ("id", "title", "title_en", "category", "ops", "examples", "version")


class MaturityError(RuntimeError):
    """能力ノートから成熟度を決められない(fail-closed: 表を作らずに止める)。"""


def _front_matter(text: str, path: str) -> dict:
    if not text.startswith("---\n"):
        raise MaturityError("%s: YAML front matter が無い" % path)
    end = text.find("\n---\n", 4)
    if end < 0:
        raise MaturityError("%s: front matter が閉じていない" % path)
    meta = {}
    for line in text[4:end].split("\n"):
        line = line.split("  #", 1)[0].rstrip()
        if not line.strip() or ":" not in line:
            continue
        key, val = line.split(":", 1)
        key, val = key.strip(), val.strip()
        if val.startswith("[") and val.endswith("]"):
            meta[key] = [x.strip() for x in val[1:-1].split(",") if x.strip()]
        else:
            meta[key] = val.strip('"')
    for k in REQUIRED_KEYS:
        if k not in meta:
            raise MaturityError("%s: front matter に %s が無い" % (path, k))
    return meta


def _test_sources() -> str:
    """``tests/`` の全ソースを 1 本に(op 名の出現を数えるため)。"""
    parts = []
    for p in sorted(glob.glob(os.path.join(_ROOT, "tests", "*.py"))):
        parts.append(io.open(p, encoding="utf-8", errors="ignore").read())
    return "\n".join(parts)


def _example_facts(eid: str) -> dict:
    """例 1 件について ``data`` と「どの門が走らせるか」を返す。

    ★ここが嘘をつくと表全体が嘘になるので、**門の実体に対応する文字列**しか返さない。
    """
    e2 = EX2._BY_ID.get(eid)
    e3 = EX3._BY_ID.get(eid)
    if e2 is None and e3 is None:
        raise MaturityError("例 %s がどちらの台帳にも無い" % eid)
    entry = e2 or e3
    data = entry.get("data", "unknown")
    if e2 is not None and eid.startswith("poc_"):
        gate = "tests/test_poc_scripts_run.py"
    elif e3 is not None:
        gate = "examples3d.py (suite runs a smoke subset)"
    else:
        gate = None
    return {"id": eid, "data": data, "gate": gate,
            "executed": gate is not None,
            "registry": "examples2d" if e2 is not None else "examples3d"}


def _status(ops_total: int, ops_tested: int, examples: list) -> str:
    ran = [e for e in examples if e["executed"]]
    if any(e["data"] == "real" for e in ran):
        return "validated-public-real-data"
    if ran or (ops_total and ops_tested == ops_total):
        return "verified-synthetic"
    return "research-prototype"


def collect() -> dict:
    tests = _test_sources()
    rows = []
    for path in sorted(glob.glob(os.path.join(SRC_DIR, "*.md"))):
        meta = _front_matter(io.open(path, encoding="utf-8").read(), path)
        ops = list(meta["ops"])
        # ★これは**下界**。``tests/`` に op 名が literal で現れるかしか見ていないので、
        # 台帳を舐めて全 op を回す掃引型の試験(``for name in ledger: ...``)は数えない。
        # 「試験が無い」ではなく「**名指しの試験が無い**」と読むこと。
        tested = [o for o in ops if re.search(r"\b%s\b" % re.escape(o), tests)]
        examples = [_example_facts(e) for e in meta["examples"]]
        rows.append({
            "id": meta["id"],
            "title": meta["title"],
            "title_en": meta["title_en"],
            "category": meta["category"],
            "note": "docs/capabilities/%s" % os.path.basename(path),
            "status": _status(len(ops), len(tested), examples),
            "ops_total": len(ops),
            "ops_named_in_tests": len(tested),
            "ops_not_named_in_tests": sorted(set(ops) - set(tested)),
            "ops_count_is_a_lower_bound":
                "tests/ に op 名が literal で現れるかだけを見ている"
                "(台帳を舐める掃引型の試験は数えない)",
            "examples": examples,
        })

    all_2d = [e["id"] for e in EX2.EXAMPLES]
    unrun = [i for i in all_2d if not i.startswith("poc_")]
    return {
        "generated_by": "tools/gen_maturity.py",
        "how_to_read": "ladder の判定は capabilities[].examples と ops_with_tests から "
                       "機械的に決まる。生の事実を残してあるので判定を再現できる。",
        "ladder": [{"id": i, "ja": ja, "en": en} for i, ja, en in LADDER],
        "capabilities": rows,
        "example_execution": {
            "examples2d_total": len(all_2d),
            "run_by_a_gate": len(all_2d) - len(unrun),
            "not_run_by_any_gate": len(unrun),
            "gate_for_poc": "tests/test_poc_scripts_run.py",
            "note": "2-D 台帳のうち poc_* 以外は、どの門も実行していない"
                    "(2026-09-09 に数えた)。",
        },
    }


def render(d: dict) -> str:
    out = ["# 成熟度台帳(Maturity)", "",
           "**Language:** 日本語 / English column in the table.", "",
           "この表は**手で書いていません**。`tools/gen_maturity.py` が能力ノート・例の台帳・",
           "門の実体・`tests/` の中身から数えて出します。`tests/test_maturity.py` が",
           "コミット済みの内容と生成物を突き合わせるので、古びると CI が落ちます。", "",
           "*This ledger is generated, not written. Each row's status is derived from facts "
           "in the repository — which operators have tests, which linked examples an actual "
           "gate executes, and whether that example is driven by real measured data.*", "",
           "## はしご(4 段)", ""]
    out.append("| 段 | 意味 | Meaning |")
    out.append("|---|---|---|")
    for i, ja, en in LADDER:
        out.append("| `%s` | %s | %s |" % (i, ja, en))
    out += ["",
            "★ **`validated-hardware` は決して出ません。** CI に実機センサが無いからです。",
            "段を先に書くのは順序が逆なので、生成器の側で構造的に到達不能にしてあります。",
            "", "## 能力ごと", "",
            "| 能力 | Capability | 分類 | 段 | op(試験あり/全) | 例(走る門) |",
            "|---|---|---|---|---|---|"]
    for r in d["capabilities"]:
        ex = "<br>".join(
            "`%s` %s %s" % (e["id"], e["data"],
                            ("→ %s" % e["gate"]) if e["executed"] else "→ **走る門が無い**")
            for e in r["examples"])
        out.append("| [%s](capabilities/%s) | %s | %s | `%s` | %d/%d | %s |" % (
            r["title"], os.path.basename(r["note"]), r["title_en"], r["category"],
            r["status"], r["ops_with_tests"], r["ops_total"], ex))
    e = d["example_execution"]
    out += ["", "## 例が実際に走っているか", "",
            "| | 件数 |", "|---|---|",
            "| 2-D 台帳の例 | %d |" % e["examples2d_total"],
            "| 門が走らせている(`poc_*`) | %d |" % e["run_by_a_gate"],
            "| **どの門も走らせていない** | **%d** |" % e["not_run_by_any_gate"],
            "",
            "走らせない門は、実行時の壊れに盲目です(2026-09-06 に PoC 側で同じ形の穴が",
            "見つかり、31 本のうち 4 本が exit 1 のまま放置されていました)。",
            "機械可読版は [`maturity.json`](maturity.json)。", ""]
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="書き込まず、コミット済みと一致するかだけ見る(exit 1 で不一致)")
    args = ap.parse_args(argv)
    data = collect()
    md = render(data)
    js = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    if args.check:
        bad = []
        for path, want in ((OUT_MD, md), (OUT_JSON, js)):
            got = io.open(path, encoding="utf-8").read() if os.path.exists(path) else None
            if got != want:
                bad.append(os.path.relpath(path, _ROOT))
        if bad:
            print("drift: %s (py -3.11 tools/gen_maturity.py で作り直す)" % ", ".join(bad))
            return 1
        print("maturity: up to date")
        return 0
    io.open(OUT_MD, "w", encoding="utf-8", newline="\n").write(md)
    io.open(OUT_JSON, "w", encoding="utf-8", newline="\n").write(js)
    print("wrote %s and %s" % (os.path.relpath(OUT_MD, _ROOT),
                               os.path.relpath(OUT_JSON, _ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
