"""RAG は op に合わせて整理されている —— 配られる側から数える門(2026-10-15)。

ユーザー: 「fullseye の RAG はちゃんと op に合わせて整理しておいてね」。RAG の入口は 1 つではない:

* op ノート ``docs/ops/<族>/<カテゴリ>/<op>.md``(正本。生成)と族ごとの ``INDEX.md``、入口の ``docs/ops/INDEX*.md``
* wheel に載る ``fullseye/data/OP_NOTES.json``(MCP)・``OP_SEARCH.json``(意味で引く検索)・``fullseye/OP_CATALOG.md``
  (pip だけの利用者の ``fullseye-rag`` がピン留めする唯一のファイル)
* 人が書いた層: 文献層のテーマ → op 表、厳選の層の軸、レシピ、評価問題集

ここに置く門は 3 つの約束を**ファイルの側から**数える(レジストリを import しない —— optional backend が欠けた
CI でも同じ答え。レジストリとノートの一致は ``test_opdocs`` の drift 門の持ち場):

1. **出荷ノートの op は、どの入口からも全部引ける**(1,351 名が OP_CATALOG に 1 度も出ていなかった、の再発防止)。
2. **人が書いた層が名指す op は全部実在する**(改名・削除で嘘のリンクを公開しない)。
3. **op の台帳を持つモジュールは全部 RAG に配線されている** —— ``pyproject.toml`` の py-modules を歩き、
   ``OPS<名前> = …`` の表を持つモジュールが ``tools/opdocs.LEDGER_DIMS`` に無ければ落ちる(登録済みだけを
   数える門は、登録されなかった族に盲目 —— 新しい族はここで止まる)。

範囲の件数には床を置く(空どうしの一致で緑にしない)。床は 2026-10-15 の実測で、下げたら赤。
"""
from __future__ import annotations

import ast
import glob
import json
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (ROOT, os.path.join(ROOT, "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

DOCS_OPS = os.path.join(ROOT, "docs", "ops")

#: 床(2026-10-15 の実測)。op を消す変更でだけ下がる —— そのときは理由を書いて下げる。
FLOOR_NOTES = 3192
FLOOR_FAMILIES = 48
FLOOR_CATEGORIES = 455
FLOOR_THEME_OPS = 344
FLOOR_CONTEXT_OPS = 394
#: 評価問題集(tests/data/rag_eval_queries.json)の hit@5 の床。整理前 0.52(26/50)→ 日本語の文脈 0.76 →
#: 英訳の文脈も足して 0.88(44/50)。言語別: en 0.64 → 0.72 → 0.96、ja 0.40 → 0.80 → 0.80。
#: ★問題集は文脈の表と同じ書き手が同じ日に書いた —— 独立な評価ではないので、床は「後戻りしない」ことだけを言う。
FLOOR_HIT_AT_5 = {"all": 0.88, "classic": 0.90, "domain": 0.91, "new": 0.85, "lang:en": 0.96, "lang:ja": 0.80}


def _read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def notes():
    """配られる op ノート ``{(族, op): ノートの相対パス}``(frontmatter から。生成器もこの関数を使う)。"""
    from fullseye.mcp.catalog import scan_notes
    out = {}
    for op, metas in scan_notes(DOCS_OPS).items():
        for m in metas:
            key = (m["dim"], op)
            assert key not in out, "同じ (族, op) のノートが 2 枚: %s" % (key,)
            out[key] = m["path"]
    assert len(out) >= FLOOR_NOTES, "op ノートが %d 枚(床 %d)—— 生成が壊れたか op が消えた" % (len(out), FLOOR_NOTES)
    return out


@pytest.fixture(scope="module")
def families(notes):
    fam = {}
    for (dim, op), path in notes.items():
        cat = path.split("/")[3]                       # docs/ops/<族>/<カテゴリ>/<op>.md
        fam.setdefault(dim, {}).setdefault(cat, set()).add(op)
    assert len(fam) >= FLOOR_FAMILIES, sorted(fam)
    assert sum(len(c) for c in fam.values()) >= FLOOR_CATEGORIES
    return fam


# --------------------------------------------------------------------------- #
# 1. 出荷ノートの op は、どの入口からも全部引ける                                  #
# --------------------------------------------------------------------------- #
def test_shipped_json_indexes_hold_exactly_the_notes(notes):
    with open(os.path.join(ROOT, "fullseye", "data", "OP_NOTES.json"), encoding="utf-8") as f:
        on = json.load(f)
    on_set = {(m["dim"], op): m["path"] for op, ms in on["notes"].items() for m in ms}
    assert on_set == notes, ("OP_NOTES.json とノートがずれた(`py -3.11 tools/gen_mcp_data.py`): 無い %s / 余分 %s"
                             % (sorted(set(notes) - set(on_set))[:8], sorted(set(on_set) - set(notes))[:8]))
    with open(os.path.join(ROOT, "fullseye", "data", "OP_SEARCH.json"), encoding="utf-8") as f:
        ix = json.load(f)
    rows = {(r["d"], r["n"]): r for r in ix["ops"]}
    assert set(rows) == set(notes), ("検索索引とノートがずれた: 無い %s / 余分 %s"
                                     % (sorted(set(notes) - set(rows))[:8], sorted(set(rows) - set(notes))[:8]))
    bad = sorted(k for k, r in rows.items() if r.get("p") != notes[k])
    assert not bad, "検索結果が別のノートを指す: %s" % bad[:8]


def _catalog_entries(md):
    """OP_CATALOG.md の「族 → カテゴリ」節の ``{(族, op)}``。見出し ``#### <族> / <カテゴリ>(n)`` の下の行。"""
    out, head, n_heads = set(), None, 0
    for line in md.splitlines():
        m = re.match(r"^#### (\S+) / (.+?)\((\d+)\)$", line)
        if m:
            head, n_heads = m.group(1), n_heads + 1
            continue
        if line.startswith("#"):
            head = None
            continue
        if head:
            m = re.match(r"^- `([^`]+)`", line)
            if m:
                out.add((head, m.group(1)))
    return out, n_heads


def test_op_catalog_lists_every_note_in_both_copies(notes, families):
    """★2026-10-15 まで OP_CATALOG.md は 5 つのレジストリだけを載せ、43 族の 1,351 名が出ていなかった。
    pip だけの利用者の RAG はこのファイルしか持たない。"""
    docs = _read(os.path.join(ROOT, "docs", "OP_CATALOG.md"))
    pkg = _read(os.path.join(ROOT, "fullseye", "OP_CATALOG.md"))
    assert docs == pkg, "docs/ と fullseye/ の OP_CATALOG.md が違う(`py -3.11 tools/gen_op_catalog.py`)"
    got, n_heads = _catalog_entries(pkg)
    assert n_heads == sum(len(c) for c in families.values()), "カテゴリ見出しの数がノートのカテゴリ数と違う"
    missing = sorted(set(notes) - got)
    extra = sorted(got - set(notes))
    assert not missing and not extra, ("OP_CATALOG.md とノートがずれた(`py -3.11 tools/gen_op_catalog.py`): "
                                       "無い %d %s / 余分 %d %s" % (len(missing), missing[:8], len(extra), extra[:8]))


def test_every_note_is_linked_from_its_family_index(notes, families):
    linked = set()
    for idx in glob.glob(os.path.join(DOCS_OPS, "*", "INDEX.md")):
        dim = os.path.basename(os.path.dirname(idx))
        for m in re.finditer(r"\]\(([^)#]+)\.md\)", _read(idx)):
            rel = m.group(1)
            if "/" in rel and not rel.startswith(("guides/", "../", "./")):
                linked.add((dim, rel.rsplit("/", 1)[1]))
    missing = sorted(set(notes) - linked)
    assert not missing, "族の INDEX.md から辿れないノート %d: %s" % (len(missing), missing[:10])


@pytest.mark.parametrize("lang", ["", ".en", ".zh", ".tw", ".ko", ".de", ".hi"])
def test_top_index_names_every_family_and_category(families, lang):
    """入口で族名だけを見せると、drive の研磨・粉末 X 線回折や optics の材料表・ファイバは開かれない。"""
    top = _read(os.path.join(DOCS_OPS, "INDEX%s.md" % lang))
    for dim, cats in families.items():
        assert "](./%s/INDEX.md)" % dim in top, "入口 INDEX%s.md に族 %s が無い" % (lang, dim)
        for cat, ops in cats.items():
            assert "[`%s`](./%s/INDEX.md#" % (cat, dim) in top, "入口 INDEX%s.md に %s / %s が無い" % (lang, dim, cat)


# --------------------------------------------------------------------------- #
# 2. 人が書いた層が名指す op は全部実在する                                        #
# --------------------------------------------------------------------------- #
def test_hand_written_layers_name_only_real_ops(notes):
    names = {op for _d, op in notes}
    import gen_literature_notes as GL
    theme = {op for t in GL.THEME_TABLES.values() for th in t for op, _w in th["ops"]}
    assert len(theme) >= FLOOR_THEME_OPS, len(theme)
    curated = set()
    for rel in GL.CURATED.values():
        man = json.loads(_read(os.path.join(ROOT, rel)))
        curated |= {op for ax in man["axes"] for op, _w in ax["ops"]}
    assert curated
    import recipes
    rec = {s[0] for r in recipes.RECIPES for s in r["stages"]}
    assert rec
    ev = json.loads(_read(os.path.join(ROOT, "tests", "data", "rag_eval_queries.json")))
    evo = {o for q in ev["queries"] for o in q["ops"]}
    assert evo
    bad = {k: sorted(v - names) for k, v in (("THEME_TABLES", theme), ("curated", curated), ("recipes", rec),
                                              ("rag_eval", evo)) if v - names}
    assert not bad, "人が書いた層に実在しない op(改名・削除?): %s" % bad


def test_literature_links_resolve_and_carry_every_theme_op(notes):
    """文献層の op リンクは全部ノートに届き、テーマ表の op は全部どこかのクラスタに出る。
    ★2026-10-15 まで、生成器はテーマごとに 8 本で黙って切っていて、表の 21 op が文献層のどこにも出ていなかった。"""
    paths = set(notes.values())
    linked, broken = set(), []
    files = glob.glob(os.path.join(ROOT, "docs", "literature", "*.md"))
    assert len(files) >= 7
    for p in files:
        for m in re.finditer(r"\[`([A-Za-z0-9_]+)`\]\(\.\./ops/([^)]+)\)", _read(p)):
            tgt = "docs/ops/" + m.group(2)
            if tgt not in paths:
                broken.append((os.path.basename(p), m.group(1), tgt))
            linked.add(m.group(1))
    assert not broken, "文献層のリンク切れ: %s" % broken[:8]
    import gen_literature_notes as GL
    theme = {op for t in GL.THEME_TABLES.values() for th in t for op, _w in th["ops"]}
    unseen = sorted(theme - linked)
    assert not unseen, ("テーマ表に在るのに文献層のどこにも出ない op(`tools/gen_literature_notes.py --rad-root <RAD>` で "
                        "作り直す / 鍵がどのクラスタにも当たらないテーマ?): %s" % unseen)
    index = _read(os.path.join(ROOT, "docs", "literature", "INDEX.md"))
    assert "どのクラスタにも当たらなかったテーマ" in index and "当たらなかったテーマ**" in index


def test_search_index_carries_the_hand_written_contexts(notes):
    """テーマ表・厳選の層の op は、意味で引く検索の索引に文脈(``t``)を持つ —— 2 つの入口に同じ知識。"""
    import gen_mcp_data as GM
    ctx = GM.op_contexts()
    assert len(ctx) >= FLOOR_CONTEXT_OPS, len(ctx)
    with open(os.path.join(ROOT, "fullseye", "data", "OP_SEARCH.json"), encoding="utf-8") as f:
        ix = json.load(f)
    have = {r["n"] for r in ix["ops"] if r.get("t")}
    missing = sorted(set(ctx) - have)
    assert not missing, "文脈が索引に入っていない(`py -3.11 tools/gen_mcp_data.py`): %s" % missing[:10]
    assert ix.get("ops_with_context") == len(have) >= FLOOR_CONTEXT_OPS
    # 英語の文脈(te)は日本語の文脈(t)と同じ行数で、日本語が混ざらない(英語の問い合わせが伸びなかった件、2026-10-15)
    jp = re.compile(r"[぀-ヿ一-鿿]")
    bad = sorted(r["n"] for r in ix["ops"] if r.get("t") and (len(r.get("te") or ()) != len(r["t"])
                                                              or any(jp.search(x) for x in r["te"])))
    assert not bad, "英語の文脈が欠けた / 日本語が混ざった op: %s" % bad[:10]


def test_context_translation_table_matches_the_phrases():
    """対訳表 docs/i18n/op_context.json は、テーマ表と厳選の層の句をちょうど覆う(欠けも、使われない古い句も無い)。"""
    import gen_mcp_data as GM
    phrases = GM.context_phrases()
    assert len(phrases) >= 500, len(phrases)
    tr = GM.load_context_i18n()
    missing = [p for p in phrases if not (tr.get(p) or {}).get("en")]
    stale = sorted(set(tr) - set(phrases))
    assert not missing, "英訳の無い句(docs/i18n/op_context.json に足す): %s" % missing[:5]
    assert not stale, "どの表にももう無い句の訳(消す): %s" % stale[:5]
    assert GM.op_contexts_en().keys() == GM.op_contexts().keys()


def test_search_recall_on_the_evaluation_set_does_not_fall():
    import opsearch_eval as E
    ev = E.load()
    assert len(ev["queries"]) >= 50
    assert E.unknown_ops(ev) == []
    res = E.score(ev)
    got = {k: v["hit_at_k"] for k, v in res["sets"].items()}
    low = {k: (got.get(k), f) for k, f in FLOOR_HIT_AT_5.items() if (got.get(k) or 0) < f}
    assert not low, "hit@5 が床を割った {集合: (今, 床)}: %s\n外れ: %s" % (
        low, [(m["q"], m["top"]) for m in res["misses"]][:12])


# --------------------------------------------------------------------------- #
# 3. op の台帳を持つモジュールは全部 RAG に配線されている                           #
# --------------------------------------------------------------------------- #
def _py_modules():
    """``pyproject.toml`` の ``py-modules``(wheel に載るモジュール)。tomllib に頼らない(3.10 でも同じ答え)。"""
    txt = _read(os.path.join(ROOT, "pyproject.toml"))
    m = re.search(r"^py-modules\s*=\s*\[(.*?)^\]", txt, re.S | re.M)
    assert m, "pyproject.toml に py-modules が無い"
    body = "\n".join(line.split("#", 1)[0] for line in m.group(1).splitlines())
    mods = re.findall(r"\"([A-Za-z_][A-Za-z0-9_]*)\"", body)
    assert len(mods) >= 300, len(mods)
    return mods


#: ``OPS<名前>`` という名前だが op の台帳ではないもの。**理由つきで列挙する**(黙って通す道は作らない)。
NOT_OP_TABLES = {
    ("ops", "OPS"): "ops.REGISTRY の後方互換の (名前, 関数) の組。2-D のノートは ops.REGISTRY から作る",
    ("graph", "OPS_JSON"): "HALCON 演算子の JSON のファイルパス(op の表ではない)",
}


def _op_tables(mod):
    """モジュールの最上位で ``OPS<名前> = …`` と代入している名前(import せずに AST で)。"""
    p = os.path.join(ROOT, mod + ".py")
    if not os.path.isfile(p):
        return []
    import warnings
    with warnings.catch_warnings():                    # 対象のソースの古い escape の警告はこの門の関心ではない
        warnings.simplefilter("ignore")
        tree = ast.parse(_read(p))
    out = []
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        for t in targets:
            if isinstance(t, ast.Name) and re.fullmatch(r"OPS[A-Z0-9_]*", t.id):
                out.append(t.id)
    return out


def test_every_shipped_op_table_is_wired_into_the_rag():
    import opdocs as OD
    import opassist
    wired = {(m["registry"], m["table"]) for m in OD.LEDGER_DIMS.values()} | {("ops3d", "OPS3D")}
    found = {(mod, t) for mod in _py_modules() for t in _op_tables(mod)}
    stale = sorted(k for k in NOT_OP_TABLES if k not in found)
    assert not stale, "NOT_OP_TABLES に、もう無い名前: %s(行を消す)" % stale
    found -= set(NOT_OP_TABLES)
    assert len(found) >= 47, sorted(found)
    unwired = sorted(found - wired)
    assert not unwired, ("op の台帳を持つのに RAG(docs/ops のノート・検索・カタログ)に配線されていないモジュール: %s —— "
                         "tools/opdocs.py の LEDGER_DIMS(と opassist._LEDGERS)に足して `py -3.11 tools/regen_all.py`" % unwired)
    gone = sorted(w for w in wired if w not in found)
    assert not gone, "LEDGER_DIMS が指す表が wheel に無い: %s" % gone
    # 同じ並びを 2 か所に持つ表(opassist は「LEDGER_DIMS と同じ並び」と書いている)は、ずれたら片方だけ増える
    assert set(opassist._LEDGERS) == wired, sorted(set(opassist._LEDGERS) ^ wired)


def test_every_family_has_notes_and_a_family_index(families):
    import opdocs as OD
    for dim in ("2d", "3d", *OD.LEDGER_DIMS):
        assert dim in families, "族 %s のノートが 1 枚も無い(`py -3.11 tools/opdocs.py all`)" % dim
        assert os.path.isfile(os.path.join(DOCS_OPS, dim, "INDEX.md")), dim
