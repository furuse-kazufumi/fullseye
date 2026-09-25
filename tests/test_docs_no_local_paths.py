# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""公開ページにローカル絶対パスを出さない門。

`docs/` は `docs/_config.yml` のとおり **そのまま https://furuse.work/ として配信**
される。ところが 2026-09-25 の実測で、その配下に **12 ファイル・25 か所**の
ローカル絶対パスが載っていた —— 作業メモ(`SESSION_SUMMARY.md`)、監査記録、
GPU の 2 本、そして **6 言語の設計判断集**。最後のものの出どころは
`tests/test_glyphops.py` の ★ コメント 1 行で、生成器がそれを転記していた。
**テストのコメントが公開ページになる**経路が在る、ということである。

★**綴りを 1 つ決め打たない。** 最初 `C:/dev` だけを探して `D:/docs/...` を
取りこぼした(しかもその D: ドライブは 2026-07-27 の移設で**もう存在しない**)。
探すのは「ドライブ文字 + 区切り」「`/Users/`」「`AppData`」「`/home/<誰か>`」
という**形**で、正当な教材例だけを理由つきで免除する。

★**配信から外す表は 1 つだけ。** 何を配信しないかは `_config.yml` の `exclude` が
正本で、この門はそれを読む。ここに別の一覧を書くと、片方だけ増える。
"""
from __future__ import annotations

import io
import os
import re

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(_ROOT, "docs")
CONFIG = os.path.join(DOCS, "_config.yml")

#: 配信されるファイル(Jekyll が素通しするもののうち、文字列を読める種類)
_SERVED_SUFFIX = (".md", ".json", ".yml", ".html", ".txt")

#: ローカルの機械を指す綴り。**形で探す** —— 特定のドライブ名を決め打たない。
_LOCAL = (
    #: ★区切りは 1 つとも 2 つとも書かれる —— JSON の中では区切りが**二重になる**。
    #:   一重の形だけ見ていたので 2026-09-25 に二重の形を丸ごと見落とした
    #:   (最大の漏れが公開 JSON の 164 か所だった)。
    #: ★ここに綴りの例を書かないこと。この門は自分のコメントも読むので、
    #:   例として書いたパスがそのまま違反になる(実際に一度そうなった)。
    #: ★`e:\n` のようなエスケープ列と LaTeX の `q:\,` は道ではない ——
    #:   区切りの次が n/r/t で語が続かないもの、道に使えない文字で始まるものは外す。
    ("ドライブ文字", re.compile(
        r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]{1,2}"
        r"(?![nrt](?![A-Za-z0-9_]))[A-Za-z0-9_.*]")),
    ("/Users/", re.compile(r"/Users/")),
    ("AppData", re.compile(r"AppData")),
    ("/home/<誰か>", re.compile(r"/home/[a-z]")),
)

#: 免除は**理由つきで名指し**する(綴りそのものを書く)。空でも表は残す ——
#: 「免除が無い」ことと「表が無い」ことを区別するため。
EXEMPT_SPELLINGS: dict = {
    "C:\\path\\to\\images":
        "読み手が自分のパスに置き換える教材例(docs/MCP.md の設定例)",
    "D:\\more":
        "同じ教材例の 2 つ目の要素(区切り文字の説明)",
    "C:\\Program Files":
        "Windows 標準の場所。読み手の機械にも在るので、こちらの環境を指していない",
    "C:\\\\...\\\\fullseye.exe":
        "説明用の省略形で、実在のパスではない",
}


def _excluded_from_the_site() -> set:
    """`_config.yml` の `exclude:` —— 配信しないものの**正本**。"""
    if not os.path.exists(CONFIG):
        return set()
    out, inside = set(), False
    for ln in io.open(CONFIG, encoding="utf-8").read().splitlines():
        if ln.startswith("exclude:"):
            inside = True
            continue
        if inside:
            m = re.match(r"\s+-\s+(.+?)\s*$", ln)
            if m:
                out.add(m.group(1))
            elif ln.strip() and not ln.startswith(("#", " ")):
                inside = False
    return out


def _served_files() -> list:
    skip = _excluded_from_the_site()
    out = []
    for root, dirs, names in os.walk(DOCS):
        rel_root = os.path.relpath(root, DOCS).replace(os.sep, "/")
        rel_root = "" if rel_root == "." else rel_root + "/"
        for n in sorted(names):
            if not n.lower().endswith(_SERVED_SUFFIX):
                continue
            rel = rel_root + n
            if rel in skip or n in skip:
                continue
            out.append(rel)
    return out


def _offences(rel: str) -> list:
    return _offences_in(rel, io.open(os.path.join(DOCS, rel),
                                     encoding="utf-8", errors="replace").read())


def _offences_in(rel: str, text: str) -> list:
    """★本文を引数で受ける —— 破壊試験が**実在のファイルの中身に依存しない**ように。
    手元の作業メモに何が書いてあるかで門の試験が変わるのは、試験の欠陥である。"""
    bad = []
    for lineno, ln in enumerate(text.splitlines(), 1):
        for label, pat in _LOCAL:
            for m in pat.finditer(ln):
                snippet = ln[max(0, m.start() - 10):m.start() + 60]
                if any(sp in ln for sp in EXEMPT_SPELLINGS):
                    continue
                bad.append("%s:%d [%s] %s" % (rel, lineno, label, snippet.strip()))
    return bad


def _assert_no_local_paths(pairs) -> None:
    """公開されるファイルにローカル絶対パスが無いこと(門の本体)。

    *pairs* は `(名前, 本文)` の並び。本文を渡せるようにしてあるのは、破壊試験が
    **本物の判定**を呼べるようにするため(式をもう一度書いた門は通ってしまう)。
    """
    bad = []
    for rel, text in pairs:
        bad.extend(_offences_in(rel, text))
    assert not bad, (
        "公開ページにローカル絶対パスが %d か所:%s%s"
        % (len(bad), chr(10), chr(10).join(bad[:12])))


def test_the_published_docs_carry_no_local_paths():
    files = _served_files()
    assert len(files) > 50, "配信対象が %d 件しか見つからない(門が何も見ていない)" % len(files)
    _assert_no_local_paths((rel, io.open(os.path.join(DOCS, rel), encoding="utf-8",
                                         errors="replace").read()) for rel in files)


@pytest.mark.parametrize("line", [
    "作業ディレクトリは `C:/dev/projects/imgevolve` です。",
    "素材は D:\\\\docs\\\\image_corpus_v2 に置いた。",
    "ログは /Users/someone/Library/Logs にある。",
    "キャッシュは AppData の下。",
    "設定は /home/kazufumi/.config にある。",
])
def test_the_local_path_gate_catches_each_spelling(line):
    """★門を壊して確かめる —— 綴りごとに 1 本ずつ、本物の判定を通す。

    2026-09-25 に最初 `C:/dev` だけを探して `D:/docs/...` を取りこぼした。
    **1 つの綴りだけ試す破壊試験では、その取りこぼしは見つからない。**
    """
    with pytest.raises(AssertionError) as e:
        _assert_no_local_paths([("ためし.md", line)])
    assert "ローカル絶対パス" in str(e.value)


def test_the_gate_does_not_fire_on_ordinary_prose():
    """通常の文では鳴らないこと(鳴りっぱなしの門は外される)。"""
    _assert_no_local_paths([
        ("ためし.md", "図は https://furuse.work/ops/2d/smoothing/gaussian.html にある。"),
        ("ためし2.md", "相対パスは `docs/ops/` や `examples/data/` と書く。"),
    ])


def test_the_work_note_is_not_served():
    """作業メモが配信対象に入っていないこと(外し忘れたら落ちる)。"""
    assert "SESSION_SUMMARY.md" not in _served_files(), (
        "SESSION_SUMMARY.md が配信される —— docs/_config.yml の exclude に入れること")


def test_the_exclude_list_is_read_from_the_site_config():
    """配信しないものの正本は `_config.yml` —— 門はそれを読む(表を 2 つ持たない)。"""
    assert "SESSION_SUMMARY.md" in _excluded_from_the_site()


def test_the_exemptions_are_spelled_out_and_actually_used():
    """免除の綴りは、実際にどこかで使われていること(消えた免除を残さない)。"""
    if not EXEMPT_SPELLINGS:
        return
    served = _served_files()
    for spelling, why in EXEMPT_SPELLINGS.items():
        assert why.strip(), "免除の理由が空: %r" % spelling
        assert any(spelling in io.open(os.path.join(DOCS, r), encoding="utf-8",
                                       errors="replace").read() for r in served), (
            "免除に在るが、どの公開ページにも出てこない: %r" % spelling)
