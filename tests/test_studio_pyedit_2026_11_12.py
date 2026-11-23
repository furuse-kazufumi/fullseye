# -*- coding: utf-8 -*-
"""Python エディタの部品(色分け・補完・変数の一覧・ウォッチ・浮いた窓)の試験(2026-11-12)。

* Qt なしの論理(studio_pyedit_syntax / _complete / _values)と、offscreen の部品(studio_pyedit_qt / _vars_qt)。
* studio.py には依存しない(部品は単体で動く)。
"""
import ast
import io
import json
import os
import re
import sys
import time
import tokenize

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import studio_pyedit_complete as comp
import studio_pyedit_i18n as i18n
import studio_pyedit_syntax as syn
import studio_pyedit_values as V
import studio_timingkit as timing

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CJK = re.compile("[\u3040-\u30ff\u4e00-\u9fff\uac00-\ud7af]")
#: 止められない Watch の試験式 / expression used for an unstoppable Watch job.
_STUCK_WATCH_EXPRESSION = "gate.acquire()"


# --------------------------------------------------------------------------- #
# 道具
# --------------------------------------------------------------------------- #
def cats_of(text, backend="base", ops=(), prelude=()):
    """全文の ``[(語, 区分)]``(区分のある字句だけ。name と bracket は除く)。"""
    lx = syn.LineLexer(backend, ops=frozenset(ops), prelude=frozenset(prelude))
    out = []
    for toks, line in zip(lx.scan_text(text), text.split("\n")):
        out.append([(line[a:b], c) for a, b, c in toks if c not in ("name", "bracket")])
    return out


def flat(text, backend="base", **kw):
    return [x for line in cats_of(text, backend, **kw) for x in line]


def char_cats(text, backend="base", **kw):
    lx = syn.LineLexer(backend, **kw)
    res = []
    for toks, line in zip(lx.scan_text(text), text.split("\n")):
        res.append(syn.char_categories(line, toks))
    return res


@pytest.fixture()
def no_optional(monkeypatch):
    """pygments と jedi の import を塞ぐ(「無い時」の試験)。"""
    for name in list(sys.modules):
        if name == "pygments" or name.startswith("pygments.") or name == "jedi" or name.startswith("jedi."):
            monkeypatch.setitem(sys.modules, name, None)
    monkeypatch.setitem(sys.modules, "pygments", None)
    monkeypatch.setitem(sys.modules, "jedi", None)
    syn.reset_backend_cache()
    comp.reset_jedi_cache()
    yield
    monkeypatch.undo()
    syn.reset_backend_cache()
    comp.reset_jedi_cache()


# --------------------------------------------------------------------------- #
# 1. 色分け
# --------------------------------------------------------------------------- #
CATEGORY_EXAMPLES = [
    ("keyword", "if x and not y: pass", "if"),
    ("keyword", "x = None", "None"),
    ("builtin", "n = len(a)", "len"),
    ("builtin", "raise ValueError('x')", "ValueError"),
    ("string", "s = 'abc'", "'abc'"),
    ("string", "s = rb'\\d+'", "rb'\\d+'"),
    ("number", "x = 0x1F + 1_000 + 2.5e-3", "0x1F"),
    ("number", "z = 3j", "3j"),
    ("comment", "x = 1  # note", "# note"),
    ("decorator", "@np.vectorize", "@np.vectorize"),
    ("decorator", "@functools.lru_cache(maxsize=2)", "@functools.lru_cache"),
    ("def_name", "def run(a): pass", "run"),
    ("class_name", "class Foo(Base): pass", "Foo"),
    ("self", "self.x = 1", "self"),
    ("operator", "y = a // b", "//"),
    ("operator", "y = a @ b", "@"),
]


@pytest.mark.parametrize("cat,line,word", CATEGORY_EXAMPLES)
def test_category_examples(cat, line, word):
    assert (word, cat) in flat(line), flat(line)


def test_tricky_f_string_nested_and_format_spec():
    line = "s = f'v={x!r:>{w}} {{lit}} {y + 1:.2f} {d[\"k\"]}'"
    f = flat(line)
    assert ("{", "interp") in f and ("}", "interp") in f
    assert ("!r", "interp") in f and (":", "interp") in f
    assert ("1", "number") in f                       # 式の中の数は数として塗る
    assert f
    assert any(c == "string" and "{{lit}}" in w for w, c in f)  # {{ }} は文字列のまま


def test_f_string_self_documenting_equals():
    f = flat("print(f'{x=}')")
    assert ("=", "interp") in f and ("=", "operator") not in f


def test_multiline_strings_keep_state_across_lines():
    text = 'x = """a\nb # not a comment\nc""" + 1\ny = 2'
    cats = cats_of(text)
    assert cats[1] == [("b # not a comment", "string")]
    assert ("1", "number") in cats[2] and ("y", "name") not in cats[3]
    lx = syn.LineLexer("base")
    _t, st = lx.scan('x = """a', 0)
    assert st != 0
    _t, st2 = lx.scan('c"""', st)
    assert st2 == 0


def test_triple_state_distinguishes_quote_kinds_and_f():
    assert syn.state_parts(syn.state_for('"', True, False)) == ('"""', True, False)
    assert syn.state_parts(syn.state_for("'", False, True)) == ("'''", False, True)
    assert syn.state_parts(0) is None
    # ''' の中の """ は閉じない
    cats = cats_of("a = '''x\"\"\"y\nz'''")
    assert cats[0][-1][1] == "string" and cats[1] == [("z'''", "string")]


def test_hash_inside_string_is_not_a_comment():
    f = flat("x = 'a # b'  # real")
    assert ("'a # b'", "string") in f and ("# real", "comment") in f
    assert f
    assert all(c != "comment" or w == "# real" for w, c in f)


def test_decorator_vs_matmul():
    assert ("@np.vectorize", "decorator") in flat("@np.vectorize")
    assert ("@", "operator") in flat("y = a @ b") and all(c != "decorator" for _w, c in flat("y = a @ b"))


def test_match_statement_soft_keywords():
    f = flat("match command.split():\n    case [action]:\n        pass\n    case _:\n        pass")
    kws = [w for w, c in f if c == "keyword"]
    assert kws.count("match") == 1 and kws.count("case") == 2 and "_" in kws
    # 普通の名前としての match / case は keyword にしない
    assert ("match", "keyword") not in flat("match = 3\nprint(match)")
    assert ("case", "keyword") not in flat("case = 1")


def test_walrus_and_annotations():
    f = flat("if (n := len(a)) > 3:\n    v: list[int] = [i for i in range(3)]")
    assert (":=", "operator") in f
    assert ("list", "builtin") in f and ("int", "builtin") in f and ("range", "builtin") in f


def test_attribute_after_dot_is_not_builtin_or_keyword():
    f = flat("obj.print(1).id.type")
    assert f, "nothing was coloured at all"            # 色の付いた字句が 0 件なら何も確かめていない
    assert all(c != "builtin" for _w, c in f)


def test_unicode_identifiers_and_comments():
    f = flat("日本語 = 3  # コメント")
    assert ("3", "number") in f and ("# コメント", "comment") in f


def test_unterminated_string_does_not_leak_to_next_line():
    cats = cats_of("x = 'abc\ny = 2")
    assert ("2", "number") in cats[1]


def test_vocabulary_overlay_marks_ops_and_prelude():
    text = "out = gaussian(img, a=0.4)\nfs.ledger.dem_slope(x)\nobj.gaussian\nshow(out)"
    f = flat(text, ops={"gaussian", "dem_slope"}, prelude={"img", "show"})
    assert ("gaussian", "op") in f and ("img", "prelude") in f and ("show", "prelude") in f
    assert ("dem_slope", "op") in f            # fs.ledger. の後ろは op
    line3 = cats_of(text, ops={"gaussian"})[2]
    assert ("gaussian", "op") not in line3     # obj.gaussian は属性


def test_bracket_matching_and_unmatched():
    lines = ["f(a, [1, 2]", "  ", "x = ]"]
    br = []
    lx = syn.LineLexer("base")
    st = 0
    for ln in lines:
        toks, st = lx.scan(ln, st)
        br.append(syn.brackets_of(toks, ln))
    pairs, bad = syn.match_brackets(br)
    assert pairs[(0, 5)] == (0, 10) and pairs[(0, 10)] == (0, 5)
    assert (2, 4) in bad                        # 余分な ]
    assert (0, 1) in bad                        # ( が閉じていない
    pairs2, bad2 = syn.match_brackets([[(0, "("), (3, ")")], [(0, "["), (1, ")")]])
    assert pairs2[(0, 0)] == (0, 3) and (1, 1) in bad2 and (1, 0) in bad2        # 種類違いは両方が対応なし
    # 文字列の中の括弧は数えない
    toks, _ = lx.scan("x = '(' + ')'", 0)
    assert syn.brackets_of(toks, "x = '(' + ')'") == []


def test_occurrences_skip_strings_and_comments():
    line = "x = x + 1  # x"
    lx = syn.LineLexer("base")
    toks, _ = lx.scan(line, 0)
    assert syn.occurrences(toks, line, "x") == [(0, 1), (4, 5)]
    assert syn.name_at(toks, line, 1) == "x"


@pytest.mark.parametrize("src", [
    "import numpy as np", "@np.vectorize", "class Foo(Base):", "def __init__(self, x: int = 3, *a, **k) -> None:",
    "def f(a, b=2.5e-3, c=0x1F, d=1_000, e=3j):", "x = 'a # b'  # c", "z = f'v={x!r:>{w}} {{l}} {y + 1:.2f}'",
    "w = f\"{a['k']} and {b}\"", "if (n := len(a)) > 3 and not b or c is None:", "match c.split():",
    "    case _:", "v: list[int] = [i for i in range(10)]", "lam = lambda q, *r: q @ r ** 2 // 3", "obj.print(1).id",
    "print(...)", "async def g(): await x", "a <<= 2; b |= c; d != e", "日本語 = 3  # コメント", "x = ~a + -b",
    "print(f'{x=}')", "x = 'unterminated", "exec('c'); __name__ == '__main__'", "x = 1if y else 2",
    "x = '''a\nb''' + \"\"\"c\nd\"\"\"", "s = rf'''\\d{x}\n{y}'''",
])
def test_base_and_pygments_agree(src):
    if not syn.pygments_available():
        pytest.skip("pygments が無い")
    assert char_cats(src, "base") == char_cats(src, "pygments")


def test_base_and_pygments_agree_on_real_files():
    if not syn.pygments_available():
        pytest.skip("pygments が無い")
    import textwrap
    import json.decoder as jd
    for mod in (textwrap, jd):
        text = open(mod.__file__, encoding="utf-8").read()
        a, b = char_cats(text, "base"), char_cats(text, "pygments")
        lines = text.split("\n")
        diffs = [(n + 1, lines[n]) for n in range(len(lines)) if a[n] != b[n]]
        assert not diffs, diffs[:3]


def test_scanner_matches_tokenize_on_real_files():
    """標準の tokenize を答えとして、コメント・数・文字列の位置が一致する。"""
    import textwrap
    import json.decoder as jd
    for mod in (textwrap, jd):
        text = open(mod.__file__, encoding="utf-8").read()
        lines = text.split("\n")
        cc = char_cats(text, "base")
        expect_comment, expect_number, in_string = set(), set(), set()
        f_string_chars = set()
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            (sr, sc), (er, ec) = tok.start, tok.end
            if tok.type == tokenize.COMMENT:
                expect_comment.update((sr - 1, c) for c in range(sc, ec))
            elif tok.type == tokenize.NUMBER:
                expect_number.update((sr - 1, c) for c in range(sc, ec))
            elif tok.type == tokenize.STRING:
                is_f = bool(re.match(r"[rRbBuU]*[fF]", tok.string))
                for r in range(sr, er + 1):
                    a = sc if r == sr else 0
                    b = ec if r == er else len(lines[r - 1])
                    for c in range(a, b):
                        (f_string_chars if is_f else in_string).add((r - 1, c))
        got_comment = {(r, c) for r, row in enumerate(cc) for c, k in enumerate(row) if k == "comment"}
        got_number = {(r, c) for r, row in enumerate(cc) for c, k in enumerate(row) if k == "number"}
        got_string = {(r, c) for r, row in enumerate(cc) for c, k in enumerate(row) if k == "string"}
        ws = {(r, c) for r, ln in enumerate(lines) for c, ch in enumerate(ln) if ch.isspace()}
        assert got_comment == expect_comment - ws
        assert got_number == expect_number - ws
        assert (in_string - ws) <= got_string          # 普通の文字列は全部 string
        assert not ((got_string - in_string - f_string_chars) - ws)    # string は文字列の字句の中だけ


def test_pygments_absent_falls_back_to_base(no_optional):
    lx = syn.LineLexer("auto")
    assert lx.active == "base" and not syn.pygments_available()
    assert ("if", "keyword") in flat("if x: pass", "auto")
    # backend="pygments" を明示しても、無ければ土台で動く(落ちない)
    assert ("if", "keyword") in flat("if x: pass", "pygments")


def test_backend_argument_is_validated():
    with pytest.raises(ValueError):
        syn.LineLexer("nope")
    with pytest.raises(ValueError):
        syn.theme_by_name("sepia")


@pytest.mark.parametrize("name", ["dark", "light"])
def test_theme_contrast_at_least_4_5(name):
    th = syn.theme_by_name(name)
    rows = syn.contrast_report(th)
    low = [r for r in rows if r[1] < syn.MIN_CONTRAST]
    assert not low, low[:5]
    assert set(th.styles) >= set(syn.CATEGORIES)


def test_contrast_ratio_known_values():
    assert syn.contrast_ratio("#000000", "#ffffff") == pytest.approx(21.0)
    assert syn.contrast_ratio("#777777", "#777777") == pytest.approx(1.0)
    with pytest.raises(ValueError):
        syn.contrast_ratio("red", "#fff")


@pytest.mark.parametrize("name", ["dark", "light"])
def test_theme_does_not_rely_on_color_alone(name):
    th = syn.theme_by_name(name)
    assert th.style("keyword").bold and th.style("comment").italic and th.style("class_name").underline
    colors = [th.style(c).color for c in ("keyword", "builtin", "string", "number", "comment", "decorator", "op", "prelude")]
    assert len(set(colors)) == len(colors)


# --------------------------------------------------------------------------- #
# 2. 補完
# --------------------------------------------------------------------------- #
def _catalog():
    P = comp.ParamInfo
    return comp.StaticOpCatalog([
        comp.OpInfo("gaussian", "Gaussian smoothing.", ("image",), "image",
                    (P("image", "image", "input: image"), P("a", "a=0.5", "a · blur σ · 0.3..3 px", "keyword"),
                     P("b", "b=0.5", "b · border handling · reflect|nearest", "keyword"))),
        comp.OpInfo("gauss_filter", "HALCON-style gauss.", ("image",), "image", (P("image", "image"),)),
        comp.OpInfo("otsu", "Otsu threshold.", ("image",), "region", (P("image", "image"),)),
        comp.OpInfo("sobel_mag", "Sobel magnitude.", ("image",), "image", (P("image", "image"),)),
        comp.OpInfo("dem_slope", "Slope of a DEM.", ("depth",), "image",
                    (P("dem", "dem"), P("cell_size", "cell_size"), P("method", "method='horn'", "", "keyword")), "ledger"),
    ])


class _Files:
    def files(self, kind):
        return {"pipeline": ["edge.json", "blur.json"], "params": ["cal.yaml"], "image": ["a.png"]}.get(kind, [])


def provider(ns=None, use_jedi=False, files=None, tr=None):
    return comp.default_provider(namespace=ns, catalog=_catalog(), project_files=files, use_jedi=use_jedi,
                                 tr=tr or (lambda s: s))


def names(items):
    return [c.name for c in items]


def at_end(p, text):
    lines = text.split("\n")
    return p.complete(text, len(lines) - 1, len(lines[-1]))


def test_complete_op_prefix_exact_first():
    r = at_end(provider(), "gaus")
    assert names(r)[:2] == ["gaussian", "gauss_filter"]          # 短い方(完全に近い方)が先
    assert r[0].kind == "op" and "image -> image" in r[0].detail and "Gaussian" in r[0].detail
    assert "input -> output" in r[0].doc and "blur σ" in r[0].doc


def test_complete_ranking_prefix_then_substring_then_fuzzy():
    cands = [comp.Completion(n, "variable") for n in ("sigma_x", "my_sigma", "sgm", "other")]
    r = names(comp.rank(cands, "sig"))
    assert r[:2] == ["sigma_x", "my_sigma"]
    assert "other" not in r
    assert comp.match_tier("sgm", "sg") == 1 and comp.match_tier("gauss_filter", "gf") == 5
    assert comp.match_tier("abc", "z") is None
    r2 = names(comp.rank([comp.Completion(n, "variable") for n in ("a_xyz", "xyz_b")], "xyz"))
    assert r2 == ["xyz_b", "a_xyz"]


def test_usage_makes_frequent_names_rise():
    u = comp.UsageStats()
    cands = [comp.Completion("alpha", "variable"), comp.Completion("alpine", "variable")]
    assert names(comp.rank(cands, "alp"))[0] == "alpha"
    for _ in range(5):
        u.bump("alpine")
    assert names(comp.rank(cands, "alp", u))[0] == "alpine"
    assert comp.UsageStats.from_dict(u.to_dict()).get("alpine") == 5


def test_complete_in_text_names_and_defs():
    text = "def my_func(a, b=2):\n    pass\nmy_value = 3\nmy_"
    r = at_end(provider(), text)
    assert {"my_func", "my_value"} <= set(names(r))
    kinds = {c.name: c.kind for c in r}
    assert kinds["my_func"] == "function" and kinds["my_value"] == "variable"


def test_op_functions_in_the_namespace_do_not_duplicate_the_op_candidate():
    p = provider(ns={"gaussian": lambda x: x, "img": np.zeros((4, 4))})
    r = [c for c in at_end(p, "gaus") if c.name == "gaussian"]
    assert len(r) == 1 and r[0].kind == "op"


def test_complete_prelude_namespace_and_keywords_and_snippets():
    p = provider(ns={"result": np.zeros((4, 4)), "img": np.zeros((4, 4))})
    assert "result" in names(at_end(p, "res"))
    assert "show" in names(at_end(p, "sho"))
    r = at_end(p, "for")
    assert ("for", "keyword") in [(c.name, c.kind) for c in r] and ("for", "snippet") in [(c.name, c.kind) for c in r]
    pipe = [c for c in at_end(p, "pip") if c.kind == "snippet"]
    assert pipe and "show(result" in pipe[0].insert and pipe[0].cursor_offset is not None
    assert pipe[0].detail                                           # 説明つき


def test_complete_attribute_of_module_and_runtime_value():
    p = provider(ns={"np": np, "img": np.zeros((4, 4))})
    assert "zeros" in names(at_end(p, "np.zer"))
    r = at_end(p, "img.sh")
    assert "shape" in names(r) and all(c.kind != "op" for c in r)
    assert "linalg" in names(at_end(p, "np.lin"))
    # 受け手を特定できないとき(呼び出しの戻り値)は何も出さない
    assert at_end(p, "foo().") == []


def test_complete_fs_ledger_names_are_ops():
    import types
    fake_fs = types.SimpleNamespace(ledger=types.SimpleNamespace(dem_slope=lambda: 1, other=lambda: 2))
    p = provider(ns={"fs": fake_fs})
    r = at_end(p, "fs.ledger.dem_s")
    assert names(r)[0] == "dem_slope" and r[0].kind == "op"


def test_complete_keyword_arguments():
    p = provider(ns={"img": np.zeros((4, 4))})
    r = at_end(p, "x = gaussian(img, sig")
    assert "sigma=" not in names(r)                # gaussian のつまみは a / b
    r = at_end(p, "x = gaussian(img, a=0.3, ")
    ps = [c for c in r if c.kind == "param"]
    assert [c.name for c in ps] == ["b="]          # 使った a= は出ない
    assert ps[0].detail.startswith("b ·")
    r = at_end(p, "x = gaussian(img, ")
    assert names([c for c in r if c.kind == "param"]) == ["a=", "b="]
    # 自分の関数の引数名
    text = "def blur(img, sigma=1.0, mode='x'):\n    pass\nblur(img, sig"
    assert "sigma=" in names(at_end(p, text))
    # ledger op の引数名
    r = at_end(p, "dem_slope(dem, cell_size=1.0, me")
    assert "method=" in names(r)
    # 入れ子の括弧の中では引数名を出さない
    assert not [c for c in at_end(p, "gaussian([img, ") if c.kind == "param"]


def test_complete_imports():
    p = provider()
    assert "numpy" in names(at_end(p, "import nump"))
    assert "os" in names(at_end(p, "from o"))
    assert "linspace" in names(at_end(p, "import numpy\nfrom numpy import linsp"))
    # 未 import のモジュールの名前は勝手に import して調べない
    assert at_end(p, "from definitely_not_imported_mod import ") == []
    r = p.complete("import ", 0, 7)
    assert r and all(c.kind == "module" for c in r)


def test_complete_file_names_in_strings(tmp_path):
    p = provider(files=_Files())
    r = at_end(p, 'steps = load_pipeline("')
    assert sorted(names(r)) == ["blur", "edge"] and all(c.kind == "file" for c in r)
    assert names(at_end(p, 'steps = load_pipeline("ed')) == ["edge"]
    assert at_end(p, 'x = "ed') == []                                          # 関係ない文字列には出さない
    assert names(at_end(p, 'load_params("c')) == ["cal"]
    # プロジェクトが無ければ出さない
    assert at_end(provider(files=None), 'load_pipeline("') == []
    # 実フォルダ
    root = tmp_path
    (root / "pipelines").mkdir()
    (root / "pipelines" / "p1.json").write_text("{}")
    (root / "pipelines" / "note.txt").write_text("x")
    dp = comp.DirectoryProjectFiles(str(root))
    assert dp.files("pipeline") == ["p1.json"] and dp.files("image") == []


def test_complete_must_not_offer_in_comments_or_when_naming():
    p = provider()
    assert at_end(p, "# gaus") == []
    assert at_end(p, "def gau") == []
    assert at_end(p, "class Gau") == []
    assert at_end(p, "x = 3.") == []


def test_complete_after_triple_quote_is_string():
    p = provider()
    assert at_end(p, 'x = """\ngaus') == []


def test_complete_works_without_jedi(no_optional):
    p = provider(ns={"np": np}, use_jedi=True)          # jedi を要求しても無ければ自前だけ
    assert not comp.jedi_available()
    assert "gaussian" in names(at_end(p, "gaus"))
    assert "zeros" in names(at_end(p, "np.zer"))


def test_complete_with_jedi_adds_general_python():
    if not comp.jedi_available():
        pytest.skip("jedi が無い")
    p = provider(ns={"np": np}, use_jedi=True)
    r = at_end(p, "import os\nos.pa")
    assert "path" in names(r)
    r = at_end(p, "x = [1, 2]\nx.app")
    assert "append" in names(r)
    # op は自前のまま
    r = at_end(p, "gaus")
    assert r[0].name == "gaussian" and r[0].kind == "op"


def test_complete_line_base_adapter():
    class One:
        def complete(self, text, line, col):
            assert line == 3 and col == 2
            return [comp.Completion("zz", "variable")]
    assert names(comp.LineBase(One(), 1).complete("a\nb\nc\nxy", 2, 2)) == ["zz"]


def test_completion_kind_is_validated():
    with pytest.raises(ValueError):
        comp.Completion("x", "bogus")


def test_auto_trigger_rules():
    assert comp.auto_trigger("np.", ".") == "dot"
    assert comp.auto_trigger("x = 3.", ".") is None
    assert comp.auto_trigger("f(", "(") == "paren"
    assert comp.auto_trigger("import ", " ") == "import"
    assert comp.auto_trigger("from os import ", " ") == "import"
    assert comp.auto_trigger("x = ", " ") is None
    assert comp.auto_trigger("g", "g") is None and comp.auto_trigger("ga", "a") == "word"


def test_complete_speed_without_jedi():
    p = provider(ns={"np": np})
    big = "\n".join("v%d = %d" % (i, i) for i in range(3000)) + "\nv2"
    at_end(p, big)
    t = time.perf_counter()
    for _ in range(5):
        r = at_end(p, big)
    ms = (time.perf_counter() - t) / 5 * 1000
    assert ms < 400, ms


# --------------------------------------------------------------------------- #
# 3. シグネチャとホバー
# --------------------------------------------------------------------------- #
def test_signature_for_op_with_knob_meaning():
    p = provider()
    sig, active = p.signature("x = gaussian(img, ", 0, 18)
    assert sig.name == "gaussian" and [q.name for q in sig.params] == ["image", "a", "b"]
    assert active == 1                                    # 1 つ目を渡した後 = 位置 1(a)
    assert "blur σ" in sig.params[1].doc and "px" in sig.params[1].doc
    bold = [s for s, b in sig.segments(active) if b]
    assert bold == ["a=0.5"]
    sig2, active2 = p.signature("x = gaussian(img, b=", 0, 20)
    assert active2 == 2


def test_signature_user_function_and_nesting():
    p = provider()
    text = "def foo(a, b=3, *rest):\n    pass\nfoo(1, bar(2), "
    sig, active = p.signature(text, 2, len("foo(1, bar(2), "))
    assert sig.name == "foo" and active == 2
    # 内側の呼び出し
    text2 = "foo(1, bar(2, "
    assert p.signature(text2, 0, len(text2)) is None             # 内側は未知の bar(foo ではない)
    assert p.signature("print(", 0, 6)[0].name == "print"
    assert p.signature("x = 3", 0, 5) is None
    assert p.signature("f('a(', ", 0, 8) is None            # 文字列の中の括弧は数えない(f は未知)


def test_signature_of_numpy_function_uses_docstring_when_needed():
    p = provider(ns={"np": np})
    r = p.signature("np.zeros(", 0, 9)
    assert r is not None and r[0].params[0].name == "shape"


def test_call_context_multiline_and_kwargs():
    text = "gaussian(\n    img,\n    a=0.2,\n    "
    lines = text.split("\n")
    ctx = comp.call_context(lines, 3, 4)
    assert ctx.callee == "gaussian" and ctx.n_positional == 1 and ctx.used_kwargs == {"a"} and ctx.innermost


def test_hover_for_op_and_prelude():
    p = provider()
    h = p.hover("out = gaussian(img)", 0, 8)
    assert h is not None and "gaussian(" in h.title and h.body == "Gaussian smoothing."
    h2 = p.hover("show(img)", 0, 2)
    assert h2 is not None and "show" in h2.title
    assert p.hover("x = 3", 0, 4) is None


# --------------------------------------------------------------------------- #
# 4. 変数の要約・木・印・編集
# --------------------------------------------------------------------------- #
class _Bad:
    def __repr__(self):
        raise RuntimeError("boom")


class _Slow:
    def __repr__(self):
        while True:
            pass


class _Huge:
    def __repr__(self):
        return "x" * 5_000_000


class _Plain:
    def __init__(self):
        self.a = 1
        self._hidden = 2
        self.items = [1, 2]

    @property
    def danger(self):
        raise AssertionError("property must not be called")


class _Slots:
    __slots__ = ("p", "q")

    def __init__(self):
        self.p = 3


def test_summary_scalars_and_arrays():
    assert V.summarize(3).text == "3" and V.summarize(3).editable
    assert V.summarize(0.5).kind == "float" and V.summarize(None).text == "None"
    s = V.summarize(np.arange(12.0).reshape(3, 4))
    assert s.shape == (3, 4) and s.dtype == "float64" and "[0 .. 11]" in s.text and "mean 5.5" in s.text
    s = V.summarize(np.array([1.0, np.nan, np.inf]))
    assert "non-finite" in s.text and "[1 .. 1]" in s.text
    s = V.summarize(np.zeros(3, dtype=[("a", "f4"), ("b", "i4")]))
    assert s.expandable and "a, b" in s.text
    assert V.summarize("x" * 1000).text.endswith("…") and len(V.summarize("x" * 1000).text) <= 100
    assert V.summarize(list(range(10))).text.startswith("list[10] [0, 1, 2, 3, …")
    assert V.summarize(np.float32(3.5)).editable


def test_summary_huge_array_does_not_scan_everything():
    huge = np.broadcast_to(np.arange(10.0), (10**7, 10))        # 1 億要素(メモリ上は 80 バイト)
    t = time.perf_counter()
    s = V.summarize(huge)
    assert time.perf_counter() - t < 1.0
    assert s.sampled and "≈" in s.text and s.shape == (10**7, 10)


def test_summary_hostile_reprs_never_hang_or_raise():
    t = time.perf_counter()
    s_bad = V.summarize(_Bad())
    s_slow = V.summarize(_Slow())
    s_slow2 = V.summarize(_Slow())
    s_huge = V.summarize(_Huge())
    assert time.perf_counter() - t < 2.0
    assert s_bad.problem == "repr_failed" and "boom" in s_bad.text
    assert s_slow.problem == "repr_timeout"
    assert len(s_huge.text) <= 100
    assert V.summarize(_Plain()).text.endswith("_Plain object>")      # 標準の repr は呼ばずに作る


def test_summary_cycles_and_deep_nesting():
    a = []
    a.append(a)
    d = {}
    d["self"] = d
    deep = cur = []
    for _ in range(20000):
        n = []
        cur.append(n)
        cur = n
    for v in (a, d, deep):
        t = time.perf_counter()
        s = V.summarize(v)
        fp = V.fingerprint(v)
        assert time.perf_counter() - t < 0.5 and s.text and fp
    ch = V.children(a, ancestors=())
    assert ch[0].cycle
    ch = V.children(d)
    assert ch[0].cycle


def test_children_never_call_properties_and_hide_private():
    obj = _Plain()
    ch = V.children(obj)
    assert {c.label for c in ch} == {"a", "items"}              # _hidden と property は出ない
    assert [c.label for c in V.children(obj, include_private=True) if c.label == "_hidden"]
    sl = V.children(_Slots())
    assert [c.label for c in sl] == ["p"]                       # 未設定の q は出ない
    # 明示で選んだ時だけ property を読む(失敗は理由つきで返し、落ちない)
    ex = V.children(obj, explicit_attrs=["danger"])
    d = [c for c in ex if c.label == "danger"][0]
    assert "AssertionError" in d.note or "could not read" in d.note
    assert "danger" in V.candidate_attributes(obj)


def test_children_of_containers_and_structured_arrays():
    ch = V.children({"a": 1, "b": [1, 2]})
    assert [c.step for c in ch] == [("item", "a"), ("item", "b")]
    big = list(range(1000))
    ch = V.children(big, limits=V.Limits(max_children=10))
    assert len(ch) == 11 and ch[-1].step is None and ch[-1].more == 990
    sa = np.zeros(2, dtype=[("x", "f4"), ("y", "i4")])
    assert [c.step for c in V.children(sa)] == [("field", "x"), ("field", "y")]
    nt = __import__("collections").namedtuple("P", "x y")(1, 2)
    assert [c.label for c in V.children(nt)] == ["x", "y"]


def test_tracker_new_changed_removed():
    tr = V.VariableTracker()
    ns = {"a": 1, "b": [1, 2], "img": np.zeros((4, 4))}
    tr.begin()
    assert all(tr.status((("name", k),), v) == "same" for k, v in ns.items())      # 最初の停止は印なし
    ns2 = {"a": 2, "b": [1, 2], "img": np.ones((4, 4)), "c": 5}
    tr.begin()
    st = {k: tr.status((("name", k),), v) for k, v in ns2.items()}
    assert st == {"a": "changed", "b": "same", "img": "changed", "c": "new"}
    ns2["b"].append(3)                                       # その場の変更も検知
    tr.begin()
    ns3 = {k: v for k, v in ns2.items() if k != "a"}
    st = {k: tr.status((("name", k),), v) for k, v in ns3.items()}
    assert st["b"] == "changed" and st["c"] == "same"
    assert tr.removed() == ["a"]


def test_tracker_children_of_a_collapsed_parent_are_not_marked_new():
    tr = V.VariableTracker()
    path = (("name", "d"),)
    tr.begin()
    tr.status(path, {"a": 1})                                     # 親だけ(展開していない)
    tr.begin()
    tr.status(path, {"a": 1})
    assert tr.status(path + (("item", "a"),), 1) == "same"        # 初めて展開した子を「新しい」としない
    tr.begin()
    tr.status(path, {"a": 1, "b": 2})
    assert tr.status(path + (("item", "a"),), 1) == "same"
    assert tr.status(path + (("item", "b"),), 2) == "new"         # 前に展開していた親に増えた子は新しい
    tr.begin()
    tr.status(path, {"a": 1, "b": 2, "c": 3})
    assert tr.status(path + (("item", "a"),), 1) == "same"
    assert tr.status(path + (("item", "c"),), 3) == "new"


def test_filter_entries_by_name_and_type():
    ents = [V.Entry(n, v, V.summarize(v)) for n, v in
            [("img", np.zeros((9, 9))), ("count", 3), ("name", "x"), ("_p", 1), ("np", np)]]
    assert [e.name for e in V.filter_entries(ents, "")] == ["img", "count", "name"]     # _ と module は既定で隠す
    assert [e.name for e in V.filter_entries(ents, "ndarray")] == ["img"]
    assert [e.name for e in V.filter_entries(ents, "type:int")] == ["count"]
    assert [e.name for e in V.filter_entries(ents, "name:na")] == ["name"]
    assert "np" in [e.name for e in V.filter_entries(ents, "", show_callables=True)]


def test_image_like_and_thumbnail():
    assert V.is_image_like(np.zeros((16, 16))) and V.is_image_like(np.zeros((16, 16, 3), np.uint8))
    assert V.is_image_like(np.zeros((16, 16, 4))) and not V.is_image_like(np.zeros((3, 3)))
    assert not V.is_image_like(np.zeros((16, 16, 5))) and not V.is_image_like(np.zeros(100))
    a = np.linspace(0, 1, 256 * 256).reshape(256, 256)
    t = V.thumbnail_u8(a, 32)
    assert t.dtype == np.uint8 and max(t.shape) <= 64 and t.min() == 0 and t.max() >= 250
    rgba = np.random.rand(40, 40, 4)
    assert V.thumbnail_u8(rgba, 16).shape[2] == 3
    nan = np.full((16, 16), np.nan)
    assert V.thumbnail_u8(nan, 8).max() == 128
    big = np.broadcast_to(np.arange(1000.0), (100000, 1000))
    t0 = time.perf_counter()
    V.thumbnail_u8(big, 48)
    assert time.perf_counter() - t0 < 0.5


@pytest.mark.parametrize("text,cur,expect", [
    ("12", 3, 12), ("0x10", 3, 16), ("true", False, True), ("0", True, False), ("1e3", 2.0, 1000.0),
    ("'hi'", "a", "hi"), ("hello", "a", "hello"), ("7", np.int16(1), np.int16(7)), ("2.5", np.float32(1), np.float32(2.5)),
])
def test_parse_edit_accepts(text, cur, expect):
    v = V.parse_edit(text, cur)
    assert v == expect and type(v) is type(expect)


@pytest.mark.parametrize("text,cur", [("abc", 3), ("3.5", 3), ("maybe", True), ("x", 1.5), ("300", np.uint8(1)),
                                      ("[1]", [1]), ("1", None)])
def test_parse_edit_rejects_with_reason(text, cur):
    with pytest.raises(V.EditError) as ei:
        V.parse_edit(text, cur)
    assert str(ei.value)


def test_parse_edit_messages_are_translated():
    tr = i18n.make_tr("ja")
    with pytest.raises(V.EditError) as ei:
        V.parse_edit("abc", 3, tr)
    assert _CJK.search(str(ei.value))


def test_assign_path_and_expression():
    ns = {"cfg": {"k": 1, "l": [1, 2]}, "o": _Plain()}
    src = V.DictSource(ns)
    src.set_value((("name", "cfg"), ("item", "k")), 5)
    src.set_value((("name", "cfg"), ("item", "l"), ("item", 1)), 9)
    src.set_value((("name", "o"), ("attr", "a")), 7)
    assert ns["cfg"]["k"] == 5 and ns["cfg"]["l"] == [1, 9] and ns["o"].a == 7
    with pytest.raises(V.EditError):
        src.set_value((("name", "o"), ("attr", "danger")), 1)      # プロパティへは書かない
    with pytest.raises(V.EditError):
        src.set_value((("name", "t"), ("item", 0)), 1)
    assert V.path_to_expression((("name", "cfg"), ("item", "l"), ("item", 1))) == "cfg['l'][1]"
    assert V.path_to_expression((("name", "o"), ("attr", "a"))) == "o.a"
    assert V.resolve_path(ns, (("name", "cfg"), ("item", "k"))) == 5


# --------------------------------------------------------------------------- #
# 5. ウォッチ
# --------------------------------------------------------------------------- #
def test_watch_evaluation_results_errors_and_timeout():
    ns = {"x": np.arange(5), "y": 3, "img": np.random.rand(32, 32)}
    ev = V.WatchEvaluator(ns, timeout_s=0.2)
    r = ev.evaluate("x.mean() + y")
    assert r.ok and r.value == 5.0
    r = ev.evaluate("nope + 1")
    assert not r.ok and "NameError" in r.error
    r = ev.evaluate("y +")
    assert not r.ok and "syntax" in r.error
    r = ev.evaluate("   ")
    assert not r.ok and r.error
    t = time.perf_counter()
    r = ev.evaluate("[i for i in iter(int, 1)]")                   # 終わらない式
    assert time.perf_counter() - t < 1.5 and r.timed_out and "timed out" in r.error
    r = ev.evaluate("img * 2")
    assert r.ok and r.summary.is_image
    assert ns == {"x": ns["x"], "y": 3, "img": ns["img"]}           # 名前空間を汚さない(walrus など)
    ev.evaluate("(zz := 5)")
    assert "zz" not in ns


def test_watch_changed_flag_and_condition():
    ns = {"v": 1}
    ev = V.WatchEvaluator(lambda: ns)
    assert not ev.evaluate("v").changed
    assert not ev.evaluate("v").changed
    ns["v"] = 2
    assert ev.evaluate("v").changed
    c = ev.condition("v > 1")
    assert c.ok and c.hit
    assert ev.condition("v > 5").hit is False
    ns["arr"] = np.arange(3)
    c = ev.condition("arr")
    assert not c.ok and "ambiguous" in c.error                    # 曖昧な真偽は止めずに理由を返す
    c = ev.condition("undefined_name")
    assert not c.ok and "NameError" in c.error


def test_watch_list_roundtrip_and_validation():
    w = V.WatchList(["a", "b", "c"])
    assert w.add("b") == 1 and len(w.exprs) == 3
    w.move(2, 0)
    assert w.exprs == ["c", "a", "b"]
    w.remove(1)
    back = V.WatchList.loads(w.dumps())
    assert back.exprs == ["c", "b"]
    for bad in ('{"fullseye_kind": "x"}', "not json", '{"fullseye_kind":"fullseye_watch","version":1,"expressions":[1]}',
                '{"fullseye_kind":"fullseye_watch","version":9,"expressions":[]}'):
        with pytest.raises(ValueError):
            V.WatchList.loads(bad)
    with pytest.raises(ValueError):
        w.add("  ")
    with pytest.raises(IndexError):
        w.move(0, 9)


# --------------------------------------------------------------------------- #
# 6. 画面の文(対訳)
# --------------------------------------------------------------------------- #
def _tr_keys_in_sources():
    keys = set()
    for fn in ("studio_pyedit_complete.py", "studio_pyedit_values.py", "studio_pyedit_qt.py", "studio_pyedit_vars_qt.py"):
        tree = ast.parse(open(os.path.join(ROOT, fn), encoding="utf-8").read())
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str):
                f = n.func
                nm = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else "")
                if nm in ("tr", "_tr"):
                    keys.add(n.args[0].value)
    return keys


def test_translation_table_is_complete_for_all_six_languages():
    tab = i18n.load_table()
    assert i18n.missing(tab) == []
    assert i18n.LANGS == ("en", "ja", "zh", "tw", "ko", "de")
    assert len(tab) >= 20, len(tab)                    # 空の表は「欠けなし」を素通りする
    for key, row in tab.items():
        assert set(row) == {"ja", "zh", "tw", "ko", "de"}, key
        # %s / %d の数が訳でも同じ
        n = len(re.findall(r"%[sd]", key))
        for lang, txt in row.items():
            assert len(re.findall(r"%[sd]", txt)) == n, (key, lang)


def test_every_tr_call_in_the_sources_has_a_translation():
    tab = i18n.load_table()
    missing = sorted(k for k in _tr_keys_in_sources() if k not in tab)
    assert not missing, missing
    dynamic = (list(comp.KINDS) + ["image", "pipeline", "python", "params"] + [s.desc for s in comp.SNIPPETS]
               + [d for _k, d in comp.DEFAULT_PRELUDE.values()])
    assert not [k for k in dynamic if k not in tab], [k for k in dynamic if k not in tab]


def test_translation_falls_back_to_english_and_validates_language():
    tr = i18n.make_tr("ja")
    assert tr("Add") == "追加" and tr("text not in the table") == "text not in the table"
    assert i18n.make_tr("en")("Add") == "Add"
    with pytest.raises(ValueError):
        i18n.make_tr("fr")
    merged = i18n.merge_into({"strings": {"Add": {"ja": "足す"}}})
    assert merged["strings"]["Add"] == {"ja": "足す"} and "Remove" in merged["strings"]


def test_japanese_completion_texts_have_no_english_left():
    tr = i18n.make_tr("ja")
    p = provider(tr=tr, files=_Files())
    items = at_end(p, "gaus") + at_end(p, "for") + at_end(p, "sho") + at_end(p, 'load_pipeline("')
    assert items
    for c in items:
        if c.kind in ("snippet", "file") or c.name in ("show", "img"):
            assert _CJK.search(c.detail), (c.name, c.detail)


# --------------------------------------------------------------------------- #
# 7. Qt の部品(offscreen)
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def qapp():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def pump(app, ms=30):
    end = time.monotonic() + ms / 1000
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.003)


def make_editor(qapp, text="", **kw):
    import studio_pyedit_qt as Q
    ed = Q.PyEditor(kw.pop("provider", provider(ns={"img": np.zeros((8, 8)), "np": np})), kw.pop("theme", "dark"),
                    kw.pop("tr", lambda s: s))
    ed.resize(760, 420)
    ed.show()
    ed.setPlainText(text)
    pump(qapp, 20)
    return ed


def fmt_at(ed, line, col):
    from PySide6 import QtGui
    blk = ed.document().findBlockByNumber(line)
    for r in blk.layout().formats():
        if r.start <= col < r.start + r.length:
            return QtGui.QTextCharFormat(r.format)
    return None


def test_highlighter_formats_and_theme_switch(qapp):
    ed = make_editor(qapp, "def f(x):\n    return len(x)  # c\n")
    kw = fmt_at(ed, 0, 0)
    assert kw is not None and kw.fontWeight() == 700                      # def は太字
    assert kw.foreground().color().name() == syn.THEMES["dark"].style("keyword").color
    cm = fmt_at(ed, 1, 20)
    assert cm.fontItalic()
    ed.assist.set_theme("light")
    pump(qapp, 20)
    assert fmt_at(ed, 0, 0).foreground().color().name() == syn.THEMES["light"].style("keyword").color
    assert "#fbfbfd" in ed.styleSheet()


def test_highlighter_multiline_string_state_follows_edits(qapp):
    ed = make_editor(qapp, 'a = 1\nb = """x\ny = 2\n"""\nc = 3\n')
    assert fmt_at(ed, 2, 0).foreground().color().name() == syn.THEMES["dark"].style("string").color
    cur = ed.textCursor()
    cur.setPosition(ed.document().findBlockByNumber(1).position() + 4)
    cur.deleteChar(); cur.deleteChar(); cur.deleteChar()                    # 開きの """ を消す
    pump(qapp, 20)
    f = fmt_at(ed, 2, 0)
    assert f is None or f.foreground().color().name() != syn.THEMES["dark"].style("string").color
    assert ed.document().findBlockByNumber(4).userState() > 0          # 残りの """ が新しい開きになる


def test_marks_errors_breakpoints_and_brackets_become_selections(qapp):
    ed = make_editor(qapp, "x = (1 + 2\ny = foo(3)\nz = 4\n")
    ed.assist.set_errors({3: "unknown op"})
    ed.assist.set_breakpoints({2})
    ed.assist.set_executing(1)
    ed.assist.refresh_decorations()
    sels = ed.extraSelections()
    waves = [s for s in sels if s.format.underlineStyle() == s.format.UnderlineStyle.WaveUnderline]
    assert len(waves) >= 2                                              # エラーの行の波線 + 対応の無い括弧
    assert any(abs(s.format.underlineColor().red() - 255) < 5 for s in waves)
    bgs = {s.format.background().color().name() for s in sels if s.format.background().style() != 0}
    th = syn.THEMES["dark"]
    assert th.breakpoint_bg in bgs and th.exec_bg in bgs and th.error_bg in bgs
    # 対応する括弧の強調(カーソルを括弧の隣へ)
    cur = ed.textCursor()
    cur.setPosition(ed.document().findBlockByNumber(1).position() + 8)       # foo( の ( の右
    ed.setTextCursor(cur)
    ed.assist.refresh_decorations()
    sels = ed.extraSelections()
    assert sels, "no extra selections at all"
    assert any(s.format.background().color().name() == th.bracket_match_bg for s in sels)


def test_same_name_is_highlighted_under_cursor(qapp):
    ed = make_editor(qapp, "alpha = 1\nbeta = alpha + 2\nprint('alpha')\n")
    cur = ed.textCursor()
    cur.setPosition(ed.document().findBlockByNumber(1).position() + 8)
    ed.setTextCursor(cur)
    ed.assist.refresh_decorations()
    th = syn.THEMES["dark"]
    occ = [s for s in ed.extraSelections() if s.format.background().color().name() == th.occurrence_bg]
    assert len(occ) == 2 and {s.cursor.selectedText() for s in occ} == {"alpha"}        # 文字列の中は含まない


def test_completion_popup_flow_with_keys(qapp):
    from PySide6 import QtCore, QtTest
    ed = make_editor(qapp, "gaus")
    cur = ed.textCursor(); cur.movePosition(cur.MoveOperation.End); ed.setTextCursor(cur)
    ed.setFocus()
    QtTest.QTest.keyClick(ed, QtCore.Qt.Key_Space, QtCore.Qt.ControlModifier)
    pump(qapp, 20)
    pop = ed.assist.popup
    assert pop.isVisible() and pop.list.count() >= 2
    assert pop.list.item(0).data(QtCore.Qt.UserRole).name == "gaussian"
    assert "gaussian" in pop.doc.text() and "blur" in pop.doc.text()                  # 右に詳しい説明
    QtTest.QTest.keyClick(ed, QtCore.Qt.Key_Down)
    assert pop.list.currentRow() == 1
    QtTest.QTest.keyClick(ed, QtCore.Qt.Key_Up)
    QtTest.QTest.keyClick(ed, QtCore.Qt.Key_Tab)                                      # Tab で確定
    assert ed.toPlainText() == "gaussian" and not pop.isVisible()
    # Esc で閉じる
    ed.setPlainText("gaus")
    cur = ed.textCursor(); cur.movePosition(cur.MoveOperation.End); ed.setTextCursor(cur)
    QtTest.QTest.keyClick(ed, QtCore.Qt.Key_Space, QtCore.Qt.ControlModifier)
    assert pop.isVisible()
    QtTest.QTest.keyClick(ed, QtCore.Qt.Key_Escape)
    assert not pop.isVisible() and ed.toPlainText() == "gaus"


def test_typing_dot_and_paren_and_snippet_accept(qapp):
    from PySide6 import QtCore, QtTest
    ed = make_editor(qapp, "")
    ed.setFocus()
    QtTest.QTest.keyClicks(ed, "np.zer")
    pump(qapp, 30)
    pop = ed.assist.popup
    assert pop.isVisible() and pop.list.item(0).data(QtCore.Qt.UserRole).name == "zeros"
    QtTest.QTest.keyClick(ed, QtCore.Qt.Key_Return)
    assert ed.toPlainText() == "np.zeros"
    QtTest.QTest.keyClicks(ed, "(")
    pump(qapp, 80)
    assert ed.assist.tip.isVisible() and "shape" in ed.assist.tip.label.text()
    # スニペット: インデントを引き継ぎ、カーソルが $0 の位置へ
    ed.setPlainText("if x:\n    for")
    cur = ed.textCursor(); cur.movePosition(cur.MoveOperation.End); ed.setTextCursor(cur)
    ed.assist.show_completions(force=True)
    pop = ed.assist.popup
    row = [i for i in range(pop.list.count()) if pop.list.item(i).data(QtCore.Qt.UserRole).kind == "snippet"][0]
    pop.list.setCurrentRow(row)
    ed.assist.accept_completion(pop.current())
    assert ed.toPlainText() == "if x:\n    for i in range():\n        pass"
    assert ed.textCursor().positionInBlock() == len("    for i in range(")


def test_signature_tip_bolds_current_param(qapp):
    import studio_pyedit_qt as Q
    ed = make_editor(qapp, "x = gaussian(img, ")
    cur = ed.textCursor(); cur.movePosition(cur.MoveOperation.End); ed.setTextCursor(cur)
    ed.assist.update_signature()
    tip = ed.assist.tip
    assert tip.isVisible()
    html = tip.label.text()
    assert "<b" in html and "a=0.5" in html and "blur σ" in html
    ed.setPlainText("x = 3")
    ed.assist.update_signature()
    assert not tip.isVisible()


def test_hover_tooltip_for_error_and_op(qapp):
    from PySide6 import QtCore, QtGui, QtWidgets
    ed = make_editor(qapp, "out = gaussian(img)\nbad = 1\n")
    ed.assist.set_errors({2: "unknown op"})
    pos = ed.cursorRect(ed.textCursorAt(1, 2) if hasattr(ed, "textCursorAt") else ed.textCursor()).center()
    c = ed.textCursor(); c.setPosition(ed.document().findBlockByNumber(1).position() + 2)
    pos = ed.cursorRect(c).center()
    ev = QtGui.QHelpEvent(QtCore.QEvent.ToolTip, pos, ed.viewport().mapToGlobal(pos))
    assert ed.assist.eventFilter(ed.viewport(), ev) is True
    assert "unknown op" in QtWidgets.QToolTip.text()
    c.setPosition(ed.document().findBlockByNumber(0).position() + 8)
    pos = ed.cursorRect(c).center()
    ev = QtGui.QHelpEvent(QtCore.QEvent.ToolTip, pos, ed.viewport().mapToGlobal(pos))
    assert ed.assist.eventFilter(ed.viewport(), ev) is True
    assert "gaussian(" in QtWidgets.QToolTip.text()


def test_gutter_click_toggles_breakpoint(qapp):
    from PySide6 import QtCore, QtGui, QtTest
    ed = make_editor(qapp, "a = 1\nb = 2\nc = 3\n")
    got = []
    ed.breakpointToggled.connect(lambda ln, on: got.append((ln, on)))
    c = ed.textCursor(); c.setPosition(ed.document().findBlockByNumber(1).position())
    y = ed.cursorRect(c).center().y()
    QtTest.QTest.mouseClick(ed._gutter, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, QtCore.QPoint(8, y))
    assert got == [(2, True)] and ed.assist.marks.breakpoints == {2}
    QtTest.QTest.mouseClick(ed._gutter, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, QtCore.QPoint(8, y))
    assert got[-1] == (2, False)


def test_assist_attaches_to_an_existing_plain_editor(qapp):
    from PySide6 import QtWidgets
    import studio_pyedit_qt as Q
    plain = QtWidgets.QPlainTextEdit()
    plain.show()
    assist = Q.PyEditAssist(plain, provider(), "light")
    plain.setPlainText("import os  # x\n")
    pump(qapp, 20)
    assert fmt_at(plain, 0, 0).foreground().color().name() == syn.THEMES["light"].style("keyword").color
    assist.external_selections = lambda: []
    assist.refresh_decorations()
    assert assist.provider is not None


def test_keystroke_redraw_time_on_5000_lines(qapp):
    """5,000 行のファイルで 1 文字打った再描画の時間(目標 16 ms)。数字は報告に書く。"""
    import studio_pyedit_qt as Q
    src = "\n".join("def f%d(a, b=2):\n    x = (a + b) * [1, 2, 3]  # c\n    s = f'v={x!r:>{b}}'\n    return gaussian(img, a=0.4)" % i
                    for i in range(1250))
    ed = make_editor(qapp, src)
    assert ed.document().blockCount() == 5000
    cur = ed.textCursor(); cur.setPosition(ed.document().findBlockByNumber(2500).position() + 5); ed.setTextCursor(cur)
    ts = []
    for _ in range(15):
        t = time.perf_counter()
        ed.textCursor().insertText("x")
        ed.assist.refresh_decorations()
        ed.viewport().repaint()
        qapp.processEvents()
        ts.append((time.perf_counter() - t) * 1000)
    med = sorted(ts)[len(ts) // 2]
    print("keystroke redraw 5000 lines: median %.1f ms, max %.1f ms" % (med, max(ts)))
    assert med < 40, ts
    # 先頭に """ を打つ(以降の全行の状態が変わる最悪の場合)
    t = time.perf_counter()
    c = ed.textCursor(); c.movePosition(c.MoveOperation.Start); c.insertText('"""')
    qapp.processEvents()
    worst = (time.perf_counter() - t) * 1000
    print("worst case (open a triple quote at the top): %.0f ms" % worst)
    assert worst < 3000


# ---- 行の高さ ----
def test_row_height_is_font_height_plus_4_everywhere(qapp):
    from PySide6 import QtWidgets
    import studio_pyedit_qt as Q
    import studio_pyedit_vars_qt as VQ
    assert Q.ROW_EXTRA_PX == 4 and VQ.ROW_EXTRA_PX == 4
    ns = {"a": 1, "b": [1, 2, 3], "img": np.zeros((16, 16))}
    panel = VQ.VariablesPanel(V.DictSource(ns))
    panel.resize(500, 300); panel.show()
    panel.refresh()
    pump(qapp, 20)
    want = panel.tree.fontMetrics().height() + 4
    tree = panel.tree
    for i in range(tree.topLevelItemCount()):
        assert tree.visualItemRect(tree.topLevelItem(i)).height() == want
    assert tree.row_h == want
    w = VQ.WatchPanel(ns)
    w.add_expression("a"); w.show()
    assert w.wait_idle()
    pump(qapp, 10)
    assert w.table.rowHeight(0) == w.table.fontMetrics().height() + 4
    ed = make_editor(qapp, "gaus")
    ed.assist.show_completions(force=True)
    pop = ed.assist.popup
    assert pop.list.visualItemRect(pop.list.item(0)).height() == pop.list.fontMetrics().height() + 4


# ---- 変数の一覧 ----
def make_vars(qapp, ns, tr=None, **kw):
    import studio_pyedit_vars_qt as VQ
    p = VQ.VariablesPanel(V.DictSource(ns), tr or (lambda s: s), **kw)
    p.resize(520, 360)
    p.show()
    p.refresh()
    pump(qapp, 20)
    return p


def top_items(tree):
    return {tree.topLevelItem(i).text(0).lstrip("+● "): tree.topLevelItem(i) for i in range(tree.topLevelItemCount())}


def test_variables_tree_columns_and_expansion(qapp):
    ns = {"n": 3, "cfg": {"k": [1, 2], "name": "x"}, "img": np.random.rand(40, 50), "o": _Plain()}
    p = make_vars(qapp, ns)
    items = top_items(p.tree)
    assert set(items) == {"n", "cfg", "img", "o"}
    assert items["img"].text(1) == "ndarray" and items["img"].text(2) == "40×50" and "mean" in items["img"].text(3)
    assert items["cfg"].text(2) == "len 2"
    items["cfg"].setExpanded(True)
    kids = [items["cfg"].child(i).text(0) for i in range(items["cfg"].childCount())]
    assert kids == ["'k'", "'name'"]
    items["cfg"].child(0).setExpanded(True)
    assert items["cfg"].child(0).childCount() == 2
    items["o"].setExpanded(True)
    assert [items["o"].child(i).text(0) for i in range(items["o"].childCount())] == ["a", "items"]
    assert not items["img"].icon(3).isNull()                      # 画像らしい配列はサムネイル
    assert items["n"].icon(3).isNull()


def test_variables_marks_new_changed_and_removed(qapp):
    ns = {"a": 1, "b": 2, "img": np.zeros((16, 16))}
    p = make_vars(qapp, ns)
    ns["a"] = 10
    ns["c"] = 5
    del ns["b"]
    ns["img"] = np.ones((16, 16))
    p.refresh()
    items = {p.tree.topLevelItem(i).text(0): p.tree.topLevelItem(i) for i in range(p.tree.topLevelItemCount())}
    assert "● a" in items and "+ c" in items and "● img" in items and "img" not in items
    assert items["● a"].font(0).bold() and "changed" in items["● a"].toolTip(3)
    assert p.removed.isVisible() and "b" in p.removed.text()
    p.refresh()                                                   # 変化なし → 印は消える
    titles = [p.tree.topLevelItem(i).text(0) for i in range(p.tree.topLevelItemCount())]
    assert titles, "the tree is empty"                            # 行が無ければ「印が消えた」は言えない
    assert all(not t.startswith(("+", "●")) for t in titles), titles


def test_variables_filter_by_name_and_type(qapp):
    ns = {"img": np.zeros((16, 16)), "count": 3, "label": "x", "_hidden": 1}
    p = make_vars(qapp, ns)
    assert set(top_items(p.tree)) == {"img", "count", "label"}
    p.filter.setText("type:int")
    assert set(top_items(p.tree)) == {"count"}
    p.filter.setText("im")
    assert set(top_items(p.tree)) == {"img"}
    p.filter.setText("")
    p.show_all.setChecked(True)
    assert "_hidden" in top_items(p.tree)


def test_variables_empty_state_has_guidance_and_buttons(qapp):
    calls = []
    p = make_vars(qapp, {}, on_run=lambda: calls.append("run"), on_open_example=lambda: calls.append("ex"))
    assert p.stack.currentWidget() is p.empty
    assert "after the program runs" in p.empty.label.text()
    assert len(p.empty.buttons) == 2 and p.empty.buttons[0].toolTip()
    p.empty.buttons[0].click(); p.empty.buttons[1].click()
    assert calls == ["run", "ex"]
    p.source.ns["x"] = 1
    p.refresh()
    assert p.stack.currentWidget() is p.tree


def test_variables_edit_values_and_reject_wrong_types(qapp):
    ns = {"n": 3, "flag": False, "s": "a", "f": 1.5, "lst": [1, 2]}
    p = make_vars(qapp, ns)
    items = top_items(p.tree)
    errs = []
    p.tree.editRejected.connect(errs.append)
    p.tree._commit(items["n"], "42")
    assert ns["n"] == 42 and not errs
    p.tree._commit(items["n"], "abc")
    assert ns["n"] == 42 and errs and errs[-1].startswith("⚠") and p.message.isVisible()
    p.tree._commit(items["flag"], "true")
    assert ns["flag"] is True
    p.tree._commit(items["s"], "'hello'")
    assert ns["s"] == "hello"
    p.tree._commit(items["f"], "2.25")
    assert ns["f"] == 2.25
    # 配列などは編集できない
    assert not (items["lst"].flags() & __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.ItemIsEditable)
    # 供給元が拒否したら理由つきで断る
    class Refuse(V.DictSource):
        def set_value(self, path, value):
            raise PermissionError("locked")
    p.tree.source = Refuse(ns)
    p.tree._commit(items["n"], "5")
    assert "locked" in errs[-1] and ns["n"] == 42


def test_variables_context_actions_copy_watch_image(qapp):
    from PySide6 import QtWidgets
    ns = {"img": np.random.rand(20, 20), "cfg": {"k": 1}}
    p = make_vars(qapp, ns)
    got = {}
    p.imageRequested.connect(lambda n, a: got.setdefault("image", (n, a.shape)))
    p.watchRequested.connect(lambda e: got.setdefault("watch", e))
    p.inspectRequested.connect(lambda n, path, v: got.setdefault("inspect", (n, path)))
    items = top_items(p.tree)
    items["cfg"].setExpanded(True)
    child = items["cfg"].child(0)
    node = p.tree.node_of(child)
    p.tree._do("watch", node)
    assert got["watch"] == "cfg['k']"
    p.tree._do("copy_expr", node)
    assert QtWidgets.QApplication.clipboard().text() == "cfg['k']"
    p.tree._do("copy_value", p.tree.node_of(items["cfg"]))
    assert QtWidgets.QApplication.clipboard().text() == "{'k': 1}"
    p.tree._do("image", p.tree.node_of(items["img"]))
    assert got["image"] == ("img", (20, 20))
    p.tree._do("inspect", node)
    assert got["inspect"] == ("cfg['k']", (("name", "cfg"), ("item", "k")))
    p.tree.setCurrentItem(items["img"])
    assert p.preview.isVisible() and not p.preview.pixmap().isNull()
    p.tree._do("table", p.tree.node_of(items["img"]))
    p.tree._do("hist", p.tree.node_of(items["img"]))
    assert len(p.tree._windows) == 2 and all(not w.isModal() for w in p.tree._windows)
    for w in p.tree._windows:
        w.close()


def test_variables_survive_hostile_values(qapp):
    ns = {"bad": _Bad(), "slow": _Slow(), "huge": np.broadcast_to(np.arange(10.0), (10**6, 10)), "cyc": []}
    ns["cyc"].append(ns["cyc"])
    t = time.perf_counter()
    p = make_vars(qapp, ns)
    assert time.perf_counter() - t < 3.0
    items = top_items(p.tree)
    assert "repr failed" in items["bad"].text(3) and "timed out" in items["slow"].text(3)
    items["cyc"].setExpanded(True)
    assert "circular" in items["cyc"].child(0).text(3)


def test_variables_expanded_state_survives_refresh(qapp):
    ns = {"cfg": {"a": {"b": 1}}}
    p = make_vars(qapp, ns)
    it = top_items(p.tree)["cfg"]
    it.setExpanded(True)
    it.child(0).setExpanded(True)
    p.refresh()
    it = top_items(p.tree)["cfg"]
    assert it.isExpanded() and it.child(0).isExpanded()


def test_japanese_ui_has_no_english_left_in_the_panels(qapp):
    import studio_pyedit_vars_qt as VQ
    tr = i18n.make_tr("ja")
    ns = {"img": np.zeros((16, 16)), "n": 1}
    w = VQ.VarsWatchWidget(V.DictSource(ns), tr, on_run=lambda: None, on_open_example=lambda: None)
    w.resize(600, 500); w.show()
    w.refresh()
    w.watch.add_expression("nope")
    assert w.watch.wait_idle()
    pump(qapp, 20)
    from PySide6 import QtWidgets
    texts = []
    for wd in w.findChildren(QtWidgets.QWidget):
        for attr in ("text", "placeholderText", "toolTip", "accessibleName"):
            f = getattr(wd, attr, None)
            if callable(f):
                try:
                    v = f()
                except TypeError:
                    continue
                if isinstance(v, str) and v:
                    texts.append(v)
    tree = w.variables.tree
    texts += [tree.headerItem().text(i) for i in range(4)]
    texts += [w.watch.table.horizontalHeaderItem(i).text() for i in range(2)]
    allowed = re.compile(r"^[\W\d_]*$")            # 記号・数字だけ(＋ − ↑ ↓)
    bad = [t for t in texts if not _CJK.search(t) and not allowed.match(t)]
    # 型の名前・式・値はデータなので除く(列の見出し・ボタン・案内・ツールヒントが対象)
    data_like = re.compile(r"^(ndarray|int|float|nan|\d.*|img|n|nope|Python|numpy|.*Error.*)$")
    bad = [t for t in bad if not data_like.match(t) and "NameError" not in t]
    assert not bad, bad


# ---- ウォッチ ----
def test_watch_panel_add_remove_reorder_and_errors(qapp):
    import studio_pyedit_vars_qt as VQ
    ns = {"x": np.arange(5.0), "img": np.random.rand(20, 20), "v": 1}
    w = VQ.WatchPanel(ns)
    w.resize(480, 300); w.show()
    assert w.stack.currentWidget() is w.empty and "re-evaluated" in w.empty.label.text()
    changed = []
    w.changed.connect(changed.append)
    for e in ("x.mean()", "nope + 1", "img * 2", "v"):
        w.input.setText(e)
        w.input.returnPressed.emit()
    assert w.watch.exprs == ["x.mean()", "nope + 1", "img * 2", "v"] and changed[-1] == w.watch.exprs
    assert w.wait_idle()
    assert w.table.item(0, 1).text() == "2 (float64)"
    err = w.table.item(1, 1)
    assert err.text().startswith("⚠") and "NameError" in err.text() and err.foreground().color().red() > 200
    assert not w.table.item(2, 1).icon().isNull()                # 画像はサムネイル
    w.table.setCurrentCell(2, 0)
    assert w.preview.isVisible()
    w.table.setCurrentCell(3, 0)
    w.move_selected(-1)
    assert w.watch.exprs == ["x.mean()", "nope + 1", "v", "img * 2"]
    w.table.setCurrentCell(1, 0)
    w.remove_selected()
    assert w.watch.exprs == ["x.mean()", "v", "img * 2"]
    # 変わった印
    ns["v"] = 7
    w.refresh()
    assert w.wait_idle()
    row = w.watch.exprs.index("v")
    assert w.table.item(row, 1).text().startswith("● ") and w.table.item(row, 1).font().bold()
    w.refresh()
    assert w.wait_idle()
    assert not w.table.item(row, 1).text().startswith("●")
    # 保存と読み込み(プロジェクトごと)
    text = w.dumps()
    w2 = VQ.WatchPanel(ns)
    w2.loads(text)
    assert w2.watch.exprs == w.watch.exprs
    with pytest.raises(ValueError):
        w2.loads("{}")
    assert w.condition_evaluator() is w.evaluator
    assert w.condition_evaluator().condition("v > 5").hit


def test_watch_python_loop_is_stopped_and_reported_in_red(qapp):
    import studio_pyedit_vars_qt as VQ
    w = VQ.WatchPanel({}, timeout_s=0.1)
    w.show()
    t = time.perf_counter()
    w.add_expression("[i for i in iter(int, 1)]")
    assert time.perf_counter() - t < 0.5                          # 評価を待たずに戻る(UI スレッドで評価しない)
    assert w.wait_idle(5)
    cell = w.table.item(0, 1)
    assert cell.text().startswith("⚠") and "timed out" in cell.text() and "could not be stopped" not in cell.text()
    assert "[i for i in iter(int, 1)]" not in w._auto_off          # 止まった式は次の更新でまた評価する


def test_watch_shows_evaluating_then_stuck_and_stops_auto_reevaluation(qapp):
    """止められない C 待機でも UI は待たされず、行に理由が出て、自動では評価し直さない。"""
    import studio_pyedit_vars_qt as VQ
    # Lock.acquire() は全 OS で Python bytecode に戻らない C 待機。有限の sleep は単に遅く、先に戻り得る。
    gate = timing.UnstoppableGate()
    retry_gate = None
    ns = {"gate": gate.lock, "v": 1}
    w = VQ.WatchPanel(ns, tr=lambda s: s, timeout_s=0.1)
    w.show()
    ticks = []
    t = QtCoreTimer(ticks)
    try:
        t0 = time.perf_counter()
        w.add_expression(_STUCK_WATCH_EXPRESSION)
        w.add_expression("v + 1")
        assert time.perf_counter() - t0 < 0.5
        assert w.table.item(0, 1).text() == "evaluating…"                # 結果が来るまで「評価中…」
        pump(qapp, 600)                                                   # 約 0.4 秒で止められなかったと判断される
        assert len(ticks) > 5                                              # この間も UI のイベントは回っている
        assert w.table.item(1, 1).text() == "2"                           # 他の式の結果は待たずに出る
        cell = w.table.item(0, 1)
        assert cell.text() == "⚠ timed out (could not be stopped)" and cell.foreground().color().red() > 200
        assert _STUCK_WATCH_EXPRESSION in w._auto_off and not w._jobs
        started = []
        orig = w.evaluator.start
        w.evaluator.start = lambda e: (started.append(e), orig(e))[1]
        w.refresh()                                                       # 停止のたびの更新: この式は評価し直さない
        assert w.wait_idle(3)
        assert started == ["v + 1"] and w.table.item(0, 1).text().startswith("⚠ timed out (could not be stopped)")
        assert "press" in w.table.item(0, 1).toolTip() or "↻" in w.table.item(0, 1).toolTip()
        # ↻ で選んだ行だけ評価し直せる(今度も 0.1 秒の上限で止められないが、始まる)
        retry_gate = timing.UnstoppableGate()
        ns["gate"] = retry_gate.lock
        w.table.setCurrentCell(0, 0)
        w.evaluate_again()
        assert started[-1] == _STUCK_WATCH_EXPRESSION and w.table.item(0, 1).text() == "evaluating…"
    finally:
        t.stop()
        gate.close()
        if retry_gate is not None:
            retry_gate.close()
        w.wait_idle(5)


class QtCoreTimer:
    """UI のイベントが回っていることを数える(100 ms ごとではなく 10 ms ごと)。"""

    def __init__(self, ticks):
        from PySide6 import QtCore
        self._t = QtCore.QTimer()
        self._t.setInterval(10)
        self._t.timeout.connect(lambda: ticks.append(1))
        self._t.start()

    def stop(self):
        self._t.stop()


def test_watch_job_logic_without_qt():
    ns = {"x": 3}
    ev = V.WatchEvaluator(ns, timeout_s=0.1)
    j = ev.start("x * 2")
    end = time.time() + 2
    while j.poll() is None and time.time() < end:
        time.sleep(0.005)
    assert j.result.ok and j.result.value == 6 and not j.result.stuck
    j = ev.start("y +")
    assert j.result is not None and "syntax" in j.result.error             # 構文エラーは始める前に分かる
    gate = timing.UnstoppableGate()
    try:
        j = V.WatchEvaluator({"gate": gate.lock}, timeout_s=0.1).start(_STUCK_WATCH_EXPRESSION)
        end = time.time() + 3
        while j.poll() is None and time.time() < end:
            time.sleep(0.01)
        assert j.result.stuck and j.result.timed_out and "could not be stopped" in j.result.error
        assert V.STUCK_THREADS
    finally:
        gate.close()


def test_add_to_watch_from_variables_goes_to_the_watch_panel(qapp):
    import studio_pyedit_vars_qt as VQ
    ns = {"cfg": {"k": 1}}
    w = VQ.VarsWatchWidget(V.DictSource(ns))
    w.show(); w.refresh()
    it = top_items(w.variables.tree)["cfg"]
    it.setExpanded(True)
    w.variables.tree._do("watch", w.variables.tree.node_of(it.child(0)))
    assert w.watch.watch.exprs == ["cfg['k']"]
    assert w.watch.wait_idle()
    assert w.watch.table.item(0, 1).text() == "1"


# ---- 浮いた窓 ----
def test_clamp_rect_to_screens():
    scr = [(0, 0, 1920, 1080), (1920, 0, 1280, 1024)]
    assert VQ_clamp((100, 100, 400, 300), scr) == (100, 100, 400, 300)
    x, y, w, h = VQ_clamp((5000, 5000, 400, 300), scr)                   # 画面の外 → 戻す
    assert 0 <= x < 1920 and 0 <= y < 1080 and (w, h) == (400, 300)
    assert VQ_clamp((-390, 100, 400, 300), scr) != (-390, 100, 400, 300)
    x, y, w, h = VQ_clamp((0, 0, 9000, 9000), [(0, 0, 800, 600)])
    assert w <= 800 and h <= 600
    assert VQ_clamp((3000, 10, 300, 300), [(0, 0, 1920, 1080)])[0] < 1920     # 画面の構成が変わった(2 枚目が無い)


def VQ_clamp(rect, scr):
    import studio_pyedit_vars_qt as VQ
    return VQ.clamp_rect_to_screens(rect, scr)


def test_floating_frame_escape_geometry_title_and_pin(qapp):
    from PySide6 import QtCore, QtTest, QtWidgets
    import studio_pyedit_vars_qt as VQ
    ns = {"cfg": {"k": 1}}
    store = VQ.DictStore()
    parent = QtWidgets.QWidget(); parent.show()
    insp = VQ.ValueInspector(V.DictSource(ns), (("name", "cfg"),))
    fr = VQ.FloatingFrame(insp, "inspect#1", "cfg", store, parent=parent)
    fr.show()
    pump(qapp, 20)
    assert not fr.isModal() and "cfg" in fr.windowTitle() and "pinned" not in fr.windowTitle()
    fr.setGeometry(120, 90, 500, 380)
    fr.pin.setChecked(True)
    assert "[pinned]" in fr.windowTitle() and insp.pinned
    ns["cfg"] = {"k": 99}                                               # 追従を止めた窓は、その時点の物のまま
    insp.refresh()
    assert "k" in insp.tree.topLevelItem(0).child(0).text(0) and "1" == insp.tree.topLevelItem(0).child(0).text(3)
    fr.pin.setChecked(False)
    insp.refresh()
    assert insp.tree.topLevelItem(0).child(0).text(3) == "99"
    QtTest.QTest.keyClick(fr, QtCore.Qt.Key_Escape)                      # Esc で閉じる
    assert not fr.isVisible()
    saved = json.loads(store.value("floating/inspect#1"))
    assert saved[2:] == [500, 380]
    fr2 = VQ.FloatingFrame(VQ.ValueInspector(V.DictSource(ns), (("name", "cfg"),)), "inspect#1", "cfg", store, parent=parent)
    g = fr2.geometry()
    assert (g.width(), g.height()) == (500, 380)                          # 大きさを覚えている
    # 画面の外に保存されていたら戻す
    store.setValue("floating/off", json.dumps([99999, 99999, 300, 200]))
    fr3 = VQ.FloatingFrame(QtWidgets.QLabel("x"), "off", "x", store, parent=parent, pinnable=False)
    assert fr3.geometry().x() < 99999
    parent.close()


def test_floating_registry_focus_existing_multiple_inspectors_and_window_list(qapp):
    from PySide6 import QtWidgets
    import studio_pyedit_vars_qt as VQ
    ns = {"a": [1], "b": {"x": 2}}
    parent = QtWidgets.QWidget(); parent.resize(800, 600); parent.show()
    reg = VQ.FloatingRegistry(parent)
    n = {"made": 0}

    def fac():
        n["made"] += 1
        return VQ.VarsWatchWidget(V.DictSource(ns))
    f1 = reg.open("vars", fac, "Variables")
    f2 = reg.open("vars", fac, "Variables")
    assert f1 is f2 and n["made"] == 1 and len(reg.frames) == 1       # 2 枚目は作らず前に出す
    i1 = reg.open_unique("inspect", lambda: VQ.ValueInspector(V.DictSource(ns), (("name", "a"),)))
    i2 = reg.open_unique("inspect", lambda: VQ.ValueInspector(V.DictSource(ns), (("name", "b"),)))
    assert i1 is not i2 and len(reg.frames) == 3                       # 変数の中身は複数枚
    titles = reg.titles()
    assert len(set(titles)) == 3 and any("a" in t for t in titles) and any("b" in t for t in titles)
    seen = []
    reg.changed.connect(lambda: seen.append(1))
    ns["a"].append(2)
    reg.refresh_all()                                                  # 追従する窓は更新される
    assert i1.content.tree.topLevelItem(0).text(2) == "len 2"
    reg.gather(parent)
    assert i2.pos().x() > parent.geometry().x()
    reg.close_all()
    assert reg.frames == {} and not f1.isVisible()
    parent.close()


def test_value_inspector_shows_missing_variable_reason_and_image(qapp):
    import studio_pyedit_vars_qt as VQ
    ns = {"img": np.random.rand(24, 24)}
    insp = VQ.ValueInspector(V.DictSource(ns), (("name", "img"),))
    insp.show()
    assert insp.preview.isVisible() and "ndarray" in insp.header.text()
    del ns["img"]
    insp.refresh()
    assert "no longer exists" in insp.header.text() and insp.header.text().startswith("⚠")
    assert insp.tree.topLevelItemCount() == 0


def test_demo_components_can_live_in_a_dock(qapp):
    """部品は QWidget なので、ドックにも入る(入れ物を選ばない)。"""
    from PySide6 import QtCore, QtWidgets
    import studio_pyedit_vars_qt as VQ
    win = QtWidgets.QMainWindow()
    dock = QtWidgets.QDockWidget("Variables", win)
    dock.setWidget(VQ.VarsWatchWidget(V.DictSource({"a": 1})))
    win.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
    win.resize(900, 500); win.show()
    dock.widget().refresh()
    assert dock.widget().variables.tree.topLevelItemCount() == 1
    dock.setFloating(True)
    assert dock.isFloating()
    win.close()
