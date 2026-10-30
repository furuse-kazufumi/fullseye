#!/usr/bin/env python3
"""Promote evidence-bearing PoCs into the ViEW2026 featured gallery.

The selection and numeric copy come from the reviewed PoC caption ledger.  This
keeps the large gallery reproducible instead of maintaining 80 hand-copied
numbers in a second file.
"""
from __future__ import annotations

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
_KANA = re.compile(r"[\u3040-\u30ff]+")


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
        raise SystemExit("%s: caption_en に訳し忘れのかな %s —— 台帳 poc_captions.json を直すこと" % (src["id"], sorted(stray)))
    return text + " _(ja)_"


#: 翼の対応では入らない分類・見せたい図の上書き(2026-10-31: 仮想工場のロボット 2 本は「ロボット」の分類で、
#: かご間ピッキングは MuJoCo の実描画の GIF を見せる)。
CATEGORY_OVERRIDE = {"poc_tote_picking_tactile": "robotics", "poc_fingervision_benchmark": "robotics"}
MEDIA_OVERRIDE = {"poc_tote_picking_tactile": "06_trial_tactile_rescue.gif"}


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


def main() -> None:
    d = json.loads(DATA.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))["exhibits"]
    all_by_id = {e["id"]: e for e in d["all"]}
    # Re-running replaces this generated batch and preserves hand-curated cards.
    d["exhibits"] = [e for e in d["exhibits"] if "numbers_source" not in e]
    old = {e["id"] for e in d["exhibits"]}
    candidates = []
    for e in ledger:
        pid = e["id"]
        media = MEDIA_OVERRIDE.get(pid) or media_for(pid)
        if (pid in old or pid not in all_by_id or e["wing"] not in WING_CATEGORY or
                not media or not re.search(r"\d", e.get("caption_en", ""))):
            continue
        # Industrial and dimensional work first, then retain variety by date/id.
        priority = 0 if e["wing"] in ("wing_industrial", "wing_metrology") else 1
        candidates.append((priority, e.get("added", ""), pid, e, media))
    candidates.sort()
    # Round-robin categories after the industrial half prevents one field from
    # consuming the gallery merely because its IDs sort first.
    industrial = [x for x in candidates if x[0] == 0]
    rest = [x for x in candidates if x not in industrial]
    buckets = {}
    for x in rest:
        buckets.setdefault(x[3]["wing"], []).append(x)
    varied = []
    while any(buckets.values()):
        for wing in sorted(buckets):
            if buckets[wing]:
                varied.append(buckets[wing].pop(0))
    chosen = industrial + varied
    # ★2026-10-30: 「出来れば全 PoC を載せたい」。初版は 80 本で切っていた。台帳の PoC は手書きの見どころか
    #   この一括のどちらかに必ず載る —— 載らない PoC があれば理由(図が無い・数が無い・分類の無い翼)ごと止める。
    left = [e["id"] for e in ledger if e["id"] not in old and e["id"] not in {x[2] for x in chosen}]
    if left:
        raise SystemExit("台帳の PoC が見どころに載らない: %s" % left)
    for _, _, pid, src, media in chosen:
        label = all_by_id[pid]["label"]
        captions = {lang: caption_for(src, lang) for lang in d["langs"]}
        item = {
            "id": pid, "category": CATEGORY_OVERRIDE.get(pid, WING_CATEGORY[src["wing"]]), "media": media,
            "motion": media.lower().endswith((".gif", ".mp4")), "label": label,
            "see": captions, "num": {lang: "" for lang in d["langs"]},
            "numbers_source": src["numbers_source"], "youtube_url": "",
        }
        d["exhibits"].append(item)
    DATA.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("added", len(chosen))
    for x in chosen:
        print(x[2], x[3]["wing"], x[3]["numbers_source"], x[4])


if __name__ == "__main__":
    main()
