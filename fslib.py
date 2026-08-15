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
    """A binary point set.  Distinct from an image *by type*, never by content."""

    mask: np.ndarray

    def __post_init__(self):
        m = np.asarray(self.mask)
        if m.ndim != 2:
            raise FsTypeError("Region must be 2-D, got %dD" % m.ndim)
        if m.dtype != bool:
            object.__setattr__(self, "mask", m.astype(bool))

    @property
    def shape(self):
        return self.mask.shape

    def area(self) -> int:
        return int(np.count_nonzero(self.mask))

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
#: Ordered backend preference per profile.  "studio" prefers the reference
#: implementation so that what the designer sees is what the oracle computes;
#: "industrial" demands a native kernel and refuses to degrade silently.
PROFILES = {
    "studio": ("numpy",),
    "industrial": ("cv2",),
    "fastest": ("cv2", "numpy"),
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
    lbl, k = ndi.label(reg.mask)
    return ObjectSet(lbl.astype(np.int32), np.arange(1, k + 1, dtype=np.int32))


@op("connection", "cv2")
def _connection_cv2(reg: Region) -> ObjectSet:
    """One pass produces the labels *and* the stats — carry both."""
    import cv2
    k, lbl, stats, cents = cv2.connectedComponentsWithStats(
        reg.mask.astype(np.uint8), 8, cv2.CV_32S)
    return ObjectSet(lbl, np.arange(1, k, dtype=np.int32),
                     {"_cc_stats": stats, "_cc_centroids": cents})


@op("measure_all", "numpy")
def _measure_all_numpy(objs: ObjectSet) -> dict:
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


@op("measure_all", "cv2")
def _measure_all_cv2(objs: ObjectSet) -> dict:
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


def _measure_all(objs: ObjectSet) -> dict:
    return _dispatch("measure_all", objs)


def region_features(objs: ObjectSet):
    """areas, rows, cols for the live objects (measured once, then cached)."""
    _require(objs, ObjectSet, "region_features")
    if len(objs) == 0:
        return (np.zeros(0), np.zeros(0), np.zeros(0))
    return (objs.feature("area"), objs.feature("row"), objs.feature("column"))


def gauss(img: FImage, sigma: float) -> FImage:
    _require(img, FImage, "gauss")
    return _dispatch("gauss", img, sigma)


def threshold(img: FImage, lo: float, hi: float) -> Region:
    _require(img, FImage, "threshold")
    return _dispatch("threshold", img, lo, hi)


def connection(reg: Region) -> ObjectSet:
    _require(reg, Region, "connection")
    return _dispatch("connection", reg)


def region_features(objs: ObjectSet):
    _require(objs, ObjectSet, "region_features")
    return _dispatch("region_features", objs)


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
