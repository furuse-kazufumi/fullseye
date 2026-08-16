"""Condense an evolved champion pipeline into a registered macro ("DNA") operator.

This is the write-side of the self-expanding registry (read-side: backends_macro.py).
It takes a ``champion_<problem>.json`` produced by ``evolve.py`` / ``robust.py``,
freezes its name-pinned stages into one entry of ``data/macro_champions.json``, and
records HONEST provenance: the full-registry train/holdout/locked score of the frozen
pipeline (recomputed here, not copied blindly) plus the trivial and hand baselines on
the same splits — including a verdict on whether it actually beats the hand baseline
on the LOCKED holdout (the strongest honesty guard). After writing, add
``"backends_macro"`` to ops.py's backend list (once) and run
``recapture_wave0_pins.py --write`` to re-bless the Wave-0 gate.

    py -3.11 champion_to_macro.py --champion out/macro_denoise/champion_denoise.json \
        --name macro_denoise --seeds 8 --gens 80 --pop 28

Correctness notes it enforces (fail-closed):
  * every DNA op must exist in the FULL registry (else the macro can't run);
  * it WARNS if a DNA op name is overridden by a backend (core vs backend semantics
    differ, so the evolution-time score may not equal the full-registry score);
  * it recomputes the score in the full registry and stores THAT (the op's real
    behaviour), disclosing any gap from the evolution-time (recorded) score.
"""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DNA_PATH = os.path.join(HERE, "data", "macro_champions.json")
PY_STORE_PATH = os.path.join(HERE, "macro_champions_data.py")


def _write_py_store(entries) -> None:
    """Mirror the entries into macro_champions_data.py — the RUNTIME store
    backends_macro reads. A flat-layout .py always ships in the wheel, whereas
    data/*.json does not, so this is what makes macro ops register on a pip-installed
    package (not only the editable source tree). Kept in sync with the JSON here."""
    import pprint
    hdr = (
        '"""Generated DNA store for macro ("self-expanding registry") ops — DO NOT hand-edit.\n\n'
        "Written by champion_to_macro.py alongside the human-readable data/macro_champions.json.\n"
        "This is the RUNTIME source backends_macro.py reads: as a plain py-module it always\n"
        "ships in the wheel (flat-layout data files under data/ do NOT), so macro ops register\n"
        'on a pip-installed package, not only in the editable source tree.\n"""\n'
        "from __future__ import annotations\n\nMACROS = "
    )
    with open(PY_STORE_PATH, "w", encoding="utf-8") as f:
        f.write(hdr)
        f.write(pprint.pformat(entries, width=100, sort_dicts=False))
        f.write("\n")

# The canonical strong hand baselines per problem, for an honest side-by-side. The
# denoise reference matches tests/data/wave0_pins.json (gaussian -> median).
REFERENCE_PIPELINES = {
    "denoise": [("gaussian", 0.4, 0.5), ("median", 0.3, 0.5)],
    "edge": [("dog", 0.5, 0.5), ("sobel_mag", 0.4, 0.5)],
}


def _overridden_core_names(ops) -> set:
    """Core op names that a backend re-defines (last occurrence wins in RT/_BY_NAME)."""
    dup = {n for n, k in Counter(op.name for op in ops.REGISTRY).items() if k > 1}
    core = {n for (n, *_rest) in ops._DEFS}
    return dup & core


def _score3(ops, prob, stages, cfg) -> dict:
    """train / holdout / locked score of a decoded pipeline on a problem's splits."""
    tr = prob.make(cfg["n_train"], cfg["size"], cfg["seed"])
    ho = prob.make(cfg["n_holdout"], cfg["size"], cfg["seed"] + 10_000)
    lk = prob.make(cfg.get("n_locked", cfg["n_holdout"]), cfg["size"], cfg["seed"] + 20_000)
    return {
        "train": round(prob.score_stages(stages, tr), 4),
        "holdout": round(prob.score_stages(stages, ho), 4),
        "locked_holdout": round(prob.score_stages(stages, lk), 4),
    }


def build_entry(champion_path: str, name: str, meta: dict) -> dict:
    import ops
    import problems

    ch = json.loads(open(champion_path, encoding="utf-8").read())
    stages_spec = ch.get("pipeline_stages")
    if not stages_spec:
        raise SystemExit(f"[abort] {champion_path} has no 'pipeline_stages' (name-pinned "
                         "record) — re-evolve with the current evolve.py")
    problem = ch["problem"]
    if problem not in problems.PROBLEMS:
        raise SystemExit(f"[abort] unknown problem {problem!r}")
    prob = problems.PROBLEMS[problem]
    cfg = ch["config"]

    used = [s["op"] for s in stages_spec]
    missing = [u for u in used if u not in ops._BY_NAME]
    if missing:
        raise SystemExit(f"[abort] DNA ops absent in the full registry: {missing}")
    overridden = sorted(set(used) & _overridden_core_names(ops))

    # Recompute the score in the FULL registry (the op's real behaviour) and compare
    # to the evolution-time recorded score. They match iff no DNA op is overridden.
    stages = ops.decode_by_names(stages_spec)
    full = _score3(ops, prob, stages, cfg)
    recorded = {"train": ch.get("train"), "holdout": ch.get("holdout"),
                "locked_holdout": ch.get("locked_holdout")}

    # Honest baselines on the same splits.
    trivial = _score3(ops, prob, ops.decode_by_names([]), cfg)
    hand = _score3(ops, prob, prob.hand_stages(), cfg)
    baselines = {"trivial": trivial, "hand": hand}
    if problem in REFERENCE_PIPELINES:
        ref = ops.decode_by_names(REFERENCE_PIPELINES[problem])
        baselines["reference"] = _score3(ops, prob, ref, cfg)

    out_sort = ops._BY_NAME[stages_spec[-1]["op"]].out_sort
    in_sort = prob.in_sort

    # Honest verdict against the strongest available hand baseline on the LOCKED split.
    hand_ref = baselines.get("reference", hand)
    beats_locked = full["locked_holdout"] > hand_ref["locked_holdout"]

    entry = {
        "name": name,
        "category": "macro",
        "problem": problem,
        "in_sort": in_sort,
        "out_sort": out_sort,
        "stages": [{"op": s["op"], "a": float(s["a"]), "b": float(s["b"])} for s in stages_spec],
        "pipeline": ops.stages_str(stages),
        "provenance": {
            "source": "evolve.py / robust.py, core-only search (IMGEVOLVE_NO_BACKENDS=1)",
            "champion_file": os.path.relpath(champion_path, HERE).replace("\\", "/"),
            "unit": prob.unit,
            "config": cfg,
            "seeds": meta.get("seeds"), "gens": ch.get("gens"), "pop": ch.get("pop"),
            "selected_seed": ch.get("seed"),
            "captured": meta.get("date"),
            "score": full,                       # full-registry score = the op's real behaviour
            "recorded_evolution_score": recorded,  # score at evolution time (NO_BACKENDS)
            "score_matches_evolution": full == {k: recorded[k] for k in full},
            "overridden_ops": overridden,         # non-empty => semantics could differ (see warning)
            "baselines": baselines,
            "beats_hand_on_locked_holdout": bool(beats_locked),
            "honest_note": (
                "A macro op is the exact evolved pipeline, knobs frozen; its score is "
                "recomputed here in the full registry. beats_hand_on_locked_holdout states, "
                "without spin, whether it beats the strongest hand baseline on the locked "
                "split (the one honesty guard evolution never selected on)."
            ),
        },
    }
    # Console disclosure.
    print(f"[macro] {name}  ({problem}, {in_sort}->{out_sort})")
    print(f"  pipeline: {entry['pipeline']}")
    print(f"  full-registry score  train {full['train']}  holdout {full['holdout']}  "
          f"locked {full['locked_holdout']}  ({prob.unit})")
    print(f"  evolution recorded   train {recorded['train']}  holdout {recorded['holdout']}  "
          f"locked {recorded['locked_holdout']}   (matches full: {entry['provenance']['score_matches_evolution']})")
    print(f"  trivial   locked {trivial['locked_holdout']}   hand locked {hand['locked_holdout']}"
          + (f"   reference locked {baselines['reference']['locked_holdout']}" if "reference" in baselines else ""))
    print(f"  beats hand on LOCKED holdout: {beats_locked}")
    if overridden:
        print(f"  [warn] DNA uses backend-overridden op(s) {overridden}: evolution-time (core) "
              "semantics differ from full-registry; the stored score is the full-registry one.")
    return entry


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--champion", required=True, help="path to champion_<problem>.json")
    ap.add_argument("--name", required=True, help="registry name for the macro op (e.g. macro_denoise)")
    ap.add_argument("--seeds", type=int, default=None, help="seeds used by robust.py (provenance only)")
    ap.add_argument("--date", default=None, help="capture date (provenance only); default: unset")
    ap.add_argument("--force", action="store_true", help="overwrite an existing entry of the same name")
    ap.add_argument("--allow-regression", action="store_true",
                    help="register even if the macro does NOT beat the hand baseline on the "
                         "locked holdout (off by default — the honesty guard is enforced, not just printed)")
    ap.add_argument("--dry-run", action="store_true", help="print the entry; do not write the file")
    a = ap.parse_args()

    entry = build_entry(a.champion, a.name, {"seeds": a.seeds, "date": a.date})

    # ★Enforce the headline honesty claim ("a DNA op is added only when it beats the
    # hand baseline on a LOCKED holdout") — previously this flag was printed but never
    # gated, so a worse-than-hand macro could be registered and then selected by the
    # next evolution.  The gate refuses that unless it is explicitly overridden.
    beats = bool(entry.get("provenance", {}).get("beats_hand_on_locked_holdout", False))
    if not beats and not a.allow_regression:
        raise SystemExit(
            f"[abort] {a.name} does NOT beat the hand baseline on the locked holdout "
            f"(beats_hand_on_locked_holdout=False). Refusing to register a non-improving "
            f"DNA op. Pass --allow-regression to override deliberately (disclosed in provenance).")

    entries = []
    if os.path.exists(DNA_PATH):
        entries = json.loads(open(DNA_PATH, encoding="utf-8").read() or "[]")
        if isinstance(entries, dict):
            entries = entries.get("macros", [])
    names = [e["name"] for e in entries]
    if a.name in names and not a.force:
        raise SystemExit(f"[abort] {a.name} already present; pass --force to overwrite")
    entries = [e for e in entries if e["name"] != a.name] + [entry]

    if a.dry_run:
        print("\n(dry run — not writing", DNA_PATH + ")")
        return 0
    os.makedirs(os.path.dirname(DNA_PATH), exist_ok=True)
    with open(DNA_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)
    _write_py_store(entries)  # runtime store that ships in the wheel
    print(f"\n[ok] wrote {DNA_PATH} + {os.path.basename(PY_STORE_PATH)}  ({len(entries)} macro op(s))")
    print("  next: add \"backends_macro\" to ops.py's backend list (once), then "
          "`py -3.11 recapture_wave0_pins.py --write`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
