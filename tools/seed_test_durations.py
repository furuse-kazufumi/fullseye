"""Fill missing pytest-split entries with its own mean-duration fallback.

This is only for bootstrapping a checked-in baseline after an interrupted first
measurement.  Subsequent CI artifacts replace estimates with observations.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    path = Path(".test_durations")
    durations = json.loads(path.read_text(encoding="utf-8"))
    output = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    nodeids = {line.strip() for line in output.splitlines() if line.startswith("tests/") and "::" in line}
    fallback = sum(durations.values()) / len(durations) if durations else 1.0
    added = 0
    for nodeid in nodeids:
        if nodeid not in durations:
            durations[nodeid] = fallback
            added += 1
    path.write_text(json.dumps(durations, indent=4, sort_keys=True) + "\n", encoding="utf-8")
    print(f"kept {len(durations) - added} measurements; seeded {added} entries at {fallback:.6f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
