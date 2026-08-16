#!/usr/bin/env python3
"""algo_gate — run an algo-tier op's honest gate as a work-graph-friendly gated node.

The raptor work-graph ``CommandWorker`` marks a node DONE when its ``produces`` file
exists OR the command exits 0 (it fails only when the command exits non-zero AND
left no artifact). A plain ``algo_difftest`` run always writes its result JSON — even
on FAIL — so using that JSON as ``produces`` would report a failing gate as DONE
(fail-open). This wrapper closes that hole for the op-wave pattern (1 op = 1 graph
node): it writes a pass-marker ``gate_ok.json`` ONLY when the honest gate passes, and
its exit code IS the verdict. Point the node's ``produces`` at the marker so a failing
difftest fails the node.

    py -3.11 tools/algo_gate.py --op gauss_solve --out <dir> [--no-c]

Exit 0 = gate passed (marker written); exit 1 = gate failed (no marker). Deterministic:
delegates entirely to ``algo_difftest.difftest`` (Python == oracle, C == Python
bit-for-bit) — this only decides how the verdict is surfaced to the graph.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# tools/ is this script's dir, so add the repo root (parent) to import algo* modules
# whatever the caller's cwd is.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import algo
import algo_difftest


def gate(op: str, out: Path, *, use_c: bool = True) -> dict:
    """Run the honest gate for ``op`` into ``out``; write ``gate_ok.json`` iff it passes.

    Returns the full difftest result dict. A stale marker from a prior run is removed
    first, so a marker present after this call always reflects THIS run's verdict.
    """
    if algo.find_algo(op) is None:
        raise SystemExit(f"unknown algo op: {op!r} (try: imgevolve.py algo list)")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    marker = out / "gate_ok.json"
    if marker.exists():                                   # never certify a stale prior pass
        marker.unlink()
    res = algo_difftest.difftest(op, out, cc="auto" if use_c else None)  # writes algo_difftest_<op>.json
    if res["passed"]:
        cb = res["c_backend"] or {}
        marker.write_text(json.dumps({
            "op": op, "passed": True,
            "python_max_abs_diff": res["python_max_abs_diff"],
            "c_verified": res["c_verified"],
            "c_vs_python_bit_identical": cb.get("c_vs_python_bit_identical"),
            "compiler": res["compiler"],
        }, indent=2), encoding="utf-8")
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--op", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-c", action="store_true", help="force the honest C skip")
    a = ap.parse_args()
    res = gate(a.op, Path(a.out), use_c=not a.no_c)
    cb = res["c_backend"] or {}
    print(f"[algo_gate:{a.op}] passed={res['passed']} "
          f"python_diff={res['python_max_abs_diff']:.2e} "
          f"C={cb.get('status')} bit_identical={cb.get('c_vs_python_bit_identical')} "
          f"c_verified={res['c_verified']}")
    return 0 if res["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
