# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""敵対的検証 2026-11-05 第 2 巡(claims): 文書・生成物の主張が実物と食い違っていた件の回帰門。

どれも「書いてある数・文が、数え直すと違う」型。数は生成器から出すか書かないことにしたので、
ここは**数え直した値と照合する**(手で書いた期待値は持たない):

* D1 ``illusion_cafe_wall`` の docstring が、錯視の消えるずらし量を取り違えていた。
* D2 HALCON 対応数の見出しが「registry の ``Op.halcon`` 由来」と説明していた(大半は facade と台帳)。
* D3 レシピ「探針の球の PF / PS」の門が主張(雑音 0 は 0、上限 8σ)より桁で緩かった。兄弟の Sobol。
* D4 / D5 / D8 / D9 README と docs の手書きの数(MCP の道具 9、台帳 2,683、★ 606、op 897 / 931)。
* D5b 「型つき台帳 N/M」の分母が台帳でなく型カタログ(typed_catalog)だった。
* D6 成熟度台帳が、例が実データを読んだかを見ずに「公開実データで検証済み」を出していた。
* D7 成熟度台帳の「どの門も走らせていない例」が定数 0 だった。
* 小: 能力ノートの印字値のコメント、KNOWN_ISSUES の解消済みの行。
"""
from __future__ import annotations

import ast
import copy
import io
import json
import math
import os
import re
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (ROOT, os.path.join(ROOT, "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _read(rel: str) -> str:
    with io.open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


# --------------------------------------------------------------------------- #
# D1 カフェウォールのずらし量                                                    #
# --------------------------------------------------------------------------- #
def _adjacent_row_correlation(shift: float) -> float:
    """隣り合う行の市松の相関の平均(+1 = 縦に揃う、-1 = 白黒が入れ替わった市松、0 = 半タイルずれ)。"""
    import illusion as IL
    size, rows = 40, 8
    img = np.asarray(IL.illusion_cafe_wall(size=size, rows=rows, cols=10, mortar=0.0, shift=shift), float)
    if img.ndim == 3:
        img = img.mean(axis=2)
    prof =[img[r * size + size // 2] - 0.5 for r in range(rows)]
    c = [float(np.dot(prof[r], prof[r + 1]) / math.sqrt(np.dot(prof[r], prof[r]) * np.dot(prof[r + 1], prof[r + 1])))
         for r in range(rows - 1)]
    assert len(c) == rows - 1
    return float(np.mean(c))


def test_d1_cafe_wall_null_offsets_are_0_and_1_and_half_tile_is_the_classic_one():
    # 錯視が消えるのは「行が揃う」(相関 +1)と「ただの市松」(相関 -1)の 2 通り(Gregory & Heard 1979)。
    assert _adjacent_row_correlation(0.0) == pytest.approx(1.0, abs=1e-12)
    assert _adjacent_row_correlation(1.0) == pytest.approx(-1.0, abs=1e-12)
    assert _adjacent_row_correlation(0.5) == pytest.approx(0.0, abs=1e-12)     # 半タイル = 古典配置
    assert _adjacent_row_correlation(0.25) == pytest.approx(0.5, abs=1e-12)    # 0.25 は消えも最強でもない


def test_d1_the_docstring_names_the_offsets_the_image_has():
    import inspect

    import illusion as IL
    doc = IL.illusion_cafe_wall.__doc__
    assert "0 または 0.5" not in doc and "0.25 前後が最も強い" not in doc, "取り違えた説明が残っている"
    assert "1.0" in doc and "0.5 前後が最も強い" in doc, doc
    # 既定値は古典配置(説明と一致)
    assert inspect.signature(IL.illusion_cafe_wall).parameters["shift"].default == 0.5
    # 6 言語の訳も同じ原文の指紋を持つ(古い訳を出さない)
    import opdocs
    _, rest = opdocs.summary_and_rest(inspect.cleandoc(doc))       # ノートは字下げを外した原文から指紋を取る
    ent = json.loads(_read("docs/i18n/op_rest.json"))["bodies"]["generative/illusion_cafe_wall"]
    assert ent["fp"] == opdocs.fingerprint(rest)
    assert "0.25" not in ent["en"] and "0.5" in ent["en"]


def test_d1_the_caliper_poc_sweeps_one_full_period_of_the_offset():
    tree = ast.parse(_read("examples/poc_calipers_under_illusion.py"))
    found = [n.value for n in ast.walk(tree) if isinstance(n, ast.Assign) and len(n.targets) == 1
             and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "shifts"]
    assert len(found) == 1, "shifts の定義が 1 つでない"
    shifts = eval(compile(ast.Expression(found[0]), "shifts", "eval"), {})   # noqa: S307 — 自前の定数式
    assert min(shifts) == 0.0 and max(shifts) == 1.0, "周期 0〜1 を振っていない: %s" % (shifts,)


# --------------------------------------------------------------------------- #
# D2 HALCON 対応数の出どころ                                                   #
# --------------------------------------------------------------------------- #
def _halcon_analysis():
    import halcon_coverage as HC
    import halcon_names_data as HN
    import ops as R
    data = {"operators": [{"name": n, "chapters": []} for n in HN.HALCON_NAMES],
            "version": HN.HALCON_VERSION}
    return HC, HC.analyze(data, R.REGISTRY, None)


def test_d2_the_source_breakdown_is_a_partition_of_the_headline():
    HC, a = _halcon_analysis()
    by = a["covered_by_source"]
    assert tuple(by) == HC.SOURCES
    union = set().union(*by.values())
    assert union == set(a["covered"]) and sum(len(v) for v in by.values()) == len(a["covered"])
    # registry の分は、registry の Op.halcon が名乗る名前そのもの(独立に数え直す)
    import ops as R
    reg_names = {(o.halcon or "").strip() for o in R.REGISTRY} - {""}
    assert by["registry"] == set(a["covered"]) & reg_names
    assert len(by["registry"]) < len(a["covered"]) / 2, "大半は facade と台帳の対応(内訳が要る理由)"


def test_d2_the_generated_headlines_state_the_breakdown():
    from conftest import requires_full_registry
    requires_full_registry()
    HC, a = _halcon_analysis()
    by = a["covered_by_source"]
    cov = _read("docs/HALCON_COVERAGE.md")
    assert "via `Op.halcon`, from" not in cov
    m = re.search(r"maps to (\d+) / \d+ HALCON operators \([\d.]+%\)\*\*: (\d+) through `Op\.halcon`.*?, "
                  r"(\d+) through perception facades.*? and (\d+) through typed-ledger ops", cov)
    assert m, "HALCON_COVERAGE.md の見出しに出どころ別の内訳が無い"
    head, n_reg, n_fac, n_led = (int(x) for x in m.groups())
    assert (n_reg, n_fac, n_led) == tuple(len(by[s]) for s in HC.SOURCES)
    assert head == n_reg + n_fac + n_led == len(a["covered"])
    par = _read("docs/HALCON_PARITY.md")
    assert "evolvable registry ops (of which" not in par
    m2 = re.search(r"\*\*(\d+) / \d+ distinct real HALCON operators.*?\n  = (\d+) names: (\d+) through `Op\.halcon`"
                   r".*?, (\d+) through perception facades.*? and (\d+) through typed-ledger ops", par, re.S)
    assert m2, "HALCON_PARITY.md の見出しの内訳が読めない"
    h, total, r_, f_, l_ = (int(x) for x in m2.groups())
    assert h == total == r_ + f_ + l_


# --------------------------------------------------------------------------- #
# D3 レシピの門が主張どおりの幅                                                 #
# --------------------------------------------------------------------------- #
PROBE = "Accept — probing error of a 3-D sensor on a calibrated sphere (VDI/VDE 2634-2 idea: PF and PS)"
SOBOL = "Analyze — global sensitivity (Sobol' indices) of a model"


def _gate(name, variant, mutate=None):
    from fullseye import recipebook as rb
    r = rb.get(name)
    s = rb.sample(r, variant)
    out, outs = rb.run(r, s["value"], s["aux"])
    if mutate is not None:
        out = copy.deepcopy(out)
        mutate(out)
    return rb.check_expect(r, out, outs, s["truth"])


def test_d3_probe_sphere_gate_passes_the_real_outputs():
    assert _gate(PROBE, 0) == [] and _gate(PROBE, 1) == []


@pytest.mark.parametrize("variant,pf", [(0, 0.05), (0, 0.15), (0, 1e-6),    # 雑音 0: 閉形式の 0 以外は外れ
                                         (1, 0.2), (1, 0.32),                 # σ = 0.02: 8σ = 0.16 を超えたら外れ
                                         (1, 0.01)])                          # 2σ 未満 = 雑音を測っていない
def test_d3_probe_sphere_pf_outside_the_claim_is_rejected(variant, pf):
    assert _gate(PROBE, variant, lambda o: o.__setitem__("pf", pf)), "PF = %g を通した(variant %d)" % (pf, variant)


@pytest.mark.parametrize("variant,ps", [(0, 1e-6), (1, 0.02)])
def test_d3_probe_sphere_ps_outside_the_claim_is_rejected(variant, ps):
    assert _gate(PROBE, variant, lambda o: o.__setitem__("ps", ps))


def test_d3_sibling_sobol_gate_tells_the_smallest_index_from_zero():
    assert _gate(SOBOL, 1) == []

    def zero_s1_2(o):
        s1 = np.array(o["S1"], dtype=float)
        s1[2] = 0.0
        o["S1"] = s1
    assert _gate(SOBOL, 1, zero_s1_2), "真の 0.024 を 0 にしても通った"


# --------------------------------------------------------------------------- #
# D4 / D5 / D8 / D9 手書きの数                                                  #
# --------------------------------------------------------------------------- #
def _allowed_op_counts() -> dict:
    from test_hand_written_counts import _allowed
    return _allowed()


def test_d4_readme_does_not_state_a_tool_count_that_differs_from_the_server():
    from fullseye.mcp import server as S
    ok = {len(S.TOOLS), len(S._profile_tool_names("minimal"))}
    md = _read("README.md")
    got = [int(n) for n in re.findall(r"(?<![\d.])(\d+) tools\b(?!/)", md)]     # `py -3.11 tools/x` は除く
    bad = sorted(set(got) - ok)
    assert not bad, "README の道具の数 %s が実物 %s と違う" % (bad, sorted(ok))


def test_d5_d8_d9_hand_written_counts_in_readme_and_docs_index_are_current():
    ok = _allowed_op_counts()
    ledger = json.loads(_read("docs/OP_INDEX.json"))["tiers"]["ledger"]
    total = json.loads(_read("docs/design_notes.json"))["total"]
    hits = []
    md = _read("README.md")
    for m in re.finditer(r"(\d[\d,]*)\s+typed-ledger operators", md):
        hits.append(("README typed-ledger", int(m.group(1).replace(",", "")), {ledger}))
    for m in re.finditer(r"(\d[\d,]*) load-bearing", md):
        hits.append(("README ★", int(m.group(1).replace(",", "")), {total}))
    op_word = r"(?:operators|Operatoren|オペレータ|個運算子|个算子|개 연산자|개연산자)"
    paths = sorted(p for p in os.listdir(os.path.join(ROOT, "docs")) if re.match(r"README(\.[a-z]{2})?\.md$", p))
    assert len(paths) == 6, paths
    for p in paths:
        for m in re.finditer(r"(\d[\d,]{2,})\s*" + op_word, _read("docs/" + p)):
            hits.append((p, int(m.group(1).replace(",", "")), set(ok)))
    caps = ["docs/capabilities/" + p for p in sorted(os.listdir(os.path.join(ROOT, "docs", "capabilities")))
            if p.endswith(".md")] + ["docs/CAPABILITIES.md", "docs/CAPABILITIES.en.md"]
    assert len(caps) > 50
    for p in caps:
        for m in re.finditer(r"op が (\d[\d,]{2,}) 本", _read(p)):
            hits.append((p, int(m.group(1).replace(",", "")), set(ok)))
    bad = [(w, n) for w, n, allowed in hits if n not in allowed]
    assert not bad, "手書きの数が実物と違う: %s(許す値 %s)" % (bad, sorted(ok))


def test_d5b_the_docs_index_counts_the_ledger_not_the_type_catalogue():
    import fullseye as fs
    import gen_docs_index_ops as G
    live = {d["name"] for d in fs.list_ops(include_ledger=True) if d["tier"] == "ledger"}
    assert len(live) > 2000 and G.ledger_names() == live     # 生成器が数える集合 = op_run が引ける台帳
    idx = json.loads(_read("docs/OP_INDEX.json"))["tiers"]["ledger"]
    m = re.search(r"型つき台帳 (\d+)/(\d+)", _read("docs/README.md"))
    assert m, "docs/README.md に「型つき台帳 N/M」が無い"
    assert int(m.group(2)) == idx and int(m.group(1)) <= idx


def test_d5b_the_type_catalogue_differs_from_the_ledger_only_where_it_says_so():
    """typed_catalog は連鎖ファザーと registry の橋(tb_*)の型カタログで、台帳ではない。差は 2 種だけ:

    * 台帳に無いもの = complexops の複素画像の 12 本(``fs.<名前>`` と registry の ``tb_cx_*`` で呼ぶ。
      op_run は台帳を引くので断る)
    * 台帳にあって型カタログに無いもの = ファイル I/O(連鎖ファザーに向かない)
    """
    import fullseye as fs
    import ops
    import ops1d
    import opsfileio
    import typed_catalog as tc
    cat = {r[0] for r in tc.catalog()}
    led = {d["name"] for d in fs.list_ops(include_ledger=True) if d["tier"] == "ledger"}
    reg = {o.name for o in ops.REGISTRY}
    extra = cat - led - reg
    missing = led - cat
    assert len(extra) == 12 and len(missing) > 0
    assert {n for n in extra if n.startswith("cx_")} | {"phase_unwrap"} == extra
    io_ops = set(opsfileio.OPSFILEIO) | {n for n, m in ops1d.OPS1D.items() if m["category"] == "io"}
    assert missing <= io_ops, "台帳にあって型カタログに無い op がファイル I/O 以外にある: %s" % sorted(missing - io_ops)
    names = sorted(extra)
    assert len(names) == 12
    for n in names:
        assert callable(getattr(fs, n)), "complexops の %s が fs から呼べない" % n


# --------------------------------------------------------------------------- #
# D6 / D7 成熟度台帳                                                           #
# --------------------------------------------------------------------------- #
def _maturity():
    return json.loads(_read("docs/maturity.json"))


def test_d6_real_data_status_needs_an_example_that_read_real_data_in_the_gate_run():
    caps = [r for r in _maturity()["capabilities"] if r["status"] == "validated-public-real-data"]
    assert len(caps) > 0
    for r in caps:
        read = [e for e in r["examples"] if e["data"] == "real" and e["executed"] and e.get("real_data_read_in_gate")]
        assert read, "%s は実データ検証を名乗るが、門の実行で実データを読む例が無い" % r["id"]


def test_d6_every_linked_real_example_has_a_measured_record():
    runs = json.loads(_read("docs/real_data_runs.json"))["examples"]
    linked = sorted({e["id"] for r in _maturity()["capabilities"] for e in r["examples"] if e["data"] == "real"})
    assert len(linked) >= 10
    assert set(linked) == set(runs), "記録と名指しの実データ例が食い違う: %s" % sorted(set(linked) ^ set(runs))
    for eid in linked:
        facts = [e for r in _maturity()["capabilities"] for e in r["examples"] if e["id"] == eid]
        assert len(facts) >= 1
        assert facts[0]["real_data_read_in_gate"] == bool(runs[eid]["exit"] == 0 and runs[eid]["datasets_read"])


def test_d6_status_rule_does_not_promote_an_example_that_skipped_its_real_data():
    import gen_maturity as GM
    skipped = [{"id": "x", "data": "real", "executed": True, "real_data_read_in_gate": False}]
    read = [{"id": "x", "data": "real", "executed": True, "real_data_read_in_gate": True}]
    assert GM._status(3, 3, skipped) == "verified-synthetic"
    assert GM._status(3, 3, read) == "validated-public-real-data"
    with pytest.raises(GM.MaturityError):
        GM._example_facts("poc_real_coin_metrology", {})          # 記録の無い実データ例は止める


def test_d6_mark_read_writes_only_when_asked(tmp_path, monkeypatch):
    import realdata
    log = tmp_path / "read.log"
    monkeypatch.delenv(realdata.REAL_DATA_LOG_ENV, raising=False)
    realdata.mark_read("probe-a")
    assert not log.exists()
    monkeypatch.setenv(realdata.REAL_DATA_LOG_ENV, str(log))
    realdata.mark_read("probe-b")
    assert log.read_text(encoding="utf-8").split() == ["probe-b"]
    with pytest.raises(ValueError):
        realdata.mark_read("two\nlines")


def test_d6_readme_says_the_tless_poc_shows_a_record_in_ci():
    md = _read("README.md")
    i = md.index("**Real RGB-D 6-DoF PoC:**")
    para = md[i:md.index("\n\n", i)]
    assert "recorded" in para and "CI" in para and "not count it as real-data validation" in para


def test_d7_not_run_by_any_gate_is_counted_from_the_disk():
    import examples2d as EX2
    e = _maturity()["example_execution"]
    tests_src = {p: _read("tests/" + p) for p in os.listdir(os.path.join(ROOT, "tests")) if p.endswith(".py")}
    assert len(tests_src) > 100
    names = sorted(EX2.EXCLUDED)
    assert len(names) > 0
    # 「走らせる」= import かパスで起動(名前を挙げるだけの、この試験のような参照は数えない)
    def runs(n, s):
        return ("from examples import" in s and re.search(r"from examples import[^\n]*\b%s\b" % n, s)) \
            or ("examples.%s import" % n) in s or ("import examples.%s" % n) in s or ("examples/%s.py" % n) in s
    unrun = sorted(n for n in names if not n.startswith("poc_")
                   and not any(runs(n, s) for s in tests_src.values()))
    assert e["not_run_by_any_gate"] == len(unrun) == len(e["not_run_by_any_gate_reasons"])
    assert sorted(e["not_run_by_any_gate_reasons"]) == unrun
    assert {"g1_policy_staged", "hand_tracking_demo", "perception_staged", "gsplat_trained_product"} <= set(unrun)
    assert e["scripts_on_disk"] == len(EX2.discover())
    m = re.search(r"Of ([\d,]+) examples, ([\d,]+) are actually run by a gate", _read("README.md"))
    assert m and (int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))) ==         (e["scripts_on_disk"], e["scripts_on_disk"] - e["not_run_by_any_gate"])


# --------------------------------------------------------------------------- #
# 小 2 件                                                                     #
# --------------------------------------------------------------------------- #
def test_small_water_note_prints_what_python_prints():
    line = [ln for ln in _read("docs/capabilities/water-transparent-media.md").splitlines()
            if "0.21 * 8.0 ** 2 / 9.80665" in ln]
    assert len(line) == 1
    printed = line[0].split("#")[-1].split()
    assert printed[-1] == str(round(0.21 * 8.0 ** 2 / 9.80665, 3))


def test_small_known_issues_32_2_and_32_3_are_struck_like_32_16():
    rows = {m.group(1): m.group(0) for m in re.finditer(r"^\| (32-(?:2|3|16)) \|.*$", _read("docs/KNOWN_ISSUES.md"), re.M)}
    assert set(rows) == {"32-2", "32-3", "32-16"}
    for k in ("32-2", "32-3"):
        assert "~~" in rows[k] and rows[k].rstrip().endswith("| 解消済み |"), rows[k]
