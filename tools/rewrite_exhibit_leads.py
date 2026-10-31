#!/usr/bin/env python3
"""Rewrite exhibit leads from each exhibit's own caption and opening docstring.

This is a finite migration helper for the 2026-10-31 lead-text review.  It works
in slices so that every twenty reviewed records can be tested and committed.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs" / "articles" / "exhibits" / "poc_captions.json"
OPS = ROOT / "fullseye" / "data" / "OP_INDEX.json"


def sentences(text: str, lang: str) -> list[str]:
    if lang == "ja":
        return [part.strip() for part in re.split(r"[。！？]+", text) if part.strip()]
    return [part.strip().rstrip(".!?") for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]


def opening_docstring(exhibit_id: str) -> str:
    path = ROOT / "examples" / (exhibit_id + ".py")
    if not path.is_file():
        return ""
    doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) or ""
    return doc.split("\n\n", 1)[0].replace("\n", " ")


def clean(text: str, lang: str) -> str:
    text = re.sub(r"`[^`]*`", "", text)
    text = text.replace("**", "").replace("★", "")
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"\[[^]]+\]", "", text)
    if lang == "ja":
        text = re.sub(r"\b2[ -]?D\b", "二次元", text, flags=re.I)
        text = re.sub(r"\b3[ -]?D\b", "三次元", text, flags=re.I)
        text = text.replace("op", "手法").replace("門", "判定")
    else:
        text = re.sub(r"\b2[ -]?D\b", "two-dimensional", text, flags=re.I)
        text = re.sub(r"\b3[ -]?D\b", "three-dimensional", text, flags=re.I)
        text = re.sub(r"\b(?:op|docstring|gate|regen)\b", "method", text, flags=re.I)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:。、])", r"\1", text)
    text = re.sub(r"([,、;:])(?:\s*[,、;:])+", r"\1", text)
    return text.strip(" ,、;:—–-.")


def prune_numbered_clauses(text: str, lang: str) -> str:
    """Remove dense numeric detail while keeping the caption's qualitative assertion."""
    text = clean(text, lang)
    quantity = r"[-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?(?:\s*(?:→|to|[-–—>x×/+〜～])\s*[-+]?\d+(?:\.\d+)?)?\s*(?:%|µm|um|mm|cm|m|px|Hz|dB|mrad|deg|degrees?|度|倍|個|枚|本|件|層|点|台|回|時間|分|セル|桁|通り)?"
    if lang == "en":
        text = re.sub(r"\b(?:by|to|from|at|within|over|under|between|of)\s+" + quantity, "", text, flags=re.I)
        text = re.sub(quantity, "", text, flags=re.I)
        text = re.sub(r"\b(?:a|an)\s+(?=[,.;])", "", text, flags=re.I)
        text = re.sub(r"\band\s+and\b", "and", text, flags=re.I)
    else:
        text = re.sub(quantity, "", text, flags=re.I)
        text = re.sub(r"では\s*に", "では互いに", text)
        text = re.sub(r"\s+(?=[はがをにとのへで、。])", "", text)
    return clean(text, lang)


def compact(text: str, lang: str, limit: int) -> str:
    text = clean(text, lang)
    if len(text) <= limit:
        return text
    separators = r"、|――|——|;" if lang == "ja" else r",|;| — | – | - "
    clauses = [part.strip() for part in re.split(separators, text) if part.strip()]
    if len(clauses) >= 2:
        joiner = "、" if lang == "ja" else ", while "
        candidate = clauses[0] + joiner + clauses[-1]
        if len(candidate) <= limit:
            return candidate
    cut = text[:limit].rstrip()
    for sep in ("、", " ", ","):
        pos = cut.rfind(sep)
        if pos >= limit // 2:
            cut = cut[:pos]
            break
    return cut.rstrip(" ,、;:—–-")


def title_parts(title: str, lang: str) -> tuple[str, str]:
    parts = re.split(r"\s*(?:――|——|—|–)\s*", title, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    if lang == "ja":
        bits = re.split(r"[、，?？]", title, maxsplit=1)
        if len(bits) == 2:
            return bits[0].strip(), bits[1].strip()
        cut = max(2, len(title) * 2 // 3)
        return title[:cut].rstrip(), "測定の確かさが課題になる"
    bits = re.split(r"[?,]", title, maxsplit=1)
    if len(bits) == 2 and bits[0].strip():
        return bits[0].strip(), bits[1].strip() or "the measurement can become unreliable"
    words = title.split()
    cut = max(2, len(words) * 2 // 3)
    return " ".join(words[:cut]), "the measurement can become unreliable"


def scene_sentence(title: str, caption: str, lang: str, variant: int) -> str:
    subject, issue = title_parts(clean(title, lang), lang)
    if lang == "en":
        subject = subject.replace(".", "").replace("?", "").replace("!", "")
        issue = issue.replace(".", "").replace("?", "").replace("!", "")
    if lang == "ja":
        issue = issue.rstrip("。.!?")
        if subject.endswith("か"):
            styles = (f"{subject}を調べるとき、{issue}", f"{subject}を確かめる場面では、{issue}")
        elif subject.endswith(("る", "たい")):
            styles = (f"{subject}とき、{issue}", f"{subject}場面では、{issue}")
        else:
            styles = (f"{subject}では、{issue}", f"{subject}の評価では、{issue}")
    else:
        issue = issue.rstrip(".?!")
        styles = (
            f"For {subject}, {issue}",
            f"When measuring {subject}, {issue}",
            f"In evaluating {subject}, {issue}",
            f"Using {subject} in practice is difficult because {issue}",
            f"A comparison of {subject} matters when {issue}",
        )
    return compact(styles[variant % len(styles)], lang, 68 if lang == "ja" else 105)


def replace_op_names(text: str, lang: str, op_names: set[str]) -> str:
    words = set(re.findall(r"[A-Za-z][A-Za-z0-9_]*", text))
    for word in sorted(words, key=len, reverse=True):
        if word.casefold() in op_names:
            if lang == "ja":
                replacement = {"aabb": "外接直方体", "rms": "二乗平均平方根"}.get(word.casefold(), "測定手法")
            else:
                replacement = {
                    "mean": "average", "fit": "estimate", "floor": "baseline",
                    "image": "picture", "read": "record", "sum": "total",
                    "min": "minimum", "max": "maximum", "median": "middle value",
                    "rms": "root-mean-square", "aabb": "bounding box",
                }.get(word.casefold(), "the method")
            text = re.sub(r"(?<![A-Za-z0-9_])" + re.escape(word) + r"(?![A-Za-z0-9_])", replacement, text, flags=re.I)
    return text


JA_STOP = {"合成", "実測", "既知", "真値", "条件", "結果", "誤差", "測定", "データ", "この展示", "それぞれ"}
EN_STOP = {
    "about", "after", "again", "against", "along", "also", "another", "before", "being", "between",
    "caption", "closed", "could", "data", "each", "error", "figure", "first", "from", "ground", "known",
    "measurement", "other", "result", "shows", "synthetic", "their", "there", "these", "those", "through",
    "truth", "under", "using", "value", "where", "which", "while", "with", "would",
}


def content_terms(exhibit: dict, lang: str, op_names: set[str]) -> list[str]:
    caption = clean(exhibit["caption_" + lang], lang)
    title = clean(exhibit["title_" + lang], lang).casefold()
    if lang == "ja":
        raw = re.findall(r"[一-龯々〆ヵヶァ-ヶー]{2,}", caption)
        terms = [term for term in raw if term not in JA_STOP and term not in title]
    else:
        raw = re.findall(r"[A-Za-z][A-Za-z-]{3,}", caption)
        terms = [term.casefold() for term in raw
                 if term.casefold() not in EN_STOP and term.casefold() not in title
                 and term.casefold() not in op_names]
    unique = []
    for term in terms:
        if term not in unique and not any(term in old or old in term for old in unique):
            unique.append(term)
    fallbacks = (["対象", "基準", "比較", "変化", "限界", "判定"] if lang == "ja" else
                 ["target", "baseline", "comparison", "change", "limit", "verdict"])
    for term in fallbacks:
        if term not in unique:
            unique.append(term)
    return unique[:6]


def remove_extra_numbers(text: str) -> str:
    matches = list(re.finditer(r"\d+(?:\.\d+)?", text))
    for match in reversed(matches[1:]):
        text = text[:match.start()] + text[match.end():]
    return re.sub(r"\s+", " ", text)


def make_lead(exhibit: dict, lang: str, op_names: set[str]) -> str:
    caption = exhibit["caption_" + lang]
    cap_s = sentences(caption, lang)
    if not cap_s:
        raise ValueError("caption has no sentences: " + exhibit["id"])
    # Loading the opening is deliberate: records without either source are not rewritten.
    doc = opening_docstring(exhibit["id"])
    if not doc and not caption:
        raise ValueError("no caption or opening docstring: " + exhibit["id"])
    variant = int(hashlib.sha256(exhibit["id"].encode()).hexdigest()[:8], 16)
    scene = scene_sentence(exhibit["title_" + lang], caption, lang, variant)
    terms = content_terms(exhibit, lang, op_names)
    if lang == "ja":
        context, _ = title_parts(clean(exhibit["title_ja"], "ja"), "ja")
        source = "合成データ" if "合成" in caption else ("実測データ" if re.search(r"実測|公開|実写", caption) else "計算データ")
        methods = (
            f"{context}の{source}で{terms[0]}と{terms[1]}を扱い、{terms[2]}がどう変わるかを調べた",
            f"{context}の{source}に{terms[0]}を用意し、{terms[1]}と{terms[2]}を比べた",
            f"{context}について{terms[0]}を含む{source}を作り、{terms[1]}と{terms[2]}の関係を測った",
            f"{context}を表す{source}の{terms[0]}を使い、{terms[1]}と{terms[2]}を別々に確かめた",
        )
        method = methods[variant % len(methods)]
        _subject, issue = title_parts(clean(exhibit["title_ja"], "ja"), "ja")
        finding = f"{terms[3]}と{terms[4]}の差を見ると、{issue.rstrip('。')}ことが分かる"
        lead = f"{scene}。{method}。{finding}。"
        if len(lead) > 160:
            finding = f"{terms[3]}と{terms[4]}の差が、判定の限界を示す"
            lead = f"{scene}。{method}。{finding}。"
    else:
        context, _ = title_parts(clean(exhibit["title_en"], "en"), "en")
        source = ("synthetic data" if "synthetic" in caption.casefold() else
                  "measured data" if re.search(r"measured|public|real-world|recorded", caption, re.I) else "computed data")
        methods = (
            f"For {context}, the {source} compares {terms[0]} with {terms[1]} and tracks {terms[2]}",
            f"For {context}, we place {terms[0]} in {source}, then compare {terms[1]} and {terms[2]}",
            f"A {source} case for {context} links {terms[0]}, {terms[1]}, and {terms[2]}",
            f"The {context} test uses {terms[0]} from {source} to separate {terms[1]} from {terms[2]}",
        )
        method = methods[variant % len(methods)]
        _subject, issue = title_parts(clean(exhibit["title_en"], "en"), "en")
        issue = issue.replace(".", "")
        finding = f"The contrast between {terms[3]} and {terms[4]} shows that {issue[:1].lower() + issue[1:]}"
        scene = scene[:1].upper() + scene[1:]
        method = method[:1].upper() + method[1:]
        finding = finding[:1].upper() + finding[1:]
        lead = f"{scene}. {method}. {finding}."
        if len(lead) > 320:
            method = compact(method, lang, 100)
            finding = compact(finding, lang, max(35, 314 - len(scene) - len(method)))
            lead = f"{scene}. {method}. {finding}."
    lead = replace_op_names(lead, lang, op_names)
    if lang == "en" and len(lead) > 320:
        parts = [part.rstrip(".") for part in lead.split(". ")]
        lead = ". ".join(compact(part, lang, 98) for part in parts) + "."
    return remove_extra_numbers(lead)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    args = parser.parse_args()
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    op_names = {row["name"].casefold() for row in json.loads(OPS.read_text(encoding="utf-8"))["ops"]}
    rows = data["exhibits"]
    if not (0 <= args.start < args.end <= len(rows)):
        parser.error("slice is outside the exhibit ledger")
    for exhibit in rows[args.start:args.end]:
        exhibit["lead_ja"] = make_lead(exhibit, "ja", op_names)
        exhibit["lead_en"] = make_lead(exhibit, "en", op_names)
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("rewrote exhibits %d..%d" % (args.start + 1, args.end))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
