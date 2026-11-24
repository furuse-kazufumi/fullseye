"""Stable text for callable signatures used in generated operator help.

NumPy 2 includes the scalar type in ``repr(np.float64(...))`` while NumPy 1
does not.  Generated call examples must remain pasteable Python and identical
across supported NumPy versions.
"""
from __future__ import annotations

import inspect

import numpy as np


def format_signature(fn) -> str:
    """Return ``fn``'s signature with NumPy scalars rendered as Python values.

    NumPy scalar defaults are converted with :meth:`numpy.generic.item` before
    :class:`inspect.Signature` renders them, so ``np.float64(1.5)`` becomes
    ``1.5`` on both NumPy 1 and NumPy 2.  Arrays and non-scalar defaults keep
    their normal Python representation; this helper changes only the
    cross-version scalar spelling.

    NumPy のスカラー既定値を ``.item()`` で Python 値にしてから署名を文字列化する。
    NumPy 1/2 で同一かつ、そのまま貼り付けて実行できる呼び出し例にする。
    """
    signature = inspect.signature(fn)
    parameters = [
        parameter.replace(default=parameter.default.item())
        if isinstance(parameter.default, np.generic) else parameter
        for parameter in signature.parameters.values()
    ]
    return str(signature.replace(parameters=parameters))
