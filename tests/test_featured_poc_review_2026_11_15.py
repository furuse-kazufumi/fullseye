"""PR #317 への独立レビュー(2026-11-15)の指摘の回帰試験。

目玉の PoC の文は、台帳(``poc_captions.json``)・ViEW2026 の手書きのカードと一覧(``docs/view2026/exhibits.json``)・
例の一覧(``examples2d.py`` とそこから作る README / カタログ)の 3 か所に別々に書かれている。台帳の側だけ直しても、
ほかの 2 か所に直す前の言い過ぎが残った(取り下げた語の lead、一覧の古い題、出典の無い手書きのカード)。
ここではその食い違いを、PoC ごとではなく家族で数える。
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = {e["id"]: e for e in json.loads(
    (ROOT / "docs/articles/exhibits/poc_captions.json").read_text(encoding="utf-8"))["exhibits"]}
V26 = json.loads((ROOT / "docs/view2026/exhibits.json").read_text(encoding="utf-8"))
CARDS = {e["id"]: e for e in V26["exhibits"]}
ALL = {e["id"]: e for e in V26["all"]}
FEATURED = list(V26["featured_ids"])
#: 本ページ(ja/en)に載る目玉(tier が showcase / featured)。#313 の時点で「数字の出どころ」を付けた対象は当時の 20 本。
MAIN = [pid for pid in FEATURED if CARDS.get(pid, {}).get("tier") in ("showcase", "featured")]
_DEC = re.compile(r"\d+[.,]\d+")
_NUM = re.compile(r"\d+(?:[.,]\d+)?")


def _numbers(text: str) -> set[str]:
    """数の集合(独仏の小数のコンマは点に直す)。"""
    return {m.replace(",", ".") for m in _NUM.findall(text)}


def _decimals(text: str) -> set[str]:
    """小数だけの集合(見出しの比・倍率。整数の個数や単位の 1 は数えない)。"""
    return {m.replace(",", ".") for m in _DEC.findall(text)}


def _withdrawn_stems(caption: str, lang: str) -> set[str]:
    """説明が「(… までは「X」と書いていた)」/「(until … called it 'X')」と取り下げた語の語幹。"""
    if lang == "ja":
        return {w.rstrip("たるてだ") for w in re.findall(r"「([^」]+)」と書いていた", caption)}
    return {re.sub(r"(?:ed|es|s|ing)$", "", w.casefold()) for w in re.findall(r"called it '([A-Za-z]+)'", caption)}


def test_withdrawn_words_stay_out_of_titles_and_leads_everywhere():
    """取り下げた語は、台帳の題・lead にも、ViEW2026 のカードと一覧の題・lead にも残さない。"""
    problems = []
    checked = 0
    for pid, row in LEDGER.items():
        for lang in ("ja", "en"):
            stems = _withdrawn_stems(row["caption_" + lang], lang)
            if not stems:
                continue
            texts = {"ledger title": row["title_" + lang], "ledger lead": row.get("lead_" + lang, "")}
            for where, src in (("card", CARDS.get(pid)), ("all", ALL.get(pid))):
                if src is None:
                    continue
                langs = [lang] if lang == "ja" else [l for l in V26["langs"] if l != "ja"]
                for l in langs:
                    texts["%s label %s" % (where, l)] = src.get("label", {}).get(l, "")
                    texts["%s lead %s" % (where, l)] = src.get("lead", {}).get(l, "")
            for where, text in texts.items():
                checked += 1
                for stem in stems:
                    if stem.casefold() in text.casefold():
                        problems.append((pid, where, stem))
    assert checked >= 10, checked
    assert not problems, problems


def test_featured_ai_card_puts_the_trivial_baseline_on_the_main_page():
    """本ページの AI の採点のカードは題と lead だけを出す。自明な基準線(AUROC 0.999)は lead に要る。"""
    card = CARDS["poc_ai_built_inspection_scored"]
    assert card.get("tier") in ("showcase", "featured")
    for lang in V26["langs"]:
        assert "0.999" in card["lead"][lang], lang
    assert "偶然を超える検査を組めたのは" in card["label"]["ja"]
    assert "above-chance" in card["label"]["en"]


def test_tum_lead_does_not_headline_the_worst_split_against_the_weakest_baseline():
    """TUM の lead は ja と en で同じ数を主張し、en だけが「合わせないの 0.42 倍」(最弱の基準・最悪の分割の比)を出さない。

    (ja と en の lead の数が違う目玉はほかにもある —— モアレ・字形 —— が、どちらも同じ主張の別の数で、言い過ぎではない。)
    """
    row = LEDGER["poc_real_tum_rgbd_slam"]
    assert _numbers(row["lead_ja"]) == _numbers(row["lead_en"]) == {"8"}
    assert "0.42" not in row["lead_en"] and "0.42" not in row["lead_ja"]


def test_every_featured_caption_says_where_its_numbers_come_from():
    """#313 が本ページの目玉の全部に付けた「数字の出どころ」が、merge で落ちていないこと(台帳かカードのどちらかに)。"""
    rows = [LEDGER[pid] for pid in MAIN if pid in LEDGER]
    assert len(rows) >= 15, len(rows)
    # 台帳を引かない手書きのカード(光弾性・地の検出限界)は、出どころをカードの文に持つ(台帳には無い。master も同じ)。
    marks = {"ja": ("数字の出どころ", "数字は、"), "en": ("where the numbers come from", "the numbers come from")}
    missing = []
    for r in rows:
        card = CARDS[r["id"]]
        for lang, keys in marks.items():
            shown = (r["caption_" + lang] + card["see"][lang] + card["num"][lang]).casefold()
            if not any(k.casefold() in shown for k in keys):
                missing.append((r["id"], lang))
    assert not missing, missing


def test_featured_cards_cite_what_their_ledger_cites():
    """台帳の説明が DOI を引く目玉は、ページのカード(手書きでも)にもその DOI の 1 つが全言語で載る。"""
    problems = []
    cited = 0
    for pid in FEATURED:
        row, card = LEDGER.get(pid), CARDS.get(pid)
        if not row or not card:
            continue
        dois = set(re.findall(r"doi:\s*(10\.\d+/[^\s;,)]+)", row["caption_en"]))
        if not dois:
            continue
        cited += 1
        for lang in V26["langs"]:
            shown = card.get("see", {}).get(lang, "") + card.get("num", {}).get(lang, "") + card["lead"].get(lang, "")
            if not any(doi in shown for doi in dois):
                problems.append((pid, lang))
    assert cited >= 1, cited
    assert not problems, problems


def test_all_list_titles_of_featured_pocs_claim_no_number_the_main_page_dropped():
    """一覧(all)の題は、目玉から外せばページに出る。本ページの題が落とした数(TUM の 0.42、クルミの 2.6)を残さない。"""
    problems = []
    for pid in FEATURED:
        card, row = CARDS.get(pid), ALL.get(pid)
        if not card or not row:
            continue
        allowed = _decimals(card["label"]["ja"]) | _decimals(card["label"]["en"])
        for lang in V26["langs"]:
            extra = _decimals(row["label"][lang]) - allowed
            if extra:
                problems.append((pid, lang, sorted(extra)))
    assert not problems, problems


_EX_ROW = re.compile(r'\{"id": "(poc_[a-z0-9_]+)", "task": "[^"]*", "data": "([a-z]+)"')


def test_examples_registry_does_not_call_a_simulation_real_data():
    """題に「シミュレーション」とある目玉の PoC を、例の一覧(examples2d.py)が実データ(real)と分類しない。

    (目玉の外の行は、この PR の範囲の外なので数えない。)
    """
    data = dict(_EX_ROW.findall((ROOT / "examples2d.py").read_text(encoding="utf-8")))
    sims = [pid for pid in FEATURED if pid in LEDGER and "シミュレーション" in LEDGER[pid]["title_ja"] and pid in data]
    assert len(sims) >= 2, sims
    wrong = [pid for pid in sims if data[pid] == "real"]
    assert not wrong, wrong


@pytest.mark.parametrize("rel", ["examples2d.py", "docs/README.md", "examples/README.md",
                                 "docs/OP_CATALOG.md", "fullseye/OP_CATALOG.md"])
def test_public_lists_drop_the_retracted_headline_claims(rel):
    """台帳で取り下げた言い過ぎが、公開の一覧(examples2d の名前・要約と、そこから作る README・カタログ)に残らない。"""
    text = (ROOT / rel).read_text(encoding="utf-8")
    retracted = ("分けられない量と検出できない誤差", "等速とほぼ同じ水準", "残差にも旗にも出ずに n_glass を",
                 "4 材質で物理的に撮像し")
    assert [p for p in retracted if p in text] == []


def _bottle_poc():
    spec = importlib.util.spec_from_file_location("_poc_bottle_review", ROOT / "examples/poc_bottle_pattern_inverse.py")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(ROOT / "examples"))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(ROOT / "examples"))
    return mod


def test_bottle_flag_names_the_wall_so_the_caption_must_not_say_unnoticed():
    """満の瓶・偏心 0.3 mm・雑音 1.5 階調(PoC の 5b と同じ種)で、旗 poorly_determined は壁厚を名指しする。

    だから説明は「壁厚の偏りには気づけない」と書けない —— 知らせないのは偏りの向きと大きさ。
    """
    B = _bottle_poc()
    x = B.band_map(0.5, 1.333)["x_mm"]
    ul = np.array([B.eccentric_u(xx, 0.3, 0.0, 1.333) for xx in x])
    U = np.tile(ul, (B.BAND_ROWS, 1))
    mm = {"u_mm": U, "weight": np.ones(U.shape), "valid": np.isfinite(U), "x_mm": x}
    r = B.fit(B.observe(mm, np.random.default_rng(5000)), x, restarts=3, rows_per_section=1)
    assert "wall_mm" in r["poorly_determined"], r["poorly_determined"]
    rel = r["sigma"]["wall_mm"] / r["wall_mm"]
    assert 0.02 < rel < 0.10, rel
    row = LEDGER["poc_bottle_pattern_inverse"]
    assert "気づけない" not in row["caption_ja"]
    assert "goes unnoticed" not in row["caption_en"]
    assert "poorly_determined" in row["caption_ja"] and "poorly_determined" in row["caption_en"]


def test_review_limits_are_stated_in_the_captions():
    """数字の読み方の限界(独立レビューの指摘)を説明に書いておく: TUM・テレセン・OCT。"""
    tum, tel, oct_ = (LEDGER[k] for k in ("poc_real_tum_rgbd_slam", "poc_telecentric_metrology", "poc_industrial_oct"))
    assert "既発表の手法の RPE の値とは桁も比べていない" in tum["caption_ja"]
    assert "no comparison, not even of magnitude" in tum["caption_en"]
    assert "± は当てはめの統計誤差だけ" in tel["caption_ja"] and "statistical fit error only" in tel["caption_en"]
    assert "顕微鏡との比較も同じ対応に依り" in oct_["caption_ja"] and "microscope comparison rests on the same assignment" in oct_["caption_en"]
