"""ViEW2026 目玉 g2 の見出し・カード・図台帳を、PoC を走らせずに照合する。"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
IDS = ["poc_registration_basin", "poc_interferometry_step", "poc_lidar_terrain_change"]
LEDGER = {row["id"]: row for row in json.loads(
    (ROOT / "docs/articles/exhibits/poc_captions.json").read_text(encoding="utf-8"))["exhibits"]}
V26 = json.loads((ROOT / "docs/view2026/exhibits.json").read_text(encoding="utf-8"))
CARDS = {row["id"]: row for row in V26["exhibits"]}
ALL = {row["id"]: row for row in V26["all"]}


def _record(pid: str, name: str):
    """PoC のモジュール直下の記録を、import も実行もせずに読む。"""
    tree = ast.parse((ROOT / "examples" / (pid + ".py")).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    return None


def _norm(text: str) -> str:
    return text.replace("\u2212", "-")


def _has_number(text: str, token: str) -> bool:
    """符号を保ち、数字・小数点に接した部分文字列を数値の一致とみなさない。"""
    return re.search(r"(?<![\d.])" + re.escape(token) + r"(?!\d|\.\d)", _norm(text)) is not None


@pytest.mark.parametrize("pid", IDS)
def test_headline_record_is_a_single_complete_string_set(pid):
    record = _record(pid, "HEADLINE")
    assert isinstance(record, dict) and len(record) >= 4
    assert not [(k, v) for k, v in record.items()
                if not isinstance(k, str) or not isinstance(v, str) or not v]


@pytest.mark.parametrize("pid", IDS)
def test_synthetic_headline_numbers_are_in_both_captions(pid):
    """HEADLINE は合成の章の実行値。符号を含む独立した数値が ja/en の台帳に載る。"""
    for lang in ("ja", "en"):
        caption = _norm(LEDGER[pid]["caption_" + lang])
        missing = [(key, value) for key, value in _record(pid, "HEADLINE").items()
                   if not _has_number(caption, value)]
        assert not missing, (pid, lang, missing)


def test_real_registration_headline_numbers_come_from_real_record():
    record = _record("poc_registration_basin", "REAL_RECORDED")
    band = record["band_p2pl"]["real"]
    loose = record["half_loose"]["p2pl"]
    values = ["%.1f" % v for v in record["narrow_span_p2pl"]]
    values += ["%d" % round(100 * min(band[d][0] for d in ("15", "30"))),
               "%d" % round(100 * max(band[d][1] for d in ("15", "30")))]
    values += ["%.1f" % loose[c][i] for c, i in (("side", 0), ("side", 1), ("real", 0), ("real", 1))]
    values += ["5.3", "4"]
    for lang in ("ja", "en"):
        caption = LEDGER["poc_registration_basin"]["caption_" + lang]
        assert not [value for value in values if not _has_number(caption, value)], (lang, values)


def test_real_lidar_headline_numbers_come_from_real_record():
    record = _record("poc_lidar_terrain_change", "REAL_USGS_RECORDED")
    values = ["%.3f" % abs(record["off_flat"]), str(record["n_valid"]),
              "%.0f" % abs(record["net_raw"]), "%+.0f" % record["net_flat"],
              "%.3f" % record["nmad"], "%.1f" % (100 * record["frac_ch"]),
              "%+.3f" % record["gshift"]]
    for lang in ("ja", "en"):
        caption = _norm(LEDGER["poc_lidar_terrain_change"]["caption_" + lang])
        # off_flat と net_raw は文章が「沈下量」「偽の土量」と向きを語るため絶対値、
        # net_flat と gshift は台帳にも明示された正符号を含めて照合する。
        unsigned = values[:3] + values[4:6]
        signed = values[3:4] + values[6:]
        assert not [value for value in unsigned if not _has_number(caption, value)], (lang, values)
        assert not [value for value in signed if not _has_number(caption, value)], (lang, values)


def test_number_match_rejects_substrings_and_preserves_sign():
    assert _has_number("value 20", "20")
    assert not _has_number("value 120 or 20.0", "20")
    assert _has_number("value +280", "+280")
    assert not _has_number("value 280", "+280")


def test_synthetic_conditions_are_disclosed_where_the_result_is_headlined():
    interference = LEDGER["poc_interferometry_step"]
    assert "合成" in interference["title_ja"] and "synthetic" in interference["title_en"]
    assert "合成" in interference["lead_ja"] and "synth" in interference["lead_en"].lower()
    assert "合成" in CARDS["poc_interferometry_step"]["label"]["ja"]
    assert "synthetic" in CARDS["poc_interferometry_step"]["label"]["en"]
    expected = {"ja": "合成", "en": "synthetic", "zh": "合成", "tw": "合成", "ko": "합성",
                "de": "synthetisch", "hi": "सिंथेटिक", "fr": "synthétique"}
    for lang, word in expected.items():
        assert word in ALL["poc_interferometry_step"]["label"][lang].lower()
    for pid in ("poc_registration_basin", "poc_lidar_terrain_change"):
        row = LEDGER[pid]
        assert "合成" in row["title_ja"] and "synthetic" in row["title_en"]
        assert "合成" in row["lead_ja"] and "synthetic" in row["lead_en"]


@pytest.mark.parametrize("pid", IDS)
def test_card_and_caption_ops_match_source(pid):
    sys.path.insert(0, str(ROOT / "tools"))
    import gen_wingpoc_gallery as gallery

    # registration のカードはまだ exhibits.json に無い(新しいカードは repo の外の断片で、main が入れる)
    if pid in CARDS:
        assert CARDS[pid]["ops"] == LEDGER[pid]["ops"]
    assert LEDGER[pid]["ops"] == gallery._ops_used(pid)


@pytest.mark.parametrize("pid", IDS)
def test_card_and_all_static_media_are_in_figures_ledger(pid):
    figures = {row["file"] for row in json.loads(
        (ROOT / "docs/articles/assets/poc" / pid / "figures.json").read_text(encoding="utf-8"))}
    card = CARDS.get(pid)
    if card and Path(card["media"]).suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
        assert card["media"] in figures
    for key in ("media", "thumb_src"):
        if (ALL[pid].get(key) and
                Path(ALL[pid][key]).suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}):
            assert ALL[pid][key] in figures
