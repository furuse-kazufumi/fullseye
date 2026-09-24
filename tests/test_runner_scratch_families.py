# -*- coding: utf-8 -*-
"""台帳の引数を束ねて op を呼ぶ「ランナー」を**家族ごと数える**門。

## なぜ 1 箇所の守りでは足りなかったか

探針が作る ``text`` は ``"ラベル 73"`` のように**相対パスとしても成立する**。
台帳でパス引数を ``text`` と宣言している書き込み op にそれが渡ると、op は素直に
cwd へ書く —— cwd は repo 直下である。

2026-09-23 に ``chain_fuzz.run_chain`` へ捨て場(``_scratch_cwd``)を入れた。
それは効いていた。にもかかわらず 2026-09-25、スイートを回した直後に repo 直下へ
``ラベル 2`` / ``ラベル 73``(中身は xlsx)がまた生まれた。理由は単純で、
**同じことをするランナーがもう 1 本あった** —— ``chain_mine.mine_chain``。
同じ ``make_generators()`` を使い、同じ ``cf._bind_args()`` で台帳の引数を束ね、
同じように op を呼ぶのに、捨て場を通っていなかった。

守りを「関数 1 つ」に置くと、同じことをする関数が増えたときに黙って外れる。
だからこの門は**守りそのもの**ではなく、**守るべき家族の数**を固定する。
3 本目のランナーが増えたら、この門が落ちて「宣言しろ」と言う。

★この検査は**ソースを読むだけ**で、重い依存を一切 import しない。
``torch`` の有無で skip される場所に置くと、無い環境で家族が増えても気づけない。
"""
from __future__ import annotations

import ast
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

#: 台帳の引数を束ねる呼び出し。これを含む関数は「op を呼ぶランナー」である。
_BINDERS = ("_bind_args",)

#: 捨て場に入る印。
_GUARD = "_scratch_cwd"

#: ★**宣言された家族**。key = "<module>.<function>"、値 = 守り方の説明。
#:   ここに無い関数が ``_bind_args`` を呼んでいたら、この門は落ちる。
DECLARED_RUNNERS = {
    "tools/chain_fuzz.py::run_chain":
        "本体が `with _scratch_cwd():` の中にある(2026-09-23)",
    "tools/chain_mine.py::_run_step":
        "op を実際に呼ぶのはここ。採掘(`mine_chain`)と再走(`replay_chain`)の"
        "両方から呼ばれ、**どちらの入口も**捨て場の中にある(2026-09-25)",
}

#: 守りを直接持たない関数は、**包んで呼ぶ親**を名指しする。
#: 自分で捨て場に入らない関数は、**呼び手を全部**辿って確かめる。
#: 1 本でも守られていない呼び手があれば、そこから漏れる。

_MODULES = ("tools/chain_fuzz.py", "tools/chain_mine.py")


def _tree(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return ast.parse(fh.read())


def _calls(node) -> set:
    """*node* の中から呼ばれている名前(属性なら末尾)を集める。"""
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                out.add(f.id)
            elif isinstance(f, ast.Attribute):
                out.add(f.attr)
    return out


def _functions(rel):
    for n in ast.walk(_tree(rel)):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield n


def _runners() -> dict:
    """台帳の引数を束ねる関数 -> その中で呼ばれている名前。"""
    found = {}
    for rel in _MODULES:
        for fn in _functions(rel):
            names = _calls(fn)
            if names & set(_BINDERS):
                found["%s::%s" % (rel, fn.name)] = names
    return found


def test_the_binder_is_actually_found_so_this_gate_is_not_empty():
    """★一致の門は空を通す。まず「探している物が在る」ことを確かめる。"""
    found = _runners()
    assert found, ("`_bind_args` を呼ぶ関数が 1 つも見つからない —— "
                   "綴りが変わったか、モジュールが動いた。門が空になっている")


def test_every_runner_that_binds_ledger_args_is_declared():
    """★家族が増えたら落ちる。守りの有無でなく、**数え漏れ**を止める門。"""
    found = set(_runners())
    declared = set(DECLARED_RUNNERS)
    undeclared = sorted(found - declared)
    assert not undeclared, (
        "台帳の引数を束ねて op を呼ぶ関数が増えている: %s\n"
        "この関数は cwd を捨て場へ移して実行しているか? 探針の text は相対パスと"
        "しても成立するので、書き込み op が repo 直下にファイルを作る。"
        "確かめたうえで DECLARED_RUNNERS に理由つきで足すこと。" % undeclared)
    gone = sorted(declared - found)
    assert not gone, (
        "宣言されているのに見つからないランナー: %s(改名か削除。"
        "宣言のほうを直すこと —— 古い宣言は「守られている」という嘘になる)" % gone)


def _guarded(rel, name, by_name, depth=0) -> bool:
    """*name* が捨て場の中でしか走らないか。**呼び手を全部**辿って確かめる。

    自分で ``_scratch_cwd`` に入るならそこで真。そうでなければ、この関数を呼ぶ
    関数が**すべて**守られている必要がある —— 1 本でも守られていない入口が
    あれば、そこから repo 直下に漏れる。
    """
    assert depth < 8, "呼び手の連鎖が長すぎる(循環?): %s" % name
    fn = by_name.get(name)
    assert fn is not None, "%s::%s が見つからない" % (rel, name)
    if _GUARD in _calls(fn):
        return True
    callers = [o.name for o in by_name.values()
               if o.name != name and name in _calls(o)]
    assert callers, ("%s::%s は捨て場に入らず、呼び手も居ない —— "
                     "外から直接呼ばれるなら自分で入ること" % (rel, name))
    return all(_guarded(rel, c, by_name, depth + 1) for c in callers)


def test_each_declared_runner_really_enters_the_scratch_directory():
    """宣言しただけで守られたことにしない。ソースで裏を取る。

    ★呼び手を**全部**見るのが要点。``_run_step`` は採掘と再走の 2 つから
    呼ばれるので、片方だけ守っても漏れる。
    """
    for rel in _MODULES:
        by_name = {fn.name: fn for fn in _functions(rel)}
        for key in DECLARED_RUNNERS:
            if not key.startswith(rel + "::"):
                continue
            name = key.split("::", 1)[1]
            assert _guarded(rel, name, by_name), (
                "%s は捨て場の外から走りうる —— 呼び手のどれかが守られていない" % key)


def test_the_gate_actually_catches_an_unguarded_runner():
    """★門は壊して確かめる。守りを外した写しで、この門が落ちることを見る。"""
    rel = "tools/chain_mine.py"
    by_name = {fn.name: fn for fn in _functions(rel)}
    src = ast.parse("def lone():" + chr(10) + "    _bind_args(1,2,3,4)" + chr(10))
    fake = dict(by_name)
    fake["lone"] = src.body[0]
    try:
        _guarded(rel, "lone", fake)
    except AssertionError as e:
        assert "呼び手も居ない" in str(e)
    else:
        raise AssertionError("守られていないランナーを門が通した")
