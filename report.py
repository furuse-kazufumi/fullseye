"""S1 — honest gate / metrics (per problem).

Compares the evolved champion against trivial/hand/random on HOLDOUT, computes the
generalization gap, and raises an honest overfit flag when the champion does not
beat the best baseline on holdout, or the gap is large. A loss is reported as a
loss. Writes metrics_<problem>.json + report_<problem>.md.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--problem", default="denoise")
    ap.add_argument("--workdir", default="out/worklog/imgevolve")
    ap.add_argument("--gap-threshold", type=float, default=0.1,
                    help="fraction of champion holdout; train-holdout gap above this flags overfit")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    wd = Path(a.workdir)
    base = json.loads((wd / f"baseline_{a.problem}.json").read_text(encoding="utf-8"))
    champ = json.loads((wd / f"champion_{a.problem}.json").read_text(encoding="utf-8"))
    unit = champ["unit"]

    triv = base["trivial"]["holdout"]
    hand = base["hand"]["holdout"]
    rand = base["random"]["holdout"]
    best_base = max(hand, rand)
    c_ho, c_tr = champ["holdout"], champ["train"]
    gap = round(c_tr - c_ho, 4)
    gap_limit = a.gap_threshold * abs(c_ho) if c_ho else a.gap_threshold
    beats_baseline = c_ho > best_base
    overfit = (not beats_baseline) or (gap > gap_limit)

    metrics = {
        "problem": a.problem, "unit": unit,
        "holdout": {"trivial": triv, "hand": hand, "random": rand, "champion": c_ho},
        "champion_pipeline": champ["pipeline"], "champion_train": c_tr,
        "generalization_gap": gap,
        "beats_hand": c_ho > hand, "beats_random_search": c_ho > rand,
        "beats_best_baseline": beats_baseline,
        "improvement_over_best_baseline": round(c_ho - best_base, 4),
        "improvement_over_random": round(c_ho - rand, 4),
        "overfit_flag": overfit,
    }
    (wd / f"metrics_{a.problem}.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    verdict = ("evolution beat the best baseline on holdout"
               if beats_baseline else "evolution did NOT beat the baseline on holdout (honest loss)")
    md = [
        f"# imgevolve S1 — {a.problem} ({unit})",
        "",
        f"**Verdict:** {verdict}" + ("  ⚠️ overfit flag" if overfit else "  (no overfit flag)"),
        "",
        f"## Holdout ({unit}, higher better)",
        "| reference | holdout |", "|---|---|",
        f"| trivial (do nothing) | {triv:.3f} |",
        f"| hand-built | {hand:.3f} |",
        f"| random search | {rand:.3f} |",
        f"| **evolved champion** | **{c_ho:.3f}** |",
        "",
        "## Champion (the designed algorithm)",
        f"- pipeline: `{champ['pipeline']}`",
        f"- train {c_tr:.3f} / holdout {c_ho:.3f} / gap {gap:.3f} "
        f"({'>' if gap > gap_limit else '<='} limit {gap_limit:.3f})",
        "",
        "## Honest read",
        f"- vs best baseline: {metrics['improvement_over_best_baseline']:+.3f} {unit} on holdout",
        f"- vs random search: {metrics['improvement_over_random']:+.3f} {unit}",
        f"- overfit flag: **{overfit}**",
    ]
    report = "\n".join(md) + "\n"
    (wd / f"report_{a.problem}.md").write_text(report, encoding="utf-8")
    if a.out:
        p = a.out if a.out.endswith(".md") else a.out + ".md"
        Path(p).write_text(report, encoding="utf-8")
    print(f"[report:{a.problem}] champion {c_ho:.3f} vs best baseline {best_base:.3f} (overfit={overfit})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
