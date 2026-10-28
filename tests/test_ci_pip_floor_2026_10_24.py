"""CI の全ジョブが、Python を用意した直後に pip と certifi を修正版へ上げること。

2026-10-21: 認証局 eMudhra(emSign)の中間 CA の秘密鍵が漏れ、certifi 2026.10.19 と、それを
同梱する pip 26.2.2 が失効させた。Python 3.15.1 / 3.14.9 / 3.13.17 は同梱の pip を上げて出たが、
CI の 3.11 / 3.12 は runner 側の古い pip(古い証明書)のまま PyPI に繋ぐ。setup-python の直後に
上げる step が無いジョブを門で拒む(ジョブを足したときの書き忘れを防ぐ)。
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.join(ROOT, ".github", "workflows")


def _steps_after_setup_python(text):
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("- uses: actions/setup-python@"):
            ind = len(ln) - len(ln.lstrip())
            j = i + 1
            while j < len(lines) and len(lines[j]) - len(lines[j].lstrip()) > ind:
                j += 1
            yield i + 1, (lines[j] if j < len(lines) else "") + "\n" + (lines[j + 1] if j + 1 < len(lines) else "")


def test_every_setup_python_is_followed_by_the_pip_and_certifi_floor():
    steps = []
    for name in ("ci.yml", "release.yml"):
        with open(os.path.join(WF, name), encoding="utf-8") as f:
            text = f.read().replace("\r\n", "\n")
        steps += [(name, lineno, nxt) for lineno, nxt in _steps_after_setup_python(text)]
    # 先に件数を保証する(読み方が壊れて 0 本になると、下のループは何も確かめずに通る)。
    assert len(steps) >= 8, "setup-python の step が %d 本しか見つからない(読み方が壊れていないか)" % len(steps)
    for name, lineno, nxt in steps:
        assert re.search(r'"pip>=26\.2\.2"', nxt) and re.search(r'"certifi>=2026\.10\.19"', nxt), (
            "%s:%d の setup-python の直後に pip / certifi を上げる step が無い" % (name, lineno))
