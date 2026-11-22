"""ViEW2026 目玉候補 g3 の見出し・合成表示・使用 op の静的な回帰試験。"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

from tools import gen_wingpoc_gallery as gallery


ROOT = Path(__file__).resolve().parents[1]
IDS = ["poc_polarization_specular", "poc_moire_alignment", "poc_tem_ctf_thon_rings"]
SYNTHETIC = ["poc_polarization_specular", "poc_moire_alignment"]
LEDGER = {e["id"]: e for e in json.loads(
    (ROOT / "docs/articles/exhibits/poc_captions.json").read_text(encoding="utf-8"))["exhibits"]}
V26 = json.loads((ROOT / "docs/view2026/exhibits.json").read_text(encoding="utf-8"))
CARDS = {e["id"]: e for e in V26["exhibits"]}
ALL = {e["id"]: e for e in V26["all"]}


def _record(pid: str, name: str):
    """PoC を実行せず、モジュール直下のリテラル定数を読む。"""
    tree = ast.parse((ROOT / "examples" / (pid + ".py")).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    return None


def _norm(text: str) -> str:
    return text.replace("−", "-")


@pytest.mark.parametrize("pid", IDS)
def test_headline_record_is_complete_for_both_budgets(pid):
    rec = _record(pid, "HEADLINE")
    assert rec is not None and set(rec) == {"full", "reduced"}
    assert set(rec["full"]) == set(rec["reduced"]) and len(rec["full"]) >= 20
    values = list(rec["full"].values()) + list(rec["reduced"].values())
    assert values
    for value in values:
        assert re.fullmatch(r"[A-Z0-9.+ -]+", value), value


@pytest.mark.parametrize("pid", IDS)
def test_full_headline_numbers_are_in_both_captions(pid):
    want = dict(_record(pid, "HEADLINE")["full"])
    want.update(_record(pid, "HEADLINE_REAL") or {})
    for lang in ("ja", "en"):
        caption = _norm(LEDGER[pid]["caption_" + lang])
        missing = [(key, token) for key, value in want.items() for token in value.split()
                   if token.lstrip("+-") not in caption]
        assert not missing, (lang, missing)


@pytest.mark.parametrize("pid", SYNTHETIC)
def test_synthetic_is_said_in_title_lead_and_labels(pid):
    row = LEDGER[pid]
    assert "合成" in row["title_ja"] and "synthetic" in row["title_en"].lower()
    assert "合成" in row["lead_ja"] and "synthetic" in row["lead_en"].lower()
    assert "合成" in ALL[pid]["label"]["ja"] and "synthetic" in ALL[pid]["label"]["en"].lower()
    if pid in CARDS:
        assert "合成" in CARDS[pid]["label"]["ja"]
        assert "synthetic" in CARDS[pid]["label"]["en"].lower()


@pytest.mark.parametrize("pid", IDS)
def test_declared_ops_match_source_and_cards(pid):
    detected = gallery._ops_used(pid)
    assert LEDGER[pid]["ops"] == detected
    if pid in CARDS:
        assert CARDS[pid]["ops"] == detected


@pytest.mark.parametrize("pid", IDS)
def test_captions_do_not_call_ops_new(pid):
    assert "新 op" not in LEDGER[pid]["caption_ja"]
    assert "new ops" not in LEDGER[pid]["caption_en"].lower()


@pytest.mark.parametrize("pid,cover", [
    ("poc_polarization_specular", "10_glare_cover.png"),
    ("poc_moire_alignment", "09_overlay_cover.png"),
    ("poc_tem_ctf_thon_rings", "17_real_cover.png"),
])
def test_cover_is_recorded_in_figures_ledger(pid, cover):
    figures = json.loads((ROOT / "docs/articles/assets/poc" / pid / "figures.json").read_text(encoding="utf-8"))
    assert cover in {figure["file"] for figure in figures}


def test_polarization_stays_a_fragment_not_an_installed_card():
    assert "poc_polarization_specular" not in CARDS
    assert LEDGER["poc_polarization_specular"]["ops"] == gallery._ops_used("poc_polarization_specular")
    assert ALL["poc_polarization_specular"]["thumb_src"] == "10_glare_cover.png"
