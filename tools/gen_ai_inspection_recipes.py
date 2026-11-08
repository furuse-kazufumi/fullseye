#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ローカル LLM に Fullseye の MCP だけを渡して検査レシピを組ませ、レシピを JSON に保存する(手元専用)。

Let a local LLM build inspection recipes through Fullseye's MCP server only, and save them as JSON
(run by hand; CI never calls an LLM).

## なぜ要るか / Why

``examples/poc_ai_built_inspection_scored.py`` は「AI が組んだ検査を公開実データの真値で採点する」。
AI の出力は揺れるので、**AI を呼ぶのはこの道具だけ**にして、出てきたレシピを
``examples/data/ai_inspection_recipes_2026_11_08.json`` に固定する。PoC と CI はその JSON を
決定的に走らせて採点する(AI を呼ばない)。同じ課題で N 回作らせ、壊れたレシピも消さずに残す。

The PoC scores saved recipes deterministically; only this tool talks to an LLM. Every run is kept,
including runs that produced no recipe or a broken one.

## 経路 / Path

LLM → ローカル LLM サーバの chat API → tool 呼び出し → **Fullseye MCP サーバ(stdio、minimal
プロファイル)** → op の検索(fullseye_find_ops = RAG)・型の計画(fullseye_plan)・op カード・
開発用画像の読み込み・pipeline の試走。LLM は画素を見ない(MCP が返す数値統計だけを読む)。

## 所在を書かない / Never write the host

ローカル LLM の所在は環境変数 ``OLLAMA_HOST`` から読み、ログ・JSON・例外文には書かない
(例外文は ``$OLLAMA_HOST`` に置き換える)。未設定なら理由を出して止まる(fail-closed)。

使い方 / Usage::

    $env:OLLAMA_HOST = "<host:port>"        # 値はシェルにだけ置く
    py -3.11 tools/gen_ai_inspection_recipes.py --model <model> --phase <phase> --runs 10
    py -3.11 tools/gen_ai_inspection_recipes.py --model <model2> --phase <phase> --runs 10

## 文脈長 / Context length (2026-11-08、作者と独立の検証で見つかった)

最初の 40 回(段 ``v1``)は OpenAI 互換の口を使い、文脈長を渡していなかった。ローカル LLM サーバの既定(4,096、同時 8 本)で
1 要求あたりの prompt が 2,050〜3,680 トークンに頭打ちになり、課題文(開発用画像の名前)を含む古い発言が
捨てられていた疑いが強い(同じ口に 24k トークンの文を渡すと 2,050 トークンしか読まず、先頭の印を答えられない。
サーバ固有の口に ``num_ctx`` を渡すと 24,055 トークンを読んで答えられる。手元で実測)。いまはサーバ固有の
``/api/chat`` に ``options.num_ctx`` を渡し、要求ごとの prompt トークン数・``num_ctx``・サーバの版・模型の digest を
記録する。prompt が ``num_ctx`` の 9 割に届いた回は ``truncation_suspect`` の印を付ける(PoC の門が数える)。
段 ``v1`` の 40 回は消さずに残す(失敗の記録)。

## 模型の名前 / Model names

記録(JSON)には再現のために模型の名前と digest を残す。展示・記事・図・印字は PoC の ``model_label`` が
一般名(「ローカル LLM 14B」)にする —— 製品名を公開の文に出さない規則(HALCON 以外)に合わせる。

実データの場所は PoC と同じ環境変数(``FULLSEYE_CRACK_DATA`` / ``FULLSEYE_VISA_DATA``)。
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import mcp_agent_eval as mae  # noqa: E402  (MCPClient / tool-call normalisation)

POC_PATH = ROOT / "examples" / "poc_ai_built_inspection_scored.py"


def load_poc():
    """PoC を module として読む(課題文・開発用画像の選び方・JSON の置き場の正本は PoC 側)。"""
    spec = importlib.util.spec_from_file_location("poc_ai_built_inspection_scored", POC_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


SYSTEM_PROMPT = (
    "あなたは産業用画像検査のエンジニアです。道具は Fullseye の MCP ツールだけです。"
    "画素を直接見ることはできません。ツールが返す数値統計(平均・最大・前景の割合など)だけを根拠にしてください。"
    "手順: (1) fullseye_find_ops で課題に合う op を探す (2) fullseye_op_cards で引数を確かめる "
    "(3) fullseye_load_image で開発用の画像を読む (4) fullseye_pipeline で op の列を試し、"
    "欠陥のある画像では領域(region)が空でなく、良品の画像では空になるように op と引数を直す。"
    "完成したら、最後の答えとして JSON だけを返してください。形は "
    '{"stages": [{"op": "<op 名>", "a": <0..1>, "b": <0..1>}, ...]} です。'
    "a と b は段の直下に書いてください({\"op\": \"gaussian\", \"a\": 0.5})。\"params\" を使うのは、"
    "op カードの named_physical_parameters に載っている名前(例: sigma_px)を渡すときだけです。"
    "最後の段の出力は region(欠陥の画素)にしてください。"
)

NUDGE_EXECUTE = ("まだ fullseye_pipeline で開発用画像を試していません。fullseye_load_image で画像を読み、"
                 "fullseye_pipeline で op の列を試してから答えてください。")
NUDGE_JSON = ('最後の答えは JSON だけにしてください: {"stages": [{"op": ..., "a": ..., "b": ...}, ...]}。'
              "説明の文は不要です。")


class LocalChat:
    """ローカル LLM サーバ固有の chat API(``/api/chat``)。所在は ``OLLAMA_HOST`` からだけ読み、外へ書かない。

    ``num_ctx`` を毎回渡す(渡さないとサーバの既定で古い発言から黙って捨てられる)。
    The location comes only from ``OLLAMA_HOST``; ``num_ctx`` is sent on every request.
    """

    def __init__(self, model: str, temperature: float, max_tokens: int = 1500, num_ctx: int = 32768):
        host = os.environ.get("OLLAMA_HOST", "").strip()
        if not host:
            raise SystemExit("OLLAMA_HOST is not set (the local LLM endpoint is read only from the environment)")
        base = host.rstrip("/")
        if not re.match(r"^https?://", base, re.I):
            base = "http://" + base
        self._secret = host
        self._base = base
        self._url = base + "/api/chat"
        self.model, self.temperature, self.max_tokens = model, float(temperature), int(max_tokens)
        self.num_ctx = int(num_ctx)

    def secrets(self) -> list[str]:
        """記録に現れてはならない文字列(環境変数の値と、そのホストの部分)。"""
        host = re.sub(r"^https?://", "", self._secret, flags=re.I).rstrip("/")
        out = {self._secret, host, host.split(":")[0]}
        return sorted(x for x in out if len(x) >= 3)

    def server_info(self) -> dict:
        """サーバの版と模型の digest(所在は含めない)。"""
        info = {"server": "local-llm-server", "num_ctx": self.num_ctx}
        try:
            with urllib.request.urlopen(self._base + "/api/version", timeout=30) as resp:
                info["server_version"] = json.loads(resp.read()).get("version")
            with urllib.request.urlopen(self._base + "/api/tags", timeout=30) as resp:
                tags = json.loads(resp.read()).get("models") or []
            info["model_digest"] = next((t.get("digest") for t in tags if t.get("name") == self.model), None)
        except Exception as exc:                                      # noqa: BLE001
            raise RuntimeError(self.safe("server info failed: %s: %s" % (type(exc).__name__, exc))) from None
        if not info.get("model_digest"):
            raise RuntimeError("model %r is not on the server" % self.model)
        return info

    def safe(self, text: str) -> str:
        return mae._secret_safe(text, self._secret)

    def complete(self, messages, tools, seed: int) -> dict:
        payload = {"model": self.model, "messages": messages, "tools": tools, "stream": False,
                   "options": {"num_ctx": self.num_ctx, "temperature": self.temperature, "seed": int(seed),
                               "num_predict": self.max_tokens}}
        req = urllib.request.Request(self._url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            body = exc.read(2000).decode("utf-8", "replace")
            raise RuntimeError(self.safe("LLM HTTP %d: %s" % (exc.code, body))) from None
        except Exception as exc:                                      # noqa: BLE001
            raise RuntimeError(self.safe("LLM request failed: %s: %s" % (type(exc).__name__, exc))) from None


_JSON_BLOCK = re.compile(r"\{.*\}", re.S)


def extract_recipe(text: str) -> list[dict] | None:
    """最後の答えの文から ``{"stages": [...]}`` を取り出す。取れなければ None(推測で補わない)。"""
    if not isinstance(text, str):
        return None
    s = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", s, re.S | re.I)
    if m:
        s = m.group(1)
    cands = [s] + [mm.group(0) for mm in _JSON_BLOCK.finditer(s)]
    for c in cands:
        try:
            obj = json.loads(c)
        except (TypeError, ValueError):
            continue
        stages = obj.get("stages") if isinstance(obj, dict) else obj if isinstance(obj, list) else None
        if isinstance(stages, list) and stages and all(isinstance(x, dict) and isinstance(x.get("op"), str)
                                                       for x in stages):
            return [normalize_stage(x) for x in stages]
    return None


def normalize_stage(st: dict) -> dict:
    """保存する段の形に揃える(op / a / b / params だけ。値は JSON のまま、範囲の検査は採点側の MCP 検証)。"""
    out: dict[str, Any] = {"op": str(st["op"])}
    for k in ("a", "b"):
        if k in st:
            out[k] = st[k]
    if isinstance(st.get("params"), dict) and st["params"]:
        out["params"] = st["params"]
    return out


def text_tool_calls(content, allowed: set) -> list[dict]:
    """本文に文字で書かれた tool 呼び出し(``{"name": ..., "arguments": {...}}``)を拾う。

    ローカルの模型は tool 呼び出しを API の欄でなく本文(前置きの文つき)に書くことがある。拾った回数は
    ``text_tool_calls`` として記録に残す(模型の癖を道具の側で黙って直したことを隠さない)。
    """
    if not isinstance(content, str) or "{" not in content:
        return []
    dec = json.JSONDecoder()
    calls, i = [], content.find("{")
    while 0 <= i < len(content):
        try:
            obj, end = dec.raw_decode(content, i)
        except ValueError:
            i = content.find("{", i + 1)
            continue
        if isinstance(obj, dict) and obj.get("name") in allowed and isinstance(obj.get("arguments", {}), dict):
            calls.append({"id": "text_call_%d" % len(calls), "type": "function",
                          "function": {"name": obj["name"], "arguments": obj.get("arguments", {})}})
        i = content.find("{", end)
    return calls


def _summary(name: str, args: dict, result: dict) -> dict:
    """1 回の tool 呼び出しの要約(JSON に残す分。全文は残さない)。"""
    row: dict[str, Any] = {"tool": name, "is_error": bool(result.get("isError"))}
    if name == "fullseye_pipeline" and isinstance(args.get("stages"), list):
        row["stages"] = [normalize_stage(s) for s in args["stages"] if isinstance(s, dict) and "op" in s]
        sc = result.get("structuredContent") or {}
        row["out_sort"] = sc.get("out_sort")
    elif name in ("fullseye_find_ops",):
        row["query"] = args.get("query")
        sc = result.get("structuredContent") or {}
        row["found"] = [o.get("name") for o in (sc.get("ops") or [])][:8]
    elif name == "fullseye_op_cards":
        row["names"] = args.get("names")
    elif name == "fullseye_load_image":
        row["path"] = os.path.basename(str(args.get("path", "")))
    if row["is_error"]:
        txt = json.dumps(result.get("structuredContent") or result.get("content"), ensure_ascii=False)
        row["error"] = txt[:300]
    return row


def run_once(chat: LocalChat, task: dict, sandbox: Path, seed: int, max_steps: int) -> dict:
    """1 回分: LLM と MCP を往復させ、最後の答えからレシピを取り出す。"""
    mae.MCP_EVAL_PROFILE = "minimal"
    t0 = time.perf_counter()
    calls: list[dict] = []
    tokens = {"prompt_tokens": 0, "completion_tokens": 0}
    per_turn: list[int] = []
    final_text, stop, nudges = "", "assistant_final", []
    with mae.MCPClient(sandbox) as mcp:
        schemas = mae._openai_tools(mcp.tools())
        allowed = {t["function"]["name"] for t in schemas}
        messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": task["request"]}]
        llm_turns = 0
        n_text_calls = 0
        while True:
            if len(calls) >= max_steps or llm_turns >= max_steps + 6:
                stop = "max_steps"
                break
            try:
                resp = chat.complete(messages, schemas, seed=seed + llm_turns)
            except RuntimeError as exc:
                stop, final_text = "llm_error", str(exc)[:300]
                break
            llm_turns += 1
            pt, ct = int(resp.get("prompt_eval_count") or 0), int(resp.get("eval_count") or 0)
            tokens["prompt_tokens"] += pt
            tokens["completion_tokens"] += ct
            per_turn.append(pt)
            msg = resp.get("message") or {}
            tcs = msg.get("tool_calls") or []
            if not tcs:
                tcs = text_tool_calls(msg.get("content"), allowed)
                n_text_calls += len(tcs)
            if not tcs:
                final_text = str(msg.get("content") or "")
                ran = any(c["tool"] == "fullseye_pipeline" and not c["is_error"] for c in calls)
                if not ran and "execute" not in nudges:
                    nudges.append("execute")
                    messages += [{"role": "assistant", "content": final_text},
                                 {"role": "user", "content": NUDGE_EXECUTE}]
                    continue
                if extract_recipe(final_text) is None and "json" not in nudges:
                    nudges.append("json")
                    messages += [{"role": "assistant", "content": final_text},
                                 {"role": "user", "content": NUDGE_JSON}]
                    continue
                break
            norm = []
            for c in tcs:
                fn = c.get("function") or {}
                a = fn.get("arguments", {})
                norm.append({"function": {"name": str(fn.get("name", "")), "arguments": a}})
            # サーバ固有の口は arguments を JSON の object で受ける(文字列で返ってきた分は読めたときだけ戻す)
            sent = []
            for c in norm:
                a = c["function"]["arguments"]
                if isinstance(a, str):
                    try:
                        a = json.loads(a)
                    except ValueError:
                        a = {}
                sent.append({"function": {"name": c["function"]["name"], "arguments": a if isinstance(a, dict) else {}}})
            messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": sent})
            for c in norm:
                if len(calls) >= max_steps:          # ★呼び出し単位で上限を守る(発言の途中でも打ち切る、2026-11-08)
                    stop = "max_steps"
                    break
                name, enc = c["function"]["name"], c["function"]["arguments"]
                args = {}
                try:
                    args = enc if isinstance(enc, dict) else (json.loads(enc) if enc else {})
                    if not isinstance(args, dict):
                        args = {}
                        raise ValueError("tool arguments are not an object")
                    result = mcp.call(name, args)
                except Exception as exc:                              # noqa: BLE001
                    result = {"isError": True, "content": [{"type": "text", "text": chat.safe(
                        "%s: %s" % (type(exc).__name__, exc))}]}
                calls.append(_summary(name, args, result))
                messages.append({"role": "tool", "tool_name": name, "content": mae._tool_payload(result)})
    recipe = extract_recipe(final_text)
    source = "final_json" if recipe else None
    if recipe is None:                                  # 最後に成功した試走の段を使う(そう記録する)
        ok = [c for c in calls if c["tool"] == "fullseye_pipeline" and not c["is_error"] and c.get("stages")]
        if ok:
            recipe, source = ok[-1]["stages"], "last_pipeline"
    peak = max(per_turn) if per_turn else 0
    return {"seed": seed, "stop": stop, "nudges": nudges, "recipe": recipe, "recipe_source": source or "none",
            "n_tool_calls": len(calls), "n_llm_turns": llm_turns, "text_tool_calls": n_text_calls, "tokens": tokens,
            "prompt_tokens_per_turn": per_turn, "num_ctx": chat.num_ctx,
            "truncation_suspect": bool(peak >= 0.9 * chat.num_ctx),
            "elapsed_s": round(time.perf_counter() - t0, 1), "calls": calls,
            "final_text": chat.safe(final_text)}


NOTE = ("Recipes written by a local LLM (and, in separate phases, other assemblers) through the Fullseye MCP "
        "server (tools/gen_ai_inspection_recipes.py). Every run is kept, including runs with no recipe. The LLM "
        "endpoint is not recorded. Model names and digests are kept here for reproducibility only; public text "
        "(captions, figures, printed output) uses generic labels.")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--model", required=True, help="local model name as the server lists it")
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--task", action="append", help="task id (default: all)")
    ap.add_argument("--phase", required=True,
                    help="name of this batch (e.g. v2_ctx32k / v3_mcpfix); runs of other phases are kept")
    ap.add_argument("--num-ctx", type=int, default=32768, help="context length sent with every request")
    ap.add_argument("--only-run", type=int,
                    help="redo just this run number (same seed) and keep the others; used when a run was "
                         "marked truncation_suspect and is redone with a larger --num-ctx")
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--max-steps", type=int, default=20)
    ap.add_argument("--seed0", type=int, default=1000)
    ap.add_argument("--out", help="JSON path (default: the PoC's recipe file)")
    ap.add_argument("--gpu-lock", default=os.environ.get("FULLSEYE_GPU_LOCK"),
                    help="GPU lock file (tools/gpu_auto_sweep.GpuLock); default $FULLSEYE_GPU_LOCK")
    a = ap.parse_args(argv)
    poc = load_poc()
    out = Path(a.out) if a.out else poc.RECIPES_JSON
    chat = LocalChat(a.model, a.temperature, num_ctx=a.num_ctx)
    info = chat.server_info()
    tasks = [t for t in poc.TASKS if not a.task or t in a.task]
    data = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    runs = [r for r in data.get("runs", [])
            if not (r["model"] == a.model and r["task"] in tasks and r.get("phase") == a.phase
                    and (a.only_run is None or r["run"] == a.only_run))]
    prompts = dict(data.get("prompts") or {})
    sys_sha = _sha(SYSTEM_PROMPT)
    prompts[sys_sha] = SYSTEM_PROMPT
    for t in poc.TASKS:
        prompts[_sha(poc.TASKS[t]["request"])] = poc.TASKS[t]["request"]
    lock = None
    if a.gpu_lock:
        from tools.gpu_auto_sweep import GpuLock
        lock = GpuLock(a.gpu_lock, "aiscore-llm", max_hold=6 * 3600)
        if not lock.acquire(max_wait=3600):
            raise SystemExit("GPU lock is held by someone else; not starting")
    try:
        with tempfile.TemporaryDirectory(prefix="aiscore_sandbox_") as tmp:
            sandbox = Path(tmp)
            poc.write_dev_sandbox(sandbox)
            for tid in tasks:
                for k in range(a.runs):
                    if a.only_run is not None and k + 1 != a.only_run:
                        continue
                    seed = a.seed0 + 97 * k
                    r = run_once(chat, poc.TASKS[tid], sandbox, seed, a.max_steps)
                    r.update({"task": tid, "model": a.model, "run": k + 1, "phase": a.phase,
                              "temperature": a.temperature, "max_steps": a.max_steps,
                              "system_prompt_sha256": sys_sha, "request_sha256": _sha(poc.TASKS[tid]["request"]),
                              "server_version": info["server_version"], "model_digest": info["model_digest"]})
                    runs.append(r)
                    print("%s %s %s run %d: %s (%s), %d calls, peak prompt %d / %d, %.0f s" % (
                        a.phase, tid, a.model, k + 1, "recipe" if r["recipe"] else "NO RECIPE", r["recipe_source"],
                        r["n_tool_calls"], max(r["prompt_tokens_per_turn"] or [0]), a.num_ctx, r["elapsed_s"]),
                        flush=True)
                    payload = dict(data)
                    payload.update({
                        "_note": NOTE, "generated": time.strftime("%Y-%m-%d"), "mcp_profile": "minimal",
                        "prompts": dict(sorted(prompts.items())),
                        "runs": sorted(runs, key=lambda r: (r.get("phase", ""), r["task"], r["model"], r["run"])),
                    })
                    text = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
                    leaked = [x for x in chat.secrets() if x in text]
                    if leaked:                                   # 所在を書かない(fail-closed)。値は印字しない
                        raise SystemExit("refusing to write: the record would contain the LLM location")
                    out.write_text(text, encoding="utf-8")
    finally:
        if lock is not None:
            lock.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
