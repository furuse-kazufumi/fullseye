# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ライセンス棚卸し・通知を決定的に生成する。

Render the dependency, transitive-resolution and third-party-material license
inventory from reviewable source records.  The resolver snapshot is captured
explicitly from ``pip --report`` so normal CI stays offline and deterministic.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
import tomllib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
LICENSE_DIR = ROOT / "docs" / "licenses"
POLICY = LICENSE_DIR / "dependency_licenses.json"
ASSETS = LICENSE_DIR / "third_party_assets.json"
SETUP_EXCLUSIONS = LICENSE_DIR / "setup_default_excluded_extras.json"
RESOLUTION = LICENSE_DIR / "resolved_win_py311.json"
DEPENDENCY_INVENTORY = LICENSE_DIR / "DEPENDENCY_INVENTORY.md"
ASSET_INVENTORY = LICENSE_DIR / "THIRD_PARTY_INVENTORY.md"
NOTICES = ROOT / "THIRD_PARTY_NOTICES.md"
WHEEL_NOTICES = ROOT / "fullseye" / "THIRD_PARTY_NOTICES.md"
OUTPUTS = (DEPENDENCY_INVENTORY, ASSET_INVENTORY, NOTICES, WHEEL_NOTICES)

_NORMALISE = re.compile(r"[-_.]+")
_REQ_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
_EXTERNAL_MARKER = re.compile(
    r"CC[ -]?(?:BY|BY-SA|BY-NC|0)|ODbL|OpenStreetMap|Fintraffic|Digitraffic|public domain|LASIESTA|skimage\.data",
    re.IGNORECASE,
)
_BSD3_SCITKIT = """BSD 3-Clause License

Copyright (c) 2009-2022 the scikit-image team
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of the copyright holder nor the names of its contributors
   may be used to endorse or promote products derived from this software without
   specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES.
"""


class AuditError(ValueError):
    """台帳または入力の不整合。 / An audit ledger or input is inconsistent."""


def _shipped_data_files() -> list[str]:
    """data/ の下で git が追跡しているファイルだけを返す(.gitignore の局所生成物を数えない)。

    Return only git-tracked files under data/. Local artefacts that .gitignore
    excludes (for example data/auto_functional_gate.json written by verify_auto.py)
    are never distributed, so they need no provenance record. Outside a git
    checkout (an unpacked sdist) every file on disk is counted, as before.
    """
    import subprocess
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "--", "data"],
                             capture_output=True, check=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return [path.relative_to(ROOT).as_posix() for path in (ROOT / "data").glob("**/*") if path.is_file()]
    return sorted(name for name in out.decode("utf-8").split("\0") if name and (ROOT / name).is_file())


def normalise(name: str) -> str:
    """PEP 503 の名前にそろえる。 / Normalise a distribution name per PEP 503."""
    return _NORMALISE.sub("-", name).lower()


def load_json(path: Path) -> dict[str, Any]:
    """JSON 台帳を fail-closed で読む。 / Read a JSON ledger fail-closed."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError("cannot read %s: %s" % (path, exc)) from exc
    if not isinstance(value, dict):
        raise AuditError("%s must be a JSON object" % path)
    return value


def default_setup_exclusions() -> dict[str, dict[str, Any]]:
    """全部入り既定から外す extra を厳密に読む。 / Read full-setup exclusions fail-closed."""
    payload = load_json(SETUP_EXCLUSIONS)
    entries = payload.get("default_setup_excluded_extras")
    if payload.get("schema") != 1 or not isinstance(entries, list) or not entries:
        raise AuditError("default setup exclusion ledger is invalid")
    result: dict[str, dict[str, Any]] = {}
    required = ("extra", "dependency", "license", "reason", "pip_install", "setup_include")
    for entry in entries:
        if not isinstance(entry, dict) or any(not str(entry.get(key, "")).strip() for key in required):
            raise AuditError("default setup exclusion record is incomplete")
        extra = str(entry["extra"])
        if extra in result:
            raise AuditError("default setup exclusion has a duplicate extra: %s" % extra)
        result[extra] = entry
    return result


def requirement_scopes() -> dict[str, tuple[str, ...]]:
    """pyproject の既定・extra の所属を読む。 / Read core and extra memberships."""
    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]
    found: dict[str, set[str]] = defaultdict(set)
    for requirement in project.get("dependencies", []):
        match = _REQ_NAME.match(requirement)
        if match is None:
            raise AuditError("cannot parse dependency: %r" % requirement)
        found[normalise(match.group(1))].add("default")
    for extra, requirements in project.get("optional-dependencies", {}).items():
        for requirement in requirements:
            match = _REQ_NAME.match(requirement)
            if match is None:
                raise AuditError("cannot parse optional dependency: %r" % requirement)
            found[normalise(match.group(1))].add(str(extra))
    return {name: tuple(sorted(scopes)) for name, scopes in sorted(found.items())}


def _metadata_license(metadata: dict[str, Any]) -> str:
    """PyPI core metadata のライセンス根拠を短く残す。 / Condense PyPI metadata evidence."""
    def compact(value: str) -> str:
        value = " ".join(value.split())
        return value if len(value) <= 240 else value[:237] + "..."

    for key in ("license_expression", "license"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return compact(value)
    classifiers = metadata.get("classifier", [])
    if isinstance(classifiers, list):
        values = [str(value) for value in classifiers if "License ::" in str(value)]
        if values:
            return "; ".join(values)
    return "NOASSERTION"


def license_class(value: str) -> str:
    """既知の文字列を保守的な分類へ写す。 / Classify license metadata conservatively."""
    lowered = value.lower()
    if not value or value == "NOASSERTION":
        return "unknown"
    if "noncommercial" in lowered or "by-nc" in lowered:
        return "non-commercial"
    if "agpl" in lowered or "affero general public license" in lowered or "odbl" in lowered:
        return "strong-copyleft"
    if "lesser general public license" in lowered:
        return "weak-copyleft"
    if "general public license" in lowered:
        return "strong-copyleft"
    if "gpl" in lowered and "lgpl" not in lowered:
        return "strong-copyleft"
    if any(item in lowered for item in ("lgpl", "mpl", "epl", "cddl")):
        return "weak-copyleft"
    return "permissive"


def capture_resolution(report_path: Path) -> None:
    """pip --report を小さな再現可能スナップショットにする。 / Capture a compact resolver snapshot."""
    report = load_json(report_path)
    installs = report.get("install")
    if not isinstance(installs, list) or not installs:
        raise AuditError("pip report has no install records")
    components = []
    for record in installs:
        if not isinstance(record, dict) or not isinstance(record.get("metadata"), dict):
            raise AuditError("pip report has an invalid install record")
        metadata = record["metadata"]
        name = metadata.get("name")
        version = metadata.get("version")
        if not isinstance(name, str) or not isinstance(version, str):
            raise AuditError("pip report component lacks name/version")
        license_files = metadata.get("license_file", [])
        if isinstance(license_files, str):
            license_files = [license_files]
        if not isinstance(license_files, list):
            license_files = []
        evidence = _metadata_license(metadata)
        components.append({
            "name": normalise(name),
            "display_name": name,
            "version": version,
            "license_metadata": evidence,
            "class": license_class(evidence),
            "license_files": sorted(str(value) for value in license_files),
            "requested": bool(record.get("requested", False)),
        })
    components.sort(key=lambda item: item["name"])
    names = [item["name"] for item in components]
    if len(names) != len(set(names)):
        raise AuditError("pip report resolved a distribution more than once")
    environment = report.get("environment", {})
    snapshot = {
        "schema": 1,
        "command": "py -3.11 -m pip install --dry-run --ignore-installed --report <file> .[all-extras]",
        "environment": {
            "implementation_name": environment.get("implementation_name", ""),
            "python_version": environment.get("python_version", ""),
            "sys_platform": environment.get("sys_platform", ""),
            "platform_machine": environment.get("platform_machine", ""),
        },
        "components": components,
    }
    RESOLUTION.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def asset_paths(asset: dict[str, Any]) -> set[str]:
    """台帳の glob を追跡済みファイルへ展開する。 / Expand ledger globs to tracked files."""
    matched: set[str] = set()
    for pattern in asset["paths"]:
        for candidate in ROOT.glob(pattern):
            if candidate.is_file():
                matched.add(candidate.relative_to(ROOT).as_posix())
    return matched


def figure_source_records() -> list[dict[str, Any]]:
    """公開図の第三者出典を figures.json から拾う。 / Collect public figure provenance."""
    records = []
    for path in sorted((ROOT / "docs" / "articles" / "assets" / "poc").glob("**/figures.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise AuditError("invalid figures ledger %s: %s" % (path, exc)) from exc
        entries = payload.get("figures", []) if isinstance(payload, dict) else payload
        if not isinstance(entries, list):
            raise AuditError("figures ledger must be a list: %s" % path)
        for item in entries:
            if not isinstance(item, dict):
                continue
            source = "%s %s" % (item.get("source", ""), item.get("caption", ""))
            if not _EXTERNAL_MARKER.search(source):
                continue
            file_name = item.get("file")
            if not isinstance(file_name, str) or not file_name:
                raise AuditError("external figure without file in %s" % path)
            records.append({
                "poc": path.parent.name,
                "file": file_name,
                "source": str(item.get("source", "")).replace("\n", " "),
                "unrecorded": not bool(str(item.get("source", "")).strip()),
            })
    if not records:
        raise AuditError("no externally sourced public figures were found")
    return records


def validate(policy: dict[str, Any], assets: dict[str, Any], resolution: dict[str, Any]) -> None:
    """新規依存・同梱物を空で通さない。 / Reject unreviewed dependencies and material."""
    packages = policy.get("packages")
    if not isinstance(packages, dict) or len(packages) < 48:
        raise AuditError("dependency policy is unexpectedly small")
    scopes = requirement_scopes()
    missing = sorted(set(scopes) - set(packages))
    if missing:
        raise AuditError("declared dependencies lack license records: %s" % ", ".join(missing))
    for name in scopes:
        record = packages[name]
        if not isinstance(record, dict) or not all(record.get(key) for key in ("spdx", "class", "license_files", "effect", "commercial")):
            raise AuditError("incomplete dependency record: %s" % name)
        if record["class"] not in {"permissive", "weak-copyleft", "strong-copyleft", "non-commercial", "unknown"}:
            raise AuditError("invalid license class for %s" % name)
        if record["class"] in {"non-commercial", "unknown"}:
            raise AuditError("default or extra dependency is not distributable: %s" % name)
    for name in ("pillow", "pyside6", "pyside6-essentials", "pybind11"):
        if name not in packages:
            raise AuditError("1.2.0 planned dependency is not pre-audited: %s" % name)
    exceptions = policy.get("strong_copyleft_exceptions", {})
    excluded = default_setup_exclusions()
    strong_extras: set[str] = set()
    for name, record in packages.items():
        if name not in scopes or record["class"] != "strong-copyleft":
            continue
        exception = exceptions.get(name)
        if not isinstance(exception, dict):
            raise AuditError("strong-copyleft dependency is not explicitly excepted: %s" % name)
        only_extra = exception.get("only_extra")
        if set(scopes[name]) != {only_extra}:
            raise AuditError("strong-copyleft dependency escaped its test-only extra: %s" % name)
        strong_extras.add(str(only_extra))
        entry = excluded.get(str(only_extra))
        if entry is None or entry["dependency"] != name or entry["license"] != record["spdx"]:
            raise AuditError("strong-copyleft extra lacks a matching full-setup exclusion: %s" % name)
    if set(excluded) != strong_extras:
        raise AuditError("default setup exclusions do not exactly cover strong-copyleft extras")
    if "all" in strong_extras:
        raise AuditError("the full extra includes a strong-copyleft dependency")

    listed_assets = assets.get("assets")
    if not isinstance(listed_assets, list) or len(listed_assets) < 18:
        raise AuditError("third-party material inventory is unexpectedly small")
    classified: set[str] = set()
    wheel_count = 0
    for asset in listed_assets:
        if not isinstance(asset, dict) or not all(asset.get(key) for key in ("id", "paths", "license", "kind", "source", "source_url", "changes")):
            raise AuditError("incomplete third-party material record")
        found = asset_paths(asset)
        if not found:
            raise AuditError("third-party material record matches no files: %s" % asset["id"])
        classified.update(found)
        if asset.get("wheel"):
            wheel_count += len(found)
    if wheel_count < 10:
        raise AuditError("too few wheel third-party files were counted")
    third_party_data = [
        rel for rel in _shipped_data_files()
        if Path(rel).name != "README.md" and not Path(rel).name.startswith(".")
    ]
    first_party_data = (
        "data/auto_specs/*", "data/gaussbonnet/genus*.npz", "data/macro_champions.json", "data/wave0_pins.json",
    )
    unclassified = [path for path in third_party_data if path not in classified and not any(fnmatch.fnmatch(path, pattern) for pattern in first_party_data)]
    if unclassified:
        raise AuditError("data files need provenance records: %s" % ", ".join(sorted(unclassified)[:10]))
    unrecorded_figures = {
        "%s/%s" % (item["poc"], item["file"])
        for item in figure_source_records() if item["unrecorded"]
    }
    unresolved = assets.get("unresolved_public_figures", {})
    cap = assets.get("unresolved_public_figure_cap")
    if not isinstance(unresolved, dict) or not isinstance(cap, int) or cap < 0:
        raise AuditError("public-figure unresolved-provenance ledger is invalid")
    if any(not isinstance(reason, str) or not reason.strip() for reason in unresolved.values()):
        raise AuditError("an unresolved public figure needs a non-empty reason")
    if len(unresolved) > cap:
        raise AuditError("unresolved public-figure count exceeds its cap")
    if unrecorded_figures != set(unresolved):
        raise AuditError(
            "public figures with missing provenance changed: expected %s, found %s"
            % (sorted(unresolved), sorted(unrecorded_figures))
        )
    components = resolution.get("components")
    if not isinstance(components, list) or len(components) < len(scopes):
        raise AuditError("resolver snapshot is missing dependencies")
    resolved = {item.get("name") for item in components if isinstance(item, dict)}
    unresolved = sorted(set(scopes) - resolved)
    if unresolved:
        raise AuditError("resolver snapshot lacks declared dependencies: %s" % ", ".join(unresolved))


def _md(value: Any) -> str:
    """表セルを Markdown 安全な 1 行にする。 / Escape a Markdown table cell."""
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_dependency_inventory(policy: dict[str, Any], resolution: dict[str, Any]) -> str:
    """依存と推移的解決の表を描く。 / Render direct and transitive dependency inventory."""
    scopes = requirement_scopes()
    packages = policy["packages"]
    lines = [
        "# Dependency licence inventory",
        "",
        "Generated by `tools/license_audit.py`; do not edit by hand.",
        "",
        "## Items requiring a decision first",
        "",
        "- `plyfile` is GPL-3.0-or-later. It is limited to the `export-verify` test extra and is not bundled in the wheel. The full setup default must exclude that extra; use `fullseye setup --include export-verify` only when independent export verification is needed.",
        "- `PySide6` is currently optional but planned for the 1.2.0 default installation. Use it only as a dynamically imported, replaceable dependency; retain Qt/PySide notices and use a Qt commercial licence if the LGPL route is unsuitable. Fullseye's commercial licence does not change Qt's licence.",
        "- `examples/data/fintraffic_sun_2026_09_20.json` carries an ODbL provenance question. It is reported separately in the material inventory; decide Produced Work vs Derivative Database before a commercial redistribution.",
        "",
        "## Direct declarations",
        "",
        "The package wheel does not vendor these distributions: pip installs them into the environment. `License files inspected` identifies the files retained by the relevant distribution, not files copied into the Fullseye wheel.",
        "",
        "| Package | Default / extra | SPDX expression | class | Licence files inspected | Apache-2.0 and commercial-distribution effect |",
        "|---|---|---|---|---|---|",
    ]
    for name in sorted(scopes):
        record = packages[name]
        lines.append("| %s | %s | %s | %s | %s | %s |" % (
            name, _md(", ".join(scopes[name])), _md(record["spdx"]), record["class"],
            _md(", ".join(record["license_files"])), _md(record["effect"] + " " + record["commercial"]),
        ))
    lines += [
        "",
        "## Prepared 1.2.0 default-dependency notices",
        "",
        "| Candidate | SPDX expression | condition before making it default |",
        "|---|---|---|",
    ]
    for name in ("pillow", "pyside6", "pyside6-essentials", "pybind11"):
        record = packages[name]
        lines.append("| %s | %s | %s |" % (name, _md(record["spdx"]), _md(record["effect"])))
    components = resolution["components"]
    counts = Counter(item["class"] for item in components)
    environment = resolution.get("environment", {})
    lines += [
        "",
        "## Transitive resolution snapshot",
        "",
        "This is a measured Windows resolver snapshot, captured with `%s` on Python %s / %s. It contains %d distributions: %s. It is an audit snapshot rather than a lock file; regenerate and review it when dependency ranges change." % (
            resolution.get("command", "pip --report"), environment.get("python_version", "unknown"), environment.get("sys_platform", "unknown"), len(components),
            ", ".join("%s %d" % (kind, counts[kind]) for kind in sorted(counts)),
        ),
        "",
        "| Distribution | resolved version | PyPI metadata licence evidence | class | metadata licence files |",
        "|---|---|---|---|---|",
    ]
    for component in components:
        lines.append("| %s | %s | %s | %s | %s |" % (
            _md(component["display_name"]), component["version"], _md(component["license_metadata"]),
            component["class"], _md(", ".join(component.get("license_files", [])) or "—"),
        ))
    return "\n".join(lines) + "\n"


def render_asset_inventory(assets: dict[str, Any]) -> str:
    """第三者の同梱物と公開図の表を描く。 / Render third-party material and public-figure inventory."""
    rows = []
    attention = []
    for asset in assets["assets"]:
        found = sorted(asset_paths(asset))
        rows.append((asset, found))
        if asset.get("status") == "attention":
            attention.append(asset)
    figure_rows = figure_source_records()
    unrecorded = [item for item in figure_rows if item["unrecorded"]]
    by_poc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in figure_rows:
        by_poc[item["poc"]].append(item)
    lines = [
        "# Third-party material inventory",
        "",
        "Generated by `tools/license_audit.py`; do not edit by hand.",
        "",
        "## Items requiring a decision first",
        "",
    ]
    for asset in attention:
        lines.append("- `%s`: %s" % (asset["id"], asset.get("note", "review required")))
    unresolved_reasons = assets.get("unresolved_public_figures", {})
    for item in unrecorded:
        key = "%s/%s" % (item["poc"], item["file"])
        lines.append("- `%s`: %s Do not redistribute it in a wheel." % (key, unresolved_reasons[key]))
    lines += [
        "",
        "## Files held in the repository",
        "",
        "| Material | files counted | licence | type | ships in wheel | source / changes |",
        "|---|---:|---|---|---|---|",
    ]
    for asset, found in rows:
        lines.append("| %s | %d | %s | %s | %s | %s; %s |" % (
            asset["id"], len(found), _md(asset["license"]), asset["kind"], "yes" if asset.get("wheel") else "no",
            _md(asset["source"]), _md(asset["changes"]),
        ))
    lines += [
        "",
        "## ViEW / article figures with an external source declaration",
        "",
        "The source text below comes from the corresponding `figures.json`. Every externally sourced public figure must have a source field unless it is listed with a reason in the bounded unresolved-provenance ledger; attribution remains next to the public figure through the generated article and ViEW pages.",
        "",
        "| PoC | externally sourced figures | source declaration |",
        "|---|---:|---|",
    ]
    for poc, records in sorted(by_poc.items()):
        declarations = sorted({record["source"] or "UNRECORDED — see items requiring a decision" for record in records})
        lines.append("| %s | %d | %s |" % (poc, len(records), _md(" / ".join(declarations))))
    return "\n".join(lines) + "\n"


def render_notices(policy: dict[str, Any], assets: dict[str, Any]) -> str:
    """wheel に同梱する通知を描く。 / Render notices copied into the wheel."""
    lines = [
        "# Third-party notices",
        "",
        "Generated by `tools/license_audit.py`; the identical copy at `fullseye/THIRD_PARTY_NOTICES.md` is shipped in the wheel.",
        "",
        "Fullseye itself is licensed under Apache-2.0; see `LICENSE` and `NOTICE`. This file identifies third-party material copied into this repository or wheel. Python dependencies are installed separately by pip and retain the notices in their own distributions.",
        "",
        "## Wheel material",
        "",
    ]
    for asset in assets["assets"]:
        if not asset.get("wheel"):
            continue
        paths = sorted(asset_paths(asset))
        lines += [
            "### %s" % asset["id"],
            "",
            "- Files: %s" % ", ".join("`%s`" % path for path in paths),
            "- Source: %s (%s)" % (asset["source"], asset["source_url"]),
            "- Licence: %s" % asset["license"],
            "- Changes: %s" % asset["changes"],
            "",
        ]
    lines += [
        "## scikit-image sample-data BSD-3-Clause text",
        "",
        "The four Studio samples identified above are redistributed under this notice:",
        "",
        "```text",
        _BSD3_SCITKIT.rstrip(),
        "```",
        "",
        "## Dynamically installed dependencies",
        "",
        "The following direct dependencies are not copied into the Fullseye wheel. Their installed distributions carry their own licence files; the authoritative audited expressions and file locations are in `docs/licenses/DEPENDENCY_INVENTORY.md`.",
        "",
    ]
    for name in sorted(requirement_scopes()):
        record = policy["packages"][name]
        lines.append("- `%s` — %s (%s)" % (name, record["spdx"], record["class"]))
    lines += [
        "",
        "## Prepared 1.2.0 default-dependency notices",
        "",
    ]
    for name in ("pillow", "pyside6", "pyside6-essentials", "pybind11"):
        record = policy["packages"][name]
        lines.append("- `%s` — %s. %s" % (name, record["spdx"], record["effect"]))
    lines += [
        "",
        "For PySide6/Qt, Fullseye dynamically imports the binding only when Studio is used. Keep the installed PySide6/Qt distribution replaceable and retain the notices and corresponding-source information provided by that distributor. A Fullseye commercial licence does not grant Qt commercial rights.",
    ]
    return "\n".join(lines) + "\n"


def write_or_check(path: Path, expected: str, check: bool) -> bool:
    """LF 固定で書くか drift を返す。 / Write LF output or report drift."""
    current = path.read_bytes().replace(b"\r\n", b"\n") if path.is_file() else None
    encoded = expected.encode("utf-8")
    if check:
        if current != encoded:
            print("drift: %s" % path.relative_to(ROOT))
            return False
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(expected, encoding="utf-8", newline="\n")
    print("wrote %s" % path.relative_to(ROOT))
    return True


def main(argv: list[str] | None = None) -> int:
    """CLI の入口。 / Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check generated inventories for drift")
    parser.add_argument("--capture-report", type=Path, help="capture a pip --report JSON before rendering")
    args = parser.parse_args(argv)
    try:
        if args.capture_report is not None:
            capture_resolution(args.capture_report)
            print("captured %s" % RESOLUTION.relative_to(ROOT))
        policy = load_json(POLICY)
        assets = load_json(ASSETS)
        resolution = load_json(RESOLUTION)
        validate(policy, assets, resolution)
        outputs = {
            DEPENDENCY_INVENTORY: render_dependency_inventory(policy, resolution),
            ASSET_INVENTORY: render_asset_inventory(assets),
            NOTICES: render_notices(policy, assets),
            WHEEL_NOTICES: render_notices(policy, assets),
        }
        okay = all(write_or_check(path, text, args.check) for path, text in outputs.items())
        if args.check and okay:
            print("license inventories are up to date")
        return 0 if okay else 1
    except (AuditError, OSError, tomllib.TOMLDecodeError) as exc:
        print("license audit failed: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
