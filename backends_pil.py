"""Pillow (PIL) incorporation — distinctive filters HALCON/the core lack.

Pillow ships classic NPR/enhance filters (emboss, contour, find-edges, edge-
enhance, mode filter, unsharp mask) and tone operators (posterize, solarize,
auto-contrast) that the numpy/HALCON core does not carry. `build()` wraps the
genuinely-distinctive, single-gray-image ones; exception-safe, output in [0,1].
Prefixed `xpil_`; `Op.halcon=""` (they lift Pillow-axis coverage, not HALCON's).
"""
from __future__ import annotations

import numpy as np


def _safe(fn):
    def w(v, a, b):
        try:
            out = fn(v, a, b)
            return out if out is not None else v
        except Exception:
            return v
    return w


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    try:
        from PIL import Image, ImageFilter, ImageOps
    except Exception:
        return []

    def _im(v):
        return Image.fromarray((np.clip(np.asarray(v, np.float64), 0, 1) * 255).astype(np.uint8), "L")

    def _arr(im):
        return np.asarray(im, np.float64) / 255.0

    def _filt(flt):
        return lambda v, a, b: _arr(_im(v).filter(flt))

    defs = [
        ("xpil_emboss", "artistic", "", IMAGE, IMAGE, _filt(ImageFilter.EMBOSS)),
        ("xpil_contour", "edges", "", IMAGE, IMAGE, _filt(ImageFilter.CONTOUR)),
        ("xpil_find_edges", "edges", "", IMAGE, IMAGE, _filt(ImageFilter.FIND_EDGES)),
        ("xpil_edge_enhance", "gray", "", IMAGE, IMAGE, _filt(ImageFilter.EDGE_ENHANCE_MORE)),
        ("xpil_smooth_more", "smoothing", "", IMAGE, IMAGE, _filt(ImageFilter.SMOOTH_MORE)),
        ("xpil_detail", "gray", "", IMAGE, IMAGE, _filt(ImageFilter.DETAIL)),
        ("xpil_mode_filter", "rank", "", IMAGE, IMAGE,
         lambda v, a, b: _arr(_im(v).filter(ImageFilter.ModeFilter(size=3 + 2 * int(a * 3))))),
        ("xpil_unsharp_mask", "smoothing", "", IMAGE, IMAGE,
         lambda v, a, b: _arr(_im(v).filter(ImageFilter.UnsharpMask(
             radius=1 + 4 * a, percent=int(50 + 200 * b), threshold=0)))),
        ("xpil_posterize", "gray", "", IMAGE, IMAGE,
         lambda v, a, b: _arr(ImageOps.posterize(_im(v), bits=1 + int(a * 6)))),
        ("xpil_solarize", "gray", "", IMAGE, IMAGE,
         lambda v, a, b: _arr(ImageOps.solarize(_im(v), threshold=int(64 + 160 * a)))),
        ("xpil_autocontrast", "gray", "", IMAGE, IMAGE,
         lambda v, a, b: _arr(ImageOps.autocontrast(_im(v), cutoff=int(a * 10)))),
    ]
    try:
        from PIL import ImageChops, ImageEnhance

        defs += [
            ("xpil_offset", "geometry", "", IMAGE, IMAGE,          # toroidal (wrap-around) shift
             lambda v, a, b: _arr(ImageChops.offset(_im(v), int(a * np.asarray(v).shape[1]),
                                                     int(b * np.asarray(v).shape[0])))),
            ("xpil_contrast", "gray", "", IMAGE, IMAGE,            # contrast about the image mean
             lambda v, a, b: _arr(ImageEnhance.Contrast(_im(v)).enhance(2 * a))),
        ]
    except Exception:
        pass
    return [Op(n, c, h, i, o, _safe(f)) for (n, c, h, i, o, f) in defs]
