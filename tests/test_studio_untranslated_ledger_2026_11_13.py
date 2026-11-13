# -*- coding: utf-8 -*-
"""日本語の UI に英語のまま残る文の門と台帳(2026-11-13、初回起動の点検 M9)。

従来の門(test_studio_first_minute_2026_11_12.py)は、窓に並ぶ見出し・ボタン・メニューの字だけを数えていた。
この門は、それに入らない 2 種類を数える。

1. **ツールヒント**(実際に Studio を起動し、日本語に切り替えて数える)。
2. **書いた所で tr() を通らない文**(studio.py の構文木から): ステータスの文 ``flash(...)``、エラーの窓の題
   ``report_error(題, ...)`` / ``ERROR_HOOK``、確認 ``CONFIRM_HOOK``、``QMessageBox.*`` の題と文、窓の題
   ``setWindowTitle(...)``。``flash`` と ``report_error`` の題は中で ``tr()`` を通すので、**書式の無い文で表に日本語の
   行がある物**は訳されている扱い。書式つき(``"... %s" % x``・``"..." + x``)は書いた所で ``tr()`` を通す。

残っている物は台帳 ``tests/data/studio_untranslated_ja.json`` に全部並べる。

* 台帳に無い英語の文が増えたら落ちる(``tr()`` を通して表に行を足すか、意図して残すなら台帳に足す)。
* 台帳にあるのに訳された(または消えた)ら落ちる(台帳から外す。台帳を古い言い訳の置き場にしない)。

2026-11-13 の直しの前後: ツールヒント 99 → 4(残りは Program 欄の 4 つ。Program 欄は別の作業の枝で作っている)、
書いた所で tr() を通らない文 161 → 台帳の件数。
"""
import ast
import json
import os
import re
import time
from collections import Counter

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "tests", "data", "studio_untranslated_ja.json")
_CJK = re.compile("[぀-ヿ一-鿿]")

#: 呼び出しの名前 → 数える引数の位置
_CALLS = {"flash": (0,), "report_error": (0,), "ERROR_HOOK": (1, 2), "CONFIRM_HOOK": (1, 2),
          "setWindowTitle": (0,), "information": (1, 2), "warning": (1, 2), "critical": (1, 2),
          "question": (1, 2), "about": (1, 2)}
#: 中で tr() を通す呼び出し(書式の無い文は、表に行があれば訳される)
_TR_INSIDE = ("flash", "report_error")


def _english(text):
    return bool(re.search(r"[A-Za-z]{3,}", text or "")) and not _CJK.search(text or "")


def _head(node):
    """引数が tr() を通らない文字列なら (書式の有無, 先頭の文字列)。tr() を通る・文字列でない時は None。"""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "tr":
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return False, node.value
    if isinstance(node, ast.JoinedStr):
        parts = [v.value for v in node.values if isinstance(v, ast.Constant) and isinstance(v.value, str)]
        return (True, "".join(parts)) if parts else None
    if isinstance(node, ast.BinOp):
        got = _head(node.left)
        return (True, got[1]) if got else None
    return None


def untranslated_literals(src=None, table=None):
    """studio.py の中で、日本語の UI でも英語のまま出る文の (呼び出し, 文) の一覧(並びは出てくる順)。"""
    import studio
    if src is None:
        with open(os.path.join(ROOT, "studio.py"), encoding="utf-8") as f:
            src = f.read()
    table = studio.STRINGS_I18N if table is None else table
    out = []
    for node in ast.walk(ast.parse(src)):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        name = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else None
        if name not in _CALLS:
            continue
        for i in _CALLS[name]:
            if i >= len(node.args):
                continue
            got = _head(node.args[i])
            if got is None:
                continue
            formatted, text = got
            if not _english(text):
                continue
            if name in _TR_INSIDE and not formatted and (table.get(text) or {}).get("ja"):
                continue
            out.append((name, text))
    return out


def english_tooltips_in_japanese():
    """日本語に切り替えた Studio の窓で、英語のまま出るツールヒント(重複なし、並べ替え済み)。"""
    from PySide6 import QtGui, QtWidgets
    import studio
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    win, _model = studio.build_window()
    win.show()
    end = time.monotonic() + 0.5
    while time.monotonic() < end:
        app.processEvents(); time.sleep(0.01)
    try:
        win._apply_language("ja"); app.processEvents()
        qt_own = set()
        for sub in win.findChildren(QtWidgets.QMdiSubWindow):
            menu = sub.systemMenu()
            if menu is not None:
                qt_own.update(menu.actions())
        tips = [w.toolTip() for w in win.findChildren(QtWidgets.QWidget) if w.toolTip() and w.isVisibleTo(win)]
        tips += [a.toolTip() for a in win.findChildren(QtGui.QAction)
                 if a not in qt_own and a.toolTip() and a.toolTip() != a.text().replace("&", "")]
        tips = sorted({t.strip() for t in tips if t.strip()})
        return len(tips), [t for t in tips if _english(t) and not re.fullmatch(r"[a-z][a-z0-9_]*", t)
                           and t != "Fullseye Studio"]
    finally:
        studio._UI_LANG["code"] = "en"
        win.close_guard = lambda: True
        win.quiesce(); win.close()


def _ledger():
    with open(LEDGER, encoding="utf-8") as f:
        return json.load(f)


def test_untranslated_literals_match_the_ledger():
    got = untranslated_literals()
    assert len(got) > 50                                   # 数え方が壊れて空になっていない
    have = Counter(map(tuple, _ledger()["literals"]))
    now = Counter(got)
    new = sorted((now - have).elements())
    gone = sorted((have - now).elements())
    assert not new, ("日本語の UI で英語のまま出る文が増えた(tr() を通して i18n.json に行を足すか、意図して残すなら "
                     "tests/data/studio_untranslated_ja.json の literals に足す): %s" % new[:10])
    assert not gone, "訳された(または消えた)文が台帳に残っている。台帳から外す: %s" % gone[:10]


def test_english_tooltips_in_japanese_match_the_ledger(monkeypatch, tmp_path):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(tmp_path / "s.ini"))
    shown, eng = english_tooltips_in_japanese()
    assert shown > 100                                     # 窓のツールヒントを実際に読めている
    want = sorted(_ledger()["tooltips"])
    assert eng == want, ("日本語の UI で英語のままのツールヒントが台帳と違う。増えた: %s / 訳された: %s"
                         % (sorted(set(eng) - set(want))[:5], sorted(set(want) - set(eng))[:5]))


def test_the_gate_sees_a_new_english_message():
    """門そのものの確かめ: 表に無い文・書式つきの文・tr() を通した文・表にある文を見分ける。"""
    src = (
        "flash('a brand new message')\n"
        "flash('pipeline cleared')\n"
        "flash('saved ' + name)\n"
        "flash(tr('saved %s') % name)\n"
        "dlg.setWindowTitle('Brand new window')\n"
        "dlg.setWindowTitle(tr('Brand new window'))\n"
        "report_error('Could not open image', e)\n"
        "QtWidgets.QMessageBox.question(win, 'Odd title', 'Odd text')\n"
    )
    table = {"pipeline cleared": {"ja": "処理手順を空にしました"}, "Could not open image": {"ja": "画像を開けませんでした"}}
    got = untranslated_literals(src, table)
    assert got == [("flash", "a brand new message"), ("flash", "saved "), ("setWindowTitle", "Brand new window"),
                   ("question", "Odd title"), ("question", "Odd text")], got
