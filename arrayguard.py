# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Small fail-closed guards for array inputs shared by public operators.

The guard reads an input's shape before a dtype conversion or a contiguous copy.
That order matters: a float64 conversion of an oversized uint8 view can allocate
many times the advertised cap before the operator has a chance to refuse it.
"""
from __future__ import annotations

import numpy as np


def precheck_shape_and_elements(a, name: str, op: str, cap: int, *,
                                expected_ndim: int | None = None,
                                multiplier: int = 1) -> tuple[int, ...] | None:
    """変換前に shape と要素数上限を検査する / Check shape and cap before coercion.

    ``np.shape`` reads ``ndarray.shape`` without materialising its data, including
    a zero-stride virtual array. Inputs whose shape cannot be read are left to
    the operator's normal coercion path, where its post-coercion guard calls this
    helper again. ``multiplier`` accounts for a known output frame count.
    """
    try:
        shape = tuple(int(d) for d in np.shape(a))
    except (TypeError, ValueError, OverflowError):
        return None
    if expected_ndim is not None and len(shape) != expected_ndim:
        raise ValueError("%s: %s must be %d-D, got shape %r"
                         % (op, name, expected_ndim, shape))
    n = 1
    for dim in shape:
        if dim < 0:
            return None
        n *= dim
    total = n * int(multiplier)
    if total > cap:
        raise ValueError("%s: %s has %d elements, over the %d cap "
                         "(refused before conversion)" % (op, name, total, cap))
    return shape
