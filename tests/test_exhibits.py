# -*- coding: utf-8 -*-
"""展示(exhibit)章の単一真実源を守る検査。

記事の「紙面の科学館」章は ``docs/articles/exhibits/`` から
``tools/build_exhibits.py`` が組み立てた生成物である。ソースだけ直して本文を
再生成し忘れる(あるいはその逆に本文を手で直す)と、両者は静かに食い違う ――
例外は出ないし、記事は普通に読める。だから CI で落とす。

fail-closed 側の検査もここに置く。展示が増えるたびに人が目視するのは続かないので、
**リンク切れ・キャプション無し・ローカルパス混入は機械が拒否する**。
"""
from __future__ import annotations

import json
import ast
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_exhibits as B  # noqa: E402
from exhibit_glossary import load_glossary, terms_for_exhibit  # noqa: E402

BASE = "https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/"
CAPTIONS = ROOT / "docs" / "articles" / "exhibits" / "poc_captions.json"

# 5b6839d9ff の lead_en を単語列にし、4 展示以上で共有された 3-gram。
# 壊れた生成器の型を具体的な回帰資料として固定し、新しい言い換えが増えても
# 禁止語を緩めない。
OLD_SHARED_LEAD_EN_TRIGRAMS = {
    "a comparison of", "a computed data", "a measured data", "a synthetic data",
    "and measured shows", "and that shows", "and the contrast", "and the method",
    "as the truth", "because the measurement", "become unreliable a",
    "become unreliable for", "become unreliable the", "become unreliable we",
    "between closed-form and", "between continues and", "between measured and",
    "built the contrast", "can become unreliable", "closed form and",
    "compares the contrast", "comparison of how", "comparison of the",
    "computed data case", "computed data compares", "computed data then",
    "computed data to", "contrast between closed-form", "contrast between continues",
    "contrast between measured", "data case for", "data case links",
    "data compares the", "data then compare", "data to separate", "data to the",
    "difficult because the", "for how much", "from computed data",
    "from measured data", "from synthetic data", "from the contrast",
    "fullseye and series", "images matters when", "in closed form",
    "in computed data", "in evaluating counting", "in evaluating measuring",
    "in evaluating where", "in measured data", "in practice is", "in synthetic data",
    "is difficult because", "matters when the", "measured data case",
    "measured data compares", "measured data then", "measured data to",
    "measured shows that", "measurement can become", "practice is difficult",
    "shows that a", "shows that and", "shows that counting", "shows that how",
    "shows that scored", "shows that the", "shows that what", "shows that where",
    "synthetic data case", "synthetic data compares", "synthetic data then",
    "synthetic data to", "that how much", "that shows that", "that the measurement",
    "the computed data", "the contrast between", "the figure shows",
    "the figures show", "the measured data", "the measurement can",
    "the plots show", "the synthetic data", "the test uses", "to the contrast",
    "unreliable we place", "when measuring a", "when measuring measuring",
    "where is the", "while scored by", "while then compare", "with the contrast",
}

_EN_ABBREVIATIONS = ("e.g.", "i.e.", "et al.", "Fig.", "Eq.", "No.",
                     "Dr.", "Mr.", "Ms.", "St.")


def _en_gate_sentences(text: str) -> list[str]:
    """小数点と既知の略語を文末と数えずに英語文を分ける。"""
    masked = re.sub(r"(?<=\d)\.(?=\d)", "<DECIMAL>", text)
    for index, abbreviation in enumerate(_EN_ABBREVIATIONS):
        masked = masked.replace(abbreviation, abbreviation.replace(".", "<ABBR%d>" % index))
    return [part.replace("<DECIMAL>", ".") for part in
            re.split(r"(?<=[.!?])\s+", masked) if part.strip()]


def _english_words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z]+(?:[-'][A-Za-z]+)*", text.casefold())


def _caption_exhibits():
    return json.loads(CAPTIONS.read_text(encoding="utf-8"))["exhibits"]


def _sentence_count(text: str, lang: str) -> int:
    if lang == "ja":
        return text.count("。")
    return text.count(". ") + int(text.endswith(".")) + text.count("? ") + int(text.endswith("?"))


def _sentences(text: str, lang: str) -> list[str]:
    """導入文の比較に使う文分割。句読点自体は比較から外す。"""
    if lang == "ja":
        return [s for s in re.split(r"[。！？]+", text) if s.strip()]
    return [s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _normalise_sentence(text: str) -> str:
    return re.sub(r"[\s\W_]+", "", text, flags=re.UNICODE).casefold()


def _opening_docstring(exhibit_id: str) -> str:
    path = ROOT / "examples" / (exhibit_id + ".py")
    if not path.is_file():
        return ""
    doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) or ""
    return doc.split("\n\n", 1)[0]


def _opening_caption(text: str, lang: str) -> str:
    return " ".join(_sentences(text, lang)[:2])


def _content_words(text: str, lang: str) -> set[str]:
    if lang == "ja":
        # 助詞を拾わず、意味を担う漢字語・カタカナ語だけを比較する。
        return set(re.findall(r"(?:[一-龯々〆ヵヶ]{2,}|[ァ-ヶー]{2,})", text))
    return {word.casefold() for word in re.findall(r"[A-Za-z]{4,}", text)}


def test_lead_sentences_are_not_shared_by_four_exhibits():
    """句読点を替えただけの定型文も、四展示へ使い回した時点で拒否する。"""
    owners: dict[tuple[str, str], set[str]] = {}
    for exhibit in _caption_exhibits():
        for lang in ("ja", "en"):
            lead = exhibit["lead_" + lang]
            for sentence in _sentences(lead, lang):
                key = lang, _normalise_sentence(sentence)
                owners.setdefault(key, set()).add(exhibit["id"])
    repeated = [(lang, sentence, sorted(ids)) for (lang, sentence), ids in owners.items() if len(ids) >= 4]
    assert not repeated, repeated[:20]


def test_english_leads_have_complete_sentences_matching_japanese():
    problems = []
    for exhibit in _caption_exhibits():
        if not exhibit["lead_ja"] and not exhibit["lead_en"]:
            continue
        sentences = _en_gate_sentences(exhibit["lead_en"])
        if not 2 <= len(sentences) <= 3:
            problems.append((exhibit["id"], "English sentence count", len(sentences)))
        if len(sentences) != len(_sentences(exhibit["lead_ja"], "ja")):
            problems.append((exhibit["id"], "Japanese/English count", len(sentences)))
        for sentence in sentences:
            plain = re.sub(r"<(?:DECIMAL|ABBR\d+)>", ".", sentence).strip()
            if not re.match(r"[A-Z]", plain):
                problems.append((exhibit["id"], "lower-case opening", plain))
            if not plain.endswith("."):
                problems.append((exhibit["id"], "non-period ending", plain))
    assert not problems, problems[:30]


def test_english_leads_have_no_mid_sentence_title_case_fragments():
    """旧生成器の ``from A historical`` 型を、必要な固有名だけ許して止める。"""
    glossary = load_glossary()
    glossary_names = {
        word
        for entry in glossary.values()
        for field in (entry["en"], *entry["match"])
        for word in re.findall(r"\b[A-Z][a-z]{2,}\b", field)
    }
    explicit_names = {
        "Airy", "Bayer", "Beer", "Bragg", "Canny", "Cauchy", "Debye",
        "Appended", "Apollonian", "Art", "Boolean", "Cattaneo", "Chinese", "Dubins",
        "Enforcement", "Fibonacci", "Fourier",
        "Fresnel", "Gauss", "Gaussian", "Gibbs", "Hertz", "Hough", "Lambert", "Lorenz",
        "Hybrid", "Japan", "Mandelbrot", "Martian", "Maxwell", "Metropolitan", "Mie",
        "Newton", "Nyquist", "Otsu", "Ozaki",
        "Poisson", "Preston", "Rayleigh", "Reynolds", "Rice", "Rician",
        "Reeds", "Road", "Rodrigues", "Schlieren", "Sholl", "Snell", "Stokes", "Voronoi",
        "Whitney", "Wiener",
    }
    allowed = glossary_names | explicit_names
    pattern = re.compile(
        r"\b(?:a|an|the|as|at|by|for|from|in|into|of|on|onto|over|through|to|under|using|with|without) "
        r"([A-Z][a-z]{2,})\b")
    problems = []
    for exhibit in _caption_exhibits():
        for sentence in _en_gate_sentences(exhibit["lead_en"]):
            for match in pattern.finditer(sentence):
                if match.start() and match.group(1) not in allowed:
                    problems.append((exhibit["id"], match.group(0)))
    assert not problems, problems[:30]


def test_english_leads_do_not_contain_four_words_from_the_title():
    problems = []
    for exhibit in _caption_exhibits():
        lead_words = _english_words(exhibit["lead_en"])
        title_words = _english_words(exhibit["title_en"])
        lead_grams = set(zip(lead_words, lead_words[1:], lead_words[2:], lead_words[3:]))
        overlap = [gram for gram in zip(title_words, title_words[1:], title_words[2:], title_words[3:])
                   if gram in lead_grams]
        if overlap:
            problems.append((exhibit["id"], " ".join(overlap[0])))
    assert not problems, problems[:30]


def test_english_leads_do_not_reuse_old_generator_trigrams():
    problems = []
    for exhibit in _caption_exhibits():
        words = _english_words(exhibit["lead_en"])
        found = sorted({" ".join(gram) for gram in zip(words, words[1:], words[2:])}
                       & OLD_SHARED_LEAD_EN_TRIGRAMS)
        if found:
            problems.append((exhibit["id"], found))
    assert not problems, problems[:30]


def test_leads_do_not_open_with_exhibit_boilerplate():
    rows = _caption_exhibits()
    for lang, prefix in (("ja", "この展示は"), ("en", "This exhibit")):
        active = [e for e in rows if e["lead_" + lang]]
        count = sum(e["lead_" + lang].startswith(prefix) for e in active)
        assert not active or count / len(active) <= 0.10, (lang, count, len(active))


def test_each_lead_uses_two_source_content_words_beyond_the_title():
    problems = []
    for exhibit in _caption_exhibits():
        doc = _opening_docstring(exhibit["id"])
        for lang in ("ja", "en"):
            lead = exhibit["lead_" + lang]
            if not lead:
                continue
            title = exhibit["title_" + lang]
            source = _opening_caption(exhibit["caption_" + lang], lang) + " " + doc
            candidates = _content_words(source, lang) - _content_words(title, lang)
            present = {word for word in candidates if word in lead.casefold()}
            if len(present) < 2:
                problems.append((exhibit["id"], lang, sorted(present), sorted(candidates)))
    assert not problems, problems[:30]


def test_leads_do_not_paste_the_full_title():
    problems = []
    for exhibit in _caption_exhibits():
        for lang in ("ja", "en"):
            lead = exhibit["lead_" + lang]
            if exhibit["title_" + lang] in lead:
                problems.append((exhibit["id"], lang))
    assert not problems, problems[:30]


def test_every_poc_has_a_paired_optional_short_plain_lead():
    """初見の導入は短く、実装語や数表の代わりにならない文だけにする。"""
    op_names = {
        row["name"].casefold()
        for row in json.loads((ROOT / "fullseye" / "data" / "OP_INDEX.json").read_text(encoding="utf-8"))["ops"]
    }
    forbidden = re.compile(r"`|\b(?:op|docstring|gate|regen)\b|門", re.IGNORECASE)
    problems = []
    for exhibit in _caption_exhibits():
        if bool(exhibit.get("lead_ja")) != bool(exhibit.get("lead_en")):
            problems.append((exhibit["id"], "unpaired lead"))
            continue
        if not exhibit.get("lead_ja"):
            continue
        for lang, limit in (("ja", 160), ("en", 320)):
            lead = exhibit.get("lead_" + lang, "")
            if _sentence_count(lead, lang) != 3:
                problems.append((exhibit["id"], lang, "not three sentences"))
            if len(lead) > limit:
                problems.append((exhibit["id"], lang, "too long"))
            if forbidden.search(lead):
                problems.append((exhibit["id"], lang, "implementation word"))
            if len(re.findall(r"\d+(?:\.\d+)?", lead)) > 1:
                problems.append((exhibit["id"], lang, "more than one number"))
            words = {w.casefold() for w in re.findall(r"[A-Za-z][A-Za-z0-9_]*", lead)}
            leaked = sorted(words & op_names)
            if leaked:
                problems.append((exhibit["id"], lang, "operator name: " + ", ".join(leaked)))
            caption = exhibit["caption_" + lang]
            if caption.startswith(lead) or lead == caption[:len(lead)]:
                problems.append((exhibit["id"], lang, "caption prefix copied"))
    assert not problems, problems[:30]


def test_leads_avoid_returned_boilerplate():
    forbidden = {
        "ja": ("の差を見ると", "を別々に確かめた", "がどう変わるかを調べた",
               "の関係を測った", "の差が、", "ことが分かる"),
        "en": ("Comparing X with Y shows", "we checked", "separately"),
    }
    problems = []
    for exhibit in _caption_exhibits():
        for lang in ("ja", "en"):
            lead = exhibit["lead_" + lang]
            for phrase in forbidden[lang]:
                if phrase.casefold() in lead.casefold():
                    problems.append((exhibit["id"], lang, phrase))
    assert not problems, problems[:30]


def test_second_and_third_sentence_openings_are_not_reused_five_times():
    for lang in ("ja", "en"):
        for sentence_index in (1, 2):
            owners = {}
            for exhibit in _caption_exhibits():
                sentences = _sentences(exhibit["lead_" + lang], lang)
                if len(sentences) <= sentence_index:
                    continue
                opening = sentences[sentence_index].strip()[:6].casefold()
                owners.setdefault(opening, []).append(exhibit["id"])
            repeated = [(opening, ids) for opening, ids in owners.items() if len(ids) >= 5]
            assert not repeated, (lang, sentence_index + 1, repeated[:20])


def test_every_lead_number_comes_from_its_caption():
    number = re.compile(r"[-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?", re.IGNORECASE)
    problems = []
    for exhibit in _caption_exhibits():
        for lang in ("ja", "en"):
            lead = exhibit["lead_" + lang]
            lead_numbers = number.findall(lead)
            caption_numbers = set(number.findall(exhibit["caption_" + lang]))
            missing = [value for value in lead_numbers if value not in caption_numbers]
            if missing:
                problems.append((exhibit["id"], lang, missing))
            if lead:
                sentences = _sentences(lead, lang)
                second_numbers = number.findall(sentences[1]) if len(sentences) > 1 else []
                if len(lead_numbers) != 1 or len(second_numbers) != 1:
                    problems.append((exhibit["id"], lang, "one number required in sentence two"))
    assert not problems, problems[:30]


def test_lead_glossary_terms_are_explained_on_the_same_exhibit():
    glossary = load_glossary()
    problems = []
    for exhibit in _caption_exhibits():
        for lang in ("ja", "en"):
            lead = exhibit["lead_" + lang]
            displayed = {term_id for term_id, _entry in terms_for_exhibit(exhibit, lang, glossary)}
            for term_id, entry in glossary.items():
                flags = re.IGNORECASE if lang == "en" else 0
                if any(re.search(r"(?<![A-Za-z0-9_])" + re.escape(alias) + r"(?![A-Za-z0-9_])", lead, flags)
                       for alias in entry["match"]):
                    if term_id not in displayed:
                        problems.append((exhibit["id"], lang, term_id))
    assert not problems, problems[:30]


def test_manifest_is_wellformed():
    manifest = B.load_manifest()
    assert manifest["asset_base"] == BASE
    for lang in ("ja", "en"):
        assert "{n}" in manifest["chapter_title"][lang], (
            "章見出しの展示点数は {n} で自動で埋める ― 手で数えると必ずずれる")
    orders = [w["order"] for w in manifest["wings"]]
    assert len(orders) == len(set(orders)), "order が重複すると並び順が不定になる"


def test_every_wing_has_both_languages():
    """ja だけ足して en を忘れる、が一番起きやすい。"""
    manifest = B.load_manifest()
    missing = []
    for wing in manifest["wings"]:
        for lang in ("ja", "en"):
            try:
                B.wing_source(wing["id"], lang)
            except B.BuildError:
                missing.append(f"{wing['id']}.{lang}")
    assert not missing, "展示ソースが無いウィング: " + ", ".join(missing)


def test_chapter_matches_generator_no_drift():
    rc = B.main(["--check"])
    assert rc == 0, "記事の展示章が古い — `py -3.11 tools/build_exhibits.py` を実行すること"


def test_exhibit_count_in_heading_is_the_real_count():
    """見出しの点数が、実際のキャプション数と一致すること。"""
    manifest = B.load_manifest()
    for lang, article in B.ARTICLES.items():
        _, total = B.render(manifest, lang)
        heading = manifest["chapter_title"][lang].format(n=total)
        assert f"## {heading}" in article.read_text(encoding="utf-8")
        assert total > 0


def test_all_referenced_assets_exist_on_disk():
    """リンク切れの記事を出さない。展示が増えるほど効く検査。"""
    manifest = B.load_manifest()
    for wing in manifest["wings"]:
        for lang in ("ja", "en"):
            body = B.wing_source(wing["id"], lang).read_text(encoding="utf-8")
            B.check_body(body, f"{wing['id']}.{lang}", BASE)   # 落ちなければ全て実在


@pytest.mark.parametrize(
    "body, needle",
    [
        (f"[![a]({BASE}science_fourier_stars.png)]({BASE}science_fourier_stars.png)\n",
         "caption"),
        ("[![a](https://example.com/x.png)](https://example.com/x.png)\n\n*↑ x。*\n",
         "asset base"),
        (f"[![a]({BASE}no_such_file_zzz.png)]({BASE}no_such_file_zzz.png)\n\n*↑ x。*\n",
         "does not exist"),
        ("説明は C:\\dev\\projects\\imgevolve にあります\n\n*↑ x。*\n", "local path"),
        ("見出しだけで展示が無いウィング\n", "no exhibits"),
    ],
)
def test_check_body_is_fail_closed(body, needle):
    """壊れた展示は生成前に止める(通してから気づく、をやらない)。"""
    with pytest.raises(B.BuildError) as exc:
        B.check_body(body, "synthetic", BASE)
    assert needle in str(exc.value)


def test_cache_busting_query_is_allowed():
    """``?v=2`` は Qiita(imgix)のキャッシュ外しに要るので、実在確認では落とす。"""
    body = (f"[![a]({BASE}science_fourier_stars.png?v=7)]"
            f"({BASE}science_fourier_stars.png?v=7)\n\n*↑ x。使用 op: `fft_image`。*\n")
    assert B.check_body(body, "synthetic", BASE) == 1


def test_a_new_wing_needs_only_two_files_and_one_manifest_line(tmp_path, monkeypatch):
    """器を増やす手数が「md 2 枚 + JSON 1 行」で済むことを、実際にやって確かめる。"""
    ex = tmp_path / "exhibits"
    ex.mkdir()
    for lang in ("ja", "en"):
        (ex / f"_intro.{lang}.md").write_text("intro\n", encoding="utf-8")
        (ex / f"demo.{lang}.md").write_text(
            f"[![a]({BASE}science_fourier_stars.png)]({BASE}science_fourier_stars.png)\n\n"
            "*↑ demo。使用 op: `fft_image`。*\n", encoding="utf-8")
    manifest = {
        "asset_base": BASE,
        "chapter_title": {"ja": "展示 {n} 点", "en": "{n} exhibits"},
        "wings": [{"id": "demo", "order": 10, "title": {"ja": "デモ", "en": "Demo"}}],
    }
    (ex / "wings.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(B, "EXHIBITS", ex)
    block, total = B.render(B.load_manifest(), "ja")
    assert total == 1
    assert "## 展示 1 点" in block and "### デモ" in block
