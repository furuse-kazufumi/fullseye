# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""CycloneDX SBOM の宣言一致と drift 門。 / Declaration and drift gates for the CycloneDX SBOM."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

# Repository paths and expected format constants. / リポジトリのパスと期待する形式の定数。
ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
PYPROJECT = ROOT / "pyproject.toml"
SBOM = ROOT / "docs" / "sbom" / "fullseye.cdx.json"
EXPECTED_BOM_FORMAT = "CycloneDX"
EXPECTED_SPEC_VERSION = "1.6"
EXPECTED_MUTATED_SPECIFIER = ">=9.9"
# Small fixtures for the mutation probe. / mutation 探針に使う小さな fixture。
SMALL_PROJECT = """[project]
name = "fixture"
version = "1.0"
dependencies = ["demo>=1"]
"""
SMALL_PROJECT_MUTATED = SMALL_PROJECT.replace("demo>=1", "demo" + EXPECTED_MUTATED_SPECIFIER)

sys.path.insert(0, os.fspath(TOOLS))
import gen_sbom as SB  # noqa: E402


def _load_generated() -> dict:
    """追跡する SBOM を読む。 / Load the tracked SBOM."""
    return json.loads(SBOM.read_text(encoding="utf-8"))


def _property_values(component: dict, name: str) -> tuple[str, ...]:
    """同名属性を決定順で取り出す。 / Return same-name properties in deterministic order."""
    return tuple(prop["value"] for prop in component["properties"] if prop["name"] == name)


def _component_signature(component: dict) -> tuple:
    """宣言との双方向照合に使う署名。 / Signature used for bidirectional declaration matching."""
    specifiers = _property_values(component, SB.PROPERTY_SPECIFIER)
    markers = _property_values(component, SB.PROPERTY_MARKER)
    return (
        component["name"],
        specifiers[0] if specifiers else "",
        markers[0] if markers else "",
        component["scope"],
        _property_values(component, SB.PROPERTY_EXTRA),
    )


def test_generated_file_matches_the_generator_now():
    """生成物の drift を拒む。 / Reject generated-file drift."""
    current = SBOM.read_bytes().replace(b"\r\n", b"\n")  # autocrlf=true checkouts hold CRLF
    assert current, "SBOM is empty"
    assert current == SB.render_sbom(PYPROJECT).encode("utf-8")


def test_raw_requirement_strings_match_without_the_generator_parser():
    """生成器の parser を通さず、pyproject の生の文字列で両方向に照合する。
    / Match raw pyproject strings in both directions without the generator's parser."""
    import tomllib

    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]
    declared = {raw.strip() for raw in project["dependencies"]}
    for requirements in project["optional-dependencies"].values():
        declared.update(raw.strip() for raw in requirements)
    assert len(declared) > len(project["dependencies"]), "no optional requirement was read"
    listed = set()
    for component in _load_generated()["components"]:
        listed.update(_property_values(component, SB.PROPERTY_REQUIREMENT))
    assert listed == declared


def test_every_declared_requirement_appears_and_no_other_component_exists():
    """依存宣言を両方向で照合する。 / Match dependency declarations in both directions."""
    project = SB.load_pyproject(PYPROJECT)
    records = SB.collect_requirements(project)
    assert records, "pyproject declares no requirements"
    expected = {
        (
            record.name,
            record.specifier,
            record.marker,
            SB.SCOPE_REQUIRED if record.required else SB.SCOPE_OPTIONAL,
            tuple(sorted(record.project_extras)),
        )
        for record in records
    }
    components = _load_generated()["components"]
    assert components, "SBOM has no dependency components"
    actual = {_component_signature(component) for component in components}
    assert len(actual) == len(components), "two components have the same declaration signature"
    assert actual == expected


def test_root_version_matches_pyproject():
    """根 component の版を照合する。 / Match the root component version."""
    project = SB.load_pyproject(PYPROJECT)
    assert project["version"], "project.version is empty"
    assert _load_generated()["metadata"]["component"]["version"] == project["version"]


def test_changed_specifier_makes_check_report_drift(tmp_path):
    """門を壊し、specifier drift を捕らえる。 / Mutate a specifier and prove the gate catches drift."""
    source_project = tmp_path / "source.toml"
    source_project.write_text(SMALL_PROJECT, encoding="utf-8", newline="\n")
    baseline = tmp_path / "baseline.json"
    baseline.write_text(SB.render_sbom(source_project), encoding="utf-8", newline="\n")
    assert SMALL_PROJECT_MUTATED != SMALL_PROJECT, "mutation probe did not change pyproject.toml"
    mutated = tmp_path / "pyproject.toml"
    mutated.write_text(SMALL_PROJECT_MUTATED, encoding="utf-8", newline="\n")
    assert SB.main([
        "--check", "--pyproject", os.fspath(mutated), "--output", os.fspath(baseline)
    ]) == SB.EXIT_DRIFT


@pytest.mark.parametrize(
    ("raw", "name", "extras", "specifier", "marker"),
    [
        ("Demo_Pkg>=1; platform_system != 'Darwin'", "demo-pkg", (), ">=1", "platform_system != 'Darwin'"),
        ("Demo.Pkg[PDF,tests]~=2.4", "demo-pkg", ("pdf", "tests"), "~=2.4", ""),
        ("Demo_Pkg==1.2", "demo-pkg", (), "==1.2", ""),
        ("Demo_Pkg>=1,<2", "demo-pkg", (), ">=1,<2", ""),
    ],
)
def test_requirement_parser(raw, name, extras, specifier, marker):
    """marker・extra・正規化・演算子を読む。 / Parse markers, extras, normalisation, and operators."""
    parsed = SB.parse_requirement(raw)
    assert parsed.normalised_name == name
    assert parsed.requested_extras == extras
    assert parsed.specifier == specifier
    assert parsed.marker == marker


def test_basic_cyclonedx_shape_and_unique_references():
    """CycloneDX の基本形と参照の一意性。 / Check basic CycloneDX shape and unique references."""
    document = _load_generated()
    assert document["bomFormat"] == EXPECTED_BOM_FORMAT
    assert document["specVersion"] == EXPECTED_SPEC_VERSION
    components = document["components"]
    assert components, "SBOM has no dependency components"
    references = [component["bom-ref"] for component in components]
    assert len(references) == len(set(references)), "component bom-refs are not unique"
    for component in components:
        missing = {"type", "name", "bom-ref", "purl"} - set(component)
        assert not missing, "component is missing required keys: %s" % sorted(missing)
        assert "version" not in component, "declared ranges must not be exact component versions"
        assert "@" not in component["purl"], "dependency purl must not claim an exact version"
