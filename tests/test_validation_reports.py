# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""外部の検証報告の台帳(``docs/validation_reports.json``)と昇格規則の門(2026-10-11)。

External validation-report registry and promotion rules.

Fullseye は個人開発で物理の計測装置を持たないので、CI は合成・閉形式の真値でしか
検証できない。実機・実データを持つ人の報告で段を上げる道を作ったが、その道が
**緩すぎても(1 件の自己申告で実機検証を名乗る)、狭すぎても(データを出せない人を
締め出す)いけない**。ここで確かめること:

1. 空の台帳では、能力ごとの段と事実が導入前と同じ(空の台帳が何かを主張しない)
2. 再現できる報告 1 件、または結果だけの独立報告 2 件以上で実機の段に上がる
3. 結果だけの報告 1 件・未受理・不確かさの外・同じ人の 2 件では上がらない
4. 台帳の形が崩れていたら表を作らない(fail-closed)。所属・勤務先の欄は拒む
5. issue form が、データ非公開の道・謝辞の任意性・所属を求めないことを守っている

★この試験ファイルには op の名前を書かない。``tools/gen_maturity.py`` は ``tests/``
に op 名が現れるかを数えるので、ここで名前を出すと成熟度台帳の事実が動く。
"""
from __future__ import annotations

import copy
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import gen_maturity as GM  # noqa: E402

FORM = os.path.join(ROOT, ".github", "ISSUE_TEMPLATE", "real_validation_report.yml")


@pytest.fixture(scope="module")
def baseline():
    """コミット済みの空台帳での生成結果(以後の比較の基準)。"""
    return GM.collect()


def _cap_ids():
    with open(os.path.join(ROOT, "docs", "maturity.json"), encoding="utf-8") as fh:
        return [r["id"] for r in json.load(fh)["capabilities"]]


def _report(rid, cap, **kw):
    r = {
        "id": rid, "capability": cap, "kind": "hardware", "review": "accepted",
        "source": "https://github.com/furuse-kazufumi/fullseye/issues/1",
        "reporter": "reporter-" + rid, "setup": "setup-" + rid,
        "ground_truth": "calibrated reference", "ground_truth_uncertainty": "0.01 mm (k=2)",
        "procedure": "documented commands", "fullseye_version": "0.5.0",
        "result": "max error 0.02 mm, n=30", "data_sharing": "results-only",
        "received_on": "2026-10-11", "traceable_reference": True,
        "within_stated_uncertainty": True,
    }
    r.update(kw)
    return r


def _write(tmp_path, reports):
    p = tmp_path / "validation_reports.json"
    p.write_text(json.dumps({"schema": 1, "reports": reports}), encoding="utf-8")
    return str(p)


def _row(data, cap):
    return next(r for r in data["capabilities"] if r["id"] == cap)


# --------------------------------------------------------------------------- 1
def test_the_committed_registry_is_well_formed_and_readable():
    reports = GM.load_registry(GM.REGISTRY, set(_cap_ids()))
    assert isinstance(reports, list)


def test_an_empty_registry_adds_nothing_to_the_ledger(baseline):
    """★空の台帳で能力の行が動いたら、台帳が黙って何かを主張している。"""
    if GM.load_registry(GM.REGISTRY):
        pytest.skip("the committed registry is not empty any more")
    assert "external_validation" not in baseline
    for r in baseline["capabilities"]:
        assert not set(r) & {"external_reports", "status_from_repository",
                             "external_rules_met"}, r["id"]
    md = GM.render(baseline)
    assert "0 件" in md and "No external report has been recorded yet." in md


# --------------------------------------------------------------------------- 2
def test_one_reproducible_hardware_report_promotes(tmp_path, baseline):
    cap = _cap_ids()[0]
    reg = _write(tmp_path, [_report("a", cap, data_sharing="synthetic-recreation",
                                    reproduced_by_maintainer=True)])
    d = GM.collect(reg)
    row = _row(d, cap)
    assert row["status"] == "validated-hardware"
    assert row["status_from_repository"] == _row(baseline, cap)["status"]
    assert row["external_rules_met"] == ["hardware-reproducible"]
    assert d["external_validation"]["accepted"] == 1
    # 他の能力は動かない
    for other in d["capabilities"]:
        if other["id"] != cap:
            assert other["status"] == _row(baseline, other["id"])["status"]
    assert "validated-hardware" in GM.render(d)


def test_two_independent_results_only_reports_promote(tmp_path):
    """データを出せない人の道: 結果だけでも、別の人・別の装置で 2 件合えば上がる。"""
    cap = _cap_ids()[1]
    reg = _write(tmp_path, [_report("a", cap), _report("b", cap)])
    row = _row(GM.collect(reg), cap)
    assert row["status"] == "validated-hardware"
    assert row["external_rules_met"] == ["hardware-independent-results"]
    assert all(x["data_sharing"] == "results-only" for x in row["external_reports"])


def test_a_reproduced_public_dataset_report_reaches_the_public_data_stage(tmp_path, baseline):
    cap = next(c for c in _cap_ids()
               if _row(baseline, c)["status"] in ("research-prototype", "verified-synthetic"))
    reg = _write(tmp_path, [_report("p", cap, kind="public-real-data", data_sharing="shared",
                                    data_url="https://example.org/dataset",
                                    data_licence="CC-BY-4.0",
                                    reproduced_by_maintainer=True)])
    assert _row(GM.collect(reg), cap)["status"] == "validated-public-real-data"


def test_external_reports_never_lower_a_stage(tmp_path, baseline):
    cap = next((c for c in _cap_ids()
                if _row(baseline, c)["status"] == "validated-public-real-data"), None)
    if cap is None:
        pytest.skip("no capability is at validated-public-real-data")
    reg = _write(tmp_path, [_report("x", cap, review="not-reproduced")])
    assert _row(GM.collect(reg), cap)["status"] == "validated-public-real-data"


# --------------------------------------------------------------------------- 3
@pytest.mark.parametrize("variant", [
    "single_results_only", "pending", "outside_uncertainty", "same_reporter",
    "same_setup", "untraceable", "not_reproduced_by_maintainer"])
def test_weak_evidence_does_not_promote(tmp_path, baseline, variant):
    cap = _cap_ids()[2]
    a, b = _report("a", cap), _report("b", cap)
    reports = {
        "single_results_only": [a],
        "pending": [a, dict(b, review="pending")],
        "outside_uncertainty": [a, dict(b, within_stated_uncertainty=False)],
        "same_reporter": [a, dict(b, reporter=a["reporter"].upper())],
        "same_setup": [a, dict(b, setup=a["setup"])],
        "untraceable": [a, dict(b, traceable_reference=False)],
        "not_reproduced_by_maintainer": [dict(a, data_sharing="shared")],
    }[variant]
    row = _row(GM.collect(_write(tmp_path, reports)), cap)
    assert row["status"] == _row(baseline, cap)["status"]
    assert not [x for x in row["external_rules_met"] if x.startswith("hardware-")]


def test_private_submission_is_a_valid_source(tmp_path):
    cap = _cap_ids()[0]
    reg = _write(tmp_path, [_report("a", cap, source=GM.PRIVATE_SOURCE, credit=None),
                            _report("b", cap, source=GM.PRIVATE_SOURCE)])
    d = GM.collect(reg)
    assert _row(d, cap)["status"] == "validated-hardware"
    assert GM.PRIVATE_SOURCE in GM.render(d)


# --------------------------------------------------------------------------- 4
@pytest.mark.parametrize("mutate, needle", [
    (lambda r: r.pop("ground_truth_uncertainty"), "必須キー"),
    (lambda r: r.__setitem__("employer", "x"), "未知のキー"),
    (lambda r: r.__setitem__("affiliation", "x"), "未知のキー"),
    (lambda r: r.__setitem__("kind", "vibes"), "kind"),
    (lambda r: r.__setitem__("review", "maybe"), "review"),
    (lambda r: r.__setitem__("data_sharing", "some"), "data_sharing"),
    (lambda r: r.__setitem__("traceable_reference", "yes"), "true/false"),
    (lambda r: r.__setitem__("source", "http://insecure"), "source"),
    (lambda r: r.__setitem__("capability", "no-such-capability"), "能力"),
    (lambda r: r.__setitem__("result", "   "), "空でない"),
])
def test_a_malformed_registry_stops_the_generator(tmp_path, mutate, needle):
    r = _report("a", _cap_ids()[0])
    mutate(r)
    with pytest.raises(GM.MaturityError, match=needle):
        GM.collect(_write(tmp_path, [r]))


def test_duplicate_ids_and_missing_file_are_refused(tmp_path):
    cap = _cap_ids()[0]
    with pytest.raises(GM.MaturityError, match="重複"):
        GM.collect(_write(tmp_path, [_report("a", cap), _report("a", cap)]))
    with pytest.raises(GM.MaturityError, match="無い"):
        GM.load_registry(str(tmp_path / "absent.json"))
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    with pytest.raises(GM.MaturityError, match="JSON"):
        GM.load_registry(str(bad))


def test_the_registry_has_no_field_for_employer_or_affiliation():
    keys = set(GM.REPORT_REQUIRED) | set(GM.REPORT_OPTIONAL)
    for banned in ("employer", "affiliation", "company", "organisation", "organization",
                   "product", "email"):
        assert banned not in keys
    assert "credit" not in GM.REPORT_REQUIRED, "謝辞は任意であること"


# --------------------------------------------------------------------------- 5
def _form():
    yaml = pytest.importorskip("yaml")
    with open(FORM, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def test_the_issue_form_parses_and_matches_the_generator_link():
    f = _form()
    assert f["name"] and f["description"] and isinstance(f["body"], list)
    assert os.path.basename(FORM) in GM.ISSUE_FORM_URL
    ids = [b.get("id") for b in f["body"] if b.get("type") != "markdown"]
    assert len(ids) == len(set(ids)), "issue form の id が重複"
    for b in f["body"]:
        assert b["type"] in ("markdown", "input", "textarea", "dropdown", "checkboxes")


def test_the_issue_form_offers_results_only_and_never_requires_identity():
    f = _form()
    fields = {b["id"]: b for b in f["body"] if b.get("id")}
    share = fields["data_sharing"]
    assert share["type"] == "dropdown" and share["validations"]["required"] is True
    opts = " ".join(share["attributes"]["options"])
    assert "結果のみ" in opts and "results only" in opts.lower()
    assert "合成" in opts and "共有可" in opts
    credit = fields["credit"]
    assert not credit.get("validations", {}).get("required", False), "謝辞は任意"
    text = json.dumps(f, ensure_ascii=False).lower()
    for banned_id in ("employer", "affiliation", "company"):
        assert banned_id not in fields
    assert "do not post confidential" in text and "社内データ" in text
    for required in ("capability", "setup", "ground_truth", "procedure", "results"):
        assert fields[required].get("validations", {}).get("required") is True, required


def test_the_issue_form_labels_are_bilingual():
    for b in _form()["body"]:
        if b["type"] == "markdown":
            continue
        label = b["attributes"]["label"]
        assert "/" in label and any(ord(c) > 0x3000 for c in label) \
            and any(c.isascii() and c.isalpha() for c in label), label


def test_the_reporting_routes_are_linked():
    cfg = os.path.join(ROOT, ".github", "ISSUE_TEMPLATE", "config.yml")
    yaml = pytest.importorskip("yaml")
    with open(cfg, encoding="utf-8") as fh:
        c = yaml.safe_load(fh)
    assert any("discussions" in x["url"] for x in c["contact_links"])
    with open(os.path.join(ROOT, "pyproject.toml"), encoding="utf-8") as fh:
        assert GM.ISSUE_FORM_URL in fh.read()
    for doc in ("CONTRIBUTING.md", "README.md", "docs/README.md", "docs/README.en.md",
                "docs/README.zh.md", "docs/README.tw.md", "docs/README.ko.md",
                "docs/README.de.md", "docs/VALIDATION_CONTRIBUTING.md",
                "docs/VALIDATION_CONTRIBUTING.en.md"):
        with open(os.path.join(ROOT, doc), encoding="utf-8") as fh:
            text = fh.read()
        assert "real_validation_report.yml" in text, doc
        assert "discussions" in text, doc


def test_deepcopy_guard_the_baseline_is_not_mutated(baseline):
    """collect() が呼ぶたびに新しい dict を返す(試験同士で汚染しない)。"""
    snap = copy.deepcopy(baseline)
    GM.collect()
    assert snap == baseline
