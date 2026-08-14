"""Self-expanding registry — macro operators condensed from evolved champions.

This is the closed loop of the evolutionary core: a champion pipeline discovered
by ``evolve.py`` / ``robust.py`` is *frozen into a single reusable operator* — a
"DNA op" unique to this system — and registered like any other op. Once present it
becomes a candidate the NEXT evolution can select in one slot, so the search can
build on its own discoveries. That is the "self-expanding registry": op count
grows not only by wrapping libraries but by condensing what the search itself
found.

Data, not code: every macro op lives as one entry in ``data/macro_champions.json``
(written by ``champion_to_macro.py`` from a ``champion_<problem>.json``), so adding
a DNA op is a data edit + a recapture, never a hand-written pipeline. Each entry
carries the champion's name-pinned stages plus honest provenance (which splits it
was measured on, its holdout/locked score, and the hand baselines it is compared
against — including where it does NOT win).

Faithfulness contract (proven in ``tests/test_macro_ops.py``): a macro op runs the
champion's exact name-pinned stages via ``ops.decode_by_names`` + ``ops.run_stages``
— the same code path evolution scored — so its output is BIT-IDENTICAL to running
that pipeline stage-by-stage on the evaluation images. The op's own ``a,b`` knobs
are FROZEN (unused): a macro op is a fixed pipeline with its evolved knobs baked in,
not a re-parameterization. Fail-soft: if a DNA op is absent in this install the
composite degrades to a sort-valid value of the input (same contract every backend
honours).

``halcon = ""`` for every macro op: a champion pipeline is a novel composite an
evolutionary search discovered — no single HALCON operator is its equivalent — so
it makes NO coverage claim. It is a brand-new, system-unique capability.
"""
from __future__ import annotations

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_DNA_PATH = os.path.join(_HERE, "data", "macro_champions.json")


def _load_entries() -> list:
    """The macro-champion DNA entries (``[]`` if none).

    Prefers the generated py-module ``macro_champions_data.MACROS``: a flat-layout
    ``.py`` always ships in the wheel, whereas ``data/`` files do NOT — so this is
    what lets macro ops register on a ``pip``-installed package, not only in the
    editable source tree. Falls back to the human-readable
    ``data/macro_champions.json`` when the module is absent (e.g. a partial
    checkout). Both are written together by ``champion_to_macro.py``.
    """
    try:
        from macro_champions_data import MACROS
        if isinstance(MACROS, list) and MACROS:
            return MACROS
    except Exception:  # noqa: BLE001 - module optional; fall back to the JSON
        pass
    if os.path.exists(_DNA_PATH):
        try:
            with open(_DNA_PATH, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                data = data.get("macros", [])
            if isinstance(data, list):
                return data
        except (OSError, ValueError):
            pass
    return []


def _make_runner(stages_spec, out_sort):
    """Return ``fn(v, a, b)`` that runs the FROZEN champion pipeline.

    ``a, b`` are unused: a macro op IS its discovered pipeline (evolved knobs baked
    into ``stages_spec``), so the output is bit-identical to running that pipeline
    stage-by-stage. Fail-soft per the op contract: any failure (e.g. a DNA op is
    absent in this install, so ``decode_by_names`` fail-closes with ``KeyError``)
    degrades to a sort-valid value derived from the input.
    """
    def run(v, a, b):
        from backend_safe import sanitize
        try:
            import ops  # fully initialised by call time (build() runs mid-import)
            out = ops.run_stages(ops.decode_by_names(stages_spec), v)
        except Exception:  # noqa: BLE001 - fail-soft per op contract
            out = None
        return sanitize(out, v, out_sort)
    return run


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    """Construct one ``Op`` per DNA entry. Malformed entries are skipped
    individually (a single bad row never suppresses the rest). Sorts are plain
    strings (``"image"``/``"region"``/...), so entry values are used directly."""
    out = []
    for e in _load_entries():
        try:
            name = e["name"]
            in_sort = e.get("in_sort", IMAGE)
            out_sort = e.get("out_sort", IMAGE)
            stages_spec = [(s["op"], float(s["a"]), float(s["b"])) for s in e["stages"]]
            if not name or not stages_spec:
                continue
            out.append(Op(name, e.get("category", "macro"), "", in_sort, out_sort,
                          _make_runner(stages_spec, out_sort)))
        except (KeyError, TypeError, ValueError):
            continue
    return out
