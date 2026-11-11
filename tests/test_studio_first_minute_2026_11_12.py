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


PENDING_ROWS_CEILING = 400
