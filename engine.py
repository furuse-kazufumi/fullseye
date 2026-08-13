"""engine.py — the Fullseye runtime: load a saved pipeline and run it from code.

Fullseye Studio is where you *author* an image-operator pipeline; ``FullseyeEngine``
is where you *execute* one — the runtime counterpart, analogous to MVTec's
**HDevEngine** (design a procedure in the visual tool, then call the exported
procedure from your own application without rewriting it).

A pipeline is a list of ``(op, a, b)`` stages. The engine loads one from the JSON
Studio's "Save pipeline" writes, from an ``--ops`` string, or from a Python list,
then lets you introspect its input/output sorts, tune each stage's knobs, and
execute it on a numpy frame (whole, up to a stage, or stage-by-stage). It also
``validate``-s the pipeline (unknown ops, sort mismatches) — the same check that
powers the Studio diagnostics panel.

    import fullseye
    eng = fullseye.FullseyeEngine.load("edge.json")     # or .from_ops("gaussian,sobel_amp,otsu")
    print(eng.input_sort(), "->", eng.output_sort())    # image -> region
    out = eng.run(frame)                                # numpy in, numpy out
    steps = eng.run_stepwise(frame)                     # intermediate result per stage
"""
from __future__ import annotations

import json
import os
from typing import Iterable

import numpy as np

import api

__all__ = ["FullseyeEngine", "diagnose_stages"]

# Sorts that thread cleanly into one another; "any" pairs with everything.
_ANY = "any"


def _compatible(out_sort: str, in_sort: str) -> bool:
    return out_sort == in_sort or out_sort == _ANY or in_sort == _ANY


def diagnose_stages(stages) -> list[dict]:
    """Validate a list of ``(op, a, b)`` stages without running them.

    Returns a list of problem dicts ``{"index", "op", "severity", "message"}``
    (``severity`` = ``"error"`` for an unknown operator, ``"warning"`` for a
    sort mismatch between adjacent stages). An empty list means the pipeline is
    structurally sound. Pure / Qt-free — reused by the Studio diagnostics panel.
    """
    problems = []
    prev_out = None
    prev_name = None
    for i, st in enumerate(stages):
        name = st[0] if isinstance(st, (tuple, list)) else st
        op = api.find_op(name)
        if op is None:
            problems.append({"index": i, "op": name, "severity": "error",
                             "message": "unknown operator %r" % name})
            prev_out = _ANY            # don't cascade sort warnings past an unknown op
            prev_name = name
            continue
        if prev_out is not None and not _compatible(prev_out, op.in_sort):
            problems.append({
                "index": i, "op": op.name, "severity": "warning",
                "message": "stage %d (%s) outputs '%s' but %s expects '%s'"
                           % (i - 1, prev_name, prev_out, op.name, op.in_sort)})
        prev_out = op.out_sort
        prev_name = op.name
    return problems


class FullseyeEngine:
    """Load a Fullseye pipeline and execute it programmatically.

    Construct with :meth:`load` (JSON file), :meth:`from_ops` (an ``--ops``
    string), :meth:`from_dict`, or directly from a list of ``(op, a, b)`` stages.
    """

    def __init__(self, stages: Iterable | None = None, name: str = "pipeline"):
        self.name = str(name)
        self.stages: list[list] = []
        for st in (stages or []):
            if isinstance(st, (tuple, list)):
                op, a, b = (list(st) + [0.5, 0.5])[:3]
            else:
                op, a, b = st, 0.5, 0.5
            self.stages.append([str(op), float(a), float(b)])

    # ------------------------------------------------------------------ load --
    @classmethod
    def from_dict(cls, d: dict, name: str = "pipeline") -> "FullseyeEngine":
        if not isinstance(d, dict) or "stages" not in d:
            raise ValueError("not a Fullseye pipeline dict (missing 'stages')")
        return cls(d.get("stages", []), name=d.get("name", name))

    @classmethod
    def load(cls, path: str) -> "FullseyeEngine":
        """Load a pipeline from the JSON that Studio's "Save pipeline" writes."""
        path = os.fspath(path)
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return cls.from_dict(d, name=os.path.splitext(os.path.basename(path))[0])

    @classmethod
    def from_ops(cls, ops: str, a: float = 0.5, b: float = 0.5,
                 name: str = "pipeline") -> "FullseyeEngine":
        """Build from a comma-separated ``--ops`` string (shared knobs)."""
        names = [s.strip() for s in str(ops).split(",") if s.strip()]
        return cls([(n, a, b) for n in names], name=name)

    # --------------------------------------------------------- introspection --
    def __len__(self):
        return len(self.stages)

    def op_names(self) -> list[str]:
        return [s[0] for s in self.stages]

    def describe(self) -> list[dict]:
        """Per-stage metadata: index, op, knobs, sort transform, HALCON alias."""
        out = []
        for i, (name, a, b) in enumerate(self.stages):
            op = api.find_op(name)
            out.append({
                "index": i, "op": name, "a": a, "b": b,
                "in_sort": op.in_sort if op else None,
                "out_sort": op.out_sort if op else None,
                "halcon": (op.halcon or None) if op else None,
                "known": op is not None,
            })
        return out

    def input_sort(self):
        """The sort the pipeline expects as input (first known op's in_sort)."""
        for name, *_ in self.stages:
            op = api.find_op(name)
            if op is not None:
                return op.in_sort
        return None

    def output_sort(self):
        """The sort the pipeline produces (last known op's out_sort)."""
        for name, *_ in reversed(self.stages):
            op = api.find_op(name)
            if op is not None:
                return op.out_sort
        return None

    def validate(self) -> list[dict]:
        """Structural problems (unknown ops / sort mismatches); [] if sound."""
        return diagnose_stages(self.stages)

    def is_runnable(self) -> bool:
        """True if every stage resolves to a known operator (no hard errors)."""
        return not any(p["severity"] == "error" for p in self.validate())

    # ------------------------------------------------------------- parameters --
    def get_knobs(self, i: int) -> tuple:
        return (self.stages[i][1], self.stages[i][2])

    def set_knobs(self, i: int, a: float | None = None, b: float | None = None) -> "FullseyeEngine":
        """Tune stage *i*'s knobs in place; returns self for chaining."""
        if a is not None:
            self.stages[i][1] = float(a)
        if b is not None:
            self.stages[i][2] = float(b)
        return self

    # -------------------------------------------------------------- execution --
    def _stage_tuples(self, upto=None):
        n = len(self.stages) if upto is None else max(0, min(int(upto) + 1, len(self.stages)))
        return [tuple(s) for s in self.stages[:n]]

    def run(self, image, upto: int | None = None, coerce: bool = True):
        """Execute the pipeline on *image* (numpy in, result out).

        *upto* runs only stages ``0..upto`` (default: all); a pipeline with no
        stages returns the input unchanged. Raises ``KeyError`` if a stage names
        an unknown operator (call :meth:`validate` first to check)."""
        stages = self._stage_tuples(upto)
        if not stages:
            return image                             # no stages -> the input, unchanged
        return api.run_pipeline(image, stages, coerce=coerce)

    def run_stepwise(self, image, coerce: bool = True) -> list:
        """Return the intermediate result after each stage (length = #stages).

        The step-through a debugger shows: ``steps[i]`` is the value after stage
        ``i``. Efficient — threads the array through once rather than re-running
        each prefix."""
        v = image
        first = True
        out = []
        for (name, sa, sb) in (tuple(s) for s in self.stages):
            op = api._resolve(name)
            if first:
                v = api._coerce_input(v, op) if coerce else v
                first = False
            v = api._ops.RT[op.name](v, sa, sb)
            out.append(v)
        return out

    def run_file(self, in_path: str, out_path: str | None = None,
                 upto: int | None = None):
        """Read an image file, run the pipeline, optionally write the result.

        Returns the raw result. If *out_path* is given and the result is a raster
        (2-D/3-D) it is saved (a scalar/feature result is returned only)."""
        import imgio
        img = imgio.load(os.fspath(in_path))
        result = self.run(img, upto=upto)
        if out_path is not None and isinstance(result, np.ndarray) and result.ndim in (2, 3):
            imgio.save(os.fspath(out_path), result)
        return result

    # ----------------------------------------------------------------- export --
    def to_dict(self) -> dict:
        return {"fullseye_pipeline": 1, "name": self.name,
                "stages": [[op, a, b] for op, a, b in self.stages]}

    def to_ops(self) -> str:
        return ",".join(s[0] for s in self.stages)

    def to_python(self) -> str:
        """The pipeline as a standalone Python function (same as Studio export)."""
        lines = ["import fullseye, numpy as np", "", "def %s(frame):" % _py_ident(self.name),
                 "    return fullseye.run_pipeline(frame, ["]
        for name, a, b in self.stages:
            lines.append("        (%r, %.3f, %.3f)," % (name, a, b))
        lines += ["    ])"]
        return "\n".join(lines) + "\n"

    def save(self, path: str) -> None:
        path = os.fspath(path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    def __repr__(self):
        return "FullseyeEngine(%r, %d stages: %s)" % (
            self.name, len(self.stages), self.to_ops() or "<empty>")


def _py_ident(name: str) -> str:
    """A safe Python function name from a pipeline name (ASCII, non-keyword)."""
    import keyword
    s = "".join(c if (c.isascii() and (c.isalnum() or c == "_")) else "_" for c in str(name))
    if not s or not s.isidentifier() or keyword.iskeyword(s):
        s = "pipeline_" + s
    if not s.isidentifier() or keyword.iskeyword(s):    # e.g. a leading digit remained
        s = "pipeline"
    return s
