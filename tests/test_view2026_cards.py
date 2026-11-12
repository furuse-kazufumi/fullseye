"""ViEW2026 の入口ページ(8 言語): 展示 1 本 = 画像 + 題 + 本文 の 1 かたまり、触って見る 1 本ずつに小さな画像、
文字だけが長く続く所が無いこと、Fullseye とは が題と発表の日時の直下にあって最後に重複しないこと(2026-11-12)。"""
from __future__ import annotations

import html
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("gen_view2026_pages_cards", ROOT / "tools" / "gen_view2026_pages.py")
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)

LANGS = ["ja", "en", "zh", "tw", "ko", "de", "hi", "fr"]
#: 画像のない行が続く区間(見出し・段落・分類名)の文字数の上限(目に見える文字、タグと属性は数えない)。
MAX_TEXT_RUN = 600
#: 展示のかたまり 1 つの、折りたたみの外に見える文字数の上限(ja は 1 文字が広いので別に持つ)。
MAX_CARD_TEXT = {"ja": 420, "en": 700}
MAX_CARD_TEXT_OTHER = 700


def _page_dir(lang: str) -> Path:
    return G.BASE if lang == "ja" else G.BASE / lang


def _lines(lang: str, data=None) -> list[str]:
    return G.build(data or G.load(), lang).splitlines()


def _visible(fragment: str) -> str:
    """タグ・属性・折りたたみの中身を除いた、目に見える文字。"""
    fragment = re.sub(r"<details>.*?</details>", "", fragment, flags=re.S)
    fragment = re.sub(r"<(style|script)\b.*?</\1>", "", fragment, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def _cards(lines: list[str]) -> list[str]:
    return [line for line in lines if line.startswith('<div class="vc">')]


def _viewer_cards(lines: list[str]) -> list[str]:
    return [line for line in lines if line.startswith('<div class="vc vv">')]


def _expected_rows(data, lang: str) -> list[dict]:
    rows = G.public_data(data)["exhibits"]
    return [e for e in rows if e["tier"] in G.MAIN_TIERS] if lang in ("ja", "en") else rows


@pytest.mark.parametrize("lang", LANGS)
def test_every_exhibit_is_one_block_with_one_image_and_its_title_once(lang: str) -> None:
    data = G.load()
    lines = _lines(lang, data)
    cards = _cards(lines)
    rows = _expected_rows(data, lang)
    assert len(cards) == len(rows) >= 10, lang
    labels = {e["label"][lang] for e in rows}
    seen = set()
    for card in cards:
        assert card.count("<img ") == 1, (lang, card[:120])
        alt = re.search(r'<img [^>]*alt="([^"]*)"', card).group(1)
        title = html.unescape(alt)
        assert title in labels, (lang, title)
        seen.add(title)
        assert 'loading="lazy"' in card and re.search(r'width="\d+" height="\d+"', card), (lang, title)
        # 題は目に見える所に 1 回だけ(画像の alt は数えない)
        assert _visible(card).count(title) == 1, (lang, title)
    assert seen == labels, lang


@pytest.mark.parametrize("lang", LANGS)
def test_every_image_the_blocks_point_to_exists(lang: str) -> None:
    page = "\n".join(_lines(lang))
    page_dir = _page_dir(lang)
    refs = re.findall(r'<img [^>]*?src="([^"]+)"', page) + re.findall(r'<source [^>]*?srcset="([^"]+)"', page)
    assert len(refs) >= 20, lang
    for ref in refs:
        if ref.startswith("data:") or ref.startswith("http"):
            continue
        assert (page_dir / ref).resolve().is_file(), (lang, ref)


@pytest.mark.parametrize("lang", LANGS)
def test_each_viewer_has_a_small_image_whose_alt_is_its_title(lang: str) -> None:
    data = G.load()
    lines = _lines(lang, data)
    viewer_lines = _viewer_cards(lines)
    vw = data["viewers"]
    by_id = {it["id"]: it for it in vw["items"]}
    if lang in ("ja", "en"):
        items = list(data["field_viewers"]["items"]) + [by_id[i] for i in vw["main_ids"]]
    else:
        items = list(vw["items"])
    assert len(viewer_lines) == len(items), lang
    for it, line in zip(items, viewer_lines):
        title = it["title"].get(lang, it["title"]["en"])
        assert line.count("<img ") == 1, (lang, title)
        assert 'alt="%s"' % html.escape(title, quote=True) in line, (lang, title)
        assert line.count(">%s</a>" % G._esc(title)) == 1, (lang, title)       # 題の見出しは 1 つ(説明文に同じ語が入ってもよい)
        assert 'loading="lazy"' in line and 'width="96" height="96"' in line


@pytest.mark.parametrize("lang", LANGS)
def test_text_without_an_image_never_runs_long(lang: str) -> None:
    """触って見る の見出しから最後の展示のかたまりまでで、画像のない行が続く文字数に上限。1 つのかたまりの文字数にも上限。"""
    data = G.load()
    lines = _lines(lang, data)
    start = next(i for i, line in enumerate(lines) if line.startswith("## "))                 # 触って見る
    last = max(i for i, line in enumerate(lines) if line.startswith('<div class="vc'))
    run, longest = 0, 0
    for line in lines[start:last + 1]:
        if "<img" in line:
            run = 0
            continue
        run += len(_visible(line))
        longest = max(longest, run)
    assert longest <= MAX_TEXT_RUN, (lang, longest)
    limit = MAX_CARD_TEXT.get(lang, MAX_CARD_TEXT_OTHER)
    for card in _cards(lines):
        assert len(_visible(card)) <= limit, (lang, len(_visible(card)), card[:100])


@pytest.mark.parametrize("lang", LANGS)
def test_page_order_is_the_same_in_every_language(lang: str) -> None:
    """題 → 発表の日時 → Fullseye とは(段落 + 画像)→ タイルの使い方 → 触って見る → 目玉 → … → シリーズ記事。
    「Fullseye とは」の見出しは最後に残らない。"""
    data = G.load()
    ui = {k: v.get(lang, "") for k, v in data["ui"].items()}
    page = "\n".join(_lines(lang, data))
    at = {
        "title": page.index("# Fullseye — ViEW2026"),
        "session": page.index(ui["session"]),
        "intro": page.index('<div class="vintro">'),
        "tap": page.index(ui["tap"]),
        "viewers": page.index("## " + data["viewers"]["h"][lang]),
        "first_card": page.index('<div class="vc">'),
        "series": page.index("## " + ui["h_series"]),
    }
    order = sorted(at, key=at.get)
    assert order == ["title", "session", "intro", "tap", "viewers", "first_card", "series"], (lang, order)
    # 「Fullseye とは」の見出しはどこにも無い。段落は冒頭に 1 回だけ。
    assert not re.search(r"^## %s$" % re.escape(ui["h_about"]), page, re.M), lang
    assert page.count(html.escape(ui["about"], quote=False)) == 1, lang
    assert page.index('<div class="vintro">') < page.index('<div class="vc vv">'), lang
    # 冒頭の画像は 1 つ、alt は文字つき
    intro = page[at["intro"]:page.index("</div></div>", at["intro"])]
    assert intro.count("<img ") == 1 and 'alt="%s"' % html.escape(ui["intro_alt"], quote=True) in intro, lang
    assert 'loading="lazy"' not in intro, "最初の画面の画像は遅延読み込みにしない"
    # 見出し(##)の並び: 触って見る → (目玉・準目玉 | 見どころ)→ シリーズ記事
    headings = [line[3:] for line in page.splitlines() if line.startswith("## ")]
    if lang in ("ja", "en"):
        want = [data["viewers"]["h"][lang], G.MAIN_TEXT[lang]["showcase"], G.MAIN_TEXT[lang]["featured"]]
    else:
        want = [data["viewers"]["h"][lang], ui["h_highlights"]]
    assert headings[:len(want)] == want, (lang, headings[:6])
    assert headings[len(want)].startswith(ui["h_series"]), (lang, headings)
