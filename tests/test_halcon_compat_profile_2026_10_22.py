import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "docs" / "halcon_compat_profile.json"
OVERRIDES = ROOT / "docs" / "halcon_compat_overrides.json"
MANIFEST = ROOT / "docs" / "halcon_comparison_manifest.json"


def _profile():
    return json.loads(PROFILE.read_text(encoding="utf-8"))


def test_profile_json_is_current():
    result = subprocess.run(
        [sys.executable, "tools/halcon_compat_profile.py", "--check", "--manifest"],
        cwd=ROOT, text=True, capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_profile_and_registry_are_bijective(capsys):
    # 索引(committed)と照合する。live registry は optional backend の有無で変わる。
    index = json.loads((ROOT / "docs" / "OP_INDEX.json").read_text(encoding="utf-8"))
    registry = {r["name"] for r in index["ops"] if r.get("halcon")}
    profiled = {e["op"] for e in _profile()["entries"]}
    print(f"registry={len(registry)} profile={len(profiled)}")
    assert profiled == registry
    assert "registry=" in capsys.readouterr().out


def _functions(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}


def test_contract_evidence_resolves_and_is_overridden():
    overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))["overrides"]
    entries = _profile()["entries"]
    assert entries
    errors = []
    for entry in entries:
        if entry["profile"] != "contract_verified":
            continue
        if entry["op"] not in overrides:
            errors.append(f"not overridden: {entry['op']}")
        if not entry["evidence"]:
            errors.append(f"no evidence: {entry['op']}")
        for node in entry["evidence"]:
            rel, function = node.split("::")
            path = ROOT / rel
            if not path.is_file() or function not in _functions(path):
                errors.append(f"missing test node: {node}")
    assert not errors, errors


def test_manifest_hashes_and_files_match():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["tests"]
    errors = []
    for item in manifest["tests"]:
        path = ROOT / item["file"]
        if not path.is_file():
            errors.append(f"missing: {item['file']}")
        elif hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() != item["sha256"]:
            errors.append(f"hash mismatch: {item['file']}")
    assert not errors, errors


def test_parity_section_counts_match_profile():
    counts = _profile()["profiles"]
    text = (ROOT / "docs" / "HALCON_PARITY.md").read_text(encoding="utf-8")
    section = text.split("## Compatibility profile (H15)", 1)[1]
    found = {name: int(value) for name, value in
             re.findall(r"^\| (contract_verified|functional_analogue|unknown) \| (\d+) \|$",
                        section, re.MULTILINE)}
    assert found == counts
    assert "Unknown is never promoted to PASS." in section
