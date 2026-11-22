"""ViEW2026 の主役 10 枚の lead の数を、PoC の記録値へ 1 つずつ結ぶ。"""
from __future__ import annotations

import ast
import copy
import json
import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V26 = json.loads((ROOT / "docs/view2026/exhibits.json").read_text(encoding="utf-8"))
CARDS = {row["id"]: row for row in V26["exhibits"]}


@dataclass(frozen=True)
class CardNumber:
    """lead の表示 1 個と、その根拠になるモジュール直下の記録の対応。"""

    pid: str
    record: str
    path: tuple[str | int, ...]
    transform: str
    ja: str
    en: str


# transform が ``key_integer`` の 3 件は設計条件の数で、値ではなく記録のキー
# (inc20_last / det64 / scratch_c_4)に明記されている。それ以外は記録値またはその丸め。
CARD_NUMBERS = (
    CardNumber("poc_fourier_ptychography", "HEADLINE", ("full", "inc20_last"), "key_integer", "20", "20"),
    CardNumber("poc_registration_basin", "REAL_RECORDED", ("narrow_span_p2pl",), "max_1f", "31.5", "31.5"),
    CardNumber("poc_tdi_linescan", "HEADLINE", ("full", "det64"), "key_integer", "64", "64"),
    CardNumber("poc_illumination_cone_vs_na", "HEADLINE", ("full", "scratch_c_4"), "key_integer", "4", "4"),
    CardNumber("poc_interferometry_step", "HEADLINE", ("std_min_nm",), "direct", "10.5", "10.5"),
    CardNumber("poc_lidar_terrain_change", "REAL_USGS_RECORDED", ("off_flat",), "abs_3f", "0.183", "0.183"),
    CardNumber("poc_polarization_specular", "HEADLINE", ("full", "film_removed_pct"), "about_tens", "9", "90"),
    CardNumber("poc_moire_alignment", "HEADLINE", ("full", "steps_moire"), "direct", "0.08", "0.08"),
    CardNumber("poc_tem_ctf_thon_rings", "HEADLINE_REAL", ("real_worst_pct",), "direct", "0.21", "0.21"),
    CardNumber("poc_solar_el_inspection", "RECORDED_REAL", ("rho", "dim"), "decimal_2f", "0.57", "0.57"),
)

# lead にある数はすべて上で記録へ対応したため、設計条件などを根拠なしとして除外する数は無い。
EXCLUDED_LEAD_NUMBERS: tuple[tuple[str, str, str, str], ...] = ()


def _record(pid: str, name: str):
    """PoC を import せず、モジュール直下のリテラル記録を読む。"""
    tree = ast.parse((ROOT / "examples" / (pid + ".py")).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == name for target in targets):
                return ast.literal_eval(node.value)
    raise AssertionError(f"{pid}: module record {name} not found")


def _at(value, path: tuple[str | int, ...]):
    for part in path:
        value = value[part]
    return value


def _displayed_from_record(case: CardNumber) -> tuple[str, str]:
    record = _record(case.pid, case.record)
    value = _at(record, case.path)
    if case.transform == "direct":
        shown = str(value)
        return shown, shown
    if case.transform == "key_integer":
        numbers = re.findall(r"\d+", str(case.path[-1]))
        assert len(numbers) == 1 and value, (case, numbers, value)
        return numbers[0], numbers[0]
    if case.transform == "max_1f":
        shown = f"{max(value):.1f}"
        return shown, shown
    if case.transform == "abs_3f":
        shown = f"{abs(value):.3f}"
        return shown, shown
    if case.transform == "about_tens":
        pct = int(value)
        return str((pct + 5) // 10), str(10 * ((pct + 5) // 10))
    if case.transform == "decimal_2f":
        shown = str(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        return shown, shown
    raise AssertionError(f"unknown transform: {case.transform}")


def _norm(text: str) -> str:
    return text.replace("−", "-")


def _has_number(text: str, token: str) -> bool:
    """符号を保ち、数字・小数点に接した部分文字列を数値の一致とみなさない。"""
    return re.search(r"(?<![\d.])" + re.escape(token) + r"(?!\d|\.\d)", _norm(text)) is not None


def _lead_numbers(text: str) -> list[str]:
    return re.findall(r"(?<![\d.])[+-]?\d+(?:\.\d+)?(?!\d|\.\d)", _norm(text))


def _card_number_errors(cards: dict[str, dict]) -> list[tuple[str, str, str]]:
    errors = []
    for case in CARD_NUMBERS:
        assert _displayed_from_record(case) == (case.ja, case.en), case
        for lang, token in (("ja", case.ja), ("en", case.en)):
            if not _has_number(cards[case.pid]["lead"][lang], token):
                errors.append((case.pid, lang, token))
    return errors


def test_every_lead_number_is_mapped_to_a_record_key():
    assert not EXCLUDED_LEAD_NUMBERS
    expected: dict[tuple[str, str], list[str]] = {}
    for case in CARD_NUMBERS:
        expected.setdefault((case.pid, "ja"), []).append(case.ja)
        expected.setdefault((case.pid, "en"), []).append(case.en)
    for (pid, lang), tokens in expected.items():
        assert sorted(_lead_numbers(CARDS[pid]["lead"][lang])) == sorted(tokens), (pid, lang)
    assert not _card_number_errors(CARDS)


def test_changed_lead_digit_is_rejected_without_editing_the_ledger():
    broken = copy.deepcopy(CARDS)
    lead = broken["poc_registration_basin"]["lead"]
    lead["ja"] = lead["ja"].replace("31.5", "31.6")
    lead["en"] = lead["en"].replace("31.5", "31.6")
    assert ("poc_registration_basin", "ja", "31.5") in _card_number_errors(broken)
    assert ("poc_registration_basin", "en", "31.5") in _card_number_errors(broken)


def test_short_value_inside_another_number_is_rejected():
    broken = copy.deepcopy(CARDS)
    lead = broken["poc_fourier_ptychography"]["lead"]
    lead["ja"] = lead["ja"].replace("20", "120")
    lead["en"] = lead["en"].replace("20", "120")
    assert ("poc_fourier_ptychography", "ja", "20") in _card_number_errors(broken)
    assert ("poc_fourier_ptychography", "en", "20") in _card_number_errors(broken)


def test_tem_truth_names_the_authors_ctffind3_estimate_in_all_languages():
    truth = CARDS["poc_tem_ctf_thon_rings"]["truth"]
    assert set(truth) == set(V26["langs"])
    assert all("CTFFIND3" in truth[lang] for lang in V26["langs"])
    assert truth["ja"] == "実データ(参照は著者の CTFFIND3 の推定値)"
    assert truth["en"] == "Real data (reference: the authors' CTFFIND3 estimate)"
