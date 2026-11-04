#!/usr/bin/env python3
"""Profile registry-op calls made by representative scripts.

各 ``ops.RT`` 呼び出しを ``perf_counter_ns`` で測り、頻度・総時間・1回平均を JSON に
出す。子プロセスや推測値ではなく、この実行で通った op だけを記録する。
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import runpy
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _write_md(payload: dict, md_path: Path) -> None:
    """``payload``(JSON と同じ構造)から順位表 Markdown を書く。PoC は再実行しない。

    手書きしない(AGENTS.md: 生成物の唯一の入口)。``--md`` はこの関数だけを使い、
    既に測った JSON から表を起こす —— PoC を回し直さずに表記だけ直せる。
    """
    rows = payload["ops"]
    runs = payload.get("runs", [])
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
    # 所見: PoC は CPU 前提の寸法で作られているので合計時間は小さい。GPU の価値は寸法で決まる。
    top = rows[0] if rows else {"op": "-", "total_s": 0.0}
    total_all = sum(r["total_s"] for r in rows)
    lines += ["", "## 所見", "",
              "実行した %d 本の PoC で `ops.RT` に到達した op は %d 種、総時間は合計 %.1f s。"
              % (len(runs), len(rows), total_all),
              "最も重い op でも合計 **%.1f s**(`%s`)で、時間×頻度の順位では GPU の出番は見えない。"
              % (top["total_s"], top["op"]),
              "既存 PoC は CPU 前提の寸法で作られているから小さいだけで、**GPU の価値は"
              "「実寸」で決まる**(`docs/perf/gpu_required_2026-11-02.md` の寸法×時間表を参照)。",
              "",
              "MCP e2e 20 課題(#224)の op 時間は未計測(この便ではローカルに実行器を立てていない)。"
              "立てた回に同じ JSON へ追記する。"]
    lines += ["", "## Workloads", ""]
    for run in runs:
        lines.append("- `%s`: %s, %.3f s%s" %
                     (run["script"], run["status"], run["elapsed_s"],
                      " — " + run["error"] if run["error"] else ""))
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scripts", nargs="*", help="Python scripts, relative to the checkout")
    parser.add_argument("--out", help="JSON output path (profiling mode)")
    parser.add_argument("--md", help="既存の JSON から .md を起こすだけ(PoC は再実行しない)")
    args = parser.parse_args()

    if args.md:
        src = Path(args.md)
        payload = json.loads(src.read_text(encoding="utf-8"))
        _write_md(payload, src.with_suffix(".md"))
        print("rendered %s from %s" % (src.with_suffix(".md"), src))
        return 0
    if not args.out or not args.scripts:
        raise SystemExit("profiling mode needs scripts and --out; or use --md <json>")

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
    # 公開 docs にローカルの絶対パスを書かない(tests/test_docs_no_local_paths.py)。版だけ残す。
    payload = {"generated_by": "tools/profile_ops.py", "python": platform.python_version(),
               "runs": runs, "ops": rows}
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
