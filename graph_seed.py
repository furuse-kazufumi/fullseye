"""Emit CommandWorker spec JSONs for the full S0/S1/S2 graph across 3 problems.

Writes specs/*.json (list-arg, shared absolute workdir so the raptor board picks
the artifacts up). It does NOT touch the work-graph DB — the caller runs
`raptor-worklog add` with these spec files (kept as a separate, auditable step).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBLEMS = ("denoise", "edge", "binarize")


def spec(cmd_tail: list[str], workdir: str, timeout: int, out_ext: str) -> dict:
    return {
        "cmd": ["py", "-3.11", *cmd_tail, "--workdir", workdir, "--out", f"<OUT>{out_ext}"],
        "cwd": str(HERE),
        "env": {"PYTHONUTF8": "1"},
        "produces": f"<OUT>{out_ext}",
        "timeout": timeout,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workdir", default="C:/dev/tools/raptor/out/worklog/imgevolve")
    a = ap.parse_args()
    sd = HERE / "specs"; sd.mkdir(exist_ok=True)
    w = a.workdir

    for p in PROBLEMS:
        (sd / f"s0_{p}.json").write_text(json.dumps(
            spec(["baseline.py", "--problem", p, "--seed", "0"], w, 600, ".json"), indent=2), "utf-8")
        (sd / f"s1_{p}.json").write_text(json.dumps(
            spec(["evolve.py", "--problem", p, "--gens", "40", "--pop", "24", "--seed", "0"], w, 3600, ".json"),
            indent=2), "utf-8")
        (sd / f"metrics_{p}.json").write_text(json.dumps(
            spec(["report.py", "--problem", p], w, 300, ".md"), indent=2), "utf-8")
    # S2 codegen+difftest on the C-demonstrable problem (edge)
    (sd / "codegen_edge.json").write_text(json.dumps(
        spec(["codegen.py", "--problem", "edge"], w, 300, ".json"), indent=2), "utf-8")
    (sd / "difftest_edge.json").write_text(json.dumps(
        spec(["difftest.py", "--problem", "edge"], w, 600, ".json"), indent=2), "utf-8")
    print(f"wrote specs for {PROBLEMS} + edge codegen/difftest -> {sd}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
