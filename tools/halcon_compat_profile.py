"""Generate the registry's evidence-based HALCON compatibility profile.

``Op.halcon`` is a name mapping, not a compatibility claim.  This generator
keeps unverified mappings explicit and validates every manually approved test
node before accepting it.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import op_example_index  # noqa: E402

PROFILE = ROOT / "docs" / "halcon_compat_profile.json"
OVERRIDES = ROOT / "docs" / "halcon_compat_overrides.json"
MANIFEST = ROOT / "docs" / "halcon_comparison_manifest.json"
TEST_FILES = [
    "tests/test_halcon_comparison_fixes_2026_10_21.py",
    "tests/test_halcon_comparison_fixes_2026_10_22.py",
    "tests/test_halcon_ncc_entry_2026_10_22.py",
    "tests/test_connection_backends_agree_2026_10_22.py",
]


def registry_rows() -> list[dict]:
    """Rows of the committed machine-readable index that carry a reference mapping.

    The live registry (``imgevolve._all_ops()``) depends on which optional backends are
    installed, so a profile generated on one machine drifted on CI (2026-10-22: 512 vs
    510 entries). ``docs/OP_INDEX.json`` is committed and checked by ``regen_all --check``,
    so it is the environment-independent scope.
    """
    index = json.loads((ROOT / "docs" / "OP_INDEX.json").read_text(encoding="utf-8"))
    return [r for r in index["ops"] if r.get("halcon")]


def _normalised_sha256(path: Path) -> str:
    """SHA-256 of the file with CRLF folded to LF (checkouts differ by OS)."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _test_functions(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {n.name for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test_")}


def validate_evidence(node: str) -> None:
    parts = node.split("::")
    if len(parts) != 2 or not parts[0].startswith("tests/"):
        raise ValueError(f"invalid test node id: {node}")
    path = ROOT / parts[0]
    if not path.is_file() or parts[1] not in _test_functions(path):
        raise ValueError(f"test node id does not exist: {node}")


def generate_profile() -> dict:
    rows = registry_rows()
    by_name = {r["name"]: r for r in rows}
    raw = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    overrides = raw["overrides"]
    extra = sorted(set(overrides) - set(by_name))
    if extra:
        raise ValueError(f"override ops are not mapped registry entries: {extra}")
    for name, item in overrides.items():
        if not item.get("evidence"):
            raise ValueError(f"contract override has no evidence: {name}")
        for node in item["evidence"]:
            validate_evidence(node)

    # 例の有無は registry でなく索引の名前で静的に走査する(registry は環境依存)。
    examples = op_example_index._index_for([r["name"] for r in rows], "examples")
    entries = []
    for row in sorted(rows, key=lambda r: r["name"]):
        name = row["name"]
        if name in overrides:
            item = overrides[name]
            profile, evidence, notes = "contract_verified", item["evidence"], item["notes"]
        elif examples.get(name):
            profile, evidence = "functional_analogue", []
            notes = "A worked example exercises this op; reference-contract equivalence is not verified."
        else:
            profile, evidence = "unknown", []
            notes = "Name mapping only; no op-level worked-example signal or reference-contract evidence."
        entries.append({"op": name, "halcon": row["halcon"], "profile": profile,
                        "evidence": evidence, "notes": notes})
    counts = Counter(e["profile"] for e in entries)
    return {
        "about": "A name mapping is not a compatibility claim. Unknown is never promoted to PASS.",
        "profiles": {k: counts[k] for k in ("contract_verified", "functional_analogue", "unknown")},
        "entries": entries,
    }


def _source_line() -> str:
    text = (ROOT / "docs" / "HALCON_COVERAGE.md").read_text(encoding="utf-8")
    match = re.search(r"^Source: `([^`]+)` \(version ([^)]+)\)\.$", text, re.MULTILINE)
    if not match:
        raise ValueError("HALCON_COVERAGE.md source line not found")
    return match.group(0), match.group(1), match.group(2)


def _literal_seeds(path: Path) -> list[int]:
    text = path.read_text(encoding="utf-8")
    values = re.findall(r"default_rng\(\s*(\d+)\s*\)|\bseed\s*=\s*(\d+)", text)
    return [int(a or b) for a, b in values]


def generate_manifest() -> dict:
    source_line, source_url, version = _source_line()
    package_version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    tests = []
    for rel in TEST_FILES:
        tests.append({"file": rel, "sha256": _normalised_sha256(ROOT / rel),
                      "seeds": _literal_seeds(ROOT / rel)})
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    return {
        "about": "Test paths, hashes, seeds, documentation source, and package version are normative. Generation date, commit, and dirty are informational and ignored by --check.",
        "reference_documentation": {"version": version, "source_url": source_url,
                                    "source_line": source_line},
        "package_version": package_version,
        "git": {"commit": commit, "dirty": dirty},
        "generation_date": "2026-10-22",
        "tests": tests,
    }


def _stable_manifest(value: dict) -> dict:
    value = dict(value)
    value.pop("generation_date", None)
    value.pop("git", None)
    return value


def _dump(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def _summary(profile: dict) -> None:
    print("compatibility profile:", " ".join(f"{k}={v}" for k, v in profile["profiles"].items()))
    families = Counter()
    rows = {r["name"]: r for r in registry_rows()}
    for e in profile["entries"]:
        if e["profile"] == "unknown":
            families[rows[e["op"]].get("category", "uncategorized")] += 1
    print("top unknown families:", ", ".join(f"{k}={v}" for k, v in families.most_common(10)))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--manifest", action="store_true")
    args = parser.parse_args(argv)
    profile = generate_profile()
    manifest = generate_manifest()
    _summary(profile)
    if args.check:
        ok = PROFILE.is_file() and PROFILE.read_text(encoding="utf-8") == _dump(profile)
        if args.manifest:
            try:
                current = json.loads(MANIFEST.read_text(encoding="utf-8"))
                ok = ok and _stable_manifest(current) == _stable_manifest(manifest)
            except (OSError, ValueError):
                ok = False
        if not ok:
            print("generated HALCON compatibility data differs", file=sys.stderr)
            return 1
        return 0
    PROFILE.write_text(_dump(profile), encoding="utf-8")
    if args.manifest:
        if MANIFEST.is_file():
            try:
                old = json.loads(MANIFEST.read_text(encoding="utf-8"))
                manifest["git"] = old["git"]
                manifest["generation_date"] = old["generation_date"]
            except (KeyError, ValueError):
                pass
        MANIFEST.write_text(_dump(manifest), encoding="utf-8")
    import lib_coverage
    lib_coverage.main(["--compat-only"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
