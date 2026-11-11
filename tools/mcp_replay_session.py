#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""MCP の道具を 1 回ずつ呼ぶ CLI(クラウドの LLM エージェントにレシピを組ませる用。条件の差は PoC の表 06 の注)。

One MCP tool call per invocation, for letting a cloud LLM agent build a recipe with the same MCP tools as the
local LLMs in ``tools/gen_ai_inspection_recipes.py``: the minimal MCP profile only, at most 24 tool calls, no
pixels, responses cut to the same length. What still differs (the agent can post-process the printed response
with its own commands, there are no nudges, the model's product name is not written) is listed in the PoC's
``CONDITION_GAPS``.

## なぜ要るか / Why

PoC ``poc_ai_built_inspection_scored`` は「手で組んだレシピ」と AI のレシピを並べるが、手のレシピは Fullseye の
内部を知った上で上限なしに組んだもので、AI と条件がそろっていない(2026-11-08、作者と独立の検証)。
そこで上位のクラウド LLM にも、ローカル LLM と同じ道具・同じ上限・同じ課題文だけで組ませ、別の列にする。

## 仕組み / How

呼ぶたびに MCP サーバ(stdio、minimal)を起こし、それまでの呼び出しを同じ順で再生してから新しい 1 回を実行する。
ハンドルは中身の SHA-256 から作られるので、再生すれば同じハンドルが同じ中身を指す。記録は ``--session`` の JSON。

使い方 / Usage::

    py -3.11 tools/mcp_replay_session.py --session S.json --init crack     # 課題文と道具の一覧を印字
    py -3.11 tools/mcp_replay_session.py --session S.json --tool fullseye_find_ops --args "{\\"query\\": \\"...\\"}"
    py -3.11 tools/mcp_replay_session.py --session S.json --final "{\\"stages\\": [...]}"
    # 終わった会話を PoC のレシピの記録へ足す(課題ごとに run 1..N、模型は一般名 cloud)
    py -3.11 tools/mcp_replay_session.py --import-into examples/data/ai_inspection_recipes_2026_11_08.json \\
        --phase cloud_v2 crack_1.json crack_2.json ...
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import gen_ai_inspection_recipes as gen  # noqa: E402
from tools import mcp_agent_eval as mae  # noqa: E402

MAX_CALLS = 24


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


#: クラウドの列の条件(記録に残す。模型は一般名、版・温度は非公開)と、エージェントに渡した依頼文(セッションの
#: パスだけを ``<session>`` に置き換えた全文)。依頼文は記録の prompts 表に SHA-256 で載る。
CLOUD_CONDITIONS = {
    "model": "cloud LLM (product name deliberately not written; the author knows the model id)",
    "temperature": "not exposed by the agent harness (agent default)",
    "harness": ("general-purpose coding agent in a fresh conversation, Bash only, driving this CLI; instructed not to "
                "read repository files, data files or images and not to search the web (compliance is self-reported); "
                "all six runs cut or parsed the printed CLI responses with their own commands (head -c, an inline "
                "JSON parse, grep; one saved responses and parsed them with its own script) — a breach of the brief"),
    "started_in_parallel": True,
    "nudges": "none (the local generator nudges once when the model answers without a trial run or without JSON)",
    "call_cap": "24, enforced per call by this CLI",
}
CLOUD_BRIEF = """You are taking part in a controlled experiment: build an image-inspection recipe using ONLY a restricted tool CLI, under exactly the same conditions as small local models were given. Fairness rules (strict):
- Use ONLY the Bash tool, and ONLY to run the CLI command shown below. Do NOT read, grep, glob or open any repository file, data file, image, or other session file. Do NOT use web search. Do not look at pixels. Everything you know about the data must come from the CLI's tool responses.
- At most 24 tool calls (the CLI enforces it). Then give the final answer with --final.

Setup (bash; run every command from this directory):
cd <worktree> && export FULLSEYE_CRACK_DATA="<data>" FULLSEYE_VISA_DATA="<data>" PYTHONUTF8=1

Start the session (prints the system instruction, the task in Japanese, and the JSON tool schemas — read them carefully; they are your whole brief):
py -3.11 tools/mcp_replay_session.py --session "<session>" --init <task>

Each tool call (one per command; the JSON arguments must follow the printed schema):
py -3.11 tools/mcp_replay_session.py --session "<same path>" --tool <tool_name> --args '<json object>'

Final answer (exactly once, JSON as the system instruction says):
py -3.11 tools/mcp_replay_session.py --session "<same path>" --final '{"stages": [...]}'

Handles (fullseye://img/...) stay valid across commands. Follow the system instruction and the task. When done, reply with one line: the final stages JSON and how many tool calls you used."""


def session_to_run(data: dict, run: int, phase: str) -> dict:
    """終わった会話 1 つを、生成道具の記録と同じ形の 1 回へ写す(レシピの出どころも同じ規則)。"""
    if data.get("final_text") is None:
        raise SystemExit("session has no final answer")
    calls = [{k: v for k, v in c.items() if k != "arguments"} for c in data["calls"]]
    recipe = gen.extract_recipe(data["final_text"])
    source = "final_json" if recipe else None
    if recipe is None:
        ok = [c for c in calls if c["tool"] == "fullseye_pipeline" and not c["is_error"] and c.get("stages")]
        if ok:
            recipe, source = ok[-1]["stages"], "last_pipeline"
    return {"task": data["task"], "model": "cloud", "run": run, "phase": phase,
            "assembler": "cloud LLM agent in a fresh conversation (separate column; not mixed with local LLMs)",
            "recipe": recipe, "recipe_source": source or "none", "n_tool_calls": len(calls), "calls": calls,
            "final_text": data["final_text"], "system_prompt_sha256": data["system_prompt_sha256"],
            "request_sha256": data["request_sha256"], "stop": "assistant_final",
            "started": data.get("started"), "finished": data.get("finished"), "max_steps": MAX_CALLS,
            "conditions": dict(CLOUD_CONDITIONS, brief_sha256=gen._sha(CLOUD_BRIEF))}


def import_sessions(target: Path, phase: str, sessions: list[str]) -> int:
    rec = json.loads(target.read_text(encoding="utf-8"))
    runs = [r for r in rec["runs"] if r.get("phase") != phase]
    k: dict = {}
    for sp in sessions:
        data = _load(Path(sp))
        k[data["task"]] = k.get(data["task"], 0) + 1
        runs.append(session_to_run(data, k[data["task"]], phase))
    rec["prompts"][gen._sha(gen.SYSTEM_PROMPT)] = gen.SYSTEM_PROMPT
    rec["prompts"][gen._sha(CLOUD_BRIEF)] = CLOUD_BRIEF
    rec["runs"] = sorted(runs, key=lambda r: (r.get("phase", ""), r["task"], r["model"], r["run"]))
    target.write_text(json.dumps(rec, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("imported %d sessions into phase %s" % (len(sessions), phase))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--session")
    ap.add_argument("--import-into", help="recipe record to add finished sessions to")
    ap.add_argument("--phase", default="cloud_v2")
    ap.add_argument("sessions", nargs="*")
    ap.add_argument("--init", help="task id: start a session and print the task and the tool list")
    ap.add_argument("--tool")
    ap.add_argument("--args", default="{}")
    ap.add_argument("--final", help='the final answer, {"stages": [...]}')
    a = ap.parse_args(argv)
    if a.import_into:
        return import_sessions(Path(a.import_into), a.phase, a.sessions)
    if not a.session:
        raise SystemExit("give --session (or --import-into)")
    path = Path(a.session)
    poc = gen.load_poc()
    if a.init:
        if path.exists():
            raise SystemExit("session already exists: %s" % path)
        if a.init not in poc.TASKS:
            raise SystemExit("unknown task: %s" % a.init)
        _save(path, {"task": a.init, "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
                     "system_prompt_sha256": gen._sha(gen.SYSTEM_PROMPT),
                     "request_sha256": gen._sha(poc.TASKS[a.init]["request"]), "calls": [], "final_text": None})
        print("=== system ===\n" + gen.SYSTEM_PROMPT + "\n\n=== user ===\n" + poc.TASKS[a.init]["request"])
    data = _load(path)
    if a.final is not None:
        if data.get("final_text") is not None:
            raise SystemExit("the final answer is already recorded")
        data["final_text"] = a.final
        data["recipe"] = gen.extract_recipe(a.final)
        data["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        _save(path, data)
        print("recorded; recipe %s" % ("parsed" if data["recipe"] else "NOT parsed"))
        return 0
    if data.get("final_text") is not None:
        raise SystemExit("the session is finished")
    if a.tool and len(data["calls"]) >= MAX_CALLS:
        raise SystemExit("the limit of %d tool calls is reached; give the final answer with --final" % MAX_CALLS)
    mae.MCP_EVAL_PROFILE = "minimal"
    with tempfile.TemporaryDirectory(prefix="aiscore_session_") as tmp:
        sandbox = Path(tmp)
        poc.write_dev_sandbox(sandbox)
        with mae.MCPClient(sandbox) as mcp:
            if a.init:
                tools = mae._openai_tools(mcp.tools())
                print("\n=== tools ===\n" + json.dumps(tools, ensure_ascii=False, indent=1))
                return 0
            if not a.tool:
                raise SystemExit("give --tool, --final or --init")
            for c in data["calls"]:                      # 再生(ハンドルは中身から決まるので同じになる)
                try:
                    mcp.call(c["tool"], c["arguments"])
                except Exception:                        # noqa: BLE001  失敗した呼び出しも同じ順で再生する
                    pass
            try:
                args = json.loads(a.args)
                if not isinstance(args, dict):
                    raise ValueError("arguments must be a JSON object")
                result = mcp.call(a.tool, args)
            except Exception as exc:                     # noqa: BLE001
                args = args if isinstance(locals().get("args"), dict) else {}
                result = {"isError": True, "content": [{"type": "text", "text": "%s: %s" % (type(exc).__name__, exc)}]}
            row = gen._summary(a.tool, args, result)
            row["arguments"] = args
            data["calls"].append(row)
            _save(path, data)
            print(mae._tool_payload(result))
            print("\n[call %d / %d]" % (len(data["calls"]), MAX_CALLS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
