# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC 展示館の記事(tools/gen_wingpoc_gallery.py)が腐らないための門。

見ているもの:

* 生成物(翼 md × 2、案内 × 2、棟 × 2 × 2 言語)が正本と一致する(``--check`` 相当)。
* 記事が参照する画像が全部 repo にある(raw URL が 404 になる形で公開しない)。
* ローカルパス・赤緑マーカーが混ざらない。
* 展示の数が examples2d の poc_* と一致する(PoC を足したのに展示に無い、を止める)。
* 動く図が JPEG に化けていない。
* ★**収蔵番号**が全展示に在り、重複せず、受入順で、欠番は理由つき(2026-09-25 追加)。
* ★**全展示がちょうど 1 つの棟に属する**。どの棟にも無い展示は記事から静かに消え、
  2 つの棟に在る展示は二重掲載になる —— どちらも例外を出さない。
* ★**数学記事と展示館が同じ PoC を載せていない**。2026-09-25 まで 7 件がこの状態だった。
"""
from __future__ import annotations

import copy
import io
import json
import os
import re
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "tools"))
sys.path.insert(0, _ROOT)

import gen_wingpoc_gallery as G   # noqa: E402

_ART = os.path.join(_ROOT, "docs", "articles")
_EX = os.path.join(_ART, "exhibits")
LEDGER = os.path.join(_EX, "exhibit_numbers.json")

#: 記事の見出しに出る収蔵番号。`## No.2026.037 —— タイトル`
_HEAD_NO = re.compile(r"^## No\.(\d{4}\.\d{3,}) ", re.M)


@pytest.fixture(scope="module")
def cap():
    return G._load()


@pytest.fixture(scope="module")
def ledger():
    assert os.path.exists(LEDGER), "収蔵台帳が無い: %s" % LEDGER
    with io.open(LEDGER, encoding="utf-8") as fh:
        return json.load(fh)


def _generated(c: dict, lang: str) -> list:
    """その言語で生成する記事の道のり。案内 + 棟(external は手書きなので入らない)。"""
    out = [G.OUT_ARTICLE[lang]]
    out += [G.part_path(p["slug"], lang) for p in c["meta"]["parts"] if p["kind"] == "generated"]
    return out


def test_generated_articles_are_up_to_date(cap):
    c, byid = cap
    nos = G._numbers()
    for lang in ("ja", "en"):
        want = [(G.OUT_WING[lang], G.build_wing_md(lang, c, byid, nos)),
                (G.OUT_ARTICLE[lang], G.build_entrance(lang, c, byid, nos))]
        for p in c["meta"]["parts"]:
            if p["kind"] == "generated":
                want.append((G.part_path(p["slug"], lang), G.build_part(p, lang, c, byid, nos)))
        for path, text in want:
            assert os.path.exists(path), path
            cur = io.open(path, encoding="utf-8").read()
            assert cur == text, ("%s が古い —— py -3.11 tools/gen_wingpoc_gallery.py"
                                 % os.path.basename(path))


def test_every_referenced_asset_exists(cap):
    c, _byid = cap
    pat = re.compile(re.escape(G.RAW) + r"([A-Za-z0-9_./-]+)")
    for lang in ("ja", "en"):
        for path in _generated(c, lang):
            text = io.open(path, encoding="utf-8").read()
            missing = sorted({m for m in pat.findall(text)
                              if not os.path.exists(os.path.join(G.ASSETS, m.replace("/", os.sep)))})
            assert not missing, (os.path.basename(path), missing[:10])


def test_no_local_paths_or_traffic_lights(cap):
    c, _byid = cap
    for lang in ("ja", "en"):
        for path in _generated(c, lang):
            text = io.open(path, encoding="utf-8").read()
            assert not G._LOCAL.search(text), os.path.basename(path)
            assert "🔴" not in text and "🟢" not in text, os.path.basename(path)


def test_exhibit_set_matches_poc_examples(cap):
    """★作った PoC はどれか 1 つの展示先に掛かっている(収蔵庫に眠らせない)。"""
    c, byid = cap
    pocs = sorted(k for k in byid if k.startswith("poc_"))
    shown = sorted(e["id"] for e in c["exhibits"])
    assert shown == pocs, ("展示に無い PoC / PoC に無い展示: %s"
                           % sorted(set(pocs) ^ set(shown)))


def test_an_animated_figure_is_embedded_as_the_gif_itself(cap):
    """★動く図を JPEG サムネに落とすと、記事では「クリックしないと動かない絵」になる。

    動きが主題の展示でそれをやると意味が消えるので、``.gif`` はそのまま埋める
    (静止の完成形は同じ展示の別の図として並んでいるので、受け皿はある)。
    2026-09-09、回転の展示を足したときに気づいた。

    ★2026-09-25: 記事を棟に割ったので、**どの棟に載っていてもよい**が、
    どこかには載っていなければならない。1 本だけ見ると、別の棟の展示を見落とす。
    """
    c, _byid = cap
    #: 手書きの数学記事に掛かっている展示は、ここでは見ない(生成器が描かないため)。
    external = {w for p in c["meta"]["parts"] if p["kind"] == "external" for w in p["wings"]}
    animated = []
    for ex in c["exhibits"]:
        if ex["wing"] in external:
            continue
        mp = os.path.join(G.ASSETS, ex["id"], "figures.json")
        if not os.path.exists(mp):
            continue
        for fig in json.load(io.open(mp, encoding="utf-8")):
            if fig.get("animated"):
                animated.append((ex["id"], fig["file"]))
    assert animated, "動く図が 1 つも無い(この門は空を通している)"

    for poc_id, name in animated:
        assert G._thumb(poc_id, name) == name, (poc_id, name)

    for lang in ("ja", "en"):
        joined = "\n".join(io.open(p, encoding="utf-8").read() for p in _generated(c, lang))
        for poc_id, name in animated:
            stem = os.path.splitext(name)[0]
            assert name in joined, (lang, poc_id, name, "どの棟にも載っていない")
            assert stem + "_720.jpg" not in joined, (lang, poc_id, "GIF が JPEG に化けている")


# --------------------------------------------------------------------------
# 収蔵番号(2026-09-25)
# --------------------------------------------------------------------------

def _tool():
    """発行道具を読む —— 門は道具の検査関数をそのまま使う(判定を二重に書かない)。"""
    import importlib.util
    p = os.path.join(_ROOT, "tools", "gen_exhibit_numbers.py")
    spec = importlib.util.spec_from_file_location("gen_exhibit_numbers", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _accession_order_breaks(led: dict) -> bool:
    """受入日が番号の順に並んでいないか(= 過去の番号を後から付け替えた跡)。"""
    rows = sorted(led["issued"].values(), key=lambda r: r["no"])
    return any(rows[i]["accessioned"] > rows[i + 1]["accessioned"]
               for i in range(len(rows) - 1))


def test_every_exhibit_has_an_accession_number(cap, ledger):
    """★全展示に番号があり、重複せず、書式が `2026.037` である。"""
    c, _byid = cap
    bad = _tool().check(c["exhibits"], ledger)
    assert not bad, "収蔵台帳に問題がある:\n  " + "\n  ".join(bad)


def test_accession_dates_are_monotone_in_the_number(ledger):
    """★番号は受入順に出ている。過去の番号を付け替えると、ここが崩れる。"""
    assert not _accession_order_breaks(ledger), (
        "受入日が番号の順に並んでいない —— 番号を付け替えた疑いがある")


def test_the_accession_gate_catches_a_renumbering(cap, ledger):
    """★破壊試験: 番号を 2 つ入れ替えたら落ちること。

    入れ替えは重複も欠番も作らないので、**単調性の検査だけ**が頼りになる。
    これが無いと、門が「何も見ていない」場合と区別がつかない。
    """
    c, _byid = cap
    # ★入れ替える 2 件は**受入日が違うもの**を選ぶ。同じ日の 2 件を入れ替えても
    #   何も壊れないので、それで「捕まえた」と言うと破壊試験が嘘になる。
    rows = sorted(ledger["issued"].items(), key=lambda kv: kv[1]["no"])
    pair = next(((a, b) for a, b in zip(rows, rows[1:])
                 if a[1]["accessioned"] != b[1]["accessioned"]), None)
    assert pair is not None, "受入日の違う隣り合う 2 件が無く、破壊試験を作れない"
    (ia, _ra), (ib, _rb) = pair
    broken = copy.deepcopy(ledger)
    broken["issued"][ia]["no"], broken["issued"][ib]["no"] = (
        broken["issued"][ib]["no"], broken["issued"][ia]["no"])
    assert _tool().check(c["exhibits"], broken) or _accession_order_breaks(broken), (
        "★番号の入れ替えを門が捕まえられていない")


def test_a_gap_in_the_numbers_is_explained(ledger):
    """★欠番は `retired` に理由つきで在る(黙って消えない)。"""
    issued = {r["no"] for r in ledger["issued"].values()}
    retired_nos = {r["no"] for r in ledger["retired"].values()}
    for year in sorted({n[:4] for n in issued | retired_nos}):
        used = sorted(int(n[5:]) for n in (issued | retired_nos) if n[:4] == year)
        missing = [i for i in range(1, max(used) + 1) if i not in used]
        assert not missing, (
            "%s に欠番がある: %s —— 外したのなら retired に理由を書くこと"
            % (year, ", ".join("%s.%03d" % (year, i) for i in missing)))
    for eid, rec in ledger["retired"].items():
        assert (rec.get("reason") or "").strip(), (
            "除籍に理由が書かれていない: %s(なぜ外したかは番号より長く要る)" % eid)


def test_the_article_headings_quote_the_ledger(cap, ledger):
    """★記事の見出し番号が台帳と一致する(生成物が台帳から離れていない)。"""
    c, _byid = cap
    no_of = {eid: r["no"] for eid, r in ledger["issued"].items()}
    for p in c["meta"]["parts"]:
        if p["kind"] != "generated":
            continue
        want = sorted(no_of[e["id"]] for e in c["exhibits"] if e["wing"] in p["wings"])
        for lang in ("ja", "en"):
            path = G.part_path(p["slug"], lang)
            got = sorted(_HEAD_NO.findall(io.open(path, encoding="utf-8").read()))
            assert got == want, (
                "%s の見出し番号が台帳と違う\n  記事にだけ在る: %s\n  台帳にだけ在る: %s"
                % (os.path.basename(path), sorted(set(got) - set(want)),
                   sorted(set(want) - set(got))))


# --------------------------------------------------------------------------
# 棟の所属(2026-09-25)
# --------------------------------------------------------------------------

def _check_parts(c: dict) -> None:
    """全翼がちょうど 1 つの棟に属する。破壊試験から呼べるよう関数に出す。"""
    home = {}
    for p in c["meta"]["parts"]:
        for w in p.get("wings", []):
            assert w not in home, "翼 %s が %s と %s の両方に在る" % (w, home[w], p["id"])
            home[w] = p["id"]
    allw = {w["id"] for w in c["wings"]}
    orphan = sorted(allw - set(home))
    assert not orphan, "どの棟にも属さない翼: %s(記事から静かに消える)" % orphan
    unknown = sorted(set(home) - allw)
    assert not unknown, "棟が実在しない翼を名指ししている: %s" % unknown


def test_every_exhibit_belongs_to_exactly_one_part(cap):
    """★全展示がちょうど 1 つの棟に属する。

    どの棟にも無い展示は記事から静かに消え、2 つの棟に在る展示は二重掲載になる。
    どちらも例外を出さないので、数えて突きつけるしかない。
    """
    c, _byid = cap
    _check_parts(c)


def test_the_part_gate_catches_a_wing_in_two_parts(cap):
    """★破壊試験: 同じ翼を 2 つの棟に入れたら落ちること。"""
    c, _byid = cap
    broken = copy.deepcopy(c)
    withw = [p for p in broken["meta"]["parts"] if p.get("wings")]
    assert len(withw) >= 2, "棟が 2 つ未満では破壊試験にならない"
    withw[1]["wings"] = list(withw[1]["wings"]) + [withw[0]["wings"][0]]
    with pytest.raises(AssertionError):
        _check_parts(broken)


def test_the_part_gate_catches_an_orphan_wing(cap):
    """★破壊試験: どの棟にも属さない翼を作ったら落ちること。"""
    c, _byid = cap
    broken = copy.deepcopy(c)
    broken["wings"].append({"id": "wing_orphan", "order": 999,
                            "title_ja": "孤児", "title_en": "orphan",
                            "placard_ja": "x", "placard_en": "x"})
    with pytest.raises(AssertionError):
        _check_parts(broken)


def test_the_math_article_and_the_museum_share_no_poc(cap):
    """★数学記事と展示館が同じ PoC を載せていない。

    載せると読者は同じ絵を 2 度見る。2026-09-25 まで **7 件**がこの状態だった ――
    例外は出ず、どちらの記事も単体では正しく見えるので、突き合わせる門が要る。
    """
    c, _byid = cap
    ext = {w for p in c["meta"]["parts"] if p["kind"] == "external" for w in p["wings"]}
    in_museum = {e["id"] for e in c["exhibits"] if e["wing"] not in ext}
    for lang in ("ja", "en"):
        path = os.path.join(_ART, "qiita_math_drawing_%s.md" % lang)
        used = set(re.findall(r"/assets/poc/(poc_[a-z0-9_]+)/",
                              io.open(path, encoding="utf-8").read()))
        dup = sorted(used & in_museum)
        assert not dup, (
            "数学記事(%s)と展示館が同じ PoC を載せている: %s\n"
            "  —— 展示先(wing)を lane_math に移すか、記事から外す" % (lang, dup))


def test_every_exhibit_in_an_external_lane_is_actually_written_up(cap):
    """★手書きの記事へ掛け替えた展示は、その記事に**本当に載っている**。

    掛け替えだけ先にやると、どこにも出ていない収蔵品ができる —— 生成器は描かず、
    手書きの記事にも無い、という状態は例外を出さない。
    """
    c, _byid = cap
    for p in c["meta"]["parts"]:
        if p["kind"] != "external":
            continue
        want = {e["id"] for e in c["exhibits"] if e["wing"] in p["wings"]}
        for lang in ("ja", "en"):
            path = os.path.join(_ART, p["article_" + lang])
            used = set(re.findall(r"/assets/poc/(poc_[a-z0-9_]+)/",
                                  io.open(path, encoding="utf-8").read()))
            gone = sorted(want - used)
            assert not gone, (
                "%s へ掛け替えたのに %s に載っていない: %s\n"
                "  —— 記事に回を書いてから掛け替えること(書けるまでは展示館に残す)"
                % (p["id"], p["article_" + lang], gone))
