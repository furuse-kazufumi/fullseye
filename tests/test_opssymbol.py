# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""`opssymbol` 台帳 —— 登録の健全性、公開経路から引けること、台帳の呼び出し例が走ること。

中身の真値の門は族ごとの試験にある(test_barcode1d / test_qrsym / test_dmsym / test_symgrade /
test_symbolpod / test_ocrclassic / test_ocrpod / test_symzxing / test_symrs)。ここでは
「台帳に載った」だけでなく ``fullseye.ledger`` から呼べて答えが合うことを見る。
"""
from __future__ import annotations

import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import opssymbol  # noqa: E402

_ALLOWED = {"table", "image2d", "signal", "matrix", "scalar"}


def test_every_registered_op_has_an_implementation():
    assert opssymbol.missing() == []
    assert len(opssymbol.OPSSYMBOL) == 33
    assert opssymbol.categories() == ["barcode1d", "datacode2d", "symbol_capture", "print_quality",
                                      "read_pod", "ocr", "symbol_bridge"]


def test_sorts_are_existing_words_and_docs_follow_the_ledger_form():
    """新しい型語彙を作らない / 要約は「…(``型``)」で終わる(op ノートの要約になる)。"""
    for name, m in opssymbol.OPSSYMBOL.items():
        assert set(m["in"]) | {m["out"]} <= _ALLOWED, name
        assert m["doc"], name
    tagged = [n for n, m in opssymbol.OPSSYMBOL.items() if "(``%s``)" % m["out"] in m["doc"]]
    assert len(tagged) >= 31, sorted(set(opssymbol.OPSSYMBOL) - set(tagged))


def test_reachable_from_the_public_ledger():
    import fullseye as fs
    for name in opssymbol.OPSSYMBOL:
        assert callable(getattr(fs.ledger, name)), name
    e = fs.ledger.encode_barcode1d("490123456789", "ean13")
    assert e["text"] == "4901234567894"
    assert fs.ledger.ean_check_digit("490123456789") == 4


def test_the_ledger_docstring_example_runs():
    """opssymbol の docstring の呼び出し例(刻印の DM → ぼけ → 読む → 等級)。"""
    import fullseye as fs
    sym = fs.ledger.dm_encode("LOT2026-1103")
    img = fs.ledger.render_symbol(sym, 5.0, rotate_deg=30.0, dot=0.8)
    img = fs.ledger.capture_degrade(img, defocus_px=3.0, full_well_e=20000.0,
                                    read_noise_e=10.0, bits=8, seed=1)
    assert fs.ledger.dm_read(img)["text"] == "LOT2026-1103"
    g = fs.ledger.grade_datacode2d(img, expected_text="LOT2026-1103")
    assert g["letter"] == "C" and g["limiting"] == ["symbol_contrast"]
    assert np.isfinite(g["symbol_contrast"])
