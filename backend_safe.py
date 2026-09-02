"""Shared safety net for library-backed operators.

Every backend wraps its op functions with an exception guard. The old fallback
was `return v` (the input), which had two defects the 2026-08-12 audit found:

  * it does NOT strip NaN/Inf that libraries emit on degenerate inputs (e.g.
    scipy.signal.wiener / skimage.denoise_wavelet / SimpleITK.LaplacianSharpening
    on a constant image) — np.clip does not remove NaN, so the whole pipeline
    score becomes NaN;
  * it returns the *input* even when the declared out_sort is region / feature /
    contour, so a failed segmentation returns a continuous grayscale image where
    a binary region is required (a type-contract violation).

`sanitize` centralises a finite-safe, sort-aware fallback: a failed or non-finite
op degrades to a valid, benign value of the DECLARED sort, derived from the input.
"""
from __future__ import annotations

import numpy as np

import os
import threading
import warnings
from contextlib import contextmanager

# --------------------------------------------------------------------------- #
# Fallback ledger — the ONE mediator every fail-soft wrapper reports to.
#
# 2026-09-02 audit: 23 backend files each carried a private ``_safe`` that swallowed
# ``Exception`` and recorded nothing, so the strict mode / error ring that lived in
# ``backends.py`` covered exactly one of 24 wrapper families.  A permanently broken
# op (an API that raises on every input) was indistinguishable from a working
# identity op — for evolution, difftest, coverage and the user alike.
#
# The contradiction is real (TRIZ: reliability #27 / ease of use #33 vs measurement
# accuracy #28 / detectability #37): the facade must not crash a user's pipeline,
# yet every degradation must be visible.  It is resolved by SEPARATION, not by
# picking a side:
#   * in SPACE   — inner wrappers may degrade but must report here (``guard``);
#                  the OUTER layer (``api.apply``) decides what to do about it;
#   * by CONDITION — the caller chooses ``on_error="fallback" | "warn" | "raise"``
#                  (or the env var FULLSEYE_ON_ERROR / IMGEVOLVE_STRICT_BACKENDS);
#   * in TIME    — the default path warns ONCE per op (``FullseyeFallbackWarning``)
#                  so a notebook user sees it and a long batch is not spammed;
#   * feedback   — ``fallbacks()`` / ``fallback_counts()`` expose the ledger so CI can
#                  assert "no op fell back on the structured probe set".
# See docs/design/TRIZ_DESIGN_PATTERN_MATRIX.md for the pattern mapping.
# --------------------------------------------------------------------------- #

class FullseyeFallbackWarning(RuntimeWarning):
    """An operator failed and a sort-valid fallback value was returned instead.

    Emitted once per op name on the default (``on_error="fallback"``) path.  Silence
    with ``warnings.filterwarnings("ignore", category=FullseyeFallbackWarning)``;
    turn it into an exception with ``on_error="raise"``.
    """


_LEDGER_LOCK = threading.Lock()
_EVENTS: list = []                  # bounded ring, oldest first
_EVENT_MAX = 256
_COUNTS: dict = {}                  # name -> number of fallbacks since clear
_WARNED: set = set()                # names that already emitted their one warning
_SEQ = 0                            # monotonically increasing event counter (never reset)
_TL = threading.local()             # .op = name the facade is currently running


def _env_flag(*names):
    for n in names:
        if os.environ.get(n, "") not in ("", "0", "false", "False"):
            return True
    return False


_STRICT = _env_flag("IMGEVOLVE_STRICT_BACKENDS", "FULLSEYE_STRICT")
_WARN_ONCE = not _env_flag("FULLSEYE_QUIET_FALLBACK")


def is_strict() -> bool:
    """True when guarded ops re-raise instead of degrading to a fallback."""
    return _STRICT


def set_strict(on: bool = True) -> bool:
    """Turn strict mode on/off; returns the PREVIOUS value so callers can restore it."""
    global _STRICT
    prev, _STRICT = _STRICT, bool(on)
    return prev


@contextmanager
def strict_mode(on: bool = True):
    """Scoped strict mode — a verifier wraps a probe call in this to tell a dead op
    (raises) from an op that genuinely returns its input (does not)."""
    prev = set_strict(on)
    try:
        yield
    finally:
        set_strict(prev)


@contextmanager
def current_op(name):
    """Attribute every fallback recorded inside the block to op *name* (thread-local)."""
    prev = getattr(_TL, "op", None)
    _TL.op = name
    try:
        yield
    finally:
        _TL.op = prev


def record(name, exc, out_sort=None, source: str = "op") -> dict:
    """Append one fallback event to the ledger and emit the once-per-name warning.

    *name* may be None: then the op the facade is currently running (``current_op``)
    is used.  *source* tags where the degradation happened: ``"op"`` (the op body
    raised), ``"gpu"`` (an accelerated path failed and the CPU op ran instead),
    ``"import"`` (a whole backend module failed to import at registry build),
    ``"input"`` (the facade was handed an array that does not match the op's
    declared input sort).
    """
    global _SEQ
    key = str(name if name is not None else getattr(_TL, "op", None) or "?")
    ev = {"name": key, "source": source, "out_sort": out_sort,
          "error": "%s: %s" % (type(exc).__name__, exc)}
    with _LEDGER_LOCK:
        _SEQ += 1
        ev["seq"] = _SEQ
        _EVENTS.append(ev)
        del _EVENTS[:-_EVENT_MAX]
        _COUNTS[key] = _COUNTS.get(key, 0) + 1
        first = key not in _WARNED
        if first:
            _WARNED.add(key)
    if first and _WARN_ONCE:
        warnings.warn("fullseye: %r degraded to a fallback (%s; %s). Further fallbacks "
                      "of this op are counted silently - see fullseye.fallbacks() or "
                      "pass on_error='raise'." % (key, source, ev["error"]),
                      FullseyeFallbackWarning, stacklevel=3)
    return ev


def fallbacks() -> list:
    """Copy of the recorded fallback events (oldest first, bounded ring)."""
    with _LEDGER_LOCK:
        return [dict(e) for e in _EVENTS]


def fallback_counts() -> dict:
    """``{name: n}`` - how many times each op fell back since the last ``clear_fallbacks``."""
    with _LEDGER_LOCK:
        return dict(_COUNTS)


def last_fallback():
    """The most recent fallback event as a dict, or None."""
    with _LEDGER_LOCK:
        return dict(_EVENTS[-1]) if _EVENTS else None


def clear_fallbacks(reset_warnings: bool = False) -> None:
    """Drop the ledger (call before a probe run). ``reset_warnings=True`` also lets
    every op warn again once."""
    with _LEDGER_LOCK:
        _EVENTS.clear()
        _COUNTS.clear()
        if reset_warnings:
            _WARNED.clear()


def mark() -> int:
    """Opaque position in the ledger; pair with :func:`events_since`."""
    with _LEDGER_LOCK:
        return _SEQ


def events_since(m: int) -> list:
    """Events recorded after :func:`mark` value *m* (still in the ring)."""
    with _LEDGER_LOCK:
        return [dict(e) for e in _EVENTS if e["seq"] > m]


def guard(fn, out_sort=None, *, name=None, on_fail=None, finish=None):
    """Wrap an op ``fn(v, a, b)`` so a failure degrades to a sort-valid value - RECORDED.

    This is the single exception guard every backend should use (``backends._safe``
    and the per-backend ``_safe`` helpers delegate here).  Behaviour:

    * ``fn`` raises  -> in strict mode the exception propagates unchanged; otherwise
      the event is recorded via :func:`record` and the result is ``on_fail(v)`` when
      given, else the sort fallback from :func:`sanitize`.
    * ``fn`` returns -> ``finish(out, v)`` when given (a backend's own post-processing,
      e.g. nan_to_num + clip), else :func:`sanitize` (finite, sort-valid).

    The recorded name is *name* if given, else the op the facade is running
    (``current_op``), else the function's qualname.
    """
    def w(v, a, b):
        try:
            out = fn(v, a, b)
        except Exception as e:           # noqa: BLE001 - the whole point is to record it
            if _STRICT:
                raise
            record(name or getattr(_TL, "op", None) or getattr(fn, "__qualname__", repr(fn)),
                   e, out_sort)
            out = None
        if out is None and on_fail is not None:
            return on_fail(v)
        if finish is not None:
            return finish(out, v)
        return sanitize(out, v, out_sort)
    w.__wrapped__ = fn
    w.__name__ = getattr(fn, "__name__", "op")
    # Keep "_safe" in the qualname: the registry-integrity tests identify a guarded
    # op that way, and `__fullseye_guarded__` is the structured form of the same fact.
    w.__qualname__ = "_safe(%s)" % getattr(fn, "__qualname__", w.__name__)
    w.__fullseye_guarded__ = True
    return w



def signed01(x):
    """Map a SIGNED filter response to [0,1] with the zero-crossing at 0.5.

    Signed responses (Harris R, Laplacian-of-Gaussian, morphological Laplace,
    high/band-pass, phase) carry information in their sign. `_norm(x)=x/max|x|`
    yields [-1,1]; the pipeline's [0,1] clip then discards the entire negative
    half. This preserves it: 0 -> 0.5, ±max -> 0/1.
    """
    x = np.asarray(x, np.float64)
    m = float(np.max(np.abs(x))) if x.size else 0.0
    return np.clip(x / (2 * m) + 0.5, 0, 1) if m > 1e-8 else np.full_like(x, 0.5)


def subpixel_refine_edges(pts, mag, ny, nx):
    """Move edge points onto the gradient-magnitude ridge with sub-pixel accuracy.

    勾配の**法線方向**に 1 px 離れた 3 点 (p-n, p, p+n) の勾配強度に放物線を当て、
    その頂点まで点をずらす(古典的なサブピクセル・エッジ位置決め。Devernay 1995 /
    HALCON ``edges_sub_pix`` と同じ考え方)。オフセットは ±1 px に制限する
    (3 点補間の外挿は当てにならない)。

    引数はすべて (row, col) 規約: ``pts`` (N,2)、``mag`` 勾配強度画像、
    ``ny``/``nx`` 単位勾配ベクトルの行/列成分(``mag`` と同 shape)。

    ★``ops._edges_sub_pix`` と ``backends_auto._sh_xld(kind="edges_sub_pix")`` の
    **両方**がこれを使う。以前は 2 つが別々に「``np.where`` の整数座標をそのまま
    返す」実装を持っており(レジストリは同名の **後勝ち** なので実際に走るのは
    backends_auto 側)、``sub_pix`` を名乗りながら画素精度しか無かった。
    """
    from scipy import ndimage as _nd

    pts = np.asarray(pts, np.float64)
    if pts.size == 0:
        return pts
    r, c = pts[:, 0], pts[:, 1]
    ri = np.clip(r.astype(int), 0, mag.shape[0] - 1)
    ci = np.clip(c.astype(int), 0, mag.shape[1] - 1)
    nyv, nxv = ny[ri, ci], nx[ri, ci]

    def _s(rr, cc):
        return _nd.map_coordinates(mag, [rr, cc], order=1, mode="nearest")

    m0, mm, mp = _s(r, c), _s(r - nyv, c - nxv), _s(r + nyv, c + nxv)
    den = mm - 2.0 * m0 + mp
    ok = np.abs(den) > 1e-12
    t = np.zeros_like(m0)
    t[ok] = 0.5 * (mm[ok] - mp[ok]) / den[ok]
    t = np.clip(np.nan_to_num(t), -1.0, 1.0)
    out = np.stack([r + t * nyv, c + t * nxv], 1)
    return np.where(np.isfinite(out), out, pts)


def gradient_normals(x):
    """Sobel gradient magnitude and the UNIT gradient (= edge normal), (mag, ny, nx)."""
    from scipy import ndimage as _nd

    x = np.asarray(x, np.float64)
    gy, gx = _nd.sobel(x, 0), _nd.sobel(x, 1)
    g = np.hypot(gx, gy)
    gs = np.where(g < 1e-12, 1e-12, g)
    return g, gy / gs, gx / gs


def _as_arr(v):
    return v if isinstance(v, np.ndarray) else None


def fallback(v, out_sort):
    """A valid, benign value of `out_sort`, derived from the input `v`."""
    vv = _as_arr(v)
    if out_sort == "feature":
        return np.float64(0.0)
    if out_sort == "contour":
        shape = tuple(vv.shape[:2]) if vv is not None and vv.ndim >= 2 else (1, 1)
        return {"shape": shape, "cs": []}
    if out_sort == "region":
        return np.zeros(vv.shape[:2], np.float64) if vv is not None and vv.ndim >= 2 else np.zeros((1, 1))
    if out_sort == "color":
        if vv is not None and vv.ndim == 3 and vv.shape[-1] == 3:
            return np.clip(vv, 0, 1)
        if vv is not None and vv.ndim == 2:
            return np.clip(np.stack([vv] * 3, -1), 0, 1)
        return np.zeros((1, 1, 3))
    if out_sort == "match":
        return np.array([0.0, 0.0, 0.0])
    # image / volume / any / unknown -> the clipped input if it is an array
    return np.clip(vv, 0, 1) if vv is not None else v


def region01(out):
    """Coerce a `region` result to the declared {0,1} contract.

    ★`sanitize` guaranteed FINITENESS but never RANGE: on the success path a
    finite float region whose values fell outside {0,1} — or an int/bool one —
    was returned untouched, so the "sort-valid" half of its promise held only by
    convention.  Every current region producer `astype`s from a bool mask, so
    this is an identity for all of them; it closes the contract for any future
    producer (a label map, a soft mask) that is not already binary.

    Out-of-range values are binarised at 0.5, the same rule `api._coerce_input`
    applies on the INPUT side.  Non-array / non-numeric outputs are left alone:
    a region op returning those is a sort bug, not a range one.
    """
    if not isinstance(out, np.ndarray) or not out.size or out.dtype.kind not in "biufc":
        return out
    r = out.real if out.dtype.kind == "c" else out
    if out.dtype.kind == "f" and np.all((r == 0) | (r == 1)):
        return out                              # already {0,1} float -> unchanged
    return (r > 0.5).astype(np.float64)


def sanitize(out, v, out_sort=None):
    """Return a finite, sort-valid result.

    Finiteness is handled by `_finite`; for out_sort=="region" the result is
    additionally forced onto the {0,1} contract by `region01`.
    """
    out = _finite(out, v, out_sort)
    return region01(out) if out_sort == "region" else out


def _finite(out, v, out_sort=None):
    """Return a finite result of the declared sort.

    * out is None (op raised)                 -> sort fallback
    * out is a float/complex array w/ NaN/Inf -> keep finite pixels, patch the
      rest from the sort fallback (or nan_to_num when shapes differ)
    * complex output for a real sort          -> take the real part
    otherwise the op's own output is returned unchanged.
    """
    if out is None:
        return fallback(v, out_sort)
    if isinstance(out, np.ndarray) and out.size and out.dtype.kind in "fc":
        real = out.real if out.dtype.kind == "c" else out
        if np.all(np.isfinite(real)):
            return real if out.dtype.kind == "c" else out
        fb = fallback(v, out_sort)
        if isinstance(fb, np.ndarray) and fb.shape == real.shape:
            return np.where(np.isfinite(real), real, fb)
        return np.nan_to_num(real, nan=0.0, posinf=1.0, neginf=0.0)
    # ★A feature op returns a numpy SCALAR, not an ndarray, so the branch above
    # never saw it: a NaN/Inf measurement (e.g. a 0/0 inside sk_blur_effect on a
    # degenerate frame) used to flow straight out of api.apply.  Scrub non-finite
    # scalars to the sort fallback so the declared "finite, sort-valid" guarantee
    # actually holds for feature/contour scalars too.
    if isinstance(out, (float, int, np.floating, np.integer, np.complexfloating, complex)):
        if not np.isfinite(float(np.real(out))):
            return fallback(v, out_sort)
    return out
