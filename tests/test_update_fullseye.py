"""tools/update_fullseye.py(環境をつぶさない安全アップデータ)のテスト。

本物の repo/リモートを触らずに検証する: preflight の dirty 拒否は一時 git repo、
RAG スキル更新は一時スキルディレクトリ(バックアップが残ること=手編集を失わない
保証)を使う。QSettings には触れない設計なので、触れないことはコード上の不変条件
(update_fullseye は QSettings を import しない)としてここで固定する。
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import setup_claude_rag as rag
import update_fullseye as upd

_git_ok = shutil.which("git") is not None
need_git = pytest.mark.skipif(not _git_ok, reason="git 不在")


def _mk_repo(path: Path):
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    (path / "a.txt").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(path), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "init"], check=True)


@need_git
def test_preflight_refuses_dirty_worktree(tmp_path, monkeypatch):
    _mk_repo(tmp_path)
    monkeypatch.setattr(upd, "REPO", tmp_path)
    assert upd.preflight() == []                       # clean -> safe
    (tmp_path / "a.txt").write_text("edited by user\n", encoding="utf-8")
    problems = upd.preflight()
    assert problems and "uncommitted" in problems[0]   # dirty -> refuse, never touch


@need_git
def test_pull_skipped_without_remote(tmp_path, monkeypatch):
    _mk_repo(tmp_path)
    monkeypatch.setattr(upd, "REPO", tmp_path)
    msg = upd.pull_ff_only(check=False)
    assert "skipped" in msg                             # no remote -> no-op, no crash


def test_rag_skill_update_backs_up_user_edits(tmp_path, monkeypatch):
    monkeypatch.setattr(rag, "default_target", lambda: tmp_path)
    # not installed -> untouched
    assert "not installed" in upd.update_rag_skill(check=False)
    assert not (tmp_path / rag.SKILL_NAME).exists()
    # installed + user-edited -> backup keeps the edit, live copy refreshed
    rag.install(tmp_path)
    skill_md = tmp_path / rag.SKILL_NAME / "SKILL.md"
    skill_md.write_text(skill_md.read_text(encoding="utf-8") + "\nUSER EDIT\n",
                        encoding="utf-8")
    msg = upd.update_rag_skill(check=False)
    assert "backed up" in msg
    baks = list(tmp_path.glob(rag.SKILL_NAME + ".bak-*"))
    assert len(baks) == 1
    assert "USER EDIT" in (baks[0] / "SKILL.md").read_text(encoding="utf-8")
    assert "USER EDIT" not in skill_md.read_text(encoding="utf-8")


def test_updater_never_touches_qsettings():
    """設計不変条件: アップデータは Qt/QSettings を import しない(=Studio の環境設定に
    構造的に触れられない)。docstring での言及は許す — 検査対象は実 import。"""
    src = (Path(upd.__file__)).read_text(encoding="utf-8")
    assert "PySide6" not in src and "QtCore" not in src
    assert "import PySide6" not in src
