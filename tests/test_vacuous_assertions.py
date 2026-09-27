# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""空振りする表明(vacuous pass)を**増やさない**門。

    assert all(cond(x) for x in xs)     # xs が空なら無条件に通る
    for x in xs: assert cond(x)         # 0 周なら通る

対象が空のとき、これらは「検査したふり」になる。値域や有限性の門が潰れを見ない
のと同じ型で、**検査が実行されていないこと**が成功と区別できない。

★2026-09-26 に 3 回踏んだ:
  1. `all("cited_by_count" in w for w in r)` を **0 件に対して真**と読んだ
  2. コーパスの選り分けで、取得器が**クエリ文字列を資料に埋めていた**ので
     全件が自分のクエリに一致した(探針が資料の中に入っていた)
  3. スイート監視が「集計行が見つからない」を**「失敗 0 件」**と表示した

★**一括修正はしない。** 探針を 3 回締めても候補は 126 件(84 ファイル)残り、その多くは
`for a, b in zip(got, imgs)` のように**読めば空でないと分かる**もので、
機械には区別できない。だから「今ある分を台帳に固定し、**増えたら落ちる**」
ラチェットにする —— `docs/COLLECTION_SIZES.json` と同じ考え方。

★**台帳が長いときは、まず探針を疑う。** 283 → 152 → 126 と落ちた。最後の 26 件は
`for img in (v, w)` —— **書き下した 2 要素の列**で、中身が呼び出しの戻りでも
周る回数は 2 と決まっている。空になりうると数えていた私の誤りだった。

台帳 = ``docs/VACUOUS_ASSERTION_DEBT.json``。落ちたら**新しく書いた側を直す**
(件数を増やすのではない)。減らしたら台帳も下げる。
"""
from __future__ import annotations

import ast
import io
import json
import os
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.join(ROOT, "tests")
LEDGER = os.path.join(ROOT, "docs", "VACUOUS_ASSERTION_DEBT.json")


def _names(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _filtered_comp(node: ast.AST) -> bool:
    """`if` のある内包表記 = 0 件になりうる。"""
    return isinstance(node, (ast.GeneratorExp, ast.ListComp, ast.SetComp)) and \
        any(g.ifs for g in node.generators)


def find_in_source(src: str) -> list[int]:
    """空になりうる対象に対する表明の数。

    絞り方: 対象が「``if`` のある内包表記」か「呼び出しの戻り」で、かつ同じ関数内に
    件数の保証(``assert xs`` / ``assert len(xs) ...`` / ``assert xs.size``)が無いもの。
    `zip` / `sorted` / `list` は中身次第なので引数側を見る。`range(定数)` は数えない。

    ★**行番号を返す**。件数だけだと「増えた」と言えても**どこを直すか**が言えず、
    落ちた人がもう一度探す手間を払う。
    """
    try:
        # ★他の試験の docstring に `\*` 等が在ると ast.parse が
        #   DeprecationWarning を出す。数えるだけの処理なので黙らせる
        #   (門の出力に無関係な警告を 84 ファイル分足さない)。
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(src)
    except SyntaxError:
        return []
    hits: list[int] = []
    for fn in [n for n in ast.walk(tree)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        guards: set[str] = set()
        risky: set[str] = set()
        for n in ast.walk(fn):
            if isinstance(n, ast.Assert):
                t = n.test
                cand = t.left if isinstance(t, ast.Compare) else t
                if isinstance(cand, ast.Call) and isinstance(cand.func, ast.Name) \
                        and cand.func.id == "len" and cand.args:
                    guards |= _names(cand.args[0])
                elif isinstance(cand, ast.Name):
                    guards.add(cand.id)
                elif isinstance(cand, ast.Attribute) and cand.attr == "size":
                    guards |= _names(cand)
            if isinstance(n, ast.Assign) and len(n.targets) == 1 \
                    and isinstance(n.targets[0], ast.Name) \
                    and (_filtered_comp(n.value) or isinstance(n.value, ast.Call)):
                risky.add(n.targets[0].id)

        def risky_source(node: ast.AST) -> bool:
            if _filtered_comp(node):
                return True
            # ★書き下した列(`for img in (v, w)`)は、中身が何であれ空にならない。
            #   中の名前が「呼び出しの戻り」でも、周る回数は 2 と決まっている。
            if isinstance(node, (ast.Tuple, ast.List, ast.Set)) and node.elts:
                return False
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "range":
                    return False
                if node.func.id in ("zip", "enumerate", "sorted", "list", "reversed"):
                    return any(risky_source(a) for a in node.args) or \
                        bool(_names(node) & risky)
                return True
            return bool(_names(node) & risky)

        for n in ast.walk(fn):
            if isinstance(n, ast.Assert):
                t = n.test
                if isinstance(t, ast.UnaryOp) and isinstance(t.op, ast.Not):
                    t = t.operand
                if isinstance(t, ast.Call) and isinstance(t.func, ast.Name) \
                        and t.func.id in ("all", "any") and t.args:
                    a = t.args[0]
                    srcs = [g.iter for g in a.generators] \
                        if isinstance(a, (ast.GeneratorExp, ast.ListComp, ast.SetComp)) else [a]
                    if any(risky_source(s) for s in srcs) and \
                            not (set().union(*[_names(s) for s in srcs]) & guards):
                        hits.append(n.lineno)
            if isinstance(n, ast.For) and len(n.body) <= 4 \
                    and any(isinstance(b, ast.Assert) for b in n.body) \
                    and risky_source(n.iter) and not (_names(n.iter) & guards):
                hits.append(n.lineno)
    return sorted(hits)


def count_in_source(src: str) -> int:
    """件数だけが要る所のための薄い包み。"""
    return len(find_in_source(src))


def measure() -> dict[str, int]:
    out: dict[str, int] = {}
    for name in sorted(os.listdir(TESTS)):
        if not (name.startswith("test_") and name.endswith(".py")):
            continue
        n = count_in_source(io.open(os.path.join(TESTS, name),
                                    encoding="utf-8", errors="replace").read())
        if n:
            out[name] = n
    return out


def _ledger() -> dict[str, int]:
    if not os.path.isfile(LEDGER):
        return {}
    return json.load(io.open(LEDGER, encoding="utf-8"))["per_file"]


# --------------------------------------------------------------------------- #
def test_the_probe_catches_a_seeded_vacuous_assertion():
    """★門を壊して確かめる —— 空振りする形を種として与え、数えられることを見る。

    守られている形(件数の保証つき・リテラルの列)を数えないことも同時に見る。
    片方だけでは、常に 0 を返す探針でも常に全部数える探針でも通ってしまう。
    """
    seeded = '''
def test_seeded_all():
    rows = fetch()                       # 空のことがある
    assert all("k" in r for r in rows)
def test_seeded_loop():
    hits = [x for x in items if x.bad]   # 絞り込み = 0 件になりうる
    for h in hits:
        assert h.ok
'''
    guarded = '''
def test_guarded():
    rows = fetch()
    assert rows, "0 件では検証にならない"
    assert all("k" in r for r in rows)
def test_literal():
    for a, b in zip([1, 2], [1, 2]):
        assert a == b
def test_range():
    for i in range(3):
        assert i >= 0
def test_literal_of_names():
    v = make(); w = make()          # 中身は呼び出しの戻りだが、周るのは 2 回で確定
    for img in (v, w):
        assert img is not None
'''
    assert count_in_source(seeded) == 2, count_in_source(seeded)
    assert count_in_source(guarded) == 0, count_in_source(guarded)


def test_the_debt_does_not_grow():
    """★今ある分は台帳に固定し、**増えたら落ちる**。

    一括修正はしない —— 候補 126 件の多くは `for a, b in zip(got, imgs)` のように
    読めば空でないと分かるもので、機械には区別できない。新しく書く分だけを止める。
    落ちたら**新しく書いた側を直す**(台帳の数を増やすのではない)。
    """
    led = _ledger()
    assert led, ("台帳が空 —— docs/VACUOUS_ASSERTION_DEBT.json が無いか壊れている。"
                 "★空の台帳はこの門を素通りさせるので、空自体を失格にする")
    now = measure()
    grew = {f: (led.get(f, 0), n) for f, n in now.items() if n > led.get(f, 0)}
    assert not grew, (
        "空になりうる対象への表明が増えた(台帳 -> 実測): %s\n"
        "  `assert all(... for ... in xs)` や `for x in xs: assert` は、xs が空なら"
        "**無条件に通る**。件数を確かめる 1 行(`assert xs`)を先に置くこと。" % grew)


def test_the_ledger_has_no_rows_for_files_that_are_gone():
    """減ったら台帳も下げる(古い床が残ると、また空振りが増える)。"""
    led = _ledger()
    now = measure()
    stale = sorted(f for f in led if not os.path.isfile(os.path.join(TESTS, f)))
    assert not stale, "台帳に在るがファイルが無い: %s" % stale
    shrank = {f: (led[f], now.get(f, 0)) for f in led if now.get(f, 0) < led[f]}
    assert not shrank, (
        "実測が台帳より少ない —— 直したのなら台帳も下げること(台帳 -> 実測): %s" % shrank)
