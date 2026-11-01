#!/usr/bin/env python3
"""Profile registry-op calls made by representative scripts.

各 ``ops.RT`` 呼び出しを ``perf_counter_ns`` で測り、頻度・総時間・1回平均を JSON に
出す。子プロセスや推測値ではなく、この実行で通った op だけを記録する。
"""
from __future__ import annotations

import argparse
import json
import os
import runpy
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scripts", nargs="+", help="Python scripts, relative to the checkout")
    parser.add_argument("--out", required=True, help="JSON output path")
    args = parser.parse_args()

    import accel_bridge
    import ops

    stats = defaultdict(lambda: {"calls": 0, "total_ns": 0})
    original = dict(ops.RT)

    def timed(name, fn):
        def wrapper(*a, **kw):
            start = time.perf_counter_ns()
            try:
                return fn(*a, **kw)
            finally:
                row = stats[name]
                row["calls"] += 1
                row["total_ns"] += time.perf_counter_ns() - start
        return wrapper

    for name, fn in original.items():
        ops.RT[name] = timed(name, fn)
    runs = []
    try:
        for item in args.scripts:
            path = (ROOT / item).resolve()
            if ROOT not in path.parents or not path.is_file():
                raise SystemExit("script is outside checkout or missing: %s" % item)
            started = time.perf_counter()
            old_argv = sys.argv
            sys.argv = [str(path)]
            try:
                runpy.run_path(str(path), run_name="__main__")
                status, error = "ok", None
            except SystemExit as exc:
                status, error = ("ok", None) if exc.code in (None, 0) else ("failed", repr(exc))
            except Exception as exc:  # noqa: BLE001 - record a failed workload without losing prior measurements
                status, error = "failed", "%s: %s" % (type(exc).__name__, str(exc)[:400])
            finally:
                sys.argv = old_argv
            runs.append({"script": item, "status": status, "error": error,
                         "elapsed_s": time.perf_counter() - started})
    finally:
        ops.RT.clear()
        ops.RT.update(original)

    import api
    rows = []
    for name, value in stats.items():
        op = api.find_op(name)
        total_s = value["total_ns"] / 1e9
        rows.append({"op": name, "family": op.category if op else "unknown",
                     "gpu": accel_bridge._C2A.get(name) or accel_bridge._C2VA.get(name)
                            or accel_bridge._C2M.get(name),
                     "calls": value["calls"], "mean_ms": 1000 * total_s / value["calls"],
                     "total_s": total_s})
    rows.sort(key=lambda row: (-row["total_s"], row["op"]))
    payload = {"generated_by": "tools/profile_ops.py", "python": sys.executable,
               "cwd": os.getcwd(), "runs": runs, "ops": rows}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path = Path(args.out).with_suffix(".md")
    lines = ["# Op time ranking — 2026-11-02", "",
             "実行したPoCで `ops.RT` に到達した呼び出しだけを実測した。総時間順。",
             "", "| rank | op | 族 | GPU | calls | 1回 ms | 合計 s |",
             "|---:|---|---|---|---:|---:|---:|"]
    for rank, row in enumerate(rows[:40], 1):
        lines.append("| %d | `%s` | %s | %s | %d | %.3f | %.3f |" %
                     (rank, row["op"], row["family"], row["gpu"] or "なし", row["calls"],
                      row["mean_ms"], row["total_s"]))
    missing = defaultdict(lambda: {"ops": 0, "total_s": 0.0})
    for row in rows[:40]:
        if not row["gpu"]:
            missing[row["family"]]["ops"] += 1
            missing[row["family"]]["total_s"] += row["total_s"]
    lines += ["", "## 上位40のGPU未対応内訳", "",
              "| 族 | op数 | 合計 s |", "|---|---:|---:|"]
    for family, value in sorted(missing.items(), key=lambda item: (-item[1]["total_s"], item[0])):
        lines.append("| %s | %d | %.3f |" % (family, value["ops"], value["total_s"]))
    lines += ["", "## Workloads", ""]
    for run in runs:
        lines.append("- `%s`: %s, %.3f s%s" %
                     (run["script"], run["status"], run["elapsed_s"],
                      " — " + run["error"] if run["error"] else ""))
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("profiled %d scripts, %d ops -> %s" % (len(runs), len(rows), args.out))
    return 1 if any(r["status"] == "failed" for r in runs) else 0


if __name__ == "__main__":
    raise SystemExit(main())
