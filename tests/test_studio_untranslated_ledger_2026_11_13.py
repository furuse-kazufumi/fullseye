# -*- coding: utf-8 -*-
"""日本語の UI に英語のまま残る文の門と台帳(2026-11-13、初回起動の点検 M9)。

従来の門(test_studio_first_minute_2026_11_12.py)は、窓に並ぶ見出し・ボタン・メニューの字だけを数えていた。
この門は、それに入らない 2 種類を数える。

1. **ツールヒント**(実際に Studio を起動し、日本語に切り替えて数える)。起動した窓に在る部品の全部(隠れている
   部品も含む)と QAction。後から開く窓(3-D ビューア・設定 …)の部品は、起動時には無いので入らない。
   **op の一覧の行(QListWidgetItem)のツールヒントは数えない**(部品ではない。op 名・HALCON の別名・category・
   sort の英語で、2026-11-15 に日本語の UI で 706 行の全部が英語のまま。直す前も 1003 行の全部)。
2. **書いた所で tr() を通らない文**(studio.py の構文木から): ステータスの文 ``flash(...)``、エラーの窓の題
   ``report_error(題, ...)`` / ``ERROR_HOOK``、確認 ``CONFIRM_HOOK``、``QMessageBox.*`` の題と文、窓の題
   ``setWindowTitle(...)``、部品の字 ``setText`` / ``setPlainText`` / ``setPlaceholderText`` / ``set_message`` /
   ``showMessage`` / ``addButton``。``flash`` と ``report_error`` の題は中で ``tr()`` を通し、``setText`` で置いた
   部品の字は言語の切り替えの時に表を引くので、**書式の無い文で表に日本語の行がある物**は訳されている扱い。
   書式つき(``"... %s" % x``・``"..." + x``)は書いた所で ``tr()`` を通す。

★この門が見ない物(2026-11-15、PR #316 の独立レビューで分かった範囲。下の試験
``test_what_the_gate_does_not_see_is_written_down`` に同じ形を書いてある): 変数に入れてから渡した文
(``msg = "..."; flash(msg)``)、``"...".format(x)``、条件式(``"a" if c else "b"``)、表に無い名前の呼び出し。
「全部」ではなく「この 16 種の呼び出しに直書きした文」の台帳。ツールヒントの側は、op の一覧の行のツールヒントを
見ない(``test_english_tooltips_in_japanese_match_the_ledger`` が、見ていない事と件数を確かめる)。

残っている物は台帳 ``tests/data/studio_untranslated_ja.json`` に全部並べる。

* 台帳に無い英語の文が増えたら落ちる(``tr()`` を通して表に行を足すか、意図して残すなら台帳に足す)。
* 台帳にあるのに訳された(または消えた)ら落ちる(台帳から外す。台帳を古い言い訳の置き場にしない)。

2026-11-13 の直しの前後: 部品のツールヒント 99 → 4(見えている部品だけの数え方。残りは Program 欄の 4 つ)、
書いた所で tr() を通らない文 161 → 113(10 種の呼び出し)。2026-11-15: 隠れている部品のヒントも数えて 17、
部品の字の呼び出しを足して台帳の件数。
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
          "question": (1, 2), "about": (1, 2),
          # 2026-11-15: 部品の字(状態の行・入力欄の案内・画像の欄の文 …)
          "setText": (0,), "setPlainText": (0,), "setPlaceholderText": (0,), "set_message": (0,),
          "showMessage": (0,), "addButton": (0,)}
#: 表を実行時に引く呼び出し(書式の無い文は、表に行があれば訳される): flash と report_error の題は中で tr() を通し、
#: setText で置いた部品の字は言語の切り替えの時に表を引く
_TR_INSIDE = ("flash", "report_error", "setText")
#: 呼び出しごとの件数の下限(走査が一部だけ空になっても気づく。実数の 8 割ほど)
_FLOORS = {"flash": 40, "report_error": 28, "setWindowTitle": 16, "setText": 30, "setPlaceholderText": 8}


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
    """日本語に切り替えた Studio の窓で、英語のまま出るツールヒント(重複なし、並べ替え済み)。

    ``(数えたツールヒントの数, 英語のままの物, op の一覧の行のツールヒント)``。3 つ目は門の範囲外(数えない物の
    件数を確かめる為だけに返す)。"""
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
        # ★2026-11-15: 隠れている部品も数える(タブの裏・畳んだ欄。見えている部品だけだと 4、全部で 17)
        tips = [w.toolTip() for w in win.findChildren(QtWidgets.QWidget) if w.toolTip()]
        tips += [a.toolTip() for a in win.findChildren(QtGui.QAction)
                 if a not in qt_own and a.toolTip() and a.toolTip() != a.text().replace("&", "")]
        tips = sorted({t.strip() for t in tips if t.strip()})
        lst = win._op_list
        rows = [lst.item(i).toolTip() for i in range(lst.count()) if lst.item(i).toolTip()]
        return len(tips), [t for t in tips if _english(t) and not re.fullmatch(r"[a-z][a-z0-9_]*", t)
                           and t != "Fullseye Studio"], rows
    finally:
        studio._UI_LANG["code"] = "en"
        win.close_guard = lambda: True
        win.quiesce(); win.close()


def _ledger():
    with open(LEDGER, encoding="utf-8") as f:
        return json.load(f)


def test_untranslated_literals_match_the_ledger():
    got = untranslated_literals()
    assert len(got) >= 120, len(got)                       # 数え方が壊れて空になっていない
    per_call = Counter(name for name, _text in got)
    for name, floor in _FLOORS.items():
        assert per_call[name] >= floor, (name, per_call[name], floor)
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
    shown, eng, rows = english_tooltips_in_japanese()
    assert shown > 150, shown                              # 窓のツールヒントを実際に読めている(隠れた部品も)
    # ★範囲外(2026-11-15、PR #316 の独立レビュー 3 回目): op の一覧の行のツールヒントは、ほぼ全部が英語のまま
    # (op 名・HALCON の別名・category・sort)。台帳は数えない。訳し始めたら、ここを台帳の件数に替える。
    assert len(rows) >= 500, len(rows)
    assert sum(1 for t in rows if _english(t)) >= 0.9 * len(rows)
    assert not set(t.strip() for t in rows) & set(eng)
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
    # 部品の字(2026-11-15 に足した呼び出し)
    src = (
        "status.setText('applied %d stage(s)' % n)\n"
        "status.setText('ready')\n"
        "status.setText('pipeline cleared')\n"
        "edit.setPlaceholderText('search operators…')\n"
        "view.set_message('Nothing to display')\n"
        "bar.showMessage('done ' + name)\n"
        "box.addButton('Throw away', role)\n"
        "box.addButton(tr('Throw away'), role)\n"
    )
    got = untranslated_literals(src, table)
    assert got == [("setText", "applied %d stage(s)"), ("setText", "ready"),
                   ("setPlaceholderText", "search operators…"), ("set_message", "Nothing to display"),
                   ("showMessage", "done "), ("addButton", "Throw away")], got


def test_what_the_gate_does_not_see_is_written_down():
    """門の限界(2026-11-15、PR #316 の独立レビュー): 変数に入れてから渡した文・``.format``・条件式は見ない。
    見えるようにしたら、この試験を書き換える(限界を黙って残さない)。"""
    src = (
        "msg = 'said through a variable'\n"
        "flash(msg)\n"
        "flash('with a format call {}'.format(x))\n"
        "flash('one text' if ok else 'another text')\n"
        "status.setText(text)\n"
        "other_call('an unlisted call')\n"
    )
    assert untranslated_literals(src, {}) == []
