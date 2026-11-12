#!/usr/bin/env python3
"""Refresh the ViEW2026 featured cards that quote the PoC caption ledger.

    py -3.11 tools/build_view2026_featured_batch.py

The set of featured exhibits is ``featured_ids`` in ``docs/view2026/exhibits.json``
(an ordered list; it is the page's tile order).  This tool never adds anything that is
not on that list.  For each listed PoC that is in the caption ledger it refreshes what
must follow the ledger -- the lead, ``numbers_source``, ``ops`` and the verbatim caption
split into ``see`` + ``num`` -- and keeps the hand-edited label, category and figure.
A listed PoC that is not yet a card is created from the ledger.  Every ledger PoC that
is not featured must still be in ``all`` (the full list), or the tool stops.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/view2026/exhibits.json"
LEDGER = ROOT / "docs/articles/exhibits/poc_captions.json"
ASSETS = ROOT / "docs/articles/assets/poc"

WING_CATEGORY = {
    "wing_industrial": "inspection", "wing_metrology": "inspection",
    "wing_bio": "ct", "wing_astroenv": "thermal",
    "wing_imaging": "inspection", "wing_xyt": "thermal",
    "wing_geometry": "geometry3d", "wing_color": "optics",
    "wing_forensics": "inspection", "wing_threed": "geometry3d",
    "wing_device": "optics",
    "lane_drive": "driving", "lane_math": "math",
}
#: 英語のキャプションの中で、日本語のまま引くのが正しい語(路面標示の文字など)。ここに無いかなは訳し忘れとして止める。
QUOTED_JA = {"止まれ"}
_KANA = re.compile(r"[぀-ヿ]+")
#: 本ページ(ja/en)に載せる tier。この tier の展示には、台帳の ``ops``(使った Fullseye の op)を写す。
MAIN_TIERS = ("showcase", "featured")


class BuildError(SystemExit):
    """台帳と目玉の集合が食い違うときに止める(何も書かない)。"""


def caption_for(src: dict, lang: str) -> str:
    """その言語のページに載せるキャプション。日本語以外はかなの漏れを検査し、引用語だけなら日本語の印を付ける。"""
    if lang == "ja":
        return src["caption_ja"]
    text = src["caption_en"]
    runs = set(_KANA.findall(text))
    if not runs:
        return text
    stray = {r for r in runs if not any(r in q for q in QUOTED_JA)}
    if stray:
        raise BuildError("%s: caption_en に訳し忘れのかな %s —— 台帳 poc_captions.json を直すこと" % (src["id"], sorted(stray)))
    return text + " _(ja)_"


def lead_for(src: dict, lang: str) -> str:
    """Use a reviewed lead when present; otherwise show the full caption."""
    key = "lead_ja" if lang == "ja" else "lead_en"
    return src.get(key, "").strip() or caption_for(src, lang)


def media_for(pid: str) -> str | None:
    p = ASSETS / pid / "figures.json"
    if not p.is_file():
        return None
    figures = json.loads(p.read_text(encoding="utf-8"))
    images = [f for f in figures if str(f.get("file", "")).lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".mp4"))]
    if not images:
        return None
    scored = sorted(images, key=lambda f: (not bool(re.search(r"\d", f.get("caption", ""))), -len(f.get("caption", ""))))
    return scored[0]["file"]


def _new_card(src: dict, all_row: dict, langs: list[str]) -> dict:
    """台帳から目玉のカードを 1 枚作る(featured_ids に新しく足した PoC だけ)。"""
    pid = src["id"]
    media = media_for(pid)
    if src["wing"] not in WING_CATEGORY or not media or not re.search(r"\d", src.get("caption_en", "")):
        raise BuildError("%s: 目玉にできない(分類の無い翼・図が無い・数が無い)" % pid)
    return {
        "id": pid, "category": WING_CATEGORY[src["wing"]], "media": media,
        "motion": media.lower().endswith((".gif", ".mp4")), "label": copy.deepcopy(all_row["label"]),
        "lead": {}, "see": {l: caption_for(src, l) for l in langs}, "num": {l: "" for l in langs},
        "numbers_source": src["numbers_source"], "youtube_url": "",
        "tier": "more",          # 本ページへ上げるかは、人が選んで tier を直す(この道具は決めない)
    }


def rebuild(d: dict, ledger: list[dict]) -> dict:
    """``d`` を書き換えずに、目玉を featured_ids どおりに作り直した写しを返す。"""
    d = copy.deepcopy(d)
    langs = d["langs"]
    featured = d.get("featured_ids")
    if not featured or len(featured) != len(set(featured)):
        raise BuildError("exhibits.json の featured_ids が無いか重複している(目玉の集合の正本)")
    ledger_by_id = {e["id"]: e for e in ledger}
    all_by_id = {e["id"]: e for e in d["all"]}
    previous = {e["id"]: e for e in d["exhibits"]}
    # ★2026-11-08: 以前は台帳の PoC を「手書きの見どころかこの一括のどちらかに必ず載せる」ために、
    #   載っていない PoC を全部目玉へ足していた。目玉を約 40 件に絞った(ユーザーの決定)ので、回すと
    #   285 件に戻ってしまう。目玉は featured_ids だけ、それ以外は all に在ることを確かめる側に替えた。
    out = []
    for pid in featured:
        src = ledger_by_id.get(pid)
        item = copy.deepcopy(previous[pid]) if pid in previous else None
        if item is None:
            if src is None or pid not in all_by_id:
                raise BuildError("%s: featured_ids に在るが、カードも台帳の行も無い" % pid)
            item = _new_card(src, all_by_id[pid], langs)
        if src is not None:
            item["lead"] = {l: lead_for(src, l) for l in langs}
            if "numbers_source" in item:
                item["numbers_source"] = src["numbers_source"]
                for l in langs:
                    cap = caption_for(src, l)
                    # 手で切った see / num はキャプションが変わっていなければそのまま。変わっていれば全文を see へ。
                    if item["see"][l] + item["num"][l] != cap:
                        item["see"][l], item["num"][l] = cap, ""
            if item.get("tier") in MAIN_TIERS and src.get("ops"):
                item["ops"] = src["ops"]
        out.append(item)
    d["exhibits"] = out
    left = sorted(e["id"] for e in ledger if e["id"] not in all_by_id)
    if left:
        raise BuildError("台帳の PoC が all(ぜんぶ見る)に無い: %s" % left)
    return d


def main() -> None:
    d = json.loads(DATA.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))["exhibits"]
    new = rebuild(d, ledger)
    DATA.write_text(json.dumps(new, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("featured", len(new["exhibits"]))


if __name__ == "__main__":
    main()
