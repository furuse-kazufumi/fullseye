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


def gate(op: str, out: Path, *, use_c: bool = True, require_c: bool = True) -> dict:
    """Run the honest gate for ``op`` into ``out``; write ``gate_ok.json`` iff it passes
    AND the C backend was actually verified (or C is deliberately off / not required).

    The stale marker is removed FIRST — before the unknown-op guard and before difftest —
    so a marker present after this call ALWAYS reflects THIS run's verdict: an unknown op,
    a failed difftest, or a C half that only skipped can never inherit a prior run's pass.

    ``require_c`` (default True) makes an honest-but-UNVERIFIED pass (C skipped because no
    toolchain was found) fail CLOSED for the work-graph: no ``gate_ok.json`` is written, so
    a detached driver on a C-less venv cannot turn the C bit-identity claim green without
    ever compiling. It is moot when ``use_c`` is False (C is off by explicit choice). A
    diagnostic ``gate_unverified.json`` (a name the node's ``produces`` cannot match) is
    written in that case so the skip is visible. Returns the difftest result dict plus
    ``gate_marker_written``.
    """
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    marker = out / "gate_ok.json"
    if marker.exists():                                   # never certify a stale prior pass
        marker.unlink()
    if algo.find_algo(op) is None:                        # fail-closed: stale marker already gone
        raise SystemExit(f"unknown algo op: {op!r} (try: imgevolve.py algo list)")
    # resolve the compiler ourselves (concrete list[str] | None) rather than passing
    # difftest's "auto" sentinel, so the type matches its signature exactly.
    cc = algo_difftest.find_c_compiler() if use_c else None
    res = algo_difftest.difftest(op, out, cc=cc)          # writes algo_difftest_<op>.json
    require_c_effective = require_c and use_c             # requiring C is moot when C is off
    verified_pass = res["passed"] and (res["c_verified"] or not require_c_effective)
    if verified_pass:
        cb = res["c_backend"] or {}
        marker.write_text(json.dumps({
            "op": op, "passed": True,
            "python_max_abs_diff": res["python_max_abs_diff"],
            "c_verified": res["c_verified"],
            "c_vs_python_bit_identical": cb.get("c_vs_python_bit_identical"),
            "compiler": res["compiler"],
        }, indent=2), encoding="utf-8")
    elif res["passed"]:                                   # passed but C unverified while required
        (out / "gate_unverified.json").write_text(json.dumps({
            "op": op, "passed": True, "c_verified": False,
            "reason": "C backend skipped (no toolchain); pass is UNVERIFIED and fails the gate",
            "compiler": res["compiler"],
        }, indent=2), encoding="utf-8")
    res["gate_marker_written"] = verified_pass
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
