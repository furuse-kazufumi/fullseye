# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Precision-union storage — a tiled array whose bit-depth varies per tile.

Motivation (the "union type over bit-depth" idea)
-------------------------------------------------
A dense array pays one fixed bit-depth for every element: a ``uint8`` label map
spends 8 bits on a region that only ever holds two labels; a ``float32`` depth
map spends 32 bits on a flat wall whose depth barely moves across a tile. Most
machine-vision arrays are *locally* low-entropy — a small tile spans only a few
distinct values or a narrow range — even when the whole image is not.

:class:`PrecisionUnion` cuts the array into tiles and stores **each tile at the
smallest bit-depth that represents it** (a *union* over depths ``{0,1,2,4,8,16}``
bits per element), via a per-tile affine code ``value = offset + code * scale``.
A constant tile costs 0 bits/element (just its ``offset``); a two-value tile
costs 1 bit; a smooth tile that fits 16 levels costs 4 bits; a busy tile falls
back to 8 or 16. Codes are bit-packed, so a 2-bit tile really occupies a quarter
of the bytes, not a byte rounded up.

The point the design is probing is **uniform processing**: the caller operates on
the container without ever branching on a tile's bit-depth. :meth:`to_dense`,
:meth:`map_pointwise`, :meth:`threshold`, and :meth:`mean` all work the same
regardless of how each tile is stored, and the cheap tiles (constant / low-bit)
are handled by a fast path. Two ops are genuinely *deferred* (no decode at all for
most tiles): :meth:`scale_shift` (pure header algebra, O(#tiles)) and :meth:`clip`
(tiles inside the window untouched, outside collapsed to constants, only straddling
tiles re-quantised). ``fullseye.apply``/``run_pipeline`` use these through
:data:`LAZY_OPS` so a chain of point ops on a union materialises once at the end.
The union carries the ``atol`` accepted at :meth:`from_array` and every lazy op
respects it (a gain scales it), so laziness never silently costs precision.

What this is and is not
-----------------------
It is block-wise adaptive quantization + sub-byte bit-packing — a known family
(image codecs, ML weight compression). It is not a novel compressor. The
contribution here is the *typed uniform surface* over a heterogeneous-precision
store, and an honest measurement of where it pays off inside fullseye's data:

* wins big on label/region maps, smooth depth maps, CAD/synthetic renders, and
  3-D volumes (memory is the binding constraint there);
* is neutral-to-negative on natural photographs (high local entropy — a tile
  already needs its 8 bits, and the per-tile metadata is pure overhead).

Only numpy + stdlib. Integer input round-trips **losslessly**; float input is
quantized to a caller-given tolerance (``atol``) and the achieved max error is
reported by :meth:`max_abs_error`.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = ["PrecisionUnion", "pack", "unpack", "LAZY_OPS"]

# bit-depths the union may choose from. 0 = constant tile (offset only); 64 = raw
# float64 (never chosen by the planner — only a lossless clip that cannot be put on
# a code grid falls back to it, see _clip_straddling).
_ALLOWED_BITS = (0, 1, 2, 4, 8, 16, 64)


# --------------------------------------------------------------------------- #
# sub-byte bit packing (the reason a 2-bit tile costs a quarter of the bytes)  #
# --------------------------------------------------------------------------- #
def _pack_codes(codes: np.ndarray, bits: int) -> bytes:
    """Pack a 1-D array of unsigned integer *codes*, each ``bits`` wide, into a
    dense byte buffer. Supports bits in {1,2,4} (sub-byte, packed little-endian
    within each byte), 8, and 16."""
    if bits == 0:
        return b""
    c = np.ascontiguousarray(codes.ravel())
    if bits == 8:
        return c.astype(np.uint8).tobytes()
    if bits == 16:
        return c.astype("<u2").tobytes()
    # sub-byte: 8 // bits codes per byte, low code in the low bits.
    ppb = 8 // bits
    n = c.size
    pad = (-n) % ppb
    if pad:
        c = np.concatenate([c, np.zeros(pad, dtype=c.dtype)])
    c = c.astype(np.uint16).reshape(-1, ppb)
    shifts = (bits * np.arange(ppb)).astype(np.uint16)
    packed = np.zeros(c.shape[0], dtype=np.uint16)
    for i in range(ppb):
        packed |= (c[:, i] & ((1 << bits) - 1)) << shifts[i]
    return packed.astype(np.uint8).tobytes()


def _unpack_codes(buf: bytes, bits: int, n: int) -> np.ndarray:
    """Inverse of :func:`_pack_codes`; returns exactly *n* codes as uint16."""
    if bits == 0:
        return np.zeros(n, dtype=np.uint16)
    if bits == 8:
        return np.frombuffer(buf, dtype=np.uint8, count=n).astype(np.uint16)
    if bits == 16:
        return np.frombuffer(buf, dtype="<u2", count=n).astype(np.uint16)
    ppb = 8 // bits
    raw = np.frombuffer(buf, dtype=np.uint8).astype(np.uint16)
    mask = (1 << bits) - 1
    out = np.empty((raw.size, ppb), dtype=np.uint16)
    for i in range(ppb):
        out[:, i] = (raw >> (bits * i)) & mask
    return out.reshape(-1)[:n]


# convenience free functions (round-trip a whole array through the union) ----- #
def pack(arr, tile=32, atol=0.0):
    """Build a :class:`PrecisionUnion` from *arr* (see the class)."""
    return PrecisionUnion.from_array(arr, tile=tile, atol=atol)


def unpack(pu):
    """Reconstruct the dense array from a :class:`PrecisionUnion`."""
    return pu.to_dense()


# --------------------------------------------------------------------------- #
# per-tile plan                                                                #
# --------------------------------------------------------------------------- #
@dataclass
class _Tile:
    bits: int          # 0 = constant, 1/2/4/8/16 = packed codes, 64 = RAW float64 "codes"
    offset: float
    scale: float
    buf: bytes
    n: int             # element count (last row/col tiles are smaller)
    cmax: int = 0      # largest code actually present (exact tile range, no over-estimate)


def _plan_tile(vals: np.ndarray, atol: float) -> _Tile:
    """Choose the smallest bit-depth in ``_ALLOWED_BITS`` that represents *vals*
    within *atol* (exactly, when the data is integer and atol==0)."""
    n = vals.size
    vmin = float(vals.min())
    vmax = float(vals.max())
    if vmax == vmin:  # constant tile — 0 bits, offset carries everything
        return _Tile(0, vmin, 0.0, b"", n)

    # "integer-exact" covers both an integer dtype and a float array whose values
    # are all integers (e.g. the output of `2*x+1` on decoded float tiles) — both
    # round-trip losslessly through the unit-scale integer path.
    int_exact = (atol == 0.0) and bool(np.all(vals == np.rint(vals)))
    span = vmax - vmin
    candidates = []  # (bits, _Tile) — the union picks the cheapest that fits

    # Affine candidate: value = offset + code*scale over the tile's range. Best
    # when the distinct values are (near-)equally spaced — a smooth gradient tile
    # rounds exactly at very few bits, and a two-value tile needs just 1 bit even
    # if those two values are far apart.
    for bits in (1, 2, 4, 8, 16):
        levels = (1 << bits) - 1
        scale = span / levels
        codes = np.rint((vals.astype(np.float64) - vmin) / scale)
        codes = np.clip(codes, 0, levels).astype(np.uint16)
        recon = vmin + codes.astype(np.float64) * scale
        err = float(np.abs(recon - vals.astype(np.float64)).max())
        ok = (err == 0.0) if int_exact else (err <= atol)
        if ok:
            candidates.append((bits, _Tile(bits, vmin, scale, _pack_codes(codes, bits), n,
                                           cmax=int(codes.max()))))
            break

    # Unit-scale integer candidate: offset=min, scale=1, code = value - min.
    # Guaranteed lossless for integer data (no rounding); best when the range is
    # narrow but densely populated (a busy uint8 tile needs 8 bits, not 16 — the
    # affine scale would be non-integer and its rounding never exactly lossless).
    if int_exact and span <= 65535:
        ispan = int(round(span))
        for bits in (1, 2, 4, 8, 16):
            if ((1 << bits) - 1) >= ispan:
                codes = (np.rint(vals).astype(np.int64) - int(round(vmin))).astype(np.uint16)
                candidates.append((bits, _Tile(bits, float(round(vmin)), 1.0, _pack_codes(codes, bits), n,
                                               cmax=ispan)))
                break

    if candidates:
        candidates.sort(key=lambda bt: bt[0])  # fewest bits wins
        return candidates[0][1]

    # 16 bits still not enough (extreme float range at atol==0): store raw-ish at
    # 16 bits anyway — this is the honest fallback, error is reported by caller.
    bits = 16
    levels = (1 << bits) - 1
    scale = span / levels
    codes = np.clip(np.rint((vals.astype(np.float64) - vmin) / scale), 0, levels).astype(np.uint16)
    return _Tile(bits, vmin, scale, _pack_codes(codes, bits), n, cmax=int(codes.max()))


def _raw_tile(vals: np.ndarray) -> _Tile:
    """A tile that keeps its values as raw float64 (bits=64): value = offset + raw*scale
    with offset 0 / scale 1. The honest escape hatch when a lossless (atol=0) union
    must hold values that no uniform code grid can represent exactly — precision is
    kept, memory is what gives (only the tiles that need it)."""
    v = np.ascontiguousarray(vals.ravel().astype(np.float64))
    return _Tile(64, 0.0, 1.0, v.astype("<f8").tobytes(), v.size, cmax=0)


class PrecisionUnion:
    """An **N-D** array stored as tiles of heterogeneous bit-depth.

    Build with :meth:`from_array` (or :func:`pack`). Read back with
    :meth:`to_dense`. Operate uniformly with :meth:`map_pointwise`,
    :meth:`threshold`, :meth:`mean`, :meth:`scale_shift` — none of which branch on
    tile bit-depth at the call site. Persist with :meth:`save` / :meth:`load`.

    Tiling generalises to any number of dimensions: a 2-D image tiles into squares,
    a 3-D volume into cubes, a video (T,H,W) into space-time bricks. The volume /
    label-volume case is where the memory win is largest (a flat or few-valued brick
    costs a fraction of a byte per voxel), so N-D support is what turns the PoC into
    a feature for fullseye's ``(depth,row,col)`` volumes and stacks.
    """

    def __init__(self, shape, dtype, tile, tiles, grid, atol=0.0):
        # the precision the caller accepted at from_array (0 = lossless). Lazy ops
        # carry it forward (a gain scales it) so re-quantisation never exceeds it.
        self.atol = float(atol)
        self.shape = tuple(int(s) for s in shape)
        self.dtype = np.dtype(dtype)
        ndim = len(self.shape)
        if isinstance(tile, (tuple, list, np.ndarray)):
            self._tsz = tuple(int(t) for t in tile)
        else:
            self._tsz = (int(tile),) * ndim
        self.tile = tile                   # as given (int or per-axis tuple)
        self._tiles = tiles                # list[_Tile], row-major over the tile grid
        self._grid = tuple(int(g) for g in grid)  # per-axis tile counts

    # -- tile grid iteration (shared by every N-D operation) ----------------- #
    def _blocks(self):
        """Yield ``(tile_index, slices, block_shape)`` for every tile, row-major
        over the per-axis tile grid. The single place tiling geometry lives."""
        import itertools
        idx = 0
        for coord in itertools.product(*(range(g) for g in self._grid)):
            slices = tuple(slice(c * ts, min(c * ts + ts, s))
                           for c, ts, s in zip(coord, self._tsz, self.shape))
            bshape = tuple(sl.stop - sl.start for sl in slices)
            yield idx, slices, bshape
            idx += 1

    # -- construction -------------------------------------------------------- #
    @classmethod
    def from_array(cls, arr, tile=32, atol=0.0):
        a = np.asarray(arr)
        if a.ndim < 1:
            raise ValueError("PrecisionUnion needs an array of >= 1 dimension; got "
                             f"a 0-d scalar")
        tsz = (tuple(int(t) for t in tile) if isinstance(tile, (tuple, list, np.ndarray))
               else (int(tile),) * a.ndim)
        if len(tsz) != a.ndim:
            raise ValueError(f"tile {tile} has {len(tsz)} axes but array is {a.ndim}-D")
        if any(t < 1 for t in tsz):
            raise ValueError("tile sizes must be >= 1")
        grid = tuple((s + t - 1) // t for s, t in zip(a.shape, tsz))
        obj = cls(a.shape, a.dtype, tile, [], grid, atol=atol)
        obj._tiles = [_plan_tile(a[sl].ravel(), atol) for _, sl, _ in obj._blocks()]
        return obj

    # -- reconstruction ------------------------------------------------------ #
    @staticmethod
    def _tile_values(t: _Tile) -> np.ndarray:
        """Decode one tile to a flat float64 array (the single decode path)."""
        if t.bits == 0:
            return np.full(t.n, t.offset, dtype=np.float64)
        if t.bits == 64:                                   # raw float64 "codes"
            raw = np.frombuffer(t.buf, dtype="<f8", count=t.n).astype(np.float64)
            return t.offset + raw * t.scale
        codes = _unpack_codes(t.buf, t.bits, t.n)
        return t.offset + codes.astype(np.float64) * t.scale

    def _tile_dense(self, t: _Tile, bshape) -> np.ndarray:
        return self._tile_values(t).reshape(bshape)

    def to_dense(self) -> np.ndarray:
        out = np.empty(self.shape, dtype=np.float64)
        for idx, sl, bshape in self._blocks():
            out[sl] = self._tile_dense(self._tiles[idx], bshape)
        if np.issubdtype(self.dtype, np.integer):
            return np.rint(out).astype(self.dtype)
        return out.astype(self.dtype)

    # -- size accounting ----------------------------------------------------- #
    @property
    def nbytes(self) -> int:
        """Total bytes of the compressed store: packed codes + per-tile metadata
        (bits:1, offset:8, scale:8 bytes each) + small header."""
        meta = len(self._tiles) * (1 + 8 + 8)
        body = sum(len(t.buf) for t in self._tiles)
        return meta + body + 32  # header: shape, dtype, tile

    @property
    def dense_nbytes(self) -> int:
        return int(np.prod(self.shape)) * self.dtype.itemsize

    @property
    def ratio(self) -> float:
        """dense_nbytes / nbytes (higher is better; >1 means it saved memory)."""
        return self.dense_nbytes / self.nbytes

    def bit_histogram(self) -> dict:
        """How many tiles landed at each bit-depth (diagnostic)."""
        h = {b: 0 for b in _ALLOWED_BITS}
        for t in self._tiles:
            h[t.bits] += 1
        return h

    # -- uniform operations (never branch on bit-depth at the call site) ----- #
    def map_pointwise(self, f, atol=0.0) -> "PrecisionUnion":
        """Apply a scalar numpy function elementwise, returning a new union.

        Constant tiles are transformed in O(1) (evaluate ``f`` once), which is
        the concrete way the union's cheap tiles turn into *compute* savings.

        ``atol`` is the tolerance for re-encoding the *output* tiles: 0.0 is
        exact for integer-valued results, but a float-valued ``f`` (e.g. sqrt)
        cannot be stored losslessly in a quantized union — pass a small ``atol``
        so the result is quantized honestly rather than dropped to the 16-bit
        fallback with an unbounded error. The result's :meth:`max_abs_error`
        against ``f(dense)`` is then bounded by ``atol``.
        """
        new_tiles = []
        for idx, _sl, bshape in self._blocks():
            t = self._tiles[idx]
            if t.bits == 0:  # fast path: one function evaluation for the whole tile
                v = float(f(np.asarray(t.offset, dtype=np.float64)))
                new_tiles.append(_Tile(0, v, 0.0, b"", t.n))
            else:
                dense = self._tile_dense(t, bshape)
                new_tiles.append(_plan_tile(np.asarray(f(dense)).ravel(), atol=atol))
        out_dtype = np.asarray(f(np.zeros(1, dtype=np.float64))).dtype
        return PrecisionUnion(self.shape, out_dtype, self.tile, new_tiles, self._grid,
                              atol=atol)

    def scale_shift(self, a: float, b: float) -> "PrecisionUnion":
        """Affine map ``value -> a*value + b`` WITHOUT decoding or re-encoding a tile.

        A tile decodes as ``value = offset + code*scale``, so its affine image is
        ``a*value + b = (a*offset + b) + code*(a*scale)``: the packed codes are
        IDENTICAL, only the per-tile ``offset``/``scale`` change. This is therefore
        O(#tiles), independent of pixel count, and the code buffers are shared
        verbatim with the source (no copy). A chain of affine ops (brightness /
        contrast / normalisation) collapses to one metadata pass plus a single
        decode at the end — the deferred-affine special case of
        :meth:`map_pointwise` where the function is affine and no tile needs
        re-quantizing. The deferred header algebra alone runs ~100x faster than the
        equivalent dense ``a*x+b`` chain; with the final materialise it is still a
        clear win once several ops are chained (measured, not assumed). Output dtype
        is float64 since an affine image of integers is generally non-integer.
        """
        new_tiles = [_Tile(t.bits, a * t.offset + b, a * t.scale, t.buf, t.n, cmax=t.cmax)
                     for t in self._tiles]
        # a gain of |a| scales every stored error by |a|: carry the tolerance along
        return PrecisionUnion(self.shape, np.float64, self.tile, new_tiles, self._grid,
                              atol=abs(a) * self.atol)

    def _tile_range(self, t: _Tile):
        """Conservative ``(lo, hi)`` bounds of a tile's values from its header alone,
        O(1). Exact for the affine candidate (codes 0 and 2**bits-1 are both
        present); for the unit-scale integer candidate ``hi`` may over-estimate,
        which is SAFE: a tile is only kept-as-is when its bounds lie inside the clip
        window, so over-estimating can cost a needless decode, never a wrong skip.
        A negative ``scale`` (after a negative-gain :meth:`scale_shift`) flips the
        endpoints, hence the min/max."""
        if t.bits == 0:
            return t.offset, t.offset
        if t.bits == 64:                                   # raw tile: decode (rare)
            v = self._tile_values(t)
            return float(v.min()), float(v.max())
        e = t.offset + t.scale * t.cmax                    # EXACT: largest code present
        return (t.offset, e) if e >= t.offset else (e, t.offset)

    def clip(self, lo: float, hi: float, atol: float | None = None) -> "PrecisionUnion":
        """``np.clip(value, lo, hi)`` with per-tile deferral — the union's answer to
        a non-affine op.

        Every tile's value range is known from its header in O(1), so:
          * range inside ``[lo, hi]``  -> the tile is UNCHANGED (clip is identity);
            it stays lazy and its codes are shared verbatim;
          * range entirely below ``lo`` / above ``hi`` -> the tile becomes a
            CONSTANT (0-bit) tile — cheaper than before;
          * range straddling a bound -> only THIS tile is decoded, clipped and
            re-quantised.

        Honest precision contract for the straddling case: ``lo``/``hi`` are new
        values that generally do not lie on the tile's affine code grid, so the
        clipped tile must be re-quantised. It is re-quantised at the union's own
        ``atol`` — the tolerance the caller accepted at :meth:`from_array`, scaled
        by any gain applied since (:meth:`scale_shift`) — never at the tile's
        (possibly much coarser) grid step. So a lazy op never adds error beyond the
        precision the caller already agreed to, and a lossless union (``atol=0``,
        e.g. an integer label map clipped to integer bounds) clips losslessly. This
        may cost the straddling tile more bits than it had (precision is kept,
        memory is what gives). Parity tests against :func:`fullseye.apply` bound
        the difference by ``atol``. Pass an explicit ``atol`` to override.
        """
        lo, hi = float(lo), float(hi)
        new_tiles = []
        for idx, _sl, bshape in self._blocks():
            t = self._tiles[idx]
            tlo, thi = self._tile_range(t)
            if tlo >= lo and thi <= hi:
                new_tiles.append(t)                          # identity: stays lazy
            elif thi <= lo:
                new_tiles.append(_Tile(0, lo, 0.0, b"", t.n))   # all clipped to lo
            elif tlo >= hi:
                new_tiles.append(_Tile(0, hi, 0.0, b"", t.n))   # all clipped to hi
            else:                                            # straddles: pay for this one
                tol = self.atol if atol is None else float(atol)
                new_tiles.append(self._clip_straddling(t, lo, hi, tol))
        tol_out = self.atol if atol is None else float(atol)
        return PrecisionUnion(self.shape, np.float64, self.tile, new_tiles, self._grid,
                              atol=tol_out)

    def _clip_straddling(self, t: _Tile, lo: float, hi: float, tol: float) -> _Tile:
        """Clip one tile whose range crosses a bound, choosing the cheapest EXACT-
        enough representation:
          (a) both bounds lie on the tile's code grid -> clip the CODES in place
              (same offset/scale/bits): exact, no decode of values, no re-plan;
          (b) tol == 0 (lossless union) -> a raw float64 tile: exact, costs memory;
          (c) otherwise -> decode, clip, re-quantise at tol (bounded error).
        """
        if t.bits not in (0, 64) and t.scale != 0.0:
            clo = (lo - t.offset) / t.scale
            chi = (hi - t.offset) / t.scale
            if clo > chi:
                clo, chi = chi, clo                          # negative scale flips order
            rlo, rhi = round(clo), round(chi)
            if abs(clo - rlo) < 1e-9 and abs(chi - rhi) < 1e-9:   # (a) on-grid bounds
                codes = _unpack_codes(t.buf, t.bits, t.n).astype(np.int64)
                codes = np.clip(codes, max(int(rlo), 0), min(int(rhi), (1 << t.bits) - 1))
                return _Tile(t.bits, t.offset, t.scale, _pack_codes(codes.astype(np.uint16), t.bits),
                             t.n, cmax=int(codes.max()))
        dense = np.clip(self._tile_values(t), lo, hi)
        if tol == 0.0:                                       # (b) lossless: keep exact
            planned = _plan_tile(dense, atol=0.0)
            if float(np.abs(self._tile_values(planned) - dense).max()) == 0.0:
                return planned                               # a grid happened to fit exactly
            return _raw_tile(dense)
        return _plan_tile(dense, atol=tol)                   # (c) bounded re-quantisation

    def threshold(self, thr) -> np.ndarray:
        """Boolean mask ``value > thr`` — constant tiles resolve without decoding.

        Honest note: this is NOT faster than a dense ``arr > thr`` from Python — a
        dense threshold is a single fully-vectorised, ~memory-bandwidth-bound numpy
        pass, and the per-tile python loop here cannot beat it even when many tiles
        are constant. The value is that it operates on the compressed store without
        a full materialise, not raw speed; realising a speed win would need a
        vectorised/compiled kernel."""
        out = np.empty(self.shape, dtype=bool)
        for idx, sl, bshape in self._blocks():
            t = self._tiles[idx]
            if t.bits == 0:
                out[sl] = (t.offset > thr)
            else:
                out[sl] = self._tile_dense(t, bshape) > thr
        return out

    def mean(self) -> float:
        """Exact mean over the reconstructed array, computed tile-wise. Constant
        tiles contribute ``offset * n`` without touching any codes. Dimension-free
        (no slicing needed) — sums each tile's decoded values directly."""
        total = 0.0
        count = 0
        for t in self._tiles:
            if t.bits == 0:
                total += t.offset * t.n
            else:
                total += float(self._tile_values(t).sum())
            count += t.n
        return total / count

    def max_abs_error(self, original) -> float:
        """Max |reconstruction - original|; 0 for lossless integer round-trips."""
        a = np.asarray(original, dtype=np.float64)
        return float(np.abs(self.to_dense().astype(np.float64) - a).max())

    # -- serialization: the memory win becomes a file-size win --------------- #
    def to_state(self) -> dict:
        """Flatten to a dict of numpy arrays (no python objects) — the persistent
        form. Per-tile headers become parallel arrays and every tile's packed bytes
        are concatenated into one buffer with an offsets array."""
        buflens = np.array([len(t.buf) for t in self._tiles], dtype=np.int64)
        body = b"".join(t.buf for t in self._tiles)
        return {
            "shape": np.asarray(self.shape, dtype=np.int64),
            "tsz": np.asarray(self._tsz, dtype=np.int64),
            "grid": np.asarray(self._grid, dtype=np.int64),
            "atol": np.asarray(self.atol, dtype=np.float64),
            "dtype": np.asarray(self.dtype.str),          # e.g. '<f8' (0-d '<U..')
            "bits": np.asarray([t.bits for t in self._tiles], dtype=np.uint8),
            "offset": np.asarray([t.offset for t in self._tiles], dtype=np.float64),
            "scale": np.asarray([t.scale for t in self._tiles], dtype=np.float64),
            "n": np.asarray([t.n for t in self._tiles], dtype=np.int64),
            "cmax": np.asarray([t.cmax for t in self._tiles], dtype=np.int64),
            "buflens": buflens,
            "body": (np.frombuffer(body, dtype=np.uint8) if body
                     else np.zeros(0, dtype=np.uint8)),
        }

    @classmethod
    def from_state(cls, d) -> "PrecisionUnion":
        """Inverse of :meth:`to_state`."""
        shape = tuple(int(x) for x in np.asarray(d["shape"]))
        tsz = tuple(int(x) for x in np.asarray(d["tsz"]))
        grid = tuple(int(x) for x in np.asarray(d["grid"]))
        dtype = np.dtype(str(np.asarray(d["dtype"])))
        bits, offset = np.asarray(d["bits"]), np.asarray(d["offset"])
        scale, ncnt = np.asarray(d["scale"]), np.asarray(d["n"])
        buflens = np.asarray(d["buflens"])
        body = np.asarray(d["body"]).tobytes()
        cmax = np.asarray(d["cmax"]) if "cmax" in d else None
        tiles, pos = [], 0
        for i in range(len(bits)):
            L = int(buflens[i])
            b_i = int(bits[i])
            if cmax is not None:
                cm = int(cmax[i])
            elif b_i in (0, 64):
                cm = 0
            else:                                   # older file: no cmax -> recover it (exact)
                cm = int(_unpack_codes(body[pos:pos + L], b_i, int(ncnt[i])).max())
            tiles.append(_Tile(b_i, float(offset[i]), float(scale[i]),
                               body[pos:pos + L], int(ncnt[i]), cmax=cm))
            pos += L
        atol = float(np.asarray(d["atol"])) if "atol" in d else 0.0   # older files: lossless
        return cls(shape, dtype, tsz, tiles, grid, atol=atol)

    def save(self, path) -> None:
        """Write the compressed store to ``path`` (a ``.npz``). File size tracks
        :attr:`nbytes`, so the memory win persists to disk."""
        np.savez_compressed(path, **self.to_state())

    @classmethod
    def load(cls, path) -> "PrecisionUnion":
        """Read a store written by :meth:`save`. ``allow_pickle=False`` — the store
        is pure numeric arrays, never pickled objects."""
        with np.load(path, allow_pickle=False) as z:
            state = {k: z[k] for k in z.files}
        return cls.from_state(state)


# --------------------------------------------------------------------------- #
# lazy op table: fullseye ops that a PrecisionUnion can run WITHOUT materialising #
# --------------------------------------------------------------------------- #
# Each entry maps an op name to ``fn(pu, a, b) -> PrecisionUnion`` reproducing the
# op's exact dense semantics (ops.py) with header algebra + per-tile clip:
#   invert     : 1 - clip(v, 0, 1)                 -> clip(0,1) then scale_shift(-1, 1)
#   scale_clip : clip((0.5+1.5a)*v + (b-0.5), 0, 1) -> scale_shift(g, off) then clip(0,1)
# The (a, b) -> (gain, offset) mapping is duplicated from ops.py on purpose and
# LOCKED by parity tests (tests/test_precision_union.py): apply(pu, name).to_dense()
# must equal apply(pu.to_dense(), name) on the real op, so any drift fails CI.
# fullseye.apply / run_pipeline consult this table for a PrecisionUnion input: a
# listed op stays a union (deferred); the first unlisted op materialises once.
LAZY_OPS = {
    "identity": lambda pu, a, b: pu,
    "invert": lambda pu, a, b: pu.clip(0.0, 1.0).scale_shift(-1.0, 1.0),
    "scale_clip": lambda pu, a, b: pu.scale_shift(0.5 + 1.5 * a, b - 0.5).clip(0.0, 1.0),
}
