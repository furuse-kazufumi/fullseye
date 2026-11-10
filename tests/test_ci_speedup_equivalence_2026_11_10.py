# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""CI の高速化(2026-11-10)で書き換えた検査が、**前と同じ答え**を出すことの門。

速くするために書き換えたのは「同じ物を何度も作る」「同じ文字列を何度も分割する」ところだけで、
門が何を表明するかは変えていない。ここでは書き換えの前の形(素直な実装)をこのファイルに
写し、同じ入力で答えが一致することを確かめる。

1. ``tools/gen_maturity._named_in``(語の集合で引く)== 以前の ``re.search(r"\\b<op>\\b")``
2. ``tests/test_provenance_naming._hits``(1 回の分割を使い回す)== 以前の語ごとの ``_contains_vendor``

★このファイルには op の名前を書かない(``tools/gen_maturity.py`` は ``tests/`` に op 名が
現れるかを数えるので、ここで名前を出すと成熟度台帳の事実が動く)。
"""
from __future__ import annotations

import ast
import glob
import importlib.util
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


GM = _load(os.path.join("tools", "gen_maturity.py"), "gen_maturity_eq_t20261110")
PN = _load(os.path.join("tests", "test_provenance_naming.py"), "provenance_naming_eq_t20261110")


def _old_named_in(ops, tests):
    """書き換える前の形(2026-11-10 まで ``collect()`` の中にあった 1 行)。"""
    return [o for o in ops if re.search(r"\b%s\b" % re.escape(o), tests)]


def test_named_in_matches_the_regex_on_edge_cases():
    text = "x = abc_def(1)\nfoo-bar baz.qux\n# 名前ab9 _lead trail_\nUnicodeé\nab9\n"
    names = ["abc_def", "abc", "def", "foo", "bar", "foo-bar", "baz.qux", "qux", "ab9", "名前ab9",
             "_lead", "lead", "trail_", "trail", "Unicodeé", "Unicode", "missing", "a.c"]
    tokens = set(re.findall(r"\w+", text))
    assert GM._named_in(names, text, tokens) == _old_named_in(names, text)
    assert GM._named_in(names, text, tokens), "空の答えどうしの一致は検査にならない"


def test_named_in_matches_the_regex_on_the_real_ledger():
    """能力ノートの op を、今の ``tests/`` の全ソースで突き合わせる。

    以前の検索は全 op で約 30 秒かかるので、3 本に 1 本(決まった間引き)と、単語文字以外を含む名前の全部。
    """
    tests = GM._test_sources()
    tokens = set(re.findall(r"\w+", tests))
    ops = []
    for p in sorted(glob.glob(os.path.join(GM.SRC_DIR, "*.md"))):
        ops += GM._front_matter(io.open(p, encoding="utf-8").read(), p)["ops"]
    assert len(ops) > 500, len(ops)
    sample = ops[::3] + [o for o in ops if not re.fullmatch(r"\w+", o)]
    new = GM._named_in(sample, tests, tokens)
    assert new == _old_named_in(sample, tests)
    assert 0 < len(new) <= len(sample)


def _old_hits(text, relpath):
    """書き換える前の ``_hits``(禁止語ごとに分割し直す)。"""
    return [w for w in PN._BANNED if PN._contains_vendor(text, w) and not PN._allowed(w, relpath)]


def test_provenance_hits_match_the_per_vendor_scan():
    samples = [("this module exists because Prophesee ships it", "newmod.py"),
               ("MVTecStyleCatalog TeliCamera toshiba_teli", "x.py"),
               ("writelines whitelist RateLimiter", "somemod.py"),
               ("Basler driver", "acquire.py"), ("Basler driver", "lightfield.py")]
    for path in sorted(glob.glob(os.path.join(ROOT, "tools", "*.py")))[:60]:
        try:
            tree = ast.parse(io.open(path, encoding="utf-8").read())
        except (SyntaxError, UnicodeDecodeError):
            continue
        doc = ast.get_docstring(tree)
        if doc:
            samples.append((doc, os.path.relpath(path, ROOT).replace(os.sep, "/")))
    assert len(samples) > 30, len(samples)
    got = [PN._hits(t, r) for t, r in samples]
    assert got == [_old_hits(t, r) for t, r in samples]
    assert any(got), "どの見本にも当たらないなら、一致は検査にならない"

