"""ViEW2026 の本ページ(8 言語とも目玉 20 本)が短く読めること、「くわしく」の行き先が実在すること、
タイルが単色でないことを守る(2026-11-12)。"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageSequence

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("gen_view2026_pages_main", ROOT / "tools" / "gen_view2026_pages.py")
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)

#: 画素値(0-255)の標準偏差の下限。単色の灰色・黒・白のタイルを通さない(実際の最小はこれより十分大きい)。
MIN_TILE_STD = 8.0


def _main_rows(data):
    return [e for e in G.public_data(data)["exhibits"] if e["tier"] in G.MAIN_TIERS]


def test_main_page_is_short_and_has_no_full_captions() -> None:
    data = G.load()
    for lang in data["langs"]:
        page = G.build(data, lang)
        assert len(page.splitlines()) < 220, lang
        visible = re.sub(r'alt="[^"]*"', "", page)          # 画像の代替文(目に見えない)は数えない
        assert "★" not in visible, "%s: 本ページに台帳のキャプション全文が残っている" % lang
        assert ("使った Fullseye の op" if lang == "ja" else "Fullseye ops used") not in page
        assert page.count('href="more.md#d-') == len(_main_rows(data)), lang


def test_every_main_exhibit_has_lead_truth_and_a_details_link_that_exists() -> None:
    data = G.load()
    rows = _main_rows(data)
    assert len(rows) >= 10
    for lang in data["langs"]:
        main, more = G.build(data, lang), G.build_more(data, lang)
        text = G.MAIN_TEXT[lang]
        for e in rows:
            blocks = [line for line in main.splitlines()
                      if line.startswith('<div class="vc">') and ">%s</a>" % G._esc(e["label"][G._content_lang(lang)]) in line]
            assert len(blocks) == 1, (lang, e["id"])
            block = blocks[0]
            assert G._code_html(G._esc(e["lead"][G._content_lang(lang)])) in block, (lang, e["id"])
            assert "%s: %s" % (text["truth"], G._esc(e["truth"][lang])) in block, (lang, e["id"])
            link = "more.md#%s" % G._anchor(e["id"])
            assert link in block, (lang, e["id"])
            # 行き先: おまけページに錨があり、その項目に全文(キャプションと op)がある
            assert more.count('id="%s"' % G._anchor(e["id"])) == 1, (lang, e["id"])
            at = more.index('id="%s"' % G._anchor(e["id"]))
            nxt = more.find("\n- [", at + 10)
            detail = more[at:nxt if nxt >= 0 else None]
            assert G._code_md(e["see"][lang]) in detail, (lang, e["id"])
            if lang in ("ja", "en"):            # 使った op の行は ja/en だけ(ほかの言語は見る所と数字まで)
                assert all(("`%s`" % op) in detail for op in e["ops"]), (lang, e["id"])


def test_viewers_on_the_main_page_are_few_and_the_rest_are_on_the_extras_page() -> None:
    data = G.load()
    vw = data["viewers"]
    assert len(vw["main_ids"]) + len(data["field_viewers"]["items"]) <= G.MAIN_VIEWERS_LIMIT
    for lang in data["langs"]:            # 8 言語とも同じ分け方(2026-11-13。それまで ja/en 以外は全部を本ページに置いていた)
        main, more = G.build(data, lang), G.build_more(data, lang)
        up = "" if lang == "ja" else "../"
        for it in vw["items"]:
            link = "%sviewers/%s.html?lang=%s" % (up, it["id"], lang)
            if it["id"] in vw["main_ids"]:
                assert link in main and link not in more, (lang, it["id"])
            else:
                assert link in more and link not in main, (lang, it["id"])


def test_every_language_shows_the_same_exhibits_in_the_same_order() -> None:
    """8 言語の本ページは、同じ展示を同じ順で、同じ画像のかたまりで出す(中身がそろっていること)。"""
    data = G.load()
    want = [e["id"] for tier in G.MAIN_TIERS for e in _main_rows(data) if e["tier"] == tier]
    assert len(want) == len(set(want)) >= 10
    for lang in data["langs"]:
        page = G.build(data, lang)
        got = re.findall(r'href="more\.md#d-([a-z0-9-]+)"', page)
        assert got == [G._anchor(i)[2:] for i in want], lang
        assert (G.BASE / ("" if lang == "ja" else lang) / "more.md").is_file(), lang
        text = G.MAIN_TEXT[lang]
        assert set(text) >= {"showcase", "featured", "more_top", "more", "truth", "detail", "detail_h", "viewers_more"}, lang
        assert set(G.MORE_TEXT[lang]) == {"title", "intro", "back"}, lang
        rows = _main_rows(data)
        assert len(rows) >= 10
        for e in rows:
            assert e["truth"][lang].strip(), (lang, e["id"])


def _tile_sources(page: str, page_dir: Path) -> dict[str, list[Path]]:
    """本ページの目玉のタイル(<a> の中の画像)から、展示ごとに読む画像(GIF・静止画・reduced-motion 用の静止画)を集める。"""
    found: dict[str, list[Path]] = {}
    page = page.split('<div class="vser">')[0]          # シリーズ記事のタイルより前(目玉と準目玉)
    for anchor in re.findall(r'<a href="[^"]*">(?:<picture>.*?</picture>|<img [^>]*>)', page, re.S):
        refs = re.findall(r'(?:src|srcset)="([^"]+)"', anchor)
        key = None
        for ref in refs:
            match = re.search(r"thumbs/([A-Za-z0-9_-]+)\.jpg|assets/poc/([A-Za-z0-9_-]+)/", ref)
            if match:
                key = match.group(1) or match.group(2)
        assert key, anchor[:120]
        found[key] = [(page_dir / ref).resolve() for ref in refs]
    return found


def test_every_main_tile_image_exists_and_is_not_a_flat_colour() -> None:
    data = G.load()
    rows = _main_rows(data)
    for lang, page_dir in (("ja", G.BASE), ("en", G.BASE / "en")):
        tiles = _tile_sources(G.build(data, lang), page_dir)
        assert {e["id"] for e in rows} == set(tiles), lang
        assert len(tiles) >= 10, lang
        for pid, paths in tiles.items():
            assert paths, pid
            for path in paths:
                assert path.is_file(), (lang, pid, path)
                with Image.open(path) as im:
                    for frame in ImageSequence.Iterator(im):
                        gray = np.asarray(frame.convert("L"), dtype=float)
                        assert gray.std() >= MIN_TILE_STD, (lang, pid, path.name, round(float(gray.std()), 2))


def test_code_like_words_are_set_in_monospace() -> None:
    """op の名前・変数名・例のファイル名(下線でつないだ識別子)は、ページでは等幅(コード記法か <code>)で出す。"""
    assert G._code_md("find_caltab で求め、n_glass は 1.52") == "`find_caltab` で求め、`n_glass` は 1.52"
    assert G._code_md("`find_caltab` と [x_y](a_b/c_d.py) と https://e.x/a_b") == "`find_caltab` と [`x_y`](a_b/c_d.py) と https://e.x/a_b"
    assert G._code_html("uses find_caltab &amp; n_glass") == "uses <code>find_caltab</code> &amp; <code>n_glass</code>"
    assert G._code_md("深さ 0.5 mm・直径 2 mm、_(ja)_") == "深さ 0.5 mm・直径 2 mm、_(ja)_"
    data = G.load()
    assert G._code_md("実際は +inf で、np.nanmedian は") == "実際は +inf で、`np.nanmedian` は"
    bare = G._CODE_WORD
    for lang in data["langs"]:
        for page in (G.build(data, lang), G.build_more(data, lang)):
            visible = re.sub(r"```.*?```", " ", page, flags=re.S)
            visible = re.sub(r'alt="[^"]*"', " ", visible)          # 画像の代替文(目に見えない。中に -> があるとタグの終わりを取り違える)
            visible = re.sub(r"<(style|script|code)\b.*?</\1>", " ", visible, flags=re.S)
            visible = re.sub(r"`[^`\n]+`", " ", visible)
            visible = re.sub(r"!\[[^\]]*\]\([^)]*\)|\]\([^)]*\)|<[^>]+>|https?://\S+", " ", visible)
            left = sorted(set(bare.findall(visible)))
            assert not left, (lang, left[:10])
