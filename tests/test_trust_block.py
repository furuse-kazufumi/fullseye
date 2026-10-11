# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""トップページの「どう確かめているか」節(trust ブロック)の門。

数は全部 ``docs/{test_count,gate_inventory,op_count_history}.json`` と ``docs/maturity.json`` に
あり、``tools/gen_trust_block.py`` が描く。ここで落ちるのは次のどれか:

* ブロック / ``docs/OP_COUNT_HISTORY.md`` が、いまのデータから描いたものと食い違う
  (手で数を直した、データを変えて生成器を回し忘れた)
* データが pyproject の版のものでない(版を上げたのに測り直していない)
* 過去の版の行が書き換えられた(記録は固定)

★各門は「壊して落ちることを確かめる」対になっている —— 一致の門は空でも通るので、
食い違いを実際に作って落ちることを見る。
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import gen_trust_block as G  # noqa: E402

#: 0.6.0 までの行の指紋。**過去の行は記録なので書き換えない。** 新しい版の行を足しても
#: この指紋は変わらない(0.6.0 以前の行だけを数える)。
FROZEN_THROUGH = "0.6.0"
FROZEN_SHA256 = "00a1f05b1f5c329fd1fec7a4671c683fc9c8f1ca2ce79bfc4d5832c80cd6939b"


@pytest.fixture(scope="module")
def data():
    return G.load_all()


def _frozen_fingerprint(history: dict) -> str:
    rows = [r for r in history["rows"] if G.vkey(r["version"]) <= G.vkey(FROZEN_THROUGH)]
    assert len(rows) == 20, len(rows)
    return hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False)
                          .encode("utf-8")).hexdigest()


def _copy_targets(tmp_path) -> str:
    """生成物の書き込み先だけを一時 dir に複製する(壊す試験用)。"""
    rels = [rel for rel, *_ in G.TARGETS] + [G.HISTORY_PAGE]
    assert len(rels) == 8
    for rel in rels:
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(os.path.join(ROOT, rel), dst)
    return str(tmp_path)


# ---------------------------------------------------------------- 一致の門

def test_blocks_and_history_page_match_the_render(data):
    probs = G.drift_problems(data)
    assert not probs, ("trust ブロックが生成物と食い違う —— `py -3.11 tools/gen_trust_block.py` を"
                       "回すこと(数は docs/*.json を直す。ブロックを手で直さない):\n" + "\n".join(probs))


def test_every_target_carries_exactly_one_block():
    assert len(G.TARGETS) == 7
    for rel, *_ in G.TARGETS:
        text = io.open(os.path.join(ROOT, rel), encoding="utf-8").read()
        assert text.count(G.START) == 1 and text.count(G.END) == 1, rel


def test_a_hand_edited_number_in_the_block_fails(data, tmp_path):
    """壊して確かめる: ブロックの中のテスト件数を 1 だけ書き換えると門が落ちる。"""
    root = _copy_targets(tmp_path)
    assert G.drift_problems(data, root=root) == []
    shown = G._n(data["tests"]["count"])
    p = os.path.join(root, "docs", "README.md")
    s = io.open(p, encoding="utf-8").read()
    block = G.extract(s)
    assert shown in block
    forged = G._n(data["tests"]["count"] + 1)
    io.open(p, "w", encoding="utf-8").write(s.replace(block, block.replace(shown, forged, 1)))
    probs = G.drift_problems(data, root=root)
    assert len(probs) == 1 and probs[0].startswith("docs/README.md"), probs


def test_a_hand_edited_history_page_fails(data, tmp_path):
    root = _copy_targets(tmp_path)
    p = os.path.join(root, G.HISTORY_PAGE)
    s = io.open(p, encoding="utf-8").read()
    assert "| 0.2.0 |" in s
    io.open(p, "w", encoding="utf-8").write(s.replace("| 0.2.0 |", "| 0.2.0 (edited) |", 1))
    probs = G.drift_problems(data, root=root)
    assert len(probs) == 1 and G.HISTORY_PAGE in probs[0], probs


def test_changing_the_data_without_regenerating_fails(data):
    """データだけ変えて生成器を回し忘れると、7 か所すべてと全版の表が食い違う。"""
    d = copy.deepcopy(data)
    d["history"]["rows"][-1]["poc"] += 1
    probs = G.drift_problems(d)
    assert len(probs) == 8, probs


def test_a_missing_marker_is_reported(data, tmp_path):
    root = _copy_targets(tmp_path)
    p = os.path.join(root, "README.md")
    s = io.open(p, encoding="utf-8").read()
    io.open(p, "w", encoding="utf-8").write(s.replace(G.END, ""))
    probs = G.drift_problems(data, root=root)
    assert len(probs) == 1 and "マーカーが無い" in probs[0], probs


# ---------------------------------------------------------------- 古びの門

def test_data_is_for_the_pyproject_version(data):
    probs = G.stale_problems(data)
    assert not probs, "\n".join(probs)


def test_a_version_without_a_history_row_fails(data):
    """壊して確かめる: pyproject の版を上げただけ(行を足さず、測り直さず)だと落ちる。"""
    d = copy.deepcopy(data)
    d["version"] = "9.9.9"
    probs = G.stale_problems(d)
    assert len(probs) == 3, probs
    assert any("9.9.9 の行が無い" in p for p in probs)
    assert any(p.startswith("test_count.json") for p in probs)
    assert any(p.startswith("gate_inventory.json") for p in probs)


def test_a_new_row_alone_is_not_enough(data):
    """行を足しても、テスト件数と門の棚卸しが古い版のままなら落ちる。"""
    d = copy.deepcopy(data)
    row = dict(d["history"]["rows"][-1], version="9.9.9", tag="v9.9.9")
    d["history"]["rows"].append(row)
    d["version"] = "9.9.9"
    probs = G.stale_problems(d)
    assert len(probs) == 2, probs


def test_current_row_against_the_index(data):
    """現行の行と索引: 普段は「行 ≤ 索引」(リリース後に op が増えるのは正常)、
    ``--release-check`` では層ごとに厳密一致。"""
    assert G.stale_problems(data, release=True) == [], \
        "版 %s の行がいまの docs/OP_INDEX.json と一致しない" % data["version"]
    grown = copy.deepcopy(data)
    grown["index"]["n_ops"] += 1
    grown["index"]["tiers"]["ledger"] += 1
    assert G.stale_problems(grown) == []
    assert len(G.stale_problems(grown, release=True)) == 2
    shrunk = copy.deepcopy(data)
    shrunk["index"]["n_ops"] -= 1
    shrunk["index"]["tiers"]["registry"] -= 1
    assert len(G.stale_problems(shrunk)) == 2


def test_rows_out_of_order_fail(data):
    d = copy.deepcopy(data)
    rows = d["history"]["rows"]
    rows.insert(0, dict(rows[-1]))          # 最新の行の複製を先頭へ = 順序違反 + 重複
    probs = G.stale_problems(d)
    assert len(probs) == 1 and "並んでいない" in probs[0], probs


# ---------------------------------------------------------------- 記録の固定

def test_past_rows_are_not_rewritten(data):
    assert _frozen_fingerprint(data["history"]) == FROZEN_SHA256, (
        "%s 以前の行が書き換えられた。過去の版の行は記録なので直さない(新しい版は行を足す)。"
        "測り方の誤りが見つかったなら、行は残して definition_changes に注記を足す。" % FROZEN_THROUGH)


def test_the_fingerprint_sees_a_one_digit_change(data):
    d = copy.deepcopy(data["history"])
    d["rows"][3]["tests"] += 1
    assert _frozen_fingerprint(d) != FROZEN_SHA256


def _git_show_index(tag: str):
    try:
        r = subprocess.run(["git", "show", "%s:docs/OP_INDEX.json" % tag], cwd=ROOT,
                           capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    return json.loads(r.stdout.decode("utf-8"))


def test_rows_agree_with_the_index_committed_at_each_tag(data):
    """独立経路の検算: 行の「索引の計」を、そのタグにコミットされた OP_INDEX.json と比べる。

    行はタグを checkout して索引を作り直した値、こちらは当時コミットされたファイル ——
    別の経路で同じ数が出るか。タグが無い checkout(浅い clone)では skip。
    """
    rows = [r for r in data["history"]["rows"] if r["index"] is not None]
    assert len(rows) >= 10
    checked = 0
    for r in rows:
        idx = _git_show_index(r["tag"])
        if idx is None:
            continue
        checked += 1
        assert idx["n_ops"] == r["index"], (r["version"], idx["n_ops"], r["index"])
        assert sorted(idx["tiers"]) == r["index_tiers"], r["version"]
    if checked == 0:
        pytest.skip("タグが無い checkout(浅い clone)なので照合できない")


# ---------------------------------------------------------------- データの形

def test_test_count_has_its_provenance_and_a_sane_floor(data):
    tc = data["tests"]
    for k in ("version", "count", "date", "commit", "command", "environment", "relation"):
        assert tc.get(k), k
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", tc["date"])
    assert re.fullmatch(r"[0-9a-f]{10}", tc["commit"])
    # 安い下限: 収集件数は、tests/ に書かれた test 関数の数を下回らないはず
    # (パラメタ化で増えることはあっても減らない)。下回るなら記録が古いか数え損ね。
    defs = 0
    for dirpath, _dirs, files in os.walk(os.path.join(ROOT, "tests")):
        for f in files:
            if f.endswith(".py"):
                src = io.open(os.path.join(dirpath, f), encoding="utf-8", errors="replace").read()
                defs += len(re.findall(r"^\s*(?:async\s+)?def test_\w+", src, re.M))
    assert defs > 1000, defs
    assert tc["count"] >= defs, ("記録したテスト件数 %d が、tests/ の test 関数の数 %d を下回る ——"
                                 "測り直すこと" % (tc["count"], defs))
    row = G._row(data["history"], tc["version"])
    if tc["relation"] == "after_release":
        assert tc["count"] >= row["tests"], (tc["count"], row["tests"])


def test_gate_inventory_is_complete(data):
    gi = data["gates"]
    assert tuple(gi["checks"]) == G.CHECKS
    mids = {m["id"] for m in gi["measurements"]}
    assert len(mids) == len(gi["measurements"]) == 2
    for m in gi["measurements"]:
        assert re.fullmatch(r"[0-9a-f]{10}", m["commit"]), m
        assert m["relation"] in ("in_release", "after_release"), m
    assert [t["id"] for t in gi["tiers"]] == ["t1", "t2", "t3", "t4", "t5", "t5b", "t6"]
    for t in gi["tiers"]:
        assert t["measurement"] in mids, t["id"]
        assert set(t["caught"]) == set(G.CHECKS), t["id"]
        assert 0 <= t["behavioural_gates"] and 0 <= t["bookkeeping_gates"], t["id"]
        # 振る舞いの門が 0 なのに ✓ がある(またはその逆)は記録の矛盾
        assert (t["behavioural_gates"] > 0) == any(t["caught"].values()), t["id"]
    for k in ("method", "not_covered"):
        assert gi[k]["ja"] and gi[k]["en"], k


def test_every_language_names_every_tier_and_has_no_kana_outside_ja(data):
    ids = [t["id"] for t in data["gates"]["tiers"]]
    assert len(ids) == 7 and len(G.L10N) == 6
    for lang, t in G.L10N.items():
        assert set(t["tiers"]) == set(ids), lang
        assert len(t["cols"]) == 4 + len(G.CHECKS), lang
        assert len(t["stages"]) == len(G.STAGES), lang
        if lang != "ja":
            block = G.build_block(lang, data)
            assert not re.search(r"[぀-ヿ]", block), "%s のブロックにかなが混ざっている" % lang


def test_no_local_paths_in_public_files():
    """測定の道具は repo の外にある —— その置き場所を公開物に書かない。"""
    rels = ["docs/test_count.json", "docs/gate_inventory.json", "docs/op_count_history.json",
            G.HISTORY_PAGE, "tools/gen_trust_block.py"]
    bad = re.compile(r"[A-Za-z]:[\\/]|/Users/|/home/|AppData|scratchpad", re.I)
    for rel in rels:
        text = io.open(os.path.join(ROOT, rel), encoding="utf-8").read()
        m = bad.search(text)
        assert not m, "%s に手元のパスがある: %r" % (rel, text[max(0, m.start() - 30):m.end() + 30])


def test_summary_shows_each_minor_release_and_both_sides_of_each_definition_change(data):
    hist = data["history"]
    shown = G.summary_versions(hist)
    minors = [r["version"] for r in hist["rows"] if r["version"].endswith(".0")]
    assert len(minors) >= 6
    assert set(minors) <= set(shown)
    assert len(hist["definition_changes"]) == 2
    for ch in hist["definition_changes"]:
        assert ch["version"] in shown and ch["compare_with"] in shown, ch
    assert shown[-1] == data["version"]
