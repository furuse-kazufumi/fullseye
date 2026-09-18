# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""mdio - typed results <-> Markdown, the companion of :mod:`fullseye.jsonio`.

JSON and Markdown are used together all the time: a result is embedded in a JSON
code fence inside a report, or a table of numbers is meant to be *read* rather
than parsed. :mod:`fullseye.jsonio` gives the machine-exact form; this module
gives the human form and the bridge between the two:

- :func:`to_markdown` renders a typed value as GitHub-flavored Markdown - a real
  table for ``table`` / ``points`` / ``matrix`` / ``signal``, a one-line summary
  for things that are not text (an ``image`` is its shape, dtype and range; a
  ``region`` is its coverage and bounding box). It never pretends to show pixels.
- :func:`json_block` wraps the *exact* JSON envelope in a ```json fence, so a
  value can live inside a Markdown document and still round-trip bit-for-bit
  (``readable=True`` by default, so the block is diff-friendly).
- :func:`extract_json` reads a Markdown string back and returns every fullseye
  envelope it finds in a fenced block as ``(value, sort)`` - other code fences
  are ignored, a malformed *fullseye* envelope fails closed.
- :func:`report` turns a list of ``(heading, value, sort)`` sections into one
  Markdown document: the readable rendering of each result, and - with
  ``with_json=True`` - the exact envelope folded underneath in a ``<details>``.

Design rules match jsonio: **fail-closed** on an unknown sort, and **exact**
wherever a machine reads it back (the JSON fence, never the rendered table).
"""
from __future__ import annotations

import json
import re

import numpy as np

from fullseye import jsonio as _J

__all__ = ["to_markdown", "json_block", "extract_json", "report"]

_FENCE = re.compile(r"```[ \t]*([A-Za-z0-9_+-]*)[ \t]*\r?\n(.*?)\r?\n```", re.DOTALL)


def _fmt(x, float_fmt):
    if isinstance(x, (float, np.floating)):
        f = float(x)
        if not np.isfinite(f):
            return "NaN" if np.isnan(f) else ("inf" if f > 0 else "-inf")
        return float_fmt % f
    if isinstance(x, (bool, np.bool_)):
        return "true" if x else "false"
    return str(x)


def _cell(x, float_fmt):
    """A GFM table cell: escape the pipe so a value never breaks the column grid."""
    return _fmt(x, float_fmt).replace("|", "\\|")


def _gfm_table(headers, rows):
    head = "| " + " | ".join(str(h) for h in headers) + " |"
    rule = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join([head, rule] + body)


def _num_table(a, max_rows, max_cols, float_fmt, row_label="row"):
    a = np.atleast_2d(np.asarray(a, dtype=np.float64))
    n, m = a.shape
    cols = list(range(min(m, max_cols)))
    headers = [row_label] + ["c%d" % c for c in cols]
    rows = []
    for i in range(min(n, max_rows)):
        rows.append([str(i)] + [_cell(a[i, c], float_fmt) for c in cols])
    md = _gfm_table(headers, rows)
    notes = []
    if n > max_rows:
        notes.append("... %d more rows" % (n - max_rows))
    if m > max_cols:
        notes.append("... %d more columns" % (m - max_cols))
    if notes:
        md += "\n\n" + " / ".join(notes)
    return md


def _stats_line(a):
    a = np.asarray(a, dtype=np.float64)
    finite = a[np.isfinite(a)]
    if finite.size == 0:
        return "no finite values"
    return "min %.6g / max %.6g / mean %.6g" % (
        float(finite.min()), float(finite.max()), float(finite.mean()))


def _table_to_md(value, float_fmt):
    if isinstance(value, dict):
        rows = [[_cell(k, float_fmt), _cell(v, float_fmt)] for k, v in value.items()]
        return _gfm_table(["key", "value"], rows)
    if isinstance(value, (list, tuple)):
        if value and all(isinstance(r, dict) for r in value):
            headers = []
            for r in value:                                     # union of keys, first-seen order
                for k in r:
                    if k not in headers:
                        headers.append(k)
            rows = [[_cell(r.get(h, ""), float_fmt) for h in headers] for r in value]
            return _gfm_table(headers, rows)
        rows = [[_cell(v, float_fmt)] for v in value]
        return _gfm_table(["value"], rows)
    return "`%s`" % _fmt(value, float_fmt)


def to_markdown(value, sort, *, max_rows=20, max_cols=12, float_fmt="%.6g", title=None):
    """A Markdown rendering of *value* of *sort*. Tables and small numeric arrays
    become real GFM tables (capped at *max_rows* x *max_cols*, with a note when
    truncated); values that are not text become a one-line summary. Fail-closed on
    an unknown sort. *title*, if given, is prepended as a bold line."""
    if sort not in _J.JSON_SORTS:
        raise ValueError("to_markdown: sort %r has no Markdown rendering (have %s)"
                         % (sort, _J.JSON_SORTS))
    if sort == "table":
        body = _table_to_md(value, float_fmt)
    elif sort in ("feature", "scalar"):
        body = "`%s`" % _fmt(float(value), float_fmt)
    elif sort in ("region", "mask"):
        a = np.asarray(value) > 0.5
        n = int(a.sum())
        h, w = a.shape
        if n == 0:
            body = "empty region on %dx%d (0 of %d px)" % (h, w, h * w)
        else:
            rs, cs = np.where(a)
            body = ("coverage %.1f%% (%d of %d px) / bbox rows %d-%d, cols %d-%d on %dx%d"
                    % (100.0 * n / (h * w), n, h * w, int(rs.min()), int(rs.max()),
                       int(cs.min()), int(cs.max()), h, w))
    elif sort == "contour":
        cs = value.get("cs", [])
        total = int(sum(np.asarray(c).shape[0] for c in cs))
        sh = tuple(int(s) for s in value.get("shape", ()))
        body = "%d contour(s), %d points total on %s" % (len(cs), total, "x".join(map(str, sh)))
    elif sort in ("points", "keypoints", "matrix", "signal", "counts", "vector", "stokes"):
        body = _num_table(value, max_rows, max_cols, float_fmt)
    else:                                                        # image / color / volume / rgbvolume / polsweep
        a = np.asarray(value)
        body = "%s %s %s / %s" % (sort, "x".join(map(str, a.shape)), a.dtype, _stats_line(a))
    return ("**%s**\n\n%s" % (title, body)) if title else body


def json_block(value, sort, *, readable=True, lang="json"):
    """The exact JSON envelope for *value* wrapped in a fenced code block, ready to
    paste into a Markdown document. Round-trips through :func:`extract_json`."""
    text = _J.to_json(value, sort, readable=readable, indent=1)
    return "```%s\n%s\n```" % (lang, text)


def extract_json(md):
    """Every fullseye envelope embedded in the Markdown string *md*, as a list of
    ``(value, sort)``. Fenced blocks that are not fullseye envelopes are ignored;
    a fenced block that *is* a fullseye envelope but malformed fails closed."""
    out = []
    for _lang, block in _FENCE.findall(md):
        block = block.strip()
        if not block:
            continue
        try:
            obj = json.loads(block)
        except ValueError:
            continue                                            # not JSON -> not ours
        if not (isinstance(obj, dict) and "fullseye_sort" in obj):
            continue                                            # JSON, but not a fullseye envelope
        out.append(_J.from_jsonable(obj))                       # malformed fullseye envelope -> ValueError
    return out


def report(sections, *, title=None, with_json=False, float_fmt="%.6g"):
    """A single Markdown document from *sections*, an iterable of ``(heading, value,
    sort)``. Each section is an ``## heading`` and the readable rendering of the
    result; with ``with_json=True`` the exact envelope is folded underneath in a
    ``<details>`` so the same document is both readable and machine-recoverable
    (via :func:`extract_json`)."""
    parts = []
    if title:
        parts.append("# %s\n" % title)
    for sec in sections:
        try:
            heading, value, sort = sec
        except (TypeError, ValueError):
            raise ValueError("report: each section must be (heading, value, sort)") from None
        parts.append("## %s\n" % heading)
        parts.append(to_markdown(value, sort, float_fmt=float_fmt))
        if with_json:
            parts.append("\n<details><summary>JSON</summary>\n\n%s\n\n</details>"
                         % json_block(value, sort))
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"
