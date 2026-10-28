# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Find operators by what they do, in any of the supported languages -> ranked rows.

意味で op を引く検索(RAG の入口)。``fullseye.search_ops("ノイズ除去")`` /
``fullseye-rag search "remove noise"`` / MCP ``fullseye_find_ops`` が同じ関数を呼ぶ。

**なぜ要るか(2026-10-07 実測)**: 知識層のノート ``docs/ops`` は本文が日本語なので、grep は
「Rauschen」「降噪」「잡음」で 0 件、「vanishing point」でも 0 件だった。op 名の部分一致
(MCP ``fullseye_search_ops``)は名前を知っている人にしか効かない。一方で全 op の要約は
``docs/i18n/op_summary.json`` に en / zh / tw / ko / de の訳がある —— それを検索面にする。

**何を照合するか**: op 名(``_`` で区切った語)・HALCON 名・族 / 分類・入出力の型と、
要約の多言語訳(ja 原文 + en / zh / tw / ko / de / hi)、それに人が書いた**文脈**(文献層のテーマ → op の
対応表の「テーマ: なぜ使うか」、日本語の原文 ``t`` と英訳 ``te``、2026-10-15)。順位は BM25(語の希少さで重み付け)。
文脈は要約と同じ重み —— 現場の言い方(「溶接ビード」/ "weld bead")を、表がその op に付けたときだけ拾う。

**語の切り方**(依存ゼロ・決定的): ラテン文字は語ごと(6 文字を超える語は先頭 6 文字に
縮めて ``denoise`` / ``denoising``、``segment`` / ``segmentation`` を同じ語にする)、漢字・仮名・
ハングルは 2 文字ずつ(分かち書きが無い言語でも部分一致が効く)。埋め込みは使わない ——
同義語(「ぼかし」と「平滑化」)は拾えないので、0 件なら別の言い方を試す(``hint`` に出す)。

**索引** ``fullseye/data/OP_SEARCH.json`` は ``tools/gen_mcp_data.py`` が書き、wheel に同梱する
(``pip install fullseye`` だけで動く)。checkout でも同じ複製を読む —— 生成物と正本の一致は
``regen_all --check`` が CI で数える。
"""
from __future__ import annotations

import json
import math
import re
import time
import unicodedata
from collections import Counter

__all__ = ["search_ops", "plan", "describe", "choose", "plan_chain", "op_cards", "choose_op", "required_inputs", "param_space",
           "pipeline_shape", "pattern_skeleton", "sort_guide",
           "load_index", "tokenize", "detect_lang", "LANGS", "main"]

#: 要約を持つ言語(ja = 原文)。表示言語の既定は問い合わせの文字種から決める(:func:`detect_lang`)。
LANGS = ("ja", "en", "zh", "tw", "ko", "de", "hi")
PKG_SEARCH = "OP_SEARCH.json"
PKG_CARDS = "OP_CARDS.json"
PKG_PROBE = "OP_PROBE.json"
PKG_GRAPH = "OP_GRAPH.json"
PKG_FAMILIES = "OP_FAMILIES.json"
PKG_SHAPES = "OP_SHAPES.json"
PKG_PATTERNS = "OP_PATTERNS.json"
_STEM = 6
_K1, _B = 1.2, 0.75
#: 場ごとの重み: 名前に入っている語は要約の語より強い手掛かり
_W_NAME, _W_HALCON, _W_META, _W_SUMMARY = 3, 2, 1, 1
#: 文脈(文献層のテーマ表で人がその op に書いた行)の重み。要約と同じ。
_W_CONTEXT = 1

_LATIN = re.compile(r"[0-9a-zß-ɏ]+")
_CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿豈-﫿]+")
_HANGUL = re.compile(r"[가-힯ᄀ-ᇿ㄰-㆏]+")
_KANA = re.compile(r"[぀-ヿ]")
#: デーヴァナーガリー(ヒンディー語)。語は空白で区切られるので語ごとに切る(母音記号・virama も語の内側)
_DEVANAGARI = re.compile(r"[ऀ-ॿ꣠-ꣿ]+")
_GERMAN = re.compile(r"[äöüß]|\b(?:der|die|das|und|nicht|mit|eines?|bild|kante|kanten|erkennen|rauschen)\b")

_CACHE: dict = {}


def _load_json(name: str) -> dict:
    """Load a non-op-list generated table, refusing missing or empty data."""
    key = "json:" + name
    if key in _CACHE:
        return _CACHE[key]
    from importlib.resources import files
    p = files("fullseye") / "data" / name
    if not p.is_file():
        raise FileNotFoundError("fullseye/data/%s is missing; run tools/gen_op_facets.py" % name)
    obj = json.loads(p.read_text(encoding="utf-8"))
    if not obj:
        raise ValueError("%s is empty" % name)
    _CACHE[key] = obj
    return obj


def _graph() -> dict:
    g = _load_json(PKG_GRAPH)
    if not g.get("nodes") or not g.get("edges"):
        raise ValueError("%s has an empty node or edge set" % PKG_GRAPH)
    return g


def _sort(value: str) -> str:
    return _graph().get("sort_aliases", {}).get(value, value)


def _result(ok: bool, reason: str, *, hint: str = "", next_tool: str | None = None, **data) -> dict:
    return {"ok": ok, "reason": reason, "hint": hint, "next_tool": next_tool, **data}


def _plan_dag(root: dict) -> tuple[list[dict], list[str]]:
    """Flatten one derivation tree into a dependency DAG with stable references."""
    stages, seen = [], {}
    def emit(node):
        if node.get("base") is not None:
            return "have:%s" % node["base"]
        key = node["signature"]
        if key in seen:
            return seen[key]
        refs = [emit(child) for child in node["children"]]
        ref = "stage:%d" % (len(stages) + 1)
        seen[key] = ref
        stages.append({"id": ref, "op": node["edge"]["op"], "inputs": refs,
                       "in_sorts": node["edge"]["inputs"], "out_sort": node["sort"],
                       "params": {}})
        return ref
    output = emit(root)
    return stages, [output]


def _hypergraph_plans(starts: list[str], want: str, query: str, *, executable_only: bool,
                      k: int, max_depth: int, max_expansions: int, timeout_ms: int,
                      allow_sources: bool) -> tuple[list[dict], dict]:
    """Knuth-style relaxation: retain bounded derivations per type, never type sets."""
    graph = _graph()
    scores = {r["name"]: r["score"] for r in search_ops(query, k=len(graph["edges"]))["ops"]}
    edges = [e for e in graph["edges"] if (e.get("executable") or not executable_only)
             and e.get("output") not in ("unknown", "any")
             and "unknown" not in e.get("inputs", ())]
    by_input = {}
    for edge in edges:
        for sort in set(edge.get("inputs", ())):
            by_input.setdefault(sort, []).append(edge)
    best = {s: [{"base": s, "sort": s, "cost": 0.0, "depth": 0,
                 "signature": "have:%s" % s, "consumed": frozenset({s})}] for s in starts}
    started = time.monotonic(); expanded = 0; changed = True; capped = None
    while changed:
        changed = False
        for edge in edges:
            if expanded >= max_expansions:
                capped = "max_expansions"; break
            if (time.monotonic() - started) * 1000 >= timeout_ms:
                capped = "timeout_ms"; break
            ins = edge.get("inputs", [])
            if not ins:
                if not allow_sources or edge.get("type_semantics") != "source":
                    continue
                children = []
            else:
                choices = []
                possible = True
                for inp in ins:
                    if inp == "poly":
                        possible = False; break
                    rows = best.get(inp)
                    if not rows:
                        possible = False; break
                    choices.append(rows[0])
                if not possible:
                    continue
                children = choices
            expanded += 1
            depth = 1 + max((x["depth"] for x in children), default=0)
            if depth > max_depth:
                continue
            out = edge["output"]
            if out == "poly":
                out = children[0]["sort"] if children else "unknown"
            consumed = frozenset().union(*(x["consumed"] for x in children)) if children else frozenset()
            if not consumed and not allow_sources:
                continue
            relevance = max(0.0, scores.get(edge["op"], 0.0))
            cost = sum(x["cost"] for x in children) + 1.0 / (1.0 + relevance)
            sig = "%s(%s)" % (edge["op"], ",".join(x["signature"] for x in children))
            row = {"sort": out, "cost": cost, "depth": depth, "edge": edge,
                   "children": children, "signature": sig, "consumed": consumed}
            rows = best.setdefault(out, [])
            if any(x["signature"] == sig for x in rows):
                continue
            rows.append(row); rows.sort(key=lambda x: (x["cost"], x["depth"], x["signature"]))
            del rows[k:]
            if row in rows:
                changed = True
        if capped:
            break
    plans = []
    for root in best.get(want, []):
        if root.get("base") is not None or not root["consumed"]:
            continue
        stages, outputs = _plan_dag(root)
        plans.append({"dag": {"stages": stages, "outputs": outputs},
                      "ops": [x["op"] for x in stages], "weight": round(root["cost"], 6),
                      "depth": root["depth"], "consumed_have": sorted(root["consumed"])})
    meta = {"expanded": expanded, "elapsed_ms": round((time.monotonic() - started) * 1000, 3),
            "limit_reached": capped, "unknown_edges_excluded": sum(
                e.get("output") in ("unknown", "any") or "unknown" in e.get("inputs", ())
                for e in graph["edges"])}
    return plans, meta


def plan(have, want: str, direction: str = "forward", pattern: str | None = None,
         constraints: dict | None = None, goal: str | None = None) -> dict:
    """Find minimum-cost typed hypergraph derivations and return dependency DAGs."""
    constraints = constraints or {}
    from fssystem import get_system
    if direction not in ("forward", "backward"):
        return _result(False, "direction must be forward or backward", hint="use direction='forward' or 'backward'", next_tool="plan")
    want = _sort(want)
    starts = [_sort(x) for x in (have if isinstance(have, (list, tuple, set)) else [have]) if x]
    query = str(goal or constraints.get("goal") or constraints.get("query") or want)
    max_depth = int(constraints.get("max_depth", get_system("plan_max_depth")))
    k = int(constraints.get("k", get_system("plan_k")))
    executable_only = constraints.get("executable_only", True)
    if direction == "backward":
        starts = sorted({_sort(x["sort"]) for x in _graph().get("acquirable_sorts", [])})
    solutions, meta = _hypergraph_plans(starts, want, query, executable_only=executable_only, k=k,
                                        max_depth=max_depth,
                                        max_expansions=int(constraints.get("max_expansions", get_system("plan_max_expansions"))),
                                        timeout_ms=int(constraints.get("timeout_ms", get_system("plan_timeout_ms"))),
                                        allow_sources=direction == "backward")
    if not solutions:
        return _result(False, "no executable typed path", hint="inspect blocked_at or broaden have", next_tool="find_ops",
                       have=starts, want=want, direction=direction, partial=meta, blocked_at=[want])
    return _result(True, "executable typed path found", next_tool="op_cards", have=starts, want=want,
                    goal=query, direction=direction, pattern=pattern, executable_only=executable_only,
                    search=meta, plans=solutions)


def describe(kind: str, name: str, budget_tokens: int = 800) -> dict:
    """Describe one sort, op, or family; never dump the complete inventory."""
    if kind == "sort":
        r = sort_guide(_sort(name))
    elif kind == "op":
        edge = next((e for e in _graph()["edges"] if e["op"] == name), None)
        r = {"found": edge is not None, "op": edge, "param_space": param_space(name, {}) if edge else None}
    elif kind == "family":
        fam = next((f for f in _load_json(PKG_FAMILIES)["families"] if f["name"] == name), None)
        r = {"found": fam is not None, "family": fam}
    else:
        return _result(False, "kind must be sort, op, or family", hint="choose a supported kind", next_tool="describe")
    return _result(bool(r.get("found", True)), "description found" if r.get("found", True) else "unknown name",
                   next_tool="choose", description=r, budget_tokens=budget_tokens)


def choose(candidates: list[str], constraints: dict | None = None) -> dict:
    """Filter candidates using only measured facts; reject unknown constraints."""
    allowed = {"device", "batch", "time_budget_ms", "exact", "edge_preserving", "stable"}
    unknown = sorted(set(constraints or {}) - allowed)
    if unknown:
        return _result(False, "unknown constraint keys", hint="remove: " + ", ".join(unknown), next_tool="describe")
    rows = []
    for name in candidates:
        edge = next((e for e in _graph()["edges"] if e["op"] == name), None)
        if edge:
            rows.append({"op": name, "eligible": edge.get("executable", False), "ranked": False,
                         "reason": "no comparable measurement"})
    return _result(bool(rows), "candidates filtered; not ranked without measurements", next_tool="op_cards", candidates=rows)


def choose_op(family: str, constraints: dict | None = None) -> dict:
    """Filter a hand-ledger family; rank only when comparable measurements exist."""
    constraints = constraints or {}
    fs = _load_json(PKG_FAMILIES).get("families") or []
    fam = next((x for x in fs if x.get("name") == family), None)
    if fam is None:
        return _result(False,"unknown family",hint="choose one of: "+", ".join(sorted(x["name"] for x in fs)),
                       next_tool="describe",family=family,matches=[],families=sorted(x["name"] for x in fs),fail_closed=True)
    allowed={"time_budget_ms","exact","edge_preserving","stable","device","batch","pixels"}
    unknown=sorted(set(constraints)-allowed)
    if unknown:
        return _result(False,"unknown constraint keys",hint="remove: "+", ".join(unknown),next_tool="describe",
                       family=family,matches=[],fail_closed=True)
    graph = {e["op"]: e for e in _graph()["edges"]}
    missing, ranked = [], []
    fact_constraints = {"time_budget_ms", "exact", "edge_preserving", "stable"} & set(constraints)
    for row in fam["ops"]:
        e = graph[row["op"]]
        reasons = ["member of %s by hand ledger: %s" % (family,row.get("membership_source"))]
        lacks = []
        if fact_constraints:
            lacks.extend(sorted(fact_constraints))
        device = constraints.get("device")
        if device == "cuda" and e.get("gpu_timing") == "unmeasured":
            lacks.append("cuda timing")
        if lacks:
            missing.extend("%s: %s" % (row["op"], x) for x in lacks)
            continue
        ranked.append({"op": row["op"], "ranked": row.get("complexity_exponent") is not None, "reasons": reasons,
                       "device": device or "unspecified", "batch": constraints.get("batch", 1)})
    return _result(bool(ranked),"measured candidates filtered" if ranked else "no candidate satisfies measured constraints",
                   hint="inspect missing measurements",next_tool="op_cards",family=family,constraints=constraints,
                   matches=ranked,missing=sorted(set(missing)),fail_closed=not bool(ranked))


def required_inputs(goal_sort: str, max_depth: int = 4, k: int = 10) -> dict:
    """Search the transposed typed hypergraph (AND inputs, OR producing edges)."""
    if max_depth < 0 or k < 1:
        raise ValueError("max_depth must be >= 0 and k must be > 0")
    g = _graph(); goal_sort = _sort(goal_sort)
    sorts = {n["sort"] for n in g["nodes"]}
    if goal_sort not in sorts:
        return {"goal_sort": goal_sort, "solutions": [], "blocked_at": [goal_sort], "reason": "unknown sort"}
    by_out = {}
    for e in g["edges"]:
        by_out.setdefault(e["output"], []).append(e)
        if e["output"] == "any":
            for s in sorts:
                by_out.setdefault(s, []).append(e)
    acquirable = {r["sort"]: r["source"] for r in g.get("acquirable_sorts", [])}

    def walk(sort, depth, seen):
        if sort in acquirable:
            return [({sort}, ["acquire:%s" % sort], 0.0)]
        if depth == 0 or sort in seen:
            return []
        out = []
        for edge in by_out.get(sort, ()):                       # OR: any producer
            combos = [(set(), [], 0.0)]
            for inp in edge["inputs"]:                          # AND: every input
                if inp == "any":
                    inp = sort
                branches = walk(inp, depth - 1, seen | {sort})
                if not branches:
                    combos = []
                    break
                combos = [(a | b, pa + pb, wa + wb) for a, pa, wa in combos
                          for b, pb, wb in branches][:k * 4]
            out.extend((s, p + [edge["op"]], w + 1.0) for s, p, w in combos)
        return out

    raw = walk(goal_sort, max_depth, set())
    uniq = {}
    for inputs, path, weight in raw:
        key = tuple(sorted(inputs))
        old = uniq.get(key)
        if old is None or (weight, path) < (old[2], old[1]): uniq[key] = (inputs, path, weight)
    sols = [{"inputs": sorted(v[0]), "path": v[1], "weight": v[2],
             "acquisition": [{"sort": x, "source": acquirable.get(x)} for x in sorted(v[0])]}
            for v in sorted(uniq.values(), key=lambda x: (len(x[0]), x[2], sorted(x[0])))[:k]]
    blocked = [] if sols else sorted({goal_sort} | {i for e in by_out.get(goal_sort, ()) for i in e["inputs"]
                                      if i not in acquirable and i not in by_out})
    return _result(bool(sols), "backward path found" if sols else "no acquisition-rooted path",
                   hint="inspect blocked_at" if not sols else "", next_tool="op_cards" if sols else "find_ops",
                   goal_sort=goal_sort, solutions=sols, blocked_at=blocked, semantics="transpose AND-OR search")


def param_space(op: str, input_context: dict | None = None) -> dict:
    """Return context-narrowed normalized knob ranges without inventing physical units."""
    input_context = input_context or {}
    edge = next((e for e in _graph()["edges"] if e["op"] == op), None)
    if edge is None:
        raise ValueError("unknown op: %s" % op)
    params = {}
    for name, meta in edge.get("parameters", {}).items():
        rec = dict(meta)
        if not rec.get("used"):
            rec.update({"search": False, "reason": "measured unused knob" if rec.get("source") != "unmeasured" else "no measured effect"})
        else:
            lo, hi = 0.0, 1.0
            reasons = ["measured normalized range"]
            width = max(1, int(input_context.get("width", input_context.get("image_width", 1))))
            height = max(1, int(input_context.get("height", input_context.get("image_height", 1))))
            value_range = input_context.get("value_range")
            bundle_n = max(1, int(input_context.get("N", input_context.get("bundle_n", 1))))
            family = edge.get("family")
            if family in ("denoise", "morphology", "edge_detection") and name == "a":
                hi = min(1.0, max(0.0, (min(width, height) - 1) / max(min(width, height), 1)))
                reasons.append("kernel/radius must fit inside the image")
            if family == "thresholding" and value_range and len(value_range) == 2:
                reasons.append("threshold constrained to input value range %s" % list(value_range))
            if family == "fringe_phase" and bundle_n == 1:
                hi = 0.0; reasons.append("N=1 cannot vary a phase-shift bundle parameter")
            rec.update({"search": hi > lo, "min": lo, "max": hi,
                        "reason": "; ".join(reasons), "rule_source": "family context rules 2026-10-28"})
            if rec.get("discrete"):
                rec["enum"] = sorted(set([lo] + [x for x in rec.pop("discrete") if lo <= x <= hi] + [hi]))
        params[name] = rec
    return {"op": op, "input_context": input_context, "parameters": params,
            "source_graph": PKG_GRAPH}


def system_params() -> dict:
    """Return the human-controlled system settings hidden from AI tool schemas."""
    return _load_json("SYSTEM_PARAMS.json")


def pipeline_shape(input_form: str, output_form: str) -> dict:
    """Describe execution topology implied by input/output forms."""
    rows = _load_json(PKG_SHAPES).get("shapes") or []
    exact = [r for r in rows if r["input_form"] == input_form and r["output_form"] == output_form]
    if not exact:
        return {"input_form": input_form, "output_form": output_form, "found": False,
                "known_input_forms": sorted({r["input_form"] for r in rows}),
                "known_output_forms": sorted({r["output_form"] for r in rows})}
    out = dict(exact[0]); out["found"] = True
    return out


def pattern_skeleton(name: str, start_sort: str, goal_sort: str) -> dict:
    """Fill a typed pattern slot with candidates from the one op graph."""
    pats = _load_json(PKG_PATTERNS).get("patterns") or []
    pat = next((p for p in pats if p["name"].lower() == name.lower()), None)
    if pat is None:
        return {"name": name, "found": False, "known": [p["name"] for p in pats]}
    out = dict(pat); out.update({"found": True, "start_sort": _sort(start_sort), "goal_sort": _sort(goal_sort),
                                "candidates": [], "reason":"pattern is not exposed until slots and examples are grounded"})
    return out


def sort_guide(sort: str | None = None) -> dict:
    """Return node/container guidance and graph-derived producer/consumer counts."""
    rows = _load_json("OP_SORTS.json").get("sorts") or []
    if sort is None:
        shown=rows[:20]
        return {"sorts": shown, "total":len(rows), "truncated":len(rows)>len(shown),
                "documented_choose_when": sum(r["choose_when"] != "undocumented" for r in rows),
                "undocumented_choose_when": sum(r["choose_when"] == "undocumented" for r in rows)}
    sort = _sort(sort)
    row = next((r for r in rows if r["sort"] == sort), None)
    return {"found": row is not None, "sort": row, "known": [] if row else [r["sort"] for r in rows]}


def _load_data(name: str) -> dict:
    """Load a generated AI-facing table from package data, fail-closed."""
    key = "data:" + name
    if key in _CACHE:
        return _CACHE[key]
    from importlib.resources import files
    p = files("fullseye") / "data" / name
    if not p.is_file():
        raise FileNotFoundError("fullseye/data/%s is missing; run tools/gen_mcp_data.py" % name)
    obj = json.loads(p.read_text(encoding="utf-8"))
    if not obj.get("ops"):
        raise ValueError("%s contains no operators" % name)
    _CACHE[key] = obj
    return obj


def _probe_map() -> dict:
    return {r["name"]: r for r in _load_data(PKG_PROBE)["ops"]}


def _with_probe(row: dict, probes: dict) -> dict:
    out = dict(row)
    out["probe"] = probes.get(row["name"], {"status": "not_in_registry", "reason": "not executable by fullseye.apply"})
    return out

#: 同じ言語の中の言い換え(手で書いた表、2026-10-07)。要約の 6 言語は**言語をまたぐ**対応は持っているが、
#: 同じ言語の別の言い方(「檢測」と「偵測」、「校正」と「キャリブレーション」)は持たない。問い合わせにどれかが
#: あれば残りを弱い重み(:data:`_W_SYNONYM`)で足す。表に無い言い換えは拾わない(``hint`` で案内する)。
SYNONYMS: tuple = (
    ("ノイズ除去", "雑音除去", "デノイズ", "ノイズ低減"), ("平滑化", "ぼかし", "スムージング"),
    ("二値化", "しきい値", "閾値"), ("校正", "較正", "キャリブレーション"), ("エッジ", "縁"),
    ("検出", "抽出"), ("点群", "ポイントクラウド"), ("位置合わせ", "レジストレーション", "整列"),
    ("去噪", "降噪", "除噪"), ("边缘", "边沿"), ("二值化", "阈值"), ("标定", "校准"), ("检测", "提取"),
    ("檢測", "偵測"), ("雜訊", "噪聲", "噪訊"), ("邊緣", "邊沿"), ("校正", "標定", "校準"), ("閾值", "臨界值"),
    ("잡음", "노이즈"), ("에지", "엣지"), ("검출", "탐지", "추출"), ("보정", "교정", "캘리브레이션"),
    ("이진화", "임계값"), ("평활화", "스무딩", "블러"),
    ("kante", "kanten"), ("rauschen", "entrauschen", "rauschunterdruckung"), ("glattung", "glatten", "weichzeichnen"),
    ("kalibrierung", "kalibrieren"), ("schwellwert", "schwelle", "binarisierung"),
    ("denoise", "noise", "despeckle"), ("blur", "smooth", "smoothing"), ("threshold", "binarize", "binarization"),
    ("calibration", "calibrate"), ("edge", "edges"), ("detect", "detection"),
    ("registration", "align", "alignment"),
)
_W_SYNONYM = 0.6

#: ヒンディー語の機能語(後置詞・助動詞・代名詞)。どの要約にも出るので、残すと「का」1 語で 1,000 op が当たる
#: (2026-10-07 実測: 「किनारे का पता लगाना」が 1,226 件・上位は無関係)。索引と問い合わせの両方から外す。
_HI_STOP = frozenset("""के का की को में से पर है हैं था थे थी और या एक यह वह ये वे जो तो भी ही
    कर करता करती करते करें करना किया होता होती होते होना हो गया गई गए वाला वाली वाले लिए साथ तक द्वारा
    इस उस इन उन कि नहीं न अपने अपना अपनी लगाना पता""".split())

#: ヒンディー語の日常語 → 英語の術語(訳の方針で術語は英語のまま書いたので、日常語で引いても当たるように)。
#: 言語をまたぐ組はこの表だけ(他の言語は要約自体が訳語で書かれている)。
HI_TERMS: tuple = (
    ("किनारा", "किनारे", "किनारों", "edge"), ("शोर", "noise"), ("पहचान", "पहचानना", "detect"),
    ("धुंधला", "blur"), ("चिकना", "smooth"), ("रंग", "color", "colour"), ("सीमा", "threshold"),
    ("कोना", "कोने", "corner"), ("गहराई", "depth"), ("मापना", "माप", "measure"), ("आकार", "shape"),
    ("बिंदु", "point"), ("रेखा", "line"), ("वृत्त", "circle"), ("प्रकाश", "light"), ("कैमरा", "camera"),
)


def _norm(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "").lower()


def tokenize(text: str) -> list[str]:
    """検索語に切る: ラテン文字は語(長い語は先頭 6 文字)、漢字・仮名・ハングルは 2 文字ずつ。"""
    t = _norm(text).replace("_", " ")
    out: list[str] = []
    for w in _LATIN.findall(t):
        out.append(w[:_STEM] if len(w) > _STEM else w)
    out.extend(w for w in _DEVANAGARI.findall(t) if w not in ("।", "॥") and w not in _HI_STOP)
    for rx in (_CJK, _HANGUL):
        for run in rx.findall(t):
            if len(run) == 1:
                out.append(run)
            else:
                out.extend(run[i:i + 2] for i in range(len(run) - 1))
    return out


def detect_lang(query: str) -> str:
    """問い合わせの文字種から表示言語を推す: ハングル → ko、仮名 → ja、漢字だけ → zh、
    ドイツ語の印(ウムラウト・ß・よく出る語)→ de、それ以外 → en。tw は推せないので ``lang="tw"`` で。"""
    q = _norm(query)
    if _DEVANAGARI.search(q):
        return "hi"
    if _HANGUL.search(q):
        return "ko"
    if _KANA.search(q):
        return "ja"
    if _CJK.search(q):
        return "zh"
    if _GERMAN.search(q):
        return "de"
    return "en"


def _fold(text: str) -> str:
    """言い換え表の照合用: NFKC・小文字・ウムラウトを落とす(Glättung → glattung)。"""
    t = unicodedata.normalize("NFKD", _norm(text))
    return "".join(c for c in t if not unicodedata.combining(c)).replace("ß", "ss")


def _synonym_tokens(query: str, have: set) -> list[str]:
    """問い合わせに含まれる言い換え表の語について、同じ組の他の語の検索語(既にあるものは除く)。"""
    fq = _fold(query)
    out: list[str] = []
    for group in SYNONYMS + HI_TERMS:
        if any(_fold(w) in fq for w in group):
            for w in group:
                for tok in tokenize(w):
                    if tok not in have and tok not in out:
                        out.append(tok)
    return out


def _pick_lang(query: str, qtok: list, top_rows: list) -> str:
    """表示言語: ハングル → ko、仮名 → ja は文字で決まる。それ以外(漢字だけ・ラテン文字)は
    文字種では ja / zh / tw、en / de を分けられないので、**上位の op の要約のうち問い合わせの語を
    いちばん多く含む言語**を採る(同点は :func:`detect_lang` の推定を優先)。"""
    guess = detect_lang(query)
    if guess in ("ko", "ja", "hi") or not top_rows:
        return guess
    # Latin text is English unless the query itself carries a German marker.
    # German summaries must not outvote an ordinary English query by BM25 noise.
    cands = ("ja", "zh", "tw") if guess == "zh" else (("de",) if guess == "de" else ("en",))
    qs = set(qtok)
    best, best_n = guess, -1
    for lang in sorted(cands, key=lambda x: x != guess):
        n = sum(len(qs & set(tokenize((r.get("s") or {}).get(lang, "")))) for r in top_rows)
        # 推定と違う言語へ乗り換えるのは**はっきり多い**ときだけ(語幹が同じ "skeleton" / "Skelett" で揺れない)
        if best_n < 0 or n > best_n * 1.5 + 1:
            best, best_n = lang, n
    return best


def load_index(path: str | None = None) -> dict:
    """同梱の索引を読んで BM25 の表を組む(1 プロセスで 1 回)。

    無ければ ``FileNotFoundError`` —— 空の索引で「該当なし」を返すと、検索層が自分の
    範囲について嘘をつく(``docs/AI_RAG_GUIDE.md`` の教訓)。"""
    key = path or "<package>"
    if key in _CACHE:
        return _CACHE[key]
    if path is None:
        from importlib.resources import files
        p = files("fullseye") / "data" / PKG_SEARCH
        if not p.is_file():
            raise FileNotFoundError(
                "fullseye/data/%s が無い。checkout なら `py -3.11 tools/gen_mcp_data.py` で作る" % PKG_SEARCH)
        raw = json.loads(p.read_text(encoding="utf-8"))
    else:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    rows = raw.get("ops") or []
    if not rows:
        raise ValueError("%s に op が 0 件(生成が壊れている)" % PKG_SEARCH)
    docs: list[Counter] = []
    df: Counter = Counter()
    for r in rows:
        tf: Counter = Counter()
        for tok in tokenize(r["n"]):
            tf[tok] += _W_NAME
        for tok in tokenize(r.get("h") or ""):
            tf[tok] += _W_HALCON
        for tok in tokenize(" ".join(x for x in (r.get("d"), r.get("c"), r.get("i"), r.get("o")) if x)):
            tf[tok] += _W_META
        for txt in (r.get("s") or {}).values():
            for tok in tokenize(txt):
                tf[tok] += _W_SUMMARY
        for txt in list(r.get("t") or ()) + list(r.get("te") or ()):
            for tok in tokenize(txt):
                tf[tok] += _W_CONTEXT
        docs.append(tf)
        df.update(tf.keys())
    lens = [sum(tf.values()) for tf in docs]
    avg = sum(lens) / len(lens)
    n = len(rows)
    idf = {t: math.log(1.0 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
    names, aliases = _name_tables(rows)
    built = {"rows": rows, "docs": docs, "lens": lens, "avg": avg, "idf": idf, "names": names,
             "aliases": aliases,
             "n_ops": n, "languages": raw.get("languages") or list(LANGS)}
    _CACHE[key] = built
    return built


def _name_tables(rows: list) -> tuple[dict, dict]:
    """完全一致で先頭に上げる表を 2 枚: op 名そのもの → 行、HALCON 別名 → 行。

    ★2026-10-11: 1 枚の表に op 名と別名を「先に出た行が勝つ」で混ぜていたので、
    ``gauss_filter`` を問うと、その名前を**別名として**名乗る前の行 ``cv_gaussian`` が先頭に
    来た(op ``gauss_filter`` 自身は 4 位)。38 op が自分の名前で引けなかった。
    名前は op 名の表を先に引き、別名は ``api.find_op`` の規則(完全一致 → ``name == halcon``
    → ``_ALIAS_CANONICAL``)が選ぶ op —— ``fullseye.apply(x, 別名)`` が実際に走らせる op —— に
    だけ与える。registry に無い別名(他の層)は従来どおり先に出た行。
    """
    names: dict = {}
    for i, r in enumerate(rows):
        names.setdefault(_norm(r["n"]), i)
    try:
        import api as _api
        find_op = _api.find_op
    except Exception:  # noqa: BLE001 - the index must stay usable without the facade
        find_op = None
    aliases: dict = {}
    for i, r in enumerate(rows):
        h = r.get("h")
        if not h:
            continue
        key = _norm(h)
        if key in aliases:
            continue
        canon = None
        if find_op is not None:
            try:
                op = find_op(h)
            except Exception:  # noqa: BLE001
                op = None
            if op is not None:
                canon = names.get(_norm(op.name))
        if canon is None:
            canon = i
        aliases[key] = canon
    return names, aliases


def search_ops(query: str, k: int = 10, *, lang: str | None = None, in_sort: str | None = None,
               out_sort: str | None = None, dim: str | None = None, index_path: str | None = None) -> dict:
    """``query``(:data:`LANGS` のどの言語でも)に合う op を順位つきで返す。

    返り: ``{"query", "lang", "total", "ops": [{"name", "dim", "category", "in_sort", "out_sort",
    "halcon", "note", "summary", "score"}], "hint"}``。``summary`` は ``lang``(既定は問い合わせから
    推した言語)の要約、無ければ en → ja。``total`` は語が 1 つでも当たった op の数。

    >>> r = search_ops("remove noise", k=3)
    >>> [o["name"] for o in r["ops"]]                       # doctest: +SKIP
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("search_ops: query must be a non-empty string")
    if lang is not None and lang not in LANGS:
        raise ValueError("search_ops: lang must be one of %s, got %r" % (LANGS, lang))
    if not (isinstance(k, int) and k > 0):
        raise ValueError("search_ops: k must be a positive int, got %r" % (k,))
    ix = load_index(index_path)
    q = list(dict.fromkeys(tokenize(query)))
    extra = _synonym_tokens(query, set(q))
    rows, docs, lens, avg, idf = ix["rows"], ix["docs"], ix["lens"], ix["avg"], ix["idf"]
    scores: dict[int, float] = {}
    matched: Counter = Counter()
    for tok in q:
        w = idf.get(tok)
        if w is None:
            continue
        for i, tf in enumerate(docs):
            f = tf.get(tok)
            if f:
                scores[i] = scores.get(i, 0.0) + w * f * (_K1 + 1) / (f + _K1 * (1 - _B + _B * lens[i] / avg))
                matched[i] += 1
    for tok in extra:
        w = idf.get(tok)
        if w is None:
            continue
        for i, tf in enumerate(docs):
            f = tf.get(tok)
            if f:
                scores[i] = scores.get(i, 0.0) + _W_SYNONYM * w * f * (_K1 + 1) / (
                    f + _K1 * (1 - _B + _B * lens[i] / avg))
    # 語を多く含む op を上に(一般語 1 つだけで当たった op が、語を全部含む op を追い越さない)。
    # 言い換えだけで当たった op も 0 にはしない(問い合わせの語が索引に無い言い方でも引けるように)
    for i in scores:
        scores[i] *= max(matched[i], 0.5) / max(len(q), 1)
    key = _norm(query.strip()).replace(" ", "_")
    exact = ix["names"].get(key)                                       # op 名そのものが先
    if exact is None:
        exact = ix.get("aliases", {}).get(key)                         # 次に、apply が走らせる別名先
    if exact is not None:
        scores[exact] = scores.get(exact, 0.0) + 1e6                   # 名前そのものなら先頭
    hits = []
    for i, s in scores.items():
        r = rows[i]
        if in_sort and r.get("i") != in_sort:
            continue
        if out_sort and r.get("o") != out_sort:
            continue
        if dim and r.get("d") != dim:
            continue
        hits.append((-s, r["n"], i))
    hits.sort()
    show = lang or _pick_lang(query, q, [rows[i] for _, _, i in hits[:10]])
    out = []
    for neg, _, i in hits[:k]:
        r = rows[i]
        summ = r.get("s") or {}
        row = {"name": r["n"], "dim": r.get("d"), "category": r.get("c"),
               "in_sort": r.get("i"), "out_sort": r.get("o"), "halcon": r.get("h"),
               "note": r.get("p"), "summary": summ.get(show) or summ.get("en") or summ.get("ja") or "",
               "score": round(-neg, 3)}
        ctx = (r.get("t") if show == "ja" else (r.get("te") or r.get("t"))) or ()
        if ctx:                                                        # 人が書いた文脈(どの場面で使う op か)
            row["contexts"] = list(ctx[:3])
        out.append(row)
    try:
        probes = _probe_map()
    except (FileNotFoundError, ValueError):
        probes = {}
    out = [_with_probe(r, probes) for r in out]
    hint = None
    if not out:
        known = [t for t in q if t in idf]
        hint = ("どの語も索引に無い。別の言い方・英語・op 名の一部を試す" if not known else
                "語は当たったが絞り込み(in_sort / out_sort / dim)で 0 件")
    return {"ok": bool(out), "reason": "operators found" if out else "no matching operator",
            "next_tool": "fullseye_plan" if out else "fullseye_find_ops",
            "query": query, "lang": show, "total": len(hits), "n_ops_indexed": ix["n_ops"],
            "ops": out, "hint": hint or "call fullseye_plan with the selected input/output sorts"}


def plan_chain(query: str, start_sort: str, goal_sort: str, k: int = 5, max_depth: int = 4,
               *, lang: str | None = None, index_path: str | None = None) -> dict:
    """Backward-compatible view of :func:`plan` over executable hyperedges."""
    if not isinstance(start_sort, str) or not start_sort or not isinstance(goal_sort, str) or not goal_sort:
        raise ValueError("plan_chain: start_sort and goal_sort must be non-empty strings")
    if not isinstance(max_depth, int) or not 1 <= max_depth <= 16:
        raise ValueError("plan_chain: max_depth must be in 1..16")
    if not isinstance(k, int) or not 1 <= k <= 100:
        raise ValueError("plan_chain: k must be in 1..100")
    # Legacy retrieval surface historically covered the full knowledge ledger.
    # The new plan() API defaults to executable_only=True.
    r = plan(start_sort, goal_sort, constraints={"query": query, "k": k, "max_depth": max_depth,
                                                 "executable_only": False})
    if not r["ok"]:
        return {"query": query, "start_sort": _sort(start_sort), "goal_sort": _sort(goal_sort),
                "found": False, "break_at": r.get("blocked_at", []), "reason": r["reason"]}
    edges = {e["op"]: e for e in _graph()["edges"]}
    ops = r["plans"][0]["ops"]
    alternatives=[]
    for p in r["plans"]:
        for n in p["ops"]:
            if n not in alternatives: alternatives.append(n)
    probes = _probe_map()
    stages = [{"stage": i, "in_sort": edges[n]["inputs"], "out_sort": edges[n]["output"],
               "candidates": ([_with_probe({"name": x, "score": 0.0}, probes) for x in alternatives[:k]] if i==1 else
                              [_with_probe({"name": n, "score": round(1.0 / max(r["plans"][0]["weight"], 1e-9), 3)}, probes)])}
              for i, n in enumerate(ops, 1)]
    return {"query": query, "start_sort": _sort(start_sort), "goal_sort": _sort(goal_sort), "found": True,
            "depth": len(ops), "stages": stages, "plans": r["plans"]}


def op_cards(names: list[str], budget_tokens: int = 500) -> dict:
    """Return complete short cards without splitting a card at the token budget."""
    if not isinstance(names, list) or not names or not all(isinstance(n, str) and n for n in names):
        raise ValueError("op_cards: names must be a non-empty list of strings")
    if not isinstance(budget_tokens, int) or budget_tokens < 1:
        raise ValueError("op_cards: budget_tokens must be a positive int")
    table = {r["name"]: r for r in _load_data(PKG_CARDS)["ops"]}
    import difflib
    edges={e["op"]:e for e in _graph()["edges"]}
    cards, used, missing = [], 0, []
    for name in names:
        card = table.get(name)
        if card is None:
            missing.append({"name":name,"near":difflib.get_close_matches(name,table,n=3,cutoff=.45)}); continue
        card=dict(card); edge=edges.get(name,{})
        card.update({"inputs":edge.get("inputs",[]),"output":edge.get("output"),
                     "executable":bool(edge.get("executable")),
                     "executable_reason":edge.get("executable_reason"),
                     "parameters":edge.get("parameter_schema",[])})
        executor=edge.get("executor")
        if executor and executor.get("kind")=="python":
            card["python_call"]="%s.%s(%s)"%(executor["module"],executor["callable"],
                ", ".join(edge.get("inputs",[])+[p["name"]+"=..." for p in edge.get("parameter_schema",[])]))
        cost = int(card.get("tokens", 1))
        if used + cost > budget_tokens:
            break
        cards.append(card); used += cost
    return {"cards": cards, "used_tokens": used, "budget_tokens": budget_tokens,
            "truncated": len(cards) + len(missing) < len(names), "missing": missing}


def _format(res: dict) -> str:
    lines = ["%d op が当たった(索引 %d op、表示言語 %s)" % (res["total"], res["n_ops_indexed"], res["lang"])]
    for j, o in enumerate(res["ops"], 1):
        sort = "%s -> %s" % (o["in_sort"], o["out_sort"]) if o["in_sort"] or o["out_sort"] else ""
        lines.append("%2d. %s  [%s/%s] %s" % (j, o["name"], o["dim"], o["category"], sort))
        if o["summary"]:
            s = o["summary"].replace("\n", " ")
            lines.append("    " + (s if len(s) <= 160 else s[:157] + "..."))
        if o["note"]:
            lines.append("    note: " + o["note"])
    if res.get("hint"):
        lines.append("hint: " + res["hint"])
    return "\n".join(lines)


def main(argv=None) -> int:
    """``fullseye-rag search <query>`` / ``py -m fullseye.opsearch <query>`` の本体。"""
    import argparse
    ap = argparse.ArgumentParser(prog="fullseye-rag search",
                                 description="Find Fullseye operators by what they do (ja/en/zh/tw/ko/de/hi).")
    ap.add_argument("query", nargs="+", help="what you want to do, in any supported language")
    ap.add_argument("-k", type=int, default=10, help="how many rows (default 10)")
    ap.add_argument("--lang", choices=LANGS, default=None, help="summary language (default: from the query)")
    ap.add_argument("--in-sort", default=None)
    ap.add_argument("--out-sort", default=None)
    ap.add_argument("--dim", default=None, help="family, e.g. 2d / 3d / optics / piv")
    ap.add_argument("--json", action="store_true", help="print JSON instead of text")
    a = ap.parse_args(argv)
    res = search_ops(" ".join(a.query), a.k, lang=a.lang, in_sort=a.in_sort, out_sort=a.out_sort, dim=a.dim)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        import sys
        text = _format(res)
        try:
            print(text)
        except UnicodeEncodeError:                      # cp932 等の端末: 落とさず置換して出す
            sys.stdout.buffer.write((text + "\n").encode(sys.stdout.encoding or "utf-8", "replace"))
    return 0 if res["ops"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
