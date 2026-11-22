# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""CycloneDX SBOM を ``pyproject.toml`` の宣言だけから作る。

Enterprise users need a dependency inventory that is reproducible without an installed
environment or network access. Dependency versions in this SBOM are the ranges declared in
``pyproject.toml``, not resolved versions.

企業利用者が、導入済み環境やネットワークに依存せず再現できる依存関係一覧を必要とするための
生成器である。SBOM の依存版は解決済みの版ではなく、``pyproject.toml`` に宣言された範囲を表す。
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Repository root and default paths. / リポジトリの根と既定パス。
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_PATH = REPO_ROOT / "pyproject.toml"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "docs" / "sbom" / "fullseye.cdx.json"

# Fixed CycloneDX and project metadata. / 固定する CycloneDX・プロジェクトのメタデータ。
BOM_FORMAT = "CycloneDX"
SPEC_VERSION = "1.6"
BOM_DOCUMENT_VERSION = 1
ROOT_COMPONENT_TYPE = "library"
TOOL_COMPONENT_TYPE = "application"
GENERATOR_NAME = "tools/gen_sbom.py"
SPDX_LICENSE_ID = "Apache-2.0"
PYPI_PURL_PREFIX = "pkg:pypi/"
SCOPE_REQUIRED = "required"
SCOPE_OPTIONAL = "optional"
BOM_REF_PREFIX = "dependency:"
IDENTITY_SEPARATOR = "\0"

# Namespaced property names used for declared requirements. / 宣言依存に使う名前空間つき属性名。
PROPERTY_REQUIREMENT = "fullseye:requirement"
PROPERTY_SPECIFIER = "fullseye:specifier"
PROPERTY_MARKER = "fullseye:marker"
PROPERTY_EXTRA = "fullseye:extra"
PROPERTY_REQUESTED_EXTRA = "fullseye:requested-extra"
PROPERTY_VERSION_BASIS = "fullseye:dependency-version-basis"
VERSION_BASIS_NOTE = (
    "Dependency versions are declared requirement ranges from pyproject.toml, "
    "not resolved versions."
)

# Stable formatting and reference settings. / 安定した整形と参照名の設定。
JSON_INDENT = 2
BOM_REF_DIGEST_LENGTH = 16
EXIT_OK = 0
EXIT_DRIFT = 1
EXIT_INVALID = 2

# PEP 503 name normalisation and the supported PEP 508 subset. / PEP 503 名正規化と対応する PEP 508 部分集合。
NORMALISE_NAME_RE = re.compile(r"[-_.]+")
REQUIREMENT_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)"
    r"(?:\[(?P<extras>[A-Za-z0-9._-]+(?:\s*,\s*[A-Za-z0-9._-]+)*)\])?"
    r"(?P<specifier>.*)$"
)
SPECIFIER_RE = re.compile(r"^(?:===|~=|==|!=|<=|>=|<|>)\s*[^\s,;]+$")


class RequirementError(ValueError):
    """依存宣言を安全に解釈できない。 / A declared requirement cannot be parsed safely."""


@dataclass(frozen=True)
class ParsedRequirement:
    """依存宣言を構造化した値。 / A structured declared requirement."""

    raw: str
    name: str
    normalised_name: str
    requested_extras: tuple[str, ...]
    specifier: str
    marker: str


@dataclass
class RequirementRecord:
    """重複宣言をまとめた SBOM の1依存。 / One deduplicated SBOM dependency."""

    name: str
    specifier: str
    marker: str
    required: bool = False
    declarations: set[str] = field(default_factory=set)
    project_extras: set[str] = field(default_factory=set)
    requested_extras: set[str] = field(default_factory=set)


def normalise_name(name: str) -> str:
    """PEP 503 に従って配布名を正規化する。 / Normalise a distribution name per PEP 503."""
    return NORMALISE_NAME_RE.sub("-", name).lower()


def parse_requirement(requirement: str) -> ParsedRequirement:
    """小さな stdlib-only parser で依存宣言を読む。 / Parse a requirement with a small stdlib-only parser."""
    if not isinstance(requirement, str) or not requirement.strip():
        raise RequirementError("requirement must be a non-empty string")
    raw = requirement.strip()
    requirement_part, separator, marker_part = raw.partition(";")
    marker = marker_part.strip() if separator else ""
    if separator and not marker:
        raise RequirementError("requirement marker must not be empty: %r" % raw)
    match = REQUIREMENT_RE.fullmatch(requirement_part.strip())
    if match is None:
        raise RequirementError("unsupported requirement syntax: %r" % raw)
    name = match.group("name")
    extras_text = match.group("extras") or ""
    requested_extras = tuple(sorted({
        normalise_name(extra.strip()) for extra in extras_text.split(",") if extra.strip()
    }))
    specifier = match.group("specifier").strip()
    if specifier:
        parts = [part.strip() for part in specifier.split(",")]
        if not parts or any(not part or SPECIFIER_RE.fullmatch(part) is None for part in parts):
            raise RequirementError("unsupported version specifier in requirement: %r" % raw)
        specifier = ",".join(parts)
    return ParsedRequirement(
        raw=raw,
        name=name,
        normalised_name=normalise_name(name),
        requested_extras=requested_extras,
        specifier=specifier,
        marker=marker,
    )


def load_pyproject(path: Path) -> dict[str, Any]:
    """TOML を標準ライブラリだけで読む。 / Read TOML using only the standard library."""
    with path.open("rb") as handle:
        document = tomllib.load(handle)
    project = document.get("project")
    if not isinstance(project, dict):
        raise RequirementError("pyproject.toml must contain a [project] table")
    return project


def _string_list(value: Any, where: str) -> list[str]:
    """依存の配列を fail-closed で検査する。 / Validate a dependency list fail-closed."""
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise RequirementError("%s must be an array of requirement strings" % where)
    return value


def collect_requirements(project: dict[str, Any]) -> list[RequirementRecord]:
    """宣言を決定的に重複排除する。 / Deduplicate declarations deterministically."""
    records: dict[tuple[str, str, str], RequirementRecord] = {}

    def add(raw: str, *, required: bool, project_extra: str | None) -> None:
        parsed = parse_requirement(raw)
        key = (parsed.normalised_name, parsed.specifier, parsed.marker)
        record = records.setdefault(
            key,
            RequirementRecord(parsed.normalised_name, parsed.specifier, parsed.marker),
        )
        record.required = record.required or required
        record.declarations.add(parsed.raw)
        record.requested_extras.update(parsed.requested_extras)
        if project_extra is not None:
            record.project_extras.add(normalise_name(project_extra))

    for requirement in _string_list(project.get("dependencies", []), "project.dependencies"):
        add(requirement, required=True, project_extra=None)

    optional = project.get("optional-dependencies", {})
    if not isinstance(optional, dict):
        raise RequirementError("project.optional-dependencies must be a table")
    for extra, requirements in sorted(optional.items()):
        if not isinstance(extra, str) or not extra.strip():
            raise RequirementError("optional dependency group names must be non-empty strings")
        for requirement in _string_list(
            requirements, "project.optional-dependencies.%s" % extra
        ):
            add(requirement, required=False, project_extra=extra)
    return [records[key] for key in sorted(records)]


def _bom_ref(record: RequirementRecord) -> str:
    """依存の宣言から安定した一意参照を作る。 / Build a stable unique reference from a declaration."""
    identity = IDENTITY_SEPARATOR.join((record.name, record.specifier, record.marker))
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:BOM_REF_DIGEST_LENGTH]
    return "%s%s:%s" % (BOM_REF_PREFIX, record.name, digest)


def _properties(record: RequirementRecord) -> list[dict[str, str]]:
    """宣言範囲・marker・extra を属性にする。 / Render range, marker, and extras as properties."""
    values: list[tuple[str, str]] = []
    values.extend((PROPERTY_REQUIREMENT, value) for value in sorted(record.declarations))
    if record.specifier:
        values.append((PROPERTY_SPECIFIER, record.specifier))
    if record.marker:
        values.append((PROPERTY_MARKER, record.marker))
    values.extend((PROPERTY_EXTRA, value) for value in sorted(record.project_extras))
    values.extend(
        (PROPERTY_REQUESTED_EXTRA, value) for value in sorted(record.requested_extras)
    )
    return [{"name": name, "value": value} for name, value in sorted(values)]


def build_sbom(project_path: Path = DEFAULT_PROJECT_PATH) -> dict[str, Any]:
    """プロジェクト宣言から CycloneDX 文書を組む。 / Build a CycloneDX document from project declarations."""
    project = load_pyproject(project_path)
    name = project.get("name")
    version = project.get("version")
    if not isinstance(name, str) or not name.strip():
        raise RequirementError("project.name must be a non-empty string")
    if not isinstance(version, str) or not version.strip():
        raise RequirementError("project.version must be a non-empty string")
    normalised_project_name = normalise_name(name)
    root_ref = "%s%s@%s" % (PYPI_PURL_PREFIX, normalised_project_name, version)
    records = collect_requirements(project)
    components = []
    required_refs = []
    dependency_entries = []
    for record in records:
        bom_ref = _bom_ref(record)
        component = {
            "type": ROOT_COMPONENT_TYPE,
            "bom-ref": bom_ref,
            "name": record.name,
            "purl": PYPI_PURL_PREFIX + record.name,
            "scope": SCOPE_REQUIRED if record.required else SCOPE_OPTIONAL,
            "properties": _properties(record),
        }
        components.append(component)
        dependency_entries.append({"ref": bom_ref, "dependsOn": []})
        if record.required:
            required_refs.append(bom_ref)
    components.sort(key=lambda item: item["bom-ref"])
    dependency_entries.sort(key=lambda item: item["ref"])
    return {
        "bomFormat": BOM_FORMAT,
        "specVersion": SPEC_VERSION,
        "version": BOM_DOCUMENT_VERSION,
        "metadata": {
            "tools": {
                "components": [{"type": TOOL_COMPONENT_TYPE, "name": GENERATOR_NAME}],
            },
            "component": {
                "type": ROOT_COMPONENT_TYPE,
                "bom-ref": root_ref,
                "name": normalised_project_name,
                "version": version,
                "purl": root_ref,
                "licenses": [{"license": {"id": SPDX_LICENSE_ID}}],
            },
            "properties": [
                {"name": PROPERTY_VERSION_BASIS, "value": VERSION_BASIS_NOTE},
            ],
        },
        "components": components,
        "dependencies": [
            {"ref": root_ref, "dependsOn": sorted(required_refs)},
            *dependency_entries,
        ],
    }


def render_sbom(project_path: Path = DEFAULT_PROJECT_PATH) -> str:
    """固定した JSON 形式で描画する。 / Render with fixed JSON formatting."""
    return json.dumps(
        build_sbom(project_path),
        indent=JSON_INDENT,
        ensure_ascii=False,
        sort_keys=False,
    ) + "\n"


def check_or_write(project_path: Path, output_path: Path, *, check: bool) -> int:
    """生成物を照合または LF で書く。 / Check the artifact or write it with LF endings."""
    expected = render_sbom(project_path)
    if check:
        # A Windows checkout with core.autocrlf=true holds the file as CRLF; compare as LF.
        # / Windows の autocrlf=true の checkout では CRLF になるので、LF にそろえて比べる。
        current = (output_path.read_bytes().replace(b"\r\n", b"\n")
                   if output_path.is_file() else None)
        if current != expected.encode("utf-8"):
            print("drift: %s (run py -3.11 tools/gen_sbom.py)" % output_path.name)
            return EXIT_DRIFT
        print("SBOM is up to date")
        return EXIT_OK
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(os.fspath(output_path), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(expected)
    print("wrote %s" % output_path.name)
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    """CLI の入口。 / CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check for drift without writing")
    parser.add_argument("--pyproject", type=Path, default=DEFAULT_PROJECT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(argv)
    try:
        return check_or_write(args.pyproject, args.output, check=args.check)
    except (OSError, tomllib.TOMLDecodeError, RequirementError) as exc:
        print("SBOM generation failed: %s" % exc, file=sys.stderr)
        return EXIT_INVALID


if __name__ == "__main__":
    raise SystemExit(main())
