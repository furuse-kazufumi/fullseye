# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""入口の頭の文が、名刺の 3 語(画像検査・三次元計測・物理シミュレーション)で始まることの門(2026-11-15)。

利用者の判断(2026-11-15): 紹介ページと README の頭の文を、名刺の表の文言にそろえる。
名刺の 3 語は論文の題「型付き演算子と物理シミュレーションに基づく画像検査・三次元計測基盤」と同じ語で、
Fullseye で何ができるか(柱)を言う。型を持つ op・物理シミュレーションの真値・MCP / RAG は
それを実現する土台なので、頭の文の 2 文目に回す。

ここで見ること:

* 日本語は名刺の字のまま(「3D 計測」「シミュレーション」などの言い換えは通さない)。
* ほかの言語は論文の題の訳(exhibits.json の ui.title_tr)と同じ語を、名刺の順で並べる。
* 1 文目の 3 語の直後に区切りや接続語を続けて、4 つ目の柱を足さない。
* 置き場所は頭: リポジトリの README はバッジの直後の段落、サイトのトップ(docs/README*.md)は
  言語の行の直後の段落、ViEW2026 のページ(8 言語)は冒頭の紹介の段落の 1 文目、
  PyPI の一行の説明は書き出し、CITATION.cff と .zenodo.json の要旨は 1 文目。
* 頭の範囲は README と ViEW2026 は段落全体、PyPI は一行全体、引用の要旨は最初の 2 文。
  そこに型を持つ op・真値・MCP / RAG の土台があり、Studio・X 線 CT・会社の形の語が無い。
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VIEW = ROOT / "docs" / "view2026"

#: 名刺の表の文言(一字一句このまま)。
CARD_JA = "画像検査・三次元計測・物理シミュレーション"

#: 言語ごとの 3 語(名刺の順)と、文の中での並べ方。語は論文の題の訳(ui.title_tr)に合わせる。
PILLARS = {
    "ja": (("画像検査", "三次元計測", "物理シミュレーション"), CARD_JA),
    "en": (("image inspection", "3-D measurement", "physics simulation"),
           "image inspection, 3-D measurement and physics simulation"),
    "zh": (("图像检测", "三维测量", "物理仿真"), "图像检测、三维测量与物理仿真"),
    "tw": (("影像檢測", "三維量測", "物理模擬"), "影像檢測、三維量測與物理模擬"),
    "ko": (("영상 검사", "3차원 계측", "물리 시뮬레이션"), "영상 검사·3차원 계측·물리 시뮬레이션"),
    "de": (("Bildprüfung", "3-D-Messung", "Physiksimulation"),
           "Bildprüfung, 3-D-Messung und Physiksimulation"),
    "hi": (("image inspection", "3-D measurement", "physics simulation"),
           "image inspection, 3-D measurement और physics simulation"),
    "fr": (("inspection d'images", "mesure 3D", "simulation physique"),
           "l'inspection d'images, la mesure 3D et la simulation physique"),
}
VIEW_LANGS = ("ja", "en", "zh", "tw", "ko", "de", "hi", "fr")
SITE_LANGS = ("ja", "en", "zh", "tw", "ko", "de")

#: 言語ごとの土台の語(型を持つ op と、物理シミュレーションで作った真値)。
FOUNDATION_TERMS = {
    "ja": ("型", "真値"),
    "en": ("typed", "ground truth"),
    "zh": ("类型化", "真值"),
    "tw": ("型別化", "真值"),
    "ko": ("타입", "참값"),
    "de": ("typisiert", "Ground Truth"),
    "hi": ("typed", "ground truth"),
    "fr": ("typés", "vérité terrain"),
}

#: 頭に出さない語(Studio・X 線 CT・実在の会社名につながる会社の形)。
_BANNED = re.compile(
    r"Studio|X ?線|X-ray|\bCT\b|tomograph|トモグラフィ|断層|"
    r"株式会社|有限会社|合同会社|\(株\)|（株）|"
    r"\bInc\.(?=\s|,|$)|\bCo\.,?\s*Ltd\.(?=\s|,|$)|\bCorporation\b|"
    r"\bCorp\.(?=\s|,|$)|\bGmbH\b|\bK\.K\.(?=\s|,|$)",
    re.I,
)
#: 3 語の直後にあると、列挙を 4 つ目へ続ける区切り・接続語。
_PILLAR_CONTINUATION = re.compile(
    r"^\s*(?:[・、,，]|と|及|与|與|및|and(?![A-Za-z])|und(?![A-Za-z])|"
    r"et(?![A-Za-zÀ-ÿ])|और)",
    re.I,
)
#: 文の終わり(ja / zh / tw の「。」、hi の「।」、それ以外は「. 」)。
_SENTENCE_END = re.compile(r"(?<=[。।])|(?<=\.)\s")


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _plain(text: str) -> str:
    """Markdown の太字・HTML のタグを外した、目に見える文。"""
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text.replace("**", "")).strip()


def first_sentence(text: str) -> str:
    return _SENTENCE_END.split(_plain(text), maxsplit=1)[0].strip()


def first_sentences(text: str, count: int) -> str:
    """目に見える文の先頭から ``count`` 文を取り出す。"""
    return " ".join(_SENTENCE_END.split(_plain(text), maxsplit=count)[:count]).strip()


def pillar_problems(sentence: str, lang: str) -> list[str]:
    """名刺の 3 語が名刺の順と字のまま入っているか。問題の一覧(空なら合格)。"""
    terms, joined = PILLARS[lang]
    got = sentence.casefold()
    problems = []
    if joined.casefold() not in got:
        problems.append("名刺の 3 語 %r がそのままの形で無い" % joined)
    pos = [got.find(t.casefold()) for t in terms]
    if -1 in pos or pos != sorted(pos):
        problems.append("3 語 %r の有無と順が名刺と違う(位置 %s)" % (terms, pos))
    joined_match = re.search(re.escape(joined), sentence, re.I)
    if joined_match and _PILLAR_CONTINUATION.match(sentence[joined_match.end():]):
        problems.append("名刺の 3 語の直後に、4 つ目の柱へ続く区切り・接続語がある")
    hit = _BANNED.search(sentence)
    if hit:
        problems.append("頭の文に出さない語 %r がある" % hit.group(0))
    return problems


def lead_problems(lead: str, lang: str) -> list[str]:
    """頭の範囲に 3 本柱と土台があり、禁止語が無いか。問題の一覧。"""
    plain = _plain(lead)
    sentence = first_sentence(plain)
    problems = pillar_problems(sentence, lang)
    hit = _BANNED.search(plain)
    if hit and not _BANNED.search(sentence):
        problems.append("頭の範囲に出さない語 %r がある" % hit.group(0))
    for term in ("MCP", "RAG", *FOUNDATION_TERMS[lang]):
        if term.casefold() not in plain.casefold():
            problems.append("頭の範囲に土台の語 %r が無い" % term)
    return problems


def _paragraph_after(text: str, is_marker) -> str:
    """``is_marker`` の行の後ろで、最初の空でない段落(行を空白でつなぐ)。"""
    lines = text.splitlines()
    i = next(k for k, ln in enumerate(lines) if is_marker(ln))
    j = i + 1
    while j < len(lines) and not lines[j].strip():
        j += 1
    para = []
    while j < len(lines) and lines[j].strip():
        para.append(lines[j].strip())
        j += 1
    assert para, "段落が見つからない"
    return " ".join(para)


def _check(label: str, lead: str, lang: str) -> None:
    sentence = first_sentence(lead)
    assert sentence, "%s: 頭の文が空" % label
    problems = lead_problems(lead, lang)
    assert not problems, "%s の頭 %r: %s" % (label, _plain(lead), "; ".join(problems))


# --------------------------------------------------------------------------- #
# 検査の側が効くこと(直す前の文・言い換え・順の入れ替えを落とす)
# --------------------------------------------------------------------------- #
def test_the_check_rejects_paraphrases_wrong_order_and_the_old_leads():
    assert pillar_problems("Fullseye は、画像検査・三次元計測・物理シミュレーションの基盤です。", "ja") == []
    assert pillar_problems("Fullseye は、画像検査・3D 計測・シミュレーションの基盤です。", "ja")
    assert pillar_problems("Fullseye は、画像検査・三次元計測・シミュレーションの基盤です。", "ja")
    assert pillar_problems("Fullseye は、物理シミュレーション・画像検査・三次元計測の基盤です。", "ja")
    assert pillar_problems("Fullseye は、画像検査・三次元計測・物理シミュレーションと X 線 CT の基盤です。", "ja")
    old_view = ("光学設計や三次元計測などのセンシングを含む物理シミュレーションと古典画像処理を、"
                "MCP と RAG で AI に渡し、課題ごとに組み合わせを考えさせる基盤です。")
    assert pillar_problems(first_sentence(old_view), "ja")
    old_readme = ("**Documentation: [furuse.work](https://furuse.work/)** — the operator index "
                  "(operators in the machine-readable index), the family guides, and the release notes.")
    assert pillar_problems(first_sentence(old_readme), "en")
    assert pillar_problems("A library for 3-D measurement, image inspection and physics simulation.", "en")
    # 文の切り方: 2 文目に 3 語があっても頭の文としては通さない
    assert pillar_problems(first_sentence("Fullseye is a library. It does " + PILLARS["en"][1] + "."), "en")
    good = ("Fullseye is a Python library for image inspection, 3-D measurement and physics simulation. "
            "It chains typed operators, checks them against ground truth, and hands them to AI assistants "
            "through MCP and RAG.")
    assert lead_problems(good, "en") == []
    assert lead_problems(good.replace("It chains", "Fullseye Studio chains"), "en")
    assert lead_problems(good.replace(" through MCP and RAG", ""), "en")
    assert lead_problems(good.replace("AI assistants", "株式会社の AI assistants"), "en")
    fourth = good.replace("physics simulation.", "physics simulation and robot control.", 1)
    assert lead_problems(fourth, "en")


@pytest.mark.parametrize("lang", VIEW_LANGS)
def test_the_three_words_are_the_words_of_the_paper_title(lang: str) -> None:
    """3 語は論文の題(日本語)とその訳(ui.title_tr)から取った語であること。"""
    d = json.loads(_read("docs/view2026/exhibits.json"))
    title = d["paper"]["title_ja"] if lang == "ja" else d["ui"]["title_tr"][lang]
    assert title, lang
    norm = title.casefold().replace("-", " ")
    for term in PILLARS[lang][0]:
        assert term.casefold().replace("-", " ") in norm, (lang, term, title)
    if lang == "ja":
        assert "型付き演算子と物理シミュレーションに基づく画像検査・三次元計測基盤" in title


# --------------------------------------------------------------------------- #
# 置き場所ごとの頭の文
# --------------------------------------------------------------------------- #
def test_repository_readme_opens_with_the_three_words():
    """リポジトリのトップと PyPI の長い説明(英語)。バッジの直後の段落が頭。"""
    lines = _read("README.md").splitlines()
    h1 = next(k for k, ln in enumerate(lines) if ln.startswith("# "))
    blocks = [b for b in re.split(r"\n\s*\n", "\n".join(lines[h1 + 1:])) if b.strip()]
    assert len(blocks) >= 5, "README の段落が少なすぎる(%d)" % len(blocks)
    k = 0
    while blocks[k].lstrip().startswith("[!["):
        k += 1
    para = " ".join(ln.strip() for ln in blocks[k].splitlines())
    assert para.startswith("**Fullseye is "), para[:80]
    _check("README.md", para, "en")


@pytest.mark.parametrize("lang", SITE_LANGS)
def test_site_top_page_opens_with_the_three_words(lang: str) -> None:
    """サイト(furuse.work)のトップ = docs/README*.md。言語の行の直後の段落が頭。"""
    name = "docs/README.md" if lang == "ja" else "docs/README.%s.md" % lang
    para = _paragraph_after(_read(name), lambda ln: ln.startswith("**Language:**"))
    assert para.startswith("**Fullseye"), (name, para[:80])
    _check(name, para, lang)


def test_site_top_page_english_summary_uses_the_three_words():
    """日本語のトップに置いた英語の要約(英語で来た人が最初に読む段落)も同じ 3 語。"""
    text = _read("docs/README.md")
    head = text.split("\n---\n", 1)[0]
    quotes = [b for b in re.split(r"\n\s*\n", head) if b.lstrip().startswith("> **Fullseye is")]
    assert len(quotes) == 1, "英語の要約の段落が見つからない(%d 個)" % len(quotes)
    para = " ".join(ln.lstrip("> ").strip() for ln in quotes[0].splitlines())
    _check("docs/README.md の英語の要約", para, "en")


@pytest.mark.parametrize("lang", VIEW_LANGS)
def test_view2026_page_intro_opens_with_the_three_words(lang: str) -> None:
    """ViEW2026 のページ(8 言語)の冒頭の紹介の段落。正本(exhibits.json の ui.about)と生成物の両方を見る。"""
    d = json.loads(_read("docs/view2026/exhibits.json"))
    _check("exhibits.json ui.about[%s]" % lang, d["ui"]["about"][lang], lang)
    page = VIEW / "index.md" if lang == "ja" else VIEW / lang / "index.md"
    text = page.read_text(encoding="utf-8")
    m = re.search(r'<div class="vintro">.*?<div class="vt"><p>(.*?)</p>', text, re.S)
    assert m, "%s に冒頭の紹介の段落が無い" % page.name
    assert html.unescape(m.group(1)) == d["ui"]["about"][lang], (
        "%s の紹介の段落が exhibits.json と違う —— py -3.11 tools/gen_view2026_pages.py で作り直す" % lang)
    _check("docs/view2026/%sindex.md" % ("" if lang == "ja" else lang + "/"), m.group(1), lang)


def test_pypi_one_line_description_opens_with_the_three_words():
    """PyPI の一行の説明(pyproject.toml の description)。書き出しが 3 語。"""
    m = re.search(r'^description = "(.*)"$', _read("pyproject.toml"), re.M)
    assert m, "pyproject.toml に description が無い"
    desc = m.group(1)
    assert desc.casefold().startswith(PILLARS["en"][1].casefold()), desc[:80]
    _check("pyproject.toml description", desc, "en")


def test_citation_and_zenodo_abstracts_open_with_the_three_words():
    """引用の要旨(CITATION.cff)と DOI の頁の説明(.zenodo.json)の最初の 2 文。"""
    cff = _read("CITATION.cff")
    m = re.search(r"^abstract: >-\n((?:  .*\n)+)", cff, re.M)
    assert m, "CITATION.cff に abstract が無い"
    abstract = " ".join(ln.strip() for ln in m.group(1).splitlines())
    _check("CITATION.cff abstract", first_sentences(abstract, 2), "en")
    zen = json.loads(_read(".zenodo.json"))["description"]
    _check(".zenodo.json description", first_sentences(zen, 2), "en")
