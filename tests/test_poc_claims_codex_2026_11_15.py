"""外部レビュー(Codex、2026-11-15)の目玉の PoC への指摘の回帰試験。

指摘は 9 件(high 1・medium 6・low 2)で、どれも「書いてある事」が門と出力の支える範囲より広いか、門が公開する数を
守っていないか、だった。ここでは直した形を PoC の関数・定数・台帳の文で固定する(PoC を走らせる重い試験は
``tests/test_poc_scripts_run.py`` が別に持つ)。
"""
from __future__ import annotations

import ast
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "examples"
LEDGER = {e["id"]: e for e in json.loads(
    (ROOT / "docs/articles/exhibits/poc_captions.json").read_text(encoding="utf-8"))["exhibits"]}
V26 = json.loads((ROOT / "docs/view2026/exhibits.json").read_text(encoding="utf-8"))


def _load(name: str):
    """PoC を走らせずに読み込む(main は呼ばない)。"""
    sys.path.insert(0, str(ROOT))
    key = "codex1115_" + name
    if key in sys.modules:
        return sys.modules[key]
    spec = importlib.util.spec_from_file_location(key, EX / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[key] = mod                     # dataclass の注釈の解決に要る
    try:
        spec.loader.exec_module(mod)
    except BaseException:
        sys.modules.pop(key, None)
        raise
    return mod


def _source(name: str) -> str:
    return (EX / (name + ".py")).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- 指摘 9: 光弾性の恒真の assert
def test_photoelasticity_tautological_check_is_not_an_assert_gate():
    """低変調を |sinδ| < 0.05 で選んだ定義から必ず成り立つ dev_max の比較は、門(assert)にしない。"""
    tree = ast.parse(_source("poc_photoelasticity"))
    gated = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Assert)
             and any(isinstance(x, ast.Name) and x.id == "dev_max" for x in ast.walk(n.test))]
    assert not gated, gated


def test_photoelasticity_low_modulation_definition_bounds_the_fringe_offset():
    """門から外した主張そのもの(定義)はここで確かめる: |sinδ| < 0.05 なら N = δ/2π と 0.5 の倍数の差は asin(0.05)/2π 以内。"""
    delta = np.linspace(0.0, 6 * np.pi, 2_000_001)
    low = np.abs(np.sin(delta)) < 0.05
    n = delta[low] / (2 * np.pi)
    dev = np.abs(2 * n - np.round(2 * n)) / 2.0
    assert low.sum() > 1000
    assert dev.max() <= np.arcsin(0.05) / (2 * np.pi) + 1e-12


# --------------------------------------------------------------------------- 指摘 5: SAM の外挿
def test_sam_superiority_gate_compares_only_frequencies_inside_the_tested_sizes():
    sam = _load("poc_sam_hybrid_bonding_voids")
    src = _source("poc_sam_hybrid_bonding_voids")
    assert "どの周波数でも、位相を使う検出の a90/95" not in src
    assert "a90/95 が両方とも試した大きさの内側にある周波数" in src
    # 表は位相の列にも(外挿)を付ける
    assert "\"%.1f%s\" % (rp[\"a90_95\"], \"(外挿)\" if rp[\"a90_95_beyond_data\"] else \"\")" in src

    def result(phase, amplitude, phase_out=False, amplitude_out=False):
        return {"位相": ({"a90_95": phase, "a90_95_beyond_data": phase_out},),
                "振幅": ({"a90_95": amplitude, "a90_95_beyond_data": amplitude_out},)}

    freqs = (1, 2, 3)
    none_inside = {f: result(1, 2, True, True) for f in freqs}
    assert sam.pod_inside_frequencies(none_inside, freqs) == []
    assert not sam.pod_phase_is_superior(none_inside, freqs)
    one_inside = dict(none_inside)
    one_inside[1] = result(7.9, 10.0)
    assert not sam.pod_phase_is_superior(one_inside, freqs)
    two_inside = {1: result(7.9, 10.0), 2: result(15.9, 20.0),
                  3: result(999.0, 0.001, True, True)}
    assert sam.pod_phase_is_superior(two_inside, freqs)      # 外挿の値は優劣に入らない
    two_inside[2] = result(16.0, 20.0)
    assert not sam.pod_phase_is_superior(two_inside, freqs)  # 8 割以上が 1 件でもあれば落ちる
    ordered = {1: result(10.0, 20.0), 2: result(12.0, 20.0),
               3: result(999.0, 0.001, True, True)}
    assert sam.pod_a90_order(ordered, 34.0, freqs)           # 外挿値 999 自体は比較しない
    ordered[2] = result(9.0, 20.0)
    assert not sam.pod_a90_order(ordered, 34.0, freqs)


def test_sam_caption_says_300_mhz_is_not_compared():
    row = LEDGER["poc_sam_hybrid_bonding_voids"]
    assert "優劣を比べない" in row["caption_ja"] and "not compared" in row["caption_en"]
    assert "34 µm" in row["caption_ja"] and "34 um" in row["caption_en"]


# --------------------------------------------------------------------------- 指摘 3・4: 仮想 SEM
def test_sem_eta_gate_is_tighter_than_absolute_004_for_light_elements():
    sem = _load("poc_virtual_sem_kv_cd_bse")
    lo, hi, m = sem.eta_window(sem.ETA_MEASURED[("C", 5)], 5000)
    assert m < 0.025, m                                        # 直す前は ±0.04(0.042〜0.125 を通した)
    assert lo > 0.055 and hi < 0.11, (lo, hi)
    # 重元素は締めすぎない(門の歯は遮蔽ラザフォードが W・Au で外れること。そこは ±0.04 のまま)
    assert sem.eta_window(sem.ETA_MEASURED[("AU", 30)], 5000)[2] == pytest.approx(sem.ETA_MARGIN)
    # 相対の分は、収録値どうしの散らばりから数えた値(手で置いた数ではない)
    spreads = [(max(v) - min(v)) / (max(v) + min(v)) for v in sem.ETA_MEASURED.values() if len(v) > 1]
    assert sem.ETA_REL == pytest.approx(max(spreads))


def test_sem_texts_separate_scored_stages_from_model_only_stages():
    sem = _load("poc_virtual_sem_kv_cd_bse")
    model_only = [s for s, how in sem.STAGE_SCORING if "模型の中" in how or "実測ではない" in how]
    assert len(model_only) >= 4, sem.STAGE_SCORING
    row = LEDGER["poc_virtual_sem_kv_cd_bse"]
    assert "各段を外の実測値で採点した" not in row["caption_ja"]          # 取り下げた言い方(「」で引く改めた旨の注は可)
    assert "every stage is scored against outside" not in row["caption_en"]
    assert "(実測値で採点)" not in row["title_ja"] and "(Scored against Measured Data)" not in row["title_en"]
    assert "各段を**外の実測値**で" not in _source("poc_virtual_sem_kv_cd_bse")


# --------------------------------------------------------------------------- 指摘 6: 薄膜の記録値の再現
def test_thin_film_publishes_only_numbers_it_gates_for_reproduction():
    tf = _load("poc_thin_film_reflectometry")
    assert tf.PUBLISHED_REAL_TOL <= 0.05                       # 直す前は写真の膜厚を ±25 % で通していた
    assert tf.PUBLISHED_REAL["real_rgb_film"] == 87.4
    row = LEDGER["poc_thin_film_reflectometry"]
    assert len(tf.PUBLISHED_REAL) == 4, tf.PUBLISHED_REAL
    for key, value in tf.PUBLISHED_REAL.items():
        txt = "%.1f" % value
        assert txt in row["caption_ja"] and txt in row["caption_en"], key
    assert "87.4" in row["lead_ja"] and "87.4" in row["lead_en"]
    numbers = dict(tf.PUBLISHED_REAL)
    assert tf.published_real_mismatches(numbers) == []
    changed = dict(numbers)
    changed["real_fit0"] += 0.06
    assert tf.published_real_mismatches(changed) == ["real_fit0"]
    missing = dict(numbers)
    missing.pop("real_fit_na")
    assert tf.published_real_mismatches(missing) == ["real_fit_na"]


# --------------------------------------------------------------------------- 指摘 7: 白色化した整合フィルタ
def test_defect_floor_has_a_prewhitened_matched_filter_that_is_linear():
    df = _load("poc_real_defect_floor")
    rng = np.random.default_rng(0)
    train = rng.normal(size=(64, 64)).cumsum(axis=1)           # 色の付いた(低域の強い)地
    det = df.whitened_matched(train)
    a, b = rng.normal(size=(64, 64)), rng.normal(size=(64, 64))
    assert np.allclose(det(a + 2.0 * b), det(a) + 2.0 * det(b), atol=1e-9)
    # 線形の速い判定は、PoC の判定(floors)と同じ答えを返す
    g = rng.normal(size=(96, 96)) * 0.05 + 0.5
    pos = [(40, 40), (40, 56), (56, 40)]
    amps = np.round(np.geomspace(0.005, 3.0, 30), 5)
    assert np.array_equal(df.floors(g, df.matched, pos, amps), df.floors_linear(g, df.matched, pos, amps))
    whitened = {name: (2.0, 1.0) for name in df.GROUNDS}
    ratios = [2.0] * len(df.GROUNDS)
    assert df.whitened_claim_holds(whitened, ratios)
    for bad in (float("nan"), float("inf")):
        bad_ratios = list(ratios)
        bad_ratios[-1] = bad
        assert not df.whitened_claim_holds(whitened, bad_ratios)
        bad_floors = dict(whitened)
        bad_floors[df.GROUNDS[-1]] = (2.0, bad)
        assert not df.whitened_claim_holds(bad_floors, ratios)


def test_defect_floor_caption_reports_the_prewhitened_comparison():
    row = LEDGER["poc_real_defect_floor"]
    assert "白色化した整合フィルタ" in row["caption_ja"] and "prewhitened matched filter" in row["caption_en"]


# --------------------------------------------------------------------------- 指摘 8: AI の自明な基準線の選び方
def test_ai_trivial_statistic_is_reselected_on_development_images_only():
    ai = _load("poc_ai_built_inspection_scored")
    assert len(ai.TRIVIAL_SELECTION) == 2
    assert set(ai.TRIVIAL_SELECTION) == {"crack", "candle"}
    for task, sel in ai.TRIVIAL_SELECTION.items():
        d = sel["dprime_dev"]
        assert set(d) == set(ai.TRIVIAL_CANDIDATES), task
        pick = max(d, key=lambda k: abs(d[k]))
        assert pick == sel["pick"] and (d[pick] > 0) == (sel["sign"] > 0), task
    assert ai.TRIVIAL_SELECTION["crack"]["pick"] == "median_minus_p1" and ai.TRIVIAL_SELECTION["crack"]["sign"] > 0
    # 規則そのもの: 試験画像は引数に無い。開発用の 2 群の d' の絶対値で選ぶ
    sel = ai.select_trivial({"std": np.array([3.0, 3.1, 1.0, 1.1]), "median_minus_p1": np.array([1.0, 2.0, 1.5, 1.4]),
                             "min": np.array([0.0, 0.1, 0.05, 0.02]), "mean": np.array([5.0, 5.0, 5.1, 4.9])},
                            np.array([1, 1, 0, 0]))
    assert sel["pick"] == "std" and sel["sign"] > 0


def test_ai_caption_discloses_how_the_trivial_statistic_was_chosen():
    row = LEDGER["poc_ai_built_inspection_scored"]
    assert "試験 400 枚のラベルで" in row["caption_ja"] and "labels of the 400 test images" in row["caption_en"]
    assert "0.700" in row["caption_ja"] and "0.700" in row["caption_en"]


# --------------------------------------------------------------------------- 指摘 1: CT の見出し
def test_ct_title_is_limited_to_the_deficit_measure_and_the_grid():
    row = LEDGER["poc_ct_casting_sparse_views"]
    assert "欠損で測る" in row["title_ja"] and "32³" in row["title_ja"] and "逆" in row["title_ja"]
    assert "Deficit" in row["title_en"] and "32³" in row["title_en"]
    for coll in ("exhibits", "all"):
        card = next(e for e in V26[coll] if e["id"] == "poc_ct_casting_sparse_views")
        for lang in V26["langs"]:
            assert "32" in card["label"][lang], (coll, lang)
            assert "1 位とは限らない" not in card["label"][lang] and "Does Not Always" not in card["label"][lang]
    assert "26.7" in row["caption_ja"] and "26.7" in row["caption_en"]


def test_ct_gate_pins_the_reversal_under_the_binary_volume():
    src = _source("poc_ct_casting_sparse_views")
    assert "半値で 2 値化した体積では順位が逆" in src
    assert "few[\"tv\"][\"vol_err\"] < few[\"fdk\"][\"vol_err\"]" in src


# --------------------------------------------------------------------------- 指摘 2: デパレタイズの記録との差の門
def test_depalletizing_full_run_gates_the_difference_from_the_record():
    dep = _load("poc_mixed_case_depalletizing")
    assert dep.RECORD_TOL_RECALL <= 0.005 + 1e-6 and dep.RECORD_TOL_FALSE <= 0.05 + 1e-6
    rec = dep.recorded_fm()
    # 地図の比較は、記録そのものを渡せば差 0・升目の数は記録と同じ
    wr, wf, n = dep.record_map_differences(rec, rec)
    assert (wr, wf, n) == (0.0, 0.0, len(dep.RECORDED_FULL["map"]))
    assert dep.record_max_difference([]) == float("inf")
    assert dep.record_max_difference([(float("nan"), 0.0)]) == float("inf")
    assert dep.record_max_difference([(float("inf"), 0.0)]) == float("inf")
    missing = dict(rec)
    k = next(iter(missing))
    missing.pop(k)
    assert dep.record_map_differences(missing, rec)[:2] == (float("inf"), float("inf"))
    extra = dict(rec)
    extra[("余分",)] = (0.0, 0.0)
    assert dep.record_map_differences(extra, rec)[:2] == (float("inf"), float("inf"))
    assert dep.record_map_differences({}, rec)[:2] == (float("inf"), float("inf"))
    for bad in (float("nan"), float("inf")):
        invalid = dict(rec)
        invalid[k] = (bad, invalid[k][1])
        assert dep.record_map_differences(invalid, rec)[0] == float("inf")
