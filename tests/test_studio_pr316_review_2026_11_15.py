# -*- coding: utf-8 -*-
"""PR #316(初回起動の点検の直し)の独立レビュー 2 本(2026-11-13、振る舞い / 安全)の指摘の回帰試験。

どの試験も、直す前の木(c1e489f773 = PR の先頭に master をマージした所)で落ちる事を確かめてから足した
(落ちない物は説明に書く)。窓は offscreen で実際に作り、キーとマウスは QTest で送る。設定は試験ごとの一時ファイル。
"""
import glob
import json
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
_CJK = re.compile("[぀-ヿ一-鿿]")


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
    prev_hooks = (studio.ERROR_HOOK, studio.CONFIRM_HOOK, studio.CLOSE_CONFIRM_HOOK)

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
    studio.ERROR_HOOK, studio.CONFIRM_HOOK, studio.CLOSE_CONFIRM_HOOK = prev_hooks
    for win in opened:
        win.close_guard = lambda: True
        win.quiesce(); win.close()
    _pump(0.1)


def _search(win, text):
    """検索欄に *text* を入れて結果を出す(打った後の遅延を待たずに、同じ関数を呼ぶ)。"""
    win._search_ui["search_now"](text); _pump(0.25)


def _enter(win):
    from PySide6 import QtCore
    from PySide6.QtTest import QTest
    QTest.keyClick(win._search_ui["edit"], QtCore.Qt.Key_Return); _pump(0.3)


def _row_names(win):
    """検索の結果に見えている op の行の名前(上から)。"""
    from PySide6 import QtCore
    lst = win._search_ui["list"]
    return [lst.item(i).data(QtCore.Qt.UserRole) for i in range(lst.count())
            if lst.item(i).data(QtCore.Qt.UserRole) and not lst.item(i).isHidden()]


def _picked(win):
    from PySide6 import QtCore
    cur = win._search_ui["list"].currentItem()
    return cur.data(QtCore.Qt.UserRole) if cur is not None else None


def _sample_combo(win):
    from PySide6 import QtWidgets
    return [c for c in win.findChildren(QtWidgets.QComboBox)
            if c.count() > 5 and c.itemText(1).startswith("Denoise")][0]


def _close(win):
    from PySide6 import QtGui, QtWidgets
    ev = QtGui.QCloseEvent(); ev.accept()
    QtWidgets.QApplication.sendEvent(win, ev)
    return ev.isAccepted()


# --------------------------------------------------------------------------- #
# 検索欄の Enter: 前の段の出力を受けられない行を入れない                              #
# --------------------------------------------------------------------------- #
def _first_stage_otsu(win, model):
    """利用者と同じ道で 1 段目に otsu(出力は領域)を入れ、op の一覧のタブへ戻る。"""
    _search(win, "otsu"); _enter(win)
    assert [s[0] for s in model.stages] == ["otsu"]
    win._docks["operators"].raise_(); _pump(0.2)


@pytest.mark.parametrize("lang,query,must_add", [
    ("ja", "ノイズ", True), ("ja", "穴の数", True), ("en", "noise", True), ("en", "count holes", True),
    ("ja", "ぼかし", False), ("ja", "輪郭", False), ("en", "engraved code", False), ("en", "lot code", False),
])
def test_enter_after_a_region_stage_never_adds_a_stage_the_chain_refuses(launch, lang, query, must_add):
    """直す前: otsu の後に「ノイズ」+ Enter で、押す前から選ばれている定番の median(image を取る)が入り、段 2 は
    「type mismatch at stage 2 (median): it takes 'image' but stage 1 (otsu) outputs 'region'」になった。
    must_add の 4 語は、M1 の前は動く op が入っていた語(レビューの実測)。"""
    win, model = launch(lang=lang, user=True)
    _first_stage_otsu(win, model)
    _search(win, query)
    assert len(_row_names(win)) >= 3, query
    picked = _picked(win)
    _enter(win)
    added = [s[0] for s in model.stages[1:]]
    if picked is None:
        assert added == []                                       # 選ばれた行が無いなら、何も入らない
    else:
        assert added == [api.find_op(picked).name]               # 押す前に選ばれていた行が入る(M1 の約束)
        assert studio.engine._compatible("region", studio._op_row(added[0])["in_sort"]), added
    if must_add:
        assert len(added) == 1, (query, picked)
    for i in range(len(model.stages)):
        model.result_upto(i)                                     # 断られる段があれば、ここで例外になる


def test_enter_says_why_when_no_listed_row_takes_the_previous_output(launch):
    """otsu の後に「熱」: 出るのは定番の 4 行だけで、どれも image を取る。黙って ERROR の段を作らず、入れずに理由を言う。
    行をクリックで選んだ時は、その行が入る(利用者が選んだ物は入れる)。"""
    win, model = launch(lang="ja", user=True)
    _first_stage_otsu(win, model)
    _search(win, "熱")
    names = _row_names(win)
    assert len(names) >= 3
    fits = [n for n in names if studio.op_insertable(n)[0]
            and studio.engine._compatible("region", studio._op_row(n)["in_sort"])]
    assert not fits, "この語は試験の前提(受けられる行が無い)に合わなくなった: %s" % fits
    assert _picked(win) is None
    _enter(win)
    assert [s[0] for s in model.stages] == ["otsu"]
    said = win.statusBar().currentMessage()
    assert "region" in said and "otsu" in said and _CJK.search(said), said
    assert not re.search(r"[A-Za-z]{4,}", said.replace("region", "").replace("otsu", "")), said
    row = win._search_ui["rows"]()["staples"][0]
    win._search_ui["list"].setCurrentItem(row["item"]); _pump(0.05)   # 利用者が行を選ぶ
    assert _picked(win) == row["name"]
    _enter(win)
    assert [s[0] for s in model.stages] == ["otsu", row["name"]]


def test_first_stage_enter_is_unchanged_by_the_type_rule(launch):
    """最初の段は入口で型を合わせるので、絞らない(画像に対して領域の op を選んでも、従来どおり入る)。
    直す前も通る(狭めすぎの見張り)。"""
    win, model = launch(lang="ja", user=True)
    _search(win, "穴埋め")
    assert _picked(win) == "fill_up"
    _enter(win)
    assert [s[0] for s in model.stages] == ["fill_up"]
    model.result_upto(0)


# --------------------------------------------------------------------------- #
# 検索欄の Enter: op 名を正確に打った時は、その行                                    #
# --------------------------------------------------------------------------- #
def test_exact_name_of_a_two_input_op_plus_enter_says_why_and_adds_nothing(launch):
    """直す前: 「abs_diff_image」+ Enter で、1 行目(2 入力なので入らない)を黙って飛ばし、2 行目の
    ph_coherence_enhancing_diffusion が入った。"""
    win, model = launch(lang="en", user=True)
    _search(win, "abs_diff_image")
    assert _row_names(win)[0] == "abs_diff_image"
    assert studio.op_insertable("abs_diff_image") == (False, "two_input")
    assert _picked(win) == "abs_diff_image"                      # Enter の対象を、押す前から見せる
    _enter(win)
    assert not model.stages
    said = win.statusBar().currentMessage()
    assert "abs_diff_image" in said and "two or more inputs" in said, said


def test_exact_name_of_a_ledger_op_plus_enter_opens_the_ledger_runner(launch, monkeypatch):
    """直す前: 「a3_distribution」(台帳の op)+ Enter で gray_histo_abs が入った。"""
    win, model = launch(lang="ja", user=True)
    opened = []
    monkeypatch.setattr(win, "_open_ledger_runner", lambda op=None, prefer_image=False: opened.append((op, prefer_image)))
    name = "a3_distribution"
    assert studio.op_insertable(name) == (False, "ledger")
    _search(win, name)
    names = _row_names(win)
    assert name in names and names[0] != name            # 型が合わないので下の群にある(先頭の行ではない)
    assert _picked(win) == name                          # それでも、名前を正確に打った行が Enter の対象
    _enter(win)
    assert not model.stages
    assert opened == [(name, True)]
    assert "台帳の op" in win.statusBar().currentMessage()


def test_an_exact_name_still_wins_over_everything_else(launch):
    """正確な名前の行が入れられる op なら、従来どおりそれが入る(median blur のような句は従来どおり先頭の行)。"""
    win, model = launch(lang="en", user=True)
    _search(win, "median")
    assert _picked(win) == "median"
    _enter(win)
    assert [s[0] for s in model.stages] == ["median"]


def test_exact_name_that_cannot_take_the_previous_output_is_not_added_and_says_why(launch):
    """otsu の後に「gaussian」と正確に打って Enter(gaussian は image を取る)。ERROR の段を作らず、隣の op も入れず、
    理由を言う。行をクリックで選べば入る。最初の検索の直しの後に残っていた 2 件(英語 40 語中 gaussian・threshold)。"""
    from PySide6 import QtCore
    win, model = launch(lang="en", user=True)
    _first_stage_otsu(win, model)
    _search(win, "gaussian")
    assert "gaussian" in _row_names(win)
    assert _picked(win) is None
    _enter(win)
    assert [s[0] for s in model.stages] == ["otsu"]
    said = win.statusBar().currentMessage()
    assert "gaussian" in said and "'image'" in said and "'region'" in said and "otsu" in said, said
    lst = win._search_ui["list"]
    item = next(lst.item(i) for i in range(lst.count()) if lst.item(i).data(QtCore.Qt.UserRole) == "gaussian")
    lst.setCurrentItem(item); _pump(0.05)                          # 利用者が行を選ぶ
    _enter(win)
    assert [s[0] for s in model.stages] == ["otsu", "gaussian"]


# --------------------------------------------------------------------------- #
# 最初の op の後のタブと、キーボードの焦点                                           #
# --------------------------------------------------------------------------- #
def _tabbed(win):
    pipe, ops = win._docks["pipeline"], win._docks["operators"]
    if pipe not in win.tabifiedDockWidgets(ops):
        pytest.skip("この配置では 2 つのパネルがタブで重なっていない")
    return pipe, ops


def test_enter_in_the_search_box_keeps_the_keys_in_a_visible_box(launch):
    """直す前: 検索欄に blur + Enter の後、op の一覧のタブが隠れ、焦点は見えない検索欄に残った。続けて otsu と打つと
    欄は「blurotsu」になり、見えない一覧の行が処理手順に入った。"""
    from PySide6.QtTest import QTest
    win, model = launch(lang="ja", user=True)
    pipe, ops = _tabbed(win)
    edit = win._search_ui["edit"]
    win.activateWindow(); edit.setFocus(); _pump(0.1)
    QTest.keyClicks(edit, "blur"); _pump(0.5)
    _enter(win)
    assert [s[0] for s in model.stages] == ["gaussian"]
    fw = win.focusWidget()
    assert fw is edit, fw
    assert not edit.visibleRegion().isEmpty(), "Enter の後、焦点のある検索欄が見えていない"
    assert not ops.visibleRegion().isEmpty()
    QTest.keyClicks(win.focusWidget(), "x"); _pump(0.4)           # 続けて打った字は、見えている欄に入る
    # (3 回目のレビューの後: Enter で入った語は選ばれているので、打った字が置き換える。従来は「blurx」)
    assert edit.text() == "x" and not edit.visibleRegion().isEmpty()


def test_plus_button_brings_the_tab_forward_and_the_focus_goes_with_it(launch):
    """+ ボタン / ダブルクリックで最初の op を入れた時は、従来どおり「処理手順と調整」のタブが前に出る。焦点は
    隠れた側(op の一覧・+ ボタン)に残さず、段の一覧へ移す。直す前は隠れた op の一覧に残った。"""
    from PySide6 import QtCore
    win, model = launch(lang="ja", user=True)
    pipe, ops = _tabbed(win)
    lst = win._op_list
    names = [lst.item(i).data(QtCore.Qt.UserRole) for i in range(lst.count())]
    win.activateWindow(); lst.setFocus(); lst.setCurrentRow(names.index("gaussian")); _pump(0.1)
    assert win.focusWidget() is lst
    win._op_buttons["insert"].click(); _pump(0.3)
    assert [s[0] for s in model.stages] == ["gaussian"]
    assert not pipe.visibleRegion().isEmpty()
    fw = win.focusWidget()
    assert fw is win._stage_list, fw
    assert not fw.visibleRegion().isEmpty()


# --------------------------------------------------------------------------- #
# M12 の短い語: 別の語の中では当てない                                              #
# --------------------------------------------------------------------------- #
#: レビュー 2 本が挙げた誤爆(どれも直す前は定番か見本が出た)
INSIDE_OTHER_WORDS = (
    "シミュレーション", "シミュレータ", "シミュレート", "光学シミュレーション", "プロット", "スロット", "パイロット", "トロット",
    "タイムラプス", "ヒストグラムライン", "キズナ", "ひびき", "きずな", "加熱処理", "熱処理", "熱延鋼板", "色温度",
    "ハーフミラー", "ドアミラー",
    "shape from shading", "phong shading", "color temperature", "colour temperature", "lane marking",
)
#: 当たり続けるべき語(狭めすぎていない事)。右は、定番に入っているはずの op
STILL_HIT = (
    ("シミ", "sk_rolling_ball"), ("シミを探す", "sk_rolling_ball"), ("シミ抜き", "sk_rolling_ball"), ("色ムラ", "sk_rolling_ball"),
    ("キズ検査", "sk_rolling_ball"), ("ヒビ割れ", "sk_frangi"), ("ゴミ検出", "tophat"), ("サビ", "std_filter"),
    ("ロット", "adaptive_gauss_thresh"), ("ロット番号", "adaptive_gauss_thresh"), ("ロットコード", "adaptive_gauss_thresh"),
    ("熱", "clahe"), ("熱を見たい", "clahe"), ("発熱", "clahe"), ("熱画像", "clahe"), ("サーモグラフィ", "clahe"),
    ("温度分布", "clahe"), ("ミラー", "mirror_image"), ("ミラー反転", "mirror_image"), ("ミラーリング", "mirror_image"),
    ("ノイズリダクション", "median"), ("ステップエッジ", "sobel_amp"), ("テンプレートマッチング", "ncc_locate"),
    ("熱雑音", "median"), ("lens shading", "sk_rolling_ball"), ("thermography", "clahe"), ("marking", "adaptive_gauss_thresh"),
)


@pytest.mark.parametrize("query", INSIDE_OTHER_WORDS)
def test_short_staple_words_do_not_fire_inside_other_words(query):
    import studio_search as ss
    assert ss.staples_for(query) == [], query
    assert ss.samples_for(query) == [], query


@pytest.mark.parametrize("query,op", STILL_HIT)
def test_the_narrowed_words_still_fire_where_they_stand_alone(query, op):
    import studio_search as ss
    assert op in ss.staples_for(query), (query, ss.staples_for(query))


def test_every_short_katakana_staple_word_is_classified_and_the_bundled_japanese_agrees():
    """3 字以下の片仮名の語は、「単独の語としてだけ当てる」か「複合語でも同じ意味なので部分文字列で当てる」かの
    どちらかに必ず入っている。同梱の日本語の文(op のヘルプと docs)から「その語を中に含む、別の片仮名の語」を機械で
    集め、単独の語の方は 1 つも当たらない事を数える(直す前は シミュレーション・スロット・タイムラプス … が当たった)。"""
    import studio_search as ss
    kata = re.compile("[ァ-ヺー]+")
    terms = sorted({t for tb in (ss.STAPLES, ss.SAMPLE_TERMS) for ts, _ in tb for t in ts if kata.fullmatch(t)})
    short = [t for t in terms if len(t) <= 3]
    assert len(terms) >= 20 and len(short) >= 10, (len(terms), short)
    standalone = [t for t in ss.STAPLE_STANDALONE_JA if kata.fullmatch(t)]
    assert set(short) == set(standalone) | set(ss.STAPLE_COMPOUND_OK_JA), short
    assert not set(standalone) & set(ss.STAPLE_COMPOUND_OK_JA)
    paths = sorted(glob.glob(os.path.join(ROOT, "studio_assets", "op_help", "*.ja.html"))
                   + glob.glob(os.path.join(ROOT, "docs", "*.md")))
    assert len(paths) >= 150, len(paths)                           # 走査が空を通していない
    words = set()
    for p in paths:
        with open(p, encoding="utf-8") as f:
            words.update(w for w in kata.findall(f.read()) if len(w) >= 3)
    assert len(words) >= 1000, len(words)
    inside = sorted((t, w) for t in standalone for w in words if t in w and w != t)
    assert len(inside) >= 8, inside                                # シミュレーション・スロット・タイムラプス・ハーフミラー …
    assert ("シミ", "シミュレーション") in inside and ("ロット", "スロット") in inside
    fired = [(t, w) for t, w in inside if ss._staple_term_hit(t, ss._staple_query_forms(w))]
    assert not fired, fired
    # 複合語でも当てる語は、同梱の文の複合語で実際に当たる(表が飾りになっていない)
    kept = sorted((t, w) for t in ss.STAPLE_COMPOUND_OK_JA for w in words if t in w and w != t)
    assert len(kept) >= 10, kept
    assert all(ss._staple_term_hit(t, ss._staple_query_forms(w)) for t, w in kept)


def test_enter_on_a_word_that_only_contains_a_staple_word_inserts_no_staple(launch):
    """直す前: 「シミュレーション」+ Enter で汚れの定番の sk_rolling_ball が入った(M1 の前は simulate_motion)。"""
    win, model = launch(lang="ja", user=True)
    _search(win, "シミュレーション")
    rows = win._search_ui["rows"]()
    assert rows["staples"] == [] and "samples" not in rows
    picked = _picked(win)
    assert picked is not None and picked != "sk_rolling_ball"
    _enter(win)
    assert [s[0] for s in model.stages] == [api.find_op(picked).name]


def test_the_first_thermal_staple_changes_the_bundled_image(launch):
    """直す前: 「熱」「サーモ」「thermal」+ Enter は scale_image_max で、同梱の coins では絵が変わらなかった
    (平均の変化 0.0024。この PR 自身の「絵が変わった」の基準は 0.01)。"""
    import sample_images
    import studio_search as ss
    img = np.asarray(sample_images.load(studio.STARTUP_SAMPLE_IMAGE), float)
    for word in ("熱", "サーモ", "赤外", "thermal", "infrared", "hot spot"):
        first = ss.staples_for(word)[0]
        out = np.asarray(api.find_op(first).fn(img, 0.5, 0.5), float)
        assert out.shape == img.shape
        assert float(np.abs(out - img).mean()) > 0.01, (word, first)


# --------------------------------------------------------------------------- #
# M10: 見本を読んだ後の編集は、保存していない変更                                    #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("edit", ["bypass", "directive", "pin"])
def test_an_edit_after_loading_a_sample_is_unsaved_work(launch, monkeypatch, edit):
    """直す前: 見本を読んだ後に 段のバイパス / dev_* の行の Apply / Pin as A のどれをしても、題に * が付かず、終了も
    別の見本の読み込みも聞かずに捨てた(比べていたのは段の名前・a・b だけ。3 つとも保存される物)。"""
    win, model = launch(lang="en")
    asked = []
    monkeypatch.setattr(studio, "CONFIRM_HOOK", lambda p, t, txt: (asked.append(t), False)[1])
    monkeypatch.setattr(studio, "CLOSE_CONFIRM_HOOK", lambda p, t, txt, can_save: (asked.append(t), "cancel")[1])
    combo = _sample_combo(win)
    combo.setCurrentIndex(1); _pump(0.3)
    names = [s[0] for s in model.stages]
    assert names and not asked and "*" not in win.windowTitle() and win.close_guard() is True
    if edit == "bypass":
        win._stage_list.setCurrentRow(0); _pump(0.05)
        win._toggle_bypass()
        saved = lambda d: any(len(st) == 4 and st[3] is True for st in d["stages"])        # noqa: E731
    elif edit == "directive":
        ed = win._program["edit"]
        ed.setPlainText(ed.toPlainText().rstrip("\n") + "\ndev_set_color ('red')\n")
        win._program["apply"]()
        saved = lambda d: d.get("directives") == ["dev_set_color ('red')"]                  # noqa: E731
    else:
        win._pin_a()
        saved = lambda d: len(d.get("pinned") or []) == 1                                   # noqa: E731
    _pump(0.3)
    assert saved(model.to_dict()), model.to_dict()                 # 保存される形が、見本と違う
    assert [s[0] for s in model.stages] == names
    assert "*" in win.windowTitle(), win.windowTitle()
    assert win.close_guard() is False and asked == ["Quit Fullseye Studio"]
    combo.setCurrentIndex(2); _pump(0.3)                           # 別の見本: 聞く。「いいえ」なら何も変わらない
    assert asked == ["Quit Fullseye Studio", "Load sample pipeline"]
    assert [s[0] for s in model.stages] == names and saved(model.to_dict())


def test_a_sample_brought_back_to_as_loaded_is_not_unsaved(launch, monkeypatch):
    win, model = launch(lang="en")
    asked = []
    monkeypatch.setattr(studio, "CONFIRM_HOOK", lambda p, t, txt: (asked.append(t), True)[1])
    monkeypatch.setattr(studio, "CLOSE_CONFIRM_HOOK", lambda p, t, txt, can_save: (asked.append(t), "cancel")[1])
    combo = _sample_combo(win)
    combo.setCurrentIndex(1); _pump(0.3)
    win._stage_list.setCurrentRow(0); _pump(0.05)
    win._toggle_bypass(); _pump(0.1)
    assert "*" in win.windowTitle()
    win._stage_list.setCurrentRow(0); _pump(0.05)
    win._toggle_bypass(); _pump(0.1)                               # 元に戻した: 読んだ時と同じ
    assert "*" not in win.windowTitle()
    assert win.close_guard() is True and not asked


def test_after_saving_the_file_is_the_baseline_not_the_sample(launch, monkeypatch, tmp_path):
    """見本 + 段 → 保存 → 足した段を消す。メモリの中身は見本と同じに戻るが、ファイルとは違うので未保存。
    直す前は「見本のまま」と見なして、題に * が付かず、聞かずに閉じた。"""
    from PySide6 import QtCore, QtWidgets
    win, model = launch(lang="en")
    monkeypatch.setattr(studio, "CONFIRM_HOOK", lambda p, t, txt: True)
    combo = _sample_combo(win)
    combo.setCurrentIndex(1); _pump(0.3)
    n = len(model.stages)
    lst = win._op_list
    win._docks["operators"].raise_(); _pump(0.1)
    names = [lst.item(i).data(QtCore.Qt.UserRole) for i in range(lst.count())]
    assert names, "op の一覧が空"
    pick = next(x for x in names if x and studio.op_insertable(x)[0])
    lst.setCurrentRow(names.index(pick)); win._op_buttons["insert"].click(); _pump(0.2)
    assert len(model.stages) == n + 1 and "*" in win.windowTitle()
    out = tmp_path / "mine.json"
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(out), "")))
    win._actions["save_pipeline"].trigger(); _pump(0.2)
    assert out.exists() and "*" not in win.windowTitle()
    added = next(i for i in range(len(model.stages)) if model.stages[i][0] == api.find_op(pick).name
                 and i == win._stage_list.currentRow())
    win._stage_list.setCurrentRow(added); _pump(0.05)
    win._actions["remove"].trigger(); _pump(0.2)
    assert len(model.stages) == n
    assert "*" in win.windowTitle(), win.windowTitle()
    asked = []
    monkeypatch.setattr(studio, "CLOSE_CONFIRM_HOOK", lambda p, t, txt, can_save: (asked.append(t), "cancel")[1])
    assert win.close_guard() is False and asked == ["Quit Fullseye Studio"]


def test_cancelling_open_sample_keeps_the_users_image(launch, monkeypatch, tmp_path):
    """直す前: 検索の「見本を開く」で破棄の確認をキャンセルしても、段の op 名の並びが見本と同じ(同じ見本を開いて
    つまみだけ調整していた)なら「読めた」と見なし、利用者の画像を見本の画像に置き換えた(image_path も None)。"""
    import fullseye
    win, model = launch(lang="en")
    name = "FA — scratch on hairline metal"
    answers = [True]
    asked = []
    monkeypatch.setattr(studio, "CONFIRM_HOOK", lambda p, t, txt: (asked.append(t), answers[-1])[1])
    assert win._open_search_sample(name) is True
    _pump(0.3)
    stages0 = [s[0] for s in model.stages]
    win._stage_list.setCurrentRow(0); _pump(0.1)
    raw = win._knob_rows[0].raw
    raw.setValue(0.83 if abs(raw.value() - 0.83) > 0.01 else 0.21); _pump(0.5)       # つまみを調整 → 未保存
    assert "*" in win.windowTitle()
    knob = model.stages[0][1]
    mine = tmp_path / "my_part.png"
    rng = np.random.default_rng(3)
    fullseye.write_image(str(mine), np.clip(rng.random((48, 64)), 0, 1))
    assert win._load_image_path(str(mine)) is True
    _pump(0.2)
    before = np.array(model.image, copy=True)
    assert before.shape == (48, 64) and win._state["image_path"] == os.path.abspath(str(mine))
    answers.append(False)                                          # 破棄の確認に「キャンセル」
    n_asked = len(asked)
    assert win._open_search_sample(name) is False
    _pump(0.3)
    assert len(asked) == n_asked + 1
    assert np.array_equal(model.image, before), "キャンセルしたのに、画像が見本の画像に替わった"
    assert win._state["image_path"] == os.path.abspath(str(mine))
    assert [s[0] for s in model.stages] == stages0 and model.stages[0][1] == knob


# --------------------------------------------------------------------------- #
# 確認の窓: 既定はキャンセル、確認が壊れても聞かずに閉じない                          #
# --------------------------------------------------------------------------- #
def test_discard_confirmation_defaults_to_cancel_in_the_ui_language(launch, monkeypatch):
    """「破棄 / キャンセル」の本物の窓。既定のボタンと Esc はキャンセル(Enter で取り返しのつかない事を起こさない)。
    書き直した ``_default_confirm`` には本物の窓を確かめる試験が無かった(直す前も通る)。"""
    from PySide6 import QtCore, QtWidgets
    win, model = launch(lang="ja")
    seen = {}
    timer = QtCore.QTimer(); timer.setInterval(50)

    def _inspect():
        box = QtWidgets.QApplication.activeModalWidget()
        if not isinstance(box, QtWidgets.QMessageBox):
            return
        timer.stop()
        seen["buttons"] = sorted(b.text() for b in box.buttons())
        seen["default"] = box.defaultButton().text()
        seen["escape"] = box.escapeButton().text()
        box.defaultButton().click()                                # Enter と同じ
    timer.timeout.connect(_inspect); timer.start()
    answer = studio._default_confirm(win, "題", "本文")
    assert answer is False                                         # Enter = キャンセル = 捨てない
    assert seen["buttons"] == sorted(["破棄", "キャンセル"]), seen
    assert seen["default"] == seen["escape"] == "キャンセル"


def test_closing_an_edited_editor_tab_asks_through_the_cancel_by_default_confirmation(launch, monkeypatch):
    """直す前: Python エディタのタブを閉じる確認は ``QMessageBox.question(Yes | No)`` で既定のボタンの指定が無く、
    Enter で「はい」= 未保存のコードを捨てて閉じた。字も英語のまま(&Yes / &No)。"""
    from PySide6 import QtWidgets
    win, model = launch(lang="ja")
    old_style = []
    monkeypatch.setattr(QtWidgets.QMessageBox, "question",
                        staticmethod(lambda *a, **k: (old_style.append(a[1:3]), QtWidgets.QMessageBox.No)[1]))
    asked = []
    answers = [False]
    monkeypatch.setattr(studio, "CONFIRM_HOOK", lambda p, t, txt: (asked.append((t, txt)), answers[-1])[1])
    win._act_pyedit.trigger(); _pump(0.3)
    pe = win._pyedit
    try:
        ed = pe["open_tab"]("x = 1\n", "mine.py")
        ed.insertPlainText("y = 2\n"); _pump(0.1)
        assert ed._dirty
        tabs = pe["tabs"]
        n = tabs.count()
        pe["close_tab"](tabs.indexOf(ed)); _pump(0.1)
        assert not old_style, "既定のボタンを指定しない Yes / No の窓がまだ出る: %s" % old_style
        assert tabs.count() == n and len(asked) == 1               # 「キャンセル」: タブは残る
        title, text = asked[0]
        assert _CJK.search(title) and _CJK.search(text) and "mine.py" in text, asked
        answers.append(True)
        pe["close_tab"](tabs.indexOf(ed)); _pump(0.1)
        assert tabs.count() == n - 1 and len(asked) == 2
    finally:
        for i in range(pe["tabs"].count()):
            pe["tabs"].widget(i)._dirty = False
        pe["dlg"].close()


def _one_unsaved_stage(win, model):
    from PySide6 import QtCore
    lst = win._op_list
    names = [lst.item(i).data(QtCore.Qt.UserRole) for i in range(lst.count())]
    lst.setCurrentRow(names.index("gaussian")); _pump(0.05)
    win._op_buttons["insert"].click(); _pump(0.2)
    assert [s[0] for s in model.stages] == ["gaussian"]


def test_a_broken_translation_row_does_not_break_the_quit_confirmation(launch, monkeypatch):
    """終了の確認の文は翻訳の表を通る。表の日本語の行から %d が落ちていても、確認は(英語の文で)出る。
    直す前は ``tr("%d unsaved stage(s)") % n`` が TypeError になり、確認は出なかった。"""
    win, model = launch(lang="ja")
    _one_unsaved_stage(win, model)
    row = dict(studio.STRINGS_I18N["%d unsaved stage(s)"]); row["ja"] = "未保存の段"
    monkeypatch.setitem(studio.STRINGS_I18N, "%d unsaved stage(s)", row)
    asked = []
    monkeypatch.setattr(studio, "CLOSE_CONFIRM_HOOK", lambda p, t, txt, can_save: (asked.append(txt), "cancel")[1])
    assert _close(win) is False
    assert len(asked) == 1 and "1 unsaved stage(s)" in asked[0], asked


_CLOSE_GUARD_RAISES = r'''
import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import studio
from PySide6 import QtGui, QtWidgets
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
win, model = studio.build_window()
win.show(); app.processEvents()
model.add_stage("gaussian"); win._state["dirty"] = True
asked = []
studio.CLOSE_CONFIRM_HOOK = lambda p, t, txt, can_save: (asked.append(txt), "cancel")[1]
def boom():
    raise RuntimeError("guard broke")
win.close_guard = boom
ev = QtGui.QCloseEvent(); ev.accept()
QtWidgets.QApplication.sendEvent(win, ev)
print("FIRST accepted=%s asked=%d english=%s" % (ev.isAccepted(), len(asked), "unsaved work failed" in "".join(asked)))
studio.CLOSE_CONFIRM_HOOK = lambda p, t, txt, can_save: (asked.append(txt), "discard")[1]
ev = QtGui.QCloseEvent(); ev.accept()
QtWidgets.QApplication.sendEvent(win, ev)
print("SECOND accepted=%s asked=%d" % (ev.isAccepted(), len(asked)))
sys.stdout.flush()
os._exit(0)
'''


def test_a_close_confirmation_that_raises_keeps_the_window_open_and_asks_in_plain_english(tmp_path):
    """終了の確認(close_guard)が例外を出しても、聞かずに閉じない・落ちない。別プロセスで走らせる:
    直す前は、例外が closeEvent の外へ出て Python ごと落ちた(access violation)。"""
    import subprocess
    import sys
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONUTF8="1",
               FULLSEYE_STUDIO_SETTINGS=str(tmp_path / "s.ini"),
               PYTHONPATH=ROOT + os.pathsep + os.environ.get("PYTHONPATH", ""))
    r = subprocess.run([sys.executable, "-c", _CLOSE_GUARD_RAISES], cwd=str(tmp_path), env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    assert r.returncode == 0, (r.returncode, r.stdout[-400:], r.stderr[-800:])
    assert "FIRST accepted=False asked=1 english=True" in r.stdout, r.stdout     # 閉じない側に倒し、英語で聞き直す
    assert "SECOND accepted=True asked=2" in r.stdout, r.stdout                  # 「保存せずに閉じる」なら閉じる


def test_every_translation_row_keeps_the_format_fields_of_its_english_key():
    """訳の行は、英語の原文と同じ書式(%s・%d …)を同じ数だけ持つ —— 持たないと ``tr(…) % 値`` が実行時に落ちる。
    従来の門は pending の日本語の %s と %d だけを見ていた。ここは strings・pending・ツールヒント・表の外の行の全言語。
    (今の表は 0 件。直す前も通る。)"""
    from collections import Counter
    with open(os.path.join(ROOT, "studio_assets", "i18n.json"), encoding="utf-8") as f:
        d = json.load(f)
    fmt = re.compile(r"%(?:\.\d+)?[sdrfg]|%%")
    sections = {s: d[s] for s in ("strings", "pending_translation", "tooltips")}
    sections["top"] = {k: v for k, v in d.items()
                       if isinstance(v, dict) and k not in ("languages", "guide") and k not in sections}
    checked, bad = 0, []
    for sect, rows in sections.items():
        for key, row in rows.items():
            if key == "_note":
                continue
            for lang, text in row.items():
                checked += 1
                if Counter(fmt.findall(key)) != Counter(fmt.findall(text)):
                    bad.append((sect, lang, key))
    assert checked >= 2000, checked                                # 走査が空を通していない
    assert sum(1 for k in d["strings"] if "%" in k) >= 20
    assert not bad, bad[:10]


# --------------------------------------------------------------------------- #
# 「表で見る(N 個)」の N = 開く表の行の数                                           #
# --------------------------------------------------------------------------- #
def test_see_as_a_table_names_the_number_of_rows_the_table_shows(launch):
    """直す前: coins + otsu で「表で見る(96 個)」、押して開く表は 63 行(表は小さな粒を落とすのに、ボタンは
    ラベル付けの個数をそのまま出していた)。"""
    from PySide6 import QtCore, QtWidgets
    from scipy import ndimage
    win, model = launch(lang="ja", user=True)
    lst = win._op_list
    names = [lst.item(i).data(QtCore.Qt.UserRole) for i in range(lst.count())]
    lst.setCurrentRow(names.index("otsu")); win._op_buttons["insert"].click(); _pump(0.2)
    win._actions["run_all"].trigger(); _pump(0.8)
    b = win._b_regions
    assert b.isVisibleTo(win)
    n = int(re.search(r"(\d+)", b.text()).group(1))
    out = np.asarray(model.result_upto(0)) > 0.5
    labelled = ndimage.label(out, structure=np.ones((3, 3), bool))[1]
    assert labelled > n > 10, (labelled, n)                        # 2 つの数え方が違う絵で確かめている
    assert n == studio._region_table_count(out)
    b.click(); _pump(0.6)
    dlg = win._feat_dlg
    assert dlg is not None and dlg.isVisible()
    tables = [t for t in dlg.findChildren(QtWidgets.QTableWidget)
              if "area" in [t.horizontalHeaderItem(c).text() for c in range(t.columnCount())]]
    assert len(tables) == 1, len(tables)                           # 2-D の領域の表
    assert tables[0].rowCount() == n, (tables[0].rowCount(), b.text())
    dlg.close(); _pump(0.1)


def test_the_table_count_follows_the_tables_own_limits():
    """行の上限と面積の下限は、表と同じ物を使う(別々に書かない)。"""
    speckle = np.zeros((400, 400))
    for i in range(30):
        for j in range(30):
            speckle[4 + 12 * i: 6 + 12 * i, 4 + 12 * j: 6 + 12 * j] = 1.0     # 4 画素の粒が 900 個
    n = studio._region_table_count(speckle)
    objs, _mode = studio.region_feature_objects(speckle, min_area=studio._region_table_min_area(speckle.size))
    assert len(objs) > studio.REGION_TABLE_MAX and n == studio.REGION_TABLE_MAX
    small = np.zeros((300, 300)); small[10:20, 10:20] = 1; small[100, 100] = 1    # 1 画素の粒は落ちる(下限 2 画素)
    assert studio._region_table_min_area(small.size) == 2
    assert studio._region_table_count(small) == 1
    assert len(studio.region_feature_objects(small, min_area=2)[0]) == 1
    assert studio._region_table_count(np.zeros((50, 50))) == 0


# --------------------------------------------------------------------------- #
# 「実装を見る」: 選んだ op の枝                                                    #
# --------------------------------------------------------------------------- #
def test_show_the_implementation_is_the_selected_ops_own_branch():
    """直す前: sobel_amp で押すと、族で共有する関数の全文(sobel_dir・prewitt・roberts・kirsch・frei の枝と内部の検証
    メモまで 1,738 字)、rotate_image・zoom_image_factor・mirror_image は 6,026 字が 1 段落で出た。"""
    sob = studio.op_impl_source("sobel_amp", None)
    assert "ndimage.sobel" in sob and "prewitt" not in sob and "kirsch" not in sob and "敵対的検証" not in sob, sob
    assert len(sob) < 200, len(sob)
    inv = studio.op_impl_source("invert_image", None)
    assert "1.0 - x" in inv and "gamma" not in inv and "equalize" not in inv and len(inv) < 200, inv
    rot = studio.op_impl_source("rotate_image", None)
    assert "ndimage.rotate" in rot and "affine_transform" not in rot and len(rot) < 300, rot
    # 族で共有していない関数は、従来どおり(最初の return の式)
    assert studio.op_impl_source("gaussian", None) == "ndimage.gaussian_filter(v, sigma=0.3 + 2.7 * a, mode=_border(b))"
    assert studio.op_impl_source("no_such_op_xyz") == ""
    # 全部の op: 族で共有する関数のうち、枝を取り出せた割合(取り出せない物は従来の全文に戻る)
    names = [r["name"] for r in api.list_ops()]
    assert len(names) > 500
    shared = [n for n in names if studio._impl_function(n) is not None
              and studio._dispatch_vars(*studio._impl_function(n))]
    assert len(shared) >= 100, len(shared)
    isolated = [n for n in shared if studio._kind_branch(*studio._impl_function(n))]
    assert len(isolated) >= 0.9 * len(shared), (len(isolated), len(shared))
    longer = [n for n in isolated if len(studio.op_impl_source(n, None)) > 1200]
    assert len(longer) <= 0.2 * len(isolated), longer[:10]          # 枝そのものが長い op は残る(上限で切る)
    # 長い実装は、開いた時も上限で切って印を付ける(つまみの欄を押し出さない)
    long = [n for n in names if len(studio.op_impl_source(n, None)) > studio.IMPL_OPEN_LIMIT]
    assert long, "上限を超える実装が 1 つも無いなら、この確かめは要らない"
    cut = studio.op_impl_source(long[0], studio.IMPL_OPEN_LIMIT, True)
    assert cut.endswith(" …") and len(cut) == studio.IMPL_OPEN_LIMIT + 2
    assert studio.op_impl_source(long[0], studio.IMPL_OPEN_LIMIT) == cut[:-2]


def test_opening_the_implementation_shows_one_branch_in_the_stage_panel(launch):
    from PySide6 import QtCore
    win, model = launch(lang="ja")
    lst = win._op_list
    names = [lst.item(i).data(QtCore.Qt.UserRole) for i in range(lst.count())]
    lst.setCurrentRow(names.index("rotate_image")); win._op_buttons["insert"].click(); _pump(0.3)
    win._stage_list.setCurrentRow(0); _pump(0.2)
    win._impl_toggle.setChecked(True); _pump(0.2)
    text = win._stage_detail.text()
    assert "ndimage.rotate" in text and "affine_transform" not in text and "zoom" not in text, text
    assert len(text) < 700, len(text)                              # 直す前は 6,000 字を超えた


# --------------------------------------------------------------------------- #
# 定番の op の、実装が読まないつまみ                                                #
# --------------------------------------------------------------------------- #
def test_starter_and_staple_knobs_the_code_never_reads_are_shown_as_unused():
    """直す前: 検索が空の時の一覧と「定番」の欄に出る op のうち 33 op・50 本のつまみが、動かしても何も変わらないのに
    動かせた(invert_image・fill_up・skeleton の a・b など)。実装が引数を 1 度も読まないつまみは「未使用」。"""
    import param_specs
    import studio_search as ss
    names = list(dict.fromkeys(list(studio.starter_ops()) + [n for _t, ops_ in ss.STAPLES for n in ops_]))
    names = [n for n in names if api.find_op(n) is not None]
    assert len(names) >= 30, len(names)
    verdict = {(n, k): studio._impl_reads_knob(n, k) for n in names for k in "ab"}
    never = sorted(key for key, v in verdict.items() if v is False)
    assert len(never) >= 30, len(never)                            # 全部の extra が入った環境で 62
    movable = [key for key in never if studio.knob_use(*key)[0] != "unused"]
    assert not movable, movable
    # 読み取りが盲目でない事: 効くと分かっているつまみは「読む」と出る
    for n, k in (("gaussian", "a"), ("gaussian", "b"), ("threshold", "a"), ("rotate_image", "a"), ("mirror_image", "a"),
                 ("scale_image", "a"), ("scale_image", "b"), ("select_shape", "a"), ("dilation_circle", "a")):
        assert studio._impl_reads_knob(n, k) is True, (n, k)
    # 表(param_specs.UNUSED_KNOBS)は、実装が読むつまみを止めていない(otsu に渡すだけの 4 本を除く)
    passed_on = {("auto_threshold", "a"), ("auto_threshold", "b"), ("binary_threshold", "a"), ("binary_threshold", "b")}
    listed = [(n, k) for n, ks in param_specs.UNUSED_KNOBS.items() for k in ks if api.find_op(n) is not None]
    assert len(listed) >= 30
    for n, k in listed:
        assert studio.knob_use(n, k) == ("unused", "spec"), (n, k)
        assert studio._impl_reads_knob(n, k) is False or (n, k) in passed_on, (n, k)


@pytest.mark.parametrize("name,dead", [("invert_image", "ab"), ("fill_up", "ab"), ("rotate_image", "b"),
                                       ("dilation_circle", "b")])
def test_the_dead_knobs_of_a_starter_op_cannot_be_moved(launch, name, dead):
    from PySide6 import QtCore
    win, model = launch()
    lst = win._op_list
    names = [lst.item(i).data(QtCore.Qt.UserRole) for i in range(lst.count())]
    lst.setCurrentRow(names.index(name)); _pump(0.1)
    assert len(win._op_arg_spins) == 2 and len(win._knob_rows) == 2  # zip が空になって素通りしない
    for spin, letter in zip(win._op_arg_spins, "ab"):               # + の上の欄
        assert spin.isEnabled() == (letter not in dead), (name, letter)
    win._op_buttons["insert"].click(); _pump(0.3)
    win._stage_list.setCurrentRow(0); _pump(0.2)
    for krow, letter in zip(win._knob_rows, "ab"):
        assert krow.raw.isEnabled() == (letter not in dead), (name, letter)


# --------------------------------------------------------------------------- #
# 検索のカード・書き出しのボタン・型で絞るスイッチのヒント                              #
# --------------------------------------------------------------------------- #
def test_search_cards_are_whole_when_the_lists_style_changes_the_font(launch):
    """直す前: 領域を出す段の後に「ぼかす」と打つと、カードに「先に: cv_dist → gaussian」の行が付いて 4 行になり、
    ラベルの高さが要る高さより低かった(下線と「p」「y」の下が欠けた)。カードの高さを、行を一覧に入れる前(様式の字の
    大きさが効く前)に 1 度だけ求めていた為。Windows のフォントでは直す前は 32 枚中 32 枚が欠け、直した後は 0 枚
    (C:/Windows/Fonts を読む設定での実測)。offscreen の既定のフォントは様式の字と同じなので差が出ない —— ここでは
    一覧の様式で字を大きくして、同じ状況(入れる前と後で字の大きさが違う)を作る。"""
    win, model = launch(lang="ja", user=True)
    _search(win, "otsu"); _enter(win)
    win._docks["operators"].raise_(); _pump(0.2)
    lst = win._search_ui["list"]
    lst.setStyleSheet("QLabel { font-size: 15pt; }"); _pump(0.1)
    _search(win, "ぼかす"); _pump(0.2)
    rows = [r for g in win._search_ui["rows"]().values() for r in g]
    four = [r for r in rows if len(r["text"].splitlines()) >= 3]
    assert len(four) >= 3, [r["text"] for r in rows][:3]            # 「先に: …」の付くカードが出ている
    cut = []
    for r in rows:
        lst.scrollToItem(r["item"]); _pump(0.05)
        label = r["label_widget"]
        need = label.heightForWidth(label.width())
        if label.height() < need:
            cut.append((r["name"], label.height(), need))
    assert not cut, cut[:5]


def test_the_docks_export_button_shows_its_label(launch):
    """直す前: 処理手順の dock の書き出しのボタンは、作った時点の sizeHint で幅を固定していて、表示後の字の幅に足りず
    「Python」が「…」になった(固定 61 px、表示後の sizeHint 89 px)。"""
    win, model = launch(lang="ja", user=True)
    win._docks["pipeline"].show(); win._docks["pipeline"].raise_(); _pump(0.3)   # hidden at first run
    b = win._buttons["export"]
    # (2026-11-15, integration) P04: a picture in the strip like its neighbours; "Python" is in its tooltip
    assert "Python" in b.toolTip() and b.isVisibleTo(win)
    import studio_theme
    side = studio_theme.density()["icon_btn"]
    from PySide6 import QtCore
    assert (b.width(), b.height()) == (side, side)                 # the picture's own square
    assert b.toolButtonStyle() != QtCore.Qt.ToolButtonTextBesideIcon


def test_the_type_filter_switch_explains_itself_in_japanese(launch):
    """直す前: 「前段の出力を受けられる op だけ表示」のヒントは、日本語の UI でも英語の文 + 日本語の注記だった
    (表に行が無かった。合成したヒントなので、英語だけのヒントを数える門にも掛からなかった)。"""
    win, model = launch(lang="ja", user=True)
    tip = win._ops_fit["check"].toolTip()
    assert "operators whose input" not in tip and "Nothing is converted" not in tip, tip
    paragraphs = [p for p in tip.split("\n\n") if p.strip()]
    assert len(paragraphs) == 2 and all(_CJK.search(p) for p in paragraphs), tip
    win._apply_language("en"); _pump(0.2)
    assert win._ops_fit["check"].toolTip().startswith("On: operators whose input type does not match")


# --------------------------------------------------------------------------- #
# docs のショートカットの表 = 実際の割り当て                                        #
# --------------------------------------------------------------------------- #
#: 表の書き方 → Qt のキーの名前
_KEY_NAMES = {"Ctrl+↑": "Ctrl+Up", "Ctrl+↓": "Ctrl+Down", "Ctrl+→": "Ctrl+Right", "Ctrl+←": "Ctrl+Left",
              "Ctrl+Enter": "Ctrl+Return"}


def _guide_shortcut_rows(text):
    """STUDIO_GUIDE の「Help ▸ Keyboard shortcuts」の文の後に続く最初の表の (操作の名前, [キー …])。"""
    lines = text.splitlines()
    start = next(i for i, ln in enumerate(lines) if "Help ▸ Keyboard shortcuts" in ln)
    rows, in_table = [], False
    for ln in lines[start:]:
        if ln.startswith("|"):
            in_table = True
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            for name, keys in zip(cells[0::2], cells[1::2]):
                found = re.findall(r"`([^`]+)`", keys)
                if name and found:
                    rows.append((name, found))
        elif in_table:
            break
    return rows


def test_the_guides_shortcut_tables_match_the_real_key_bindings(launch):
    """直す前: F1 を「選んでいる op のヘルプ」に変えた(一覧は Ctrl+F1)のに、STUDIO_GUIDE の 7 言語と STUDIO_UX の
    15 か所が「Keyboard shortcuts = F1」のままだった。11/12 に足した門は、決まった 3 つの誤りの形しか探さない。
    ここでは、表の行のうち窓の QAction の名前と一致する物を全部、実際の割り当てと突き合わせる。"""
    from PySide6 import QtGui
    win, model = launch(lang="en")
    bound = {}
    for a in win.findChildren(QtGui.QAction):
        name = a.text().replace("&", "").replace("…", "").strip().lower()
        if name and a.shortcuts():
            bound.setdefault(name, set()).update(k.toString() for k in a.shortcuts())
    assert len(bound) >= 40, len(bound)
    paths = sorted(glob.glob(os.path.join(ROOT, "docs", "STUDIO_GUIDE*.md")))
    assert len(paths) == 7, paths
    list_key = win._actions["shortcuts"].shortcut().toString()
    assert list_key == "Ctrl+F1" and win._actions["selected_help"].shortcut().toString() == "F1"
    for p in paths:
        with open(p, encoding="utf-8") as f:
            text = f.read()
        rows = _guide_shortcut_rows(text)
        assert len(rows) >= 20, (os.path.basename(p), len(rows))
        assert {"Keyboard shortcuts", "Help for the selected operator", "Undo", "Redo"} <= {n for n, _k in rows}
        matched = 0
        for name, keys in rows:
            have = bound.get(name.lower())
            if have is None:
                continue                     # 「Zoom in / out」のように 2 つの操作をまとめた行は、名前では引けない
            matched += 1
            for k in keys:
                want = QtGui.QKeySequence(_KEY_NAMES.get(k, k)).toString()
                assert want and want in have, (os.path.basename(p), name, k, sorted(have))
        assert matched >= 18, (os.path.basename(p), matched)
    for p in paths + [os.path.join(ROOT, "docs", "STUDIO_UX.md")]:
        with open(p, encoding="utf-8") as f:
            said = re.findall("Help ▸ Keyboard shortcuts\\s*[(（]([^)）]+)[)）]", f.read())
        assert said and set(said) == {list_key}, (os.path.basename(p), said)


def test_the_changelog_tells_the_user_about_the_keys_that_moved():
    with open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8") as f:
        text = f.read()
    head = text[:text.index("## 1.1.1")]
    for word in ("`F1`", "`Ctrl+F1`", "`Ctrl+Y`", "coins", "保存して閉じる"):
        assert word in head, word


# --------------------------------------------------------------------------- #
# 独立レビュー 3 回目(2026-11-15): Enter の後のステータスと検索欄・見本の後の題・     #
# 確認が 2 回壊れて閉じる時の写し                                                    #
# --------------------------------------------------------------------------- #
def test_a_not_added_sentence_does_not_outlive_the_next_enter_that_adds(launch):
    """直す前: abs_diff_image + Enter(入らない)の後に gaussian + Enter で段は入ったが、ステータスは最大 6 秒
    「abs_diff_image … (not added)」のまま(入れたのに入っていないと読めた)。"""
    win, model = launch(lang="en", user=True)
    _search(win, "abs_diff_image"); _enter(win)
    assert not model.stages and "abs_diff_image" in win.statusBar().currentMessage()
    _search(win, "gaussian"); _enter(win)
    assert [s[0] for s in model.stages] == ["gaussian"]
    assert "abs_diff_image" not in win.statusBar().currentMessage(), win.statusBar().currentMessage()


def test_the_plus_button_also_clears_an_old_not_added_sentence(launch):
    """+ ボタンで入れた時も同じ(段を入れる道は 1 つ: add_op)。"""
    from PySide6 import QtCore
    win, model = launch(lang="en", user=True)
    _search(win, "abs_diff_image"); _enter(win)
    assert "abs_diff_image" in win.statusBar().currentMessage()
    win._search_ui["edit"].clear(); _pump(0.6)
    lst = win._op_list
    names = [lst.item(i).data(QtCore.Qt.UserRole) for i in range(lst.count())]
    lst.setCurrentRow(names.index("median")); _pump(0.05)
    win._op_buttons["insert"].click(); _pump(0.3)
    assert [s[0] for s in model.stages] == ["median"]
    assert "abs_diff_image" not in win.statusBar().currentMessage()


def test_a_sentence_saying_why_stays_when_enter_adds_nothing(launch):
    """入らなかった時の文は消さない(狭めすぎの見張り。直す前も通る)。"""
    win, model = launch(lang="en", user=True)
    _search(win, "gaussian"); _enter(win)
    _search(win, "abs_diff_image"); _enter(win)
    assert [s[0] for s in model.stages] == ["gaussian"]
    assert "abs_diff_image" in win.statusBar().currentMessage()


def test_after_enter_adds_the_query_is_selected_so_the_next_word_replaces_it(launch):
    """直す前: 「二値化」+ Enter の後も欄の字は残り、選ばれていなかった。続けて「ノイズ」と打つと「二値化ノイズ」で
    検索した。ここでは英語の語で、キーは QTest で打つ。"""
    from PySide6.QtTest import QTest
    win, model = launch(lang="en", user=True)
    edit = win._search_ui["edit"]
    win.activateWindow(); edit.setFocus(); _pump(0.1)
    QTest.keyClicks(edit, "otsu"); _pump(0.5)
    _enter(win)
    assert [s[0] for s in model.stages] == ["otsu"]
    assert edit.text() == "otsu" and edit.selectedText() == "otsu", (edit.text(), edit.selectedText())
    QTest.keyClicks(win.focusWidget(), "fill"); _pump(0.5)
    assert edit.text() == "fill", edit.text()


def test_after_enter_adds_nothing_the_query_is_left_as_typed(launch):
    """入らなかった時は選ばない(打ち直すか、行をクリックして選ぶ)。直す前も通る。"""
    win, model = launch(lang="en", user=True)
    edit = win._search_ui["edit"]
    _search(win, "abs_diff_image"); _enter(win)
    assert not model.stages and edit.text() == "abs_diff_image" and edit.selectedText() == ""


def test_opening_a_sample_image_retitles_the_window(launch, tmp_path):
    """直す前: 写真を開いた後に File ▸ Sample images(または検索の「見本を開く」)で見本の画像に替えても、窓の題は
    写真のファイル名のままだった(image_path は None)。合成のデモ画像に替えた時も同じ。"""
    import fullseye
    win, model = launch(lang="en")
    photo = tmp_path / "review_photo.png"
    fullseye.write_image(str(photo), np.clip(np.random.default_rng(5).random((40, 56)), 0, 1))
    assert win._load_image_path(str(photo)) is True
    _pump(0.2)
    assert "review_photo.png" in win.windowTitle()
    win._load_sample_image("coins"); _pump(0.2)
    assert win._state["input_sample"] == "coins" and win._state["image_path"] is None
    assert "review_photo.png" not in win.windowTitle(), win.windowTitle()
    assert win._load_image_path(str(photo)) is True
    _pump(0.2)
    assert "review_photo.png" in win.windowTitle()
    win._actions["demo"].trigger(); _pump(0.2)
    assert win._state["input_sample"] == "__demo__"
    assert "review_photo.png" not in win.windowTitle(), win.windowTitle()


def test_opening_a_search_sample_after_discarding_retitles_the_window(launch, monkeypatch, tmp_path):
    """検索の「見本を開く」で破棄に答えた時(M12 で見本の画像も読むようになった入口)。"""
    import fullseye
    win, model = launch(lang="en")
    monkeypatch.setattr(studio, "CONFIRM_HOOK", lambda p, t, txt: True)
    photo = tmp_path / "review_photo.png"
    fullseye.write_image(str(photo), np.clip(np.random.default_rng(6).random((40, 56)), 0, 1))
    assert win._load_image_path(str(photo)) is True
    _one_unsaved_stage(win, model)
    assert "review_photo.png" in win.windowTitle()
    assert win._open_search_sample("FA — scratch on hairline metal") is True
    _pump(0.3)
    assert win._state["input_sample"] == "metal_hairline_scratch"
    assert "review_photo.png" not in win.windowTitle(), win.windowTitle()


def _break_both_confirmations(win, monkeypatch, tmp_path):
    """終了の確認も、代わりに出す英語の確認も例外を出す。ログと写しの置き場は tmp_path(本物の置き場に書かない)。"""
    log = tmp_path / "studio_crash.log"
    monkeypatch.setattr(studio, "_crash_log_path", lambda: str(log))

    def boom():
        raise RuntimeError("guard broke")

    def hook_boom(*_a):
        raise RuntimeError("dialog broke")
    win.close_guard = boom
    monkeypatch.setattr(studio, "CLOSE_CONFIRM_HOOK", hook_boom)
    return log


def test_closing_after_two_broken_confirmations_keeps_a_copy_of_the_unsaved_work(launch, monkeypatch, tmp_path):
    """直す前: 確認が 2 回続けて壊れると、2 回目で聞かずに閉じ、未保存の段はログの 1 行(例外)だけを残して消えた。
    今は閉じる前に、処理手順(Open pipeline で開ける形)と Program の未適用の文を studio_crash.log の隣に書き、
    置き場をログに残す。"""
    win, model = launch(lang="en")
    _one_unsaved_stage(win, model)
    win._state["code_dirty"] = True
    log = _break_both_confirmations(win, monkeypatch, tmp_path)
    assert _close(win) is False                                  # 1 回目は閉じない
    assert not glob.glob(str(tmp_path / "studio_unsaved_*"))
    assert _close(win) is True                                   # 2 回目は閉じる(閉じられない窓にしない)
    pipes = glob.glob(str(tmp_path / "studio_unsaved_*_pipeline.json"))
    progs = glob.glob(str(tmp_path / "studio_unsaved_*_program.txt"))
    assert len(pipes) == 1 and len(progs) == 1, os.listdir(str(tmp_path))
    with open(pipes[0], encoding="utf-8") as fh:
        saved = json.load(fh)
    assert [st[0] for st in saved["stages"]] == ["gaussian"]
    back = studio.PipelineModel(np.zeros((8, 8)))
    back.load_dict(saved)                                         # Open pipeline と同じ読み方で読める
    assert [st[0] for st in back.stages] == ["gaussian"]
    text = log.read_text(encoding="utf-8")
    assert "a copy of the unsaved work was kept" in text and pipes[0] in text, text


def test_closing_after_two_broken_confirmations_writes_nothing_when_nothing_is_unsaved(launch, monkeypatch, tmp_path):
    """未保存の物が無ければ写しは書かない(置き場に空のファイルを増やさない)。"""
    win, model = launch(lang="en")
    _break_both_confirmations(win, monkeypatch, tmp_path)
    assert _close(win) is False and _close(win) is True
    assert not glob.glob(str(tmp_path / "studio_unsaved_*"))
