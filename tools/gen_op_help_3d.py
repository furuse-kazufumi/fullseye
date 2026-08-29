"""DEPRECATED — 3-D op-help generation moved into tools/opdocs.py (md = source of truth).

Historically this dev tool rendered per-op 3-D help cards straight from ``ops3d`` into
``studio_assets/op_help/3d/<name>.html``. That duplicated the content now held in the
Markdown corpus (``docs/ops/3d/**/*.md``), which ``tools/opdocs.py`` generates and then
bulk-converts to the same HTML — so a single source (the Markdown notes) drives both the
AI-readable corpus and the Studio/gallery help, with author/licence, references, sample-data
URLs and version linkage that the old inline card lacked.

This module is kept as a thin backward-compatible shim: running it just delegates to
``opdocs.cmd_html`` so any muscle-memory / script that still calls
``py -3.11 tools/gen_op_help_3d.py`` keeps working and regenerates via the unified path.

    py -3.11 tools/gen_op_help_3d.py     # equivalent to: py -3.11 tools/opdocs.py html
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "tools"))


def main() -> int:
    sys.stderr.write(
        "gen_op_help_3d.py is DEPRECATED — 3-D help is now generated from the Markdown "
        "corpus by tools/opdocs.py. Delegating to `opdocs html`...\n")
    import opdocs
    opdocs.cmd_html()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
