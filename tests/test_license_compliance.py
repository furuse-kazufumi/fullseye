# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ライセンス台帳の門。 / Licence-inventory gates."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "license_audit.py"


def _tool():
    """生成器を副作用なしで読む。 / Load the generator without invoking its CLI."""
    spec = importlib.util.spec_from_file_location("_license_audit", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _ledgers(module):
    """監査の3台帳を読む。 / Load the three audit ledgers."""
    return (module.load_json(module.POLICY), module.load_json(module.ASSETS),
            module.load_json(module.RESOLUTION))


def test_declared_dependencies_and_material_records_pass_the_audit():
    """既定・extra・同梱物を実台帳で検査する。 / Check declared dependencies and material records."""
    module = _tool()
    module.validate(*_ledgers(module))


def test_missing_direct_dependency_record_fails_closed():
    """新しい依存の台帳漏れを空で通さない。 / New dependencies need a reviewed record."""
    module = _tool()
    policy, assets, resolution = _ledgers(module)
    policy = copy.deepcopy(policy)
    policy["packages"].pop("numpy")
    with pytest.raises(module.AuditError, match="lack license records"):
        module.validate(policy, assets, resolution)


def test_noncommercial_direct_dependency_fails_closed():
    """非商用依存を既定・extra へ足れない。 / Refuse non-commercial runtime dependencies."""
    module = _tool()
    policy, assets, resolution = _ledgers(module)
    policy = copy.deepcopy(policy)
    policy["packages"]["numpy"]["class"] = "non-commercial"
    with pytest.raises(module.AuditError, match="not distributable"):
        module.validate(policy, assets, resolution)


def test_gpl_exception_is_limited_to_the_test_extra():
    """GPL を runtime へ広げない。 / Keep GPL out of runtime dependency groups."""
    module = _tool()
    policy, _, _ = _ledgers(module)
    record = policy["packages"]["plyfile"]
    assert record["class"] == "strong-copyleft"
    assert policy["strong_copyleft_exceptions"]["plyfile"]["only_extra"] == "export-verify"
    assert module.requirement_scopes()["plyfile"] == ("export-verify",)


def test_full_setup_exclusion_is_the_single_gpl_source_of_truth():
    """GPL extra の既定除外は一箇所の台帳で決める。 / Keep the GPL default exclusion in one ledger."""
    module = _tool()
    excluded = module.default_setup_exclusions()
    assert set(excluded) == {"export-verify"}
    record = excluded["export-verify"]
    assert record["dependency"] == "plyfile"
    assert record["license"] == "GPL-3.0-or-later"
    assert "verification" in record["reason"].lower()
    assert record["setup_include"] == "fullseye setup --include export-verify"


def test_public_figure_provenance_has_no_unexplained_omission():
    """公開図の出典欄を空の台帳で通さない。 / Reject unexplained public-figure provenance gaps."""
    module = _tool()
    _, assets, _ = _ledgers(module)
    records = module.figure_source_records()
    unrecorded = {"%s/%s" % (record["poc"], record["file"])
                  for record in records if record["unrecorded"]}
    assert unrecorded == set(assets["unresolved_public_figures"])
    assert not unrecorded
    synced = json.loads((ROOT / "docs" / "licenses" / "public_figure_provenance.json").read_text(encoding="utf-8"))
    figures = {figure for entry in synced["records"] for figure in entry["figures"]}
    assert len(figures) == 65
    assert all("Retrieved:" in record["source"] and "Licence:" in record["source"]
               for record in records if "%s/%s" % (record["poc"], record["file"]) in figures)


def test_fintraffic_and_osm_attribution_is_on_figures_pages_and_readme():
    """Fintraffic/OSM 帰属を図・展示ページ・README から落とさない。 / Keep Fintraffic/OSM credit published."""
    required = ("Fintraffic / Digitraffic weather-camera history", "© OpenStreetMap contributors", "ODbL 1.0")
    figures = (ROOT / "docs" / "articles" / "assets" / "poc" /
               "poc_public_camera_heading_real" / "figures.json").read_text(encoding="utf-8")
    pages = [
        ROOT / "docs" / "articles" / "exhibits" / "wingpoc.ja.md",
        ROOT / "docs" / "articles" / "exhibits" / "wingpoc.en.md",
        ROOT / "docs" / "articles" / "fullseye_poc_museum_how_qiita_ja.md",
        ROOT / "docs" / "articles" / "fullseye_poc_museum_how_qiita_en.md",
    ]
    assert all(token in figures for token in required)
    assert all(all(token in page.read_text(encoding="utf-8") for token in required) for page in pages)
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "© OpenStreetMap contributors" in readme and "ODbL 1.0" in readme
    assert "Source: Fintraffic / digitraffic.fi, license CC 4.0 BY" in readme


@pytest.mark.parametrize(
    ("metadata", "expected"),
    [
        ("GNU GENERAL PUBLIC LICENSE Version 3", "strong-copyleft"),
        ("GNU Lesser General Public License v3 or later", "weak-copyleft"),
        ("Affero General Public License", "strong-copyleft"),
    ],
)
def test_long_form_copyleft_metadata_is_not_misclassified(metadata, expected):
    """長い GPL 表記も許容型へ誤分類しない。 / Do not treat long GPL names as permissive."""
    assert _tool().license_class(metadata) == expected


def test_generated_notices_and_inventories_have_no_drift():
    """通知・棚卸し・wheel 用の写しを同じ生成元で照合する。 / Reject notice drift."""
    module = _tool()
    assert module.main(["--check"]) == 0


def test_wheel_notice_carries_bundled_material_and_bsd_text():
    """wheel 同梱物の出典と必要な BSD 全文を確認する。 / Check shipped material notices."""
    text = (ROOT / "fullseye" / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    assert "kenney-car-kit" in text and "hokusai-great-wave" in text
    assert "BSD 3-Clause License" in text and "scikit-image team" in text
    assert "Prepared 1.2.0" in text and "pybind11" in text and "pyside6-essentials" in text
    assert (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8") == text


def test_sbom_has_a_license_expression_for_every_component():
    """CycloneDX でライセンス列を空にしない。 / Require SBOM license expressions."""
    sbom = json.loads((ROOT / "docs" / "sbom" / "fullseye.cdx.json").read_text(encoding="utf-8"))
    assert len(sbom["components"]) >= 40
    assert all(component.get("licenses") for component in sbom["components"])
