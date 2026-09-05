# -*- coding: utf-8 -*-
"""Studio の設定入口が 1 つに保たれていること。

2026-09-05 のセキュリティ監査で、**テストが利用者の実レジストリに書いていた**
実害が見つかった(`HKCU\\Software\\Fullseye\\Studio\\recent_files` の 10 件中
8 件が pytest の一時パス)。原因は「隔離を個々のテストファイルに置いていた」こと
で、置き忘れた `test_studio_params.py` が素通しになっていた。

隔離そのものは `tests/conftest.py` のセッション autouse に移した。ここでは
**その隔離を迂回する書き方が入り込んでいないか**をソースの不変条件として見る。
隔離を足しても、迂回できるなら同じ事故がまた起きるので。
"""
from __future__ import annotations

import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

#: `QSettings(` の出現。org/app 名を渡す形だけが「ネイティブ格納庫に書く」形。
_NATIVE_QSETTINGS = re.compile(r"""QSettings\(\s*["']Fullseye["']""")


def _read(path):
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


def test_studio_builds_qsettings_only_inside_its_one_factory():
    """`studio.py` の中で `QSettings(` を組むのは `_settings()` だけ。

    入口が 2 つ以上あると、片方にだけ環境変数の逃がしが効いて残りが漏れる。
    """
    src = _read(os.path.join(ROOT, "studio.py")).splitlines()
    factory_lines = set()
    inside = False
    for i, line in enumerate(src):
        if line.startswith("def _settings("):
            inside = True
        elif inside and line and not line[0].isspace():
            inside = False
        if inside:
            factory_lines.add(i)
    stray = [(i + 1, ln.strip()) for i, ln in enumerate(src)
             if "QSettings(" in ln and i not in factory_lines]
    assert not stray, (
        "studio.py が `_settings()` の外で QSettings を組んでいる。"
        "設定入口は 1 つに保つこと(環境変数の逃がしが効かなくなる): %s" % stray)


def test_no_test_constructs_the_native_settings_store_directly():
    """テストが `QSettings("Fullseye", ...)` を直に組まない。

    直に組むと `FULLSEYE_STUDIO_SETTINGS` を無視して**利用者の**レジストリ /
    plist / 設定 ini に書く。2026-09-05 に実際に起きた形。
    """
    offenders = []
    for name in sorted(os.listdir(HERE)):
        if not name.endswith(".py"):
            continue
        text = _read(os.path.join(HERE, name))
        for i, line in enumerate(text.splitlines(), 1):
            if _NATIVE_QSETTINGS.search(line):
                offenders.append("%s:%d" % (name, i))
    assert not offenders, (
        "テストがネイティブ設定格納庫を直に開いている(利用者の環境を汚す)。"
        "`studio._settings()` を使うこと: %s" % offenders)


def test_the_session_isolation_is_actually_in_force():
    """隔離が**効いていること**を実際に確かめる。宣言だけでは足りない。"""
    ini = os.environ.get("FULLSEYE_STUDIO_SETTINGS", "")
    assert ini, "セッション autouse の隔離が効いていない(conftest.py を見ること)"
    assert ini.endswith(".ini")
    studio = pytest.importorskip("studio")
    s = studio._settings()
    got = s.fileName()
    assert os.path.abspath(got) == os.path.abspath(ini), (
        "_settings() が隔離先を返していない: %s" % got)
