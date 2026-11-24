"""ViEW2026 本ページの目玉30本、その8言語のカードと案内文、除外した展示を守る。"""
from __future__ import annotations

import importlib.util
import re
from collections import Counter
from pathlib import Path
from string import Formatter

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "gen_view2026_pages_featured30", ROOT / "tools" / "gen_view2026_pages.py"
)
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)

THERMOGRAPHY_ID = "poc_thermography_ndt"


def _main_rows(data: dict) -> list[dict]:
    """本ページに載せる tier の展示を、正本の順で返す。"""
    return [e for e in data["exhibits"] if e.get("tier") in G.MAIN_TIERS]


def _read_main_pages(data: dict) -> dict[str, str]:
    """生成済みの8言語の本ページを読む。"""
    return {
        lang: (G.BASE / ("" if lang == "ja" else lang) / "index.md").read_text(encoding="utf-8")
        for lang in data["langs"]
    }


def _card_ids(page: str, exhibits: list[dict]) -> list[str]:
    """既存ゲートと同じ「くわしく」の錨をカードの印として、ページ上の展示 id を読む。"""
    anchor_to_id = {G._anchor(e["id"]): e["id"] for e in exhibits}
    assert len(anchor_to_id) == len(exhibits), "展示 id の錨が衝突している"
    anchors = re.findall(r'href="more\.html#(d-[a-z0-9-]+)"', page)
    unknown = [anchor for anchor in anchors if anchor not in anchor_to_id]
    assert not unknown, ("台帳に無い本ページのカード", unknown)
    return [anchor_to_id[anchor] for anchor in anchors]


def _assert_tier_card_counts(data: dict, pages: dict[str, str]) -> None:
    """正本の tier 別本数と、実ファイルに並ぶカードの tier 別本数を突き合わせる。"""
    rows = _main_rows(data)
    expected = Counter(e["tier"] for e in rows)
    assert len(rows) <= G.MAIN_LIMIT, (len(rows), G.MAIN_LIMIT)
    assert (expected["showcase"], expected["featured"], len(rows)) == (16, 14, 30), expected

    by_id = {e["id"]: e for e in data["exhibits"]}
    assert len(by_id) == len(data["exhibits"]), "exhibits の id が重複している"
    for lang in data["langs"]:
        assert lang in pages, (lang, "本ページを読めていない")
        card_ids = _card_ids(pages[lang], data["exhibits"])
        got = Counter(by_id[pid]["tier"] for pid in card_ids)
        assert got == expected, (lang, got, expected)


def _more_top_pattern(template: str) -> re.Pattern[str]:
    """MAIN_TEXT の more_top を、n と m を読む正規表現にする。"""
    parts: list[str] = []
    fields: list[str] = []
    for literal, field, format_spec, conversion in Formatter().parse(template):
        parts.append(re.escape(literal))
        if field is None:
            continue
        assert field in {"n", "m"} and not format_spec and conversion is None, template
        assert field not in fields, (template, field)
        fields.append(field)
        parts.append(rf"(?P<{field}>[0-9]+)")
    assert set(fields) == {"n", "m"}, template
    return re.compile("".join(parts))


def _assert_more_top_counts(data: dict, pages: dict[str, str]) -> None:
    """8言語の more_top に書かれた本ページと残りの本数を正本から検算する。"""
    public = G.public_data(data)
    main_rows = _main_rows(public)
    main_ids = {e["id"] for e in main_rows}
    all_ids = {e["id"] for e in public["all"]}
    assert main_ids <= all_ids, sorted(main_ids - all_ids)
    want = (len(main_rows), len(public["all"]) - len(main_ids))
    for lang in data["langs"]:
        assert lang in pages, (lang, "本ページを読めていない")
        matches = list(_more_top_pattern(G.MAIN_TEXT[lang]["more_top"]).finditer(pages[lang]))
        assert len(matches) == 1, (lang, "more_top が1行見つからない", len(matches))
        got = (int(matches[0].group("n")), int(matches[0].group("m")))
        assert got == want, (lang, got, want)


def _assert_featured_ids(data: dict) -> None:
    """featured_ids は exhibits の id と同じ並びで、重複を許さない。"""
    exhibit_ids = [e["id"] for e in data["exhibits"]]
    featured_ids = data["featured_ids"]
    assert featured_ids == exhibit_ids
    assert len(featured_ids) == len(set(featured_ids)), "featured_ids が重複している"


def _assert_thermography_excluded(data: dict, thumb: Path) -> None:
    """Fullseye の op を通らない熱画像NDTを本ページ系から外し、全展示には残す。"""
    assert THERMOGRAPHY_ID not in {e["id"] for e in data["exhibits"]}
    assert THERMOGRAPHY_ID not in data["featured_ids"]
    assert THERMOGRAPHY_ID not in data["viewers"]["main_ids"]
    assert THERMOGRAPHY_ID in {e["id"] for e in data["all"]}
    assert not thumb.exists(), thumb


def test_tier_counts_match_cards_in_all_eight_generated_main_pages() -> None:
    data = G.load()
    _assert_tier_card_counts(data, _read_main_pages(data))


def test_more_top_reports_main_and_remaining_counts_in_all_eight_languages() -> None:
    data = G.load()
    _assert_more_top_counts(data, _read_main_pages(data))


def test_featured_ids_equal_exhibit_ids_in_order_without_duplicates() -> None:
    _assert_featured_ids(G.load())


def test_thermography_ndt_stays_out_of_main_page_inputs_and_thumbnail() -> None:
    _assert_thermography_excluded(
        G.load(), ROOT / "docs" / "view2026" / "thumbs" / f"{THERMOGRAPHY_ID}.jpg"
    )
