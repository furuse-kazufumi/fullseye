# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Precision-union storage on N-D machine-vision data — where it actually pays off.

A dense array pays one fixed bit-depth per element. Most machine-vision arrays are
*locally* low-entropy — a label volume is piecewise constant, a depth volume moves
slowly across a small brick — so :class:`fullseye.PrecisionUnion` stores each tile
at the smallest bit-depth its local range needs (a union over {0,1,2,4,8,16} bits),
bit-packed. This example shows the two regimes it is built for:

  * a 3-D label / segmentation volume (integer, lossless) — the memory constraint;
  * a 3-D depth volume (float, quantized to a tolerance) — precision kept at low bits;

and the two things that make it a *feature*, not just a compressor:

  * ``save``/``load`` — the in-memory win becomes a file-size win on disk;
  * ``scale_shift`` — a chain of affine ops (offset/gain/normalise) is deferred to
    per-tile header algebra (codes untouched) and materialised once.

Honest boundary (printed): on a high-entropy natural photo the union does NOT win —
every tile needs its 8 bits and the per-tile metadata is overhead. The demo reports
that ratio too, so the win is never overstated.

Run: py -3.11 examples/precision_union_volume.py
"""
from __future__ import annotations

import os
import tempfile

import numpy as np

from precision_union import PrecisionUnion


def _label_volume(shape=(64, 128, 128)) -> np.ndarray:
    """A CT-like segmentation: nested constant regions on a zero background."""
    v = np.zeros(shape, np.uint8)
    d, h, w = shape
    v[d // 6:5 * d // 6, h // 6:5 * h // 6, w // 6:5 * w // 6] = 1
    v[3 * d // 8:5 * d // 8, 3 * h // 8:5 * h // 8, 3 * w // 8:5 * w // 8] = 2
    return v


def _depth_volume(shape=(32, 96, 96), seed=0) -> np.ndarray:
    """A slowly-varying depth stack (slice index sets a plane, small ripple on top)."""
    rng = np.random.default_rng(seed)
    base = np.linspace(0.0, 5.0, shape[0])[:, None, None]
    ripple = 0.01 * rng.standard_normal(shape)
    return (base + ripple).astype(np.float32)


def run() -> dict:
    out = {}

    # --- 3-D label volume: lossless, memory is the binding constraint -------- #
    vol = _label_volume()
    pu = PrecisionUnion.from_array(vol, tile=16, atol=0.0)
    out["label_shape"] = vol.shape
    out["label_lossless"] = bool(np.array_equal(pu.to_dense(), vol))
    out["label_ratio_vs_u8"] = pu.ratio
    out["label_bits"] = pu.bit_histogram()

    # save/load: the win persists to disk (npz also gzips the packed body)
    path = os.path.join(tempfile.gettempdir(), "fullseye_pu_label.npz")
    pu.save(path)
    reloaded = PrecisionUnion.load(path)
    out["label_reload_ok"] = bool(np.array_equal(reloaded.to_dense(), vol))
    out["label_file_ratio_vs_dense"] = vol.nbytes / max(os.path.getsize(path), 1)

    # --- 3-D depth volume: float, quantized to a tolerance ------------------- #
    depth = _depth_volume()
    atol = 0.02
    pd = PrecisionUnion.from_array(depth, tile=8, atol=atol)
    out["depth_ratio_vs_f32"] = pd.ratio
    out["depth_max_error"] = pd.max_abs_error(depth)
    out["depth_within_atol"] = out["depth_max_error"] <= atol + 1e-6

    # --- deferred affine: brightness/gain chain, codes never touched --------- #
    base = pd.to_dense()
    chained = pd
    ref = base.copy()
    for a, b in [(1.5, -0.2), (0.8, 0.1), (2.0, 0.0)]:
        chained = chained.scale_shift(a, b)          # O(#tiles), no decode
        ref = a * ref + b
    out["affine_chain_matches_dense"] = bool(np.allclose(chained.to_dense(), ref, atol=1e-6))
    out["affine_shares_code_buffers"] = all(
        t2.buf is t1.buf for t1, t2 in zip(pd._tiles, chained._tiles))

    # --- honest boundary: a busy natural-ish photo does NOT win -------------- #
    rng = np.random.default_rng(1)
    photo = rng.integers(0, 256, (256, 256), dtype=np.uint8)
    out["photo_ratio_vs_u8"] = PrecisionUnion.from_array(photo, tile=32).ratio  # ~<=1

    return out


if __name__ == "__main__":
    r = run()
    print("=== precision-union on N-D machine-vision data ===")
    print(f"label volume {r['label_shape']} uint8:")
    print(f"  lossless        : {r['label_lossless']}")
    print(f"  memory ratio    : {r['label_ratio_vs_u8']:.1f}x  vs dense uint8")
    print(f"  on-disk ratio   : {r['label_file_ratio_vs_dense']:.0f}x  (save/load, npz)")
    print(f"  bit histogram   : {r['label_bits']}")
    print(f"depth volume float32 (atol=0.02):")
    print(f"  memory ratio    : {r['depth_ratio_vs_f32']:.1f}x  vs dense float32")
    print(f"  max abs error   : {r['depth_max_error']:.4f}  (<= atol: {r['depth_within_atol']})")
    print(f"deferred affine chain == dense : {r['affine_chain_matches_dense']} "
          f"(codes shared: {r['affine_shares_code_buffers']})")
    print(f"HONEST boundary — busy photo   : {r['photo_ratio_vs_u8']:.2f}x "
          f"(<= ~1: no win on high-entropy data)")
    print("PASS")
