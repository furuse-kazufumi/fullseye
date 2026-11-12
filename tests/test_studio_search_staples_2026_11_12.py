# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""入門の語で定番の op が先頭に出る(使い勝手の点検 P-09、2026-11-12)。

直す前: 「二値化」の先頭は ``hx_close_edges``、「回転」は ``rope_rotate``、「ラベリング」は ``polar_unwrap``。
検索の順位(``search_ops``)は変えず、``search_grouped`` が別の欄 ``staples`` を返し、Studio が先頭の
「定番」に出す。
"""
from __future__ import annotations

import os
import time

import numpy as np
import pytest

import studio_search as ss


def _image():
    return np.random.default_rng(0).random((48, 64))


def test_every_staple_op_is_in_the_index():
    """表の op が 1 つでも索引から消えたら落ちる(「在るものだけ返す」で黙って縮まない)。"""
    names = [n for _terms, ops in ss.STAPLES for n in ops]
    assert len(names) >= 40 and len(ss.STAPLES) >= 20          # 表そのものが縮んでいない
    missing = [n for n in names if ss._row_of(n) is None]
    assert not missing, missing


@pytest.mark.parametrize("query,first", [
    ("二値化", "otsu"), ("しきい値", "otsu"), ("画像を二値化したい", "otsu"),
    ("ノイズ除去", "median"), ("ぼかし", "gaussian"), ("エッジ", "sobel_amp"),
    ("画像を明るく", "scale_image"), ("回転", "rotate_image"), ("拡大", "zoom_image_factor"),
    ("膨張", "dilation_circle"), ("収縮", "erosion_circle"), ("穴埋め", "fill_up"),
    ("ラベリング", "connect_and_holes"), ("円検出", "cv_hough_circles"),
    ("テンプレートマッチング", "ncc_locate"), ("thresholding", "otsu"), ("blur", "gaussian"),
    ("ｒｏｔａｔｅ", "rotate_image"),                             # 全角は NFKC で寄せる
])
def test_beginner_words_put_the_staple_first(query, first):
    res = ss.search_grouped(query, _image(), k=10, lang="ja")
    names = [e["name"] for e in res["staples"]]
    assert names and names[0] == first, (query, names)
    assert len(names) == len(set(names)) <= ss.STAPLES_MAX


def test_staple_rows_have_the_same_shape_as_group_rows_and_say_their_group():
    res = ss.search_grouped("膨張", _image(), k=10, lang="ja")
    row = res["staples"][0]
    for key in ("name", "label", "in_sort", "out_sort", "score", "why", "tier", "fit", "bridge", "extra_inputs"):
        assert key in row, key
    # 画像(image)に領域(region)用の膨張は直接は掛からない: 前処理の列が付く
    assert row["group"] == "needs_preprocessing" and row["bridge"], row
    assert "_rank" not in row
    on_image = ss.search_grouped("二値化", _image(), k=10, lang="ja")["staples"][0]
    assert on_image["group"] == "applicable" and on_image["label"] != on_image["name"]   # 日本語の要約が付く


def test_no_staple_for_op_names_and_unknown_words():
    for q in ("xyzzy", "gaussian", "threshold", "hx_close_edges", "小さい領域を消す"):   # op 名そのものには重ねない
        assert ss.search_grouped(q, _image(), k=10)["staples"] == [], q
    assert ss.staples_for("") == [] and ss.staples_for(None) == []


def test_groups_are_untouched_by_staples(monkeypatch):
    """3 群の中身と並びは、定番の表が空でも同じ(順位の約束を変えていない)。"""
    with_staples = ss.search_grouped("二値化", _image(), k=20, lang="ja")
    monkeypatch.setattr(ss, "STAPLES", ())
    without = ss.search_grouped("二値化", _image(), k=20, lang="ja")
    assert without["staples"] == [] and with_staples["staples"]
    for g in ss.GROUPS:
        assert [e["name"] for e in with_staples[g]] == [e["name"] for e in without[g]], g


# --------------------------------------------------------------------------- Studio の画面
def _pump(sec):
    from PySide6 import QtWidgets
    end = time.monotonic() + sec
    while time.monotonic() < end:
        QtWidgets.QApplication.processEvents()
        time.sleep(0.01)


def test_studio_lists_the_staples_first(tmp_path, monkeypatch):
    pytest.importorskip("PySide6")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6 import QtCore, QtWidgets
    import studio
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(tmp_path / "s.ini"))
    win, _model = studio.build_window()
    win.show(); _pump(0.4)
    try:
        ui = win._search_ui
        ui["search_now"]("二値化"); _pump(0.3)
        lst = ui["list"]
        ops = [lst.item(i).data(QtCore.Qt.UserRole) for i in range(lst.count())]
        ops = [n for n in ops if n]
        assert ops[:2] == ["otsu", "threshold"], ops[:6]
        assert [r["name"] for r in ui["rows"]()["staples"]][0] == "otsu"
        assert lst.item(0).data(QtCore.Qt.UserRole + 4) == "staples"      # 先頭の見出しが「定番」
        # P-19: 行は一覧の見える幅に収まり、「試す」「ヘルプ」のボタンが横スクロールの先に隠れない
        vw = lst.viewport().width()
        rows = [r for g in ui["rows"]().values() for r in g]
        assert len(rows) >= 5
        for r in rows:
            assert lst.visualItemRect(r["item"]).width() <= vw, r["name"]
            b = r["help_button"]
            assert b.mapTo(lst.viewport(), b.rect().topRight()).x() <= vw, r["name"]
            assert r["text"].startswith(r["name"])                          # op 名が行の先頭
        # 前処理が要る定番は「先に: a → この op」と別の行に出る
        ui["search_now"]("膨張"); _pump(0.3)
        first = ui["rows"]()["staples"][0]
        assert first["name"] == "dilation_circle" and first["text"].splitlines()[-1].endswith("→ dilation_circle")
        # 定番が無い語では見出しを出さない
        ui["search_now"]("gaussian"); _pump(0.3)
        assert lst.item(0).data(QtCore.Qt.UserRole + 4) != "staples"
        assert ui["rows"]()["staples"] == []
    finally:
        studio._UI_LANG["code"] = "en"
        win.close_guard = lambda: True
        win.quiesce(); win.close(); _pump(0.1)


def test_colour_file_is_announced_as_read_in_greyscale(tmp_path, monkeypatch):
    """P-17: カラーの PNG を開くと黙って灰色になっていた。状態バーでそう言う(灰色のファイルでは言わない)。"""
    pytest.importorskip("PySide6")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6 import QtWidgets
    import imgio
    import studio
    rgb = np.zeros((24, 32, 3)); rgb[..., 0] = 0.9; rgb[:, 16:, 2] = 0.7
    grey3 = np.repeat(np.linspace(0, 1, 32)[None, :, None], 24, axis=0).repeat(3, axis=2)
    colour_png, grey_png = str(tmp_path / "c.png"), str(tmp_path / "g.png")
    imgio.save(colour_png, rgb); imgio.save(grey_png, grey3[..., 0])
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(tmp_path / "s.ini"))
    win, model = studio.build_window()
    win.show(); _pump(0.3)
    try:
        assert win._file_has_colour(colour_png) is True and win._file_has_colour(grey_png) is False
        assert win._file_has_colour(str(tmp_path / "missing.png")) is False
        assert win._load_image_path(colour_png); _pump(0.1)
        assert model.image.ndim == 2                                   # 読み方そのものは変えていない
        assert "greyscale" in win.statusBar().currentMessage()
        assert win._load_image_path(grey_png); _pump(0.1)
        assert "greyscale" not in win.statusBar().currentMessage()
    finally:
        studio._UI_LANG["code"] = "en"
        win.close_guard = lambda: True
        win.quiesce(); win.close(); _pump(0.1)
