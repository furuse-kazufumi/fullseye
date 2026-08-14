"""Re-bless the Wave-0 north-star gate after the op registry changes.

`tests/test_wave0.py` pins the denoise/edge champions and the decode of five fixed
genomes across every start sort, guarded by a registry *fingerprint* (the per-sort
candidate counts). Adding an op to `ops.REGISTRY` grows a sort's candidate list, so
`decode()`'s ``int(t * len(cands))`` index moves and the fingerprint no longer
matches — the strict pins then SKIP (they are honestly install-specific), which is
graceful (the suite stays green) but silently drops the north-star regression check.

This script regenerates `data/wave0_pins.json` from the CURRENT registry so the gate
keeps protecting after a deliberate op-add:

    py -3.11 recapture_wave0_pins.py            # show the delta, do not write
    py -3.11 recapture_wave0_pins.py --write    # write data/wave0_pins.json

The north-star check is a set of FIXED reference pipelines (name-pinned, core ops):
their score is invariant to op-adding, so a drop means a building-block op's behaviour
changed — a real regression the script refuses to persist without --force. (An evolved
champion is NOT used: at gens=8 it is search-variance — adding an op remaps decode()
indices, so the tiny search finds a different pipeline every time; proven 2026-08-14,
when the old edge champion pipeline still scored its exact old value after +35 ops
while the re-evolved champion drifted.) The five seed genomes and the decode pins are
the fingerprint that guards the install-specific strict pins; both are regenerated.
"""
from __future__ import annotations

import argparse
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PINS_PATH = os.path.join(HERE, "data", "wave0_pins.json")
SORTS = ["image", "region", "feature", "contour", "match", "volume", "any"]

# North-star = FIXED reference pipelines (name-pinned), NOT an evolved champion.
# Rationale (proven 2026-08-14): an evolved champion at gens=8 is search-variance —
# adding an op remaps decode() indices, so the tiny search finds a different (better
# or worse) pipeline every time, which is NOT a regression signal. A FIXED pipeline's
# score, by contrast, is invariant to op-adding (only that pipeline's own ops matter),
# so a drop is a REAL behaviour change in a building-block op — exactly what the gate
# should catch. These use core ops so they are install-independent.
REFERENCE_PIPELINES = {
    "denoise": [("gaussian", 0.4, 0.5), ("median", 0.3, 0.5)],
    "edge": [("dog", 0.5, 0.5), ("sobel_mag", 0.4, 0.5)],
}


def _seed_genomes():
    """The fixed gate genomes. Preferred source: the existing pins file (so the seed
    is defined once); fall back to the canonical construction if the file is absent."""
    if os.path.exists(PINS_PATH):
        with open(PINS_PATH, encoding="utf-8") as f:
            g = json.load(f).get("genomes")
        if g:
            return g
    import numpy as np
    n = 18
    return [[0.0] * n, [1.0] * n, [0.5] * n,
            list(np.linspace(0.0, 1.0, n)), [0.999999] * n]


def recapture() -> dict:
    import ops
    import problems
    genomes = _seed_genomes()
    cand_counts = {s: len(ops._candidates(s)) for s in SORTS}
    pins = [{s: ops.pipeline_str(g, s) for s in SORTS} for g in genomes]
    refs = {}
    for name, spec in REFERENCE_PIPELINES.items():
        prob = problems.PROBLEMS[name]
        stages = ops.decode_by_names(spec)  # fail-closed if a ref op is absent
        tr = prob.make(14, 64, 0)
        ho = prob.make(8, 64, 10_000)
        refs[name] = {
            "stages": [[s.op, float(s.a), float(s.b)] for s in stages],
            "pipeline": ops.stages_str(stages),
            "train": round(prob.score_stages(stages, tr), 4),
            "holdout": round(prob.score_stages(stages, ho), 4),
        }
    return {"cand_counts": cand_counts, "genomes": genomes, "pins": pins,
            "reference_pipelines": refs}


def _load_old():
    if os.path.exists(PINS_PATH):
        with open(PINS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return None


def _report(old, new) -> bool:
    """Print the delta; return True if no reference pipeline's score regressed.

    A fixed reference pipeline should score the SAME regardless of how many ops were
    added — a drop means a building-block op's behaviour changed (a real regression).
    """
    print("candidate counts:")
    for s in SORTS:
        o = (old or {}).get("cand_counts", {}).get(s)
        n = new["cand_counts"][s]
        mark = "" if o == n else f"  (was {o})"
        print(f"  {s:8s} {n}{mark}")
    ok = True
    old_refs = (old or {}).get("reference_pipelines", {})
    for prob, n in new["reference_pipelines"].items():
        o = old_refs.get(prob, {})
        dtr = None if not o else round(n["train"] - o["train"], 4)
        print(f"\n{prob} (reference): {n['pipeline']}")
        print(f"  train {n['train']}  holdout {n['holdout']}"
              + ("" if not o else f"   (was train {o['train']} holdout {o['holdout']}, dtrain {dtr:+})"))
        if o and n["train"] + 1e-9 < o["train"]:
            ok = False
            print(f"  [warn] {prob} reference pipeline dropped by {-dtr} — a building-block op "
                  f"changed behaviour; investigate before writing")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true", help="write data/wave0_pins.json")
    ap.add_argument("--force", action="store_true", help="write even if a champion regressed")
    a = ap.parse_args()
    old = _load_old()
    new = recapture()
    ok = _report(old, new)
    identical = old == new
    print("\nidentical to current pins:", identical)
    if a.write:
        if not ok and not a.force:
            print("[abort] a champion regressed; re-run with --force if this is intended")
            return 1
        os.makedirs(os.path.dirname(PINS_PATH), exist_ok=True)
        with open(PINS_PATH, "w", encoding="utf-8") as f:
            json.dump(new, f, ensure_ascii=False, indent=1)
        print(f"[ok] wrote {PINS_PATH}")
    else:
        print("(dry run — pass --write to update data/wave0_pins.json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
