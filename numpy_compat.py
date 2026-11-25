# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""NumPy version compatibility helpers / NumPy 版差の小さな互換層。"""
from __future__ import annotations

import numpy as np


def trapezoid(y, x=None, dx=1.0, axis=-1):
    """Integrate with the public spelling available in NumPy 1.x or 2.x.

    NumPy 2.x exposes :func:`numpy.trapezoid` but removes ``numpy.trapz``;
    older supported NumPy releases provide only ``trapz``.  Select lazily so
    the absent spelling is never evaluated / NumPy 2.x と対応する旧版のどちら
    でも、存在しない綴りを参照せず台形則を選ぶ。
    """
    integrate = np.trapezoid if hasattr(np, "trapezoid") else np.trapz
    return integrate(y, x=x, dx=dx, axis=axis)
