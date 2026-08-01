"""S0 — the honest floor.

Measures three references on a train/holdout split so S1's evolution has an
honest yardstick (nothing here is 'the answer'; it is what evolution must beat):

  - noisy    : do nothing (PSNR of the noisy input vs clean) — the absolute floor.
  - hand     : a hand-built fixed Gaussian denoiser (sigma=1.0) — the expert guess.
  - random   : best of N random pipelines *selected on train*, reported on holdout
               (same protocol as evolution, so S1's win over `random` isolates the
               value of *search* over blind sampling).

Writes baseline.json into the shared workdir. Deterministic (seeded).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import ops


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workdir", default="out/worklog/imgevolve")
    ap.add_argument("--out", default=None, help="also copy baseline.json here (<OUT>.json)")
    ap.add_argument("--n-train", type=int, default=12)
    ap.add_argument("--n-holdout", type=int, default=6)
    ap.add_argument("--size", type=int, default=64)
    ap.add_argument("--noise", type=float, default=0.12)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--random-samples", type=int, default=200)
    a = ap.parse_args()

    wd = Path(a.workdir); wd.mkdir(parents=True, exist_ok=True)
    # disjoint splits: train seed vs holdout seed are different generators.
    c_tr, n_tr = ops.make_dataset(a.n_train, a.size, a.noise, seed=a.seed)
    c_ho, n_ho = ops.make_dataset(a.n_holdout, a.size, a.noise, seed=a.seed + 10_000)

    # do-nothing floor
    noisy_tr = float(np.mean([ops.psnr(n_tr[i], c_tr[i]) for i in range(len(c_tr))]))
    noisy_ho = float(np.mean([ops.psnr(n_ho[i], c_ho[i]) for i in range(len(c_ho))]))

    # hand-built: single Gaussian sigma=1.0  -> genome slot0 = gaussian, a s.t. sigma≈1.0
    a_for_sigma1 = (1.0 - 0.3) / 2.7  # invert 0.3+2.7a
    hand = np.zeros(ops.GENOME_LEN)
    hand[0] = (1 + 0.5) / ops.N_OPS  # op index 1 = gaussian
    hand[1] = a_for_sigma1
    hand_tr = ops.mean_psnr_over(hand, c_tr, n_tr)
    hand_ho = ops.mean_psnr_over(hand, c_ho, n_ho)

    # random search: select best on TRAIN, report holdout (fair protocol)
    rng = np.random.default_rng(a.seed + 777)
    best_g, best_tr = None, -1e9
    for _ in range(a.random_samples):
        g = rng.random(ops.GENOME_LEN)
        s = ops.mean_psnr_over(g, c_tr, n_tr)
        if s > best_tr:
            best_tr, best_g = s, g
    rand_ho = ops.mean_psnr_over(best_g, c_ho, n_ho)

    result = {
        "config": {"n_train": a.n_train, "n_holdout": a.n_holdout, "size": a.size,
                   "noise": a.noise, "seed": a.seed, "random_samples": a.random_samples},
        "noisy": {"train_psnr": round(noisy_tr, 4), "holdout_psnr": round(noisy_ho, 4)},
        "hand": {"train_psnr": round(hand_tr, 4), "holdout_psnr": round(hand_ho, 4),
                 "pipeline": ops.pipeline_str(hand)},
        "random": {"train_psnr": round(best_tr, 4), "holdout_psnr": round(rand_ho, 4),
                   "pipeline": ops.pipeline_str(best_g), "genome": best_g.tolist()},
    }
    (wd / "baseline.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    if a.out:
        Path(a.out if a.out.endswith(".json") else a.out + ".json").write_text(
            json.dumps(result, indent=2), encoding="utf-8")
    print(f"[baseline] noisy holdout {noisy_ho:.2f} dB | hand {hand_ho:.2f} | "
          f"random {rand_ho:.2f} -> {wd/'baseline.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
