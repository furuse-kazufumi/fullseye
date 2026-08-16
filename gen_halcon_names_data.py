"""Generate halcon_names_data.py — the wheel-shippable mirror of data/halcon_operators.json.

The scraped MVTec reference lives under the flat-layout ``data/`` dir, which setuptools
does NOT include in the wheel (``packages=["fullseye"]`` maps package-data to the
package, not the root ``data/`` tree). ``backends_auto._real_ops()`` / ``imgops_nary.
_real_ops()`` therefore returned an EMPTY set on a pip-installed package, and an empty
real-name set turned their ``fail-closed`` name guard into a pass-everything no-op:
fabricated / mistyped HALCON names were compiled in, counted covered and passed the
functional gate. Only the NAMES are needed for the guard, so this ships just those —
same data-as-code fix the macro DNA store (macro_champions_data.py) and the auto specs
(auto_specs_data.py) already use. Re-run after re-scraping the reference::

    py -3.11 gen_halcon_names_data.py
"""
from __future__ import annotations

import json
import os
import pprint

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "data", "halcon_operators.json")
OUT = os.path.join(HERE, "halcon_names_data.py")


def collect() -> list:
    """Every real HALCON operator name in the scraped reference, sorted."""
    with open(SRC, encoding="utf-8") as f:
        data = json.load(f)
    return sorted({op["name"] for op in data["operators"]})


def main() -> int:
    if not os.path.isfile(SRC):
        raise SystemExit(f"[abort] {SRC} not found")
    with open(SRC, encoding="utf-8") as f:
        version = json.load(f).get("version", "?")
    names = collect()
    hdr = (
        '"""Generated wheel-shippable mirror of the real HALCON operator NAMES — DO NOT hand-edit.\n\n'
        "Written by gen_halcon_names_data.py from data/halcon_operators.json (MVTec reference\n"
        "v%s, %d operators). backends_auto._real_ops() and imgops_nary._real_ops() read this\n"
        "FIRST so their fail-closed name guard still has a reference set on a pip-installed\n"
        'wheel, where the flat-layout data/ tree is absent."""\n'
        "from __future__ import annotations\n\nHALCON_VERSION = %r\n\nHALCON_NAMES = "
        % (version, len(names), version)
    )
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(hdr)
        f.write(pprint.pformat(names, width=100))
        f.write("\n")
    print(f"[ok] wrote {OUT}  ({len(names)} names from {SRC})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
