# -*- coding: utf-8 -*-
"""AI 向け指示書 3 本(`AGENTS.md` / `.github/copilot-instructions.md` / `GEMINI.md`)の門。

## なぜ要るか(2026-09-15)

この repo には Claude 向けの `skills/fullseye-ops/SKILL.md` **しか**無く、
Codex / Copilot / Gemini から見ると **1,946 本のノートが在ることすら分からない**
状態だった。3 本を手で書けば必ず食い違うので、**原稿 1 つから生成**する
(`tools/gen_agent_files.py`)。

ここで見張るのは 4 つ。どれも「書いたのに嘘になっている」を止めるためのもので、
**書いてあることが本当に動くか**まで確かめる(散文は自分では落ちない):

1. コミット済み == 生成物(他の docs 生成物と同じ drift 検査)
2. **件数が実数**(この門が索引とコーパスを**自分で数え直して**照合する。
   生成器と同じ関数を呼ぶと「生成器が一貫している」ことしか言えない)
3. **書いてある CLI コマンドが実際に動く**(`ops find icp` を 1 本走らせる)
4. ローカル絶対パスが混ざっていない(公開物なので)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

FILES = ["AGENTS.md", os.path.join(".github", "copilot-instructions.md"), "GEMINI.md"]

#: 各ファイルの上限(短さは仕様 —— 読まれない指示書は無いのと同じ)。
MAX_LINES = 60


def _text(rel: str) -> str:
    p = os.path.join(ROOT, rel)
    assert os.path.exists(p), "%s が無い —— `py -3.11 tools/gen_agent_files.py`" % rel
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def test_the_committed_files_match_what_the_generator_produces():
    """★本体の drift 検査。古びたらここで落ちる(直し方はコマンドを出す)。"""
    r = subprocess.run([sys.executable, os.path.join("tools", "gen_agent_files.py"), "--check"],
                       cwd=ROOT, capture_output=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, (
        "AI 向け指示書がコミット済みと食い違う —— "
        "`py -3.11 tools/gen_agent_files.py` で作り直す\n" + (r.stdout or "") + (r.stderr or ""))


@pytest.mark.parametrize("rel", FILES)
def test_each_file_is_short_and_not_empty(rel):
    lines = _text(rel).splitlines()
    assert 20 <= len(lines) <= MAX_LINES, "%s が %d 行(20〜%d 行に収める)" % (rel, len(lines), MAX_LINES)


@pytest.mark.parametrize("rel", FILES)
def test_no_local_absolute_paths(rel):
    """公開物にローカル絶対パスを書かない。"""
    bad = re.findall(r"[A-Za-z]:[\\/](?:dev|Users|home)[\\/]\S*|/home/\S+|/Users/\S+", _text(rel))
    assert not bad, "%s にローカル絶対パス: %s" % (rel, bad[:5])


@pytest.mark.parametrize("rel", FILES)
def test_the_counts_are_the_real_ones(rel):
    """★件数を**この門が数え直して**照合する。

    生成器の `facts()` を呼ぶと「生成器が自分と一致する」ことしか言えない
    ([[feedback_drift_gate_passes_empty_output]] の「一致の門は空を通す」)。
    ここでは索引 JSON とコーパスの**ファイルの側**から独立に数える。
    """
    with open(os.path.join(ROOT, "docs", "OP_INDEX.json"), encoding="utf-8") as fh:
        idx = json.load(fh)
    tiers = idx["tiers"]
    registry = sum(tiers.get(k, 0) for k in ("registry", "color", "nary"))
    notes = 0
    for dirpath, _dirs, files in os.walk(os.path.join(ROOT, "docs", "ops")):
        if os.path.basename(dirpath) in ("guides", "_fig"):
            continue
        notes += sum(1 for f in files if f.endswith(".md") and not f.startswith("INDEX")
                     and f != "SAMPLES.md")
    assert registry > 0 and tiers.get("ledger", 0) > 0 and notes > 0, "数え方が壊れている"

    text = _text(rel)
    for what, n in (("総数", idx["n_ops"]), ("registry", registry),
                    ("ledger", tiers["ledger"]), ("notes", notes),
                    ("sorts", len(idx["sorts"]))):
        assert re.search(r"\b%d\b" % n, text), (
            "%s に %s の実数 %d が書かれていない —— "
            "`py -3.11 tools/gen_agent_files.py` で作り直す(手で書かない)" % (rel, what, n))


def test_the_documented_cli_command_actually_runs():
    """★書いてある検索コマンドを 1 本走らせる。散文は自分では落ちないので。"""
    text = _text("AGENTS.md")
    assert "imgevolve.py ops find" in text, "検索順の 1 番目(CLI の横断検索)が書かれていない"
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "imgevolve.py"),
                        "ops", "find", "icp", "--json"],
                       cwd=ROOT, env=env, capture_output=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, "AGENTS.md が書いているコマンドが動かない:\n" + (r.stderr or "")
    rows = json.loads(r.stdout)
    assert rows, "書いてあるコマンドが 0 件を返す(指示書が空回りしている)"


def test_the_three_files_carry_the_same_manuscript():
    """宛名の 1 行を除いて本文が同一(3 か所に書くと必ず食い違う、を封じる)。"""
    bodies = {rel: _text(rel).split("\n\n", 1)[1].split("\n", 1)[1] for rel in FILES}
    uniq = set(bodies.values())
    assert len(uniq) == 1, "3 本の本文が食い違っている: %s" % sorted(bodies)


def test_it_does_not_contradict_the_claude_skill():
    """SKILL.md と同じ入口を指していること(片方だけ古びるのを止める)。"""
    skill = _text(os.path.join("skills", "fullseye-ops", "SKILL.md"))
    agents = _text("AGENTS.md")
    for anchor in ("docs/ops/INDEX.md", "import fullseye"):
        assert anchor in skill and anchor in agents, "%s がどちらかに無い" % anchor
