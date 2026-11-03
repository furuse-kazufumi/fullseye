"""中身の薄い HALCON 対応は「対応済み」に数えず「部分対応」として見せる(2026-11-03、ユーザー決定)。

完成度監査 B(``C:/dev/docs/completeness_audit_2026_11_03/B_functional_gaps_vs_oss.md``)が、名前は HALCON の
operator に対応しているが中身が一部だけの関数を挙げた(例: ``find_deformable_surface_model`` は剛体の PPF 照合を
呼ぶだけ)。表は ``halcon_coverage.PARTIAL``。ここで守ること:

1. 数え方: ``halcon_coverage.analyze`` が PARTIAL を ``covered`` から外し ``partial`` に出す。表が古くなれば止まる。
2. 同梱の ``fullseye/data/halcon_stubs.json``: 9 名とも ``covered: false`` + ``partial``、``n_covered`` が中身と一致。
3. 関数の docstring が「何をして何をしないか」を書いている(先頭行に ``[部分対応]``、英語の 1 行も)。
4. 生成物の見出し(HALCON_COVERAGE.md / HALCON_PARITY.md / docs/README*.md)が同じ数を言う。
"""
import importlib
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _hc():
    import halcon_coverage as HC
    return HC


def test_partial_table_is_the_audited_seven_families():
    HC = _hc()
    assert set(HC.PARTIAL) == {
        "find_deformable_surface_model", "find_planar_uncalib_deformable_model",
        "measure_profile_sheet_of_light", "calibrate_sheet_of_light", "create_ocv_proj",
        "create_bead_inspection_model", "apply_bead_inspection_model", "find_box_3d", "binocular_calibration"}
    for name, (ref, does, does_not) in HC.PARTIAL.items():
        assert ref.endswith("." + name) and does.strip() and does_not.strip(), name


def test_analyze_moves_partial_out_of_covered():
    HC = _hc()
    import halcon_names_data as HN
    import ops as R
    data = {"operators": [{"name": n, "chapters": []} for n in HN.HALCON_NAMES], "version": HN.HALCON_VERSION}
    a = HC.analyze(data, R.REGISTRY, None)
    assert a["partial"] == sorted(HC.PARTIAL)
    assert not set(a["partial"]) & set(a["covered"])
    assert len(a["covered"]) >= 900


def test_analyze_refuses_a_stale_partial_name(monkeypatch):
    HC = _hc()
    import halcon_names_data as HN
    import ops as R
    monkeypatch.setitem(HC.PARTIAL, "no_such_halcon_operator_xyz", ("x.no_such_halcon_operator_xyz", "a", "b"))
    data = {"operators": [{"name": n, "chapters": []} for n in HN.HALCON_NAMES], "version": HN.HALCON_VERSION}
    with pytest.raises(SystemExit, match="no_such_halcon_operator_xyz"):
        HC.analyze(data, R.REGISTRY, None)


def test_shipped_stubs_mark_partial_and_count_honestly():
    HC = _hc()
    stubs = json.loads((ROOT / "fullseye" / "data" / "halcon_stubs.json").read_text(encoding="utf-8"))
    facade = json.loads((ROOT / "fullseye" / "data" / "halcon_facade_map.json").read_text(encoding="utf-8"))
    ops = stubs["operators"]
    for name, (ref, does, does_not) in HC.PARTIAL.items():
        assert ops[name]["covered"] is False, name
        assert ops[name]["partial"] == {"does": does, "does_not": does_not}, name
        assert facade[name] == ref, (name, facade.get(name), ref)
    assert sum(1 for v in ops.values() if v.get("partial")) == len(HC.PARTIAL)
    assert stubs["n_covered"] == sum(1 for v in ops.values() if v.get("covered"))


@pytest.mark.parametrize("name", sorted(__import__("halcon_coverage").PARTIAL))
def test_docstring_says_what_it_does_and_does_not(name):
    HC = _hc()
    mod, _, fn = HC.PARTIAL[name][0].rpartition(".")
    doc = getattr(importlib.import_module(mod), fn).__doc__ or ""
    first = doc.strip().splitlines()[0]
    assert first.startswith("[部分対応]") and ("(%s)" % name) in first, first     # unified.py が先頭行を出す
    assert "しない" in doc and "部分対応" in doc and "halcon_coverage.PARTIAL" in doc
    assert "[Partial HALCON analogue]" in doc


def test_generated_headlines_agree():
    stubs = json.loads((ROOT / "fullseye" / "data" / "halcon_stubs.json").read_text(encoding="utf-8"))
    cov = (ROOT / "docs" / "HALCON_COVERAGE.md").read_text(encoding="utf-8")
    m = re.search(r"maps to (\d+) / (\d+) HALCON operators", cov)
    assert m and int(m.group(1)) == stubs["n_covered"], (m and m.group(0), stubs["n_covered"])
    assert "## Partial analogues" in cov
    for name in _hc().PARTIAL:
        assert "| %s |" % name in cov, name
    parity = (ROOT / "docs" / "HALCON_PARITY.md").read_text(encoding="utf-8")
    head = int(re.search(r"\*\*(\d+) / 2313 distinct real HALCON operators", parity).group(1))
    assert "partial analogues" in parity
    readmes = sorted((ROOT / "docs").glob("README*.md"))
    assert len(readmes) == 6
    for p in readmes:
        nums = re.findall(r"(\d+)/2313", p.read_text(encoding="utf-8"))
        assert nums and set(nums) == {str(head)}, (p.name, nums, head)
