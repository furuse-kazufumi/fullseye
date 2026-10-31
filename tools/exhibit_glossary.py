#!/usr/bin/env python3
"""展示台帳の冒頭から専門用語を拾う共通部品。

辞書の公開部分は ``exhibit_glossary_source.json`` に置く。同綴りの SAM だけは
展示 ID で意味を分け、題、説明の第1文、第2文の順に最大6語を返す。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(__file__).with_name("exhibit_glossary_source.json")
GLOSSARY = ROOT / "docs" / "articles" / "exhibits" / "glossary.json"
LEDGER = ROOT / "docs" / "articles" / "exhibits" / "poc_captions.json"

# terms_v1 を作った候補辞書を移し、依頼で挙げられた候補を追加したもの。
# source JSON に未収録の候補も、台帳の冒頭に現れた時点で門が名指しする。
CANDIDATE_TERMS = {
    "zernike": ["Zernike", "ゼルニケ"],
    "strehl": ["Strehl", "ストレール"],
    "nyquist": ["Nyquist", "ナイキスト"],
    "mtf50": ["MTF50"],
    "airy": ["Airy", "エアリー"],
    "rayleigh": ["Rayleigh criterion", "Rayleigh resolution", "レイリー限界", "レイリー基準"],
    "brewster": ["Brewster angle", "Brewster's angle", "ブリュースター角"],
    "stokes": ["Stokes vector", "Stokes parameters", "ストークスベクトル", "ストークスパラメータ"],
    "jones": ["Jones matrix", "Jones vector", "ジョーンズ行列", "ジョーンズベクトル"],
    "hough": ["Hough", "ハフ変換"],
    "ransac": ["RANSAC", "random sample consensus"],
    "icp": ["ICP", "iterative closest point"],
    "sfm": ["SfM", "structure from motion"],
    "dic": ["DIC", "digital image correlation"],
    "insar": ["InSAR", "interferometric synthetic aperture radar"],
    "oct": ["OCT", "optical coherence tomography", "光干渉断層"],
    "pod": ["POD", "probability of detection", "検出確率"],
    "a90_95": ["a90/95", "a90/95"],
    "gauge_rr": ["Gauge R&R", "Gage R&R", "ゲージ R&R"],
    "auroc": ["AUROC", "area under the ROC"],
    "roc": ["ROC", "receiver operating characteristic"],
    "iou": ["IoU", "intersection over union"],
    "hausdorff": ["Hausdorff", "ハウスドルフ"],
    "kirsch": ["Kirsch"],
    "hondros": ["Hondros"],
    "bruggeman": ["Bruggeman", "ブルッゲマン"],
    "beer_lambert": ["Beer-Lambert", "Beer–Lambert", "ベール–ランベルト", "ランベルト–ベール"],
    "emva_1288": ["EMVA 1288", "EMVA"],
    "gum": ["GUM", "Guide to the Expression of Uncertainty in Measurement"],
    "clopper_pearson": ["Clopper-Pearson", "Clopper–Pearson"],
    "wilson": ["Wilson interval", "Wilson score", "Wilson 95", "Wilson 95 %", "Wilson 95%"],
    "jeffreys": ["Jeffreys interval", "Jeffreys prior"],
    "talbot_effect": ["Talbot effect", "Talbot distance", "Talbot length", "fractional Talbot", "タルボ効果", "タルボ距離", "分数タルボ"],
    "talbot_carpet": ["Talbot carpet", "タルボ絨毯"],
    "lau": ["Lau", "ラウ干渉"],
    "moire": ["Moiré", "Moire", "モアレ"],
    "takeda": ["Takeda", "武田法"],
    "lock_in": ["lock-in", "lock in", "ロックイン"],
    "debye_rings": ["Debye ring", "Debye rings", "デバイ環"],
    "thon_rings": ["Thon ring", "Thon rings", "Thon リング", "ソンリング"],
    "ctf": ["CTF", "contrast transfer function"],
    "kelvin_wake": ["Kelvin wake", "Kelvin ship wave", "ケルビン航跡"],
    "gsd": ["GSD", "ground sample distance"],
}

_ENDS = re.compile(r"[\u3002\uff01\uff1f]|[.!?](?=\s+(?:[A-Z0-9*\u2605\u3010]|$))")


def sentences(text: str) -> list[str]:
    """小数点を文末と誤認せず、日本語と英語の文を分ける。"""
    out, start = [], 0
    for m in _ENDS.finditer(text):
        out.append(text[start:m.end()].strip())
        start = m.end()
    if start < len(text):
        out.append(text[start:].strip())
    return [s for s in out if s]


def opening_text(exhibit: dict, lang: str) -> tuple[str, str, str]:
    """優先順位どおりの (題、第1文、第2文)。"""
    suffix = "ja" if lang == "ja" else "en"
    ss = sentences(exhibit["caption_" + suffix])
    return exhibit["title_" + suffix], *(ss + ["", ""])[:2]


def load_source() -> dict:
    return json.loads(SOURCE.read_text(encoding="utf-8"))


def load_glossary() -> dict:
    return json.loads(GLOSSARY.read_text(encoding="utf-8"))


def _allowed(term_id: str, exhibit_id: str) -> bool:
    if term_id == "sam_spectral":
        return exhibit_id in {"poc_recycling_sorting", "poc_hyperspectral_foreign_matter"}
    if term_id == "sam_ultrasonic":
        return exhibit_id == "poc_sam_hybrid_bonding_voids"
    return True


def _span(text: str, aliases: list[str]) -> tuple[int, int] | None:
    """最初の一致位置。同位置なら長い表記を優先する。"""
    best = None
    for alias in aliases:
        pattern = r"(?<![A-Za-z0-9_])" + re.escape(alias) + r"(?![A-Za-z0-9_])"
        letters = "".join(c for c in alias if c.isalpha() and c.isascii())
        flags = 0 if letters and len(letters) <= 8 and letters.upper() == letters else re.IGNORECASE
        m = re.search(pattern, text, flags)
        if m and (best is None or (m.start(), -len(alias)) < (best[0], -best[1])):
            best = (m.start(), len(alias))
    return best


def candidate_hits(exhibit: dict, lang: str) -> list[str]:
    """拡張候補辞書で冒頭を走査した term_id。未定義語を検出する門用。"""
    candidates = dict(CANDIDATE_TERMS)
    for term_id, entry in load_source().items():
        candidates.setdefault(term_id, entry["match"])
    found = []
    for segment in opening_text(exhibit, lang):
        ranked = []
        for term_id, aliases in candidates.items():
            if term_id in found or not _allowed(term_id, exhibit["id"]):
                continue
            hit = _span(segment, aliases)
            if hit:
                ranked.append((hit[0], -hit[1], term_id))
        found.extend(x[2] for x in sorted(ranked))
    return found


def terms_for_exhibit(exhibit: dict, lang: str, glossary: dict | None = None,
                      limit: int = 6) -> list[tuple[str, dict]]:
    """題、第1文、第2文の順に見つかる公開用語を返す。"""
    glossary = glossary or load_glossary()
    found = []
    for segment in opening_text(exhibit, lang):
        ranked = []
        for term_id, entry in glossary.items():
            if term_id in found or not _allowed(term_id, exhibit["id"]):
                continue
            hit = _span(segment, entry["match"])
            if hit:
                ranked.append((hit[0], -hit[1], term_id))
        found.extend(x[2] for x in sorted(ranked))
        if len(found) >= limit:
            break
    return [(term_id, glossary[term_id]) for term_id in found[:limit]]


def glossary_line(exhibit: dict, lang: str, glossary: dict | None = None) -> str:
    """ページへ載せる1行。将来は entry[lang] があればそれを使う。"""
    terms = terms_for_exhibit(exhibit, lang, glossary)
    if not terms:
        return ""
    label = "用語" if lang == "ja" else "Terms"
    body = []
    for _term_id, entry in terms:
        name = entry["match"][0]
        desc = entry.get(lang) or entry["en"]
        body.append("%s — %s" % (name, desc))
    return "%s: %s" % (label, "; ".join(body))
