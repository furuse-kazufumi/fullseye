"""S1 — honest gate / metrics.

Compares the evolved champion against the S0 baselines on HOLDOUT, computes the
generalization gap (train - holdout), and raises an honest overfit flag when the
champion does not actually beat the best baseline on holdout, or when the gap is
large. Writes metrics.json + report.md. The report is deliberately un-spun: a loss
is reported as a loss (honest disclosure).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workdir", default="out/worklog/imgevolve")
    ap.add_argument("--gap-threshold", type=float, default=1.5, help="dB train-holdout gap that flags overfit")
    ap.add_argument("--out", default=None, help="also copy report.md here (<OUT>.md)")
    a = ap.parse_args()

    wd = Path(a.workdir)
    base = json.loads((wd / "baseline.json").read_text(encoding="utf-8"))
    champ = json.loads((wd / "champion.json").read_text(encoding="utf-8"))

    noisy_ho = base["noisy"]["holdout_psnr"]
    hand_ho = base["hand"]["holdout_psnr"]
    rand_ho = base["random"]["holdout_psnr"]
    best_base_ho = max(hand_ho, rand_ho)
    champ_ho = champ["holdout_psnr"]
    champ_tr = champ["train_psnr"]

    gap = round(champ_tr - champ_ho, 4)
    beats_hand = champ_ho > hand_ho
    beats_random = champ_ho > rand_ho
    beats_baseline = champ_ho > best_base_ho
    overfit = (not beats_baseline) or (gap > a.gap_threshold)

    metrics = {
        "holdout_psnr": {"noisy": noisy_ho, "hand": hand_ho, "random": rand_ho, "champion": champ_ho},
        "champion_pipeline": champ["pipeline"],
        "champion_train_psnr": champ_tr,
        "generalization_gap_db": gap,
        "beats_hand": beats_hand,
        "beats_random_search": beats_random,
        "beats_best_baseline": beats_baseline,
        "improvement_over_best_baseline_db": round(champ_ho - best_base_ho, 4),
        "improvement_over_noisy_db": round(champ_ho - noisy_ho, 4),
        "overfit_flag": overfit,
    }
    (wd / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    verdict = ("evolution beat the best baseline on holdout"
               if beats_baseline else "evolution did NOT beat the baseline on holdout (honest loss)")
    md = [
        "# imgevolve S1 — honest metrics",
        "",
        f"**Verdict:** {verdict}"
        + ("  ⚠️ overfit flag raised" if overfit else "  (no overfit flag)"),
        "",
        "## Holdout PSNR (dB, higher better)",
        "| reference | holdout |",
        "|---|---|",
        f"| noisy (do nothing) | {noisy_ho:.2f} |",
        f"| hand-built (fixed Gaussian) | {hand_ho:.2f} |",
        f"| random search (best-on-train) | {rand_ho:.2f} |",
        f"| **evolved champion** | **{champ_ho:.2f}** |",
        "",
        "## Champion (the designed algorithm)",
        f"- pipeline: `{champ['pipeline']}`",
        f"- train PSNR: {champ_tr:.2f} dB",
        f"- holdout PSNR: {champ_ho:.2f} dB",
        f"- generalization gap (train-holdout): {gap:.2f} dB "
        f"({'>' if gap > a.gap_threshold else '<='} threshold {a.gap_threshold})",
        "",
        "## Honest read",
        f"- vs best baseline: {metrics['improvement_over_best_baseline_db']:+.2f} dB on holdout",
        f"- vs doing nothing: {metrics['improvement_over_noisy_db']:+.2f} dB on holdout",
        f"- overfit flag: **{overfit}** "
        + ("(champion did not beat baseline OR gap too large — do NOT proceed to S2 blindly)"
           if overfit else "(clean — safe to consider S2)"),
    ]
    report = "\n".join(md) + "\n"
    (wd / "report.md").write_text(report, encoding="utf-8")
    if a.out:
        Path(a.out if a.out.endswith(".md") else a.out + ".md").write_text(report, encoding="utf-8")
    print(f"[report] champion holdout {champ_ho:.2f} vs best baseline {best_base_ho:.2f} "
          f"(overfit={overfit}) -> {wd/'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
