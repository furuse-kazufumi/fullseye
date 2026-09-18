# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""jsonio — typed results <-> JSON, one bridge per sort, bit-exact round trips.

Every op returns a *sort* (``image`` / ``region`` / ``points`` / ``contour`` /
``feature`` / ``matrix`` / ``signal`` / ...). Those values are NumPy arrays and
small dicts, which is right for the next op and wrong for a file, a log line, an
LLM or another process. This module gives each sort **one** JSON form and one
way back, with three rules:

1. **Self-describing.** The envelope names the sort, so ``from_json`` needs no
   hint: ``{"fullseye_sort": "points", "version": 1, ...}``.
2. **Bit-exact.** Float arrays travel as base64 of little-endian float64
   (``"encoding": "b64f64"``); booleans and integers likewise (``b64u8`` /
   ``b64i64``). ``to_json`` → ``from_json`` reproduces the array to the last
   bit, and the tests demand it for every sort with the same probes the op
   gates use. A human-readable ``"encoding": "list"`` is available for small
   values (``readable=True``); it is also exact because Python's ``repr`` of
   a float is the shortest round-tripping decimal.
3. **Fail-closed.** An unknown sort, a value that does not fit the sort's
   shape, or an envelope with the wrong version raises ``ValueError`` — nothing
   is guessed from the array's shape alone (a ``(4,)`` is a Stokes vector or a
   bbox depending on who made it).

Sorts covered (2-D registry + typed ledgers' common vocabulary):

===============  ===========================================  ===================
sort             Python value                                 JSON payload
===============  ===========================================  ===================
image, image2d   (H, W) float                                 array
region, mask     (H, W) 0/1 float or bool                     row-major run-length (``runs``)
color, rgb,      (H, W, 3) float                              array
rgbimage
volume           (D, H, W) float                              array
rgbvolume        (D, H, W, 3) float                           array
polsweep         (4, H, W) float                              array
points,          (N, k) float, k >= 2                         array
keypoints
signal, counts,  (N,) float                                   array
vector
matrix           (R, C) float                                 array
stokes           (4,) float                                   array
feature, scalar  float                                        number
contour          ``{"shape": (H, W), "cs": [(N_i, 2) ...]}``  shape + list of arrays
table            JSON-native list / dict (arrays inside are   as is, arrays converted
                 converted to lists)
===============  ===========================================  ===================

Not covered on purpose: ``match`` (the registry carries 3- and 4-element
conventions side by side; a JSON form would freeze one of them — the
convention has to be unified first), and opaque handles.
"""
from __future__ import annotations

import base64
import json

import numpy as np

__all__ = ["JSON_SORTS", "to_jsonable", "to_json", "from_jsonable", "from_json",
           "save_json", "load_json", "to_json_lines", "from_json_lines"]

VERSION = 1

#: sort -> (canonical family, expected ndim or None, trailing shape constraint)
_ARRAY_SORTS = {
    "image": ("array", 2, None), "image2d": ("array", 2, None),
    "color": ("array", 3, 3), "rgb": ("array", 3, 3), "rgbimage": ("array", 3, 3),
    "volume": ("array", 3, None), "rgbvolume": ("array", 4, 3), "polsweep": ("array", 3, None),
    "points": ("array", 2, None), "keypoints": ("array", 2, None),
    "signal": ("array", 1, None), "counts": ("array", 1, None), "vector": ("array", 1, None),
    "matrix": ("array", 2, None), "stokes": ("array", 1, 4),
}
_SPECIAL_SORTS = ("region", "mask", "feature", "scalar", "contour", "table")
JSON_SORTS = tuple(sorted(list(_ARRAY_SORTS) + list(_SPECIAL_SORTS)))


# --------------------------------------------------------------------------- #
# array <-> payload                                                            #
# --------------------------------------------------------------------------- #
def _encode_array(a, readable):
    a = np.ascontiguousarray(a)
    if a.dtype == np.bool_:
        enc, arr = "b64u8", a.astype(np.uint8)
    elif np.issubdtype(a.dtype, np.integer):
        enc, arr = "b64i64", a.astype("<i8")
    else:
        enc, arr = "b64f64", a.astype("<f8")
    if readable:
        return {"encoding": "list", "dtype": str(a.dtype), "shape": list(a.shape),
                "data": arr.tolist()}
    return {"encoding": enc, "dtype": str(a.dtype), "shape": list(a.shape),
            "data": base64.b64encode(arr.tobytes()).decode("ascii")}


def _decode_array(p, name="value"):
    if not isinstance(p, dict) or "encoding" not in p or "shape" not in p or "data" not in p:
        raise ValueError("%s: array payload needs encoding / shape / data" % name)
    shape = tuple(int(s) for s in p["shape"])
    enc = p["encoding"]
    if enc == "list":
        arr = np.asarray(p["data"], dtype=p.get("dtype", "float64"))
        n = int(np.prod(shape)) if shape else 1
        if arr.size != n:
            raise ValueError("%s: list data has %d values, envelope shape %r wants %d"
                             % (name, arr.size, shape, n))
        return arr.reshape(shape)                      # an empty (0, 2) lists as [] — shape restores it
    dt = {"b64f64": "<f8", "b64i64": "<i8", "b64u8": "u1"}.get(enc)
    if dt is None:
        raise ValueError("%s: unknown encoding %r" % (name, enc))
    raw = base64.b64decode(p["data"], validate=True)
    n = int(np.prod(shape)) if shape else 1
    arr = np.frombuffer(raw, dtype=dt)
    if arr.size != n:
        raise ValueError("%s: %d values in data, shape %r wants %d" % (name, arr.size, shape, n))
    arr = arr.reshape(shape).copy()
    if enc == "b64u8" and p.get("dtype") == "bool":
        arr = arr.astype(bool)
    elif enc == "b64i64" and p.get("dtype"):
        arr = arr.astype(p["dtype"])
    return arr


def _rle_encode(mask):
    """Row-major run lengths of a 0/1 mask: ``[len0, len1, len0, ...]`` starting with a
    run of zeros (possibly empty). Total = H*W."""
    flat = np.asarray(mask).reshape(-1) > 0.5
    if flat.size == 0:
        return []
    change = np.flatnonzero(np.diff(flat.astype(np.int8))) + 1
    bounds = np.concatenate(([0], change, [flat.size]))
    runs = np.diff(bounds).tolist()
    if flat[0]:
        runs = [0] + runs
    return [int(r) for r in runs]


def _rle_decode(runs, shape):
    h, w = (int(shape[0]), int(shape[1]))
    total = h * w
    out = np.zeros(total, dtype=np.float64)
    pos, val = 0, 0.0
    for r in runs:
        r = int(r)
        if r < 0 or pos + r > total:
            raise ValueError("region: run lengths do not fit %dx%d" % (h, w))
        if val:
            out[pos:pos + r] = 1.0
        pos += r
        val = 1.0 - val
    if pos != total:
        raise ValueError("region: runs cover %d of %d pixels" % (pos, total))
    return out.reshape(h, w)


def _jsonable_scalar_tree(v):
    """Tables: turn numpy scalars / arrays inside a dict or list into JSON-native values."""
    if isinstance(v, dict):
        return {str(k): _jsonable_scalar_tree(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jsonable_scalar_tree(x) for x in v]
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.floating):
        return float(v)
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    raise ValueError("table: cannot serialise a %s" % type(v).__name__)


# --------------------------------------------------------------------------- #
# public                                                                       #
# --------------------------------------------------------------------------- #
def to_jsonable(value, sort, readable=False):
    """The JSON-native envelope (a dict) for *value* of *sort*. See module doc."""
    if sort not in JSON_SORTS:
        raise ValueError("to_jsonable: sort %r has no JSON bridge (have %s)" % (sort, JSON_SORTS))
    env = {"fullseye_sort": sort, "version": VERSION}
    if sort in _ARRAY_SORTS:
        _, ndim, last = _ARRAY_SORTS[sort]
        a = np.asarray(value)
        if a.ndim != ndim:
            raise ValueError("to_jsonable: %s must be %d-D, got shape %r" % (sort, ndim, a.shape))
        if last is not None and a.shape[-1] != last:
            raise ValueError("to_jsonable: %s must have a last axis of %d, got shape %r"
                             % (sort, last, a.shape))
        if a.dtype == object:
            raise ValueError("to_jsonable: %s is an object array" % sort)
        if np.issubdtype(a.dtype, np.floating) and not np.isfinite(a).all():
            env["nonfinite"] = True                 # said, not hidden: JSON has no NaN/inf
        env["payload"] = _encode_array(a, readable)
        return env
    if sort in ("region", "mask"):
        a = np.asarray(value)
        if a.ndim != 2:
            raise ValueError("to_jsonable: %s must be 2-D, got shape %r" % (sort, a.shape))
        env["payload"] = {"encoding": "rle", "shape": list(a.shape), "runs": _rle_encode(a)}
        return env
    if sort in ("feature", "scalar"):
        try:
            f = float(value)
        except (TypeError, ValueError):
            raise ValueError("to_jsonable: %s must be a number, got %r" % (sort, type(value).__name__)) from None
        env["payload"] = {"value": f if np.isfinite(f) else repr(f)}
        return env
    if sort == "contour":
        if not isinstance(value, dict) or "cs" not in value or "shape" not in value:
            raise ValueError("to_jsonable: contour must be {'shape': (H, W), 'cs': [arrays]}")
        cs = []
        for c in value["cs"]:
            a = np.asarray(c, dtype=np.float64)
            if a.ndim != 2 or a.shape[1] != 2:
                raise ValueError("to_jsonable: each contour must be (N, 2), got %r" % (a.shape,))
            cs.append(_encode_array(a, readable))
        env["payload"] = {"shape": [int(s) for s in value["shape"]], "cs": cs}
        return env
    if sort == "table":
        env["payload"] = _jsonable_scalar_tree(value)
        return env
    raise ValueError("to_jsonable: unhandled sort %r" % sort)       # pragma: no cover


def to_json(value, sort, readable=False, indent=None):
    """``json.dumps`` of :func:`to_jsonable`. ``allow_nan=False``: a non-finite
    array is flagged in the envelope and travels as bytes, never as a bare NaN token."""
    return json.dumps(to_jsonable(value, sort, readable=readable), ensure_ascii=False,
                      allow_nan=False, indent=indent)


def from_jsonable(env):
    """Inverse of :func:`to_jsonable`: ``(value, sort)``. Fail-closed on a bad envelope."""
    if not isinstance(env, dict) or "fullseye_sort" not in env:
        raise ValueError("from_jsonable: not a fullseye envelope (no 'fullseye_sort')")
    if env.get("version") != VERSION:
        raise ValueError("from_jsonable: envelope version %r, this reader knows %d"
                         % (env.get("version"), VERSION))
    sort = env["fullseye_sort"]
    if sort not in JSON_SORTS:
        raise ValueError("from_jsonable: unknown sort %r" % (sort,))
    p = env.get("payload")
    if sort in _ARRAY_SORTS:
        a = _decode_array(p, sort)
        _, ndim, last = _ARRAY_SORTS[sort]
        if a.ndim != ndim or (last is not None and a.shape[-1] != last):
            raise ValueError("from_jsonable: %s payload has shape %r" % (sort, a.shape))
        return a, sort
    if sort in ("region", "mask"):
        if not isinstance(p, dict) or p.get("encoding") != "rle":
            raise ValueError("from_jsonable: %s payload must be rle" % sort)
        return _rle_decode(p["runs"], p["shape"]), sort
    if sort in ("feature", "scalar"):
        v = p["value"] if isinstance(p, dict) else None
        if isinstance(v, str):
            v = float(v)                                   # "nan" / "inf" written by repr
        if not isinstance(v, (int, float)):
            raise ValueError("from_jsonable: %s payload must be a number" % sort)
        return float(v), sort
    if sort == "contour":
        if not isinstance(p, dict) or "cs" not in p or "shape" not in p:
            raise ValueError("from_jsonable: contour payload needs shape and cs")
        cs = [_decode_array(c, "contour") for c in p["cs"]]
        return {"shape": tuple(int(s) for s in p["shape"]), "cs": cs}, sort
    if sort == "table":
        return p, sort
    raise ValueError("from_jsonable: unhandled sort %r" % sort)     # pragma: no cover


def from_json(text):
    """``(value, sort)`` from a JSON string written by :func:`to_json`."""
    try:
        env = json.loads(text)
    except (TypeError, ValueError) as exc:
        raise ValueError("from_json: not JSON (%s)" % exc) from None
    return from_jsonable(env)


# --------------------------------------------------------------------------- #
# convenience: files and lists (JSON is used in many places)                   #
# --------------------------------------------------------------------------- #
def save_json(value, sort, path, *, readable=False, indent=None):
    """Write ``to_json(value, sort)`` to *path* (UTF-8, ``\n`` newlines). Returns *path*."""
    text = to_json(value, sort, readable=readable, indent=indent)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return path


def load_json(path):
    """Read a file written by :func:`save_json` / :func:`to_json` and return ``(value, sort)``."""
    with open(path, encoding="utf-8") as fh:
        return from_json(fh.read())


def to_json_lines(items, *, readable=False):
    """A JSON Lines string for an iterable of ``(value, sort)`` pairs: one compact
    envelope per line. Good for a ledger of per-object results (bboxes, features,
    contours) that grows a row at a time and appends to a log."""
    out = []
    for pair in items:
        try:
            value, sort = pair
        except (TypeError, ValueError):
            raise ValueError("to_json_lines: each item must be a (value, sort) pair") from None
        out.append(to_json(value, sort, readable=readable, indent=None))
    return "\n".join(out)


def from_json_lines(text):
    """Inverse of :func:`to_json_lines`: a list of ``(value, sort)``. Blank lines are
    skipped; a non-blank line that is not a valid envelope fails closed."""
    items = []
    for i, line in enumerate(text.splitlines()):
        if not line.strip():
            continue
        try:
            items.append(from_json(line))
        except ValueError as exc:
            raise ValueError("from_json_lines: line %d is not a valid envelope (%s)" % (i + 1, exc)) from None
    return items
