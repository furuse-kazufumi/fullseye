# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: a *precision-union* array — per-tile adaptive bit-depth with a uniform op interface.

User idea (2026-09-02):
  「ユニオン型のようなものでビット深さを複数のパターンに分割して、量子化された要素数を
   どれだけ分けてそれに乗せて、一元的に処理できるかが大事なんじゃないか。その仕組みを
   作れたら省メモリや高速化にもつながる。」

Read literally: split an image into pieces, store each piece at whatever bit-depth
it actually needs (a *union* over precisions {0,1,2,4,8,16} bits), and expose a
single processing interface that does not care which bit-depth a given piece uses.
The claimed payoff is memory (a flat region does not deserve 8 bits) and speed.

This is the same shape as the exact geometric predicates already in the library:
there the precision axis is a 2-level union {float64, exact-rational} chosen *per
input* by a measured error bound. Here the union is {0,1,2,4,8,16}-bit affine codes
chosen *per tile* by a measured value range. Both pick the cheapest representation
that is provably good enough, and both hide the choice behind one call.

What this PoC actually demonstrates, and what it does NOT
--------------------------------------------------------
WINS (measured in bitunion_bench.py):
  * memory: label maps, masks, smooth/flat and HDR-float data pack far below a
    global uint8/float32 — each tile carries only the bits its range needs.
  * speed: a point-affine op ``v -> a*v + b`` is exact algebra on the affine
    header: ``offset' = a*offset + b``, ``scale' = a*scale``. The packed CODES ARE
    NOT TOUCHED. A chain of such ops costs O(#tiles), independent of #pixels, and
    materialises once at the end. This is deferred/lazy affine, not a trick.
  * threshold: a flat tile (bits==0) or a tile whose whole range is on one side of
    the threshold is decided in O(1); only straddling tiles decode.

HONEST NON-WINS:
  * high-entropy noise: per-tile headers are pure overhead; the union is LARGER
    than dense. The container measures and reports this rather than hiding it.
  * neighbourhood ops (convolution, morphology): they cross tile boundaries and
    need decoded values, so the code-space shortcut does not apply — you pay a
    decode. The union helps their *inputs'* memory, not their compute.

Only stdlib + numpy. This lives under poc/ and is deliberately NOT wired into the
package (pyproject py-modules) — it is a proof of concept, not a public API yet.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

_ALLOWED_BITS = (0, 1, 2, 4, 8, 16)


def _choose_bits(vmin: float, vmax: float, tol: float, allowed=_ALLOWED_BITS) -> int:
    """Smallest bit-width whose affine quantisation error over [vmin, vmax] is <= tol.

    With ``levels = 2**bits`` codes spanning [vmin, vmax], the quantisation step is
    ``(vmax - vmin) / (levels - 1)`` and the worst-case rounding error is half a
    step. bits==0 means the tile is constant to within tol (store one value).
    """
    span = float(vmax) - float(vmin)
    if span <= tol:
        return 0
    for b in allowed:
        if b == 0:
            continue
        levels = (1 << b)
        step = span / (levels - 1)
        if step * 0.5 <= tol:
            return b
    return max(allowed)  # 16: best we offer; error may exceed tol (reported by caller)


@dataclass
class PrecisionUnion:
    """A 2-D array stored as per-tile affine codes at heterogeneous bit-depths.

    Layout: the array is tiled ``tile x tile``. Tile ``k`` (raster order) has a
    header ``(bits_k, offset_k, scale_k)`` and ``bits_k * npix_k`` packed bits in a
    single shared bitstream ``blob``. A value is ``offset_k + scale_k * code``.
    """
    shape: tuple            # original (H, W)
    tile: int
    grid: tuple             # (rows, cols) of tiles
    headers: np.ndarray     # (ntiles, 3) float64 columns: bits, offset, scale
    tile_hw: np.ndarray     # (ntiles, 2) int: actual height, width of each tile
    blob: np.ndarray        # uint8, the concatenated packed bitstream
    orig_dtype: np.dtype

    # ---- accounting -------------------------------------------------------- #
    @property
    def nbytes(self) -> int:
        """Real stored size: headers + tile sizes + packed codes."""
        return int(self.headers.nbytes + self.tile_hw.nbytes + self.blob.nbytes)

    def dense_nbytes(self, dtype=np.uint8) -> int:
        return int(np.prod(self.shape)) * np.dtype(dtype).itemsize

    def bits_histogram(self) -> dict:
        """Audit: how many tiles landed at each bit-depth (what precision cost)."""
        b = self.headers[:, 0].astype(int)
        return {int(k): int(v) for k, v in zip(*np.unique(b, return_counts=True))}

    # ---- uniform point-affine op (the headline win): O(#tiles), no decode --- #
    def scale_shift(self, a: float, b: float) -> "PrecisionUnion":
        """Return ``a*self + b`` WITHOUT touching the packed codes.

        v' = a*(offset + scale*code) + b = (a*offset + b) + (a*scale)*code.
        So offset' = a*offset + b, scale' = a*scale; codes are shared verbatim.
        """
        h = self.headers.copy()
        h[:, 1] = a * self.headers[:, 1] + b          # offset' = a*offset + b
        h[:, 2] = a * self.headers[:, 2]              # scale'  = a*scale
        return PrecisionUnion(self.shape, self.tile, self.grid, h,
                              self.tile_hw, self.blob, self.orig_dtype)

    # ---- reduction in code space ------------------------------------------ #
    def sum(self) -> float:
        """Sum over all pixels: sum_k (offset_k*npix_k + scale_k*sum(codes_k))."""
        total = 0.0
        for k, (bits, off, scale) in enumerate(self.headers):
            h, w = int(self.tile_hw[k, 0]), int(self.tile_hw[k, 1])
            n = h * w
            if bits == 0:
                total += off * n
            else:
                codes = self._tile_codes(k)
                total += off * n + scale * float(codes.sum())
        return float(total)

    def mean(self) -> float:
        return self.sum() / float(np.prod(self.shape))

    # ---- threshold: flat / one-sided tiles decided without decoding -------- #
    def threshold(self, t: float) -> np.ndarray:
        """Boolean mask ``value > t``. Constant and one-sided tiles skip decode."""
        out = np.zeros(self.shape, dtype=bool)
        for k, (bits, off, scale) in enumerate(self.headers):
            r, c = self._tile_origin(k)
            h, w = int(self.tile_hw[k, 0]), int(self.tile_hw[k, 1])
            if bits == 0:
                if off > t:
                    out[r:r + h, c:c + w] = True
                continue
            lo, hi = off, off + scale * ((1 << int(bits)) - 1)
            if lo > t:                       # whole tile above threshold: O(1)
                out[r:r + h, c:c + w] = True
                continue
            if hi <= t:                      # whole tile at/below: O(1)
                continue
            codes = self._tile_codes(k).reshape(h, w)  # straddles: decode this one
            out[r:r + h, c:c + w] = (off + scale * codes) > t
        return out

    # ---- materialise ------------------------------------------------------- #
    def to_dense(self) -> np.ndarray:
        out = np.empty(self.shape, dtype=np.float64)
        for k, (bits, off, scale) in enumerate(self.headers):
            r, c = self._tile_origin(k)
            h, w = int(self.tile_hw[k, 0]), int(self.tile_hw[k, 1])
            if bits == 0:
                out[r:r + h, c:c + w] = off
            else:
                codes = self._tile_codes(k).reshape(h, w)
                out[r:r + h, c:c + w] = off + scale * codes
        return out.astype(self.orig_dtype) if np.issubdtype(self.orig_dtype, np.integer) else out

    # ---- internals --------------------------------------------------------- #
    def _tile_origin(self, k: int) -> tuple:
        cols = self.grid[1]
        return (k // cols) * self.tile, (k % cols) * self.tile

    def _bit_offset(self, k: int) -> int:
        # start bit of tile k in the shared stream = sum of prior tiles' bit counts
        bits = self.headers[:, 0].astype(np.int64)
        npix = (self.tile_hw[:, 0] * self.tile_hw[:, 1]).astype(np.int64)
        return int((bits[:k] * npix[:k]).sum())

    def _tile_codes(self, k: int) -> np.ndarray:
        bits = int(self.headers[k, 0])
        h, w = int(self.tile_hw[k, 0]), int(self.tile_hw[k, 1])
        n = h * w
        start = self._bit_offset(k)
        nbits = bits * n
        # slice the bitstream, unpack, and fold groups of `bits` into integer codes
        all_bits = np.unpackbits(self.blob)
        seg = all_bits[start:start + nbits].reshape(n, bits)
        weights = (1 << np.arange(bits - 1, -1, -1)).astype(np.int64)  # MSB first
        return (seg.astype(np.int64) * weights).sum(axis=1)


def encode(arr: np.ndarray, tile: int = 16, tol: float = 0.0,
           allowed=_ALLOWED_BITS) -> PrecisionUnion:
    """Encode a 2-D array as a PrecisionUnion.

    tol=0 with an integer input is lossless (each tile uses ceil(log2(range+1))
    bits). tol>0 allows lossy affine quantisation to shrink further.
    """
    a = np.asarray(arr)
    if a.ndim != 2:
        raise ValueError("PoC encodes 2-D arrays only")
    H, W = a.shape
    af = a.astype(np.float64)
    rows = (H + tile - 1) // tile
    cols = (W + tile - 1) // tile
    ntiles = rows * cols
    headers = np.zeros((ntiles, 3), dtype=np.float64)
    tile_hw = np.zeros((ntiles, 2), dtype=np.int64)
    bit_chunks = []  # list of 0/1 uint8 arrays to concatenate then packbits
    for tr in range(rows):
        for tc in range(cols):
            k = tr * cols + tc
            r0, c0 = tr * tile, tc * tile
            blk = af[r0:r0 + tile, c0:c0 + tile]
            h, w = blk.shape
            tile_hw[k] = (h, w)
            vmin, vmax = float(blk.min()), float(blk.max())
            # integer lossless: bits = ceil(log2(range+1)); else measured affine
            if np.issubdtype(a.dtype, np.integer) and tol == 0.0:
                rng = int(vmax) - int(vmin)
                bits = 0 if rng == 0 else int(np.ceil(np.log2(rng + 1)))
                bits = min(b for b in allowed if b >= bits) if bits > 0 else 0
                scale = 1.0
            else:
                bits = _choose_bits(vmin, vmax, tol, allowed)
                scale = 0.0 if bits == 0 else (vmax - vmin) / ((1 << bits) - 1)
            headers[k] = (bits, vmin, scale)
            if bits == 0:
                continue
            if scale > 0:
                codes = np.rint((blk - vmin) / scale).astype(np.int64)
            else:
                codes = np.zeros_like(blk, dtype=np.int64)
            codes = np.clip(codes, 0, (1 << bits) - 1).reshape(-1)
            # expand each code to `bits` bits, MSB first
            shifts = np.arange(bits - 1, -1, -1)
            expanded = ((codes[:, None] >> shifts) & 1).astype(np.uint8).reshape(-1)
            bit_chunks.append(expanded)
    stream = np.concatenate(bit_chunks) if bit_chunks else np.zeros(0, dtype=np.uint8)
    blob = np.packbits(stream) if stream.size else np.zeros(0, dtype=np.uint8)
    return PrecisionUnion((H, W), tile, (rows, cols), headers, tile_hw, blob, a.dtype)
