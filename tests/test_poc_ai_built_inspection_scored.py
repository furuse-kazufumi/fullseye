# -*- coding: utf-8 -*-
"""``poc_ai_built_inspection_scored`` と ``tools/gen_ai_inspection_recipes.py`` の門(データ不要)。

Gates for the AI-built-inspection PoC and its recipe generator that need no data and no LLM:
the saved recipe file is well formed and carries no LLM location, the prompts it was made from are
the current ones, the recipe extraction is fail-closed, and the scoring counts what it says.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def poc():
    return _load(ROOT / "examples" / "poc_ai_built_inspection_scored.py", "poc_ai_built_inspection_scored")


@pytest.fixture(scope="module")
def gen():
    return _load(ROOT / "tools" / "gen_ai_inspection_recipes.py", "gen_ai_inspection_recipes")


@pytest.fixture(scope="module")
def saved(poc):
    return json.loads(poc.RECIPES_JSON.read_text(encoding="utf-8"))


def test_saved_runs_are_well_formed_and_none_is_dropped(poc, saved):
    runs = saved["runs"]
    assert runs, "no saved AI run"
    for r in runs:
        assert r["task"] in poc.TASKS
        assert r["phase"] in poc.PHASES
        assert isinstance(r["model"], str) and r["model"]
        assert isinstance(r["run"], int) and r["run"] >= 1
        assert r["recipe_source"] in ("final_json", "last_pipeline", "none")
        assert (r["recipe"] is None) == (r["recipe_source"] == "none")
        if r["recipe"] is not None:
            assert all(isinstance(s, dict) and isinstance(s.get("op"), str) for s in r["recipe"])
    # 各 (課題, 模型) の回は 1..N の連番(失敗した回を消していない)
    groups: dict = {}
    for r in runs:
        groups.setdefault((r["task"], r["phase"], r["model"]), []).append(r["run"])
    assert groups
    for key, ks in groups.items():
        assert sorted(ks) == list(range(1, poc.PHASES[key[1]]["expected"] + 1)), key
    # 便はすべて、課題ごとに少なくとも 1 つの模型で埋まっている
    for task in poc.TASKS:
        assert {ph for (t, ph, _m) in groups if t == task} == set(poc.PHASES), task


def test_saved_file_never_records_where_the_llm_runs(poc):
    import os
    text = poc.RECIPES_JSON.read_text(encoding="utf-8")
    assert not re.search(r"https?://", text)
    assert not re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", text)          # IPv4
    assert not re.search(r"localhost", text, re.I)
    assert not re.search(r"\.(?:lan|local|localdomain|internal|intranet|corp|home\.arpa)\b", text, re.I)  # ホスト名
    # 手元に所在があれば、その値とホストの部分が記録に無いこと(値そのものはどこにも書かない)
    host = os.environ.get("OLLAMA_HOST", "").strip()
    if host:
        bare = re.sub(r"^https?://", "", host, flags=re.I).rstrip("/")
        for part in {host, bare, bare.split(":")[0]}:
            if len(part) >= 3:
                assert part not in text


def test_saved_runs_were_made_from_the_current_prompts(poc, gen, saved):
    import hashlib
    sha = lambda t: hashlib.sha256(t.encode("utf-8")).hexdigest()  # noqa: E731
    prompts = saved["prompts"]
    assert prompts and all(sha(v) == k for k, v in prompts.items())         # 表は自分の SHA-256 と一致
    current = [r for r in saved["runs"] if poc.PHASES[r["phase"]]["current_prompts"]]
    assert current
    for r in saved["runs"]:
        assert r["system_prompt_sha256"] in prompts and r["request_sha256"] in prompts, r["phase"]
    for r in current:
        assert r["request_sha256"] == sha(poc.TASKS[r["task"]]["request"]), (r["phase"], r["task"], r["run"])
        assert r["system_prompt_sha256"] == sha(gen.SYSTEM_PROMPT), (r["phase"], r["task"], r["run"])


def test_the_recipe_record_is_pinned(poc, saved):
    assert poc.recipes_fingerprint(saved) == poc.RECIPES_SHA256


def test_every_saved_recipe_follows_from_its_transcript(gen, saved):
    """レシピは発言記録から再導出できる(final_json = 最後の答えの JSON、last_pipeline = 最後に成功した試走)。"""
    unverifiable = []
    assert saved["runs"]
    for r in saved["runs"]:
        key = (r["phase"], r["task"], r["model"], r["run"])
        if r["recipe_source"] == "final_json":
            got = gen.extract_recipe(r["final_text"])
            if got is None and r.get("final_text_truncated_at"):
                unverifiable.append(key)                 # 第 1 便は発言を 600 字で切って保存していた
                continue
            assert got == r["recipe"], key
        elif r["recipe_source"] == "last_pipeline":
            ok = [c for c in r["calls"] if c["tool"] == "fullseye_pipeline" and not c["is_error"] and c.get("stages")]
            assert ok and ok[-1]["stages"] == r["recipe"], key
            assert gen.extract_recipe(r["final_text"]) is None, key
        else:
            assert r["recipe"] is None, key
    # 再導出できないのは第 1 便の切れた 1 本だけ(増えたら保存の仕方が壊れている)
    assert all(k[0] == "v1_openai_ctx4096" for k in unverifiable), unverifiable
    assert len(unverifiable) <= 1, unverifiable


def test_scores_file_rows_match_the_saved_recipes(poc, saved):
    rec = json.loads(poc.SCORES_JSON.read_text(encoding="utf-8"))
    assert poc.TASKS
    for task in poc.TASKS:
        rows = {r["key"]: r for r in rec[task]["rows"]}
        ms = poc.methods_for(task, saved)
        assert ms
        assert len(rows) == len(ms) + 1                                  # + 良品学習
        for m in ms:
            want = poc.recipe_sha(m["stages"]) if m["stages"] else None
            assert rows[m["key"]]["recipe_sha256"] == want, m["key"]


def test_extract_recipe_takes_only_a_stage_list(gen):
    ok = gen.extract_recipe('完成です。\n```json\n{"stages": [{"op": "gaussian", "a": 0.5}, {"op": "otsu"}]}\n```')
    assert ok == [{"op": "gaussian", "a": 0.5}, {"op": "otsu"}]
    assert gen.extract_recipe("gaussian のあと otsu を使います") is None
    assert gen.extract_recipe('{"stages": []}') is None
    assert gen.extract_recipe('{"stages": [{"a": 0.5}]}') is None             # op の無い段は拒否
    assert gen.extract_recipe('{"name": "fullseye_pipeline", "arguments": {}}') is None
    # 余計な鍵は落とす(保存する段は op / a / b / params だけ)
    assert gen.extract_recipe('{"stages": [{"op": "otsu", "why": "x"}]}') == [{"op": "otsu"}]


def test_text_tool_calls_are_picked_from_prose_and_only_for_known_tools(gen):
    allowed = {"fullseye_load_image", "fullseye_pipeline"}
    txt = ('まず画像を読みます。\n{"name": "fullseye_load_image", "arguments": {"path": "a.png"}}\n'
           'つぎに {"name": "rm_rf", "arguments": {}} は知らない道具')
    calls = gen.text_tool_calls(txt, allowed)
    assert [c["function"]["name"] for c in calls] == ["fullseye_load_image"]
    assert calls[0]["function"]["arguments"] == {"path": "a.png"}
    assert gen.text_tool_calls("JSON の無い文", allowed) == []


def test_local_chat_reads_the_host_only_from_the_environment(gen, monkeypatch):
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    with pytest.raises(SystemExit):
        gen.LocalChat("m", 0.7)
    monkeypatch.setenv("OLLAMA_HOST", "198.51.100.7:9")                 # TEST-NET-2(文書用の番地)
    chat = gen.LocalChat("m", 0.7)
    assert "198.51.100.7" not in chat.safe("failed to reach 198.51.100.7:9")


def test_runs_over_the_call_cap_are_scored_as_cut_at_the_cap(poc, saved):
    over = [r for r in saved["runs"] if len(r["calls"]) > poc.CALL_CAP]
    assert over, "記録に上限を超えた回がある前提(ローカルの道具は発言の頭でしか数えていなかった)"
    for r in over:
        stages, capped = poc.capped_recipe(r)
        ok = [c for c in r["calls"][:poc.CALL_CAP] if c["tool"] == "fullseye_pipeline" and not c["is_error"]
              and c.get("stages")]
        assert capped and stages == (ok[-1]["stages"] if ok else None), (r["phase"], r["task"], r["run"])
    inside = next(r for r in saved["runs"] if len(r["calls"]) <= poc.CALL_CAP and r["recipe"])
    assert poc.capped_recipe(inside) == (inside["recipe"], False)


def test_the_cloud_column_records_its_conditions(poc, saved):
    cloud = [r for r in saved["runs"] if r["phase"] == "cloud_v2"]
    assert len(cloud) == 3 * len(poc.TASKS)
    for r in cloud:
        c = r["conditions"]
        assert {"model", "temperature", "harness", "nudges", "call_cap", "brief_sha256"} <= set(c)
        assert c["brief_sha256"] in saved["prompts"]
        assert r["model"] == "cloud" and len(r["calls"]) <= poc.CALL_CAP


def test_scoring_counts_what_it_says(poc):
    lab = np.array([1, 1, 0, 0])
    m = np.zeros((4, 6, 6), bool)
    m[0, 1:3, 1:3] = True
    m[3, 5, 5] = True
    gt = np.zeros_like(m)
    gt[0, 1:4, 1:4] = True
    gt[1, 0:2, 0:2] = True
    s = poc.score(m, [None] * 4, lab, gt)
    assert (s["tpr"], s["fpr"], s["hit"]) == (0.5, 0.5, 0.5)
    assert s["bal"] == 0.5
    err = poc.score(np.zeros_like(m), [None, None, "x", None], lab, gt)
    assert err["fpr"] == 0.5 and err["n_err"] == 1                       # 落ちた良品は NG(fail-closed)
    assert poc.status_of("ok", poc.score(np.zeros_like(m), [None] * 4, lab, gt)) == "flags_nothing"


def test_hand_and_existing_recipes_are_valid_region_chains(poc):
    assert poc.HAND and poc.EXISTING
    for task, st in poc.HAND.items():
        assert poc.validate(st) == ("ok", ""), task
    for name in poc.EXISTING:
        assert poc.validate(poc.existing_stages(name))[0] == "ok", name
