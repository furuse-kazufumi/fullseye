# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""zxing-cpp の仲介(symzxing)の門 —— 入っていれば読める、入っていなければ明示の ImportError。"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import barcode1d as B  # noqa: E402
import symrender as SR  # noqa: E402
import symzxing as Z  # noqa: E402


def test_missing_dependency_is_fail_closed(monkeypatch):
    monkeypatch.setitem(sys.modules, "zxingcpp", None)          # import が ImportError になる
    assert Z.zxing_available() is False
    with pytest.raises(ImportError, match="zxing-cpp"):
        Z.read_symbols_zxing(np.ones((40, 40)) * 0.8)


def test_reads_ean_and_qr_when_installed():
    pytest.importorskip("zxingcpp")
    qrsym = pytest.importorskip("qrsym")
    img = SR.render_symbol(B.encode_barcode1d("4006381333931", "ean13"), 3.0)
    r = Z.read_symbols_zxing(img, ["EAN13"])
    assert r["n"] == 1 and r["texts"] == ["4006381333931"] and r["formats"] == ["EAN13"]
    assert r["reader"].startswith("zxing-cpp ")
    q = Z.read_symbols_zxing(SR.render_symbol(qrsym.qr_encode("FULLSEYE"), 4.0, rotate_deg=30))
    assert q["texts"] == ["FULLSEYE"] and q["positions"][0].shape == (4, 2)
    assert Z.read_symbols_zxing(np.full((60, 60), 0.8))["n"] == 0   # 読めないのは結果


def test_input_validation():
    with pytest.raises(ValueError):
        Z.read_symbols_zxing(np.ones((4, 4, 3)))
    with pytest.raises(ValueError):
        Z.read_symbols_zxing(np.full((10, 10), np.nan))
    with pytest.raises(ValueError):
        Z.read_symbols_zxing(np.full((10, 10), 2.0))
    if Z.zxing_available():
        with pytest.raises(ValueError):
            Z.read_symbols_zxing(np.ones((10, 10)), ["NotAFormat"])
