"""Generate auto_specs_data.py — the wheel-shippable mirror of data/auto_specs/*.json.

The auto_specs JSON files live under the flat-layout ``data/`` dir, which setuptools
does NOT include in the wheel (``packages=["fullseye"]`` maps package-data to the
package, not the root ``data/`` tree). ``backends_auto.load_specs()`` therefore lost
all of these agent-authored specs on a pip-installed package — the ~50 data-driven
HALCON-parity ops built from them silently vanished on a non-editable install, exactly
the failure the macro DNA store already dodges.

This script concatenates every ``data/auto_specs/*.json`` (in sorted filename order —
the exact order ``load_specs()`` iterates) into a single ``AUTO_SPECS`` list written to
``auto_specs_data.py``, a plain py-module that always ships in the wheel. Re-run after
editing any ``data/auto_specs/*.json`` so the two stay in sync::

    py -3.11 gen_auto_specs_data.py
"""
from __future__ import annotations

import json
import os
import pprint

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "data", "auto_specs")
OUT = os.path.join(HERE, "auto_specs_data.py")


def collect() -> list:
    """Every spec in data/auto_specs/*.json, sorted filename order (== load_specs)."""
    specs: list = []
    for fn in sorted(os.listdir(SRC)):
        if fn.endswith(".json"):
            with open(os.path.join(SRC, fn), encoding="utf-8") as f:
                specs.extend(json.load(f))
    return specs


def main() -> int:
    if not os.path.isdir(SRC):
        raise SystemExit(f"[abort] {SRC} not found")
    specs = collect()
    hdr = (
        '"""Generated wheel-shippable mirror of data/auto_specs/*.json — DO NOT hand-edit.\n\n'
        "Written by gen_auto_specs_data.py. backends_auto.load_specs() reads this when the\n"
        "flat-layout data/auto_specs/ dir is absent (a pip-installed wheel), so the data-driven\n"
        'auto ops register on an installed package, not only in the editable source tree."""\n'
        "from __future__ import annotations\n\nAUTO_SPECS = "
    )
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(hdr)
        f.write(pprint.pformat(specs, width=100, sort_dicts=False))
        f.write("\n")
    print(f"[ok] wrote {OUT}  ({len(specs)} specs from {SRC})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
