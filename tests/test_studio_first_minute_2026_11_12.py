# -*- coding: utf-8 -*-
"""Studio の最初の 1 分(2026-11-12 の使い勝手点検)の回帰テスト: 言語(P-05)・案内(P-12)・ショートカット(P-11)。

件数は**実際に Studio を起動して**数える(ソースの grep ではない)。
"""
import json
import os
import re
import time

import pytest

import studio
import studio_layout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CJK = re.compile("[\u3040-\u30ff\u4e00-\u9fff]")


@pytest.fixture(scope="module")
def win(tmp_path_factory):
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    ini = tmp_path_factory.mktemp("first_minute") / "s.ini"
    prev = os.environ.get("FULLSEYE_STUDIO_SETTINGS")
    os.environ["FULLSEYE_STUDIO_SETTINGS"] = str(ini)
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    w, _model = studio.build_window()
    w.show()
    end = time.monotonic() + 0.8
    while time.monotonic() < end:
        app.processEvents(); time.sleep(0.01)
    yield w
    studio._UI_LANG["code"] = "en"
    w.close_guard = lambda: True
    w.quiesce(); w.close()
    if prev is None:
        os.environ.pop("FULLSEYE_STUDIO_SETTINGS", None)
    else:
        os.environ["FULLSEYE_STUDIO_SETTINGS"] = prev


def _pump(sec=0.3):
    from PySide6 import QtWidgets
    end = time.monotonic() + sec
    while time.monotonic() < end:
        QtWidgets.QApplication.processEvents(); time.sleep(0.01)


# --------------------------------------------------------------------------- #
# P-05: 言語の混在                                                              #
# --------------------------------------------------------------------------- #
def _texts(w):
    """Studio が作った操作部品の表示文字列(menu / action / ボタン / 見出し / 検索欄 / 枠 / 状態表示)。"""
    from PySide6 import QtGui, QtWidgets
    out = set()
    # Qt が MDI 子窓に付ける標準のシステムメニュー(Close / Maximize ...)は Studio が作った部品ではない
    qt_own = set()
    for sub in w.findChildren(QtWidgets.QMdiSubWindow):
        menu = sub.systemMenu()
        if menu is not None:
            qt_own.update(menu.actions())

    def add(t):
        t = (t or "").replace("&", "").strip()
        if t:
            out.add(t)
    for a in w.findChildren(QtGui.QAction):
        if a not in qt_own:
            add(a.text())
    for m in w.findChildren(QtWidgets.QMenu):
        add(m.title())
    for cls in (QtWidgets.QPushButton, QtWidgets.QLabel, QtWidgets.QToolButton, QtWidgets.QCheckBox,
                QtWidgets.QRadioButton):
        for x in w.findChildren(cls):
            add(x.text())
    for x in w.findChildren(QtWidgets.QGroupBox):
        add(x.title())
    for x in w.findChildren(QtWidgets.QLineEdit):
        add(x.placeholderText())
    for cls in (QtWidgets.QDockWidget, QtWidgets.QToolBar):
        for x in w.findChildren(cls):
            add(x.windowTitle())
    return out


def _exempt(text):
    """言語と無関係な表示文字列(除外の規則)。

    * 英字 3 文字以上の並びが無い(記号・単位・数だけ)
    * 識別子そのもの(小文字で始まり空白無し: op 名・サンプル画像名・カラーマップ名)
    * 製品名、言語の自称(English / Deutsch / 日本語 ... と、それを並べた言語メニューの題)
    * 画像情報の行(256×256 float64 [..])
    """
    if not re.search(r"[A-Za-z]{3,}", text):
        return True
    if re.fullmatch(r"[a-z][a-z0-9_]*", text):
        return True
    if text == "Fullseye Studio" or text in studio.LANGUAGES.values() or text == "Language / 言語 / 语言":
        return True
    if re.match(r"\d+×\d+ ", text):
        return True
    return False


#: 日本語モードで、英語のまま残る表示文字列の上限(実測。減らす方向にだけ動かす)
JA_MODE_ENGLISH_CEILING = 0


def test_japanese_mode_leaves_no_english_only_chrome(win):
    win._apply_language("ja"); _pump()
    try:
        left = sorted(t for t in _texts(win) if not _CJK.search(t) and not _exempt(t))
    finally:
        win._apply_language("en"); _pump()
    assert len(left) <= JA_MODE_ENGLISH_CEILING, "日本語モードで英語のまま(%d 件): %s" % (len(left), left[:20])


def test_english_mode_has_no_cjk_chrome(win):
    win._apply_language("en"); _pump()
    mixed = sorted(t for t in _texts(win) if _CJK.search(t) and t not in studio.LANGUAGES.values()
                   and t != "Language / 言語 / 语言")
    assert not mixed, "英語モードに日本語が混ざっている(%d 件): %s" % (len(mixed), mixed[:20])


def test_language_round_trip_restores_the_english_baseline(win):
    before = _texts(win)
    win._apply_language("ja"); _pump()
    assert _texts(win) != before
    win._apply_language("en"); _pump()
    assert _texts(win) == before


def test_work_mode_and_panel_names_equal_the_layout_models_japanese_labels():
    rows = studio.STRINGS_I18N
    for mode_id, en in studio.WORK_MODE_EN.items():
        assert rows[en]["ja"] == studio_layout.MODES[mode_id].label
    for panel, en in studio.PANEL_NAME_EN.items():
        if panel == "compare":
            continue          # 「Stage in → out」は先に別の訳「段の前後」があり、dock の題として使われてきた
        assert rows[en]["ja"] == studio_layout.PANELS[panel]["name"]
    assert set(studio.WORK_MODE_EN) == set(studio_layout.MODES)
    assert set(studio.PANEL_NAME_EN) == set(studio_layout.PANELS)


def test_rows_without_a_full_translation_are_counted_not_hidden():
    """日本語だけの行は ``pending_translation`` に置く(``strings`` の全言語テストを嘘にしない)。

    他言語は未訳で、UI は英語のまま。機械訳を「訳済み」として入れていない。件数は減らす方向にだけ動かす。
    """
    with open(os.path.join(ROOT, "studio_assets", "i18n.json"), encoding="utf-8") as f:
        d = json.load(f)
    rows = {k: v for k, v in d["pending_translation"].items() if k != "_note"}
    langs = [c for c in d["languages"] if c not in ("en", "ja")]
    pending = {c: sum(1 for v in rows.values() if not v.get(c)) for c in langs}
    assert all(v.get("ja") for v in rows.values()), "pending 行は少なくとも日本語を持つ"
    assert not set(rows) & set(d["strings"]), "同じ行が strings と pending の両方にある"
    assert len(rows) <= PENDING_ROWS_CEILING, "pending 行が増えた: %d" % len(rows)
    assert all(n == len(rows) for n in pending.values()), pending     # いまは全て日本語だけ


#: 2026-11-12 の画像欄の直し(日本語モードに残る英語)で、日本語だけの行を 83 本足した(210 → 293)。他言語は未訳のまま
PENDING_ROWS_CEILING = 294   # +1: 「impl: %s」(2 回目の直し)
# 2026-11-13 初回起動の点検の直し: 入れられない op の理由 3 文・行の印・最初の段の注記(S2)
PENDING_ROWS_CEILING += 5
PENDING_ROWS_CEILING += 1    # M5: 座標つきの画素の読み取りの 1 行
PENDING_ROWS_CEILING += 5    # M12: 検索の「見本」の群(見出し・行・ボタン・ツールチップ・使えない時の文)
PENDING_ROWS_CEILING += 18   # M10 / M9: 終了と破棄の確認の文・ボタン・題、見本を読んだ時の文
PENDING_ROWS_CEILING += 124  # M9: 窓のツールヒント 95(英語のまま 99 → 4)、ステータスの文・エラーと窓の題 29
PENDING_ROWS_CEILING += 3    # M3 / M4: 「実装を見る」とそのツールヒント、実測で出力が変わらなかったつまみの文
PENDING_ROWS_CEILING += 1    # L10: 空のパイプラインで実行した時の 1 行
PENDING_ROWS_CEILING += 2    # M15: ヘルプの検索で当たらない時・別の名前に寄せた時の文
PENDING_ROWS_CEILING += 2    # M13: 台帳の op の理由の文とボタン
PENDING_ROWS_CEILING += 1    # L9: 開けないファイルを落とした時の 1 行
PENDING_ROWS_CEILING += 3    # L11: op の一覧の右クリックのメニュー


# --------------------------------------------------------------------------- #
# P-12: ヒントの無い操作部品(実際に起動して数える)                                  #
# --------------------------------------------------------------------------- #
def _controls(w):
    """Studio が作った操作部品(ボタン・入力欄・選択・つまみ)。Qt 自身が中に作る部品は除く。"""
    from PySide6 import QtWidgets as W
    classes = (W.QPushButton, W.QToolButton, W.QComboBox, W.QSlider, W.QSpinBox, W.QDoubleSpinBox,
               W.QCheckBox, W.QRadioButton, W.QLineEdit, W.QListWidget, W.QTableWidget)
    out = []
    for cls in classes:
        for x in w.findChildren(cls):
            if x.objectName().startswith("qt_") or x.objectName() in ("ScrollLeftButton", "ScrollRightButton"):
                continue
            parent = x.parentWidget()
            if cls is W.QLineEdit and isinstance(parent, (W.QSpinBox, W.QDoubleSpinBox, W.QComboBox)):
                continue                              # 数値欄・コンボが中に持つ編集欄
            if cls is W.QToolButton and isinstance(parent, (W.QLineEdit, W.QMenuBar)):
                continue                              # 検索欄の「消す」ボタン・メニューバーの拡張ボタン(Qt の部品)
            out.append(x)
    return out


def _has_hint(x):
    ph = x.placeholderText() if hasattr(x, "placeholderText") else ""
    return bool(x.toolTip() or x.statusTip() or x.whatsThis() or ph)


#: ヒントもステータス説明もプレースホルダも無い操作部品の上限(2026-11-12 の点検では 40 件だった)
UNHINTED_CONTROL_CEILING = 0


def test_every_control_studio_builds_explains_itself(win):
    controls = _controls(win)
    assert len(controls) >= 100, "census が空に近い(%d)。数え方が壊れている" % len(controls)    # all() の前に件数を見る
    bare = [(type(x).__name__, (x.text() if hasattr(x, "text") else "")[:30]) for x in controls if not _has_hint(x)]
    assert len(bare) <= UNHINTED_CONTROL_CEILING, "ヒントの無い操作部品 %d 件: %s" % (len(bare), bare[:15])


def test_hints_follow_the_language_and_mode_buttons_name_their_panels(win):
    win._apply_language("en"); _pump()
    modes = {m: win._work_mode_actions[m] for m in studio_layout.MODES}
    tips_en = {m: a.toolTip() for m, a in modes.items()}
    assert len(set(tips_en.values())) == 4, "作業モードのヒントが同じ文の使い回し"
    for mode_id, mode in studio_layout.MODES.items():
        shown = [p for p in mode.visible if p != "result"]
        assert shown                                   # 件数を先に見る
        for panel in shown:
            en = studio.PANEL_NAME_EN[panel].split(" (")[0]
            first = en.split(" · ")[0].split(" & ")[0]
            assert first in tips_en[mode_id], (mode_id, panel, tips_en[mode_id])
    win._apply_language("ja"); _pump()
    try:
        tips_ja = {m: a.toolTip() for m, a in modes.items()}
    finally:
        win._apply_language("en"); _pump()
    assert all(_CJK.search(t) for t in tips_ja.values()), tips_ja
    assert len(set(tips_ja.values())) == 4


def test_new_hints_are_not_just_the_part_name_repeated(win):
    controls = _controls(win)
    assert len(controls) >= 100
    for x in controls:
        tip, text = x.toolTip().strip().lower(), (x.text() if hasattr(x, "text") else "").strip().lower()
        if tip and text:
            assert tip != text, "ヒントが部品名の繰り返し: %r" % text


#: 日本語モードで、英語のままのツールチップ件数の上限(従来から英語だけだったヒント。実測 2026-11-12)
JA_MODE_ENGLISH_TIP_CEILING = 123


def test_japanese_mode_english_only_tips_are_counted(win):
    from PySide6 import QtGui, QtWidgets
    win._apply_language("ja"); _pump()
    try:
        tips = set()
        for x in win.findChildren(QtWidgets.QWidget):
            if x.toolTip():
                tips.add(x.toolTip())
        for a in win.findChildren(QtGui.QAction):
            if a.toolTip() and a.toolTip() != a.text():
                tips.add(a.toolTip())
        english = [t for t in tips if not _CJK.search(t) and re.search(r"[A-Za-z]{3,}", t)]
    finally:
        win._apply_language("en"); _pump()
    assert len(tips) > 100
    assert len(english) <= JA_MODE_ENGLISH_TIP_CEILING, len(english)


# ---- op 一覧の行のヒント = その op のヘルプの先頭 1 文 ---------------------------------------- #
def test_op_row_tooltip_shows_the_help_sentence_in_the_ui_language(win):
    en = studio._help_first_sentence("abs_diff_image", "en")
    ja = studio._help_first_sentence("abs_diff_image", "ja")
    assert en and not _CJK.search(en), en
    assert ja and _CJK.search(ja), ja
    win._apply_language("en"); _pump()
    tip_en = win._op_row_tooltip("abs_diff_image")
    assert en in tip_en and "meaning depends on the op" not in tip_en
    win._apply_language("ja"); _pump()
    try:
        tip_ja = win._op_row_tooltip("abs_diff_image")
    finally:
        win._apply_language("en"); _pump()
    assert ja in tip_ja
    # ページの無い言語・op は今の文のまま
    row = studio._op_row("gaussian") if hasattr(studio, "_op_row") else None
    assert studio._help_first_sentence("no_such_op_xyz", "en") == ""


def test_hovering_an_op_row_shows_that_tooltip(win):
    from PySide6 import QtCore, QtGui, QtWidgets
    lst = win._op_list
    row = next(i for i in range(lst.count()) if lst.item(i).data(QtCore.Qt.UserRole) == "abs_diff_image")
    item = lst.item(row)
    rect = lst.visualItemRect(item)
    if not lst.viewport().rect().contains(rect.center()):
        lst.scrollToItem(item); _pump()
        rect = lst.visualItemRect(item)
    pos = rect.center()
    QtWidgets.QToolTip.hideText()
    ev = QtGui.QHelpEvent(QtCore.QEvent.ToolTip, pos, lst.viewport().mapToGlobal(pos))
    QtWidgets.QApplication.sendEvent(lst.viewport(), ev); _pump(0.2)
    assert studio._help_first_sentence("abs_diff_image", "en") in QtWidgets.QToolTip.text()
    QtWidgets.QToolTip.hideText()


# ---- 最初の 3 手の案内 ------------------------------------------------------------------------- #
def test_first_steps_band_shows_once_closes_and_returns_from_help(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(tmp_path / "s.ini"))
    from PySide6 import QtWidgets
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def launch():
        w, _m = studio.build_window()
        w.show(); _pump(0.3)
        return w

    def shut(w):
        w.close_guard = lambda: True
        w.quiesce(); w.close(); _pump(0.2)

    w = launch()
    try:
        assert not w._first_steps.isHidden(), "初回は案内を出す"
        text = " ".join(l.text() for l in w._first_steps.findChildren(QtWidgets.QLabel))
        assert "Sample images" in text and "+" in text and "▶▶" in text
        w._first_steps_close.click(); _pump()
        assert w._first_steps.isHidden()
    finally:
        shut(w)
    w = launch()
    try:
        assert w._first_steps.isHidden(), "閉じたら次回は出さない"
        act = next(a for a in w.menuBar().actions() if a.text().replace("&", "") == "Help").menu()
        first = next(a for a in act.actions() if a.text() == "First steps")
        first.trigger(); _pump()
        assert not w._first_steps.isHidden(), "Help から再表示できる"
    finally:
        shut(w)


def test_first_steps_text_is_translated(win):
    from PySide6 import QtWidgets
    win._apply_language("ja"); _pump()
    try:
        text = " ".join(l.text() for l in win._first_steps.findChildren(QtWidgets.QLabel))
    finally:
        win._apply_language("en"); _pump()
    assert "サンプルを開く" in text and "最初の 3 手" in text


# --------------------------------------------------------------------------- #
# P-11: ツールチップに書いたショートカットが、実際のキー割り当てと一致する              #
# --------------------------------------------------------------------------- #
_KEY_RE = re.compile(r"(?:(?:Ctrl|Shift|Alt)\+)+(?:[A-Za-z0-9]+|=|-)|\bF(?:1[0-2]|[1-9])\b|\bDel\b|\bHome\b|\bEsc\b")
_STOP = {"the", "and", "for", "all", "one", "this", "that", "with", "from", "into", "then", "any", "its", "your"}


def _tokens(text):
    text = re.sub(r"\([^)]*\)", " ", text.lower().replace("-", ""))
    return {t for t in re.findall(r"[a-z0-9]{3,}", text) if t not in _STOP}


def test_run_menu_lists_each_command_once(win):
    from PySide6 import QtWidgets
    run = next(a for a in win.menuBar().actions() if a.text().replace("&", "") == "Run").menu()
    names = [re.sub(r"\s*\([^)]*\)", "", a.text()).replace("…", "").strip().lower()
             for a in run.actions() if not a.isSeparator()]
    assert len(names) >= 3
    assert len(names) == len(set(names)), "Run メニューに同じ項目が 2 つある: %s" % names
    # 項目を減らしても、どこからでも効く F5 / F6 / Shift+F5 は生きている
    for key, seq in (("dbg_run", "F5"), ("dbg_step", "F6"), ("dbg_reset", "Shift+F5")):
        assert win._actions[key].shortcut().toString() == seq


def test_docs_no_longer_claim_the_wrong_shortcuts():
    import glob
    paths = glob.glob(os.path.join(ROOT, "docs", "STUDIO_GUIDE*.md")) + [os.path.join(ROOT, "docs", "STUDIO_UX.md")]
    assert len(paths) >= 8
    for p in paths:
        with open(p, encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                assert not re.search(r"Synthetic demo[^|]*Ctrl\+D", line), (p, n, line)   # Ctrl+D = Duplicate stage
                assert not re.search(r"1:1[^|]{0,6}Ctrl\+1\b", line), (p, n, line)       # 実際は Ctrl+Alt+1
                assert not re.search(r"3-?D surface[^|]{0,6}Ctrl\+3\b", line), (p, n, line)  # 実際は Ctrl+Alt+3
                assert "`Ctrl+0` / `Ctrl+1`" not in line and "| `Ctrl+3` |" not in line, (p, n, line)


def test_shortcuts_written_in_tooltips_match_the_real_key_bindings(win):
    from PySide6 import QtGui, QtWidgets
    win._apply_language("en"); _pump()
    actions = [a for a in win.findChildren(QtGui.QAction) if not a.shortcuts() == []]
    assert len(actions) > 20, "ショートカット付き action が少なすぎる(数え方が壊れている)"
    tips = []
    for x in win.findChildren(QtWidgets.QWidget):
        if x.toolTip():
            tips.append(x.toolTip())
    for a in win.findChildren(QtGui.QAction):
        if a.toolTip() and a.toolTip() != a.text():
            tips.append(a.toolTip())
    checked = 0
    problems = []
    for tip in tips:
        for m in _KEY_RE.finditer(tip):
            key = m.group(0).replace("Enter", "Return")
            seq = QtGui.QKeySequence(key)
            owners = [a for a in actions if seq in a.shortcuts()]
            words = _tokens(tip[:m.start()] + " " + tip[m.end():])
            ok = any(words & _tokens(a.text() + " " + a.toolTip()) for a in owners)
            checked += 1
            if not ok:
                problems.append((key, tip[:70], [a.text() for a in owners]))
    assert checked >= 10, "照合した件数が少なすぎる(%d)。検査が空振りしている" % checked
    assert not problems, "ツールチップのショートカットが実際の割り当てと合わない: %s" % problems


# --------------------------------------------------------------------------- #
# P-07 / P-20                                                                  #
# --------------------------------------------------------------------------- #
def test_fallback_help_cards_do_not_talk_to_developers():
    card2d = studio.op_help_html("no_such_op_xyz", "en", meta={"category": "demo", "in_sort": "image", "out_sort": "image"})
    card3d = studio.op_help_html_3d("no_such_op_xyz", {"category": "demo", "in": "mesh", "out": "mesh"})
    for card in (card2d, card3d):
        assert "No help page has been written" in card
        assert "studio_assets" not in card and "opdocs" not in card and "op_help" not in card


def test_message_text_on_the_picture_has_strong_contrast(win):
    from PySide6 import QtGui
    win._main_view.set_message("Pipeline error\n\ncontrast check")
    img = win._main_view._item.pixmap().toImage()

    def lum(c):
        f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        return 0.2126 * f(c.redF()) + 0.7152 * f(c.greenF()) + 0.0722 * f(c.blueF())
    bg = QtGui.QColor("#12141b")
    best = max(lum(QtGui.QColor(img.pixel(x, y))) for y in range(0, img.height(), 2) for x in range(0, img.width(), 2))
    ratio = (best + 0.05) / (lum(bg) + 0.05)
    assert ratio >= 7.0, "メッセージの文字のコントラストが足りない: %.2f:1(以前は 5.8:1)" % ratio
