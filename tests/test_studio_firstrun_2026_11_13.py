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
