"""ViEW2026 の目玉に足す候補 3 本(フーリエ・タイコグラフィ・TDI ラインスキャン・照明の円錐)の回帰試験(2026-11-15)。

独立レビュー(Claude と Codex)の指摘:
* TDI のカードの CNR(1.52 -> 1.54)が、10-21 の linescan の変更の後の実行(1.23 -> 1.21)と食い違ったまま残っていた。
* 3 本とも題・lead・カードの label に(合成)が無く、FP は「4 倍の視野のまま 20 倍の解像」と、比べる相手(単色の平行光の
  20 倍)と図に出ていない視野を言い切っていた。

各 PoC は見出しの数を ``HEADLINE``(full / reduced の印字)に持ち、実行の値と照合する門を置いた。ここではその記録の
full の値が、台帳の説明(ja / en)に載っていることを静的に確かめる(PoC を走らせない)。
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = {e["id"]: e for e in json.loads(
    (ROOT / "docs/articles/exhibits/poc_captions.json").read_text(encoding="utf-8"))["exhibits"]}
V26 = json.loads((ROOT / "docs/view2026/exhibits.json").read_text(encoding="utf-8"))
CARDS = {e["id"]: e for e in V26["exhibits"]}
ALL = {e["id"]: e for e in V26["all"]}
IDS = ["poc_fourier_ptychography", "poc_tdi_linescan", "poc_illumination_cone_vs_na"]


def _record(pid: str, name: str):
    """PoC のモジュール直下の定数(``HEADLINE`` など)を、実行せずに読む。"""
    tree = ast.parse((ROOT / "examples" / (pid + ".py")).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    return None


def _norm(text: str) -> str:
    return text.replace("\u2212", "-")


@pytest.mark.parametrize("pid", IDS)
def test_headline_record_is_complete_for_both_budgets(pid):
    rec = _record(pid, "HEADLINE")
    assert rec is not None and set(rec) == {"full", "reduced"}
    assert set(rec["full"]) == set(rec["reduced"]) and len(rec["full"]) >= 20
    for value in list(rec["full"].values()) + list(rec["reduced"].values()):
        assert re.fullmatch(r"-?[A-Z0-9. ]+", value), value


@pytest.mark.parametrize("pid", IDS)
def test_full_headline_numbers_are_in_both_captions(pid):
    """記録(full)の数が台帳の説明に全部載る(数字の並びで照合。符号は落とす)。"""
    want = dict(_record(pid, "HEADLINE")["full"])
    want.update(_record(pid, "HEADLINE_REAL") or {})
    for lang in ("ja", "en"):
        cap = _norm(LEDGER[pid]["caption_" + lang])
        missing = [(k, tok) for k, v in want.items() for tok in v.split() if tok.lstrip("-") not in cap]
        assert not missing, (lang, missing)


@pytest.mark.parametrize("pid", IDS)
def test_synthetic_is_said_in_title_lead_and_label(pid):
    row, card = LEDGER[pid], CARDS[pid]
    assert "合成" in row["title_ja"] and "synthetic" in row["title_en"]
    assert "合成" in row["lead_ja"] and "synthetic" in row["lead_en"]
    assert "合成" in card["label"]["ja"] and "synthetic" in card["label"]["en"]
    assert "合成" in ALL[pid]["label"]["ja"] and "synthetic" in ALL[pid]["label"]["en"]
    for lang in V26["langs"]:
        assert card["truth"][lang].strip(), lang
    assert card["ops"] == row["ops"] and row["ops"] == sorted(set(row["ops"]))
    assert "数字の出どころ" in row["caption_ja"] and "Where the numbers come from" in row["caption_en"]
    assert "新 op" not in row["caption_ja"] and "new ops" not in row["caption_en"].lower()


def test_fp_names_its_comparator_and_drops_the_field_claim():
    """FP は「単色の平行光で照らした 20 倍」と条件を書き、普通の照明の 20 倍に届かないことと、図に無い視野を言わない。"""
    row, card = LEDGER["poc_fourier_ptychography"], CARDS["poc_fourier_ptychography"]
    for text in (row["title_ja"], row["lead_ja"], card["label"]["ja"], ALL["poc_fourier_ptychography"]["label"]["ja"]):
        assert "視野のまま" not in text and "20 倍相当" not in text, text
    assert "単色の平行光" in row["lead_ja"] and "普通の照明" in row["lead_ja"]
    assert "ordinary" in row["lead_en"] and "parallel light" in row["lead_en"]
    assert "公表値の独立の確認ではない" in row["caption_ja"] and "not an independent confirmation" in row["caption_en"]
    assert "拒否される" in row["caption_ja"] and "refuses the reconstruction" in row["caption_en"]
    src = (ROOT / "examples/poc_fourier_ptychography.py").read_text(encoding="utf-8")
    assert "位相は reduced では一致、full では 0.19 違い拒否" not in src      # 門の文言(CI の実行も拒否だった)


def test_tdi_does_not_headline_quantities_that_hold_by_construction():
    """照度の 3 因子の積・同じ白板で作った補正の揃い・補正の前後の変調は検算で、見出しの数に出さない。"""
    row = LEDGER["poc_tdi_linescan"]
    for stale in ("1.52", "1.54", "0.961", "0.0006", "2e-16"):
        assert stale not in row["caption_ja"] and stale not in row["caption_en"], stale
    src = (ROOT / "examples/poc_tdi_linescan.py").read_text(encoding="utf-8")
    assert src.count('check("') == 3
    assert "n1[1] == 0 and nmax[1] == 3" in src and 'nmax[2] == 0)' in src


def test_cover_figures_are_the_cards_media():
    """カードの表紙は、縮めても読める図(TDI は 1 段と 64 段の拡大、照明の円錐は 2 x 2)。"""
    for pid, media in (("poc_tdi_linescan", "11_tdi_1_vs_64_closeup.png"),
                       ("poc_illumination_cone_vs_na", "07_cone_cover.png")):
        assert CARDS[pid]["media"] == media
        figures = json.loads((ROOT / "docs/articles/assets/poc" / pid / "figures.json").read_text(encoding="utf-8"))
        assert media in {f["file"] for f in figures}
    assert ALL["poc_illumination_cone_vs_na"]["thumb_src"] == "07_cone_cover.png"
