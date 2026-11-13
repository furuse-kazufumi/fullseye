# -*- coding: utf-8 -*-
"""初めて起動した人の体験の点検(2026-11-13)で見つかったつまずきの回帰試験。

点検の番号(S2・M1 …)を試験の説明に書く。窓は offscreen で実際に作り、キーとマウスは QTest で送る。
設定は試験ごとの一時ファイル(利用者の本物の設定には触らない)。
"""
import os
import re
import time

import numpy as np
import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import api  # noqa: E402
import studio  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CJK = re.compile("[\u3040-\u30ff\u4e00-\u9fff]")


def _pump(sec=0.2):
    from PySide6 import QtWidgets
    end = time.monotonic() + sec
    while time.monotonic() < end:
        QtWidgets.QApplication.processEvents(); time.sleep(0.01)


@pytest.fixture
def launch(tmp_path, monkeypatch):
    """``launch(lang="en", user=False)`` -> (win, model).  Every window gets its own settings file and is
    closed at the end of the test.  ``user=True`` also does what ``main()`` does for a user-started window."""
    from PySide6 import QtWidgets
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    opened = []
    prev_hooks = (studio.ERROR_HOOK, studio.CONFIRM_HOOK)

    def _launch(lang="en", user=False, size=(1366, 768)):
        monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(tmp_path / ("s%d.ini" % len(opened))))
        win, model = studio.build_window()
        if lang != "en":
            win._apply_language(lang)
        win.resize(*size); win.show(); _pump(0.3)
        if user:                                # main() と同じ順(show の後)
            win._first_launch_scene(); _pump(0.2)
        opened.append(win)
        return win, model

    yield _launch
    studio._UI_LANG["code"] = "en"
    studio.ERROR_HOOK, studio.CONFIRM_HOOK = prev_hooks
    for win in opened:
        win.close_guard = lambda: True
        win.quiesce(); win.close()
    _pump(0.1)


def _names(win):
    """一覧に出ている op の名前(見出しの行は除く)。"""
    from PySide6 import QtCore
    lst = win._op_list
    return [lst.item(i).data(QtCore.Qt.UserRole) for i in range(lst.count())
            if lst.item(i).data(QtCore.Qt.UserRole)]


def _item(win, name):
    from PySide6 import QtCore
    lst = win._op_list
    hit = [lst.item(i) for i in range(lst.count()) if lst.item(i).data(QtCore.Qt.UserRole) == name]
    assert hit, "%s is not listed" % name
    return hit[0]


def _click_row(win, item):
    from PySide6 import QtCore
    from PySide6.QtTest import QTest
    lst = win._op_list
    lst.scrollToItem(item); _pump(0.05)
    QTest.mouseClick(lst.viewport(), QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, lst.visualItemRect(item).center())
    _pump(0.1)


# --------------------------------------------------------------------------- #
# S2: 検索が空の時の op の一覧                                                   #
# --------------------------------------------------------------------------- #
def test_s2_browse_list_starts_from_the_staples(launch):
    """直す前は先頭の 17 行が 2 入力の op で、どれも入れられなかった。一覧は定番から始まる。"""
    win, _model = launch()
    names = _names(win)
    starters = studio.starter_ops()
    assert len(starters) >= 15, starters
    assert tuple(starters[:5]) == studio.STARTER_HEAD == ("gaussian", "median", "sobel_amp", "otsu", "threshold")
    shown_starters = [n for n in starters if n in names]
    assert len(shown_starters) >= 15
    assert names[:len(shown_starters)] == shown_starters
    # 定番は、定番の表(studio_search.STAPLES)の各組の先頭から取っている(別の表を持たない)
    import studio_search
    firsts = {ops_[0] for _t, ops_ in studio_search.STAPLES}
    assert set(starters) <= firsts | set(studio.STARTER_HEAD)


def test_s2_rows_that_cannot_be_a_stage_come_last_and_are_marked(launch):
    from PySide6 import QtCore
    win, _model = launch()
    win._ops_fit["check"].setChecked(False); _pump(0.1)             # 全部の op を並べる
    names = _names(win)
    rows = {r["name"]: r for r in api.list_ops(include_algo=True)}
    assert len(names) == len(rows) > 900                           # 並べ替えで行を落としていない
    ok = [studio.op_insertable(n, rows[n])[0] for n in names]
    n_bad = ok.count(False)
    assert n_bad >= 17, n_bad                                      # 2 入力の 17 本 + 一般アルゴリズム
    assert all(ok[:-n_bad]) and not any(ok[-n_bad:]), "入れられない op が末尾にまとまっていない"
    marked = [n for n in names if _item(win, n).data(QtCore.Qt.UserRole + 5)]
    assert marked == names[-n_bad:]
    two_input = [n for n in names if studio.op_insertable(n, rows[n])[1] == "two_input"]
    assert len(two_input) >= 10 and "abs_diff_image" in two_input
    assert "cannot be added as a stage" in _item(win, "abs_diff_image").text()
    assert "cannot be added as a stage" not in _item(win, "gaussian").text()


def test_s2_first_stage_lists_only_ops_that_can_take_the_loaded_image(launch):
    """「前段の出力を受けられる op だけ表示」が入っている時、最初の段でも beatcube 用のレーダーの op は並ばない。"""
    win, model = launch()
    rows = {r["name"]: r for r in api.list_ops(include_algo=True)}
    radar = [n for n, r in rows.items() if r["in_sort"] == "beatcube"]
    assert len(radar) >= 3, radar
    assert win._ops_fit["check"].isChecked() and not model.stages
    names = _names(win)
    assert 300 < len(names) < len(rows)
    sorts = {rows[n]["in_sort"] for n in names}
    assert sorts <= {"image", "region", "any"}, sorts
    assert not set(radar) & set(names)
    assert "First stage" in win._ops_fit["note"].text() and str(len(names)) in win._ops_fit["note"].text()
    win._ops_fit["check"].setChecked(False); _pump(0.1)             # スイッチを切れば全部出る
    assert set(radar) <= set(_names(win)) and len(_names(win)) == len(rows)


def test_s2_entry_rule_is_a_pure_function():
    rows = api.list_ops(include_algo=True)
    assert len(rows) > 900
    grey = np.linspace(0, 1, 64 * 64).reshape(64, 64)
    assert studio.entry_sort_of(grey) == "image"
    assert studio.entry_sort_of((grey > 0.5).astype(float)) == "region"
    assert studio.entry_sort_of(None) is None
    img_rows = studio._ops_accepting_entry(rows, "image")
    assert 300 < len(img_rows) < len(rows)
    assert {r["in_sort"] for r in img_rows} == {"image", "region", "any"}
    assert studio._ops_accepting_entry(rows, "region") == img_rows       # 二値の画像も同じ入口を通る
    assert studio._ops_accepting_entry(rows, None) == rows               # 型が分からなければ絞らない
    vol = studio._ops_accepting_entry(rows, "volume")
    assert vol and {r["in_sort"] for r in vol} <= {"volume", "any"}


def test_s2_first_steps_band_can_be_followed_literally(launch):
    """「最初の 3 手」の帯の文どおりにやって、必ず成功する(直す前は 2 手目で止まった)。"""
    from PySide6 import QtCore, QtWidgets
    from PySide6.QtTest import QTest
    win, model = launch()
    steps = [l.text() for l in win._first_steps.findChildren(QtWidgets.QLabel)]
    text = " ".join(steps)
    # 1 手目: 帯に書いてあるメニュー(File ▸ Sample images)の先頭の画像を開く
    assert "File ▸ Sample images" in text
    file_menu = next(a.menu() for a in win.menuBar().actions() if a.text().replace("&", "") == "File")
    sample_menu = next(a.menu() for a in file_menu.actions() if a.menu() and a.text() == "Sample images")
    assert len(sample_menu.actions()) >= 5
    assert sample_menu.actions()[0].text() == studio.STARTUP_SAMPLE_IMAGE      # M2: 先頭は変化の見える画像
    before = model.image.copy()
    sample_menu.actions()[0].trigger(); _pump(0.3)
    assert model.image.shape != before.shape or not np.array_equal(model.image, before)
    # 2 手目: Operators パネルで op を選び(一覧の先頭の行)、+ を押す
    assert "Operators panel" in text and "+" in text
    lst = win._op_list
    first = lst.item(0)
    first_name = first.data(QtCore.Qt.UserRole)
    assert first_name, "一覧の先頭の行が op でない"
    _click_row(win, first)
    assert lst.currentItem() is first
    QTest.mouseClick(win._op_buttons["insert"], QtCore.Qt.LeftButton); _pump(0.4)
    assert [s[0] for s in model.stages] == [first_name]     # (入れた後、一覧は次の段向けに作り直される)
    # 3 手目: ▶▶ で実行
    assert "▶▶" in text
    win._actions["run_all"].trigger(); _pump(0.6)
    out = model.result_upto(len(model.stages) - 1)
    assert isinstance(out, np.ndarray) and out.shape == model.image.shape
    assert np.isfinite(out).all()
    # M2: 直す前の先頭(gradient)では平均の変化が 0.00004 で、▶▶ を押しても絵が変わらなかった
    assert float(np.abs(out - model.image).mean()) > 0.01, "実行しても絵が変わらない"
    # 先頭だけでなく、最初に見えている行はどれも入れられる
    lst.scrollToTop(); _pump(0.05)
    visible = [lst.item(i) for i in range(lst.count())
               if lst.viewport().rect().contains(lst.visualItemRect(lst.item(i)).center())]
    assert len(visible) >= 8
    assert all(studio.op_insertable(it.data(QtCore.Qt.UserRole))[0] for it in visible)


def test_s2_pressing_plus_on_a_two_input_op_says_why_in_the_ui_language(launch):
    from PySide6 import QtCore
    from PySide6.QtTest import QTest
    win, model = launch(lang="ja")
    win._ops_fit["check"].setChecked(False); _pump(0.1)
    item = _item(win, "abs_diff_image")
    assert "段としては入れられません" in item.text()
    _click_row(win, item)
    QTest.mouseClick(win._op_buttons["insert"], QtCore.Qt.LeftButton); _pump(0.2)
    assert not model.stages
    said = win.statusBar().currentMessage()
    assert "abs_diff_image" in said and "入力が 2 つ以上" in said and _CJK.search(said)
    assert "takes two or more inputs" not in said
    assert "入力が 2 つ以上" in win._op_param.text()                  # + ボタンのすぐ上にも出る
    # 理由の文は 3 種とも表にある
    assert len(studio.NOT_INSERTABLE_TEXT) == 3
    assert all(studio.STRINGS_I18N.get(t, {}).get("ja") for t in studio.NOT_INSERTABLE_TEXT.values())


# --------------------------------------------------------------------------- #
# M1: 検索して Enter で入る op = 見えている先頭の行                                  #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("query,want", [
    ("blur", "gaussian"), ("ぼかす", "gaussian"), ("edge", "sobel_amp"), ("二値化", "otsu"),
    ("canny edge", "canny*"),           # op 名を含む問い合わせ: 定番は出ず、canny の op(11/12 の sobel_amp に戻らない)
])
def test_m1_enter_inserts_the_highlighted_first_row(launch, query, want):
    """直す前: 「blur」で先頭に gaussian が見えているのに、Enter で入るのは下の欄の 1 位(xkor_bilateral)だった。"""
    from PySide6 import QtCore
    from PySide6.QtTest import QTest
    win, model = launch()
    ui = win._search_ui
    lst = ui["list"]
    ui["search_now"](query); _pump(0.2)
    on_screen = [lst.item(i) for i in range(lst.count())
                 if lst.item(i).data(QtCore.Qt.UserRole) and not lst.item(i).isHidden()]
    assert len(on_screen) >= 3, query
    first = next(it for it in on_screen if studio.op_insertable(it.data(QtCore.Qt.UserRole))[0])
    cur = lst.currentItem()
    assert cur is first, (query, cur and cur.data(QtCore.Qt.UserRole), first.data(QtCore.Qt.UserRole))
    name = cur.data(QtCore.Qt.UserRole)
    if want.endswith("*"):
        assert want[:-1] in name and name != "sobel_amp", name
    else:
        assert name == want
    n0 = len(model.stages)
    QTest.keyClick(ui["edit"], QtCore.Qt.Key_Return); _pump(0.3)
    assert [s[0] for s in model.stages[n0:]] == [api.find_op(name).name]


def test_m1_a_clicked_row_stays_the_choice_for_enter(launch):
    """結果が出ている時に Enter で検索し直さない(利用者がクリックで選んだ行が消えていた)。"""
    from PySide6 import QtCore
    from PySide6.QtTest import QTest
    win, model = launch()
    ui = win._search_ui
    lst = ui["list"]
    ui["search_now"]("blur"); _pump(0.2)
    staples = [r["name"] for r in ui["rows"]()["staples"]]
    assert staples[:3] == ["gaussian", "mean_image", "median"], staples
    target = ui["rows"]()["staples"][2]["item"]                     # median を選ぶ
    lst.setCurrentItem(target); _pump(0.05)
    QTest.keyClick(ui["edit"], QtCore.Qt.Key_Return); _pump(0.3)
    assert [s[0] for s in model.stages] == ["median"]


# --------------------------------------------------------------------------- #
# M2: 起動した人が最初に見る画像                                                  #
# --------------------------------------------------------------------------- #
def test_m2_user_window_opens_on_a_sample_every_first_op_visibly_changes(launch):
    from scipy import ndimage
    win, model = launch(user=True)
    import sample_images
    assert studio.STARTUP_SAMPLE_IMAGE == "coins"
    assert np.array_equal(model.image, sample_images.load("coins"))
    # 来歴とライセンスが同梱の一覧にある
    entry = [e for e in sample_images.entries() if e["name"] == studio.STARTUP_SAMPLE_IMAGE]
    assert len(entry) == 1 and entry[0]["source"] and entry[0]["licence"]
    img = np.asarray(model.image, float)
    demo = studio.demo_image()
    for op, floor in (("gaussian", 0.02), ("median", 0.02), ("sobel_amp", 0.1)):
        out = np.asarray(api.find_op(op).fn(img, 0.5, 0.5), float)
        changed = float(np.abs(out - img).mean())
        before = float(np.abs(np.asarray(api.find_op(op).fn(demo, 0.5, 0.5), float) - demo).mean())
        assert changed > floor, (op, changed)
        assert op == "sobel_amp" or changed > 5 * before, (op, changed, before)   # 合成のデモ画像より大きく変わる
    reg = np.asarray(api.find_op("otsu").fn(img, 0.5, 0.5), float) > 0.5
    assert 0.2 < reg.mean() < 0.6                                     # 二値化で前景と背景が分かれる
    filled = ndimage.binary_fill_holes(reg)
    n = ndimage.label(ndimage.binary_opening(filled, iterations=2))[1]
    assert 15 <= n <= 40, n                                           # 粒(コイン)が数えられる
    assert "coins" in win.statusBar().currentMessage()                # 何を開いたかを言う
    from PySide6 import QtWidgets
    readout = win.statusBar().findChildren(QtWidgets.QLabel)[0]
    assert not readout.isVisible()                                    # 文と画素の読み取りが重ならない


def test_m2_build_window_default_and_main_entry(launch):
    """build_window() の既定は合成のデモ画像のまま(試験と埋め込みの前提)。利用者の入口 main() だけが見本を開く。"""
    import inspect
    _win, model = launch()
    assert np.array_equal(model.image, studio.demo_image())
    src = inspect.getsource(studio.main)
    assert src.count("_first_launch_scene()") == 1
    assert src.index("build_window()") < src.index("win.show()") < src.index("_first_launch_scene()")
    order = studio.sample_menu_order(["gradient", "blobs", "coins", "cell"])
    assert order == ["coins", "gradient", "blobs", "cell"]
    assert studio.sample_menu_order(["gradient", "blobs"]) == ["gradient", "blobs"]   # 無ければ並びは同じ


# --------------------------------------------------------------------------- #
# M5・L8: 画素の読み取り / ステータスバーの文                                       #
# --------------------------------------------------------------------------- #
def _hover(win, model, x, y):
    """画像の上でカーソルを動かした時と同じ呼び出し(ImageView.hover_cb)。"""
    from PySide6 import QtWidgets
    view = [w for w in win.findChildren(QtWidgets.QWidget) if type(w).__name__ == "ImageView"][0]
    view.hover_cb(x, y, model.image[y, x])
    return view


@pytest.mark.parametrize("lang,word", [("ja", "値"), ("en", "value")])
def test_m5_readout_has_coordinates_in_the_ui_language(launch, lang, word):
    win, model = launch(lang=lang, user=True)
    _hover(win, model, 12, 34)
    text = win._readout.text()
    assert text.startswith("x=12  y=34   "), text
    assert word in text
    assert bool(_CJK.search(text)) == (lang == "ja"), text
    v = float(model.image[34, 12])
    assert format(v, ".4g") in text                                  # 読んでいる画素の値そのもの


def test_m5_real_mouse_move_over_the_image_gives_coordinates(launch):
    from PySide6 import QtCore
    from PySide6.QtTest import QTest
    win, model = launch(lang="ja", user=True)
    from PySide6 import QtWidgets
    view = [w for w in win.findChildren(QtWidgets.QWidget) if type(w).__name__ == "ImageView"][0]
    vp = view.viewport() if hasattr(view, "viewport") else view
    c = vp.rect().center()
    QTest.mouseMove(vp, c); _pump(0.1)
    QTest.mouseMove(vp, QtCore.QPoint(c.x() + 5, c.y() + 3)); _pump(0.2)
    text = win._readout.text()
    m = re.match(r"x=(\d+)  y=(\d+)   値 ", text)
    assert m, text
    x, y = int(m.group(1)), int(m.group(2))
    h, w = model.image.shape[:2]
    assert 0 <= x < w and 0 <= y < h
    assert abs(x - w // 2) < w // 4 and abs(y - h // 2) < h // 4      # 中央付近を指している


def test_l8_reloading_the_image_clears_the_readout(launch):
    win, model = launch(lang="ja", user=True)
    hint = studio.STRINGS_I18N["hover over the image for pixel coordinates + value"]["ja"]
    _hover(win, model, 3, 4)
    assert win._readout.text().startswith("x=3  y=4")
    win._load_sample_image("blobs"); _pump(0.2)
    assert win._readout.text() == hint                               # 前の画像の値が残らない
    _hover(win, model, 5, 6)
    assert win._readout.text().startswith("x=5  y=6")
    win._load_sample_image("blobs"); _pump(0.2)                      # 同じ名前でも新しく読んだ画像
    assert win._readout.text() == hint


def test_status_messages_get_room_to_be_seen(launch):
    """一時的な文(flash)を描く欄が幅 0 で、どの文も画面に出ていなかった(読み取りの欄は隠れ、右の欄が全幅を取っていた)。"""
    win, model = launch(lang="ja", size=(1366, 768))
    bar = win.statusBar()
    bar.showMessage("x" * 40, 3000); _pump(0.2)
    assert bar.currentMessage()
    first_permanent = min(w.x() for w in (win._img_info, win._run_ui["box"]) if w.isVisible())
    width_for_text = first_permanent - 6
    need = bar.fontMetrics().horizontalAdvance("x" * 40)
    assert width_for_text >= need, (width_for_text, need)


# --------------------------------------------------------------------------- #
# M12: 検索の語彙に現場の言葉                                                     #
# --------------------------------------------------------------------------- #
#: 点検の時に 0 件・無関係だった語(日英)。どれも定番の op が先頭に出る
FIELD_WORDS = ("傷", "きず", "キズ", "擦り傷", "へこみ", "凹み", "打痕", "欠け", "割れ", "ひび", "汚れ", "シミ", "ムラ",
               "異物", "熱", "サーモ", "錆", "刻印", "穴の数", "scratch", "dent", "crack", "stain", "dirt", "mura",
               "foreign fibre", "thermal", "thermography", "rust", "engraved code", "count holes")


@pytest.mark.parametrize("word", FIELD_WORDS)
def test_m12_field_words_reach_insertable_staples(word):
    import studio_search as ss
    names = ss.staples_for(word)
    assert names, word
    assert studio.op_insertable(names[0])[0], (word, names[0])


def test_m12_field_words_reach_the_fa_samples_and_never_the_xray_one():
    import recipes
    import studio_search as ss
    assert ss.samples_for("傷") == ["FA — scratch on hairline metal"]
    assert ss.samples_for("打痕") == ss.samples_for("dent") == ["FA — dent and foreign fibre on resin"]
    assert ss.samples_for("刻印") == ["FA — engraved lot code (binarize for OCR)"]
    assert ss.samples_for("count holes") == ["FA — count holes in a back-lit plate"]
    assert ss.samples_for("ぼかし") == [] and ss.samples_for("canny edge") == []
    names = [n for _t, ns in ss.SAMPLE_TERMS for n in ns]
    assert len(names) == 4 and set(names) <= set(recipes.names())
    assert not any("x-ray" in n.lower() for n in names)
    # X 線・CT に関わる語は表に入れない(定番にも見本にも)
    terms = [t.lower() for tb in (ss.STAPLES, ss.SAMPLE_TERMS) for ts, _ in tb for t in ts]
    assert len(terms) > 100
    for bad in ("x線", "x 線", "x-ray", "xray", "ct", "レントゲン", "透過", "断層", "tomograph", "radiograph"):
        assert not any(bad == t or bad in t.split() or (not bad.isascii() and bad in t) for t in terms), bad
    # 見本の語はどれも定番にもある(画面では定番の直後に並び、Enter で入る先頭の op は変わらない)
    for ts, _names in ss.SAMPLE_TERMS:
        for t in ts:
            assert ss.staples_for(t), t


@pytest.mark.parametrize("query", ["stainless steel", "student", "trust", "industrial", "chip", "文字列"])
def test_m12_words_inside_other_words_do_not_fire(query):
    import studio_search as ss
    assert ss.staples_for(query) == []
    assert ss.samples_for(query) == []


def test_m12_search_shows_the_sample_after_the_staples_and_opens_it_with_its_image(launch):
    from PySide6 import QtCore
    from PySide6.QtTest import QTest
    import sample_images
    win, model = launch(lang="ja", user=True)
    ui = win._search_ui
    lst = ui["list"]
    ui["search_now"]("傷"); _pump(0.3)
    rows = ui["rows"]()
    assert [r["name"] for r in rows["staples"]][:2] == ["sk_rolling_ball", "bothat"]
    assert [r["name"] for r in rows["samples"]] == ["FA — scratch on hairline metal"]
    heads = [lst.item(i).data(QtCore.Qt.UserRole + 4) for i in range(lst.count())
             if lst.item(i).data(QtCore.Qt.UserRole + 4)]
    assert heads[:2] == ["staples", "samples"]
    assert "見本" in rows["samples"][0]["try_button"].text()
    # Enter で入るのは先頭の op(見本の行ではない)
    assert lst.currentItem().data(QtCore.Qt.UserRole) == "sk_rolling_ball"
    # 「見本を開く」で、見本の処理手順と見本の画像の両方が入る
    QTest.mouseClick(rows["samples"][0]["try_button"], QtCore.Qt.LeftButton); _pump(0.5)
    import recipes
    assert [s[0] for s in model.stages] == [st[0] for st in recipes.stages("FA — scratch on hairline metal")]
    assert np.array_equal(model.image, sample_images.load("metal_hairline_scratch"))


# --------------------------------------------------------------------------- #
# M10: 未保存で閉じる時の確認                                                     #
# --------------------------------------------------------------------------- #
def _dirty_pipeline(win, model):
    """+ で段を 1 つ入れる(利用者の操作と同じ経路。未保存になる)。"""
    from PySide6 import QtCore
    lst = win._op_list
    names = [lst.item(i).data(QtCore.Qt.UserRole) for i in range(lst.count())]
    lst.setCurrentRow(names.index("gaussian")); _pump(0.05)
    win._op_buttons["insert"].click(); _pump(0.2)
    assert [s[0] for s in model.stages] == ["gaussian"]


def _close(win):
    from PySide6 import QtGui, QtWidgets
    ev = QtGui.QCloseEvent(); ev.accept()
    QtWidgets.QApplication.sendEvent(win, ev)
    return ev.isAccepted()


def test_m10_quit_asks_with_three_choices_in_the_ui_language(launch, monkeypatch):
    from PySide6 import QtCore, QtWidgets
    win, model = launch(lang="ja")
    _dirty_pipeline(win, model)
    assert win.windowTitle().startswith("untitled*")
    # 本物の窓を出す(ほかの試験のモジュールが CONFIRM_HOOK を差し替えたままの事がある)
    monkeypatch.setattr(studio, "CONFIRM_HOOK", studio._default_confirm)
    monkeypatch.setattr(studio, "CLOSE_CONFIRM_HOOK", studio._default_close_confirm)
    seen = {}
    timer = QtCore.QTimer(); timer.setInterval(50)

    def _inspect():
        box = QtWidgets.QApplication.activeModalWidget()
        if not isinstance(box, QtWidgets.QMessageBox):
            return                                                     # まだ出ていない: 次の 50 ms
        timer.stop()
        seen["title"] = box.windowTitle(); seen["text"] = box.text()
        seen["buttons"] = [b.text() for b in box.buttons()]
        seen["default"] = box.defaultButton().text()
        seen["escape"] = box.escapeButton().text()
        box.escapeButton().click()                                     # Esc と同じ = キャンセル
    timer.timeout.connect(_inspect); timer.start()
    assert _close(win) is False                                       # キャンセル → 閉じない
    assert sorted(seen["buttons"]) == sorted(["保存して閉じる", "保存せずに閉じる", "キャンセル"]), seen
    assert seen["default"] == seen["escape"] == "キャンセル"
    assert seen["title"] == "Fullseye Studio を終了"
    assert "未保存の段 1 個" in seen["text"] and "保存しますか" in seen["text"], seen["text"]
    assert not re.search(r"[A-Za-z]{4,}", seen["text"].replace("Program", "")), seen["text"]


def test_m10_save_and_close_saves_then_closes_and_a_cancelled_save_keeps_the_window(launch, monkeypatch, tmp_path):
    from PySide6 import QtWidgets
    win, model = launch(lang="en")
    _dirty_pipeline(win, model)
    calls = []

    def _hook(parent, title, text, can_save):
        calls.append((title, text, can_save))
        return "save"
    monkeypatch.setattr(studio, "CLOSE_CONFIRM_HOOK", _hook)
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: ("", "")))
    assert _close(win) is False                                       # 保存の窓を取り消した → 閉じない
    assert calls[-1][2] is True and "Save the pipeline before closing?" in calls[-1][1]
    out = tmp_path / "p.json"
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(out), "")))
    assert _close(win) is True
    assert out.exists() and '"gaussian"' in out.read_text(encoding="utf-8")
    monkeypatch.setattr(studio, "CLOSE_CONFIRM_HOOK", lambda *a: "discard")
    assert _close(win) is True                                        # 保存済み: 聞かずに閉じる
    assert len(calls) == 2


def test_m10_discard_and_cancel(launch, monkeypatch):
    win, model = launch(lang="en")
    _dirty_pipeline(win, model)
    monkeypatch.setattr(studio, "CLOSE_CONFIRM_HOOK", lambda *a: "cancel")
    assert _close(win) is False
    monkeypatch.setattr(studio, "CLOSE_CONFIRM_HOOK", lambda *a: "discard")
    assert _close(win) is True


def test_m10_a_sample_left_as_loaded_is_not_unsaved(launch, monkeypatch):
    from PySide6 import QtWidgets
    win, model = launch(lang="ja")
    asked = []
    monkeypatch.setattr(studio, "CONFIRM_HOOK", lambda p, t, txt: (asked.append((t, txt)), True)[1])
    combo = [c for c in win.findChildren(QtWidgets.QComboBox)
             if c.count() > 5 and c.itemText(1).startswith("Denoise")][0]
    combo.setCurrentIndex(1); _pump(0.3)
    assert len(model.stages) >= 1 and not asked
    assert "*" not in win.windowTitle()
    combo.setCurrentIndex(2); _pump(0.3)                              # 見本 → 別の見本: 聞かない
    assert not asked
    assert win.close_guard() is True                                  # 見本のままなら終了も聞かない
    win._op_list.setCurrentRow(0); win._op_buttons["insert"].click(); _pump(0.2)   # 段を足すと未保存
    assert "*" in win.windowTitle()
    combo.setCurrentIndex(3); _pump(0.3)
    assert len(asked) == 1
    title, text = asked[0]
    assert title == "見本の処理手順を読み込む" and "破棄しますか" in text, asked


# --------------------------------------------------------------------------- #
# M3・M4・L6: つまみの欄                                                          #
# --------------------------------------------------------------------------- #
def _knob_line(name, letter):
    detail = studio.op_signature_detail(studio._op_row(name))
    return [ln for ln in detail.splitlines() if ln.startswith("knob %s" % letter)][0]


def test_m3_ops_missing_from_the_role_table_are_not_called_unused():
    """直す前: 役割の表に無い op は全部「(unused)」。sk_rolling_ball の a(球の半径)・xkor_bilateral の a・b も。"""
    assert "(unused)" not in _knob_line("sk_rolling_ball", "a") and "ball radius" in _knob_line("sk_rolling_ball", "a")
    assert "(unused)" in _knob_line("sk_rolling_ball", "b")                 # spec が未使用と言う(実装で確かめ済み)
    assert "(unused)" not in _knob_line("erosion_circle", "a")
    if api.find_op("xkor_bilateral") is not None:
        assert "(unused)" not in _knob_line("xkor_bilateral", "a") and "(unused)" not in _knob_line("xkor_bilateral", "b")
    assert "(unused)" in _knob_line("sobel_amp", "a") and "(unused)" in _knob_line("sobel_amp", "b")
    assert studio.knob_use("sobel_amp", "a") == ("unused", "spec")
    assert studio.knob_use("otsu", "b") == ("unused", "table")
    assert studio.knob_use("gaussian", "a")[0] == "used"
    # 実測だけ(図の 1 枚の入力)では「未使用」と言わず、止めもしない
    measured = [(n, k) for n in ("erosion_circle", "fill_up", "select_shape") for k in "ab"
                if studio.knob_use(n, k) == ("unknown", "measured")]
    if studio.knob_dead_measured("erosion_circle"):                      # docs のある checkout だけ
        assert measured
        n, k = measured[0]
        assert "(unused)" not in _knob_line(n, k) and "measured" in _knob_line(n, k)


@pytest.mark.parametrize("name,dead", [("sobel_amp", "ab"), ("otsu", "ab"), ("gaussian", ""), ("threshold", "b")])
def test_m3_unused_knobs_are_greyed_out_in_both_panels(launch, name, dead):
    from PySide6 import QtCore
    win, model = launch()
    lst = win._op_list
    names = [lst.item(i).data(QtCore.Qt.UserRole) for i in range(lst.count())]
    lst.setCurrentRow(names.index(name)); _pump(0.1)
    for spin, letter in zip(win._op_arg_spins, "ab"):                   # + の上の欄
        assert spin.isEnabled() == (letter not in dead), (name, letter)
    win._op_buttons["insert"].click(); _pump(0.3)
    assert [s[0] for s in model.stages] == [name]
    win._stage_list.setCurrentRow(0); _pump(0.2)
    for krow, letter in zip(win._knob_rows, "ab"):
        live = [w.isEnabled() for w in (krow.raw, krow.typed) + ((krow.slider,) if krow.slider else ())]
        if letter in dead:
            assert not any(live), (name, letter, live)                    # 値の欄も含めて動かせない
        else:
            assert krow.raw.isEnabled() and (krow.slider is None or krow.slider.isEnabled()), (name, letter)


def test_m4_the_implementation_is_folded_until_asked(launch):
    from PySide6 import QtCore
    win, model = launch(lang="ja")
    lst = win._op_list
    names = [lst.item(i).data(QtCore.Qt.UserRole) for i in range(lst.count())]
    lst.setCurrentRow(names.index("gaussian")); win._op_buttons["insert"].click(); _pump(0.3)
    win._stage_list.setCurrentRow(0); _pump(0.2)
    d = win._stage_detail
    assert "実装" not in d.text() and "つまみ a" in d.text()
    assert win._impl_toggle.isVisibleTo(win) and win._impl_toggle.text() == "実装を見る"
    win._impl_toggle.setChecked(True); _pump(0.1)
    full = studio.op_impl_source("gaussian", None)
    assert full and full in d.text()                                      # 途中で切らない
    win._impl_toggle.setChecked(False); _pump(0.1)
    assert full not in d.text()


def test_l6_a_slider_move_stores_a_short_knob_that_reads_back_the_same(launch):
    from PySide6 import QtCore
    win, model = launch()
    lst = win._op_list
    names = [lst.item(i).data(QtCore.Qt.UserRole) for i in range(lst.count())]
    lst.setCurrentRow(names.index("bilateral")); win._op_buttons["insert"].click(); _pump(0.3)
    win._stage_list.setCurrentRow(0); _pump(0.2)
    ka = win._knob_rows[0]
    moved = 0
    for frac in (0.13, 0.37, 0.5, 0.71, 0.849, 0.97):
        pos = int(ka.slider.maximum() * frac)
        ka.slider.setValue(pos); _pump(0.05)
        knob = model.stages[0][1]
        assert len(repr(knob)) <= 7, (frac, knob)                         # 0.847 のような短い数
        assert ka.knob_to_pos(knob) == pos                                # 同じ目盛り
        long_knob = ka.pos_to_knob(pos)
        assert studio.param_specs.format_display(ka.spec, knob) == studio.param_specs.format_display(ka.spec, long_knob)
        moved += 1
    assert moved == 6
    _pump(0.3)
    code = win._program["edit"].toPlainText()
    line = [ln for ln in code.splitlines() if ln.startswith("bilateral")][0]
    assert line == "bilateral (%r, %r)" % (model.stages[0][1], model.stages[0][2]), line
    stages, errs = studio.parse_hdev_program(line, studio.api.op_names())
    assert not errs and stages[0][1] == model.stages[0][1]               # 往復で値が変わらない


# --------------------------------------------------------------------------- #
# L1・L10・L3・M15・M14・M13・L9・L11                                            #
# --------------------------------------------------------------------------- #
def test_l1_ctrl_y_redoes(launch):
    from PySide6 import QtCore
    from PySide6.QtTest import QTest
    win, model = launch()
    keys = [s.toString() for s in win._actions["redo"].shortcuts()]
    assert keys == ["Ctrl+Shift+Z", "Ctrl+Y"]
    _dirty_pipeline(win, model)
    win._stage_list.setFocus()
    QTest.keyClick(win, QtCore.Qt.Key_Z, QtCore.Qt.ControlModifier); _pump(0.2)
    assert model.stages == []
    QTest.keyClick(win, QtCore.Qt.Key_Y, QtCore.Qt.ControlModifier); _pump(0.2)
    assert [s[0] for s in model.stages] == ["gaussian"]


def test_l10_running_an_empty_pipeline_says_so(launch):
    from PySide6 import QtCore
    from PySide6.QtTest import QTest
    win, model = launch(lang="ja")
    assert not model.stages
    win._op_list.setFocus(); _pump(0.05)
    QTest.keyClick(win._op_list, QtCore.Qt.Key_F5); _pump(0.2)
    said = win.statusBar().currentMessage()
    assert "まだ実行する物がありません" in said and "Enter" in said, said
    win.statusBar().clearMessage()
    QTest.keyClick(win._op_list, QtCore.Qt.Key_R, QtCore.Qt.ControlModifier); _pump(0.2)   # Ctrl+R も同じ
    assert "まだ実行する物がありません" in win.statusBar().currentMessage()
    _dirty_pipeline(win, model)
    win.statusBar().clearMessage()
    win._op_list.setFocus(); _pump(0.05)
    QTest.keyClick(win._op_list, QtCore.Qt.Key_F5); _pump(0.4)
    assert "まだ実行する物がありません" not in win.statusBar().currentMessage()


def test_l3_search_cards_are_whole_and_plain(launch):
    win, model = launch(lang="ja")
    ui = win._search_ui
    ui["search_now"]("ぼかす"); _pump(0.3)
    rows = [r for g in ui["rows"]().values() for r in g]
    assert len(rows) >= 5
    for r in rows:
        assert "``" not in r["text"] and "`" not in r["label_widget"].text(), r["text"]
        label, box, it = r["label_widget"], r["box"], r["item"]
        need = box.layout().heightForWidth(box.width())
        assert it.sizeHint().height() >= need, (r["name"], it.sizeHint().height(), need)   # 下が欠けない
        assert it.sizeHint().height() >= label.heightForWidth(label.width()) + r["try_button"].sizeHint().height()
    assert "gauss_filter" in rows[0]["text"] and "``gauss_filter``" not in rows[0]["text"]


def test_l3_help_pages_show_emphasis_not_asterisks():
    html = studio.op_help_html("sobel_amp", "ja", studio._op_row("sobel_amp"))
    assert "<p>*" not in html and "<p>**" not in html
    assert "<em>" in html
    raw = "<p>*図は合成の入力。*</p><p>**つまみ a を振る**(0.1):</p><pre>x = a * b ** 2</pre><p>A_t = Da*lap(A)</p>"
    out = studio.help_plain_markup(raw)
    assert out == "<p><em>図は合成の入力。</em></p><p><b>つまみ a を振る</b>(0.1):</p><pre>x = a * b ** 2</pre><p>A_t = Da*lap(A)</p>"
    assert studio.plain_summary("HALCON の ``gauss_filter`` と `x`") == "HALCON の gauss_filter と x"


def test_m15_help_search_prefers_the_exact_name():
    names = ["select_shape_xld", "select_shape", "cv_cc_count", "connect_and_holes", "gaussian", "fill_holes  (3D)"]
    halcon = {"cv_cc_count": "connection", "select_shape": "select_shape", "connect_and_holes": "connection_holes"}
    assert studio.help_query_target("select_shape", names, halcon) == "select_shape"
    assert studio.help_query_target("SELECT_SHAPE", names, halcon) == "select_shape"
    assert studio.help_query_target("connection", names, halcon) == "cv_cc_count"          # HALCON の名前
    assert studio.help_query_target("gauss", names, halcon) == "gaussian"                  # 前方一致
    assert studio.help_query_target("holes", names, halcon) == "fill_holes  (3D)"           # 部分一致の最短
    assert studio.help_query_target("xyzzy", names, halcon) is None
    assert studio.help_query_target("  ", names, halcon) is None


def test_m15_typing_in_the_help_picker_opens_the_exact_page(launch):
    from PySide6 import QtCore
    from PySide6.QtTest import QTest
    win, model = launch()
    win._actions["op_reference"].trigger(); _pump(0.5)
    pick, br = win._help["pick"], win._help["browser"]
    ed = pick.lineEdit()
    n0 = pick.count()
    for typed, want in (("select_shape", "select_shape"), ("connection", "cv_cc_count"), ("otsu", "otsu")):
        ed.setFocus(); QTest.keyClick(ed, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
        QTest.keyClicks(ed, typed); _pump(0.2)
        QTest.keyClick(ed, QtCore.Qt.Key_Return); _pump(0.4)
        assert pick.currentText() == want, (typed, pick.currentText())
        assert want in br.toPlainText()[:400], (typed, br.toPlainText()[:120])
    assert pick.count() == n0                                         # 打った語を行として足さない
    win._help["dialog"].close()
