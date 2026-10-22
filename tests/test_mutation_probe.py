"""層別の変異探針そのものを軽量に検査する。全試験の実行はここでは行わない。"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("mutation_probe", ROOT / "tools" / "mutation_probe.py")
MP = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MP)


def _mini_root(tmp_path: Path, tier: str) -> Path:
    root = tmp_path / "repo"
    target = Path(MP.TIERS[tier][0])
    if tier == "t6":
        shutil.copytree(ROOT / "fullseye", root / "fullseye")
    else:
        (root / target.parent).mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / target, root / target)
    (root / "docs").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "docs" / "gate_inventory.json", root / "docs" / "gate_inventory.json")
    if tier != "t6":
        shutil.copy2(ROOT / "imgevolve.py", root / "imgevolve.py")
    return root


def test_list_names_every_inventory_tier(capsys):
    MP.list_probe(ROOT)
    output = capsys.readouterr().out
    inventory = MP.load_inventory(ROOT)
    listed = {line.split(":", 1)[0] for line in output.splitlines()}
    assert {t["id"] for t in inventory["tiers"]} <= listed
    assert set(MP.KINDS) <= {line.split(":", 1)[0] for line in output.splitlines()}


@pytest.mark.parametrize("tier", sorted(MP.TIERS))
@pytest.mark.parametrize("kind", list(MP.KINDS))
def test_inject_restore_exact_round_trip(tmp_path, tier, kind):
    root = _mini_root(tmp_path, tier)
    target = root / MP.TIERS[tier][0]
    before = target.read_bytes()
    MP.inject(root, tier, kind, f"probe_{tier}_{kind}")
    assert MP.BEGIN.encode() in target.read_bytes()
    assert (root / "probe_injected.py").is_file()
    compile((root / "probe_injected.py").read_text(encoding="utf-8"),
            "probe_injected.py", "exec")
    MP.restore(root)
    assert target.read_bytes() == before
    assert not (root / "probe_injected.py").exists()
    assert not (root / MP.STATE).exists()


@pytest.mark.parametrize("tier", sorted(MP.TIERS))
def test_injected_op_uses_the_tier_discovery_path(tmp_path, tier):
    root = _mini_root(tmp_path, tier)
    name = f"probe_{tier}_a"
    MP.inject(root, tier, "a", name)
    if tier == "t6":
        script = f"import fullseye; assert callable(fullseye.{name})"
        (root / "fullseye" / "__init__.py").parent.mkdir(exist_ok=True)
    else:
        script = f"import imgevolve; assert {name!r} in {{r['name'] for r in imgevolve._build_op_index()['ops']}}"
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join((str(root), str(ROOT)))
    proc = subprocess.run([sys.executable, "-c", script], cwd=root, env=env,
                          capture_output=True, text=True, timeout=120)
    MP.restore(root)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_parse_junit_collects_failures_errors_and_durations(tmp_path):
    xml = tmp_path / "tiny.xml"
    xml.write_text("""<testsuite time="1.5">
      <testcase classname="tests.test_x" name="test_ok" time="0.1" />
      <testcase classname="tests.test_x" name="test_bad" time="0.2"><failure>no</failure></testcase>
      <testcase classname="tests.test_y" name="test_error" time="0.3"><error>boom</error></testcase>
    </testsuite>""", encoding="utf-8")
    got = MP.parse_junit(xml)
    assert got["failed"] == ["tests.test_x::test_bad"]
    assert got["errors"] == ["tests.test_y::test_error"]
    assert got["duration"] == 1.5
    assert got["durations"]["tests.test_x::test_ok"] == 0.1


def test_summary_excludes_baseline_and_bookkeeping():
    results = {
        "a": {"failed": ["base", "book"]},
        "b": {"failed": ["base", "book", "raises_gate"]},
        "c": {"failed": ["nan_gate"], "errors": ["base"]},
    }
    got = MP.summarize(results, {"base"})
    assert got["bookkeeping"] == ["book"]
    assert got["caught"]["raises"] is True
    assert got["behavioural"]["raises"] == ["raises_gate"]
    assert got["behavioural"]["nan"] == ["nan_gate"]
    assert got["caught"]["wrong_type"] is False
    assert got["behavioural_gates"] == 2


def test_max_hours_writes_partial_summary_without_starting_kind(tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    (out / "t1_baseline.json").write_text(json.dumps({
        "failed": [], "errors": [], "duration": 7200, "wall_duration": 7200,
    }), encoding="utf-8")
    monkeypatch.setattr(MP, "inject", lambda *a, **k: pytest.fail("kind must not start"))
    args = argparse.Namespace(root=ROOT, out=str(out), tier="t1", kinds="a,b",
                              baseline=True, pytest_args="-n 3", max_hours=1.0)
    MP.run_probe(args)
    summary = json.loads((out / "t1_summary.json").read_text(encoding="utf-8"))
    assert summary["partial"] is True
    assert summary["completed_kinds"] == []


def test_restore_refuses_a_changed_registration_file(tmp_path):
    root = _mini_root(tmp_path, "t1")
    MP.inject(root, "t1", "a", "probe_t1_a")
    target = root / "ops.py"
    target.write_text(target.read_text(encoding="utf-8") + "# foreign edit\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="changed after injection"):
        MP.restore(root)
