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
    ("edge detection", "sobel_amp"), ("fill holes", "fill_up"), ("template matching", "ncc_locate"),
    ("左右反転", "mirror_image"), ("エッジ保存平滑", "bilateral"), ("edge preserving smoothing", "bilateral"),
    ("顕微鏡の画像を二値化", "otsu"),
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
        assert studio.hdev_last_clamped() == ["line 1: gaussian a=9 → 1", "line 1: gaussian b=-3 → 0"]
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



# --------------------------------------------------------------------------- 2 回目の独立レビュー(2026-11-12)
@pytest.mark.parametrize("query", [
    "顕微鏡", "楕円", "account", "discount", "knowledge", "hedge", "nothing", "smoothness",
    "canny edge", "median blur", "circle_fit", "area_open", "line", "count", "area",
])
def test_staples_do_not_fire_on_unrelated_or_name_queries(query):
    """部分一致の誤爆(顕微鏡 → mirror、account → ラベリング、nothing → skeleton …)と、op 名を含む問い合わせ。"""
    assert ss.staples_for(query) == [], query


def test_mirror_and_invert_are_told_apart():
    assert ss.staples_for("左右反転") == ["mirror_image"]
    assert ss.staples_for("反転") == ["invert_image"]
    assert "sobel_amp" not in ss.staples_for("edge preserving smoothing")
    assert "sobel_amp" not in ss.staples_for("エッジ保存平滑")


def test_first_search_with_staples_is_not_slow():
    """定番の行は索引から直接組む(op ごとに検索を呼ぶと最初の検索が約 1 秒かかった)。"""
    import time
    ss.search_grouped("ぼかし", _image(), k=10, lang="ja")              # 索引を温める
    ss.clear_caches()
    t0 = time.perf_counter()
    res = ss.search_grouped("二値化", _image(), k=10, lang="ja")
    dt = time.perf_counter() - t0
    assert res["staples"] and res["staples"][0]["label"] != "otsu"       # 日本語の要約は付いている
    assert dt < 0.6, dt


def _studio_window(tmp_path, monkeypatch):
    pytest.importorskip("PySide6")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6 import QtWidgets
    import studio
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(tmp_path / "s.ini"))
    win, model = studio.build_window()
    win.show(); _pump(0.3)
    return studio, win, model


def _close_window(studio, win):
    studio._UI_LANG["code"] = "en"
    win.close_guard = lambda: True
    win.quiesce(); win.close(); _pump(0.1)


def test_enter_inserts_the_top_search_hit_not_a_staple(tmp_path, monkeypatch):
    """定番の欄を先頭に出しても、Enter が入れるのは検索の 1 位(「blur」で Enter → 定番の gaussian ではなく 1 位)。"""
    studio, win, model = _studio_window(tmp_path, monkeypatch)
    try:
        ui = win._search_ui
        win._ops_fit["check"].setChecked(False)
        ui["edit"].setText("blur"); ui["search_now"]("blur"); _pump(0.3)
        rows = ui["rows"]()
        assert rows["staples"], "この試験は定番が出る語で行う"
        ranked = [r["name"] for g in ("applicable", "needs_preprocessing", "other") for r in rows[g]]
        n0 = len(model.stages)
        ui["list"].setCurrentItem(None)
        ui["edit"].returnPressed.emit(); _pump(0.3)
        assert len(model.stages) == n0 + 1
        # 1 位が、この環境に無い op(optional backend が未導入)の事がある(CI の py3.12 / py3.14 で
        # 「blur」の 1 位が xkor_bilateral だった)。その時は、入れられる最初の行が入る。
        addable = [n for n in ranked if studio.api.find_op(n) is not None]
        assert addable, ranked[:5]
        assert model.stages[-1][0] == studio.api.find_op(addable[0]).name, (
            model.stages[-1][0], ranked[:3], rows["staples"][0]["name"])
        assert model.stages[-1][0] != rows["staples"][0]["name"] or addable[0] == rows["staples"][0]["name"]
    finally:
        _close_window(studio, win)


def test_enter_skips_a_top_hit_that_is_not_installed_here(tmp_path, monkeypatch, capfd):
    """検索の 1 位がこの環境で呼べない op でも、Enter は次の入れられる行を入れ、例外を出さない(2026-11-13 の回帰)。"""
    studio, win, model = _studio_window(tmp_path, monkeypatch)
    try:
        ui = win._search_ui
        win._ops_fit["check"].setChecked(False)
        ui["edit"].setText("blur"); ui["search_now"]("blur"); _pump(0.3)
        rows = ui["rows"]()
        ranked = [r["name"] for g in ("applicable", "needs_preprocessing", "other") for r in rows[g]]
        real = studio.api.find_op
        addable = [n for n in ranked if real(n) is not None]
        assert len(addable) >= 2, ranked[:5]
        gone = addable[0]                                   # 1 位が「未導入」だった事にする
        monkeypatch.setattr(studio.api, "find_op", lambda name, *a, **k: None if name == gone else real(name, *a, **k))
        n0 = len(model.stages)
        ui["list"].setCurrentItem(None)
        ui["edit"].returnPressed.emit(); _pump(0.3)
        assert len(model.stages) == n0 + 1
        assert model.stages[-1][0] == real(addable[1]).name, (model.stages[-1][0], addable[:3])
        # 無い op を自分で選んで入れようとした時は、入らず、例外も出ない。
        from PySide6 import QtCore as _QtCore
        items = [ui["list"].item(i) for i in range(ui["list"].count())]
        target = [it for it in items if it.data(_QtCore.Qt.UserRole) == gone]
        assert target, gone
        n1 = len(model.stages)
        ui["list"].itemActivated.emit(target[0]); _pump(0.3)
        assert len(model.stages) == n1
        assert "Traceback" not in capfd.readouterr().err
    finally:
        _close_window(studio, win)


def test_search_rows_refit_when_the_list_gets_narrower(tmp_path, monkeypatch):
    """検索の後でパネルを狭めても、行とボタンが一覧の見える幅に収まる(P-19 の症状が戻らない)。"""
    studio, win, _model = _studio_window(tmp_path, monkeypatch)
    try:
        ui = win._search_ui
        lst = ui["list"]
        ui["search_now"]("二値化"); _pump(0.3)
        lst.setFixedWidth(max(300, lst.width() // 2)); _pump(0.3)
        vw = lst.viewport().width()
        rows = [r for g in ui["rows"]().values() for r in g]
        assert len(rows) >= 5
        for r in rows:
            assert lst.visualItemRect(r["item"]).width() <= vw, (r["name"], vw)
            b = r["help_button"]
            assert b.mapTo(lst.viewport(), b.rect().topRight()).x() <= vw, (r["name"], vw)
    finally:
        _close_window(studio, win)


def test_choice_knob_slider_range_is_reset_when_the_spec_changes(tmp_path, monkeypatch):
    """choice のスライダに前の spec の範囲が残っていた(int の後に開くと右端が knob 0.04 になった)。"""
    studio, win, model = _studio_window(tmp_path, monkeypatch)
    try:
        for name in ("reg_erode", "gaussian", "median"):
            model.add_stage(name, 0.5, 0.5)
        model.step_states()
        ra, rb = win._knob_rows
        for first, second in ((0, 2), (0, 1), (2, 1)):
            win._refresh_stage_list(select=first); _pump(0.05)
            win._refresh_stage_list(select=second); _pump(0.05)
            for row in (ra, rb):
                if row.spec.get("kind") == "choice" and row.slider:
                    assert (row.slider.minimum(), row.slider.maximum()) == (0, 100), (first, second, row.spec["label"])
        win._refresh_stage_list(select=2); _pump(0.05)                 # median: a は窓の大きさ(choice)
        ra.slider.setValue(ra.slider.maximum()); _pump(0.05)
        assert model.stages[2][1] > 0.75                                # 右端 = いちばん大きい窓(3 に戻らない)
    finally:
        win._knob_timer.stop()
        _close_window(studio, win)


def test_non_finite_knobs_are_a_parse_error_and_clamp_notes_follow_live_lines():
    pytest.importorskip("PySide6")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    import studio
    names = {"gaussian", "median"}
    stages, errs, _lines = studio.parse_hdev_program_lines("gaussian (nan, 0.5)", names)
    assert stages == [] and errs and "finite" in errs[0]
    stages, errs, _lines = studio.parse_hdev_program_lines("median (inf, 0.5)", names)
    assert stages == [] and errs
    # if 0 の中の行は走らないので知らせない。走る行は行番号つき。丸め誤差(1.0000000001)は知らせない
    text = "if 0\ngaussian (9, 0.5)\nendif\nmedian (0.5, 2)\ngaussian (1.0000000001, 0.5)"
    stages, errs, lines = studio.parse_hdev_program_lines(text, names)
    assert not errs and [s[0] for s in stages] == ["median", "gaussian"] and lines == [4, 5]
    assert studio.hdev_last_clamped() == ["line 4: median b=2 → 1"]


def test_colour_check_does_not_decode_the_full_image(tmp_path):
    """カラーの判定は縮めた絵で行う(全画素を float64 で復号し直していた: 8000×6000 で 2.46 GB)。"""
    Image = pytest.importorskip("PIL.Image")
    pytest.importorskip("PySide6")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    import tracemalloc
    from PySide6 import QtWidgets
    import studio
    big = np.zeros((3000, 4000, 3), np.uint8); big[..., 0] = 200; big[1000:2000, :, 2] = 90
    colour, grey = str(tmp_path / "big.jpg"), str(tmp_path / "grey.png")
    Image.fromarray(big).save(colour, quality=80)
    Image.fromarray(big[..., 0]).save(grey)
    rgba_grey = np.dstack([big[..., 0]] * 3 + [np.full(big.shape[:2], 255, np.uint8)])
    grey_rgba = str(tmp_path / "grey_rgba.png"); Image.fromarray(rgba_grey[:300, :400]).save(grey_rgba)
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    prev_ini = os.environ.get("FULLSEYE_STUDIO_SETTINGS")     # セッションの隔離の値。終わりに必ず戻す
    os.environ["FULLSEYE_STUDIO_SETTINGS"] = str(tmp_path / "s.ini")
    win, _model = studio.build_window()
    try:
        tracemalloc.start()
        assert win._file_has_colour(colour) is True
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        assert peak < 80 * 1024 * 1024, peak          # 全画素の float64 カラーなら 288 MB
        assert win._file_has_colour(grey) is False and win._file_has_colour(grey_rgba) is False
    finally:
        if prev_ini is None:
            os.environ.pop("FULLSEYE_STUDIO_SETTINGS", None)
        else:
            os.environ["FULLSEYE_STUDIO_SETTINGS"] = prev_ini
        studio._UI_LANG["code"] = "en"
        win.close_guard = lambda: True
        win.quiesce(); win.close(); _pump(0.1)


def test_sobel_help_states_the_real_normalisation():
    """ヘルプは「自分の最大値で割る」。実装もそうである(最小〜最大での引き伸ばしではない)。"""
    import fullseye as fs
    from scipy import ndimage
    rng = np.random.default_rng(3)
    img = np.clip(rng.normal(0.3, 0.05, (48, 64)), 0, 1); img[14:30, 20:44] += 0.4
    out = np.asarray(fs.apply(img, "sobel_mag", 0.5, 0.5), float)
    mag = np.hypot(ndimage.sobel(img, 1), ndimage.sobel(img, 0))
    assert np.allclose(out, mag / mag.max(), atol=1e-12)
    assert out.min() > 0.0 and out.max() == pytest.approx(1.0)        # 最小は 0 に引き伸ばされない
    assert "divided by its own maximum" in _help("sobel_mag") and "最大値で割る" in _help("sobel_mag", "ja")
    assert "minimum and maximum" not in _help("sobel_mag")


def test_op_list_rows_are_compact_and_search_rows_keep_their_height(monkeypatch, tmp_path):
    """op の一覧の行は「文字の高さ + 数 px」。様式が足す余白で 2 倍近くに膨らまない(Windows 11 の様式で 30 px だった)。
    検索結果の行(名前・説明・ボタン)は自分の高さを保つ。"""
    pytest.importorskip("PySide6")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6 import QtWidgets
    import studio
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(tmp_path / "s.ini"))
    win, _model = studio.build_window()
    win.show(); _pump(0.4)
    try:
        ol = win._op_list
        fm = ol.fontMetrics().height()
        assert ol.count() > 100
        rows = [ol.sizeHintForRow(i) for i in range(10)]
        assert all(fm <= h <= fm + studio._OP_ROW_PAD + 2 for h in rows), (fm, rows)
        # 行の高さの指定そのもの(既定の様式では差が出ないので、QSS の height を直接確かめる)
        assert "height: %dpx" % (fm + studio._OP_ROW_PAD) in ol.styleSheet(), ol.styleSheet()
        win._search_ui["search_now"]("threshold"); _pump(0.5)
        tall = [ol.sizeHintForRow(i) for i in range(ol.count())]
        assert max(tall) >= 2 * fm, tall[:8]            # 説明とボタンのある行は潰れていない
    finally:
        win.close_guard = lambda: True
        win.quiesce(); win.close(); _pump(0.1)


def test_op_list_rows_stay_compact_under_the_windows11_style_when_available(monkeypatch, tmp_path):
    """Windows 11 相当の様式(行に上下 14 px を足す)を使える Qt では、その様式での実測。使えない環境は skip。"""
    pytest.importorskip("PySide6")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6 import QtWidgets
    import studio
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    if "windows11" not in [k.lower() for k in QtWidgets.QStyleFactory.keys()]:
        pytest.skip("this Qt has no windows11 style")
    prev = app.style().objectName()
    app.setStyle("windows11")
    try:
        monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(tmp_path / "s.ini"))
        win, _model = studio.build_window()
        win.show(); _pump(0.4)
        try:
            ol = win._op_list
            fm = ol.fontMetrics().height()
            rows = [ol.sizeHintForRow(i) for i in range(10)]
            assert len(rows) == 10 and all(h <= fm + studio._OP_ROW_PAD + 2 for h in rows), (fm, rows)
        finally:
            win.close_guard = lambda: True
            win.quiesce(); win.close(); _pump(0.1)
    finally:
        app.setStyle(prev)


def test_startup_language_decision():
    """起動時の分岐(offscreen では build_window の中で走らない)を関数に切り出して試験する。"""
    import studio
    f = studio._startup_language
    assert f("de", "ja_JP") == "de" and f("en", "ja_JP") == "en"          # 保存があればそれ(OS が変わっても追従しない)
    assert f(None, "ja_JP") == "ja" and f(None, "zh_TW") == "tw" and f(None, "fr_FR") == "en"   # 初回は OS から
    assert f("xx", "ko_KR") == "ko" and f("", "ja_JP") == "ja"            # 表に無い保存値は初回と同じ扱い
    assert f(None, "ja_JP", languages={"en": "English"}) == "en"


def test_first_run_language_follows_the_os_locale():
    """初回起動の言語は OS の言語から決める(日本語の Windows で英語の画面から始まっていた)。表に無い言語は英語。"""
    import studio
    f = studio.lang_from_locale
    assert f("ja_JP") == "ja" and f("ja") == "ja" and f("ja-JP") == "ja"
    assert f("zh_CN") == "zh" and f("zh_Hans_CN") == "zh" and f("zh_SG") == "zh"
    assert f("zh_TW") == "tw" and f("zh_HK") == "tw" and f("zh_Hant_TW") == "tw" and f("zh-Hant") == "tw"
    assert f("ko_KR") == "ko" and f("de_AT") == "de" and f("hi_IN") == "hi"
    assert f("en_US") == "en" and f("fr_FR") == "en" and f("C") == "en" and f("") == "en" and f(None) == "en"
    assert f("ja_JP", languages={"en": "English"}) == "en"          # 表に無ければ英語
    assert all(f(code) == code for code in studio.LANGUAGES)        # 表の言語は全部自分に決まる


def test_bare_ambiguous_words_give_no_staple_but_the_specific_phrases_do():
    """2 回目のレビュー(f54982b9f9)で**意図して**狭めた語。単独の「鏡」「左右」「上下」「ラベル」は誤爆するので定番を出さない
    (顕微鏡・上下限・左右対称・ラベル文字列)。具体的な言い方では出る。3 回目のレビューで「意図した変更か」を確かめて固定した。"""
    for bare in ("鏡", "左右", "上下", "ラベル", "顕微鏡"):
        assert ss.staples_for(bare) == [], bare
    assert ss.staples_for("左右反転") == ["mirror_image"] and "mirror_image" in ss.staples_for("上下を反転")
    assert ss.staples_for("鏡像")[:1] == ["mirror_image"]
    for phrase in ("ラベル付け", "ラベリング"):
        assert "connect_and_holes" in ss.staples_for(phrase), phrase


@pytest.mark.parametrize("word", ["equalize", "invert", "skeleton", "thinning", "difference"])
def test_english_words_that_are_also_op_names_give_no_staple_by_design(word):
    """op 名と同じ英語の語は単独では定番を出さない。「op 名そのものを打った人の先頭に別の op を置かない」決まりの結果で、
    そのままにしている(困るなら、語を 2 つ以上にするか、別の言い方 equalise / skeletonize / negative を使う)。"""
    assert ss._row_of(word) is not None                  # 理由: その語は op 名として索引に在る
    assert ss.staples_for(word) == []
    assert ss.staples_for(word + "_") == []


def test_recent_images_with_one_entry_survive_a_restart(tmp_path, monkeypatch):
    """最近開いた画像が 1 件だけの時、設定の読み戻しが str を返す事があり、パスが 1 文字ずつの項目になっていた(2026-11-13)。

    QSettings は 1 件だけの列を str で返す事がある(形式と中身による)。その場合を直接作って確かめる。"""
    import studio as _studio
    from PySide6 import QtWidgets
    target = str(tmp_path / "one image.png")
    real = _studio._settings

    class _OneStringSettings:
        """recent_files だけ str を返す(1 件だけの列が str で戻る QSettings の振る舞い)。"""
        def __init__(self):
            self._s = real()

        def value(self, key, default=None, *args, **kw):
            if key == "recent_files":
                return target
            return self._s.value(key, default, *args, **kw)

        def __getattr__(self, name):
            return getattr(self._s, name)

    monkeypatch.setattr(_studio, "_settings", _OneStringSettings)
    studio, win, model = _studio_window(tmp_path, monkeypatch)
    try:
        menus = [m for m in win.findChildren(QtWidgets.QMenu)
                 if any("one image.png" in a.text() or a.text().strip() in ("o", "n", "e") for a in m.actions())]
        assert len(menus) == 1, [m.title() for m in menus]
        texts = [a.text() for a in menus[0].actions() if a.text() and not a.isSeparator()]
        files = [x for x in texts if "one image.png" in x]
        assert len(files) == 1, texts
        assert len(texts) <= 3, texts          # 1 件 +「消す」などの項目。1 文字ずつなら数十になる
    finally:
        _close_window(studio, win)


def test_adding_a_two_input_op_says_why_it_was_not_added(tmp_path, monkeypatch, capfd):
    """2 入力の op を入れようとした時、「optional backend が未導入」と誤った理由を言っていた(2026-11-13)。"""
    studio, win, model = _studio_window(tmp_path, monkeypatch)
    try:
        said = []
        ui = win._search_ui
        nary = sorted(studio.api._nary_by_name())
        assert nary, "2 入力の op が 1 つも無い"
        name = next((n for n in nary if studio.api.find_op(n) is None), None)
        assert name, nary[:5]
        ui["edit"].setText(name); ui["search_now"](name); _pump(0.3)
        from PySide6 import QtCore as _QtCore
        items = [ui["list"].item(i) for i in range(ui["list"].count())]
        target = [it for it in items if it.data(_QtCore.Qt.UserRole) == name]
        assert target, name
        bar = win.statusBar()
        n0 = len(model.stages)
        ui["list"].itemActivated.emit(target[0]); _pump(0.3)
        said.append(bar.currentMessage())
        assert len(model.stages) == n0
        assert "two or more inputs" in said[0], said
        assert "optional backend" not in said[0]
        assert "Traceback" not in capfd.readouterr().err
    finally:
        _close_window(studio, win)
