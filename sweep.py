"""Queue one self-running exploration round onto the raptor work-graph.

Each round re-seeds baseline->evolve->metrics per problem with a fresh --seed (a
different search trajectory) and fresh node ids, so `raptor-worklog serve` keeps
advancing the exploration autonomously. A round's champions land in the shared
workdir; the review node (human-gated) compares rounds. This is the concrete
"self-run" mechanism (the graph runs unattended; a human queues rounds + reviews).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBLEMS = ("denoise", "edge", "binarize")


def _spec(cmd_tail, workdir, timeout, ext):
    return {"cmd": ["py", "-3.11", *cmd_tail, "--workdir", workdir, "--out", f"<OUT>{ext}"],
            "cwd": str(HERE), "env": {"PYTHONUTF8": "1"}, "produces": f"<OUT>{ext}", "timeout": timeout}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--raptor", default="C:/dev/tools/raptor")
    ap.add_argument("--workdir", default="C:/dev/tools/raptor/out/worklog/imgevolve")
    ap.add_argument("--gens", type=int, default=40)
    a = ap.parse_args()
    n = a.round
    sd = HERE / "specs"; sd.mkdir(exist_ok=True)
    wl = [sys.executable, str(Path(a.raptor) / "libexec" / "raptor-worklog")]

    def add(tid, title, cap, specfile=None, spec_text=None, depends=None, constraints=None):
        cmd = wl + ["add", "--project", "imgevolve", "--id", tid, "--title", title, "--capability", cap]
        if specfile:
            cmd += ["--spec-file", str(specfile)]
        if spec_text:
            cmd += ["--spec", spec_text]
        if depends:
            cmd += ["--depends", ",".join(depends)]
        if constraints:
            cmd += ["--constraints", ",".join(constraints)]
        subprocess.run(cmd, cwd=a.raptor, capture_output=True, text=True)
        print(f"  + {tid}")

    metrics_ids = []
    for p in PROBLEMS:
        s0 = sd / f"r{n}_s0_{p}.json"; s1 = sd / f"r{n}_s1_{p}.json"; mt = sd / f"r{n}_metrics_{p}.json"
        s0.write_text(json.dumps(_spec(["baseline.py", "--problem", p, "--seed", str(n)], a.workdir, 600, ".json"), indent=2), "utf-8")
        s1.write_text(json.dumps(_spec(["evolve.py", "--problem", p, "--gens", str(a.gens), "--pop", "24", "--seed", str(n)], a.workdir, 3600, ".json"), indent=2), "utf-8")
        mt.write_text(json.dumps(_spec(["report.py", "--problem", p], a.workdir, 300, ".md"), indent=2), "utf-8")
        b, e, m = f"imgevolve-r{n}-s0-{p}", f"imgevolve-r{n}-s1-{p}", f"imgevolve-r{n}-metrics-{p}"
        add(b, f"r{n} S0 baseline ({p})", "tool", specfile=s0)
        add(e, f"r{n} S1 evolve ({p}, seed {n})", "tool", specfile=s1, depends=[b])
        add(m, f"r{n} S1 metrics ({p})", "tool", specfile=mt, depends=[e])
        metrics_ids.append(m)
    add(f"imgevolve-r{n}-review", f"r{n} review: compare champions vs baselines (honest)", "reason",
        spec_text=f"Round {n}: read report_*.md in the imgevolve workdir. Which problems did evolution beat "
                  "random search on, by how much, any overfit flags? Compare to prior rounds if present.",
        depends=metrics_ids, constraints=["needs-human-judgment"])
    print(f"queued round {n}: {len(PROBLEMS)*3+1} nodes. Run: raptor-worklog serve --workers 1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
