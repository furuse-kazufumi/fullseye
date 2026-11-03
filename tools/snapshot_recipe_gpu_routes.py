"""Snapshot which recipe stage ops have a GPU route in pipeline context (``gpu_route.route(op, "pipeline")``).

``gpu_route`` is not on master yet (it lives on the GPU branch's worktree). This tool reads it **read-only**
and writes ``docs/recipe_gpu_routes.json``; ``tools/gen_recipe_coverage.py`` reads only that snapshot, so the
coverage table is deterministic and ``regen_all --check`` does not depend on the other worktree.

    py -3.11 tools/snapshot_recipe_gpu_routes.py --gpu-worktree C:/dev/projects/imgevolve_wt_gpu_cross

The routes are asked twice, each in its own process:

* ``repo_first`` — this repo on ``sys.path`` first, the GPU worktree appended at the END (only ``gpu_route``
  itself comes from there; ``accel`` and the other tables it reads come from this repo).
* ``gpu_first`` — the GPU worktree alone (its own ``accel`` tables; the state the GPU branch will merge).

★2026-11-03 実測: 2 つは 6 op で食い違った(area_center / count_obj / remove_small / select_largest /
select_shape ... の accel 経路は GPU の枝の ``accel`` にだけある)。``gpu_route`` が読む表は枝の側が正本なので
**``routes`` には gpu_first を採り**、repo_first との差は ``repo_first_differs`` に残す。

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

_PROBE = r"""
import json, os, sys
ops = json.loads(sys.stdin.read())
import gpu_route
out = {}
for op in ops:
    r = gpu_route.route(op, "pipeline")
    out[op] = None if r is None else {"kind": r.kind, "use": r.use,
                                      "ratio": None if r.ratio is None else round(float(r.ratio), 3)}
print(json.dumps({"module": gpu_route.__file__, "routes": out}))
"""


def recipe_ops() -> list:
    data = json.loads((ROOT / "fullseye/data/RECIPE_INDEX.json").read_text(encoding="utf-8"))
    return sorted({st["op"] for r in data["recipes"] for st in r["stages"]})


def _ask(pythonpath: str, cwd: str, ops: list) -> dict:
    env = dict(os.environ, PYTHONPATH=pythonpath, FULLSEYE_DEVICE="cpu")
    p = subprocess.run([sys.executable, "-c", _PROBE], input=json.dumps(ops), capture_output=True,
                       text=True, cwd=cwd, env=env, check=False)
    if p.returncode != 0:
        raise SystemExit("gpu_route probe failed (%s):\n%s" % (pythonpath, p.stderr[-2000:]))
    return json.loads(p.stdout.strip().splitlines()[-1])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--gpu-worktree", required=True)
    a = ap.parse_args(argv)
    wt = os.path.abspath(a.gpu_worktree)
    if not os.path.isfile(os.path.join(wt, "gpu_route.py")):
        print("no gpu_route.py in %s" % wt, file=sys.stderr)
        return 2
    ops = recipe_ops()
    repo_first = _ask(os.pathsep.join([str(ROOT), wt]), str(ROOT), ops)
    gpu_first = _ask(wt, wt, ops)
    commit = subprocess.run(["git", "-C", wt, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    routes = gpu_first["routes"]
    differs = {op: {"repo_first": repo_first["routes"][op], "gpu_first": routes[op]}
               for op in ops if repo_first["routes"][op] != routes[op]}
    data = {"method": "gpu_route.route(op, 'pipeline'), read-only, from the GPU worktree on its own (gpu_first); "
                      "null = no matching GPU route; ops absent from this table are unmeasured. "
                      "repo_first_differs = ops whose answer changes when this repo's tables are on sys.path first.",
            "gpu_worktree_commit": commit, "n_ops": len(routes),
            "n_with_route": sum(v is not None for v in routes.values()),
            "n_with_route_repo_first": sum(v is not None for v in repo_first["routes"].values()),
            "repo_first_differs": differs, "routes": routes}
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(OUT, data["n_with_route"], "/", data["n_ops"], "(repo_first %d, differ %d)"
          % (data["n_with_route_repo_first"], len(differs)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
