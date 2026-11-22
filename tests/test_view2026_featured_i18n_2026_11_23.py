"""ViEW2026 の目玉翻訳、言語別 YouTube URL、新しい動画展示を守る。"""
from __future__ import annotations

import copy
import importlib.util
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = ROOT / "tools" / "gen_view2026_pages.py"
_SPEC = importlib.util.spec_from_file_location("gen_view2026_pages_i18n", GENERATOR_PATH)
G = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(G)

#: 日本語・英語以外で、目玉の題と lead を手訳する言語。
OTHER_LANGS = ("zh", "tw", "ko", "de", "hi", "fr")
#: 小数コンマを使う言語。
DECIMAL_COMMA_LANGS = ("de", "fr")
#: 題と lead に現れる整数・小数。
NUMBER_TOKEN_RE = re.compile(r"\d+(?:[.,]\d+)?")
#: 日本語以外の訳へ残してはならないかな。
KANA_RE = re.compile(r"[\u3040-\u30ff]")
#: 小数点と小数コンマの表記を調べる式。
DECIMAL_POINT_RE = re.compile(r"\d\.\d")
DECIMAL_COMMA_RE = re.compile(r"\d,\d")
#: ui.about に必要な「シミュレーションが真値を作る」の言い回し。
SIMULATION_TRUTH_PHRASES = {
    "ja": "物理・撮像シミュレーションが作る真値",
    "en": "ground truth that the physics and imaging simulation produces",
    "zh": "物理与成像仿真生成的真值",
    "tw": "物理與成像模擬產生的真值",
    "ko": "물리·촬상 시뮬레이션이 만든 참값",
    "de": "Ground Truth, die die Physik- und Bildgebungssimulation erzeugt",
    "hi": "physics और imaging simulation से बने ground truth",
    "fr": "vérité terrain produite par la simulation physique et d'imagerie",
}
#: 言語別 URL を持つ検査 PoC 動画の展示 id と URL。
REEL_ID = "inspection_poc_reel"
REEL_JA_URL = "https://youtu.be/FZC3k6uGtZE"
REEL_EN_URL = "https://youtu.be/6XtEJW_w6Xk"
#: 人型ロボット動画の展示 id と分類 id。
G1_ID = "g1_iroha_climb"
#: 銀座(CARLA)の動画の展示(日本語の動画 1 本を全言語で出す)。
GINZA_ID = "carla_ginza_perception"
HUMANOID_CATEGORY_ID = "humanoid"
#: 厳密な URL 検査が拒否すべき例。
BAD_YOUTUBE_URLS = (
    "https://youtu.be/FZC3k6uGtZE/extra",
    "https://youtu.be/FZC3k6uGtZE?feature=x",
    "https://example.com/watch?v=FZC3k6uGtZE",
    "https://youtu.be/FZC3k6uGtZ",
    "http://youtu.be/FZC3k6uGtZE",
)


def _main_rows(data: dict) -> list[dict]:
    """本ページに載る目玉を正本の順で返す。"""
    return [row for row in data["exhibits"] if row["tier"] in G.MAIN_TIERS]


#: 本ページの目玉の本数(test_view2026_featured30_2026_11_15 と同じ。空の行に対して表明が素通りしないように数える)。
MAIN_CARD_COUNT = 30


def _checked_rows(data: dict) -> list[dict]:
    """本ページの目玉を返す。本数が違えば(空なら特に)止める。"""
    rows = _main_rows(data)
    assert len(rows) == MAIN_CARD_COUNT, len(rows)
    return rows


def _number_tokens(text: str, lang: str) -> Counter:
    """小数コンマだけ点へそろえた数値 multiset。"""
    tokens = NUMBER_TOKEN_RE.findall(text)
    if lang in DECIMAL_COMMA_LANGS:
        tokens = [token.replace(",", ".") for token in tokens]
    return Counter(tokens)


def _number_errors(data: dict) -> list[tuple[str, str, str, Counter, Counter]]:
    """目玉翻訳で英語と数値 multiset が違う欄を返す。"""
    errors = []
    for row in _main_rows(data):
        for field in ("label", "lead"):
            expected = _number_tokens(row[field]["en"], "en")
            for lang in OTHER_LANGS:
                got = _number_tokens(row[field][lang], lang)
                if got != expected:
                    errors.append((row["id"], field, lang, expected, got))
    return errors


def _youtube_values(row: dict) -> list[str]:
    """文字列形式と object 形式から登録 URL をすべて返す。"""
    value = row.get("youtube_url", "")
    return list(value.values()) if isinstance(value, dict) else [value]


def test_every_main_card_has_real_translations_in_all_other_languages() -> None:
    data = G.load()
    untranslated = []
    for row in _checked_rows(data):
        for field in ("label", "lead"):
            for lang in OTHER_LANGS:
                value = row[field].get(lang, "")
                if not value or value == row[field]["en"]:
                    untranslated.append((row["id"], field, lang))
    assert not untranslated, untranslated[:30]


def test_translated_labels_and_leads_preserve_numbers_and_each_lead_has_one() -> None:
    data = G.load()
    assert not _number_errors(data)
    for row in _checked_rows(data):
        for lang in ("en", *OTHER_LANGS):
            assert sum(_number_tokens(row["lead"][lang], lang).values()) == 1, (row["id"], lang)


def test_translations_use_the_decimal_mark_of_their_language() -> None:
    for row in _checked_rows(G.load()):
        for field in ("label", "lead"):
            for lang in DECIMAL_COMMA_LANGS:
                assert DECIMAL_POINT_RE.search(row[field][lang]) is None, (row["id"], field, lang)
            for lang in set(OTHER_LANGS) - set(DECIMAL_COMMA_LANGS):
                assert DECIMAL_COMMA_RE.search(row[field][lang]) is None, (row["id"], field, lang)


def test_other_language_translations_have_no_kana() -> None:
    for row in _checked_rows(G.load()):
        for field in ("label", "lead"):
            for lang in OTHER_LANGS:
                assert KANA_RE.search(row[field][lang]) is None, (row["id"], field, lang)


def test_number_gate_rejects_a_changed_translation_digit() -> None:
    broken = copy.deepcopy(G.load())
    row = _main_rows(broken)[0]
    lang = OTHER_LANGS[0]
    token = next(iter(_number_tokens(row["lead"][lang], lang)))
    replacement = str(int(float(token)) + 1)
    row["lead"][lang] = row["lead"][lang].replace(token, replacement, 1)
    errors = _number_errors(broken)
    assert errors
    assert any(error[:3] == (row["id"], "lead", lang) for error in errors), errors


def test_about_says_the_simulation_produces_the_ground_truth() -> None:
    about = G.load()["ui"]["about"]
    assert set(SIMULATION_TRUTH_PHRASES) == set(about)
    for lang, phrase in SIMULATION_TRUTH_PHRASES.items():
        assert phrase in about[lang], (lang, phrase)


def test_every_youtube_url_is_strict_and_bad_forms_are_rejected() -> None:
    registered = []
    for row in G.load()["exhibits"]:
        registered.extend(url for url in _youtube_values(row) if url)
    assert registered
    assert all(G.YOUTUBE_URL_RE.fullmatch(url) for url in registered)
    assert all(G.YOUTUBE_URL_RE.fullmatch(url) is None for url in BAD_YOUTUBE_URLS)


def test_every_registered_youtube_url_is_rendered_for_each_language() -> None:
    data = G.load()
    public_ids = {row["id"] for row in G.public_data(data)["exhibits"]}
    registered = [row for row in data["exhibits"] if any(_youtube_values(row)) and row["id"] in public_ids]
    assert registered
    assert {G1_ID, REEL_ID, GINZA_ID} <= {row["id"] for row in registered}
    for lang in data["langs"]:
        pages = G.build(data, lang) + "\n" + G.build_more(data, lang)
        for row in registered:
            url = G.youtube_url_for(row, lang)
            assert "](%s)" % url in pages, (lang, row["id"], url)
        if lang == "ja":
            assert REEL_JA_URL in pages
        else:
            assert REEL_EN_URL in pages and REEL_JA_URL not in pages, lang


def test_g1_video_is_under_the_humanoid_heading_on_the_extras_page() -> None:
    data = G.load()
    category = next(row for row in data["categories"] if row["id"] == HUMANOID_CATEGORY_ID)
    exhibit = next(row for row in data["exhibits"] if row["id"] == G1_ID)
    for lang in data["langs"]:
        page = G.build_more(data, lang)
        start = page.index("**%s**" % category[lang])
        end = page.find("\n**", start + len(category[lang]))
        section = page[start:end if end >= 0 else None]
        assert exhibit["label"][lang] in section, lang


def test_per_language_youtube_object_rejects_empty_values() -> None:
    """言語別の youtube_url で空の値(en も他の言語も)を validate が止める。文字列の空は未登録として通す。"""
    data = G.load()
    assert G.validate(data) == []
    row_index = next(i for i, row in enumerate(data["exhibits"]) if row["id"] == REEL_ID)
    for broken_value in ({"en": ""}, {"en": REEL_EN_URL, "ja": ""}):
        broken = copy.deepcopy(data)
        broken["exhibits"][row_index]["youtube_url"] = broken_value
        bad = G.validate(broken)
        assert bad, broken_value
        assert any(REEL_ID in message and "youtube_url" in message for message in bad), (broken_value, bad)
