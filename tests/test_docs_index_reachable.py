# -*- coding: utf-8 -*-
"""★索引から 1 本も辿れない文書を作らない。

## なぜ要るか(2026-09-06)

`docs/README.md` は GitHub Pages のトップ(<https://furuse.work/>)であり、
**AI コーディング支援が引く検索面**でもある(README が「op ノートは RAG
コーパスを兼ねる」と書いている)。この日に数えたところ:

| | 到達 / 全体 |
|---|---|
| `docs/*.md` | **31 / 74** |
| `docs/ops/**/INDEX.md` | **0 / 32** |
| 族ガイド | **0 / 48** |
| op ノート | **0 / 1,842** |
| `docs/articles/**` | **0 / 40** |

op ノート 1,842 本 —— **この repo でいちばん大きい中身**が、入口から 1 本も
辿れなかった。原因は 2 つあって、どちらも「在るものを無いことにする」形:

1. 索引に `docs/ops/` へのリンクが 1 本も無かった。
2. 足したはずの生成器が `OD.records()`(実体は `_records`)を `hasattr` で
   探し、**見つからないと黙って空を返して**いた。表が空・「0 本の op ノート」
   と書かれた索引が 6 言語ぶん公開されていた。

数が減っていくのを止めるのではなく、**ゼロであることを守る**門にする。
新しい文書を足したら、索引のどこかから辿れるようにするか、
`tools/gen_docs_index_ops.py` の `DOC_GROUPS` に足す(足し忘れても
「そのほか」に自動で出るので、この門が落ちるのは**リンクを壊したとき**だけ)。
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from collections import deque
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
INDEX = DOCS / "README.md"

#: 索引の言語版。ja(README.md)以外は同じ生成ブロックを持つ。
LANGS = ["", "en", "zh", "tw", "ko", "de"]

#: 生成ブロックのマーカー。**外したら索引が腐る**ので存在も確かめる。
MARKERS = ["<!-- ops-index:start -->", "<!-- ops-index:end -->",
           "<!-- poc-index:start -->", "<!-- poc-index:end -->",
           "<!-- docmap:start -->", "<!-- docmap:end -->"]

_LINK = re.compile(r"\]\(([^)\s]+)")
#: ```…``` のブロックと `…` のインラインコード。**この中はリンクではない**
#: (`docs/I18N.md` が検査の説明として `](*.md)` と書いており、素朴に走査すると
#: 「リンク切れ」に見える)。
_FENCE = re.compile(r"^```.*?^```", re.S | re.M)
_CODE = re.compile(r"`[^`\n]*`")


def _prose(text: str) -> str:
    return _CODE.sub("", _FENCE.sub("", text))


#: ★Markdown 記法だけ見ると足りない。`docs/GALLERY.md` は表の中で
#: `<img src="...">` を 14 か所使っており、素朴な `](` の走査では 1 つも
#: 見えない(Codex の敵対的レビューで判明、2026-09-06)。生の HTML も見る。
_HTML = re.compile(r"""<(?:img[^>]+src|a[^>]+href)=["']([^"']+)""", re.I)


def _links(path: Path) -> list:
    """md 内の相対リンク先を絶対パスで返す(http / mailto / アンカーは除く)。

    Markdown の `](...)` と、生 HTML の `<img src>` / `<a href>` の両方。
    """
    text = _prose(path.read_text(encoding="utf-8"))
    out = []
    for m in list(_LINK.finditer(text)) + list(_HTML.finditer(text)):
        t = m.group(1).split("#")[0].strip()
        if not t or t.startswith(("http://", "https://", "mailto:", "data:", "<")):
            continue
        out.append((path.parent / t).resolve())
    return out


def _index_path(lang: str) -> Path:
    return DOCS / ("README.md" if not lang else "README.%s.md" % lang)


def _reachable(root: Path = INDEX) -> set:
    seen = {root.resolve()}
    q = deque(seen)
    while q:
        cur = q.popleft()
        for nxt in _links(Path(cur)):
            if nxt in seen or nxt.suffix != ".md" or not nxt.is_file():
                continue
            seen.add(nxt)
            q.append(nxt)
    return seen


def _all_md() -> list:
    return sorted(p.resolve() for p in DOCS.rglob("*.md"))


@pytest.mark.parametrize("lang", LANGS, ids=lambda x: x or "ja")
def test_every_document_is_reachable_from_the_index(lang):
    """★これが本体。`docs/**/*.md` が 1 本残らず索引から辿れること。

    **6 言語すべてを出発点にして測る**(Codex の敵対的レビュー、2026-09-06)。
    ja からだけ測ると、英語で来た人と英語で引く RAG には辿れない文書が
    残っていても緑になる。生成ブロックは 6 言語に同じ相対リンクを入れるので、
    差が出るのは**手書き部分の抜け**だけ —— それがまさに見たいもの。
    """
    root = _index_path(lang)
    seen = _reachable(root)
    orphans = [p for p in _all_md() if p not in seen]
    rel = sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in orphans)
    assert not orphans, (
        "索引 %s から辿れない文書が %d 本ある。入口が無い文書は在っても無いのと"
        "同じ。`py -3.11 tools/gen_docs_index_ops.py` を走らせるか、どこかから"
        "リンクすること:\n  %s" % (root.name, len(rel), "\n  ".join(rel[:40])))


#: リンク切れを見る拡張子。**画像も見る** —— 索引の扉絵が消えても
#: 「文書は全部辿れます」で緑になってしまうため。
_CHECKED = (".md", ".json", ".py", ".cff", ".toml", ".txt",
            ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".mp4")


def test_the_index_has_no_broken_links():
    """★リンク切れは到達性より先に効く(切れた先はそもそも数えられない)。"""
    bad = []
    for md in _all_md():
        for t in _links(Path(md)):
            if t.suffix.lower() in _CHECKED and not t.exists():
                bad.append("%s -> %s" % (
                    Path(md).relative_to(ROOT), t.relative_to(ROOT)
                    if str(t).startswith(str(ROOT)) else t))
    assert not bad, "リンク切れ %d 件:\n  %s" % (len(bad), "\n  ".join(bad[:40]))


def test_link_targets_match_the_real_filename_case():
    """★Windows では通り、Linux CI と GitHub Pages では 404 になるリンクを止める。

    開発は Windows(大文字小文字を区別しない)、公開は Linux。`ops/2D/INDEX.md`
    のような 1 文字違いは**手元でだけ**動く。この repo は「門は事故の起きる
    場所に立てる」で一度痛い目を見ている(配布物と Linux で数える)ので、
    ここでも**公開側の規則**で見る。
    """
    bad = []
    for md in _all_md():
        for t in _links(Path(md)):
            if t.suffix.lower() not in _CHECKED or not t.exists():
                continue
            try:
                if t.name not in os.listdir(t.parent):
                    bad.append("%s -> %s" % (Path(md).relative_to(ROOT), t.name))
            except OSError:
                pass
    assert not bad, ("大文字小文字が実ファイル名と違うリンク %d 件"
                     "(Linux では 404):\n  %s" % (len(bad), "\n  ".join(bad[:20])))


@pytest.mark.parametrize("lang", LANGS, ids=lambda x: x or "ja")
def test_every_language_index_carries_the_generated_blocks(lang):
    """片方の言語だけ生成し忘れる事故を止める。"""
    name = "README.md" if not lang else "README.%s.md" % lang
    s = (DOCS / name).read_text(encoding="utf-8")
    missing = [m for m in MARKERS if m not in s]
    assert not missing, "%s に生成ブロックが無い: %s —— " \
        "`py -3.11 tools/gen_docs_index_ops.py`" % (name, missing)
    # ★マーカーの重複を許すと、古い表がもう 1 つ残ったまま緑になる。
    # 生成器は最初の start〜end しか書き換えないので、2 つ目は永久に古いまま
    # 公開され続ける(Codex の敵対的レビュー、2026-09-06)。
    dup = [m for m in MARKERS if s.count(m) != 1]
    assert not dup, "%s にマーカーが 2 回以上ある(古い表が残る): %s" % (name, dup)
    for a, b in zip(MARKERS[::2], MARKERS[1::2]):
        assert s.index(a) < s.index(b), "%s の %s が end より後ろにある" % (name, a)


def test_the_operator_table_is_not_empty():
    """★空の表を公開しない(実際に「0 本の op ノート」を 6 言語で公開した)。

    生成器が一次情報の名前を取り違えて黙って空を返したときに鳴る。
    「N 本」の N が 0 でないこと、次元の行が実際にあることを見る。
    """
    s = (DOCS / "README.md").read_text(encoding="utf-8")
    block = s.split("<!-- ops-index:start -->", 1)[1].split("<!-- ops-index:end -->")[0]
    assert "**0 " not in block, "「0 本の op ノート」と書かれている —— 生成器が壊れている"

    # ★「20 行あって 4 つの次元名が見える」で通していたが、それでは数百 op
    # 落ちても緑になる(Codex の敵対的レビュー、2026-09-06)。**次元ごとの
    # 実数**と 1 つ残らず突き合わせる。
    sys.path.insert(0, str(ROOT / "tools"))
    sys.path.insert(0, str(ROOT))
    import gen_docs_index_ops as G

    live = {}
    for r in G._records():
        live[r["dim"]] = live.get(r["dim"], 0) + 1
    shown = {}
    for line in block.splitlines():
        m = re.match(r"\|\s*`([^`]+)`[^|]*\|\s*([\d,]+)\s*\|", line)
        if m:
            shown[m.group(1)] = int(m.group(2).replace(",", ""))
    assert shown == live, (
        "表の op 数が実数と違う。表にだけある: %s / 実数にだけある: %s / "
        "数が違う: %s" % (
            sorted(set(shown) - set(live)), sorted(set(live) - set(shown)),
            {k: (shown[k], live[k]) for k in set(shown) & set(live)
             if shown[k] != live[k]}))
    assert sum(live.values()) == len(G._records())


def test_the_generated_blocks_are_current():
    """生成物と commit 済みが一致していること(ドリフト門)。"""
    sys.path.insert(0, str(ROOT / "tools"))
    sys.path.insert(0, str(ROOT))
    import gen_docs_index_ops as G

    for lang in LANGS:
        name = "README.md" if not lang else "README.%s.md" % lang
        s = (DOCS / name).read_text(encoding="utf-8")
        for want, a, b in ((G.build(lang), G.START, G.END),
                           (G.build_poc(lang), G.PSTART, G.PEND),
                           (G.build_docmap(lang), G.DSTART, G.DEND)):
            got = a + s.split(a, 1)[1].split(b, 1)[0] + b
            if got != want:
                # ★どこが違うかを出す。出さないと、全体スイートでだけ落ちる
                # ような順序依存(レジストリ汚染など)を追えない。
                import difflib
                d = list(difflib.unified_diff(
                    got.splitlines(), want.splitlines(),
                    "committed", "generated", lineterm="", n=1))
                raise AssertionError(
                    "%s の %s ブロックが古い —— "
                    "`py -3.11 tools/gen_docs_index_ops.py` で再生成すること。\n"
                    "差分(commit 済み → いま生成される):\n%s"
                    % (name, a, chr(10).join(d[:40])))

    s = (DOCS / "articles" / "README.md").read_text(encoding="utf-8")
    want = G.build_articles()
    got = G.ASTART + s.split(G.ASTART, 1)[1].split(G.AEND, 1)[0] + G.AEND
    assert got == want, ("docs/articles/README.md の一覧が古い —— "
                         "`py -3.11 tools/gen_docs_index_ops.py`")


def test_the_index_points_at_the_machine_readable_entry_points():
    """★索引は人だけでなく RAG の入口でもある。

    op ノートは AI コーディング支援の検索コーパスを兼ねる(README がそう
    書いている)。機械が読む入口 —— `OP_INDEX.json` と `AI_RAG_GUIDE.md` ——
    が索引から辿れること。
    """
    s = INDEX.read_text(encoding="utf-8")
    for target in ("OP_INDEX.json", "AI_RAG_GUIDE.md", "OP_CATALOG.md"):
        assert "(%s)" % target in s, (
            "索引から %s へのリンクが無い。AI から引く入口なので消さないこと。"
            % target)
    assert (DOCS / "OP_INDEX.json").is_file(), "OP_INDEX.json が無い"


def test_the_machine_readable_index_is_current():
    """★★`docs/OP_INDEX.json` が**いまの登録**と一致していること。

    2026-09-06 に索引から「AI から引く入口」としてリンクした直後に数えたら、
    中身は **538 op / 8 sort**、最終更新は 2026-08-12 だった。実際は
    **902 op / 19 sort**。**4 割が入っていない索引を、機械が引く入口として
    公開しようとしていた**。人が読むページなら「古いな」で済むが、RAG は
    載っていない 4 割について**自信を持って間違える**(在るものを「無い」と
    答える)ので、人向けの古さより悪い。

    落ちたら `py -3.11 imgevolve.py index` を走らせる。
    """
    import json

    sys.path.insert(0, str(ROOT))
    import imgevolve as IE

    got = json.loads((DOCS / "OP_INDEX.json").read_text(encoding="utf-8"))
    fresh = IE._build_op_index()          # ★公開されるものと同じ組み立て
    live = fresh["ops"]
    assert got == fresh, (
        "docs/OP_INDEX.json が生成物と一致しない —— "
        "`py -3.11 imgevolve.py index` で書き直すこと")
    assert got["n_ops"] == len(live) == len(got["ops"]), (
        "docs/OP_INDEX.json が古い: n_ops=%d / 配列 %d 件 / いまは %d op —— "
        "`py -3.11 imgevolve.py index` で書き直すこと"
        % (got["n_ops"], len(got["ops"]), len(live)))

    # ★件数と名前だけでは、型の契約(in_sort/out_sort)・カテゴリ・HALCON 対応・
    # tier が丸ごと古いまま緑になる(Codex の敵対的レビュー、2026-09-06)。
    # RAG は型が繋がる op を選ぶのに in_sort/out_sort を読むので、そこが古いと
    # **繋がらない鎖を自信満々に提案する**。中身ごと突き合わせる。
    names = [r["name"] for r in got["ops"]]
    assert len(names) == len(set(names)), (
        "OP_INDEX.json に同じ名前が 2 度出ている: %s"
        % sorted({n for n in names if names.count(n) > 1})[:10])
    by_name_json = {r["name"]: r for r in got["ops"]}
    by_name_live = {r["name"]: r for r in live}
    assert set(by_name_json) == set(by_name_live), (
        "OP_INDEX.json と登録の名前が食い違う(json のみ %s / 登録のみ %s)"
        % (sorted(set(by_name_json) - set(by_name_live))[:5],
           sorted(set(by_name_live) - set(by_name_json))[:5]))
    diff = [n for n in sorted(by_name_live)
            if by_name_json[n] != by_name_live[n]]
    assert not diff, (
        "OP_INDEX.json の中身が %d 件ずれている(型やカテゴリが古い)。例: %s "
        "—— `py -3.11 imgevolve.py index`"
        % (len(diff), [(n, by_name_json[n], by_name_live[n]) for n in diff[:2]]))
    live_sorts = sorted({r["in_sort"] for r in live} | {r["out_sort"] for r in live})
    assert got["sorts"] == live_sorts, (
        "OP_INDEX.json の sort 一覧が古い: %s ではなく %s"
        % (got["sorts"], live_sorts))


def test_the_rag_guide_note_count_is_current():
    """`AI_RAG_GUIDE.md` の「ノート N 枚」が索引と**同じ数**であること。

    「約 1000 枚」と書いたまま 1,842 枚まで放置されていた。直すときに
    **ファイルを数えて 1,843 と書いてしまい**、索引(1,842)と食い違う数を
    同時に公開しかけた(Codex の敵対的レビューが検出、2026-09-06)。差の
    1 本は `docs/ops/SAMPLES.md` —— op ノートではない。数える対象は
    「台帳の記録」であって「`docs/ops` の md ファイル」ではない。
    """
    sys.path.insert(0, str(ROOT / "tools"))
    sys.path.insert(0, str(ROOT))
    import gen_docs_index_ops as G

    n = len(G._records())
    s = (DOCS / "AI_RAG_GUIDE.md").read_text(encoding="utf-8")
    assert "{:,}".format(n) in s, (
        "docs/AI_RAG_GUIDE.md のノート枚数が古い(いまは %s 枚)" % "{:,}".format(n))


def test_the_note_files_on_disk_match_the_ledger_exactly():
    """★ファイルと台帳が**双方向に**一致すること。

    片側しか見ないと、消えた op のノートが「権威ある文書」として検索に
    残り続ける(RAG は在ると答える)。逆に、記録はあるのにファイルが無ければ
    リンク切れになる。既知の例外は 1 つだけ、明示して数える。
    """
    sys.path.insert(0, str(ROOT / "tools"))
    sys.path.insert(0, str(ROOT))
    import gen_docs_index_ops as G
    import opdocs as OD

    #: op ノートではないが `docs/ops/` に置いてある文書。増やすなら理由を書く。
    NOT_A_NOTE = {"SAMPLES.md"}

    want = {Path(OD._op_path(r)).resolve() for r in G._records()}
    have = {p.resolve() for p in (DOCS / "ops").rglob("*.md")
            if p.name != "INDEX.md" and "guides" not in p.parts
            and p.name not in NOT_A_NOTE}
    extra = sorted(str(p.relative_to(ROOT)) for p in have - want)
    gone = sorted(str(p.relative_to(ROOT)) for p in want - have)
    assert not extra, ("台帳に無いノートが残っている(消えた op の説明が検索に"
                       "残る): %s" % extra[:20])
    assert not gone, ("台帳にあるのにノートが無い: %s —— "
                      "`py -3.11 tools/opdocs.py all`" % gone[:20])


def test_the_docmap_lists_every_top_level_document():
    """地図が `docs/*.md` と `docs/design/*.md` を 1 本残らず含むこと。"""
    sys.path.insert(0, str(ROOT / "tools"))
    sys.path.insert(0, str(ROOT))
    import gen_docs_index_ops as G

    block = INDEX.read_text(encoding="utf-8").split(G.DSTART, 1)[1].split(G.DEND)[0]
    missing = [d for d in G._all_docs() if "](%s)" % d not in block]
    assert not missing, "地図に載っていない文書: %s" % missing


def test_the_index_renders_as_a_page_without_local_paths():
    """公開ページにローカル絶対パスを載せない(前に api-keys.json の絶対パスが
    載っていた)。索引は 6 言語すべて見る。"""
    bad = []
    for lang in LANGS:
        name = "README.md" if not lang else "README.%s.md" % lang
        s = (DOCS / name).read_text(encoding="utf-8")
        for m in re.finditer(r"[A-Za-z]:[\\/](?:dev|Users)[\\/][^\s`)\"']+", s):
            bad.append("%s: %s" % (name, m.group(0)))
    assert not bad, "公開索引にローカル絶対パス: %s" % bad


# --------------------------------------------------------------------------- #
# ★生成物が「中身か」を見る —— 一致だけ見る門は、両方が空でも緑になる            #
# --------------------------------------------------------------------------- #
#: 2026-09-06 の実測。**下回ったら落ちる**(上げるのは自由)。
_NOTES_FLOOR = 1842            # op ノートの本数
_WITH_EXAMPLE_FLOOR = 1637     # 実行できる例が 1 本以上あるノート
_WITH_USAGE_FLOOR = 1348       # 使い方が 120 字以上あるノート
_GUIDES_FLOOR = 48             # 族ガイド
_GUIDE_BYTES_FLOOR = 2000      # いちばん短い族ガイドの下限


def test_the_notes_have_actual_content_not_just_structure():
    """★ユーザーの指摘(2026-09-06)「生成物が正しいのか確かめて、中身が空とか
    なってたら意味ない。」への門。

    ドリフト門は**生成物と commit 済みが一致するか**しか見ない。生成器が
    空を吐けば両方が空で一致し、緑のまま「1,842 本のノートがあります」と
    書かれた空のページが公開される。ここでは一致ではなく**中身の量**を測る。

    構造(frontmatter・呼び出し・型・次に繋がる op)は全数必須。読んで役に
    立つ部分(実行できる例・使い方の本文)は**いま届いている数を床にする**
    ratchet で、後戻りだけ止める。床の値は索引にもそのまま出している。
    """
    sys.path.insert(0, str(ROOT / "tools"))
    sys.path.insert(0, str(ROOT))
    import gen_docs_index_ops as G

    n, ex, use = G._note_substance()
    assert n >= _NOTES_FLOOR, "ノートが %d 本に減っている(床 %d)" % (n, _NOTES_FLOOR)
    assert ex >= _WITH_EXAMPLE_FLOOR, (
        "実行できる例のあるノートが %d 本に減った(床 %d)。例を消したなら "
        "床も一緒に動かす理由を書くこと" % (ex, _WITH_EXAMPLE_FLOOR))
    assert use >= _WITH_USAGE_FLOOR, (
        "使い方が書かれたノートが %d 本に減った(床 %d)" % (use, _WITH_USAGE_FLOOR))


def test_every_note_carries_the_structural_parts():
    """構造は**全数**。1 本でも欠けたら落とす(こちらは ratchet にしない)。"""
    notes = [p for p in (DOCS / "ops").rglob("*.md")
             if p.name not in ("INDEX.md", "SAMPLES.md")
             and "guides" not in p.parts]
    need = ("**呼び出し**", "**データ種**", "## 実行できる例",
            "型が繋がる次の op")
    bad = []
    for p in notes:
        s = p.read_text(encoding="utf-8")
        miss = [w for w in need if w not in s]
        if not s.startswith("---" + chr(10)):
            miss.append("frontmatter")
        if miss:
            bad.append("%s: %s" % (p.relative_to(ROOT), miss))
    assert not bad, "構造が欠けたノート %d 本:\n  %s" % (
        len(bad), chr(10).join("  " + b for b in bad[:15]))


def test_the_family_guides_are_not_stubs():
    """族ガイドは「48 本あります」と索引に書く以上、空であってはならない。"""
    guides = sorted((DOCS / "ops").rglob("guides/*.md"))
    assert len(guides) >= _GUIDES_FLOOR, (
        "族ガイドが %d 本に減っている(床 %d)" % (len(guides), _GUIDES_FLOOR))
    thin = [(len(p.read_text(encoding="utf-8")), str(p.relative_to(ROOT)))
            for p in guides]
    small = sorted(t for t in thin if t[0] < _GUIDE_BYTES_FLOOR)
    assert not small, "中身の薄い族ガイド(< %d B): %s" % (_GUIDE_BYTES_FLOOR, small)


def test_the_index_tables_are_not_empty_anywhere():
    """★6 言語すべてで、生成した 3 つの表に**実際に行がある**こと。

    「0 本の op ノート」と書かれた空の表を 6 言語ぶん公開した日の再発防止。
    行数の下限は実測(op 31 次元 + 見出し、PoC 分野 23、地図 71 本)。
    """
    import re as _re
    for lang in LANGS:
        name = "README.md" if not lang else "README.%s.md" % lang
        s = (DOCS / name).read_text(encoding="utf-8")
        for a, b, floor, what in (
                ("<!-- ops-index:start -->", "<!-- ops-index:end -->", 31, "次元"),
                ("<!-- poc-index:start -->", "<!-- poc-index:end -->", 20, "PoC 分野"),
                ("<!-- docmap:start -->", "<!-- docmap:end -->", 65, "文書")):
            blk = s.split(a, 1)[1].split(b, 1)[0]
            rows = [l for l in blk.splitlines()
                    if l.startswith("| ") and not _re.match(r"^\|[-:\s|]+\|$", l)]
            assert len(rows) >= floor, (
                "%s の %s の表が %d 行しかない(床 %d)" % (name, what, len(rows), floor))
            # 空セルを含む行を作らない(生成器がデータを取り落としたときに出る)
            empty = [l for l in rows
                     if any(c.strip() == "" for c in l.strip("|").split("|"))]
            assert not empty, "%s の %s の表に空のセル: %s" % (
                name, what, empty[:3])


def test_underscore_directories_are_served_by_pages():
    """★Jekyll は `_` で始まるディレクトリを配信しない。

    op の図を `docs/ops/_fig/` に置いたら、手元のリンク検査は全部通り、公開
    サイトでは 724 枚が **404** だった(2026-09-07 実測)。配信側の規則は
    配信側でしか見えないので、`docs/_config.yml` の `include` に、リンクされて
    いる `_` ディレクトリが**すべて**載っていることをここで確かめる。
    """
    cfg = DOCS / "_config.yml"
    assert cfg.is_file(), "docs/_config.yml が無い(Jekyll の include 設定)"
    included = set(re.findall(r"^\s*-\s*(_\S+)\s*$", cfg.read_text(encoding="utf-8"), re.M))
    linked = set()
    for md in _all_md():
        for t in _links(Path(md)):
            try:
                rel = t.relative_to(DOCS)
            except ValueError:
                continue
            for part in rel.parts[:-1]:
                if part.startswith("_"):
                    linked.add(part)
    missing = sorted(linked - included)
    assert not missing, (
        "リンクされているのに Jekyll が配信しない `_` ディレクトリ: %s —— "
        "docs/_config.yml の include に足すこと" % missing)
