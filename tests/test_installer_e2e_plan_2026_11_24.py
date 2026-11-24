"""共有 E2E harness を手元では安全に dry-run できる / safely inspect every CI stage locally."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_e2e_dry_run_creates_no_workdir_and_lists_full_lifecycle(tmp_path):
    work = tmp_path / "must-not-exist"
    got = subprocess.run([sys.executable, str(ROOT / "tools" / "installer_e2e.py"), "--dry-run", "--workdir", str(work)],
                         cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert got.returncode == 0, got.stderr
    assert not work.exists(), "--dry-run must never touch a developer's menus, registry, Claude files, or even its workdir"
    for stage in ("install-wheel", "first-command", "setup-all", "rag-index", "rag-search", "studio-offscreen", "uninstall"):
        assert stage in got.stdout


def test_e2e_real_run_refuses_without_ci_or_explicit_real_user_state_opt_in(tmp_path):
    """拒否は venv / Desktop / Start Menu / HKCU に触れる前に起きる / refusal happens before any venv, Desktop, Start Menu, or HKCU change."""
    work = tmp_path / "must-not-exist"
    env = dict(os.environ)
    env.pop("CI", None)
    env.pop("FULLSEYE_E2E_ALLOW_REAL_USER_STATE", None)
    got = subprocess.run([sys.executable, str(ROOT / "tools" / "installer_e2e.py"), "--wheel", str(tmp_path / "fake.whl"),
                          "--workdir", str(work)], cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert got.returncode == 2
    assert not work.exists(), "a refused real E2E run must not create its workdir or touch user state"
    assert "拒否しました" in got.stdout and "Refused:" in got.stdout
    assert "CI=true" in got.stdout and "FULLSEYE_E2E_ALLOW_REAL_USER_STATE='1'" in got.stdout
    assert "--dry-run" in got.stdout


def test_e2e_source_explicitly_checks_the_artifacts_it_creates():
    text = (ROOT / "tools" / "installer_e2e.py").read_text(encoding="utf-8")
    for token in ("Fullseye Studio.lnk", "fullseye-studio.desktop", "RAG_MANIFEST.json", "OP_SEARCH.json", "registry-gone", "FULLSEYE_E2E_ALLOW_AUTO_SHORTCUTS"):
        assert token in text


def test_e2e_forces_utf8_for_children_and_decodes_logs_fail_softly():
    """Windows のローカル code page が日本語の子出力を壊しても、artifact log は必ず残す。"""
    text = (ROOT / "tools" / "installer_e2e.py").read_text(encoding="utf-8")
    assert '"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"' in text
    assert 'encoding="utf-8", errors="replace"' in text
