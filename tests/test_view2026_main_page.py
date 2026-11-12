"""ViEW2026 の ja/en の本ページ(目玉 20 本)が短く読めること、「くわしく」の行き先が実在すること、
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
    for lang in ("ja", "en"):
        page = G.build(data, lang)
        assert len(page.splitlines()) < 220, lang
        visible = re.sub(r'alt="[^"]*"', "", page)          # 画像の代替文(目に見えない)は数えない
        assert "★" not in visible, "%s: 本ページに台帳のキャプション全文が残っている" % lang
        assert ("使った Fullseye の op" if lang == "ja" else "Fullseye ops used") not in page
        assert page.count("](more.md#d-") == len(_main_rows(data)), lang


def test_every_main_exhibit_has_lead_truth_and_a_details_link_that_exists() -> None:
    data = G.load()
    rows = _main_rows(data)
    assert len(rows) >= 10
    for lang in ("ja", "en"):
        main, more = G.build(data, lang), G.build_more(data, lang)
        text = G.MAIN_TEXT[lang]
        for e in rows:
            marker = "- **[%s]" % e["label"][lang]
            start = main.index(marker)
            end = main.find("\n- **[", start + len(marker))
            block = main[start:end if end >= 0 else None]
            assert e["lead"][lang] in block, (lang, e["id"])
            assert "%s: %s" % (text["truth"], e["truth"][lang]) in block, (lang, e["id"])
            link = "more.md#%s" % G._anchor(e["id"])
            assert link in block, (lang, e["id"])
            # 行き先: おまけページに錨があり、その項目に全文(キャプションと op)がある
            assert more.count('id="%s"' % G._anchor(e["id"])) == 1, (lang, e["id"])
            at = more.index('id="%s"' % G._anchor(e["id"]))
            nxt = more.find("\n- [", at + 10)
            detail = more[at:nxt if nxt >= 0 else None]
            assert e["see"][lang] in detail, (lang, e["id"])
            assert all(("`%s`" % op) in detail for op in e["ops"]), (lang, e["id"])


def test_viewers_on_the_main_page_are_few_and_the_rest_are_on_the_extras_page() -> None:
    data = G.load()
    vw = data["viewers"]
    assert len(vw["main_ids"]) + len(data["field_viewers"]["items"]) <= G.MAIN_VIEWERS_LIMIT
    for lang in ("ja", "en"):
        main, more = G.build(data, lang), G.build_more(data, lang)
        up = "" if lang == "ja" else "../"
        for it in vw["items"]:
            link = "%sviewers/%s.html?lang=%s" % (up, it["id"], lang)
            if it["id"] in vw["main_ids"]:
                assert link in main and link not in more, (lang, it["id"])
            else:
                assert link in more and link not in main, (lang, it["id"])
    # ほかの 6 言語は従来どおり全部
    assert all("viewers/%s.html" % it["id"] in G.build(data, "de") for it in vw["items"])


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
        for pid, paths in tiles.items():
            assert paths, pid
            for path in paths:
                assert path.is_file(), (lang, pid, path)
                with Image.open(path) as im:
                    for frame in ImageSequence.Iterator(im):
                        gray = np.asarray(frame.convert("L"), dtype=float)
                        assert gray.std() >= MIN_TILE_STD, (lang, pid, path.name, round(float(gray.std()), 2))
