# -*- coding: utf-8 -*-
"""CLI の入口が**全層を横断する**ことの門(2026-09-15)。

## なぜ要るか

外部 AI(Codex / Copilot)に「文書だけ渡して op を探させる」実測をしたところ、
CLI から出る答えと Python API から出る答えが**別の集合**だった:

| 入口 | 見ていた層 |
|---|---|
| `imgevolve.py ops --search icp` | レジストリ + HALCON 名だけ → **0 件** |
| `imgevolve.py has frame_align` | 同上 → **exit 1(無い)** |
| `fullseye.op_find("icp")` | 全層 → **7 件** |
| `fullseye.op_assist("otsu")` | 台帳専用 → **ValueError** |
| `fullseye.op_path("image","region")` | 台帳専用の型グラフ → **[]** |

どれも「無い」ではなく「**その入口からは見えない**」。呼ぶ側にその 2 つは
区別できないので、`icp` も `frame_align` も実装済みなのに「無い」と結論して
同じものを作りかける([[feedback_registered_only_gates_miss_unregistered]] と
同型 —— 登録済みだけを数える門は、未登録に構造的に盲目)。

ここで見張るのは「**入口が違っても同じ集合が見えること**」と、
「**0 件が『見ていない』の言い換えになっていないこと**」(census 行が実際に
見た層の内訳を数字で出す)。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = os.path.join(ROOT, "imgevolve.py")


def run_cli(*args):
    """CLI を子プロセスで走らせ (rc, stdout, stderr)。

    ★`PYTHONIOENCODING` を立てる。Windows の既定は cp932 で、日本語の注記を
    書き出す時点で子プロセスが `UnicodeEncodeError` になりうる —— それは
    「CLI が壊れている」ではなく「試験環境の文字コード」なので、ここで固定する
    (同じ理由で、この CLI を PowerShell から読む AI には `-Encoding utf8` が要る。
    `AGENTS.md` にそう書いてある)。
    """
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, CLI, *args], cwd=ROOT, env=env,
                       capture_output=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr


# --------------------------------------------------------------------------- #
# find —— 台帳が引けること                                                      #
# --------------------------------------------------------------------------- #
def test_find_reaches_the_typed_ledgers():
    """`ops find icp` が 1 件以上。**これが 0 件だったのが直した defect**。"""
    rc, out, err = run_cli("ops", "find", "icp")
    assert rc == 0, err
    hits = [ln for ln in out.splitlines() if ln.startswith("icp") or " [ledger/" in ln]
    assert hits, "ops find icp が 1 件も返さない:\n" + out
    assert "hits for 'icp'" in out


def test_find_counts_the_layers_it_actually_looked_at():
    """「0 件」と「見ていない」を分ける —— census 行が層ごとの実数を出す。

    台帳(numpy/scipy だけで組める一次モジュール)は環境によらず千件規模。
    ここが痩せたら、それは検索が効いていない証拠であって『そういう環境』ではない。
    """
    rc, out, _ = run_cli("ops", "find", "icp")
    assert rc == 0
    line = [ln for ln in out.splitlines() if ln.startswith("見た層:")]
    assert line, "見た層の内訳が出ていない(0 件の理由を言えない門になる):\n" + out
    n_ledger = int(line[0].split("ledger ")[1].split(" ")[0])
    assert n_ledger >= 900, "台帳が %d 件しか見えていない(検索が層に届いていない)" % n_ledger


def test_find_json_is_the_only_thing_on_stdout():
    rc, out, _ = run_cli("ops", "find", "icp", "--json")
    assert rc == 0
    rows = json.loads(out)                       # ← 汚れていれば例外で落ちる
    assert rows and rows[0]["op"] and rows[0]["tier"]
    assert {"op", "tier", "in_sort", "out_sort", "call", "score"} <= set(rows[0])


def test_find_filters_do_not_silently_pass_everything():
    """`--out pose` の絞り込みが本当に効く(空を通す門にしない)。"""
    rc, out, _ = run_cli("ops", "find", "icp", "--out", "pose", "--json")
    assert rc == 0
    rows = json.loads(out)
    assert rows, "--out pose で 1 件も残らない"
    assert all(r["out_sort"] == "pose" for r in rows)


# --------------------------------------------------------------------------- #
# describe —— 層が違っても同じ形、落ちない                                      #
# --------------------------------------------------------------------------- #
def test_describe_survives_an_op_that_op_assist_refuses():
    """`otsu` は台帳に無い(`fs.op_assist` は ValueError)。describe は落ちない。"""
    rc, out, err = run_cli("ops", "describe", "otsu")
    assert rc == 0, err
    assert "tier=registry" in out, out
    assert "image -> region" in out


def test_describe_says_which_tier_the_answer_came_from():
    for op, tier in (("otsu", "registry"), ("icp_point2plane", "ledger")):
        rc, out, err = run_cli("ops", "describe", op, "--json")
        assert rc == 0, err
        d = json.loads(out)
        assert d["tier"] == tier, "%s の tier が %s" % (op, d["tier"])
        assert d["source"], "どの層から来た情報か言っていない"
        assert d["call"], "呼び方(層で違う)を言っていない"


def test_describe_of_an_unknown_op_fails_with_a_reason():
    rc, out, _ = run_cli("ops", "describe", "no_such_op_at_all")
    assert rc != 0, "実在しない op で 0 を返している"
    assert "unknown op" in out and "見た層:" in out, out


# --------------------------------------------------------------------------- #
# path —— 型で繋ぐ                                                             #
# --------------------------------------------------------------------------- #
def test_path_image_to_region_is_not_empty():
    """`otsu` を筆頭に image→region の op は実測 83 本。**[] は嘘**だった。"""
    rc, out, err = run_cli("ops", "path", "image", "region")
    assert rc == 0, err
    assert "最短 1 段" in out, out
    rc, out, _ = run_cli("ops", "path", "image", "region", "--json")
    d = json.loads(out)
    assert d["n_chains"] >= 1 and d["chains"], d
    assert d["steps"][0][0]["call"], "各段の呼び方(層で違う)が無い"


def test_path_with_an_unknown_sort_says_so_instead_of_returning_nothing():
    rc, out, _ = run_cli("ops", "path", "image", "no_such_sort_at_all")
    assert rc != 0
    assert "型語彙に無い" in out and "見た層:" in out, out


# --------------------------------------------------------------------------- #
# 旧挙動を壊していないこと                                                      #
# --------------------------------------------------------------------------- #
def test_registry_only_keeps_the_old_search_behaviour():
    """`--registry-only` は旧挙動そのまま(レジストリ + HALCON 名だけ)。"""
    rc, out, err = run_cli("ops", "--search", "icp", "--registry-only")
    assert rc == 0, err
    assert out.strip().endswith("--- 0 ops match ---"), out


def test_default_search_now_crosses_the_layers():
    rc, out, err = run_cli("ops", "--search", "icp")
    assert rc == 0, err
    assert "台帳" in out and "0 ops match" not in out, out


def test_bare_ops_still_lists_the_registry():
    rc, out, err = run_cli("ops")
    assert rc == 0, err
    tail = out.strip().splitlines()[-1]
    assert tail.startswith("--- ") and tail.endswith(" ops match ---"), tail
    assert int(tail.split()[1]) > 800, tail


def test_has_consults_the_ledger_before_saying_no():
    """`frame_align` は opsastrostack に実装済み。exit 1 で「無い」は嘘だった。"""
    rc, out, err = run_cli("has", "frame_align")
    assert rc == 0, err + out
    assert "IMPLEMENTED" in out and "tier=ledger" in out, out


@pytest.mark.parametrize("op", ["no_such_halcon_op_at_all"])
def test_has_still_reports_a_genuinely_unknown_op(op):
    rc, out, _ = run_cli("has", op)
    assert rc != 0 and "unknown op" in out
