# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""実験計画(doe.py、opsmultivar の plan / coding)の門 —— 真値は公表された表と閉形式。

* 直交表 L4・L8・L9・L12・L16・L27 は NIST Dataplot の ``L*.DAT``(tests/data/doe_published/、米国政府の
  著作物 = パブリックドメイン)と**行まで一致**、L18(2^1 3^7)は 1・2 列目を 6 水準にまとめると NIST の
  6^1 3^6 と一致。表は York 大学の公開表から写したもの(doe.OA_SOURCES)—— 2 つの独立な出典が一致する。
* 一部実施 2^(k−p): NIST e-Handbook Table 3.17 の生成子から作った計画の分解能・実験回数が表の値と一致。
* 回転可能 CCD の α = F^{1/4}(NIST Table 3.23)と、3 因子 CCC・Box-Behnken が NIST Table 3.24 の点と一致。
* 回転可能性の閉形式(Σx_i^4 = 3 Σx_i^2 x_j^2)、LHS の層(各因子の各層にちょうど 1 点)。
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import doe  # noqa: E402

DATA = ROOT / "tests" / "data" / "doe_published"


def _dat(name):
    lines = (DATA / name).read_text(encoding="ascii").splitlines()
    i = next(j for j, ln in enumerate(lines) if ln.startswith("---"))
    return np.array([[int(x) for x in ln.split()] for ln in lines[i + 1:] if ln.strip()])


def _nist():
    return json.loads((DATA / "nist_tables.json").read_text(encoding="utf-8"))


def _rows(a, nd=3):
    return sorted(tuple(np.round(r, nd) + 0.0) for r in np.asarray(a, float))


# --------------------------------------------------------------------------- #
# 1. 直交表 = 公表表                                                           #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", ["L4", "L8", "L9", "L12", "L16", "L27"])
def test_orthogonal_arrays_equal_the_nist_dataplot_files_row_for_row(name):
    assert np.array_equal(np.array(doe.OA_PUBLISHED[name]["rows"]), _dat(name + ".DAT"))


def test_l18_equals_nist_after_merging_columns_1_and_2():
    t = np.array(doe.OA_PUBLISHED["L18"]["rows"])
    merged = np.column_stack([3 * (t[:, 0] - 1) + t[:, 1], t[:, 2:]])
    assert np.array_equal(merged, _dat("L18.DAT"))
    assert doe.OA_PUBLISHED["L18"]["levels"] == [2] + [3] * 7


@pytest.mark.parametrize("name", list(doe.OA_PUBLISHED))
def test_every_published_array_is_strength_two(name):
    t = np.array(doe.OA_PUBLISHED[name]["rows"])
    assert doe._oa_strength2_ok(t)
    d = doe.doe_orthogonal_array(name)
    assert d["meta"]["strength2_ok"] and d["coded"].shape == t.shape
    # 公表の記号 1/2(/3)→ −1/+1(/−1,0,+1)、列は釣り合う
    for j in range(t.shape[1]):
        vals, cnt = np.unique(d["coded"][:, j], return_counts=True)
        assert len(set(cnt)) == 1 and vals[0] == -1.0 and vals[-1] == 1.0


def test_interaction_columns_match_the_known_structure():
    # L8: 1 x 2 は 3 列目に丸ごと(Taguchi の線点図の 1-2-3)
    sh = doe._oa_interaction_share(np.array(doe.OA_PUBLISHED["L8"]["rows"]), 0, 1)
    assert sh[2] == pytest.approx(1.0) and np.allclose(np.delete(sh, 2), 0.0, atol=1e-12)
    # L9: 1 x 2 は 3・4 列目に半分ずつ(3 水準の正則な表)
    sh = doe._oa_interaction_share(np.array(doe.OA_PUBLISHED["L9"]["rows"]), 0, 1)
    assert sh[2] == pytest.approx(0.5) and sh[3] == pytest.approx(0.5)
    # L12(Plackett-Burman 12): 交互作用は残り 9 列に 1/9 ずつ薄く広がる(非正則)
    sh = doe._oa_interaction_share(np.array(doe.OA_PUBLISHED["L12"]["rows"]), 0, 1)
    assert np.allclose(sh[2:], 1.0 / 9.0)
    # L18: 1 列目 x 2 列目の交互作用はどの列にも乗らない(他の列を犠牲にせず取れる、L18 の性質)
    sh = doe._oa_interaction_share(np.array(doe.OA_PUBLISHED["L18"]["rows"]), 0, 1)
    assert np.allclose(sh, 0.0, atol=1e-12)
    assert not doe.doe_orthogonal_array("L12", 3)["meta"]["regular"]
    assert doe.doe_orthogonal_array("L8", 3)["meta"]["regular"]


def test_orthogonal_array_names_confounding_of_assigned_columns():
    d = doe.doe_orthogonal_array("L8", ["A", "B", "C"], columns=[1, 2, 3])
    assert any(line.startswith("A x B falls on column 3 (C") for line in d["alias"])
    d = doe.doe_orthogonal_array("L8", ["A", "B", "C"], columns=[1, 2, 4])
    assert d["alias"] == []                                   # 3 列目(A x B)を空けた割り付け
    d = doe.doe_orthogonal_array("L9", [("light", 10, 30, "W"), ("exp", 1, 4, "ms"), ("gain", 0, 12, "dB")])
    assert sorted(set(d["natural"][:, 0])) == [10.0, 20.0, 30.0]


# --------------------------------------------------------------------------- #
# 2. 一部実施 = NIST Table 3.17                                                 #
# --------------------------------------------------------------------------- #
def test_fractional_factorials_reproduce_nist_table_3_17():
    rows = _nist()["fractional_factorial"]
    assert len(rows) >= 27
    for e in rows:
        d = doe.doe_fractional_factorial(e["k"], e["p"])
        assert d["meta"]["generators"] == e["generators"]
        assert d["coded"].shape == (e["runs"], e["k"]), e
        assert d["resolution"] == e["resolution"], e
        c = d["coded"]
        assert np.allclose(c.T @ c, e["runs"] * np.eye(e["k"]))     # 主効果は直交
        for g in e["generators"]:                                    # 列 = 生成子の積
            new, word = g.split("=")
            prod = np.prod([c[:, doe.LETTERS.index(ch)] for ch in word], axis=0)
            assert np.array_equal(c[:, doe.LETTERS.index(new)], prod)


def test_fraction_alias_table_and_refusals():
    d = doe.doe_fractional_factorial(["gain", "light", "exp", "angle", "filter"], 2)
    assert d["meta"]["defining_relation"] == ["I", "ABD", "ACE", "BCDE"]
    assert "gain = light*angle = exp*filter" in d["alias"]
    full = doe.doe_fractional_factorial(3, 0)
    assert full["coded"].shape == (8, 3) and full["resolution"] is None
    with pytest.raises(ValueError):
        doe.doe_fractional_factorial(5, 2, generators=["D=AB", "E=AB"])     # 同じ語 → 2 因子が交絡
    with pytest.raises(ValueError):
        doe.doe_fractional_factorial(5, 2, generators=["D=AB", "D=AC"])
    with pytest.raises(ValueError):
        doe.doe_fractional_factorial(5, 2, generators=["D=AZ", "E=AC"])
    with pytest.raises(ValueError):
        doe.doe_fractional_factorial(12, 1)                                 # 表に無い (k, p)


# --------------------------------------------------------------------------- #
# 3. 応答曲面の計画 = NIST Table 3.23 / 3.24 と閉形式                            #
# --------------------------------------------------------------------------- #
def test_rotatable_alpha_matches_nist_table_3_23():
    for e in _nist()["ccd_alpha"]:
        k, F = e["k"], e["factorial_runs"]
        p = int(round(k - math.log2(F)))
        gens = list(doe.FF_NIST[(k, p)][1]) if p else None
        d = doe.doe_central_composite(k, generators=gens)
        assert d["meta"]["n_factorial"] == F
        assert round(d["meta"]["alpha"], 3) == pytest.approx(e["alpha"], abs=5e-4), e


def test_three_factor_ccc_and_box_behnken_equal_nist_table_3_24():
    n = _nist()
    assert _rows(doe.doe_central_composite(3, center=6)["coded"]) == _rows(n["ccc_3"])
    assert _rows(doe.doe_box_behnken(3, center=3)["coded"]) == _rows(n["box_behnken_3"])


@pytest.mark.parametrize("k", [2, 3, 4, 5])
def test_rotatable_ccd_satisfies_the_moment_condition(k):
    c = doe.doe_central_composite(k)["coded"]
    assert (c[:, 0] ** 4).sum() == pytest.approx(3 * (c[:, 0] ** 2 * c[:, 1] ** 2).sum())


def test_box_behnken_four_factors_is_rotatable_three_is_not():
    c4 = doe.doe_box_behnken(4)["coded"]
    assert c4.shape == (27, 4)
    assert (c4[:, 0] ** 4).sum() == pytest.approx(3 * (c4[:, 0] ** 2 * c4[:, 1] ** 2).sum())
    c3 = doe.doe_box_behnken(3)["coded"]
    assert (c3[:, 0] ** 4).sum() != pytest.approx(3 * (c3[:, 0] ** 2 * c3[:, 1] ** 2).sum())
    assert not np.any(np.all(np.abs(c3) == 1, axis=1))                    # 角は 1 点も無い
    with pytest.raises(ValueError):
        doe.doe_box_behnken(6)


def test_ccd_reports_axial_points_outside_the_range_and_inscribed_keeps_them_in():
    d = doe.doe_central_composite([("T", 150, 200, "C"), ("t", 10, 30, "s")])
    assert d["meta"]["outside_range"] == ["T", "t"]
    assert d["natural"][:, 0].min() < 150 and d["natural"][:, 0].max() > 200
    di = doe.doe_central_composite([("T", 150, 200, "C"), ("t", 10, 30, "s")], inscribed=True)
    assert di["meta"]["outside_range"] == []
    assert di["natural"][:, 0].min() == pytest.approx(150) and di["natural"][:, 0].max() == pytest.approx(200)
    with pytest.raises(ValueError):                                       # 分解能 III の要因部では二次が立たない
        doe.doe_central_composite(5, generators=["D=AB", "E=AC"])


# --------------------------------------------------------------------------- #
# 4. LHS と符号化                                                               #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("n,k,m", [(5, 2, 0), (37, 6, 0), (20, 3, 30), (8, 1, 0)])
def test_latin_hypercube_has_one_point_per_stratum(n, k, m):
    d = doe.doe_lhs(n, k, seed=3, maximin=m)
    u = (d["coded"] + 1) / 2
    for j in range(k):
        assert np.array_equal(np.sort(np.floor(u[:, j] * n).astype(int)), np.arange(n))
    assert d["meta"]["strata_ok"]


def test_maximin_spreads_the_points_and_is_reproducible():
    plain = [doe.doe_lhs(20, 3, seed=s)["meta"]["min_distance"] for s in range(10)]
    best = doe.doe_lhs(20, 3, seed=0, maximin=50)["meta"]["min_distance"]
    assert best > np.median(plain)
    assert np.array_equal(doe.doe_lhs(20, 3, seed=5)["coded"], doe.doe_lhs(20, 3, seed=5)["coded"])


def test_encode_decode_round_trip_linear_and_log():
    f = [("temp", 150.0, 200.0, "C"), ("time", 1.0, 100.0, "s", "log")]
    nat = np.array([[150.0, 1.0], [175.0, 10.0], [200.0, 100.0], [210.0, 1000.0]])
    d = doe.doe_encode(nat, f)
    assert np.allclose(d["coded"], [[-1, -1], [0, 0], [1, 1], [1.4, 2.0]])
    assert d["meta"]["outside_range"] == ["temp", "time"]
    assert np.allclose(doe.doe_decode(d), nat)
    assert np.allclose(doe.doe_decode(d, [0.0, 0.0]), [[175.0, 10.0]])
    bb = doe.doe_box_behnken([("a", 0, 10), ("b", 1, 1000, "", "log"), ("c", -1, 1)])
    assert sorted(set(np.round(bb["natural"][:, 1], 9))) == [1.0, 31.622776602, 1000.0]


@pytest.mark.parametrize("bad", [
    lambda: doe.doe_encode([[1.0, 2.0]], None),                       # 範囲は推測しない
    lambda: doe.doe_encode([[1.0, np.nan]], 2),
    lambda: doe.doe_encode([[1.0, 2.0]], 3),                          # 列数の不一致
    lambda: doe.doe_lhs(1, 2),
    lambda: doe.doe_lhs(10, [("a", 1.0, 1.0)]),                       # lo == hi
    lambda: doe.doe_lhs(10, [("a", 0.0, 1.0, "", "log")]),            # 対数で lo <= 0
    lambda: doe.doe_lhs(10, ["a", "a"]),
    lambda: doe.doe_orthogonal_array("L7"),
    lambda: doe.doe_orthogonal_array("L4", 4),                        # 列が足りない
    lambda: doe.doe_orthogonal_array("L8", 2, columns=[1, 1]),
    lambda: doe.doe_decode({"sort": "matrix"}),
    lambda: doe.doe_decode(doe.doe_box_behnken(3), [0.0, 0.0]),
    lambda: doe.doe_central_composite(3, alpha=-1.0),
])
def test_fail_closed(bad):
    with pytest.raises(ValueError):
        bad()


# --------------------------------------------------------------------------- #
# 5. 台帳と公開経路(登録面を 1 つ落とすと静かに消える)                          #
# --------------------------------------------------------------------------- #
def test_ledger_lists_every_doe_op_and_nothing_is_missing():
    import opsmultivar as om
    assert set(om.list_ops("plan")) | set(om.list_ops("coding")) == set(doe.__all__)
    assert om.missing() == []


def test_doe_ops_are_reachable_from_the_public_tier():
    import fullseye as fs
    for name in doe.__all__:
        assert hasattr(fs.ledger, name), name
    assert fs.ledger.doe_orthogonal_array("L9", 4)["coded"].shape == (9, 4)
    assert fs.doe.doe_box_behnken(3)["kind"] == "box_behnken"


def test_typed_catalog_and_fuzzer_know_the_design_sort():
    import typed_catalog as tc
    sys.path.insert(0, str(ROOT / "tools"))
    import chain_fuzz as cf
    rows = {r[0]: r for r in tc.catalog() if r[0] in doe.__all__}
    assert set(rows) == set(doe.__all__)
    assert tuple(rows["doe_lhs"][1:4]) == ("multivar", [], "design")
    assert tuple(rows["doe_decode"][2:4]) == (["design"], "matrix")
    seed = cf.make_generators()["design"]
    rng = np.random.default_rng(0)
    before = rng.bit_generator.state
    assert cf.TYPE_CHECKS["design"](seed(rng))
    assert rng.bit_generator.state == before          # 種は乱数を引かない(他の型の種をずらさない)
    assert not cf.TYPE_CHECKS["design"](np.zeros((3, 2)))
    for name in ("doe_encode", "doe_decode"):
        args, kw = cf.OP_ARG_BUILDERS[name](None, np.random.default_rng(0))
        out = getattr(doe, name)(*args, **kw)
        assert cf.TYPE_CHECKS[rows[name][3]](out)


def test_op_summaries_have_matching_fingerprints():
    sys.path.insert(0, str(ROOT / "tools"))
    import opdocs
    d = json.loads((ROOT / "docs" / "i18n" / "op_summary.json").read_text(encoding="utf-8"))
    for name in doe.__all__:
        line = getattr(doe, name).__doc__.strip().splitlines()[0]
        e = d["summaries"]["multivar/" + name]
        assert e["fp"] == opdocs.fingerprint(line), name
        for lang in ("ja", "zh", "tw", "ko", "de", "hi"):
            assert e[lang].strip(), (name, lang)
