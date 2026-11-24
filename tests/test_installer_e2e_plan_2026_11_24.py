"""共有 E2E harness を手元では安全に dry-run できる / safely inspect every CI stage locally."""
from __future__ import annotations

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


def test_e2e_source_explicitly_checks_the_artifacts_it_creates():
    text = (ROOT / "tools" / "installer_e2e.py").read_text(encoding="utf-8")
    for token in ("Fullseye Studio.lnk", "fullseye-studio.desktop", "RAG_MANIFEST.json", "OP_SEARCH.json", "registry-gone", "FULLSEYE_E2E_ALLOW_AUTO_SHORTCUTS"):
        assert token in text
