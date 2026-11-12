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


def test_out_of_range_knobs_are_reported_after_apply(tmp_path, monkeypatch):
    """P-13: `gaussian (9.0, -3.0)` は通って 0..1 に丸めて走る。何を何として走らせたかを Program の状態欄で言う。"""
    pytest.importorskip("PySide6")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6 import QtWidgets
    import studio
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(tmp_path / "s.ini"))
    win, model = studio.build_window()
    win.show(); _pump(0.3)
    try:
        assert studio.parse_hdev_program_lines("gaussian (9.0, -3.0)", {"gaussian"})[0] == [("gaussian", 1.0, 0.0)]
        assert studio.hdev_last_clamped() == ["gaussian a=9 → 1", "gaussian b=-3 → 0"]
        studio.parse_hdev_program_lines("gaussian (0.2, 0.3)", {"gaussian"})
        assert studio.hdev_last_clamped() == []                          # 解析のたびに空になる
        prog = win._program
        prog["edit"].setPlainText("gaussian (9.0, -3.0)"); prog["apply"](); _pump(0.3)
        text = prog["status"]().text()
        assert "gaussian a=9 → 1" in text and "gaussian b=-3 → 0" in text, text
        assert len(model.stages) == 1                                    # 実行そのものは止めていない
        prog["edit"].setPlainText("gaussian (0.4, 0.5)"); prog["apply"](); _pump(0.3)
        assert "→" not in prog["status"]().text()
    finally:
        studio._UI_LANG["code"] = "en"
        win.close_guard = lambda: True
        win.quiesce(); win.close(); _pump(0.1)


# --------------------------------------------------------------------------- 手書きのヘルプ 3 本(P-08)
_HAND = ("gaussian", "otsu", "sobel_mag")


def _help(name, lang=None):
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fn = "%s.%s.html" % (name, lang) if lang else "%s.html" % name
    with open(os.path.join(here, "studio_assets", "op_help", fn), encoding="utf-8") as f:
        return f.read()


def test_hand_authored_help_has_a_japanese_page_in_step_with_the_english_one():
    import re
    for name in _HAND:
        en, ja = _help(name), _help(name, "ja")
        links = lambda s: sorted(re.findall(r'href="((?:op|sample|run):[^"]+)"', s))
        assert links(en) == links(ja) and len(links(en)) >= 5, name          # 同じリンク(実行できるサンプルを含む)
        assert en.count("<h3") == ja.count("<h3") == 4, name                  # 同じ節
        text = re.sub(r"<pre.*?</pre>|<code.*?</code>|<[^>]+>", "", ja, flags=re.S)
        kana = sum(1 for ch in text if "\u3040" <= ch <= "\u30ff")
        assert kana >= 60, (name, kana)                                        # 中身が日本語
        for word in ("Arguments", "Usage", "Sample code", "Related operators", "reserved", "unused"):
            assert word not in ja, (name, word)


def test_hand_authored_help_says_what_the_knobs_really_do():
    """直す前の英語版は otsu の a を「しきい値の偏り」、sobel_mag の a を「出力の利得」、gaussian の b を
    「未使用」と書いていた。実装は otsu / sobel_mag が a・b とも未使用、gaussian の b は端の扱い。"""
    import fullseye as fs
    rng = np.random.default_rng(3)
    img = np.clip(rng.normal(0.3, 0.05, (48, 64)), 0, 1); img[14:30, 20:44] += 0.4
    for name in ("otsu", "sobel_mag"):
        ref = fs.apply(img, name, 0.5, 0.5)
        for a, b in ((0.05, 0.5), (0.95, 0.5), (0.5, 0.05), (0.5, 0.95)):
            assert np.array_equal(fs.apply(img, name, a, b), ref), (name, a, b)
        page = _help(name)
        assert page.count("unused") >= 2 and "bias applied" not in page and "output gain" not in page, name
    lo, hi = fs.apply(img, "gaussian", 0.5, 0.2), fs.apply(img, "gaussian", 0.5, 0.9)
    diff = np.abs(lo - hi)
    assert diff.max() > 1e-6                                   # b は効く
    assert diff[12:-12, 12:-12].max() < 1e-12                  # ただし端の近くだけ(σ = 1.65、窓の半径 7)
    assert "border" in _help("gaussian") and "reserved / unused" not in _help("gaussian")
    assert "端の扱い" in _help("gaussian", "ja")


# --------------------------------------------------------------------------- 対訳の表が画面に届いているか
def test_every_translated_row_in_the_table_reaches_tr():
    """i18n.json の最上位に置いた行は、一覧に載った一部しか読まれていなかった(検索結果の見出し・「試す」
    「ヘルプ」のボタンが日本語 UI でも英語のままだった)。最上位の行は全部 tr() に届く。"""
    import json
    pytest.importorskip("PySide6")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    import studio
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(here, "studio_assets", "i18n.json"), encoding="utf-8") as f:
        data = json.load(f)
    top = [k for k, v in data.items() if k not in studio._I18N_SECTIONS and isinstance(v, dict)]
    assert len(top) >= 20
    prev = studio._UI_LANG["code"]
    studio._UI_LANG["code"] = "ja"
    try:
        dead = [k for k in top if "ja" in data[k] and studio.tr(k) != data[k]["ja"]]
        assert not dead, dead
        assert studio.tr("Applicable to the current input") == "現在の入力に適用できる"
        assert studio.tr("Common choices") == "定番"
    finally:
        studio._UI_LANG["code"] = prev


def test_every_tr_literal_in_studio_has_a_japanese_row():
    """studio.py の tr("…") に渡している文は、全部が表に日本語の行を持つ(持たないと日本語 UI に英語が残る)。"""
    import ast
    pytest.importorskip("PySide6")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    import studio
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(here, "studio.py"), encoding="utf-8") as f:
        tree = ast.parse(f.read())
    keys = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "tr"
                and len(node.args) == 1 and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)):
            keys.add(node.args[0].value)
    assert len(keys) >= 200                                      # 走査が空を通していない
    same_in_japanese = {"A | B"}                                 # 記号だけで訳すものが無い
    missing = sorted(k for k in keys - same_in_japanese if "ja" not in studio.STRINGS_I18N.get(k, {}))
    assert not missing, missing


# --------------------------------------------------------------------------- 「未使用」と出すつまみ
def test_knobs_shown_as_unused_really_do_nothing():
    """Studio が「b (–) · この op では使いません」と出して無効にするつまみは、動かしても出力が変わらない。

    直す前: gaussian / mean_box / median の b(端の扱い)と gerode / gdilate / gopen / gclose の b(構造要素の形)が
    「未使用」と出て、つまみが無効になっていた(vol_gaussian の b を合わせて 8 本。値域の両端まで振ると出力が最大 0.23〜0.54 動く)。
    """
    import warnings
    pytest.importorskip("PySide6")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    import fullseye as fs
    import param_specs
    import studio
    rng = np.random.default_rng(5)
    img = np.clip(rng.normal(0.35, 0.08, (72, 96)), 0, 1); img[20:50, 30:70] += 0.35
    img = np.clip(img, 0, 1)
    inputs = (img, (img > 0.5).astype(np.float64), np.clip(rng.random((12, 24, 24)), 0, 1))
    claims = {}
    for name, roles in studio._ARG_ROLES.items():
        for letter, role in zip("ab", roles):
            if role == "":
                claims.setdefault(name, set()).add(letter)
    for name in param_specs.PARAM_SPECS:
        sp = param_specs.spec_for(name)
        for letter in "ab":
            if sp[letter].get("kind") == "unused":
                claims.setdefault(name, set()).add(letter)
    assert len(claims) >= 50
    checked, moved = 0, []
    for name, letters in sorted(claims.items()):
        for letter in sorted(letters):
            for x in inputs:
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        outs = [np.asarray(fs.apply(x, name, v if letter == "a" else 0.5,
                                                    v if letter == "b" else 0.5, on_error="raise"), float)
                                for v in (0.07, 0.31, 0.5, 0.69, 0.93)]
                except Exception:                                   # noqa: BLE001 — この入力の型では走らない
                    continue
                checked += 1
                if any(o.shape != outs[2].shape or not np.array_equal(o, outs[2], equal_nan=True) for o in outs):
                    moved.append((name, letter))
                break
    assert checked >= 45, checked                                   # 走った件数に下限(空を通さない)
    assert not moved, moved


def test_border_and_shape_choices_follow_the_op_source():
    import ops
    import param_specs as PS
    for name in ("gaussian", "mean_box", "median"):
        sp = PS.spec_for(name)["b"]
        assert sp["choices"] == ["reflect", "nearest", "constant", "wrap"]
        for x in np.linspace(0.0, 1.0, 1201):
            assert sp["choices"][PS.knob_to_display(sp, x)] == ops._border(x), (name, x)
        for i in range(4):
            assert PS.knob_to_display(sp, PS.display_to_knob(sp, i)) == i
        assert PS.display_to_knob(sp, 0) == 0.5                     # 既定(reflect)は保存済みの値 0.5 のまま
    shape = PS.spec_for("gdilate")["b"]
    assert shape["choices"] == ["square", "cross", "disc", "line"]
    for name in ("gerode", "gdilate", "gopen", "gclose"):
        assert PS.spec_for(name)["b"] is shape or PS.spec_for(name)["b"]["choices"] == shape["choices"]
    for x in np.linspace(0.0, 1.0, 601):
        se = ops._se(x, 7)
        want = PS.knob_to_display(shape, x)
        got = 0 if se is None else (1 if se.sum() == 13 else (3 if se.sum() == 7 else 2))
        assert got == want, x
