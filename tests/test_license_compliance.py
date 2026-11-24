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
