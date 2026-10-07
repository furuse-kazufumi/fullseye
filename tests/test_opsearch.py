"""意味で op を引く検索(fullseye.opsearch / fullseye-rag search / MCP fullseye_find_ops)の門(2026-10-07)。

ノートの本文が日本語なので、grep では「Rauschen」「降噪」「잡음」が 0 件だった。要約 6 言語を
索引にした検索が、各言語で意味の合う op を上位に返すこと・索引が正本と同じ範囲を数えることを固定する。
"""
import json
import os

import pytest

import fullseye
from fullseye import opsearch
from fullseye.opsearch import detect_lang, search_ops, tokenize

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EDGE = {"canny3d", "sobel_mag", "sobel_amp", "prewitt_mag", "roberts_mag", "xpil_find_edges", "xkor_canny",
        "hx_detect_edge_segments", "xsp_gauss_grad_mag", "sk_canny", "edges_image", "roberts"}
NOISE = {"xsp_dct_denoise", "xcv3_denoise_tvl1", "cv_median", "sk_wavelet", "sk_tv", "sk_tv_bregman", "sk_nlm",
         "cv_nlmeans", "temporal_bilateral", "tb_temporal_bilateral", "bilateral_filter_depth", "median_image",
         "tb_mls_smooth", "mls_smooth", "ph_total_variation_flow", "xwt_firm_denoise", "remove_noise_region",
         "gray_opening_rect", "xmh_majority"}


@pytest.mark.parametrize("lang,query,want", [
    ("ja", "エッジ検出", EDGE), ("en", "edge detection", EDGE), ("zh", "边缘检测", EDGE),
    ("ko", "에지 검출", EDGE), ("de", "Kantenerkennung", EDGE), ("tw", "邊緣", EDGE),
    ("ja", "ノイズ除去", NOISE), ("en", "denoise", NOISE), ("zh", "去噪", NOISE),
    ("ko", "노이즈 제거", NOISE), ("de", "Rauschen entfernen", NOISE), ("tw", "雜訊去除", NOISE),
    # hi: 訳の方針(術語は英語のまま)に合わせ、術語は英語・文はヒンディー語の問い合わせ
    ("hi", "edge पहचान", EDGE), ("hi", "noise हटाना", NOISE),
])
def test_each_language_finds_ops_that_do_the_job(lang, query, want):
    r = search_ops(query, k=8, lang=lang)
    names = [o["name"] for o in r["ops"]]
    assert len(names) == 8
    assert set(names) & want, "%s %r: %s" % (lang, query, names)
    rows = r["ops"]
    assert rows
    assert all(o["summary"] for o in rows)


def test_a_grep_of_the_notes_cannot_do_this():
    """零点: 同じ問い合わせ語はノート本文に無い(だから要約の訳を索引にした)。"""
    hits = 0
    for dp, _, fs in os.walk(os.path.join(ROOT, "docs", "ops")):
        for f in fs:
            if f.endswith(".md"):
                with open(os.path.join(dp, f), encoding="utf-8") as fh:
                    t = fh.read()
                hits += ("Rauschen" in t) + ("잡음" in t) + ("降噪" in t)
    assert hits == 0
    for q in ("Rauschen entfernen", "잡음 제거", "降噪"):
        assert search_ops(q, k=5)["ops"]


def test_exact_name_and_halcon_name_come_first():
    assert search_ops("otsu", k=3)["ops"][0]["name"] == "otsu"
    r = search_ops("abs_diff_image", k=3)
    assert r["ops"][0]["name"] == "abs_diff_image"


def test_language_is_inferred_from_the_query():
    assert detect_lang("잡음") == "ko" and detect_lang("ノイズ") == "ja"
    assert detect_lang("降噪") == "zh" and detect_lang("Rauschunterdrückung") == "de"
    assert detect_lang("denoise") == "en"
    # 漢字だけの日本語は文字種で決まらない → 要約の当たりで ja を選ぶ
    assert search_ops("二値化", k=5)["lang"] == "ja"
    assert search_ops("Kanten erkennen", k=5)["lang"] == "de"


def test_tokenizer_splits_cjk_into_bigrams_and_stems_latin():
    assert tokenize("ノイズ除去") == ["ノイ", "イズ", "ズ除", "除去"]
    assert tokenize("denoising") == tokenize("denoise") == ["denois"]
    assert tokenize("gauss_filter") == ["gauss", "filter"]


def test_index_covers_the_same_ops_as_the_notes():
    """検索層が自分の範囲を正直に数えること: 索引の op 数 = 出荷ノートの枚数。"""
    with open(os.path.join(ROOT, "fullseye", "data", "OP_NOTES.json"), encoding="utf-8") as f:
        notes = json.load(f)
    with open(os.path.join(ROOT, "fullseye", "data", "OP_SEARCH.json"), encoding="utf-8") as f:
        ix = json.load(f)
    assert ix["n_ops"] == len(ix["ops"]) == notes["n_notes"]
    per = ix["summaries_per_language"]
    assert per["ja"] == ix["n_ops"]                                      # 要約の無い op は無い
    # 訳の床(下げたら赤): 2026-10-07 の実測
    assert per["en"] >= 2396 and min(per[x] for x in ("zh", "tw", "ko", "de")) >= 2997
    rows = ix["ops"]
    assert rows
    assert all(r.get("p") for r in rows)                                # 全行がノートを指す


def test_index_is_shipped_in_the_wheel():
    with open(os.path.join(ROOT, "pyproject.toml"), encoding="utf-8") as f:
        assert '"data/OP_SEARCH.json"' in f.read()


def test_filters_and_errors():
    rows = search_ops("threshold", k=20, out_sort="region")["ops"]
    assert rows
    assert all(o["out_sort"] == "region" for o in rows)
    r = search_ops("qqqzzzxx")
    assert r["total"] == 0 and r["hint"]
    with pytest.raises(ValueError):
        search_ops("  ")
    with pytest.raises(ValueError):
        search_ops("edge", lang="fr")
    with pytest.raises(ValueError):
        search_ops("edge", k=0)


def test_facade_cli_and_mcp_share_one_search(capsys):
    assert fullseye.search_ops is opsearch.search_ops
    from fullseye import rag_setup
    assert rag_setup.main(["search", "otsu", "-k", "2"]) == 0
    out = capsys.readouterr().out
    assert "otsu" in out and "note: docs/ops/" in out
    assert rag_setup.main(["search", "qqqzzzxx"]) == 1
    from fullseye.mcp.catalog import Catalog
    from fullseye.mcp.server import ArgError, call_tool
    cat = Catalog.load()
    res = call_tool("fullseye_find_ops", {"query": "边缘检测", "limit": 5}, cat)
    rows = res["structuredContent"]["ops"]
    assert len(rows) == 5 and set(o["name"] for o in rows) & EDGE
    with pytest.raises(ArgError):
        call_tool("fullseye_find_ops", {"query": " "}, cat)



@pytest.mark.parametrize("query,lang,want", [
    ("雑音除去", "ja", NOISE),          # 要約は「ノイズ除去」と書く —— 言い換え表なしでは 0 件だった
    ("邊緣檢測", "tw", EDGE),           # 台湾の要約は「偵測」と書く —— 言い換え表なしでは 0 件だった
])
def test_same_language_synonyms_reach_ops_written_with_the_other_word(query, lang, want):
    names = [o["name"] for o in search_ops(query, k=8, lang=lang)["ops"]]
    assert names
    assert set(names) & want, names


def test_synonym_table_is_not_cross_language_and_stays_small():
    """言い換え表は同じ言語の中だけ(言語をまたぐ対応は 6 言語の要約が持つ)。広い語(境界・輪郭)を
    入れるとメッシュの「辺」などを巻き込んで悪化した(2026-10-07 実測)ので、狭く保つ。"""
    from fullseye.opsearch import SYNONYMS
    assert SYNONYMS
    assert all(2 <= len(g) <= 4 for g in SYNONYMS)
    banned = {"boundary", "rand", "輪郭", "轮廓", "경계"}
    assert not banned & {w for g in SYNONYMS for w in g}



def test_hindi_function_words_do_not_match_everything():
    """★2026-10-07: 「का」「पता」のような機能語を残すと 1 語で 1,000 op 以上が当たった。"""
    from fullseye.opsearch import tokenize
    assert tokenize("किनारे का पता लगाना") == ["किनारे"]
    assert detect_lang("edge पहचान") == "hi"
    r = search_ops("edge पहचान", k=3)
    rows = r["ops"]
    assert r["lang"] == "hi"
    assert rows
    assert all(o["summary"] for o in rows)
