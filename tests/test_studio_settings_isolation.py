# -*- coding: utf-8 -*-
"""Studio の設定入口が 1 つに保たれていること。

2026-09-05 のセキュリティ監査で、**テストが利用者の実レジストリに書いていた**
実害が見つかった(`HKCU\\Software\\Fullseye\\Studio\\recent_files` の 10 件中
8 件が pytest の一時パス)。原因は「隔離を個々のテストファイルに置いていた」ことで、
置き忘れた `test_studio_params.py` が素通しになっていた。

隔離そのものは `tests/conftest.py` のセッション autouse に移した。ここでは
**その隔離を迂回する書き方が入り込んでいないか**をソースの不変条件として見る。
隔離を足しても迂回できるなら、同じ事故がまた起きるので。

判定は **AST** で行う。文字列やコメントの中の `QSettings(` を数えると、
この検査自身の説明文で落ちる(最初にそれを踏んだ)。
"""
from __future__ import annotations

import ast
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _parse(path):
    with open(path, encoding="utf-8", errors="ignore") as f:
        return ast.parse(f.read(), filename=path)


def _qsettings_calls(tree):
    """`QSettings(...)` の呼び出しを (行, 第 1 引数が文字列か) で返す。"""
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        nm = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
        if nm != "QSettings":
            continue
        first_is_str = bool(node.args) and isinstance(node.args[0], ast.Constant) \
            and isinstance(node.args[0].value, str)
        out.append((node.lineno, first_is_str, node))
    return out


def test_studio_builds_qsettings_only_inside_its_one_factory():
    """`studio.py` で `QSettings(` を組むのは `_settings()` の中だけ。

    入口が 2 つ以上あると、片方にだけ環境変数の逃がしが効いて残りが漏れる。
    """
    tree = _parse(os.path.join(ROOT, "studio.py"))
    span = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_settings":
            span = (node.lineno, node.end_lineno)
            break
    assert span, "studio.py に _settings() が無い(設定入口の集約が失われている)"
    stray = [ln for ln, _, _ in _qsettings_calls(tree) if not span[0] <= ln <= span[1]]
    assert not stray, (
        "studio.py が _settings() の外で QSettings を組んでいる。設定入口は 1 つに"
        "保つこと(環境変数の逃がしが効かなくなる)。行: %s" % stray)


def test_no_test_opens_the_native_settings_store_directly():
    """テストが `QSettings("Fullseye", ...)` を直に組まない。

    org/app 名を渡す形はネイティブ格納庫(Windows ならレジストリ)を開くので、
    `FULLSEYE_STUDIO_SETTINGS` を無視して**利用者の環境**に書く。
    ini のパスを渡す形は隔離先なので許す。
    """
    offenders = []
    for name in sorted(os.listdir(HERE)):
        if not name.endswith(".py"):
            continue
        for ln, first_is_str, node in _qsettings_calls(_parse(os.path.join(HERE, name))):
            # 第 1 引数が文字列で、かつ 2 引数以上 = QSettings(org, app) 形。
            if first_is_str and len(node.args) >= 2:
                offenders.append("%s:%d" % (name, ln))
    assert not offenders, (
        "テストがネイティブ設定格納庫を直に開いている(利用者の環境を汚す)。"
        "`studio._settings()` を使うこと: %s" % offenders)


def test_the_session_isolation_is_actually_in_force():
    """隔離が**効いていること**を実際に確かめる。宣言だけでは足りない。"""
    ini = os.environ.get("FULLSEYE_STUDIO_SETTINGS", "")
    assert ini, "セッション autouse の隔離が効いていない(tests/conftest.py を見ること)"
    assert ini.endswith(".ini")
    studio = pytest.importorskip("studio")
    got = studio._settings().fileName()
    assert os.path.abspath(got) == os.path.abspath(ini), (
        "_settings() が隔離先を返していない: %s" % got)
