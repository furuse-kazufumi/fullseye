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

It prints the champion delta so a human can confirm the op-add did not *break* or
*catastrophically degrade* the evolution (a genuine new op should never lower the
champion below the old value by more than search noise; it may raise it). The five
seed genomes are the fixed gate definition and are preserved verbatim.

Honest note: after an op-add the denoise/edge champion may legitimately CHANGE (a
richer candidate set is a different search landscape). Re-capturing tracks the new
state; it does not certify the old champion — that is what the delta print is for.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PINS_PATH = os.path.join(HERE, "data", "wave0_pins.json")
SORTS = ["image", "region", "feature", "contour", "match", "volume", "any"]


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
    import evolve
    import ops
    genomes = _seed_genomes()
    cand_counts = {s: len(ops._candidates(s)) for s in SORTS}
    pins = [{s: ops.pipeline_str(g, s) for s in SORTS} for g in genomes]
    with tempfile.TemporaryDirectory() as td:
        dz = evolve.run("denoise", workdir=td, gens=8, pop=12, seed=0, verbose=False)
        eg = evolve.run("edge", workdir=td, gens=8, pop=12, seed=4, verbose=False)
    return {
        "cand_counts": cand_counts,
        "genomes": genomes,
        "pins": pins,
        "denoise": {"pipeline": dz["pipeline"], "train": dz["train"], "holdout": dz["holdout"]},
        "edge": {"pipeline": eg["pipeline"], "train": eg["train"], "holdout": eg["holdout"]},
    }


def _load_old():
    if os.path.exists(PINS_PATH):
        with open(PINS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return None


def _report(old, new) -> bool:
    """Print the delta; return True if the champions did not regress."""
    print("candidate counts:")
    for s in SORTS:
        o = (old or {}).get("cand_counts", {}).get(s)
        n = new["cand_counts"][s]
        mark = "" if o == n else f"  (was {o})"
        print(f"  {s:8s} {n}{mark}")
    ok = True
    for prob in ("denoise", "edge"):
        n = new[prob]
        o = (old or {}).get(prob, {})
        dtr = None if not o else round(n["train"] - o["train"], 4)
        print(f"\n{prob}: {n['pipeline']}")
        print(f"  train {n['train']}  holdout {n['holdout']}"
              + ("" if not o else f"   (was train {o['train']} holdout {o['holdout']}, dtrain {dtr:+})"))
        if o and n["train"] + 1e-9 < o["train"]:
            ok = False
            print(f"  [warn] {prob} champion train dropped by {-dtr} — investigate before writing")
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
