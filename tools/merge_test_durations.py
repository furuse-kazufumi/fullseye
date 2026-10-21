"""Merge pytest-split duration files into one deterministic baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def merge(paths: list[Path], baseline: dict[str, float] | None = None) -> dict[str, float]:
    """Return the union of *paths*, keeping the slowest duplicate observation.

    pytest-split's ``--store-durations`` rewrites the whole file: tests that did not run
    in that shard keep the value they had before.  Those carried-over values are **not**
    observations, so with *baseline* (the file the shards started from) a value equal to
    the baseline entry is ignored; a test nobody measured keeps its baseline value.
    Without *baseline* every value counts (the 2026-10-22 run showed why that is wrong:
    the seed's mean-value placeholders won ``max`` against every real duration under it).
    """
    baseline = dict(baseline or {})
    observed: dict[str, float] = {}
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"{path}: expected a JSON object")
        for nodeid, duration in data.items():
            if not isinstance(nodeid, str) or not isinstance(duration, (int, float)):
                raise ValueError(f"{path}: invalid duration entry {nodeid!r}: {duration!r}")
            if duration < 0:
                raise ValueError(f"{path}: negative duration for {nodeid}")
            base = baseline.get(nodeid)
            if base is not None and abs(float(duration) - base) < 1e-12:
                continue
            observed[nodeid] = max(observed.get(nodeid, 0.0), float(duration))
    merged = dict(baseline)
    merged.update(observed)
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("-o", "--output", required=True, type=Path)
    parser.add_argument("--baseline", type=Path, default=None,
                        help="the durations file the shards started from; values equal to it are carried over, not observed")
    args = parser.parse_args()
    baseline = None
    if args.baseline is not None:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        if not isinstance(baseline, dict):
            raise ValueError(f"{args.baseline}: expected a JSON object")
    result = merge(args.files, baseline)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=4, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    n_obs = len(result) if baseline is None else sum(1 for k, v in result.items() if baseline.get(k) != v)
    print(f"merged {len(result)} test durations into {args.output} ({n_obs} observed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
