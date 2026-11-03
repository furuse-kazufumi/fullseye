# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""zxing-cpp を仲介する記号の読み取り(optional extra ``symbols``、Apache-2.0)。

Bridge to zxing-cpp (``pip install "fullseye[symbols]"`` = ``zxing-cpp``, Apache-2.0)
as a second, independent reader for the symbol-reading family. Fullseye's own readers
(``barcode1d`` / ``qrsym`` / ``dmsym``) are the ones that expose decode margins and
corrected-codeword counts for print-quality grading; zxing-cpp covers many more
symbologies (PDF417, Aztec, MaxiCode, DataBar, DMRE …) and is battle-tested on real
images, so a read-rate POD can be measured for both readers on the same captures.

依存が無い環境では **fail-closed**: 呼ぶと ``ImportError``(何を入れればよいかを書く)。
黙って自前の読み取り器へ切り替えることはしない(どちらで読んだかが結果の意味を変えるため)。
Without the extra, calling raises ``ImportError`` naming the package — never a silent
fallback to another reader.

ライセンス / licence: zxing-cpp は Apache-2.0(Fullseye と同じ)。LGPL の zbar(pyzbar)は
動的リンクでも配布の条件が増えるので仲介しない。
"""
from __future__ import annotations

import numpy as np

__all__ = ["read_symbols_zxing", "zxing_available"]


def zxing_available() -> bool:
    """zxing-cpp が import できるか(``bool``)/ whether zxing-cpp can be imported."""
    try:
        import zxingcpp  # noqa: F401
    except ImportError:
        return False
    return True


def read_symbols_zxing(image, formats=None, *, try_rotate=True, try_invert=True):
    """zxing-cpp で画像の記号(1-D / 2-D)を全部読む(``table``)。

    Read every symbol zxing-cpp finds in a 2-D reflectance image (values in [0, 1],
    converted to 8-bit). ``formats`` is None (all) or a list of zxing format names
    (``"QRCode"``, ``"DataMatrix"``, ``"EAN13"``, ``"Code128"`` …). Returns ``n``,
    ``texts``, ``formats``, ``positions`` (4 corners (row, col) per symbol, top-left
    first as zxing reports them), ``valid`` and ``reader`` = ``"zxing-cpp <version>"``.

    空の入力(辺が 0)は ``ValueError``。
    拒否(``ValueError``): 2-D でない、非有限、値が [0, 1] の外、未知の形式名。
    zxing-cpp が入っていなければ ``ImportError``(fail-closed、``pip install zxing-cpp``)。
    何も見つからなければ ``n = 0``(読めないことは例外ではなく結果)。
    """
    op = "read_symbols_zxing"
    a = np.asarray(image, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError("%s: image must be 2-D, got shape %s" % (op, a.shape))
    if a.size == 0:
        raise ValueError("%s: image is empty" % op)
    if not np.isfinite(a).all():
        raise ValueError("%s: image has non-finite values" % op)
    if a.min() < -1e-9 or a.max() > 1 + 1e-9:
        raise ValueError("%s: image values must lie in [0, 1]" % op)
    try:
        import zxingcpp
    except ImportError as exc:
        raise ImportError("%s: needs the optional dependency zxing-cpp "
                          "(pip install zxing-cpp, or fullseye[symbols])" % op) from exc
    fmt = None
    if formats is not None:
        names = [formats] if isinstance(formats, str) else list(formats)
        fmt_objs = []
        for n in names:
            obj = getattr(zxingcpp.BarcodeFormat, str(n), None)
            if obj is None:
                raise ValueError("%s: unknown zxing format %r" % (op, n))
            fmt_objs.append(obj)
        fmt = fmt_objs[0]
        for o in fmt_objs[1:]:
            fmt = fmt | o
    u8 = np.ascontiguousarray(np.round(np.clip(a, 0.0, 1.0) * 255.0).astype(np.uint8))
    kw = {"try_rotate": bool(try_rotate), "try_invert": bool(try_invert)}
    if fmt is not None:
        kw["formats"] = fmt
    try:
        res = zxingcpp.read_barcodes(u8, **kw)
    except TypeError:                              # 古い版は try_* の名前が違う / older API
        res = zxingcpp.read_barcodes(u8, formats=fmt) if fmt is not None else zxingcpp.read_barcodes(u8)
    texts, fmts, pos, valid = [], [], [], []
    for r in res:
        texts.append(r.text)
        fmts.append(getattr(r.format, "name", str(r.format)))
        p = r.position
        pts = [p.top_left, p.top_right, p.bottom_right, p.bottom_left]
        pos.append(np.array([[q.y, q.x] for q in pts], dtype=np.float64))
        valid.append(bool(getattr(r, "valid", True)))
    try:
        from importlib.metadata import version as _version
        ver = _version("zxing-cpp")
    except Exception:                              # noqa: BLE001 - 版が引けなくても読みは返す
        ver = "unknown"
    return {"n": len(texts), "texts": texts, "formats": fmts, "positions": pos, "valid": valid,
            "reader": "zxing-cpp %s" % ver}
