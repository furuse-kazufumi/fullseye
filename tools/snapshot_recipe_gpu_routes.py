"""Snapshot which recipe stage ops have a GPU route in pipeline context (``gpu_route.route(op, "pipeline")``).

``gpu_route`` is not on master yet (it lives on the GPU branch's worktree). This tool reads it **read-only**
from a worktree given on the command line, appended to the END of ``sys.path`` (this repo's modules win),
and writes ``docs/recipe_gpu_routes.json``. ``tools/gen_recipe_coverage.py`` reads only that snapshot, so the
coverage table is deterministic and ``regen_all --check`` does not depend on the other worktree.

    py -3.11 tools/snapshot_recipe_gpu_routes.py --gpu-worktree C:/dev/projects/imgevolve_wt_gpu_cross

Not part of regen_all (needs the other worktree). Re-run it when recipes gain ops or the GPU ledger moves;
ops that are missing from the snapshot are shown as 未計測 (unmeasured), never as "no GPU".
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "recipe_gpu_routes.json"


def recipe_ops() -> list:
    data = json.loads((ROOT / "fullseye/data/RECIPE_INDEX.json").read_text(encoding="utf-8"))
    return sorted({st["op"] for r in data["recipes"] for st in r["stages"]})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--gpu-worktree", required=True)
    a = ap.parse_args(argv)
    wt = os.path.abspath(a.gpu_worktree)
    if not os.path.isfile(os.path.join(wt, "gpu_route.py")):
        print("no gpu_route.py in %s" % wt, file=sys.stderr)
        return 2
    os.environ["FULLSEYE_DEVICE"] = "cpu"
    sys.path.insert(0, str(ROOT))
    import fullseye  # noqa: F401  (engine modules on sys.path, ahead of the GPU worktree)
    sys.path.append(wt)
    import gpu_route
    commit = subprocess.run(["git", "-C", wt, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    routes = {}
    for op in recipe_ops():
        r = gpu_route.route(op, "pipeline")
        routes[op] = None if r is None else {"kind": r.kind, "use": r.use,
                                              "ratio": None if r.ratio is None else round(float(r.ratio), 3)}
    data = {"method": "gpu_route.route(op, 'pipeline') from a read-only GPU worktree appended to sys.path; "
                      "null = no matching GPU route; ops absent from this table are unmeasured",
            "gpu_route_module": os.path.relpath(gpu_route.__file__, wt).replace("\\", "/"),
            "gpu_worktree_commit": commit, "n_ops": len(routes),
            "n_with_route": sum(v is not None for v in routes.values()), "routes": routes}
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=False) + "\n", encoding="utf-8", newline="\n")
    print(OUT, data["n_with_route"], "/", data["n_ops"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
