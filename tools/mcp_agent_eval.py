#!/usr/bin/env python3
"""Run deterministic Fullseye MCP tasks with a local Ollama agent.

The CPU side (input synthesis, MCP transport, judging, aggregation) is
deterministic.  Only the chat-completion calls are non-deterministic.  The
server is always exercised through its stdio JSON-RPC interface; importing its
``call_tool`` function here would turn this into a unit benchmark instead of an
end-to-end one.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASKS = ROOT / "docs" / "ops" / "mcp_agent_tasks.json"
CATEGORIES = ("general", "positioning", "multi_product", "specular_transparent", "fast_3d")


def load_tasks(path: str | Path = DEFAULT_TASKS) -> dict[str, Any]:
    """Load and strictly validate the hand-written task source."""
    source = Path(path)
    data = json.loads(source.read_text(encoding="utf-8"))
    if data.get("version") != 1:
        raise ValueError("task version must be 1")
    tasks = data.get("tasks")
    if not isinstance(tasks, list) or len(tasks) < 20:
        raise ValueError("tasks must contain at least 20 entries")
    if tuple(data.get("categories", ())) != CATEGORIES:
        raise ValueError("categories must match the five rag_benchmark categories")
    ids: set[str] = set()
    counts: Counter[str] = Counter()
    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            raise ValueError(f"tasks[{index}] must be an object")
        required = {"id", "category", "request", "input", "judge"}
        missing = required - set(task)
        extra = set(task) - required
        if missing or extra:
            raise ValueError(f"tasks[{index}] fields: missing={sorted(missing)} extra={sorted(extra)}")
        task_id = task["id"]
        if not isinstance(task_id, str) or not re.fullmatch(r"[a-z0-9_]+", task_id):
            raise ValueError(f"invalid task id: {task_id!r}")
        if task_id in ids:
            raise ValueError(f"duplicate task id: {task_id}")
        ids.add(task_id)
        category = task["category"]
        if category not in CATEGORIES:
            raise ValueError(f"unknown category: {category!r}")
        counts[category] += 1
        if not isinstance(task["request"], str) or not task["request"].strip():
            raise ValueError(f"empty request: {task_id}")
        spec = task["input"]
        if (not isinstance(spec, dict) or set(spec) != {"generator", "params"}
                or spec.get("generator") not in GENERATORS or not isinstance(spec.get("params"), dict)):
            raise ValueError(f"invalid input generator: {task_id}")
        if task["judge"] not in JUDGES:
            raise ValueError(f"unknown judge: {task['judge']!r}")
    if any(counts[category] < 4 for category in CATEGORIES):
        raise ValueError(f"each category needs at least four tasks: {dict(counts)}")
    return data


@dataclass(frozen=True)
class PreparedInput:
    files: tuple[str, ...]
    roles: tuple[str, ...]
    stack_sort: str | None
    truth: dict[str, Any]
    sha256: tuple[str, ...]

    def prompt(self) -> str:
        rows = [f"- {name}: {role}" for name, role in zip(self.files, self.roles)]
        stack = f"\n画像列として読む場合の種別: {self.stack_sort}" if self.stack_sort else ""
        return "入力ファイル:\n" + "\n".join(rows) + stack


def _save_arrays(task_id: str, root: Path, arrays: list[np.ndarray], roles: list[str],
                 *, stack_sort: str | None, truth: dict[str, Any]) -> PreparedInput:
    root.mkdir(parents=True, exist_ok=True)
    names: list[str] = []
    digests: list[str] = []
    for index, array in enumerate(arrays):
        name = f"{task_id}_{index:02d}.npy"
        path = root / name
        np.save(path, np.asarray(array), allow_pickle=False)
        names.append(name)
        digests.append(hashlib.sha256(path.read_bytes()).hexdigest())
    return PreparedInput(tuple(names), tuple(roles), stack_sort, truth, tuple(digests))


def _binary_components(task_id: str, root: Path, p: dict[str, Any]) -> PreparedInput:
    count = int(p["count"])
    rng = np.random.default_rng(int(p["seed"]))
    image = np.full((96, 96), 0.06, dtype=np.float64)
    slots = ((12, 12), (51, 10), (21, 42), (60, 47), (36, 70), (72, 72))
    for index, (x, y) in enumerate(slots[:count]):
        width = 10 + index % 3
        height = 9 + (index + 1) % 3
        image[y:y + height, x:x + width] = 0.88
    image += rng.normal(0.0, 0.006, image.shape)
    image = np.clip(image, 0.0, 1.0)
    return _save_arrays(task_id, root, [image], ["検査画像"], stack_sort=None,
                        truth={"count": count})


def _binary_rectangle(task_id: str, root: Path, p: dict[str, Any]) -> PreparedInput:
    image = np.full((96, 96), 0.08, dtype=np.float64)
    x, y, width, height = (int(p[k]) for k in ("x", "y", "width", "height"))
    image[y:y + height, x:x + width] = 0.92
    fraction = float(width * height / image.size)
    return _save_arrays(task_id, root, [image], ["検査画像"], stack_sort=None,
                        truth={"fraction": fraction})


def _noisy_gradient(task_id: str, root: Path, p: dict[str, Any]) -> PreparedInput:
    rng = np.random.default_rng(int(p["seed"]))
    x = np.linspace(0.25, 0.75, 96, dtype=np.float64)
    clean = np.repeat(x[None, :], 96, axis=0)
    image = np.clip(clean + rng.normal(0.0, float(p["sigma"]), clean.shape), 0.0, 1.0)
    return _save_arrays(task_id, root, [image], ["ノイズを含む検査画像"], stack_sort=None,
                        truth={"input_std": float(image.std()), "max_std": float(image.std() * 0.92)})


def _corner_grid(task_id: str, root: Path, p: dict[str, Any]) -> PreparedInput:
    cells, margin = int(p["cells"]), int(p["margin"])
    image = np.full((96, 96), 0.08, dtype=np.float64)
    usable = 96 - 2 * margin
    step = max(5, usable // cells)
    block = max(3, step // 2)
    for row in range(cells):
        for col in range(cells):
            if (row + col) % 2 == 0:
                y, x = margin + row * step, margin + col * step
                image[y:y + block, x:x + block] = 0.92
    return _save_arrays(task_id, root, [image], ["位置合わせ画像"], stack_sort=None,
                        truth={"min_features": max(4, cells)})


def _template_scene(task_id: str, root: Path, p: dict[str, Any]) -> PreparedInput:
    x, y, rotation = int(p["x"]), int(p["y"]), int(p["rotation"])
    template = np.full((17, 17), 0.08, dtype=np.float64)
    template[3:14, 3:7] = 0.92
    template[10:14, 3:14] = 0.92
    turns = (rotation // 90) % 4
    placed = np.rot90(template, turns)
    scene = np.full((96, 96), 0.08, dtype=np.float64)
    half = placed.shape[0] // 2
    scene[y - half:y - half + placed.shape[0], x - half:x - half + placed.shape[1]] = placed
    return _save_arrays(task_id, root, [scene, template],
                        ["探索対象のシーン", "登録済みの見本画像"], stack_sort=None,
                        truth={"x": x, "y": y, "rotation": rotation, "position_tolerance": 3.0})


def _polar_sweep(task_id: str, root: Path, p: dict[str, Any]) -> PreparedInput:
    diffuse, specular = float(p["diffuse"]), float(p["specular"])
    azimuth = float(p["azimuth"])
    yy, xx = np.mgrid[:64, :64]
    texture = 0.88 + 0.12 * (xx + yy) / 126.0
    d = diffuse * texture
    s = specular * texture
    angles = (0.0, 45.0, 90.0, 135.0)
    frames = [0.5 * d + s * np.cos(np.radians(angle - azimuth)) ** 2 for angle in angles]
    target = float(np.mean(s / (d + s)))
    roles = [f"偏光角 {int(angle)} 度" for angle in angles]
    return _save_arrays(task_id, root, frames, roles, stack_sort="polsweep",
                        truth={"mean": target, "tolerance": 2e-3})


def _fringe_sweep(task_id: str, root: Path, p: dict[str, Any]) -> PreparedInput:
    lo, hi = float(p["phase_min"]), float(p["phase_max"])
    ramp = np.linspace(lo, hi, 72, dtype=np.float64)
    phase = np.repeat(ramp[None, :], 64, axis=0) if p["axis"] == "x" else np.repeat(ramp[:, None], 64, axis=1)
    deltas = np.arange(4, dtype=np.float64) * (2.0 * np.pi / 4.0)
    frames = [0.5 + 0.34 * np.cos(phase - delta) for delta in deltas]
    roles = [f"位相シフト {index}/4 周期" for index in range(4)]
    return _save_arrays(task_id, root, frames, roles, stack_sort="seq<image>",
                        truth={"mean": float(phase.mean()), "tolerance": 3e-2})


GENERATORS: dict[str, Callable[[str, Path, dict[str, Any]], PreparedInput]] = {
    "binary_components": _binary_components,
    "binary_rectangle": _binary_rectangle,
    "noisy_gradient": _noisy_gradient,
    "corner_grid": _corner_grid,
    "template_scene": _template_scene,
    "polar_sweep": _polar_sweep,
    "fringe_sweep": _fringe_sweep,
}


def generate_task_input(task: dict[str, Any], root: str | Path) -> PreparedInput:
    spec = task["input"]
    return GENERATORS[spec["generator"]](task["id"], Path(root), dict(spec["params"]))


def _structured(event: dict[str, Any]) -> dict[str, Any]:
    result = event.get("result") or {}
    value = result.get("structuredContent") if isinstance(result, dict) else None
    return value if isinstance(value, dict) else {}


def _records(events: list[dict[str, Any]], names: set[str]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for event in events:
        if event.get("tool") not in {"fullseye_apply", "fullseye_pipeline"}:
            continue
        structured = _structured(event)
        candidates = structured.get("stages") if isinstance(structured.get("stages"), list) else [structured]
        for record in candidates:
            if (isinstance(record, dict) and record.get("op") in names
                    and record.get("status", "ok") == "ok" and "error" not in record):
                found.append(record)
    return found


def _metric(record: dict[str, Any], key: str) -> float | None:
    value = record.get("value") if key == "value" else (record.get("stats") or {}).get(key)
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return None


def _answer(passed: bool, metric: Any, expected: Any, detail: str) -> dict[str, Any]:
    return {"passed": bool(passed), "metric": metric, "expected": expected, "detail": detail}


def judge_component_count(task: dict[str, Any], prepared: PreparedInput,
                          events: list[dict[str, Any]]) -> dict[str, Any]:
    records = _records(events, {"count_obj"})
    value = _metric(records[-1], "value") if records else None
    expected = int(prepared.truth["count"])
    return _answer(value is not None and int(round(value)) == expected, value, expected,
                   "独立領域数")


def judge_region_fraction(task: dict[str, Any], prepared: PreparedInput,
                          events: list[dict[str, Any]]) -> dict[str, Any]:
    records = _records(events, {"otsu", "cv_otsu", "sk_otsu"})
    value = _metric(records[-1], "mean") if records else None
    expected = float(prepared.truth["fraction"])
    return _answer(value is not None and abs(value - expected) <= 0.015, value, expected,
                   "二値領域の占有率")


def judge_smoothed_std(task: dict[str, Any], prepared: PreparedInput,
                       events: list[dict[str, Any]]) -> dict[str, Any]:
    records = _records(events, {"gaussian", "cv_gaussian"})
    value = _metric(records[-1], "std") if records else None
    expected = float(prepared.truth["max_std"])
    return _answer(value is not None and value < expected, value, {"less_than": expected},
                   "平滑化後の標準偏差")


def judge_feature_count(task: dict[str, Any], prepared: PreparedInput,
                        events: list[dict[str, Any]]) -> dict[str, Any]:
    records = _records(events, {"cv_good_features"})
    value: float | None = None
    if records:
        value = _metric(records[-1], "value")
        stats = records[-1].get("stats") or {}
        shape = stats.get("shape")
        if value is None and isinstance(shape, list) and shape:
            value = float(shape[0])
        elif value is None and isinstance(stats.get("size"), int):
            value = float(stats["size"])
    expected = int(prepared.truth["min_features"])
    return _answer(value is not None and value >= expected, value, {"at_least": expected},
                   "抽出特徴点数")


def _flatten_numbers(value: Any) -> list[float]:
    out: list[float] = []
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        out.append(float(value))
    elif isinstance(value, dict):
        for item in value.values():
            out.extend(_flatten_numbers(item))
    elif isinstance(value, list):
        for item in value:
            out.extend(_flatten_numbers(item))
    return out


def judge_match_position(task: dict[str, Any], prepared: PreparedInput,
                         events: list[dict[str, Any]]) -> dict[str, Any]:
    records = _records(events, {"ncc_locate", "shape_locate"})
    numbers = _flatten_numbers(records[-1].get("value")) if records else []
    expected = {"y": prepared.truth["y"], "x": prepared.truth["x"]}
    metric: dict[str, float] | None = None
    passed = False
    # ncc: [score,y,x], shape: [score,y,x,angle].
    if len(numbers) >= 3:
        metric = {"score": numbers[0], "y": numbers[1], "x": numbers[2]}
        tol = float(prepared.truth["position_tolerance"])
        passed = (numbers[0] > 0.5 and abs(numbers[1] - expected["y"]) <= tol
                  and abs(numbers[2] - expected["x"]) <= tol)
    return _answer(passed, metric, expected, "登録見本の一致位置")


def _judge_mean(events: list[dict[str, Any]], names: set[str], prepared: PreparedInput,
                label: str) -> dict[str, Any]:
    records = _records(events, names)
    value = _metric(records[-1], "mean") if records else None
    expected = float(prepared.truth["mean"])
    tolerance = float(prepared.truth["tolerance"])
    return _answer(value is not None and abs(value - expected) <= tolerance, value,
                   {"value": expected, "tolerance": tolerance}, label)


def judge_dolp_mean(task: dict[str, Any], prepared: PreparedInput,
                    events: list[dict[str, Any]]) -> dict[str, Any]:
    return _judge_mean(events, {"polarization_dolp_map"}, prepared, "線偏光度の平均")


def judge_phase_mean(task: dict[str, Any], prepared: PreparedInput,
                     events: list[dict[str, Any]]) -> dict[str, Any]:
    return _judge_mean(events, {"wrapped_phase"}, prepared, "ラップ位相の平均")


def judge_depth_mean(task: dict[str, Any], prepared: PreparedInput,
                     events: list[dict[str, Any]]) -> dict[str, Any]:
    return _judge_mean(events, {"decode_fringe"}, prepared, "復元高さの平均")


JUDGES: dict[str, Callable[[dict[str, Any], PreparedInput, list[dict[str, Any]]], dict[str, Any]]] = {
    fn.__name__: fn for fn in (
        judge_component_count, judge_region_fraction, judge_smoothed_std,
        judge_feature_count, judge_match_position, judge_dolp_mean,
        judge_phase_mean, judge_depth_mean,
    )
}


def judge_task(task: dict[str, Any], prepared: PreparedInput,
               events: list[dict[str, Any]]) -> dict[str, Any]:
    return JUDGES[task["judge"]](task, prepared, events)


class MCPError(RuntimeError):
    pass


class MCPClient:
    """Small synchronous client for the server's Content-Length transport."""

    def __init__(self, input_root: Path):
        env = dict(os.environ)
        env.update({"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
                    "FULLSEYE_MCP_ROOT": str(input_root), "FULLSEYE_MCP_PROFILE": "minimal"})
        self.process = subprocess.Popen(
            [sys.executable, "-m", "fullseye.mcp"], cwd=ROOT, env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        self.sequence = 0
        self.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                     "clientInfo": {"name": "mcp-agent-eval", "version": "1"}})

    def _write(self, message: dict[str, Any]) -> None:
        assert self.process.stdin is not None
        body = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.process.stdin.write(b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n\r\n" + body)
        self.process.stdin.flush()

    def _read(self) -> dict[str, Any]:
        assert self.process.stdout is not None
        headers: dict[bytes, bytes] = {}
        while True:
            line = self.process.stdout.readline()
            if not line:
                raise MCPError("MCP server closed its output")
            if not line.strip():
                break
            key, separator, value = line.partition(b":")
            if separator:
                headers[key.strip().lower()] = value.strip()
        if b"content-length" not in headers:
            raise MCPError("MCP response has no Content-Length")
        body = self.process.stdout.read(int(headers[b"content-length"]))
        return json.loads(body)

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self.sequence += 1
        self._write({"jsonrpc": "2.0", "id": self.sequence, "method": method, "params": params})
        response = self._read()
        if response.get("id") != self.sequence:
            raise MCPError("MCP response id mismatch")
        if "error" in response:
            error = response["error"]
            raise MCPError(f"{error.get('code')}: {error.get('message')}")
        return response["result"]

    def tools(self) -> list[dict[str, Any]]:
        return self.request("tools/list", {})["tools"]

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.request("tools/call", {"name": name, "arguments": arguments})

    def close(self) -> None:
        if self.process.stdin and not self.process.stdin.closed:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=15)

    def __enter__(self) -> "MCPClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _secret_safe(text: str, secret: str | None) -> str:
    return text.replace(secret, "$OLLAMA_HOST") if secret else text


class OllamaChat:
    def __init__(self, model: str):
        host = os.environ.get("OLLAMA_HOST")
        if not host:
            raise RuntimeError("OLLAMA_HOST is not set")
        base = host.rstrip("/")
        if not re.match(r"^https?://", base, re.I):
            base = "http://" + base
        self._secret = host
        self._url = base + "/v1/chat/completions"
        self.model = model

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        payload = {"model": self.model, "messages": messages, "tools": tools,
                   "tool_choice": "auto", "temperature": 0.1, "max_tokens": 1024,
                   "stream": False}
        request = urllib.request.Request(
            self._url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            body = exc.read(2000).decode("utf-8", "replace")
            raise RuntimeError(_secret_safe(f"Ollama HTTP {exc.code}: {body}", self._secret)) from None
        except Exception as exc:
            raise RuntimeError(_secret_safe(f"Ollama request failed: {type(exc).__name__}: {exc}", self._secret)) from None


def available_models() -> list[str]:
    """Return names from ``ollama list`` without ever returning connection metadata."""
    host = os.environ.get("OLLAMA_HOST")
    completed = subprocess.run(["ollama", "list"], cwd=ROOT, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=60, check=False)
    if completed.returncode:
        raise RuntimeError(_secret_safe("ollama list failed: " + completed.stderr.strip(), host))
    lines = [line.split() for line in completed.stdout.splitlines()[1:] if line.split()]
    return [parts[0] for parts in lines]


def choose_model(models: list[str]) -> str:
    if not models:
        raise RuntimeError("ollama list returned no models")

    def score(name: str) -> tuple[int, int, int]:
        lower = name.lower()
        match = re.search(r"(?<!\d)(\d+(?:\.\d+)?)b", lower)
        size = float(match.group(1)) if match else 0.0
        in_range = 14.0 <= size <= 32.0
        instruction_family = any(token in lower for token in ("qwen", "llama", "mistral"))
        # Prefer 14–32B instruction/tool-capable families, then the larger one.
        return int(in_range), int(instruction_family), int(size * 10)

    return max(models, key=score)


SYSTEM_PROMPT = """あなたは画像処理の実行エージェントです。与えられた課題は必ず Fullseye MCP ツールだけで解いてください。画素を直接見たふりや、値の推測をしてはいけません。業務用語から候補を検索し、必要なら型付き計画や短い op カードを確認し、入力を読み、処理を実行してください。検索結果の説明や実行用コードを書くだけでは未完了です。必ず MCP の実行ツールを呼び、依頼された最終数値がツール応答に現れるまで最終回答を返さないでください。失敗した呼び出しは理由を読んで修正してください。最終回答は短い日本語と数値にしてください。"""


def _openai_tools(mcp_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"type": "function", "function": {"name": tool["name"],
            "description": tool.get("description", ""), "parameters": tool["inputSchema"]}}
            for tool in mcp_tools]


def _tool_payload(result: dict[str, Any]) -> str:
    compact = {key: result[key] for key in ("content", "structuredContent", "isError") if key in result}
    text = json.dumps(compact, ensure_ascii=False, separators=(",", ":"), default=str)
    if len(text) > 30000:
        text = text[:30000] + "…(response truncated by evaluator)"
    return text


def _content_tool_calls(message: dict[str, Any], allowed: set[str]) -> list[dict[str, Any]]:
    """Normalize the strict JSON tool form some Ollama templates put in content."""
    content = message.get("content")
    if not isinstance(content, str):
        return []
    text = content.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.I | re.S)
    if fenced:
        text = fenced.group(1)
    try:
        decoded = json.loads(text)
    except (TypeError, ValueError):
        return []
    rows = decoded if isinstance(decoded, list) else [decoded]
    calls = []
    for row in rows:
        if not isinstance(row, dict) or row.get("name") not in allowed:
            return []
        arguments = row.get("arguments", {})
        if not isinstance(arguments, dict):
            return []
        calls.append({"id": f"content_call_{len(calls)}", "type": "function",
                      "function": {"name": row["name"], "arguments": arguments}})
    return calls


def _failure_reason(message: str) -> str:
    lower = message.lower()
    if any(token in lower for token in ("unknown_op", "知らない op", "ではない: ", "not_executable")):
        return "unknown_op"
    if any(token in lower for token in ("sort_mismatch", "型の不一致", "type mismatch", "in_sort")):
        return "type_mismatch"
    if any(token in lower for token in ("minimum", "maximum", "最小値", "最大値", "範囲外")):
        return "out_of_range"
    if any(token in lower for token in ("余計なキー", "additional", "unknown_parameter", "unexpected")):
        return "extra_key"
    return "other"


def run_task(chat: OllamaChat, model: str, task: dict[str, Any], prepared: PreparedInput,
             input_root: Path, max_steps: int) -> dict[str, Any]:
    started = time.perf_counter()
    events: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    usage: Counter[str] = Counter()
    final_text = ""
    stop_reason = "assistant_final"
    premature_finals = 0
    with MCPClient(input_root) as mcp:
        schemas = _openai_tools(mcp.tools())
        allowed_tools = {tool["function"]["name"] for tool in schemas}
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task["request"] + "\n\n" + prepared.prompt()},
        ]
        while len(events) < max_steps:
            response = chat.complete(messages, schemas)
            raw_usage = response.get("usage") or {}
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                usage[key] += int(raw_usage.get(key, 0) or 0)
            message = (response.get("choices") or [{}])[0].get("message") or {}
            tool_calls = message.get("tool_calls") or _content_tool_calls(message, allowed_tools)
            if not tool_calls:
                final_text = str(message.get("content") or "")
                has_execution = any(event.get("tool") in {"fullseye_apply", "fullseye_pipeline"}
                                    for event in events)
                if not has_execution and premature_finals < 2:
                    premature_finals += 1
                    messages.append({"role": "assistant", "content": final_text})
                    messages.append({"role": "user", "content":
                        "まだMCPの実行ツールによる数値結果がありません。候補の説明やコード例では課題は未完了です。"
                        "取得済みの情報を使い、MCPツールで入力を読み、処理を実行して依頼された数値を得てください。"})
                    continue
                break
            normalized_calls: list[dict[str, Any]] = []
            for index, call in enumerate(tool_calls):
                function = call.get("function") or {}
                call_id = str(call.get("id") or f"call_{len(events)}_{index}")
                arguments = function.get("arguments", {})
                if isinstance(arguments, dict):
                    encoded_arguments = json.dumps(arguments, ensure_ascii=False, separators=(",", ":"))
                else:
                    encoded_arguments = str(arguments)
                normalized_calls.append({"id": call_id, "type": "function",
                                         "function": {"name": str(function.get("name", "")),
                                                      "arguments": encoded_arguments}})
            messages.append({"role": "assistant", "content": message.get("content") or "",
                             "tool_calls": normalized_calls})
            for call in normalized_calls:
                if len(events) >= max_steps:
                    break
                name = call["function"]["name"]
                encoded = call["function"]["arguments"]
                try:
                    arguments = json.loads(encoded) if encoded else {}
                    if not isinstance(arguments, dict):
                        raise ValueError("tool arguments are not an object")
                    result = mcp.call(name, arguments)
                    event = {"step": len(events) + 1, "tool": name, "arguments": arguments,
                             "is_error": bool(result.get("isError")), "result": result}
                    if result.get("isError"):
                        message_text = _tool_payload(result)
                        refusal = {"step": event["step"], "tool": name,
                                   "reason": _failure_reason(message_text), "message": message_text[:1000]}
                        failures.append(refusal)
                except Exception as exc:
                    safe = _secret_safe(f"{type(exc).__name__}: {exc}", os.environ.get("OLLAMA_HOST"))
                    event = {"step": len(events) + 1, "tool": name,
                             "arguments": json.loads(encoded) if encoded.startswith("{") else encoded,
                             "is_error": True, "error": safe}
                    result = {"isError": True, "content": [{"type": "text", "text": safe}]}
                    failures.append({"step": event["step"], "tool": name,
                                     "reason": _failure_reason(safe), "message": safe[:1000]})
                events.append(event)
                messages.append({"role": "tool", "tool_call_id": call["id"], "name": name,
                                 "content": _tool_payload(result)})
        else:
            stop_reason = "max_steps"
    judgment = judge_task(task, prepared, events)
    return {
        "task_id": task["id"], "category": task["category"], "model": model,
        "passed": judgment["passed"], "judgment": judgment, "steps": len(events),
        "tools": [event["tool"] for event in events], "events": events, "failed_calls": failures,
        "final_text": final_text, "stop_reason": stop_reason,
        "elapsed_seconds": round(time.perf_counter() - started, 3), "tokens": dict(usage),
    }


EXPECTED_OPS = {
    "judge_component_count": {"count_obj"},
    "judge_region_fraction": {"otsu", "cv_otsu", "sk_otsu"},
    "judge_smoothed_std": {"gaussian", "cv_gaussian"},
    "judge_feature_count": {"cv_good_features"},
    "judge_match_position": {"ncc_locate", "shape_locate"},
    "judge_dolp_mean": {"polarization_dolp_map"},
    "judge_phase_mean": {"wrapped_phase"},
    "judge_depth_mean": {"decode_fringe"},
}


def classify_failure(result: dict[str, Any], task: dict[str, Any]) -> str | None:
    if result["passed"]:
        return None
    if result.get("stop_reason") in {"max_steps", "agent_error"}:
        return "step_limit"
    reasons = {item["reason"] for item in result.get("failed_calls", [])}
    if "type_mismatch" in reasons:
        return "type_mismatch"
    expected = EXPECTED_OPS[task["judge"]]
    successful = _records(result.get("events", []), expected)
    if successful:
        return "judgment_miss"
    serialized = json.dumps(result.get("events", []), ensure_ascii=False)
    found = any(name in serialized for name in expected)
    return "argument_build" if found else "search_not_found"


FAILURE_JA = {
    "search_not_found": "検索で見つからない",
    "argument_build": "見つかるが引数が組めない",
    "type_mismatch": "組めるが型が合わない",
    "judgment_miss": "実行はするが判定が外れる",
    "step_limit": "手数切れ・モデル異常終了",
}


def _sequence(result: dict[str, Any]) -> str:
    labels: list[str] = []
    for event in result.get("events", []):
        label = event["tool"]
        args = event.get("arguments")
        if isinstance(args, dict):
            op = args.get("op")
            stages = args.get("stages")
            if op:
                label += f"[{op}]"
            elif isinstance(stages, list):
                names = [str(stage.get("op")) for stage in stages if isinstance(stage, dict) and stage.get("op")]
                if names:
                    label += "[" + ",".join(names) + "]"
        labels.append(label + ("!" if event.get("is_error") else ""))
    return " → ".join(labels) if labels else "(ツール呼び出しなし)"


def _representative(results: list[dict[str, Any]], predicate: Callable[[dict[str, Any]], bool]) -> dict[str, Any] | None:
    return next((result for result in results if predicate(result)), None)


def improvement_rows(results: list[dict[str, Any]], task_by_id: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    match = _representative(results, lambda r: not r["passed"] and task_by_id[r["task_id"]]["judge"] == "judge_match_position")
    if match:
        rows.append({"proposal": "登録見本を明示的に渡せる `fullseye_load_template` と、テンプレート handle を必須引数にした位置決めツールを用意する。現在の単項 pipeline ではシーンと見本を結べない。",
                     "evidence": f"{match['task_id']}: {_sequence(match)}"})

    missing = _representative(results, lambda r: classify_failure(r, task_by_id[r["task_id"]]) == "search_not_found")
    if missing:
        rows.append({"proposal": "`fullseye_find_ops` の説明・同義語に、失敗した業務表現と入出力型を追加し、0件時には英訳候補を返す。",
                     "evidence": f"{missing['task_id']}: {_sequence(missing)}"})

    arguments = _representative(results, lambda r: classify_failure(r, task_by_id[r["task_id"]]) == "argument_build")
    if arguments:
        rows.append({"proposal": "検索結果の各候補に、そのまま使える次の呼び出し骨格（`load_image` / `load_stack` の種別、pipeline stage）を短く添える。",
                     "evidence": f"{arguments['task_id']}: {_sequence(arguments)}"})

    mismatch = _representative(results, lambda r: classify_failure(r, task_by_id[r["task_id"]]) == "type_mismatch")
    if mismatch:
        rows.append({"proposal": "型不一致エラーを構造化し、実型・期待型・直すための具体的な loader/変換候補を同じ応答に載せる。",
                     "evidence": f"{mismatch['task_id']}: {_sequence(mismatch)}"})

    long_run = _representative(sorted(results, key=lambda r: r["steps"], reverse=True),
                               lambda r: r["steps"] >= 6)
    if long_run:
        rows.append({"proposal": "検索→カード→検証→実行を繰り返す課題向けに、候補が一意なら検証済み pipeline 案を返す高水準ツールを追加して手数を減らす。",
                     "evidence": f"{long_run['task_id']} ({long_run['steps']}手): {_sequence(long_run)}"})
    return rows[:5]


def build_report(payload: dict[str, Any], tasks: list[dict[str, Any]]) -> str:
    results = payload["results"]
    task_by_id = {task["id"]: task for task in tasks}
    runs = sorted({int(result["run"]) for result in results})
    category_rows = []
    for category in CATEGORIES:
        rates = []
        for run in runs:
            subset = [r for r in results if r["category"] == category and int(r["run"]) == run]
            rates.append(sum(r["passed"] for r in subset) / len(subset) if subset else 0.0)
        category_rows.append((category, statistics.median(rates), rates))

    failure_counts: Counter[str] = Counter()
    for result in results:
        kind = classify_failure(result, task_by_id[result["task_id"]])
        if kind:
            failure_counts[kind] += 1

    lines = [
        "# Fullseye MCP LLM エンドツーエンド評価",
        "",
        f"- model: `{payload['model']}`",
        f"- 課題数: {payload['task_count']}（各課題 {payload['runs']} 回、合計 {len(results)} 試行）",
        f"- 最大手数: {payload['max_steps']}",
        "- 判定: 合成時に作った真値を、LLMを使わない関数で照合",
        "",
        "## 分類ごとの合格率",
        "",
        "3回それぞれの分類内合格率を計算し、その中央値を示す。",
        "",
        "| 分類 | 合格率（3回の中央値） | run 1 / 2 / 3 |",
        "|---|---:|---|",
    ]
    for category, median, rates in category_rows:
        raw = " / ".join(f"{rate:.0%}" for rate in rates)
        lines.append(f"| {category} | {median:.0%} | {raw} |")
    lines.extend(["", "## 失敗の内訳", "", "| 内訳 | 試行数 |", "|---|---:|"])
    for key in ("search_not_found", "argument_build", "type_mismatch", "judgment_miss", "step_limit"):
        lines.append(f"| {FAILURE_JA[key]} | {failure_counts[key]} |")

    lines.extend(["", "## サーバ側の改善提案", ""])
    improvements = improvement_rows(results, task_by_id)
    if improvements:
        for index, row in enumerate(improvements, 1):
            lines.extend([f"{index}. {row['proposal']}", f"   - 証拠: `{row['evidence']}`"])
    else:
        lines.append("全試行が短い経路で合格し、今回の記録から追加の改善根拠は得られなかった。")

    passed = sum(result["passed"] for result in results)
    elapsed = sum(float(result["elapsed_seconds"]) for result in results)
    tokens = sum(int(result.get("tokens", {}).get("total_tokens", 0)) for result in results)
    lines.extend([
        "", "## 全体", "",
        f"- 合格: {passed}/{len(results)}（{passed / len(results):.1%}）",
        f"- 所要時間合計: {elapsed:.1f} 秒",
        f"- total tokens 合計: {tokens}",
        "- 生データには手数、ツール列、拒否分類、最終数値、合否、時間、token数を試行ごとに保存した。",
    ])
    agent_errors = sum(result.get("stop_reason") == "agent_error" for result in results)
    if agent_errors:
        lines.append(f"- モデルAPI異常終了: {agent_errors}試行（手数切れ・モデル異常終了に集計）")
    gate = payload.get("gate") or {}
    lines.extend([
        "", "## LLMなしの門", "",
        f"- 課題形式・生成・判定のテスト: {gate.get('task_tests', '別途実行')}",
        f"- 実MCPサーバで読めた課題入力: {gate.get('tasks', '別途実行')}",
        f"- MCP入力門: {gate.get('mcp', '別途実行')}",
    ])
    if gate.get("mcp_tests"):
        lines.append(f"- `tests/test_mcp_*.py`: {gate['mcp_tests']}")
    if gate.get("regen"):
        lines.append(f"- `tools/regen_all.py --check`: {gate['regen']}")
    lines.append("")
    return "\n".join(lines)


def validate_inputs(task_data: dict[str, Any]) -> dict[str, Any]:
    """Generate every input and verify that the real MCP server can load it."""
    checked = 0
    with tempfile.TemporaryDirectory(prefix="fullseye-agent-eval-") as temp:
        root = Path(temp)
        prepared_rows = [(task, generate_task_input(task, root)) for task in task_data["tasks"]]
        with MCPClient(root) as mcp:
            names = {tool["name"] for tool in mcp.tools()}
            required = {"fullseye_load_image", "fullseye_load_stack", "fullseye_find_ops",
                        "fullseye_pipeline"}
            if not required <= names:
                raise RuntimeError(f"MCP tools missing: {sorted(required - names)}")
            for task, prepared in prepared_rows:
                if prepared.stack_sort:
                    result = mcp.call("fullseye_load_stack",
                                      {"paths": list(prepared.files), "sort": prepared.stack_sort})
                else:
                    result = mcp.call("fullseye_load_image", {"path": prepared.files[0], "vision": "none"})
                if result.get("isError"):
                    raise RuntimeError(f"MCP could not load task {task['id']}")
                checked += 1
    return {"tasks": checked, "mcp": "ok"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", default=str(DEFAULT_TASKS))
    parser.add_argument("--model", help="Ollama model name; auto-selects a 14-32B model when omitted")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--max-steps", type=int)
    parser.add_argument("--output", help="non-repository JSON result path")
    parser.add_argument("--report", help="non-repository Markdown report path")
    parser.add_argument("--task", action="append", dest="task_ids", help="run only this task id")
    parser.add_argument("--validate-only", action="store_true", help="run deterministic gates without Ollama")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    task_data = load_tasks(args.tasks)
    if args.validate_only:
        print(json.dumps(validate_inputs(task_data), ensure_ascii=False))
        return 0
    if not args.output or not args.report:
        raise SystemExit("--output and --report are required for an evaluation run")
    tasks = task_data["tasks"]
    if args.task_ids:
        wanted = set(args.task_ids)
        tasks = [task for task in tasks if task["id"] in wanted]
        missing = wanted - {task["id"] for task in tasks}
        if missing:
            raise SystemExit(f"unknown task ids: {sorted(missing)}")
    model = args.model or choose_model(available_models())
    max_steps = int(args.max_steps or task_data["max_steps"])
    if args.runs < 1 or max_steps < 1:
        raise SystemExit("--runs and --max-steps must be positive")
    chat = OllamaChat(model)
    all_results: list[dict[str, Any]] = []
    started = time.time()
    with tempfile.TemporaryDirectory(prefix="fullseye-agent-eval-") as temp:
        input_root = Path(temp)
        prepared = {task["id"]: generate_task_input(task, input_root) for task in tasks}
        for run in range(1, args.runs + 1):
            for index, task in enumerate(tasks, 1):
                print(f"run {run}/{args.runs} task {index}/{len(tasks)} {task['id']}", flush=True)
                try:
                    result = run_task(chat, model, task, prepared[task["id"]], input_root, max_steps)
                except Exception as exc:
                    safe = _secret_safe(f"{type(exc).__name__}: {exc}", os.environ.get("OLLAMA_HOST"))
                    result = {"task_id": task["id"], "category": task["category"], "model": model,
                              "passed": False, "judgment": {"passed": False, "metric": None,
                              "expected": None, "detail": safe}, "steps": 0, "tools": [], "events": [],
                              "failed_calls": [], "final_text": "", "stop_reason": "agent_error",
                              "elapsed_seconds": 0.0, "tokens": {}, "error": safe}
                result["run"] = run
                all_results.append(result)
    gate = validate_inputs(task_data)
    gate["task_tests"] = "tests/test_mcp_agent_eval_tasks.py"
    payload = {"version": 1, "model": model, "task_count": len(tasks), "runs": args.runs,
               "max_steps": max_steps, "started_unix": started, "finished_unix": time.time(),
               "gate": gate, "results": all_results}
    output = Path(args.output)
    report = Path(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    report.write_text(build_report(payload, tasks), encoding="utf-8", newline="\n")
    print(f"wrote results: {output.name}")
    print(f"wrote report: {report.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
