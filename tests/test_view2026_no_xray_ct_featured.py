# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""X 線 CT を ViEW2026 のページの目玉・代表の位置に置かない門(2026-11-15)。

ユーザーの決まり: X 線 CT は Fullseye の主役・代表として扱わない(会社の知財と分けるため)。
PoC 自体と、おまけページ(``more.md``)・全体の一覧(``all``、「ぜんぶ見る」)への掲載は残す。
この門が見るのは次の 3 つ:

* 目玉(``tier`` が showcase / featured、本ページに載る展示)に X 線 CT の PoC が無い。
* 生成した本ページ(8 言語の ``index.md``)が X 線 CT の PoC の図・サムネイルを引いていない。
* おまけページの分類ごとの一覧と「ぜんぶ見る」の群で、X 線 CT の PoC が先頭に来ない
  (分類 ``ct`` = X 線 CT そのものの分類の中は除く)。

X 線 CT かどうかは、分類 ``ct``・id(``poc_ct_*`` / ``*_ct_*`` / ``*_ct`` / ``cbct``)・日英の題の
語 ``CT`` のどれかで決める。OCT(光の干渉による断層)は語境界で外れる(``\\bCT\\b`` は ``OCT`` に当たらない)。

★``featured_ids`` は目玉の 20 本ではなく、カードを持つ展示 50 本の並びの正本(``exhibits`` の id の並びと
一致することを ``tools/gen_view2026_pages.py`` が検査する)。目玉かどうかは ``tier`` で決まるので、
この門も ``tier`` を見る。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = ROOT / "docs" / "view2026"
DATA = VIEW / "exhibits.json"
MAIN_TIERS = ("showcase", "featured")      # tools/gen_view2026_pages.py の MAIN_TIERS と同じ
_ID = re.compile(r"(^poc_ct_|_ct_|_ct$|cbct)")
_LABEL = re.compile(r"\bCT\b")


def _data() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def is_xray_ct(row: dict) -> bool:
    """展示(exhibits)か一覧(all)の 1 行が X 線 CT の PoC か。"""
    label = row.get("label", {})
    text = "%s %s" % (label.get("ja", ""), label.get("en", ""))
    return row.get("category") == "ct" or bool(_ID.search(row["id"])) or bool(_LABEL.search(text))


def test_the_detector_finds_the_known_xray_ct_pocs():
    """探針が空振りしない: 今ある X 線 CT の PoC を拾い、CT でない OCT は拾わない。"""
    d = _data()
    rows = {r["id"]: r for r in d["all"] + d["exhibits"]}      # 分類(category)はカードの側にだけある
    found = sorted({r["id"] for r in d["exhibits"] + d["all"] if is_xray_ct(r)})
    for pid in ("poc_real_walnut_cbct", "poc_ct_casting_sparse_views", "poc_weld_radiograph_porosity",
                "poc_am_thermal_to_ct", "poc_ct_fidelity"):
        assert pid in found, (pid, found)
    assert "poc_industrial_oct" in rows
    assert not is_xray_ct(rows["poc_industrial_oct"])


def test_no_xray_ct_poc_is_a_main_exhibit():
    """目玉(showcase / featured)に X 線 CT の PoC を置かない。"""
    d = _data()
    main = [e for e in d["exhibits"] if e.get("tier") in MAIN_TIERS]
    assert len(main) >= 10                  # 目玉の集合が空・縮んだ状態で通らないように
    bad = [(e["id"], e["tier"]) for e in main if is_xray_ct(e)]
    assert bad == [], "X 線 CT の PoC が目玉にある(tier を more に下げる): %s" % bad


def test_the_xray_ct_pocs_stay_listed():
    """下げても消さない: カードはおまけページに、PoC は全体の一覧(all)に残る。"""
    d = _data()
    all_ids = {a["id"] for a in d["all"]}
    cards = {e["id"]: e for e in d["exhibits"]}
    assert "poc_real_walnut_cbct" in all_ids
    assert cards["poc_real_walnut_cbct"]["tier"] == "more"
    missing = sorted(e["id"] for e in d["exhibits"] if is_xray_ct(e) and e["id"] not in all_ids)
    assert missing == []


def _page(lang: str) -> Path:
    return VIEW / "index.md" if lang == "ja" else VIEW / lang / "index.md"


def test_the_generated_main_pages_do_not_show_xray_ct():
    """生成した本ページ(8 言語)が X 線 CT の PoC の図もサムネイルも引かない。目玉の展示は全部引いている。"""
    d = _data()
    ct_ids = sorted({r["id"] for r in d["exhibits"] + d["all"] if is_xray_ct(r)})
    main_ids = [e["id"] for e in d["exhibits"] if e.get("tier") in MAIN_TIERS]
    assert len(ct_ids) >= 5 and len(main_ids) >= 10
    assert len(d["langs"]) == 8
    shown_ct, not_shown_main = [], []
    for lang in d["langs"]:
        text = _page(lang).read_text(encoding="utf-8")
        shown_ct += [(lang, pid) for pid in ct_ids
                     if "/poc/%s/" % pid in text or "thumbs/%s.jpg" % pid in text]
        not_shown_main += [(lang, pid) for pid in main_ids if "/poc/%s/" % pid not in text]
    assert not_shown_main == [], "目玉の展示が本ページに出ていない(生成し直しが要る): %s" % not_shown_main[:5]
    assert shown_ct == [], "本ページが X 線 CT の PoC を出している: %s" % shown_ct[:5]


def test_no_xray_ct_poc_heads_a_category_or_group():
    """おまけページの分類ごとの一覧と「ぜんぶ見る」の群の先頭に X 線 CT を置かない(分類 ct の中は除く)。"""
    d = _data()
    main_ids = {e["id"] for e in d["exhibits"] if e.get("tier") in MAIN_TIERS}
    rest = [e for e in d["exhibits"] if e["id"] not in main_ids]
    heads = {}
    for e in rest:
        heads.setdefault(("category", e["category"]), e)
    # 「ぜんぶ見る」は all から本ページの展示を除いて群ごとに並べる(gen_view2026_pages.build_more)。
    # 除く前の並びの先頭も見る(本ページの展示が群の先頭なら、除いた後の先頭は 2 番目になる)。
    for kind, rows in (("group", d["all"]), ("group_on_more", [a for a in d["all"] if a["id"] not in main_ids])):
        for a in rows:
            heads.setdefault((kind, a["group"]), a)
    assert len(heads) >= 10
    bad = sorted((kind, key, row["id"]) for (kind, key), row in heads.items()
                 if key != "ct" and is_xray_ct(row))
    assert bad == [], "X 線 CT の PoC が分類・群の先頭にある(後ろへ下げる): %s" % bad
