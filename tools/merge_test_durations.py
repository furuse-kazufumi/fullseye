"""Merge pytest-split duration files into one deterministic baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def merge(paths: list[Path]) -> dict[str, float]:
    """Return the union of *paths*, keeping the slowest duplicate observation."""
    merged: dict[str, float] = {}
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"{path}: expected a JSON object")
        for nodeid, duration in data.items():
            if not isinstance(nodeid, str) or not isinstance(duration, (int, float)):
                raise ValueError(f"{path}: invalid duration entry {nodeid!r}: {duration!r}")
            if duration < 0:
                raise ValueError(f"{path}: negative duration for {nodeid}")
            merged[nodeid] = max(merged.get(nodeid, 0.0), float(duration))
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("-o", "--output", required=True, type=Path)
    args = parser.parse_args()
    result = merge(args.files)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=4, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"merged {len(result)} test durations into {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
