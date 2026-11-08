# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""``examples/poc_real_typewritten_ocr.py`` の部品の門(実データ無しで回る分)。

PoC 本体は ``tests/test_poc_scripts_run.py`` が走らせる。ここは取得物の照合が fail-closed であること、
せん断の向きが ``text_line_slant`` の符号と同じであること、辞書の直し方が辞書にある語を触らないこと、
書き起こしの台帳の形を固定する。
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("poc_real_typewritten_ocr",
                                               ROOT / "examples" / "poc_real_typewritten_ocr.py")
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)


def test_transcription_has_100_lines_on_three_pages():
    counts = {p: len(v) for p, v in P.TRANSCRIPTION.items()}
    assert counts == {2: 27, 4: 31, 6: 42}
    texts = [t for v in P.TRANSCRIPTION.values() for t in v.values()]
    assert len(texts) == 100
    assert min(len(t.replace(" ", "")) for t in texts) >= 7
    # 字形に忠実: このタイプライターには数字の 1 が無い(小文字の l で打つ)
    assert not any("1" in t for t in texts)


def test_a_pdf_with_the_wrong_digest_is_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("FULLSEYE_NACA_TN898_DATA", str(tmp_path))
    assert P.load_naca_pages(required=False) is None
    with pytest.raises(P.realdata.RealDataError):
        P.load_naca_pages(required=True)
    (tmp_path / P.PDF_NAME).write_bytes(b"%PDF-1.6 not the report")
    with pytest.raises(P.realdata.RealDataError):
        P.load_naca_pages(required=False)


def test_shear_direction_matches_the_sign_of_text_line_slant():
    img = np.ones((40, 200))
    for x in range(20, 180, 16):
        img[5:35, x:x + 3] = 0.0                    # 直立した縦画
    assert abs(P.L.text_line_slant(img, max_angle=45.0, step=0.25)) < 0.5
    est = P.L.text_line_slant(P.shear(img, 15.0), max_angle=45.0, step=0.25)
    assert 10.0 < est < 20.0, est    # 符号が主眼(縦画 30 画素なので数度の粗さ)
    est = P.L.text_line_slant(P.shear(img, -15.0), max_angle=45.0, step=0.25)
    assert -20.0 < est < -10.0, est


def test_rotation_sign_of_ndimage_is_the_opposite_of_the_op():
    img = np.ones((200, 400))
    for r in range(30, 180, 25):
        img[r:r + 6, 40:360] = 0.0
    base = P.L.text_line_orientation(img, max_angle=30.0, step=0.05)
    from scipy import ndimage as ndi
    est = P.L.text_line_orientation(ndi.rotate(img, 5.0, reshape=True, order=1, cval=1.0),
                                    max_angle=30.0, step=0.05) - base
    assert -6.0 < est < -4.0, est     # 符号が主眼(ndimage の +5° は op の −5°)


def test_correct_keeps_known_words_and_fixes_only_distance_one():
    lex = P.L.create_lexicon(["strain", "gage", "holes", "apart"])
    assert P.correct(lex, "strain,") == "strain,"
    assert P.correct(lex, "strajn,") == "strain,"          # 1 字違い → 直す、句読点は残す
    assert P.correct(lex, "stxxin") == "stxxin"            # 2 字違い → 触らない
    assert P.correct(lex, "ga") == "ga"                    # 3 字未満は触らない
    # 開いた語彙の限界: 辞書に無い正しい語も 1 字違いの別の語に直してしまう
    assert P.correct(lex, "hole") == "holes"
    assert P.correct(lex, "part") == "apart"


def test_naca_cache_honours_the_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("FULLSEYE_NACA_TN898_DATA", str(tmp_path / "x"))
    assert P.naca_cache() == tmp_path / "x"
    monkeypatch.delenv("FULLSEYE_NACA_TN898_DATA")
    assert P.naca_cache().name == "naca_tn898"
    assert os.fspath(ROOT) not in os.fspath(P.naca_cache())    # 置き場は repo の外
