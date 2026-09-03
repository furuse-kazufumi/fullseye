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
are handled by a fast path so the *savings compound into speed*, not only memory.

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

__all__ = ["PrecisionUnion", "pack", "unpack"]

# bit-depths the union may choose from. 0 = constant tile (offset only).
_ALLOWED_BITS = (0, 1, 2, 4, 8, 16)


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
    bits: int
    offset: float
    scale: float
    buf: bytes
    n: int  # element count (last row/col tiles are smaller)


def _plan_tile(vals: np.ndarray, atol: float) -> _Tile:
    """Choose the smallest bit-depth in ``_ALLOWED_BITS`` that represents *vals*
    within *atol* (exactly, when the data is integer and atol==0)."""
    n = vals.size
    vmin = float(vals.min())
    vmax = float(vals.max())
    if vmax == vmin:  # constant tile — 0 bits, offset carries everything
        return _Tile(0, vmin, 0.0, b"", n)

    is_int = np.issubdtype(vals.dtype, np.integer)
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
        ok = (err == 0.0) if (is_int and atol == 0.0) else (err <= atol)
        if ok:
            candidates.append((bits, _Tile(bits, vmin, scale, _pack_codes(codes, bits), n)))
            break

    # Unit-scale integer candidate: offset=min, scale=1, code = value - min.
    # Guaranteed lossless for integer data (no rounding); best when the range is
    # narrow but densely populated (a busy uint8 tile needs 8 bits, not 16 — the
    # affine scale would be non-integer and its rounding never exactly lossless).
    if is_int and atol == 0.0 and span <= 65535:
        ispan = int(round(span))
        for bits in (1, 2, 4, 8, 16):
            if ((1 << bits) - 1) >= ispan:
                codes = (vals.astype(np.int64) - int(round(vmin))).astype(np.uint16)
                candidates.append((bits, _Tile(bits, float(round(vmin)), 1.0, _pack_codes(codes, bits), n)))
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
    return _Tile(bits, vmin, scale, _pack_codes(codes, bits), n)


class PrecisionUnion:
    """A 2-D array stored as tiles of heterogeneous bit-depth.

    Build with :meth:`from_array` (or :func:`pack`). Read back with
    :meth:`to_dense`. Operate uniformly with :meth:`map_pointwise`,
    :meth:`threshold`, :meth:`mean` — none of which branch on tile bit-depth at
    the call site.
    """

    def __init__(self, shape, dtype, tile, tiles, grid):
        self.shape = tuple(shape)
        self.dtype = np.dtype(dtype)
        self.tile = int(tile)
        self._tiles = tiles                # list[_Tile], row-major over grid
        self._grid = grid                  # (n_tile_rows, n_tile_cols)

    # -- construction -------------------------------------------------------- #
    @classmethod
    def from_array(cls, arr, tile=32, atol=0.0):
        a = np.asarray(arr)
        if a.ndim != 2:
            raise ValueError("PrecisionUnion PoC handles 2-D arrays; got shape "
                             f"{a.shape}")
        h, w = a.shape
        tr = (h + tile - 1) // tile
        tc = (w + tile - 1) // tile
        tiles = []
        for ti in range(tr):
            for tj in range(tc):
                block = a[ti * tile:(ti + 1) * tile, tj * tile:(tj + 1) * tile]
                tiles.append(_plan_tile(block.ravel(), atol))
        return cls(a.shape, a.dtype, tile, tiles, (tr, tc))

    # -- reconstruction ------------------------------------------------------ #
    def _tile_dense(self, t: _Tile, th: int, tw: int) -> np.ndarray:
        if t.bits == 0:
            vals = np.full(t.n, t.offset, dtype=np.float64)
        else:
            codes = _unpack_codes(t.buf, t.bits, t.n)
            vals = t.offset + codes.astype(np.float64) * t.scale
        return vals.reshape(th, tw)

    def to_dense(self) -> np.ndarray:
        h, w = self.shape
        out = np.empty((h, w), dtype=np.float64)
        tr, tc = self._grid
        idx = 0
        for ti in range(tr):
            for tj in range(tc):
                th = min(self.tile, h - ti * self.tile)
                tw = min(self.tile, w - tj * self.tile)
                out[ti * self.tile:ti * self.tile + th,
                    tj * self.tile:tj * self.tile + tw] = self._tile_dense(self._tiles[idx], th, tw)
                idx += 1
        if np.issubdtype(self.dtype, np.integer):
            out = np.rint(out).astype(self.dtype)
        else:
            out = out.astype(self.dtype)
        return out

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
        tr, tc = self._grid
        h, w = self.shape
        new_tiles = []
        idx = 0
        for ti in range(tr):
            for tj in range(tc):
                th = min(self.tile, h - ti * self.tile)
                tw = min(self.tile, w - tj * self.tile)
                t = self._tiles[idx]
                if t.bits == 0:  # fast path: one function evaluation for the whole tile
                    v = float(f(np.asarray(t.offset, dtype=np.float64)))
                    new_tiles.append(_Tile(0, v, 0.0, b"", t.n))
                else:
                    dense = self._tile_dense(t, th, tw)
                    new_tiles.append(_plan_tile(np.asarray(f(dense)).ravel(), atol=atol))
                idx += 1
        out_dtype = np.asarray(f(np.zeros(1, dtype=np.float64))).dtype
        return PrecisionUnion(self.shape, out_dtype, self.tile, new_tiles, self._grid)

    def threshold(self, thr) -> np.ndarray:
        """Boolean mask ``value > thr`` — constant tiles resolve without decoding."""
        h, w = self.shape
        out = np.empty((h, w), dtype=bool)
        tr, tc = self._grid
        idx = 0
        for ti in range(tr):
            for tj in range(tc):
                th = min(self.tile, h - ti * self.tile)
                tw = min(self.tile, w - tj * self.tile)
                t = self._tiles[idx]
                sl = (slice(ti * self.tile, ti * self.tile + th),
                      slice(tj * self.tile, tj * self.tile + tw))
                if t.bits == 0:
                    out[sl] = (t.offset > thr)
                else:
                    out[sl] = self._tile_dense(t, th, tw) > thr
                idx += 1
        return out

    def mean(self) -> float:
        """Exact mean over the reconstructed array, computed tile-wise. Constant
        tiles contribute ``offset * n`` without touching any codes."""
        total = 0.0
        count = 0
        h, w = self.shape
        tr, tc = self._grid
        idx = 0
        for ti in range(tr):
            for tj in range(tc):
                th = min(self.tile, h - ti * self.tile)
                tw = min(self.tile, w - tj * self.tile)
                t = self._tiles[idx]
                if t.bits == 0:
                    total += t.offset * t.n
                else:
                    total += float(self._tile_dense(t, th, tw).sum())
                count += t.n
                idx += 1
        return total / count

    def max_abs_error(self, original) -> float:
        """Max |reconstruction - original|; 0 for lossless integer round-trips."""
        a = np.asarray(original, dtype=np.float64)
        return float(np.abs(self.to_dense().astype(np.float64) - a).max())
