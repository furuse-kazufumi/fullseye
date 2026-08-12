"""CLI operator-name resolution (imgevolve._find_op).

Several ops share a HALCON alias (e.g. `remove_small` carries halcon='select_shape'
AND there is an op literally named `select_shape`). First-match-wins on
`name==key or halcon==key` made `apply select_shape` bind to `remove_small`
(a fraction-of-image threshold that deletes normal-sized objects) instead of the
op the user named. Resolution must prefer an exact NAME match.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

import imgevolve
import ops


def test_find_op_prefers_exact_name_over_halcon_alias():
    op = imgevolve._find_op(ops, "select_shape")
    assert op is not None and op.name == "select_shape", (
        f"select_shape resolved to {op.name if op else None}, expected the op named select_shape")


def test_apply_select_shape_keeps_normal_sized_blobs():
    reg = np.zeros((128, 128))
    reg[10:25, 10:25] = 1.0
    reg[40:60, 40:60] = 1.0
    reg[80:95, 80:95] = 1.0                       # three mid-sized blobs
    op = imgevolve._find_op(ops, "select_shape")
    out = np.asarray(op.fn(reg, 0.1, 0.0), np.float64)
    assert ndimage.label(out > 0.5)[1] >= 1, "select_shape deleted every blob"


def test_documented_microscopy_recipe_counts_blobs():
    """The image-processing skill's verified recipe (gauss_filter,otsu,fill_up)
    must segment distinct blobs so count_obj is > 1 on a multi-blob field."""
    img = np.full((96, 96), 0.1)
    for (r, c) in [(20, 20), (20, 70), (70, 20), (70, 70)]:
        yy, xx = np.mgrid[0:96, 0:96]
        img[(yy - r) ** 2 + (xx - c) ** 2 < 64] = 0.85
    img = np.clip(img + np.random.default_rng(0).normal(0, 0.05, img.shape), 0, 1)
    v = img
    for name in ["gaussian", "otsu", "fill_holes"]:   # gauss_filter/otsu/fill_up op names
        v = ops.RT[name](v, 0.5, 0.5)
    assert float(ops.RT["blob_count"](v, 0.0, 0.0)) == 4.0
