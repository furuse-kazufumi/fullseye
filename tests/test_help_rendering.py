# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Studio op ヘルプの**描画**と**多言語被覆**の門(2026-10-07)。

生成できたことと読めることは別。2026-10-07 の見直しで、全言語の頁に次の 4 つが
出ていた(実測、英語版 3,089 枚中):

a. RST の二重バッククォート ``x`` を `x` 2 組と読み、コードと散文が**反転**(2,835 枚)
b. ``:func:`residue_crt``` などの RST ロールが生で見える(628 枚)
c. 太字の中にコードがあると ``**`` ごと生で出る(562 枚)
d. docstring の折り返し 1 行ごとに段落が切れる(小文字で始まる段落 6,366 個)

ここでは (1) 各欠陥を最小入力で固定し、(2) 同梱の全頁を数えて残りゼロを門にし、
(3) 門が本当に噛むことを壊した入力で確かめる。あわせて、訳の被覆が**後退しない**
ことを ``docs/i18n/help_coverage.json`` と突き合わせる(ラチェット)。
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import opdocs as OD  # noqa: E402

HELP = os.path.join(ROOT, "studio_assets", "op_help")


def _p(html):
    """``<p>…</p>`` の中身の一覧(順序どおり)。"""
    import re
    return re.findall(r"<p(?:\s[^>]*)?>(.*?)</p>", html, re.S)


# --------------------------------------------------------------------------- #
# a. 二重バッククォート                                                          #
# --------------------------------------------------------------------------- #
def test_double_backticks_are_one_code_span_not_inverted():
    got = OD.md_to_html("A band of wavelength ``p`` measures the local shift only modulo ``p``, so")
    assert got.count("<code") == 2, got
    assert '<code style="color:#22d3bf">p</code> measures the local shift only modulo ' in got, got
    assert "`" not in got, got
    assert "</code><code" not in got, got


def test_double_backticks_may_contain_a_single_backtick_and_padding():
    got = OD.md_to_html("use `` `x` `` here and ``a**2`` there")
    assert ">`x`</code>" in got, got
    assert ">a**2</code>" in got and "<b>" not in got, got


def test_single_backticks_still_work():
    got = OD.md_to_html("call `fullseye.apply` now")
    assert ">fullseye.apply</code>" in got and "`" not in got


# --------------------------------------------------------------------------- #
# b. RST ロール                                                                  #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("src,shown", [
    (":func:`residue_crt`", "residue_crt"),
    (":class:`~pkg.mod.Thing`", "Thing"),
    (":mod:`fullseye.ledger`", "fullseye.ledger"),
    (":meth:`the method <Thing.run>`", "the method"),
    (":data:`SEEN_STRINGS`", "SEEN_STRINGS"),
    (":attr:`!x.y`", "x.y"),
    (":py:func:`f`", "f"),
])
def test_rst_roles_render_as_code_of_the_target(src, shown):
    got = OD.md_to_html("see %s for details" % src)
    assert '<code style="color:#22d3bf">%s</code>' % shown in got, got
    assert OD.render_artifacts(got)["rst_role_leak"] == 0, got


# --------------------------------------------------------------------------- #
# c. 太字の中のコード / 冪乗                                                      #
# --------------------------------------------------------------------------- #
def test_bold_may_contain_code():
    got = OD.md_to_html("- **complex input raises `ValueError`** — float64 truncates")
    assert '<b>complex input raises <code style="color:#22d3bf">ValueError</code></b>' in got, got
    assert "**" not in got, got


def test_bold_ending_in_code_does_not_swallow_the_next_item():
    """回帰: 太字の末尾がコード(``**… `ValueError`**``)でも次の箇条書きは別の項目。"""
    md = ("- **complex 入力は `ValueError`** — 虚部を捨てる。`.real` を明示する。\n"
          "- **masked array は `ValueError`** — マスクを剥がさない。\n"
          "- **NaN/Inf は `ValueError`**。")
    got = OD.md_to_html(md)
    assert got.count("• ") == 3, got
    assert got.count("<b>") == 3 and "**" not in got, got


def test_bold_may_contain_a_link():
    got = OD.md_to_html("**see [the guide](../guides/blob_analysis.md) first**")
    assert got.count("<b>") == 1 and 'href="guide2d:blob_analysis"' in got, got
    assert "**" not in got, got


def test_power_operator_in_prose_is_not_bold():
    got = OD.md_to_html("energy is x**2 + y**2 here")
    assert "<b>" not in got and "x**2 + y**2" in got, got
    assert OD.render_artifacts(got)["literal_double_star"] == 0, got


@pytest.mark.parametrize("src,want", [
    ("逆に**中間を強調する**S字カーブ", "<b>中間を強調する</b>S字カーブ"),          # 閉じの直後が英字
    ("— **regardless of *slopes*** (tie)", "<b>regardless of *slopes*</b> (tie)"),   # 星が 3 つ続く
    ("大域解ではなく **E ≤ 2c E\\*** の保証", "<b>E ≤ 2c E*</b> の保証"),           # \* のエスケープ
    ("**0.5095**(相対 +1.9 %)", "<b>0.5095</b>(相対 +1.9 %)"),                   # 閉じの直後が ASCII 括弧
])
def test_bold_edge_cases_seen_in_the_corpus(src, want):
    got = OD.md_to_html(src)
    assert want in got, got
    assert OD.render_artifacts(got)["literal_double_star"] == 0, got


def test_bold_that_wraps_across_lines_is_joined_even_when_indented():
    md = ("Head line\n  more\n\n      16   0.1   0.2\n\n"
          "  (実測)が、帯が 1.5 倍になる。**規格に合わせる側を採り、\n  ずれを書く**方を選んだ。")
    got = OD.md_to_html(md)
    assert "<b>規格に合わせる側を採り、ずれを書く</b>方を選んだ。" in got, got


def test_code_span_that_wraps_inside_an_indented_block_is_joined():
    md = 'Summary.\n\nReturns:\n    dict: ``{"a": (3,),\n    "b": float}``\n'
    got = OD.md_to_html(md)
    assert '<code style="color:#22d3bf">{&quot;a&quot;: (3,), &quot;b&quot;: float}</code>' in got, got
    assert "`" not in got, got


def test_kwargs_field_is_not_a_bold_opener():
    md = "Args:\n    arrows: whether.\n    **stream_kw: passed through.\nReturns:\n    image."
    got = OD.md_to_html(md)
    assert "**stream_kw: passed through." in got and "Returns:" in got, got
    assert "passed through. Returns" not in got, got                 # 次の欄へ流れ込まない
    assert OD.render_artifacts(got)["literal_double_star"] == 0, got


def test_japanese_bold_next_to_kana_still_bolds():
    got = OD.md_to_html("``b < 0.5`` は**全部同じ濃さ**、それ以外")
    assert "<b>全部同じ濃さ</b>" in got, got


# --------------------------------------------------------------------------- #
# d. 段落の折り返し                                                              #
# --------------------------------------------------------------------------- #
def test_wrapped_lines_join_into_one_paragraph():
    md = "Local displacement from band phases.\nA band of wavelength ``p`` is\nmeasured here.\n\nSecond paragraph."
    ps = _p(OD.md_to_html(md))
    assert len(ps) == 2, ps
    assert ps[0].startswith("Local displacement from band phases. A band of wavelength"), ps


def test_raw_docstring_first_line_joins_its_indented_continuation():
    """``__doc__`` のまま: 1 行目だけ左端 0、続きは 4 字下げ(cleandoc と同じ事情)。"""
    md = "Summary that wraps\n    onto a second line.\n\n    Body paragraph that\n    also wraps."
    ps = _p(OD.md_to_html(md))
    assert ps == ["Summary that wraps onto a second line.", "Body paragraph that also wraps."], ps


def test_a_label_line_starts_a_new_paragraph():
    """「**Where it applies**: …」「注意: …」のような見出し語の行は前の段落につながない。"""
    md = ("**Where it applies**: textured\nregions.\n**Where it does not**: within\nboundary.\n"
          "注意: 画像は\n続く。")
    ps = _p(OD.md_to_html(md))
    assert ps == ["<b>Where it applies</b>: textured regions.",
                  "<b>Where it does not</b>: within boundary.",
                  "注意: 画像は続く。"], ps


def test_japanese_lines_join_without_a_space():
    ps = _p(OD.md_to_html("日本語の行は\n続く。"))
    assert ps == ["日本語の行は続く。"], ps


def test_structure_survives_joining():
    md = ("Intro line one\nintro line two:\n\n"
          "- item one\n  continues\n- item two\n\n"
          "| a | b |\n| 1 | 2 |\n\n"
          "Parameters\n----------\nx : int\n    first desc\n\n"
          "    u_t = Du*lap(u) - u v^2\n    v_t = Dv*lap(v) + u v^2\n\n"
          ">>> f(1)\n2\n\n"
          "```python\nline1\nline2\n```\n"
          "## Heading\nafter heading")
    html = OD.md_to_html(md)
    ps = _p(html)
    assert "Intro line one intro line two:" in ps
    assert "• item one continues" in ps and "• item two" in ps
    assert "| a | b |" in ps and "| 1 | 2 |" in ps                     # 表の行は 1 行ずつ
    assert '<h4 style="color:#17b8a6;margin:6px 0 2px 0">Parameters</h4>' in html
    assert "----------" not in html
    assert "x : int" in ps
    assert "u_t = Du*lap(u) - u v^2" in ps and "v_t = Dv*lap(v) + u v^2" in ps  # 数式はつながない
    assert "&gt;&gt;&gt; f(1)" in ps
    assert "line1\nline2" in html                                       # コード塊は改行のまま
    assert "<h3" in html and "after heading" in ps


# --------------------------------------------------------------------------- #
# 枠の文言(ボタン・ラベル・図の種類)は読み手の言語で                              #
# --------------------------------------------------------------------------- #
def test_fixed_ui_labels_follow_the_page_language():
    md = "```program\ngaussian(0.5,0.5)\n```\n```mermaid\ngraph LR\n```\n```math\nx\n```"
    tbl = OD._i18n()
    for lang in ("en", "zh", "ko", "de"):
        got = OD.md_to_html(md, lang=lang)
        for key in ("▸ このパイプラインを読み込む", "読み込んで実行", "Mermaid 図(ソース):",
                    "数式(LaTeX)(ソース):"):
            want = tbl[key][lang]
            import html as _h
            assert _h.escape(want) in got, (lang, key, got)
        assert "ソース" not in got, (lang, got)
    assert "Load this pipeline" in OD.md_to_html(md, lang="en")
    assert "このパイプラインを読み込む" in OD.md_to_html(md)       # 既定は日本語


def test_jpeg_figure_link_label_is_translated():
    md = "![threshold: knob a sweep](../_fig/threshold_knob_a.jpg)"
    got = OD.md_to_html(md, lang="de")
    assert "threshold: Regler a durchfahren" in got and "(Doku-Website)" in got, got
    assert "knob a sweep" not in got and "docs site" not in got, got


# --------------------------------------------------------------------------- #
# 背景知識ガイドの題名                                                            #
# --------------------------------------------------------------------------- #
def test_every_knowledge_guide_title_is_translated():
    kg = OD.knowledge_guides()
    assert len(kg) >= 15, "知識ガイドが %d 本しか見つからない(走査が縮んだ?)" % len(kg)
    assert not OD.guides_without_title_translation(), OD.guides_without_title_translation()
    for g in kg:
        for lang in ("en", "de"):
            assert not OD.has_japanese(OD.guide_title(g, lang).replace("—", "")), (g["stem"], lang)


def test_guide_page_heading_is_localized_but_ja_is_untouched():
    g = OD.knowledge_guides()[0]
    with open(g["path"], encoding="utf-8") as f:
        md = f.read()
    assert OD._localize_guide_md(md, "ja") == md
    en = OD._localize_guide_md(md, "en")
    assert ("# " + OD.guide_title(g, "en")) in en and ("# " + g["title"]) not in en


# --------------------------------------------------------------------------- #
# 全頁の門(同梱物を数える)+ 門が噛むことの確認                                    #
# --------------------------------------------------------------------------- #
def _generated_pages():
    out = []
    for dp, _dn, fn in os.walk(HELP):
        if os.path.basename(dp) == "fig":
            continue
        for f in fn:
            if f.endswith(".html"):
                p = os.path.join(dp, f)
                with open(p, encoding="utf-8") as fh:
                    raw = fh.read()
                if OD._GEN_MARK in raw[:200]:
                    out.append((os.path.relpath(p, HELP).replace(os.sep, "/"), raw))
    return out


#: 2026-10-07 時点の同梱頁は 6 言語 × 約 3,100 op + ガイド。これを大きく割ったら
#: 走査が縮んでいる(門が空を通す)ので落とす。
_MIN_PAGES = 15000


def test_generated_help_pages_have_no_rendering_artifacts():
    if not os.path.isdir(HELP):
        pytest.skip("studio_assets/op_help が無い")
    pages = _generated_pages()
    assert len(pages) >= _MIN_PAGES, "生成頁が %d 枚しか無い(下限 %d)" % (len(pages), _MIN_PAGES)
    total, where = {}, {}
    for rel, raw in pages:
        for k, v in OD.render_artifacts(raw).items():
            total[k] = total.get(k, 0) + v
            if v and k not in where:
                where[k] = rel
    bad = {k: v for k, v in total.items() if v}
    assert not bad, ("ヘルプに描画欠陥が残っている %s(例: %s)—— "
                     "`py -3.11 tools/opdocs.py html`" % (bad, where))


def _item_lines(md):
    """``md`` の箇条書きの行数(コード塊の中は数えない)。"""
    n, in_code = 0, False
    for line in md.split("\n"):
        st = line.strip()
        if st.startswith("```"):
            in_code = not in_code
            continue
        if not in_code and (st.startswith("- ") or st.startswith("* ") or st.startswith("• ")):
            n += 1
    return n


def test_joining_never_swallows_a_list_item_across_the_corpus():
    """段落をつなぐ規則が箇条書きを飲み込まないこと(全ノート・全ガイドで数える)。

    描画欠陥の門(上)は「生の記号が残る」を数えるが、「2 項目が 1 項目に化ける」は
    記号を残さないので見えない —— 2026-10-07 に zh の契約欄でそれが起きた。
    """
    import glob
    paths = [p for p in glob.glob(os.path.join(OD.DOCS, "**", "*.md"), recursive=True)
             if os.path.basename(p) not in ("SAMPLES.md",) and not os.path.basename(p).startswith("INDEX")]
    assert len(paths) >= 3000, "ノートが %d 本しか無い(走査が縮んだ?)" % len(paths)
    bad = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            md = f.read()
        want = _item_lines(md)
        got = OD.md_to_html(md).count(">• ")
        if got != want:
            bad.append("%s (%d→%d)" % (os.path.relpath(p, OD.DOCS), want, got))
    assert not bad, "箇条書きの数が変わったノート %d 本: %s" % (len(bad), bad[:8])


@pytest.mark.parametrize("broken,kind", [
    # 2026-10-06 までの生成器が実際に出していた形
    ('<p>A band of wavelength `<code style="color:#22d3bf">p</code><code style="color:#22d3bf">'
     ' measures the local shift only modulo </code><code style="color:#22d3bf">p</code>`, so</p>',
     "split_code"),
    ('<p>A band of wavelength `<code style="color:#22d3bf">p</code><code style="color:#22d3bf">'
     ' measures</code>`</p>', "stray_backtick"),
    ('<p>of :func:<code style="color:#22d3bf">residue_crt</code>.</p>', "rst_role_leak"),
    ('<p>• **complex input raises <code style="color:#22d3bf">ValueError</code>** — x</p>',
     "literal_double_star"),
])
def test_the_rendering_gate_bites(broken, kind):
    assert OD.render_artifacts(broken)[kind] > 0


def test_pre_blocks_are_exempt_from_the_rendering_gate():
    """``<pre>`` の中(プログラム・doctest・Mermaid)は原文どおりなので数えない。"""
    assert not any(OD.render_artifacts('<pre style="x">a**b `c` :func:x</pre>').values())


# --------------------------------------------------------------------------- #
# 被覆のラチェット                                                               #
# --------------------------------------------------------------------------- #
def _committed_coverage():
    p = OD.HELP_COVERAGE_PATH
    assert os.path.exists(p), "docs/i18n/help_coverage.json が無い —— `py -3.11 tools/opdocs.py coverage`"
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def test_help_coverage_ledger_names_every_language():
    cov = _committed_coverage()
    assert set(cov["languages"]) == set(OD.LANGS), sorted(cov["languages"])
    for lang in OD.LANGS:
        if lang != "ja":
            row = cov["languages"][lang]
            assert row["pages"] >= 1000, (lang, row)
            assert {"pages_with_kana", "summaries_untranslated", "pages_with_example",
                    "summary_translated_share", "kana_free_share"} <= set(row), row


def test_help_translation_coverage_does_not_regress():
    """訳済み比率が下がる・未訳が増えると赤。意図した後退は
    ``py -3.11 tools/opdocs.py coverage --accept-regression`` で人が受け入れる。"""
    if not os.path.isdir(HELP):
        pytest.skip("studio_assets/op_help が無い")
    bad = OD.coverage_regressions(_committed_coverage(), OD.help_coverage())
    assert not bad, "ヘルプの訳の被覆が後退した: " + "; ".join(bad)


def test_new_ops_need_an_english_summary():
    """英語の要約が無い op(英語版で「まだ訳がありません」と断る頁)を**増やさない**。

    要約訳は ``docs/i18n/op_summary.json``(``<dim>/<op>`` → ``fp`` + 言語ごとの訳)。
    """
    if not os.path.isdir(HELP):
        pytest.skip("studio_assets/op_help が無い")
    was = _committed_coverage()["languages"]["en"]["summaries_untranslated"]
    now = OD.help_coverage()["languages"]["en"]["summaries_untranslated"]
    assert now <= was, ("英語の要約が無い op が %d → %d に増えた。docs/i18n/op_summary.json に "
                        "en の要約(と fp)を足す" % (was, now))


def test_the_coverage_ratchet_bites():
    cur = {"languages": {"en": {"summaries_untranslated": 10, "summary_translated_share": 0.9}},
           "frame_strings": {"keys": 10, "en": 10}, "knowledge_guide_titles": {"guides": 2, "en": 2}}
    worse = json.loads(json.dumps(cur))
    worse["languages"]["en"].update(summaries_untranslated=11, summary_translated_share=0.89)
    worse["frame_strings"]["en"] = 9
    worse["knowledge_guide_titles"]["en"] = 1
    bad = OD.coverage_regressions(cur, worse)
    assert len(bad) == 4, bad
    assert not OD.coverage_regressions(cur, cur)
    assert OD.coverage_regressions(cur, {"languages": {}}), "言語ごと消えたのを見逃す"
