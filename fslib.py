"""L1 — the Fullseye library the language calls (typed model + selectable backends).

This is the de-risking seed for the architecture decided in ``docs/FSCRIPT_DECISION.md``.
It exists to prove three claims *before* the rest of the plan is built on them:

1. **The sort and the value range are carried, not guessed.**  ``FImage`` holds its
   own ``value_range``, so a threshold means the same thing regardless of what
   else happens to be in the frame.  (The current ``fscript._norm01`` divides by
   the image maximum, so one specular highlight silently changes the judgement —
   measured in ``docs/FSCRIPT_MEASUREMENTS.md`` section 7, defect 2.)
2. **One operator, several backends.**  ``gauss`` is one operator whose numpy and
   OpenCV implementations are interchangeable, selected by *profile* — not two
   differently-named ops as the registry has today.
3. **The numpy implementation is the oracle.**  A native backend is only allowed
   into the ``industrial`` profile once a differential test shows it agrees with
   numpy on real inputs (``tests/test_fslib.py``).

Nothing here imports the 650-op registry: the industrial profile must stay small
and cheap to start (cold start is a measured requirement, not a preference).
"""
from __future__ import annotations

import contextlib
import threading
from dataclasses import dataclass, field, replace
from typing import Callable

import numpy as np
from scipy import ndimage as ndi

__all__ = [
    "FImage", "Region", "ObjectSet", "FsTypeError", "FsBackendError",
    "profile", "current_profile", "backends_for", "op",
    "unmet_ops", "readiness_report", "require_ready",
    "gauss", "threshold", "connection", "region_features", "select_shape", "measure_all",
]


class FsTypeError(TypeError):
    """A value was used where the language's type model forbids it."""


class FsBackendError(RuntimeError):
    """No backend satisfies the active profile for this operator."""


# --------------------------------------------------------------------------- #
# Typed iconic model
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Region:
    """A binary point set.  Distinct from an image *by type*, never by content.

    **The storage is not part of the API** (`fullseye_abi.h` R-2).  Today it is a
    dense mask; HALCON stores regions as row runs, which makes region algebra
    O(runs) instead of O(pixels) and matters as soon as a recipe works on many
    small ROIs.  Keeping `_mask` private is what allows that swap later without
    touching a single caller — so callers get `area()` / `run_count()` /
    `runs()`, which are exactly the accessors the C ABI exposes.
    """

    _mask: np.ndarray

    def __post_init__(self):
        m = np.asarray(self._mask)
        if m.ndim != 2:
            raise FsTypeError("Region must be 2-D, got %dD" % m.ndim)
        if m.dtype != bool:
            object.__setattr__(self, "_mask", m.astype(bool))

    @property
    def shape(self):
        return self._mask.shape

    def area(self) -> int:
        """fs_region_area"""
        return int(np.count_nonzero(self._mask))

    def run_count(self) -> int:
        """fs_region_run_count — how many row runs this region encodes to."""
        return int(self.runs().shape[0])

    def runs(self) -> np.ndarray:
        """fs_region_runs — (N, 3) int32 array of (row, col_begin, col_end).

        The representation-independent view.  A native run-length region returns
        the same array without materialising anything.
        """
        m = self._mask
        rows, cols = np.nonzero(m)
        if rows.size == 0:
            return np.zeros((0, 3), dtype=np.int32)
        # a run breaks where the row changes or the column is not contiguous
        brk = np.empty(rows.size, dtype=bool)
        brk[0] = True
        brk[1:] = (rows[1:] != rows[:-1]) | (cols[1:] != cols[:-1] + 1)
        begin = np.flatnonzero(brk)
        end = np.append(begin[1:], rows.size) - 1
        return np.stack([rows[begin], cols[begin], cols[end] + 1], axis=1).astype(np.int32)

    def __bool__(self):
        # Defect 4: `if (Region)` silently meant `.any()`.  Iconic values are not
        # truthy — the language must force an explicit predicate.
        raise FsTypeError(
            "a Region has no truth value; write `|Objects| > 0` or `area(R) > 0`")


@dataclass(frozen=True)
class FImage:
    """Pixels + the declared value range + the processing domain (HALCON model).

    ``value_range`` is the contract that makes a threshold mean the same thing on
    every frame.  It is declared once at acquisition, never re-derived from the
    pixels.
    """

    pixels: np.ndarray
    value_range: tuple[float, float] = (0.0, 1.0)
    domain: Region | None = None          # None = full frame

    def __post_init__(self):
        p = np.asarray(self.pixels)
        if p.ndim != 2:
            raise FsTypeError("FImage must be 2-D (single channel), got %dD" % p.ndim)
        object.__setattr__(self, "pixels", p)
        lo, hi = self.value_range
        if not (hi > lo):
            raise FsTypeError("value_range must be increasing, got %r" % (self.value_range,))
        if self.domain is not None and self.domain.shape != p.shape:
            raise FsTypeError("domain shape %r does not match pixels %r"
                              % (self.domain.shape, p.shape))

    @property
    def shape(self):
        return self.pixels.shape

    @classmethod
    def from_u8(cls, a) -> "FImage":
        """8-bit acquisition — the range is 0..255 because the *sensor* says so."""
        return cls(np.asarray(a, dtype=np.uint8), value_range=(0.0, 255.0))

    @classmethod
    def from_unit_float(cls, a) -> "FImage":
        return cls(np.asarray(a, dtype=np.float32), value_range=(0.0, 1.0))

    def absolute(self, relative: float) -> float:
        """Map a 0..1 relative threshold onto this image's declared range."""
        lo, hi = self.value_range
        return lo + relative * (hi - lo)

    def with_pixels(self, pixels) -> "FImage":
        return replace(self, pixels=pixels)

    @property
    def sort(self) -> str:
        """The value's sort, carried by the type (never inferred)."""
        return "image"

    def __bool__(self):
        raise FsTypeError("an FImage has no truth value; compare a measurement instead")


@dataclass(frozen=True)
class ObjectSet:
    """A label image plus the ids that are live — masks are never materialised.

    Replaces ``connection`` returning one full-frame mask per blob, which was
    measured at 5.8x slower and 10.2x more peak memory
    (``docs/FSCRIPT_MEASUREMENTS.md`` section 0).

    **Features travel with the set.**  Measuring the whole label image is one
    pass; an API that recomputes it per query turns a 10 ms cycle into a 40 ms
    one (measured while building this PoC).  ``feats`` maps a feature name to a
    value per *label id* — indexed by id, so ``select`` is a pure id filter and
    costs nothing.
    """

    labels: np.ndarray                    # int32 label image, 0 = background
    ids: np.ndarray = field(default=None)  # 1-D int array of live labels
    feats: dict = field(default=None, compare=False)   # name -> value per id

    def __post_init__(self):
        if self.ids is None:
            object.__setattr__(self, "ids", np.unique(self.labels)[1:].astype(np.int32))
        if self.feats is None:
            object.__setattr__(self, "feats", {})

    def __len__(self):
        return int(self.ids.size)

    def feature(self, name: str) -> np.ndarray:
        """Values of ``name`` for the live ids, computing once if needed."""
        table = self.feats.get(name)
        if table is None:
            for k, v in _measure_all(self).items():
                self.feats.setdefault(k, v)
            table = self.feats[name]
        return table[self.ids]           # table is indexed by label id

    def region(self, i: int) -> Region:
        """Materialise one object on demand (the only place a mask is built)."""
        if not (0 <= i < len(self)):
            raise IndexError("object %d out of range 0..%d" % (i, len(self) - 1))
        return Region(self.labels == self.ids[i])

    def select(self, keep) -> "ObjectSet":
        """Filter ids — the label image and the measured features are shared."""
        return ObjectSet(self.labels, np.asarray(self.ids)[np.asarray(keep)], self.feats)

    def __bool__(self):
        raise FsTypeError("an ObjectSet has no truth value; write `|Objects| > 0`")


# --------------------------------------------------------------------------- #
# Profiles and backend selection
# --------------------------------------------------------------------------- #
#: Ordered backend preference per profile.
#:
#: **What the designer sees must be what ships.**  If the Studio ran the numpy
#: reference while the line ran the native kernel, a recipe tuned near a decision
#: boundary could flip on deployment — and manufacturing does not accept "we
#: shipped a migration tool", it asks for proof that the judgement is unchanged.
#: So "studio" prefers the *same* native backend the line will use, and falls back
#: to numpy only where no native kernel exists yet.
#:
#: The numpy implementation's job is to be the **oracle in tests** (profile
#: "reference"), not the designer's default.
PROFILES = {
    "studio": ("cv2", "numpy"),
    "industrial": ("cv2",),      # fail-closed: never degrade silently on the line
    "reference": ("numpy",),     # the oracle — differential tests only
}

_state = threading.local()


def current_profile() -> str:
    return getattr(_state, "profile", "studio")


@contextlib.contextmanager
def profile(name: str):
    if name not in PROFILES:
        raise FsBackendError("unknown profile %r (have: %s)" % (name, ", ".join(PROFILES)))
    prev = current_profile()
    _state.profile = name
    try:
        yield
    finally:
        _state.profile = prev


_REGISTRY: dict[str, dict[str, Callable]] = {}


def op(name: str, backend: str):
    """Register one implementation of one operator."""
    def deco(fn):
        _REGISTRY.setdefault(name, {})[backend] = fn
        return fn
    return deco


def backends_for(name: str) -> list[str]:
    """Which backends are registered *and* importable right now."""
    out = []
    for b in _REGISTRY.get(name, {}):
        if b == "cv2" and not _have_cv2():
            continue
        out.append(b)
    return out


def _have_cv2() -> bool:
    try:
        import cv2  # noqa: F401
        return True
    except Exception:
        return False


def _dispatch(name: str, *args, **kw):
    impls = _REGISTRY.get(name)
    if not impls:
        raise FsBackendError("no operator %r" % name)
    available = backends_for(name)
    for b in PROFILES[current_profile()]:
        if b in available:
            return impls[b](*args, **kw)
    raise FsBackendError(
        "operator %r has no backend for profile %r (registered: %s, available: %s). "
        "The industrial profile refuses to fall back silently — a recipe that needs "
        "this operator cannot be deployed until a native backend passes its "
        "differential test." % (name, current_profile(),
                                ", ".join(_REGISTRY[name]), ", ".join(available) or "none"))


# --------------------------------------------------------------------------- #
# Load-time self-check — the answer to the registry's fail-open hazard.
#
# The 650-op evolution registry (``backends._safe``) swallows an op failure and
# returns a benign value of the declared sort, so on a line a missing dependency
# would silently report "no defects" (docs/FSCRIPT_DECISION.md 1.6b).  fslib's
# dispatch already fails *closed at run time*; this adds the stronger guarantee
# the decision doc requires (R-1 / R-4): a runtime must verify, *before it
# becomes READY*, that every operator a recipe uses has a WORKING backend — not
# merely that the name is registered.  Name existence is not availability.
# --------------------------------------------------------------------------- #
def _profile_prefs(profile_name: str) -> tuple[str, ...]:
    if profile_name not in PROFILES:
        raise FsBackendError("unknown profile %r (have: %s)"
                             % (profile_name, ", ".join(PROFILES)))
    return PROFILES[profile_name]


def unmet_ops(op_names, profile_name: str = "industrial") -> list[str]:
    """Operators from ``op_names`` that have NO backend satisfying ``profile_name``.

    An operator is *unmet* if it is unregistered, or if none of its registered
    backends is importable under the profile's preference list.  An empty result
    means every operator would dispatch to a real implementation.
    """
    prefs = _profile_prefs(profile_name)
    missing = []
    for name in op_names:
        if name not in _REGISTRY:
            missing.append(name)
            continue
        available = backends_for(name)
        if not any(b in available for b in prefs):
            missing.append(name)
    return missing


def readiness_report(op_names, profile_name: str = "industrial") -> dict:
    """Per-operator readiness for diagnostics.

    Maps each operator name to the backend it *would* dispatch to under the
    profile, or ``None`` when nothing satisfies it (i.e. it is unmet).
    """
    prefs = _profile_prefs(profile_name)
    report = {}
    for name in op_names:
        available = backends_for(name) if name in _REGISTRY else []
        report[name] = next((b for b in prefs if b in available), None)
    return report


def require_ready(op_names, profile_name: str = "industrial") -> None:
    """Load-time gate: refuse READY unless every operator has a working backend.

    Raises ``FsBackendError`` (never degrades) listing every unmet operator, so a
    runtime started against a machine missing a dependency stops at load rather
    than silently judging every part OK.
    """
    missing = unmet_ops(op_names, profile_name)
    if missing:
        raise FsBackendError(
            "recipe is not ready under profile %r: %d operator(s) have no working "
            "backend: %s. The runtime refuses to start rather than run a pipeline "
            "that would silently degrade." % (profile_name, len(missing),
                                              ", ".join(sorted(missing))))


# --------------------------------------------------------------------------- #
# Operators — numpy is always the oracle, cv2 is the native backend
# --------------------------------------------------------------------------- #
@op("gauss", "numpy")
def _gauss_numpy(img: FImage, sigma: float) -> FImage:
    return img.with_pixels(
        ndi.gaussian_filter(img.pixels.astype(np.float32), float(sigma)))


@op("gauss", "cv2")
def _gauss_cv2(img: FImage, sigma: float) -> FImage:
    import cv2
    return img.with_pixels(cv2.GaussianBlur(img.pixels, (0, 0), float(sigma)))


@op("threshold", "numpy")
def _threshold_numpy(img: FImage, lo: float, hi: float) -> Region:
    a = img.pixels
    return Region((a >= img.absolute(lo)) & (a <= img.absolute(hi)))


@op("threshold", "cv2")
def _threshold_cv2(img: FImage, lo: float, hi: float) -> Region:
    a = img.pixels
    return Region((a >= img.absolute(lo)) & (a <= img.absolute(hi)))


@op("connection", "numpy")
def _connection_numpy(reg: Region) -> ObjectSet:
    lbl, k = ndi.label(reg._mask)
    return ObjectSet(lbl.astype(np.int32), np.arange(1, k + 1, dtype=np.int32))


@op("connection", "cv2")
def _connection_cv2(reg: Region) -> ObjectSet:
    """One pass produces the labels *and* the stats — carry both."""
    import cv2
    k, lbl, stats, cents = cv2.connectedComponentsWithStats(
        reg._mask.astype(np.uint8), 8, cv2.CV_32S)
    return ObjectSet(lbl, np.arange(1, k, dtype=np.int32),
                     {"_cc_stats": stats, "_cc_centroids": cents})


def _tables_numpy(objs: ObjectSet) -> dict:
    """Measure every label once.  Returned tables are indexed by label id."""
    n = int(objs.labels.max())
    if n == 0:
        z = np.zeros(1)
        return {"area": z, "row": z.copy(), "column": z.copy()}
    idx = np.arange(1, n + 1)
    binary = objs.labels > 0
    areas = np.asarray(ndi.sum_labels(binary, objs.labels, index=idx), dtype=np.float64)
    cents = np.atleast_2d(np.asarray(
        ndi.center_of_mass(binary, objs.labels, idx), dtype=np.float64))
    return {"area": np.concatenate([[0.0], areas]),
            "row": np.concatenate([[0.0], cents[:, 0]]),
            "column": np.concatenate([[0.0], cents[:, 1]])}


def _tables_cv2(objs: ObjectSet) -> dict:
    import cv2
    stats = objs.feats.get("_cc_stats")
    cents = objs.feats.get("_cc_centroids")
    if stats is None:
        # No stats were carried from `connection` — measure now.
        _n, _lbl, stats, cents = cv2.connectedComponentsWithStats(
            (objs.labels > 0).astype(np.uint8), 8, cv2.CV_32S)
    return {"area": stats[:, cv2.CC_STAT_AREA].astype(np.float64),
            "row": cents[:, 1].astype(np.float64),
            "column": cents[:, 0].astype(np.float64)}


@op("measure_all", "numpy")
def _measure_all_numpy(objs: ObjectSet):
    return _measure_with(objs, _tables_numpy)


@op("measure_all", "cv2")
def _measure_all_cv2(objs: ObjectSet):
    return _measure_with(objs, _tables_cv2)


def _measure_with(objs: ObjectSet, tables_fn):
    """fs_measure_all shape: three tuples for the LIVE objects.

    The label-indexed tables stay behind the boundary as a private cache so that
    `select` costs nothing; only the per-object values cross the API, which is
    what the C ABI declares (no dictionary crosses the boundary — ABI rule R-4).
    """
    if len(objs) == 0:
        z = np.zeros(0)
        return (z, z.copy(), z.copy())
    for k, v in tables_fn(objs).items():
        objs.feats.setdefault(k, v)
    ids = objs.ids
    return (objs.feats["area"][ids], objs.feats["row"][ids], objs.feats["column"][ids])


def _measure_all(objs: ObjectSet) -> dict:
    """Internal: fill the label-indexed cache using the active backend."""
    _dispatch("measure_all", objs)
    return objs.feats


def measure_all(objs: ObjectSet):
    """fs_measure_all — (area, row, column) for the live objects."""
    _require(objs, ObjectSet, "measure_all")
    return _dispatch("measure_all", objs)


#: `region_features` is the historical name; `measure_all` is the ABI one.
region_features = measure_all


def gauss(img: FImage, sigma: float) -> FImage:
    _require(img, FImage, "gauss")
    return _dispatch("gauss", img, sigma)


def threshold(img: FImage, lo: float, hi: float) -> Region:
    _require(img, FImage, "threshold")
    return _dispatch("threshold", img, lo, hi)


def connection(reg: Region) -> ObjectSet:
    _require(reg, Region, "connection")
    return _dispatch("connection", reg)


def select_shape(objs: ObjectSet, feature: str, vmin: float, vmax: float) -> ObjectSet:
    """Filter by a measured feature — on ids, without materialising masks."""
    areas, rows, cols = region_features(objs)
    values = {"area": areas, "row": rows, "column": cols}.get(feature)
    if values is None:
        raise FsTypeError("unknown feature %r (have: area, row, column)" % feature)
    return objs.select((values >= float(vmin)) & (values <= float(vmax)))


def _require(v, cls, where):
    if not isinstance(v, cls):
        raise FsTypeError("%s expects %s, got %s — the sort is carried by the type, "
                          "not inferred from the pixels" % (where, cls.__name__, type(v).__name__))
