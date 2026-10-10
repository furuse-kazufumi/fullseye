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

★``validated-hardware`` は**この repo の中の事実からは到達不能**にしてある。CI に
実機センサが無い以上、repo 内の門だけではその段を決して出さない。到達する道は 1 本
だけ —— **実機・実データを持つ外部の人の検証報告**を保守者が受理し、
``docs/validation_reports.json`` に記録したとき(2026-10-11)。その場合も段は
「受理した」だけでは上がらず、下の昇格規則(``PROMOTION_RULES``)を機械的に満たした
報告だけが効く。段を先に書くのは順序が逆、という規律は変わらない。

★**データを出せない人の報告を一級の経路にする。** 企業の画像・CAD・測定値は普通
外に出せない。だから報告の ``data_sharing`` は ``shared`` / ``synthetic-recreation``
/ ``results-only`` の 3 通りで、``results-only``(結果の数値だけ)も数える ——
ただし重みは低い: 再現できる報告は 1 件で段が上がるが、結果だけの報告は
**別の人・別の装置の 2 件以上が、それぞれ申告した不確かさの中で合う**ことが要る。

★外部報告の台帳が**空のとき**、能力ごとの行と ``maturity.json`` の能力行は
外部報告の導入前と**同じ**になる(空の台帳で表が動いたら、台帳が黙って何かを
主張している)。``tests/test_maturity.py`` が確かめる。

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
     "実機センサ・装置で検証済み(★CI に実機は無い。外部の実機検証報告を保守者が受理し、"
     "昇格規則を満たしたときだけ出る)",
     "Validated against physical sensors or instruments. CI has no hardware, so this is "
     "emitted only from accepted external reports that meet the promotion rules "
     "(docs/VALIDATION_CONTRIBUTING.en.md)."),
]

#: 段の強さの順。外部報告と repo 内の判定は**強いほう**を採る(弱めることはしない)。
_RANK = {i: n for n, (i, _ja, _en) in enumerate(LADDER)}

#: 外部の検証報告の台帳(保守者が受理した報告を手で記録する。生成器は読むだけ)。
REGISTRY = os.path.join(_ROOT, "docs", "validation_reports.json")
REGISTRY_REL = "docs/validation_reports.json"
#: 報告を出す入口(GitHub の issue form)。
ISSUE_FORM_URL = ("https://github.com/furuse-kazufumi/fullseye/issues/new"
                  "?template=real_validation_report.yml")

#: 報告 1 件の必須キー。
REPORT_REQUIRED = ("id", "capability", "kind", "review", "source", "reporter", "setup",
                   "ground_truth", "ground_truth_uncertainty", "procedure",
                   "fullseye_version", "result", "data_sharing", "received_on")
#: 任意キー。**ここに無いキーは拒む**(fail-closed)。★所属・勤務先・製品名の欄は
#: 意図して持たない —— 報告者に求めない情報は、台帳に置く場所も作らない。
REPORT_OPTIONAL = ("credit", "traceable_reference", "reproduced_by_maintainer",
                   "within_stated_uncertainty", "data_licence", "data_url",
                   "reviewed_on", "failure_conditions", "note")
REPORT_BOOLS = ("traceable_reference", "reproduced_by_maintainer",
                "within_stated_uncertainty")
REPORT_KINDS = ("hardware", "public-real-data")
REPORT_REVIEWS = ("pending", "accepted", "not-reproduced", "withdrawn")
#: データの出し方。``results-only`` も正規の経路(重みが低いだけ)。
DATA_SHARING = ("shared", "synthetic-recreation", "results-only")
#: ``source`` に書ける非公開提出の印(メールで受け取り、同意の上で集計値だけ公開)。
PRIVATE_SOURCE = "private-submission"

#: 昇格規則。生成物にも書き出す(読み手が判定を再現できるように)。
PROMOTION_RULES = [
    ("hardware-reproducible", "validated-hardware",
     "実機の報告 1 件で足りる条件: 受理済み・真値が追跡可能な基準(校正済み計測器 / "
     "認証された基準器 / 公表値)・データか合成で作り直したデータと手順を共有・"
     "保守者がそれで再実行して、申告した不確かさの中で同じ数値を得た",
     "One accepted hardware report with a traceable reference (calibrated instrument, "
     "certified artefact or published values) that shares its data or a synthetic "
     "re-creation of it plus the procedure, and that the maintainer re-ran and "
     "reproduced within the stated uncertainty."),
    ("hardware-independent-results", "validated-hardware",
     "結果だけの報告でも足りる条件(重みが低いので 2 件以上): 受理済みの実機報告が "
     "2 件以上・報告者が別・装置構成が別・どれも真値が追跡可能・どれも申告した不確かさの"
     "中で合っている(データ共有は不要)",
     "Two or more accepted hardware reports (results-only is fine) from different "
     "reporters on different setups, each with a traceable reference and each "
     "agreeing within its stated uncertainty. Data need not be shared."),
    ("public-data-reproduced", "validated-public-real-data",
     "公開実データの報告 1 件で足りる条件: 受理済み・データの URL とライセンスがある・"
     "保守者が同じデータで再実行して報告どおりの数値を得た",
     "One accepted report on a public real dataset (URL and licence given) that the "
     "maintainer re-ran and reproduced."),
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
    elif e2 is not None:
        gate = "tests/test_example_scripts_run.py"
    elif e3 is not None:
        gate = "examples3d.py (suite runs a smoke subset)"
    else:
        gate = None
    return {"id": eid, "data": data, "gate": gate,
            "executed": gate is not None,
            "registry": "examples2d" if e2 is not None else "examples3d"}


def load_registry(path: str = REGISTRY, capability_ids=None) -> list:
    """外部の検証報告の台帳を読み、**形を全部確かめてから**返す(fail-closed)。

    台帳は保守者が手で書くので、ここが最後の検査になる。未知のキー・型違い・
    未知の能力・重複 id は全部止める —— 1 件でも疑わしければ表を作らない。
    """
    if not os.path.exists(path):
        raise MaturityError("%s が無い(空でも reports を空配列にして置く)" % path)
    try:
        with io.open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except ValueError as exc:
        raise MaturityError("%s: JSON として読めない: %s" % (path, exc))
    if not isinstance(doc, dict) or not isinstance(doc.get("reports"), list):
        raise MaturityError("%s: 最上位は reports 配列を持つオブジェクトであること" % path)
    seen = set()
    out = []
    for n, r in enumerate(doc["reports"]):
        where = "%s reports[%d]" % (os.path.basename(path), n)
        if not isinstance(r, dict):
            raise MaturityError("%s: オブジェクトでない" % where)
        missing = [k for k in REPORT_REQUIRED if k not in r]
        if missing:
            raise MaturityError("%s: 必須キーが無い: %s" % (where, missing))
        unknown = sorted(set(r) - set(REPORT_REQUIRED) - set(REPORT_OPTIONAL))
        if unknown:
            raise MaturityError("%s: 未知のキー %s(所属・勤務先・製品名などは記録しない)"
                                % (where, unknown))
        for k in REPORT_REQUIRED:
            if not isinstance(r[k], str) or not r[k].strip():
                raise MaturityError("%s: %s は空でない文字列であること" % (where, k))
        for k in REPORT_BOOLS:
            if k in r and not isinstance(r[k], bool):
                raise MaturityError("%s: %s は true/false であること" % (where, k))
        if r.get("credit") is not None and not isinstance(r["credit"], str):
            raise MaturityError("%s: credit は文字列か null" % where)
        if r["kind"] not in REPORT_KINDS:
            raise MaturityError("%s: kind は %s のどれか" % (where, REPORT_KINDS))
        if r["review"] not in REPORT_REVIEWS:
            raise MaturityError("%s: review は %s のどれか" % (where, REPORT_REVIEWS))
        if r["data_sharing"] not in DATA_SHARING:
            raise MaturityError("%s: data_sharing は %s のどれか" % (where, DATA_SHARING))
        if not (r["source"].startswith("https://") or r["source"] == PRIVATE_SOURCE):
            raise MaturityError("%s: source は https の URL か %s" % (where, PRIVATE_SOURCE))
        if r["id"] in seen:
            raise MaturityError("%s: id %s が重複" % (where, r["id"]))
        seen.add(r["id"])
        if capability_ids is not None and r["capability"] not in capability_ids:
            raise MaturityError("%s: 能力 %s が docs/capabilities に無い"
                                % (where, r["capability"]))
        out.append(r)
    return out


def _report_route(r: dict):
    """報告 1 件**だけで**満たす昇格規則の id(無ければ None)。"""
    if r["review"] != "accepted":
        return None
    if (r["kind"] == "hardware" and r.get("traceable_reference") is True
            and r["data_sharing"] in ("shared", "synthetic-recreation")
            and r.get("reproduced_by_maintainer") is True
            and r.get("within_stated_uncertainty") is True):
        return "hardware-reproducible"
    if (r["kind"] == "public-real-data" and r.get("reproduced_by_maintainer") is True
            and (r.get("data_url") or "").startswith("https://")
            and (r.get("data_licence") or "").strip()):
        return "public-data-reproduced"
    return None


def external_status(reports: list):
    """能力 1 つに付いた報告群から (段, 満たした規則の一覧) を返す。段が無ければ (None, [])。

    ★結果だけの報告は 1 件では段を上げない。別の人・別の装置で、どれも追跡可能な
    基準を持ち、どれも申告した不確かさの中で合っている 2 件以上が要る。
    """
    routes = {x for x in (_report_route(r) for r in reports) if x}
    agree = [r for r in reports if r["review"] == "accepted" and r["kind"] == "hardware"
             and r.get("traceable_reference") is True
             and r.get("within_stated_uncertainty") is True]
    if (len({r["reporter"].strip().lower() for r in agree}) >= 2
            and len({r["setup"].strip().lower() for r in agree}) >= 2):
        routes.add("hardware-independent-results")
    stage = None
    for rid, st, _ja, _en in PROMOTION_RULES:
        if rid in routes and (stage is None or _RANK[st] > _RANK[stage]):
            stage = st
    return stage, sorted(routes)


def _status(ops_total: int, ops_tested: int, examples: list) -> str:
    ran = [e for e in examples if e["executed"]]
    if any(e["data"] == "real" for e in ran):
        return "validated-public-real-data"
    if ran or (ops_total and ops_tested == ops_total):
        return "verified-synthetic"
    return "research-prototype"


def collect(registry_path: str = REGISTRY) -> dict:
    tests = _test_sources()
    rows = []
    paths = sorted(glob.glob(os.path.join(SRC_DIR, "*.md")))
    cap_ids = {_front_matter(io.open(p, encoding="utf-8").read(), p)["id"] for p in paths}
    reports = load_registry(registry_path, cap_ids)
    for path in paths:
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
        mine = [r for r in reports if r["capability"] == meta["id"]]
        if mine:
            # ★報告が付いた行にだけ鍵を足す(空の台帳で出力を動かさない)。
            # repo 内の判定は別の鍵に残す —— 1 つの段に畳まない。
            row = rows[-1]
            row["status_from_repository"] = row["status"]
            stage, routes = external_status(mine)
            if stage and _RANK[stage] > _RANK[row["status"]]:
                row["status"] = stage
            row["external_rules_met"] = routes
            row["external_reports"] = [{
                "id": r["id"], "kind": r["kind"], "review": r["review"],
                "source": r["source"], "data_sharing": r["data_sharing"],
                "credit": r.get("credit"),
                "single_report_rule": _report_route(r),
            } for r in mine]

    all_2d = [e["id"] for e in EX2.EXAMPLES]
    poc = [i for i in all_2d if i.startswith("poc_")]
    other = [i for i in all_2d if not i.startswith("poc_")]
    out = {
        "generated_by": "tools/gen_maturity.py",
        "how_to_read": "ladder の判定は capabilities[].examples と ops_named_in_tests から "
                       "機械的に決まる。生の事実を残してあるので判定を再現できる。",
        "ladder": [{"id": i, "ja": ja, "en": en} for i, ja, en in LADDER],
        "capabilities": rows,
        "example_execution": {
            "examples2d_total": len(all_2d),
            "run_by_the_poc_gate": len(poc),
            "run_by_the_example_gate": len(other),
            "not_run_by_any_gate": 0,
            "gates": ["tests/test_poc_scripts_run.py",
                      "tests/test_example_scripts_run.py"],
            "note": "2026-09-09 まで poc_* 以外の 83 件を実行する門が無く、"
                    "そのうち 2 件が exit 1 のまま残っていた。両方の門とも "
                    "PYTHONPATH を渡さずに走らせる(利用者と同じ条件)。",
        },
    }
    if reports:
        out["external_validation"] = {
            "registry": REGISTRY_REL,
            "report_form": ISSUE_FORM_URL,
            "reports_total": len(reports),
            "accepted": sum(1 for r in reports if r["review"] == "accepted"),
            "promotion_rules": [{"id": i, "promotes_to": st, "ja": ja, "en": en}
                                for i, st, ja, en in PROMOTION_RULES],
        }
    return out


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
            "★ **`validated-hardware` は repo の中の事実からは出ません。** CI に実機センサが",
            "無いからです。出る道は 1 本だけで、実機・実データを持つ人の検証報告を保守者が",
            "受理して `%s` に記録し、昇格規則を満たしたときです。" % REGISTRY_REL,
            "データを外に出せない場合も、結果の数値だけで報告できます。",
            "",
            "*Fullseye is developed without physical measurement rigs, so CI can only verify "
            "against synthetic or computed ground truth. If you have real hardware or real "
            "data, your results can move a capability up this ladder — results-only reports "
            "(data kept private) count too:* "
            "[report form](%s) · [how reports are judged](VALIDATION_CONTRIBUTING.en.md) · "
            "[日本語](VALIDATION_CONTRIBUTING.md)" % ISSUE_FORM_URL,
            "", "## 能力ごと", "",
            "| 能力 | Capability | 分類 | 段 | op(名指しの試験/全) | 例(走る門) |",
            "|---|---|---|---|---|---|"]
    for r in d["capabilities"]:
        ex = "<br>".join(
            "`%s` %s %s" % (e["id"], e["data"],
                            ("→ %s" % e["gate"]) if e["executed"] else "→ **走る門が無い**")
            for e in r["examples"])
        out.append("| [%s](capabilities/%s) | %s | %s | `%s` | %d/%d | %s |" % (
            r["title"], os.path.basename(r["note"]), r["title_en"], r["category"],
            r["status"], r["ops_named_in_tests"], r["ops_total"], ex))
    ext = d.get("external_validation")
    out += ["", "## 外部からの検証報告(External validation reports)", ""]
    if not ext:
        out += ["記録した報告はまだ **0 件**です(`%s` は空)。" % REGISTRY_REL,
                "*No external report has been recorded yet.*"]
    else:
        out += ["受理 %d 件 / 記録 %d 件。昇格規則:" % (ext["accepted"], ext["reports_total"]),
                "", "| 規則 | 上がる段 | 条件 | Condition |", "|---|---|---|---|"]
        for p in ext["promotion_rules"]:
            out.append("| `%s` | `%s` | %s | %s |" % (p["id"], p["promotes_to"],
                                                    p["ja"], p["en"]))
        out += ["", "| 能力 | 報告 | 種類 | データ | 審査 | 単独で満たす規則 | 謝辞 |",
                "|---|---|---|---|---|---|---|"]
        for r in d["capabilities"]:
            for x in r.get("external_reports", []):
                src = x["source"]
                ref = ("[%s](%s)" % (x["id"], src)) if src.startswith("https://") \
                    else "%s (%s)" % (x["id"], src)
                out.append("| %s | %s | %s | %s | %s | %s | %s |" % (
                    r["id"], ref, x["kind"], x["data_sharing"], x["review"],
                    ("`%s`" % x["single_report_rule"]) if x["single_report_rule"] else "-",
                    x["credit"] or "-"))
    e = d["example_execution"]
    out += ["", "## 例が実際に走っているか", "",
            "| | 件数 |", "|---|---|",
            "| 2-D 台帳の例 | %d |" % e["examples2d_total"],
            "| `tests/test_poc_scripts_run.py` が走らせる | %d |" % e["run_by_the_poc_gate"],
            "| `tests/test_example_scripts_run.py` が走らせる | %d |"
            % e["run_by_the_example_gate"],
            "| **どの門も走らせていない** | **%d** |" % e["not_run_by_any_gate"],
            "",
            "走らせない門は、実行時の壊れに盲目です。2026-09-06 に PoC 側で穴が見つかり",
            "(31 本のうち 4 本が exit 1 のまま放置)、**2026-09-09 に同じ穴が 1 つ内側で",
            "再演していた**ことが分かりました —— 門を作ったのに、対象を数え直さなかったので",
            "`poc_*` 以外の 83 件が外に残り、そのうち 2 件が落ちていました。",
            "どちらの門も `PYTHONPATH` を渡さずに走らせます(利用者と同じ条件)。",
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
