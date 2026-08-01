"""imgevolve quickstart — the whole workflow in one runnable file.

    py -3.11 examples/quickstart.py

Shows: (1) the operator registry, (2) applying a typed hand pipeline, (3) decoding
a genome, (4) scoring on a task, (5) running the evolution driver, (6) codegen +
differential test. Run from the repo root (so `import ops` resolves).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ops  # noqa: E402
import problems  # noqa: E402

PY = sys.executable
ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    # 1. what's in the registry
    cats = ops.categories()
    print(f"registry: {ops.N_OPS} ops, {len(cats)} categories, "
          f"sorts={sorted({o.in_sort for o in ops.REGISTRY} | {o.out_sort for o in ops.REGISTRY})}")

    # 2. apply a typed HAND pipeline (image -> image): edge-preserving denoise
    img = problems._make_denoise(1, 64, 0)["input"][0]
    stages = [ops.stage("median", 0.3, 0.0), ops.stage("bilateral", 0.4, 0.1)]
    out = ops.run_stages(stages, img)
    print("hand pipeline:", " -> ".join(s.op for s in stages),
          f"| shape {out.shape}, mean {out.mean():.3f}")

    # 3. a full HALCON-shaped chain image -> region -> feature (count blobs)
    chain = [ops.stage("gaussian", 0.3, 0), ops.stage("otsu", 0, 0),
             ops.stage("remove_small", 0.2, 0), ops.stage("blob_count", 0, 0)]
    print("count chain:", " -> ".join(s.op for s in chain), "=>", float(ops.run_stages(chain, img)))

    # 4. an XLD contour chain image -> contour -> region
    xld = [ops.stage("edges_sub_pix", 0.2, 0), ops.stage("select_contours", 0.2, 0),
           ops.stage("contours_to_region", 0.3, 0)]
    reg = ops.run_stages(xld, img)
    print("XLD chain:", " -> ".join(s.op for s in xld), f"| region pixels {int(reg.sum())}")

    # 5. score a random genome on a task, then decode it to a readable pipeline
    prob = problems.PROBLEMS["count"]
    data = prob.make(6, 64, 0)
    g = np.random.default_rng(0).random(ops.GENOME_LEN)
    print(f"random genome scores {prob.score(g, data):.3f} {prob.unit} | pipeline: {ops.pipeline_str(g)}")

    # 6. drive evolve -> codegen -> difftest (writes into a scratch workdir)
    wd = ROOT / "out" / "quickstart"
    for argv in (["baseline.py", "--problem", "edge", "--workdir", str(wd), "--seed", "0"],
                 ["evolve.py", "--problem", "edge", "--workdir", str(wd), "--gens", "30", "--seed", "0"],
                 ["codegen.py", "--problem", "edge", "--workdir", str(wd)],
                 ["difftest.py", "--problem", "edge", "--workdir", str(wd)]):
        r = subprocess.run([PY, str(ROOT / argv[0]), *argv[1:]], cwd=str(ROOT), capture_output=True, text=True)
        print("  " + (r.stdout.strip().splitlines() or [""])[-1])

    print("\ngenerated backend:", wd / "gen_edge.py", "(+ gen_edge.c). See docs/EXAMPLES.md for library recipes.")


if __name__ == "__main__":
    main()
