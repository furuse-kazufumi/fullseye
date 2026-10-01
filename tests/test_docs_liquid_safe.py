# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""公開サイト(docs/ を GitHub Pages の Jekyll がそのまま配信)で Liquid が読む文字列を置かない門。

★事故(2026-10-01): vxcore の docstring の C の宣言(波括弧を 2 つ重ねた配列の初期化子)が op ノート
docs/ops/vx/geometry/vx_warp_affine.md に写り、Jekyll がそれを Liquid の変数と読んで
**サイト全体のビルドが止まった**(furuse.work が 2 push 続けて更新されず、CI は緑のまま)。
Liquid はコード片(バッククォート)の中でも評価する。配信側の規則は配信側でしか見えないので、
git が追跡している docs/ の Markdown(Jekyll が処理する全部)を数える。
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPEN_VAR = "{" + "{"
OPEN_TAG = "{" + "%"
LIQUID = re.compile(re.escape(OPEN_VAR) + "|" + re.escape(OPEN_TAG))


def _offending(text: str) -> list[int]:
    """Liquid の開き記号がある行番号(1 始まり)。"""
    return [i for i, line in enumerate(text.splitlines(), 1) if LIQUID.search(line)]


def _served_markdown() -> list[Path]:
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "docs"], capture_output=True, check=True).stdout
    names = [n for n in out.decode("utf-8").split(chr(0)) if n]
    return [ROOT / n for n in names if n.endswith((".md", ".markdown")) and not n.startswith("docs/_site/")]


def test_the_probe_catches_liquid_openers():
    assert _offending("ok" + chr(10) + "mat = " + OPEN_VAR + "a,d},{b,e}}" + chr(10)) == [2]
    assert _offending(OPEN_TAG + " raw %}") == [1]
    assert _offending("{ {a,d}, {b,e} } と {x} は通る") == []


def test_no_served_markdown_has_liquid_openers():
    files = _served_markdown()
    assert len(files) > 1000, len(files)                 # 空を数えて通らない
    bad = []
    for p in files:
        rows = _offending(p.read_text(encoding="utf-8", errors="replace"))
        if rows:
            bad.append("%s:%s" % (p.relative_to(ROOT).as_posix(), rows[:5]))
    assert not bad, "Jekyll が Liquid と読む開き記号が公開 Markdown にある(サイトのビルドが止まる): %s" % bad[:20]
