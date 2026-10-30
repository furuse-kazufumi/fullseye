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
N = 80

WING_CATEGORY = {
    "wing_industrial": "inspection", "wing_metrology": "inspection",
    "wing_bio": "ct", "wing_astroenv": "thermal",
    "wing_imaging": "inspection", "wing_xyt": "thermal",
    "wing_geometry": "geometry3d", "wing_color": "optics",
    "wing_forensics": "inspection", "wing_threed": "geometry3d",
    "wing_device": "optics",
}
SEE = {
    "ja": "実行した PoC の図で、真値との一致と破綻条件を確認する。",
    "en": "The executed PoC shows agreement with ground truth and where it fails.",
    "zh": "运行 PoC 的图同时显示与真值的一致性及失效条件。",
    "tw": "執行 PoC 的圖同時顯示與真值的一致性及失效條件。",
    "ko": "실행한 PoC 그림에서 참값과의 일치와 실패 조건을 확인한다.",
    "de": "Die ausgeführte PoC zeigt Übereinstimmung mit der Referenz und die Versagensgrenze.",
    "hi": "चलाया गया PoC सत्य मान से मेल और विफलता की सीमा दिखाता है।",
    "fr": "Le PoC exécuté montre l'accord avec la vérité terrain et sa limite d'échec.",
}


def numeric_excerpt(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chosen = [s for s in sentences if re.search(r"\d", s)]
    return " ".join(chosen[:2])[:520].strip()


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
        media = media_for(pid)
        if (pid in old or pid not in all_by_id or e["wing"] not in WING_CATEGORY or
                not media or not re.search(r"\d", e.get("caption_en", ""))):
            continue
        # Industrial and dimensional work first, then retain variety by date/id.
        priority = 0 if e["wing"] in ("wing_industrial", "wing_metrology") else 1
        candidates.append((priority, e.get("added", ""), pid, e, media))
    candidates.sort()
    # Round-robin categories after the industrial half prevents one field from
    # consuming the gallery merely because its IDs sort first.
    industrial = [x for x in candidates if x[0] == 0][:40]
    rest = [x for x in candidates if x not in industrial]
    buckets = {}
    for x in rest:
        buckets.setdefault(x[3]["wing"], []).append(x)
    varied = []
    while len(varied) < N - len(industrial) and any(buckets.values()):
        for wing in sorted(buckets):
            if buckets[wing] and len(varied) < N - len(industrial):
                varied.append(buckets[wing].pop(0))
    chosen = industrial + varied
    if len(chosen) != N:
        raise SystemExit(f"only {len(chosen)} eligible PoCs")
    for _, _, pid, src, media in chosen:
        label = all_by_id[pid]["label"]
        evidence = numeric_excerpt(src["caption_en"])
        item = {
            "id": pid, "category": WING_CATEGORY[src["wing"]], "media": media,
            "motion": media.lower().endswith((".gif", ".mp4")), "label": label,
            "see": dict(SEE), "num": {lang: evidence for lang in d["langs"]},
            "numbers_source": src["numbers_source"],
        }
        d["exhibits"].append(item)
    DATA.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("added", len(chosen))
    for x in chosen:
        print(x[2], x[3]["wing"], x[3]["numbers_source"], x[4])


if __name__ == "__main__":
    main()
