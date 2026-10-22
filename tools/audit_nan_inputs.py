"""全登録 op の非有限入力に対する挙動を実測する。

通常実行は JSON と Markdown を更新し、``--markdown-from-json`` は保存済み
JSON だけから Markdown を再生成する。各呼出しは別プロセスで監視するため、
停止する実装があっても 20 秒で次へ進む。
"""
from __future__ import annotations

import argparse
import copy
import inspect
import json
import multiprocessing as mp
import numbers
import queue
import time
import warnings
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "docs" / "nan_input_audit.json"
MD_PATH = ROOT / "docs" / "NAN_INPUT_AUDIT.md"
COMMAND = "py -3.11 tools/audit_nan_inputs.py"
TIMEOUT = 20.0
OUTCOMES = (
    "raises_fsvalueerror", "raises_other", "propagates_nan", "silent_finite",
    "silent_identical", "timeout", "baseline_failed", "not_applicable",
)

# ndarray として一画素を書き換えられる登録 sort。一覧にない sort も黙って
# 落とさず not_applicable 行に残す。
ARRAY_SORTS = {
    "any", "image", "region", "points", "signal", "video", "volume", "color",
    "qimage", "cimage", "counts", "lightfield", "matrix", "rgbimage", "beatcube",
    "keypoints",
}


def baseline_for_sort(sort: str) -> np.ndarray | None:
    """決定的で有限な、sort ごとの代表入力を返す。"""
    rng = np.random.default_rng(20261022)
    if sort not in ARRAY_SORTS:
        return None
    if sort == "region":
        y, x = np.ogrid[:32, :32]
        return (((x - 16) ** 2 + (y - 16) ** 2) < 10 ** 2).astype(np.float64)
    if sort in {"points", "keypoints"}:
        return rng.random((48, 3), dtype=np.float64)
    if sort == "signal":
        return (0.5 + 0.25 * np.sin(np.linspace(0, 8 * np.pi, 256))).astype(np.float64)
    if sort == "video":
        return rng.random((5, 32, 32), dtype=np.float64)
    if sort == "volume":
        return rng.random((16, 16, 16), dtype=np.float64)
    if sort in {"color", "cimage", "rgbimage", "qimage"}:
        channels = 4 if sort == "qimage" else 3
        return rng.random((32, 32, channels), dtype=np.float64)
    if sort == "lightfield":
        return rng.random((3, 3, 16, 16), dtype=np.float64)
    if sort == "beatcube":
        return rng.random((4, 16, 16), dtype=np.float64)
    if sort == "matrix":
        return np.eye(8, dtype=np.float64) + 0.05
    if sort == "counts":
        return np.arange(1, 65, dtype=np.float64)
    # image / any: non-constant values avoid refusing valid baselines.
    return rng.random((32, 32), dtype=np.float64)


def contains_nonfinite(value, depth: int = 0) -> bool:
    """辞書や tuple の内側を含め、数値 leaf に NaN/inf があるか調べる。"""
    if depth > 8:
        return False
    if isinstance(value, np.ndarray):
        if value.dtype.kind in "fc":
            return not bool(np.isfinite(value).all())
        if value.dtype.kind == "O":
            return any(contains_nonfinite(x, depth + 1) for x in value.flat)
        return False
    if isinstance(value, (bool, np.bool_, numbers.Integral)):
        return False
    if isinstance(value, numbers.Number):
        try:
            return not bool(np.isfinite(value))
        except TypeError:
            return False
    if isinstance(value, dict):
        return any(contains_nonfinite(x, depth + 1) for x in value.values())
    if isinstance(value, (tuple, list)):
        return any(contains_nonfinite(x, depth + 1) for x in value)
    return False


def bit_identical(left, right, depth: int = 0) -> bool:
    """dtype、shape、浮動小数の bit を含む構造的な完全一致。"""
    if depth > 8:
        return True
    if isinstance(left, np.ndarray) or isinstance(right, np.ndarray):
        if not isinstance(left, np.ndarray) or not isinstance(right, np.ndarray):
            return False
        if left.shape != right.shape or left.dtype != right.dtype:
            return False
        if left.dtype.kind == "O":
            return all(bit_identical(a, b, depth + 1) for a, b in zip(left.flat, right.flat))
        return left.tobytes() == right.tobytes()
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return list(left) == list(right) and all(
            bit_identical(left[k], right[k], depth + 1) for k in left)
    if isinstance(left, (tuple, list)):
        return len(left) == len(right) and all(
            bit_identical(a, b, depth + 1) for a, b in zip(left, right))
    try:
        return bool(left == right)
    except Exception:  # noqa: BLE001 - foreign return objects are not identical
        return False


def classify_result(result, baseline_result) -> str:
    if contains_nonfinite(result):
        return "propagates_nan"
    return "silent_identical" if bit_identical(result, baseline_result) else "silent_finite"


def enumerate_ops() -> list[dict[str, object]]:
    """主登録表を順序どおり全件列挙する。"""
    import ops
    return [{"name": op.name, "category": op.category, "in_sort": op.in_sort,
             "out_sort": op.out_sort, "module": inspect.unwrap(op.fn).__module__,
             "applicable": op.in_sort in ARRAY_SORTS} for op in ops.REGISTRY]


def _call(name: str, value: np.ndarray):
    import ops
    op = next(item for item in ops.REGISTRY if item.name == name)
    fn = inspect.unwrap(op.fn)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            result = fn(copy.deepcopy(value), 0.5, 0.5)
            return {"kind": "return", "value": result,
                    "warnings": [f"{w.category.__name__}: {w.message}"[:240] for w in caught]}
        except BaseException as exc:  # noqa: BLE001 - audit records every implementation failure
            return {"kind": "raise", "exception_type": type(exc).__name__,
                    "exception_message": str(exc)[:240],
                    "warnings": [f"{w.category.__name__}: {w.message}"[:240] for w in caught]}


def _child(name: str, value: np.ndarray, out) -> None:
    out.put(_call(name, value))


def timed_call(name: str, value: np.ndarray, timeout: float = TIMEOUT) -> tuple[dict, float]:
    ctx = mp.get_context("spawn")
    out = ctx.Queue()
    proc = ctx.Process(target=_child, args=(name, value, out))
    started = time.perf_counter()
    proc.start()
    try:
        answer = out.get(timeout=timeout)
    except queue.Empty:
        proc.terminate()
        proc.join(5)
        return {"kind": "timeout"}, time.perf_counter() - started
    proc.join(5)
    if proc.is_alive():
        proc.terminate()
        proc.join(5)
    return answer, time.perf_counter() - started


def _exception_outcome(answer: dict) -> str:
    return ("raises_fsvalueerror" if answer.get("exception_type") == "FsValueError"
            else "raises_other")


def _wrapper_behaviour(name: str, value: np.ndarray) -> str:
    import api
    try:
        api.apply(value, name, on_error="raise", coerce=False, fast=False)
        return "returned"
    except BaseException as exc:  # noqa: BLE001 - public-path observation
        return f"raised_{type(exc).__name__}"


def audit_one(meta: dict[str, object], timeout: float = TIMEOUT) -> dict[str, object]:
    base = {k: meta[k] for k in ("name", "category", "in_sort", "out_sort", "module")}
    base.update(nan_outcome="not_applicable", inf_outcome="not_applicable",
                exceptions={}, wrapper_behaviour={}, warnings={}, elapsed={})
    value = baseline_for_sort(str(meta["in_sort"]))
    if value is None:
        return base
    name = str(meta["name"])
    normal, sec = timed_call(name, value, timeout)
    base["elapsed"]["baseline"] = round(sec, 6)
    if normal["kind"] != "return":
        base["nan_outcome"] = base["inf_outcome"] = "baseline_failed"
        base["exceptions"]["baseline"] = {
            "type": normal.get("exception_type", normal["kind"]),
            "message": normal.get("exception_message", ""),
        }
        return base
    base["warnings"]["baseline"] = normal.get("warnings", [])
    baseline_result = normal["value"]
    for label, injected in (("nan", np.nan), ("inf", np.inf)):
        changed = value.copy()
        changed.flat[changed.size // 2] = injected
        answer, sec = timed_call(name, changed, timeout)
        base["elapsed"][label] = round(sec, 6)
        base["warnings"][label] = answer.get("warnings", [])
        if answer["kind"] == "timeout":
            outcome = "timeout"
        elif answer["kind"] == "raise":
            outcome = _exception_outcome(answer)
            base["exceptions"][label] = {"type": answer["exception_type"],
                                                   "message": answer["exception_message"]}
            base["wrapper_behaviour"][label] = _wrapper_behaviour(name, changed)
        else:
            outcome = classify_result(answer["value"], baseline_result)
        base[f"{label}_outcome"] = outcome
    return base


def make_document(records: list[dict[str, object]], elapsed: float) -> dict[str, object]:
    counts = {kind: {outcome: sum(r[f"{kind}_outcome"] == outcome for r in records)
                     for outcome in OUTCOMES} for kind in ("nan", "inf")}
    silent = defaultdict(list)
    for record in records:
        kinds = [k for k in ("nan", "inf") if record[f"{k}_outcome"] == "silent_finite"]
        if kinds:
            silent[str(record["module"])].append({"name": record["name"], "inputs": kinds})
    families = dict(sorted(Counter(str(r["in_sort"]) for r in records).items()))
    return {
        "header": {"command": COMMAND, "timeout_seconds": TIMEOUT,
                   "elapsed_seconds": round(elapsed, 3), "registry_entries": len(records)},
        "summary": {"families": families, "counts": counts,
                    "silent_finite_by_module": dict(sorted(silent.items())),
                    "contaminated": any(r["nan_outcome"] == "baseline_failed" for r in records)},
        "records": records,
    }


def render_markdown(data: dict[str, object]) -> str:
    summary = data["summary"]
    lines = ["# 非有限入力監査", "", "## 方法", "",
             f"登録表の全 {data['header']['registry_entries']} 件を列挙し、適用可能な op へ有限な基準入力、中央の1要素だけを NaN、+inf にした入力を渡した。",
             f"各呼出しは {data['header']['timeout_seconds']:g} 秒で打ち切り、入れ子の数値出力も検査した。基準入力が失敗した行は注入結果から除外した。",
             "", "## 結果", "", "| outcome | NaN | +inf |", "|---|---:|---:|"]
    for outcome in OUTCOMES:
        lines.append(f"| `{outcome}` | {summary['counts']['nan'][outcome]} | {summary['counts']['inf'][outcome]} |")
    lines += ["", "## silent_finite", ""]
    if summary["silent_finite_by_module"]:
        for module, rows in summary["silent_finite_by_module"].items():
            lines += [f"### `{module}`", ""]
            lines += [f"- `{row['name']}`: {', '.join(row['inputs'])}" for row in rows]
            lines.append("")
    else:
        lines += ["該当なし。", ""]
    if summary["contaminated"]:
        failed = [r["name"] for r in data["records"] if r["nan_outcome"] == "baseline_failed"]
        lines += ["## contaminated", "", "基準入力が失敗したため、次の行は注入結果を判定していない: " + ", ".join(f"`{n}`" for n in failed), ""]
    else:
        lines += ["## contaminated", "", "基準入力の失敗なし。", ""]
    return "\n".join(lines)


def _write_text(path: Path, text: str, check: bool) -> bool:
    if check:
        return path.exists() and path.read_text(encoding="utf-8") == text
    path.write_text(text, encoding="utf-8", newline="\n")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--markdown-from-json", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args(argv)
    if args.markdown_from_json:
        data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        fresh = render_markdown(data)
        ok = _write_text(MD_PATH, fresh, args.check)
        return 0 if ok else 1
    started = time.perf_counter()
    metas = enumerate_ops()
    if args.limit is not None:
        metas = metas[:args.limit]
    records = []
    for index, meta in enumerate(metas, 1):
        records.append(audit_one(meta))
        print(f"{index:4}/{len(metas)} {meta['name']}", flush=True)
    data = make_document(records, time.perf_counter() - started)
    json_text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    md_text = render_markdown(data)
    ok = _write_text(JSON_PATH, json_text, args.check) & _write_text(MD_PATH, md_text, args.check)
    return 0 if ok else 1


if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(main())
