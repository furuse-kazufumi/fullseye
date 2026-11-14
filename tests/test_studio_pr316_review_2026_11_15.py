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
    assert edit.text() == "blurx" and not edit.visibleRegion().isEmpty()


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
